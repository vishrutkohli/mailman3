# Copyright (C) 2011-2014 by the Free Software Foundation, Inc.
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

"""REST for users."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'AUser',
    'AllUsers',
    ]


from passlib.utils import generate_password as generate
from uuid import UUID
from zope.component import getUtility

from mailman.config import config
from mailman.core.errors import (
    ReadOnlyPATCHRequestError, UnknownPATCHRequestError)
from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.rest.addresses import UserAddresses
from mailman.rest.helpers import (
    BadRequest, CollectionMixin, GetterSetter, NotFound, bad_request, child,
    created, etag, forbidden, no_content, not_found, okay, paginate, path_to)
from mailman.rest.preferences import Preferences
from mailman.rest.validator import PatchValidator, Validator


# Attributes of a user which can be changed via the REST API.
class PasswordEncrypterGetterSetter(GetterSetter):
    def __init__(self):
        super(PasswordEncrypterGetterSetter, self).__init__(
            config.password_context.encrypt)
    def get(self, obj, attribute):
        assert attribute == 'cleartext_password'
        super(PasswordEncrypterGetterSetter, self).get(obj, 'password')
    def put(self, obj, attribute, value):
        assert attribute == 'cleartext_password'
        super(PasswordEncrypterGetterSetter, self).put(obj, 'password', value)


ATTRIBUTES = dict(
    display_name=GetterSetter(unicode),
    cleartext_password=PasswordEncrypterGetterSetter(),
    )



class _UserBase(CollectionMixin):
    """Shared base class for user representations."""

    def _resource_as_dict(self, user):
        """See `CollectionMixin`."""
        # The canonical URL for a user is their unique user id, although we
        # can always look up a user based on any registered and validated
        # email address associated with their account.  The user id is a UUID,
        # but we serialize its integer equivalent.
        user_id = user.user_id.int
        resource = dict(
            user_id=user_id,
            created_on=user.created_on,
            self_link=path_to('users/{0}'.format(user_id)),
            )
        # Add the password attribute, only if the user has a password.  Same
        # with the real name.  These could be None or the empty string.
        if user.password:
            resource['password'] = user.password
        if user.display_name:
            resource['display_name'] = user.display_name
        return resource

    @paginate
    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IUserManager).users)



class AllUsers(_UserBase):
    """The users."""

    def on_get(self, request, response):
        """/users"""
        resource = self._make_collection(request)
        okay(response, etag(resource))

    def on_post(self, request, response):
        """Create a new user."""
        try:
            validator = Validator(email=unicode,
                                  display_name=unicode,
                                  password=unicode,
                                  _optional=('display_name', 'password'))
            arguments = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        # We can't pass the 'password' argument to the user creation method,
        # so strip that out (if it exists), then create the user, adding the
        # password after the fact if successful.
        password = arguments.pop('password', None)
        try:
            user = getUtility(IUserManager).create_user(**arguments)
        except ExistingAddressError as error:
            bad_request(
                response,
                body=b'Address already exists: {0}'.format(error.address))
            return
        if password is None:
            # This will have to be reset since it cannot be retrieved.
            password = generate(int(config.passwords.password_length))
        user.password = config.password_context.encrypt(password)
        location = path_to('users/{0}'.format(user.user_id.int))
        created(response, location)



class AUser(_UserBase):
    """A user."""

    def __init__(self, user_identifier):
        """Get a user by various type of identifiers.

        :param user_identifier: The identifier used to retrieve the user.  The
            identifier may either be an integer user-id, or an email address
            controlled by the user.  The type of identifier is auto-detected
            by looking for an `@` symbol, in which case it's taken as an email
            address, otherwise it's assumed to be an integer.
        :type user_identifier: string
        """
        user_manager = getUtility(IUserManager)
        if '@' in user_identifier:
            self._user = user_manager.get_user(user_identifier)
        else:
            # The identifier is the string representation of an integer that
            # must be converted to a UUID.
            try:
                user_id = UUID(int=int(user_identifier))
            except ValueError:
                self._user = None
            else:
                self._user = user_manager.get_user_by_id(user_id)

    def on_get(self, request, response):
        """Return a single user end-point."""
        if self._user is None:
            not_found(response)
        else:
            okay(response, self._resource_as_json(self._user))

    @child()
    def addresses(self, request, segments):
        """/users/<uid>/addresses"""
        if self._user is None:
            return NotFound(), []
        return UserAddresses(self._user)

    def on_delete(self, request, response):
        """Delete the named user, all her memberships, and addresses."""
        if self._user is None:
            not_found(response)
            return
        for member in self._user.memberships.members:
            member.unsubscribe()
        user_manager = getUtility(IUserManager)
        for address in self._user.addresses:
            user_manager.delete_address(address)
        user_manager.delete_user(self._user)
        no_content(response)

    @child()
    def preferences(self, request, segments):
        """/addresses/<email>/preferences"""
        if len(segments) != 0:
            return BadRequest(), []
        if self._user is None:
            return NotFound(), []
        child = Preferences(
            self._user.preferences,
            'users/{0}'.format(self._user.user_id.int))
        return child, []

    def on_patch(self, request, response):
        """Patch the user's configuration (i.e. partial update)."""
        if self._user is None:
            not_found(response)
            return
        try:
            validator = PatchValidator(request, ATTRIBUTES)
        except UnknownPATCHRequestError as error:
            bad_request(
                response, b'Unknown attribute: {0}'.format(error.attribute))
        except ReadOnlyPATCHRequestError as error:
            bad_request(
                response, b'Read-only attribute: {0}'.format(error.attribute))
        else:
            validator.update(self._user, request)
            no_content(response)

    def on_put(self, request, response):
        """Put the user's configuration (i.e. full update)."""
        if self._user is None:
            not_found(response)
            return
        validator = Validator(**ATTRIBUTES)
        try:
            validator.update(self._user, request)
        except UnknownPATCHRequestError as error:
            bad_request(
                response, b'Unknown attribute: {0}'.format(error.attribute))
        except ReadOnlyPATCHRequestError as error:
            bad_request(
                response, b'Read-only attribute: {0}'.format(error.attribute))
        except ValueError as error:
            bad_request(response, str(error))
        else:
            no_content(response)

    @child()
    def login(self, request, segments):
        """Log the user in, sort of, by verifying a given password."""
        if self._user is None:
            return NotFound(), []
        return Login(self._user)



class Login:
    """<api>/users/<uid>/login"""

    def __init__(self, user):
        assert user is not None
        self._user = user

    def on_post(self, request, response):
        # We do not want to encrypt the plaintext password given in the POST
        # data.  That would hash the password, but we need to have the
        # plaintext in order to pass into passlib.
        validator = Validator(cleartext_password=GetterSetter(unicode))
        try:
            values = validator(request)
        except ValueError as error:
            bad_request(response, str(error))
            return
        is_valid, new_hash = config.password_context.verify(
            values['cleartext_password'], self._user.password)
        if is_valid:
            if new_hash is not None:
                self._user.password = new_hash
            no_content(response)
        else:
            forbidden(response)
