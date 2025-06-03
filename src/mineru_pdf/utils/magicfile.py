import json
import logging
from pathlib import Path
from re import search as re_search

import torch
from magic_pdf.data.data_reader_writer import FileBasedDataReader, FileBasedDataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult

from ..tasks.exceptions import CUDANotAvailableError, GPUOutOfMemoryError


logger = logging.getLogger(__name__)

def tune_spell(input_args: dict) -> dict:

    input_args.setdefault('apply_ocr', True)
    if not isinstance(input_args['apply_ocr'], bool):
        input_args['apply_ocr'] = True

    input_args.setdefault('target_language', None)
    if input_args['target_language'] not in [ None, 'ch', 'en' ]:
        raise RuntimeError(
            f'unknown target_language {input_args["target_language"]},'
            f'supported value are ch (chinese) and en (english)'
        )

    input_args.setdefault('enable_formula', None)
    if not isinstance(input_args['enable_formula'], (bool, None)):
        raise RuntimeError(
            'invalid type for enable_formula, only supported True, False and None'
        )

    input_args.setdefault('enable_table', None)
    if not isinstance(input_args['enable_table'], (bool, None)):
        raise RuntimeError(
            'invalid type for enable_table, only supported True, False and None'
        )

    return {
        'ocr': input_args['apply_ocr'],
        'lang': input_args['target_language'],
        'formula_enable': input_args['enable_formula'],
        'table_enable': input_args['enable_table'],
        # TODO layout model name depended by outside config,
        #      current disabled because unable checking
        'layout_model': None
    }

def magic_file(input_file: Path, output_dir: Path,  **tune_args: dict) -> None:

    if 'ocr' not in tune_args:
        raise RuntimeError('key ocr not found, please ensure exists and try again')

    txt_dir = output_dir.resolve()
    if not txt_dir.exists() or txt_dir.is_file():
        raise RuntimeError(
            f'output dir {output_dir} does not exist or it is not a directory'
        )

    img_dir = output_dir.joinpath('images').resolve()
    if not img_dir.exists():
        img_dir.mkdir()

    img_writer = FileBasedDataWriter(str(img_dir))
    txt_writer = FileBasedDataWriter(str(txt_dir))

    ds: PymuDocDataset = PymuDocDataset(
        FileBasedDataReader().read(str(input_file))
    )

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
