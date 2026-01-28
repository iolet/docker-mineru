from pathlib import Path

import click
from filename_sanitizer import sanitize_path_fragment

from ..constants import ParserEngines, ParserPrefers, TargetLanguages


@click.command('parse')
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False, file_okay=True))
@click.argument('output_dir', type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option('-e', '--engine', type=click.Choice(ParserEngines, case_sensitive=False), default=ParserEngines.PIPELINE)
@click.option('-p', '--prefer', type=click.Choice(ParserPrefers, case_sensitive=False), default=ParserPrefers.AUTO)
@click.option('-l', '--lang', type=click.Choice(TargetLanguages, case_sensitive=False), default=TargetLanguages.CH)
@click.option('-t', '--table', type=click.BOOL, help='Enable table parser', default=False)
@click.option('-f', '--formula', type=click.BOOL, help='Enable formal parser', default=False)
def parse_file(
    input_file: Path, output_dir: Path, engine: ParserEngines,
    prefer: ParserPrefers, lang: TargetLanguages, table: bool, formula: bool
):
    """Extract PDF document blocks"""

    src_file: Path = Path(input_file)
    click.echo(f'input from {src_file}...')

    dest_path: Path = Path(output_dir).joinpath(
        sanitize_path_fragment(src_file.name)
    ).with_suffix('')

    if dest_path.exists():
        click.echo(f'dir {dest_path} exist, this is maybe a issue, abort', err=True)
        return 3

    dest_path.mkdir()

    if 'magic_file' not in globals():
        from ..utils.magicfile import magic_file

    magic_file(src_file, dest_path, **{ # type: ignore
        'backend': engine.value,
        'parse_method': prefer.value,
        'lang_list': [ lang.value ],
        'formula_enabled': formula,
        'table_enabled': table,
    })

    click.echo(f'output to {dest_path}.')

    return 0
