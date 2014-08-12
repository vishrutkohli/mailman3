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

"""The root of the REST API."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Root',
    ]


import falcon

from base64 import b64decode
from restish import http
from zope.component import getUtility

from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.core.system import system
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.styles import IStyleManager
from mailman.rest.addresses import AllAddresses, AnAddress
from mailman.rest.domains import ADomain, AllDomains
from mailman.rest.helpers import etag, path_to
from mailman.rest.lists import AList, AllLists
from mailman.rest.members import AMember, AllMembers, FindMembers
from mailman.rest.preferences import ReadOnlyPreferences
from mailman.rest.templates import TemplateFinder
from mailman.rest.users import AUser, AllUsers


def child(matcher=None):
    def decorator(func):
        if matcher is None:
            func.__matcher__ = func.__name__
        else:
            func.__matcher__ = matcher
        return func
    return decorator


class BadRequest:
    def on_get(self, request, response):
        raise falcon.HTTPError(falcon.HTTP_400, None)

STOP = []



class Root:
    """The RESTful root resource.

    At the root of the tree are the API version numbers.  Everything else
    lives underneath those.  Currently there is only one API version number,
    and we start at 3.0 to match the Mailman version number.  That may not
    always be the case though.
    """

    @child(config.webservice.api_version)
    def api_version(self, request, segments):
        # We have to do this here instead of in a @falcon.before() handler
        # because those handlers are not compatible with our custom traversal
        # logic.  Specifically, falcon's before/after handlers will call the
        # responder, but the method we're wrapping isn't a responder, it's a
        # child traversal method.  There's no way to cause the thing that
        # calls the before hook to follow through with the child traversal in
        # the case where no error is raised.
        if request.auth is None:
            raise falcon.HTTPUnauthorized(
                b'401 Unauthorized',
                b'The REST API requires authentication')
        if request.auth.startswith('Basic '):
            credentials = b64decode(request.auth[6:])
            username, password = credentials.split(':', 1)
            if (username != config.webservice.admin_user or
                password != config.webservice.admin_pass):
                # Not authorized.
                raise falcon.HTTPUnauthorized(
                    b'401 Unauthorized',
                    b'User is not authorized for the REST API')
        return TopLevel(), segments


class System:
    def on_get(self, request, response):
        """/<api>/system"""
        resource = dict(
            mailman_version=system.mailman_version,
            python_version=system.python_version,
            self_link=path_to('system'),
            )
        response.status = falcon.HTTP_200
        response.body = etag(resource)


class TopLevel:
    """Top level collections and entries."""

    @child()
    def system(self, request, segments):
        """/<api>/system"""
        if len(segments) == 0:
            return System(), STOP
        elif len(segments) > 1:
            return BadRequest(), STOP
        elif segments[0] == 'preferences':
            return ReadOnlyPreferences(system_preferences, 'system'), STOP
        else:
            return BadRequest(), STOP

    @child()
    def addresses(self, request, segments):
        """/<api>/addresses
           /<api>/addresses/<email>
        """
        if len(segments) == 0:
            return AllAddresses()
        else:
            email = segments.pop(0)
            return AnAddress(email), segments

    @child()
    def domains(self, request, segments):
        """/<api>/domains
           /<api>/domains/<domain>
        """
        if len(segments) == 0:
            return AllDomains()
        else:
            domain = segments.pop(0)
            return ADomain(domain), segments

    @child()
    def lists(self, request, segments):
        """/<api>/lists
           /<api>/lists/<list>
           /<api>/lists/<list>/...
        """
        if len(segments) == 0:
            return AllLists()
        elif len(segments) == 1 and segments[0] == 'styles':
            manager = getUtility(IStyleManager)
            style_names = sorted(style.name for style in manager.styles)
            resource = dict(style_names=style_names,
                            default=config.styles.default)
            return http.ok([], etag(resource))
        else:
            # list-id is preferred, but for backward compatibility,
            # fqdn_listname is also accepted.
            list_identifier = segments.pop(0)
            return AList(list_identifier), segments

    @child()
    def members(self, request, segments):
        """/<api>/members"""
        if len(segments) == 0:
            return AllMembers()
        # Either the next segment is the string "find" or a member id.  They
        # cannot collide.
        segment = segments.pop(0)
        if segment == 'find':
            return FindMembers(), segments
        else:
            return AMember(segment), segments

    @child()
    def users(self, request, segments):
        """/<api>/users"""
        if len(segments) == 0:
            return AllUsers()
        else:
            user_id = segments.pop(0)
            return AUser(user_id), segments

    @child()
    def templates(self, request, segments):
        """/<api>/templates/<fqdn_listname>/<template>/[<language>]

        Use content negotiation to request language and suffix (content-type).
        """
        if len(segments) == 3:
            fqdn_listname, template, language = segments
        elif len(segments) == 2:
            fqdn_listname, template = segments
            language = 'en'
        else:
            return http.bad_request()
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            return http.not_found()
        # XXX dig out content-type from request
        content_type = None
        return TemplateFinder(
            fqdn_listname, template, language, content_type)
