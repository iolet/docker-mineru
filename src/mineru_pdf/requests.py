from enum import Enum
from typing import Annotated
from pydantic import AfterValidator, BaseModel, Field, HttpUrl
from re import sub as preg_replace


def safe_fileid(value):
    if not preg_replace(r'[a-zA-z0-9-_.@]', '', value).isspace():
        raise ValueError(
            f'value {value} should be ensure contain '
            f'alphabets, numbers, dashes, underscore, '
            f'dot and at sign only'
        )

    return value

class LangEnum(str, Enum):
    ch = 'zh'
    en = 'en'

class TaskRequest(BaseModel):

    file_url: Annotated[HttpUrl, Field(max_length=2048, is_required=True)]
    file_id: Annotated[str, Field(max_length=128, is_required=True), AfterValidator(safe_fileid)]
    apply_ocr: Annotated[bool, Field(is_required=False, default=True)]
    enable_table: Annotated[bool, Field(is_required=False, default=False)]
    enable_formula: Annotated[bool, Field(is_required=False, default=False)]
    prefer_language: LangEnum = LangEnum.ch
    callback_url: Annotated[HttpUrl, Field(is_required=False, default=None)]
