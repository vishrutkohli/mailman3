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

"""Test database schema migrations"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest
import types

import alembic.command
from mock import Mock
from sqlalchemy import MetaData, Table, Column, Integer, Unicode

from mailman.config import config
from mailman.testing.layers import DatabaseLayer
from mailman.database.factory import SchemaManager, _reset
from mailman.database.sqlite import SQLiteDatabase
from mailman.database.alembic import alembic_cfg
from mailman.database.model import Model



class TestSchemaManager(unittest.TestCase):

    layer = DatabaseLayer

    def setUp(self):
        config.db = SQLiteDatabase()
        config.db.initialize()
        config.db._reset = types.MethodType(_reset, config.db)
        self.schema_mgr = SchemaManager(config.db)

    def tearDown(self):
        if "version" in Model.metadata.tables:
            version = Model.metadata.tables["version"]
            version.drop(config.db.engine, checkfirst=True)
            Model.metadata.remove(version)


    def _table_exists(self, tablename):
        md = MetaData()
        md.reflect(bind=config.db.engine)
        return tablename in md.tables

    def _create_storm_version_table(self, revision):
        version_table = Table("version", Model.metadata,
                Column("id", Integer, primary_key=True),
                Column("component", Unicode),
                Column("version", Unicode),
                )
        version_table.create(config.db.engine)
        config.db.store.execute(version_table.insert().values(
                component='schema', version=revision))
        config.db.commit()


    def test_current_db(self):
        """The database is already at the latest version"""
        alembic.command.stamp(alembic_cfg, "head")
        self.schema_mgr._create = Mock()
        self.schema_mgr._upgrade = Mock()
        self.schema_mgr.setup_db()
        self.assertFalse(self.schema_mgr._create.called)
        self.assertFalse(self.schema_mgr._upgrade.called)

    def test_initial(self):
        """No existing database"""
        self.assertFalse(self._table_exists("mailinglist"))
        self.assertFalse(self._table_exists("alembic_version"))
        self.schema_mgr._upgrade = Mock()
        self.schema_mgr.setup_db()
        self.assertFalse(self.schema_mgr._upgrade.called)
        self.assertTrue(self._table_exists("mailinglist"))
        self.assertTrue(self._table_exists("alembic_version"))

    def test_storm(self):
        """Existing Storm database"""
        Model.metadata.create_all(config.db.engine)
        self._create_storm_version_table(
                self.schema_mgr.LAST_STORM_SCHEMA_VERSION)
        self.schema_mgr._create = Mock()
        self.schema_mgr.setup_db()
        self.assertFalse(self.schema_mgr._create.called)
        self.assertTrue(self._table_exists("mailinglist")
                    and self._table_exists("alembic_version")
                    and not self._table_exists("version"))

    def test_old_storm(self):
        """Existing Storm database in an old version"""
        Model.metadata.create_all(config.db.engine)
        self._create_storm_version_table("001")
        self.schema_mgr._create = Mock()
        self.assertRaises(RuntimeError, self.schema_mgr.setup_db)
        self.assertFalse(self.schema_mgr._create.called)

    def test_old_db(self):
        """The database is in an old revision, must upgrade"""
        alembic.command.stamp(alembic_cfg, "head")
        md = MetaData()
        md.reflect(bind=config.db.engine)
        config.db.store.execute(md.tables["alembic_version"].delete())
        config.db.store.execute(md.tables["alembic_version"].insert().values(
                version_num="dummyrevision"))
        config.db.commit()
        self.schema_mgr._create = Mock()
        self.schema_mgr._upgrade = Mock()
        self.schema_mgr.setup_db()
        self.assertFalse(self.schema_mgr._create.called)
        self.assertTrue(self.schema_mgr._upgrade.called)
