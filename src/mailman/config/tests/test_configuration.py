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

"""Test the system-wide global configuration."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestConfiguration',
    'TestExternal',
    ]


import unittest

from pkg_resources import resource_filename

from mailman.config.config import external_configuration, load_external
from mailman.interfaces.configuration import (
    ConfigurationUpdatedEvent, MissingConfigurationFileError)
from mailman.testing.helpers import configuration, event_subscribers
from mailman.testing.layers import ConfigLayer



class TestConfiguration(unittest.TestCase):
    layer = ConfigLayer

    def test_push_and_pop_trigger_events(self):
        # Pushing a new configuration onto the stack triggers a
        # post-processing event.
        events = []
        def on_event(event):
            if isinstance(event, ConfigurationUpdatedEvent):
                # Record both the event and the top overlay.
                events.append(event.config.overlays[0].name)
        with event_subscribers(on_event):
            with configuration('test', _configname='my test'):
                pass
        # There should be two pushed configuration names on the list now, one
        # for the push leaving 'my test' on the top of the stack, and one for
        # the pop, leaving the ConfigLayer's 'test config' on top.
        self.assertEqual(events, ['my test', 'test config'])



class TestExternal(unittest.TestCase):
    """Test external configuration file loading APIs."""

    def test_load_external_by_filename_as_bytes(self):
        filename = resource_filename('mailman.config', 'postfix.cfg')
        contents = load_external(filename)
        self.assertIsInstance(contents, bytes)
        self.assertEqual(contents[:9], b'[postfix]')

    def test_load_external_by_path_as_bytes(self):
        contents = load_external('python:mailman.config.postfix')
        self.assertIsInstance(contents, bytes)
        self.assertEqual(contents[:9], b'[postfix]')

    def test_load_external_by_filename_as_string(self):
        filename = resource_filename('mailman.config', 'postfix.cfg')
        contents = load_external(filename, encoding='utf-8')
        self.assertIsInstance(contents, unicode)
        self.assertEqual(contents[:9], '[postfix]')

    def test_load_external_by_path_as_string(self):
        contents = load_external('python:mailman.config.postfix', 'utf-8')
        self.assertIsInstance(contents, unicode)
        self.assertEqual(contents[:9], '[postfix]')

    def test_external_configuration_by_filename(self):
        filename = resource_filename('mailman.config', 'postfix.cfg')
        parser = external_configuration(filename)
        self.assertEqual(parser.get('postfix', 'postmap_command'),
                         '/usr/sbin/postmap')

    def test_external_configuration_by_path(self):
        parser = external_configuration('python:mailman.config.postfix')
        self.assertEqual(parser.get('postfix', 'postmap_command'),
                         '/usr/sbin/postmap')

    def test_missing_configuration_file(self):
        with self.assertRaises(MissingConfigurationFileError) as cm:
            external_configuration('path:mailman.config.missing')
        self.assertEqual(cm.exception.path, 'path:mailman.config.missing')
