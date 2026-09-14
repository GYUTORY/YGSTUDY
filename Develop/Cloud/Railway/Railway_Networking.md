---
title: Railway 네트워킹
tags: [cloud, backend, docker, devops, network, http, proxy]
updated: 2026-09-14
---

# Railway 네트워킹

## 프로젝트 내부 네트워크

Railway 프로젝트 안에서 서비스끼리 통신할 때 퍼블릭 인터넷을 거치지 않는다. 각 서비스는 자동으로 `.railway.internal` 도메인을 받고, 이 도메인은 프로젝트 내부 네트워크에서만 해석된다.

형식은 `{서비스명}.railway.internal`이다. 서비스 이름에 공백이 있으면 하이픈으로 바뀐다. `api-server`라는 서비스는 `api-server.railway.internal`로 접근한다.

```env
DATABASE_URL=postgresql://user:password@postgres.railway.internal:5432/mydb
REDIS_URL=redis://redis.railway.internal:6379
```

퍼블릭 도메인으로 서비스 간 통신하면 Railway CDN을 타고 돌아온다. 레이턴시도 늘고 불필요한 트래픽 비용도 붙는다. 같은 프로젝트 안에서는 `.railway.internal`만 쓴다.

### 포트 번호

`.railway.internal`을 쓸 때 포트는 서비스가 실제로 바인딩하는 값 그대로다. Railway가 `PORT` 환경변수를 자동으로 주입하는데, 앱이 이 값을 읽어서 리슨해야 한다. `app.listen(3000)`처럼 하드코딩하면 Railway가 주입한 포트와 불일치가 생겨 헬스체크에서 죽는다.

```javascript
const port = process.env.PORT || 3000;
app.listen(port);
```

## 포트 충돌이 없는 이유

Docker 네트워크 격리 때문이다. Railway의 각 서비스는 별도 컨테이너로 실행되고, 각 컨테이너에는 독립된 네트워크 네임스페이스가 있다. A 서비스가 8080에서 리슨하고 B 서비스도 8080에서 리슨해도 서로 다른 네임스페이스에 있어서 충돌이 없다.

`.railway.internal` 도메인 해석도 Railway 내부 DNS가 서비스 이름을 컨테이너 IP로 매핑하는 구조라, 포트는 각 컨테이너 기준이다. PostgreSQL, Redis, 앱 서버를 전부 같은 포트로 띄워도 문제가 없다.

## 리버스 프록시 타임아웃

Railway는 퍼블릭 트래픽 앞에 리버스 프록시를 세운다. 이 프록시의 기본 요청 타임아웃은 5분(300초)다. 서버가 5분 안에 응답을 돌려주지 못하면 프록시가 연결을 끊고 클라이언트에 502 또는 504를 보낸다.

문제가 생기는 지점은 대용량 파일 처리, 장시간 데이터 집계, AI 모델 추론처럼 응답이 늦는 작업이다. 서버가 내부적으로 완료하더라도 5분을 넘기면 클라이언트는 이미 에러를 받은 상태다.

우회 방법은 두 가지다.

작업을 비동기로 분리한다. 요청을 받으면 즉시 작업 ID를 반환하고, 클라이언트가 주기적으로 상태를 폴링하거나 WebSocket으로 결과를 받는 구조로 바꾼다.

스트리밍 응답(SSE, chunked transfer)을 쓴다. 서버가 데이터를 조각으로 계속 보내면 프록시는 응답이 진행 중이라고 판단해 타임아웃을 적용하지 않는다. 단, 청크가 아예 안 오는 상태로 5분이 지나면 마찬가지로 끊긴다. SSE 구현에서 주기적으로 keepalive 청크를 보내야 하는 이유가 이 때문이다.

```javascript
// SSE에서 keepalive를 보내지 않으면 5분 후 프록시가 연결을 끊는다
res.setHeader('Content-Type', 'text/event-stream');
res.setHeader('Cache-Control', 'no-cache');

const keepalive = setInterval(() => {
  res.write(': keepalive\n\n');
}, 25000);  // 25초마다. 30초를 넘기면 위험하다

req.on('close', () => clearInterval(keepalive));
```

## WebSocket과 Long-polling

Railway는 WebSocket을 지원한다. 초기 HTTP Upgrade 핸드셰이크가 완료되면 그 이후는 HTTP 타임아웃 규칙이 적용되지 않는다. WebSocket 연결은 클라이언트나 서버가 명시적으로 닫거나 Railway가 서비스를 재시작할 때까지 유지된다.

연결이 idle 상태로 오래 유지되면 중간 인프라가 연결을 끊을 수 있다. 클라이언트와 서버 양쪽에서 주기적으로 ping/pong을 교환해야 한다. 30초 간격이 안전하다.

```javascript
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: process.env.PORT });

wss.on('connection', (ws) => {
  const interval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.ping();
    }
  }, 30000);

  ws.on('close', () => clearInterval(interval));
});
```

Long-polling은 다르다. HTTP 요청을 서버가 응답 없이 붙잡고 있는 구조라 5분 타임아웃이 그대로 적용된다. 서버 이벤트를 5분 이상 기다리는 Long-polling 요청은 타임아웃으로 끊긴다. 서버 측에서 4분 정도에서 명시적으로 빈 응답을 반환하고 클라이언트가 다시 연결하도록 설계해야 한다.

```javascript
// Long-polling 서버 측: 5분 전에 먼저 응답을 반환한다
app.get('/poll', async (req, res) => {
  const timeout = 4 * 60 * 1000;  // 4분
  const deadline = Date.now() + timeout;

  while (Date.now() < deadline) {
    const event = await checkForEvent();
    if (event) return res.json(event);
    await sleep(1000);
  }

  res.json({ type: 'timeout' });  // 클라이언트가 재연결한다
});
```

Railway에서 실시간 양방향 통신이 필요하면 WebSocket을 쓰는 게 낫다. Long-polling은 타임아웃 관리가 복잡하다.

## 퍼블릭 도메인

### 자동 생성 도메인

서비스에 퍼블릭 엔드포인트를 붙이면 Railway가 `{랜덤}-production.up.railway.app` 형식의 도메인을 자동으로 만든다. HTTPS가 기본으로 붙고, 인증서 관리는 Railway가 처리한다.

자동 도메인은 서비스를 삭제하고 다시 만들면 주소가 바뀐다. 외부 시스템이 이 주소를 하드코딩했다면 깨진다. 웹훅 URL이나 OAuth 리다이렉트 URL에 자동 도메인을 쓰면 이런 상황이 생긴다.

### 커스텀 도메인 연결

Railway 대시보드에서 커스텀 도메인을 추가하면 CNAME 레코드 값을 알려준다. DNS 제공자에서 이 CNAME을 설정하면 인증서 발급까지 자동으로 처리된다.

```
CNAME: {서비스명}.up.railway.app
```

CNAME 전파는 5분에서 최대 48시간까지 걸린다. Railway 대시보드의 "Verify DNS" 버튼이 전파 전에는 계속 실패로 나온다. 기다리면 자동으로 통과된다.

루트 도메인(`example.com`)에는 CNAME을 쓸 수 없다는 DNS 스펙 제약이 있다. Cloudflare의 CNAME Flattening이나 AWS Route53의 ALIAS 레코드로 해결한다. 일반 호스팅 제공자에서 루트 도메인을 Railway에 붙이려면 이 제약을 먼저 확인해야 한다.

## TCP Proxy

HTTP가 아닌 프로토콜을 쓰는 서비스—PostgreSQL, Redis, MySQL 등—를 외부에서 직접 접속하려면 TCP Proxy를 활성화해야 한다.

서비스의 "Settings" > "Networking" 탭에서 TCP Proxy를 켜면 두 가지를 준다.

- 호스트: `roundhouse.proxy.rlwy.net` 형식의 주소
- 포트: 랜덤 5자리 포트 번호

```
postgresql://user:password@roundhouse.proxy.rlwy.net:12345/mydb
```

데이터베이스 GUI 툴이나 외부 서버에서 마이그레이션을 돌릴 때 이 주소를 쓴다. 구조는 외부 → TCP Proxy → 내부 컨테이너 포트 순서다.

### 연결 수 제한

TCP Proxy는 동시 연결 수에 상한이 있다. Railway가 플랜별 정확한 수치를 문서화하지는 않지만, Hobby 플랜 기준으로 동시 연결이 수십 개를 넘는 시점부터 새 연결 거부나 기존 연결 강제 종료가 나타난다.

프로덕션 데이터베이스를 외부에서 상시 연결하는 용도로는 적합하지 않다. 개발 도구에서 세션을 여러 개 열어두거나, 부하 테스트를 TCP Proxy 경유로 돌리면 금방 한도에 걸린다.

연결 수를 줄이려면 PgBouncer를 Railway 서비스로 추가하고, 앱과 외부 도구 모두 PgBouncer를 통해 DB에 붙는 구조로 바꾼다.

```
앱 서버       → postgres.railway.internal:5432 → PgBouncer → PostgreSQL
외부 도구     → TCP Proxy → PgBouncer → PostgreSQL
```

PgBouncer의 transaction pooling 모드를 쓰면 실제 PostgreSQL 연결 수를 앱 인스턴스 수와 무관하게 일정하게 유지할 수 있다. 단, transaction pooling은 `SET` 명령이나 prepared statement를 세션 수준에서 유지하지 않아서 ORM과의 호환성을 먼저 확인해야 한다.

### SSL 처리

TCP Proxy 레벨의 SSL 처리에는 Railway가 관여하지 않는다. PostgreSQL의 경우 `sslmode=require`를 쓰면 데이터베이스 자체의 SSL 설정을 따른다. Postgres가 SSL을 비활성화한 상태면 연결이 실패한다.

```
postgresql://user:password@proxy-host:port/db?sslmode=disable
```

로컬 개발에서 Railway 데이터베이스에 붙을 때 `sslmode=disable`로 시작해서 연결부터 확인하는 게 빠르다.

## Rate Limit

Railway는 애플리케이션 레벨 rate limit을 제공하지 않는다. 인프라 레벨에서 기본적인 트래픽 차단 정도는 있지만, 특정 IP나 사용자의 요청 빈도를 제한하는 건 앱에서 직접 구현해야 한다.

인스턴스가 여러 개라면 인메모리 카운터로는 제한이 안 된다. 각 인스턴스가 독립적으로 카운터를 관리해서 실제로는 인스턴스 수만큼 한도가 늘어난다. Redis를 카운터 스토리지로 쓰는 것이 표준이다.

```javascript
const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');
const { createClient } = require('redis');

const redisClient = createClient({ url: process.env.REDIS_URL });
await redisClient.connect();

const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  store: new RedisStore({
    sendCommand: (...args) => redisClient.sendCommand(args),
  }),
});

app.use('/api', limiter);
```

Railway 서비스 앞에 Cloudflare를 두면 Cloudflare의 rate limiting 규칙을 쓸 수 있다. Railway 도메인 대신 Cloudflare에 연결한 커스텀 도메인으로 트래픽을 받고, Cloudflare에서 IP 기반 요청 제한을 설정하면 앱 서버까지 도달하는 트래픽 자체를 줄인다. 크롤러나 무차별 요청을 막을 때 이 구조가 효과적이다.

## 멀티 리전 배포

Railway는 하나의 서비스를 여러 리전에 동시에 배포하는 기능이 없다. 서비스는 생성 시 선택한 단일 리전에서만 실행된다. 리전 간 자동 장애 조치나 지리 기반 라우팅을 Railway 자체에서 처리하지 않는다.

지원 리전은 US West(Oregon), US East(Virginia), EU West(Frankfurt)다. 아시아 리전은 없다. 한국에서 접근하면 US West 기준 왕복 150~180ms 정도 레이턴시가 생긴다. 관리 도구나 사이드 프로젝트는 문제가 안 되지만, 실시간 요구사항이 있는 서비스에는 병목이 된다.

실행 중인 서비스를 다른 리전으로 옮기는 기능도 없다. 리전을 바꾸려면 서비스를 삭제하고 새 리전에 다시 만들어야 한다. 서비스에 볼륨이 붙어 있으면 데이터 마이그레이션도 별도로 처리해야 한다.

멀티 리전이 필요한 경우, 리전별로 별도 Railway 프로젝트를 만들고 앞에 Cloudflare Load Balancing 같은 외부 로드 밸런서를 두어 지리적으로 가까운 프로젝트로 트래픽을 보내는 구조가 현실적이다. 단, 이 경우 프로젝트별로 데이터베이스가 분리되므로 데이터 동기화 문제가 따라온다.

## 서비스 참조로 주소 주입

Railway의 서비스 참조(Service References) 기능으로 다른 서비스의 환경변수를 가져온다. `${{서비스명.변수명}}` 문법을 쓴다.

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

Railway가 자동으로 주입하는 변수도 있다.

```env
RAILWAY_PRIVATE_DOMAIN=api-server.railway.internal
RAILWAY_PUBLIC_DOMAIN=api-server-production.up.railway.app
PORT=3000
```

서비스 이름을 바꾸면 `RAILWAY_PRIVATE_DOMAIN`도 바뀐다. 다른 서비스에서 `.railway.internal` 주소를 하드코딩했다면 이름 변경 시 같이 수정해야 한다.
