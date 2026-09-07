---
title: JSON-RPC
tags: [network, http, tcp, api, backend, grpc]
updated: 2026-09-07
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

이더리움 노드에서 블록 데이터를 수집할 때 배치를 쓰면 왕복 지연을 크게 줄인다. 다만 노드마다 배치 크기 제한이 다르다. Infura는 기본 1,000, Alchemy는 100이다.

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
- OpenRPC: JSON-RPC API 명세 표준. OpenAPI의 JSON-RPC 버전에 해당

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
