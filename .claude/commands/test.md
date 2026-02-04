# Test Skill

Run tests for the Tencent MCP project.

## Usage

```
/test [options]
```

## Arguments

- `$ARGUMENTS` - Optional: test path or options (e.g., `unit`, `integration`, `--cov`)

## Instructions

Based on the arguments provided, run the appropriate pytest command:

1. **No arguments or `all`**: Run all tests
   ```bash
   pytest
   ```

2. **`unit`**: Run unit tests only
   ```bash
   pytest tests/unit/
   ```

3. **`integration`**: Run integration tests only
   ```bash
   pytest tests/integration/
   ```

4. **`cov` or `coverage`**: Run tests with coverage report
   ```bash
   pytest --cov=app tests/
   ```

5. **Specific file/pattern**: Run tests matching the pattern
   ```bash
   pytest $ARGUMENTS
   ```

After running tests:
- Report the number of passed/failed tests
- If there are failures, summarize the key error messages
- Suggest fixes for common test failures
