# 📝 PR Review Guidelines & Good Practices

## 1. Control Flow: Guard Clauses & Early Returns

**Rule:** Avoid `if/else` chains and cascading nesting. Use guard clauses.

### Example 1

**❌ Wrong:**

```python
def func(x):
    if x:
      variable = do_something(x)
    else:
      variable = do_something_else(x)
    return variable
```

**✅ Right:**

```python
def func(x):
    if not x:
        return do_something_else(x)
    return do_something(x)
```

### Example 2

**❌ Wrong:**

```python
if a:
    if b:
        if c:
            do_something()
        else:
            return
    else:
        do_something_else()
else:
    return
```

**✅ Right:**

```python
if not a:
    return
if not b:
    do_something_else()
    return
if not c:
    return
do_something()
```

---

## 2\. Python 3.11 Typing

**Rule:** Always use Python 3.11 built-in generics instead of importing from `typing`.

**❌ Wrong:**

```python
from typing import Any, Dict, List, Set
```

**✅ Right:**

```python
from typing import Any
# use built-in generics
```

---

## 3\. Variable Naming

**Rule:** Never use 1 letter variable names.

### Example 1

**❌ Wrong:**

```python
except Exception as e:
    handle(e)
```

**✅ Right:**

```python
except Exception as exc:
    handle(exc)
```

### Example 2

**❌ Wrong:**

```python
aync def search_tweets(q: str)
```

**✅ Right:**

```python
async def search_tweets(query: str)
```

---

## 4\. Function Naming

**Rule:** Function names need to be clear about what they do and their scope.

### Example 1

**❌ Wrong:**

```python
async def get_latest_tweets_by_handle()
```

**✅ Right:**

```python
async def get_latest_tweets_by_handle(handle: str)
# OR
async def get_latest_tweets()
```

### Example 2

**❌ Wrong:**

```python
async def top_50()
```

**✅ Right:**

```python
async def get_top_50_tweets()
```

---

## 5\. Magic Numbers/Strings

**Rule:** Use constants instead of magic numbers/strings to make code more readable and maintainable.

**❌ Wrong:**

```python
list_of_something = list_of_something_else[:1458]
```

**✅ Right:**

```python
MAX_SOMETHING = 1458
list_of_something = list_of_something_else[:MAX_SOMETHING]
```

---

## 6\. Exception Handling

**Rule:** Don't have empty `try/except` blocks.

**❌ Wrong:**

```python
try:
    do_something()
except Exception:
    pass
```

**✅ Right:**

```python
with contextlib.suppress(Exception):
    do_something()
```

---

## 7\. Intermediary Variables

**Rule:** Don't have intermediary variables unless they improve readability.

### Example 1

**❌ Wrong:**

```python
result = do_something()
return result
```

**✅ Right:**

```python
return do_something()
```

### Example 2

**❌ Wrong:**

```python
result = {(k, v.do_something(k)) for some_dict in get_list_of_dicts() if some_dict for k, v in some_dict.items() if v.is_valid() and valid_key(k)}
```

**✅ Right:**

```python
valid_dicts = [some_dict for some_dict in get_list_of_dicts() if some_dict]

return {
    (key, value.do_something(key))
    for dataset in valid_datasets
    for key, value in dataset.items()
    if value.is_valid() and valid_key(key)
}
```

### Example 3

**❌ Wrong:**

```python
tasks.append(
    self._fetch_tokens_for_tier(
        sort_by,
        min_cap,
        max_cap,
    )
)
```

**✅ Right:**

```python
task = self._fetch_tokens_for_tier(sort_by, min_cap, max_cap)
tasks.append(task)
```

---

## 8\. Unnecessary Parentheses

**Rule:** Don't use unnecessary parentheses.

**❌ Wrong:**

```python
class TierToValue(Enum):
    FIRST = ("first", 1)
    SECOND = ("second", 2)
```

**✅ Right:**

```python
class TierToValue(Enum):
    FIRST = "first", 1
    SECOND = "second", 2
```

---

## 9\. Context Nesting

**Rule:** Code should be nested by context, not just sequentially, and should never mix contexts.

**❌ Wrong:**

```python
def func():
    do_something()

    if not condition:
        return
    do_another_thing()
    variable = compute_variable()

    if another_condition:
        use_variable(variable)
    completely_unrelated_thing()
```

**✅ Right:**

```python
def func():
    do_something()
    if not condition:
        return

    do_another_thing()

    variable = compute_variable()
    if another_condition:
        use_variable(variable)

    completely_unrelated_thing()
```

**❌ Wrong:**

```python
def func():
    variable = compute_variable()
    try:
        do_something_with_variable(variable)
    except Exception:
        handle_exception()
    do_unrelated_thing()
```

**✅ Right:**

```python
def func():
    variable = compute_variable()
    try:
        do_something_with_variable(variable)
    except Exception:
        handle_exception()

    do_unrelated_thing()
```

---

## 10\. Type Hints

**Rule:** Functions must always have type hints.

**❌ Wrong:**

```python
async def retrieve_unclaimed_cashback(session, user_id):
```

**✅ Right:**

```python
async def retrieve_unclaimed_cashback(session: aiohttp.ClientSession, user_id: str) -> float:
```

---

## 11\. None Types

**Rule:** `None` shouldn't be used as a type, otherwise it can lead to mistakes and bugs.

**❌ Wrong:**

```python
class Example:
  field: Literal["value1", "value2", None] = None
```

**✅ Right:**

```python
class Example:
  field: Literal["value1", "value2", "no_value"] = "no_value"
```

---

## 12\. Dead Code

**Rule:** Clear unused imports, classes, functions, variables, etc. Dead code is bad code.

---

## 13\. Formatting

**Rule:** Useless line breaks should be removed unless mandated by `black`.

**❌ Wrong:**

```python
async def save_execution_transaction_to_db(
    documents: list[ExecutionDBTransaction],
) -> list[ExecutionTransaction]:
```

**✅ Right:**

```python
async def save_execution_transaction_to_db(documents: list[ExecutionDBTransaction]) -> list[ExecutionTransaction]:
```

---

## 14\. Long Functions

**Rule:** Functions that are too long are a massive code smell. If a function is too big to read and understand in one go, it needs to be broken down into smaller functions.

---

## 15\. Default Class Fields

**Rule:** Avoid mutable default class fields.

**❌ Wrong:**

```python
class Example:
    def __init__(self, items: list[int] = []):
        self.items = items
# OR
class Example:
    items: list[int] = []
```

**✅ Right:**

```python
class Example:
    def __init__(self, items: list[int] | None = None):
        self.items = items or []
# OR
class Example:
    items: list[int] = field(default_factory=list)
```

---

## 16\. YAGNI

**Rule:** Don't add functionality that isn't currently needed or that would add too much complexity for little gain.

**❌ Wrong:**

Trying to handle every possible edge case or failure scenario and trying to recover from every possible error.

**✅ Right:**

Focusing on the core functionality, adding error handling for the most common or likely errors, and logging unexpected errors for future investigation.

---

## 17\. Avoid One Use Variables

**Rule:** Don't create variables that are only used in one place unless they improve readability.

**❌ Wrong:**

```python
data = fetch_data()
process(data)
```

**✅ Right:**

```python
process(fetch_data())
```

---

## 18\. Simplify Dictionary/List Comprehensions

**Rule:** Avoid unnecessary complexity in dictionary/list comprehensions.

**❌ Wrong:**

```python
result = {}
for key, value in some_dict.items():
    if condition(value):
        result[key] = transform(value)
```

**✅ Right:**

```python
result = {key: transform(value) for key, value in some_dict.items() if condition(value)}
```

---

## 19\.

**Rule:** If a line has been broken into multiple lines by the formatter because of the presence of a comma, but the line would fit within the 120 character limit without the comma, remove the comma.

**❌ Wrong:**

```python
some_function(
    argument_one,
    argument_two,
)
```

**✅ Right:**

```python
some_function(argument_one, argument_two)
```

---

## 20\. Grouped Code

**Rule:** Variables should be created near the code that uses them.

**❌ Wrong:**

```python
variable_one = compute_one()

if condition():
    variable_two = compute_two()
    use_variable(variable_two)

results = []
for item in items:
    result = process_item(item, variable_two)
    results.append(result)

analyzed = []
for dataset in datasets:
    analysis = analyze_dataset(dataset, variable_one)
    analyzed.append(analysis)

finalize(results, analyzed)
```

**✅ Right:**

```python
if condition():
    variable_two = compute_two()
    use_variable(variable_two)

results = []
for item in items:
    results.append(process_item(item, variable_two))

analyzed = []
for dataset in datasets:
    analyzed.append(analyze_dataset(dataset, variable_one))

finalize(results, analyzed)
```
