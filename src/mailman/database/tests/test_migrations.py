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
    'TestMigration20120407MigratedData',
    'TestMigration20120407Schema',
    'TestMigration20120407UnchangedData',
    'TestMigration20121015MigratedData',
    'TestMigration20121015Schema',
    ]


import unittest

from operator import attrgetter
from pkg_resources import resource_string
from storm.exceptions import DatabaseError
from zope.component import getUtility

from mailman.interfaces.database import IDatabaseFactory
from mailman.interfaces.domain import IDomainManager
from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mailinglist import IAcceptableAliasSet
from mailman.interfaces.nntp import NewsgroupModeration
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.model.bans import Ban
from mailman.testing.helpers import temporary_db
from mailman.testing.layers import ConfigLayer



class MigrationTestBase(unittest.TestCase):
    """Test database migrations."""

    layer = ConfigLayer

    def setUp(self):
        self._database = getUtility(IDatabaseFactory, 'temporary').create()

    def tearDown(self):
        self._database._cleanup()

    def _missing_present(self, table, migrations, missing, present):
        """The appropriate migrations leave columns missing and present.

        :param table: The table to test columns from.
        :param migrations: Sequence of migrations to load.
        :param missing: Set of columns which should be missing after the
            migrations are loaded.
        :param present: Set of columns which should be present after the
            migrations are loaded.
        """
        for migration in migrations:
            self._database.load_migrations(migration)
            self._database.store.commit()
        for column in missing:
            self.assertRaises(DatabaseError,
                              self._database.store.execute,
                              'select {0} from {1};'.format(column, table))
            self._database.store.rollback()
        for column in present:
            # This should not produce an exception.  Is there some better test
            # that we can perform?
            self._database.store.execute(
                'select {0} from {1};'.format(column, table))



class TestMigration20120407Schema(MigrationTestBase):
    """Test column migrations."""

    def test_pre_upgrade_columns_migration(self):
        # Test that before the migration, the old table columns are present
        # and the new database columns are not.
        self._missing_present('mailinglist',
                              ['20120406999999'],
                              # New columns are missing.
                              ('allow_list_posts',
                               'archive_policy',
                               'list_id',
                               'nntp_prefix_subject_too'),
                              # Old columns are present.
                              ('archive',
                              'archive_private',
                              'archive_volume_frequency',
                              'generic_nonmember_action',
                              'include_list_post_header',
                              'news_moderation',
                              'news_prefix_subject_too',
                              'nntp_host'))
        self._missing_present('member',
                              ['20120406999999'],
                              ('list_id',),
                              ('mailing_list',))

    def test_post_upgrade_columns_migration(self):
        # Test that after the migration, the old table columns are missing
        # and the new database columns are present.
        self._missing_present('mailinglist',
                              ['20120406999999',
                               '20120407000000'],
                              # The old columns are missing.
                              ('archive',
                               'archive_private',
                               'archive_volume_frequency',
                               'generic_nonmember_action',
                               'include_list_post_header',
                               'news_moderation',
                               'news_prefix_subject_too',
                               'nntp_host'),
                              # The new columns are present.
                              ('allow_list_posts',
                              'archive_policy',
                              'list_id',
                              'nntp_prefix_subject_too'))
        self._missing_present('member',
                              ['20120406999999',
                               '20120407000000'],
                              ('mailing_list',),
                              ('list_id',))



class TestMigration20120407UnchangedData(MigrationTestBase):
    """Test non-migrated data."""

    def setUp(self):
        MigrationTestBase.setUp(self)
        # Load all the migrations to just before the one we're testing.
        self._database.load_migrations('20120406999999')
        # Load the previous schema's sample data.
        sample_data = resource_string(
            'mailman.database.tests.data',
            'migration_{0}_1.sql'.format(self._database.TAG))
        self._database.load_sql(self._database.store, sample_data)
        # XXX 2012-12-28: We have to load the last migration defined in the
        # system, otherwise the ORM model will not match the SQL table
        # definitions and we'll get OperationalErrors from SQLite.
        self._database.load_migrations('20121015000000')

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



class TestMigration20120407MigratedData(MigrationTestBase):
    """Test affected migration data."""

    def setUp(self):
        MigrationTestBase.setUp(self)
        # Load all the migrations to just before the one we're testing.
        self._database.load_migrations('20120406999999')
        # Load the previous schema's sample data.
        sample_data = resource_string(
            'mailman.database.tests.data',
            'migration_{0}_1.sql'.format(self._database.TAG))
        self._database.load_sql(self._database.store, sample_data)

    def _upgrade(self):
        # XXX 2012-12-28: We have to load the last migration defined in the
        # system, otherwise the ORM model will not match the SQL table
        # definitions and we'll get OperationalErrors from SQLite.
        self._database.load_migrations('20121015000000')

    def test_migration_archive_policy_never_0(self):
        # Test that the new archive_policy value is updated correctly.  In the
        # case of old column archive=0, the archive_private column is
        # ignored.  This test sets it to 0 to ensure it's ignored.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = {0}, archive_private = {0} '
            'WHERE id = 1;'.format(self._database.FALSE))
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
            'UPDATE mailinglist SET archive = {0}, archive_private = {1} '
            'WHERE id = 1;'.format(self._database.FALSE,
                                   self._database.TRUE))
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.never)

    def test_archive_policy_private(self):
        # Test that the new archive_policy value is updated correctly for
        # private archives.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = {0}, archive_private = {0} '
            'WHERE id = 1;'.format(self._database.TRUE))
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.private)

    def test_archive_policy_public(self):
        # Test that the new archive_policy value is updated correctly for
        # public archives.
        self._database.store.execute(
            'UPDATE mailinglist SET archive = {1}, archive_private = {0} '
            'WHERE id = 1;'.format(self._database.FALSE,
                                   self._database.TRUE))
        # Complete the migration
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.archive_policy, ArchivePolicy.public)

    def test_list_id(self):
        # Test that the mailinglist table gets a list_id column.
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.list_id, 'test.example.com')

    def test_list_id_member(self):
        # Test that the member table's mailing_list column becomes list_id.
        self._upgrade()
        with temporary_db(self._database):
            service = getUtility(ISubscriptionService)
            members = list(service.find_members(list_id='test.example.com'))
        self.assertEqual(len(members), 4)

    def test_news_moderation_none(self):
        # Test that news_moderation becomes newsgroup_moderation.
        self._database.store.execute(
            'UPDATE mailinglist SET news_moderation = 0 '
            'WHERE id = 1;')
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.newsgroup_moderation,
                             NewsgroupModeration.none)

    def test_news_moderation_open_moderated(self):
        # Test that news_moderation becomes newsgroup_moderation.
        self._database.store.execute(
            'UPDATE mailinglist SET news_moderation = 1 '
            'WHERE id = 1;')
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.newsgroup_moderation,
                             NewsgroupModeration.open_moderated)

    def test_news_moderation_moderated(self):
        # Test that news_moderation becomes newsgroup_moderation.
        self._database.store.execute(
            'UPDATE mailinglist SET news_moderation = 2 '
            'WHERE id = 1;')
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertEqual(mlist.newsgroup_moderation,
                             NewsgroupModeration.moderated)

    def test_nntp_prefix_subject_too_false(self):
        # Test that news_prefix_subject_too becomes nntp_prefix_subject_too.
        self._database.store.execute(
            'UPDATE mailinglist SET news_prefix_subject_too = {0} '
            'WHERE id = 1;'.format(self._database.FALSE))
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertFalse(mlist.nntp_prefix_subject_too)

    def test_nntp_prefix_subject_too_true(self):
        # Test that news_prefix_subject_too becomes nntp_prefix_subject_too.
        self._database.store.execute(
            'UPDATE mailinglist SET news_prefix_subject_too = {0} '
            'WHERE id = 1;'.format(self._database.TRUE))
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertTrue(mlist.nntp_prefix_subject_too)

    def test_allow_list_posts_false(self):
        # Test that include_list_post_header -> allow_list_posts.
        self._database.store.execute(
            'UPDATE mailinglist SET include_list_post_header = {0} '
            'WHERE id = 1;'.format(self._database.FALSE))
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertFalse(mlist.allow_list_posts)

    def test_allow_list_posts_true(self):
        # Test that include_list_post_header -> allow_list_posts.
        self._database.store.execute(
            'UPDATE mailinglist SET include_list_post_header = {0} '
            'WHERE id = 1;'.format(self._database.TRUE))
        self._upgrade()
        with temporary_db(self._database):
            mlist = getUtility(IListManager).get('test@example.com')
            self.assertTrue(mlist.allow_list_posts)



class TestMigration20121015Schema(MigrationTestBase):
    """Test column migrations."""

    def test_pre_upgrade_column_migrations(self):
        self._missing_present('ban',
                              ['20121014999999'],
                              ('list_id',),
                              ('mailing_list',))
        self._missing_present('mailinglist',
                              ['20121014999999'],
                              (),
                              ('new_member_options', 'send_reminders',
                               'subscribe_policy', 'unsubscribe_policy',
                               'subscribe_auto_approval', 'private_roster',
                               'admin_member_chunksize'),
                              )

    def test_post_upgrade_column_migrations(self):
        self._missing_present('ban',
                              ['20121014999999',
                               '20121015000000'],
                              ('mailing_list',),
                              ('list_id',))
        self._missing_present('mailinglist',
                              ['20121014999999',
                               '20121015000000'],
                              ('new_member_options', 'send_reminders',
                               'subscribe_policy', 'unsubscribe_policy',
                               'subscribe_auto_approval', 'private_roster',
                               'admin_member_chunksize'),
                              ())



class TestMigration20121015MigratedData(MigrationTestBase):
    """Test non-migrated data."""

    def test_migration_bans(self):
        # Load all the migrations to just before the one we're testing.
        self._database.load_migrations('20121014999999')
        # Insert a list-specific ban.
        self._database.store.execute("""
            INSERT INTO ban VALUES (
                1, 'anne@example.com', 'test@example.com');
            """)
        # Insert a global ban.
        self._database.store.execute("""
            INSERT INTO ban VALUES (
                2, 'bart@example.com', NULL);
            """)
        # Update to the current migration we're testing.
        self._database.load_migrations('20121015000000')
        # Now both the local and global bans should still be present.
        bans = sorted(self._database.store.find(Ban),
                      key=attrgetter('email'))
        self.assertEqual(bans[0].email, 'anne@example.com')
        self.assertEqual(bans[0].list_id, 'test.example.com')
        self.assertEqual(bans[1].email, 'bart@example.com')
        self.assertEqual(bans[1].list_id, None)
