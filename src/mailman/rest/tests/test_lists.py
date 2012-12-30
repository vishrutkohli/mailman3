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

"""REST list tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestLists',
    'TestListsMissing',
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestListsMissing(unittest.TestCase):
    """Test expected failures."""

    layer = RESTLayer

    def test_missing_list_roster_member_404(self):
        # /lists/<missing>/roster/member gives 404
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/roster/member')
        self.assertEqual(cm.exception.code, 404)

    def test_missing_list_roster_owner_404(self):
        # /lists/<missing>/roster/owner gives 404
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/roster/owner')
        self.assertEqual(cm.exception.code, 404)

    def test_missing_list_roster_moderator_404(self):
        # /lists/<missing>/roster/member gives 404
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/roster/moderator')
        self.assertEqual(cm.exception.code, 404)

    def test_missing_list_configuration_404(self):
        # /lists/<missing>/config gives 404
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/lists/missing@example.com/config')
        self.assertEqual(cm.exception.code, 404)



class TestLists(unittest.TestCase):
    """Test various aspects of mailing list resources."""

    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')
        self._usermanager = getUtility(IUserManager)

    def test_member_count_with_no_members(self):
        # The list initially has 0 members.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com')
        self.assertEqual(response.status, 200)
        self.assertEqual(resource['member_count'], 0)

    def test_member_count_with_one_member(self):
        # Add a member to a list and check that the resource reflects this.
        with transaction():
            anne = self._usermanager.create_address('anne@example.com')
            self._mlist.subscribe(anne)
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com')
        self.assertEqual(response.status, 200)
        self.assertEqual(resource['member_count'], 1)

    def test_member_count_with_two_members(self):
        # Add two members to a list and check that the resource reflects this.
        with transaction():
            anne = self._usermanager.create_address('anne@example.com')
            self._mlist.subscribe(anne)
            bart = self._usermanager.create_address('bar@example.com')
            self._mlist.subscribe(bart)
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com')
        self.assertEqual(response.status, 200)
        self.assertEqual(resource['member_count'], 2)

    def test_query_for_lists_in_missing_domain(self):
        # You cannot ask all the mailing lists in a non-existent domain.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/domains/no.example.org/lists')
        self.assertEqual(cm.exception.code, 404)

    def test_cannot_create_list_in_missing_domain(self):
        # You cannot create a mailing list in a domain that does not exist.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists', {
                     'fqdn_listname': 'ant@no-domain.example.org',
                     })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason,
                         'Domain does not exist: no-domain.example.org')

    def test_cannot_create_duplicate_list(self):
        # You cannot create a list that already exists.
        call_api('http://localhost:9001/3.0/lists', {
                 'fqdn_listname': 'ant@example.com',
                 })
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists', {
                     'fqdn_listname': 'ant@example.com',
                     })
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(cm.exception.reason, 'Mailing list exists')

    def test_cannot_delete_missing_list(self):
        # You cannot delete a list that does not exist.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/bee.example.com',
                     method='DELETE')
        self.assertEqual(cm.exception.code, 404)

    def test_cannot_delete_already_deleted_list(self):
        # You cannot delete a list twice.
        call_api('http://localhost:9001/3.0/lists', {
                 'fqdn_listname': 'ant@example.com',
                 })
        call_api('http://localhost:9001/3.0/lists/ant.example.com',
                 method='DELETE')
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/lists/ant.example.com',
                     method='DELETE')
        self.assertEqual(cm.exception.code, 404)
