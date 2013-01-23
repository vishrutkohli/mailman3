# Copyright (C) 2009-2013 by the Free Software Foundation, Inc.
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

"""Print the mailman configuration."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Mailmanconf'
    ]


import sys

from zope.interface import implementer
from lazr.config._config import Section

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand



@implementer(ICLISubCommand)
class Mailmanconf:
    """Print the mailman configuration."""

    name = 'mailmanconf'

    def add(self, parser, command_parser):
        self.parser = parser
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-o', '--output',
            action='store', help=_("""\
            File to send the output to.  If not given, standard output is
            used."""))
        command_parser.add_argument(
            '-s', '--section',
            action='store', help=_("Section to use for the lookup (optional)."))
        command_parser.add_argument(
            '-k', '--key',
            action='store', help=_("Key to use for the lookup (optional)."))

    def __get_section(self, section):
        return getattr(config, section)
    
    def __get_value(self, section, key):
        return getattr(getattr(config, section), key)

    def __print_full_syntax(self, section, key, value, output):
        print('[{0}] {1}: {2}'.format(section, key, value), file=output)

    def __show_section_error(self, section):
        self.parser.error('No such section: {0}'.format(section))

    def process(self, args):
        """See `ICLISubCommand`."""
        if args.output is None:
            output = sys.stdout
        else:
            # We don't need to close output because that will happen
            # automatically when the script exits.
            output = open(args.output, 'w')
        # Both section and key are given, we can directly look up the value
        if args.section is not None and args.key is not None:
            try:
                section = self.__get_section(args.section)
            except AttributeError:
                self.__show_section_error(args.section)
            try:
                value = self.__get_key(section, args.key)
            except AttributeError:
                self.parser.error('No such key: {0}'.format(args.key))
            print(value, file=output)
        elif args.section is not None and args.key is None:
            try:
                # not all the attributes in config are actual sections,
                # so we have to check their types first and display an
                # error if the given section is not really a section
                if isinstance(getattr(config, args.section), Section):
                    for key in getattr(config, args.section):
                        self.__print_full_syntax(args.section, key, self.__get_value(args.section, key), output)
                else:
                    self.__show_section_error(args.section)
            except AttributeError:
                self.__show_section_error(args.section)
        elif args.section is None and args.key is not None:
            for section in config.schema._section_schemas:
                # We have to ensure that the current section actually exists and
                # that it contains the given key
                if hasattr(config, section) and hasattr(getattr(config, section), args.key):
                    self.__print_full_syntax(section, args.key, self.__get_value(section, args.key), output)
        # Just display all the sections and their corresponding key/value pairs.
        # However, we have to make sure that the current sections and key
        # which are being looked up actually exist before trying to print them.
        elif args.section is None and args.key is None:
            section_schemas = config.schema._section_schemas
            for section in section_schemas:
                if hasattr(config, section):
                    current_section = getattr(config, section)
                    for key in current_section:
                        if hasattr(current_section, key):
                            self.__print_full_syntax(section, key, self.__get_value(section, key), output)