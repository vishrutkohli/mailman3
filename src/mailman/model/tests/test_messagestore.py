# Copyright (C) 2014-2015 by the Free Software Foundation, Inc.
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

"""Test the message store."""

__all__ = [
    'TestMessageStore',
    ]


import unittest

from mailman.interfaces.messages import IMessageStore
from mailman.testing.helpers import (
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer
from mailman.utilities.email import add_message_hash
from zope.component import getUtility



class TestMessageStore(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._store = getUtility(IMessageStore)

    def test_message_id_required(self):
        # The Message-ID header is required in order to add it to the store.
        message = mfs("""\
Subject: An important message

This message is very important.
""")
        self.assertRaises(ValueError, self._store.add, message)

    def test_get_message_by_hash(self):
        # Messages have an X-Message-ID-Hash header, the value of which can be
        # used to look the message up in the message store.
        message = mfs("""\
Subject: An important message
Message-ID: <ant>

This message is very important.
""")
        add_message_hash(message)
        self._store.add(message)
        self.assertEqual(message['x-message-id-hash'],
                         'V3YEHAFKE2WVJNK63Z7RFP4JMHISI2RG')
        found = self._store.get_message_by_hash(
            'V3YEHAFKE2WVJNK63Z7RFP4JMHISI2RG')
        self.assertEqual(found['message-id'], '<ant>')
        self.assertEqual(found['x-message-id-hash'],
                         'V3YEHAFKE2WVJNK63Z7RFP4JMHISI2RG')

    def test_cannot_delete_missing_message(self):
        self.assertRaises(LookupError, self._store.delete_message, 'missing')
