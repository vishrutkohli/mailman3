============
Registration
============

When a user wants to join a mailing list, they must register and verify their
email address.  Then depending on how the mailing list is configured, they may
need to confirm their subscription and have it approved by the list
moderator.  The ``IRegistrar`` interface manages this work flow.

    >>> from mailman.interfaces.registrar import IRegistrar

Registrars adapt mailing lists.

    >>> from mailman.interfaces.mailinglist import SubscriptionPolicy
    >>> mlist = create_list('ant@example.com')
    >>> mlist.send_welcome_message = False
    >>> mlist.subscription_policy = SubscriptionPolicy.open
    >>> registrar = IRegistrar(mlist)

Usually, addresses are registered, but users with preferred addresses can be
registered too.

    >>> from mailman.interfaces.usermanager import IUserManager
    >>> from zope.component import getUtility
    >>> anne = getUtility(IUserManager).create_address(
    ...     'anne@example.com', 'Anne Person')


Register an email address
=========================

When the registration steps involve confirmation or moderator approval, the
process will pause until these steps are completed.  A unique token is created
which represents this work flow.

Anne attempts to join the mailing list.

    >>> token, token_owner, member = registrar.register(anne)

Because her email address has not yet been verified, she has not yet become a
member of the mailing list.

    >>> print(member)
    None
    >>> print(mlist.members.get_member('anne@example.com'))
    None

Once she verifies her email address, she will become a member of the mailing
list.  In this case, verifying implies that she also confirms her wish to join
the mailing list.

    >>> token, token_owner, member = registrar.confirm(token)
    >>> member
    <Member: Anne Person <anne@example.com> on ant@example.com
        as MemberRole.member>
    >>> mlist.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com> on ant@example.com
        as MemberRole.member>


Register a user
===============

Users can also register, but they must have a preferred address.  The mailing
list will deliver messages to this preferred address.

    >>> bart = getUtility(IUserManager).make_user(
    ...     'bart@example.com', 'Bart Person')

Bart verifies his address and makes it his preferred address.

    >>> from mailman.utilities.datetime import now
    >>> preferred = list(bart.addresses)[0]
    >>> preferred.verified_on = now()
    >>> bart.preferred_address = preferred

The mailing list's subscription policy does not require Bart to confirm his
subscription, but the moderate does want to approve all subscriptions.

    >>> mlist.subscription_policy = SubscriptionPolicy.moderate

Now when Bart registers as a user for the mailing list, a token will still be
generated, but this is only used by the moderator.  At first, Bart is not
subscribed to the mailing list.

    >>> token, token_owner, member = registrar.register(bart)
    >>> print(member)
    None
    >>> print(mlist.members.get_member('bart@example.com'))
    None

When the moderator confirms Bart's subscription, he joins the mailing list.

    >>> token, token_owner, member = registrar.confirm(token)
    >>> member
    <Member: Bart Person <bart@example.com> on ant@example.com
        as MemberRole.member>
    >>> mlist.members.get_member('bart@example.com')
    <Member: Bart Person <bart@example.com> on ant@example.com
        as MemberRole.member>
