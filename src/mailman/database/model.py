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

"""Base class for all database classes."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Model',
    ]


import contextlib
from operator import attrgetter

from sqlalchemy.ext.declarative import declarative_base

from mailman.config import config

class ModelMeta(object):
    """Do more magic on table classes."""

    @staticmethod
    def _reset(db):
        meta = Model.metadata
        engine = config.db.engine
        with contextlib.closing(engine.connect()) as con:
            trans = con.begin()
            for table in reversed(meta.sorted_tables):
                con.execute(table.delete())
            trans.commit()

Model = declarative_base(cls=ModelMeta)
