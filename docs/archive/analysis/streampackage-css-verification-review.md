# StreamPackage & CSS 검증 가능 여부 검토

## 현재 구현 상태

### ✅ 구현 완료
1. **StreamPackage 연결 확인**: StreamLive 채널에서 StreamPackage ID 추출
2. **StreamPackage 입력 정보**: StreamPackage 채널의 입력 URL 목록 확인
3. **CSS 연결 확인**: StreamPackage 연결 여부 확인

### ⚠️ 개선 필요
1. **StreamPackage 입력 활성화 상태**: 현재는 입력 URL만 확인, 실제 활성 입력 판단 미흡
2. **StreamLive 출력 URL 매칭**: StreamLive 출력 URL과 StreamPackage 입력 URL 매칭 로직 부족
3. **CSS backup stream 확인**: CSS의 DescribeBackupStreamList API 미사용

## 검증 가능 여부 분석

### 1. StreamPackage를 통한 main/backup 확인

#### 가능한 방법
- **StreamPackage 입력 URL 순서**: 첫 번째 입력 = main, 두 번째 입력 = backup
- **StreamLive 출력 URL 매칭**: StreamLive 출력 URL과 StreamPackage 입력 URL을 매칭하여 어떤 입력이 활성인지 확인

#### 제한사항
- StreamPackage API는 직접적으로 "어떤 입력이 활성화되어 있는지"를 알려주지 않음
- 입력 URL이 모두 설정되어 있어도 실제로 어떤 입력에서 데이터가 들어오는지는 확인 어려움

#### 개선 방안
```python
# StreamLive 출력 URL 추출
streamlive_output_url = get_streamlive_output_url(channel_id)

# StreamPackage 입력 URL과 매칭
for idx, sp_input in enumerate(streampackage_inputs):
    if match_url(streamlive_output_url, sp_input.url):
        active_input = "main" if idx == 0 else "backup"
        break
```

### 2. CSS를 통한 main/backup 확인

#### 가능한 방법
- **DescribeBackupStreamList API**: CSS의 backup stream 목록 확인
- **스트림 상태 확인**: primary stream과 backup stream의 활성 상태 비교

#### 제한사항
- DescribeLiveStreamState는 primary/backup을 구분하지 않음
- CSS 도메인과 스트림 이름 정보 필요

#### 개선 방안
```python
# CSS backup stream 확인
backup_streams = describe_backup_stream_list(domain, app_name, stream_name)

# Primary stream과 backup stream 상태 비교
primary_active = check_stream_state(domain, app_name, stream_name)
backup_active = check_backup_stream_state(backup_streams)

# Backup이 활성화되어 있으면 backup 신호 사용 중
if backup_active and not primary_active:
    active_input = "backup"
```

## 권장 개선 사항

### 1. StreamLive 출력 URL 추출 및 매칭
- StreamLive 채널의 OutputGroups에서 출력 URL 추출
- StreamPackage 입력 URL과 매칭하여 활성 입력 확인

### 2. CSS DescribeBackupStreamList API 활용
- CSS backup stream 목록 확인
- Primary/backup stream 상태 비교

### 3. 다단계 검증 로직 강화
- StreamLink → StreamLive → StreamPackage → CSS 순서로 검증
- 각 단계에서 일치하는 결과를 우선 사용
- 불일치 시 경고 표시

## 구현 우선순위

### 높음 (즉시 구현 가능)
1. ✅ StreamPackage 입력 URL과 StreamLive 출력 URL 매칭
2. ✅ StreamPackage 입력 순서 기반 main/backup 판단

### 중간 (추가 API 필요)
3. ⭐ CSS DescribeBackupStreamList API 통합
4. ⭐ CSS 도메인 및 스트림 정보 추출

### 낮음 (선택적)
5. CSS origin 서버 정보 확인
6. 실시간 트래픽 모니터링

## 결론

### 현재 가능한 검증
- ✅ StreamPackage 연결 확인
- ✅ StreamPackage 입력 URL 목록 확인
- ⚠️ StreamPackage 활성 입력 간접 확인 (URL 매칭 필요)

### 추가 구현 필요
- ⭐ StreamLive 출력 URL 추출 및 매칭
- ⭐ CSS DescribeBackupStreamList API 통합
- ⭐ CSS backup stream 상태 확인

### 최종 정확도 예상
- 현재 (StreamLink만): 80-90%
- StreamPackage URL 매칭 추가: 85-92%
- CSS backup stream 확인 추가: 90-95%
