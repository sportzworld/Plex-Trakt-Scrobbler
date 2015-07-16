from plugin.core.filters import Filters
from plugin.core.helpers.variable import to_integer
from plugin.managers.core.base import Get, Manager, Update
from plugin.managers.core.exceptions import UserFilteredException
from plugin.models import User, UserRule, PlexAccount

import apsw
import logging
import peewee

log = logging.getLogger(__name__)


class GetUser(Get):
    def __call__(self, user):
        user = self.manager.parse_user(user)

        if not user:
            return None

        return super(GetUser, self).__call__(
            User.key == to_integer(user['key'])
        )

    def or_create(self, user, fetch=False, match=False, filtered_exception=False):
        user = self.manager.parse_user(user)

        if not user:
            return None

        try:
            # Create new user
            obj = self.manager.create(
                key=to_integer(user['key'])
            )

            # Update newly created object
            self.manager.update(
                obj, user,

                fetch=fetch,
                match=match,
                filtered_exception=filtered_exception
            )

            return obj
        except (apsw.ConstraintError, peewee.IntegrityError):
            # Return existing user
            obj = self(user)

            if fetch or match:
                # Update existing `User`
                self.manager.update(
                    obj, user,

                    fetch=fetch,
                    match=match,
                    filtered_exception=filtered_exception
                )

            return obj


class UpdateUser(Update):
    def __call__(self, obj, user, fetch=False, match=False, filtered_exception=False):
        user = self.manager.parse_user(user)

        if not user:
            return None

        filtered, data = self.to_dict(
            obj, user,

            fetch=fetch,
            match=match
        )

        updated = super(UpdateUser, self).__call__(
            obj, data
        )

        if filtered and filtered_exception:
            raise UserFilteredException

        return updated

    def to_dict(self, obj, user, fetch=False, match=False):
        result = {}

        # Fill `result` with available fields
        if user.get('title'):
            result['name'] = user['title']

        if user.get('thumb'):
            result['thumb'] = user['thumb']

        filtered = False

        if match:
            # Try match `User` against rules
            filtered, result = self.match(
                result, user
            )

        return filtered, result

    @classmethod
    def match(cls, result, user):
        # Apply global filters
        if not Filters.is_valid_user(user):
            # User didn't pass filters, update `account` attribute and return
            result['account'] = None

            return True, result

        # Find matching `UserRule`
        query = UserRule.select().where((
            (UserRule.name == user['title']) | (UserRule.name << ['*', None])
        ))

        rules = list(query.execute())

        if len(rules) == 1:
            # Process rule
            if rules[0].account_function is not None:
                result['account'] = cls.account_function(user, rules[0])
            else:
                result['account'] = rules[0].account_id
        else:
            result['account'] = None

        return False, result

    @staticmethod
    def account_function(user, rule):
        func = rule.account_function

        # Map
        if func == '@':
            # Try find matching `PlexAccount`
            plex_account = (PlexAccount
                .select()
                .where(PlexAccount.username == user['title'])
                .first()
            )

            log.debug('Mapped user %r to account %r', user['title'], plex_account.account_id)
            return plex_account.account_id

        return None


class UserManager(Manager):
    get = GetUser
    update = UpdateUser

    model = User

    @classmethod
    def parse_user(cls, user):
        if type(user) is not dict:
            # Build user dict from object
            user = {
                'key': user.id,
                'title': user.title,
                'thumb': user.thumb
            }

        # Validate `user`
        if not user.get('key'):
            return None

        return user
