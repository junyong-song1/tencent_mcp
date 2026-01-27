# 검증 우선순위 수정 문서

## 문제 발견

cj_onstyle 채널 확인 시:
- **StreamPackage/CSS 검증 결과**: MAIN
- **실제 StreamLink 플로우 상태**: BACKUP (cj_onstyle_b 실행 중)

## 원인 분석

### 잘못된 우선순위

**기존 구현:**
```python
# Priority 1: StreamPackage result (most reliable)
if streampackage_result and streampackage_result.get("active_input"):
    active_input_type = streampackage_result.get("active_input")
    verification_sources.append("StreamPackage")

# Priority 2: StreamLink flow type
elif active_input_id in flow_type_by_input:
    active_input_type = flow_type_by_input[active_input_id]
    verification_sources.append("StreamLink")
```

**문제점:**
- StreamPackage 입력 순서는 **추정**일 뿐, 실제 활성 입력을 보장하지 않음
- StreamLink 플로우 상태가 **실시간으로 가장 정확한 지표**임에도 우선순위가 낮음

### StreamPackage 입력 순서의 한계

1. **입력 URL이 모두 설정되어 있어도** 실제로 어떤 입력에서 데이터가 들어오는지는 확인 불가
2. **첫 번째 입력 = MAIN**은 관례일 뿐, 실제 활성 입력과 다를 수 있음
3. **Failover 발생 시** backup 입력이 활성화되어도 순서는 변하지 않음

### StreamLink 플로우 상태의 정확성

1. **실시간 상태 확인**: `running` = 실제 활성, `idle` = 비활성
2. **명확한 구분**: 플로우 이름(`_m`, `_b`)으로 main/backup 명확히 구분
3. **직접적인 연결**: StreamLink → StreamLive 직접 연결 확인

## 수정 내용

### 새로운 우선순위

```python
# Priority 1: StreamLink flow type (MOST RELIABLE - real-time status)
if active_input_id in flow_type_by_input:
    active_input_type = flow_type_by_input[active_input_id]
    verification_sources.append("StreamLink")

# Priority 2: StreamPackage result (fallback - input order only)
elif streampackage_result and streampackage_result.get("active_input"):
    active_input_type = streampackage_result.get("active_input")
    verification_sources.append("StreamPackage")
```

### 검증 우선순위 정리

1. **1순위: StreamLink 플로우 상태** ✅
   - 실시간 상태 확인
   - 플로우 이름으로 main/backup 구분
   - 가장 신뢰할 수 있는 지표

2. **2순위: StreamLive 입력 통계**
   - NetworkValid=True, NetworkIn > 0인 입력
   - 실제 트래픽 확인

3. **3순위: StreamPackage 입력 순서** ⚠️
   - 첫 번째 입력 = MAIN (추정)
   - 보조 확인용으로만 사용

4. **4순위: FailOverSettings**
   - Primary/Secondary 입력 관계

5. **5순위: 입력 이름 패턴**
   - 이름에서 main/backup 키워드 확인

## 검증 결과

### cj_onstyle 채널

**StreamLink 플로우 상태:**
- `cj_onstyle_m` (MAIN): `idle` (비활성)
- `cj_onstyle_b` (BACKUP): `running` (활성) ✅

**최종 판단:**
- **BACKUP 신호로 서비스 중** (StreamLink 플로우 상태 기반)
- StreamPackage 입력 순서는 보조 확인용

## 결론

**가장 정확한 검증 방법:**
1. StreamLink 플로우 상태 확인 (실시간, 명확)
2. StreamLive 입력 통계 확인 (실제 트래픽)
3. StreamPackage 입력 순서 (보조 확인)

**수정 후:**
- StreamLink 플로우 상태를 최우선으로 확인
- StreamPackage 입력 순서는 StreamLink 정보가 없을 때만 사용
- 더 정확한 신호 감지 가능
