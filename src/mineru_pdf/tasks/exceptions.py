
from .constants import Errors


class CUDANotAvailableError(RuntimeError):
    """CUDA not available occurred."""

    code = Errors.GPU_RUNTIME_ERROR

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class GPUOutOfMemoryError(RuntimeError):
    """GPU out of memory occurred."""

    code = Errors.GPU_OUT_OF_MEMORY

    def __str__(self):
        return f'{self.code}: {super().__str__()}'


class FileEncryptionFoundError(ValueError):
    """File has been encrypted"""

    code = Errors.FILE_ENCRYPTION_FOUND

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class FilePageRatioInvalidError(ValueError):
    """Page ratio unexpected"""

    code = Errors.FILE_PAGE_RADIO_INVALID

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class FileMIMEUnsupportedError(ValueError):
    """File MIME type unsupported"""

    code = Errors.FILE_MIME_UNSUPPORTED

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class FileTooLargeSizeError(ValueError):
    """File too large size"""

    code = Errors.FILE_TOO_LARGE_SIZE

    def __str__(self):
        return f'{self.code}: {super().__str__()}'

class FileTooManyPagesError(ValueError):
    """File too many pages"""

    code = Errors.FILE_TOO_MANY_PAGES

    def __str__(self):
        return f'{self.code}: {super().__str__()}'
