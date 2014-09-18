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

from operator import attrgetter

from sqlalchemy.ext.declarative import declarative_base


class ModelMeta(object):
    """Do more magic on table classes."""

    _class_registry = set()

    def __init__(self, name, bases, dict):
        # Before we let the base class do it's thing, force an __tablename__
        # property to enforce our table naming convention.
        self.__tablename__ = name.lower()
        # super(ModelMeta, self).__init__(name, bases, dict)
        # Register the model class so that it can be more easily cleared.
        # This is required by the test framework so that the corresponding
        # table can be reset between tests.
        #
        # The PRESERVE flag indicates whether the table should be reset or
        # not.  We have to handle the actual Model base class explicitly
        # because it does not correspond to a table in the database.
        if not getattr(self, 'PRESERVE', False) and name != 'Model':
            ModelMeta._class_registry.add(self)

    @staticmethod
    def _reset(db):
        Model.metadata.drop_all(db.engine)
        Model.metadata.create_all(db.engine)

        # Make sure this is deterministic, by sorting on the storm table name.
        # classes = sorted(ModelMeta._class_registry,
        #                  key=attrgetter('__tablename__'))
        # print("\n\n" + str(classes) + "\n\n")
        # for model_class in classes:
        #    store.query(model_class).delete()

Model = declarative_base(cls=ModelMeta)
