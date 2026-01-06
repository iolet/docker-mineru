from json import loads as json_loads
from json.decoder import JSONDecodeError
from typing import Union

from celery import Celery, Task
from flask import Flask

def integrate_celery(app: Flask) -> Celery:

    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    def try_decode_json(json: str) -> Union[dict, str]:
        try:
            return json_loads(json)
        except JSONDecodeError:
            return json

    celery_app = Celery(app.name, task_cls=FlaskTask)

    prefix: str = 'CELERY_'
    config: dict = {
        k.removeprefix(prefix).lower(): try_decode_json(v)
        for k, v in app.config.items()
        if k.startswith(prefix) and v is not None
    }

    options: dict = config.get('result_backend_transport_options', {})

    if options.get('global_keyprefix', '').isspace():
        config.update({
            'result_backend_transport_options': {
                'global_keyprefix': app.config['APP_NAME'] + '_celery-result_'
            }
        })

    config['broker_connection_retry_on_startup'] = True
    config['worker_hijack_root_logger'] = False

    celery_app.config_from_object(config)
    celery_app.set_default()

    app.extensions["celery"] = celery_app

    return celery_app
