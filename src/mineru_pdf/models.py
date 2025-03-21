from typing import Optional

from sqlalchemy import BigInteger, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from .services import database


class Task(database.Model):

    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, nullable=False)
    uuid: Mapped[str] = mapped_column(String(128), nullable=False, default='', insert_default='')
    file_id: Mapped[str] = mapped_column(String(128), nullable=False, default='', insert_default='')
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False, default='', insert_default='')
    finetune_args: Mapped[str] = mapped_column(String(2048), nullable=False, default='', insert_default='')
    callback_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=False, default='', insert_default='')
    tarball_location: Mapped[str] = mapped_column(String(2048), nullable=False, default='', insert_default='')
    tarball_checksum: Mapped[str] = mapped_column(String(255), nullable=False, default='', insert_default='')
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='', insert_default='')
    result: Mapped[str] = mapped_column(String(32), nullable=False, default='', insert_default='')
    started_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP(True), nullable=True)
    finished_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP(True), nullable=True)
    created_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP(True), nullable=True)
    updated_at: Mapped[Optional[TIMESTAMP]] = mapped_column(TIMESTAMP(True), nullable=True)
