# 00 — Bootstrap (spec-kit + Codex)

## 0) 템플릿 주입
터미널:
- `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`
- `specify init . --ai codex --script sh --force`

## 1) Codex 세션 시작(레포 루트)
Codex에게:
- "이 레포는 spec-kit SDD를 따른다. /speckit.constitution부터 시작하자.
   AGENTS.md와 docs/PRD.md를 참고해서 헌법을 만들어줘."

## 2) 산출물 체크
- `.specify/memory/constitution.md` 생성/업데이트 확인
- `specs/001-adaptive-traffic-sim/` 산출물 생성 확인
