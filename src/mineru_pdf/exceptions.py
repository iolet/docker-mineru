
from enum import StrEnum

class ExtraErrorCodes(StrEnum):
    """Extra error code collection"""

    NONE_ = 'None'
    INTERNAL_ERROR = 'InternalError'

    ACCESS_DENIED = 'AccessDenied'
    ACCESS_FORBIDDEN = 'AccessForbidden'
    UNKNOWN_PROVIDER = 'UnknownProvider'

    VALIDATION_FAIL = 'ValidationFail'
    TASK_NOT_FOUND = 'TaskNotFound'

class AppBaseException(Exception):
    """The app base exception"""

    code = ExtraErrorCodes.INTERNAL_ERROR

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class CUDANotAvailableException(AppBaseException):
    """CUDA not available occurred."""

    code = 'CudaNotAvailable'

class GPUOutOfMemoryException(AppBaseException):
    """GPU out of memory occurred."""

    code = 'GpuOutOfMemory'

class FileEncryptionFoundError(AppBaseException):
    """File has been encrypted"""

    code = 'FileEncryptionFound'

class FilePageRatioInvalidError(AppBaseException):
    """Page ratio unexpected"""

    code = 'FilePageRatioInvalid'

class FileMIMEUnsupportedError(AppBaseException):
    """File MIME type unsupported"""

    code = 'FileMimeUnsupported'

class FileSizeTooLargeError(AppBaseException):
    """File size too large"""

    code = 'FileSizeTooLarge'

class FilePagesTooManyError(AppBaseException):
    """File pages too many"""

    code = 'FilePagesTooMany'

class FileDownloadFailureError(AppBaseException):
    """File download failed"""

    code = 'FileDownloadFailure'
