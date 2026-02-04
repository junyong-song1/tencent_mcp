# Commit Skill

Git 커밋 및 푸시를 자동화합니다.

## Usage

```
/commit [message]
```

## Arguments

- `$ARGUMENTS` - 커밋 메시지 (선택사항, 없으면 변경 내용 기반으로 자동 생성)

## Instructions

1. **변경 사항 확인**
   ```bash
   git status
   git diff --stat
   ```

2. **커밋 메시지 생성**
   - 인자로 메시지가 주어지면 해당 메시지 사용
   - 없으면 변경 내용을 분석하여 자동 생성
   - 형식: `type: 한글 설명`
   - type: feat, fix, refactor, docs, test, chore

3. **커밋 실행**
   ```bash
   git add <변경된 파일들>
   git commit -m "$(cat <<'EOF'
   커밋 메시지

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
   EOF
   )"
   ```

4. **푸시 확인**
   - 사용자에게 푸시 여부 확인
   - 승인 시: `git push origin main`

## 주의사항

- `.env`, `credentials` 등 민감한 파일은 커밋하지 않음
- `.claude/settings.local.json`은 제외
- 변경 파일이 없으면 커밋하지 않음
