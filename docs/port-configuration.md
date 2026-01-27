# 포트 설정 가이드

이 문서는 Tencent Cloud MCP 서버의 포트 설정 방법을 설명합니다.

## 포트 설정 옵션

### 옵션 1: 다른 포트 사용 (권장)

80 포트가 이미 사용 중이면 다른 포트를 사용하고, 리버스 프록시로 80 포트로 라우팅합니다.

#### 설정 방법

`.env` 파일:
```bash
PORT=8000  # 또는 8080, 3000 등 사용 가능한 포트
```

#### 장점
- Root 권한 불필요
- 다른 서비스와 충돌 없음
- 리버스 프록시로 80 포트 라우팅 가능

### 옵션 2: 직접 80 포트 사용

80 포트를 직접 사용하려면 root 권한이 필요합니다.

#### 설정 방법

`.env` 파일:
```bash
PORT=80
```

#### 실행 방법

**방법 A: sudo로 실행**
```bash
sudo python3 -m uvicorn app.main:app --host 0.0.0.0 --port 80
```

**방법 B: systemd service 사용 (권장)**
```bash
# systemd service 파일 수정
sudo nano /etc/systemd/system/tencent-mcp.service

# ExecStart에 --port 80 추가
# User를 root로 변경하거나 setcap 사용
```

**방법 C: setcap으로 권한 부여 (더 안전)**
```bash
# Python 실행 파일에 권한 부여
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3

# 또는 venv의 python에
sudo setcap 'cap_net_bind_service=+ep' /home/ubuntu/tencent_mcp/venv/bin/python3
```

#### 주의사항
- Root 권한 필요 (보안 위험)
- 다른 서비스와 포트 충돌 가능
- 권장하지 않음 (리버스 프록시 사용 권장)

### 옵션 3: 리버스 프록시 사용 (가장 권장)

Nginx를 사용하여 80 포트로 들어오는 요청을 애플리케이션 포트로 전달합니다.

#### 아키텍처

```
인터넷
  ↓ (포트 80)
Nginx (리버스 프록시)
  ↓ (포트 8000)
FastAPI 애플리케이션
```

#### 설정 방법

1. **애플리케이션은 다른 포트에서 실행**

`.env` 파일:
```bash
PORT=8000
```

2. **Nginx 설정**

`deploy/nginx.conf.example` 파일을 참고하여 Nginx 설정:

```bash
# 설정 파일 복사
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/tencent-mcp

# 도메인/IP 수정
sudo nano /etc/nginx/sites-available/tencent-mcp

# Symlink 생성
sudo ln -s /etc/nginx/sites-available/tencent-mcp /etc/nginx/sites-enabled/

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl reload nginx
```

3. **방화벽 설정**

```bash
# 포트 80 열기 (Nginx)
sudo ufw allow 80/tcp

# 포트 8000은 localhost만 접근 (선택사항)
sudo ufw allow from 127.0.0.1 to any port 8000
```

#### 장점
- Root 권한 불필요 (애플리케이션은 일반 사용자로 실행)
- 보안 향상 (애플리케이션은 내부 포트에서만 실행)
- SSL/TLS 쉽게 추가 가능
- 로드 밸런싱, 캐싱 등 추가 기능 활용 가능

## 현재 설정 확인

### 포트 확인

```bash
# 현재 사용 중인 포트 확인
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000

# 또는
sudo ss -tlnp | grep :80
sudo ss -tlnp | grep :8000
```

### 환경 변수 확인

```bash
# .env 파일 확인
cat .env | grep PORT

# 실행 중인 프로세스 확인
ps aux | grep uvicorn
```

## 권장 설정

### 프로덕션 환경

1. **애플리케이션**: 포트 8000에서 실행 (일반 사용자)
2. **Nginx**: 포트 80에서 리버스 프록시
3. **방화벽**: 포트 80만 외부에 노출

### 개발 환경

```bash
# .env 파일
PORT=8000
DEBUG=True
```

직접 접근: `http://localhost:8000`

## Cloud Function Webhook URL

포트 설정에 따라 Cloud Function의 webhook URL도 변경해야 합니다:

### 포트 8000 사용 시
```
https://your-server.com:8000/api/v1/webhooks/cloud-function
```

### Nginx 리버스 프록시 사용 시 (포트 80)
```
https://your-server.com/api/v1/webhooks/cloud-function
```

### 직접 80 포트 사용 시
```
https://your-server.com/api/v1/webhooks/cloud-function
```

## 문제 해결

### 포트가 이미 사용 중

```bash
# 어떤 프로세스가 포트를 사용하는지 확인
sudo lsof -i :80
sudo lsof -i :8000

# 프로세스 종료 (필요시)
sudo kill -9 <PID>
```

### 권한 오류 (80 포트)

```bash
# setcap으로 권한 부여
sudo setcap 'cap_net_bind_service=+ep' $(which python3)

# 또는 sudo로 실행 (권장하지 않음)
sudo python3 -m uvicorn app.main:app --host 0.0.0.0 --port 80
```

### Nginx 설정 오류

```bash
# 설정 파일 문법 확인
sudo nginx -t

# 에러 로그 확인
sudo tail -f /var/log/nginx/error.log
```

## 빠른 시작

### 개발 환경

```bash
# .env 파일
PORT=8000

# 실행
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 프로덕션 환경 (Nginx 사용)

```bash
# 1. 애플리케이션 설정
# .env 파일
PORT=8000

# 2. Nginx 설정
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/tencent-mcp
sudo nano /etc/nginx/sites-available/tencent-mcp  # 도메인/IP 수정
sudo ln -s /etc/nginx/sites-available/tencent-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 3. 애플리케이션 실행
./scripts/start.sh
```
