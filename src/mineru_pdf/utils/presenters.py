from marshmallow import Schema, fields, EXCLUDE

from ..models import Task
from ..utils.task import Status


class TaskSchema(Schema):

    file_id = fields.String()
    status = fields.String()
    started_at = fields.DateTime()
    finished_at = fields.DateTime()
    tarball = fields.Method('to_tarball')

    def to_tarball(self, task: Task):
        return {
            'location': task.tarball_location,
            'checksum': task.tarball_checksum,
        } if Status.COMPLETED == task.status else None

    class Meta:
        unknown = EXCLUDE
