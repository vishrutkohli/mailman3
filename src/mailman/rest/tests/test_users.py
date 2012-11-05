# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""REST user tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestUsers',
    'TestLP1074374',
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestUsers(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')

    def test_delete_bogus_user(self):
        # Try to delete a user that does not exist.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/99', method='DELETE')
        self.assertEqual(cm.exception.code, 404)



class TestLP1074374(unittest.TestCase):
    """LP: #1074374 - deleting a user left their address records active."""

    layer = RESTLayer

    def setUp(self):
        self.user_manager = getUtility(IUserManager)
        with transaction():
            self.mlist = create_list('test@example.com')
            self.anne = self.user_manager.create_user(
                'anne@example.com', 'Anne Person')

    def test_deleting_user_deletes_address(self):
        with transaction():
            user_id = self.anne.user_id
        call_api('http://localhost:9001/3.0/users/anne@example.com',
                 method='DELETE')
        # The user record is gone.
        self.assertIsNone(self.user_manager.get_user_by_id(user_id))
        self.assertIsNone(self.user_manager.get_user('anne@example.com'))
        # Anne's address is also gone.
        self.assertIsNone(self.user_manager.get_address('anne@example.com'))

    def test_deleting_user_deletes_addresses(self):
        # All of Anne's linked addresses are deleted when her user record is
        # deleted.  So, register and link another address to Anne.
        with transaction():
            self.anne.register('aperson@example.org')
        call_api('http://localhost:9001/3.0/users/anne@example.com',
                 method='DELETE')
        self.assertIsNone(self.user_manager.get_user('anne@example.com'))
        self.assertIsNone(self.user_manager.get_user('aperson@example.org'))

    def test_lp_1074374(self):
        # Specific steps to reproduce the bug:
        # - create a user through the REST API (well, we did that outside the
        #   REST API here, but that should be fine)
        # - delete that user through the API
        # - repeating step 1 gives a 500 status code
        # - /3.0/addresses still contains the original address
        # - /3.0/members gives a 500
        with transaction():
            user_id = self.anne.user_id
            address = list(self.anne.addresses)[0]
            self.mlist.subscribe(address)
        call_api('http://localhost:9001/3.0/users/anne@example.com',
                 method='DELETE')
        content, response = call_api('http://localhost:9001/3.0/addresses')
        # There are no addresses, and thus no entries in the returned JSON.
        self.assertNotIn('entries', content)
        self.assertEqual(content['total_size'], 0)
        # There are also no members.
        content, response = call_api('http://localhost:9001/3.0/members')
        self.assertNotIn('entries', content)
        self.assertEqual(content['total_size'], 0)
        # Now we can create a new user record for Anne, and subscribe her to
        # the mailing list, this time all through the API.
        call_api('http://localhost:9001/3.0/users', dict(
            email='anne@example.com',
            password='bbb'))
        call_api('http://localhost:9001/3.0/members', dict(
            list_id='test.example.com',
            subscriber='anne@example.com',
            role='member'))
        # This is not the Anne you're looking for.  (IOW, the new Anne is a
        # different user).
        content, response = call_api(
            'http://localhost:9001/3.0/users/anne@example.com')
        self.assertNotEqual(user_id, content['user_id'])
        # Anne has an address record.
        content, response = call_api('http://localhost:9001/3.0/addresses')
        self.assertEqual(content['total_size'], 1)
        self.assertEqual(content['entries'][0]['email'], 'anne@example.com')
        # Anne is also a member of the mailing list.
        content, response = call_api('http://localhost:9001/3.0/members')
        self.assertEqual(content['total_size'], 1)
        member = content['entries'][0]
        self.assertEqual(member['address'], 'anne@example.com')
        self.assertEqual(member['delivery_mode'], 'regular')
        self.assertEqual(member['list_id'], 'test.example.com')
        self.assertEqual(member['role'], 'member')
