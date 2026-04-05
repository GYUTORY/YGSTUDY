---
title: MCP (Model Context Protocol) 핵심 개념
tags: [ai, mcp, model-context-protocol, anthropic, open-standard]
updated: 2026-04-05
---

# MCP (Model Context Protocol)

## 1. MCP란

**MCP(Model Context Protocol)**는 Anthropic이 2024년 11월에 발표한 **오픈 표준 프로토콜**로, AI 모델과 외부 도구/데이터 소스를 표준화된 방식으로 연결한다. 흔히 **"AI의 USB-C"**라고 불린다.

2025년 12월, Anthropic은 MCP를 Linux Foundation 산하 **Agentic AI Foundation(AAIF)**에 기부하여 업계 공통 표준으로 발전시켰다.

### 1.1 왜 MCP가 필요한가

```
MCP 이전:
  Claude Code ←→ 커스텀 연동 ←→ PostgreSQL
  Cursor     ←→ 별도 연동    ←→ PostgreSQL
  Codex      ←→ 또 다른 연동 ←→ PostgreSQL

MCP 이후:
  Claude Code ←→ MCP ←→ PostgreSQL MCP Server
  Cursor     ←→ MCP ←→ (같은 서버 재사용)
  Codex      ←→ MCP ←→ (같은 서버 재사용)
```

**한번 만든 MCP 서버를 모든 AI 도구에서 재사용** 가능.

### 1.2 지원 도구

| 도구 | MCP 지원 |
|------|---------|
| Claude Code | 네이티브 지원 |
| Cursor | 네이티브 지원 |
| OpenAI Codex | 지원 |
| VS Code | 확장 필요 |
| Windsurf | 지원 |
| Gemini CLI | 지원 |
| GitHub Copilot | 지원 |

---

## 2. 아키텍처

### 2.1 구성 요소

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│   Host   │────▶│  Client  │────▶│  MCP Server  │
│ (AI 도구) │     │ (연결 관리)│     │ (도구 제공)    │
└──────────┘     └──────────┘     └──────────────┘
  Claude Code      내장 클라이언트     PostgreSQL 서버
  Cursor           자동 관리          GitHub 서버
  VS Code                           Slack 서버
```

| 구성 요소 | 역할 | 예시 |
|-----------|------|------|
| **Host** | MCP를 사용하는 AI 도구 | Claude Code, Cursor |
| **Client** | Host와 Server 사이의 인터페이스 | 내장 (자동 관리) |
| **Server** | 도구와 데이터를 AI에 노출 | DB 서버, API 서버 |

### 2.2 통신 프로토콜

**JSON-RPC 2.0** 기반이며, 전송 방식은 세 가지다.

### 2.3 전송 방식 (Transport)

#### stdio (표준 입출력)

Host가 MCP 서버를 **자식 프로세스로 직접 실행**하고, stdin/stdout으로 JSON-RPC 메시지를 주고받는다.

```
Host ──fork──▶ MCP Server 프로세스
     stdin ◀──────────▶ stdout
```

- 로컬에서만 동작한다. 네트워크를 거치지 않으므로 인증 설정이 필요 없다.
- Claude Code, Cursor 등에서 `command`/`args`로 설정하면 자동으로 이 방식을 쓴다.
- 서버 프로세스가 죽으면 연결도 끊긴다. Host가 알아서 재시작하는 경우가 많다.
- 하나의 Host에 하나의 서버 인스턴스가 붙는 1:1 구조다.

**언제 쓰는가**: 로컬 개발 환경에서 자기만 쓸 MCP 서버를 띄울 때. 대부분의 경우 이걸로 충분하다.

#### SSE (Server-Sent Events) — deprecated

HTTP 기반 전송 방식으로, 2024년 사양에 포함됐지만 **2025-03-26 사양 개정에서 deprecated**됐다.

- 클라이언트 → 서버: HTTP POST 요청
- 서버 → 클라이언트: SSE 스트림으로 응답

기존에 SSE로 만든 서버가 있다면 동작은 하지만, 신규 개발에는 Streamable HTTP를 쓴다.

#### Streamable HTTP

SSE를 대체하는 원격 전송 방식이다. 단일 HTTP 엔드포인트(`/mcp`)로 요청과 응답을 모두 처리한다.

```
Client ──POST /mcp──▶ Server
       ◀── 200 OK (JSON-RPC 응답) ──
       또는
       ◀── SSE 스트림 (여러 응답을 스트리밍) ──
```

- 서버가 응답을 한번에 줄 수도 있고, SSE 스트림으로 줄 수도 있다. 클라이언트는 둘 다 처리해야 한다.
- 여러 클라이언트가 하나의 서버에 연결할 수 있다. 팀 공용 MCP 서버를 띄울 때 필요하다.
- 원격 서버이므로 인증이 필요하다 (OAuth 2.1, 8.3절 참고).
- Stateless 모드와 Stateful 모드 둘 다 지원한다. 세션이 필요하면 `Mcp-Session-Id` 헤더를 쓴다.

**언제 쓰는가**: 원격에 MCP 서버를 배포해서 여러 사람이 공유하거나, 클라우드 환경에서 운영할 때.

#### 전송 방식 선택 기준

| 기준 | stdio | Streamable HTTP |
|------|-------|-----------------|
| 배포 위치 | 로컬만 | 로컬/원격 둘 다 |
| 클라이언트 수 | 1:1 | 다수 가능 |
| 인증 | 불필요 | OAuth 2.1 필요 (원격) |
| 설정 복잡도 | 낮음 | 높음 |
| 적합한 상황 | 개인 개발 환경 | 팀 공유, 프로덕션 배포 |

로컬에서 혼자 쓸 거면 stdio로 시작하고, 팀에 공유할 필요가 생기면 Streamable HTTP로 전환한다.

---

## 3. 핵심 프리미티브

MCP 서버가 제공하는 네 가지 프리미티브가 있다.

### 3.1 Tools (도구)

AI가 **실행할 수 있는 함수/액션**이다. API 호출, DB 쿼리, 파일 작업 등.

```typescript
// TypeScript SDK
server.tool(
  "query_database",
  "SQL 쿼리를 실행하고 결과를 반환한다",
  { query: { type: "string", description: "실행할 SQL 쿼리" } },
  async ({ query }) => {
    const result = await db.execute(query);
    return {
      content: [{ type: "text", text: JSON.stringify(result) }],
    };
  }
);
```

```python
# Python SDK
@server.tool()
async def query_database(query: str) -> str:
    """SQL 쿼리를 실행하고 결과를 반환한다"""
    result = await db.execute(query)
    return json.dumps(result)
```

AI가 `tools/list`로 사용 가능한 도구 목록을 조회하고, `tools/call`로 특정 도구를 실행한다.

### 3.2 Resources (리소스)

AI에게 **컨텍스트 정보를 제공하는 데이터 소스**이다. 파일, DB 스키마, API 문서 등. Tool과 달리 **읽기 전용**이고, AI가 참고 자료로 사용한다.

```typescript
// TypeScript SDK — 정적 리소스 등록
server.resource(
  "db-schema",                        // 리소스 식별자
  "db://mydb/schema",                 // URI
  { mimeType: "application/json" },   // 메타데이터
  async () => {
    const schema = await db.getSchema();
    return {
      contents: [{
        uri: "db://mydb/schema",
        mimeType: "application/json",
        text: JSON.stringify(schema),
      }],
    };
  }
);
```

```python
# Python SDK — 리소스 등록
@server.resource("db://mydb/schema")
async def get_schema() -> str:
    """데이터베이스 스키마 정보"""
    schema = await db.get_schema()
    return json.dumps(schema)
```

동적으로 URI 패턴을 만들 수도 있다. 예를 들어 `db://mydb/tables/{table_name}/schema` 같은 패턴으로 등록하면, AI가 특정 테이블 스키마만 조회할 수 있다.

```typescript
// 리소스 템플릿 — URI 패턴으로 동적 리소스 제공
server.resource(
  "table-schema",
  new ResourceTemplate("db://mydb/tables/{tableName}/schema", {
    list: async () => {
      const tables = await db.listTables();
      return tables.map(t => ({
        uri: `db://mydb/tables/${t}/schema`,
        name: `${t} 스키마`,
      }));
    },
  }),
  async (uri, { tableName }) => {
    const schema = await db.getTableSchema(tableName);
    return {
      contents: [{
        uri: uri.href,
        mimeType: "application/json",
        text: JSON.stringify(schema),
      }],
    };
  }
);
```

### 3.3 Prompts (프롬프트)

AI와의 상호작용을 표준화하는 **재사용 가능한 프롬프트 템플릿**이다. 클라이언트가 `prompts/list`로 목록을 조회하고, `prompts/get`으로 특정 프롬프트를 가져온다.

```typescript
// TypeScript SDK — 프롬프트 등록
server.prompt(
  "code_review",
  "코드 리뷰를 요청한다",
  { code: { type: "string", description: "리뷰할 코드" },
    language: { type: "string", description: "프로그래밍 언어" } },
  ({ code, language }) => ({
    messages: [{
      role: "user",
      content: {
        type: "text",
        text: `다음 ${language} 코드를 리뷰해줘. 버그, 성능 문제, 개선점을 찾아줘.\n\n${code}`,
      },
    }],
  })
);
```

```python
# Python SDK — 프롬프트 등록
@server.prompt()
async def code_review(code: str, language: str) -> str:
    """코드 리뷰를 요청한다"""
    return f"다음 {language} 코드를 리뷰해줘. 버그, 성능 문제, 개선점을 찾아줘.\n\n{code}"
```

Prompts는 사실 많이 쓰이지 않는다. 대부분의 클라이언트가 Tool 중심으로 동작하고, 프롬프트 선택 UI를 제공하는 클라이언트가 아직 적다. 팀 내에서 반복되는 작업 패턴을 표준화할 때 쓸 수 있다.

### 3.4 Sampling (샘플링)

**서버가 클라이언트를 통해 LLM을 호출하는 기능**이다. 일반적인 MCP 흐름은 클라이언트(AI)가 서버의 tool을 호출하는 방향인데, Sampling은 그 반대다. 서버가 작업 중에 LLM의 판단이 필요할 때 클라이언트에게 "이 내용으로 LLM 호출 좀 해줘"라고 요청한다.

```
일반 흐름:   Client(AI) ──tool 호출──▶ Server
Sampling:   Server ──sampling/createMessage──▶ Client ──LLM 호출──▶ AI 모델
```

서버가 직접 AI API를 호출하지 않는다는 게 핵심이다. 서버는 LLM에 접근할 수 없고, 클라이언트가 중간에서 LLM 호출을 대행한다. 이 구조 덕분에 서버에 API 키를 넣을 필요가 없고, 클라이언트가 요청 내용을 검토하거나 사용자에게 승인을 받을 수 있다.

```typescript
// 서버에서 Sampling 요청을 보내는 예시
const result = await server.server.createMessage({
  messages: [
    {
      role: "user",
      content: {
        type: "text",
        text: "다음 코드 변경사항을 요약해줘:\n" + diffContent,
      },
    },
  ],
  maxTokens: 500,
});

// result.content에 LLM 응답이 담겨 있다
const summary = result.content.text;
```

실제로 쓰이는 경우:

- **코드 분석 서버**: Git diff를 읽은 다음 LLM에게 변경 요약을 요청하고, 그 결과를 정리해서 반환한다.
- **문서 생성 서버**: DB 스키마를 읽어서 LLM에게 문서 초안 작성을 맡기고, 결과를 파일로 저장한다.
- **다단계 추론**: tool 실행 중간에 LLM 판단이 필요한 경우. 예를 들어 로그 분석 서버가 로그를 수집한 뒤 "이 로그에서 에러 패턴을 찾아줘"라고 LLM에 요청한다.

주의할 점이 있다. 모든 클라이언트가 Sampling을 지원하는 건 아니다. 2025년 기준으로 Sampling을 지원하는 클라이언트가 많지 않다. 서버를 만들 때 Sampling이 실패하는 경우의 폴백 로직을 넣어두는 게 좋다.

---

## 4. Roots, Elicitation, Notifications

핵심 프리미티브(Tools, Resources, Prompts, Sampling) 외에 클라이언트-서버 간 상호작용을 보조하는 메커니즘이 세 가지 더 있다.

### 4.1 Roots (루트)

**클라이언트가 서버에게 작업 범위를 알려주는 기능**이다. 클라이언트가 "내가 지금 이 디렉토리에서 작업하고 있어"라고 서버에 URI 목록을 전달한다.

```
Client ──roots/list 응답──▶ Server
  "file:///home/user/project-a"
  "file:///home/user/shared-lib"
```

서버는 이 정보를 받아서 **자기가 작업해야 할 범위를 파악**한다. 파일 시스템 서버라면 해당 디렉토리만 인덱싱하고, Git 서버라면 해당 레포만 관리한다.

Roots는 강제 제한이 아니다. 서버가 Roots 밖의 파일에 접근하는 걸 프로토콜 수준에서 막지는 않는다. 서버가 스스로 범위를 좁히는 데 참고하는 힌트에 가깝다. 하지만 잘 만든 서버라면 Roots 범위를 벗어나는 작업은 하지 않도록 구현해야 한다.

클라이언트가 작업 디렉토리를 변경하면 `notifications/roots/list_changed` 알림을 보낸다. 서버는 이 알림을 받으면 `roots/list`를 다시 호출해서 새 범위를 확인한다.

```typescript
// 서버에서 Roots 변경 알림을 처리하는 예시
server.setNotificationHandler(
  "notifications/roots/list_changed",
  async () => {
    const { roots } = await server.listRoots();
    // 새로운 작업 범위로 인덱스를 갱신한다
    await reindexDirectories(roots.map(r => r.uri));
  }
);
```

### 4.2 Elicitation (사용자 입력 요청)

**서버가 사용자에게 직접 입력을 요청하는 기능**이다. tool 실행 중에 서버가 추가 정보를 사용자에게 물어봐야 할 때 쓴다.

```
Server ──elicitation/create──▶ Client ──UI 표시──▶ 사용자
사용자 ──입력──▶ Client ──응답──▶ Server
```

예를 들어 DB 마이그레이션 서버가 있다고 하자. 마이그레이션 tool을 실행하는 중에 "이 테이블을 삭제해도 되는지"를 사용자에게 확인받아야 하는 상황이 생긴다. 이때 Elicitation으로 사용자에게 직접 질문을 던진다.

```typescript
// 서버에서 사용자에게 확인을 요청하는 예시
const response = await server.elicit({
  message: "users 테이블을 삭제합니다. 계속할까요?",
  requestedSchema: {
    type: "object",
    properties: {
      confirm: {
        type: "boolean",
        description: "삭제를 승인합니다",
      },
    },
    required: ["confirm"],
  },
});

if (response.action === "accept" && response.content?.confirm) {
  await db.dropTable("users");
} else {
  return { content: [{ type: "text", text: "사용자가 취소했다." }] };
}
```

Elicitation 응답에는 세 가지 상태가 있다.

| action | 의미 |
|--------|------|
| `accept` | 사용자가 입력을 제출했다. `content`에 값이 들어 있다. |
| `decline` | 사용자가 거부했다. |
| `cancel` | 사용자가 입력 창을 닫거나 취소했다. |

`requestedSchema`는 JSON Schema로 입력 형식을 정의한다. 문자열, 숫자, boolean, enum 등을 조합할 수 있다. 클라이언트가 이 스키마를 보고 적절한 UI(텍스트 입력, 드롭다운, 체크박스 등)를 자동으로 렌더링한다.

Sampling과 마찬가지로 모든 클라이언트가 Elicitation을 지원하지는 않는다. 서버에서 Elicitation 요청을 보냈는데 클라이언트가 지원하지 않으면 에러가 돌아온다.

### 4.3 Notifications (알림)

**클라이언트와 서버가 상대방에게 상태 변경을 알리는 단방향 메시지**다. JSON-RPC의 notification(응답 없는 메시지)으로 구현되어 있다. 요청-응답 패턴이 아니라 "보내고 끝"이다.

주요 알림 종류:

| 알림 | 발신 | 의미 |
|------|------|------|
| `notifications/tools/list_changed` | 서버 → 클라이언트 | 서버의 tool 목록이 변경됐다 |
| `notifications/resources/list_changed` | 서버 → 클라이언트 | 서버의 resource 목록이 변경됐다 |
| `notifications/resources/updated` | 서버 → 클라이언트 | 특정 resource의 내용이 변경됐다 |
| `notifications/prompts/list_changed` | 서버 → 클라이언트 | 서버의 prompt 목록이 변경됐다 |
| `notifications/roots/list_changed` | 클라이언트 → 서버 | 클라이언트의 작업 범위(Roots)가 변경됐다 |
| `notifications/progress` | 양방향 | 장시간 작업의 진행 상황 보고 |
| `notifications/cancelled` | 양방향 | 진행 중인 요청을 취소한다 |

실무에서 자주 쓰는 패턴은 **tool 목록 동적 변경**이다. 서버가 런타임에 tool을 추가하거나 제거한 뒤 `notifications/tools/list_changed`를 보내면, 클라이언트가 `tools/list`를 다시 호출해서 최신 목록을 가져간다.

```typescript
// 서버에서 tool을 동적으로 추가하고 알림을 보내는 예시
server.tool("new_feature", "새 기능", {}, async () => {
  return { content: [{ type: "text", text: "done" }] };
});

// 클라이언트에게 tool 목록이 바뀌었다고 알린다
await server.server.sendToolListChanged();
```

`notifications/progress`는 오래 걸리는 작업에서 유용하다. tool 실행 중에 진행률을 보내면 클라이언트가 사용자에게 프로그레스 바 같은 걸 보여줄 수 있다.

```typescript
server.tool("import_data", "대량 데이터 가져오기", { file: { type: "string" } },
  async ({ file }, { sendProgress }) => {
    const lines = await readLines(file);
    for (let i = 0; i < lines.length; i++) {
      await processLine(lines[i]);
      // 진행 상황을 클라이언트에 알린다
      await sendProgress(i + 1, lines.length);
    }
    return { content: [{ type: "text", text: `${lines.length}건 처리 완료` }] };
  }
);
```

---

## 5. MCP 서버 만들기

### 5.1 TypeScript로 만들기

```bash
npm install @modelcontextprotocol/sdk
```

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({
  name: "my-server",
  version: "1.0.0",
});

// 도구 등록
server.tool(
  "get_user",
  "사용자 정보를 조회한다",
  { userId: { type: "string", description: "사용자 ID" } },
  async ({ userId }) => {
    const user = await db.findUser(userId);
    return {
      content: [{ type: "text", text: JSON.stringify(user) }],
    };
  }
);

// 서버 시작
const transport = new StdioServerTransport();
await server.connect(transport);
```

### 5.2 Python으로 만들기

```bash
pip install mcp
```

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("my-server")

@server.tool()
async def get_user(user_id: str) -> str:
    """사용자 정보를 조회한다"""
    user = await db.find_user(user_id)
    return json.dumps(user)

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)
```

### 5.3 MCP 서버 연결 설정

```json
// Claude Code: .claude/settings.json
// Cursor: .cursor/mcp.json
// Codex: .codex/config.toml의 [mcp_servers] 섹션
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["./mcp-server/index.js"],
      "env": {
        "DB_URL": "postgresql://localhost:5432/mydb"
      }
    }
  }
}
```

원격 서버에 연결할 때는 `command` 대신 `url`을 쓴다.

```json
{
  "mcpServers": {
    "remote-server": {
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_TOKEN}"
      }
    }
  }
}
```

---

## 6. MCP 서버 디버깅

### 6.1 MCP Inspector

MCP Inspector는 공식 디버깅 도구다. 브라우저에서 MCP 서버에 연결해서 tool 목록 확인, tool 호출 테스트, 요청/응답 로그 확인을 할 수 있다.

```bash
npx @modelcontextprotocol/inspector
```

실행하면 브라우저가 열린다. 왼쪽에서 서버 실행 커맨드를 입력하고 Connect를 누르면 된다. stdio 서버는 커맨드(`node index.js`)를 입력하고, 원격 서버는 URL을 입력한다.

Inspector에서 확인할 수 있는 것:

- **Tools 탭**: 등록된 tool 목록, 각 tool의 inputSchema, 직접 파라미터를 넣어서 호출 테스트
- **Resources 탭**: 등록된 resource 목록, URI로 직접 조회
- **Prompts 탭**: 등록된 prompt 목록, 파라미터를 넣어서 생성 결과 확인
- **Notifications**: 서버에서 보내는 알림 메시지 실시간 확인

### 6.2 로그 확인

stdio 방식에서 서버의 `console.log`는 stdout으로 나가기 때문에 **JSON-RPC 메시지와 섞여서 프로토콜이 깨진다**. 디버그 로그는 반드시 stderr로 보내야 한다.

```typescript
// stdout은 JSON-RPC 통신에 쓰이므로 절대 console.log 쓰지 않는다
console.error("[DEBUG] tool called:", toolName);  // stderr로 출력
```

```python
import sys
print(f"[DEBUG] tool called: {tool_name}", file=sys.stderr)
```

Claude Code에서 MCP 서버 로그를 보려면:

```bash
# Claude Code의 MCP 로그 파일 위치
cat ~/.claude/logs/mcp*.log
```

### 6.3 연결이 안 되는 경우

MCP 서버 연결 문제의 대부분은 몇 가지 원인으로 좁혀진다.

**서버 프로세스가 실행 자체가 안 되는 경우**

```bash
# 설정에 적은 커맨드를 직접 터미널에서 실행해본다
node ./mcp-server/index.js
# 에러가 나면 그게 원인이다. 대부분 경로 오류, 의존성 미설치, Node 버전 문제.
```

**실행은 되는데 클라이언트가 연결을 못 하는 경우**

- `command` 경로가 상대 경로인 경우: Host의 작업 디렉토리 기준인지 확인한다. 절대 경로로 바꿔보는 게 빠르다.
- `env`에 필요한 환경 변수가 빠져 있는 경우: 서버가 시작 직후 환경 변수를 읽다가 죽는 경우가 많다.
- `npx`로 실행하는 서버: `npx` 캐시 문제로 실행이 안 되는 경우가 있다. `npx --yes @package/name`으로 명시하거나, 글로벌 설치 후 직접 경로를 지정한다.

**Inspector로 확인하는 방법**

```bash
# Inspector에서 같은 커맨드로 서버를 띄워본다
npx @modelcontextprotocol/inspector
# 여기서 연결이 되면 클라이언트 설정 문제, 안 되면 서버 자체 문제다.
```

---

## 7. MCP 서버 테스트

MCP 서버를 만들고 나면 tool 호출이 제대로 동작하는지 자동화된 테스트가 필요하다.

### 7.1 인메모리 전송으로 단위 테스트

실제 stdio나 HTTP 연결 없이 서버를 테스트할 수 있다. SDK에서 제공하는 인메모리 전송(InMemoryTransport)을 쓰면 된다.

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { describe, it, expect } from "vitest";

describe("my-mcp-server", () => {
  let client: Client;
  let server: McpServer;

  beforeEach(async () => {
    // 서버 생성 및 tool 등록
    server = new McpServer({ name: "test-server", version: "1.0.0" });
    server.tool(
      "add",
      "두 수를 더한다",
      { a: { type: "number" }, b: { type: "number" } },
      async ({ a, b }) => ({
        content: [{ type: "text", text: String(a + b) }],
      })
    );

    // 인메모리 전송으로 클라이언트-서버 연결
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await server.connect(serverTransport);

    client = new Client({ name: "test-client", version: "1.0.0" });
    await client.connect(clientTransport);
  });

  it("tool 목록을 조회한다", async () => {
    const { tools } = await client.listTools();
    expect(tools).toHaveLength(1);
    expect(tools[0].name).toBe("add");
  });

  it("add tool을 호출한다", async () => {
    const result = await client.callTool({ name: "add", arguments: { a: 2, b: 3 } });
    expect(result.content[0].text).toBe("5");
  });
});
```

```python
import pytest
from mcp import ClientSession, types
from mcp.server import Server
from mcp.shared.memory import create_connected_server_and_client_session

@pytest.fixture
async def client_session():
    server = Server("test-server")

    @server.tool()
    async def add(a: int, b: int) -> str:
        """두 수를 더한다"""
        return str(a + b)

    async with create_connected_server_and_client_session(server) as client:
        yield client

@pytest.mark.anyio
async def test_list_tools(client_session: ClientSession):
    result = await client_session.list_tools()
    assert len(result.tools) == 1
    assert result.tools[0].name == "add"

@pytest.mark.anyio
async def test_call_tool(client_session: ClientSession):
    result = await client_session.call_tool("add", {"a": 2, "b": 3})
    assert result.content[0].text == "5"
```

### 7.2 테스트할 때 주의할 점

- tool 핸들러에서 외부 의존성(DB, API 등)이 있으면 테스트용 mock이나 fixture를 따로 만들어야 한다. 서버 생성 시 의존성을 주입할 수 있게 구조를 잡아두면 테스트가 편하다.
- tool 호출 결과의 `isError` 필드로 에러 케이스도 테스트한다. 잘못된 파라미터를 넣었을 때 서버가 죽지 않고 에러 응답을 돌려주는지 확인해야 한다.
- resource와 prompt도 같은 방식으로 테스트한다. `client.listResources()`, `client.readResource()`, `client.listPrompts()`, `client.getPrompt()` 등을 쓴다.

---

## 8. 프로덕션 배포

MCP 서버를 로컬에서 돌리는 것과 프로덕션에 배포하는 건 다른 문제다. 실제 운영 환경에서 부딪히는 문제들을 정리한다.

### 8.1 세션 관리

Streamable HTTP로 배포할 때 세션 관리가 가장 까다로운 부분이다.

**Stateless vs Stateful**

Stateless 모드에서는 서버가 `Mcp-Session-Id` 헤더를 발행하지 않는다. 매 요청이 독립적이고, 서버가 재시작되어도 클라이언트에 영향이 없다. 대신 tool 실행 중에 중간 상태를 유지할 수 없다.

Stateful 모드에서는 서버가 초기화 시 `Mcp-Session-Id`를 발행하고, 클라이언트가 이후 모든 요청에 이 헤더를 포함한다. 서버가 해당 세션의 상태를 메모리에 유지한다.

```typescript
// Stateful 서버에서 세션별 상태 관리
const sessions = new Map<string, SessionState>();

// 세션 초기화 시
server.onInitialize((sessionId) => {
  sessions.set(sessionId, { connectedAt: Date.now(), context: {} });
});

// 세션 종료 시 정리
server.onClose((sessionId) => {
  sessions.delete(sessionId);
});
```

여기서 문제가 생긴다. 서버를 여러 인스턴스로 스케일 아웃하면 세션 상태가 인스턴스마다 다르다. 클라이언트의 요청이 다른 인스턴스로 가면 세션을 찾을 수 없다. 해결 방법은 두 가지다.

- **sticky session**: 로드 밸런서에서 같은 세션의 요청을 같은 인스턴스로 라우팅한다. 간단하지만 인스턴스가 죽으면 세션도 날아간다.
- **외부 세션 저장소**: Redis 같은 곳에 세션 상태를 저장한다. 인스턴스가 죽어도 세션이 유지되지만 구현이 복잡하다.

가능하면 Stateless로 설계하는 게 운영이 편하다. tool 하나 호출하는 데 세션 상태가 필요 없는 경우가 대부분이다.

### 8.2 서버 재시작 처리

stdio 방식에서는 Host가 서버 프로세스를 직접 관리하므로, 서버가 죽으면 Host가 재시작한다. Claude Code 같은 클라이언트는 자동 재시작을 해준다.

Streamable HTTP에서는 상황이 다르다. 서버가 재시작되면:

1. 기존 SSE 연결이 끊긴다.
2. Stateful 모드에서는 세션 상태가 사라진다.
3. 클라이언트가 `Mcp-Session-Id`로 요청을 보내면 서버가 모른다고 응답한다.

이때 서버는 `404 Not Found`를 반환하고, 클라이언트는 새로 초기화(`initialize` 요청)를 해야 한다.

```typescript
// Streamable HTTP 서버에서 세션 검증
app.post("/mcp", (req, res) => {
  const sessionId = req.headers["mcp-session-id"];

  if (sessionId && !sessions.has(sessionId)) {
    // 모르는 세션이다. 클라이언트에게 재초기화를 요구한다.
    return res.status(404).json({
      jsonrpc: "2.0",
      error: { code: -32000, message: "Session not found" },
    });
  }

  // 정상 처리
  handleRequest(req, res);
});
```

클라이언트 구현에서 중요한 건 **재초기화 후 tool 목록을 다시 가져가는 것**이다. 서버가 업데이트되면서 tool이 변경됐을 수 있다.

### 8.3 에러 핸들링 패턴

MCP 서버의 tool 핸들러에서 에러가 나면 서버 프로세스가 죽으면 안 된다. JSON-RPC 에러 응답을 돌려줘야 한다.

**tool 핸들러 내부 에러**

tool 실행 중 예외가 발생하면 `isError: true`와 함께 에러 메시지를 반환한다. 서버 프로세스는 살아 있어야 한다.

```typescript
server.tool("query_database", "SQL 쿼리 실행", { query: { type: "string" } },
  async ({ query }) => {
    try {
      const result = await db.execute(query);
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
      };
    } catch (err) {
      // 서버가 죽지 않고 에러를 응답으로 돌려준다
      return {
        isError: true,
        content: [{ type: "text", text: `쿼리 실행 실패: ${err.message}` }],
      };
    }
  }
);
```

```python
@server.tool()
async def query_database(query: str) -> str:
    """SQL 쿼리 실행"""
    try:
        result = await db.execute(query)
        return json.dumps(result)
    except Exception as e:
        # Python SDK에서는 McpError를 raise하면 isError 응답이 된다
        raise McpError(f"쿼리 실행 실패: {e}")
```

**타임아웃 처리**

tool이 외부 API를 호출하는데 응답이 안 오면 클라이언트가 무한 대기에 빠진다. tool 핸들러에 타임아웃을 걸어야 한다.

```typescript
server.tool("call_external_api", "외부 API 호출", { url: { type: "string" } },
  async ({ url }) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30_000); // 30초

    try {
      const res = await fetch(url, { signal: controller.signal });
      const data = await res.json();
      return { content: [{ type: "text", text: JSON.stringify(data) }] };
    } catch (err) {
      if (err.name === "AbortError") {
        return {
          isError: true,
          content: [{ type: "text", text: "API 호출이 30초 안에 응답하지 않았다." }],
        };
      }
      return {
        isError: true,
        content: [{ type: "text", text: `API 호출 실패: ${err.message}` }],
      };
    } finally {
      clearTimeout(timeout);
    }
  }
);
```

**프로세스 수준 에러 방어**

tool 핸들러에서 잡지 못한 예외가 프로세스를 죽이는 걸 막아야 한다.

```typescript
// 잡지 못한 예외로 프로세스가 죽는 걸 방지
process.on("uncaughtException", (err) => {
  console.error("[FATAL] uncaught exception:", err);
  // 로그만 남기고 프로세스는 유지한다.
  // 다만 상태가 오염됐을 수 있으므로 graceful restart를 고려한다.
});

process.on("unhandledRejection", (reason) => {
  console.error("[FATAL] unhandled rejection:", reason);
});
```

```python
import asyncio
import sys

def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    print(f"[FATAL] unhandled exception: {msg}", file=sys.stderr)

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)
```

### 8.4 배포 시 흔히 겪는 문제

**컨테이너 환경에서 stdio 서버를 쓸 수 없다**

stdio는 Host가 서버를 자식 프로세스로 실행하는 방식이다. 서버가 별도 컨테이너에 있으면 fork가 안 되므로 Streamable HTTP를 써야 한다.

**헬스체크**

Streamable HTTP 서버를 로드 밸런서 뒤에 두면 헬스체크 엔드포인트가 필요하다. MCP 사양에 헬스체크가 정의되어 있지 않으므로 별도로 만들어야 한다.

```typescript
app.get("/health", (req, res) => {
  // DB 연결 등 의존성 상태도 확인한다
  const dbOk = db.isConnected();
  if (dbOk) {
    res.status(200).json({ status: "ok" });
  } else {
    res.status(503).json({ status: "unhealthy", reason: "db disconnected" });
  }
});
```

**Graceful shutdown**

서버가 종료될 때 진행 중인 tool 호출이 있으면 완료를 기다려야 한다. SIGTERM을 받으면 새 요청을 거부하고, 기존 요청이 끝나면 종료한다.

```typescript
let shuttingDown = false;

process.on("SIGTERM", async () => {
  shuttingDown = true;
  console.error("[INFO] shutting down gracefully...");

  // 진행 중인 요청이 끝날 때까지 대기 (최대 30초)
  await waitForPendingRequests(30_000);
  process.exit(0);
});

app.post("/mcp", (req, res) => {
  if (shuttingDown) {
    return res.status(503).json({ error: "server is shutting down" });
  }
  handleRequest(req, res);
});
```

---

## 9. 주요 MCP 서버

### 9.1 공식 서버 (Anthropic)

| 서버 | 용도 |
|------|------|
| **PostgreSQL** | DB 쿼리, 스키마 조회 |
| **GitHub** | 이슈, PR, 레포 관리 |
| **Git** | 로컬 Git 작업 |
| **Slack** | 메시지 전송, 채널 관리 |
| **Google Drive** | 문서 읽기/검색 |
| **Puppeteer** | 웹 브라우저 자동화 |

### 9.2 커뮤니티 서버

| 서버 | 용도 |
|------|------|
| **Brave Search** | 웹 검색 |
| **Supabase** | Edge Functions, DB |
| **Terraform** | IaC 관리 |
| **Kubernetes** | K8s 클러스터 관리 |
| **Prometheus** | 모니터링 메트릭 |
| **PagerDuty** | 인시던트 관리 |
| **Zapier** | 수천 개 앱 연동 |

GitHub의 **awesome-mcp-servers** 레포에서 전체 목록을 확인할 수 있다.

---

## 10. 보안 고려사항

### 10.1 주요 보안 위험

| 위험 | 설명 | 대응 |
|------|------|------|
| **프롬프트 인젝션** | 악의적 지시가 도구 메타데이터에 숨겨짐 | 신뢰할 수 있는 서버만 사용 |
| **도구 포이즈닝** | MCP 도구 설명에 악성 명령 삽입 | 서버 소스 코드 검증 |
| **자격 증명 노출** | 잘못된 설정으로 API 키 유출 | 환경 변수로 시크릿 관리 |
| **권한 상승** | 에이전트가 과도한 권한 획득 | 최소 권한 원칙 적용 |
| **임의 코드 실행** | 신뢰할 수 없는 서버가 악성 코드 실행 | 공식/검증된 서버만 설치 |

### 10.2 보안 설정 시 지켜야 할 것

- MCP 서버는 **공식 또는 검증된 소스**에서만 설치한다
- 시크릿은 반드시 **환경 변수**로 관리한다 (설정 파일에 하드코딩 금지)
- **최소 권한 원칙**: 필요한 도구만 활성화한다
- 프로덕션 환경에서는 **네트워크 격리**를 적용한다
- 연결된 MCP 서버를 정기적으로 점검한다

### 10.3 원격 MCP 서버 인증 (OAuth 2.1)

원격으로 MCP 서버를 배포하면 아무나 접근할 수 있으므로 인증이 필요하다. MCP 사양은 **OAuth 2.1**을 표준 인증 방식으로 정의한다.

#### 인증 흐름

```
1) 클라이언트가 MCP 서버에 접속 시도
2) 서버가 401 Unauthorized 응답
3) 클라이언트가 서버의 /.well-known/oauth-authorization-server에서 메타데이터 조회
4) 동적 클라이언트 등록 (RFC 7591) — 클라이언트가 자동으로 client_id를 발급받음
5) Authorization Code + PKCE 흐름으로 사용자 인증
6) 발급받은 access_token을 Authorization 헤더에 담아 요청
```

구체적으로 보면:

**1단계 — 서버 메타데이터 조회**

클라이언트가 `GET /.well-known/oauth-authorization-server`를 호출해서 authorization endpoint, token endpoint, 지원하는 scope 등을 가져온다.

**2단계 — 동적 클라이언트 등록**

MCP 클라이언트는 사전에 client_id를 알 수 없으므로, RFC 7591 동적 클라이언트 등록을 쓴다. 서버의 registration endpoint에 POST 요청을 보내면 client_id를 발급받는다.

**3단계 — Authorization Code + PKCE**

OAuth 2.1은 PKCE가 필수다. 클라이언트가 code_verifier를 생성하고, code_challenge를 authorization 요청에 포함한다. 사용자가 브라우저에서 인증을 완료하면 authorization code를 받고, 이를 access_token으로 교환한다.

**4단계 — API 호출**

이후 모든 MCP 요청에 `Authorization: Bearer <token>` 헤더를 포함한다.

#### 서버 구현 시 참고

직접 OAuth 서버를 구현하는 건 복잡하다. 실무에서는 두 가지 방법 중 하나를 선택한다.

- **기존 IdP 앞에 프록시**: Auth0, Keycloak 같은 기존 인증 서버를 authorization server로 쓰고, MCP 서버는 토큰 검증만 한다.
- **SDK의 인증 미들웨어**: MCP SDK에서 제공하는 OAuth 관련 유틸을 쓴다. TypeScript SDK의 경우 `@modelcontextprotocol/sdk/server/auth` 모듈이 있다.

third-party 인증 서버(GitHub, Google 등)를 authorization server로 쓸 때는, 해당 서버가 동적 클라이언트 등록을 지원하지 않을 수 있으므로 MCP 서버가 프록시 역할을 해야 한다.

---

## 11. 관련 프로토콜

MCP가 AI와 도구의 **수직 연결**(AI <-> Tool)을 담당한다면, 에이전트 간 **수평 연결**(Agent <-> Agent)을 위한 프로토콜도 있다.

| 프로토콜 | 방향 | 개발사 | 역할 |
|---------|------|--------|------|
| **MCP** | 수직 (AI <-> Tool) | Anthropic -> AAIF | 도구/데이터 연결 |
| **A2A** | 수평 (Agent <-> Agent) | Google | 에이전트 간 통신 |
| **ACP** | 수평 (Agent <-> Agent) | IBM Research | 에이전트 간 통신 |

> A2A와 ACP는 Linux Foundation 하에서 통합 진행 중

---

## 참고

- [MCP 공식 사이트](https://modelcontextprotocol.io)
- [MCP 사양](https://modelcontextprotocol.io/specification)
- [MCP 서버 개발 가이드](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP 아키텍처](https://modelcontextprotocol.io/docs/learn/architecture)
- [Anthropic MCP 발표](https://www.anthropic.com/news/model-context-protocol)
- [Awesome MCP Servers (GitHub)](https://github.com/punkpeye/awesome-mcp-servers)
