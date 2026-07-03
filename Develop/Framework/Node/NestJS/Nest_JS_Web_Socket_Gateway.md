---
title: NestJS WebSocket Gateway 운영기
tags: [nestjs, websocket, socket.io, redis-adapter, realtime, gateway]
updated: 2026-05-20
---

# NestJS WebSocket Gateway 운영기

REST로 알림을 폴링하던 서비스가 모바일에서 배터리 문제를 일으키면서 WebSocket을 붙였다. NestJS의 `@WebSocketGateway`는 처음엔 `@Controller`처럼 익숙해 보이는데, 막상 다중 인스턴스 환경에 올리면 "내 메시지가 다른 서버에 붙은 사용자한테 안 간다"는 버그가 가장 먼저 터진다. 이 문서는 NestJS에서 WebSocket을 실서비스에 올리면서 부딪힌 지점들을 정리한다.

HTTP 요청 라이프사이클은 [Nest_JS_요청_라이프사이클.md](Nest_JS_요청_라이프사이클.md)에서 다루고, 본 문서는 그 위에 양방향 통신 레이어가 어떻게 얹히는지에 집중한다.


## Gateway가 컨트롤러와 다른 점

`@WebSocketGateway()`는 NestJS가 WebSocket 연결을 모듈에 묶기 위한 데코레이터다. 컨트롤러처럼 의존성 주입을 받고 같은 라이프사이클을 따르는데, 결정적으로 다른 점이 두 가지 있다.

첫째, 요청-응답이 1:1로 끝나지 않는다. 한 연결 안에서 여러 이벤트가 양방향으로 오간다. 그래서 메서드 하나가 응답을 반환해도 호출한 클라이언트한테만 가지 다른 사용자한테는 안 간다. 브로드캐스트가 필요하면 `server.emit()`이나 룸 단위 emit을 명시적으로 해야 한다.

둘째, 게이트웨이 인스턴스는 싱글톤이고 클라이언트 상태는 `Socket` 객체에 묶인다. 컨트롤러는 요청마다 새 컨텍스트가 만들어지지만 게이트웨이는 연결이 살아있는 동안 같은 핸들러가 반복 호출된다. 그래서 클라이언트별 상태(세션, 권한, 구독 중인 채널)는 `client.data`에 박아두거나 외부 저장소(Redis)에 두는 게 안전하다.

```typescript
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  MessageBody,
  ConnectedSocket,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';

@WebSocketGateway({
  cors: { origin: process.env.ALLOWED_ORIGIN?.split(',') ?? false },
  pingInterval: 25000,
  pingTimeout: 60000,
})
export class ChatGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  handleConnection(client: Socket) {
    // 인증·룸 조인은 여기서 처리한다
  }

  handleDisconnect(client: Socket) {
    // 룸 leave, presence 정리
  }

  @SubscribeMessage('chat:send')
  onSend(
    @MessageBody() payload: { room: string; text: string },
    @ConnectedSocket() client: Socket,
  ) {
    this.server.to(payload.room).emit('chat:message', {
      from: client.data.userId,
      text: payload.text,
      at: Date.now(),
    });
  }
}
```

`pingInterval`과 `pingTimeout`은 기본값(25s/20s)으로 두면 모바일에서 백그라운드 진입 시 좀비 커넥션이 쌓인다. `pingTimeout`을 늘려도 모바일 OS가 소켓을 끊으면 어차피 재연결이 일어나므로, 백엔드 입장에선 좀비를 빨리 털어내는 쪽이 메모리에 유리하다.


## 어댑터 선택: socket.io vs ws

NestJS는 `WebSocketAdapter` 추상화 위에 동작한다. 기본 어댑터는 `IoAdapter`(socket.io), 더 가벼운 옵션으로 `WsAdapter`(ws)가 있다.

**socket.io**는 자동 재연결, 룸/네임스페이스, fallback 폴링, 바이너리 전송, ack 콜백까지 다 들어있다. 대신 클라이언트도 같은 버전의 socket.io를 써야 한다. 표준 WebSocket 클라이언트(브라우저 `WebSocket`, 일부 IoT 라이브러리)는 못 붙는다.

**ws**는 표준 WebSocket 프로토콜(RFC 6455)만 다룬다. 룸/네임스페이스가 없어서 직접 구현해야 한다. 대신 라이브러리 크기가 작고 비표준 클라이언트도 붙는다.

실서비스 양방향 통신이라면 socket.io가 거의 정답이다. ws는 표준 클라이언트를 강제로 받아야 하는 IoT, 게임 서버, 외부 파트너 연동에서만 선택했다.

```typescript
// main.ts — socket.io 어댑터 (기본값이라 명시 안 해도 됨)
import { IoAdapter } from '@nestjs/platform-socket.io';

const app = await NestFactory.create(AppModule);
app.useWebSocketAdapter(new IoAdapter(app));

// ws 어댑터로 바꾸려면
import { WsAdapter } from '@nestjs/platform-ws';
app.useWebSocketAdapter(new WsAdapter(app));
```

ws 어댑터를 쓰면 `@WebSocketGateway()`에 path를 지정하고 `@SubscribeMessage('event')` 대신 JSON payload의 `event` 필드를 직접 파싱해야 한다. 게이트웨이 코드가 socket.io 기준으로 짜여있다면 마이그레이션 비용이 꽤 든다.

socket.io v4와 클라이언트 v2~v3는 프로토콜이 호환되지 않는다. 기존 모바일 앱이 socket.io v2 클라이언트로 박혀있으면 서버에서 `allowEIO3: true` 옵션을 켜야 한다.

```typescript
@WebSocketGateway({
  cors: true,
  allowEIO3: true, // socket.io v2/v3 클라이언트 호환
})
```


## 네임스페이스와 룸

socket.io에서 네임스페이스와 룸은 자주 헷갈리는데 역할이 다르다.

**네임스페이스**는 URL path 수준의 분리다. `/chat`, `/notification`, `/admin` 같은 식으로 갈라서 게이트웨이 자체를 다른 인스턴스로 둘 수 있다. 각 네임스페이스는 독립된 이벤트 핸들러, 미들웨어, 인증 정책을 가진다. 클라이언트는 `io('https://api.example.com/chat')` 처럼 path를 지정해 연결한다.

**룸**은 네임스페이스 안에서 클라이언트를 묶는 동적 그룹이다. 채팅방, 사용자별 알림 채널, 문서 협업 세션 같은 단위로 쓴다. 룸은 메모리 위 `Map<string, Set<socketId>>`이라 만들고 지우는 비용이 거의 없다.

```typescript
@WebSocketGateway({ namespace: '/chat', cors: true })
export class ChatGateway {
  @WebSocketServer()
  server: Server;

  @SubscribeMessage('room:join')
  async joinRoom(
    @MessageBody() { roomId }: { roomId: string },
    @ConnectedSocket() client: Socket,
  ) {
    const allowed = await this.chatService.canJoin(client.data.userId, roomId);
    if (!allowed) throw new WsException('forbidden');

    await client.join(roomId);
    this.server.to(roomId).emit('room:joined', { userId: client.data.userId });
  }

  @SubscribeMessage('room:leave')
  async leaveRoom(
    @MessageBody() { roomId }: { roomId: string },
    @ConnectedSocket() client: Socket,
  ) {
    await client.leave(roomId);
    this.server.to(roomId).emit('room:left', { userId: client.data.userId });
  }
}
```

룸에 들어갈 권한은 반드시 서버에서 검증해야 한다. 클라이언트가 `room:join`을 부르면 서버가 DB나 캐시를 봐서 멤버십을 확인한 뒤에야 `client.join()`을 호출해야 한다. 권한 체크 없이 룸에 조인시키면 채팅방 ID만 알아내면 누구나 메시지를 수신할 수 있는 구조가 된다.

사용자별 개인 채널이 필요하면 `room = "user:" + userId` 같은 컨벤션으로 룸을 쓰는 게 편하다. 사용자가 동시에 PC, 모바일, 태블릿에 접속해 있어도 같은 룸에 다 들어있으니 한 번 emit으로 모든 디바이스로 푸시된다.

```typescript
handleConnection(client: Socket) {
  const userId = client.data.userId;
  client.join(`user:${userId}`);
}

// 특정 사용자에게 알림
this.server.to(`user:${userId}`).emit('notification', payload);
```


## 인증: 핸드셰이크에서 끝내라

WebSocket 인증은 HTTP와 달리 매 메시지마다 토큰을 검증하지 않는다. 첫 연결 핸드셰이크에서 한 번 검증하고, 통과한 소켓은 신뢰하는 모델이다. 그래서 인증 실패는 메시지 거부가 아니라 연결 거부로 처리해야 한다.

토큰은 보통 세 가지 위치에 넣는다.

1. **`auth` 페이로드**(socket.io v3+ 권장): `io(url, { auth: { token } })`로 보내는 방식. 쿼리스트링과 달리 서버 로그에 남지 않는다.
2. **쿠키**: 같은 도메인의 HTTP 세션을 그대로 쓸 때 유용하다. CORS·SameSite 설정을 정확히 맞춰야 한다.
3. **쿼리스트링**: 가장 간단한데 토큰이 access log에 그대로 박히므로 운영 환경에선 피한다.

NestJS에선 socket.io의 미들웨어 패턴을 게이트웨이 라이프사이클 훅에 녹여 쓴다. `afterInit`에서 namespace 미들웨어를 등록하면 핸들러 호출 전에 인증을 강제할 수 있다.

```typescript
import { OnGatewayInit } from '@nestjs/websockets';
import { JwtService } from '@nestjs/jwt';

@WebSocketGateway({ namespace: '/chat' })
export class ChatGateway implements OnGatewayInit, OnGatewayConnection {
  constructor(private readonly jwt: JwtService) {}

  @WebSocketServer()
  server: Server;

  afterInit(server: Server) {
    server.use(async (socket, next) => {
      try {
        const token =
          socket.handshake.auth?.token ??
          socket.handshake.headers['authorization']?.replace('Bearer ', '');

        if (!token) return next(new Error('unauthorized'));

        const payload = await this.jwt.verifyAsync(token);
        socket.data.userId = payload.sub;
        socket.data.roles = payload.roles ?? [];
        next();
      } catch (err) {
        next(new Error('invalid token'));
      }
    });
  }

  handleConnection(client: Socket) {
    // 여기 도달했다면 인증된 클라이언트다
    client.join(`user:${client.data.userId}`);
  }
}
```

`server.use()` 미들웨어가 `next(error)`로 끊으면 클라이언트는 `connect_error` 이벤트를 받는다. 에러 메시지가 그대로 노출되므로 "invalid token", "user not found" 같은 내부 정보는 빼고 `unauthorized`로 통일하는 쪽이 안전하다.

NestJS Guard(`CanActivate`)를 게이트웨이에 붙일 수도 있는데, Guard는 메시지 단위로만 동작한다. 핸드셰이크 차단은 못 한다. 그래서 첫 연결 인증은 미들웨어, 메시지별 권한 체크는 Guard로 역할을 나눈다.

```typescript
@UseGuards(WsRolesGuard)
@SubscribeMessage('admin:broadcast')
adminBroadcast(@MessageBody() payload: any) { /* ... */ }
```

JWT 만료 처리도 신경 써야 한다. 핸드셰이크 시점엔 유효했던 토큰이 한 시간 뒤에는 만료된다. WebSocket은 그동안 계속 살아있다. 권한 변경이나 강제 로그아웃 같은 이벤트가 있으면 별도 채널(Redis pub/sub)로 게이트웨이가 받아서 해당 소켓을 끊어야 한다.

```typescript
async revokeUser(userId: string) {
  const sockets = await this.server.in(`user:${userId}`).fetchSockets();
  for (const s of sockets) s.disconnect(true);
}
```


## 다중 인스턴스: Redis Adapter

서버 인스턴스가 둘 이상이면 메모리 기반 룸으로는 메시지가 안 닿는다. 인스턴스 A에 붙은 사용자가 보낸 메시지가 인스턴스 B에 붙은 사용자한테는 절대 안 간다. 이 문제는 socket.io의 Redis Adapter로 푼다.

```bash
npm i @socket.io/redis-adapter ioredis
```

```typescript
// redis-io.adapter.ts
import { IoAdapter } from '@nestjs/platform-socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { ServerOptions } from 'socket.io';
import Redis from 'ioredis';
import { INestApplicationContext } from '@nestjs/common';

export class RedisIoAdapter extends IoAdapter {
  private adapterConstructor: ReturnType<typeof createAdapter>;

  constructor(app: INestApplicationContext) {
    super(app);
  }

  async connectToRedis(url: string) {
    const pub = new Redis(url);
    const sub = pub.duplicate();
    await Promise.all([pub.ping(), sub.ping()]);
    this.adapterConstructor = createAdapter(pub, sub);
  }

  createIOServer(port: number, options?: ServerOptions): any {
    const server = super.createIOServer(port, options);
    server.adapter(this.adapterConstructor);
    return server;
  }
}
```

```typescript
// main.ts
const app = await NestFactory.create(AppModule);
const redisAdapter = new RedisIoAdapter(app);
await redisAdapter.connectToRedis(process.env.REDIS_URL);
app.useWebSocketAdapter(redisAdapter);
```

Redis Adapter가 하는 일은 pub/sub 채널 두 개를 빌려 인스턴스 간 emit을 중계하는 것뿐이다. 메시지 페이로드가 통째로 Redis를 거치므로 대용량 바이너리를 보낼 때는 부하를 측정해야 한다. 우리 사례에서는 평균 페이로드 1~2KB, 초당 5천 메시지 환경에서 Redis CPU가 15%대로 안정적이었다.

ioredis 클러스터 모드에서는 pub/sub이 슬롯 하나에 묶이는 점을 조심해야 한다. 클러스터 노드 6개에 분산해도 socket.io 어댑터 트래픽은 한 노드에 쏠린다. 알림 트래픽이 크면 클러스터 대신 단일 노드 + 레플리카 구성이 운영하기 더 쉽다.

Redis가 잠깐 끊겼다 붙으면 그 사이 emit은 유실된다. 메시지 영속성이 필요하면 DB나 Stream에 먼저 쓰고 그 다음 emit하는 패턴을 쓴다. 채팅처럼 메시지 유실이 사용자 신뢰를 망가뜨리는 영역에서는 필수다.

```typescript
@SubscribeMessage('chat:send')
async onSend(@MessageBody() dto: SendDto, @ConnectedSocket() client: Socket) {
  const saved = await this.chatRepo.insert({
    roomId: dto.roomId,
    senderId: client.data.userId,
    text: dto.text,
  });

  this.server.to(dto.roomId).emit('chat:message', saved);
  return { ok: true, id: saved.id }; // ack 콜백
}
```

DB에 저장된 다음에 emit하는 순서를 지키면, Redis가 끊겨도 클라이언트는 재연결 후 `chat:since` 같은 이벤트로 누락분을 가져갈 수 있다.


## 연결 끊김과 재연결

socket.io 클라이언트는 기본적으로 자동 재연결을 시도한다. 백오프는 1초에서 시작해 최대 5초까지 늘어나며 무한 재시도한다. 서버 입장에선 한 사용자가 30초 동안 재연결을 반복하면 같은 사용자에서 다섯 번의 connect/disconnect 이벤트를 받는다. 이 점을 모르고 connect마다 DB 트랜잭션을 돌리면 부하가 폭증한다.

연결 안정성을 잡는 포인트는 세 가지다.

**Sticky session**: 로드밸런서가 같은 클라이언트를 같은 인스턴스로 보내야 한다. socket.io는 long-polling으로 fallback할 때 같은 인스턴스에 붙어야 핸드셰이크가 완성된다. AWS ALB는 stickiness를 켜고, Nginx는 `ip_hash`나 `upstream_hash $cookie_io` 같은 식으로 잡는다.

**Heartbeat 튜닝**: 모바일 백그라운드, 와이파이→LTE 전환, NAT 타임아웃 같은 상황에서 좀비 커넥션이 생긴다. `pingInterval: 25000`, `pingTimeout: 20000`이 기본인데 모바일이 많으면 `pingTimeout`을 30~60초로 늘리고 `pingInterval`은 그대로 두는 게 균형이 좋았다.

**재연결 후 상태 복구**: 클라이언트는 재연결하면 새 socket.id를 받는다. 룸 멤버십도 다 풀려있다. 그래서 클라이언트는 connect 이벤트가 올 때마다 어떤 룸에 있어야 하는지를 다시 알려야 한다. 서버 쪽도 핸드셰이크에서 사용자의 활성 룸 목록을 DB/캐시에서 읽어 자동으로 조인시키는 패턴이 깔끔하다.

```typescript
async handleConnection(client: Socket) {
  const userId = client.data.userId;
  const activeRooms = await this.presenceService.getRoomsOf(userId);
  for (const roomId of activeRooms) {
    await client.join(roomId);
  }
  client.emit('connect:ready', { rooms: activeRooms });
}
```

재연결 시 메시지 유실은 `since` 패턴으로 처리한다. 클라이언트가 마지막으로 받은 메시지의 id나 timestamp를 보관하고, 재연결 후 `chat:since` 이벤트로 그 이후 메시지를 요청한다. 서버는 DB에서 해당 구간을 읽어 응답한다.

```typescript
@SubscribeMessage('chat:since')
async since(
  @MessageBody() { roomId, lastId }: { roomId: string; lastId: number },
  @ConnectedSocket() client: Socket,
) {
  const messages = await this.chatRepo.findSince(roomId, lastId);
  return { messages };
}
```


## 채팅 구현 예제

채팅방, 메시지 전송, 읽음 처리까지 들어간 게이트웨이 예제다. 단순화를 위해 인증 미들웨어는 위 코드를 그대로 쓴다고 가정한다.

```typescript
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
  MessageBody,
  ConnectedSocket,
  WsException,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { ChatService } from './chat.service';

@WebSocketGateway({ namespace: '/chat', cors: true })
export class ChatGateway implements OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  constructor(private readonly chat: ChatService) {}

  async handleConnection(client: Socket) {
    const userId = client.data.userId;
    client.join(`user:${userId}`);

    const rooms = await this.chat.findActiveRooms(userId);
    for (const r of rooms) await client.join(`room:${r.id}`);

    this.server.to(rooms.map((r) => `room:${r.id}`)).emit('presence:online', {
      userId,
    });
  }

  async handleDisconnect(client: Socket) {
    const userId = client.data.userId;
    if (!userId) return;

    const sockets = await this.server.in(`user:${userId}`).fetchSockets();
    if (sockets.length === 0) {
      this.server.emit('presence:offline', { userId });
    }
  }

  @SubscribeMessage('chat:send')
  async send(
    @MessageBody() dto: { roomId: string; text: string; clientMsgId: string },
    @ConnectedSocket() client: Socket,
  ) {
    if (!dto.text?.trim()) throw new WsException('empty message');
    if (dto.text.length > 2000) throw new WsException('too long');

    const allowed = await this.chat.canSend(client.data.userId, dto.roomId);
    if (!allowed) throw new WsException('forbidden');

    const saved = await this.chat.save({
      roomId: dto.roomId,
      senderId: client.data.userId,
      text: dto.text,
      clientMsgId: dto.clientMsgId,
    });

    this.server.to(`room:${dto.roomId}`).emit('chat:message', saved);
    return { ok: true, id: saved.id, at: saved.createdAt };
  }

  @SubscribeMessage('chat:read')
  async read(
    @MessageBody() { roomId, messageId }: { roomId: string; messageId: number },
    @ConnectedSocket() client: Socket,
  ) {
    await this.chat.markRead(client.data.userId, roomId, messageId);
    this.server.to(`room:${roomId}`).emit('chat:read', {
      userId: client.data.userId,
      messageId,
    });
  }
}
```

몇 가지 실무에서 빼먹기 쉬운 포인트.

`clientMsgId`는 클라이언트가 발급하는 멱등성 키다. 재전송이 발생해도 같은 키면 서버에서 중복 저장을 막는다. 모바일 환경에서 네트워크 끊김 직전에 보낸 메시지가 ack를 못 받고 재전송될 때를 대비한다.

발송자에게도 같은 룸으로 emit한다. 자신이 보낸 메시지를 자기 화면에 다시 그릴 때 서버가 부여한 id와 timestamp를 받기 위해서다. 별도로 `socket.broadcast.to()`를 써서 발송자를 제외하면 클라이언트 코드가 더 복잡해진다.

ack 콜백(`return { ok, id, at }`)은 socket.io의 기본 기능이다. 클라이언트에서 `socket.emit('chat:send', dto, (ack) => { ... })` 형태로 받는다. timeout을 클라이언트 쪽에 둬서 5초 안에 ack가 안 오면 실패로 표시하는 패턴을 쓴다.

presence(접속 상태)는 `fetchSockets()`로 확인한다. 사용자가 동시 접속을 5개까지 허용한다면, 한 소켓이 끊겨도 다른 4개가 살아있으면 offline 이벤트를 쏘면 안 된다.


## 알림 구현 예제

알림은 채팅과 달리 한 방향이고, 송신은 보통 HTTP 핸들러나 백그라운드 잡에서 일어난다. 그래서 게이트웨이는 emit 진입점만 제공하고, 비즈니스 로직은 서비스에 둔다.

```typescript
@Injectable()
export class NotificationService {
  constructor(
    @Inject('NOTIFICATION_GATEWAY')
    private readonly gateway: NotificationGateway,
    private readonly repo: NotificationRepo,
  ) {}

  async push(userId: string, payload: NotificationPayload) {
    const saved = await this.repo.insert({ userId, ...payload });
    this.gateway.sendToUser(userId, saved);
    return saved;
  }
}

@WebSocketGateway({ namespace: '/notification' })
export class NotificationGateway implements OnGatewayConnection {
  @WebSocketServer()
  server: Server;

  handleConnection(client: Socket) {
    client.join(`user:${client.data.userId}`);
  }

  sendToUser(userId: string, payload: any) {
    this.server.to(`user:${userId}`).emit('notification', payload);
  }

  @SubscribeMessage('notification:ack')
  async ack(
    @MessageBody() { id }: { id: number },
    @ConnectedSocket() client: Socket,
  ) {
    // 클라이언트가 받았다고 표시한 시점에 읽음 처리
  }
}
```

HTTP 컨트롤러에서 호출하는 흐름은 이렇다.

```typescript
@Post('orders/:id/ship')
async ship(@Param('id') id: string) {
  const order = await this.orderService.ship(id);
  await this.notificationService.push(order.userId, {
    type: 'order.shipped',
    title: '주문이 발송되었습니다',
    orderId: id,
  });
  return order;
}
```

알림은 사용자가 오프라인일 때를 반드시 고려해야 한다. 게이트웨이로 emit해도 받는 소켓이 없으면 메시지는 사라진다. DB에 먼저 저장한 다음 emit하면, 사용자가 재접속했을 때 안 읽은 알림을 따로 조회해서 보여줄 수 있다. emit은 실시간 전달용, DB는 영속성용으로 역할을 나눠야 한다.

푸시 알림(FCM, APNs)과 WebSocket 알림은 보완 관계다. 사용자가 앱을 켜놓고 있으면 WebSocket으로, 백그라운드면 푸시로 보낸다. WebSocket으로 보낸 알림에 클라이언트가 일정 시간 안에 ack를 안 보내면 푸시로 fallback하는 패턴도 자주 쓴다.


## 에러 처리와 예외 필터

`WsException`은 HTTP의 `HttpException`에 대응한다. throw하면 socket.io는 ack 콜백의 첫 인자로 에러를 넘긴다. 클라이언트에서 `socket.emit('event', dto, ([err, data]) => ...)`로 받는다.

기본 동작은 `WsException`의 메시지를 그대로 클라이언트에 보낸다. 에러 메시지가 내부 구조를 노출할 위험이 있으면 예외 필터를 붙여 표준화한다.

```typescript
import { Catch, ArgumentsHost } from '@nestjs/common';
import { BaseWsExceptionFilter } from '@nestjs/websockets';

@Catch()
export class WsAllExceptionFilter extends BaseWsExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const client = host.switchToWs().getClient<Socket>();
    const data = host.switchToWs().getData();

    const message =
      exception instanceof WsException
        ? exception.getError()
        : 'internal error';

    client.emit('error', { code: 'ERR', message, event: data?.event });
  }
}

// main.ts
app.useGlobalFilters(new WsAllExceptionFilter());
```

`@SubscribeMessage` 핸들러는 비동기 함수에서 throw한 에러를 잡지 못하면 프로세스가 unhandled rejection으로 떨어질 수 있다. 핸들러를 항상 try/catch로 감싸거나 위처럼 글로벌 필터를 거는 게 안전하다.


## 부하 분산과 성능 관찰

WebSocket은 long-lived connection이라 동시 접속 수가 곧 자원 점유다. 일반적인 Node.js 인스턴스(2 vCPU, 4GB)는 10k~30k 동시 접속을 다룬다. 메시지 처리량보다 메모리·소켓 수가 먼저 한계에 닿는다.

`server.engine.clientsCount`로 현재 인스턴스의 접속 수를 잴 수 있다. Prometheus 같은 메트릭으로 빼서 인스턴스별 분포를 봐야 한다. Sticky session이 안 잡혀있으면 한 인스턴스로 트래픽이 쏠리는 게 여기서 보인다.

socket.io는 `server.fetchSockets()`로 클러스터 전체 소켓을 가져올 수 있다(Redis Adapter 필수). 운영 중에 특정 사용자를 강제 로그아웃하거나 디버깅용으로 메시지를 직접 보낼 때 쓴다. 다만 클러스터 전체를 도는 동기 작업이라 자주 호출하면 안 된다.

연결 부하가 크다면 OS 수준의 file descriptor 한계도 본다. `ulimit -n`이 1024로 잡혀있으면 1k 접속에서 막힌다. 컨테이너 환경에서는 `LimitNOFILE` 설정과 sysctl `fs.file-max`까지 확인한다.


## 운영 중에 자주 부딪힌 함정

**CORS는 socket.io 옵션에 따로 줘야 한다.** NestJS의 `app.enableCors()`는 HTTP에만 적용된다. socket.io 핸드셰이크는 별도 옵션이 필요하다. credentials를 쓰면 `origin: true`가 아니라 명시적 도메인 배열로 지정해야 브라우저가 받아준다.

**`forRoot()`를 두 번 호출하면 어댑터가 깨진다.** 마이크로서비스와 게이트웨이를 한 프로세스에 같이 띄우면 어댑터 우선순위 이슈가 생긴다. 가능하면 게이트웨이는 별도 인스턴스로 분리하는 쪽이 운영이 단순하다.

**클라이언트 라이브러리 버전 불일치.** socket.io v2 클라이언트와 v4 서버는 자동으로 안 붙는다. 모바일 앱 배포 주기가 길면 서버에서 호환 옵션을 켜두거나 점진 마이그레이션 경로를 잡아야 한다.

**룸 이름 충돌.** socket.id 자체가 룸 이름이다. `client.join(someId)`에서 someId가 우연히 다른 클라이언트의 socket.id와 같으면 그 클라이언트로도 메시지가 간다. 룸 이름에는 항상 `user:`, `room:`, `doc:` 같은 prefix를 붙인다.

**`disconnect` 이벤트의 reason.** `client.on('disconnect', (reason) => ...)`에서 reason이 `transport close`, `ping timeout`, `server namespace disconnect` 등으로 갈린다. `client namespace disconnect`는 클라이언트가 의도적으로 끊은 경우, `transport close`는 네트워크 이슈, `server namespace disconnect`는 서버가 끊은 경우다. presence 처리에서 의도적 로그아웃과 일시 단절을 구분하려면 이 reason을 봐야 한다.

WebSocket은 한 번 잘 깔아두면 알림, 채팅, 실시간 협업까지 같은 인프라로 확장된다. 처음에 어댑터·인증·재연결만 단단히 잡으면 나머지는 비즈니스 로직 문제로 좁혀진다.
