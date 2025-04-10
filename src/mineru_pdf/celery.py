import logging
import logging.config

from . import create_app

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}

logging.config.dictConfig(LOGGING)

app = create_app().extensions["celery"]

app.conf.update(
    worker_hijack_root_logger=False
)
