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

"""Test addresses."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestAddress',
    ]


import unittest

from mailman.email.validate import InvalidEmailAddressError
from mailman.model.address import Address
from mailman.testing.layers import ConfigLayer



class TestAddress(unittest.TestCase):
    """Test addresses."""

    layer = ConfigLayer

    def test_invalid_email_string_raises_exception(self):
        with self.assertRaises(InvalidEmailAddressError):
            Address('not_a_valid_email_string', '')
