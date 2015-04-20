# Copyright (C) 2012-2015 by the Free Software Foundation, Inc.
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

"""Test the `confirm` command."""

__all__ = [
    'TestConfirm',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.commands.eml_confirm import Confirm
from mailman.email.message import Message
from mailman.interfaces.command import ContinueProcessing
from mailman.interfaces.registrar import IRegistrar
from mailman.interfaces.usermanager import IUserManager
from mailman.runners.command import Results
from mailman.testing.helpers import get_queue_messages
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility



class TestConfirm(unittest.TestCase):
    """Test the `confirm` command."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        anne = getUtility(IUserManager).create_address(
            'anne@example.com', 'Anne Person')
        self._token, token_owner, member = IRegistrar(self._mlist).register(
            anne)
        self._command = Confirm()
        # Clear the virgin queue.
        get_queue_messages('virgin')

    def test_welcome_message(self):
        # A confirmation causes a welcome message to be sent to the member, if
        # enabled by the mailing list.
        status = self._command.process(
            self._mlist, Message(), {}, (self._token,), Results())
        self.assertEqual(status, ContinueProcessing.yes)
        # There should be one messages in the queue; the welcome message.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        # Grab the welcome message.
        welcome = messages[0].msg
        self.assertEqual(welcome['subject'],
                         'Welcome to the "Test" mailing list')
        self.assertEqual(welcome['to'], 'Anne Person <anne@example.com>')

    def test_no_welcome_message(self):
        # When configured not to send a welcome message, none is sent.
        self._mlist.send_welcome_message = False
        status = self._command.process(
            self._mlist, Message(), {}, (self._token,), Results())
        self.assertEqual(status, ContinueProcessing.yes)
        # There will be no messages in the queue.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 0)
