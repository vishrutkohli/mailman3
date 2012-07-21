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

"""Database test helpers."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ResetHelper',
    ]


from mailman.model.version import Version



class ResetHelper:
    """Help with database resets; used by schema migrations."""

    def __init__(self, version, store):
        self.version = version
        # Save the entry in the Version table for the test suite reset.  This
        # will be restored below.
        result = store.find(Version, component=version).one()
        self.saved = result.version

    def restore(self, store):
        # We need to preserve the Version table entry for this migration,
        # since its existence defines the fact that the tables have been
        # loaded.
        store.add(Version(component='schema', version=self.version))
        store.add(Version(component=self.version, version=self.saved))
