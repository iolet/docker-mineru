class Result(object):

    NONE_: str = 'NONE'
    COLLECTING: str = 'COLLECTING'
    INFERRING: str = 'INFERRING'
    PACKING: str = 'PACKING'
    CLEANING: str = 'CLEANING'
    FINISHED: str = 'FINISHED'

class Status(object):

    CREATED: str = 'CREATED'
    RUNNING: str = 'RUNNING'
    COMPLETED: str = 'COMPLETED'
    TERMINATED: str = 'TERMINATED'

class Errors(object):

    NONE_ = 'NONE_'

    DNS_NXDOMAIN: str = 'DNS_NXDOMAIN'

    HTTP_UNAUTHORIZED: str = 'HTTP_UNAUTHORIZED'
    HTTP_FORBIDDEN: str = 'HTTP_FORBIDDEN'
    HTTP_NOT_FOUND: str = 'HTTP_NOT_FOUND'
    HTTP_NOT_ALLOWED: str = 'HTTP_NOT_ALLOWED'
    HTTP_OTHERS_CASES: str = 'HTTP_OTHERS_CASES'

    PYI_MEMORY_ERROR: str = 'PYI_MEMORY_ERROR'
    GPU_OUT_OF_MEMORY: str = 'GPU_OUT_OF_MEMORY'
    GPU_RUNTIME_ERROR: str = 'GPU_RUNTIME_ERROR'

    SYS_INTERNAL_ERROR: str = 'SYS_INTERNAL_ERROR'

def find_http_errors(status_code: int) -> str:

    if 401 == status_code:
        return Errors.HTTP_UNAUTHORIZED

    if 403 == status_code:
        return Errors.HTTP_FORBIDDEN

    if 404 == status_code:
        return Errors.HTTP_NOT_FOUND

    if 405 == status_code:
        return Errors.HTTP_NOT_ALLOWED

    return Errors.HTTP_OTHERS_CASES
