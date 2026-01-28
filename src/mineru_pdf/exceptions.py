
from enum import StrEnum

class ExtraErrorCodes(StrEnum):
    NONE_ = 'NONE'
    INTERNAL_ERROR = 'SYS_INTERNAL_ERROR'
    VALIDATION_FAIL = 'REQ_VALIDATION_FAIL'

class AppBaseException(Exception):
    """The app base exception"""

    code = ExtraErrorCodes.INTERNAL_ERROR

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class CUDANotAvailableException(AppBaseException):
    """CUDA not available occurred."""

    code = 'GPU_RUNTIME_ERROR'

class GPUOutOfMemoryException(AppBaseException):
    """GPU out of memory occurred."""

    code = 'GPU_OUT_OF_MEMORY'

class FileEncryptionFoundError(AppBaseException):
    """File has been encrypted"""

    code = 'FILE_ENCRYPTION_FOUND'

class FilePageRatioInvalidError(AppBaseException):
    """Page ratio unexpected"""

    code = 'FILE_PAGE_RADIO_INVALID'

class FileMIMEUnsupportedError(AppBaseException):
    """File MIME type unsupported"""

    code = 'FILE_MIME_UNSUPPORTED'

class FileTooLargeSizeError(AppBaseException):
    """File too large size"""

    code = 'FILE_TOO_LARGE_SIZE'

class FileTooManyPagesError(AppBaseException):
    """File too many pages"""

    code = 'FILE_TOO_MANY_PAGES'

class FileDownloadFailureError(AppBaseException):
    """File download failed"""

    code = 'FILE_DOWNLOAD_FAILURE'
