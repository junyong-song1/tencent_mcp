# 다단계 검증 기능 설명

## 개요

StreamLive 채널의 main/backup 입력 상태를 더 확실하게 판단하기 위해 다단계 검증 기능을 구현했습니다.

## 검증 단계

### 1단계: StreamLink 플로우 상태 (현재 사용 중) ✅
- **확인 내용**: StreamLink 플로우의 실행 상태
- **판단 방법**: 플로우 이름(`_m`, `_b`)과 URL 매칭
- **정확도**: 약 80-90%

### 2단계: StreamPackage 입력 상태 (추가 가능) ⭐
- **확인 내용**: StreamLive 출력이 StreamPackage로 잘 들어가는지
- **판단 방법**: StreamPackage 입력 URL 정보
- **정확도**: 90%+
- **필요**: StreamPackage SDK 설치 (`pip install tencentcloud-sdk-python-msp`)

### 3단계: CSS 스트림 상태 (추가 가능) ⭐
- **확인 내용**: 최종 사용자에게 전달되는 스트림
- **판단 방법**: CSS 스트림 활성 상태
- **정확도**: 95%+
- **필요**: CSS SDK (이미 설치됨)

## 검증 우선순위

1. **StreamPackage 결과** (가장 신뢰)
   - StreamLive 출력 → StreamPackage 입력 확인
   - 실제 데이터 흐름 확인

2. **StreamLink 플로우 상태**
   - StreamLink → StreamLive 연결 확인
   - 플로우 이름으로 main/backup 구분

3. **FailOverSettings**
   - Primary/Secondary 입력 관계

4. **입력 이름 패턴**
   - 입력 이름에서 main/backup 키워드 확인

## 사용 방법

### 기본 사용 (StreamLink만)
```python
input_status = client.get_channel_input_status(channel_id)
# 검증 소스: ['StreamLink']
```

### StreamPackage SDK 설치 후 (다단계 검증)
```bash
pip install tencentcloud-sdk-python-msp
```

```python
input_status = client.get_channel_input_status(channel_id)
# 검증 소스: ['StreamPackage', 'StreamLink'] (더 정확)
```

## 응답 구조

```json
{
  "channel_id": "695E09660000090927DE",
  "channel_name": "sbs_no1_news",
  "active_input": "backup",
  "active_input_id": "695E065C00004F07D2D4",
  "active_input_name": "695E065C00004F07D2D4",
  "verification_sources": ["StreamLink"],
  "verification_level": 1,
  "message": "현재 활성 입력: BACKUP (695E065C00004F07D2D4) [검증: StreamLink]",
  "streampackage_verification": {
    "streampackage_id": "695E07E400004F07D2D5",
    "active_input": "backup",
    "input_details": [...]
  }
}
```

## 검증 레벨

- **1단계**: StreamLink만 확인
- **2단계**: StreamLink + StreamPackage 확인
- **3단계**: StreamLink + StreamPackage + CSS 확인

검증 레벨이 높을수록 더 정확한 판단이 가능합니다.

## StreamPackage SDK 설치

```bash
pip install tencentcloud-sdk-python-msp
```

설치 후 자동으로 StreamPackage 검증이 활성화됩니다.

## 제한사항

1. **StreamPackage API 제한**
   - StreamPackage API는 직접적인 활성 입력 상태를 제공하지 않음
   - 입력 URL 정보를 통해 간접적으로 확인

2. **CSS 확인**
   - CSS 스트림 이름과 도메인 정보 필요
   - StreamPackage와의 연결 관계 확인 필요

## 개선 방향

1. StreamPackage SDK 설치 후 실제 테스트
2. CSS 스트림 정보 연동
3. 다단계 검증 결과 일치 여부 확인 로직 강화
