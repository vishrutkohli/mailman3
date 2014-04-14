# Copyright (C) 2007-2014 by the Free Software Foundation, Inc.
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

"""Implementation of the IUserRegistrar interface."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Registrar',
    'handle_ConfirmationNeededEvent',
    ]


import logging

from zope.component import getUtility
from zope.event import notify
from zope.interface import implementer

from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.address import IEmailValidator
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import DeliveryMode, MemberRole
from mailman.interfaces.pending import IPendable, IPendings
from mailman.interfaces.registrar import ConfirmationNeededEvent, IRegistrar
from mailman.interfaces.templates import ITemplateLoader
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.datetime import now


log = logging.getLogger('mailman.error')



@implementer(IPendable)
class PendableRegistration(dict):
    PEND_KEY = 'registration'



@implementer(IRegistrar)
class Registrar:
    """Handle registrations and confirmations for subscriptions."""

    def register(self, mlist, email, display_name=None, delivery_mode=None):
        """See `IUserRegistrar`."""
        if delivery_mode is None:
            delivery_mode = DeliveryMode.regular
        # First, do validation on the email address.  If the address is
        # invalid, it will raise an exception, otherwise it just returns.
        getUtility(IEmailValidator).validate(email)
        # Create a pendable for the registration.
        pendable = PendableRegistration(
            type=PendableRegistration.PEND_KEY,
            email=email,
            display_name=display_name,
            delivery_mode=delivery_mode.name,
            list_id=mlist.list_id)
        token = getUtility(IPendings).add(pendable)
        # We now have everything we need to begin the confirmation dance.
        # Trigger the event to start the ball rolling, and return the
        # generated token.
        notify(ConfirmationNeededEvent(mlist, pendable, token))
        return token

    def confirm(self, token):
        """See `IUserRegistrar`."""
        # For convenience
        pendable = getUtility(IPendings).confirm(token)
        if pendable is None:
            return False
        missing = object()
        email = pendable.get('email', missing)
        display_name = pendable.get('display_name', missing)
        pended_delivery_mode = pendable.get('delivery_mode', 'regular')
        try:
            delivery_mode = DeliveryMode[pended_delivery_mode]
        except ValueError:
            log.error('Invalid pended delivery_mode for {0}: {1}',
                      email, pended_delivery_mode)
            delivery_mode = DeliveryMode.regular
        if pendable.get('type') != PendableRegistration.PEND_KEY:
            # It seems like it would be very difficult to accurately guess
            # tokens, or brute force an attack on the SHA1 hash, so we'll just
            # throw the pendable away in that case.  It's possible we'll need
            # to repend the event or adjust the API to handle this case
            # better, but for now, the simpler the better.
            return False
        # We are going to end up with an IAddress for the verified address
        # and an IUser linked to this IAddress.  See if any of these objects
        # currently exist in our database.
        user_manager = getUtility(IUserManager)
        address = (user_manager.get_address(email)
                   if email is not missing else None)
        user = (user_manager.get_user(email)
                if email is not missing else None)
        # If there is neither an address nor a user matching the confirmed
        # record, then create the user, which will in turn create the address
        # and link the two together
        if address is None:
            assert user is None, 'How did we get a user but not an address?'
            user = user_manager.create_user(email, display_name)
            # Because the database changes haven't been flushed, we can't use
            # IUserManager.get_address() to find the IAddress just created
            # under the hood.  Instead, iterate through the IUser's addresses,
            # of which really there should be only one.
            for address in user.addresses:
                if address.email == email:
                    break
            else:
                raise AssertionError('Could not find expected IAddress')
        elif user is None:
            user = user_manager.create_user()
            user.display_name = display_name
            user.link(address)
        else:
            # The IAddress and linked IUser already exist, so all we need to
            # do is verify the address.
            pass
        address.verified_on = now()
        # If this registration is tied to a mailing list, subscribe the person
        # to the list right now.  That will generate a SubscriptionEvent,
        # which can be used to send a welcome message.
        list_id = pendable.get('list_id')
        if list_id is not None:
            mlist = getUtility(IListManager).get_by_list_id(list_id)
            if mlist is not None:
                member = mlist.subscribe(address, MemberRole.member)
                member.preferences.delivery_mode = delivery_mode
        return True

    def discard(self, token):
        # Throw the record away.
        getUtility(IPendings).confirm(token)



def handle_ConfirmationNeededEvent(event):
    if not isinstance(event, ConfirmationNeededEvent):
        return
    # There are three ways for a user to confirm their subscription.  They
    # can reply to the original message and let the VERP'd return address
    # encode the token, they can reply to the robot and keep the token in
    # the Subject header, or they can click on the URL in the body of the
    # message and confirm through the web.
    subject = 'confirm ' + event.token
    mlist = getUtility(IListManager).get_by_list_id(event.pendable['list_id'])
    confirm_address = mlist.confirm_address(event.token)
    # For i18n interpolation.
    confirm_url = mlist.domain.confirm_url(event.token)
    email_address = event.pendable['email']
    domain_name = mlist.domain.mail_host
    contact_address = mlist.domain.contact_address
    # Send a verification email to the address.
    template = getUtility(ITemplateLoader).get(
        'mailman:///{0}/{1}/confirm.txt'.format(
            mlist.fqdn_listname,
            mlist.preferred_language.code))
    text = _(template)
    msg = UserNotification(email_address, confirm_address, subject, text)
    msg.send(mlist)
