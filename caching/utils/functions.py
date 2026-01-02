import functools
from typing import Any, Callable


@functools.cache
def get_function_id(function: Callable[..., Any]) -> str:
    """
    Returns the unique identifier for the function, which is a combination of its module and qualified name.
    """
    return f"{function.__module__}.{function.__qualname__}"
