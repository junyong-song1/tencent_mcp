# StreamLive Failover: Input Source Redundancy vs Channel-level Failover

## 현재 설정 분석

**이미지에서 확인된 설정:**
- 입력 이름: `3tier_3pro_tv`
- 입력 타입: `RTMP_PUSH`
- **InputAddress01**: `rtmp://1353725051.ap-seoul-1.streamlive.myqcloud.com/...`
- **InputAddress02**: `rtmp://1353725051.ap-seoul-2.streamlive.myqcloud.com/...`

**핵심:**
- 하나의 입력에 두 개의 소스 주소가 설정되어 있음
- 이것은 **Input Source Redundancy (입력 소스 중복)** 방식

## 두 가지 Failover 방식

### 방식 1: Input Source Redundancy (입력 소스 중복)

**설정 방법:**
- 하나의 입력 객체에 여러 소스 주소를 설정
- InputAddress01, InputAddress02 등
- 입력의 "Details"에서 여러 주소 확인 가능

**동작 방식:**
```
하나의 입력 (3tier_3pro_tv)
  ├─ InputAddress01 (ap-seoul-1) ← Primary 소스
  └─ InputAddress02 (ap-seoul-2) ← Backup 소스
  
InputAddress01 실패 → 자동으로 InputAddress02로 전환
```

**특징:**
- ✅ 입력 레벨에서 소스 중복 제공
- ✅ StreamLive가 자동으로 사용 가능한 소스로 전환
- ✅ `FailOverSettings.SecondaryInputId` 불필요
- ✅ API 응답에서 `SecondaryInputId`가 비어있어도 정상

**현재 설정:**
- ✅ 이 방식으로 구성됨
- ✅ Failover 기능 작동함

### 방식 2: Channel-level Failover (채널 레벨 Failover)

**설정 방법:**
- 두 개의 별도 입력을 채널에 추가
- Primary 입력과 Secondary 입력 설정
- `FailOverSettings.SecondaryInputId`로 연결

**동작 방식:**
```
채널
  ├─ Input 1 (Primary) ← FailOverSettings.SecondaryInputId = Input 2
  └─ Input 2 (Secondary)
  
Input 1 실패 → 자동으로 Input 2로 전환
```

**특징:**
- ✅ 채널 레벨에서 입력 간 전환
- ✅ `FailOverSettings.SecondaryInputId` 필요
- ✅ API 응답에서 `SecondaryInputId`에 Secondary 입력 ID 설정됨

**현재 설정:**
- ❌ 이 방식으로 구성 안 됨
- ❌ `SecondaryInputId`가 비어있음

## 차이점 비교

| 항목 | Input Source Redundancy | Channel-level Failover |
|------|------------------------|------------------------|
| **설정 위치** | 하나의 입력 내부 | 채널 레벨 (두 입력 간) |
| **소스 주소** | InputAddress01, InputAddress02 | 별도 입력 객체 |
| **SecondaryInputId** | 불필요 (비어있어도 정상) | 필요 (Secondary 입력 ID) |
| **API 응답** | `SecondaryInputId: ""` (정상) | `SecondaryInputId: "input-id"` |
| **Failover 범위** | 입력 소스 간 전환 | 입력 객체 간 전환 |
| **설정 복잡도** | 낮음 (하나의 입력에 여러 주소) | 높음 (두 입력 추가 및 연결) |

## 현재 설정에서의 Failover 동작

**현재 설정:**
- 하나의 입력 (`3tier_3pro_tv`)에 두 개의 소스 주소 설정
- InputAddress01 (ap-seoul-1)
- InputAddress02 (ap-seoul-2)

**Failover 동작:**
1. InputAddress01 (ap-seoul-1)에서 스트림 수신 중
2. InputAddress01 실패 감지
3. 자동으로 InputAddress02 (ap-seoul-2)로 전환
4. InputAddress02에서 스트림 서비스 계속

**결론:**
- ✅ **Failover가 작동합니다!**
- ✅ Input Source Redundancy 방식으로 구성됨
- ✅ `SecondaryInputId`가 비어있어도 정상 (이 방식에서는 불필요)

## 왜 SecondaryInputId가 비어있는가?

**이유:**
- Input Source Redundancy 방식에서는 `SecondaryInputId`가 필요 없음
- 하나의 입력 객체 내부에서 소스 주소 간 전환
- Channel-level Failover가 아니므로 `SecondaryInputId`가 비어있음
- 이것은 정상적인 상태

## 언제 Channel-level Failover가 필요한가?

**Channel-level Failover가 필요한 경우:**
- 두 개의 완전히 다른 입력 소스를 사용해야 할 때
- 입력 타입이 다른 경우 (예: 하나는 RTMP_PUSH, 다른 하나는 RTP_PUSH)
- 입력 설정이 완전히 다른 경우
- 더 세밀한 Failover 제어가 필요한 경우

**현재 설정:**
- Input Source Redundancy로 충분함
- 두 개의 소스 주소가 같은 입력에 설정되어 있음
- Channel-level Failover는 불필요

## 결론

**현재 설정:**
- ✅ Input Source Redundancy 방식으로 구성됨
- ✅ Failover 기능 작동함
- ✅ `SecondaryInputId`가 비어있어도 정상 (이 방식에서는 불필요)

**사용자 질문에 대한 답변:**
- "현재 이렇게 input에서 설정이 되어져 있는데 그럼 failover가 일어나느거잖아~"
- **맞습니다!** Input Source Redundancy 방식으로 Failover가 작동합니다.
- `SecondaryInputId`가 비어있는 것은 정상입니다 (이 방식에서는 필요 없음).
