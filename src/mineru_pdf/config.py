from pathlib import Path
from typing import Union, Optional


class Default_(object):

    def __init__(self, instance_path: Union[str, Path]) -> None:
        self.__instance_path = Path(instance_path)

    @property
    def APP_NAME(self) -> str:
        return 'mineru-pdf'

    @property
    def APP_URL(self) -> str:
        return 'http://localhost:5000'

    @property
    def TIMEZONE(self) -> str:
        return 'Asia/Shanghai'

    @property
    def SECRET_KEY(self) -> Optional[str]:
        return None

    @property
    def MAX_CONTENT_LENGTH(self) -> int:
        return 200 * 1024 * 1024

    ###
    ### Flask SQLAlchemy
    ###

    @property
    def SQLALCHEMY_DATABASE_URI(self)-> Optional[str]:
        return None

    ###
    ### Celery
    ###

    @property
    def CELERY_BROKER_URL(self) -> Optional[str]:
        return None

    @property
    def CELERY_BROKER_TRANSPORT_OPTIONS(self) -> Optional[str]:
        return None

    @property
    def CELERY_RESULT_BACKEND(self) -> Optional[str]:
        return None

    @property
    def CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS(self) -> Optional[str]:
        return None

    @property
    def FLASK_PYDANTIC_VALIDATION_ERROR_RAISE(self) -> bool:
        return True
