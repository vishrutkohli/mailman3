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
    'TestLP1074374',
    'TestLogin',
    'TestUsers',
    ]


import os
import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.database.transaction import transaction
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api, configuration
from mailman.testing.layers import RESTLayer



class TestUsers(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')

    def test_get_missing_user_by_id(self):
        # You can't GET a missing user by user id.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/99')
        self.assertEqual(cm.exception.code, 404)

    def test_get_missing_user_by_address(self):
        # You can't GET a missing user by address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/missing@example.org')
        self.assertEqual(cm.exception.code, 404)

    def test_patch_missing_user_by_id(self):
        # You can't PATCH a missing user by user id.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/99', {
                     'display_name': 'Bob Dobbs',
                     }, method='PATCH')
        self.assertEqual(cm.exception.code, 404)

    def test_patch_missing_user_by_address(self):
        # You can't PATCH a missing user by user address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/bob@example.org', {
                     'display_name': 'Bob Dobbs',
                     }, method='PATCH')
        self.assertEqual(cm.exception.code, 404)

    def test_put_missing_user_by_id(self):
        # You can't PUT a missing user by user id.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/99', {
                     'display_name': 'Bob Dobbs',
                     'cleartext_password': 'abc123',
                     }, method='PUT')
        self.assertEqual(cm.exception.code, 404)

    def test_put_missing_user_by_address(self):
        # You can't PUT a missing user by user address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/bob@example.org', {
                     'display_name': 'Bob Dobbs',
                     'cleartext_password': 'abc123',
                     }, method='PUT')
        self.assertEqual(cm.exception.code, 404)

    def test_delete_missing_user_by_id(self):
        # You can't DELETE a missing user by user id.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/99', method='DELETE')
        self.assertEqual(cm.exception.code, 404)

    def test_delete_missing_user_by_address(self):
        # You can't DELETE a missing user by user address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/bob@example.com',
                     method='DELETE')
        self.assertEqual(cm.exception.code, 404)

    def test_existing_user_error(self):
        # Creating a user twice results in an error.
        call_api('http://localhost:9001/3.0/users', {
                 'email': 'anne@example.com',
                 })
        # The second try returns an error.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users', {
                     'email': 'anne@example.com',
                     })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason,
                         'Address already exists: anne@example.com')

    def test_addresses_of_missing_user_id(self):
        # Trying to get the /addresses of a missing user id results in error.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/801/addresses')
        self.assertEqual(cm.exception.code, 404)

    def test_addresses_of_missing_user_address(self):
        # Trying to get the /addresses of a missing user id results in error.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/z@example.net/addresses')
        self.assertEqual(cm.exception.code, 404)

    def test_login_missing_user_by_id(self):
        # Verify a password for a non-existing user, by id.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/99/login', {
                     'cleartext_password': 'wrong',
                     })
        self.assertEqual(cm.exception.code, 404)

    def test_login_missing_user_by_address(self):
        # Verify a password for a non-existing user, by address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/z@example.org/login', {
                     'cleartext_password': 'wrong',
                     })
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



class TestLogin(unittest.TestCase):
    """Test user 'login' (really just password verification)."""

    layer = RESTLayer

    def setUp(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            self.anne = user_manager.create_user(
                'anne@example.com', 'Anne Person')
            self.anne.password = config.password_context.encrypt('abc123')

    def test_wrong_parameter(self):
        # A bad request because it is mistyped the required attribute.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/1/login', {
                     'hashed_password': 'bad hash',
                     })
        self.assertEqual(cm.exception.code, 400)

    def test_not_enough_parameters(self):
        # A bad request because it is missing the required attribute.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/1/login', {
                     })
        self.assertEqual(cm.exception.code, 400)

    def test_too_many_parameters(self):
        # A bad request because it has too many attributes.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/users/1/login', {
                     'cleartext_password': 'abc123',
                     'display_name': 'Annie Personhood',
                     })
        self.assertEqual(cm.exception.code, 400)

    def test_successful_login_updates_password(self):
        # Passlib supports updating the hash when the hash algorithm changes.
        # When a user logs in successfully, the password will be updated if
        # necessary.
        #
        # Start by hashing Anne's password with a different hashing algorithm
        # than the one that the REST runner uses by default during testing.
        config_file = os.path.join(config.VAR_DIR, 'passlib-tmp.config')
        with open(config_file, 'w') as fp:
            print("""\
[passlib]
schemes = hex_md5
""", file=fp)
        with configuration('passwords', configuration=config_file):
            with transaction():
                self.anne.password = config.password_context.encrypt('abc123')
                # Just ensure Anne's password is hashed correctly.
                self.assertEqual(self.anne.password,
                                 'e99a18c428cb38d5f260853678922e03')
        # Now, Anne logs in with a successful password.  This should change it
        # back to the plaintext hash.
        call_api('http://localhost:9001/3.0/users/1/login', {
                 'cleartext_password': 'abc123',
                 })
        self.assertEqual(self.anne.password, '{plaintext}abc123')
