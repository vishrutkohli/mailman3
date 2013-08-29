===========================
Hooking up your mail server
===========================

Mailman needs to communicate with your *MTA* (*mail transport agent*
or *mail server*, the software which handles sending mail across the
Internet), both to accept incoming mail and to deliver outgoing mail.
Mailman itself never delivers messages to the end user.  It sends them
to its immediate upstream MTA, which delivers them.  In the same way,
Mailman never receives mail directly.  Mail from outside always comes
via the MTA.

Mailman accepts incoming messages from the MTA using the `Local Mail
Transfer Protocol`_ (LMTP_) interface.  Mailman can use other incoming
transports, but LMTP is much more efficient than spawning a process
just to do the delivery.  Most open source MTAs support LMTP for local
delivery.  If yours doesn't, and you need to use a different
interface, please ask on the `mailing list or on IRC`_.

Mailman passes all outgoing messages to the MTA using the `Simple Mail
Transfer Protocol`_ (SMTP_).

Cooperation between Mailman and the MTA requires some configuration of
both.  MTA configuration differs for each of the available MTAs, and
there is a section for each one.  Instructions for Postfix are given
below.  We would really appreciate contributions of configurations for
Exim and Sendmail, and welcome information about other popular open
source mail servers.

Configuring Mailman to communicate with the MTA is straightforward,
and basically the same for all MTAs.  In your ``mailman.cfg`` file,
add (or edit) a section like the following::

    [mta]
    incoming: mailman.mta.postfix.LMTP
    outgoing: mailman.mta.deliver.deliver
    lmtp_host: 127.0.0.1
    lmtp_port: 8024
    smtp_host: localhost
    smtp_port: 25

This configuration is for a system where Mailman and the MTA are on
the same host.

The ``incoming`` and ``outgoing`` parameters identify the Python
objects used to communicate with the MTA.  The ``deliver`` module used
in ``outgoing`` is pretty standard across all MTAs.  The ``postfix``
module in ``incoming`` is specific to Postfix.  See the section for
your MTA below for details on these parameters.

``lmtp_host`` and ``lmtp_port`` are parameters which are used by
Mailman, but also will be passed to the MTA to identify the Mailman
host.  The "same host" case is special; some MTAs (including Postfix)
do not recognize "localhost", and need the numerical IP address.  If
they are on different hosts, ``lmtp_host`` should be set to the domain
name or IP address of the Mailman host.  ``lmtp_port`` is fairly
arbitrary (there is no standard port for LMTP).  Use any port
convenient for your site.  "8024" is as good as any, unless another
service is using it.

``smtp_host`` and ``smtp_port`` are parameters used to identify the
MTA to Mailman.  If the MTA and Mailman are on separate hosts,
``smtp_host`` should be set to the domain name or IP address of the
MTA host.  ``smtp_port`` will almost always be 25, which is the
standard port for SMTP.  (Some special site configurations set it to a
different port.  If you need this, you probably already know that,
know why, and what to do, too!)

Mailman also provides many other configuration variables that you can
use to tweak performance for your operating environment.  See the
``src/mailman/config/schema.cfg`` file for details.


Postfix
=======

Postfix_ is an open source mail server by Wietse Venema.


Mailman settings
----------------

You need to tell Mailman that you are using the Postfix mail server.  In your
``mailman.cfg`` file, add the following section::

    [mta]
    incoming: mailman.mta.postfix.LMTP
    outgoing: mailman.mta.deliver.deliver
    lmtp_host: mail.example.com
    lmtp_port: 8024
    smtp_host: mail.example.com
    smtp_port: 25

Some of these settings are already the default, so take a look at Mailman's
``src/mailman/config/schema.cfg`` file for details.  You'll need to change the
``lmtp_host`` and ``smtp_host`` to the appropriate host names of course.
Generally, Postfix will listen for incoming SMTP connections on port 25.
Postfix will deliver via LMTP over port 24 by default, however if you are not
running Mailman as root, you'll need to change this to a higher port number,
as shown above.


Basic Postfix connections
-------------------------

There are several ways to hook Postfix up to Mailman, so here are the simplest
instructions.  The following settings should be added to Postfix's ``main.cf``
file.

Mailman supports a technique called `Variable Envelope Return Path`_ (VERP) to
disambiguate and accurately record bounces.  By default Mailman's VERP
delimiter is the `+` sign, so adding this setting allows Postfix to properly
handle Mailman's VERP'd messages::

    # Support the default VERP delimiter.
    recipient_delimiter = +

In older versions of Postfix, unknown local recipients generated a temporary
failure.  It's much better (and the default in newer Postfix releases) to
treat them as permanent failures.  You can add this to your ``main.cf`` file
if needed (use the `postconf`_ command to check the defaults)::

    unknown_local_recipient_reject_code = 550

While generally not necessary if you set ``recipient_delimiter`` as described
above, it's better for Postfix to not treat ``owner-`` and ``-request``
addresses specially::

    owner_request_special = no


Transport maps
--------------

By default, Mailman works well with Postfix transport maps as a way to deliver
incoming messages to Mailman's LMTP server.  Mailman will automatically write
the correct transport map when its ``bin/mailman aliases`` command is run, or
whenever a mailing list is created or removed via other commands.  To connect
Postfix to Mailman's LMTP server, add the following to Postfix's ``main.cf``
file::

    transport_maps =
        hash:/path-to-mailman/var/data/postfix_lmtp
    local_recipient_maps =
        hash:/path-to-mailman/var/data/postfix_lmtp
    relay_domains =
        hash:/path-to-mailman/var/data/postfix_domains

where ``path-to-mailman`` is replaced with the actual path that you're running
Mailman from.  Setting ``local_recipient_maps`` as well as ``transport_maps``
allows Postfix to properly reject all messages destined for non-existent local
users.  Setting `relay_domains`_ means Postfix will start to accept mail for
newly added domains even if they are not part of `mydestination`_.

Note that if you are not using virtual domains, then `relay_domains`_ isn't
strictly needed (but it is harmless).  All you need to do in this scenario is
to make sure that Postfix accepts mail for your one domain, normally by
including it in ``mydestination``.


Postfix documentation
---------------------

For more information regarding how to configure Postfix, please see
the Postfix documentation at:

.. _`The official Postfix documentation`:
   http://www.postfix.org/documentation.html
.. _`The reference page for all Postfix configuration parameters`:
   http://www.postfix.org/postconf.5.html
.. _`relay_domains`: http://www.postfix.org/postconf.5.html#relay_domains
.. _`mydestination`: http://www.postfix.org/postconf.5.html#mydestination


Exim
====

Contributions are welcome!


Sendmail
========

Contributions are welcome!


.. _`mailing list or on IRC`: START.html#contact-us
.. _`Local Mail Transfer Protocol`:
   http://en.wikipedia.org/wiki/Local_Mail_Transfer_Protocol
.. _LMTP: http://www.faqs.org/rfcs/rfc2033.html
.. _`Simple Mail Transfer Protocol`:
   http://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol
.. _SMTP: http://www.faqs.org/rfcs/rfc5321.html
.. _Postfix: http://www.postfix.org
.. _`Variable Envelope Return Path`:
   http://en.wikipedia.org/wiki/Variable_envelope_return_path
.. _postconf: http://www.postfix.org/postconf.1.html
