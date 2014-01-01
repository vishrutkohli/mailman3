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

"""3.0b3 -> 3.0b4 schema migrations.

Renamed:
 * bounceevent.list_name -> bounceevent.list_id
"""


from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'upgrade'
    ]


from mailman.database.schema.helpers import make_listid, pivot


VERSION = '20130406000000'



def upgrade(database, store, version, module_path):
    if database.TAG == 'sqlite':
        upgrade_sqlite(database, store, version, module_path)
    else:
        upgrade_postgres(database, store, version, module_path)



def upgrade_sqlite(database, store, version, module_path):
    database.load_schema(
        store, version, 'sqlite_{}_01.sql'.format(version), module_path)
    results = store.execute("""
        SELECT id, list_name
        FROM bounceevent;
        """)
    for id, list_name in results:
        store.execute("""
            UPDATE bounceevent_backup SET list_id = '{}'
            WHERE id = {};
            """.format(make_listid(list_name), id))
    pivot(store, 'bounceevent')



def upgrade_postgres(database, store, version, module_path):
    pass
