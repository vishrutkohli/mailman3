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
    'TestSchemaManager',
    ]


import unittest
import alembic.command

from mock import patch
from sqlalchemy import MetaData, Table, Column, Integer, Unicode
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.schema import Index

from mailman.config import config
from mailman.database.alembic import alembic_cfg
from mailman.database.factory import LAST_STORM_SCHEMA_VERSION, SchemaManager
from mailman.database.model import Model
from mailman.interfaces.database import DatabaseError
from mailman.testing.layers import ConfigLayer



class TestSchemaManager(unittest.TestCase):

    layer = ConfigLayer

    def setUp(self):
        # Drop the existing database.
        Model.metadata.drop_all(config.db.engine)
        md = MetaData()
        md.reflect(bind=config.db.engine)
        for tablename in ('alembic_version', 'version'):
            if tablename in md.tables:
                md.tables[tablename].drop(config.db.engine)
        self.schema_mgr = SchemaManager(config.db)

    def tearDown(self):
        self._drop_storm_database()
        # Restore a virgin database.
        Model.metadata.create_all(config.db.engine)

    def _table_exists(self, tablename):
        md = MetaData()
        md.reflect(bind=config.db.engine)
        return tablename in md.tables

    def _create_storm_database(self, revision):
        version_table = Table(
            'version', Model.metadata,
            Column('id', Integer, primary_key=True),
            Column('component', Unicode),
            Column('version', Unicode),
            )
        version_table.create(config.db.engine)
        config.db.store.execute(version_table.insert().values(
            component='schema', version=revision))
        config.db.commit()
        # Other Storm specific changes, those SQL statements hopefully work on
        # all DB engines...
        config.db.engine.execute(
            'ALTER TABLE mailinglist ADD COLUMN acceptable_aliases_id INT')
        Index('ix_user__user_id').drop(bind=config.db.engine)
        # Don't pollute our main metadata object, create a new one.
        md = MetaData()
        user_table = Model.metadata.tables['user'].tometadata(md)
        Index('ix_user_user_id', user_table.c._user_id).create(
            bind=config.db.engine)
        config.db.commit()

    def _drop_storm_database(self):
        """Remove the leftovers from a Storm DB.

        A drop_all() must be issued afterwards.
        """
        if 'version' in Model.metadata.tables:
            version = Model.metadata.tables['version']
            version.drop(config.db.engine, checkfirst=True)
            Model.metadata.remove(version)
        try:
            Index('ix_user_user_id').drop(bind=config.db.engine)
        except (ProgrammingError, OperationalError):
            # Nonexistent.  PostgreSQL raises a ProgrammingError, while SQLite
            # raises an OperationalError.
            pass
        config.db.commit()

    def test_current_database(self):
        # The database is already at the latest version.
        alembic.command.stamp(alembic_cfg, 'head')
        with patch('alembic.command') as alembic_command:
            self.schema_mgr.setup_database()
            self.assertFalse(alembic_command.stamp.called)
            self.assertFalse(alembic_command.upgrade.called)

    @patch('alembic.command')
    def test_initial(self, alembic_command):
        # No existing database.
        self.assertFalse(self._table_exists('mailinglist'))
        self.assertFalse(self._table_exists('alembic_version'))
        self.schema_mgr.setup_database()
        self.assertFalse(alembic_command.upgrade.called)
        self.assertTrue(self._table_exists('mailinglist'))
        self.assertTrue(self._table_exists('alembic_version'))

    @patch('alembic.command.stamp')
    def test_storm(self, alembic_command_stamp):
        # Existing Storm database.
        Model.metadata.create_all(config.db.engine)
        self._create_storm_database(LAST_STORM_SCHEMA_VERSION)
        self.schema_mgr.setup_database()
        self.assertFalse(alembic_command_stamp.called)
        self.assertTrue(
            self._table_exists('mailinglist')
            and self._table_exists('alembic_version')
            and not self._table_exists('version'))

    @patch('alembic.command')
    def test_old_storm(self, alembic_command):
        # Existing Storm database in an old version.
        Model.metadata.create_all(config.db.engine)
        self._create_storm_database('001')
        self.assertRaises(DatabaseError, self.schema_mgr.setup_database)
        self.assertFalse(alembic_command.stamp.called)
        self.assertFalse(alembic_command.upgrade.called)

    def test_old_db(self):
        # The database is in an old revision, must upgrade.
        alembic.command.stamp(alembic_cfg, 'head')
        md = MetaData()
        md.reflect(bind=config.db.engine)
        config.db.store.execute(md.tables['alembic_version'].delete())
        config.db.store.execute(md.tables['alembic_version'].insert().values(
            version_num='dummyrevision'))
        config.db.commit()
        with patch('alembic.command') as alembic_command:
            self.schema_mgr.setup_database()
            self.assertFalse(alembic_command.stamp.called)
            self.assertTrue(alembic_command.upgrade.called)
