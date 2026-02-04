# Service Skill

Explore and work with service modules.

## Usage

```
/service [name]
```

## Arguments

- `$ARGUMENTS` - Service name or `list`

## Instructions

1. **No arguments or `list`**: List all services
   - Read `app/services/` directory
   - Show each service with description:

   | Service | Purpose |
   |---------|---------|
   | tencent_client.py | Tencent Cloud API wrapper |
   | schedule_manager.py | Broadcast schedule CRUD |
   | scheduler.py | APScheduler background tasks |
   | notification.py | Schedule alerts & notifications |
   | alert_monitor.py | Channel alert monitoring |
   | linkage.py | Resource relationship matching |
   | ai_assistant.py | Claude AI integration |

2. **`tencent` or `client`**: Show TencentCloudClient details
   - Key methods for StreamLive (MDL)
   - Key methods for StreamLink (MDC)
   - Key methods for StreamPackage (MDP)
   - Key methods for CSS (Live)
   - Caching and threading configuration

3. **`schedule`**: Show ScheduleManager details
   - CRUD operations
   - Thread-safe implementation
   - JSON storage integration

4. **`notification`**: Show notification service
   - Alert types and triggers
   - Slack notification formatting
   - Auto-start callbacks

5. **`alert`**: Show alert monitoring service
   - Alert severity classification
   - Polling configuration
   - Channel filtering

6. **`linkage`**: Show linkage service
   - StreamLink to StreamLive mapping
   - Output URL matching logic
   - Resource hierarchy

7. **Specific service file**: Read and explain the service
   - Show main class/functions
   - Explain key methods
   - Show usage examples from handlers

Services follow these patterns:
- Async support via `asyncio.to_thread()`
- Thread-safe operations with `threading.Lock`
- TTL caching for API responses
- Dependency injection via constructor
