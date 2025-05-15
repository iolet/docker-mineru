import sys
from pathlib import Path

import click
from flask import current_app


@click.group()
def storage():
    """Manage public storage"""

@storage.command('link')
def link():
    """
    Create the symbolic links configured for the application
    """

    src: Path = Path(current_app.instance_path).joinpath('archives')
    dst: Path = Path(current_app.instance_path).joinpath('public', 'archives')

    if not src.exists() or src.is_file():
        click.secho(f'the source directory {src} does not exists or it is a file', fg='red')
        sys.exit(1)

    if not dst.parent.exists():
        dst.parent.mkdir()

    if not dst.is_symlink():
        dst.symlink_to(src)

    click.secho(f'created {src} -> {dst}', fg='green')

    sys.exit(0)

@storage.command('unlink')
def unlink():
    """
    Remove the symbolic links configured for the application
    """

    link_: Path = Path(current_app.instance_path).joinpath('public', 'archives')

    if not link_.exists():
        click.secho(f'removed {link_} already', fg='green')
        sys.exit(0)

    if not link_.is_symlink():
        click.secho(f'{link_} is not symlink, it maybe a issue', fg='yellow')
        sys.exit(4)

    link_.unlink()
    click.secho(f'removed {link_}', fg='green')

    sys.exit(0)
