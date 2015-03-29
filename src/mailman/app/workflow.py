# Copyright (C) 2015 by the Free Software Foundation, Inc.
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

"""Generic workflow."""

__all__ = [
    'Workflow',
    ]


import json

from collections import deque
from mailman.interfaces.workflow import IWorkflowStateManager
from zope.component import getUtility



class Workflow:
    """Generic workflow."""

    _save_key = ''
    _save_attributes = []
    _initial_state = []

    def __init__(self):
        self._next = deque(self._initial_state)

    def __iter__(self):
        return self

    def _pop(self):
        name = self._next.popleft()
        step = getattr(self, '_step_{}'.format(name))
        return step, name

    def __next__(self):
        try:
            step, name = self._pop()
            step()
        except IndexError:
            raise StopIteration
        except:
            raise

    def save_state(self):
        state_manager = getUtility(IWorkflowStateManager)
        data = {attr: getattr(self, attr) for attr in self._save_attributes}
        # Note: only the next step is saved, not the whole stack. Not an issue
        # since there's never more than a single step in the queue anyway.
        # If we want to support more than a single step in the queue AND want
        # to support state saving/restoring, change this method and the
        # restore_state() method.
        if len(self._next) == 0:
            step = None
        elif len(self._next) == 1:
            step = self._next[0]
        else:
            raise AssertionError(
                "Can't save a workflow state with more than one step "
                "in the queue")
        state_manager.save(
            self.__class__.__name__,
            self._save_key,
            step,
            json.dumps(data))

    def restore_state(self):
        state_manager = getUtility(IWorkflowStateManager)
        state = state_manager.restore(self.__class__.__name__, self._save_key)
        if state is not None:
            self._next.clear()
            if state.step:
                self._next.append(state.step)
            if state.data is not None:
                for attr, value in json.loads(state.data).items():
                    setattr(self, attr, value)
