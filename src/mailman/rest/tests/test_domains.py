# Copyright (C) 2011-2015 by the Free Software Foundation, Inc.
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

"""REST domain tests."""

__all__ = [
    'TestDomains',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.listmanager import IListManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer
from urllib.error import HTTPError
from zope.component import getUtility



class TestDomains(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')

    def test_bogus_endpoint_extension(self):
        # /domains/<domain>/lists/<anything> is not a valid endpoint.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/domains/example.com'
                     '/lists/wrong')
        self.assertEqual(cm.exception.code, 400)

    def test_bogus_endpoint(self):
        # /domains/<domain>/<!lists> does not exist.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/domains/example.com/wrong')
        self.assertEqual(cm.exception.code, 404)

    def test_lists_are_deleted_when_domain_is_deleted(self):
        # /domains/<domain> DELETE removes all associated mailing lists.
        with transaction():
            create_list('ant@example.com')
        content, response = call_api(
            'http://localhost:9001/3.0/domains/example.com', method='DELETE')
        self.assertEqual(response.status, 204)
        self.assertIsNone(getUtility(IListManager).get('ant@example.com'))

    def test_missing_domain(self):
        # You get a 404 if you try to access a nonexisting domain.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/domains/does-not-exist.com')
        self.assertEqual(cm.exception.code, 404)

    def test_missing_domain_lists(self):
        # You get a 404 if you try to access the mailing lists of a
        # nonexisting domain.
        with self.assertRaises(HTTPError) as cm:
            call_api(
                'http://localhost:9001/3.0/domains/does-not-exist.com/lists')
        self.assertEqual(cm.exception.code, 404)

    def test_double_delete(self):
        # You cannot delete a domain twice.
        content, response = call_api(
            'http://localhost:9001/3.0/domains/example.com',
            method='DELETE')
        self.assertEqual(response.status, 204)
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/domains/example.com',
                     method='DELETE')
        self.assertEqual(cm.exception.code, 404)
