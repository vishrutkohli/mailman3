# Copyright (C) 2010-2014 by the Free Software Foundation, Inc.
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

"""REST for mailing lists."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AList',
    'AllLists',
    'ListArchivers',
    'ListConfiguration',
    'ListsForDomain',
    ]


from lazr.config import as_boolean
from operator import attrgetter
from restish import http, resource
from zope.component import getUtility

from mailman.app.lifecycle import create_list, remove_list
from mailman.interfaces.domain import BadDomainSpecificationError
from mailman.interfaces.listmanager import (
    IListManager, ListAlreadyExistsError)
from mailman.interfaces.mailinglist import IListArchiverSet
from mailman.interfaces.member import MemberRole
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.rest.configuration import ListConfiguration
from mailman.rest.helpers import (
    CollectionMixin, GetterSetter, PATCH, etag, no_content, paginate, path_to,
    restish_matcher)
from mailman.rest.members import AMember, MemberCollection
from mailman.rest.moderation import HeldMessages, SubscriptionRequests
from mailman.rest.validator import Validator



@restish_matcher
def member_matcher(request, segments):
    """A matcher of member URLs inside mailing lists.

    e.g. /<role>/aperson@example.org
    """
    if len(segments) != 2:
        return None
    try:
        role = MemberRole[segments[0]]
    except KeyError:
        # Not a valid role.
        return None
    # No more segments.
    # XXX 2010-02-25 barry Matchers are undocumented in restish; they return a
    # 3-tuple of (match_args, match_kws, segments).
    return (), dict(role=role, email=segments[1]), ()


@restish_matcher
def roster_matcher(request, segments):
    """A matcher of all members URLs inside mailing lists.

    e.g. /roster/<role>
    """
    if len(segments) != 2 or segments[0] != 'roster':
        return None
    try:
        return (), dict(role=MemberRole[segments[1]]), ()
    except KeyError:
        # Not a valid role.
        return None


@restish_matcher
def config_matcher(request, segments):
    """A matcher for a mailing list's configuration resource.

    e.g. /config
    e.g. /config/description
    """
    if len(segments) < 1 or segments[0] != 'config':
        return None
    if len(segments) == 1:
        return (), {}, ()
    if len(segments) == 2:
        return (), dict(attribute=segments[1]), ()
    # More segments are not allowed.
    return None



class _ListBase(resource.Resource, CollectionMixin):
    """Shared base class for mailing list representations."""

    def _resource_as_dict(self, mlist):
        """See `CollectionMixin`."""
        return dict(
            display_name=mlist.display_name,
            fqdn_listname=mlist.fqdn_listname,
            list_id=mlist.list_id,
            list_name=mlist.list_name,
            mail_host=mlist.mail_host,
            member_count=mlist.members.member_count,
            volume=mlist.volume,
            self_link=path_to('lists/{0}'.format(mlist.list_id)),
            )

    @paginate
    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IListManager))


class AList(_ListBase):
    """A mailing list."""

    def __init__(self, list_identifier):
        # list-id is preferred, but for backward compatibility, fqdn_listname
        # is also accepted.  If the string contains '@', treat it as the
        # latter.
        manager = getUtility(IListManager)
        if '@' in list_identifier:
            self._mlist = manager.get(list_identifier)
        else:
            self._mlist = manager.get_by_list_id(list_identifier)

    @resource.GET()
    def mailing_list(self, request):
        """Return a single mailing list end-point."""
        if self._mlist is None:
            return http.not_found()
        return http.ok([], self._resource_as_json(self._mlist))

    @resource.DELETE()
    def delete_list(self, request):
        """Delete the named mailing list."""
        if self._mlist is None:
            return http.not_found()
        remove_list(self._mlist)
        return no_content()

    @resource.child(member_matcher)
    def member(self, request, segments, role, email):
        """Return a single member representation."""
        if self._mlist is None:
            return http.not_found()
        members = getUtility(ISubscriptionService).find_members(
            email, self._mlist.list_id, role)
        if len(members) == 0:
            return http.not_found()
        assert len(members) == 1, 'Too many matches'
        return AMember(members[0].member_id)

    @resource.child(roster_matcher)
    def roster(self, request, segments, role):
        """Return the collection of all a mailing list's members."""
        if self._mlist is None:
            return http.not_found()
        return MembersOfList(self._mlist, role)

    @resource.child(config_matcher)
    def config(self, request, segments, attribute=None):
        """Return a mailing list configuration object."""
        if self._mlist is None:
            return http.not_found()
        return ListConfiguration(self._mlist, attribute)

    @resource.child()
    def held(self, request, segments):
        """Return a list of held messages for the mailing list."""
        if self._mlist is None:
            return http.not_found()
        return HeldMessages(self._mlist)

    @resource.child()
    def requests(self, request, segments):
        """Return a list of subscription/unsubscription requests."""
        if self._mlist is None:
            return http.not_found()
        return SubscriptionRequests(self._mlist)

    @resource.child()
    def archivers(self, request, segments):
        """Return a representation of mailing list archivers."""
        if self._mlist is None:
            return http.not_found()
        return ListArchivers(self._mlist)



class AllLists(_ListBase):
    """The mailing lists."""

    @resource.POST()
    def create(self, request):
        """Create a new mailing list."""
        try:
            validator = Validator(fqdn_listname=unicode,
                                  style_name=unicode,
                                  _optional=('style_name',))
            mlist = create_list(**validator(request))
        except ListAlreadyExistsError:
            return http.bad_request([], b'Mailing list exists')
        except BadDomainSpecificationError as error:
            return http.bad_request([], b'Domain does not exist: {0}'.format(
                error.domain))
        except ValueError as error:
            return http.bad_request([], str(error))
        # wsgiref wants headers to be bytes, not unicodes.
        location = path_to('lists/{0}'.format(mlist.list_id))
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def collection(self, request):
        """/lists"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



class MembersOfList(MemberCollection):
    """The members of a mailing list."""

    def __init__(self, mailing_list, role):
        super(MembersOfList, self).__init__()
        self._mlist = mailing_list
        self._role = role

    @paginate
    def _get_collection(self, request):
        """See `CollectionMixin`."""
        # Overrides _MemberBase._get_collection() because we only want to
        # return the members from the requested roster.
        roster = self._mlist.get_roster(self._role)
        address_of_member = attrgetter('address.email')
        return list(sorted(roster.members, key=address_of_member))


class ListsForDomain(_ListBase):
    """The mailing lists for a particular domain."""

    def __init__(self, domain):
        self._domain = domain

    @resource.GET()
    def collection(self, request):
        """/domains/<domain>/lists"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))

    @paginate
    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(self._domain.mailing_lists)



class ArchiverGetterSetter(GetterSetter):
    """Resource for updating archiver statuses."""

    def __init__(self, mlist):
        super(ArchiverGetterSetter, self).__init__()
        self._archiver_set = IListArchiverSet(mlist)

    def put(self, mlist, attribute, value):
        # attribute will contain the (bytes) name of the archiver that is
        # getting a new status.  value will be the representation of the new
        # boolean status.
        archiver = self._archiver_set.get(attribute.decode('utf-8'))
        if archiver is None:
            raise ValueError('No such archiver: {}'.format(attribute))
        archiver.is_enabled = as_boolean(value)


class ListArchivers(resource.Resource):
    """The archivers for a list, with their enabled flags."""

    def __init__(self, mlist):
        self._mlist = mlist

    @resource.GET()
    def statuses(self, request):
        """Get all the archiver statuses."""
        archiver_set = IListArchiverSet(self._mlist)
        resource = {archiver.name: archiver.is_enabled
                    for archiver in archiver_set.archivers}
        return http.ok([], etag(resource))

    def patch_put(self, request, is_optional):
        archiver_set = IListArchiverSet(self._mlist)
        kws = {archiver.name: ArchiverGetterSetter(self._mlist)
               for archiver in archiver_set.archivers}
        if is_optional:
            # For a PUT, all attributes are optional.
            kws['_optional'] = kws.keys()
        try:
            Validator(**kws).update(self._mlist, request)
        except ValueError as error:
            return http.bad_request([], str(error))
        return no_content()

    @resource.PUT()
    def put_statuses(self, request):
        """Update all the archiver statuses."""
        return self.patch_put(request, is_optional=False)

    @PATCH()
    def patch_statuses(self, request):
        """Patch some archiver statueses."""
        return self.patch_put(request, is_optional=True)
