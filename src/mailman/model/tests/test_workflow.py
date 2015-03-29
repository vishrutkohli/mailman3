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

"""Test the workflow model."""

__all__ = [
    'TestWorkflow',
    ]


import unittest

from mailman.interfaces.workflow import IWorkflowStateManager
from mailman.testing.layers import ConfigLayer
from zope.component import getUtility



class TestWorkflow(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._manager = getUtility(IWorkflowStateManager)

    def test_save_restore_workflow(self):
        # Save and restore a workflow.
        name = 'ant'
        key = 'bee'
        step = 'cat'
        data = 'dog'
        self._manager.save(name, key, step, data)
        workflow = self._manager.restore(name, key)
        self.assertEqual(workflow.name, name)
        self.assertEqual(workflow.key, key)
        self.assertEqual(workflow.step, step)
        self.assertEqual(workflow.data, data)

    def test_save_restore_workflow_without_step(self):
        # Save and restore a workflow that contains no step.
        name = 'ant'
        key = 'bee'
        data = 'dog'
        self._manager.save(name, key, data=data)
        workflow = self._manager.restore(name, key)
        self.assertEqual(workflow.name, name)
        self.assertEqual(workflow.key, key)
        self.assertIsNone(workflow.step)
        self.assertEqual(workflow.data, data)

    def test_save_restore_workflow_without_data(self):
        # Save and restore a workflow that contains no data.
        name = 'ant'
        key = 'bee'
        step = 'cat'
        self._manager.save(name, key, step)
        workflow = self._manager.restore(name, key)
        self.assertEqual(workflow.name, name)
        self.assertEqual(workflow.key, key)
        self.assertEqual(workflow.step, step)
        self.assertIsNone(workflow.data)

    def test_save_restore_workflow_without_step_or_data(self):
        # Save and restore a workflow that contains no step or data.
        name = 'ant'
        key = 'bee'
        self._manager.save(name, key)
        workflow = self._manager.restore(name, key)
        self.assertEqual(workflow.name, name)
        self.assertEqual(workflow.key, key)
        self.assertIsNone(workflow.step)
        self.assertIsNone(workflow.data)

    def test_restore_workflow_with_no_matching_name(self):
        # Try to restore a workflow that has no matching name in the database.
        name = 'ant'
        key = 'bee'
        self._manager.save(name, key)
        workflow = self._manager.restore('ewe', key)
        self.assertIsNone(workflow)

    def test_restore_workflow_with_no_matching_key(self):
        # Try to restore a workflow that has no matching key in the database.
        name = 'ant'
        key = 'bee'
        self._manager.save(name, key)
        workflow = self._manager.restore(name, 'fly')
        self.assertIsNone(workflow)

    def test_restore_workflow_with_no_matching_key_or_name(self):
        # Try to restore a workflow that has no matching key or name in the
        # database.
        name = 'ant'
        key = 'bee'
        self._manager.save(name, key)
        workflow = self._manager.restore('ewe', 'fly')
        self.assertIsNone(workflow)
