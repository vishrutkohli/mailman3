# Copyright (C) 2007-2014 by the Free Software Foundation, Inc.
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

"""Storm type conversions."""


from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Enum',
    'UUID',
    ]

import uuid

from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator, BINARY, CHAR
from sqlalchemy.dialects import postgresql



class Enum(TypeDecorator):
    """
    Stores an integer-based Enum as an integer in the database, and converts it
    on-the-fly.
    """

    impl = Integer

    def __init__(self, *args, **kw):
        self.enum = kw.pop("enum")
        TypeDecorator.__init__(self, *args, **kw)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        return value.value


    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum(value)



class UUID(TypeDecorator):
    """
    Stores a UUID in the database natively when it can and falls back to
    a BINARY(16) or a CHAR(32) when it can't.

    ::

        from sqlalchemy_utils import UUIDType
        import uuid

        class User(Base):
            __tablename__ = 'user'

            # Pass `binary=False` to fallback to CHAR instead of BINARY
            id = sa.Column(UUIDType(binary=False), primary_key=True)
    """
    impl = BINARY(16)

    python_type = uuid.UUID

    def __init__(self, binary=True, native=True):
        """
        :param binary: Whether to use a BINARY(16) or CHAR(32) fallback.
        """
        self.binary = binary
        self.native = native

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql' and self.native:
            # Use the native UUID type.
            return dialect.type_descriptor(postgresql.UUID())

        else:
            # Fallback to either a BINARY or a CHAR.
            kind = self.impl if self.binary else CHAR(32)
            return dialect.type_descriptor(kind)

    @staticmethod
    def _coerce(value):
        if value and not isinstance(value, uuid.UUID):
            try:
                value = uuid.UUID(value)

            except (TypeError, ValueError):
                value = uuid.UUID(bytes=value)

        return value

    def process_bind_param(self, value, dialect):
        if value is None:
            return value

        if not isinstance(value, uuid.UUID):
            value = self._coerce(value)

        if self.native and dialect.name == 'postgresql':
            return str(value)

        return value.bytes if self.binary else value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value

        if self.native and dialect.name == 'postgresql':
            return uuid.UUID(value)

        return uuid.UUID(bytes=value) if self.binary else uuid.UUID(value)
