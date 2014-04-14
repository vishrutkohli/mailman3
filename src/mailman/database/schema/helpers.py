# Copyright (C) 2013-2014 by the Free Software Foundation, Inc.
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

"""Schema migration helpers."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'make_listid',
    ]



def make_listid(fqdn_listname):
    """Turn a FQDN list name into a List-ID."""
    list_name, at, mail_host = fqdn_listname.partition('@')
    if at == '':
        # If there is no @ sign in the value, assume it already contains the
        # list-id.
        return fqdn_listname
    return '{0}.{1}'.format(list_name, mail_host)



def pivot(store, table_name):
    """Pivot a backup table into the real table name."""
    store.execute('DROP TABLE {}'.format(table_name))
    store.execute('ALTER TABLE {0}_backup RENAME TO {0}'.format(table_name))
