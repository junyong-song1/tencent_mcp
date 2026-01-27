# Failover 체크 로직 업데이트: Input Source Redundancy 지원

## 문제점

**기존 로직의 문제:**
- Channel-level Failover 방식만 고려
- Input Source Redundancy 방식에서 어떤 소스 주소(InputAddress01 vs InputAddress02)가 활성인지 확인하지 못함
- 하나의 입력에 여러 소스 주소가 있는 경우를 처리하지 못함

## 해결 방법

### 1. Input Source Redundancy 감지

**방식:**
- StreamLink 플로우의 출력 URL에서 소스 주소 확인
- `ap-seoul-1` → main (InputAddress01)
- `ap-seoul-2` → backup (InputAddress02)

**코드 변경:**
```python
# StreamLink 플로우 출력 URL과 입력 엔드포인트 매칭
for endpoint in channel_info.get("input_endpoints", []):
    for flow_url in flow_output_urls:
        # ap-seoul-1 vs ap-seoul-2로 main/backup 판단
        if "ap-seoul-1" in endpoint.lower() or "ap-seoul-1" in flow_url.lower():
            matched_source = "main"
            active_source_address = endpoint
        elif "ap-seoul-2" in endpoint.lower() or "ap-seoul-2" in flow_url.lower():
            matched_source = "backup"
            active_source_address = endpoint
```

### 2. 소스 주소 타입 저장

**변경 사항:**
- `flow_type_by_input`: 입력 ID → main/backup 매핑
- `active_source_address`: 현재 활성 소스 주소 저장
- `is_input_source_redundancy`: Input Source Redundancy 모드인지 표시

### 3. 결과에 추가 정보 포함

**추가된 필드:**
```python
result = {
    ...
    "is_input_source_redundancy": is_input_source_redundancy,
    "active_source_address": active_source_address,
    ...
}
```

## 동작 방식

### Channel-level Failover (기존 방식)

```
채널
  ├─ Input 1 (Primary) ← FailOverSettings.SecondaryInputId = Input 2
  └─ Input 2 (Secondary)

로직:
1. StreamLink 플로우 이름에서 _m, _b 확인
2. 플로우 출력 URL과 입력 엔드포인트 매칭
3. 입력 ID로 main/backup 판단
```

### Input Source Redundancy (새로 지원)

```
하나의 입력 (3tier_3pro_tv)
  ├─ InputAddress01 (ap-seoul-1) ← main
  └─ InputAddress02 (ap-seoul-2) ← backup

로직:
1. StreamLink 플로우 이름에서 _m, _b 확인
2. 플로우 출력 URL에서 ap-seoul-1 vs ap-seoul-2 확인
3. 소스 주소로 main/backup 판단
4. active_source_address에 현재 활성 소스 주소 저장
```

## 검증 소스

**우선순위:**
1. **StreamLink 플로우 상태** (가장 신뢰)
   - 플로우 이름: `_m` = main, `_b` = backup
   - 출력 URL: `ap-seoul-1` = main, `ap-seoul-2` = backup
2. StreamPackage 결과 (fallback)
3. FailOverSettings (Channel-level Failover만)
4. 입력 이름 패턴

**Input Source Redundancy 감지:**
- `active_source_address`가 설정되면 Input Source Redundancy 모드로 판단
- `is_input_source_redundancy = True`로 표시
- 검증 소스에 "InputSourceRedundancy" 추가

## 테스트 필요 사항

1. **Input Source Redundancy 채널 테스트**
   - 하나의 입력에 두 개의 소스 주소가 있는 채널
   - StreamLink main 플로우가 ap-seoul-1로 연결된 경우
   - StreamLink backup 플로우가 ap-seoul-2로 연결된 경우
   - 현재 활성 소스 주소가 올바르게 감지되는지 확인

2. **Channel-level Failover 채널 테스트**
   - 두 개의 별도 입력이 있는 채널
   - FailOverSettings.SecondaryInputId가 설정된 경우
   - 기존 로직이 여전히 작동하는지 확인

## 결론

**개선 사항:**
- ✅ Input Source Redundancy 방식 지원
- ✅ 소스 주소 레벨에서 main/backup 판단
- ✅ 현재 활성 소스 주소 추적
- ✅ Input Source Redundancy 모드 감지

**다음 단계:**
- 실제 채널에서 테스트하여 정확성 확인
- 필요시 추가 개선
