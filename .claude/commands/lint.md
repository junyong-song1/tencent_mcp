# Lint Skill

Run code quality checks and formatting for the project.

## Usage

```
/lint [options]
```

## Arguments

- `$ARGUMENTS` - Optional: `check`, `fix`, or specific path

## Instructions

Based on the arguments:

1. **No arguments or `fix`**: Format and check code
   ```bash
   # Format with black
   black app/ tests/ mcp_server/

   # Check with flake8
   flake8 app/ tests/ mcp_server/
   ```

2. **`check`**: Only check without modifying (CI mode)
   ```bash
   black --check app/ tests/ mcp_server/
   flake8 app/ tests/ mcp_server/
   ```

3. **Specific path**: Lint only the specified path
   ```bash
   black $ARGUMENTS
   flake8 $ARGUMENTS
   ```

Report:
- Number of files formatted by black
- Any flake8 warnings/errors with file:line references
- Suggestions to fix common issues (unused imports, line length, etc.)
