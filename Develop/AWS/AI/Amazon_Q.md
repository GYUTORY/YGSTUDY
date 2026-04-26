---
title: Amazon Q
tags:
  - AWS
  - AI
  - Amazon Q
  - Developer Tools
  - Code Assistant
updated: 2026-04-26
---

# Amazon Q

## 정의

Amazon Q는 AWS가 만든 생성형 AI 어시스턴트다. 크게 두 갈래로 나뉜다.

- **Amazon Q Developer**: 코드 작성, AWS 리소스 관리, 디버깅, 코드 변환을 돕는 개발자용 도구. 과거 CodeWhisperer의 후속.
- **Amazon Q Business**: 사내 문서·데이터소스(S3, Confluence, SharePoint, Jira 등)를 RAG로 연결해서 사내 지식 검색·답변을 해주는 기업용 도구.

이 문서는 주로 Developer 쪽에 무게를 두고, Business는 차이점 위주로 정리한다. 실무에서 보통 "Amazon Q 써봤어?"라고 물어보면 Developer 얘기인 경우가 대부분이다.

## 왜 AWS가 Amazon Q를 만들었나

이 맥락을 모르고 쓰면 Claude Code, Copilot, Cursor와 뭐가 다른지 감이 안 온다. AWS의 동기는 명확하다.

1. **AWS 환경에 특화된 어시스턴트**: 다른 도구는 일반 코드에 강하지만, AWS 콘솔이나 IAM, CloudFormation 같은 AWS 고유 영역에서는 정확도가 떨어진다. AWS 내부 문서와 운영 노하우를 학습시킨 전용 모델이 필요했다.
2. **기업 데이터 격리**: 엔터프라이즈 고객이 "우리 코드가 OpenAI 서버로 간다"를 못 받아들이는 경우가 많다. AWS 계정 안에서 추론까지 끝내는 옵션이 필요했다.
3. **AWS 생태계 종속성 유지**: 개발자가 IDE에서부터 Cursor 같은 외부 도구에 익숙해지면, AWS 콘솔·SDK 사용 경험이 희석된다. AWS 입장에선 이 접점을 뺏기기 싫다.

그래서 Amazon Q는 "범용 코딩 어시스턴트"라기보단 "AWS를 잘 아는 어시스턴트"로 포지셔닝돼 있다. 이걸 알고 기대치를 설정하면 실망할 일이 줄어든다.

## 사용 환경

### IDE 통합

VS Code와 JetBrains 계열(IntelliJ, PyCharm, WebStorm, Rider 등)에서 공식 플러그인이 있다. Visual Studio도 지원한다. 설치는 마켓플레이스에서 "Amazon Q"로 검색해 설치하면 끝이다.

처음 쓸 때 혼동되는 부분이 **인증 방식이 두 가지**라는 점이다.

- **AWS Builder ID**: 개인용. AWS 계정 없이도 무료 플랜을 쓸 수 있다.
- **IAM Identity Center (SSO)**: 조직 계정. 회사에서 Pro 구독을 샀다면 이쪽으로 로그인해야 기능이 풀린다.

처음 로그인했는데 "Pro 기능이 안 보인다"는 경우 대부분 Builder ID로 로그인한 채 조직 계정으로 전환을 안 한 상태다. 플러그인 하단 상태바에서 계정 전환이 된다.

```text
# VS Code 기준 설치 후 흐름
1. Command Palette → "Amazon Q: Sign in"
2. AWS Builder ID 또는 IAM Identity Center 중 선택
3. 브라우저로 승인 → IDE로 돌아와 로그인 완료
4. 사이드바 Amazon Q 아이콘에서 채팅/인라인 제안 사용
```

IDE 안에서 제공하는 기능은 대체로 다음과 같다.

- **인라인 코드 제안**: 주석이나 함수명을 기반으로 코드 자동완성. Copilot과 유사.
- **채팅**: 사이드바에서 코드 블록을 선택하고 "이 함수 리팩토링해줘" 같은 지시.
- **/dev, /doc, /test, /transform, /review 슬래시 명령**: 에이전트 방식으로 파일 여러 개를 수정하거나 테스트를 생성.
- **AWS 리소스 질의**: "내 계정의 Lambda 함수 중 Node 16 런타임 있어?" 같은 질문에 실제 계정을 뒤져서 답함(권한 필요).

### AWS 콘솔 내 Q

AWS 콘솔 우측 상단에 Amazon Q 아이콘이 박혀 있다. 콘솔에서 특정 서비스 페이지를 열어놓고 질문하면 그 문맥을 반영한다. 예를 들어 RDS 페이지에서 "이 인스턴스 비용 줄일 방법 있어?"라고 물으면 RDS 관점의 답이 나온다.

실무에서 유용한 장면은 에러 해석이다. CloudWatch Logs에서 에러 로그를 띄우고 "이 오류 원인이 뭐야"를 물으면 꽤 구체적으로 답해준다. 특히 IAM 권한 부족 에러처럼 어떤 Action을 추가해야 할지 모를 때 정책 JSON 초안까지 뽑아준다.

다만 주의할 점은 **콘솔 Q는 모델 출력이 간결하게 잘리는 경향**이 있다는 것이다. 긴 설명이나 여러 파일에 걸친 수정은 IDE 쪽 Q를 쓰는 게 낫다.

### CLI 통합

터미널에서도 Q를 쓸 수 있다. `q chat` 명령으로 대화형 셸이 열리고, 자연어로 셸 명령을 생성하거나 AWS CLI 명령을 조합해준다. macOS·Linux 지원하고, 설치는 홈브루나 DMG로 가능하다.

```bash
$ q chat
> S3 버킷 중 버전 관리 꺼져 있는 것만 리스트로 뽑아줘

# 모델이 aws s3api 명령 여러 개를 조합해서 스크립트 제안
```

콘솔보다 빠르게 뭔가 확인하고 싶을 때 쓰면 편하다. 다만 실행 전 항상 확인 절차를 거치니 자동화 스크립트 용도로는 부적합하다.

## Q Developer 슬래시 명령과 에이전트

IDE 챗 입력창에서 `/`를 치면 에이전트 모드 명령 목록이 뜬다. 사이드바 채팅과 가장 큰 차이는 **여러 파일을 한 번에 수정**하고, 변경된 diff를 한 묶음으로 검토할 수 있다는 점이다. 실제 워크플로우와 한계를 정리한다.

### /dev — 새 기능 구현

자연어로 요구사항을 주면 프로젝트를 스캔해서 어떤 파일을 만들거나 고칠지 계획서를 먼저 보여준다. 사용자가 승인하면 파일을 생성·수정한다.

```text
# 일반적인 흐름
1. 채팅창에서 /dev 입력
2. 요구사항 작성 (예: "주문 테이블에 환불 사유 컬럼 추가하고 API와 DTO도 같이 수정해줘")
3. Q가 변경 계획(파일 목록 + 의도) 제시
4. 사용자 승인
5. 파일 생성/수정 → diff 형태로 적용
6. 거부할 때는 변경 단위별로 reject 가능
```

실무에서 주의할 점이 몇 가지 있다.

- **컨텍스트 윈도우 한계**: 모델 입력 한도는 명시적으로 공개돼 있지 않지만, 경험상 단일 워크스페이스에서 약 200KB~250KB 분량의 코드를 한 번에 처리할 수 있는 수준이다. 그 이상 들어가면 임의의 파일을 잘라서 보내기 시작한다. 프로젝트가 크면 Q가 핵심 파일을 못 읽고 엉뚱한 추측을 한다.
- **모노레포에서 잘 깨진다**: 한 워크스페이스에 서비스 10~20개가 들어 있는 모노레포는 컨텍스트 수집 단계에서 무관한 파일까지 끌어와 토큰을 낭비한다. 의도한 서비스 디렉터리만 VS Code에서 별도 워크스페이스로 열어주는 게 정확도를 가장 빠르게 올리는 방법이다.
- **`.gitignore`를 따르긴 하는데 완벽하지 않다**: `node_modules`, `dist`, `target` 같은 디렉터리를 그래도 가끔 읽으려 시도한다. `.amazonqignore`(VS Code 플러그인 1.30 이상)에 명시적으로 적어두면 안전하다.
- **잘 동작하는 디렉터리 구조**: 단일 언어 + 단일 빌드 시스템 + 모듈 명확히 분리(`src/`, `tests/`, `docs/`) 형태가 가장 안정적이다. Spring Boot 단일 애플리케이션, Next.js 앱 하나 같은 표준 구조에선 거의 실패하지 않는다.
- **잘 깨지는 구조**: 빌드 산출물이 소스와 같은 디렉터리에 섞여 있는 경우, 자동 생성 코드가 git에 같이 들어 있는 경우(예: protobuf 컴파일 결과), 심볼릭 링크로 외부 폴더를 가져오는 경우.

### /doc — 문서 생성

코드를 읽고 README, API 명세, 함수 docstring을 만들어 준다. 가장 잘 쓰이는 시점은 레거시 모듈을 인수인계 받을 때다.

```text
# 시나리오: 인수인계 받은 결제 모듈 문서 작성
> /doc payment 디렉터리 전체에 대해 모듈 README와 각 서비스 클래스 JavaDoc 작성

→ Q가 컨트롤러·서비스·리포지토리를 훑어 호출 그래프를 추론하고
  README + 클래스별 JavaDoc 변경 제안
```

한계는 분명하다.

- 외부 시스템 호출(외부 결제사 API)의 동작은 코드에 안 적혀 있으니 추측한다. "이 메서드는 외부 결제 API를 호출해 승인 결과를 반환한다" 같은 모호한 문장이 자주 나온다. 문서 통과 전에 사람이 사실 검증해야 한다.
- 한국어 문서 품질은 영어보다 한 단계 떨어진다. 번역투가 섞이고, 같은 영어 단어를 매번 다른 한국어로 옮긴다. 사내 용어집을 `.amazonq/rules/`에 두고 "이 단어는 이렇게 옮겨라"고 적어주면 그나마 나아진다.

### /test — 테스트 생성

선택한 클래스/함수에 대해 단위 테스트를 만든다. JUnit 5, pytest, Jest를 가장 잘 다룬다.

```text
> /test UserService 클래스에 대해 happy path와 예외 케이스 테스트 생성
```

- **모킹 라이브러리 감지가 들쭉날쭉**: Mockito면 잘 되는데, MockK(Kotlin)나 Sinon 같은 건 가끔 잘못된 import를 만든다. 첫 실행 후 나오는 import 정리는 사람이 한다.
- **DB 연동 테스트는 약하다**: Testcontainers 기반 통합 테스트는 도구 자체보다 프로젝트의 기존 테스트 패턴에서 배운다. 기존에 `@Testcontainers` 베이스 클래스가 있으면 그걸 따라가지만, 없는 상태에서 새로 만들어달라 하면 단순 H2 인메모리로 빠지는 경우가 많다.
- **커버리지 자동 채우기는 무리**: "이 클래스 커버리지 80%까지 올려줘" 같은 요청은 표면적으로 통과하는 가짜 테스트(`assertNotNull(result)`만 하는 테스트)를 양산한다. 시나리오를 사람이 짚어주는 게 낫다.

### /transform — 코드 변환

별도 섹션에서 자세히 다룬다. (아래 "코드 변환" 참고)

### /review — 보안·품질 리뷰

PR을 올리기 전에 한 번 돌리는 용도로 쓴다. 정적 분석 + LLM 리뷰가 합쳐진 형태다. 보안 스캔과 동일 엔진을 쓰며, 결과는 IDE의 Problems 탭에 나온다.

## MCP 서버 연동

2026년 초에 Q Developer가 **Model Context Protocol(MCP)** 클라이언트로 동작하기 시작했다. Anthropic이 제안한 표준이고, Claude Code·Cursor가 먼저 지원하던 방식인데 Q도 이제 같은 생태계에 들어왔다. 사내 도구나 외부 SaaS를 Q에 붙여서 채팅 안에서 호출하게 하는 용도다.

### 설정 위치

VS Code 기준으로 Q의 MCP 설정 파일은 다음 경로에 둔다.

```text
~/.aws/amazonq/mcp.json                # 사용자 전역
<프로젝트 루트>/.amazonq/mcp.json       # 프로젝트별 (팀 공유 가능)
```

JSON 스키마는 Claude Code의 `mcp.json`과 거의 동일하다. 같은 MCP 서버 바이너리를 그대로 쓸 수 있다.

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@atlassian/mcp-server-jira"],
      "env": {
        "JIRA_HOST": "https://mycorp.atlassian.net",
        "JIRA_EMAIL": "${env:JIRA_EMAIL}",
        "JIRA_API_TOKEN": "${env:JIRA_API_TOKEN}"
      }
    },
    "internal-deploy": {
      "command": "/usr/local/bin/internal-deploy-mcp",
      "args": ["--mode", "stdio"],
      "env": {
        "DEPLOY_TOKEN": "${env:DEPLOY_TOKEN}"
      }
    },
    "postgres-readonly": {
      "command": "uvx",
      "args": ["mcp-server-postgres", "--readonly"],
      "env": {
        "DATABASE_URL": "${env:DATABASE_URL_RO}"
      }
    }
  }
}
```

### 사내 도구를 붙이는 일반적인 패턴

사내에 이미 도커 이미지로 떠 있는 내부 API 게이트웨이가 있을 때, 그 앞에 얇은 MCP 서버 어댑터를 만들어 둔다. 그러면 개발자가 채팅창에서 "스테이징 환경 v1.42.3 배포 상태 알려줘" 같은 질문을 자연어로 던질 수 있다.

```bash
# 어댑터 직접 작성 시 일반적인 구조
my-internal-mcp/
├── package.json
├── src/
│   ├── server.ts          # MCP stdio 서버 진입점
│   ├── tools/
│   │   ├── deploy_status.ts
│   │   ├── deploy_rollback.ts
│   │   └── slack_notify.ts
│   └── auth.ts            # AWS STS / OIDC 토큰 교환
└── README.md
```

실제 운영에 들어갈 때 챙겨야 할 점이 있다.

- **자격 증명 관리**: MCP 서버는 로컬 머신에서 사용자 권한으로 도는 프로세스다. 자격 증명을 평문으로 `mcp.json`에 넣으면 이게 그대로 git에 올라가는 사고가 흔하다. `${env:VAR}` 표기로 환경변수에서만 읽도록 하고, `.amazonq/mcp.json`은 git에 올리되 토큰은 절대 안 들어가게 한다.
- **호출 승인 모드**: Q는 MCP 도구 호출 전에 사용자에게 한 번 묻는 것이 기본값이다. 자동 승인을 켜면 모델이 임의로 도구를 호출하니, 파괴적인 작업(배포, 롤백, 데이터 삭제)을 하는 도구는 항상 묻기로 둔다.
- **MCP 서버 자체 권한 모델**: Q는 호출 권한을 검증하지 않는다. "이 도구는 누가 어떤 행동을 할 수 있는가"를 도구 자신이 결정해야 한다. 사내 인증 토큰을 그냥 받지 말고 OIDC로 사용자 신원을 검증한 후 행동을 분기하는 식이 안전하다.
- **로깅**: MCP 호출은 IDE 로컬에서 일어나니 CloudTrail에 안 남는다. 도구 쪽에서 자체 감사 로그를 남기지 않으면 누가 무엇을 호출했는지 추적이 안 된다.

## 코드 변환 (Q Transform)

Amazon Q에서 실무적으로 가장 차별적인 기능이 **코드 변환**이다. 현재 지원하는 대표 변환은 다음과 같다.

- Java 8 / 11 → Java 17, 21
- .NET Framework → .NET (cross-platform)
- Windows 기반 .NET → Linux 기반으로 이식
- 임베디드 SQL → AWS Glue 호환 코드(2026년 초 추가)

Java 8에서 17로 올리는 작업을 실제 프로젝트에서 돌려봤을 때 경험을 정리하면 이렇다.

### 돌리는 방식

IDE 플러그인에서 `/transform`을 선택하면 프로젝트를 업로드하고, AWS 쪽에서 변환 작업이 실행된다. 완료되면 변경 사항을 diff로 받아서 PR 형태로 머지한다. Maven 프로젝트가 가장 안정적이고, Gradle은 지원되긴 하지만 빌드 스크립트 구조에 따라 실패 빈도가 높다.

```text
1. IDE에서 /transform 실행
2. 대상 프로젝트 루트와 빌드 시스템(Maven/Gradle) 지정
3. 클라우드에서 빌드 → 의존성 업그레이드 → 테스트 실행
4. 결과 diff 확인 후 수락/거절
```

### 실제로 바뀌는 것

- `pom.xml`의 Java 버전과 플러그인 버전 업데이트
- Deprecated API(`javax.*` → `jakarta.*`) 자동 변경
- Spring Boot 2.x → 3.x 업그레이드에 필요한 종속성 조정
- 일부 Lombok, MapStruct 같은 애너테이션 프로세서 호환 버전 매칭

### 주의사항

- **변환 후 반드시 테스트 커버리지 확인**: 모델이 API 마이그레이션을 잘못 해석해서 기능이 미묘하게 바뀌는 경우가 있다. 특히 `Date`, `Calendar` 쪽과 `HttpClient` 주변은 손으로 다시 검증해야 한다.
- **종속성 지옥**: 서드파티 라이브러리 중 Java 17 미지원인 게 섞여 있으면 빌드가 중간에 깨진다. 이럴 땐 Q가 제안한 업그레이드 버전이 실제로 존재하는지 Maven Central을 확인해야 한다.
- **대형 프로젝트는 모듈 단위로**: 멀티모듈 프로젝트 전체를 한 번에 변환하려 하면 타임아웃이 자주 발생한다. 하위 모듈부터 나눠서 진행하는 게 낫다.

실무 감각으로는 "사람이 2주 걸릴 작업을 2시간으로 줄여준다"기보단, "사람이 2주 걸릴 작업의 80%를 자동으로 처리해주고 나머지 20%는 여전히 사람이 디버깅해야 한다"에 가깝다. 그럼에도 첫 초안을 쥐고 시작하는 게 백지에서 시작하는 것보다 훨씬 빠르다.

### Transform 실패 시 로그 위치

`/transform`이 중간에 죽거나 빌드 실패로 끝나는 경우가 잦다. 어디를 봐야 하는지 정리해 둔다.

```text
# 클라이언트 측 (IDE 로컬)
VS Code:        ~/.aws/amazonq/logs/transform/<job-id>/
JetBrains:      ~/.aws/amazonq/logs/transform/<job-id>/  (동일)
Windows:        %USERPROFILE%\.aws\amazonq\logs\transform\<job-id>\

# 위 디렉터리에 있는 파일들
manifest.json           # 작업 메타데이터, 시작/종료 시각, 입력 빌드 시스템
client.log              # 업로드/다운로드, 인증 흐름
build-output.txt        # 클라우드 빌드 단계 stdout (실패 시 핵심)
diff-summary.json       # 적용 직전 변경 요약
```

`build-output.txt`가 실제 빌드 실패 원인이 가장 잘 드러나는 파일이다. JDK 버전 충돌, 사라진 transitive dependency, 테스트 단계에서의 OOM 등이 여기 찍힌다.

서버 측 작업 상태는 IDE 채팅창에 "View transformation hub"로 들어가면 단계별 진행률이 보인다. 클라우드 측 raw 로그는 사용자가 직접 못 보고, AWS 지원 케이스 열 때 `<job-id>`를 알려줘야 한다.

## 보안 스캔

Amazon Q Developer는 코드 보안 스캔을 내장하고 있다. IDE에서 `Run Security Scan` 또는 `/review`로 실행한다.

탐지하는 것들을 대략 분류하면 이렇다.

- OWASP Top 10 계열: SQL Injection, XSS, 하드코딩된 시크릿
- AWS SDK 사용 시 안티패턴: credential을 코드에 박아둔 경우, 과도한 IAM 권한 요청
- 의존성 취약점(CVE)

SonarQube나 Snyk을 쓰는 팀에겐 완전 대체재는 아니다. Amazon Q의 보안 스캔은 **AWS 맥락의 실수에 민감하다**는 게 장점이다. 예를 들어 S3 버킷에 `s3:*` 권한을 주는 IAM 정책을 발견하거나, Lambda 환경 변수에 AWS 자격 증명을 넣는 패턴을 잡아낸다. 일반 SAST 도구는 이런 걸 잘 못 잡는다.

반면 Java 바이트코드 분석이나 복잡한 taint analysis 같은 건 SonarQube·Checkmarx 수준에 못 미친다. 보조 도구로 보는 게 현실적이다.

## Q Business 심화

Q Business는 사내 데이터를 RAG로 묶어 검색·답변을 해주는 도구다. 도입할 때 가장 신경 써야 할 두 가지가 **Retriever 선택**과 **ACL 동기화**다.

### Retriever 구성: Kendra vs Native

Q Business의 Retriever는 두 가지 중 하나를 고른다. 한 번 선택하면 나중에 바꾸기 어렵다.

| 항목 | Kendra retriever | Native retriever |
|------|------------------|------------------|
| 인덱스 엔진 | 별도의 Kendra 인덱스 | Q Business 내부 벡터 스토어 |
| 비용 | Kendra 인덱스 시간당 + Q 사용자당 | Q 사용자당 + 인덱스 용량당 |
| 데이터 소스 종류 | Kendra 커넥터(40여 종) | Q Business 커넥터(2026년 기준 35여 종) |
| 검색 품질 | 키워드 + 시맨틱 하이브리드, 오랜 튜닝 결과 반영 | 시맨틱 중심, 단순 |
| 권한(ACL) 동기화 | Kendra 측 커넥터가 처리 | Q Business 측이 처리 |
| 유지비 | 사용량 적어도 Kendra Edition 시간당 비용 발생 | 사용량 비례 |
| 고도화 기능 | 커스텀 동의어, 어구 검색, 메타데이터 부스팅 | 제한적 |

선택 기준은 단순하다.

- **이미 Kendra를 쓰고 있다**: Kendra retriever를 그대로 연결한다. 인덱스 재구축 안 해도 된다.
- **데이터가 수십만 페이지 이상**, 검색 정확도가 핵심**: Kendra retriever. 키워드 매칭 튜닝이 가능해 사내 약어·코드 검색에 강하다.
- **PoC, 사용자 100명 미만, 데이터 적음**: Native retriever. 시간당 고정비가 없어 트래픽 적을 때 훨씬 싸다.
- **데이터가 빠르게 변한다**: Native retriever 쪽이 인덱싱 지연이 짧다(분 단위). Kendra는 커넥터에 따라 시간 단위로 미뤄지는 경우가 있다.

### S3, Confluence, Jira 인덱싱과 ACL 동기화

데이터 소스를 붙일 때 권한 처리가 가장 까다롭다. "Confluence에서 보안팀 페이지는 보안팀만 볼 수 있어야 한다"가 깨지면 사고가 된다.

| 데이터 소스 | ACL 동기화 동작 | 자주 터지는 함정 |
|------------|----------------|-----------------|
| S3 | 객체 메타데이터에 사용자/그룹 ID를 명시하거나, ACL 매니페스트(JSON Lines) 별도 업로드 | 객체별 ACL을 명시 안 하면 인덱스에 들어간 모든 문서가 전사 공개로 잡힘 |
| Confluence | 스페이스 단위 권한 + 페이지 단위 제한을 그대로 복제 | 익명 권한이 켜진 페이지는 Q에서도 전 직원에게 공개됨 |
| Jira | 프로젝트 권한 스킴, 이슈 보안 레벨 동기화 | 외부 협력사 계정이 Confluence/Jira에 있으면 Q 라이선스 없는 사용자가 권한 동기화에 같이 쓸려 들어가 동기화 실패 |
| SharePoint | 사이트 권한 + 폴더/파일 권한 동기화. AAD 그룹 매핑 필요 | AAD ↔ Identity Center 그룹 ID가 일치하지 않으면 권한 매칭 실패 |

권한 누수가 실제로 어떻게 터지는지 사례 몇 가지를 정리한다.

- **S3 ACL 매니페스트 누락**: 인사팀이 평가 결과를 S3에 올리고 데이터 소스에 연결만 했는데, ACL 매니페스트를 안 올려 모든 직원이 검색에서 보였다. 인덱싱이 끝나기 전엔 외부에서 알 수 없으니, 첫 인덱싱 직후 권한 리뷰를 의무화해야 한다.
- **Confluence 익명 권한**: "Anyone can view"가 켜진 오래된 위키 페이지가 그대로 인덱스에 들어가, 사내 검색에서 외주 계정도 볼 수 있게 됐다. 인덱싱 전에 익명 권한 페이지를 스캔해 차단 목록에 넣는 사전 단계가 필요하다.
- **그룹 ID 표기 차이**: Identity Center 그룹 ID는 UUID인데, Confluence 측 그룹은 이름 기반이다. 매핑을 잘못 걸면 권한이 비교 자체가 안 돼 모두 거부 또는 모두 허용으로 빠진다. 도입 초기엔 더미 사용자로 권한 격자를 직접 검증해야 한다.

### 인덱스 동기화 일정

데이터 소스 동기화는 풀(Pull) 기반이다. 일정 옵션은 다음과 같다.

```text
- 한 번만 (수동)
- 시간당
- 일간
- 주간
- 매월 1일
- cron 표현식 (rate(15 minutes), cron(0 */6 * * ? *) 등)
```

업무 시간에 매시간 동기화를 거는 경우, 데이터 소스 측 API 한도(특히 Jira/Confluence Cloud)에 닿아서 동기화가 부분 실패로 끝날 수 있다. 사용자가 적은 새벽 시간대에 일 1회로 두고, 핫한 데이터(현재 운영 중인 사고 페이지 등)는 별도 데이터 소스로 분리해서 짧게 도는 패턴이 안전하다.

### Q Apps 빌더

Q Business 안에는 Q Apps라는 노코드 앱 빌더가 들어 있다. 사내 사용자가 Q를 그냥 채팅으로만 쓰지 않고, 자기 업무에 맞는 작은 도구를 만들어 동료에게 공유할 수 있다.

```text
# 일반적인 흐름
1. Q Business 웹 콘솔 → Apps 탭 → "Create app"
2. 자연어로 앱 설명 (예: "고객 문의 메일을 붙여 넣으면 카테고리 분류와 답변 초안을 생성")
3. Q가 입력 필드, 프롬프트, 출력 형식을 자동 구성
4. 사용자가 입력 라벨, 데이터 소스 사용 여부, 출력 형식 미세 조정
5. "Publish to library" → 같은 Q Business 인스턴스의 다른 사용자가 검색해서 사용
```

실무에서 본 한계는 다음과 같다.

- **외부 시스템 호출 불가**: Q Apps는 RAG 검색 + 모델 호출까지만 한다. "Jira 티켓 생성"처럼 쓰기 동작이 필요하면 Q Apps로는 안 된다. Lambda로 별도 백엔드를 만들어 Q Business API에서 부르거나, 결과를 사용자가 수동으로 옮기는 식으로 우회한다.
- **버전 관리 없음**: 앱을 수정하면 기존 사용자가 바로 새 버전을 쓰게 된다. 롤백 기능이 없으니 운영 중인 앱은 복제본을 만들어 테스트 후 교체하는 식으로 다뤄야 한다.
- **권한이 단순**: 앱은 "발행자 본인만" 또는 "전체 공개"만 된다. 부서별 공개가 안 돼서 인사팀 전용 앱을 만들면 다른 부서도 검색에서 볼 수 있다.
- **데이터 소스 사용 권한은 사용자별로 적용**: 앱이 데이터 소스를 검색해도, 응답에는 사용자 본인이 접근 권한 있는 문서만 들어간다. 즉 같은 앱이라도 사용자에 따라 답이 달라진다.

PoC 수준에선 빠르게 만들기 좋지만, 사내 표준 사례로 자리 잡으려면 위 한계를 사용자에게 미리 공지해 둬야 한다.

## IAM 권한 구성

Q Developer를 회사에서 굴리려면 IAM Identity Center 측 라이선스 외에, AWS 계정에서 Q가 다른 AWS 리소스에 접근하는 권한을 따로 정리해야 한다. 자주 쓰는 정책 두 종류를 예시로 둔다.

### 사용자에게 부여하는 Q Developer 사용 권한

직원이 IDE에서 Q를 켜고 자기 계정 리소스를 질의할 때 필요한 최소 권한이다. Identity Center 사용자에 직접 붙이거나, Permission Set의 인라인 정책으로 넣는다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAmazonQDeveloperRead",
      "Effect": "Allow",
      "Action": [
        "q:SendMessage",
        "q:GetConversation",
        "q:ListConversations",
        "q:StartConversation",
        "q:DeleteConversation",
        "q:GetIdentityMetadata"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowResourceQueries",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "lambda:List*",
        "lambda:Get*",
        "logs:Describe*",
        "logs:GetLogEvents",
        "logs:FilterLogEvents",
        "cloudformation:List*",
        "cloudformation:Describe*",
        "iam:Get*",
        "iam:List*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDestructive",
      "Effect": "Deny",
      "Action": [
        "*:Delete*",
        "*:Terminate*",
        "*:Stop*"
      ],
      "Resource": "*"
    }
  ]
}
```

`Describe`/`List`/`Get` 류만 허용하고, 파괴적인 호출은 명시적으로 거부했다. Q가 콘솔에서 "이거 지워드릴까요?"를 제안할 때 사용자가 yes를 누르면 사용자 ID로 호출이 나간다. 그 호출이 정책을 통과하지 않게 막아야 안전하다.

### Q에 필요한 최소 서비스 권한 (Q Business 관리자)

Q Business 인스턴스를 만들고 데이터 소스를 붙이는 관리자에게 주는 정책이다. 일반 사용자가 아니라 운영자에게만 한정한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "QBusinessAdmin",
      "Effect": "Allow",
      "Action": [
        "qbusiness:*",
        "kendra:CreateIndex",
        "kendra:UpdateIndex",
        "kendra:DescribeIndex",
        "kendra:CreateDataSource",
        "kendra:UpdateDataSource",
        "kendra:DeleteDataSource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ServiceLinkedRole",
      "Effect": "Allow",
      "Action": "iam:CreateServiceLinkedRole",
      "Resource": "arn:aws:iam::*:role/aws-service-role/qbusiness.amazonaws.com/*",
      "Condition": {
        "StringLike": {
          "iam:AWSServiceName": "qbusiness.amazonaws.com"
        }
      }
    },
    {
      "Sid": "AccessIdentityCenter",
      "Effect": "Allow",
      "Action": [
        "sso:DescribeInstance",
        "sso:ListInstances",
        "sso-directory:DescribeUsers",
        "sso-directory:DescribeGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

Q Business는 Identity Center를 쳐다보고 사용자/그룹을 가져온다. 그래서 sso, sso-directory 권한이 같이 필요하다. 빠뜨리면 데이터 소스의 ACL 동기화가 절반만 동작한다.

### 데이터 소스 IAM 역할

데이터 소스마다 별도의 IAM 역할이 따로 만들어진다. 예를 들어 S3 데이터 소스 역할은 인덱싱할 버킷의 `s3:GetObject`, `s3:ListBucket`만 받게 좁혀야 한다. 콘솔이 자동 생성하는 역할은 너무 넓은 경우가 있어, 운영 환경에선 직접 작성한 역할을 가져다 붙이는 편이 낫다.

## IAM Identity Center 운영

조직에서 Q를 굴리는 거의 모든 경우 IAM Identity Center가 출발점이 된다. 라이선스 할당과 사용량 추적이 여기 모인다.

### 그룹 단위 라이선스 할당

Q Developer Pro 라이선스는 "사용자 단위"로 결제되지만, 할당 자체는 Identity Center 그룹에 걸어두는 게 운영하기 좋다.

```text
# 일반적인 그룹 구조
identity-center/
├── eng-q-developer-pro     # Q Pro 라이선스 받는 개발자
├── eng-q-developer-free    # Free만 쓰는 인턴/계약직
├── biz-q-business-users    # Q Business를 쓰는 영업/마케팅
└── biz-q-business-admin    # Q Business 관리자
```

콘솔 경로는 `Amazon Q Developer → Settings → Subscriptions`에 들어가서 그룹 단위로 Pro 구독을 켜면 된다. 신규 입사자가 `eng-q-developer-pro` 그룹에 들어가는 순간 자동으로 Pro가 풀린다. 퇴사자는 그룹에서 빠지면서 자동 정리된다. 사용자 한 명 한 명 직접 클릭하지 않는 게 첫 번째 운영 원칙이다.

### 사용량 모니터링

`Amazon Q Developer 콘솔 → Dashboard`에 들어가면 다음 지표가 보인다.

```text
- 활성 사용자 수 (DAU/MAU)
- 코드 제안 수락률
- 채팅 메시지 수
- /transform 잡 수와 처리 라인 수
- /dev, /doc, /test 호출 횟수
- 보안 스캔 실행 횟수
- Pro 라이선스 사용률 (할당 대비 활성 사용자)
```

라이선스 사용률 지표가 가장 중요하다. Pro 라이선스 100개를 사놓고 활성 사용자가 30명이면 70개 라이선스 비용이 그냥 나가고 있다. 분기마다 활성 사용자 30일 미만 라이선스를 회수하는 절차를 만들어 두면 비용이 한 자릿수 % 단위로 빠진다.

콘솔 외에 CloudWatch에도 `AWS/AmazonQ` 네임스페이스로 일부 지표가 게시된다. 사내 BI 도구로 끌고 가서 부서별 사용량 리포트로 만드는 게 일반적인 운영 패턴이다.

## CloudTrail 감사

Q 관련 호출은 CloudTrail에 `q.amazonaws.com`, `qbusiness.amazonaws.com`, `codewhisperer.amazonaws.com` 이벤트 소스로 기록된다. CodeWhisperer 시절 이벤트가 아직 일부 남아 있다는 점이 헷갈리는 부분이다.

### 자주 보는 이벤트

```text
SendMessage              # 채팅 메시지 1건
StartConversation        # 새 채팅 세션 시작
StartCodeAnalysis        # 보안 스캔 실행
CreateUploadUrl          # /transform 또는 보안 스캔용 업로드 URL 발급
StartTransformation      # /transform 잡 시작
GetTransformation        # 잡 상태 폴링
ListConversations        # 사용자가 본인 히스토리 조회
```

### CloudTrail Lake 쿼리 예제

조직 차원 감사 로그를 CloudTrail Lake로 모았다고 가정하면, 가장 자주 쓰는 쿼리는 다음 정도다.

```sql
-- 최근 7일간 사용자별 Q 채팅 횟수
SELECT
    userIdentity.principalId AS user_id,
    userIdentity.userName AS user_name,
    COUNT(*) AS message_count
FROM <event-data-store-id>
WHERE eventSource IN ('q.amazonaws.com', 'qbusiness.amazonaws.com')
  AND eventName = 'SendMessage'
  AND eventTime > timestamp '2026-04-19'
GROUP BY userIdentity.principalId, userIdentity.userName
ORDER BY message_count DESC
LIMIT 50;
```

```sql
-- /transform 작업 시작/실패 추적
SELECT
    eventTime,
    userIdentity.userName AS user_name,
    eventName,
    errorCode,
    errorMessage,
    requestParameters
FROM <event-data-store-id>
WHERE eventSource = 'q.amazonaws.com'
  AND eventName IN ('StartTransformation', 'GetTransformation')
  AND eventTime > timestamp '2026-04-12'
ORDER BY eventTime DESC;
```

```sql
-- VPC 외부에서 들어오는 Q 호출 (PrivateLink 강제 위반 감지)
SELECT
    eventTime,
    userIdentity.userName AS user_name,
    sourceIPAddress,
    vpcEndpointId,
    eventName
FROM <event-data-store-id>
WHERE eventSource IN ('q.amazonaws.com', 'qbusiness.amazonaws.com')
  AND vpcEndpointId IS NULL
  AND sourceIPAddress NOT LIKE '10.%'
ORDER BY eventTime DESC;
```

### 내용 자체는 안 남는다

CloudTrail에는 누가 언제 어떤 API를 불렀는지가 남고, 채팅 메시지 본문이나 모델 응답은 기록되지 않는다. 본문을 감사하려면 Q Developer Settings에서 "Customer Managed Logging"을 켜고 별도의 S3 버킷으로 보내야 한다(2026년 기준 Pro 플랜에서만 제공). 이 기능을 쓰면 사용자 동의 정책을 사내 규정에 미리 반영해 둬야 분쟁이 없다.

## 요금제

### Developer Free vs Pro

| 항목 | Free | Pro |
|------|------|-----|
| 월 요금 | $0 | 사용자당 $19/월 (2026년 기준) |
| 코드 제안 | 제한 있음 | 무제한 |
| 채팅 메시지 | 월 50개 제한 | 무제한 |
| 코드 변환 (Transform) | 월 1,000줄 | 월 4,000줄 (추가 시 과금) |
| 에이전트 실행 | 월 10회 | 월 30회 |
| 보안 스캔 | 프로젝트당 월 25회 | 프로젝트당 월 500회 |
| AWS 리소스 접근 (Q in console) | 가능 | 가능 |
| 커스터마이제이션 (사내 코드 학습) | 불가 | 가능 |
| 관리자 대시보드 | 없음 | 있음 |

Free 플랜은 혼자 개인 프로젝트를 만지는 수준에선 충분하지만, 업무용으로는 거의 항상 한도에 걸린다. 특히 채팅 메시지 50개는 하루 만에 바닥난다.

Pro에서 중요한 건 **커스터마이제이션**이다. 사내 GitLab/GitHub 저장소를 연결해 Q가 사내 코드 스타일과 내부 라이브러리를 학습하게 할 수 있다. 이 기능이 있어야 "우리 팀의 공통 유틸 함수를 써서 구현해줘" 같은 요청이 제대로 먹는다. Copilot Enterprise와 동일한 컨셉이다.

### Transform 추가 라인 과금 계산 예시

`/transform`은 Pro 사용자당 월 4,000줄까지 포함이고, 그 이상은 라인당 추가 요금이 붙는다. 2026년 기준 1,000줄당 $0.50 수준이다(요율은 분기별로 변동).

```text
시나리오: Pro 사용자 30명, 한 달간 Java 8→17 마이그레이션 진행
- 포함 한도: 30명 × 4,000줄 = 120,000줄
- 실제 변환 라인: 320,000줄
- 초과분: 320,000 - 120,000 = 200,000줄
- 추가 비용: 200,000 / 1,000 × $0.50 = $100

Pro 구독 비용: 30 × $19 = $570
Transform 초과 비용: $100
월 합계: $670
```

라인 수는 Q Transform이 실제로 분석·수정한 코드 라인 기준이다. `pom.xml` 한 줄 바꾸려고 잡을 돌렸을 때도 의존 분석 대상 라인이 합산되니, 작은 잡을 자주 돌리는 패턴이 비용에는 더 불리하다. 가능하면 모듈 단위로 모아서 한 번에 돌리는 게 같은 결과로도 라인 카운트가 적게 나온다.

### Business 플랜과 인덱스 용량 과금

Q Business는 별도 요금제다.

```text
- Lite: 사용자당 $3/월   (검색·답변 기본 기능)
- Pro:  사용자당 $20/월  (Q Apps, 커스텀 플러그인, 광범위한 데이터 소스)
- Premium: 사용자당 $40/월 (감사 로깅 본문 기록, SLA 등 추가)
```

여기에 **인덱스 용량 과금**이 붙는다. Native retriever 기준으로 인덱스 1GB·월당 요금이 정해져 있고, Kendra retriever를 고르면 Kendra Edition 시간당 비용이 그대로 따라온다.

```text
시나리오: Q Business Pro, 사용자 200명, Native retriever
        Confluence 위키 12GB + S3 정책 문서 8GB = 인덱스 20GB

월 사용자 비용: 200 × $20 = $4,000
인덱스 용량 비용: 20GB × $0.140/GB·월 = $2.80   ※ 2026년 Native retriever 예시 단가
월 합계 (대략): $4,003
```

```text
시나리오: 동일한 데이터를 Kendra Developer Edition retriever로 운영
- Q Business Pro 사용자 비용은 동일: $4,000
- Kendra Developer Edition: 시간당 $1.125 × 24 × 30 ≈ $810/월
- (Enterprise Edition은 시간당 약 $7로 훨씬 비쌈)
월 합계: 약 $4,810
```

같은 데이터를 다뤄도 retriever 선택만으로 월 $800 가까이 차이가 난다. 인덱스가 작고 사용자가 적은 단계에선 Native가 명백히 싸다. 다만 인덱스가 100GB 단위로 커지면 Native의 GB 과금이 누적되어 Kendra 고정 비용보다 비싸지는 시점이 온다. 도입 시 1년 사용 시뮬레이션을 해보고 결정하는 게 안전하다.

## 기업 환경에서의 데이터 격리

엔터프라이즈에서 도구 선정할 때 항상 부딪히는 질문이 "우리 코드가 모델 학습에 쓰이냐"다. Amazon Q의 입장은 명확하다.

- **Pro 플랜 이상**: 고객 콘텐츠가 서비스 개선이나 모델 학습에 사용되지 않는다. 이건 계약상 보장된다.
- **Free 플랜**: 설정에서 명시적으로 끄지 않으면 일부 데이터가 서비스 개선에 사용될 수 있다. 기본값이 opt-out인 경우도 있으니 조직 정책으로 따로 관리하는 게 낫다.
- **리전 선택**: 데이터가 처리되는 리전을 지정할 수 있다. 국내 금융·공공 고객은 서울 리전을 요구하는데, 2026년 기준으로 Q Developer 일부 기능이 아직 서울 리전에서 제약이 있다. 도입 전에 반드시 해당 리전의 기능 매트릭스를 확인해야 한다.

기업 환경에서 실무적으로 챙겨야 할 포인트는 몇 가지 더 있다.

- **IAM Identity Center 기반 SSO 강제**: 직원 개인 Builder ID로 쓰게 두면 데이터 통제가 안 된다. 조직 차원에서 SSO 로그인만 허용하고 사용 로그를 감사해야 한다.
- **VPC 엔드포인트**: 민감한 코드베이스를 다루는 프로젝트는 PrivateLink로 VPC 안에서만 Q 트래픽을 통과시키는 구성이 가능하다. 단 모든 기능이 VPC 엔드포인트에서 동작하는 건 아니어서, 사전에 확인해야 한다.
- **사용 로그**: CloudTrail과 CloudWatch에서 Q 관련 이벤트를 추적할 수 있다. 누가 언제 어떤 파일에 대해 질문했는지 감사 로그로 남는다.

## 트러블슈팅

### Pro 라이선스인데 기능이 안 풀릴 때

가장 흔한 신고다. 확인 순서를 고정해두면 빨리 해결된다.

```text
1. IDE 좌하단 계정 표시 확인
   - "AWS Builder ID"로 로그인된 상태면 Pro 안 풀림
   - "IAM Identity Center" + 회사 도메인 표시되어야 함
2. Identity Center 콘솔 → Users → 본인 계정 → Group 탭
   - Pro 그룹(eng-q-developer-pro 등)에 속해 있는지
3. Q Developer 콘솔 → Subscriptions
   - 해당 그룹/사용자에 Pro가 할당돼 있는지
4. 플러그인 버전 확인
   - 너무 오래된 버전은 Pro 인식 자체를 못 함. 최신으로 업데이트
5. 캐시 초기화
   - VS Code: ~/.aws/amazonq/cache/ 삭제 후 재로그인
6. 그래도 안 되면 약 15분 대기
   - 라이선스 변경 반영에 시간차가 있다 (특히 신규 그룹 만든 직후)
7. CloudTrail에서 SendMessage 호출의 errorCode 확인
   - "QSubscriptionNotFound" → 구독 미할당
   - "AccessDenied" → IAM 정책 문제
```

대부분 1~3단계에서 끝난다. 6단계까지 가는 건 드물다.

### VPC 엔드포인트로 차단되는 기능

PrivateLink로 Q 트래픽을 강제할 때, **모든 기능이 VPC 엔드포인트로 도는 건 아니다**. 2026년 4월 기준으로 정리하면 다음과 같다(서비스가 빠르게 추가되니 도입 전에 다시 확인 권장).

| 기능 | 인터페이스 엔드포인트 지원 | 비고 |
|------|------|-----|
| 인라인 코드 제안 | 지원 | `com.amazonaws.<region>.codewhisperer` |
| 채팅 / SendMessage | 지원 | `com.amazonaws.<region>.q` |
| /dev, /doc, /test 에이전트 | 지원 | 위와 동일 엔드포인트 |
| /transform | 부분 지원 | 작업 자체는 통과, 결과 다운로드 시 일부 리전에서 추가 엔드포인트 필요 |
| 보안 스캔 | 지원 | |
| Q Apps (Q Business) | 부분 지원 | 일부 데이터 소스 커넥터(SaaS)는 인터넷 트래픽 필수 |
| Q in 콘솔 (RDS/CloudWatch 페이지) | 미지원 | 콘솔 자체가 인터넷 호출 |
| MCP 클라이언트 호출 | 해당 없음 | 로컬 머신에서 도는 부분, 엔드포인트와 무관 |

VPC 엔드포인트만 열어둔 폐쇄망 PC에서 Q 콘솔 기능이 안 된다고 신고가 들어오면 거의 항상 위 표의 "미지원" 항목이다. 콘솔용은 어차피 대부분의 기업이 인터넷 프록시를 따로 두니, 그쪽 화이트리스트에 `q.amazonaws.com`, `qbusiness.amazonaws.com`을 추가하는 식으로 풀어준다.

### /transform 실패 시 어디부터 보나

실패 신호별로 보는 위치가 다르다.

```text
[ 빌드 실패 (compile error) ]
→ ~/.aws/amazonq/logs/transform/<job-id>/build-output.txt
   하단의 "BUILD FAILURE" 직전 스택을 본다

[ 의존성 해석 실패 ]
→ 같은 디렉터리의 manifest.json + build-output.txt
   "Could not resolve dependencies" 메시지 → Maven Central 또는 사내 Nexus 접근 가능 여부 확인

[ 테스트 실패 ]
→ build-output.txt 의 surefire/failsafe 리포트 위치 추적
   사용자 환경(Docker, Testcontainers)에 의존하는 테스트는 클라우드 빌드에서 못 돈다 → @DisabledOnTransform 같이 표식 달아 제외

[ 작업이 중간에 멈춤 / 타임아웃 ]
→ IDE 채팅창의 Transformation Hub → "View progress" → 단계 확인
→ 보통 단일 모듈이 너무 큼 (>5,000 파일). 모듈 분리 후 재시도

[ 인증/업로드 단계 실패 ]
→ client.log 에서 401/403 검색
→ Pro 구독, IAM 권한 (q:CreateUploadUrl 등), 프록시 설정 순으로 확인
```

지원 케이스를 열어야 할 때는 **반드시 `<job-id>`를 함께 첨부**한다. 그게 없으면 AWS 측에서 추적이 안 돼 핑퐁만 길어진다.

## Claude Code, Copilot, Cursor와 비교

이 세 도구는 각각 성격이 다르다. 실무에서 "무조건 Q가 낫다" 또는 "무조건 Cursor가 낫다" 같은 답은 없고, 일하는 맥락에 따라 다르다.

### 모델 품질 관점

순수하게 코드 생성 품질만 보면 2026년 기준으로 **Claude Code > Cursor (Claude 모델 사용 시) > Copilot > Amazon Q** 순으로 느껴진다. Q는 AWS 특화 학습은 잘 됐지만, 일반적인 알고리즘 문제나 복잡한 리팩토링에서는 Claude 기반 도구에 밀린다.

### AWS 관련 작업

반대로 AWS 쪽 작업에선 Q가 가장 정확하다.

- IAM 정책 JSON 생성: Q가 가장 정확하다. Claude Code도 잘하지만 최신 Action 이름이나 Condition Key는 Q가 더 안정적이다.
- CloudFormation/CDK/Terraform 초안: 차이가 크진 않지만 Q가 AWS 내부 문서 기반이라 옵션명을 덜 틀린다.
- AWS 콘솔 내 실시간 질의: Q 외에는 불가능하다. 콘솔에 들어가 있다는 맥락 자체가 Q만의 장점이다.

### 에이전트/자율 작업

Claude Code와 Cursor는 여러 파일을 자유롭게 수정하고 테스트를 돌리는 에이전트 루프가 성숙해 있다. Q에도 `/dev` 같은 에이전트 기능이 있지만, 실제로 써보면 컨텍스트 유지와 반복 작업 안정성이 Claude Code 쪽이 한 수 위다. 대형 리팩토링이나 새 기능 추가엔 Claude Code가 낫다.

### 코드 변환 작업

Java 8→17, .NET Framework → .NET 이런 업그레이드 작업은 Q Transform이 압도적이다. Claude Code도 하려면 할 수 있지만, Q는 AWS 내부적으로 대규모 코드베이스를 변환한 경험을 학습 데이터로 써서 실패율이 낮다. 레거시 마이그레이션 프로젝트엔 Q가 답이다.

### 기업 환경

- **데이터 격리 규제가 심한 곳**: AWS 계정 내 처리를 보장받을 수 있는 Q가 선택지가 된다. Copilot Enterprise도 비슷한 보장을 하지만, AWS 계정 거버넌스 안에서 감사 로그를 통합 관리하려면 Q가 편하다.
- **이미 AWS 계정 비용 관리 체계가 있는 곳**: Q는 AWS 청구에 포함되어 추가 벤더 관리가 불필요하다. 기업 구매팀 입장에선 이게 장점이다.

### 한계

- **생태계가 좁다**: VS Code 기반의 Cursor, Windsurf, Cline 같은 도구가 만든 플러그인 생태계를 Q는 못 따라간다. MCP 지원이 들어오면서 격차가 줄긴 했지만 도구 수 자체가 적다.
- **IDE 외 환경이 빈약**: 웹 IDE, JetBrains Gateway, 원격 개발 컨테이너 같은 환경에서 경험이 떨어진다. Cursor처럼 별도 앱으로 집중적인 경험을 제공하는 것도 아니다.
- **모델 선택 불가**: Cursor는 Claude, GPT, Gemini를 마음대로 바꿔 쓸 수 있는데, Q는 내부 모델 고정이다. 사용자가 "이번엔 최신 Claude로 돌려보고 싶다"가 안 된다.
- **한국어 품질**: Claude나 GPT 계열 대비 한국어 응답 품질이 살짝 떨어진다. 설계 문서나 주석 생성을 한국어로 뽑으면 어색한 번역투가 섞인다.

## 언제 Q를 고를까

현실적인 선택 기준을 정리하면 이렇다.

- **AWS 네이티브 팀**: EKS, Lambda, Step Functions 중심으로 일하는 팀이면 Q를 기본으로 깔고, 복잡한 기능 구현은 Claude Code를 따로 쓰는 하이브리드가 유력하다.
- **레거시 Java/.NET 마이그레이션 프로젝트**: Q Transform 목적으로만이라도 도입 가치가 있다. 이걸 위해 몇 달만 Pro를 결제하는 팀도 많다.
- **규제 산업(금융·공공·의료)**: 데이터 경로 통제가 중요한 곳에선 Q가 현실적인 선택지다. 다만 서울 리전 기능 지원 상태를 반드시 확인해야 한다.
- **사내 지식 검색이 필요한 비개발 부서**: Q Business가 의외로 잘 맞는다. Slack 봇처럼 가져다 붙이는 데 코드 거의 없이 가능하다.
- **범용 개발 팀, 프론트엔드 중심 팀**: Copilot이나 Cursor가 더 잘 맞는다. Q는 AWS 쪽 맥락이 없으면 강점이 희석된다.

도입 전 파일럿으로 2~4주 써보고 팀의 실제 사용 패턴에 맞는지 보는 게 제일 확실하다. Free 플랜으로도 감은 잡힌다.
