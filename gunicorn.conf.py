import os
from datetime import time
from pathlib import Path
from pytz import timezone

# loading target application
wsgi_app = 'src.mineru_pdf:create_app()'

# listen address and port
bind = [ f'{os.getenv("BIND", "127.0.0.1:18089")}']

# worker process
workers = int(os.getenv('WORKERS', 4))

# maximum number of requests a worker will process before restarting
max_requests = int(os.getenv('MAX_REQUESTS', 200))

# maximum jitter to add the max_requests
max_requests_jitter = int(max_requests * 0.1)

# pretty process naming
proc_name = 'mineru_pdf'

# does not daemonize, avoid supervisor missing status track and
# try restarting again until fails
daemon = False

# recommended use memory filesystem path to avoid slow response
worker_tmp_dir = '/tmp'

# workers silent for more than this may seconds are killed and restarted
timeout = int(os.getenv('TIMEOUT', 7200))

# logging handle global, added thread number and logger name
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['console_stdout']
    },
    'loggers': {
        'src': {
            'level': 'INFO',
            'handlers': ['application'],
            'propagate': True
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['access_log'],
            'propagate': True,
            'qualname': 'gunicorn.access'
        },
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['console_stdout'],
            'propagate': True,
            'qualname': 'gunicorn.error'
        }
    },
    'handlers': {
        'application': {
            'class': 'concurrent_log_handler.ConcurrentTimedRotatingFileHandler',
            'formatter': 'generic',
            'filename': Path(__file__).parent.joinpath('instance', 'logs', 'flask.log'),
            'when': 'midnight',
            'backupCount': 24,
            'delay': True,
            'atTime': time(tzinfo=timezone('Asia/Shanghai'))
        },
        'access_log': {
            'class': 'concurrent_log_handler.ConcurrentTimedRotatingFileHandler',
            'formatter': 'access_log',
            'filename': Path(__file__).parent.joinpath('instance', 'logs', 'access.log'),
            'when': 'midnight',
            'backupCount': 24,
            'delay': True,
            'atTime': time(tzinfo=timezone('Asia/Shanghai'))
        },
        'console_stdout': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': 'ext://sys.stdout'
        },
    },
    'formatters': {
        'access_log': {
            'format': '%(message)s"',
            'class': 'logging.Formatter'
        },
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(thread)d] [%(name)s::%(funcName)s:L%(lineno)d] [%(levelname)s] %(message)s',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter'
        }
    }
}

# set log level to info
loglevel = 'info'

# does not redirect access log to syslog
disable_redirect_access_to_syslog = True
