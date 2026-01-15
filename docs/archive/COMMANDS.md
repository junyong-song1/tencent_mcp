# Tencent MCP Slack Bot - 명령어 가이드

## 📋 목차
1. [기본 사용법](#기본-사용법)
2. [검색 명령어](#검색-명령어)
3. [제어 명령어](#제어-명령어)
4. [시스템 명령어](#시스템-명령어)
5. [UI 버튼](#ui-버튼)

---

## 기본 사용법

### 봇 호출 방법

1. **멘션 (@Tencent MCP)**
   ```
   @Tencent MCP 채널 검색
   ```

2. **Slash Command**
   ```
   /tencent 채널 검색
   ```

3. **Direct Message (DM)**
   ```
   채널 검색
   ```

---

## 검색 명령어

### 전체 채널 조회
```
채널 검색
채널 목록
채널 리스트
목록
리스트
```

### 키워드 검색
```
KBO 채널 찾아줘
TVING 검색
라이브 스포츠 채널 보여줘
```

### 서비스별 검색
```
StreamLink 목록
StreamLink 채널 검색
MediaLive 채널 보여줘
MediaConnect 목록
CSS 스트림 검색
VOD 미디어 목록
```

### 상태별 검색
```
상태
현황
오류 상태인 채널이 있어?
실행 중인 채널 보여줘
중지된 채널 목록
```

**지원 키워드:**
- 검색: `검색`, `찾아`, `찾아줘`, `조회`, `보여줘`, `알려줘`, `list`, `search`, `find`
- 서비스: `StreamLink`, `StreamLive`, `MediaLive`, `MediaConnect`, `CSS`, `VOD`, `mdc`, `mdl`
- 상태: `상태`, `status`, `분석`, `analyze`, `현황`, `어때`

---

## 제어 명령어

### 채널 시작
```
"채널ID" 시작
"mdc-xxx" 시작
"mdl-xxx" 실행
채널ID start
```

**지원 키워드:**
- `시작`, `start`, `켜`, `run`, `실행`

### 채널 중지
```
"채널ID" 중지
"mdc-xxx" 중지
"mdl-xxx" stop
채널ID 꺼
```

**지원 키워드:**
- `중지`, `stop`, `꺼`, `멈춰`, `종료`

### 채널 재시작
```
"채널ID" 재시작
"mdc-xxx" 다시 시작
"mdl-xxx" restart
```

**지원 키워드:**
- `재시작`, `restart`, `리스타트`, `다시 시작`

### 서비스 지정 제어
```
StreamLink "mdc-xxx" 시작
MediaLive "mdl-xxx" 중지
```

---

## 시스템 명령어

### 도움말
```
help
도움말
사용법
/tencent help
```

### 대화 초기화
```
clear
reset
초기화
/tencent clear
```

### 시스템 통계
```
stats
통계
/tencent stats
```

---

## UI 버튼

검색 결과에서 표시되는 버튼들:

### ▶️ 실행 (Start)
- 중지된 채널을 시작합니다
- 클릭 시 즉시 실행

### ⏹️ 중지 (Stop)
- 실행 중인 채널을 중지합니다
- 클릭 시 즉시 실행

### 🔄 재시작 (Restart)
- 오류 상태의 채널을 재시작합니다
- 중지 후 시작을 순차적으로 실행

### 📋 상세 정보 (Info)
- 채널의 상세 정보를 표시합니다
- ID, 이름, 상태, 이벤트 그룹 등

---

## 명령어 예시

### 기본 검색
```
@Tencent MCP 채널 검색
→ 모든 채널 목록 표시

@Tencent MCP KBO 검색
→ "KBO" 키워드가 포함된 채널 검색

@Tencent MCP StreamLink 목록
→ StreamLink 서비스의 채널만 표시
```

### 제어
```
@Tencent MCP "mdc-abc123" 시작
→ StreamLink 채널 시작

@Tencent MCP "mdl-xyz789" 중지
→ MediaLive 채널 중지

@Tencent MCP "mdc-abc123" 재시작
→ StreamLink 채널 재시작
```


### 상태 확인
```
@Tencent MCP 상태
→ 전체 채널 상태 조회

@Tencent MCP 오류 상태인 채널이 있어?
→ 오류 상태 채널 검색
```

---

## 서비스별 명령어

### StreamLink (MediaConnect)
- 서비스명: `StreamLink`, `MediaConnect`, `mdc`
- 리소스 타입: Flow, Input
- 제어: Flow 시작/중지

### MediaLive (StreamLive)
- 서비스명: `MediaLive`, `StreamLive`, `mdl`
- 리소스 타입: Channel
- 제어: Channel 시작/중지/재시작

### CSS (Cloud Streaming Services)
- 서비스명: `CSS`
- 리소스 타입: Stream
- 제어: Stream 중지 (drop)

### VOD (Video on Demand)
- 서비스명: `VOD`
- 리소스 타입: Media
- 제어: 조회만 가능 (제어 기능 없음)

---

## 주의사항

1. **채널 ID 형식**
   - StreamLink: `mdc-xxx` 또는 Flow ID
   - MediaLive: `mdl-xxx` 또는 Channel ID
   - 따옴표로 감싸면 정확한 ID로 인식됩니다

2. **서비스 지정**
   - 명령어에 서비스명을 포함하면 해당 서비스만 검색/제어합니다
   - 서비스명 없으면 전체 서비스에서 검색합니다


4. **권한**
   - `.env` 파일의 `ALLOWED_USERS`에 설정된 사용자만 사용 가능합니다
   - 설정하지 않으면 모든 사용자가 사용할 수 있습니다

---

## 문제 해결

### 명령어가 인식되지 않을 때
1. 키워드를 명확하게 입력하세요
2. 서비스명이나 채널 ID를 정확히 입력하세요
3. `help` 명령어로 사용법을 확인하세요

### 채널을 찾을 수 없을 때
1. 채널 ID가 정확한지 확인하세요
2. 서비스명을 포함하여 검색해보세요
3. 전체 목록을 조회하여 채널 ID를 확인하세요


---

## 업데이트 이력

- 2024-12-XX: 초기 명령어 가이드 작성
- StreamLink(MediaConnect), MediaLive 제어 기능 추가
