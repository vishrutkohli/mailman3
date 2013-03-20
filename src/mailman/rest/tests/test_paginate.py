# Copyright (C) 2011-2013 by the Free Software Foundation, Inc.
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

"""paginate helper tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestPaginateHelper',
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.database.transaction import transaction
from mailman.interfaces.listmanager import IListManager
from mailman.rest.helpers import paginate
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer


class FakeRequest:
    """Fake restish.http.Request object."""

    def __init__(self, count=None, page=None):
        self.GET = {}
        if count is not None:
            self.GET['count'] = count
        if page is not None:
            self.GET['page'] = page


class TestPaginateHelper(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        with transaction():
            self._mlist = create_list('test@example.com')

    def test_no_pagination(self):
        # No pagination params in request
        # Collection with 5 items.
        @paginate()
        def get_collection(self, request):
            return ['one', 'two', 'three', 'four', 'five']
        # Expect two items
        page = get_collection(None, FakeRequest())
        self.assertEqual(page, ['one', 'two', 'three', 'four', 'five'])

    def test_valid_pagination_request_page_one(self):
        # ?count=2&page=1 is a valid GET query string.
        # Collection with 5 items.
        @paginate()
        def get_collection(self, request):
            return ['one', 'two', 'three', 'four', 'five']
        # Expect two items
        page = get_collection(None, FakeRequest(2, 1))
        self.assertEqual(page, ['one', 'two'])

    def test_valid_pagination_request_page_two(self):
        # ?count=2&page=2 is a valid GET query string.
        # Collection with 5 items.
        @paginate()
        def get_collection(self, request):
            return ['one', 'two', 'three', 'four', 'five']
        # Expect two items
        page = get_collection(None, FakeRequest(2, 2))
        self.assertEqual(page, ['three', 'four'])

    def test_2nd_index_larger_than_total(self):
        # ?count=2&page=3 is a valid GET query string.
        # Collection with 5 items.
        @paginate()
        def get_collection(self, request):
            return ['one', 'two', 'three', 'four', 'five']
        # Expect two items
        page = get_collection(None, FakeRequest(2, 3))
        self.assertEqual(page, ['five'])

    def test_out_of_range_returns_empty_list(self):
        # ?count=2&page=3 is a valid GET query string.
        # Collection with 5 items.
        @paginate()
        def get_collection(self, request):
            return ['one', 'two', 'three', 'four', 'five']
        # Expect two items
        page = get_collection(None, FakeRequest(2, 4))
        self.assertEqual(page, [])

    def test_count_as_string_returns_bad_request(self):
        # ?count=two&page=2 are not valid values.
        @paginate()
        def get_collection(self, request):
            return []
        response = get_collection(None, FakeRequest('two', 1))
        self.assertEqual(response.status, '400 Bad Request')

    def test_no_get_attr_returns_bad_request(self):
        # ?count=two&page=2 are not valid values.
        @paginate()
        def get_collection(self, request):
            return []
        request = FakeRequest()
        del request.GET
        # Assert request obj has no GET attr.
        self.assertTrue(getattr(request, 'GET', None) is None)
        response = get_collection(None, request)
        self.assertEqual(response.status, '400 Bad Request')
