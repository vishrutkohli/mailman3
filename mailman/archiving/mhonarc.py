# Copyright (C) 2008 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""MHonArc archiver."""

__metaclass__ = type
__all__ = [
    'MHonArc',
    ]


import hashlib
import logging
import subprocess

from base64 import b32encode
from string import Template
from urlparse import urljoin
from zope.interface import implements

from mailman.configuration import config
from mailman.interfaces.archiver import IArchiver


log = logging.getLogger('mailman.archiver')



class MHonArc:
    """Local MHonArc archiver."""

    implements(IArchiver)

    name = 'mhonarc'
    is_enabled = False

    @staticmethod
    def list_url(mlist):
        """See `IArchiver`."""
        # XXX What about private MHonArc archives?
        web_host = config.domains.get(mlist.host_name, mlist.host_name)
        return Template(config.PUBLIC_ARCHIVE_URL).safe_substitute(
            listname=mlist.fqdn_listname,
            hostname=web_host,
            fqdn_listname=mlist.fqdn_listname,
            )

    @staticmethod
    def permalink(mlist, msg):
        """See `IArchiver`."""
        # XXX What about private MHonArc archives?
        message_id = msg.get('message-id')
        # It is not the archiver's job to ensure the message has a Message-ID.
        assert message_id is not None, 'No Message-ID found'
        # The angle brackets are not part of the Message-ID.  See RFC 2822.
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        else:
            message_id = message_id.strip()
        sha = hashlib.sha1(message_id)
        message_id_hash = b32encode(sha.digest())
        del msg['x-message-id-hash']
        msg['X-Message-ID-Hash'] = message_id_hash
        return urljoin(MHonArc.list_url(mlist), message_id_hash)

    @staticmethod
    def archive_message(mlist, msg):
        """See `IArchiver`."""
        substitutions = config.__dict__.copy()
        substitutions['listname'] = mlist.fqdn_listname
        command = Template(config.MHONARC_COMMAND).safe_substitute(
            substitutions)
        proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True)
        stdout, stderr = proc.communicate(msg.as_string())
        if proc.returncode <> 0:
            log.error('%s: mhonarc subprocess had non-zero exit code: %s' %
                      (msg['message-id'], proc.returncode))
        log.info(stdout)
        log.error(stderr)
