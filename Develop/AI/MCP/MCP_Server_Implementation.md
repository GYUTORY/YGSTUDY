---
title: MCP 서버 직접 구현
tags: [ai, mcp, typescript, python, fastmcp, sdk, tool-registration, claude-code]
updated: 2026-08-04
volatility: high
---

# MCP 서버 직접 구현

MCP 서버를 처음 만들 때 대부분 FastMCP부터 시작한다. 데코레이터 하나로 함수를 tool로 등록하고 `mcp.run()`으로 끝나니까. 그런데 실제 서비스에 붙이다 보면 FastMCP만으로 해결 안 되는 상황이 생긴다.

비동기 초기화가 필요한 경우가 대표적이다. DB 커넥션 풀이나 외부 API 클라이언트를 서버 시작 시점에 세팅해두고 싶은데, FastMCP는 이 흐름을 제어하기 어렵다. 입력 스키마를 정밀하게 정의해야 할 때도 마찬가지다. Zod나 JSON Schema로 enum, pattern, minimum 같은 제약을 걸어야 할 때 FastMCP의 타입 추론만으로는 부족하다. 저수준 SDK를 직접 쓰는 게 낫다.

---

## TypeScript SDK

### 패키지 구조

```bash
npm install @modelcontextprotocol/sdk zod
```

TypeScript 서버는 두 클래스로 구분한다. `Server`는 JSON-RPC 핸들러를 직접 등록하는 가장 낮은 레이어고, `McpServer`는 그 위에 tool/resource/prompt를 편하게 등록하는 래퍼다. 대부분의 경우 `McpServer`로 충분하다.

### 서버 초기화

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

interface AppContext {
  db: DatabasePool;
  cache: Redis;
}

let ctx: AppContext;

const server = new McpServer({
  name: "backend-tools",
  version: "1.0.0",
});

async function main() {
  // 외부 의존성은 서버 연결 전에 초기화한다
  ctx = {
    db: await createPool({ connectionString: process.env.DATABASE_URL }),
    cache: await createRedis(process.env.REDIS_URL),
  };

  const transport = new StdioServerTransport();
  await server.connect(transport);

  process.on("SIGTERM", async () => {
    await server.close();
    await ctx.db.end();
    await ctx.cache.quit();
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("[FATAL]", err);
  process.exit(1);
});
```

stdio 방식에서 서버가 비정상 종료하면 Claude Code가 재시작한다. SIGTERM 핸들러에서 자원을 정리하지 않으면 재시작마다 커넥션이 누적된다.

### 도구 등록과 입력 스키마

```typescript
server.tool(
  "find_orders",
  "주문 목록 조회. status 필터와 날짜 범위를 지정할 수 있다.",
  {
    status: z
      .enum(["pending", "paid", "shipped", "cancelled"])
      .optional()
      .describe("주문 상태 필터"),
    from_date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional()
      .describe("조회 시작일 (YYYY-MM-DD)"),
    to_date: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional()
      .describe("조회 종료일 (YYYY-MM-DD)"),
    limit: z.number().int().min(1).max(100).default(20),
  },
  async ({ status, from_date, to_date, limit }) => {
    const where: Record<string, unknown> = {};
    if (status) where.status = status;
    if (from_date) where.created_at = { gte: new Date(from_date) };
    if (to_date) where.created_at = { ...where.created_at, lte: new Date(to_date) };

    const orders = await ctx.db.orders.findMany({ where, take: limit });
    return {
      content: [{ type: "text", text: JSON.stringify(orders) }],
    };
  }
);
```

Zod 스키마가 JSON Schema로 자동 변환되어 AI에게 전달된다. `describe()`로 설명을 달아두면 AI가 파라미터 의도를 더 정확하게 파악한다. `enum`을 쓰면 AI가 유효하지 않은 값을 넣는 경우가 크게 준다.

### 응답 형식

content 배열에 세 가지 타입을 쓸 수 있다.

```typescript
// 텍스트 — 가장 많이 쓴다
return {
  content: [{ type: "text", text: JSON.stringify(result) }],
};

// 이미지 — 차트나 스크린샷 반환 시
const chartBuffer = await generateChart(data);
return {
  content: [{
    type: "image",
    data: chartBuffer.toString("base64"),
    mimeType: "image/png",
  }],
};

// 리소스 참조 — 대용량 파일
return {
  content: [{
    type: "resource",
    resource: {
      uri: `file:///tmp/export-${Date.now()}.csv`,
      mimeType: "text/csv",
      text: csvContent,
    },
  }],
};
```

실무에서 text + JSON이 95% 이상이다. AI가 JSON을 파싱해서 다음 판단을 내리기 때문에 구조화된 데이터는 JSON으로 직렬화해서 넘긴다.

### 에러 처리

```typescript
server.tool(
  "execute_sql",
  "읽기 전용 SELECT만 허용. UPDATE/DELETE는 거부된다.",
  {
    sql: z.string().min(1),
    params: z.array(z.union([z.string(), z.number(), z.null()])).optional().default([]),
  },
  async ({ sql, params }) => {
    const trimmed = sql.trim().toUpperCase();

    if (!trimmed.startsWith("SELECT")) {
      return {
        isError: true,
        content: [{ type: "text", text: "SELECT만 실행할 수 있다." }],
      };
    }

    // 타임아웃 처리
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);

    try {
      const rows = await ctx.db.raw(sql, params, { signal: controller.signal });
      return {
        content: [{ type: "text", text: JSON.stringify(rows) }],
      };
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        return {
          isError: true,
          content: [{ type: "text", text: "10초 안에 완료되지 않아 중단됐다." }],
        };
      }
      return {
        isError: true,
        content: [{ type: "text", text: `실행 실패: ${(err as Error).message}` }],
      };
    } finally {
      clearTimeout(timeout);
    }
  }
);
```

`isError: true`로 반환하면 MCP 레벨에서는 정상 응답이고 AI가 에러 내용을 읽고 판단한다. `throw`를 쓰면 JSON-RPC 에러가 되는데, 일부 클라이언트가 내용을 제대로 파싱하지 못한다. 비즈니스 에러는 `isError: true` 반환으로 처리하는 게 안전하다.

---

## Python SDK

### FastMCP vs 저수준 Server

FastMCP는 타입 힌트에서 inputSchema를 자동으로 만들어준다. 빠르게 만들 때 쓴다.

```python
from mcp.server.fastmcp import FastMCP
import asyncio

mcp = FastMCP("backend-tools")
db = None

@mcp.tool()
async def find_orders(
    status: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """주문 목록 조회"""
    return await db.orders.find(status=status, limit=limit)

if __name__ == "__main__":
    # FastMCP는 lifespan으로 초기화를 처리한다
    async def lifespan(app):
        global db
        db = await create_database_pool(DATABASE_URL)
        yield
        await db.close()

    mcp = FastMCP("backend-tools", lifespan=lifespan)
    mcp.run()
```

저수준 `Server`는 스키마를 직접 쓰고 싶거나, 요청 처리 흐름을 직접 제어해야 할 때 쓴다.

```python
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("backend-tools")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="find_orders",
            description="주문 목록 조회. status 필터와 limit을 지정할 수 있다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "paid", "shipped", "cancelled"],
                        "description": "주문 상태 필터",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20,
                    },
                },
            },
        ),
        types.Tool(
            name="get_order",
            description="주문 단건 조회",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "pattern": r"^ORD-\d{8}$",
                        "description": "주문 번호. ORD-XXXXXXXX 형식.",
                    },
                },
                "required": ["order_id"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.ContentType]:
    if name == "find_orders":
        status = arguments.get("status")
        limit = arguments.get("limit", 20)
        orders = await db.orders.find(status=status, limit=limit)
        return [types.TextContent(type="text", text=json.dumps(orders))]

    if name == "get_order":
        order_id = arguments["order_id"]
        order = await db.orders.find_one(order_id)
        if not order:
            return [types.TextContent(type="text", text="{}")]
        return [types.TextContent(type="text", text=json.dumps(order))]

    raise ValueError(f"알 수 없는 tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
```

### Python에서 에러 처리

```python
from mcp.shared.exceptions import McpError
from mcp import types

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.ContentType]:
    if name == "execute_sql":
        sql = arguments.get("sql", "").strip()

        if not sql.upper().startswith("SELECT"):
            # McpError를 raise하면 SDK가 isError: true로 변환한다
            raise McpError("SELECT만 실행할 수 있다.")

        try:
            rows = await db.execute(sql)
            return [types.TextContent(type="text", text=json.dumps(rows))]
        except asyncio.TimeoutError:
            raise McpError("쿼리가 10초 안에 완료되지 않아 중단됐다.")
        except Exception as e:
            raise McpError(f"실행 실패: {e}")
```

Python SDK에서 `McpError`를 raise하면 `isError: true` 응답이 된다. 일반 `Exception`은 JSON-RPC 에러 응답으로 나가므로, 비즈니스 에러는 `McpError`로 감싸야 AI가 내용을 읽을 수 있다.

stderr 로그도 빠뜨리면 안 된다.

```python
import sys

def log(msg: str):
    print(f"[mcp-server] {msg}", file=sys.stderr, flush=True)

log("server started")
log(f"db connected: {db.is_connected()}")
```

---

## Claude Code와 로컬 연동

### 설정 파일

`.claude/settings.json`에 서버를 등록한다.

```json
{
  "mcpServers": {
    "backend-tools": {
      "command": "/Users/username/project/.venv/bin/python",
      "args": ["/Users/username/project/mcp_server.py"],
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/mydb",
        "REDIS_URL": "redis://localhost:6379"
      }
    }
  }
}
```

`command`는 절대 경로를 써야 한다. `python`만 쓰면 시스템 Python이 실행돼서 패키지 못 찾는다고 나온다. `env`에 서버가 필요로 하는 환경 변수를 전부 써야 한다. 로컬 셸 환경에서 자동으로 상속되지 않는다.

TypeScript 서버는 빌드 후 실행하는 게 낫다. tsx나 ts-node는 Claude Code가 타임아웃을 먼저 내는 경우가 있다.

```json
{
  "mcpServers": {
    "backend-tools-ts": {
      "command": "node",
      "args": ["/Users/username/project/dist/server.js"],
      "env": {
        "DATABASE_URL": "postgresql://localhost:5432/mydb"
      }
    }
  }
}
```

### 연동 확인

Claude Code를 재시작하거나 `/mcp` 명령을 실행하면 등록된 서버와 tool 목록이 보인다. 서버 옆에 오류 표시가 있으면 서버 실행 자체가 실패한 것이다.

로그를 직접 본다.

```bash
tail -f ~/.claude/logs/mcp-*.log
```

서버의 stderr 출력이 여기 나온다. 서버가 시작하자마자 죽으면 `Process exited with code 1` 메시지와 함께 서버에서 찍은 에러 로그가 보인다.

### MCP Inspector로 선행 테스트

Claude Code에 붙이기 전에 Inspector로 먼저 확인한다.

```bash
# TypeScript/JavaScript 서버
npx @modelcontextprotocol/inspector

# Python 서버
uvx mcp dev mcp_server.py
```

Inspector 브라우저 화면에서 서버를 연결하면 tool 목록, 파라미터 스키마, 실행 결과를 직접 테스트할 수 있다. Claude Code에서 tool이 이상하게 동작할 때 Inspector로 먼저 격리해서 테스트하면 원인을 빨리 찾는다. Claude Code를 거치지 않으므로 프롬프트 해석 문제인지 서버 로직 문제인지 구분된다.

### 자주 겪는 문제

**서버가 시작 직후 죽는다**

대부분 환경 변수를 못 읽거나 DB 연결에 실패한 경우다. settings.json의 command와 args를 터미널에서 직접 실행해보면 에러 메시지를 바로 확인할 수 있다.

```bash
/Users/username/project/.venv/bin/python /Users/username/project/mcp_server.py
```

**stdout에 로그를 찍으면 연결이 끊긴다**

stdio 서버에서 stdout은 JSON-RPC 통신 전용이다. `print()`나 `console.log()`가 섞이면 클라이언트가 파싱 에러를 낸다. 로그는 반드시 stderr로 보낸다.

```python
print("[DEBUG] started", file=sys.stderr)  # 올바름
print("[DEBUG] started")  # 프로토콜을 오염시킨다
```

```typescript
console.error("[DEBUG] started");  // 올바름
console.log("[DEBUG] started");    // 프로토콜을 오염시킨다
```

**tool을 수정했는데 Claude Code에서 이전 버전으로 동작한다**

Claude Code는 연결 시점의 tool 목록을 캐시한다. 서버를 수정했으면 Claude Code를 재시작하거나 `/mcp`로 서버를 재연결한다. 서버가 `notifications/tools/list_changed`를 보내면 자동 갱신되지만, 대부분의 서버가 이 알림을 구현하지 않는다.

**로컬 DB에 연결이 안 된다**

Claude Code가 서버를 실행할 때 현재 디렉토리가 다를 수 있다. DB 소켓 경로를 상대 경로로 쓰지 말고 절대 경로나 호스트:포트 방식으로 쓴다. PostgreSQL 유닉스 소켓의 경우 `postgresql://localhost:5432/mydb` 대신 `postgresql:///mydb` 같은 로컬 소켓 URL이 실패할 수 있다.

---

## 관련 문서

- [MCP 핵심 개념](MCP.md) — 프로토콜 구조, 프리미티브(Tool/Resource/Prompt/Sampling) 전반
- [MCP 전송 방식](SSE_and_Stdio.md) — stdio와 Streamable HTTP 동작 원리, 프로덕션 배포 시 고려사항
