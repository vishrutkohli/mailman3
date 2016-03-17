# Copyright (C) 2012-2016 by the Free Software Foundation, Inc.
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

"""Test email address validation."""

__all__ = [
    'TestValidator',
    ]


import unittest

from mailman.email.validate import Validator



class TestValidator(unittest.TestCase):
    """Test email address validation."""
	
    def setUp(self):
        self._validator = Validator()
        
    def test_email_valid(self):
        email = 'test@gmail.com'
        self.assertEqual(self._validator.is_valid(email), True)
        
    def test_email_contians_badchars(self):
        email = 'test[0]@gmail.com'
        self.assertEqual(self._validator.is_valid(email), False)

    def test_email_contians_no_domain(self):
        email = 'nodomain'
        self.assertEqual(self._validator.is_valid(email), False)
