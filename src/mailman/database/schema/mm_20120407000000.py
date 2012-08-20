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

"""3.0b1 -> 3.0b2 schema migrations.

All column changes are in the `mailinglist` table.

* Renames:
 - news_prefix_subject_too -> nntp_prefix_subject_too
 - news_moderation         -> newsgroup_moderation

* Collapsing:
 - archive, archive_private -> archive_policy

* Remove:
 - archive_volume_frequency
 - generic_nonmember_action
 - nntp_host

See https://bugs.launchpad.net/mailman/+bug/971013 for details.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'upgrade',
    ]


from mailman.interfaces.archiver import ArchivePolicy


VERSION = '20120407000000'
_helper = None



def upgrade(database, store, version, module_path):
    if database.TAG == 'sqlite':
        upgrade_sqlite(database, store, version, module_path)
    else:
        upgrade_postgres(database, store, version, module_path)



def archive_policy(archive, archive_private):
    """Convert archive and archive_private to archive_policy."""
    if archive == 0:
        return int(ArchivePolicy.never)
    elif archive_private == 1:
        return int(ArchivePolicy.private)
    else:
        return int(ArchivePolicy.public)



def upgrade_sqlite(database, store, version, module_path):
    # Load the first part of the migration.  This creates a temporary table to
    # hold the new mailinglist table columns.  The problem is that some of the
    # changes must be performed in Python, so after the first part is loaded,
    # we do the Python changes, drop the old mailing list table, and then
    # rename the temporary table to its place.
    database.load_schema(
        store, version, 'sqlite_{0}_01.sql'.format(version), module_path)
    results = store.execute(
        'SELECT id, include_list_post_header, '
        'news_prefix_subject_too, news_moderation, '
        'archive, archive_private FROM mailinglist;')
    for value in results:
        (id, list_post,
         news_prefix, news_moderation,
         archive, archive_private) = value
        # Figure out what the new archive_policy column value should be.
        store.execute(
            'UPDATE ml_backup SET '
            '    allow_list_posts = {0}, '
            '    newsgroup_moderation = {1}, '
            '    nntp_prefix_subject_too = {2}, '
            '    archive_policy = {3} '
            'WHERE id = {4};'.format(
                list_post,
                news_moderation,
                news_prefix,
                archive_policy(archive, archive_private),
                id))
    store.execute('DROP TABLE mailinglist;')
    store.execute('ALTER TABLE ml_backup RENAME TO mailinglist;')



def upgrade_postgres(database, store, version, module_path):
    # Get the old values from the mailinglist table.
    results = store.execute(
        'SELECT id, archive, archive_private FROM mailinglist;')
    # Do the simple renames first.
    store.execute(
        'ALTER TABLE mailinglist '
        '   RENAME COLUMN news_prefix_subject_too TO nntp_prefix_subject_too;')
    store.execute(
        'ALTER TABLE mailinglist '
        '   RENAME COLUMN news_moderation TO newsgroup_moderation;')
    store.execute(
        'ALTER TABLE mailinglist '
        '   RENAME COLUMN include_list_post_header TO allow_list_posts;')
    # Do the easy column drops next.
    for column in ('archive_volume_frequency', 
                   'generic_nonmember_action',
                   'nntp_host'):
        store.execute(
            'ALTER TABLE mailinglist DROP COLUMN {0};'.format(column))
    # Now do the trickier collapsing of values.  Add the new columns.
    store.execute('ALTER TABLE mailinglist ADD COLUMN archive_policy INTEGER;')
    # Query the database for the old values of archive and archive_private in
    # each column.  Then loop through all the results and update the new
    # archive_policy from the old values.
    for value in results:
        id, archive, archive_private = value
        store.execute('UPDATE mailinglist SET '
                      '    archive_policy = {0} '
                      'WHERE id = {1};'.format(
                          archive_policy(archive, archive_private),
                          id))
    # Now drop the old columns.
    for column in ('archive', 'archive_private'):
        store.execute(
            'ALTER TABLE mailinglist DROP COLUMN {0};'.format(column))
    # Record the migration in the version table.
    database.load_schema(store, version, None, module_path)
