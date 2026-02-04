# API Skill

Explore and test the REST API endpoints.

## Usage

```
/api [action] [endpoint]
```

## Arguments

- `$ARGUMENTS` - Action (list, test, docs) and optional endpoint

## Instructions

1. **No arguments or `list`**: List all API endpoints
   - Read `app/api/routes/` directory
   - Parse route definitions
   - Display table of endpoints:

   | Method | Endpoint | Description |
   |--------|----------|-------------|
   | GET | /api/v1/health | Health check |
   | GET | /api/v1/resources | List resources |
   | GET | /api/v1/schedules | List schedules |
   | POST | /api/v1/schedules | Create schedule |
   | GET | /docs | Swagger UI |

2. **`test [endpoint]`**: Test an endpoint
   ```bash
   # Health check
   curl -s http://localhost:8000/api/v1/health | python -m json.tool

   # Resources
   curl -s http://localhost:8000/api/v1/resources | python -m json.tool
   ```

3. **`docs`**: Open API documentation info
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - OpenAPI JSON: http://localhost:8000/openapi.json

4. **`health`**: Quick health check
   ```bash
   curl -sf http://localhost:8000/api/v1/health && echo "API is healthy" || echo "API is not responding"
   ```

5. **Specific endpoint path**: Show endpoint details
   - Find the route definition
   - Show request/response schemas
   - Provide curl example

Before testing:
- Verify the server is running on port 8000
- Check if authentication is required
