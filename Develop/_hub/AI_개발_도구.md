---
title: AI 개발 도구 허브
tags: [hub, ai, claude, llm, copilot, prompt-engineering, rag, agent, mcp, gemini, cursor]
updated: 2026-07-29
---

# AI 개발 도구 허브

## 이 주제를 언제 찾게 되는가

- Claude Code를 처음 도입하거나, 오케스트레이션·멀티 에이전트로 확장하려 할 때
- LLM 기반 기능을 프로덕션에 붙여야 하는데 RAG·파인튜닝·임베딩 중 어느 방향인지 갈릴 때
- AI 코딩 도구(Claude Code, Cursor, Copilot, Codex, Gemini CLI)를 비교해서 프로젝트에 맞는 걸 고르고 싶을 때
- MCP 서버를 만들거나 Claude Agent SDK로 자체 에이전트를 구축하려 할 때
- 모델 선택(Claude Opus, Gemini, GPT, DeepSeek, Qwen, Grok)이 필요할 때
- AI가 생성한 코드의 보안 취약점이나 할루시네이션을 걱정할 때
- 로컬 LLM(Ollama, GGUF) 셀프호스팅을 검토할 때
- LLM 추론 최적화, KV 캐시, 양자화 같은 인프라 수준 문제를 다룰 때

## 문서 지도

### Claude Code — AI 코딩 에이전트 핵심

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Claude Code](../AI/Claude_Code/Claude_Code.md) | Claude Code 전반 개요 — MCP, 훅, 슬래시 명령어, 권한 모델 | 입문 |
| [Claude Code 실전 팁](../AI/Claude_Code/Claude_Code_Tips.md) | 실무에서 쌓인 생산성 노하우, 모델 선택 경험칙 | 실무 |
| [Claude Code 스킬과 룰 시스템](../AI/Claude_Code/Claude_Code_Skill_Rule.md) | CLAUDE.md 룰과 Skill의 차이, 각 용도와 작성법 | 실무 |
| [Claude Code 메모리 시스템](../AI/Claude_Code/Claude_Code_Memory.md) | 세션 간 컨텍스트 유지를 위한 메모리 계층 구조 | 실무 |
| [Claude Code 플랜모드 실전 활용](../AI/Claude_Code/Claude_Code_Plan_Mode.md) | 대규모 리팩토링·마이그레이션 전 플랜 검증 워크플로 | 실무 |
| [Claude Code Auto Mode](../AI/Claude_Code/Claude_Code_Auto_Mode.md) | 반복 확인 마찰을 줄이는 자동 모드 설정과 한계 | 실무 |
| [Claude Code 개발 루틴](../AI/Claude_Code/Claude_Code_Routine.md) | 하루 일과 속 Claude Code 투입 시점과 주기 설계 | 실무 |
| [Claude Code Agent 시스템](../AI/Claude_Code/Claude_Code_Agent.md) | 세션 내 서브에이전트 위임 메커니즘 | 실무 |
| [Claude Code 오케스트레이션](../AI/Claude_Code/Claude_Code_Orchestration.md) | 외부 SDK로 다수 인스턴스를 조율하는 멀티 에이전트 설계 | 심화 |
| [Claude Code OMC](../AI/Claude_Code/Claude_Code_OMC.md) | 프로세스 N개를 병렬로 돌리는 OMC 운영 방식 | 심화 |
| [Claude Code Worktree](../AI/Claude_Code/Claude_Code_Worktree.md) | git worktree로 브랜치별 격리 개발 환경 구성 | 심화 |
| [Claude Code Worktree 병렬 스크립트](../AI/Claude_Code/Claude_Code_Worktree_Script.md) | --print 모드 활용 병렬 자동화 스크립트 | 심화 |
| [Claude Code 롱잡 운영](../AI/Claude_Code/Claude_Code_Long_Job.md) | 2분 타임아웃·컨텍스트 폭발 없이 장시간 작업 처리 | 심화 |
| [Claude Code 하네스](../AI/Claude_Code/Claude_Code_Harness.md) | 하네스 내부 동작, 권한·훅·샌드박스 디버깅 | 심화 |
| [Claude Code 모델 선택](../AI/Claude_Code/Claude_Code_Model.md) | 에이전틱 환경에서 Opus·Sonnet·Haiku 선택 기준 | 실무 |
| [Claude Code Ultra Review](../AI/Claude_Code/Claude_Code_Ultra.md) | /code-review ultra 멀티에이전트 코드 리뷰 사용법 | 실무 |
| [Claude Code 웹취약점 대응](../AI/Claude_Code/Claude_Code_Web_Vulnerability.md) | AI 생성 코드에서 XSS·SSRF·IDOR가 발생하는 패턴과 차단 | 실무 |
| [Claude Code Fable 5 릴리스](../AI/Claude_Code/Claude_Code_Fable_5.md) | Fable 5 주요 변경사항과 마이그레이션 체크리스트 | 실무 |
| [Claude Code 트러블슈팅](../AI/Claude_Code/Claude_Code_Troubleshooting.md) | 실무에서 자주 겪는 CLI 문제와 해결법 | 실무 |

### Claude API & 모델

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Claude](../AI/Claude/Claude.md) | Claude 모델 패밀리 개요, API 기초, 모델 비교 | 입문 |
| [Claude를 전문가처럼 활용](../AI/Claude/Claude_Expert_Usage.md) | Web·API·Desktop 전반에서 시스템 프롬프트·Projects 세팅 | 실무 |
| [Claude API 고급 기능](../AI/Claude/Claude_API_Advanced.md) | Batch API, Citations, Files API, Prompt Caching 실무 | 실무 |
| [Claude Agent SDK](../AI/Claude/Claude_Agent.md) | 도구 루프·컨텍스트 압축·권한 처리를 SDK로 묶는 방법 | 심화 |
| [Claude Opus 4.7](../AI/Claude/Claude_Opus_4_7.md) | 4.6 대비 긴 컨텍스트 일관성·도구 호출 품질 개선 포인트 | 실무 |
| [Claude Opus 4.8](../AI/Claude/Claude_Opus_4_8.md) | 4.7 대비 추론 깊이·도구 호출 캘리브레이션 개선과 비용 | 실무 |

### LLM 핵심 개념

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [LLM 동작 원리와 프로덕션 통합](../AI/Concepts/LLM.md) | 트랜스포머·추론·파인튜닝·임베딩·평가 전 범위 개요 | 입문 |
| [프롬프트 엔지니어링](../AI/Concepts/Prompt_Engineering.md) | Few-shot, CoT, 코딩 특화 프롬프트 설계 원칙 | 입문 |
| [LLM 에이전트](../AI/Concepts/LLM_Agent.md) | ReAct·도구 루프·계획·메모리 등 에이전트 구성 요소 | 실무 |
| [멀티 에이전트 시스템](../AI/Concepts/Multi_Agent_Systems.md) | 오케스트레이터-워커, A2A 핸드오프, 컨텍스트 격리 패턴 | 심화 |
| [Agent Harness](../AI/Concepts/Agent_Harness.md) | Claude Code 하네스로 보는 에이전트 런타임 구조 | 심화 |
| [Tool Use / Function Calling](../AI/Concepts/Tool_Use.md) | JSON Schema 정의부터 도구 루프 구현까지 | 실무 |
| [Structured Output](../AI/Concepts/Structured_Output.md) | LLM 출력을 DTO·enum에 매핑하는 강제 구조화 기법 | 실무 |
| [LLM Reasoning 패턴과 모델](../AI/Concepts/LLM_Reasoning.md) | CoT·ReAct·Tree-of-Thoughts·o1·Extended Thinking 비교 | 심화 |
| [Effort Mode](../AI/Concepts/Effort_Mode.md) | reasoning effort 다이얼이 생긴 배경과 모델별 설정법 | 실무 |
| [LLM Context Window](../AI/Concepts/LLM_Context_Window.md) | RoPE·YaRN·Long Context·Prompt Caching 동작 원리 | 심화 |
| [LLM 보안 위협과 대응](../AI/Concepts/LLM_Security.md) | Prompt Injection·PII 유출·Jailbreak·Guardrails | 실무 |
| [바이브 코딩 보안 대처법](../AI/Concepts/Vibe_Coding_Security.md) | Slopsquatting·Prompt Injection·SAST 연동으로 위험 줄이기 | 실무 |
| [AI 할루시네이션](../AI/Concepts/AI_Hallucination.md) | 코드 생성에서 할루시네이션이 발생하는 이유와 검증 전략 | 실무 |
| [LLM 평가 방법론](../AI/Concepts/LLM_Evaluation.md) | MMLU·HumanEval·MT-Bench 등 벤치마크의 함정과 실무 평가 | 실무 |
| [LLM 파인튜닝 실무](../AI/Concepts/LLM_Fine_Tuning.md) | LoRA·QLoRA·PEFT — 파인튜닝을 시작하기 전 판단 기준 | 심화 |
| [LLM 추론 최적화 심화](../AI/Concepts/LLM_Inference_Optimization.md) | Quantization·KV Cache·PagedAttention·Speculative Decoding | 심화 |
| [LLM 스케일링 법칙](../AI/Concepts/LLM_Scaling_Laws.md) | Chinchilla·Compute-Optimal·창발적 능력과 파라미터 배분 | 심화 |
| [LLM 토크나이저](../AI/Concepts/LLM_Tokenizer.md) | BPE 내부 구현과 토크나이저 병리 현상 | 심화 |
| [LLM 사전학습 파이프라인](../AI/Concepts/LLM_Pretraining.md) | 데이터 준비·학습 루프·학습 불안정 원인 (nanoGPT 기반) | 심화 |

### RAG 및 검색 증강

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [RAG 파이프라인](../AI/Concepts/RAG_Pipeline.md) | 문서 파싱·청킹·검색·생성 전 과정 설계와 비용 | 실무 |
| [Functional RAG](../AI/Concepts/Functional_RAG.md) | 함수형 파이프라인으로 RAG 복잡도 관리 (LCEL 활용) | 실무 |
| [RAG for Code](../AI/Concepts/RAG_for_Code.md) | 코드베이스를 대상으로 한 RAG 아키텍처 | 심화 |
| [텍스트 임베딩 실무](../AI/Concepts/Embeddings.md) | OpenAI·Cohere·BGE·E5 비교, 코사인 유사도 검색 설계 | 실무 |
| [벡터 DB 실무 비교](../AI/Concepts/Vector_Database.md) | pgvector·Qdrant·Pinecone·Milvus 선택 기준과 운영 | 실무 |
| [온톨로지](../AI/Concepts/Ontology.md) | 지식 그래프·RDF·OWL·SPARQL — RAG 품질 향상을 위한 구조화 지식 | 심화 |

### MCP (Model Context Protocol)

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [MCP 핵심 개념](../AI/MCP/MCP.md) | MCP 프로토콜 구조, 서버/클라이언트 역할, 도구 등록 | 입문 |
| [MCP 전송 방식](../AI/MCP/SSE_and_Stdio.md) | stdio vs SSE vs Streamable HTTP 전송 선택 기준 | 실무 |

### AI 코딩 도구 비교

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Cursor](../AI/Cursor/Cursor.md) | AI 네이티브 IDE Cursor의 핵심 기능과 Composer 활용 | 입문 |
| [Cursor Rules](../AI/Cursor/Cursor_Rules.md) | 프로젝트별 AI 동작 규칙 설정 (.cursorrules) | 실무 |
| [Cursor Context 관리](../AI/Cursor/Cursor_Context_Management.md) | @태그·인덱싱·CursorIgnore·토큰 관리 | 실무 |
| [GitHub Copilot](../AI/GitHub_Copilot/GitHub_Copilot.md) | Copilot 핵심 기능, Agent Mode, IDE별 차이 | 입문 |
| [OpenAI Codex](../AI/Codex/Codex.md) | Codex CLI 사용법, 에이전틱 코딩 특성 | 입문 |
| [Gemini Code Assist & CLI](../AI/Gemini/Gemini.md) | Gemini Code Assist 플러그인과 CLI — 1M 토큰 활용 | 실무 |
| [CodeSight --wiki](../AI/CodeSight/Code_Sight_Wiki.md) | 코드베이스 문서화 자동화 CLI 도구 | 실무 |
| [Clawsweeper](../AI/Clawsweeper/Clawsweeper.md) | 데드코드 탐지·정리 AI 정적 분석 CLI 도구 | 실무 |
| [UltraReview](../AI/Concepts/Ultra_Review.md) | CI/CD 연동 AI 심층 코드 리뷰 도구 | 실무 |

### Gemini / Google AI

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [Gemini API 실무](../AI/Gemini/Gemini_API.md) | SDK 인증·기본 호출·멀티모달 입력 기초 | 입문 |
| [Gemini API 심화](../AI/Gemini/Gemini_API_Advanced.md) | Function Calling·Streaming·Safety·Context Caching | 심화 |
| [Google AI Studio](../AI/Gemini/Google_AI_Studio.md) | 프로토타이핑 웹 도구 활용과 API 키 발급 | 입문 |
| [Gemini 트러블슈팅](../AI/Gemini/Gemini_Troubleshooting.md) | 429 에러·인증 만료·멀티모달 파일 제한 대응 | 실무 |

### 기타 LLM 모델

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [GPT-5.5](../AI/GPT/GPT_5_5.md) | GPT-5.5 모델 특성, API 사용, Claude와 비교 | 실무 |
| [DeepSeek](../AI/DeepSeek/Deep_Seek.md) | DeepSeek MoE 모델 패밀리, 오픈소스 셀프호스팅 | 실무 |
| [Qwen](../AI/Qwen/Qwen.md) | Alibaba Qwen 패밀리, DashScope API, 추론 모델 활용 | 실무 |
| [Grok](../AI/Grok/Grok.md) | xAI Grok, 코딩 보조, API 접근 방법 | 실무 |
| [Ollama](../AI/Ollama/Ollama.md) | 로컬 LLM 서빙 — GGUF, 모델 관리, vLLM 비교 | 실무 |
| [Unsloth Qwen3 GGUF 로컬 구동](../AI/Concepts/Unsloth_Qwen3_GGUF.md) | 27B GGUF 모델 로컬 구동과 llama.cpp·Ollama 연동 | 실무 |

### AI 업무 활용 및 워크플로우

| 문서 | 이 문서가 답하는 것 | 깊이 |
|---|---|---|
| [팔란티어가 AI로 일하는 방식](../AI/Concepts/Palantir_AI_Workflow.md) | Foundry·AIP·온톨로지 기반 엔터프라이즈 AI 운영 | 심화 |
| [Karpathy LLM + Obsidian 워크플로우](../AI/Concepts/Karpathy_LLM_Obsidian.md) | vault를 LLM에 먹여서 지식 관리를 확장하는 방법 | 실무 |
| [Obsidian 실무 사용법](../AI/Concepts/Obsidian.md) | vault 구조·플러그인·동기화, AI와 함께 쓸 때 주의사항 | 실무 |
| [GBrain](../AI/GBrain/G_Brain.md) | 국내 엔터프라이즈 AI 지식 관리 도구 GBrain | 입문 |

## 읽는 순서

### Claude Code를 처음 도입하는 경우

1. **Claude Code** — 전체 기능 지형을 먼저 파악한다
2. **Claude Code 스킬과 룰 시스템** — CLAUDE.md와 Skill을 올바르게 구분해서 세팅한다
3. **Claude Code 실전 팁** — 빠르게 생산성을 높이는 경험칙을 흡수한다
4. **Claude Code 플랜모드 실전 활용** — 대형 작업 전 플랜 검증 습관을 들인다
5. **Claude Code 개발 루틴** — 일상 업무 사이클에 통합하는 방법을 잡는다

### LLM 기반 기능을 서비스에 붙이는 경우

1. **LLM 동작 원리와 프로덕션 통합** — LLM 전반 개념을 먼저 잡는다
2. **프롬프트 엔지니어링** — 기능 품질의 절반은 프롬프트 설계에서 결정된다
3. **Tool Use / Function Calling** — 외부 시스템 연동을 위한 도구 호출 구조를 익힌다
4. **Structured Output** — 백엔드 파이프라인이 받을 수 있는 형태로 출력을 강제한다
5. **RAG 파이프라인 → 텍스트 임베딩 실무 → 벡터 DB 실무 비교** — 문서 검색 기능 구축의 전 과정
6. **LLM 보안 위협과 대응 → 바이브 코딩 보안 대처법** — 보안 위협을 일찍 차단한다

### 멀티 에이전트 / 오케스트레이션으로 확장하는 경우

1. **LLM 에이전트** — 에이전트 구성 요소 전체를 파악한다
2. **Claude Code Agent 시스템** — 세션 내 위임 메커니즘을 먼저 이해한다
3. **Claude Code 오케스트레이션** — 프로세스 레벨 확장으로 넘어간다
4. **멀티 에이전트 시스템** — A2A 핸드오프·컨텍스트 격리 패턴을 설계한다
5. **Agent Harness** — 런타임 구조를 깊이 이해해서 하네스를 직접 만들거나 디버깅한다
6. **MCP 핵심 개념 → MCP 전송 방식** — MCP로 도구를 외부 서버로 분리한다

### LLM 인프라를 직접 운영하는 경우

1. **Ollama** — 로컬 서빙 환경을 빠르게 구성한다
2. **LLM 추론 최적화 심화** — Quantization·KV Cache·PagedAttention으로 비용·속도를 잡는다
3. **LLM 파인튜닝 실무** — 파인튜닝이 정말 필요한 상황인지 판단하고 실행한다
4. **LLM 스케일링 법칙 → LLM 사전학습 파이프라인** — 학습 예산 배분과 데이터 파이프라인 이해

## 아직 없는 것

- Claude Code SDK를 이용한 자체 하네스 구현 실전 튜토리얼
- LangChain / LlamaIndex vs 순수 SDK 선택 가이드
- RAG 품질 평가 지표(RAGAS, TRULENS) 실무 적용
- Prompt Caching 비용 최적화 상세 가이드 (Anthropic·Gemini 비교)
- AI 코드 리뷰 CI/CD 파이프라인 구축 가이드 (Semgrep + LLM 연동)
- A/B 테스트로 프롬프트 버전을 관리하는 실무 패턴
- 멀티모달 (이미지·PDF·음성) 입력 파이프라인 설계
- OpenAI Assistants API vs Claude Agent SDK 상세 비교
- 온프레미스 GPU 클러스터에서 vLLM 운영 실전 가이드
- MCP 서버 직접 구현 — TypeScript·Python SDK 예시
