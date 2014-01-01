# Copyright (C) 2010-2014 by the Free Software Foundation, Inc.
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

"""Tests for config.pck imports."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestArchiveImport',
    'TestBasicImport',
    ]


import cPickle
import unittest

from mailman.app.lifecycle import create_list, remove_list
from mailman.interfaces.archiver import ArchivePolicy
from mailman.testing.layers import ConfigLayer
from mailman.utilities.importer import import_config_pck
from pkg_resources import resource_filename



class TestBasicImport(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        pickle_file = resource_filename('mailman.testing', 'config.pck')
        with open(pickle_file) as fp:
            self._pckdict = cPickle.load(fp)

    def tearDown(self):
        remove_list(self._mlist)

    def _import(self):
        import_config_pck(self._mlist, self._pckdict)

    def test_display_name(self):
        # The mlist.display_name gets set from the old list's real_name.
        self.assertEqual(self._mlist.display_name, 'Blank')
        self._import()
        self.assertEqual(self._mlist.display_name, 'Test')

    def test_mail_host(self):
        # The mlist.mail_host gets set.
        self.assertEqual(self._mlist.mail_host, 'example.com')
        self._import()
        self.assertEqual(self._mlist.mail_host, 'heresy.example.org')

    def test_rfc2369_headers(self):
        self._mlist.allow_list_posts = False
        self._mlist.include_rfc2369_headers = False
        self._import()
        self.assertTrue(self._mlist.allow_list_posts)
        self.assertTrue(self._mlist.include_rfc2369_headers)



class TestArchiveImport(unittest.TestCase):
    """Test conversion of the archive policies.

    Mailman 2.1 had two variables `archive` and `archive_private`.  Now
    there's just a single `archive_policy` enum.
    """
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._mlist.archive_policy = 'INITIAL-TEST-VALUE'

    def _do_test(self, pckdict, expected):
        import_config_pck(self._mlist, pckdict)
        self.assertEqual(self._mlist.archive_policy, expected)

    def test_public(self):
        self._do_test(dict(archive=True, archive_private=False),
                      ArchivePolicy.public)

    def test_private(self):
        self._do_test(dict(archive=True, archive_private=True),
                      ArchivePolicy.private)

    def test_no_archive(self):
        self._do_test(dict(archive=False, archive_private=False),
                      ArchivePolicy.never)

    def test_bad_state(self):
        # For some reason, the old list has the invalid archiving state where
        # `archive` is False and `archive_private` is True.  It doesn't matter
        # because this still collapses to the same enum value.
        self._do_test(dict(archive=False, archive_private=True),
                      ArchivePolicy.never)

    def test_missing_archive_key(self):
        # For some reason, the old list didn't have an `archive` key.  We
        # treat this as if no archiving is done.
        self._do_test(dict(archive_private=False), ArchivePolicy.never)

    def test_missing_archive_key_archive_public(self):
        # For some reason, the old list didn't have an `archive` key, and it
        # has weird value for archive_private.  We treat this as if no
        # archiving is done.
        self._do_test(dict(archive_private=True), ArchivePolicy.never)

    def test_missing_archive_private_key(self):
        # For some reason, the old list was missing an `archive_private` key.
        # For maximum safety, we treat this as private archiving.
        self._do_test(dict(archive=True), ArchivePolicy.private)
