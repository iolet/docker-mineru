import sys
from pathlib import Path

import click
from flask import current_app
from flask import Blueprint


storage = Blueprint('cli_storage', __name__, cli_group='storage')

@storage.cli.command('link')
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

    click.secho(f'link {src} to {dst}', fg='green')

    sys.exit(0)

@storage.cli.command('unlink')
def unlink():
    """
    Remove the symbolic links configured for the application
    """

    link_: Path = Path(current_app.instance_path).joinpath('public', 'archives')

    if not link_.exists():
        click.secho(f'link {link_} already cleaned', fg='green')
        sys.exit(0)

    if not link_.is_symlink():
        click.secho(f'link {link_} is not symlink, it maybe a issue', fg='yellow')
        sys.exit(4)

    link_.unlink()
    click.secho(f'link {link_} has been cleaned', fg='green')

    sys.exit(0)
