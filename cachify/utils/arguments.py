import hashlib
import inspect
import pickle
from collections.abc import Callable, Generator, Mapping, Sequence, Set
from contextlib import suppress
from inspect import Signature
from typing import Any

from cachify.types import CacheKeyFunction
from cachify.utils.functions import get_function_id


def _process_isolated_fingerprint(value: Any) -> str:
    stack = [value]
    seen = set()
    result = hashlib.blake2b(digest_size=16)

    while stack:
        current = stack.pop()
        current_id = id(current)

        # Avoid processing the same object multiple times
        if current_id in seen:
            continue
        seen.add(current_id)

        with suppress(TypeError):
            result.update(hash(current).to_bytes(8, "big", signed=True))
            continue

        if isinstance(current, Sequence):
            stack.extend(current)
            continue

        if isinstance(current, Set):
            stack.extend(sorted(current))
            continue

        if isinstance(current, Mapping):
            stack.extend(current.items())
            continue

        result.update(current_id.to_bytes(8, "big", signed=True))

    return result.hexdigest()


def _process_shared_fingerprint(value: Any) -> str:
    try:
        payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    except (pickle.PicklingError, TypeError, AttributeError) as exc:
        raise ValueError(
            "Process-shared cache key contains non-picklable items - Consider ignoring suspect fields"
        ) from exc

    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def _cache_key_fingerprint(value: Any, process_isolated: bool) -> str:
    if process_isolated:
        return _process_isolated_fingerprint(value)
    return _process_shared_fingerprint(value)


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
