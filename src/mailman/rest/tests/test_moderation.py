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

"""REST moderation tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from urllib2 import HTTPError

from mailman.app.lifecycle import create_list
from mailman.app.moderator import hold_message, hold_subscription
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.member import DeliveryMode
from mailman.testing.helpers import (
    call_api, specialized_message_from_string as mfs)
from mailman.testing.layers import RESTLayer



class TestModeration(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('ant@example.com')
        self._msg = mfs("""\
From: anne@example.com
To: ant@example.com
Subject: Something
Message-ID: <alpha>

Something else.
""")

    def test_not_found(self):
        # When a bogus mailing list is given, 404 should result.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/bee@example.com/held')
        self.assertEqual(cm.exception.code, 404)

    def test_bad_held_message_request_id(self):
        # Bad request when request_id is not an integer.
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/ant@example.com/held/bogus')
        self.assertEqual(cm.exception.code, 400)

    def test_missing_held_message_request_id(self):
        # Bad request when the request_id is not in the database.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant@example.com/held/99')
        self.assertEqual(cm.exception.code, 404)

    def test_subscription_request_as_held_message(self):
        # Provide the request id of a subscription request using the held
        # message API returns a not-found even though the request id is
        # in the database.
        held_id = hold_message(self._mlist, self._msg)
        subscribe_id = hold_subscription(
            self._mlist, 'bperson@example.net', 'Bart Person', 'xyz',
            DeliveryMode.regular, 'en')
        config.db.store.commit()
        url = 'http://localhost:9001/3.0/lists/ant@example.com/held/{0}'
        with self.assertRaises(HTTPError) as cm:
            call_api(url.format(subscribe_id))
        self.assertEqual(cm.exception.code, 404)
        # But using the held_id returns a valid response.
        response, content = call_api(url.format(held_id))
        self.assertEqual(response['message_id'], '<alpha>')

    def test_bad_held_message_action(self):
        # POSTing to a held message with a bad action.
        held_id = hold_message(self._mlist, self._msg)
        url = 'http://localhost:9001/3.0/lists/ant@example.com/held/{0}'
        with self.assertRaises(HTTPError) as cm:
            call_api(url.format(held_id), {'action': 'bogus'})
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.msg, 'Cannot convert parameters: action')

    def test_bad_subscription_request_id(self):
        # Bad request when request_id is not an integer.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant@example.com/'
                     'requests/bogus')
        self.assertEqual(cm.exception.code, 400)

    def test_missing_subscription_request_id(self):
        # Bad request when the request_id is not in the database.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant@example.com/'
                     'requests/99')
        self.assertEqual(cm.exception.code, 404)

    def test_bad_subscription_action(self):
        # POSTing to a held message with a bad action.
        held_id = hold_subscription(
            self._mlist, 'cperson@example.net', 'Cris Person', 'xyz',
            DeliveryMode.regular, 'en')
        config.db.store.commit()
        url = 'http://localhost:9001/3.0/lists/ant@example.com/requests/{0}'
        with self.assertRaises(HTTPError) as cm:
            call_api(url.format(held_id), {'action': 'bogus'})
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.msg, 'Cannot convert parameters: action')
