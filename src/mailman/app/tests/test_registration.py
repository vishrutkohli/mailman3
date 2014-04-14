# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Test email address registration."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestEmailValidation',
    'TestRegistration',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.pending import IPendings
from mailman.interfaces.registrar import ConfirmationNeededEvent, IRegistrar
from mailman.testing.helpers import event_subscribers
from mailman.testing.layers import ConfigLayer



class TestEmailValidation(unittest.TestCase):
    """Test basic email validation."""

    layer = ConfigLayer

    def setUp(self):
        self.registrar = getUtility(IRegistrar)
        self.mlist = create_list('alpha@example.com')

    def test_empty_string_is_invalid(self):
        self.assertRaises(InvalidEmailAddressError,
                          self.registrar.register, self.mlist,
                          '')

    def test_no_spaces_allowed(self):
        self.assertRaises(InvalidEmailAddressError,
                          self.registrar.register, self.mlist,
                          'some name@example.com')

    def test_no_angle_brackets(self):
        self.assertRaises(InvalidEmailAddressError,
                          self.registrar.register, self.mlist,
                          '<script>@example.com')

    def test_ascii_only(self):
        self.assertRaises(InvalidEmailAddressError,
                          self.registrar.register, self.mlist,
                          '\xa0@example.com')

    def test_domain_required(self):
        self.assertRaises(InvalidEmailAddressError,
                          self.registrar.register, self.mlist,
                          'noatsign')

    def test_full_domain_required(self):
        self.assertRaises(InvalidEmailAddressError,
                          self.registrar.register, self.mlist,
                          'nodom@ain')



class TestRegistration(unittest.TestCase):
    """Test registration."""

    layer = ConfigLayer

    def setUp(self):
        self.registrar = getUtility(IRegistrar)
        self.mlist = create_list('alpha@example.com')

    def test_confirmation_event_received(self):
        # Registering an email address generates an event.
        def capture_event(event):
            self.assertIsInstance(event, ConfirmationNeededEvent)
        with event_subscribers(capture_event):
            self.registrar.register(self.mlist, 'anne@example.com')

    def test_event_mlist(self):
        # The event has a reference to the mailing list being subscribed to.
        def capture_event(event):
            self.assertIs(event.mlist, self.mlist)
        with event_subscribers(capture_event):
            self.registrar.register(self.mlist, 'anne@example.com')

    def test_event_pendable(self):
        # The event has an IPendable which contains additional information.
        def capture_event(event):
            pendable = event.pendable
            self.assertEqual(pendable['type'], 'registration')
            self.assertEqual(pendable['email'], 'anne@example.com')
            # The key is present, but the value is None.
            self.assertIsNone(pendable['display_name'])
            # The default is regular delivery.
            self.assertEqual(pendable['delivery_mode'], 'regular')
            self.assertEqual(pendable['list_id'], 'alpha.example.com')
        with event_subscribers(capture_event):
            self.registrar.register(self.mlist, 'anne@example.com')

    def test_token(self):
        # Registering the email address returns a token, and this token links
        # back to the pendable.
        captured_events = []
        def capture_event(event):
            captured_events.append(event)
        with event_subscribers(capture_event):
            token = self.registrar.register(self.mlist, 'anne@example.com')
        self.assertEqual(len(captured_events), 1)
        event = captured_events[0]
        self.assertEqual(event.token, token)
        pending = getUtility(IPendings).confirm(token)
        self.assertEqual(pending, event.pendable)
