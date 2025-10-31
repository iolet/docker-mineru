import os
from pathlib import Path
from typing import Union, Optional

from dotenv import dotenv_values
from sqlalchemy import URL

class Default_(object):

    def __init__(
        self,
        instance_path: Union[str, Path],
        env_file: Optional[Union[Path, str]] = None
    ) -> None:
        self.__instance_path = Path(instance_path)
        self.env_pair = {}

        if env_file is not None and os.access(env_file, os.R_OK):
            self.env_pair = dotenv_values(env_file)

    @property
    def APP_NAME(self) -> str:
        return self.env_pair.get('APP_NAME') or 'flask'

    @property
    def APP_URL(self) -> str:
        return self.env_pair.get('APP_URL') or 'http://localhost:5000'

    @property
    def SECRET_KEY(self) -> Optional[str]:
        return self.env_pair.get('APP_KEY')

    @property
    def TIMEZONE(self) -> str:
        return self.env_pair.get('TIMEZONE') or 'Asia/Shanghai'

    @property
    def MAX_CONTENT_LENGTH(self) -> int:
        return 200 * 1024 * 1024

    ###
    ### Flask SQLAlchemy
    ###

    @property
    def DB_DRIVER(self) -> str:
        return self.env_pair.get('DB_DRIVER') or 'sqlite'

    @property
    def DB_HOST(self) -> Optional[str]:
        return self.env_pair.get('DB_HOST')

    @property
    def DB_PORT(self) -> Optional[int]:
        port_str = self.env_pair.get('DB_PORT')
        return port_str if port_str is None else int(port_str)

    @property
    def DB_DATABASE(self) -> Optional[str]:

        db = self.env_pair.get('DB_DATABASE')

        if not db and 'sqlite' in self.DB_DRIVER:
            return 'db.sqlite3'

        return db

    @property
    def DB_USERNAME(self) -> Optional[str]:
        return self.env_pair.get('DB_USERNAME')

    @property
    def DB_PASSWORD(self) -> Optional[str]:
        return self.env_pair.get('DB_PASSWORD')

    @property
    def SQLALCHEMY_DATABASE_URI(self)-> Optional[str]:

        if 'sqlite' in self.DB_DRIVER and isinstance(self.DB_DATABASE, str):
            return f'{self.DB_DRIVER}:///file:{self.DB_DATABASE}?uri=true'

        return URL.create(
            drivername=self.DB_DRIVER,
            username=self.DB_USERNAME,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_DATABASE
        ).render_as_string(False)

    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> dict:
        return {
            'max_overflow': 10, 'pool_size': 100,
            'pool_recycle': 2688, 'pool_pre_ping': True
        }

    ###
    ### Celery
    ###

    @property
    def CELERY_BROKER_URL(self) -> Optional[str]:
        return self.env_pair.get('CELERY_BROKER_URL')

    @property
    def CELERY_BROKER_TRANSPORT_OPTIONS(self) -> Optional[str]:
        return self.env_pair.get('CELERY_BROKER_TRANSPORT_OPTIONS')

    @property
    def CELERY_RESULT_BACKEND(self) -> Optional[str]:
        return self.env_pair.get('CELERY_RESULT_BACKEND')

    @property
    def CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS(self) -> Optional[str]:
        return self.env_pair.get('CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS')

    @property
    def FLASK_PYDANTIC_VALIDATION_ERROR_RAISE(self) -> bool:

        bool_str = self.env_pair.get('FLASK_PYDANTIC_VALIDATION_ERROR_RAISE') or 'false'

        if bool_str in [ 'true', 'yes' ]:
            return True

        if bool_str in [ 'false', 'no' ]:
            return False

        raise ValueError(f'unsupported value {bool_str}, only support: true yes false no')
