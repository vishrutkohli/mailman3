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

"""Interface describing the state of a workflow."""

__all__ = [
    'IWorkflowState',
    'IWorkflowStateManager',
    ]


from zope.interface import Interface, Attribute



class IWorkflowState(Interface):
    """The state of a workflow."""

    name = Attribute(
        """The name of the workflow.""")

    key = Attribute(
        """A unique key identifying the workflow instance.""")

    step = Attribute(
        """This workflow's next step.""")

    data = Attribute(
        """Additional data (may be JSON-encodedeJSON .""")



class IWorkflowStateManager(Interface):
    """The workflow states manager."""

    def save(name, key, step, data=None):
        """Save the state of a workflow

        :param name: The name of the workflow.
        :type name: str
        :param key: A unique key identifying this workflow instance.
        :type key: str
        :param step: The next step for this workflow.
        :type step: str
        :param data: Additional data (workflow-specific).
        :type data: str
        """

    def restore(name, key):
        """Get the saved state for a workflow or None if nothing was saved.

        :param name: The name of the workflow.
        :type name: str
        :param key: A unique key identifying this workflow instance.
        :type key: str
        """
