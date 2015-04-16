# Copyright (C) 2012-2015 by the Free Software Foundation, Inc.
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

"""REST API for held subscription requests."""

__all__ = [
    'SubscriptionRequests',
    ]


from mailman.interfaces.action import Action
from mailman.interfaces.pending import IPendings
from mailman.interfaces.registrar import IRegistrar
from mailman.rest.helpers import (
    CollectionMixin, bad_request, child, etag, no_content, not_found, okay)
from mailman.rest.validator import Validator, enum_validator
from zope.component import getUtility



class _ModerationBase:
    """Common base class."""

    def __init__(self):
        self._pendings = getUtility(IPendings)

    def _make_resource(self, token):
        pendable = self._pendings.confirm(token, expunge=False)
        resource = dict(token=token)
        resource.update(pendable)
        return resource



class IndividualRequest(_ModerationBase):
    """Resource for moderating a membership change."""

    def __init__(self, mlist, token):
        self._mlist = mlist
        self._registrar = IRegistrar(self._mlist)
        self._token = token

    def on_get(self, request, response):
        try:
            token, token_owner, member = self._registrar.confirm(self._token)
        except LookupError:
            not_found(response)
            return
        try:
            request_id = int(self._request_id)
        except ValueError:
            bad_request(response)
            return
        resource = self._make_resource(request_id, MEMBERSHIP_CHANGE_REQUESTS)
        if resource is None:
            not_found(response)
        else:
            # Remove unnecessary keys.
            del resource['key']
            okay(response, etag(resource))

    def on_post(self, request, response):
        try:
            validator = Validator(action=enum_validator(Action))
            arguments = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        requests = IListRequests(self._mlist)
        try:
            request_id = int(self._request_id)
        except ValueError:
            bad_request(response)
            return
        results = requests.get_request(request_id)
        if results is None:
            not_found(response)
            return
        key, data = results
        try:
            request_type = RequestType[data['_request_type']]
        except ValueError:
            bad_request(response)
            return
        if request_type is RequestType.subscription:
            handle_subscription(self._mlist, request_id, **arguments)
        elif request_type is RequestType.unsubscription:
            handle_unsubscription(self._mlist, request_id, **arguments)
        else:
            bad_request(response)
            return
        no_content(response)


class SubscriptionRequests(_ModerationBase, CollectionMixin):
    """Resource for membership change requests."""

    def __init__(self, mlist):
        super().__init__()
        self._mlist = mlist

    def _get_collection(self, request):
        # There's currently no better way to query the pendings database for
        # all the entries that are associated with subscription holds on this
        # mailing list.  Brute force for now.
        return [token for token, pendable in getUtility(IPendings)]

    def on_get(self, request, response):
        """/lists/listname/requests"""
        resource = self._make_collection(request)
        okay(response, etag(resource))

    @child(r'^(?P<token>[^/]+)')
    def subscription(self, request, segments, **kw):
        return IndividualRequest(self._mlist, kw['token'])
