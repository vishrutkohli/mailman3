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

"""REST for domains."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ADomain',
    'AllDomains',
    ]


import falcon

from mailman.interfaces.domain import (
    BadDomainSpecificationError, IDomainManager)
from mailman.rest.helpers import (
    BadRequest, CollectionMixin, NotFound, child, etag, path_to)
from mailman.rest.lists import ListsForDomain
from mailman.rest.validator import Validator
from zope.component import getUtility



class _DomainBase(CollectionMixin):
    """Shared base class for domain representations."""

    def _resource_as_dict(self, domain):
        """See `CollectionMixin`."""
        return dict(
            base_url=domain.base_url,
            contact_address=domain.contact_address,
            description=domain.description,
            mail_host=domain.mail_host,
            self_link=path_to('domains/{0}'.format(domain.mail_host)),
            url_host=domain.url_host,
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IDomainManager))


class ADomain(_DomainBase):
    """A domain."""

    def __init__(self, domain):
        self._domain = domain

    def on_get(self, request, response):
        """Return a single domain end-point."""
        domain = getUtility(IDomainManager).get(self._domain)
        if domain is None:
            falcon.responders.path_not_found(request, response)
        else:
            response.status = falcon.HTTP_200
            response.body = self._resource_as_json(domain)

    def on_delete(self, request, response):
        """Delete the domain."""
        try:
            getUtility(IDomainManager).remove(self._domain)
        except KeyError:
            # The domain does not exist.
            falcon.responders.path_not_found(
                request, response, '404 Not Found')
        else:
            response.status = falcon.HTTP_204

    @child()
    def lists(self, request, segments):
        """/domains/<domain>/lists"""
        if len(segments) == 0:
            domain = getUtility(IDomainManager).get(self._domain)
            if domain is None:
                return NotFound()
            return ListsForDomain(domain)
        else:
            return BadRequest(), []


class AllDomains(_DomainBase):
    """The domains."""

    def on_post(self, request, response):
        """Create a new domain."""
        domain_manager = getUtility(IDomainManager)
        try:
            validator = Validator(mail_host=unicode,
                                  description=unicode,
                                  base_url=unicode,
                                  contact_address=unicode,
                                  _optional=('description', 'base_url',
                                             'contact_address'))
            domain = domain_manager.add(**validator(request))
        except BadDomainSpecificationError:
            falcon.responders.bad_request(
                request, response, body=b'Domain exists')
        except ValueError as error:
            falcon.responders.bad_request(
                request, response, body=str(error))
        else:
            location = path_to('domains/{0}'.format(domain.mail_host))
            response.status = falcon.HTTP_201
            response.location = location

    def on_get(self, request, response):
        """/domains"""
        resource = self._make_collection(request)
        response.status = falcon.HTTP_200
        response.body = etag(resource)
