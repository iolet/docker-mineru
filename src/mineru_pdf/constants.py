from enum import StrEnum

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
