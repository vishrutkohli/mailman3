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

"""Tests for config.pck imports."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestBasicImport',
    ]


import cPickle
import unittest
from datetime import timedelta, datetime
from traceback import format_exc

from mailman.app.lifecycle import create_list, remove_list
from mailman.testing.layers import ConfigLayer
from mailman.utilities.importer import import_config_pck, Import21Error
from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.action import Action, FilterAction
from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.bounce import UnrecognizedBounceDisposition
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.mailinglist import IAcceptableAliasSet
from mailman.interfaces.nntp import NewsgroupModeration
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.templates import ITemplateLoader
from mailman.interfaces.usermanager import IUserManager
from mailman.interfaces.member import DeliveryMode, DeliveryStatus, MemberRole
from mailman.interfaces.languages import ILanguageManager
from mailman.model.address import Address
from mailman.handlers.decorate import decorate
from mailman.utilities.string import expand
from pkg_resources import resource_filename
from enum import Enum
from zope.component import getUtility
from storm.locals import Store



class DummyEnum(Enum):
    # For testing purposes
    val = 42


class TestBasicImport(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        pickle_file = resource_filename('mailman.testing', 'config.pck')
        with open(pickle_file) as fp:
            self._pckdict = cPickle.load(fp)

    def tearDown(self):
        remove_list(self._mlist)

    def _import(self):
        import_config_pck(self._mlist, self._pckdict)

    def test_display_name(self):
        # The mlist.display_name gets set from the old list's real_name.
        self.assertEqual(self._mlist.display_name, 'Blank')
        self._import()
        self.assertEqual(self._mlist.display_name, 'Test')

    def test_mail_host_invariant(self):
        # The mlist.mail_host must not be updated when importing (it will
        # change the list_id property, which is supposed to be read-only)
        self.assertEqual(self._mlist.mail_host, 'example.com')
        self._import()
        self.assertEqual(self._mlist.mail_host, 'example.com')

    def test_rfc2369_headers(self):
        self._mlist.allow_list_posts = False
        self._mlist.include_rfc2369_headers = False
        self._import()
        self.assertTrue(self._mlist.allow_list_posts)
        self.assertTrue(self._mlist.include_rfc2369_headers)

    def test_no_overwrite_rosters(self):
        # The mlist.members and mlist.digest_members rosters must not be
        # overwritten.
        for rname in ("members", "digest_members"):
            roster = getattr(self._mlist, rname)
            self.assertFalse(isinstance(roster, dict))
            self._import()
            self.assertFalse(isinstance(roster, dict),
                "The %s roster has been overwritten by the import" % rname)

    def test_last_post_time(self):
        # last_post_time -> last_post_at
        self._pckdict["last_post_time"] = 1270420800.274485
        self.assertEqual(self._mlist.last_post_at, None)
        self._import()
        # convert 1270420800.2744851 to datetime
        expected = datetime(2010, 4, 4, 22, 40, 0, 274485)
        self.assertEqual(self._mlist.last_post_at, expected)

    def test_autoresponse_grace_period(self):
        # autoresponse_graceperiod -> autoresponse_grace_period
        # must be a timedelta, not an int
        self._mlist.autoresponse_grace_period = timedelta(days=42)
        self._import()
        self.assertTrue(isinstance(
                self._mlist.autoresponse_grace_period, timedelta))
        self.assertEqual(self._mlist.autoresponse_grace_period,
                         timedelta(days=90))

    def test_autoresponse_admin_to_owner(self):
        # admin -> owner
        self._mlist.autorespond_owner = DummyEnum.val
        self._mlist.autoresponse_owner_text = 'DUMMY'
        self._import()
        self.assertEqual(self._mlist.autorespond_owner, ResponseAction.none)
        self.assertEqual(self._mlist.autoresponse_owner_text, '')

    #def test_administrative(self):
    #    # administrivia -> administrative
    #    self._mlist.administrative = None
    #    self._import()
    #    self.assertTrue(self._mlist.administrative)

    def test_filter_pass_renames(self):
        # mime_types -> types
        # filename_extensions -> extensions
        self._mlist.filter_types = ["dummy"]
        self._mlist.pass_types = ["dummy"]
        self._mlist.filter_extensions = ["dummy"]
        self._mlist.pass_extensions = ["dummy"]
        self._import()
        self.assertEqual(list(self._mlist.filter_types), [])
        self.assertEqual(list(self._mlist.filter_extensions),
                         ['exe', 'bat', 'cmd', 'com', 'pif',
                          'scr', 'vbs', 'cpl'])
        self.assertEqual(list(self._mlist.pass_types),
                ['multipart/mixed', 'multipart/alternative', 'text/plain'])
        self.assertEqual(list(self._mlist.pass_extensions), [])

    def test_process_bounces(self):
        # bounce_processing -> process_bounces
        self._mlist.process_bounces = None
        self._import()
        self.assertTrue(self._mlist.process_bounces)

    def test_forward_unrecognized_bounces_to(self):
        # bounce_unrecognized_goes_to_list_owner -> forward_unrecognized_bounces_to
        self._mlist.forward_unrecognized_bounces_to = DummyEnum.val
        self._import()
        self.assertEqual(self._mlist.forward_unrecognized_bounces_to,
                         UnrecognizedBounceDisposition.administrators)

    def test_moderator_password(self):
        # mod_password -> moderator_password
        self._mlist.moderator_password = str("TESTDATA")
        self._import()
        self.assertEqual(self._mlist.moderator_password, None)

    def test_moderator_password_str(self):
        # moderator_password must not be unicode
        self._pckdict[b"mod_password"] = b'TESTVALUE'
        self._import()
        self.assertFalse(isinstance(self._mlist.moderator_password, unicode))
        self.assertEqual(self._mlist.moderator_password, b'TESTVALUE')

    def test_newsgroup_moderation(self):
        # news_moderation -> newsgroup_moderation
        # news_prefix_subject_too -> nntp_prefix_subject_too
        self._mlist.newsgroup_moderation = DummyEnum.val
        self._mlist.nntp_prefix_subject_too = None
        self._import()
        self.assertEqual(self._mlist.newsgroup_moderation,
                         NewsgroupModeration.none)
        self.assertTrue(self._mlist.nntp_prefix_subject_too)

    def test_msg_to_message(self):
        # send_welcome_msg -> send_welcome_message
        # send_goodbye_msg -> send_goodbye_message
        self._mlist.send_welcome_message = None
        self._mlist.send_goodbye_message = None
        self._import()
        self.assertTrue(self._mlist.send_welcome_message)
        self.assertTrue(self._mlist.send_goodbye_message)

    def test_ban_list(self):
        banned = [
            ("anne@example.com", "anne@example.com"),
            ("^.*@example.com", "bob@example.com"),
            ("non-ascii-\xe8@example.com", "non-ascii-\ufffd@example.com"),
            ]
        self._pckdict["ban_list"] = [ b[0].encode("iso-8859-1") for b in banned ]
        try:
            self._import()
        except UnicodeDecodeError, e:
            print(format_exc())
            self.fail(e)
        for _pattern, addr in banned:
            self.assertTrue(IBanManager(self._mlist).is_banned(addr))

    def test_acceptable_aliases(self):
        # it used to be a plain-text field (values are newline-separated)
        aliases = ["alias1@example.com",
                   "alias2@exemple.com",
                   "non-ascii-\xe8@example.com",
                   ]
        self._pckdict[b"acceptable_aliases"] = \
                ("\n".join(aliases)).encode("utf-8")
        self._import()
        alias_set = IAcceptableAliasSet(self._mlist)
        self.assertEqual(sorted(alias_set.aliases), aliases)

    def test_acceptable_aliases_invalid(self):
        # values without an '@' sign used to be matched against the local part,
        # now we need to add the '^' sign
        aliases = ["invalid-value", ]
        self._pckdict[b"acceptable_aliases"] = \
                ("\n".join(aliases)).encode("utf-8")
        try:
            self._import()
        except ValueError, e:
            print(format_exc())
            self.fail("Invalid value '%s' caused a crash" % e)
        alias_set = IAcceptableAliasSet(self._mlist)
        self.assertEqual(sorted(alias_set.aliases),
                         [ ("^" + a) for a in aliases ])

    def test_info_non_ascii(self):
        # info can contain non-ascii chars
        info = 'O idioma aceito \xe9 somente Portugu\xeas do Brasil'
        self._pckdict[b"info"] = info.encode("utf-8")
        self._import()
        self.assertEqual(self._mlist.info, info,
                         "Encoding to UTF-8 is not handled")
        # test fallback to ascii with replace
        self._pckdict[b"info"] = info.encode("iso-8859-1")
        self._import()
        self.assertEqual(self._mlist.info,
                         unicode(self._pckdict[b"info"], "ascii", "replace"),
                         "We don't fall back to replacing non-ascii chars")

    def test_preferred_language(self):
        self._pckdict[b"preferred_language"] = b'ja'
        english = getUtility(ILanguageManager).get('en')
        japanese = getUtility(ILanguageManager).get('ja')
        self.assertEqual(self._mlist.preferred_language, english)
        self._import()
        self.assertEqual(self._mlist.preferred_language, japanese)

    def test_preferred_language_unknown_previous(self):
        # when the previous language is unknown, it should not fail
        self._mlist._preferred_language = 'xx' # non-existant
        self._import()
        english = getUtility(ILanguageManager).get('en')
        self.assertEqual(self._mlist.preferred_language, english)

    def test_new_language(self):
        self._pckdict[b"preferred_language"] = b'xx_XX'
        try:
            self._import()
        except Import21Error, e:
            # check the message
            self.assertTrue("[language.xx_XX]" in str(e))
        else:
            self.fail("Import21Error was not raised")



class TestArchiveImport(unittest.TestCase):
    # The mlist.archive_policy gets set from the old list's archive and
    # archive_private values

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._mlist.archive_policy = DummyEnum.val

    def tearDown(self):
        remove_list(self._mlist)

    def _do_test(self, pckdict, expected):
        import_config_pck(self._mlist, pckdict)
        self.assertEqual(self._mlist.archive_policy, expected)

    def test_public(self):
        self._do_test({ "archive": True, "archive_private": False },
                      ArchivePolicy.public)

    def test_private(self):
        self._do_test({ "archive": True, "archive_private": True },
                      ArchivePolicy.private)

    def test_no_archive(self):
        self._do_test({ "archive": False, "archive_private": False },
                      ArchivePolicy.never)



class TestFilterActionImport(unittest.TestCase):
    # The mlist.filter_action enum values have changed. In Mailman 2.1 the
    # order was 'Discard', 'Reject', 'Forward to List Owner', 'Preserve'.

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._mlist.filter_action = DummyEnum.val

    def tearDown(self):
        remove_list(self._mlist)

    def _do_test(self, original, expected):
        import_config_pck(self._mlist, { "filter_action": original })
        self.assertEqual(self._mlist.filter_action, expected)

    def test_discard(self):
        self._do_test(0, FilterAction.discard)

    def test_reject(self):
        self._do_test(1, FilterAction.reject)

    def test_forward(self):
        self._do_test(2, FilterAction.forward)

    def test_preserve(self):
        self._do_test(3, FilterAction.preserve)



class TestMemberActionImport(unittest.TestCase):
    # The mlist.default_member_action and mlist.default_nonmember_action enum
    # values are different in Mailman 2.1, they have been merged into a
    # single enum in Mailman 3
    # For default_member_action, which used to be called
    # member_moderation_action, the values were:
    # 0==Hold, 1=Reject, 2==Discard
    # For default_nonmember_action, which used to be called
    # generic_nonmember_action, the values were:
    # 0==Accept, 1==Hold, 2==Reject, 3==Discard

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._mlist.default_member_action = DummyEnum.val
        self._mlist.default_nonmember_action = DummyEnum.val
        self._pckdict = {
            b"member_moderation_action": DummyEnum.val,
            b"generic_nonmember_action": DummyEnum.val,
        }

    def tearDown(self):
        remove_list(self._mlist)

    def _do_test(self, expected):
        import_config_pck(self._mlist, self._pckdict)
        for key, value in expected.iteritems():
            self.assertEqual(getattr(self._mlist, key), value)

    def test_member_hold(self):
        self._pckdict[b"member_moderation_action"] = 0
        self._do_test({"default_member_action": Action.hold})

    def test_member_reject(self):
        self._pckdict[b"member_moderation_action"] = 1
        self._do_test({"default_member_action": Action.reject})

    def test_member_discard(self):
        self._pckdict[b"member_moderation_action"] = 2
        self._do_test({"default_member_action": Action.discard})

    def test_nonmember_accept(self):
        self._pckdict[b"generic_nonmember_action"] = 0
        self._do_test({"default_nonmember_action": Action.accept})

    def test_nonmember_hold(self):
        self._pckdict[b"generic_nonmember_action"] = 1
        self._do_test({"default_nonmember_action": Action.hold})

    def test_nonmember_reject(self):
        self._pckdict[b"generic_nonmember_action"] = 2
        self._do_test({"default_nonmember_action": Action.reject})

    def test_nonmember_discard(self):
        self._pckdict[b"generic_nonmember_action"] = 3
        self._do_test({"default_nonmember_action": Action.discard})



class TestConvertToURI(unittest.TestCase):
    # The following values were plain text, and are now URIs in Mailman 3:
    # - welcome_message_uri
    # - goodbye_message_uri
    # - header_uri
    # - footer_uri
    # - digest_header_uri
    # - digest_footer_uri
    #
    # The templates contain variables that must be replaced:
    # - %(real_name)s -> %(display_name)s
    # - %(real_name)s@%(host_name)s -> %(fqdn_listname)s
    # - %(web_page_url)slistinfo%(cgiext)s/%(_internal_name)s -> %(listinfo_uri)s

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._conf_mapping = {
            "welcome_msg": "welcome_message_uri",
            "goodbye_msg": "goodbye_message_uri",
            "msg_header": "header_uri",
            "msg_footer": "footer_uri",
            "digest_header": "digest_header_uri",
            "digest_footer": "digest_footer_uri",
        }
        self._pckdict = {}
        #self._pckdict = {
        #    "preferred_language": "XX", # templates are lang-specific
        #}

    def tearDown(self):
        remove_list(self._mlist)

    def test_text_to_uri(self):
        for oldvar, newvar in self._conf_mapping.iteritems():
            self._pckdict[str(oldvar)] = b"TEST VALUE"
            import_config_pck(self._mlist, self._pckdict)
            newattr = getattr(self._mlist, newvar)
            text = decorate(self._mlist, newattr)
            self.assertEqual(text, "TEST VALUE",
                    "Old variable %s was not properly imported to %s"
                    % (oldvar, newvar))

    def test_substitutions(self):
        test_text = ("UNIT TESTING %(real_name)s mailing list\n"
                     "%(real_name)s@%(host_name)s\n"
                     "%(web_page_url)slistinfo%(cgiext)s/%(_internal_name)s")
        expected_text = ("UNIT TESTING $display_name mailing list\n"
                         "$fqdn_listname\n"
                         "$listinfo_uri")
        for oldvar, newvar in self._conf_mapping.iteritems():
            self._pckdict[str(oldvar)] = str(test_text)
            import_config_pck(self._mlist, self._pckdict)
            newattr = getattr(self._mlist, newvar)
            template_uri = expand(newattr, dict(
                listname=self._mlist.fqdn_listname,
                language=self._mlist.preferred_language.code,
                ))
            loader = getUtility(ITemplateLoader)
            text = loader.get(template_uri)
            self.assertEqual(text, expected_text,
                    "Old variables were not converted for %s" % newvar)

    def test_keep_default(self):
        # If the value was not changed from MM2.1's default, don't import it
        default_msg_footer = (
            "_______________________________________________\n"
            "%(real_name)s mailing list\n"
            "%(real_name)s@%(host_name)s\n"
            "%(web_page_url)slistinfo%(cgiext)s/%(_internal_name)s"
            )
        for oldvar in ("msg_footer", "digest_footer"):
            newvar = self._conf_mapping[oldvar]
            self._pckdict[str(oldvar)] = str(default_msg_footer)
            old_value = getattr(self._mlist, newvar)
            import_config_pck(self._mlist, self._pckdict)
            new_value = getattr(self._mlist, newvar)
            self.assertEqual(old_value, new_value,
                    "Default value was not preserved for %s" % newvar)

    def test_keep_default_if_fqdn_changed(self):
        # Use case: importing the old a@ex.com into b@ex.com
        # We can't check if it changed from the default
        # -> don't import, we may do more harm than good and it's easy to
        # change if needed
        test_value = b"TEST-VALUE"
        for oldvar, newvar in self._conf_mapping.iteritems():
            self._mlist.mail_host = "example.com"
            self._pckdict[b"mail_host"] = b"test.example.com"
            self._pckdict[str(oldvar)] = test_value
            old_value = getattr(self._mlist, newvar)
            import_config_pck(self._mlist, self._pckdict)
            new_value = getattr(self._mlist, newvar)
            self.assertEqual(old_value, new_value,
                    "Default value was not preserved for %s" % newvar)

    def test_unicode(self):
        for oldvar in self._conf_mapping:
            self._pckdict[str(oldvar)] = b"Ol\xe1!"
        try:
            import_config_pck(self._mlist, self._pckdict)
        except UnicodeDecodeError, e:
            print(format_exc())
            self.fail(e)
        for oldvar, newvar in self._conf_mapping.iteritems():
            newattr = getattr(self._mlist, newvar)
            text = decorate(self._mlist, newattr)
            expected = u'Ol\ufffd!'.encode("utf-8")
            # we get bytestrings because the text is stored in a file
            self.assertEqual(text, expected)



class TestRosterImport(unittest.TestCase):

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._pckdict = {
            b"members": {
                b"anne@example.com": 0,
                b"bob@example.com": b"bob@ExampLe.Com",
            },
            b"digest_members": {
                b"cindy@example.com": 0,
                b"dave@example.com": b"dave@ExampLe.Com",
            },
            b"passwords": {
                b"anne@example.com" : b"annepass",
                b"bob@example.com"  : b"bobpass",
                b"cindy@example.com": b"cindypass",
                b"dave@example.com" : b"davepass",
            },
            b"language": {
                b"anne@example.com" : b"fr",
                b"bob@example.com"  : b"de",
                b"cindy@example.com": b"es",
                b"dave@example.com" : b"it",
            },
            b"usernames": { # Usernames are unicode strings in the pickle
                b"anne@example.com" : "Anne",
                b"bob@example.com"  : "Bob",
                b"cindy@example.com": "Cindy",
                b"dave@example.com" : "Dave",
            },
            b"owner": [
                b"anne@example.com",
                b"emily@example.com",
            ],
            b"moderator": [
                b"bob@example.com",
                b"fred@example.com",
            ],
        }
        self._usermanager = getUtility(IUserManager)
        language_manager = getUtility(ILanguageManager)
        for code in self._pckdict[b"language"].values():
            if code not in language_manager.codes:
                language_manager.add(code, 'utf-8', code)

    def tearDown(self):
        remove_list(self._mlist)

    def test_member(self):
        import_config_pck(self._mlist, self._pckdict)
        for name in ("anne", "bob", "cindy", "dave"):
            addr = "%s@example.com" % name
            self.assertTrue(
                    addr in [ a.email for a in self._mlist.members.addresses],
                    "Address %s was not imported" % addr)
        self.assertTrue("anne@example.com" in [ a.email
                        for a in self._mlist.regular_members.addresses])
        self.assertTrue("bob@example.com" in [ a.email
                        for a in self._mlist.regular_members.addresses])
        self.assertTrue("cindy@example.com" in [ a.email
                        for a in self._mlist.digest_members.addresses])
        self.assertTrue("dave@example.com" in [ a.email
                        for a in self._mlist.digest_members.addresses])

    def test_original_email(self):
        import_config_pck(self._mlist, self._pckdict)
        bob = self._usermanager.get_address("bob@example.com")
        self.assertEqual(bob.original_email, "bob@ExampLe.Com")
        dave = self._usermanager.get_address("dave@example.com")
        self.assertEqual(dave.original_email, "dave@ExampLe.Com")

    def test_language(self):
        import_config_pck(self._mlist, self._pckdict)
        for name in ("anne", "bob", "cindy", "dave"):
            addr = "%s@example.com" % name
            member = self._mlist.members.get_member(addr)
            self.assertTrue(member is not None,
                            "Address %s was not imported" % addr)
            print(self._pckdict["language"])
            print(member.preferred_language, member.preferred_language.code)
            self.assertEqual(member.preferred_language.code,
                             self._pckdict["language"][addr])

    def test_new_language(self):
        self._pckdict[b"language"][b"anne@example.com"] = b'xx_XX'
        try:
            import_config_pck(self._mlist, self._pckdict)
        except Import21Error, e:
            # check the message
            self.assertTrue("[language.xx_XX]" in str(e))
        else:
            self.fail("Import21Error was not raised")

    def test_username(self):
        import_config_pck(self._mlist, self._pckdict)
        for name in ("anne", "bob", "cindy", "dave"):
            addr = "%s@example.com" % name
            user = self._usermanager.get_user(addr)
            address = self._usermanager.get_address(addr)
            self.assertTrue(user is not None,
                    "User %s was not imported" % addr)
            self.assertTrue(address is not None,
                    "Address %s was not imported" % addr)
            display_name = self._pckdict["usernames"][addr]
            self.assertEqual(user.display_name, display_name,
                    "The display name was not set for User %s" % addr)
            self.assertEqual(address.display_name, display_name,
                    "The display name was not set for Address %s" % addr)

    def test_owner(self):
        import_config_pck(self._mlist, self._pckdict)
        for name in ("anne", "emily"):
            addr = "%s@example.com" % name
            self.assertTrue(
                    addr in [ a.email for a in self._mlist.owners.addresses ],
                    "Address %s was not imported as owner" % addr)
        self.assertFalse("emily@example.com" in
                [ a.email for a in self._mlist.members.addresses ],
                "Address emily@ was wrongly added to the members list")

    def test_moderator(self):
        import_config_pck(self._mlist, self._pckdict)
        for name in ("bob", "fred"):
            addr = "%s@example.com" % name
            self.assertTrue(
                    addr in [ a.email for a in self._mlist.moderators.addresses ],
                    "Address %s was not imported as moderator" % addr)
        self.assertFalse("fred@example.com" in
                [ a.email for a in self._mlist.members.addresses ],
                "Address fred@ was wrongly added to the members list")

    def test_password(self):
        #self.anne.password = config.password_context.encrypt('abc123')
        import_config_pck(self._mlist, self._pckdict)
        for name in ("anne", "bob", "cindy", "dave"):
            addr = "%s@example.com" % name
            user = self._usermanager.get_user(addr)
            self.assertTrue(user is not None,
                    "Address %s was not imported" % addr)
            self.assertEqual(user.password, b'{plaintext}%spass' % name,
                    "Password for %s was not imported" % addr)

    def test_same_user(self):
        # Adding the address of an existing User must not create another user
        user = self._usermanager.create_user('anne@example.com', 'Anne')
        user.register("bob@example.com") # secondary email
        import_config_pck(self._mlist, self._pckdict)
        member = self._mlist.members.get_member('bob@example.com')
        self.assertEqual(member.user, user)

    def test_owner_and_moderator_not_lowercase(self):
        # In the v2.1 pickled dict, the owner and moderator lists are not
        # necessarily lowercased already
        self._pckdict[b"owner"] = [b"Anne@example.com"]
        self._pckdict[b"moderator"] = [b"Anne@example.com"]
        try:
            import_config_pck(self._mlist, self._pckdict)
        except AssertionError:
            print(format_exc())
            self.fail("The address was not lowercased")
        self.assertTrue("anne@example.com" in
                [ a.email for a in self._mlist.owners.addresses ])
        self.assertTrue("anne@example.com" in
                [ a.email for a in self._mlist.moderators.addresses])

    def test_address_already_exists_but_no_user(self):
        # An address already exists, but it is not linked to a user nor
        # subscribed
        anne_addr = Address("anne@example.com", "Anne")
        Store.of(self._mlist).add(anne_addr)
        try:
            import_config_pck(self._mlist, self._pckdict)
        except ExistingAddressError:
            print(format_exc())
            self.fail("existing address was not checked")
        anne = self._usermanager.get_user("anne@example.com")
        self.assertTrue(anne.controls("anne@example.com"))
        self.assertTrue(anne_addr in self._mlist.regular_members.addresses)

    def test_address_already_subscribed_but_no_user(self):
        # An address is already subscribed, but it is not linked to a user
        anne_addr = Address("anne@example.com", "Anne")
        self._mlist.subscribe(anne_addr)
        try:
            import_config_pck(self._mlist, self._pckdict)
        except ExistingAddressError:
            print(format_exc())
            self.fail("existing address was not checked")
        anne = self._usermanager.get_user("anne@example.com")
        self.assertTrue(anne.controls("anne@example.com"))




class TestPreferencesImport(unittest.TestCase):

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('blank@example.com')
        self._pckdict = {
            b"members": { b"anne@example.com": 0 },
            b"user_options": {},
            b"delivery_status": {},
        }
        self._usermanager = getUtility(IUserManager)

    def tearDown(self):
        remove_list(self._mlist)

    def _do_test(self, oldvalue, expected):
        self._pckdict[b"user_options"][b"anne@example.com"] = oldvalue
        import_config_pck(self._mlist, self._pckdict)
        user = self._usermanager.get_user("anne@example.com")
        self.assertTrue(user is not None, "User was not imported")
        member = self._mlist.members.get_member("anne@example.com")
        self.assertTrue(member is not None, "Address was not subscribed")
        for exp_name, exp_val in expected.iteritems():
            try:
                currentval = getattr(member, exp_name)
            except AttributeError:
                # hide_address has no direct getter
                currentval = getattr(member.preferences, exp_name)
            self.assertEqual(currentval, exp_val,
                    "Preference %s was not imported" % exp_name)
        # XXX: should I check that other params are still equal to
        # mailman.core.constants.system_preferences ?

    def test_acknowledge_posts(self):
        # AcknowledgePosts
        self._do_test(4, {"acknowledge_posts": True})

    def test_hide_address(self):
        # ConcealSubscription
        self._do_test(16, {"hide_address": True})

    def test_receive_own_postings(self):
        # DontReceiveOwnPosts
        self._do_test(2, {"receive_own_postings": False})

    def test_receive_list_copy(self):
        # DontReceiveDuplicates
        self._do_test(256, {"receive_list_copy": False})

    def test_digest_plain(self):
        # Digests & DisableMime
        self._pckdict[b"digest_members"] = self._pckdict[b"members"].copy()
        self._pckdict[b"members"] = {}
        self._do_test(8, {"delivery_mode": DeliveryMode.plaintext_digests})

    def test_digest_mime(self):
        # Digests & not DisableMime
        self._pckdict[b"digest_members"] = self._pckdict[b"members"].copy()
        self._pckdict[b"members"] = {}
        self._do_test(0, {"delivery_mode": DeliveryMode.mime_digests})

    def test_delivery_status(self):
        # look for the pckdict["delivery_status"] key which will look like
        # (status, time) where status is among the following:
        # ENABLED  = 0 # enabled
        # UNKNOWN  = 1 # legacy disabled
        # BYUSER   = 2 # disabled by user choice
        # BYADMIN  = 3 # disabled by admin choice
        # BYBOUNCE = 4 # disabled by bounces
        for oldval, expected in enumerate((DeliveryStatus.enabled,
                DeliveryStatus.unknown, DeliveryStatus.by_user,
                DeliveryStatus.by_moderator, DeliveryStatus.by_bounces)):
            self._pckdict[b"delivery_status"][b"anne@example.com"] = (oldval, 0)
            import_config_pck(self._mlist, self._pckdict)
            member = self._mlist.members.get_member("anne@example.com")
            self.assertTrue(member is not None, "Address was not subscribed")
            self.assertEqual(member.delivery_status, expected)
            member.unsubscribe()

    def test_moderate(self):
        # Option flag Moderate is translated to
        # member.moderation_action = Action.hold
        self._do_test(128, {"moderation_action": Action.hold})

    def test_multiple_options(self):
        # DontReceiveDuplicates & DisableMime & SuppressPasswordReminder
        self._pckdict[b"digest_members"] = self._pckdict[b"members"].copy()
        self._pckdict[b"members"] = {}
        self._do_test(296, {
                "receive_list_copy": False,
                "delivery_mode": DeliveryMode.plaintext_digests,
                })
