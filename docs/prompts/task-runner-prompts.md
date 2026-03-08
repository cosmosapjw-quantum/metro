# Task Runner Prompts

## Execute Task (Korean)

```text
tasks.md의 [T-XXX]를 구현해줘. 먼저 관련 문서(계획/데이터모델)에서 근거 위치를 인용(파일 경로+섹션 제목)하고,
그 다음 최소 diff로 구현해. 마지막에 pytest와 데모 스모크를 돌린 로그 요약까지 줘.
리뷰: 방금 diff를 /review로 검토해줘. (1) 불변량 위반 가능성 (2) 성능 병목 (3) JAX jit 가능성 관점으로 우선순위 큐로 정리.
```

## Execute Task (English)

```text
Implement [T-XXX] from tasks.md. First cite supporting locations from plan/data-model (file path + section title),
then implement with minimal diff. Finally provide a summary of pytest + demo smoke logs.
Review: run /review on the diff and prioritize findings by (1) invariant risk, (2) performance bottlenecks, (3) JAX jit opportunities.
```
