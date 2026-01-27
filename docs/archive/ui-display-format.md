# Slack UI 표시 형식 가이드

## 개요

StreamLive 채널의 정보 버튼(ℹ️)을 클릭하면 입력 상태가 Slack에 표시됩니다.

## 실제 표시 형식

### 예제: Main 입력 활성 (QueryInputStreamState 확인)

```
*sbs_no1_news*
ID: `695E09660000090927DE`
서비스: StreamLive
상태: running

🟢 *입력 상태*: MAIN (695E065C00004F07D2D4)
   검증: QueryInputStreamState, InputSourceRedundancy (2단계)
   활성 소스: MAIN (rtmp://1353725051.ap-seoul-1.streamlive.myqcloud.c...)
   📦 StreamPackage 확인: MAIN
```

### 예제: Backup 입력 활성

```
*My StreamLive Channel*
ID: `channel-123`
서비스: StreamLive
상태: running

⚠️ *입력 상태*: BACKUP (backup-input-002)
   검증: QueryInputStreamState, InputSourceRedundancy (2단계)
   활성 소스: BACKUP (rtmp://...ap-seoul-2...)
```

## 표시 항목 설명

### 1. 채널 기본 정보

- **채널 이름**: StreamLive 채널 이름 (예: `sbs_no1_news`)
- **채널 ID**: Tencent Cloud 채널 ID (예: `695E09660000090927DE`)
- **서비스**: `StreamLive`
- **상태**: `running`, `stopped`, `idle`, `error` 등

### 2. 입력 상태

**이모지:**
- 🟢 (`:large_green_circle:`): MAIN 입력 활성
- ⚠️ (`:warning:`): BACKUP 입력 활성
- ❓ (`:question:`): 상태 확인 불가

**표시 형식:**
```
🟢 *입력 상태*: MAIN (695E065C00004F07D2D4)
```

**의미:**
- 현재 활성 입력 타입 (MAIN 또는 BACKUP)
- 활성 입력 ID 또는 이름

### 3. 검증 정보

**표시 형식:**
```
검증: QueryInputStreamState, InputSourceRedundancy (2단계)
```

**검증 소스:**
- `QueryInputStreamState`: StreamLive API에서 직접 확인 (가장 신뢰)
- `InputSourceRedundancy`: Input Source Redundancy 방식 감지
- `StreamLink`: StreamLink 플로우 상태 확인 (fallback)
- `CSS`: CSS 스트림 흐름 확인 (fallback)

**검증 레벨:**
- 검증 단계 수 (예: 2단계, 3단계)
- 더 많은 단계 = 더 신뢰할 수 있는 결과

### 4. 활성 소스 주소 (Input Source Redundancy인 경우)

**표시 형식:**
```
활성 소스: MAIN (rtmp://1353725051.ap-seoul-1.streamlive.myqcloud.c...)
```

**의미:**
- Input Source Redundancy 방식으로 구성됨
- 현재 활성 소스 주소 (ap-seoul-1 = main, ap-seoul-2 = backup)
- URL이 길면 50자로 잘림

### 5. StreamPackage 검증 (있는 경우)

**표시 형식:**
```
📦 StreamPackage 확인: MAIN
```

**의미:**
- StreamPackage에서 확인한 활성 입력
- StreamPackage가 연결되어 있는 경우에만 표시

## UI 표시 규칙

### 이모지 선택 규칙

```python
if active_input == "main":
    active_emoji = ":large_green_circle:"  # 🟢
elif active_input == "backup":
    active_emoji = ":warning:"  # ⚠️
else:
    active_emoji = ":question:"  # ❓
```

### 검증 소스 표시 규칙

1. **QueryInputStreamState가 있는 경우:**
   - 최우선 표시
   - StreamLive API에서 직접 확인됨

2. **InputSourceRedundancy가 있는 경우:**
   - Input Source Redundancy 방식으로 구성됨
   - 활성 소스 주소도 함께 표시

3. **StreamLink가 있는 경우:**
   - QueryInputStreamState가 실패한 경우 fallback
   - StreamLink 플로우 상태로 추론

4. **CSS가 있는 경우:**
   - 스트림 흐름 확인
   - 보조 검증

### 활성 소스 주소 표시 규칙

**표시 조건:**
- `is_input_source_redundancy == True`
- `active_source_address`가 설정됨

**표시 형식:**
- URL이 50자 이하: 전체 표시
- URL이 50자 초과: 50자로 잘라서 표시

**소스 타입 판단:**
- `ap-seoul-1` → `main`
- `ap-seoul-2` → `backup`

## 사용 예제

### 시나리오 1: 정상 운영 (Main 입력 활성)

**Slack 표시:**
```
*sbs_no1_news*
ID: `695E09660000090927DE`
서비스: StreamLive
상태: running

🟢 *입력 상태*: MAIN (695E065C00004F07D2D4)
   검증: QueryInputStreamState, InputSourceRedundancy (2단계)
   활성 소스: MAIN (rtmp://...ap-seoul-1...)
```

**의미:**
- Main 입력이 활성화되어 있음
- QueryInputStreamState API로 확인됨
- Input Source Redundancy 방식
- Main 소스 주소 (ap-seoul-1)가 활성

### 시나리오 2: Failover 발생 (Backup 입력 활성)

**Slack 표시:**
```
*My StreamLive Channel*
ID: `channel-123`
서비스: StreamLive
상태: running

⚠️ *입력 상태*: BACKUP (backup-input-002)
   검증: QueryInputStreamState, InputSourceRedundancy (2단계)
   활성 소스: BACKUP (rtmp://...ap-seoul-2...)
```

**의미:**
- Backup 입력이 활성화되어 있음
- QueryInputStreamState API로 확인됨
- Input Source Redundancy 방식
- Backup 소스 주소 (ap-seoul-2)가 활성
- Main 입력 문제 확인 필요

### 시나리오 3: 상태 확인 불가

**Slack 표시:**
```
*My StreamLive Channel*
ID: `channel-123`
서비스: StreamLive
상태: running

❓ *입력 상태*: 확인 불가
```

**의미:**
- 입력 상태를 확인할 수 없음
- API 오류 또는 입력 정보 없음

## 업데이트 사항

### QueryInputStreamState API 사용

**변경 전:**
- 검증 소스: `StreamLink`, `InputSourceRedundancy`, `CSS`
- StreamLink 플로우 상태로 추론

**변경 후:**
- 검증 소스: `QueryInputStreamState`, `InputSourceRedundancy`
- StreamLive API에서 직접 확인
- 더 정확한 활성 소스 확인

### 활성 소스 주소 표시 추가

**새로 추가된 정보:**
- Input Source Redundancy인 경우 활성 소스 주소 표시
- 소스 타입 (main/backup)과 URL 표시

## 결론

**Slack UI 표시 형식:**
1. 채널 기본 정보 (이름, ID, 서비스, 상태)
2. 입력 상태 (이모지 + MAIN/BACKUP)
3. 검증 정보 (검증 소스 + 레벨)
4. 활성 소스 주소 (Input Source Redundancy인 경우)
5. StreamPackage 검증 (있는 경우)

**검증 방법:**
- QueryInputStreamState API를 최우선으로 사용
- StreamLive가 직접 제공하는 상태 정보로 정확한 활성 소스 확인
