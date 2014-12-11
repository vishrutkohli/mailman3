# Copyright (C) 2014 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Test the digest runner."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestDigest',
    ]


import unittest

from StringIO import StringIO
from email.iterators import _structure as structure
from email.mime.text import MIMEText
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.email.message import Message
from mailman.runners.digest import DigestRunner
from mailman.testing.helpers import (
    LogFileMark, digest_mbox, get_queue_messages, make_digest_messages,
    make_testable_runner, message_from_string)
from mailman.testing.layers import ConfigLayer
from string import Template



class TestDigest(unittest.TestCase):
    """Test the digest runner."""

    layer = ConfigLayer
    maxDiff = None

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.digest_size_threshold = 1
        self._digestq = config.switchboards['digest']
        self._shuntq = config.switchboards['shunt']
        self._virginq = config.switchboards['virgin']
        self._runner = make_testable_runner(DigestRunner, 'digest')
        self._process = config.handlers['to-digest'].process

    def _check_virgin_queue(self):
        # There should be two messages in the virgin queue: the digest as
        # plain-text and as multipart.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            sorted(item.msg.get_content_type() for item in messages),
            ['multipart/mixed', 'text/plain'])
        for item in messages:
            self.assertEqual(item.msg['subject'],
                             'Test Digest, Vol 1, Issue 1')

    def test_simple_message(self):
        make_digest_messages(self._mlist)
        self._check_virgin_queue()

    def test_non_ascii_message(self):
        msg = Message()
        msg['From'] = 'anne@example.org'
        msg['To'] = 'test@example.com'
        msg['Content-Type'] = 'multipart/mixed'
        msg.attach(MIMEText('message with non-ascii chars: \xc3\xa9',
                            'plain', 'utf-8'))
        mbox = digest_mbox(self._mlist)
        mbox.add(msg.as_string())
        # Use any error logs as the error message if the test fails.
        error_log = LogFileMark('mailman.error')
        make_digest_messages(self._mlist, msg)
        # The runner will send the file to the shunt queue on exception.
        self.assertEqual(len(self._shuntq.files), 0, error_log.read())
        self._check_virgin_queue()

    def test_mime_digest_format(self):
        # Make sure that the format of the MIME digest is as expected.
        self._mlist.digest_size_threshold = 0.6
        self._mlist.volume = 1
        self._mlist.next_digest_number = 1
        self._mlist.send_welcome_message = False
        # Fill the digest.
        process = config.handlers['to-digest'].process
        size = 0
        for i in range(1, 5):
            text = Template("""\
From: aperson@example.com
To: xtest@example.com
Subject: Test message $i
List-Post: <test@example.com>

Here is message $i
""").substitute(i=i)
            msg = message_from_string(text)
            process(self._mlist, msg, {})
            size += len(text)
            if size >= self._mlist.digest_size_threshold * 1024:
                break
        # Run the digest runner to create the MIME and RFC 1153 digests.
        runner = make_testable_runner(DigestRunner)
        runner.run()
        items = get_queue_messages('virgin')
        self.assertEqual(len(items), 2)
        # Find the MIME one.
        mime_digest = None
        for item in items:
            if item.msg.is_multipart():
                assert mime_digest is None, 'We got two MIME digests'
                mime_digest = item.msg
        fp = StringIO()
        # Verify the structure is what we expect.
        structure(mime_digest, fp)
        self.assertMultiLineEqual(fp.getvalue(), """\
multipart/mixed
    text/plain
    text/plain
    message/rfc822
        text/plain
    message/rfc822
        text/plain
    message/rfc822
        text/plain
    message/rfc822
        text/plain
    text/plain
""")
