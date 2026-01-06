from enum import StrEnum
from typing import Annotated
from pydantic import AfterValidator, BaseModel, Field, HttpUrl
from re import sub as preg_replace


def safe_fileid(value):
    result: str = preg_replace(r'[a-zA-z0-9-_.@]+', '', value)
    if (not result.isspace()) and len(result) > 0:
        raise ValueError(
            f'value {value} should be ensure contain '
            f'alphabets, numbers, dashes, underscore, '
            f'dot and at sign only'
        )

    return value

class ParserEngines(StrEnum):
    PIPELINE = 'pipeline'
    VLM_AUTO_ENGINE = 'vlm-auto-engine'
    VLM_HTTP_CLIENT = 'vlm-http-client'
    HYBRID_AUTO_ENGINE = 'hybrid-auto-engine'
    HYBRID_HTTP_CLIENT = 'hybrid-http-client'

class ParserPrefers(StrEnum):
    AUTO = 'auto'
    TXT = 'txt'
    OCR = 'ocr'

class TargetLanguages(StrEnum):
    ARABIC = 'arabic'
    CH = 'ch'
    CHINESE_CHT = 'chinese_cht'
    CH_LITE = 'ch_lite'
    CH_SERVER = 'ch_server'
    CYRILLIC = 'cyrillic'
    DEVANAGARI = 'devanagari'
    EAST_SLAVIC = 'east_slavic'
    EL = 'el'
    EN = 'en'
    JAPAN = 'japan'
    KA = 'ka'
    KOREAN = 'korean'
    LATIN = 'latin'
    TA = 'ta'
    TE = 'te'
    TH = 'th'

class TaskRequest(BaseModel):

    file_url: Annotated[HttpUrl, Field(max_length=2048, is_required=True)]
    file_id: Annotated[str, Field(max_length=128, is_required=True), AfterValidator(safe_fileid)]
    parser_engine: Annotated[ParserEngines, Field(is_required=False, default=ParserEngines.HYBRID_AUTO_ENGINE)]
    parser_prefer: Annotated[ParserPrefers, Field(is_required=False, default=ParserPrefers.AUTO)]
    target_language: Annotated[TargetLanguages, Field(is_required=False, default=None)]
    enable_table: Annotated[bool, Field(is_required=False, default=True)]
    enable_formula: Annotated[bool, Field(is_required=False, default=False)]
    callback_url: Annotated[HttpUrl, Field(is_required=False, default=None)]
