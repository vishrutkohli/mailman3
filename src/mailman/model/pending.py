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

"""Implementations of the IPendable and IPending interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Pended',
    'Pendings',
    ]


import time
import random
import hashlib

from lazr.config import as_timedelta
from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, LargeBinary, Unicode)
from sqlalchemy.orm import relationship
from zope.interface import implementer
from zope.interface.verify import verifyObject

from mailman.config import config
from mailman.database.model import Model
from mailman.database.transaction import dbconnection
from mailman.interfaces.pending import (
    IPendable, IPended, IPendedKeyValue, IPendings)
from mailman.utilities.datetime import now
from mailman.utilities.modules import call_name



@implementer(IPendedKeyValue)
class PendedKeyValue(Model):
    """A pended key/value pair, tied to a token."""

    __tablename__ = 'pendedkeyvalue'

    def __init__(self, key, value):
        self.key = key
        self.value = value

    id = Column(Integer, primary_key=True)
    key = Column(Unicode)
    value = Column(Unicode)
    pended_id = Column(Integer, ForeignKey('pended.id'))



@implementer(IPended)
class Pended(Model):
    """A pended event, tied to a token."""

    __tablename__ = 'pended'

    def __init__(self, token, expiration_date):
        super(Pended, self).__init__()
        self.token = token
        self.expiration_date = expiration_date

    id = Column(Integer, primary_key=True)
    token = Column(LargeBinary) # TODO : was RawStr()
    expiration_date = Column(DateTime)
    key_values = relationship('PendedKeyValue')



@implementer(IPendable)
class UnpendedPendable(dict):
    pass



@implementer(IPendings)
class Pendings:
    """Implementation of the IPending interface."""

    @dbconnection
    def add(self, store, pendable, lifetime=None):
        verifyObject(IPendable, pendable)
        # Calculate the token and the lifetime.
        if lifetime is None:
            lifetime = as_timedelta(config.mailman.pending_request_life)
        # Calculate a unique token.  Algorithm vetted by the Timbot.  time()
        # has high resolution on Linux, clock() on Windows.  random gives us
        # about 45 bits in Python 2.2, 53 bits on Python 2.3.  The time and
        # clock values basically help obscure the random number generator, as
        # does the hash calculation.  The integral parts of the time values
        # are discarded because they're the most predictable bits.
        for attempts in range(3):
            right_now = time.time()
            x = random.random() + right_now % 1.0 + time.clock() % 1.0
            # Use sha1 because it produces shorter strings.
            token = hashlib.sha1(repr(x)).hexdigest()
            # In practice, we'll never get a duplicate, but we'll be anal
            # about checking anyway.
            if store.query(Pended).filter_by(token=token).count() == 0:
                break
        else:
            raise AssertionError('Could not find a valid pendings token')
        # Create the record, and then the individual key/value pairs.
        pending = Pended(
            token=token,
            expiration_date=now() + lifetime)
        for key, value in pendable.items():
            if isinstance(key, str):
                key = key.encode('utf-8')
            if isinstance(value, str):
                value = value.encode('utf-8')
            elif type(value) is int:
                value = '__builtin__.int\1%s' % value
            elif type(value) is float:
                value = '__builtin__.float\1%s' % value
            elif type(value) is bool:
                value = '__builtin__.bool\1%s' % value
            elif type(value) is list:
                # We expect this to be a list of strings.
                value = ('mailman.model.pending.unpack_list\1' +
                         '\2'.join(value))
            keyval = PendedKeyValue(key=key, value=value)
            pending.key_values.append(keyval)
        store.add(pending)
        return token

    @dbconnection
    def confirm(self, store, token, expunge=True):
        # Token can come in as a unicode, but it's stored in the database as
        # bytes.  They must be ascii.
        pendings = store.query(Pended).filter_by(token=str(token))
        if pendings.count() == 0:
            return None
        assert pendings.count() == 1, (
            'Unexpected token count: {0}'.format(pendings.count()))
        pending = pendings[0]
        pendable = UnpendedPendable()
        # Find all PendedKeyValue entries that are associated with the pending
        # object's ID.  Watch out for type conversions.
        entries = store.query(PendedKeyValue).filter(
            PendedKeyValue.pended_id == pending.id)
        for keyvalue in entries:
            if keyvalue.value is not None and '\1' in keyvalue.value:
                type_name, value = keyvalue.value.split('\1', 1)
                pendable[keyvalue.key] = call_name(type_name, value)
            else:
                pendable[keyvalue.key] = keyvalue.value
            if expunge:
                store.delete(keyvalue)
        if expunge:
            store.delete(pending)
        return pendable

    @dbconnection
    def evict(self, store):
        right_now = now()
        for pending in store.query(Pended).all():
            if pending.expiration_date < right_now:
                # Find all PendedKeyValue entries that are associated with the
                # pending object's ID.
                q = store.query(PendedKeyValue).filter(
                    PendedKeyValue.pended_id == pending.id)
                for keyvalue in q:
                    store.delete(keyvalue)
                store.delete(pending)



def unpack_list(value):
    return value.split('\2')
