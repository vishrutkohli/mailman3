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

"""REST membership tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestMembership',
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer
from mailman.utilities.datetime import now



class TestMembership(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')
        self._usermanager = getUtility(IUserManager)

    def test_try_to_join_missing_list(self):
        # A user tries to join a non-existent list.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members', {
                'list_id': 'missing.example.com',
                'subscriber': 'nobody@example.com',
                })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.msg, 'No such list')

    def test_try_to_leave_missing_list(self):
        # A user tries to leave a non-existent list.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/member/nobody@example.com',
                     method='DELETE')
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, '404 Not Found')

    def test_try_to_leave_list_with_bogus_address(self):
        # Try to leave a mailing list using an invalid membership address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members/1', method='DELETE')
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, '404 Not Found')

    def test_try_to_leave_a_list_twice(self):
        with transaction():
            anne = self._usermanager.create_address('anne@example.com')
            self._mlist.subscribe(anne)
        url = 'http://localhost:9001/3.0/members/1'
        content, response = call_api(url, method='DELETE')
        # For a successful DELETE, the response code is 204 and there is no
        # content.
        self.assertEqual(content, None)
        self.assertEqual(response.status, 204)
        with self.assertRaises(HTTPError) as cm:
            call_api(url, method='DELETE')
        self.assertEqual(cm.exception.code, 404)
        self.assertEqual(cm.exception.msg, '404 Not Found')

    def test_try_to_join_a_list_twice(self):
        with transaction():
            anne = self._usermanager.create_address('anne@example.com')
            self._mlist.subscribe(anne)
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members', {
                'list_id': 'test.example.com',
                'subscriber': 'anne@example.com',
                })
        self.assertEqual(cm.exception.code, 409)
        self.assertEqual(cm.exception.msg, 'Member already subscribed')

    def test_join_with_invalid_delivery_mode(self):
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members', {
                'list_id': 'test.example.com',
                'subscriber': 'anne@example.com',
                'display_name': 'Anne Person',
                'delivery_mode': 'invalid-mode',
                })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.msg,
                         'Cannot convert parameters: delivery_mode')

    def test_join_email_contains_slash(self):
        content, response = call_api('http://localhost:9001/3.0/members', {
            'list_id': 'test.example.com',
            'subscriber': 'hugh/person@example.com',
            'display_name': 'Hugh Person',
            })
        self.assertEqual(content, None)
        self.assertEqual(response.status, 201)
        self.assertEqual(response['location'],
                         'http://localhost:9001/3.0/members/1')
        # Reset any current transaction.
        config.db.abort()
        members = list(self._mlist.members.members)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].address.email, 'hugh/person@example.com')

    def test_join_as_user_with_preferred_address(self):
        with transaction():
            anne = self._usermanager.create_user('anne@example.com')
            preferred = list(anne.addresses)[0]
            preferred.verified_on = now()
            anne.preferred_address = preferred
            self._mlist.subscribe(anne)
        content, response = call_api('http://localhost:9001/3.0/members')
        self.assertEqual(response.status, 200)
        self.assertEqual(int(content['total_size']), 1)
        entry_0 = content['entries'][0]
        self.assertEqual(entry_0['self_link'],
                         'http://localhost:9001/3.0/members/1')
        self.assertEqual(entry_0['role'], 'member')
        self.assertEqual(entry_0['user'], 'http://localhost:9001/3.0/users/1')
        self.assertEqual(entry_0['address'], 'anne@example.com')
        self.assertEqual(entry_0['list_id'], 'test.example.com')

    def test_member_changes_preferred_address(self):
        with transaction():
            anne = self._usermanager.create_user('anne@example.com')
            preferred = list(anne.addresses)[0]
            preferred.verified_on = now()
            anne.preferred_address = preferred
            self._mlist.subscribe(anne)
        # Take a look at Anne's current membership.
        content, response = call_api('http://localhost:9001/3.0/members')
        self.assertEqual(int(content['total_size']), 1)
        entry_0 = content['entries'][0]
        self.assertEqual(entry_0['address'], 'anne@example.com')
        # Anne registers a new address and makes it her preferred address.
        # There are no changes to her membership.
        with transaction():
            new_preferred = anne.register('aperson@example.com')
            new_preferred.verified_on = now()
            anne.preferred_address = new_preferred
        # Take another look at Anne's current membership.
        content, response = call_api('http://localhost:9001/3.0/members')
        self.assertEqual(int(content['total_size']), 1)
        entry_0 = content['entries'][0]
        self.assertEqual(entry_0['address'], 'aperson@example.com')

    def test_get_nonexistent_member(self):
        # /members/<bogus> returns 404
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members/bogus')
        self.assertEqual(cm.exception.code, 404)

    def test_patch_nonexistent_member(self):
        # /members/<missing> PATCH returns 404
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members/801', method='PATCH')
        self.assertEqual(cm.exception.code, 404)

    def test_patch_member_bogus_attribute(self):
        # /members/<id> PATCH 'bogus' returns 400
        with transaction():
            anne = self._usermanager.create_address('anne@example.com')
            self._mlist.subscribe(anne)
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members/1', {
                     'powers': 'super',
                     }, method='PATCH')
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.msg, 'Unexpected parameters: powers')

    def test_member_all_without_preferences(self):
        # /members/<id>/all should return a 404 when it isn't trailed by
        # `preferences`
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/members/1/all')
        self.assertEqual(cm.exception.code, 404)
