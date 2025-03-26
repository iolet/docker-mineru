from pathlib import Path

import click
from filename_sanitizer import sanitize_path_fragment
from flask import Blueprint

from ..utils.magicpdf import parse_pdf


extraction = Blueprint('cli_extract', __name__, cli_group=None)

@extraction.cli.command('extract')
@click.argument('input_file', type=click.Path(exists=True, dir_okay=False, file_okay=True))
@click.argument('output_dir', type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option('-t', '--table', type=click.BOOL, help='Enable table parser')
@click.option('-f', '--formula', type=click.BOOL, help='Enable formal parser')
def extract(input_file, output_dir, table, formula):
    """
    Extract contents from file (supported many types)
    """

    src_file: Path = Path(input_file)
    click.echo(f'input from {src_file}...')

    dest_path: Path = Path(output_dir).joinpath(
        sanitize_path_fragment(src_file.name)
    ).with_suffix('')

    if dest_path.exists():
        click.echo(f'dir {dest_path} exist, this is maybe a issue, abort', err=True)
        return 3

    dest_path.mkdir()

    parse_pdf(src_file, dest_path, formula_enable=formula, table_enable=table)

    click.echo(f'output to {dest_path}.')

    return 0
