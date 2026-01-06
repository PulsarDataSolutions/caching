import hashlib
import inspect
import logging
import pickle
from collections.abc import Callable, Generator
from inspect import Signature
from typing import Any

from cachify.types import CacheKeyFunction
from cachify.utils.functions import get_function_id


def _cache_key_fingerprint(value: object, process_isolated: bool) -> str:
    try:
        payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    except (pickle.PicklingError, TypeError) as exc:
        if not process_isolated:
            raise ValueError(
                "Process-shared cache key contains non-picklable items - Consider ignoring suspect fields"
            ) from exc

        payload = id(value).to_bytes(8, byteorder="big", signed=True)
        logging.debug("Using process-isolated cache key generation for non-picklable cache key items.")

    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def _iter_arguments(
    function_signature: Signature,
    args: tuple,
    kwargs: dict,
    ignore_fields: tuple[str, ...],
) -> Generator[Any, None, None]:
    bound = function_signature.bind_partial(*args, **kwargs)
    bound.apply_defaults()

    for name, value in bound.arguments.items():
        if name in ignore_fields:
            continue

        param = function_signature.parameters[name]

        # Positional variable arguments can just be yielded like so
        if param.kind == param.VAR_POSITIONAL:
            yield from value
            continue

        # Keyword variable arguments need to be unpacked from .items()
        if param.kind == param.VAR_KEYWORD:
            yield from value.items()
            continue

        yield name, value


def create_cache_key(
    function: Callable[..., Any],
    cache_key_func: CacheKeyFunction | None,
    ignore_fields: tuple[str, ...],
    args: tuple,
    kwargs: dict,
    process_isolated: bool,
) -> str:
    function_id = get_function_id(function)

    if not cache_key_func:
        function_signature = inspect.signature(function)
        items = tuple(_iter_arguments(function_signature, args, kwargs, ignore_fields))
        return f"{function_id}:{_cache_key_fingerprint(items, process_isolated)}"

    cache_key = cache_key_func(args, kwargs)
    try:
        return f"{function_id}:{_cache_key_fingerprint(cache_key, process_isolated)}"
    except TypeError as exc:
        raise ValueError(
            "Cache key function must return a hashable cache key - be careful with mutable types (list, dict, set) and non built-in types"
        ) from exc
