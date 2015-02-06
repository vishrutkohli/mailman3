# Copyright (C) 2015 by the Free Software Foundation, Inc.
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

"""Test the IUserManager implementation."""

__all__ = [
    'TestUserManager',
    ]


import unittest

from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility


class TestUserManager(unittest.TestCase):
    layer = ConfigLayer

    def test_create_user_with_existing_address(self):
        # LP: #1418280.  If a user is created when an email address is passed
        # in, and that address already exists, the user object should not get
        # created.
        manager = getUtility(IUserManager)
        # Create the address we're going to try to duplicate.
        manager.create_address('anne@example.com')
        # There are no users.
        self.assertEqual(len(list(manager.users)), 0)
        # Now create the user with an already existing address.
        with self.assertRaises(ExistingAddressError) as cm:
            manager.create_user('anne@example.com')
        self.assertEqual(cm.exception.address, 'anne@example.com')
        # There are still no users.
        self.assertEqual(len(list(manager.users)), 0)
