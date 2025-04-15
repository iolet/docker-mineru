import logging
import logging.config

from celery import Celery

from . import create_app


logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['console_stdout']
    },
    'loggers': {
        'src': {
            'level': 'DEBUG',
            'handlers': [ 'console_stdout' ],
            'propagate': False
        },
    },
    'handlers': {
        'console_stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': 'ext://sys.stdout'
        },
    },
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(thread)d] [%(name)s::%(funcName)s:L%(lineno)d] [%(levelname)s] %(message)s',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter'
        }
    }
})

app: Celery = create_app().extensions["celery"]
