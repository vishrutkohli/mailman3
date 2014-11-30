# Copyright (C) 2012-2014 by the Free Software Foundation, Inc.
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

"""Test the cook_headers handler."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestCookHeaders',
    ]


import unittest
from email.mime.multipart import MIMEMultipart

from mailman.app.lifecycle import create_list
from mailman.handlers import cook_headers
from mailman.testing.layers import ConfigLayer



class TestCookHeaders(unittest.TestCase):
    """Test the cook_headers handler."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')

    def test_process_multipart(self):
        # The digest runner creates MIMEMultipart message instances which have
        # no sender property.
        msg = MIMEMultipart()
        msg["message-id"] = "<test>"
        try:
            cook_headers.process(self._mlist, msg, {})
        except AttributeError as e:
            self.fail(e)
