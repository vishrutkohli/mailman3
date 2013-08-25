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
import mailman

from mailman.testing.layers import ConfigLayer, MockAndMonkeyLayer
from nose2.events import Plugin


TOPDIR = os.path.dirname(mailman.__file__)


class NosePlugin(Plugin):
    configSection = 'mailman'

    def __init__(self):
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
