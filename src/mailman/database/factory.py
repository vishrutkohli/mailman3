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

"""Database factory."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'DatabaseFactory',
    'DatabaseTemporaryFactory',
    'DatabaseTestingFactory',
    ]


import os
import types
import shutil
import tempfile

from functools import partial
from urlparse import urlsplit, urlunsplit
from zope.interface import implementer
from zope.interface.verify import verifyObject

from mailman.config import config
from mailman.interfaces.database import IDatabase, IDatabaseFactory
from mailman.testing.helpers import configuration
from mailman.utilities.modules import call_name



@implementer(IDatabaseFactory)
class DatabaseFactory:
    """Create a new database."""

    @staticmethod
    def create():
        """See `IDatabaseFactory`."""
        database_class = config.database['class']
        database = call_name(database_class)
        verifyObject(IDatabase, database)
        database.initialize()
        database.load_migrations()
        database.commit()
        return database



def _reset(self):
    """See `IDatabase`."""
    from mailman.database.model import ModelMeta
    self.store.rollback()
    self._pre_reset(self.store)
    ModelMeta._reset(self.store)
    self._post_reset(self.store)
    self.store.commit()


@implementer(IDatabaseFactory)
class DatabaseTestingFactory:
    """Create a new database for testing."""

    @staticmethod
    def create():
        """See `IDatabaseFactory`."""
        database_class = config.database['class']
        database = call_name(database_class)
        verifyObject(IDatabase, database)
        database.initialize()
        database.load_migrations()
        database.commit()
        # Make _reset() a bound method of the database instance.
        database._reset = types.MethodType(_reset, database)
        return database



def _sqlite_cleanup(self, tempdir):
    shutil.rmtree(tempdir)


def _postgresql_cleanup(self, database, tempdb_name):
    database.store.rollback()
    database.store.close()
    config.db.store.execute('DROP DATABASE {0}'.format(tempdb_name))


@implementer(IDatabaseFactory)
class DatabaseTemporaryFactory:
    """Create a temporary database for some of the migration tests."""

    @staticmethod
    def create():
        """See `IDatabaseFactory`."""
        database_class_name = config.database['class']
        database = call_name(database_class_name)
        verifyObject(IDatabase, database)
        if database.TAG == 'sqlite':
            tempdir = tempfile.mkdtemp()
            url = 'sqlite:///' + os.path.join(tempdir, 'mailman.db')
            with configuration('database', url=url):
                database.initialize()
            database._cleanup = types.MethodType(
                partial(_sqlite_cleanup, tempdir=tempdir), database)
            # bool column values in SQLite must be integers.
            database.FALSE = 0
            database.TRUE = 1
        elif database.TAG == 'postgres':
            parts = urlsplit(config.database.url)
            assert parts.scheme == 'postgres'
            new_parts = list(parts)
            new_parts[2] = '/mmtest'
            url = urlunsplit(new_parts)
            # Use the existing database connection to create a new testing
            # database.
            config.db.store.execute('ABORT;')
            config.db.store.execute('CREATE DATABASE mmtest;')
            with configuration('database', url=url):
                database.initialize()
            database._cleanup = types.MethodType(
                partial(_postgresql_cleanup, 
                        database=database, 
                        tempdb_name='mmtest'),
                database)
            # bool column values in PostgreSQL.
            database.FALSE = 'False'
            database.TRUE = 'True'
        else:
            raise RuntimeError(
                'Unsupported test database: {0}'.format(database.TAG))
        # Don't load the migrations.
        return database
