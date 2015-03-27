# Copyright (C) 2007-2015 by the Free Software Foundation, Inc.
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

"""Model for workflow states."""

__all__ = [
    'WorkflowState',
    'WorkflowStateManager',
    ]


from mailman.database.model import Model
from mailman.database.transaction import dbconnection
from mailman.interfaces.workflowstate import (
    IWorkflowState, IWorkflowStateManager)
from sqlalchemy import Column, Unicode
from zope.interface import implementer



@implementer(IWorkflowState)
class WorkflowState(Model):
    """Workflow states."""

    __tablename__ = 'workflowstate'

    name = Column(Unicode, primary_key=True)
    key = Column(Unicode, primary_key=True)
    step = Column(Unicode)
    data = Column(Unicode)



@implementer(IWorkflowStateManager)
class WorkflowStateManager:
    """See `IWorkflowStateManager`."""

    @dbconnection
    def save(self, store, name, key, step=None, data=None):
        """See `IWorkflowStateManager`."""
        state = store.query(WorkflowState).get((name, key))
        if state is None:
            state = store.add(WorkflowState(
                name=name, key=key, step=step, data=data))
        else:
            state.step = step
            state.data = data

    @dbconnection
    def restore(self, store, name, key):
        """See `IWorkflowStateManager`."""
        return store.query(WorkflowState).get((name, key))
