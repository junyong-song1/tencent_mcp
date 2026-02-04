# Setup Skill

Initialize or verify the project development environment.

## Usage

```
/setup [action]
```

## Arguments

- `$ARGUMENTS` - Optional: `init`, `verify`, `env`, or `clean`

## Instructions

1. **No arguments or `init`**: Full project setup
   ```bash
   # Create virtual environment if not exists
   [ ! -d venv ] && python3 -m venv venv

   # Activate and install dependencies
   source venv/bin/activate
   pip install -r requirements.txt

   # Create .env from example if not exists
   [ ! -f .env ] && cp .env.example .env && echo "Created .env - please configure it"
   ```

2. **`verify`**: Verify setup is complete
   - Check venv exists and is activated
   - Check all requirements are installed
   - Check .env file exists with required variables
   - Test imports of main modules

3. **`env`**: Setup environment file
   - Check if .env.example exists
   - Create .env from .env.example if missing
   - List required variables that need to be configured:
     - SLACK_BOT_TOKEN (xoxb-...)
     - SLACK_APP_TOKEN (xapp-...)
     - SLACK_SIGNING_SECRET
     - TENCENT_SECRET_ID
     - TENCENT_SECRET_KEY
     - TENCENT_REGION (default: ap-seoul)

4. **`clean`**: Clean up environment
   ```bash
   # Remove cached files
   find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
   find . -type f -name "*.pyc" -delete
   rm -rf .pytest_cache .coverage htmlcov
   ```

5. **`deps`**: Update dependencies
   ```bash
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt --upgrade
   ```

Report the status of each step and any issues encountered.
