# Copyright (C) 2006-2014 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'StormBaseDatabase',
    ]


import os
import sys
import logging

from lazr.config import as_boolean
from pkg_resources import resource_listdir, resource_string
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from zope.interface import implementer

from mailman.config import config
from mailman.interfaces.database import IDatabase
from mailman.model.version import Version
from mailman.utilities.string import expand

log = logging.getLogger('mailman.config')

NL = '\n'



@implementer(IDatabase)
class SABaseDatabase:
    """The database base class for use with SQLAlchemy.

    Use this as a base class for your DB_Specific derived classes.
    """
    TAG=''

    def __init__(self):
        self.url = None
        self.store = None
        self.transaction = None

    def begin(self):
        pass

    def commit(self):
        self.store.commit()

    def abort(self):
        self.store.rollback()

    def _prepare(self, url):
        pass

    def _database_exists(self):
        """Return True if the database exists and is initialized.

        Return False when Mailman needs to create and initialize the
        underlying database schema.

        Base classes *must* override this.
        """
        raise NotImplementedError

    def _pre_reset(self, store):
        """Clean up method for testing.

        This method is called during the test suite just before all the model
        tables are removed.  Override this to perform any database-specific
        pre-removal cleanup.
        """
        pass

    def _post_reset(self, store):
        """Clean up method for testing.

        This method is called during the test suite just after all the model
        tables have been removed.  Override this to perform any
        database-specific post-removal cleanup.
        """
        pass
    def initialize(self, debug=None):
        url = expand(config.database.url, config.paths)
        log.debug('Database url: %s', url)
        self.url = url
        self._prepare(url)
        self.engine = create_engine(url)
        session = sessionmaker(bind=self.engine)
        self.store = session()
        self.store.commit()

    def load_migrations(self, until=None):
        """Load schema migrations.

        :param until: Load only the migrations up to the specified timestamp.
            With default value of None, load all migrations.
        :type until: string
        """
        from mailman.database.model import Model
        Model.metadata.create_all(self.engine)

    def load_sql(self, store, sql):
        """Load the given SQL into the store.

        :param store: The Storm store to load the schema into.
        :type store: storm.locals.Store`
        :param sql: The possibly multi-line SQL to load.
        :type sql: string
        """
        # Discard all blank and comment lines.
        lines = (line for line in sql.splitlines()
                 if line.strip() != '' and line.strip()[:2] != '--')
        sql = NL.join(lines)
        for statement in sql.split(';'):
            if statement.strip() != '':
                store.execute(statement + ';')

    def load_schema(self, store, version, filename, module_path):
        """Load the schema from a file.

        This is a helper method for migration classes to call.

        :param store: The Storm store to load the schema into.
        :type store: storm.locals.Store`
        :param version: The schema version identifier of the form
            YYYYMMDDHHMMSS.
        :type version: string
        :param filename: The file name containing the schema to load.  Pass
            `None` if there is no schema file to load.
        :type filename: string
        :param module_path: The fully qualified Python module path to the
            migration module being loaded.  This is used to record information
            for use by the test suite.
        :type module_path: string
        """
        if filename is not None:
            contents = resource_string('mailman.database.schema', filename)
            self.load_sql(store, contents)
        # Add a marker that indicates the migration version being applied.
        store.add(Version(component='schema', version=version))



    @staticmethod
    def _make_temporary():
        raise NotImplementedError
