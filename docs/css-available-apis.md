# CSS API 확인 가능한 정보

Tencent Cloud CSS (Live) API에서 제공하는 모든 정보를 확인할 수 있습니다!

## 확인 가능한 API 목록

### 1. 대역폭/트래픽 정보

| API | 설명 | 확인 가능한 정보 |
|-----|------|------------------|
| `DescribeBillBandwidthAndFluxList` | 재생 대역폭/트래픽 | 재생 대역폭, 트래픽 데이터 |
| `DescribePushBandwidthAndFluxList` | 푸시 대역폭/트래픽 | 푸시 대역폭, 트래픽 데이터 |
| `DescribeStreamDayPlayInfoList` | 스트림 일일 재생 정보 | 일일 재생 데이터 |

### 2. 스트림 품질 정보

| API | 설명 | 확인 가능한 정보 |
|-----|------|------------------|
| `DescribeStreamPushInfoList` | 푸시 품질 데이터 | 푸시 비트레이트, 프레임레이트, 해상도 등 |
| `DescribeStreamPlayInfoList` | 재생 정보 | 재생 비트레이트, 시청자 수, 품질 등 |
| `DescribeLiveStreamPushInfoList` | 온라인 스트림 푸시 정보 | 푸시 URL, 상태 등 (일부 구현됨) |

### 3. 시청자 수 정보

| API | 설명 | 확인 가능한 정보 |
|-----|------|------------------|
| `DescribeStreamPlayInfoList` | 재생 정보 | 시청자 수, 재생 시간 등 |
| `DescribeAllStreamPlayInfoList` | 모든 스트림 재생 데이터 | 시청자 수 집계 |

### 4. 로그 정보

| API | 설명 | 확인 가능한 정보 |
|-----|------|------------------|
| `DescribeLogDownloadList` | 로그 다운로드 URL | 로그 파일 다운로드 링크 |
| `DescribeLiveStreamEventList` | 스트림 이벤트 목록 | 스트림 이벤트 (시작, 중단 등) |
| `DescribeCallbackRecordsList` | 콜백 이벤트 기록 | 콜백 이벤트 로그 |

### 5. 통계 정보

| API | 설명 | 확인 가능한 정보 |
|-----|------|------------------|
| `DescribeProIspPlaySumInfoList` | 지역/ISP별 재생 통계 | 지역별, ISP별 재생 데이터 |
| `DescribeHttpStatusInfoList` | HTTP 상태코드 통계 | HTTP 상태코드별 통계 |
| `DescribePlayErrorCodeDetailInfoList` | 재생 오류코드 상세 | 재생 오류 상세 정보 |

## 현재 구현된 API

✅ **이미 구현됨:**
- `DescribeLiveDomains` - 도메인 목록
- `DescribeLiveStreamOnlineList` - 활성 스트림 목록
- `DescribeLiveStreamState` - 스트림 상태
- `DescribeLiveStreamPushInfoList` - 푸시 정보 (일부)

## 추가 구현 가능한 API

다음 API들을 추가로 구현할 수 있습니다:

### 우선순위 높음 (OTT 운영에 유용)

1. **대역폭/트래픽**
   - `DescribeBillBandwidthAndFluxList` - 재생 대역폭/트래픽
   - `DescribePushBandwidthAndFluxList` - 푸시 대역폭/트래픽

2. **스트림 품질**
   - `DescribeStreamPushInfoList` - 푸시 품질 (비트레이트, 프레임레이트 등)
   - `DescribeStreamPlayInfoList` - 재생 품질 및 시청자 수

3. **로그**
   - `DescribeLiveStreamEventList` - 스트림 이벤트 목록
   - `DescribeLogDownloadList` - 로그 다운로드

### 우선순위 중간

4. **통계**
   - `DescribeProIspPlaySumInfoList` - 지역/ISP별 통계
   - `DescribeHttpStatusInfoList` - HTTP 상태코드 통계

## 구현 제안

이 API들을 추가로 구현하면:

✅ **대역폭 사용량** 확인 가능
✅ **시청자 수** 확인 가능  
✅ **스트림 품질** (비트레이트, 프레임레이트, 해상도) 확인 가능
✅ **상세 로그** (이벤트, 오류 등) 확인 가능

필요하시면 이 API들을 추가로 구현하겠습니다!
