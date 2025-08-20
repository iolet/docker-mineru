import json
import logging
import os
from pathlib import Path
from re import search as re_search
from typing import Dict, Union

import torch
from mineru.data.data_reader_writer import FileBasedDataReader
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipe_doc_analyze
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze

from .fileguard import ImgWriter, TxtWriter
from ..tasks.exceptions import CUDANotAvailableError, GPUOutOfMemoryError


logger = logging.getLogger(__name__)

def tune_spell(input_args: dict) -> dict:

    input_args.setdefault('model_type', 'pipe')
    if input_args['model_type'] not in [ 'pipe', 'vlm' ]:
        raise RuntimeError(
            f'unknown model_type {input_args["model_type"]},'
            f'supported value are pipe (default) and vlm'
        )

    result_args: dict = {}

    if 'pipe' == input_args['model_type']:

        input_args.setdefault('parse_prefer', 'auto')
        if input_args['parse_prefer'] not in [ 'auto', 'ocr', 'txt' ]:
            raise RuntimeError(
                f'unknown parse_prefer {input_args["parse_prefer"]},'
                f'supported value are auto (default), ocr (for many picture)'
                f'and txt (text only)'
            )
        result_args['parse_method'] = input_args['parse_prefer']

        input_args.setdefault('target_language', 'ch')
        if input_args['target_language'] not in [ 'ch', 'en' ]:
            raise RuntimeError(
                f'unknown target_language {input_args["target_language"]},'
                f'supported value are ch (chinese) and en (english)'
            )
        result_args['lang_list'] = [ input_args['target_language'] ]

        input_args.setdefault('enable_formula', False)
        if not isinstance(input_args['enable_formula'], bool):
            raise RuntimeError(
                'invalid type for enable_formula, only supported True and False'
            )
        result_args['formula_enable'] = input_args['enable_formula']

        input_args.setdefault('enable_table', True)
        if not isinstance(input_args['enable_table'], bool):
            raise RuntimeError(
                'invalid type for enable_table, only supported True and False'
            )
        result_args['table_enable'] = input_args['enable_table']

    if 'vlm' == input_args['model_type']:

        input_args.setdefault('backend_handler', 'transformers')
        if input_args['backend_handler'] not in [ 'transformers', 'sglang-client', ]:
            raise RuntimeError(
                f'unknown backend_handler {input_args["backend_handler"]},'
                f'supported value are transformers (default), sglang-client'
                f'and sglang-engine'
            )
        result_args['backend'] = input_args['backend_handler']

        input_args.setdefault('enable_formula', False)
        if not isinstance(input_args['enable_formula'], bool):
            raise RuntimeError(
                'invalid type for enable_formula, only supported True and False'
            )
        os.environ['MINERU_VLM_FORMULA_ENABLE'] = str(input_args['enable_formula'])

        input_args.setdefault('enable_table', True)
        if not isinstance(input_args['enable_table'], bool):
            raise RuntimeError(
                'invalid type for enable_table, only supported True and False'
            )
        os.environ['MINERU_VLM_TABLE_ENABLE'] = str(input_args['enable_table'])

    return result_args

def magic_file(input_file: Path, output_dir: Path,  **tune_args: Dict[str, Union[str, bool, None]]) -> None:

    txt_dir = output_dir.resolve()
    if not txt_dir.exists() or txt_dir.is_file():
        raise RuntimeError(
            f'output dir {output_dir} does not exist or it is not a directory'
        )

    img_dir = output_dir.joinpath('images').resolve()
    if not img_dir.exists():
        img_dir.mkdir()

    img_writer = ImgWriter(img_dir)
    txt_writer = TxtWriter(txt_dir)

    ds: PymuDocDataset = PymuDocDataset(
        FileBasedDataReader().read(str(input_file))
    )

    if tune_args['ocr'] is None:
        tune_args['ocr'] = ds.classify() == SupportedPdfParseMethod.OCR

    try:

        # infer dataset
        inferred_result: InferenceResult = ds.apply(doc_analyze, **tune_args)

        # pipe result
        if tune_args['ocr']:
            pipped_result: PipeResult = inferred_result.pipe_ocr_mode(
                imageWriter=img_writer,
                start_page_id=tune_args.get('start_page_id', 0),
                end_page_id=tune_args.get('end_page_id', None),
                lang=tune_args.get('lang', None)
            )
        else:
            pipped_result: PipeResult = inferred_result.pipe_txt_mode(
                imageWriter=img_writer,
                start_page_id=tune_args.get('start_page_id', 0),
                end_page_id=tune_args.get('end_page_id', None),
                lang=tune_args.get('lang', None)
            )

    except (MemoryError, torch.OutOfMemoryError) as e:

        raise GPUOutOfMemoryError('GPU out of memory') from e

    except ValueError as e:

        pattern = r'Invalid\s+CUDA\s+\S+\s+requested.\s+Use\s+\S+\s+or\s+pass\s+valid\s+CUDA\s+device\(s\)\s+if\s+available'

        if re_search(pattern, str(e)):
            raise CUDANotAvailableError('CUDA invalid, maybe a driver issues') from e

        raise e

    finally:

        # we try release dataset first
        del ds

        # then try release gpu memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    # dump content list
    pipped_result.dump_content_list(txt_writer, 'content_list.json', img_dir)

    # dump markdown content
    pipped_result.dump_md(txt_writer, 'content.md', img_dir)

    # dump pipe result
    pipped_result.dump_middle_json(txt_writer, 'middle.json')

    # output model conf
    txt_writer.write_string(txt_dir.joinpath('model.json'), json.dumps(
        inferred_result.get_infer_res(), indent=2, ensure_ascii=False
    ))

    # enable review
    if 'enable_review' in tune_args:
        pipped_result.draw_layout(str(output_dir.joinpath('layout.pdf')))
        pipped_result.draw_span(str(output_dir.joinpath('spans.pdf')))
        pipped_result.draw_line_sort(str(output_dir.joinpath('line_sort.pdf')))
        inferred_result.draw_model(str(output_dir.joinpath('model.pdf')))

    # release memory
    del pipped_result
    del inferred_result
