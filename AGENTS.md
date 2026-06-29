# Repository Coding Conventions

## Naming

- Function names must use `snake_case`.
- Class names must use `PascalCase`.
- Variable names must use `camelCase`.
- Class member variable names must use `camelCase` with the `m_` prefix.
- File names must use `camelCase`.

## Examples

```python
class CenterlineBuilder:
    def __init__(self):
        self.m_centerlineResult = None

    def build_centerline(self, vesselTree):
        centerlineResult = vesselTree.create_centerline()
        self.m_centerlineResult = centerlineResult
        return centerlineResult
```

## Notes

- Keep new code consistent with these conventions.
- When editing existing code, prefer preserving behavior and avoid unrelated renaming unless the task explicitly requires it.
