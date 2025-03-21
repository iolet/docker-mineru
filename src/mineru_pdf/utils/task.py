
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
