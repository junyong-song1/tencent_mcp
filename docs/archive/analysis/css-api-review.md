# CSS API 문서 검토 결과

## 문서 확인

**문서 URL:** https://www.tencentcloud.com/ko/document/product/267/30760  
**서비스:** CSS (Live Streaming Service) - API Category

## 관련 API 목록

### Live Stream Management APIs

문서에서 확인된 API들:

1. **DescribeLiveStreamState** - Queries stream status
   - 현재 사용 중: ✅ (`_get_css_stream_status` 메서드)
   - 응답: `StreamState` (active/inactive/forbid)
   - **제한사항:** 활성 입력 소스 정보는 제공하지 않음

2. **DescribeLiveStreamOnlineList** - Queries live streams
   - 현재 사용 중: ❌
   - 가능성: 활성 스트림 목록 확인

3. **DescribeLiveStreamPublishedList** - Queries the list of pushed streams
   - 현재 사용 중: ❌
   - 가능성: 푸시된 스트림 목록 확인

4. **DescribeLiveStreamEventList** - Queries streaming events
   - 현재 사용 중: ❌
   - 가능성: 스트림 이벤트 (failover, input switch 등) 확인

## 현재 구현 상태

### DescribeLiveStreamState 사용

```python
def _get_css_stream_status(self, stream_name: str, domain: str = None):
    req = live_models.DescribeLiveStreamStateRequest()
    req.DomainName = domain
    req.AppName = parts[0]
    req.StreamName = "/".join(parts[1:])
    
    resp = client.DescribeLiveStreamState(req)
    stream_state = getattr(resp, "StreamState", "")
    is_active = stream_state in ["active", "ACTIVE"]
```

**제한사항:**
- 스트림 상태만 확인 (active/inactive/forbid)
- 활성 입력 소스 주소 정보 없음
- main/backup 구분 불가

## 추가 확인 필요 API

### 1. DescribeLiveStreamEventList

**가능성:**
- 스트림 이벤트 목록 확인
- Failover 이벤트, 입력 전환 이벤트 등 포함 가능
- 최근 이벤트에서 활성 입력 소스 추론 가능

**확인 필요:**
- 이벤트 타입에 failover/input switch 포함 여부
- 이벤트에 입력 소스 주소 정보 포함 여부

### 2. DescribeLiveStreamPublishedList

**가능성:**
- 푸시된 스트림 목록 확인
- 각 스트림의 푸시 소스 정보 포함 가능

**확인 필요:**
- 응답에 입력 소스 주소 정보 포함 여부
- main/backup 구분 가능 여부

### 3. DescribeLiveStreamOnlineList

**가능성:**
- 활성 스트림 목록 확인
- 각 스트림의 소스 정보 포함 가능

**확인 필요:**
- 응답에 입력 소스 주소 정보 포함 여부

## StreamLive (MDL) vs CSS (Live)

### 서비스 차이

**StreamLive (MDL):**
- 미디어 라이브 스트리밍 서비스
- 채널, 입력, 출력 관리
- `QueryInputStreamState` API 제공

**CSS (Live):**
- 라이브 스트리밍 서비스
- 도메인, 스트림 관리
- `DescribeLiveStreamState` API 제공

### 연관성

**StreamLive → CSS:**
- StreamLive 채널의 출력이 CSS로 전달될 수 있음
- StreamPackage를 통해 연결 가능

**현재 사용:**
- StreamPackage가 연결된 경우 CSS 검증 시도
- 하지만 CSS API로는 활성 입력 소스를 직접 확인할 수 없음

## 결론

### 현재 상황

1. **CSS API 한계:**
   - `DescribeLiveStreamState`: 스트림 상태만 확인
   - 활성 입력 소스 정보는 제공하지 않음

2. **추가 확인 필요:**
   - `DescribeLiveStreamEventList`: 이벤트에서 failover 정보 확인 가능 여부
   - `DescribeLiveStreamPublishedList`: 푸시 소스 정보 확인 가능 여부
   - `DescribeLiveStreamOnlineList`: 활성 스트림 소스 정보 확인 가능 여부

### 권장 사항

1. **추가 API 테스트:**
   - `DescribeLiveStreamEventList`로 failover 이벤트 확인
   - `DescribeLiveStreamPublishedList`로 푸시 소스 정보 확인

2. **문서 확인:**
   - 각 API의 상세 문서 확인
   - 응답 구조에서 입력 소스 정보 포함 여부 확인

3. **현재 로직 유지:**
   - StreamLive `QueryInputStreamState`가 가장 신뢰할 수 있는 방법
   - CSS API는 보조 검증용으로만 사용

## 다음 단계

1. `DescribeLiveStreamEventList` API 테스트
2. `DescribeLiveStreamPublishedList` API 테스트
3. 각 API의 상세 문서 확인
4. 응답 구조 분석
