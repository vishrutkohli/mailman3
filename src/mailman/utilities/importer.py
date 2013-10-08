# Copyright (C) 2010-2013 by the Free Software Foundation, Inc.
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

"""Importer routines."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'import_config_pck',
    ]


import sys
import datetime
import os
from urllib2 import URLError

from mailman.config import config
from mailman.interfaces.action import FilterAction, Action
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.digests import DigestFrequency
from mailman.interfaces.mailinglist import Personalization, ReplyToMunging
from mailman.interfaces.nntp import NewsgroupModeration
from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.mailinglist import IAcceptableAliasSet
from mailman.interfaces.bounce import UnrecognizedBounceDisposition
from mailman.interfaces.usermanager import IUserManager
from mailman.interfaces.member import DeliveryMode, DeliveryStatus, MemberRole
from mailman.handlers.decorate import decorate, decorate_template
from mailman.utilities.i18n import search
from zope.component import getUtility



def seconds_to_delta(value):
    return datetime.timedelta(seconds=value)


def days_to_delta(value):
    return datetime.timedelta(days=value)


def list_members_to_unicode(value):
    return [ unicode(item) for item in value ]


def filter_action_mapping(value):
    # The filter_action enum values have changed. In Mailman 2.1 the order was
    # 'Discard', 'Reject', 'Forward to List Owner', 'Preserve'.
    # In 3.0 it's 'hold', 'reject', 'discard', 'accept', 'defer', 'forward',
    # 'preserve'
    if value == 0:
        return FilterAction.discard
    elif value == 1:
        return FilterAction.reject
    elif value == 2:
        return FilterAction.forward
    elif value == 3:
        return FilterAction.preserve
    else:
        raise ValueError("Unknown filter_action value: %s" % value)


def member_action_mapping(value):
    # The mlist.default_member_action and mlist.default_nonmember_action enum
    # values are different in Mailman 2.1, because they have been merged into a
    # single enum in Mailman 3
    # For default_member_action, which used to be called
    # member_moderation_action, the values were:
    # 0==Hold, 1=Reject, 2==Discard
    if value == 0:
        return Action.hold
    elif value == 1:
        return Action.reject
    elif value == 2:
        return Action.discard
def nonmember_action_mapping(value):
    # For default_nonmember_action, which used to be called
    # generic_nonmember_action, the values were:
    # 0==Accept, 1==Hold, 2==Reject, 3==Discard
    if value == 0:
        return Action.accept
    elif value == 1:
        return Action.hold
    elif value == 2:
        return Action.reject
    elif value == 3:
        return Action.discard


def unicode_to_string(value):
    return str(value) if value is not None else None


# Attributes in Mailman 2 which have a different type in Mailman 3.
TYPES = dict(
    autorespond_owner=ResponseAction,
    autorespond_postings=ResponseAction,
    autorespond_requests=ResponseAction,
    autoresponse_grace_period=days_to_delta,
    bounce_info_stale_after=seconds_to_delta,
    bounce_you_are_disabled_warnings_interval=seconds_to_delta,
    digest_volume_frequency=DigestFrequency,
    filter_action=filter_action_mapping,
    newsgroup_moderation=NewsgroupModeration,
    personalize=Personalization,
    reply_goes_to_list=ReplyToMunging,
    filter_types=list_members_to_unicode,
    pass_types=list_members_to_unicode,
    filter_extensions=list_members_to_unicode,
    pass_extensions=list_members_to_unicode,
    forward_unrecognized_bounces_to=UnrecognizedBounceDisposition,
    default_member_action=member_action_mapping,
    default_nonmember_action=nonmember_action_mapping,
    moderator_password=unicode_to_string,
    )


# Attribute names in Mailman 2 which are renamed in Mailman 3.
NAME_MAPPINGS = dict(
    host_name='mail_host',
    include_list_post_header='allow_list_posts',
    real_name='display_name',
    last_post_time='last_post_at',
    autoresponse_graceperiod='autoresponse_grace_period',
    autorespond_admin='autorespond_owner',
    autoresponse_admin_text='autoresponse_owner_text',
    filter_mime_types='filter_types',
    pass_mime_types='pass_types',
    filter_filename_extensions='filter_extensions',
    pass_filename_extensions='pass_extensions',
    bounce_processing='process_bounces',
    bounce_unrecognized_goes_to_list_owner='forward_unrecognized_bounces_to',
    mod_password='moderator_password',
    news_moderation='newsgroup_moderation',
    news_prefix_subject_too='nntp_prefix_subject_too',
    send_welcome_msg='send_welcome_message',
    send_goodbye_msg='send_goodbye_message',
    member_moderation_action='default_member_action',
    generic_nonmember_action='default_nonmember_action',
    )

EXCLUDES = (
    "members",
    "digest_members",
    )



def import_config_pck(mlist, config_dict):
    """Apply a config.pck configuration dictionary to a mailing list.

    :param mlist: The mailing list.
    :type mlist: IMailingList
    :param config_dict: The Mailman 2.1 configuration dictionary.
    :type config_dict: dict
    """
    for key, value in config_dict.items():
        # Some attributes must not be directly imported
        if key in EXCLUDES:
            continue
        # Some attributes from Mailman 2 were renamed in Mailman 3.
        key = NAME_MAPPINGS.get(key, key)
        # Handle the simple case where the key is an attribute of the
        # IMailingList and the types are the same (modulo 8-bit/unicode
        # strings).
        if hasattr(mlist, key):
            if isinstance(value, str):
                for encoding in ("ascii", "utf-8"):
                    try:
                        value = unicode(value, encoding)
                    except UnicodeDecodeError, e:
                        continue
                    else:
                        break
                if isinstance(value, str): # we did our best
                    value = unicode(value, 'ascii', 'replace')
            # Some types require conversion.
            converter = TYPES.get(key)
            if converter is not None:
                value = converter(value)
            try:
                setattr(mlist, key, value)
            except TypeError:
                print('Type conversion error:', key, file=sys.stderr)
                raise
    # Handle the archiving policy
    if config_dict.get("archive"):
        if config_dict.get("archive_private"):
            mlist.archive_policy = ArchivePolicy.private
        else:
            mlist.archive_policy = ArchivePolicy.public
    else:
        mlist.archive_policy = ArchivePolicy.never
    # Handle ban list
    for addr in config_dict.get('ban_list', []):
        IBanManager(mlist).ban(unicode(addr))
    # Handle acceptable aliases
    for addr in config_dict.get('acceptable_aliases', '').splitlines():
        addr = addr.strip()
        if not addr:
            continue
        IAcceptableAliasSet(mlist).add(unicode(addr))
    # Handle conversion to URIs
    convert_to_uri = {
        "welcome_msg": "welcome_message_uri",
        "goodbye_msg": "goodbye_message_uri",
        "msg_header": "header_uri",
        "msg_footer": "footer_uri",
        "digest_header": "digest_header_uri",
        "digest_footer": "digest_footer_uri",
        }
    convert_placeholders = { # only the most common ones
        "%(real_name)s": "$display_name",
        "%(real_name)s@%(host_name)s": "$fqdn_listname",
        "%(web_page_url)slistinfo%(cgiext)s/%(_internal_name)s": "$listinfo_uri",
    }
    # Collect defaults
    defaults = {}
    for oldvar, newvar in convert_to_uri.iteritems():
        default_value = getattr(mlist, newvar)
        if not default_value:
            continue
        # Check if the value changed from the default
        try:
            default_text = decorate(mlist, default_value)
        except (URLError, KeyError):
            # Use case: importing the old a@ex.com into b@ex.com
            # We can't check if it changed from the default
            # -> don't import, we may do more harm than good and it's easy to
            # change if needed
            continue
        defaults[newvar] = (default_value, default_text)
    for oldvar, newvar in convert_to_uri.iteritems():
        if oldvar not in config_dict:
            continue
        text = config_dict[oldvar]
        text = unicode(text, "utf-8", "replace")
        for oldph, newph in convert_placeholders.iteritems():
            text = text.replace(oldph, newph)
        default_value, default_text  = defaults.get(newvar, (None, None))
        if not text and not (default_value or default_text):
            continue # both are empty, leave it
        # Check if the value changed from the default
        try:
            expanded_text = decorate_template(mlist, text)
        except KeyError:
            # Use case: importing the old a@ex.com into b@ex.com
            # We can't check if it changed from the default
            # -> don't import, we may do more harm than good and it's easy to
            # change if needed
            continue
        if expanded_text and default_text \
                and expanded_text.strip() == default_text.strip():
            continue # keep the default
        # Write the custom value to the right file
        base_uri = "mailman:///$listname/$language/"
        if default_value:
            filename = default_value.rpartition("/")[2]
        else:
            filename = "%s.txt" % newvar[:-4]
        if not default_value or not default_value.startswith(base_uri):
            setattr(mlist, newvar, base_uri + filename)
        filepath = list(search(filename, mlist))[0]
        try:
            os.makedirs(os.path.dirname(filepath))
        except OSError, e:
            if e.errno != 17: # Already exists
                raise
        with open(filepath, "w") as template:
            template.write(text.encode('utf-8'))
    # Import rosters
    members = set(config_dict.get("members", {}).keys()
                + config_dict.get("digest_members", {}).keys())
    import_roster(mlist, config_dict, members, MemberRole.member)
    import_roster(mlist, config_dict, config_dict.get("owner", []),
                  MemberRole.owner)
    import_roster(mlist, config_dict, config_dict.get("moderator", []),
                  MemberRole.moderator)



def import_roster(mlist, config_dict, members, role):
    """
    Import members lists from a config.pck configuration dictionary to a
    mailing list.

    :param mlist: The mailing list.
    :type  mlist: IMailingList
    :param config_dict: The Mailman 2.1 configuration dictionary.
    :type  config_dict: dict
    :param members: The members list to import
    :type  members: list
    :param role: The MemberRole to import them as
    :type  role: MemberRole enum
    """
    usermanager = getUtility(IUserManager)
    for email in members:
        email = unicode(email)
        roster = mlist.get_roster(role)
        if roster.get_member(email) is not None:
            print("%s is already imported with role %s" % (email, role),
                  file=sys.stderr)
            continue
        user = usermanager.get_user(email)
        if user is None:
            merged_members = {}
            merged_members.update(config_dict.get("members", {}))
            merged_members.update(config_dict.get("digest_members", {}))
            if merged_members.get(email, 0) != 0:
                original_email = merged_members[email]
            else:
                original_email = email
            user = usermanager.create_user(unicode(original_email))
        address = usermanager.get_address(email)
        address.verified_on = datetime.datetime.now()
        mlist.subscribe(address, role)
        member = roster.get_member(email)
        assert member is not None
        prefs = config_dict.get("user_options", {}).get(email, 0)
        if email in config_dict.get("members", {}):
            member.preferences.delivery_mode = DeliveryMode.regular
        elif email in config_dict.get("digest_members", {}):
            if prefs & 8: # DisableMime
                member.preferences.delivery_mode = DeliveryMode.plaintext_digests
            else:
                member.preferences.delivery_mode = DeliveryMode.mime_digests
        else:
            # probably not adding a member role here
            pass
        if email in config_dict.get("language", {}):
            member.preferences.preferred_language = \
                unicode(config_dict["language"][email])
        # if the user already exists, display_name and password will be
        # overwritten
        if email in config_dict.get("usernames", {}):
            address.display_name = unicode(config_dict["usernames"][email])
            user.display_name    = unicode(config_dict["usernames"][email])
        if email in config_dict.get("passwords", {}):
            user.password = config.password_context.encrypt(
                                    config_dict["passwords"][email])
        # delivery_status
        oldds = config_dict.get("delivery_status", {}).get(email, (0, 0))[0]
        if oldds == 0:
            member.preferences.delivery_status = DeliveryStatus.enabled
        elif oldds == 1:
            member.preferences.delivery_status = DeliveryStatus.unknown
        elif oldds == 2:
            member.preferences.delivery_status = DeliveryStatus.by_user
        elif oldds == 3:
            member.preferences.delivery_status = DeliveryStatus.by_moderator
        elif oldds == 4:
            member.preferences.delivery_status = DeliveryStatus.by_bounces
        # moderation
        if prefs & 128:
            member.moderation_action = Action.hold
        # other preferences
        member.preferences.acknowledge_posts = bool(prefs & 4) # AcknowledgePosts
        member.preferences.hide_address = bool(prefs & 16) # ConcealSubscription
        member.preferences.receive_own_postings = not bool(prefs & 2) # DontReceiveOwnPosts
        member.preferences.receive_list_copy = not bool(prefs & 256) # DontReceiveDuplicates
