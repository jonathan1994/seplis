import os
import os.path
import yaml
import tempfile
from seplis import schemas

config = {
    'debug': False,
    'sentry_dsn': None,
    'api': {
        'database': 'sqlite:///seplis.db',    
        'redis': {
            'ip': '127.0.0.1',
            'port': 6379,
        },
        'elasticsearch': 'localhost:9200',
        'storitch': None,
        'port': 8002,
        'max_workers': 5,
    },
    'web': {
        'url': 'https://seplis.net',
        'cookie_secret': 'CHANGE_ME',
        'port': 8001,
        'image_url': 'https://images.seplis.net',
    },
    'logging': {
        'level': 'warning',
        'path': None,
        'max_size': 100 * 1000 * 1000,# ~ 95 mb
        'num_backups': 10,
    },
    'client': {
        'access_token': None,
        'thetvdb': None,
        'id': 'CHANGE_ME',
        'validate_cert': True,
        'api_url': 'https://api.seplis.net',
    },
    'play': {
        'database': 'sqlite:///seplis-play.db',
        'secret': None,
        'scan': None,
        'media_types': [
            'mp4',
            'mkv',
            'avi',            
        ],
        'ffmpeg_folder': '/usr/src/ffmpeg/',
        'port': 8003,
        'temp_folder': os.path.join(tempfile.gettempdir(), 'seplis-play'),
        'segment_time': 8,
        'session_timeout': 40, # Timeout for HLS sessions
        'devices':{
            'chrome': {
                'names':    [
                    'h264',
                    'webm',
                ],
                'default_codec': 'libx264',
                'type': 'stream',
            },
            'default': {
                'names':    [
                    'h264',
                ],
                'default_codec': 'libx264',
                'type': 'stream',
            },
            'apple': {
                'names':    [
                    'h264',
                ],
                'default_codec': 'libx264',
                'type': 'hls',
            },
        }, 
        'x-accel': False,
    }
}

def load(path=None):
    default_paths = [
        './seplis.yaml',
        '~/seplis.yaml',
        '/etc/seplis/seplis.yaml',
        '/etc/seplis.yaml',
    ]
    if not path:
        path = os.environ.get('SEPLIS_CONFIG', None)
        if not path:
            for p in default_paths:
                p = os.path.expanduser(p)
                if os.path.isfile(p):
                    path = p
                    break
    if not path:
        raise Exception('No config file specified.')
    if not os.path.isfile(path):
        raise Exception('Config: "{}" could not be found.'.format(path))
    with open(path) as f:
        data = yaml.load(f)
    for key in data:
        if key in config:
            if isinstance(config[key], dict):
                config[key].update(data[key])
            else:
                config[key] = data[key]
    if config['play']['scan']:# validate the play scan items
        schemas.Config_play_scan(
            config['play']['scan']
        )
    config['web']['url'] = config['web']['url'].rstrip('/')
    config['web']['image_url'] = config['web']['image_url'].rstrip('/')
    config['client']['api_url'] = config['client']['api_url'].rstrip('/')