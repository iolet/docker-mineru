__version__ = '0.0.1'

def create_app():

    # create flask instance
    from flask import Flask
    from os import environ
    app = Flask(
        import_name=__name__,
        instance_path=environ.get('FLASK_INSTANCE_DIR', default=None),
        instance_relative_config=True
    )

    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # setup configuration
    from .config import Default_
    app.config.from_object(Default_(app.instance_path))

    from dotenv import dotenv_values
    from pathlib import Path
    env_file = Path('.').resolve().joinpath('.env')
    if env_file.exists() and env_file.is_file():
        app.config.from_mapping(dotenv_values(env_file))

    # init essential components
    from .services import database, migrate
    database.init_app(app)
    migrate.init_app(
        app, db=database,
        directory=Path(app.root_path).joinpath('migrations'), # type: ignore
        render_as_batch=True
    )

    # register commands
    from .cli.extraction import extract
    from .cli.storage import storage
    app.cli.add_command(extract)
    app.cli.add_command(storage)

    # register blueprint
    from .api.v4.tasks import tasks
    app.register_blueprint(tasks, url_prefix='/api/v4')

    # register fallback handler
    from .api import handle_server_error
    app.register_error_handler(Exception, handle_server_error) # type: ignore

    # integrate celery with flask
    from .utils.integrators import integrate_celery
    integrate_celery(app)

    app.logger.info(f'Current Instance Path -> {app.instance_path}')

    return app
