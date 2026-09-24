---
title: Claude Code SDK로 자체 하네스 구현
tags: [ai, backend, typescript]
updated: 2026-09-24
---

# Claude Code SDK로 자체 하네스 구현

[Claude_Code_Harness.md](Claude_Code_Harness.md)는 Claude Code 런타임 내부에서 무슨 일이 일어나는지를 설명한다. 이 문서는 그 내부 구조를 참고해서, **같은 것을 직접 만드는 방법**을 다룬다.

CLI로는 안 되는 것들이 있다. 기존 웹 서비스에 에이전트 루프를 내장하고 싶을 때, 권한 체크를 사내 인증 시스템과 연동해야 할 때, 특정 도구 결과를 DB에 저장하면서 루프를 돌려야 할 때다. 이런 경우 `@anthropic-ai/sdk`로 직접 하네스를 만드는 편이 낫다.

---

## 에이전트 루프의 본체

하네스의 핵심은 단순하다. API를 호출하고, 응답에 도구 호출이 있으면 실행하고, 결과를 메시지로 붙여서 다시 API를 호출하는 것을 반복한다. 이 루프가 멈추는 조건은 두 가지다: 모델이 `end_turn`을 내놓거나, 메시지에 도구 호출이 없는 텍스트만 남거나.

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

type Message = Anthropic.MessageParam;
type Tool = Anthropic.Tool;

async function agentLoop(
  systemPrompt: string,
  userMessage: string,
  tools: Tool[]
): Promise<string> {
  const messages: Message[] = [{ role: "user", content: userMessage }];

  while (true) {
    const response = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 8096,
      system: systemPrompt,
      tools,
      messages,
    });

    // 어시스턴트 응답 전체를 메시지 히스토리에 넣는다
    messages.push({ role: "assistant", content: response.content });

    if (response.stop_reason === "end_turn") {
      // 텍스트 블록만 모아서 반환
      return response.content
        .filter((b) => b.type === "text")
        .map((b) => (b as Anthropic.TextBlock).text)
        .join("\n");
    }

    if (response.stop_reason !== "tool_use") {
      throw new Error(`예상치 못한 stop_reason: ${response.stop_reason}`);
    }

    // 도구 호출 블록만 추려서 실행
    const toolUseBlocks = response.content.filter(
      (b) => b.type === "tool_use"
    ) as Anthropic.ToolUseBlock[];

    const toolResults = await Promise.all(
      toolUseBlocks.map(async (block) => {
        const result = await executeTool(block.name, block.input);
        return {
          type: "tool_result" as const,
          tool_use_id: block.id,
          content: result,
        };
      })
    );

    messages.push({ role: "user", content: toolResults });
  }
}
```

여기서 흔히 실수하는 부분이 있다. 도구 결과를 `user` 역할의 메시지로 보내야 하는데, 도구 결과만 있어도 `role: "user"`여야 한다. `role: "tool"` 같은 역할은 없다. 이걸 바꾸면 `invalid_request_error`가 나고, 에러 메시지가 직관적이지 않아서 원인 파악에 시간이 걸린다.

도구를 병렬로 실행하는 `Promise.all`은 간단한 경우에는 괜찮은데, 도구 간에 순서가 있거나 한 도구 결과가 다른 도구의 입력이 되는 경우에는 순서를 보장해야 한다. 모델이 같은 턴에 연쇄 의존적인 도구를 동시에 요청하는 경우는 드물지만, 방어 코드를 넣는 편이 안전하다.

---

## 도구 정의와 디스패처

도구는 JSON Schema로 정의하고, 핸들러 함수와 쌍으로 관리한다. 도구가 많아지면 이름으로 핸들러를 찾는 디스패처 구조가 필요하다.

```typescript
type ToolHandler = (input: Record<string, unknown>) => Promise<string>;

interface ToolDef {
  schema: Tool;
  handler: ToolHandler;
}

const toolRegistry = new Map<string, ToolDef>();

function registerTool(
  schema: Tool,
  handler: ToolHandler
) {
  toolRegistry.set(schema.name, { schema, handler });
}

async function executeTool(
  name: string,
  input: Record<string, unknown>
): Promise<string> {
  const def = toolRegistry.get(name);
  if (!def) {
    return `Error: 알 수 없는 도구 '${name}'`;
  }
  try {
    return await def.handler(input);
  } catch (err) {
    return `Error: ${(err as Error).message}`;
  }
}

// 도구 등록 예시
registerTool(
  {
    name: "read_file",
    description: "파일을 읽어서 내용을 반환한다",
    input_schema: {
      type: "object",
      properties: {
        path: { type: "string", description: "파일 경로" },
        limit: { type: "number", description: "최대 읽을 줄 수" },
      },
      required: ["path"],
    },
  },
  async ({ path, limit }) => {
    const { readFile } = await import("fs/promises");
    const content = await readFile(path as string, "utf-8");
    const lines = content.split("\n");
    if (limit) return lines.slice(0, limit as number).join("\n");
    return content;
  }
);
```

도구 에러를 `throw`로 올리지 말고 문자열로 반환하는 이유가 있다. 도구 실행이 실패해도 루프는 계속 돌아야 한다. 에러 메시지가 모델에게 돌아가면 모델이 다른 방법을 찾는다. `throw`로 올리면 루프 전체가 중단된다. 복구 불가능한 에러(인증 실패, 쿼터 초과 등)만 예외로 올리고 나머지는 문자열로 반환한다.

---

## 권한 처리 레이어

Claude Code 내부의 `permission gate`는 도구 실행 전에 룰을 검사한다. 직접 구현할 때도 같은 위치에 끼워넣는다.

```typescript
type PermissionResult =
  | { allowed: true }
  | { allowed: false; reason: string };

type PermissionCheck = (
  toolName: string,
  input: Record<string, unknown>
) => Promise<PermissionResult>;

const permissionChecks: PermissionCheck[] = [];

function addPermissionCheck(check: PermissionCheck) {
  permissionChecks.push(check);
}

async function checkPermission(
  toolName: string,
  input: Record<string, unknown>
): Promise<PermissionResult> {
  for (const check of permissionChecks) {
    const result = await check(toolName, input);
    if (!result.allowed) return result;
  }
  return { allowed: true };
}

// 실제 executeTool에 권한 검사를 추가
async function executeToolWithPermission(
  name: string,
  input: Record<string, unknown>
): Promise<string> {
  const permission = await checkPermission(name, input);
  if (!permission.allowed) {
    return `Permission denied: ${permission.reason}`;
  }
  return executeTool(name, input);
}
```

권한 검사 예시 두 개.

```typescript
// 셸 명령 중 rm -rf 차단
addPermissionCheck(async (toolName, input) => {
  if (toolName !== "bash") return { allowed: true };
  const command = input.command as string;
  if (/rm\s+-[rf]+\s+\//.test(command)) {
    return { allowed: false, reason: "루트 삭제 명령은 허용하지 않는다" };
  }
  return { allowed: true };
});

// 사용자 인터랙티브 승인 (터미널 환경)
addPermissionCheck(async (toolName, input) => {
  const dangerousTools = ["bash", "write_file", "delete_file"];
  if (!dangerousTools.includes(toolName)) return { allowed: true };

  const readline = await import("readline");
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  return new Promise((resolve) => {
    const preview = JSON.stringify(input).slice(0, 100);
    rl.question(
      `[${toolName}] ${preview}\n승인? (y/n): `,
      (answer) => {
        rl.close();
        resolve(answer.trim().toLowerCase() === "y"
          ? { allowed: true }
          : { allowed: false, reason: "사용자가 거부했다" });
      }
    );
  });
});
```

권한 거부 결과를 `throw` 대신 문자열로 돌려주는 점이 중요하다. 모델이 "이 도구는 권한이 없다"는 메시지를 받으면, 다른 접근 방법을 시도한다. 예외로 올리면 루프가 죽는다.

웹 서비스에 내장하는 경우에는 사용자 인터랙티브 승인 대신 HTTP 요청을 대기하는 비동기 로직을 써야 한다. WebSocket이나 SSE로 프론트엔드에 승인 요청을 보내고, 사용자가 승인하면 Promise를 resolve한다.

---

## 컨텍스트 압축

모델에게 보내는 메시지 배열이 쌓이면 토큰 한도에 가까워진다. 응답 헤더의 `usage.input_tokens`를 보면 현재 누적 토큰을 알 수 있다. 일정 임계치를 넘으면 오래된 메시지를 요약으로 대체한다.

```typescript
const TOKEN_LIMIT = 150_000; // 200K 모델에서 75% 지점
const COMPRESS_KEEP_LAST = 4; // 최근 메시지 N개는 보존

async function compressMessages(
  messages: Message[],
  systemPrompt: string
): Promise<Message[]> {
  if (messages.length <= COMPRESS_KEEP_LAST * 2) {
    return messages;
  }

  const toCompress = messages.slice(0, messages.length - COMPRESS_KEEP_LAST * 2);
  const toKeep = messages.slice(messages.length - COMPRESS_KEEP_LAST * 2);

  const compressionResponse = await client.messages.create({
    model: "claude-haiku-4-5-20251001", // 압축은 빠른 모델로
    max_tokens: 4096,
    system: "대화 요약 전문가다. 핵심 결정, 실행된 도구, 발견된 사실만 보존하고 나머지는 버린다.",
    messages: [
      {
        role: "user",
        content: `다음 대화를 요약해라. 반드시 보존해야 할 것: (1) 사용자의 최초 요청, (2) 완료된 작업 목록, (3) 실패한 시도와 이유, (4) 현재 상태.\n\n${JSON.stringify(toCompress)}`,
      },
    ],
  });

  const summary = compressionResponse.content
    .filter((b) => b.type === "text")
    .map((b) => (b as Anthropic.TextBlock).text)
    .join("\n");

  const summaryMessage: Message = {
    role: "user",
    content: `[이전 대화 요약]\n${summary}`,
  };

  // assistant 역할로 시작해야 하는 메시지 배열 구조를 맞춘다
  return [summaryMessage, ...toKeep];
}

// 루프에서 사용
async function agentLoopWithCompression(
  systemPrompt: string,
  userMessage: string,
  tools: Tool[]
): Promise<string> {
  let messages: Message[] = [{ role: "user", content: userMessage }];

  while (true) {
    const response = await client.messages.create({
      model: "claude-sonnet-4-6",
      max_tokens: 8096,
      system: systemPrompt,
      tools,
      messages,
    });

    messages.push({ role: "assistant", content: response.content });

    if (response.stop_reason === "end_turn") {
      return response.content
        .filter((b) => b.type === "text")
        .map((b) => (b as Anthropic.TextBlock).text)
        .join("\n");
    }

    // 도구 실행 (생략)

    // 임계치 초과 시 압축
    if (response.usage.input_tokens > TOKEN_LIMIT) {
      messages = await compressMessages(messages, systemPrompt);
    }
  }
}
```

압축 직후에는 캐시가 깨진다. 다음 호출이 느린 건 정상이다. 중요한 건 압축 대상 선택이다. 도구 결과 블록(`tool_result`)이 들어있는 메시지를 압축 대상에 포함하면, 대화 구조가 깨져서 API가 `invalid_request_error`를 낸다. 도구 호출(`tool_use`)과 결과(`tool_result`)는 항상 쌍으로 유지해야 한다. `toCompress`를 고를 때 이 쌍이 잘리지 않도록 경계를 찾는 로직이 필요하다.

```typescript
function findSafeCompressBoundary(messages: Message[]): number {
  // tool_use / tool_result 쌍의 경계를 찾는다
  for (let i = messages.length - COMPRESS_KEEP_LAST * 2 - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === "user") {
      const hasToolResult = Array.isArray(msg.content) &&
        msg.content.some((b: Anthropic.ContentBlock) => b.type === "tool_result");
      if (!hasToolResult) return i + 1; // user 메시지이고 tool_result가 없는 경계
    }
  }
  return 0;
}
```

---

## 에러 복구

API 에러는 종류가 다르다. 재시도 가능한 에러와 그렇지 않은 에러를 구분해야 한다.

```typescript
const RETRYABLE_ERRORS = new Set([529, 500, 503]); // 과부하, 서버 에러
const MAX_RETRIES = 3;

async function callWithRetry(
  fn: () => Promise<Anthropic.Message>
): Promise<Anthropic.Message> {
  let attempt = 0;

  while (attempt < MAX_RETRIES) {
    try {
      return await fn();
    } catch (err) {
      if (err instanceof Anthropic.APIStatusError) {
        if (!RETRYABLE_ERRORS.has(err.status)) {
          throw err; // 400, 401, 403, 404는 재시도해도 안 된다
        }
        attempt++;
        if (attempt >= MAX_RETRIES) throw err;

        // 지수 백오프: 1초, 2초, 4초
        const delay = Math.pow(2, attempt - 1) * 1000;
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }
      throw err;
    }
  }
  throw new Error("도달 불가능한 코드");
}
```

도구 실패를 모델이 무한 재시도하는 상황도 막아야 한다. 같은 도구를 같은 인자로 N번 이상 호출하면 루프를 끊는다.

```typescript
function makeLoopDetector() {
  const callCounts = new Map<string, number>();
  const MAX_SAME_CALL = 3;

  return function detect(name: string, input: Record<string, unknown>): boolean {
    const key = `${name}:${JSON.stringify(input)}`;
    const count = (callCounts.get(key) ?? 0) + 1;
    callCounts.set(key, count);
    return count > MAX_SAME_CALL;
  };
}

// 루프 안에서 사용
const isLoop = makeLoopDetector();

for (const block of toolUseBlocks) {
  if (isLoop(block.name, block.input)) {
    throw new Error(`무한 루프 감지: ${block.name}이 같은 인자로 반복 호출되고 있다`);
  }
  // 실행...
}
```

턴 수 상한도 설정한다. 작업에 따라 다르지만 30~50턴을 넘기는 작업은 대부분 모델이 같은 시도를 반복하고 있는 상태다.

```typescript
const MAX_TURNS = 30;
let turnCount = 0;

while (true) {
  if (++turnCount > MAX_TURNS) {
    throw new Error(`최대 턴 수(${MAX_TURNS}) 초과. 작업을 더 작게 쪼개야 한다`);
  }
  // ...
}
```

---

## 프롬프트 캐싱 적용

시스템 프롬프트와 도구 정의가 크면 캐시를 붙인다. API 호출당 40~60%의 비용을 절감할 수 있다.

```typescript
const response = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 8096,
  system: [
    {
      type: "text",
      text: systemPrompt,
      cache_control: { type: "ephemeral" }, // 5분 캐시
    },
  ],
  tools: tools.map((tool, i) =>
    i === tools.length - 1
      ? { ...tool, cache_control: { type: "ephemeral" } } // 마지막 도구에만 마커
      : tool
  ),
  messages,
});
```

캐시 마커는 최대 4개까지 쓸 수 있다. 시스템 프롬프트에 1개, 도구 배열 끝에 1개를 붙이는 게 일반적이다. 마커 위치 이전까지가 캐시 대상이다. 시스템 프롬프트가 변하지 않고 도구 정의도 고정이라면, 매 턴마다 같은 토큰을 새로 보내지 않는다.

캐시가 제대로 붙었는지 확인하려면 응답의 `usage`를 본다.

```typescript
console.log(response.usage);
// {
//   input_tokens: 12,
//   cache_read_input_tokens: 8420,
//   cache_creation_input_tokens: 0,
//   output_tokens: 384
// }
```

`cache_read_input_tokens`가 0이면 캐시 미스다. 첫 번째 호출에서는 `cache_creation_input_tokens`가 있어야 정상이다. 두 번째 호출부터 `cache_read_input_tokens`가 올라와야 캐시가 동작하는 것이다.

---

## 실제로 겪은 문제들

**도구 결과가 너무 크면 그 다음 턴이 비정상적으로 느리다.** 한 도구가 10만 토큰짜리 결과를 반환하면, 그 결과가 메시지 히스토리에 쌓이고, 이후 모든 턴에서 그 토큰을 계속 보낸다. 캐시가 붙어있어도 메시지 히스토리 캐시는 더 복잡하다. 도구 결과는 미리 잘라야 한다. `content.slice(0, maxLen)`로 자른 다음 `...truncated` 표시를 붙인다.

**`tool_use`와 `tool_result`의 id가 맞지 않으면 API가 에러를 낸다.** 비동기 처리 중에 순서가 뒤섞이는 경우가 있다. `block.id`를 키로 `Map`에 결과를 모으고, 나중에 정렬해서 `messages`에 추가한다.

**모델이 존재하지 않는 도구를 호출하는 경우가 있다.** 이건 시스템 프롬프트에서 언급한 도구 이름과 실제 등록된 도구 이름이 다를 때 주로 발생한다. `toolRegistry.get(name)`이 undefined를 반환하면 명확한 에러 메시지를 돌려줘야 한다. 단순히 빈 문자열을 반환하면 모델이 성공으로 착각하고 계속 진행한다.

**사용자 승인 로직에서 타임아웃을 빠뜨리면 루프가 영원히 멈춘다.** 서버에서 실행하는 경우 특히 위험하다. `Promise.race`로 타임아웃과 승인 응답 중 먼저 오는 걸 처리하고, 타임아웃이 나면 거부로 처리한다.
