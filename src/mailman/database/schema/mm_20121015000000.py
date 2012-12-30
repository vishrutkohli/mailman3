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

"""3.0b2 -> 3.0b3 schema migrations.

Renamed:
 * bans.mailing_list -> bans.list_id

Removed:
 * mailinglist.new_member_options
 * mailinglist.send_remindersn
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'upgrade',
    ]


VERSION = '20121015000000'



def upgrade(database, store, version, module_path):
    if database.TAG == 'sqlite':
        upgrade_sqlite(database, store, version, module_path)
    else:
        upgrade_postgres(database, store, version, module_path)



def _make_listid(fqdn_listname):
    list_name, at, mail_host = fqdn_listname.partition('@')
    if at == '':
        # If there is no @ sign in the value, assume it already contains the
        # list-id.
        return fqdn_listname
    return '{0}.{1}'.format(list_name, mail_host)



def upgrade_sqlite(database, store, version, module_path):
    database.load_schema(
        store, version, 'sqlite_{0}_01.sql'.format(version), module_path)
    results = store.execute("""
        SELECT id, mailing_list
        FROM ban;
        """)
    for id, mailing_list in results:
        # Skip global bans since there's nothing to update.
        if mailing_list is None:
            continue
        store.execute("""
            UPDATE ban_backup SET list_id = '{0}'
            WHERE id = {1};
            """.format(_make_listid(mailing_list), id))
    # Pivot the bans backup table to the real thing.
    store.execute('DROP TABLE ban;')
    store.execute('ALTER TABLE ban_backup RENAME TO ban;')
    # Pivot the mailinglist backup table to the real thing.
    store.execute('DROP TABLE mailinglist;')
    store.execute('ALTER TABLE ml_backup RENAME TO mailinglist;')



def upgrade_postgres(database, store, version, module_path):
    # Get the old values from the ban table.
    results = store.execute('SELECT id, mailing_list FROM ban;')
    store.execute('ALTER TABLE ban ADD COLUMN list_id TEXT;')
    for id, mailing_list in results:
        # Skip global bans since there's nothing to update.
        if mailing_list is None:
            continue
        store.execute("""
            UPDATE ban SET list_id = '{0}'
            WHERE id = {1};
            """.format(_make_listid(mailing_list), id))
    store.execute('ALTER TABLE ban DROP COLUMN mailing_list;')
    store.execute('ALTER TABLE mailinglist DROP COLUMN new_member_options;')
    store.execute('ALTER TABLE mailinglist DROP COLUMN send_reminders;')
    store.execute('ALTER TABLE mailinglist DROP COLUMN subscribe_policy;')
    store.execute('ALTER TABLE mailinglist DROP COLUMN unsubscribe_policy;')
    store.execute(
        'ALTER TABLE mailinglist DROP COLUMN subscribe_auto_approval;')
    store.execute('ALTER TABLE mailinglist DROP COLUMN private_roster;')
    store.execute(
        'ALTER TABLE mailinglist DROP COLUMN admin_member_chunksize;')
    # Record the migration in the version table.
    database.load_schema(store, version, None, module_path)
