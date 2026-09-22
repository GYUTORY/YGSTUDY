---
title: JSON-RPC
tags: [network, http, tcp, api, backend, grpc]
updated: 2026-09-22
---

# JSON-RPC

JSON을 직렬화 포맷으로 사용하는 RPC 프로토콜이다. 전송 계층에 종속되지 않아 HTTP, WebSocket, TCP 위에서 모두 동작한다. 사양이 단순해서 구현 부담이 적고, 어떤 언어에서도 JSON 파서 하나면 클라이언트를 만들 수 있다.

## 1.0과 2.0의 차이

1.0(2005)은 요청 필드가 `method`, `params`, `id` 세 개고 `id`에 `null`을 허용하지 않는다. 모든 요청은 응답을 기대한다.

2.0(2010)이 현재 표준이다. 변경 내용:

- `jsonrpc: "2.0"` 필드 추가 — 버전 식별
- `id` 생략으로 알림(notification) 표현 — 응답을 요청하지 않는 단방향 호출
- 배치 요청(batch request) 공식 지원
- `params`가 배열과 객체 모두 허용 (1.0은 배열만)
- 에러 객체 구조 표준화

1.0 서버에 2.0 클라이언트를 붙이면 `jsonrpc` 필드를 모르는 서버가 무시하거나 에러를 낼 수 있다. 이더리움 클라이언트 구현체마다 버전 처리가 달라 혼선이 생기는 경우가 있다.

## 요청과 응답 구조

**요청(Request)**

```json
{
  "jsonrpc": "2.0",
  "method": "eth_getBalance",
  "params": ["0xd3CdA913deB6f4967b2Ef66ae8b1", "latest"],
  "id": 1
}
```

- `jsonrpc`: 반드시 `"2.0"` 문자열
- `method`: 호출할 메서드 이름. `rpc.` 접두사는 내부용으로 예약
- `params`: 배열(positional) 또는 객체(named). 생략 가능
- `id`: 문자열, 숫자, null 허용. 요청-응답 매칭에 사용. 알림이면 생략

**성공 응답**

```json
{
  "jsonrpc": "2.0",
  "result": "0x0234c8a3397aab58",
  "id": 1
}
```

- `result`와 `error`는 동시에 존재할 수 없다
- `id`는 요청의 `id`와 같아야 한다. 요청 `id`를 파싱하지 못하면 `null`

**에러 응답**

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": "jsonrpc field missing"
  },
  "id": null
}
```

`data` 필드는 선택 사항이고 구조 제약이 없다. 구현체마다 형태가 다르다.

**알림(Notification)**

`id` 필드가 없으면 알림이다. 서버는 알림에 응답을 보내지 않는다.

```json
{
  "jsonrpc": "2.0",
  "method": "eth_subscription",
  "params": {
    "subscription": "0x9ce59a13059e417087c02d3236a0b1cc",
    "result": {}
  }
}
```

## 배치 요청

여러 요청을 배열로 묶어 한 번에 보낸다.

```json
[
  {"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
  {"jsonrpc": "2.0", "method": "eth_gasPrice", "id": 2},
  {"jsonrpc": "2.0", "method": "net_version", "id": 3}
]
```

서버는 각 요청을 독립적으로 처리하고 결과를 배열로 돌려준다. 순서 보장은 없다. `id`로 어느 요청의 응답인지 맞춰야 한다.

```json
[
  {"jsonrpc": "2.0", "result": "0x10d4f", "id": 1},
  {"jsonrpc": "2.0", "result": "0x3b9aca00", "id": 2},
  {"jsonrpc": "2.0", "result": "1", "id": 3}
]
```

배치 안에 알림이 섞여 있으면 그 항목에 대한 응답은 배열에 포함되지 않는다. 배치 전체가 알림이면 서버는 아무것도 돌려주지 않는다.

**배치 크기 제한 실무**

노드마다 배치 크기 제한이 다르다. Infura는 기본 1,000, Alchemy는 100이다. 제한을 초과하면 보통 `-32005` 또는 HTTP 413으로 거절한다. 공급자가 정해져 있지 않은 상황이라면 100을 기본값으로 잡는다.

```javascript
const BATCH_LIMIT = 100;

async function batchRpc(requests, endpoint) {
  const results = [];
  for (let i = 0; i < requests.length; i += BATCH_LIMIT) {
    const chunk = requests.slice(i, i + BATCH_LIMIT);
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(chunk),
    });
    const data = await res.json();
    results.push(...(Array.isArray(data) ? data : [data]));
  }
  // id 기준으로 원래 순서로 정렬
  const byId = Object.fromEntries(results.map(r => [r.id, r]));
  return requests.map(req => byId[req.id]);
}
```

배치 응답의 순서가 보장되지 않는다. 위 코드처럼 `id`로 재정렬하지 않으면 결과가 섞인다. 직접 짠 배치 클라이언트에서 자주 놓치는 부분이다.

## 에러 코드 체계

프로토콜 예약 범위는 `-32768` ~ `-32000`이다.

| 코드 | 의미 |
|------|------|
| -32700 | Parse error — JSON 파싱 실패 |
| -32600 | Invalid Request — 요청 객체가 JSON-RPC 명세 위반 |
| -32601 | Method not found — 존재하지 않는 메서드 |
| -32602 | Invalid params — 파라미터 타입 또는 개수 오류 |
| -32603 | Internal error — 서버 내부 오류 |
| -32000 ~ -32099 | Server error — 구현체 정의 서버 오류 |

`-32000` ~ `-32099`는 서버가 자유롭게 정의하는 범위다. 이더리움 클라이언트들이 이 범위를 써서 트랜잭션 거부, 가스 부족, 논스 충돌 같은 오류를 구분한다.

애플리케이션 레벨 오류는 `-32000` 위쪽 범위를 쓰지만 사양에 명시되지 않아서 구현체마다 제각각이다. 클라이언트 코드에서 애플리케이션 에러와 프로토콜 에러를 분리해서 처리해야 한다.

```javascript
function handleRpcError(error) {
  if (error.code >= -32099 && error.code <= -32000) {
    return handleServerDefinedError(error);
  }
  if (error.code > -32000) {
    return handleAppError(error);
  }
  // -32700 ~ -32603: 프로토콜 에러
  throw new ProtocolError(error.code, error.message);
}
```

## HTTP와 WebSocket 전송 방식

**HTTP**

모든 요청은 `POST /`에 `Content-Type: application/json`으로 보낸다. 경로 구분이 없고 메서드 이름이 본문 안에 있다. REST와 달리 GET을 쓰지 않는다.

```
POST / HTTP/1.1
Host: localhost:8545
Content-Type: application/json

{"jsonrpc":"2.0","method":"eth_blockNumber","id":1}
```

요청마다 TCP 연결을 새로 열면 오버헤드가 크다. keep-alive를 쓰거나 HTTP/2로 멀티플렉싱한다. 배치 요청도 왕복 횟수를 줄이는 수단이다.

서버 푸시가 없다. 서버에서 클라이언트로 이벤트를 보내려면 클라이언트가 폴링해야 한다.

**WebSocket**

연결을 한 번 맺어두고 양방향으로 메시지를 교환한다. 같은 JSON-RPC 메시지 형식을 그대로 쓴다.

```
// 클라이언트 → 서버: 새 블록 헤더 구독
{"jsonrpc":"2.0","method":"eth_subscribe","params":["newHeads"],"id":1}

// 서버 → 클라이언트: 구독 ID 반환
{"jsonrpc":"2.0","result":"0x9ce59a13059e417087c02d3236a0b1cc","id":1}

// 서버 → 클라이언트: 새 블록마다 알림
{"jsonrpc":"2.0","method":"eth_subscription","params":{"subscription":"0x9ce59a1...","result":{...}}}
```

서버가 알림을 클라이언트에 밀어넣는다. 이더리움에서 블록 이벤트를 구독하거나 pending 트랜잭션을 실시간으로 받을 때 WebSocket을 선택하는 이유다.

연결 상태를 유지해야 하므로 서버 부담이 HTTP보다 크다. 연결이 끊기면 재구독해야 한다.

## 서버 구현

### Node.js

`jsonrpc` 필드 검사, 알림 처리, 배치 분기를 모두 담은 최소 구현이다.

```javascript
const http = require('http');

const METHODS = {
  add: ([a, b]) => a + b,
  subtract: ([a, b]) => a - b,
};

function dispatch(req) {
  if (!req || req.jsonrpc !== '2.0' || typeof req.method !== 'string') {
    return { jsonrpc: '2.0', error: { code: -32600, message: 'Invalid Request' }, id: req?.id ?? null };
  }

  const fn = METHODS[req.method];
  if (!fn) {
    return { jsonrpc: '2.0', error: { code: -32601, message: 'Method not found' }, id: req.id ?? null };
  }

  try {
    const result = fn(req.params ?? []);
    if (!('id' in req)) return null; // 알림: 응답 없음
    return { jsonrpc: '2.0', result, id: req.id };
  } catch (e) {
    return { jsonrpc: '2.0', error: { code: -32603, message: e.message }, id: req.id ?? null };
  }
}

const server = http.createServer((req, res) => {
  if (req.method !== 'POST') { res.writeHead(405).end(); return; }

  let raw = '';
  req.on('data', c => { raw += c; });
  req.on('end', () => {
    let body;
    try { body = JSON.parse(raw); } catch {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ jsonrpc: '2.0', error: { code: -32700, message: 'Parse error' }, id: null }));
      return;
    }

    const isBatch = Array.isArray(body);
    const responses = isBatch
      ? body.map(dispatch).filter(r => r !== null)
      : dispatch(body);

    res.writeHead(200, { 'Content-Type': 'application/json' });
    if (responses === null || (isBatch && responses.length === 0)) {
      res.end(); // 알림만 있는 배치는 빈 응답
    } else {
      res.end(JSON.stringify(responses));
    }
  });
});

server.listen(8080);
```

배치가 전부 알림이면 응답 바디 없이 200을 돌려준다. 스펙 상 이 경우 응답 자체를 보내지 말라고 되어 있어서 `res.end()`만 호출한다.

### Python

표준 라이브러리만 써서 동일한 구조를 구현한다.

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

METHODS = {
    'add': lambda p: p[0] + p[1],
    'subtract': lambda p: p[0] - p[1],
}

def dispatch(req):
    if not isinstance(req, dict) or req.get('jsonrpc') != '2.0':
        return {'jsonrpc': '2.0', 'error': {'code': -32600, 'message': 'Invalid Request'}, 'id': req.get('id')}

    fn = METHODS.get(req.get('method', ''))
    if not fn:
        return {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': 'Method not found'}, 'id': req.get('id')}

    try:
        result = fn(req.get('params', []))
        if 'id' not in req:
            return None  # 알림
        return {'jsonrpc': '2.0', 'result': result, 'id': req['id']}
    except Exception as e:
        return {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': str(e)}, 'id': req.get('id')}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._send({'jsonrpc': '2.0', 'error': {'code': -32700, 'message': 'Parse error'}, 'id': None})
            return

        if isinstance(body, list):
            results = [r for r in map(dispatch, body) if r is not None]
            if results:
                self._send(results)
            else:
                self.send_response(200); self.end_headers()
        else:
            result = dispatch(body)
            if result is not None:
                self._send(result)
            else:
                self.send_response(200); self.end_headers()

    def _send(self, data):
        payload = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_): pass

HTTPServer(('', 8080), Handler).serve_forever()
```

## 인증과 보안

JSON-RPC는 프로토콜 레벨에 인증 개념이 없다. 전송 계층이나 요청 핸들러에서 직접 처리해야 한다.

**API 키**

가장 단순한 방법이다. `X-API-Key` 헤더로 받아서 핸들러 진입 전에 검사한다.

```javascript
const VALID_KEYS = new Set(process.env.API_KEYS.split(','));

function checkApiKey(headers) {
  const key = headers['x-api-key'];
  if (!key || !VALID_KEYS.has(key)) {
    return { jsonrpc: '2.0', error: { code: -32001, message: 'Unauthorized' }, id: null };
  }
  return null;
}

// 핸들러 안에서
const authError = checkApiKey(req.headers);
if (authError) { res.end(JSON.stringify(authError)); return; }
```

API 키를 환경변수에서 읽고 쉼표 구분으로 여러 개를 지원한다. 키 교체 시 구 키와 신 키를 동시에 유효 상태로 두었다가 롤아웃 후 구 키를 제거하는 방식이 편하다.

**JWT**

서버 간 통신에서 발급자·만료·권한 범위까지 토큰 안에 담을 때 쓴다.

```javascript
const jwt = require('jsonwebtoken');

function verifyBearer(headers) {
  const auth = headers['authorization'] ?? '';
  if (!auth.startsWith('Bearer ')) return null;
  try {
    return jwt.verify(auth.slice(7), process.env.JWT_SECRET, { algorithms: ['HS256'] });
  } catch {
    return null;
  }
}

// 핸들러 안에서
const claims = verifyBearer(req.headers);
if (!claims) {
  res.end(JSON.stringify({ jsonrpc: '2.0', error: { code: -32001, message: 'Unauthorized' }, id: null }));
  return;
}
// claims.sub, claims.scope 등으로 메서드별 권한 분기 가능
```

메서드별로 권한을 다르게 줄 때는 `claims.scope`에 허용 메서드 목록을 넣는 방식이 자주 쓰인다. 예를 들어 읽기 전용 클라이언트에는 `scope: "read"`, 쓰기 권한은 `scope: "write"`로 구분한다.

**IP 화이트리스트**

내부망이나 특정 서버에서만 접근을 허용할 때 쓴다. 리버스 프록시(Nginx, HAProxy) 레벨에서 처리하는 쪽이 애플리케이션 코드를 단순하게 유지한다. 애플리케이션에서 직접 처리할 때는 `X-Forwarded-For`를 신뢰 여부를 결정해야 한다.

```javascript
const ALLOWED_IPS = new Set(['127.0.0.1', '::1', '10.0.0.5']);

function checkIp(req) {
  // 리버스 프록시 뒤라면 X-Forwarded-For의 첫 번째 IP
  const forwarded = req.headers['x-forwarded-for'];
  const ip = forwarded ? forwarded.split(',')[0].trim() : req.socket.remoteAddress;
  return ALLOWED_IPS.has(ip);
}
```

`X-Forwarded-For`를 신뢰할 수 없는 환경(직접 인터넷 노출)이라면 `req.socket.remoteAddress`만 쓴다. 클라이언트가 헤더를 조작할 수 있기 때문이다.

**퍼블릭 엔드포인트에서 자주 보이는 공격**

이더리움 노드 RPC를 실수로 공개하면 `eth_sendRawTransaction`으로 잔액을 털어가거나, `debug_*`나 `admin_*` 메서드로 노드를 종료시키는 시도가 들어온다. `--http.api` 플래그로 노출할 네임스페이스를 `eth,net,web3`로 제한하고, `--http.vhosts`로 허용 도메인을 명시한다.

## 커넥션 풀과 재시도

**HTTP keep-alive 풀**

Node.js의 기본 `fetch`는 연결 재사용 설정이 없다. `http.Agent`로 풀을 만들어 넘겨야 한다.

```javascript
const http = require('http');
const https = require('https');

const agent = new http.Agent({
  keepAlive: true,
  maxSockets: 10,        // 동시 연결 상한
  maxFreeSockets: 5,     // 유휴 연결 유지 수
  keepAliveMsecs: 30000, // keep-alive 핑 간격
  timeout: 10000,
});

async function rpcCall(method, params, id, endpoint) {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', method, params, id }),
    // Node 18+에서 dispatcher로 agent를 넘기는 방법은 undici 사용
  });
  const data = await res.json();
  if (data.error) throw Object.assign(new Error(data.error.message), { code: data.error.code });
  return data.result;
}
```

Python에서는 `requests.Session`이 연결 풀을 내장한다. `urllib3.HTTPConnectionPool`의 `maxsize`가 풀 크기다.

```python
import requests

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=2, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)

def rpc_call(method, params, req_id, endpoint):
    payload = {'jsonrpc': '2.0', 'method': method, 'params': params, 'id': req_id}
    res = session.post(endpoint, json=payload, timeout=10)
    data = res.json()
    if 'error' in data:
        raise RuntimeError(f"[{data['error']['code']}] {data['error']['message']}")
    return data['result']
```

**재시도 패턴**

프로토콜 에러(`-32600`, `-32601`, `-32602`)는 재시도해도 같은 결과가 나온다. 재시도 대상은 네트워크 오류와 서버 정의 에러(`-32000` ~ `-32099`) 일부다.

```javascript
async function rpcWithRetry(method, params, id, endpoint, opts = {}) {
  const { maxRetries = 3, baseDelay = 200 } = opts;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await rpcCall(method, params, id, endpoint);
    } catch (err) {
      const isProtocolError = err.code && err.code <= -32600 && err.code >= -32603;
      if (isProtocolError || attempt === maxRetries) throw err;

      const delay = baseDelay * 2 ** attempt + Math.random() * 50; // jitter
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

jitter를 넣는 이유는 서버 장애 직후 다수 클라이언트가 동시에 재시도하면 복구 중인 서버에 스파이크가 다시 생기기 때문이다. `Math.random() * 50` 수준의 작은 jitter만으로도 충돌이 크게 줄어든다.

**타임아웃 분리**

연결 타임아웃과 읽기 타임아웃을 분리해서 설정한다. 연결은 빠르게 실패해야 하고, 읽기는 메서드 특성에 따라 다를 수 있다. `debug_traceTransaction` 같은 무거운 메서드는 수십 초가 걸리기도 한다.

## OpenRPC 명세

OpenRPC는 JSON-RPC API를 기술하는 명세 포맷이다. OpenAPI가 REST API를 기술하는 것과 같은 역할이다. 스키마가 없는 JSON-RPC의 단점을 문서·검증·코드 생성 측면에서 보완한다.

```json
{
  "openrpc": "1.2.6",
  "info": {
    "title": "계산기 API",
    "version": "1.0.0",
    "description": "덧셈과 뺄셈을 제공하는 JSON-RPC 서버"
  },
  "methods": [
    {
      "name": "add",
      "summary": "두 정수를 더한다",
      "params": [
        {
          "name": "a",
          "required": true,
          "schema": { "type": "integer" }
        },
        {
          "name": "b",
          "required": true,
          "schema": { "type": "integer" }
        }
      ],
      "result": {
        "name": "sum",
        "schema": { "type": "integer" }
      },
      "errors": [
        { "code": -32602, "message": "Invalid params" }
      ],
      "examples": [
        {
          "name": "정수 덧셈",
          "params": [
            { "name": "a", "value": 3 },
            { "name": "b", "value": 5 }
          ],
          "result": { "name": "sum", "value": 8 }
        }
      ]
    },
    {
      "name": "subtract",
      "summary": "a에서 b를 뺀다",
      "params": [
        { "name": "a", "required": true, "schema": { "type": "integer" } },
        { "name": "b", "required": true, "schema": { "type": "integer" } }
      ],
      "result": {
        "name": "difference",
        "schema": { "type": "integer" }
      }
    }
  ]
}
```

이더리움 Execution API 전체가 OpenRPC로 작성되어 있다. 실제 규모의 명세 참고 용도로 적합하다.

명세를 작성해두면 `@open-rpc/schema-utils-js`로 런타임 파라미터 검증을 붙이거나, `openrpc-generator`로 클라이언트 스텁을 생성할 수 있다. 팀 규모가 크지 않으면 문서 용도로만 써도 API 계약이 명확해지는 효과가 있다.

```bash
# openrpc playground에서 로컬 명세를 열어보기
npx @open-rpc/playground
```

## 실무에서 쓰이는 곳

**이더리움 노드 API**

이더리움 실행 계층(geth, erigon, nethermind)의 외부 API가 JSON-RPC다. `eth_`, `net_`, `web3_`, `debug_`, `admin_` 네임스페이스로 나뉜다.

```bash
# 현재 블록 번호 조회
curl -s -X POST http://localhost:8545 \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","id":1}'

# 응답
{"jsonrpc":"2.0","id":1,"result":"0x12c4567"}
```

geth는 HTTP, WebSocket, IPC(유닉스 소켓)를 동시에 열 수 있다. IPC가 로컬에서 오버헤드가 가장 적다.

**Language Server Protocol (LSP)**

VS Code, Neovim, JetBrains의 언어 서버 통신 프로토콜이 JSON-RPC 2.0 기반이다. 편집기가 클라이언트, 언어 서버(pylsp, rust-analyzer, gopls 등)가 서버다.

```
Content-Length: 154\r\n
\r\n
{"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":"file:///main.py","languageId":"python","version":1,"text":"import os\n"}}}
```

헤더에 `Content-Length`를 붙인다. HTTP가 아니라 stdin/stdout 또는 TCP 소켓으로 전송한다. JSON-RPC의 전송 독립성을 활용한 사례다.

**그 외**

- Bitcoin Core RPC: `bitcoin-cli`가 JSON-RPC로 `bitcoind`와 통신
- Solana RPC: 이더리움과 유사한 구조로 클러스터 API 제공

## gRPC와 선택 기준

두 프로토콜이 자주 비교된다. 둘 다 함수 호출 추상화를 제공하지만 선택 맥락이 다르다.

| 항목 | JSON-RPC | gRPC |
|------|----------|------|
| 직렬화 | JSON (텍스트) | Protocol Buffers (바이너리) |
| 스키마 | 없음 (선택적 OpenRPC) | `.proto` 필수 |
| HTTP | 1.1, 2.0 모두 가능 | HTTP/2 전용 |
| 브라우저 지원 | 기본 지원 | grpc-web 필요 |
| 스트리밍 | WebSocket으로 구현 | 프로토콜 수준 내장 |
| 코드 생성 | 선택 | 필수 |
| 디버깅 | curl로 바로 가능 | 전용 도구 필요 |

**JSON-RPC를 선택하는 상황**

프로토콜 명세 자체가 단순해서 구현이 빠르다. `curl`이나 브라우저 `fetch`로 바로 붙을 수 있다. 스키마가 없어서 API 변경이 자유롭다. 클라이언트가 다양한 언어와 환경에 걸쳐있고 별도 코드 생성이 부담될 때 쓴다.

블록체인 노드처럼 외부에 열어두는 공개 API, 에디터 플러그인처럼 내부 프로세스 간 통신, 프로토타입 단계에 적합하다.

**gRPC를 선택하는 상황**

서비스 간 계약을 `.proto`로 명시적으로 관리하고 싶을 때. 바이너리 직렬화로 페이로드 크기를 줄여야 할 때. 서버 스트리밍이나 양방향 스트리밍이 필요할 때. 생성된 클라이언트 스텁으로 타입 안전성을 확보하고 싶을 때.

마이크로서비스 내부 통신, 고트래픽 서비스 간 통신, 다국어 팀에서 API 계약을 공유할 때 선택한다.

JSON-RPC를 쓰다가 gRPC로 넘어가야 할 신호는 명확하다. 페이로드가 커서 직렬화 비용이 병목이거나, `.proto` 없이 관리하면 API 계약이 흐려지는 시점이다.
