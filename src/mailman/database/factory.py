# Copyright (C) 2012-2014 by the Free Software Foundation, Inc.
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
    'DatabaseTestingFactory',
    ]


import os
import types

from alembic import command
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flufl.lock import Lock
from sqlalchemy import MetaData
from zope.interface import implementer
from zope.interface.verify import verifyObject

from mailman.config import config
from mailman.database.model import Model
from mailman.database.alembic import alembic_cfg
from mailman.interfaces.database import IDatabase, IDatabaseFactory
from mailman.utilities.modules import call_name, expand_path



@implementer(IDatabaseFactory)
class DatabaseFactory:
    """Create a new database."""

    @staticmethod
    def create():
        """See `IDatabaseFactory`."""
        with Lock(os.path.join(config.LOCK_DIR, 'dbcreate.lck')):
            database_class = config.database['class']
            database = call_name(database_class)
            verifyObject(IDatabase, database)
            database.initialize()
            schema_mgr = SchemaManager(database)
            schema_mgr.setup_db()
            database.commit()
            return database



class SchemaManager:

    LAST_STORM_SCHEMA_VERSION = '20130406000000'

    def __init__(self, database):
        self.database = database
        self.script = ScriptDirectory.from_config(alembic_cfg)

    def get_storm_schema_version(self):
        md = MetaData()
        md.reflect(bind=self.database.engine)
        if "version" not in md.tables:
            return None
        Version = md.tables["version"]
        last_version = self.database.store.query(Version.c.version).filter(
                Version.c.component == "schema"
                ).order_by(Version.c.version.desc()).first()
        # Don't leave open transactions or they will block any schema change
        self.database.commit()
        return last_version

    def _create(self):
        # initial DB creation
        Model.metadata.create_all(self.database.engine)
        command.stamp(alembic_cfg, "head")

    def _upgrade(self):
        command.upgrade(alembic_cfg, "head")

    def setup_db(self):
        context = MigrationContext.configure(self.database.store.connection())
        current_rev = context.get_current_revision()
        head_rev = self.script.get_current_head()
        if current_rev == head_rev:
            return head_rev # already at the latest revision, nothing to do
        if current_rev == None:
            # no alembic information
            storm_version = self.get_storm_schema_version()
            if storm_version is None:
                # initial DB creation
                self._create()
            else:
                # DB from a previous version managed by Storm
                if storm_version.version < self.LAST_STORM_SCHEMA_VERSION:
                    raise RuntimeError(
                            "Upgrading while skipping beta version is "
                            "unsupported, please install the previous "
                            "Mailman beta release")
                # Run migrations to remove the Storm-specific table and
                # upgrade to SQLAlchemy & Alembic
                self._upgrade()
        elif current_rev != head_rev:
            self._upgrade()
        return head_rev



def _reset(self):
    """See `IDatabase`."""
    # Avoid a circular import at module level.
    from mailman.database.model import Model
    self.store.rollback()
    self._pre_reset(self.store)
    Model._reset(self)
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
        Model.metadata.create_all(database.engine)
        database.commit()
        # Make _reset() a bound method of the database instance.
        database._reset = types.MethodType(_reset, database)
        return database
