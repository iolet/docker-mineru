from enum import StrEnum
from typing import Annotated
from re import sub as preg_replace

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, AfterValidator, field_validator
from werkzeug.datastructures import FileStorage


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
    VLM_VLLM_ENGINE = 'vlm-vllm-engine'
    VLM_HTTP_CLIENT = 'vlm-http-client'
    HYBRID_AUTO_ENGINE = 'hybrid-auto-engine'
    HYBRID_VLLM_ENGINE = 'hybrid-vllm-engine'
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

class FileParseForm(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    file: FileStorage
    parser_engine: Annotated[ParserEngines, Field(max_length=64, default=None)]
    parser_prefer: Annotated[ParserPrefers, Field(max_length=64, default=None)]
    target_language: Annotated[TargetLanguages, Field(max_length=32, default=None)]
    enable_table: Annotated[bool, Field(default=None)]
    enable_formula: Annotated[bool, Field(default=None)]
    apply_scaled: Annotated[bool, Field(default=False)]

    return_md: Annotated[bool, Field(default=True)]
    return_info: Annotated[bool, Field(default=True)]
    return_content_list: Annotated[bool, Field(default=True)]
    return_layout: Annotated[bool, Field(default=True)]
    return_images: Annotated[bool, Field(default=True)]

    @field_validator("file")
    def validate_file(cls, v: FileStorage):

        if not isinstance(v, FileStorage):
            raise TypeError("file must be a FileStorage")

        if not v.filename:
            raise ValueError("file is required")

        ext = v.filename.rsplit(".", 1)[-1].lower() if "." in v.filename else ""
        if 'pdf' != ext:
            raise ValueError(f"unsupported file extension {ext}")
        if 'application/pdf' != v.mimetype:
            raise ValueError(f"unsupported mimetype: {v.mimetype}")

        return v

class TaskRequest(BaseModel):

    file_url: Annotated[HttpUrl, Field(max_length=2048)]
    file_id: Annotated[str, Field(max_length=128), AfterValidator(safe_fileid)]
    parser_engine: Annotated[ParserEngines, Field(max_length=64, default=None)]
    parser_prefer: Annotated[ParserPrefers, Field(max_length=64, default=None)]
    target_language: Annotated[TargetLanguages, Field(max_length=32, default=None)]
    enable_table: Annotated[bool, Field(default=None)]
    enable_formula: Annotated[bool, Field(default=None)]
    apply_scaled: Annotated[bool, Field(default=None)]
    callback_url: Annotated[HttpUrl, Field(default=None)]
