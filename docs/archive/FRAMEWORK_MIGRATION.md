# 프레임워크 마이그레이션 가이드

## 추천 프레임워크: FastAPI

### 선택 이유

1. **경량 & 확장성**: 웹 UI 없이도 사용 가능, 나중에 관리 API 추가 용이
2. **비동기 지원**: Tencent Cloud API 호출 성능 향상
3. **의존성 주입**: 테스트와 모듈 교체 용이
4. **자동 문서화**: OpenAPI/Swagger 자동 생성 (나중에 API 추가 시 유용)
5. **Slack Bolt 호환**: 기존 Slack Bolt 코드와 완벽 호환

---

## 새로운 프로젝트 구조

```
tencent_mcp/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 + Slack Bolt 통합
│   ├── config.py               # 설정 관리
│   │
│   ├── api/                    # REST API (선택사항, 나중에 확장용)
│   │   ├── __init__.py
│   │   ├── routes.py           # API 엔드포인트
│   │   └── dependencies.py     # 공통 의존성
│   │
│   ├── slack/                  # Slack 관련
│   │   ├── __init__.py
│   │   ├── handlers.py         # Slack 이벤트 핸들러
│   │   ├── ui.py               # Block Kit UI 생성
│   │   └── commands.py         # 명령어 처리
│   │
│   ├── services/               # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── tencent_client.py   # Tencent Cloud 클라이언트
│   │   ├── scheduler.py        # 스케줄링 (APScheduler 사용)
│   │   ├── notification.py     # 알림 서비스
│   │   ├── schedule_manager.py # 방송 스케줄 관리
│   │   └── linkage_service.py  # 리소스 연결 서비스
│   │
│   ├── models/                 # 데이터 모델
│   │   ├── __init__.py
│   │   ├── schedule.py         # BroadcastSchedule
│   │   └── resource.py         # Resource 모델
│   │
│   └── storage/                # 데이터 저장
│       ├── __init__.py
│       └── file_storage.py     # JSON 파일 저장 (나중에 DB로 교체 가능)
│
├── tests/
├── scripts/
├── docs/
└── requirements.txt
```

---

## 마이그레이션 단계

### Phase 1: 기본 구조 설정

1. **FastAPI 앱 생성**
   ```python
   # app/main.py
   from fastapi import FastAPI
   from slack_bolt import App
   from slack_bolt.adapter.socket_mode import SocketModeHandler
   
   app = FastAPI(title="Tencent MCP Bot")
   slack_app = App(token=Config.SLACK_BOT_TOKEN)
   
   @app.on_event("startup")
   async def startup():
       # Slack Bolt 시작
       handler = SocketModeHandler(slack_app, Config.SLACK_APP_TOKEN)
       handler.start()
   ```

2. **의존성 주입 설정**
   ```python
   # app/services/tencent_client.py
   from fastapi import Depends
   
   def get_tencent_client() -> TencentCloudClient:
       return TencentCloudClient()
   
   # 사용 예시
   @slack_app.command("/tencent")
   def handle_command(ack, body, client, tencent=Depends(get_tencent_client)):
       ...
   ```

### Phase 2: 모듈 분리

1. **Slack 핸들러 분리**
   - `app_v2.py` → `app/slack/handlers.py`
   - 명령어별로 함수 분리

2. **서비스 레이어 분리**
   - `tencent_cloud_client.py` → `app/services/tencent_client.py`
   - `scheduler.py` → `app/services/scheduler.py` (APScheduler로 교체)
   - `notification_service.py` → `app/services/notification.py`

3. **모델 분리**
   - `BroadcastSchedule` → `app/models/schedule.py`
   - 리소스 모델 → `app/models/resource.py`

### Phase 3: 스케줄러 개선 (APScheduler)

```python
# app/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

class ScheduleService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
    
    async def add_schedule(self, schedule: BroadcastSchedule):
        # 시작 시간 스케줄
        self.scheduler.add_job(
            self._start_channel,
            trigger=DateTrigger(run_date=schedule.start_time),
            id=f"start_{schedule.schedule_id}",
            args=[schedule]
        )
        
        # 종료 시간 스케줄
        self.scheduler.add_job(
            self._stop_channel,
            trigger=DateTrigger(run_date=schedule.end_time),
            id=f"stop_{schedule.schedule_id}",
            args=[schedule]
        )
```

### Phase 4: API 엔드포인트 추가 (선택사항)

```python
# app/api/routes.py
from fastapi import APIRouter, Depends
from app.services.tencent_client import get_tencent_client

router = APIRouter(prefix="/api/v1")

@router.get("/resources")
async def list_resources(tencent=Depends(get_tencent_client)):
    """리소스 목록 조회 (모니터링용)"""
    return await tencent.list_all_resources()

@router.get("/schedules")
async def list_schedules(schedule_manager=Depends(get_schedule_manager)):
    """스케줄 목록 조회"""
    return schedule_manager.list_schedules()
```

---

## 의존성 추가

```txt
# requirements.txt에 추가
fastapi==0.104.1
uvicorn[standard]==0.24.0
apscheduler==3.10.4
pydantic==2.5.0
```

---

## 실행 방법

```bash
# 개발 모드
uvicorn app.main:app --reload

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 장점 요약

1. **모듈화**: 각 기능이 명확히 분리되어 유지보수 용이
2. **테스트 용이**: 의존성 주입으로 모킹 쉬움
3. **확장성**: 나중에 API, 웹훅, 모니터링 추가 용이
4. **성능**: 비동기 처리로 응답 속도 향상
5. **표준화**: FastAPI는 Python 웹 프레임워크 표준

---

## 대안: APScheduler만 추가

웹 프레임워크가 정말 필요 없다면:

```python
# app/main.py (간단 버전)
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from apscheduler.schedulers.background import BackgroundScheduler

app = App(token=Config.SLACK_BOT_TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()

# Slack 핸들러 등록
# ...

if __name__ == "__main__":
    handler = SocketModeHandler(app, Config.SLACK_APP_TOKEN)
    handler.start()
```

이 경우 구조화는 수동으로 모듈 분리만 진행.
