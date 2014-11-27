# Copyright (C) 2012-2014 by the Free Software Foundation, Inc.
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

import os
import unittest
from email.mime.text import MIMEText

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.email.message import Message
from mailman.runners.digest import DigestRunner
from mailman.testing.helpers import (
    digest_mbox, make_testable_runner, reset_the_world,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestDigest(unittest.TestCase):
    """Test the digest runner."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.digest_size_threshold = 1
        #self._mlist.volume = 1
        #self._mlist.next_digest_number = 1
        self._digestq = config.switchboards['digest']
        self._shuntq = config.switchboards['shunt']
        self._virginq = config.switchboards['virgin']
        self._runner = make_testable_runner(DigestRunner, 'digest')
        self._process = config.handlers['to-digest'].process

    def tearDown(self):
        reset_the_world()

    def test_simple_message(self):
        msg = mfs("""\
From: anne@example.org
To: test@example.com

message triggering a digest
""")
        mbox = digest_mbox(self._mlist)
        mbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        self._process(self._mlist, msg, {})
        self._digestq.enqueue(msg,
            listname=self._mlist.fqdn_listname,
            digest_path=mbox_path,
            volume=1, digest_number=1)
        self._runner.run()

    def test_non_ascii_message(self):
        msg = Message()
        msg["From"] = "anne@example.org"
        msg["To"] = "test@example.com"
        msg["Content-Type"] = "multipart/mixed"
        msg.attach(MIMEText("message with non-ascii chars: \xc3\xa9",
                            "plain", "utf-8"))
        mbox = digest_mbox(self._mlist)
        mbox_path = os.path.join(self._mlist.data_path, 'digest.mmdf')
        mbox.add(msg.as_string())
        self._digestq.enqueue(msg,
            listname=self._mlist.fqdn_listname,
            digest_path=mbox_path,
            volume=1, digest_number=1)
        self._runner.run()
        errorlog = open(os.path.join(config.LOG_DIR, "error")).read()
        # The runner will send the file to the shunt queue on exception
        self.assertEqual(len(self._shuntq.files), 0, errorlog)
        # 2 messages in the virgin queue: the digest as plain-text and as multipart
        self.assertEqual(len(self._virginq.files), 2, errorlog)
