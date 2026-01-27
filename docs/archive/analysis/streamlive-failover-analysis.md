# StreamLive Failover 기능 분석

## Failover 설정 확인

### 현재 채널 설정 (`cj_onstyle_2`)

**AttachedInputs:**
- Input 1: `69425CAF0000BBDE05D7`
  - `FailOverSettings.SecondaryInputId`: **없음**
  - `FailOverSettings.FailOverInputId`: **없음**
- Input 2: `696DBEAA525C101CD983`
  - `FailOverSettings.SecondaryInputId`: **없음**
  - `FailOverSettings.FailOverInputId`: **없음**

**결론:**
- ❌ **Failover 설정이 되어 있지 않음**
- 두 입력이 연결되어 있지만 Primary/Secondary 관계가 설정되지 않음

## Failover 설정이 필요한 이유

### Failover 설정이 있는 경우

```json
{
  "AttachedInputs": [
    {
      "Id": "input-1",
      "FailOverSettings": {
        "SecondaryInputId": "input-2"  // ← 이게 있어야 Failover 작동
      }
    }
  ]
}
```

**동작:**
- Primary 입력(`input-1`)이 실패하면 자동으로 Secondary 입력(`input-2`)으로 전환
- `SecondaryInputId`가 설정되어 있어야 자동 Failover 작동

### Failover 설정이 없는 경우 (현재 상태)

```json
{
  "AttachedInputs": [
    {
      "Id": "input-1",
      "FailOverSettings": {
        "SecondaryInputId": ""  // ← 비어있음
      }
    },
    {
      "Id": "input-2",
      "FailOverSettings": {
        "SecondaryInputId": ""  // ← 비어있음
      }
    }
  ]
}
```

**동작:**
- 두 입력이 모두 연결되어 있지만 Failover 관계가 설정되지 않음
- 자동 Failover 작동 안 함
- 수동 전환만 가능하거나 다른 방식으로 입력 선택

## Failover 동작 기준

### 1. 설정 기준

**필수 조건:**
- `AttachedInputs`에 2개 이상의 입력이 연결되어 있어야 함
- Primary 입력의 `FailOverSettings.SecondaryInputId`가 설정되어 있어야 함

**현재 상태:**
- ✅ 2개 입력 연결됨
- ❌ `SecondaryInputId` 설정 안 됨
- **결론: Failover 설정 안 됨**

### 2. 동작 기준 (추정)

Tencent Cloud 문서에 따르면 Failover는 다음 조건에서 발생:

1. **Primary 입력 실패 감지**
   - 네트워크 연결 끊김
   - 스트림 신호 없음
   - 입력 장치 오류

2. **Failover 시간 임계값**
   - 일정 시간 동안 Primary 입력이 실패하면 자동 전환
   - 설정 가능한 시간 임계값 (예: 5초, 10초)

3. **Secondary 입력 상태 확인**
   - Secondary 입력이 정상 상태여야 함
   - Secondary 입력도 실패하면 Failover 불가

### 3. 현재 설정에서의 동작

**현재 상태:**
- 두 입력이 모두 연결되어 있음
- 하지만 `SecondaryInputId`가 설정되지 않음

**가능한 동작:**
1. **수동 전환**: 사용자가 직접 입력을 선택/전환
2. **기본 입력 사용**: 첫 번째 입력을 기본으로 사용
3. **자동 Failover 없음**: Primary 실패 시 자동으로 Secondary로 전환되지 않음

## Failover 설정 방법

### 설정이 필요한 경우

StreamLive 채널을 수정하여 Failover 설정을 추가해야 함:

```python
# StreamLive 채널 수정
modify_req = mdl_models.ModifyStreamLiveChannelRequest()
modify_req.Id = channel_id

# AttachedInputs 수정
attached_input = mdl_models.AttachedInput()
attached_input.Id = primary_input_id
attached_input.FailOverSettings = mdl_models.FailOverSettings()
attached_input.FailOverSettings.SecondaryInputId = secondary_input_id

modify_req.AttachedInputs = [attached_input]
```

## 현재 채널 분석

### cj_onstyle_2 채널

**설정 상태:**
- Input 1: `69425CAF0000BBDE05D7` (Failover 설정 없음)
- Input 2: `696DBEAA525C101CD983` (Failover 설정 없음)

**실제 동작:**
- StreamLink 플로우 상태로 보면 MAIN 플로우가 활성화되어 있음
- 하지만 Failover 설정이 없으므로:
  - 자동 Failover는 작동하지 않음
  - Primary 입력이 실패해도 자동으로 Secondary로 전환되지 않음
  - 수동 전환이나 다른 방식으로 입력 선택

## 결론

### 현재 설정에서 Failover 가능 여부

**답변: ❌ Failover 설정이 되어 있지 않음**

**이유:**
1. `FailOverSettings.SecondaryInputId`가 비어있음
2. Primary/Secondary 입력 관계가 설정되지 않음
3. 자동 Failover 기능이 활성화되지 않음

### Failover를 사용하려면

1. **채널 수정 필요**
   - Primary 입력의 `FailOverSettings.SecondaryInputId` 설정
   - Secondary 입력 ID 지정

2. **설정 후 동작**
   - Primary 입력 실패 시 자동으로 Secondary 입력으로 전환
   - Failover 시간 임계값에 따라 전환

3. **현재는 수동 관리**
   - StreamLink 플로우 상태로 입력 선택
   - 수동으로 입력 전환 필요

## 권장 사항

1. **Failover 설정 추가**
   - Primary 입력에 Secondary 입력 ID 설정
   - 자동 Failover 기능 활성화

2. **모니터링 강화**
   - StreamLink 플로우 상태 모니터링
   - 입력 통계 확인
   - Failover 발생 시 알림

3. **다단계 검증 유지**
   - StreamLink 플로우 상태 확인 (현재 사용 중)
   - StreamLive 입력 통계 확인
   - StreamPackage 입력 확인
