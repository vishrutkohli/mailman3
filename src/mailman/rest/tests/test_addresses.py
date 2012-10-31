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
