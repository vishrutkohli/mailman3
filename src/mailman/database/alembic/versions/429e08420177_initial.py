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

"""Initial migration.

This empty migration file makes sure there is always an alembic_version
in the database.  As a consequence, if the database version is reported
as None, it means the database needs to be created from scratch with
SQLAlchemy itself.

It also removes the `version` table left over from Storm (if it exists).

Revision ID: 429e08420177
Revises: None
Create Date: 2014-10-02 10:18:17.333354
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]

# Revision identifiers, used by Alembic.
revision = '429e08420177'
down_revision = None

from alembic import op


def upgrade():
    op.drop_table('version')


def downgrade():
    pass
