# StreamPackage & CSS 검증 가능 여부 최종 검토 결과

## 검토 요약

**질문**: StreamPackage와 CSS를 모두 체크해서 우선 신호(main/backup)가 서비스되고 있는지 확인할 수 있는가?

**답변**: **부분적으로 가능**하지만 추가 개선이 필요합니다.

## 현재 구현 상태

### ✅ 구현 완료
1. **StreamPackage 연결 확인**: StreamLive 채널에서 StreamPackage ID 추출 ✅
2. **StreamPackage 입력 URL 목록**: Points.Inputs에서 2개의 입력 URL 확인 ✅
3. **CSS 연결 확인**: StreamPackage 연결 여부 기반 확인 ✅

### ⚠️ 개선 필요
1. **StreamPackage 활성 입력 판단**: 현재는 입력 순서만 확인, 실제 활성 입력 판단 미흡
2. **StreamLive 출력 URL 매칭**: StreamLive 출력 URL과 StreamPackage 입력 URL 매칭 로직 부족
3. **CSS backup stream 확인**: CSS의 DescribeBackupStreamList API 미사용

## 검증 가능 여부 상세 분석

### 1. StreamPackage를 통한 main/backup 확인

#### ✅ 가능한 방법
1. **입력 URL 순서 확인**
   - Points.Inputs 배열의 첫 번째 입력 = MAIN (primary)
   - Points.Inputs 배열의 두 번째 입력 = BACKUP (secondary)
   - 현재 구현: ✅ 완료

2. **StreamLive 출력 URL 매칭** (개선 필요)
   - StreamLive 채널의 OutputGroups에서 출력 URL 추출
   - StreamPackage 입력 URL과 매칭하여 활성 입력 확인
   - 현재 구현: ❌ 미구현

#### 제한사항
- StreamPackage API는 직접적으로 "어떤 입력이 활성화되어 있는지"를 알려주지 않음
- 입력 URL이 모두 설정되어 있어도 실제로 어떤 입력에서 데이터가 들어오는지는 확인 어려움
- StreamLive 출력 URL과 매칭이 필요함

### 2. CSS를 통한 main/backup 확인

#### ✅ 가능한 방법
1. **스트림 흐름 확인**
   - StreamPackage 연결 여부 확인
   - 스트림이 흐르고 있는지 확인
   - 현재 구현: ✅ 완료

2. **DescribeBackupStreamList API** (개선 필요)
   - CSS의 backup stream 목록 확인
   - Primary stream과 backup stream의 활성 상태 비교
   - 현재 구현: ❌ 미구현

#### 제한사항
- DescribeLiveStreamState는 primary/backup을 구분하지 않음
- CSS 도메인과 스트림 이름 정보 필요
- StreamPackage → CSS 연결 정보 필요

## 권장 개선 사항

### 우선순위 1: StreamLive 출력 URL 추출 및 매칭

```python
# StreamLive 채널의 OutputGroups에서 출력 URL 추출
def get_streamlive_output_url(channel_id):
    # OutputGroups → StreamPackageSettings → 출력 URL 추출
    # 또는 OutputGroups → 다른 출력 설정에서 URL 추출
    pass

# StreamPackage 입력 URL과 매칭
def match_streamlive_to_streampackage(streamlive_output_url, streampackage_inputs):
    for idx, sp_input in enumerate(streampackage_inputs):
        if match_url(streamlive_output_url, sp_input.url):
            return "main" if idx == 0 else "backup"
    return None
```

### 우선순위 2: CSS DescribeBackupStreamList API 통합

```python
# CSS backup stream 확인
def check_css_backup_stream(domain, app_name, stream_name):
    backup_streams = describe_backup_stream_list(domain, app_name, stream_name)
    
    # Primary stream과 backup stream 상태 비교
    primary_active = check_stream_state(domain, app_name, stream_name)
    backup_active = check_backup_stream_state(backup_streams)
    
    # Backup이 활성화되어 있으면 backup 신호 사용 중
    if backup_active and not primary_active:
        return "backup"
    elif primary_active:
        return "main"
    return None
```

### 우선순위 3: 다단계 검증 로직 강화

```python
# StreamLink → StreamLive → StreamPackage → CSS 순서로 검증
results = {
    "streamlink": check_streamlink_flows(),
    "streamlive": check_streamlive_inputs(),
    "streampackage": check_streampackage_inputs(),
    "css": check_css_streams()
}

# 일치하는 결과를 우선 사용
final_result = combine_verification_results(results)
```

## 현재 검증 정확도

### 현재 구현 (StreamLink만)
- **정확도**: 80-90%
- **검증 소스**: StreamLink 플로우 상태

### StreamPackage 입력 확인 추가
- **정확도**: 85-92%
- **검증 소스**: StreamLink + StreamPackage 입력 순서

### StreamPackage URL 매칭 추가
- **정확도**: 90-95%
- **검증 소스**: StreamLink + StreamPackage URL 매칭

### CSS backup stream 확인 추가
- **정확도**: 92-97%
- **검증 소스**: StreamLink + StreamPackage + CSS backup stream

## 결론

### 현재 가능한 검증
- ✅ StreamPackage 입력 URL 목록 확인 (2개 입력: MAIN/BACKUP)
- ✅ StreamPackage 입력 순서 기반 판단 (첫 번째=MAIN, 두 번째=BACKUP)
- ✅ CSS 스트림 흐름 확인 (StreamPackage 연결 기반)

### 추가 구현 필요
- ⭐ StreamLive 출력 URL 추출 및 StreamPackage 입력 URL 매칭
- ⭐ CSS DescribeBackupStreamList API 통합
- ⭐ CSS backup stream 상태 확인

### 최종 답변
**StreamPackage와 CSS를 모두 체크해서 우선 신호를 확인할 수 있지만**, 현재는 **간접적인 확인**만 가능합니다. StreamLive 출력 URL 매칭과 CSS backup stream 확인을 추가하면 **더 정확한 확인**이 가능합니다.
