import logging

import requests

from django.shortcuts import redirect
from django.utils.http import urlquote

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from social_core.pipeline.social_auth import associate_by_email
from social_core.exceptions import (AuthAlreadyAssociated, SocialAuthBaseException)
from social_django.middleware import SocialAuthExceptionMiddleware

ANONYMOUS_AVATAR = '/static/images/header/avatar.png'
(NO_AVATAR, GRAVATAR, TWITTER, PRIVATETAR) = (0, 1, 2, 4)
AVATARS = (NO_AVATAR, GRAVATAR, TWITTER, PRIVATETAR)

logger = logging.getLogger(__name__)

def pic_storage_url(user, backend, url):
    pic_file_name = '/pic/{}/{}'.format(backend, user)
    # download cover image to cover_file
    try:
        r = requests.get(url)
        pic_file = ContentFile(r.content)
        content_type = r.headers.get('content-type', '')
        if u'text' in content_type:
            logger.warning('Cover return text for pic_url={}'.format(url))
            return None
        pic_file.content_type = content_type
        default_storage.save(pic_file_name, pic_file)
        return default_storage.url(pic_file_name)
    except Exception as e:
        # if there is a problem, return None for cover URL
        logger.warning('Failed to store cover for username={}'.format(user))
        return None


def selectively_associate_by_email(backend, details, user=None, *args, **kwargs):
     return associate_by_email(backend, details, user=None, *args, **kwargs)


def deliver_extra_data(backend, user, social, response, *args, **kwargs):
    pass

# following is needed because of length limitations in a unique constrain for MySQL
def chop_username(username, *args, **kwargs):
    if username and len(username) > 222:
        return {'username':username[0:222]}

def selective_social_user(backend, uid, user=None, *args, **kwargs):
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    if social:
        if user and social.user != user:
            msg = 'This {0} account is already in use.'.format(provider)
            raise AuthAlreadyAssociated(backend, msg)
        elif not user:
            user = social.user
    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': False}

# https://stackoverflow.com/a/19361220
# adapting https://github.com/omab/python-social-auth/blob/v0.2.10/social/apps/django_app/middleware.py#L25

class SocialAuthExceptionMiddlewareWithoutMessages(SocialAuthExceptionMiddleware):
    """
    a modification of SocialAuthExceptionMiddleware to pass backend and message without
    attempting django.messages
    """
    def process_exception(self, request, exception):

        if isinstance(exception, SocialAuthBaseException):
            backend = getattr(request, 'backend', None)
            backend_name = getattr(backend, 'name', 'unknown-backend')

            message = self.get_message(request, exception)
            logger.warning(message)

            url = self.get_redirect_uri(request, exception)
            url += ('?' in url and '&' or '?') + \
                   'message={0}&backend={1}'.format(urlquote(message),
                                                    backend_name)
            return redirect(url)
