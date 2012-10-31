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

"""REST root object tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from urllib2 import HTTPError

from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestSystem(unittest.TestCase):
    layer = RESTLayer

    def test_system_url_too_long(self):
        # /system/foo/bar is not allowed.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/system/foo/bar')
        self.assertEqual(cm.exception.code, 400)

    def test_system_url_not_preferences(self):
        # /system/foo where `foo` is not `preferences`.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/system/foo')
        self.assertEqual(cm.exception.code, 400)

    def test_system_preferences_are_read_only(self):
        # /system/preferences are read-only.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/system/preferences', {
                     'acknowledge_posts': True,
                     }, method='PATCH')
        self.assertEqual(cm.exception.code, 405)
        # /system/preferences are read-only.
        with self.assertRaises(HTTPError) as cm:
            call_api('http://localhost:9001/3.0/system/preferences', {
                'acknowledge_posts': False,
                'delivery_mode': 'regular',
                'delivery_status': 'enabled',
                'hide_address': True,
                'preferred_language': 'en',
                'receive_list_copy': True,
                'receive_own_postings': True,
                }, method='PUT')
        self.assertEqual(cm.exception.code, 405)
