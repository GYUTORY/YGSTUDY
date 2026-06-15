---
title: Gemini Code Assist & CLI 사용법
tags: [ai, gemini, google, code-assist, gemini-cli]
updated: 2026-06-15
---

# Gemini Code Assist & CLI

Google의 AI 코딩 도구는 두 갈래다. 하나는 IDE에 붙는 Gemini Code Assist 플러그인, 다른 하나는 터미널에서 도는 Gemini CLI다. 둘 다 개인 Google 계정으로 무료로 쓸 수 있고 컨텍스트 윈도우가 1M 토큰까지 잡힌다. 여기서는 스펙 나열보다 실제로 쓰면서 걸렸던 부분과 다른 도구와의 체감 차이를 정리한다.

## Gemini CLI

![Gemini CLI 실행 화면 스크린샷](../../assets/images/auto/gemini/1bdbd627.png)


설치는 npm 글로벌이나 npx 둘 중 하나로 한다.

```bash
# 설치 없이 바로
npx @google/gemini-cli

# 글로벌 설치
npm install -g @google/gemini-cli
gemini
```

첫 실행에서 브라우저가 열리고 Google 계정 OAuth로 로그인하면 끝난다. API 키 발급 과정이 없어서 진입 장벽은 낮다. 다만 회사 계정(Workspace)으로 로그인하면 조직 정책에 따라 막히는 경우가 있어서, 막히면 개인 Gmail 계정으로 바꿔 로그인하는 게 빠르다.

### GEMINI.md — 모델이 따르는 지침과 무시하는 지침

`GEMINI.md`는 Claude Code의 `CLAUDE.md`, Codex의 `AGENTS.md`와 같은 역할을 한다. 프로젝트 루트에 두면 매 세션 시작 때 시스템 컨텍스트로 주입된다. 계층 구조를 지원해서 `~/.gemini/GEMINI.md`(전역), 프로젝트 루트, 하위 디렉토리 순으로 합쳐진다.

```markdown
# 프로젝트 규칙

## 기술 스택
- Node.js 20 + TypeScript
- Express, Prisma, PostgreSQL

## 작업 규칙
- 새 파일은 src/ 아래에만 만든다
- 커밋은 내가 직접 한다. git commit 실행하지 마라
- 테스트는 vitest로 작성한다
```

써보면 어떤 지침은 잘 따르고 어떤 건 무시한다. 기술 스택이나 디렉토리 위치 같은 사실 정보는 비교적 잘 반영한다. 반면 "절대 ~하지 마라" 같은 부정 지침은 세션이 길어지면 잊는다. 특히 `git commit 하지 마라`를 적어둬도 작업 끝나면 자기가 커밋까지 해버리는 경우가 있다. 그래서 git 관련 자동 실행을 막으려면 GEMINI.md 문구에만 기대지 말고 `--yolo` 같은 자동 승인 플래그를 안 쓰는 쪽이 안전하다.

규칙을 길게 쓸수록 뒷부분일수록 반영률이 떨어진다. 20줄 넘어가면 핵심 규칙을 위쪽에 몰아두는 게 낫다. 코딩 스타일 같은 건 GEMINI.md에 적는 것보다 ESLint/Prettier 설정으로 강제하고 "lint 통과시켜라"만 적는 편이 결과가 일정하다.

### 비대화형(headless) 모드

`-p` 플래그로 프롬프트를 넘기면 대화형 셸을 띄우지 않고 한 번 실행하고 끝난다. 스크립트나 CI에서 쓸 때 이게 핵심이다.

```bash
# 단발 실행
gemini -p "src/api 디렉토리의 라우트 핸들러 목록을 마크다운 표로 정리해줘"

# 파이프로 입력 받기
git diff --staged | gemini -p "이 diff에 대한 커밋 메시지를 한 줄로 작성해줘"

# 모델 지정 + 자동 승인 (파일 수정까지 자동)
gemini -m gemini-3-flash --yolo -p "package.json의 deprecated 의존성을 최신으로 올려줘"
```

주의할 점이 두 가지 있다. 첫째, headless에서 파일을 수정하는 작업은 `--yolo`가 없으면 승인 프롬프트에서 멈춰버린다. 비대화형인데 입력을 기다리느라 스크립트가 행(hang)에 걸린다. 둘째, `-p`의 출력에는 모델의 사고 과정이나 도구 호출 로그가 섞여 나올 때가 있어서, 커밋 메시지 같은 깔끔한 결과만 뽑으려면 출력 뒷부분만 파싱하거나 프롬프트에 "설명 없이 결과만 출력"을 명시해야 한다.

### MCP 서버 연결

MCP 서버는 `~/.gemini/settings.json` 또는 프로젝트의 `.gemini/settings.json`에 등록한다.

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "ghp_xxx" }
    }
  }
}
```

연결이 실패하는 패턴이 몇 가지 정해져 있다. stdio 방식 서버는 `command`가 PATH에 없으면 조용히 죽는다. CLI 안에서 `/mcp`를 치면 서버별 연결 상태와 등록된 도구 목록이 나오는데, 여기서 서버가 안 보이거나 도구 0개로 잡히면 대부분 실행 경로 문제다. `npx`로 띄우는 서버는 첫 실행 때 패키지를 받느라 시간이 걸려서 타임아웃으로 실패하기도 한다. 이럴 땐 해당 패키지를 미리 한 번 `npx`로 직접 실행해 캐시해두고 다시 CLI를 띄우면 붙는다.

`env`에 넣은 토큰이 서버로 전달이 안 되는 경우도 있다. 셸 환경변수와 settings.json의 `env`가 충돌하면 어느 쪽이 이기는지 헷갈리는데, 확실하게 하려면 settings.json에 명시적으로 박아두는 게 낫다. 토큰을 셸 환경변수로만 export 해두면 headless 실행 환경에서 누락되기 쉽다.

### 무료 티어 한도와 초과 시 동작

개인 Google 계정 로그인으로 쓰면 분당 60 요청(RPM), 일 1,000 요청(RPD) 한도가 걸린다. CLI에서 한 번 질문해도 모델이 도구를 여러 번 호출하면서 내부적으로 여러 요청을 쓰기 때문에, 큰 작업 하나가 요청 수십 개를 잡아먹는다. 체감상 코드베이스를 훑으며 리팩토링 시키는 작업 몇 번 돌리면 RPD가 생각보다 빨리 닳는다.

한도를 넘기면 429가 떨어진다. CLI는 자동으로 잠깐 기다렸다 재시도하지만, 일일 한도(RPD)를 넘기면 재시도해도 소용없고 다음 날(태평양 시간 자정 리셋)까지 막힌다. 분당 한도(RPM)는 잠시 쉬면 풀린다. 무료 한도로 부족하면 API 키를 발급받아 유료 티어로 붙이거나 Vertex AI 쪽으로 인증을 바꿔야 한다. 무료/유료 한도 차이와 429 대응은 [Gemini 트러블슈팅](Gemini_Troubleshooting.md)에 API 기준으로 더 정리해뒀다.

### 1M 컨텍스트를 실제로 채웠을 때

1M 토큰 컨텍스트는 큰 코드베이스를 한 번에 물린다는 점에서 장점으로 광고되지만, 실제로 절반 이상 채우면 응답이 눈에 띄게 나빠진다. 세션 초반에 준 지침을 잊고, 앞에서 수정한 파일을 다시 원래대로 되돌리거나, 이미 한 작업을 또 하려 든다. 길이가 길수록 중간에 있던 정보를 놓치는 현상(lost in the middle)이 그대로 나타난다.

응답 지연도 같이 커진다. 컨텍스트가 차면 한 턴 응답에 수십 초씩 걸린다. 그래서 1M을 다 쓴다는 생각보다, 작업이 한 덩어리 끝나면 세션을 새로 시작하거나 컨텍스트를 정리하는 쪽이 결과가 안정적이다. 관련 없는 큰 파일을 통째로 읽히기보다 필요한 파일만 짚어주는 게 토큰도 아끼고 정확도도 높다.

## Gemini Code Assist (IDE)

VS Code, JetBrains, Android Studio에 플러그인으로 붙는다. 인라인 자동완성, IDE 안 채팅, 파일을 직접 수정하는 Agent Mode를 제공한다. 개인 플랜은 무료고 신용카드도 안 받는다.

### 자동완성과 Agent Mode가 동작 안 하는 케이스

깔았는데 자동완성이 안 뜨는 경우가 꽤 흔하다. 원인이 몇 가지로 갈린다.

- 로그인은 됐는데 라이선스가 안 붙은 상태. 상태 바의 Gemini 아이콘이 회색이거나 로그인 재요청이 뜬다. 로그아웃 후 다시 로그인하면 풀리는 경우가 많다.
- 회사 네트워크/프록시 환경에서 인증 토큰 갱신이 막혀서 일정 시간 뒤 조용히 죽는다. 어제까진 됐는데 오늘 안 되면 이쪽을 의심한다.
- 특정 파일 타입이나 거대한 파일에서는 자동완성 제안이 안 뜬다. 파일이 수천 줄이면 제안 생성을 포기한다.
- Agent Mode는 VS Code에서 아직 프리뷰라 안정성이 떨어진다. 파일 수정 중간에 멈추거나 변경 diff를 제대로 못 그리는 경우가 있다. JetBrains 쪽이 좀 더 안정적이다.

증상별 원인 추적과 로그 확인 방법은 [Gemini 트러블슈팅](Gemini_Troubleshooting.md)에 정리돼 있으니 같이 보면 된다.

## Gemini CLI vs Claude Code vs Codex — 써보고 느낀 차이

세 도구 다 터미널 에이전트라는 점은 같지만 결이 다르다. 스펙표로는 안 드러나는 부분 위주로 정리한다.

비용 구조가 가장 큰 차이다. Gemini CLI는 개인 계정이면 무료 한도 안에서 돈을 안 쓴다. 가볍게 이것저것 시켜보기에는 부담이 없다. Claude Code와 Codex는 구독이나 API 사용량으로 돈이 나가는 대신 무료 한도 같은 벽이 없어서, 큰 작업을 끊김 없이 돌릴 때는 오히려 편하다. 무료라는 이유로 Gemini를 메인으로 쓰다 보면 한참 작업하던 중에 일일 한도에 걸려 멈추는 일이 생긴다.

작업 정확도와 끈기는 체감상 Claude Code 쪽이 앞선다. 여러 파일을 고치는 복잡한 작업에서 Claude Code는 계획을 세우고 끝까지 밀어붙이는 편인데, Gemini CLI는 중간에 엉뚱한 파일을 건드리거나 같은 수정을 반복하는 경우가 더 잦다. 다만 코드베이스 전체를 훑어서 "이 패턴이 어디에 쓰이는지" 같은 탐색성 질문은 1M 컨텍스트 덕에 Gemini가 한 번에 답하기도 한다.

Codex는 OpenAI 모델을 쓰고 샌드박스 실행에 신경을 많이 쓴 느낌이다. 코드 생성 품질은 준수한데 도구 호출 방식이 셋 중 가장 보수적이라 승인 프롬프트가 자주 뜬다.

설정 파일은 셋 다 같은 개념이다. Gemini는 `GEMINI.md`, Claude Code는 `CLAUDE.md`, Codex는 `AGENTS.md`. 내용 문법도 거의 호환돼서 한 프로젝트에서 세 도구를 같이 쓰면 파일만 복사해 이름 바꿔 두기도 한다.

비용 없이 가볍게 쓰거나 큰 코드베이스를 탐색할 때는 Gemini CLI, 복잡한 다단계 작업을 끝까지 맡길 때는 Claude Code, 샌드박스 격리가 중요하면 Codex 쪽이 맞는다.

## 주의사항과 함정

- 무료 한도(RPD)는 생각보다 빨리 소진된다. 큰 작업을 무료 계정으로 돌리다 중간에 막히면 작업 컨텍스트가 날아간다. 중요한 작업은 한도를 미리 염두에 두거나 유료로 붙여 쓴다.
- `--yolo` 자동 승인은 편하지만 파일 삭제나 git 명령까지 묻지 않고 실행한다. 모르는 코드베이스에서는 켜지 않는다.
- GEMINI.md의 부정 지침("~하지 마라")은 세션이 길어지면 무시되기 쉽다. 실행 자체를 막아야 하는 건 플래그나 권한으로 통제한다.
- 컨텍스트를 1M까지 채우면 응답 품질과 속도가 같이 떨어진다. 작업 단위로 세션을 끊는 게 낫다.
- MCP 서버가 `/mcp`에서 안 보이면 대부분 실행 경로나 첫 실행 지연 문제다. 패키지를 미리 캐시하고 토큰은 settings.json에 명시한다.
- IDE 자동완성이 멈추면 십중팔구 인증 토큰 갱신 실패다. 재로그인부터 시도한다.

## 참고

- [Gemini Code Assist 공식 사이트](https://codeassist.google)
- [Gemini Code Assist 문서](https://developers.google.com/gemini-code-assist/docs/overview)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI 문서](https://developers.google.com/gemini-code-assist/docs/gemini-cli)
- [Gemini 모델](https://ai.google.dev/gemini-api/docs/models)