import logging
import os
import signal

from flask import Flask, appcontext_tearing_down, g

logger = logging.getLogger(__name__)


def term_if_gpu_oom(sender: Flask, **extra):
    if g.is_gpu_oom:
        os.kill(os.getpid(), signal.SIGTERM)

def connect_subscribers(app: Flask):
    appcontext_tearing_down.connect(term_if_gpu_oom, app)
