# Copyright (C) 2014 by the Free Software Foundation, Inc.
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

"""Alembic migration environment."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'run_migrations_offline',
    'run_migrations_online',
    ]


from alembic import context
from alembic.config import Config
from contextlib import closing
from sqlalchemy import create_engine

from mailman.config import config
from mailman.database.model import Model
from mailman.utilities.modules import expand_path
from mailman.utilities.string import expand



def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well.  By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script
    output.
    """
    url = expand(config.database.url, config.paths)
    context.configure(url=url, target_metadata=Model.metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    alembic_cfg = Config()
    alembic_cfg.set_main_option(
        'script_location', expand_path(config.database['alembic_scripts']))
    alembic_cfg.set_section_option('logger_alembic' ,'level' , 'ERROR')
    url = expand(config.database.url, config.paths)
    engine = create_engine(url)

    connection = engine.connect()
    with closing(connection):
        context.configure(
            connection=connection, target_metadata=Model.metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
