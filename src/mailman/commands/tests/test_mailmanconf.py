# Copyright (C) 2011-2013 by the Free Software Foundation, Inc.
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

"""Test the mailmanconf subcommand."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]

import sys
import unittest

from mailman.commands.cli_mailmanconf import Mailmanconf
from mailman.config import config


class FakeArgs:
    section = None
    key = None
    output = None


class FakeParser:
    def __init__(self):
        self.message = None

    def error(self, message):
        self.message = message
        sys.exit(1)



class TestMailmanconf(unittest.TestCase):
    """Test the mailmanconf subcommand."""

    def setUp(self):
        self.command = Mailmanconf()
        self.command.parser = FakeParser()
        self.args = FakeArgs()

    def test_cannot_access_nonexistent_section(self):
        self.args.section = 'thissectiondoesnotexist'
        self.args.key = None
        try:
            self.command.process(self.args)
        except SystemExit:
            pass
        self.assertEqual(self.command.parser.message,
                         'No such section: thissectiondoesnotexist')

    def test_cannot_access_nonexistent_key(self):
        self.args.section = "mailman"
        self.args.key = 'thiskeydoesnotexist'
        try:
            self.command.process(self.args)
        except SystemExit:
            pass
        self.assertEqual(self.command.parser.message,
                         'Section mailman: No such key: thiskeydoesnotexist')
        