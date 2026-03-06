---
title: MCP (Model Context Protocol) 핵심 개념
tags: [ai, mcp, model-context-protocol, anthropic, open-standard]
updated: 2026-03-01
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

- **JSON-RPC 2.0** 기반
- **전송 방식**: stdio (로컬), HTTP+SSE (원격)

---

## 3. 핵심 프리미티브

MCP 서버는 세 가지 프리미티브를 제공한다.

### 3.1 Tools (도구)

AI가 **실행할 수 있는 함수/액션**이다. API 호출, DB 쿼리, 파일 작업 등.

```json
{
  "name": "query_database",
  "description": "SQL 쿼리를 실행하고 결과를 반환합니다",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "실행할 SQL 쿼리" }
    },
    "required": ["query"]
  }
}
```

### 3.2 Resources (리소스)

AI에게 **컨텍스트 정보를 제공하는 데이터 소스**이다. 파일, DB 스키마, API 문서 등.

```json
{
  "uri": "db://mydb/schema",
  "name": "데이터베이스 스키마",
  "mimeType": "application/json"
}
```

### 3.3 Prompts (프롬프트)

AI와의 상호작용을 표준화하는 **재사용 가능한 프롬프트 템플릿**이다.

```json
{
  "name": "code_review",
  "description": "코드 리뷰 요청 프롬프트",
  "arguments": [
    { "name": "language", "description": "프로그래밍 언어" }
  ]
}
```

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
  "사용자 정보를 조회합니다",
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
    """사용자 정보를 조회합니다"""
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

---

## 5. 주요 MCP 서버

### 5.1 공식 서버 (Anthropic)

| 서버 | 용도 |
|------|------|
| **PostgreSQL** | DB 쿼리, 스키마 조회 |
| **GitHub** | 이슈, PR, 레포 관리 |
| **Git** | 로컬 Git 작업 |
| **Slack** | 메시지 전송, 채널 관리 |
| **Google Drive** | 문서 읽기/검색 |
| **Puppeteer** | 웹 브라우저 자동화 |

### 5.2 커뮤니티 서버

| 서버 | 용도 |
|------|------|
| **Brave Search** | 웹 검색 |
| **Supabase** | Edge Functions, DB |
| **Terraform** | IaC 관리 |
| **Kubernetes** | K8s 클러스터 관리 |
| **Prometheus** | 모니터링 메트릭 |
| **PagerDuty** | 인시던트 관리 |
| **Zapier** | 수천 개 앱 연동 |

📌 GitHub의 **awesome-mcp-servers** 레포에서 전체 목록 확인 가능

---

## 6. 보안 고려사항

### 6.1 주요 보안 위험

| 위험 | 설명 | 대응 |
|------|------|------|
| **프롬프트 인젝션** | 악의적 지시가 도구 메타데이터에 숨겨짐 | 신뢰할 수 있는 서버만 사용 |
| **도구 포이즈닝** | MCP 도구 설명에 악성 명령 삽입 | 서버 소스 코드 검증 |
| **자격 증명 노출** | 잘못된 설정으로 API 키 유출 | 환경 변수로 시크릿 관리 |
| **권한 상승** | 에이전트가 과도한 권한 획득 | 최소 권한 원칙 적용 |
| **임의 코드 실행** | 신뢰할 수 없는 서버가 악성 코드 실행 | 공식/검증된 서버만 설치 |

### 6.2 모범 사례

- MCP 서버는 **공식 또는 검증된 소스**에서만 설치
- 시크릿은 반드시 **환경 변수**로 관리 (설정 파일에 하드코딩 금지)
- **최소 권한 원칙**: 필요한 도구만 활성화
- 프로덕션 환경에서는 **네트워크 격리** 고려
- 정기적으로 연결된 MCP 서버 **감사**

---

## 7. 관련 프로토콜

MCP가 AI와 도구의 **수직 연결**(AI ↔ Tool)을 담당한다면, 에이전트 간 **수평 연결**(Agent ↔ Agent)을 위한 프로토콜도 있다.

| 프로토콜 | 방향 | 개발사 | 역할 |
|---------|------|--------|------|
| **MCP** | 수직 (AI ↔ Tool) | Anthropic → AAIF | 도구/데이터 연결 |
| **A2A** | 수평 (Agent ↔ Agent) | Google | 에이전트 간 통신 |
| **ACP** | 수평 (Agent ↔ Agent) | IBM Research | 에이전트 간 통신 |

> A2A와 ACP는 Linux Foundation 하에서 통합 진행 중

---

## 참고

- [MCP 공식 사이트](https://modelcontextprotocol.io)
- [MCP 사양](https://modelcontextprotocol.io/specification)
- [MCP 서버 개발 가이드](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP 아키텍처](https://modelcontextprotocol.io/docs/learn/architecture)
- [Anthropic MCP 발표](https://www.anthropic.com/news/model-context-protocol)
- [Awesome MCP Servers (GitHub)](https://github.com/punkpeye/awesome-mcp-servers)
