""" handle caching and thumbnailing of covers """

import logging

from django.utils.functional import LazyObject

import sorl

from sorl.thumbnail import get_thumbnail as sorl_get_thumbnail

from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.conf import settings, defaults as default_settings
from sorl.thumbnail.helpers import get_module_class
from sorl.thumbnail.images import BaseImageFile, ImageFile
from sorl.thumbnail import default

import regluit

logger = logging.getLogger(__name__)

DEFAULT_COVER_LARGE = '/static/images/generic_cover_full.png'
DEFAULT_COVER = '/static/images/generic_cover_larger.png'
DEFAULT_COVER_SMALL = '/static/images/generic_cover_thumb.png'

_storage = None

class Storage(LazyObject):
    '''
    Monkey patch to fix S3 backend slowness in sorl.thumbnail
    https://github.com/jazzband/sorl-thumbnail/issues/301
    '''
    def _setup(self):
        global _storage
        if not _storage:
            _storage = get_module_class(settings.THUMBNAIL_STORAGE)()

        self._wrapped = _storage

sorl.thumbnail.default.storage = Storage()


class DefaultImageFile(BaseImageFile):
    is_default = True

    def __init__(self, geometry_string='x550'):
        if geometry_string == '128':
            self._url = DEFAULT_COVER
            self.size = (131, 192)
        elif geometry_string == 'x80':
            self._url = DEFAULT_COVER_SMALL
            self.size = (55, 80)
        else:
            self._url = DEFAULT_COVER_LARGE
            self.size = (376, 550)

    @property
    def url(self):
        return self._url

    def exists(self):
        return True

class ReadOnlyThumbnailBackend(ThumbnailBackend):
    """
    A backend that never makes a new thumbnail, but adds missing thumbnails to a task queue
    """

    def get_thumbnail(self, file_, geometry_string, **options):
        """
        Returns thumbnail as an ImageFile instance for file with geometry and
        options given. It will try to get it from the key value store,
        otherwise return a Dummy.
        """
        logger.debug('Getting thumbnail for file [%s] at [%s]', file_, geometry_string)

        if file_:
            source = ImageFile(file_)
        else:
            raise ValueError('falsey file_ argument in get_thumbnail()')

        # preserve image filetype
        if settings.THUMBNAIL_PRESERVE_FORMAT:
            options.setdefault('format', self._get_format(source))

        for key, value in self.default_options.items():
            options.setdefault(key, value)

        for key, attr in self.extra_options:
            value = getattr(settings, attr)
            if value != getattr(default_settings, attr):
                options.setdefault(key, value)

        name = self._get_thumbnail_filename(source, geometry_string, options)
        thumbnail = ImageFile(name, default.storage)
        cached = default.kvstore.get(thumbnail)

        if cached:
            setattr(cached, 'is_default', False)
            return cached

        logger.info('tasking a new thumbnail for %s, %s', file_, geometry_string)
        regluit.core.tasks.make_cover_thumbnail.delay(file_, geometry_string, **options)
        return DefaultImageFile(geometry_string)


backend = ReadOnlyThumbnailBackend()
get_thumbnail = backend.get_thumbnail

def make_cover_thumbnail(url, geometry_string, **options):
    try:
        im = sorl_get_thumbnail(url, geometry_string, **options)
    except (IOError, OSError):
        logger.error('couldnt make thumbnail for %s, probably UnidentifiedImageError', url)
        return False
    
    if im.exists():
        return True
    logger.error('couldnt make thumbnail for %s, got non-existent im', url)
    return False
