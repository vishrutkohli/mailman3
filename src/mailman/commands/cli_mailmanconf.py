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

    def _get_value(self, section, key):
        return getattr(getattr(config, section), key)

    def _print_full_syntax(self, section, key, value, output):
        print('[{0}] {1}: {2}'.format(section, key, value), file=output)

    def _show_key_error(self, section, key):
        self.parser.error('Section %s: No such key: %s' % (section, key))

    def _show_section_error(self, section):
        self.parser.error('No such section: %s' % section)

    def _print_values_for_section(self, section, output):
        current_section = getattr(config, section)
        for key in current_section:
            if hasattr(current_section, key):
                self._print_full_syntax(section, key, self._get_value(section, key), output)

    def _section_exists(self, section):
        # not all the attributes in config are actual sections,
        # so we have to additionally check a sections type
        return hasattr(config, section) and isinstance(getattr(config, section), Section)

    def process(self, args):
        """See `ICLISubCommand`."""
        if args.output is None:
            output = sys.stdout
        else:
            # We don't need to close output because that will happen
            # automatically when the script exits.
            output = open(args.output, 'w')
        section = args.section
        key = args.key
        # Case 1: Both section and key are given, we can directly look up the value
        if section is not None and key is not None:
            if not self._section_exists(section):
                self._show_section_error(section)
            elif not hasattr(getattr(config, section), key):
                self._show_key_error(section, key)
            else:
                print(self._get_value(section, key))
        # Case 2: Section is given, key is not given
        elif section is not None and key is None:
            if self._section_exists(section):
                self._print_values_for_section(section, output)
            else:
                self._show_section_error(section)
        # Case 3: Section is not given, key is given
        elif section is None and key is not None:
            for current_section in config.schema._section_schemas:
                # We have to ensure that the current section actually exists and
                # that it contains the given key
                if self._section_exists(current_section) and hasattr(getattr(config, current_section), key):
                    self._print_full_syntax(current_section, key, self._get_value(current_section, key), output)
        # Case 4: Neither section nor key are given, 
        # just display all the sections and their corresponding key/value pairs.
        elif section is None and key is None:
            for current_section in config.schema._section_schemas:
                # However, we have to make sure that the current sections and key
                # which are being looked up actually exist before trying to print them
                if self._section_exists(current_section):
                    self._print_values_for_section(current_section, output)
