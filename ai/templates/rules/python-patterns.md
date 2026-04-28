---
description: Copy to .claude/rules/ — Python patterns and Django conventions
paths:
  - "**/*.py"
---

# Python Patterns

## Type Hints

- Use primitive types: `list`, `dict`, `set`, `tuple`
- Use `Optional[T]` over `T | None`
- Only import from `typing` when no primitive alternative exists
- All functions must have fully typed arguments and return types
- Never use `Any` except for complex nested dictionary responses

## Function Design

- Function names should clearly convey responsibility
- Single responsibility: one function, one job
- Public functions get full docstrings (Args, Returns, Raises)
- Private helpers may omit docstrings if the name is self-explanatory

## Django Conventions

- Keep views thin — business logic in use cases or services
- Prefer declarative serializers, filters, and pagination over custom methods
- Use `transaction.atomic()` for multi-write mutations
- Use `transaction.on_commit()` for side effects that depend on committed rows
- Watch for N+1 queries — use `select_related` and `prefetch_related`

## Testing

- Tests named `test_<function_name>_<suffix>`
- First test has no suffix (base case), subsequent tests describe the specific case
- Use `assert` for value comparisons, assertion methods only for mock calls
- Parametrize similar test cases with `@pytest.mark.parametrize`
- Test the changed path specifically, not just nearby happy paths
