# StreamLive 입력 상태 UI 표시 가이드 (업데이트)

## 개요

StreamLive 채널이 운영 중일 때, main/backup 입력 중 어느 신호로 우선 서비스되고 있는지 확인할 수 있는 기능입니다.

**업데이트:** QueryInputStreamState API를 사용하여 정확한 활성 소스를 확인합니다.

## UI 동작 방식

### 1. 대시보드에서 정보 확인

#### 1.1 대시보드 열기
- 슬랙에서 `/tencent` 명령어 입력
- 또는 봇 멘션 후 대시보드 요청

#### 1.2 채널 목록 확인
대시보드 모달에서 StreamLive 채널들이 표시됩니다.

### 2. 입력 상태 확인하기

#### 2.1 정보 버튼 클릭
StreamLive 채널의 **ℹ️ (정보)** 버튼을 클릭합니다.

#### 2.2 입력 상태 표시
정보가 슬랙 채널에 다음과 같이 표시됩니다:

**케이스 1: Main 입력이 활성화된 경우 (QueryInputStreamState 확인)**
```
┌─────────────────────────────────────────┐
│  *sbs_no1_news*                          │
│  ID: `695E09660000090927DE`              │
│  서비스: StreamLive                      │
│  상태: running                           │
│                                          │
│  🟢 *입력 상태*: MAIN                   │
│     (695E065C00004F07D2D4)              │
│   검증: QueryInputStreamState,          │
│         InputSourceRedundancy (2단계)    │
│   📦 StreamPackage 확인: MAIN            │
└─────────────────────────────────────────┘
```

**케이스 2: Backup 입력이 활성화된 경우**
```
┌─────────────────────────────────────────┐
│  *My StreamLive Channel*                 │
│  ID: `channel-123`                       │
│  서비스: StreamLive                      │
│  상태: running                           │
│                                          │
│  ⚠️ *입력 상태*: BACKUP                 │
│     (backup-input-002)                  │
│   검증: QueryInputStreamState,          │
│         InputSourceRedundancy (2단계)    │
└─────────────────────────────────────────┘
```

**케이스 3: 입력 상태 확인 불가능한 경우**
```
┌─────────────────────────────────────────┐
│  *My StreamLive Channel*                 │
│  ID: `channel-123`                       │
│  서비스: StreamLive                      │
│  상태: running                           │
│                                          │
│  ❓ *입력 상태*: 확인 불가               │
└─────────────────────────────────────────┘
```

## UI 요소 설명

### 이모지 표시 규칙

| 이모지 | 의미 | 설명 |
|--------|------|------|
| 🟢 | Main 입력 활성 | 정상적으로 main 입력이 사용 중 |
| ⚠️ | Backup 입력 활성 | Failover 발생, backup 입력 사용 중 |
| ❓ | 상태 확인 불가 | API 오류 또는 입력 정보 없음 |

### 표시되는 정보

1. **채널 이름**: StreamLive 채널의 이름
2. **채널 ID**: Tencent Cloud의 채널 식별자
3. **서비스 타입**: StreamLive
4. **채널 상태**: running, stopped, idle, error 등
5. **입력 상태**: MAIN 또는 BACKUP
6. **활성 입력 이름/ID**: 현재 사용 중인 입력의 이름 또는 ID
7. **검증 정보**: 
   - 검증 소스: `QueryInputStreamState`, `InputSourceRedundancy`, `StreamLink`, `CSS` 등
   - 검증 레벨: 검증 단계 수 (예: 2단계, 3단계)
8. **StreamPackage 검증** (있는 경우): StreamPackage에서 확인한 활성 입력

## 검증 소스 설명

### QueryInputStreamState (최우선)

**의미:**
- StreamLive API에서 직접 제공하는 상태 정보
- 가장 신뢰할 수 있는 검증 방법

**표시:**
- `검증: QueryInputStreamState, InputSourceRedundancy (2단계)`

### InputSourceRedundancy

**의미:**
- Input Source Redundancy 방식으로 구성됨
- 하나의 입력에 여러 소스 주소가 설정되어 있음

**표시:**
- `검증: QueryInputStreamState, InputSourceRedundancy (2단계)`

### StreamLink (Fallback)

**의미:**
- StreamLink 플로우 상태로 추론
- QueryInputStreamState가 실패한 경우 사용

**표시:**
- `검증: StreamLink, InputSourceRedundancy, CSS (3단계)`

### CSS (Fallback)

**의미:**
- CSS (Cloud Streaming Service) 검증
- 스트림 흐름 확인

**표시:**
- `검증: StreamLink, InputSourceRedundancy, CSS (3단계)`

## 실제 표시 예제

### 예제 1: Main 입력 활성 (QueryInputStreamState 확인)

```
*sbs_no1_news*
ID: `695E09660000090927DE`
서비스: StreamLive
상태: running

🟢 *입력 상태*: MAIN
   (695E065C00004F07D2D4)
   검증: QueryInputStreamState, InputSourceRedundancy (2단계)
   📦 StreamPackage 확인: MAIN
```

**의미:**
- QueryInputStreamState API로 확인됨
- Input Source Redundancy 방식
- Main 소스 주소 (ap-seoul-1)가 활성
- StreamPackage도 Main 확인

### 예제 2: Backup 입력 활성

```
*My StreamLive Channel*
ID: `channel-123`
서비스: StreamLive
상태: running

⚠️ *입력 상태*: BACKUP
   (backup-input-002)
   검증: QueryInputStreamState, InputSourceRedundancy (2단계)
```

**의미:**
- QueryInputStreamState API로 확인됨
- Input Source Redundancy 방식
- Backup 소스 주소 (ap-seoul-2)가 활성

## 검증 레벨 설명

### 2단계 검증

**예시:**
- `QueryInputStreamState, InputSourceRedundancy`

**의미:**
- QueryInputStreamState로 직접 확인
- Input Source Redundancy 방식 감지

### 3단계 검증

**예시:**
- `StreamLink, InputSourceRedundancy, CSS`

**의미:**
- StreamLink 플로우 상태 확인
- Input Source Redundancy 방식 감지
- CSS 스트림 흐름 확인

## 업데이트 사항

### 변경 전

**검증 방법:**
- StreamLink 플로우 상태 확인 (추론)
- 통계 데이터 확인
- QueryInputStreamState (파라미터 문제로 사용 안 됨)

**문제점:**
- StreamLink 플로우 상태만으로는 실제 활성 소스를 알 수 없음
- 두 플로우가 모두 running이면 둘 다 실행 중
- 실제로 StreamLive가 어떤 소스를 사용하는지는 확인 불가

### 변경 후

**검증 방법:**
1. **QueryInputStreamState** (최우선 - StreamLive가 직접 제공)
   - 각 입력에 대해 `QueryInputStreamState` 호출
   - `InputStreamInfoList`에서 `Status == 1`인 소스 확인
   - `InputAddress`로 main/backup 구분
2. StreamLink 플로우 상태 확인 (fallback)
3. 통계 데이터 확인 (fallback)

**장점:**
- ✅ StreamLive가 직접 제공하는 상태 정보
- ✅ 실시간 확인 가능
- ✅ 정확한 활성 소스 주소 확인
- ✅ Input Source Redundancy 방식에서도 정확한 활성 소스 확인

## 사용 시나리오

### 시나리오 1: 정상 운영 확인
1. 대시보드에서 실행 중인 StreamLive 채널 찾기
2. ℹ️ 버튼 클릭
3. "🟢 입력 상태: MAIN" 확인 → 정상
4. "검증: QueryInputStreamState, InputSourceRedundancy" 확인 → 정확한 검증

### 시나리오 2: Failover 확인
1. 대시보드에서 실행 중인 StreamLive 채널 찾기
2. ℹ️ 버튼 클릭
3. "⚠️ 입력 상태: BACKUP" 확인 → Failover 발생
4. "검증: QueryInputStreamState" 확인 → StreamLive API로 직접 확인됨
5. Main 입력 문제 확인 필요

### 시나리오 3: 여러 채널 일괄 확인
1. 대시보드에서 여러 StreamLive 채널 확인
2. 각 채널의 ℹ️ 버튼 클릭하여 입력 상태 확인
3. Backup 입력 사용 중인 채널 식별
4. 검증 소스로 정확성 확인

## 제한사항

1. **실행 중인 채널만 확인 가능**
   - 중지된 채널에서는 입력 상태를 확인할 수 없습니다
   - 채널이 실행 중(running)일 때만 입력 상태가 표시됩니다

2. **API 응답 시간**
   - 입력 상태 확인을 위해 추가 API 호출이 필요합니다
   - QueryInputStreamState API 호출 시간이 소요됩니다

3. **QueryInputStreamState 지원**
   - 일부 입력 타입은 QueryInputStreamState를 지원하지 않을 수 있습니다
   - 이 경우 StreamLink 플로우 상태로 fallback합니다
