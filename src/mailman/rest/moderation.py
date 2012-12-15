# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""REST API for Message moderation."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'HeldMessage',
    'HeldMessages',
    'SubscriptionRequests',
    ]


from restish import http, resource
from zope.component import getUtility

from mailman.app.moderator import handle_message
from mailman.interfaces.action import Action
from mailman.interfaces.messages import IMessageStore
from mailman.interfaces.requests import IListRequests, RequestType
from mailman.rest.helpers import CollectionMixin, etag, no_content
from mailman.rest.validator import Validator, enum_validator



class HeldMessage(resource.Resource, CollectionMixin):
    """Resource for moderating a held message."""

    def __init__(self, mlist, request_id):
        self._mlist = mlist
        self._request_id = request_id

    @resource.GET()
    def details(self, request):
        requests = IListRequests(self._mlist)
        try:
            request_id = int(self._request_id)
        except ValueError:
            return http.bad_request()
        results = requests.get_request(request_id, RequestType.held_message)
        if results is None:
            return http.not_found()
        key, data = results
        msg = getUtility(IMessageStore).get_message_by_id(key)
        resource = dict(
            key=key,
            # XXX convert _mod_{subject,hold_date,reason,sender,message_id}
            # into top level values of the resource dict.
            data=data,
            msg=msg.as_string(),
            id=request_id,
            )
        return http.ok([], etag(resource))

    @resource.POST()
    def moderate(self, request):
        try:
            validator = Validator(action=enum_validator(Action))
            arguments = validator(request)
        except ValueError as error:
            return http.bad_request([], str(error))
        requests = IListRequests(self._mlist)
        try:
            request_id = int(self._request_id)
        except ValueError:
            return http.bad_request()
        results = requests.get_request(request_id, RequestType.held_message)
        if results is None:
            return http.not_found()
        handle_message(self._mlist, request_id, **arguments)
        return no_content()



class HeldMessages(resource.Resource, CollectionMixin):
    """Resource for messages held for moderation."""

    def __init__(self, mlist):
        self._mlist = mlist
        self._requests = None

    def _resource_as_dict(self, request):
        """See `CollectionMixin`."""
        key, data = self._requests.get_request(request.id)
        return dict(
            key=key,
            data=data,
            id=request.id,
            )

    def _get_collection(self, request):
        requests = IListRequests(self._mlist)
        self._requests = requests
        return list(requests.of_type(RequestType.held_message))

    @resource.GET()
    def requests(self, request):
        """/lists/listname/held"""
        # `request` is a restish.http.Request object.
        resource = self._make_collection(request)
        return http.ok([], etag(resource))

    @resource.child('{id}')
    def message(self, request, segments, **kw):
        return HeldMessage(self._mlist, kw['id'])



class SubscriptionRequests(resource.Resource, CollectionMixin):
    """Resource for subscription and unsubscription requests."""

    def __init__(self, mlist):
        self._mlist = mlist
        self._requests = None

    def _resource_as_dict(self, request_and_type):
        """See `CollectionMixin`."""
        request, request_type = request_and_type
        key, data = self._requests.get_request(request.id)
        resource = dict(
            key=key,
            id=request.id,
            )
        # Flatten the IRequest payload into the JSON representation.
        resource.update(data)
        # Add a key indicating what type of subscription request this is.
        resource['type'] = request_type.name
        return resource

    def _get_collection(self, request):
        requests = IListRequests(self._mlist)
        self._requests = requests
        items = []
        for request_type in (RequestType.subscription,
                             RequestType.unsubscription):
            for request in requests.of_type(request_type):
                items.append((request, request_type))
        return items

    @resource.GET()
    def requests(self, request):
        """/lists/listname/requests"""
        # `request` is a restish.http.Request object.
        resource = self._make_collection(request)
        return http.ok([], etag(resource))

    @resource.child('{id}')
    def subscription(self, request, segments, **kw):
        pass
