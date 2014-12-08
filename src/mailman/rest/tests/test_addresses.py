# Copyright (C) 2011-2014 by the Free Software Foundation, Inc.
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

"""REST address tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestAddresses',
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer
from mailman.utilities.datetime import now



class TestAddresses(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')

    def test_no_addresses(self):
        # At first, there are no addresses.
        url = 'http://localhost:9001/3.0/addresses'
        json, response = call_api(url)
        self.assertEqual(json['start'], 0)
        self.assertEqual(json['total_size'], 0)

    def test_membership_of_missing_address(self):
        # Try to get the memberships of a missing address.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/addresses/'
                     'nobody@example.com/memberships')
        self.assertEqual(cm.exception.code, 404)

    def test_verify_a_missing_address(self):
        # POSTing to the 'verify' sub-resource returns a 404.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/addresses/'
                     'nobody@example.com/verify', {})
        self.assertEqual(cm.exception.code, 404)

    def test_unverify_a_missing_address(self):
        # POSTing to the 'unverify' sub-resource returns a 404.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/addresses/'
                     'nobody@example.com/unverify', {})
        self.assertEqual(cm.exception.code, 404)

    def test_verify_already_verified(self):
        # It's okay to verify an already verified; it just doesn't change the
        # value.
        verified_on = now()
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
            anne.verified_on = verified_on
        response, content = call_api(
            'http://localhost:9001/3.0/addresses/anne@example.com/verify', {})
        self.assertEqual(content['status'], '204')
        self.assertEqual(anne.verified_on, verified_on)

    def test_unverify_already_unverified(self):
        # It's okay to unverify an already unverified; it just doesn't change
        # the value.
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
            self.assertEqual(anne.verified_on, None)
        response, content = call_api(
           'http://localhost:9001/3.0/addresses/anne@example.com/unverify', {})
        self.assertEqual(content['status'], '204')
        self.assertEqual(anne.verified_on, None)

    def test_verify_bad_request(self):
        # Too many segments after /verify.
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
            self.assertEqual(anne.verified_on, None)
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/addresses/'
                     'anne@example.com/verify/foo', {})
        self.assertEqual(cm.exception.code, 400)

    def test_unverify_bad_request(self):
        # Too many segments after /verify.
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
            self.assertEqual(anne.verified_on, None)
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/addresses/'
                     'anne@example.com/unverify/foo', {})
        self.assertEqual(cm.exception.code, 400)

    def test_address_added_to_user(self):
        # An address is added to a user record.
        user_manager = getUtility(IUserManager)
        with transaction():
            anne = user_manager.create_user('anne@example.com')
        response, content = call_api(
            'http://localhost:9001/3.0/users/anne@example.com/addresses', {
                'email': 'anne.person@example.org',
                })
        self.assertIn('anne.person@example.org',
                      [addr.email for addr in anne.addresses])
        self.assertEqual(content['status'], '201')
        self.assertEqual(
            content['location'],
            'http://localhost:9001/3.0/addresses/anne.person@example.org')
        # The address has no display name.
        anne_person = user_manager.get_address('anne.person@example.org')
        self.assertEqual(anne_person.display_name, '')

    def test_address_and_display_name_added_to_user(self):
        # Address with a display name is added to the user record.
        user_manager = getUtility(IUserManager)
        with transaction():
            anne = user_manager.create_user('anne@example.com')
        response, content = call_api(
            'http://localhost:9001/3.0/users/anne@example.com/addresses', {
                'email': 'anne.person@example.org',
                'display_name': 'Ann E Person',
                })
        self.assertIn('anne.person@example.org',
                      [addr.email for addr in anne.addresses])
        self.assertEqual(content['status'], '201')
        self.assertEqual(
            content['location'],
            'http://localhost:9001/3.0/addresses/anne.person@example.org')
        # The address has no display name.
        anne_person = user_manager.get_address('anne.person@example.org')
        self.assertEqual(anne_person.display_name, 'Ann E Person')

    def test_existing_address_bad_request(self):
        # Trying to add an existing address returns 400.
        with transaction():
            getUtility(IUserManager).create_user('anne@example.com')
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/users/anne@example.com/addresses', {
                     'email': 'anne@example.com',
                     })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Address already exists')

    def test_invalid_address_bad_request(self):
        # Trying to add an invalid address string returns 400.
        with transaction():
            getUtility(IUserManager).create_user('anne@example.com')
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/users/anne@example.com/addresses', {
                     'email': 'invalid_address_string'
                     })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Invalid email address')

    def test_empty_address_bad_request(self):
        # The address is required.
        with transaction():
            getUtility(IUserManager).create_user('anne@example.com')
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/users/anne@example.com/addresses',
                {})
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Missing parameters: email')

    def test_get_addresses_of_missing_user(self):
        # There is no user associated with the given address.
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/users/anne@example.com/addresses')
        self.assertEqual(cm.exception.code, 404)

    def test_add_address_to_missing_user(self):
        # The user that the address is being added to must exist.
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/users/anne@example.com/addresses', {
                    'email': 'anne.person@example.org',
                    })
        self.assertEqual(cm.exception.code, 404)

    def test_address_with_user(self):
        with transaction():
            anne = getUtility(IUserManager).create_user('anne@example.com')
        json, headers = call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com')
        self.assertEqual(headers['status'], '200')
        self.assertIn("user", json)
        self.assertEqual(json["user"], "http://localhost:9001/3.0/users/1")

    def test_address_without_user(self):
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
        json, headers = call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com')
        self.assertEqual(headers['status'], '200')
        self.assertNotIn("user", json)

    def test_user_subresource_on_unlinked_address(self):
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com/user')
        self.assertEqual(cm.exception.code, 404)

    def test_user_subresource(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            anne = user_manager.create_user('anne@example.com', 'Anne')
        json, headers = call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com/user')
        self.assertEqual(headers['status'], '200')
        self.assertEqual(json["user_id"], 1)
        self.assertEqual(json["display_name"], "Anne")
        self.assertEqual(json["self_link"], "http://localhost:9001/3.0/users/1")

    def test_user_subresource_post(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            anne = user_manager.create_user('anne.person@example.org', 'Anne')
            anne_addr = user_manager.create_address('anne@example.com')
        response, headers = call_api(
            'http://localhost:9001/3.0/addresses/anne@example.com/user', {
                'user_id': anne.user_id.int,
                })
        self.assertEqual(headers['status'], '200')
        self.assertEqual(anne_addr.user, anne)
        self.assertEqual(sorted([a.email for a in anne.addresses]),
                         ['anne.person@example.org', 'anne@example.com'])

    def test_user_subresource_post_new_user(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            anne_addr = user_manager.create_address('anne@example.com')
        response, headers = call_api(
            'http://localhost:9001/3.0/addresses/anne@example.com/user', {
                'display_name': 'Anne',
                })
        self.assertEqual(headers['status'], '201')
        anne = user_manager.get_user('anne@example.com')
        self.assertTrue(anne is not None)
        self.assertEqual(anne.display_name, 'Anne')
        self.assertEqual([a.email for a in anne.addresses],
                         ['anne@example.com'])
        self.assertEqual(anne_addr.user, anne)
        self.assertEqual(headers['location'],
                         'http://localhost:9001/3.0/users/1')

    def test_user_subresource_post_conflict(self):
        with transaction():
            anne = getUtility(IUserManager).create_user('anne@example.com')
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com/user', {
                    'email': 'anne.person@example.org',
                })
        self.assertEqual(cm.exception.code, 409)

    def test_user_subresource_post_new_user_no_autocreate(self):
        with transaction():
            anne = getUtility(IUserManager).create_address('anne@example.com')
        with self.assertRaises(HTTPError) as cm:
            json, headers = call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com/user', {
                    'display_name': 'Anne',
                    'autocreate': 0,
                })
            print("test_user_subresource_post_new_user_no_autocreate", headers, json)
        self.assertEqual(cm.exception.code, 404)

    def test_user_subresource_unlink(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            anne = user_manager.create_user('anne@example.com')
        response, headers = call_api(
                'http://localhost:9001/3.0/addresses/anne@example.com/user',
                method="DELETE")
        self.assertEqual(headers["status"], '204')
        anne_addr = user_manager.get_address('anne@example.com')
        self.assertTrue(anne_addr.user is None, "The address is still linked")
        self.assertTrue(user_manager.get_user('anne@example.com') is None)

    def test_user_subresource_put(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            anne_1 = user_manager.create_user('anne@example.com', 'Anne 1')
            anne_2 = user_manager.create_user(display_name='Anne 2')
        response, headers = call_api(
            'http://localhost:9001/3.0/addresses/anne@example.com/user', {
                'user_id': anne_2.user_id.int,
                }, method="PUT")
        self.assertEqual(headers['status'], '200')
        self.assertEqual(anne_1.addresses, [])
        self.assertEqual([a.email for a in anne_2.addresses],
                         ['anne@example.com'])
        self.assertEqual(anne_2,
            user_manager.get_address('anne@example.com').user)

    def test_user_subresource_put_create(self):
        user_manager = getUtility(IUserManager)
        with transaction():
            anne = user_manager.create_user('anne@example.com', 'Anne')
        response, headers = call_api(
            'http://localhost:9001/3.0/addresses/anne@example.com/user', {
                'email': 'anne.person@example.org',
                }, method="PUT")
        self.assertEqual(headers['status'], '201')
        self.assertEqual(anne.addresses, [])
        anne_person = user_manager.get_user('anne.person@example.org')
        self.assertTrue(anne_person is not None)
        self.assertEqual(sorted([a.email for a in anne_person.addresses]),
                         ["anne.person@example.org", "anne@example.com"])
        anne_addr = user_manager.get_address('anne@example.com')
        self.assertTrue(anne_addr is not None)
        self.assertEqual(anne_addr.user, anne_person)
