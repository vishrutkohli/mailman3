# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software 
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Local SMTP direct drop-off.

This module delivers messages via SMTP to a locally specified daemon.  This
should be compatible with any modern SMTP server.  It is expected that the MTA
handles all final delivery.  We have to play tricks so that the list object
isn't locked while delivery occurs synchronously.

"""

import os
import time
import socket
import smtplib
from types import TupleType

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.Logging.Syslog import syslog
from Mailman.SafeDict import MsgSafeDict

threading = None
try:
    if mm_cfg.MAX_DELIVERY_THREADS > 0:
        import threading
        import Queue
except ImportError:
    pass

DOT = '.'



def process(mlist, msg, msgdata):
    recips = msgdata.get('recips')
    if not recips:
        # Nobody to deliver to!
        return
    # Get the flat, plain text of the message
    msgtext = msg.as_string(unixfrom=0)
    # Calculate the envelope sender.  When VERPing, envsender is a 2-tuple
    # containing the list's bounces address and the list's host_name.
    envsender = None
    if mlist:
        listname = mlist.internal_name()
        if not msgdata.get('verp'):
            envsender = mlist.getListAddress('bounces')
    else:
        listname = '<no list>'
        if not msgdata.get('verp'):
            envsender = Utils.get_site_email(extra='bounces')
    if envsender is None:
        # We're VERPing.  Pre-calculate what we can.
        bmailbox, bdomain = Utils.ParseEmail(mlist.getListAddress('bounces'))
        envsender = (bmailbox, DOT.join(bdomain))
    # Time to split up the recipient list.  If we're VERPing then each chunk
    # will have exactly one recipient, and we'll hand craft an envelope sender
    # for each one separately.  If we're not VERPing, then we'll chunkify
    # based on SMTP_MAX_RCPTS.  Note that most MTAs have a limit on the number
    # of recipients they'll swallow in a single transaction.
    if msgdata.get('verp'):
        chunks = [[recip] for recip in recips]
    elif mm_cfg.SMTP_MAX_RCPTS <= 0:
        chunks = [recips]
    else:
        chunks = chunkify(recips, mm_cfg.SMTP_MAX_RCPTS)
    refused = {}
    t0 = time.time()
    if threading:
        threaded_deliver(envsender, msgtext, chunks, refused)
    else:
        # Don't supply a hostname and port here because that implies a
        # connection attempt.  We'll connect later in deliver().
        conn = smtplib.SMTP()
        for chunk in chunks:
            deliver(envsender, msgtext, chunk, refused, conn)
        conn.close()
    # Log the successful post
    t1 = time.time()
    d = MsgSafeDict(msg, {'time'    : t1-t0,
                          'size'    : len(msgtext),
                          '#recips' : len(recips),
                          '#refused': len(refused),
                          'listname': listname,
                          'sender'  : msg.get_sender(),
                          })
    # We have to use the copy() method because extended call syntax requires a
    # concrete dictionary object; it does not allow a generic mapping.  It's
    # still worthwhile doing the interpolation in syslog() because it'll catch
    # any catastrophic exceptions due to bogus format strings.
    if mm_cfg.SMTP_LOG_EVERY_MESSAGE:
        syslog.write_ex(mm_cfg.SMTP_LOG_EVERY_MESSAGE[0],
                        mm_cfg.SMTP_LOG_EVERY_MESSAGE[1], kws=d)

    if refused:
        if mm_cfg.SMTP_LOG_REFUSED:
            syslog.write_ex(mm_cfg.SMTP_LOG_REFUSED[0],
                            mm_cfg.SMTP_LOG_REFUSED[1], kws=d)

    elif msgdata.get('tolist'):
        # Log the successful post, but only if it really was a post to the
        # mailing list.  Don't log sends to the -owner, or -admin addrs.
        # -request addrs should never get here.  BAW: it may be useful to log
        # the other messages, but in that case, we should probably have a
        # separate configuration variable to control that.
        if mm_cfg.SMTP_LOG_SUCCESS:
            syslog.write_ex(mm_cfg.SMTP_LOG_SUCCESS[0],
                            mm_cfg.SMTP_LOG_SUCCESS[1], kws=d)

    # Process any failed deliveries.
    tempfailures = []
    permfailures = []
    for recip, (code, smtpmsg) in refused.items():
        # DRUMS is an internet draft, but it says:
        #
        #    [RFC-821] incorrectly listed the error where an SMTP server
        #    exhausts its implementation limit on the number of RCPT commands
        #    ("too many recipients") as having reply code 552.  The correct
        #    reply code for this condition is 452. Clients SHOULD treat a 552
        #    code in this case as a temporary, rather than permanent failure
        #    so the logic below works.
        #
        if code >= 500 and code <> 552:
            # A permanent failure
            permfailures.append(recip)
        else:
            # Deal with persistent transient failures by queuing them up for
            # future delivery.  TBD: this could generate lots of log entries!
            tempfailures.append(recip)
        if mm_cfg.SMTP_LOG_EACH_FAILURE:
            d.update({'recipient': recip,
                      'failcode' : code,
                      'failmsg'  : smtpmsg})
            syslog.write_ex(mm_cfg.SMTP_LOG_EACH_FAILURE[0],
                            mm_cfg.SMTP_LOG_EACH_FAILURE[1], kws=d)
    # Return the results
    if tempfailures or permfailures:
        raise Errors.SomeRecipientsFailed(tempfailures, permfailures)



def chunkify(recips, chunksize):
    # First do a simple sort on top level domain.  It probably doesn't buy us
    # much to try to sort on MX record -- that's the MTA's job.  We're just
    # trying to avoid getting a max recips error.  Split the chunks along
    # these lines (as suggested originally by Chuq Von Rospach and slightly
    # elaborated by BAW).
    chunkmap = {'com': 1,
                'net': 2,
                'org': 2,
                'edu': 3,
                'us' : 3,
                'ca' : 3,
                }
    buckets = {}
    for r in recips:
        tld = None
        i = r.rfind('.')
        if i >= 0:
            tld = r[i+1:]
        bin = chunkmap.get(tld, 0)
        bucket = buckets.get(bin, [])
        bucket.append(r)
        buckets[bin] = bucket
    # Now start filling the chunks
    chunks = []
    currentchunk = []
    chunklen = 0
    for bin in buckets.values():
        for r in bin:
            currentchunk.append(r)
            chunklen = chunklen + 1
            if chunklen >= chunksize:
                chunks.append(currentchunk)
                currentchunk = []
                chunklen = 0
        if currentchunk:
            chunks.append(currentchunk)
            currentchunk = []
            chunklen = 0
    return chunks



def pre_deliver(envsender, msgtext, failures, chunkq, conn):
    while 1:
        # Get the next recipient chunk, if there is one
        try:
            recips = chunkq.get(0)
        except Queue.Empty:
            # We're done
            break
        # Otherwise, process the chunk
        deliver(envsender, msgtext, recips, failures, conn)


def threaded_deliver(envsender, msgtext, chunks, failures):
    threads = {}
    numchunks = len(chunks)
    chunkq = Queue.Queue(numchunks)
    # Populate the queue with all the chunks that need processing.
    for chunk in chunks:
        chunkq.put(chunk)
    # Start all the threads.  We want each thread to share a connection to the
    # SMTP server.
    for i in range(min(numchunks, mm_cfg.MAX_DELIVERY_THREADS)):
        threadfailures = {}
        # Don't supply a hostname and port here because that implies a
        # connection attempt.  We'll connect later in deliver().
        conn = smtplib.SMTP()
        t = threading.Thread(
            target=pre_deliver,
            args=(envsender, msgtext, threadfailures, chunkq, conn))
        threads[t] = (threadfailures, conn)
        t.start()
    # Now wait for all the threads to complete and collate their failure
    # dictionaries.
    for t, (threadfailures, conn) in threads.items():
        t.join()
        failures.update(threadfailures)
        conn.close()
    # All threads have exited
    threads.clear()



def deliver(envsender, msgtext, recips, failures, conn):
    # If we're VERPIng, we have to calculate the envelope sender for each
    # recipient.  Note that the list of recipients must be of length 1.
    if isinstance(envsender, TupleType) and len(recips) == 1:
        mailbox, domain = Utils.ParseEmail(recips[0])
        d = {'bounces': envsender[0],
             'mailbox': mailbox,
             'host'   : DOT.join(domain),
             }
        envsender = '%s@%s' % ((mm_cfg.VERP_FORMAT % d), envsender[1])
    refused = {}
    try:
        # We attempt to connect to the SMTP server.  This test is bogus
        # because there should be a cleaner way to see if we're already
        # connected or not. :(
        if not getattr(conn, 'sock', 0):
            conn.connect(mm_cfg.SMTPHOST, mm_cfg.SMTPPORT)
        try:
            # make sure the connect happens, which won't be done by the
            # constructor if SMTPHOST is false
            refused = conn.sendmail(envsender, recips, msgtext)
        finally:
            conn.quit()
    except smtplib.SMTPRecipientsRefused, e:
        refused = e.recipients
    # MTA not responding, or other socket problems, or any other kind of
    # SMTPException.  In that case, nothing got delivered
    except (socket.error, smtplib.SMTPException), e:
        # BAW: should this be configurable?
        syslog('smtp', 'All recipients refused: %s', e)
        # If the exception had an associated error code, use it, otherwise,
        # fake it with a non-triggering exception code
        errcode = getattr(e, 'smtp_code', -1)
        errmsg = getattr(e, 'smtp_error', 'ignore')
        for r in recips:
            refused[r] = (errcode, errmsg)
    failures.update(refused)
