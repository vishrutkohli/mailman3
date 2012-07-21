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

"""3.0b1 -> 3.0b2 schema migrations."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'post_reset',
    'pre_reset',
    'upgrade',
    ]


from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.database import DatabaseError


VERSION = '20120407000000'
_helper = None



def upgrade(database, store, version, module_path):
    if database.TAG == 'sqlite':
        upgrade_sqlite(database, store, version, module_path)
    else:
        # XXX 2012-04-07 BAW: Implement PostgreSQL migration.
        raise DatabaseError('Database {0} migration not support: {1}'.format(
            database.TAG, version))



def upgrade_sqlite(database, store, version, module_path):
    # Load the first part of the migration.  This creates a temporary table to
    # hold the new mailinglist table columns.  The problem is that some of the
    # changes must be performed in Python, so after the first part is loaded,
    # we do the Python changes, drop the old mailing list table, and then
    # rename the temporary table to its place.
    database.load_schema(
        store, version, 'sqlite_{0}_01.sql'.format(version), module_path)
    results = store.execute(
        'select id, news_prefix_subject_too, news_moderation, '
        'archive, archive_private from mailinglist;')
    for value in results:
        id, news_prefix, news_moderation, archive, archive_private = value
        # Figure out what the new archive_policy column value should be.
        if archive == 0:
            archive_policy = int(ArchivePolicy.never)
        elif archive_private == 1:
            archive_policy = int(ArchivePolicy.private)
        else:
            archive_policy = int(ArchivePolicy.public)
        store.execute(
            'update ml_backup set '
            '    newsgroup_moderation = {0}, '
            '    nntp_prefix_subject_too = {1}, '
            '    archive_policy = {2} '
            'where id = {2};'.format(news_moderation, news_prefix, 
                                     archive_policy, id))
    store.execute('drop table mailinglist;')
    store.execute('alter table ml_backup rename to mailinglist;')



def pre_reset(store):
    global _helper
    from mailman.testing.database import ResetHelper
    _helper = ResetHelper(VERSION, store)


def post_reset(store):
    _helper.restore(store)
