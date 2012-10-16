# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Ban manager."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'BanManager',
    ]


import re

from storm.locals import Int, Unicode
from zope.interface import implementer

from mailman.database.model import Model
from mailman.database.transaction import dbconnection
from mailman.interfaces.bans import IBan, IBanManager



@implementer(IBan)
class Ban(Model):
    """See `IBan`."""

    id = Int(primary=True)
    email = Unicode()
    list_id = Unicode()

    def __init__(self, email, list_id):
        super(Ban, self).__init__()
        self.email = email
        self.list_id = list_id



@implementer(IBanManager)
class BanManager:
    """See `IBanManager`."""

    def __init__(self, mailing_list=None):
        self._list_id = (None if mailing_list is None
                         else mailing_list.list_id)

    @dbconnection
    def ban(self, store, email):
        """See `IBanManager`."""
        bans = store.find(Ban, email=email, list_id=self._list_id)
        if bans.count() == 0:
            ban = Ban(email, self._list_id)
            store.add(ban)

    @dbconnection
    def unban(self, store, email):
        """See `IBanManager`."""
        ban = store.find(Ban, email=email, list_id=self._list_id).one()
        if ban is not None:
            store.remove(ban)

    @dbconnection
    def is_banned(self, store, email):
        """See `IBanManager`."""
        list_id = self._list_id
        if list_id is None:
            # The client is asking for global bans.  Look up bans on the
            # specific email address first.
            bans = store.find(Ban, email=email, list_id=None)
            if bans.count() > 0:
                return True
            # And now look for global pattern bans.
            bans = store.find(Ban, list_id=None)
            for ban in bans:
                if (ban.email.startswith('^') and
                    re.match(ban.email, email, re.IGNORECASE) is not None):
                    return True
        else:
            # This is a list-specific ban.
            bans = store.find(Ban, email=email, list_id=list_id)
            if bans.count() > 0:
                return True
            # Try global bans next.
            bans = store.find(Ban, email=email, list_id=None)
            if bans.count() > 0:
                return True
            # Now try specific mailing list bans, but with a pattern.
            bans = store.find(Ban, list_id=list_id)
            for ban in bans:
                if (ban.email.startswith('^') and
                    re.match(ban.email, email, re.IGNORECASE) is not None):
                    return True
            # And now try global pattern bans.
            bans = store.find(Ban, list_id=None)
            for ban in bans:
                if (ban.email.startswith('^') and
                    re.match(ban.email, email, re.IGNORECASE) is not None):
                    return True
        return False
