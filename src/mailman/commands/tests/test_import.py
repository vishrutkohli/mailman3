# Copyright (C) 2011-2015 by the Free Software Foundation, Inc.
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

"""Test the `mailman import21` subcommand."""

__all__ = [
    'TestImport',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.commands.cli_import import Import21
from mailman.testing.layers import ConfigLayer
from mock import patch
from pkg_resources import resource_filename



class FakeArgs:
    listname = ["test@example.com"]
    pickle_file = [resource_filename(
        'mailman.testing', 'config-with-instances.pck')]



class TestImport(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self.command = Import21()
        self.args = FakeArgs()
        self.mlist = create_list('test@example.com')

    @patch("mailman.commands.cli_import.import_config_pck")
    def test_process(self, import_config_pck):
        try:
            self.command.process(self.args)
        except ImportError:
            self.fail("The pickle failed loading")
        self.assertTrue(import_config_pck.called)
