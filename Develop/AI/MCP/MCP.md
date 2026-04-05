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
- 원격 서버이므로 인증이 필요하다 (OAuth 2.1, 6.3절 참고).
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

MCP 서버는 세 가지 프리미티브를 제공한다.

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

---

## 4. MCP 서버 만들기

### 4.1 TypeScript로 만들기

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

### 4.2 Python으로 만들기

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

### 4.3 MCP 서버 연결 설정

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

## 5. MCP 서버 디버깅

### 5.1 MCP Inspector

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

### 5.2 로그 확인

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

### 5.3 연결이 안 되는 경우

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

## 6. MCP 서버 테스트

MCP 서버를 만들고 나면 tool 호출이 제대로 동작하는지 자동화된 테스트가 필요하다.

### 6.1 인메모리 전송으로 단위 테스트

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

### 6.2 테스트할 때 주의할 점

- tool 핸들러에서 외부 의존성(DB, API 등)이 있으면 테스트용 mock이나 fixture를 따로 만들어야 한다. 서버 생성 시 의존성을 주입할 수 있게 구조를 잡아두면 테스트가 편하다.
- tool 호출 결과의 `isError` 필드로 에러 케이스도 테스트한다. 잘못된 파라미터를 넣었을 때 서버가 죽지 않고 에러 응답을 돌려주는지 확인해야 한다.
- resource와 prompt도 같은 방식으로 테스트한다. `client.listResources()`, `client.readResource()`, `client.listPrompts()`, `client.getPrompt()` 등을 쓴다.

---

## 7. 주요 MCP 서버

### 7.1 공식 서버 (Anthropic)

| 서버 | 용도 |
|------|------|
| **PostgreSQL** | DB 쿼리, 스키마 조회 |
| **GitHub** | 이슈, PR, 레포 관리 |
| **Git** | 로컬 Git 작업 |
| **Slack** | 메시지 전송, 채널 관리 |
| **Google Drive** | 문서 읽기/검색 |
| **Puppeteer** | 웹 브라우저 자동화 |

### 7.2 커뮤니티 서버

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

## 8. 보안 고려사항

### 8.1 주요 보안 위험

| 위험 | 설명 | 대응 |
|------|------|------|
| **프롬프트 인젝션** | 악의적 지시가 도구 메타데이터에 숨겨짐 | 신뢰할 수 있는 서버만 사용 |
| **도구 포이즈닝** | MCP 도구 설명에 악성 명령 삽입 | 서버 소스 코드 검증 |
| **자격 증명 노출** | 잘못된 설정으로 API 키 유출 | 환경 변수로 시크릿 관리 |
| **권한 상승** | 에이전트가 과도한 권한 획득 | 최소 권한 원칙 적용 |
| **임의 코드 실행** | 신뢰할 수 없는 서버가 악성 코드 실행 | 공식/검증된 서버만 설치 |

### 8.2 보안 설정 시 지켜야 할 것

- MCP 서버는 **공식 또는 검증된 소스**에서만 설치한다
- 시크릿은 반드시 **환경 변수**로 관리한다 (설정 파일에 하드코딩 금지)
- **최소 권한 원칙**: 필요한 도구만 활성화한다
- 프로덕션 환경에서는 **네트워크 격리**를 적용한다
- 연결된 MCP 서버를 정기적으로 점검한다

### 8.3 원격 MCP 서버 인증 (OAuth 2.1)

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

## 9. 관련 프로토콜

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
