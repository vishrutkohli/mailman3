# Copyright (C) 2013 by the Free Software Foundation, Inc.
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

"""nose2 test infrastructure."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'NosePlugin',
    ]


import os
import re
import doctest
import mailman
import importlib

from mailman.testing.documentation import setup, teardown
from mailman.testing.layers import ConfigLayer, MockAndMonkeyLayer, SMTPLayer
from nose2.events import Plugin

DOT = '.'
FLAGS = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE | doctest.REPORT_NDIFF
TOPDIR = os.path.dirname(mailman.__file__)



class NosePlugin(Plugin):
    configSection = 'mailman'

    def __init__(self):
        super(NosePlugin, self).__init__()
        self.patterns = []
        self.addArgument(self.patterns, 'P', 'pattern',
                         'Add a test matching pattern')

    def startTestRun(self, event):
        MockAndMonkeyLayer.testing_mode = True
        ConfigLayer.enable_stderr()

    def getTestCaseNames(self, event):
        if len(self.patterns) == 0:
            # No filter patterns, so everything should be tested.
            return
        names = filter(event.isTestMethod, dir(event.testCase))
        for name in names:
            for pattern in self.patterns:
                if re.search(pattern, name):
                    break
            else:
                event.excludedNames.append(name)

    def handleFile(self, event):
        path = event.path[len(TOPDIR)+1:]
        if len(self.patterns) > 0:
            for pattern in self.patterns:
                if re.search(pattern, path):
                    break
            else:
                # Skip this doctest.
                return
        base, ext = os.path.splitext(path)
        if ext != '.rst':
            return
        # Look to see if the package defines a test layer, otherwise use the
        # default layer.  First turn the file system path into a dotted Python
        # module path.
        parent = os.path.dirname(path)
        dotted = 'mailman.' + DOT.join(parent.split(os.path.sep))
        try:
            module = importlib.import_module(dotted)
        except ImportError:
            layer = SMTPLayer
        else:
            layer = getattr(module, 'layer', SMTPLayer)
        test = doctest.DocFileTest(
            path, package='mailman',
            optionflags=FLAGS,
            setUp=setup,
            tearDown=teardown)
        test.layer = layer
        # Suppress the extra "Doctest: ..." line.
        test.shortDescription = lambda: None
        event.extraTests.append(test)
