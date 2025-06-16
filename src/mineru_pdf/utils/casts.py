from typing import Optional, Union


def as_bool_or_throw(input_: Union[str, bool, None]) -> bool:

    if input_ is None:
        return False

    if isinstance(input_, bool):
        return input_

    if isinstance(input_, str) and input_.isspace():
        return False

    parsed = input_.strip().lower()

    if parsed in ['true', 'yes', 'y', '1']:
         return True

    if parsed in ['false', 'no', 'n', '0', '']:
        return False

    raise ValueError(f'unable convert {input_} to bool')

def as_bool_or_default(input_: Union[str, bool, None], default: Optional[bool]) -> Optional[bool]:

    try:
        return as_bool_or_throw(input_)
    except ValueError:
        return default
