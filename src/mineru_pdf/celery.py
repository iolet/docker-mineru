import logging
import logging.config

from celery import Celery
from celery.schedules import crontab

from . import create_app
from .tasks.miner import prune_archives, remove_workdir


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

@app.on_after_configure.connect # type: ignore
def setup_periodic_tasks(sender: Celery, **kwargs):

    # Remove workdir every day at 18:17
    sender.add_periodic_task(
        crontab(hour=18, minute=17), remove_workdir.signature() # type: ignore
    )

    # Prune archives every day at 06:07
    sender.add_periodic_task(
        crontab(hour=6, minute=7), prune_archives.signature() # type: ignore
    )
