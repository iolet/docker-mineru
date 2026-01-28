from marshmallow import EXCLUDE, Schema, fields, post_dump

from .constants import TaskStatus
from .models import Task


class TaskSchema(Schema):

    @post_dump
    def remove_none_values(self, data, **kwargs):
        """
        for more details, see https://github.com/marshmallow-code/marshmallow/issues/229#issuecomment-134387999
        """
        return { k: v for k, v in data.items() if v is not None }

    class Meta:
        unknown = EXCLUDE

    file_id = fields.String()
    status = fields.String()
    result = fields.String()
    errors = fields.String()
    started_at = fields.DateTime()
    finished_at = fields.DateTime()
    tarball = fields.Method('to_tarball')

    def to_tarball(self, task: Task):
        return {
            'location': task.tarball_location,
            'checksum': task.tarball_checksum,
        } if TaskStatus.COMPLETED == task.status else None
