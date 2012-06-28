# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""A wrapper around passlib."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'encrypt',
    'verify',
    ]


import re

from passlib.registry import get_crypt_handler

from mailman.config import config
from mailman.testing import layers
from mailman.utilities.modules import find_name

SCHEME_RE = r'{(?P<scheme>[^}]+?)}(?P<rest>.*)'.encode()



def encrypt(secret):
    hasher = find_name(config.passwords.password_scheme)
    # For reproducibility, don't use any salt in the test suite.
    kws = {}
    if layers.is_testing and 'salt' in hasher.setting_kwds:
        kws['salt'] = b''
    hashed = hasher.encrypt(secret, **kws)
    return b'{{{0}}}{1}'.format(hasher.name, hashed)


def verify(hashed, password):
    mo = re.match(SCHEME_RE, hashed, re.IGNORECASE)
    if not mo:
        return False
    scheme, secret = mo.groups(('scheme', 'rest'))
    hasher = get_crypt_handler(scheme)
    return hasher.verify(password, secret)
