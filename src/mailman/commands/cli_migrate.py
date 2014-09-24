# Copyright (C) 2010-2014 by the Free Software Foundation, Inc.
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

"""bin/mailman migrate."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Migrate',
]

from alembic import command
from alembic.config import Config
from zope.interface import implementer

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand


@implementer(ICLISubCommand)
class Migrate:
    """Migrate the mailman database to the schema."""

    name = 'migrate'

    def add(self, parser, comman_parser):
        """See `ICLISubCommand`."""
        pass

    def process(self, args):
        alembic_cfg= Config()
        alembic_cfg.set_main_option(
            "script_location", config.alembic['script_location'])
        command.upgrade(alembic_cfg, "head")
        print("Updated the database schema.")
