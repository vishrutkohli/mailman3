# Copyright (C) 2009-2015 by the Free Software Foundation, Inc.
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

"""Handle subscriptions."""

__all__ = [
    'SubscriptionService',
    'SubscriptionWorkflow',
    'handle_ListDeletingEvent',
    ]


from collections import deque
from operator import attrgetter
from sqlalchemy import and_, or_
from uuid import UUID
from zope.component import getUtility
from zope.interface import implementer

from mailman.app.membership import add_member, delete_member
from mailman.app.moderator import hold_subscription
from mailman.core.constants import system_preferences
from mailman.database.transaction import dbconnection
from mailman.interfaces.address import IAddress
from mailman.interfaces.listmanager import (
    IListManager, ListDeletingEvent, NoSuchListError)
from mailman.interfaces.mailinglist import SubscriptionPolicy
from mailman.interfaces.member import DeliveryMode, MemberRole
from mailman.interfaces.subscriptions import (
    ISubscriptionService, MissingUserError, RequestRecord)
from mailman.interfaces.user import IUser
from mailman.interfaces.usermanager import IUserManager
from mailman.model.member import Member
from mailman.utilities.datetime import now


def _membership_sort_key(member):
    """Sort function for find_members().

    The members are sorted first by unique list id, then by subscribed email
    address, then by role.
    """
    return (member.list_id, member.address.email, member.role.value)


class SubscriptionWorkflow:
    """Workflow of a subscription request."""

    def __init__(self, mlist, subscriber,
                 pre_verified, pre_confirmed, pre_approved):
        self.mlist = mlist
        # The subscriber must be either an IUser or IAddress.
        if IAddress.providedBy(subscriber):
            self.address = subscriber
            self.user = self.address.user
        elif IUser.providedBy(subscriber):
            self.address = subscriber.preferred_address
            self.user = subscriber
        self.subscriber = subscriber
        self.pre_verified = pre_verified
        self.pre_confirmed = pre_confirmed
        self.pre_approved = pre_approved
        # Prepare the state machine.
        self._next = deque()
        self._next.append(self._verification_check)

    def __iter__(self):
        return self

    def _pop(self):
        step = self._next.popleft()
        # step could be a partial or a method.
        name = getattr(step, 'func', step).__name__
        return step, name

    def __next__(self):
        try:
            step, name = self._pop()
            step()
        except IndexError:
            raise StopIteration
        except:
            raise

    def _maybe_set_preferred_address(self):
        if self.user is None:
            # The address has no linked user so create one, link it, and set
            # the user's preferred address.
            assert self.address is not None, 'No address or user'
            self.user = getUtility(IUserManager).make_user(self.address.email)
            self.user.preferred_address = self.address
        elif self.user.preferred_address is None:
            assert self.address is not None, 'No address or user'
            # The address has a linked user, but no preferred address is set
            # yet.  This is required, so use the address.
            self.user.preferred_address = self.address

    def _verification_check(self):
        if self.address.verified_on is not None:
            # The address is already verified.  Give the user a preferred
            # address if it doesn't already have one.  We may still have to do
            # a subscription confirmation check.  See below.
            self._maybe_set_preferred_address()
        else:
            # The address is not yet verified.  Maybe we're pre-verifying it.
            # If so, we also want to give the user a preferred address if it
            # doesn't already have one.  We may still have to do a
            # subscription confirmation check.  See below.
            if self.pre_verified:
                self.address.verified_on = now()
                self._maybe_set_preferred_address()
            else:
                # Since the address was not already verified, and not
                # pre-verified, we have to send a confirmation check, which
                # doubles as a verification step.  Skip to that now.
                self._next.append(self._send_confirmation)
                return
        self._next.append(self._confirmation_check)

    def _confirmation_check(self):
        # Must the user confirm their subscription request?  If the policy is
        # open subscriptions, then we need neither confirmation nor moderator
        # approval, so just subscribe them now.
        if self.mlist.subscription_policy == SubscriptionPolicy.open:
            self._next.append(self._do_subscription)
        elif self.pre_confirmed:
            # No confirmation is necessary.  We can skip to seeing whether a
            # moderator confirmation is necessary.
            self._next.append(self._moderation_check)
        else:
            self._next.append(self._send_confirmation)

    def _moderation_check(self):
        # Does the moderator need to approve the subscription request?
        if self.mlist.subscription_policy in (
                SubscriptionPolicy.moderate,
                SubscriptionPolicy.confirm_then_moderate):
            self._next.append(self._get_moderator_approval)
        else:
            # The moderator does not need to approve the subscription, so go
            # ahead and do that now.
            self._next.append(self._do_subscription)

    def _get_moderator_approval(self):
        # In order to get the moderator's approval, we need to hold the
        # subscription request in the database
        request = RequestRecord(
            self.address.email, self.subscriber.display_name,
            DeliveryMode.regular, 'en')
        hold_subscription(self.mlist, request)

    def _do_subscription(self):
        # We can immediately subscribe the user to the mailing list.
        self.mlist.subscribe(self.subscriber)


@implementer(ISubscriptionService)
class SubscriptionService:
    """Subscription services for the REST API."""

    __name__ = 'members'

    def get_members(self):
        """See `ISubscriptionService`."""
        # {list_id -> {role -> [members]}}
        by_list = {}
        user_manager = getUtility(IUserManager)
        for member in user_manager.members:
            by_role = by_list.setdefault(member.list_id, {})
            members = by_role.setdefault(member.role.name, [])
            members.append(member)
        # Flatten into single list sorted as per the interface.
        all_members = []
        address_of_member = attrgetter('address.email')
        for list_id in sorted(by_list):
            by_role = by_list[list_id]
            all_members.extend(
                sorted(by_role.get('owner', []), key=address_of_member))
            all_members.extend(
                sorted(by_role.get('moderator', []), key=address_of_member))
            all_members.extend(
                sorted(by_role.get('member', []), key=address_of_member))
        return all_members

    @dbconnection
    def get_member(self, store, member_id):
        """See `ISubscriptionService`."""
        members = store.query(Member).filter(Member._member_id == member_id)
        if members.count() == 0:
            return None
        else:
            assert members.count() == 1, 'Too many matching members'
            return members[0]

    @dbconnection
    def find_members(self, store, subscriber=None, list_id=None, role=None):
        """See `ISubscriptionService`."""
        # If `subscriber` is a user id, then we'll search for all addresses
        # which are controlled by the user, otherwise we'll just search for
        # the given address.
        user_manager = getUtility(IUserManager)
        if subscriber is None and list_id is None and role is None:
            return []
        # Querying for the subscriber is the most complicated part, because
        # the parameter can either be an email address or a user id.
        query = []
        if subscriber is not None:
            if isinstance(subscriber, str):
                # subscriber is an email address.
                address = user_manager.get_address(subscriber)
                user = user_manager.get_user(subscriber)
                # This probably could be made more efficient.
                if address is None or user is None:
                    return []
                query.append(or_(Member.address_id == address.id,
                                 Member.user_id == user.id))
            else:
                # subscriber is a user id.
                user = user_manager.get_user_by_id(subscriber)
                address_ids = list(address.id for address in user.addresses
                                   if address.id is not None)
                if len(address_ids) == 0 or user is None:
                    return []
                query.append(or_(Member.user_id == user.id,
                                 Member.address_id.in_(address_ids)))
        # Calculate the rest of the query expression, which will get And'd
        # with the Or clause above (if there is one).
        if list_id is not None:
            query.append(Member.list_id == list_id)
        if role is not None:
            query.append(Member.role == role)
        results = store.query(Member).filter(and_(*query))
        return sorted(results, key=_membership_sort_key)

    def __iter__(self):
        for member in self.get_members():
            yield member

    def join(self, list_id, subscriber,
             display_name=None,
             delivery_mode=DeliveryMode.regular,
             role=MemberRole.member):
        """See `ISubscriptionService`."""
        mlist = getUtility(IListManager).get_by_list_id(list_id)
        if mlist is None:
            raise NoSuchListError(list_id)
        # Is the subscriber an email address or user id?
        if isinstance(subscriber, str):
            if display_name is None:
                display_name, at, domain = subscriber.partition('@')
            return add_member(
                mlist,
                RequestRecord(subscriber, display_name, delivery_mode,
                              system_preferences.preferred_language),
                role)
        else:
            # We have to assume it's a UUID.
            assert isinstance(subscriber, UUID), 'Not a UUID'
            user = getUtility(IUserManager).get_user_by_id(subscriber)
            if user is None:
                raise MissingUserError(subscriber)
            return mlist.subscribe(user, role)

    def leave(self, list_id, email):
        """See `ISubscriptionService`."""
        mlist = getUtility(IListManager).get_by_list_id(list_id)
        if mlist is None:
            raise NoSuchListError(list_id)
        # XXX for now, no notification or user acknowledgment.
        delete_member(mlist, email, False, False)


def handle_ListDeletingEvent(event):
    """Delete a mailing list's members when the list is being deleted."""

    if not isinstance(event, ListDeletingEvent):
        return
    # Find all the members still associated with the mailing list.
    members = getUtility(ISubscriptionService).find_members(
        list_id=event.mailing_list.list_id)
    for member in members:
        member.unsubscribe()
