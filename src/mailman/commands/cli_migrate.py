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
from zope.interface import implementer

from mailman.core.i18n import _
from mailman.database.alembic import alembic_cfg
from mailman.interfaces.command import ICLISubCommand



@implementer(ICLISubCommand)
class Migrate:
    """Migrate the Mailman database to the latest schema."""

    name = 'migrate'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-a', '--autogenerate',
            action='store_true', help=_("""\
            Autogenerate the migration script using Alembic."""))
        command_parser.add_argument(
            '-q', '--quiet',
            action='store_true', default=False,
            help=('Produce less output.'))

    def process(self, args):
        if args.autogenerate:
            command.revision(alembic_cfg, autogenerate=True)
        else:
            command.upgrade(alembic_cfg, 'head')
            if not args.quiet:
                print('Updated the database schema.')
