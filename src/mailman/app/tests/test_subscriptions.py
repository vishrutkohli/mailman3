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

"""Tests for the subscription service."""

__all__ = [
    'TestJoin',
    'TestSubscriptionWorkflow',
    ]


import uuid
import unittest

from mailman.app.lifecycle import create_list
from mailman.app.subscriptions import Workflow, SubscriptionWorkflow
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.member import MemberRole, MissingPreferredAddressError
from mailman.interfaces.requests import IListRequests, RequestType
from mailman.interfaces.subscriptions import (
    MissingUserError, ISubscriptionService)
from mailman.testing.layers import ConfigLayer
from mailman.interfaces.mailinglist import SubscriptionPolicy
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.datetime import now
from mock import Mock
from zope.component import getUtility



class TestJoin(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._service = getUtility(ISubscriptionService)

    def test_join_user_with_bogus_id(self):
        # When `subscriber` is a missing user id, an exception is raised.
        with self.assertRaises(MissingUserError) as cm:
            self._service.join('test.example.com', uuid.UUID(int=99))
        self.assertEqual(cm.exception.user_id, uuid.UUID(int=99))

    def test_join_user_with_invalid_email_address(self):
        # When `subscriber` is a string that is not an email address, an
        # exception is raised.
        with self.assertRaises(InvalidEmailAddressError) as cm:
            self._service.join('test.example.com', 'bogus')
        self.assertEqual(cm.exception.email, 'bogus')

    def test_missing_preferred_address(self):
        # A user cannot join a mailing list if they have no preferred address.
        anne = self._service.join(
            'test.example.com', 'anne@example.com', 'Anne Person')
        # Try to join Anne as a user with a different role.  Her user has no
        # preferred address, so this will fail.
        self.assertRaises(MissingPreferredAddressError,
                          self._service.join,
                          'test.example.com', anne.user.user_id,
                          role=MemberRole.owner)



class TestWorkflow(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self.workflow = Workflow()
        self.workflow._test_attribute = "test-value"
        self.workflow._step_test = Mock()
        self.workflow._next.append("test")

    def test_iter_steps(self):
        next(self.workflow)
        self.assertTrue(self.workflow._step_test.called)
        self.assertEqual(len(self.workflow._next), 0)
        try:
            next(self.workflow)
        except StopIteration:
            pass
        else:
            self.fail()

    def test_save_restore(self):
        self.workflow.save_state()
        # Now create a new instance and restore
        new_workflow = Workflow()
        self.assertEqual(len(new_workflow._next), 0)
        self.assertFalse(hasattr(new_workflow, "_test_attribute"))
        new_workflow.restore_state()
        self.assertEqual(len(new_workflow._next), 1)
        self.assertEqual(new_workflow._next[0], "test")
        self.assertEqual(self.workflow._test_attribute, "test-value")

    def test_save_restore_no_next_step(self):
        self.workflow._next.clear()
        self.workflow.save_state()
        # Now create a new instance and restore
        new_workflow = Workflow()
        new_workflow._next.append("test")
        new_workflow.restore_state()
        self.assertEqual(len(new_workflow._next), 0)



class TestSubscriptionWorkflow(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._anne = 'anne@example.com'
        self._user_manager = getUtility(IUserManager)

    def test_preverified_address_joins_open_list(self):
        # The mailing list has an open subscription policy, so the subscriber
        # becomes a member with no human intervention.
        self._mlist.subscription_policy = SubscriptionPolicy.open
        anne = self._user_manager.create_address(self._anne, 'Anne Person')
        self.assertIsNone(anne.verified_on)
        self.assertIsNone(anne.user)
        self.assertIsNone(self._mlist.subscribers.get_member(self._anne))
        workflow = SubscriptionWorkflow(
            self._mlist, anne,
            pre_verified=True, pre_confirmed=False, pre_approved=False)
        # Run the state machine to the end.  The result is that her address
        # will be verified, linked to a user, and subscribed to the mailing
        # list.
        list(workflow)
        self.assertIsNotNone(anne.verified_on)
        self.assertIsNotNone(anne.user)
        self.assertIsNotNone(self._mlist.subscribers.get_member(self._anne))

    def test_verified_address_joins_moderated_list(self):
        # The mailing list is moderated but the subscriber is not a verified
        # address and the subscription request is not pre-verified.
        # A confirmation email must be sent, it will serve as the verification
        # email too.
        anne = self._user_manager.create_address(self._anne, 'Anne Person')
        request_db = IListRequests(self._mlist)
        def _do_check():
            anne.verified_on = now()
            self.assertIsNone(self._mlist.subscribers.get_member(self._anne))
            workflow = SubscriptionWorkflow(
                self._mlist, anne,
                pre_verified=False, pre_confirmed=True, pre_approved=False)
            # Run the state machine to the end.
            list(workflow)
            # Look in the requests db
            requests = list(request_db.of_type(RequestType.subscription))
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0].key, anne.email)
            request_db.delete_request(requests[0].id)
        self._mlist.subscription_policy = SubscriptionPolicy.moderate
        _do_check()
        self._mlist.subscription_policy = \
            SubscriptionPolicy.confirm_then_moderate
        _do_check()

    def test_confirmation_required(self):
        # Tests subscriptions where user confirmation is required
        self._mlist.subscription_policy = \
            SubscriptionPolicy.confirm_then_moderate
        anne = self._user_manager.create_address(self._anne, 'Anne Person')
        self.assertIsNone(self._mlist.subscribers.get_member(self._anne))
        workflow = SubscriptionWorkflow(
            self._mlist, anne,
            pre_verified=True, pre_confirmed=False, pre_approved=True)
        # Run the state machine to the end.
        list(workflow)
        # A confirmation request must be pending
        # TODO: test it
        # Now restore and re-run the state machine as if we got the confirmation
        workflow.restore_state()
        list(workflow)
        self.assertIsNotNone(self._mlist.subscribers.get_member(self._anne))
