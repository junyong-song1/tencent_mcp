# StreamLive Failover 기준 상세 설명

## Failover 동작 기준

### 1. 설정 기준 (필수 조건)

**Failover가 작동하려면:**

1. **2개 이상의 입력 연결**
   - ✅ 현재: 2개 입력 연결됨
   - Input 1: `69425CAF0000BBDE05D7`
   - Input 2: `696DBEAA525C101CD983`

2. **SecondaryInputId 설정**
   - ❌ 현재: **설정 안 됨**
   - Primary 입력의 `FailOverSettings.SecondaryInputId`에 Secondary 입력 ID가 설정되어 있어야 함

3. **입력 타입 일치**
   - Primary와 Secondary 입력이 같은 타입이어야 함 (예: 둘 다 RTMP_PUSH)

4. **Pipeline 개수 일치**
   - Primary와 Secondary 입력의 Pipeline 개수가 같아야 함

### 2. Failover 트리거 조건

**Failover가 발생하는 경우:**

1. **Primary 입력 데이터 손실**
   - Primary 입력에서 데이터가 들어오지 않을 때
   - 네트워크 연결 끊김
   - 스트림 신호 없음
   - 입력 장치 오류

2. **LossThreshold 시간 초과**
   - 기본값: **3000ms (3초)**
   - Primary 입력에서 데이터가 없을 때 이 시간 동안 지속되면 Failover 발생
   - 설정 가능 (예: 5000ms, 10000ms)

3. **Secondary 입력 정상 상태**
   - Secondary 입력이 정상 상태여야 함
   - Secondary 입력도 실패하면 Failover 불가

### 3. Failover 동작 방식

**전환 과정:**
```
1. Primary 입력에서 데이터 수신 중 (정상)
   ↓
2. Primary 입력 데이터 손실 감지
   ↓
3. LossThreshold 시간 동안 대기 (기본 3초)
   ↓
4. Secondary 입력으로 자동 전환
   ↓
5. Secondary 입력에서 스트림 서비스 계속
```

**복구 동작 (RecoverBehavior):**

- **CURRENT_PREFERRED** (기본값)
  - Primary 입력이 복구되어도 Secondary 입력에 계속 머무름
  - 수동 전환 필요

- **PRIMARY_PREFERRED**
  - Primary 입력이 복구되면 자동으로 Primary로 다시 전환

## 현재 설정 분석

### cj_onstyle_2 채널

**설정 상태:**
```
Input 1: 69425CAF0000BBDE05D7
  FailOverSettings:
    SecondaryInputId: ❌ 없음
    LossThreshold: 기본값 (3000ms)
    RecoverBehavior: 기본값 (CURRENT_PREFERRED)

Input 2: 696DBEAA525C101CD983
  FailOverSettings:
    SecondaryInputId: ❌ 없음
    LossThreshold: 기본값 (3000ms)
    RecoverBehavior: 기본값 (CURRENT_PREFERRED)
```

**Failover 가능 여부:**
- ❌ **Failover 설정 안 됨**
- `SecondaryInputId`가 비어있어서 자동 Failover 작동 안 함

### 현재 동작 방식

**Failover가 설정되지 않은 경우:**

1. **수동 전환**
   - 사용자가 직접 입력을 선택/전환
   - StreamLink 플로우 상태로 입력 선택

2. **기본 입력 사용**
   - 첫 번째 입력을 기본으로 사용
   - StreamLink 플로우 상태에 따라 입력 선택

3. **자동 Failover 없음**
   - Primary 입력이 실패해도 자동으로 Secondary로 전환되지 않음
   - 수동 개입 필요

## Failover 설정 방법

### 설정이 필요한 경우

**채널 수정 API 사용:**
```python
modify_req = mdl_models.ModifyStreamLiveChannelRequest()
modify_req.Id = channel_id

# Primary 입력 설정
attached_input = mdl_models.AttachedInput()
attached_input.Id = primary_input_id  # Input 1

# Failover 설정
failover_settings = mdl_models.FailOverSettings()
failover_settings.SecondaryInputId = secondary_input_id  # Input 2
failover_settings.LossThreshold = 3000  # 3초 (선택)
failover_settings.RecoverBehavior = "PRIMARY_PREFERRED"  # 선택

attached_input.FailOverSettings = failover_settings
modify_req.AttachedInputs = [attached_input]
```

**설정 후:**
- Primary 입력 실패 시 자동으로 Secondary 입력으로 전환
- LossThreshold 시간 동안 Primary 입력이 실패하면 전환
- RecoverBehavior에 따라 Primary 복구 시 동작 결정

## 결론

### 현재 설정에서 Failover 가능 여부

**답변: ❌ Failover 설정이 되어 있지 않아 자동 Failover가 작동하지 않음**

**이유:**
1. `FailOverSettings.SecondaryInputId`가 비어있음
2. Primary/Secondary 입력 관계가 설정되지 않음
3. 자동 Failover 기능이 활성화되지 않음

### Failover를 사용하려면

1. **채널 수정 필요**
   - Primary 입력의 `SecondaryInputId` 설정
   - LossThreshold 설정 (선택)
   - RecoverBehavior 설정 (선택)

2. **설정 후 동작**
   - Primary 입력 실패 시 자동으로 Secondary 입력으로 전환
   - LossThreshold 시간 동안 Primary 입력이 실패하면 전환

3. **현재는 수동 관리**
   - StreamLink 플로우 상태로 입력 선택
   - 수동으로 입력 전환 필요

## 권장 사항

1. **Failover 설정 추가**
   - Primary 입력에 Secondary 입력 ID 설정
   - 자동 Failover 기능 활성화
   - LossThreshold 적절히 설정 (3-5초 권장)

2. **모니터링 강화**
   - StreamLink 플로우 상태 모니터링
   - 입력 통계 확인
   - Failover 발생 시 알림

3. **RecoverBehavior 선택**
   - `PRIMARY_PREFERRED`: Primary 복구 시 자동 전환
   - `CURRENT_PREFERRED`: 수동 전환 유지
