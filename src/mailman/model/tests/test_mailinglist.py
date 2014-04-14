# Copyright (C) 2013-2014 by the Free Software Foundation, Inc.
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

"""Test MailingLists and related model objects.."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestListArchiver',
    'TestDisabledListArchiver',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.mailinglist import IListArchiverSet
from mailman.testing.helpers import configuration
from mailman.testing.layers import ConfigLayer



class TestListArchiver(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')
        self._set = IListArchiverSet(self._mlist)

    def test_list_archivers(self):
        # Find the set of archivers registered for this mailing list.
        self.assertEqual(
            ['mail-archive', 'mhonarc', 'prototype'],
            sorted(archiver.name for archiver in self._set.archivers))

    def test_get_archiver(self):
        # Use .get() to see if a mailing list has an archiver.
        archiver = self._set.get('prototype')
        self.assertEqual(archiver.name, 'prototype')
        self.assertTrue(archiver.is_enabled)
        self.assertEqual(archiver.mailing_list, self._mlist)
        self.assertEqual(archiver.system_archiver.name, 'prototype')

    def test_get_archiver_no_such(self):
        # Using .get() on a non-existing name returns None.
        self.assertIsNone(self._set.get('no-such-archiver'))

    def test_site_disabled(self):
        # Here the system configuration enables all the archivers in time for
        # the archive set to be created with all list archivers enabled.  But
        # then the site-wide archiver gets disabled, so the list specific
        # archiver will also be disabled.
        archiver_set = IListArchiverSet(self._mlist)
        archiver = archiver_set.get('prototype')
        self.assertTrue(archiver.is_enabled)
        # Disable the site-wide archiver.
        config.push('enable prototype', """\
        [archiver.prototype]
        enable: no
        """)
        self.assertFalse(archiver.is_enabled)
        config.pop('enable prototype')



class TestDisabledListArchiver(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')

    @configuration('archiver.prototype', enable='no')
    def test_enable_list_archiver(self):
        # When the system configuration file disables an archiver site-wide,
        # the list-specific mailing list will get initialized as not enabled.
        # Create the archiver set on the fly so that it doesn't get
        # initialized with a configuration that enables the prototype archiver.
        archiver_set = IListArchiverSet(self._mlist)
        archiver = archiver_set.get('prototype')
        self.assertFalse(archiver.is_enabled)
        # Enable both the list archiver and the system archiver.
        archiver.is_enabled = True
        config.push('enable prototype', """\
        [archiver.prototype]
        enable: yes
        """)
        # Get the IListArchiver again.
        archiver = archiver_set.get('prototype')
        self.assertTrue(archiver.is_enabled)
        config.pop('enable prototype')
