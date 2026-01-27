# FailoverSettings.SecondaryInputId가 비어있는 이유 분석

## 문제 상황

**사용자 지적:**
- StreamLink의 main/backup 플로우가 StreamLive의 main/backup 입력에 연결되어 있음
- 하지만 `FailOverSettings.SecondaryInputId`가 비어있음
- 이는 설정 문제인지, API 응답 문제인지 확인 필요

## 확인 결과

### StreamLink 플로우 상태
- `cj_onstyle_m2` (MAIN): `running`
- `cj_onstyle_b2` (BACKUP): `running`
- 두 플로우 모두 StreamLive 채널에 연결됨

### StreamLive 입력 상태
- Input 1: `69425CAF0000BBDE05D7`
- Input 2: `696DBEAA525C101CD983`
- Input 3: `696DC83753681085A29E` (3개 입력 존재)

### FailOverSettings 상태
- 모든 입력의 `FailOverSettings.SecondaryInputId`: **빈 문자열 ("")**
- `LossThreshold`: 0
- `RecoverBehavior`: 빈 문자열

## 가능한 원인

### 1. 실제로 Failover 설정이 안 되어 있음

**가능성: 높음**

**이유:**
- StreamLink 플로우가 연결되어 있어도 StreamLive의 Failover 기능은 별도로 설정해야 함
- 콘솔에서 "Input Failover" 토글을 켜고 Secondary 입력을 선택해야 함
- API로 채널을 생성/수정할 때 Failover 설정을 명시적으로 지정해야 함

**확인 방법:**
- Tencent Cloud 콘솔에서 채널 설정 확인
- "Input Settings" → "Input Failover" 토글이 켜져있는지 확인
- Secondary 입력이 선택되어 있는지 확인

### 2. 입력 타입이 Failover를 지원하지 않음

**가능성: 중간**

**요구사항:**
- Primary와 Secondary 입력이 **같은 타입**이어야 함
- **RTMP_PUSH** 또는 **RTP_PUSH** 타입만 Failover 지원
- URL_PULL, SRT_PUSH 등은 Failover 지원 안 됨

**확인 필요:**
- 각 입력의 타입 확인
- 입력 타입이 일치하는지 확인
- RTMP_PUSH 또는 RTP_PUSH인지 확인

### 3. API 응답 문제

**가능성: 낮음**

**이유:**
- API 응답에서 `FailOverSettings` 객체는 존재하지만 `SecondaryInputId`가 빈 문자열
- 설정이 되어 있어도 API가 제대로 반환하지 않을 수 있음
- 하지만 객체 자체는 존재하므로 설정이 안 되어 있을 가능성이 높음

### 4. StreamLink 레벨에서 Failover 관리

**가능성: 중간**

**이유:**
- StreamLink 플로우가 main/backup으로 구성되어 있음
- StreamLink 레벨에서 이미 failover가 관리되고 있을 수 있음
- StreamLive는 단순히 두 입력을 모두 받고, StreamLink가 어떤 플로우를 활성화할지 결정
- 따라서 StreamLive 레벨의 Failover 설정이 필요 없을 수 있음

## 결론

### 현재 상황

1. **StreamLink 플로우**: main/backup으로 구성되어 있고 모두 연결됨
2. **StreamLive 입력**: 3개 입력이 연결되어 있음
3. **FailOverSettings**: `SecondaryInputId`가 비어있음

### 가능한 시나리오

**시나리오 1: Failover 설정 누락**
- StreamLink 플로우는 연결되어 있지만
- StreamLive의 Failover 기능은 별도로 설정하지 않음
- 따라서 `SecondaryInputId`가 비어있음
- **해결**: 콘솔에서 Input Failover 설정 필요

**시나리오 2: StreamLink 레벨 Failover**
- StreamLink에서 main/backup 플로우를 관리
- StreamLive는 두 입력을 모두 받지만
- StreamLink가 어떤 플로우를 활성화할지 결정
- StreamLive 레벨의 Failover는 필요 없음
- **현재 상태**: 정상 (StreamLink가 관리)

**시나리오 3: 입력 타입 문제**
- 입력 타입이 RTMP_PUSH/RTP_PUSH가 아님
- 또는 입력 타입이 일치하지 않음
- Failover 설정 불가
- **해결**: 입력 타입 확인 및 수정 필요

## 권장 확인 사항

1. **입력 타입 확인**
   - 각 입력의 타입 확인
   - RTMP_PUSH 또는 RTP_PUSH인지 확인
   - 입력 타입이 일치하는지 확인

2. **콘솔 설정 확인**
   - Tencent Cloud 콘솔에서 채널 설정 확인
   - "Input Failover" 토글이 켜져있는지 확인
   - Secondary 입력이 선택되어 있는지 확인

3. **실제 동작 확인**
   - StreamLink 플로우 상태로 입력 선택이 되는지 확인
   - StreamLive 레벨의 Failover가 필요한지 확인
   - StreamLink 레벨에서만 관리해도 되는지 확인

## 최종 답변

**현재 설정에서 Failover 가능 여부:**
- StreamLink 플로우는 main/backup으로 연결되어 있음 ✅
- 하지만 StreamLive의 `FailOverSettings.SecondaryInputId`는 비어있음 ❌

**가능한 이유:**
1. StreamLink 레벨에서만 Failover 관리 (StreamLive 설정 불필요)
2. 실제로 StreamLive Failover 설정이 누락됨
3. 입력 타입이 Failover를 지원하지 않음

**확인 필요:**
- 입력 타입 확인
- 콘솔 설정 확인
- 실제 동작 방식 확인
