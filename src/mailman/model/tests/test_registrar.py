# Copyright (C) 2014 by the Free Software Foundation, Inc.
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

"""Test `IRegistrar`."""

__all__ = [
    'TestRegistrar',
    ]


import unittest

from functools import partial
from mailman.app.lifecycle import create_list
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.registrar import IRegistrar
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility



class TestRegistrar(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        mlist = create_list('test@example.com')
        self._register = partial(getUtility(IRegistrar).register, mlist)

    def test_invalid_empty_string(self):
        self.assertRaises(InvalidEmailAddressError, self._register, '')

    def test_invalid_space_in_name(self):
        self.assertRaises(InvalidEmailAddressError, self._register,
                          'some name@example.com')

    def test_invalid_funky_characters(self):
        self.assertRaises(InvalidEmailAddressError, self._register,
                          '<script>@example.com')

    def test_invalid_nonascii(self):
        self.assertRaises(InvalidEmailAddressError, self._register,
                          '\xa0@example.com')

    def test_invalid_no_at_sign(self):
        self.assertRaises(InvalidEmailAddressError, self._register,
                          'noatsign')

    def test_invalid_no_domain(self):
        self.assertRaises(InvalidEmailAddressError, self._register,
                          'nodom@ain')
