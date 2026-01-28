import logging
import os
from pathlib import Path
from re import search as re_search
from typing import Dict, Union
from urllib.parse import ParseResult, urlparse

import torch
from toolz.dicttoolz import valfilter

from ..constants import ParserEngines, ParserPrefers, TargetLanguages
from ..exceptions import CUDANotAvailableException, GPUOutOfMemoryException

logger = logging.getLogger(__name__)


def magic_args(input_args: dict) -> Dict[str, Union[str, bool, None]]:

    logger.info(f'input args {input_args}')

    def is_nonempty(v: Union[bool, str, None]) -> bool:
        return not (v is None or (isinstance(v, str) and (len(v) < 1 or v.isspace())))

    input_args_: dict = valfilter(is_nonempty, input_args)
    output_args: dict = {}

    input_args_.setdefault('parser_engine', ParserEngines.HYBRID_HTTP_CLIENT.value)
    available_engines = [ member.value for name, member in ParserEngines.__members__.items() ]
    if input_args_['parser_engine'] not in available_engines:
        raise ValueError(
            f'unknown parser_engine {input_args_["parser_engine"]},'
            f'supported value are {", ".join(available_engines)}'
        )
    output_args['backend'] = input_args_['parser_engine']

    input_args_.setdefault('parser_prefer', ParserPrefers.AUTO.value)
    available_prefers = [ member.value for name, member in ParserPrefers.__members__.items() ]
    if input_args_['parser_prefer'] not in available_prefers:
        raise ValueError(
            f'unknown parser_prefer {input_args_["parser_prefer"]},'
            f'supported value are auto (default), ocr (for many picture)'
            f'and txt (text only)'
        )
    output_args['parse_method'] = input_args_['parser_prefer']

    input_args_.setdefault('target_language', TargetLanguages.CH.value)
    available_languages = [ member.value for name, member in TargetLanguages.__members__.items() ]
    if input_args_['target_language'] not in available_languages:
        raise ValueError(
            f'unknown target_language {input_args_["target_language"]},'
            f'supported value are { ', '.join(available_languages) }'
        )
    output_args['lang_list'] = [ input_args_['target_language'] ]

    input_args_.setdefault('enable_formula', False)
    if not isinstance(input_args_['enable_formula'], bool):
        raise ValueError(
            'invalid type for enable_formula, only supported True and False'
        )
    output_args['formula_enabled'] = input_args_['enable_formula']
    os.environ['MINERU_VLM_FORMULA_ENABLE'] = str(input_args_['enable_formula'])

    input_args_.setdefault('enable_table', True)
    if not isinstance(input_args_['enable_table'], bool):
        raise ValueError(
            'invalid type for enable_table, only supported True and False'
        )
    output_args['table_enabled'] = input_args_['enable_table']
    os.environ['MINERU_VLM_TABLE_ENABLE'] = str(input_args_['enable_table'])

    if output_args['backend'].endswith('client'):
        vllm_endpoint: ParseResult = urlparse(input_args_.get('vllm_endpoint') or '')
        if vllm_endpoint.scheme not in [ 'http', 'https' ] or vllm_endpoint.hostname is None:
            raise ValueError(
                'vllm_endpoint scheme unknown or invalid, only supported http and https'
            )
        output_args['server_url'] = vllm_endpoint.geturl()

    input_args_.setdefault('apply_scaled', False)
    if not isinstance(input_args_['apply_scaled'], bool):
        raise ValueError(
            'invalid type for apply_scaled, only supported True and False'
        )
    output_args['apply_scaled_output'] = input_args_['apply_scaled']

    logger.info(f'output args {output_args}')

    return output_args

def magic_file(input_file: Path, output_dir: Path,  **magic_kwargs: Dict[str, Union[str, bool, None]]) -> None:

    logger.info(f'input file: {input_file}')
    logger.info(f'output dir: {output_dir}')

    save_dir = output_dir.resolve()
    if not save_dir.exists() or save_dir.is_file():
        raise ValueError(
            f'output dir {save_dir} does not exist or it is not a directory'
        )

    if 'do_parse' not in globals():
        from .mineru import do_parse, read_fn

    try:
        do_parse( # type: ignore
            output_dir=save_dir.resolve(),
            pdf_file_names=[ input_file.name ],
            pdf_bytes_list=[ read_fn(input_file) ], # type: ignore
            p_lang_list=magic_kwargs.get('lang_list'), # type: ignore
            backend=magic_kwargs.get('backend'), # type: ignore
            parse_method=magic_kwargs.get('parse_method'), # type: ignore
            formula_enable=magic_kwargs.get('formula_enabled'), # type: ignore
            table_enable=magic_kwargs.get('table_enabled'), # type: ignore
            server_url=magic_kwargs.get('server_url'),
            f_draw_layout_bbox=magic_kwargs.get('enable_review', False), # type: ignore
            f_dump_orig_pdf=magic_kwargs.get('enable_review', False), # type: ignore
            apply_scaled_output=magic_kwargs.get('apply_scaled_output', False)
        )
    except (MemoryError, torch.OutOfMemoryError) as e:
        raise GPUOutOfMemoryException('GPU out of memory') from e
    except ValueError as e:
        pattern = r'Invalid\s+CUDA\s+\S+\s+requested.\s+Use\s+\S+\s+or\s+pass\s+valid\s+CUDA\s+device\(s\)\s+if\s+available'
        if re_search(pattern, str(e)):
            raise CUDANotAvailableException('CUDA invalid, maybe a driver issues') from e
        raise e
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    logger.info(f'saved in: {save_dir}')
