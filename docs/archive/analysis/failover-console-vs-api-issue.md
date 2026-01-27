# StreamLive Failover: 콘솔 설정 vs API 응답 불일치 문제

## 사용자 확인 사항

1. **StreamLink input failover**: 사용 안 함
2. **StreamLive failover 기능**: 켜짐
3. **입력 타입**: RTMP_PUSH (동일)

## 문제 상황

- 콘솔에서 StreamLive failover 기능을 켰다고 함
- 하지만 API 응답에서 `FailOverSettings.SecondaryInputId`가 비어있음
- 입력 타입은 RTMP_PUSH로 동일하여 Failover 지원됨

## 원인 분석

### Tencent Cloud 문서에 따르면

**Failover 설정 완료를 위해서는:**

1. **"Input Failover" 토글 켜기** ✅ (사용자가 완료)
2. **"Select Backup Input" 선택** ❓ (확인 필요)
   - Primary 입력을 선택한 후
   - Secondary 입력을 드롭다운에서 선택해야 함
   - 이 단계를 완료하지 않으면 `SecondaryInputId`가 설정되지 않음

### API 응답 분석

현재 API 응답:
```json
{
  "AttachedInputs": [
    {
      "Id": "69425CAF0000BBDE05D7",
      "FailOverSettings": {
        "SecondaryInputId": "",  // ← 비어있음
        "LossThreshold": 0,
        "RecoverBehavior": ""
      }
    },
    {
      "Id": "696DBEAA525C101CD983",
      "FailOverSettings": {
        "SecondaryInputId": "",  // ← 비어있음
        "LossThreshold": 0,
        "RecoverBehavior": ""
      }
    },
    {
      "Id": "696DC83753681085A29E",
      "FailOverSettings": {
        "SecondaryInputId": "",  // ← 비어있음
        "LossThreshold": 0,
        "RecoverBehavior": ""
      }
    }
  ]
}
```

**분석:**
- `FailOverSettings` 객체는 존재함 (토글은 켜져있음)
- 하지만 `SecondaryInputId`가 비어있음
- `LossThreshold`가 0 (기본값, 설정 안 됨)
- `RecoverBehavior`가 빈 문자열 (설정 안 됨)

## 가능한 원인

### 1. Backup Input 선택 단계 누락 (가장 가능성 높음)

**증상:**
- 콘솔에서 "Input Failover" 토글은 켜져있음
- 하지만 "Select Backup Input" 드롭다운에서 Secondary 입력을 선택하지 않음
- 결과: `SecondaryInputId`가 비어있음

**확인 방법:**
- Tencent Cloud 콘솔에서 채널 설정 확인
- "Input Settings" → "Input Failover" 섹션 확인
- Primary 입력 옆에 "Backup Input" 드롭다운이 있고 선택되어 있는지 확인

### 2. 설정 저장/적용 누락

**증상:**
- 콘솔에서 모든 설정을 완료했지만
- "Save" 또는 "Confirm" 버튼을 누르지 않음
- 결과: 설정이 저장되지 않아 API에 반영 안 됨

**확인 방법:**
- 콘솔에서 설정을 다시 확인하고 "Save" 버튼 클릭
- 몇 분 후 API 응답 다시 확인

### 3. API 동기화 지연

**증상:**
- 콘솔에서 설정을 완료했지만
- API 응답에 아직 반영되지 않음
- 결과: 일시적인 불일치

**확인 방법:**
- 몇 분 후 API 응답 다시 확인
- 또는 콘솔에서 설정을 다시 저장

### 4. 입력 연결 문제

**증상:**
- 3개 입력이 연결되어 있음
- 어떤 입력이 Primary이고 어떤 입력이 Secondary인지 불명확
- 결과: Failover 관계 설정 불가

**확인 필요:**
- StreamLink main 플로우와 연결된 입력이 Primary
- StreamLink backup 플로우와 연결된 입력이 Secondary
- 이 관계가 콘솔에서 제대로 설정되었는지 확인

## 해결 방법

### 1. 콘솔에서 Failover 설정 완료

**단계:**
1. Tencent Cloud 콘솔 → StreamLive → Channel Management
2. 해당 채널 선택 → Edit
3. "Input Settings" 섹션으로 이동
4. "Input Failover" 토글이 켜져있는지 확인
5. **중요**: Primary 입력 옆에 "Backup Input" 드롭다운에서 Secondary 입력 선택
6. "Loss Threshold" 설정 (선택사항, 기본값 사용 가능)
7. "Recover Behavior" 설정 (선택사항, 기본값 사용 가능)
8. "Save" 또는 "Confirm" 버튼 클릭

### 2. 입력 매칭 확인

**StreamLink → StreamLive 입력 매칭:**
- MAIN 플로우 (`cj_onstyle_m2`) → StreamLive Input (Primary로 설정)
- BACKUP 플로우 (`cj_onstyle_b2`) → StreamLive Input (Secondary로 설정)

**확인 방법:**
- StreamLink 플로우의 출력 URL과 StreamLive 입력의 엔드포인트 매칭
- MAIN 플로우와 연결된 입력을 Primary로 설정
- BACKUP 플로우와 연결된 입력을 Secondary로 설정

### 3. API 응답 재확인

설정 완료 후:
```python
# API로 확인
resp = mdl_cli.DescribeStreamLiveChannel(req)
for att in resp.Info.AttachedInputs:
    failover = att.FailOverSettings
    if failover.SecondaryInputId:
        print(f"✅ Failover 설정됨: Primary={att.Id}, Secondary={failover.SecondaryInputId}")
```

## 예상 결과

설정이 완료되면:
```json
{
  "AttachedInputs": [
    {
      "Id": "69425CAF0000BBDE05D7",  // Primary Input
      "FailOverSettings": {
        "SecondaryInputId": "696DBEAA525C101CD983",  // ← Secondary Input ID
        "LossThreshold": 3000,  // 또는 설정한 값
        "RecoverBehavior": "CURRENT_PREFERRED"  // 또는 설정한 값
      }
    },
    {
      "Id": "696DBEAA525C101CD983",  // Secondary Input
      "FailOverSettings": {
        "SecondaryInputId": "",  // Secondary는 SecondaryInputId 없음
        "LossThreshold": 0,
        "RecoverBehavior": ""
      }
    }
  ]
}
```

## 결론

**현재 상황:**
- StreamLive failover 기능은 콘솔에서 켜져있음
- 하지만 "Select Backup Input" 단계가 완료되지 않았을 가능성이 높음
- 또는 설정이 저장되지 않았을 수 있음

**확인 필요:**
1. 콘솔에서 "Backup Input" 드롭다운에서 Secondary 입력이 선택되어 있는지 확인
2. 설정을 저장했는지 확인
3. 몇 분 후 API 응답 다시 확인

**다음 단계:**
- 콘솔에서 Failover 설정을 완전히 완료
- API 응답에서 `SecondaryInputId`가 설정되었는지 확인
