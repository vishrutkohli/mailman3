# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Test schema migrations."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestMigration20120407',
    ]


import os
import shutil
import sqlite3
import tempfile
import unittest

from pkg_resources import resource_filename
from zope.component import getUtility

from mailman.config import config
from mailman.interfaces.domain import IDomainManager
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mailinglist import IAcceptableAliasSet
from mailman.testing.helpers import configuration
from mailman.testing.layers import ConfigLayer
from mailman.utilities.modules import call_name



class TestMigration20120407(unittest.TestCase):
    """Test the dated migration (LP: #971013)

    Circa: 3.0b1 -> 3.0b2

    table mailinglist:
    * news_moderation -> newsgroup_moderation
    * news_prefix_subject_too -> nntp_prefix_subject_too
    * ADD archive_policy
    * REMOVE archive
    * REMOVE archive_private
    * REMOVE archive_volume_frequency
    * REMOVE nntp_host
    """

    layer = ConfigLayer

    def setUp(self):
        self._tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tempdir)

    def test_sqlite_base(self):
        # Test that before the migration, the old table columns are present
        # and the new database columns are not.
        url = 'sqlite:///' + os.path.join(self._tempdir, 'mailman.db')
        database_class = config.database['class']
        database = call_name(database_class)
        with configuration('database', url=url):
            database.initialize()
        # Load all the database SQL to just before ours.
        database.load_migrations('20120406999999')
        # Verify that the database has not yet been migrated.
        for missing in ('archive_policy',
                        'nntp_prefix_subject_too'):
            self.assertRaises(sqlite3.OperationalError,
                              database.store.execute,
                              'select {0} from mailinglist;'.format(missing))
        for present in ('archive',
                        'archive_private',
                        'archive_volume_frequency',
                        'news_moderation',
                        'news_prefix_subject_too',
                        'nntp_host'):
            # This should not produce an exception.  Is there some better test
            # that we can perform?
            database.store.execute(
                'select {0} from mailinglist;'.format(present))

    def test_sqlite_migration(self):
        # Test that after the migration, the old table columns are missing
        # and the new database columns are present.
        url = 'sqlite:///' + os.path.join(self._tempdir, 'mailman.db')
        database_class = config.database['class']
        database = call_name(database_class)
        with configuration('database', url=url):
            database.initialize()
        # Load all the database SQL to just before ours.
        database.load_migrations('20120406999999')
        # Load all migrations, up to and including this one.
        database.load_migrations('20120407000000')
        # Verify that the database has been migrated.
        for present in ('archive_policy',
                        'nntp_prefix_subject_too'):
            # This should not produce an exception.  Is there some better test
            # that we can perform?
            database.store.execute(
                'select {0} from mailinglist;'.format(present))
        for missing in ('archive',
                        'archive_private',
                        'archive_volume_frequency',
                        'news_moderation',
                        'news_prefix_subject_too',
                        'nntp_host'):
            self.assertRaises(sqlite3.OperationalError,
                              database.store.execute,
                              'select {0} from mailinglist;'.format(missing))

    def test_data_after_migration(self):
        # Ensure that the existing data and foreign key references are
        # preserved across a migration.  Unfortunately, this requires sample
        # data, which kind of sucks.
        dst = os.path.join(self._tempdir, 'mailman.db')
        src = resource_filename('mailman.database.tests.data', 'mailman_01.db')
        shutil.copyfile(src, dst)
        url = 'sqlite:///' + dst
        database_class = config.database['class']
        database = call_name(database_class)
        with configuration('database', url=url):
            # Initialize the database and perform the migrations.
            database.initialize()
            database.load_migrations('20120407000000')
            # Check that the domains survived the migration.  This table was
            # not touched so it should be fine.
            domains = list(getUtility(IDomainManager))
            self.assertEqual(len(domains), 1)
            self.assertEqual(domains[0].mail_host, 'example.com')
            # There should be exactly one mailing list defined.
            mlists = list(getUtility(IListManager).mailing_lists)
            self.assertEqual(len(mlists), 1)
            # Get the mailing list object and check its acceptable aliases.
            # This tests that foreign keys continue to work.
            aliases_set = IAcceptableAliasSet(mlists)
            self.assertEqual(set(aliases_set.aliases),
                             set(['foo@example.com', 'bar@example.com']))
