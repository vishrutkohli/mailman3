# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Interfaces for database interaction."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'DatabaseError',
    'IDatabase',
    'IDatabaseFactory',
    ]


from zope.interface import Attribute, Interface

from mailman.interfaces.errors import MailmanError



class DatabaseError(MailmanError):
    """A problem with the database occurred."""



class IDatabase(Interface):
    """Database layer interface."""

    def initialize(debug=None):
        """Initialize the database layer, using whatever means necessary.

        :param debug: When None (the default), the configuration file
            determines whether the database layer should have increased
            debugging or not.  When True or False, this overrides the
            configuration file setting.
        """

    def _make_temporary():
        """Make a temporary database.

        This is a @staticmethod used in the test framework.

        :return: An object with one attribute and one method.  The attribute
            `database` is the temporary `IDatabase`.  The method is a callable
            named `cleanup()`, taking no arguments which should be called when
            the temporary database is no longer necessary.  The database will
            already be initialized, but no migrations will have been loaded
            into it.
        """

    def begin():
        """Begin the current transaction."""

    def commit():
        """Commit the current transaction."""

    def abort():
        """Abort the current transaction."""

    store = Attribute(
        """The underlying Storm store on which you can do queries.""")



class IDatabaseFactory(Interface):
    "Interface for creating new databases."""

    def create():
        """Return a new `IDatabase`.

        The database will be initialized and all migrations will be loaded.

        :return: A new database.
        :rtype: IDatabase
        """
