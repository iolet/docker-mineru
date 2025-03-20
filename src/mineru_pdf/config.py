from pathlib import Path
from typing import Union, Optional


class Default_(object):

    def __init__(self, instance_path: Union[str, Path]) -> None:
        self.__instance_path = Path(instance_path)

    @property
    def APP_NAME(self) -> str:
        return 'mineru_pdf'

    @property
    def TIMEZONE(self) -> str:
        return 'Asia/Shanghai'

    @property
    def SECRET_KEY(self) -> Optional[str]:
        return None


    ###
    ### Flask SQLAlchemy
    ###

    @property
    def SQLALCHEMY_DATABASE_URI(self)-> Optional[str]:
        return None
