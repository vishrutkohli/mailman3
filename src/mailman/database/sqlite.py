# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""SQLite database support."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'SQLiteDatabase',
    ]


import os
import shutil
import tempfile

from urlparse import urlparse

from mailman.database.base import StormBaseDatabase



class _TestDB:
    # For the test suite; bool column values.
    TRUE = 1
    FALSE = 0

    def __init__(self, database, tempdir):
        self.database = database
        self._tempdir = tempdir

    def cleanup(self):
        shutil.rmtree(self._tempdir)



class SQLiteDatabase(StormBaseDatabase):
    """Database class for SQLite."""

    TAG = 'sqlite'

    def _database_exists(self, store):
        """See `BaseDatabase`."""
        table_query = 'select tbl_name from sqlite_master;'
        table_names = set(item[0] for item in
                          store.execute(table_query))
        return 'version' in table_names

    def _prepare(self, url):
        parts = urlparse(url)
        assert parts.scheme == 'sqlite', (
            'Database url mismatch (expected sqlite prefix): {0}'.format(url))
        path = os.path.normpath(parts.path)
        fd = os.open(path, os.O_WRONLY |  os.O_NONBLOCK | os.O_CREAT, 0666)
        # Ignore errors
        if fd > 0:
            os.close(fd)

    @staticmethod
    def _make_testdb():
        from mailman.testing.helpers import configuration
        tempdir = tempfile.mkdtemp()
        url = 'sqlite:///' + os.path.join(tempdir, 'mailman.db')
        database = SQLiteDatabase()
        with configuration('database', url=url):
            database.initialize()
        return _TestDB(database, tempdir)
