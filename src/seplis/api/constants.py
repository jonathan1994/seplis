import re

LEVEL_USER = 0

LEVEL_EDIT_SHOW = 2

LEVEL_EDIT_USER = 3
LEVEL_SHOW_USER_EMAIL = LEVEL_EDIT_USER

LEVEL_GOD = 6

PER_PAGE = 25

EXTERNAL_TYPES = (
    'imdb',
    'thetvdb',
    'tvrage',
)
EXTERNAL_TYPE_NAMES = {
    'imdb': 'IMDb',
    'thetvdb': 'TheTVDB',
    'tvrage': 'TVRage',
}
EXTERNAL_REQUIRED_TYPES = (
    'imdb',
)

INDEX_TYPES = (
    ('info', (
        'thetvdb',
        'tvrage',
    )),
    ('episodes', (
        'thetvdb',
        'tvrage',
    )),
    ('images', (
        'thetvdb',
    ))
)

INDEX_TYPE_NAMES = {
    'info': 'Info',
    'episodes': 'Episodes',
    'images': 'Images',
}

IMAGE_RELATION_TYPE_SHOW = 1

IMAGE_TYPE_POSTER = 1
IMAGE_TYPES = {
    IMAGE_TYPE_POSTER: 'poster',
}

SHOW_SORT_FIELDS = (
    ('title', 'Title'),
    ('fans', 'Fans'),
    ('premiered', 'Premiered'),
)

USER_STAT_FIELDS = (
    'fan_of',
    'minutes_spent',
    'episodes_watched',
)