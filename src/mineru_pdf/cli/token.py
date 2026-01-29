import secrets
import sys
from pathlib import Path
from typing import Optional, Sequence

import arrow
import base58
import click
from flask import current_app
from sqlalchemy import select

from ..constants import TokenLabels
from ..extensions import database
from ..models import Bearer


@click.group()
def token():
    """Manage token authentication"""

@token.command('create')
@click.option('--owner', type=str, default='maintainer', help='Setup the token owner')
@click.option('--label',
              type=click.Choice([label.value for label in TokenLabels.__members__.values()]),
              multiple=True, help='For token usage')
def create(owner: Optional[str], label: Optional[tuple]):
    """Create a new token"""

    bearer = Bearer(
        owner=owner, # type: ignore
        token=base58.b58encode(secrets.token_bytes(48)).decode(), # type: ignore
        labels=', '.join(label or []), # type: ignore
        created_at=arrow.now(current_app.config.get('TIMEZONE')).datetime, # type: ignore
        updated_at=arrow.now(current_app.config.get('TIMEZONE')).datetime # type: ignore
    )

    database.session.add(bearer)
    database.session.commit()

    click.secho(f'token {bearer.token} with label(s) [{bearer.labels}] created successfully', fg='green')

    sys.exit(0)

@token.command('remove')
@click.argument('token')
@click.option('--force', type=bool, default=False, help='Force remove token, event multiple')
def remove(token: str, force: bool):
    """
    Remove the token
    """

    bearers: Sequence[Bearer] = database.session.scalars(
        select(Bearer).where(Bearer.token.like(f'{token}%')).order_by(Bearer.id.desc())
    ).all()

    if len(bearers) < 1:
        click.secho(f'token like {token} has been removed already', fg='green')
        sys.exit(0)

    if len(bearers) > 1:
        if force:
            for bearer in bearers:
                database.session.delete(bearer)
            database.session.commit()
            click.secho(f'token like {token} has been force removed successfully', fg='green')
            sys.exit(0)
        else:
            raise click.ClickException('multiple same token found')

    database.session.delete(bearers[0])
    database.session.commit()
    click.secho(f'token like {token} has been removed successfully', fg='green')
    sys.exit(0)
