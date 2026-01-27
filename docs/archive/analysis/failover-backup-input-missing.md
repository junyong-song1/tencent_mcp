# StreamLive Failover: Backup Input이 채널에 추가되지 않음

## 문제 상황

**사용자 확인:**
- 콘솔에서 "Input Setting" 섹션 확인
- 현재 채널에 **단 하나의 입력만** 추가되어 있음
- "Input Pipeline Failover" 토글은 켜져 있음
- 하지만 **backup input 드롭다운에 선택할 입력이 없음**

## 원인 분석

### StreamLink vs StreamLive 입력 관계

**StreamLink 플로우:**
- MAIN 플로우 (`cj_onstyle_m2`): StreamLive 입력 엔드포인트로 연결됨
- BACKUP 플로우 (`cj_onstyle_b2`): StreamLive 입력 엔드포인트로 연결됨

**StreamLive 채널:**
- StreamLink MAIN 플로우와 연결된 입력만 채널에 추가됨
- StreamLink BACKUP 플로우와 연결된 입력은 채널에 추가되지 않음

### 핵심 문제

**StreamLive Failover가 작동하려면:**
1. ✅ "Input Pipeline Failover" 토글 켜기 (완료)
2. ❌ **백업 입력을 채널에 추가하기** (누락)
3. ❌ 백업 입력을 Primary 입력의 Failover 설정에서 선택하기 (불가능 - 백업 입력이 없음)

**현재 상태:**
- 채널에 입력이 1개만 추가되어 있음
- 따라서 backup input 드롭다운에 선택할 입력이 없음
- Failover 설정이 완료되지 않음

## 해결 방법

### 1. StreamLink BACKUP 플로우와 연결된 StreamLive 입력 확인

**StreamLink BACKUP 플로우:**
- 플로우 이름: `cj_onstyle_b2`
- 출력 URL: `rtmp://...ap-seoul-2.../f4ed1a71cf914d73972ec6d1341af8d3`

**StreamLive 입력 엔드포인트:**
- `rtmp://...ap-seoul-2.../f4ed1a71cf914d73972ec6d1341af8d3` (BACKUP 플로우와 매칭)

### 2. StreamLive 채널에 백업 입력 추가

**단계:**
1. Tencent Cloud 콘솔 → StreamLive → Channel Management
2. 해당 채널 선택 → Edit
3. "Input Setting" 섹션으로 이동
4. **"Add" 버튼 클릭**하여 입력 추가
5. StreamLink BACKUP 플로우와 연결된 StreamLive 입력을 선택
   - 입력 타입: RTMP_PUSH (Primary 입력과 동일해야 함)
   - 입력 엔드포인트: `rtmp://...ap-seoul-2.../f4ed1a71cf914d73972ec6d1341af8d3`
6. 입력 추가 완료

### 3. Failover 설정 완료

**단계:**
1. "Input Pipeline Failover" 토글이 켜져있는지 확인
2. Primary 입력 (StreamLink MAIN 플로우와 연결된 입력) 옆의 "Backup Input" 드롭다운에서
3. 방금 추가한 백업 입력 (StreamLink BACKUP 플로우와 연결된 입력) 선택
4. "Save" 또는 "Confirm" 버튼 클릭

### 4. 확인

설정 완료 후:
- 채널에 입력이 2개 추가되어 있음
- Primary 입력의 Failover 설정에서 Secondary 입력이 선택됨
- API 응답에서 `FailOverSettings.SecondaryInputId`가 설정됨

## 중요 사항

### 입력 타입 일치

**요구사항:**
- Primary 입력과 Secondary 입력이 **같은 타입**이어야 함
- RTMP_PUSH 입력은 RTMP_PUSH 입력과만 Failover 가능
- 입력 타입이 다르면 Failover 설정 불가

### Pipeline 개수 일치

**요구사항:**
- Primary 입력과 Secondary 입력의 **Pipeline 개수가 같아야 함**
- Pipeline 개수가 다르면 Failover 설정 불가

### StreamLink 플로우 연결

**현재 구조:**
```
StreamLink MAIN 플로우 → StreamLive 입력 1 (Primary)
StreamLink BACKUP 플로우 → StreamLive 입력 2 (Secondary)
```

**StreamLive Failover 동작:**
- Primary 입력 (StreamLink MAIN)이 실패하면
- 자동으로 Secondary 입력 (StreamLink BACKUP)으로 전환
- StreamLink 레벨의 failover와는 별개로 StreamLive 레벨에서도 failover 작동

## 결론

**현재 문제:**
- StreamLink BACKUP 플로우와 연결된 StreamLive 입력이 채널에 추가되지 않음
- 따라서 backup input 드롭다운에 선택할 입력이 없음
- Failover 설정이 완료되지 않음

**해결:**
1. StreamLink BACKUP 플로우와 연결된 StreamLive 입력을 채널에 추가
2. Primary 입력의 Failover 설정에서 백업 입력 선택
3. 설정 저장

**결과:**
- 채널에 입력이 2개 추가됨
- Failover 설정 완료
- API 응답에서 `SecondaryInputId`가 설정됨
