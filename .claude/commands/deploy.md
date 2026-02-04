# Deploy Skill

서버 배포 및 관리를 수행합니다.

## Usage

```
/deploy [action]
```

## Arguments

- `$ARGUMENTS` - 액션: `start`, `stop`, `restart`, `logs`, `status` (기본: status)

## Instructions

### 1. `status` (기본)
현재 서버 상태 확인
```bash
pgrep -f "uvicorn app.main:app" && echo "서버 실행 중" || echo "서버 중지됨"
```

### 2. `start`
서버 시작
```bash
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
sleep 2
pgrep -f "uvicorn app.main:app" && echo "서버 시작 완료"
```

### 3. `stop`
서버 중지
```bash
pkill -f "uvicorn app.main:app"
echo "서버 종료됨"
```

### 4. `restart`
서버 재시작
```bash
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
sleep 2
pgrep -f "uvicorn app.main:app" && echo "서버 재시작 완료"
```

### 5. `logs`
최근 로그 확인
```bash
tail -50 app.log
```

## 환경

- 가상환경: `venv/`
- 로그 파일: `app.log`
- 포트: 8000
