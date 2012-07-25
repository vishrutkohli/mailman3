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
    'TestMigration20120407ArchiveData',
    'TestMigration20120407Data',
    'TestMigration20120407Schema',
    ]


import unittest

from pkg_resources import resource_string
from storm.exceptions import DatabaseError
from zope.component import getUtility

from mailman.config import config
from mailman.interfaces.domain import IDomainManager
from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mailinglist import IAcceptableAliasSet
from mailman.testing.helpers import temporary_db
from mailman.testing.layers import ConfigLayer
from mailman.utilities.modules import call_name



class TestMigration20120407Schema(unittest.TestCase):
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
        database_class_name = config.database['class']
        database_class = call_name(database_class_name)
        self._temporary = database_class._make_temporary()
        self._database = self._temporary.database

    def tearDown(self):
        self._temporary.cleanup()

    def test_pre_upgrade_columns_base(self):
        # Test that before the migration, the old table columns are present
        # and the new database columns are not.
        #
        # Load all the migrations to just before the one we're testing.
        self._database.load_migrations('20120406999999')
        # Verify that the database has not yet been migrated.
        for missing in ('archive_policy',
                        'nntp_prefix_subject_too'):
            self.assertRaises(DatabaseError,
                              self._database.store.execute,
                              'select {0} from mailinglist;'.format(missing))
            # Avoid PostgreSQL complaint: InternalError: current transaction
            # is aborted, commands ignored until end of transaction block.
            self._database.store.execute('ABORT;')
        for present in ('archive',
                        'archive_private',
                        'archive_volume_frequency',
                        'news_moderation',
                        'news_prefix_subject_too',
                        'nntp_host'):
            # This should not produce an exception.  Is there some better test
            # that we can perform?
            self._database.store.execute(
                'select {0} from mailinglist;'.format(present))

    def test_post_upgrade_columns_migration(self):
        # Test that after the migration, the old table columns are missing
        # and the new database columns are present.
        #
        # Load all the migrations up to and including the one we're testing.
        self._database.load_migrations('20120406999999')
        self._database.load_migrations('20120407000000')
        # Verify that the database has been migrated.
        for present in ('archive_policy',
                        'nntp_prefix_subject_too'):
            # This should not produce an exception.  Is there some better test
            # that we can perform?
            self._database.store.execute(
                'select {0} from mailinglist;'.format(present))
        for missing in ('archive',
                        'archive_private',
                        'archive_volume_frequency',
                        'news_moderation',
                        'news_prefix_subject_too',
                        'nntp_host'):
            self.assertRaises(DatabaseError,
                              self._database.store.execute,
                              'select {0} from mailinglist;'.format(missing))
            # Avoid PostgreSQL complaint: InternalError: current transaction
            # is aborted, commands ignored until end of transaction block.
            self._database.store.execute('ABORT;')



class TestMigration20120407Data(unittest.TestCase):
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
        database_class_name = config.database['class']
        database_class = call_name(database_class_name)
        self._temporary = database_class._make_temporary()
        self._database = self._temporary.database
        # Load all the migrations to just before the one we're testing.
        self._database.load_migrations('20120406999999')
        # Load the previous schema's sample data.
        sample_data = resource_string(
            'mailman.database.tests.data',
            'migration_{0}_1.sql'.format(database_class.TAG))
        self._database.load_sql(self._database.store, sample_data)
        # Update to the current migration we're testing.
        self._database.load_migrations('20120407000000')

    def tearDown(self):
        self._temporary.cleanup()

    def test_migration_domains(self):
        # Test that the domains table, which isn't touched, doesn't change.
        with temporary_db(self._database):
            # Check that the domains survived the migration.  This table
            # was not touched so it should be fine.
            domains = list(getUtility(IDomainManager))
            self.assertEqual(len(domains), 1)
            self.assertEqual(domains[0].mail_host, 'example.com')

    def test_migration_mailing_lists(self):
        # Test that the mailing lists survive migration.
        with temporary_db(self._database):
            # There should be exactly one mailing list defined.
            mlists = list(getUtility(IListManager).mailing_lists)
            self.assertEqual(len(mlists), 1)
            self.assertEqual(mlists[0].fqdn_listname, 'test@example.com')

    def test_migration_acceptable_aliases(self):
        # Test that the mailing list's acceptable aliases survive migration.
        # This proves that foreign key references are migrated properly.
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            aliases_set = IAcceptableAliasSet(mlist)
            self.assertEqual(set(aliases_set.aliases),
                             set(['foo@example.com', 'bar@example.com']))

    def test_migration_members(self):
        # Test that the members of a mailing list all survive migration.
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            # Test that all the members we expect are still there.  Start with
            # the two list delivery members.
            addresses = set(address.email
                            for address in mlist.members.addresses)
            self.assertEqual(addresses,
                             set(['anne@example.com', 'bart@example.com']))
            # There is one owner.
            owners = set(address.email for address in mlist.owners.addresses)
            self.assertEqual(len(owners), 1)
            self.assertEqual(owners.pop(), 'anne@example.com')
            # There is one moderator.
            moderators = set(address.email
                             for address in mlist.moderators.addresses)
            self.assertEqual(len(moderators), 1)
            self.assertEqual(moderators.pop(), 'bart@example.com')



class TestMigration20120407ArchiveData(unittest.TestCase):
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
        database_class_name = config.database['class']
        database_class = call_name(database_class_name)
        self._temporary = database_class._make_temporary()
        self._database = self._temporary.database
        # Load all the migrations to just before the one we're testing.
        self._database.load_migrations('20120406999999')
        # Load the previous schema's sample data.
        sample_data = resource_string(
            'mailman.database.tests.data',
            'migration_{0}_1.sql'.format(database_class.TAG))
        self._database.load_sql(self._database.store, sample_data)

    def _upgrade(self):
        # Update to the current migration we're testing.
        self._database.load_migrations('20120407000000')

    def tearDown(self):
        self._temporary.cleanup()

    def test_migration_archive_policy_never_0(self):
        # Test that the new archive_policy value is updated correctly.  In the
        # case of old column archive=0, the archive_private column is
        # ignored.  This test sets it to 0 to ensure it's ignored.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = False, archive_private = False '
            'WHERE id = 1;')
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.never)

    def test_migration_archive_policy_never_1(self):
        # Test that the new archive_policy value is updated correctly.  In the
        # case of old column archive=0, the archive_private column is
        # ignored.  This test sets it to 1 to ensure it's ignored.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = False, archive_private = True '
            'WHERE id = 1;')
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.never)

    def test_archive_policy_private(self):
        # Test that the new archive_policy value is updated correctly for
        # private archives.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = True, archive_private = True '
            'WHERE id = 1;')
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.private)

    def test_archive_policy_public(self):
        # Test that the new archive_policy value is updated correctly for
        # public archives.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = True, archive_private = False '
            'WHERE id = 1;')
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.public)
