
class CUDANotAvailableError(RuntimeError):
    """CUDA not available occurred."""

class GPUOutOfMemoryError(RuntimeError):
    """GPU out of memory occurred."""

class FileEncryptionFoundError(ValueError):
    """File has been encrypted"""
