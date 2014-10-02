"""Initial migration

This empty migration file makes sure there is always an alembic_version in the
database. As a consequence, if the DB version is reported as None, it means the
database needs to be created from scratch with SQLAlchemy itself.

It also removes the "version" table left over from Storm (if it exists).


Revision ID: 429e08420177
Revises: None
Create Date: 2014-10-02 10:18:17.333354

"""

# revision identifiers, used by Alembic.
revision = '429e08420177'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_table('version')


def downgrade():
    pass
