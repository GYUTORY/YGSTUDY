---
title: NestJS Server-Sent Events (SSE)
tags: [nodejs]
updated: 2026-07-10
---

# NestJS Server-Sent Events

SSE는 서버에서 클라이언트로 단방향 실시간 데이터를 푸시하는 HTTP 기반 프로토콜이다. WebSocket과 달리 일반 HTTP 연결을 그대로 쓰고, 브라우저가 자동 재연결을 처리한다.

NestJS에서는 `@Sse()` 데코레이터와 RxJS `Observable`을 조합해 구현한다. 컨트롤러에서 Observable을 반환하면 프레임워크가 `text/event-stream` 응답으로 변환해준다.

## 기본 구조

```typescript
import { Controller, Sse, MessageEvent } from '@nestjs/common';
import { Observable, interval } from 'rxjs';
import { map } from 'rxjs/operators';

@Controller('events')
export class EventsController {
  @Sse('stream')
  stream(): Observable<MessageEvent> {
    return interval(1000).pipe(
      map(() => ({
        data: { timestamp: new Date().toISOString() },
      })),
    );
  }
}
```

`MessageEvent`는 `data`, `id`, `type`, `retry` 필드를 가진다. `data`에 객체를 넣으면 NestJS가 자동으로 JSON 직렬화한다.

클라이언트에서는 `EventSource`로 연결한다.

```javascript
const source = new EventSource('/events/stream');
source.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  console.log(payload);
};
```

## EventEmitter와 결합

실제 서비스에서는 1초마다 데이터를 보내는 게 아니라, 특정 이벤트가 발생했을 때 연결된 클라이언트에 데이터를 보내야 한다. `Subject`를 써서 이벤트 기반으로 만든다.

```typescript
import { Injectable } from '@nestjs/common';
import { OnEvent } from '@nestjs/event-emitter';
import { Subject } from 'rxjs';
import { MessageEvent } from '@nestjs/common';

@Injectable()
export class NotificationService {
  private subjects = new Map<string, Subject<MessageEvent>>();

  getStream(userId: string): Subject<MessageEvent> {
    if (!this.subjects.has(userId)) {
      this.subjects.set(userId, new Subject<MessageEvent>());
    }
    return this.subjects.get(userId);
  }

  removeStream(userId: string): void {
    const subject = this.subjects.get(userId);
    if (subject) {
      subject.complete();
      this.subjects.delete(userId);
    }
  }

  @OnEvent('order.created')
  handleOrderCreated(payload: { userId: string; orderId: string }) {
    const subject = this.subjects.get(payload.userId);
    if (subject) {
      subject.next({
        data: {
          type: 'ORDER_CREATED',
          orderId: payload.orderId,
        },
      });
    }
  }
}
```

컨트롤러에서는 Subject를 Observable로 노출한다.

```typescript
@Controller('notifications')
export class NotificationsController {
  constructor(private readonly notificationService: NotificationService) {}

  @Sse('stream')
  @UseGuards(JwtAuthGuard)
  stream(@Request() req): Observable<MessageEvent> {
    const userId = req.user.id;
    return this.notificationService.getStream(userId).asObservable();
  }
}
```

## 클라이언트 연결 관리와 cleanup

연결이 끊겼을 때 Subject를 Map에서 제거하지 않으면 메모리 누수가 생긴다. `Observable`의 `finalize` 연산자로 cleanup을 처리한다.

```typescript
import { finalize } from 'rxjs/operators';

@Sse('stream')
@UseGuards(JwtAuthGuard)
stream(@Request() req): Observable<MessageEvent> {
  const userId = req.user.id;
  const subject = this.notificationService.getStream(userId);

  return subject.asObservable().pipe(
    finalize(() => {
      this.notificationService.removeStream(userId);
    }),
  );
}
```

`finalize`는 Observable이 완료되거나 에러가 발생하거나 구독이 취소될 때 실행된다. 클라이언트가 탭을 닫으면 NestJS가 구독을 취소하고 `finalize`가 호출된다.

같은 userId로 중복 연결이 들어오는 경우도 고려해야 한다. 위 코드에서 `getStream`은 기존 Subject를 재사용하므로, 이전 연결이 cleanup되면 새 연결도 Subject가 삭제되어버린다. 연결마다 고유 키를 쓰거나 참조 카운트를 관리해야 한다.

```typescript
private subjects = new Map<string, { subject: Subject<MessageEvent>; count: number }>();

getStream(userId: string): Subject<MessageEvent> {
  if (!this.subjects.has(userId)) {
    this.subjects.set(userId, { subject: new Subject(), count: 0 });
  }
  const entry = this.subjects.get(userId);
  entry.count++;
  return entry.subject;
}

removeStream(userId: string): void {
  const entry = this.subjects.get(userId);
  if (!entry) return;

  entry.count--;
  if (entry.count <= 0) {
    entry.subject.complete();
    this.subjects.delete(userId);
  }
}
```

## WebSocket과 SSE 선택 기준

두 기술의 차이는 통신 방향에서 나온다.

| 항목 | SSE | WebSocket |
|------|-----|-----------|
| 방향 | 서버 → 클라이언트 | 양방향 |
| 프로토콜 | HTTP/1.1, HTTP/2 | WS/WSS (업그레이드) |
| 재연결 | 브라우저 자동 처리 | 수동 구현 필요 |
| 인증 | 기존 HTTP 쿠키/헤더 사용 | 핸드셰이크 시 별도 처리 |
| 프록시 | 일반 HTTP 프록시 통과 | 별도 설정 필요 |

서버에서 클라이언트로 알림만 보내면 되는 경우라면 SSE가 적합하다. 주문 상태 변경, 배치 작업 진행률, 실시간 로그 스트리밍, 알림 센터 같은 케이스다.

클라이언트가 서버로도 데이터를 보내야 하거나, 지연 시간이 극도로 중요하거나, 바이너리 데이터를 전송해야 한다면 WebSocket을 쓴다. 채팅, 게임, 실시간 협업 편집기 같은 케이스다.

HTTP/2 환경에서 SSE의 성능은 WebSocket에 필적한다. 하나의 TCP 연결에서 멀티플렉싱이 되므로, HTTP/1.1처럼 연결 수 제한(보통 도메인당 6개)에 걸리지 않는다.

## CORS 처리

`EventSource`는 쿠키를 기본으로 보내지 않는다. 인증 쿠키가 필요한 경우 `withCredentials` 옵션을 써야 한다.

```javascript
const source = new EventSource('/notifications/stream', {
  withCredentials: true,
});
```

서버에서는 CORS 설정에 `credentials: true`를 추가한다.

```typescript
// main.ts
app.enableCors({
  origin: 'https://your-frontend.com',
  credentials: true,
});
```

`origin: '*'`과 `credentials: true`는 함께 쓸 수 없다. 브라우저가 차단한다. 명시적인 origin을 지정해야 한다.

JWT를 쿠키가 아닌 Authorization 헤더로 전달하는 경우, `EventSource`는 커스텀 헤더를 지원하지 않는다. 이때는 URL 파라미터로 토큰을 넘기거나, 인증된 세션 토큰을 별도로 발급해서 쿼리스트링으로 전달하는 방식을 쓴다.

```typescript
@Sse('stream')
stream(@Query('token') token: string): Observable<MessageEvent> {
  const user = this.authService.verifyToken(token);
  // ...
}
```

쿼리스트링으로 JWT를 노출하는 건 보안상 좋지 않다. 로그에 남거나 Referer 헤더에 포함될 수 있다. 단명 토큰(수십 초 유효)을 별도로 발급해서 쓰는 패턴이 낫다.

## Nginx 프록시 설정

Nginx를 앞단에 두면 SSE가 작동하지 않는 경우가 있다. Nginx가 기본적으로 응답을 버퍼링하기 때문이다. 버퍼링이 활성화되면 NestJS가 데이터를 보내도 Nginx가 쌓아두다가 한꺼번에 보낸다.

```nginx
location /notifications/stream {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    
    # 버퍼링 비활성화 - SSE 필수 설정
    proxy_buffering off;
    proxy_cache off;
    
    # 청크 전송 인코딩 비활성화
    proxy_set_header X-Accel-Buffering no;
    
    # 타임아웃 설정 (SSE는 장시간 연결 유지)
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    
    # 일반 헤더
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

`proxy_buffering off`만 설정해도 대부분 해결된다. `X-Accel-Buffering: no` 헤더를 응답에 포함시키면 Nginx 설정 없이도 버퍼링을 끌 수 있다.

NestJS 인터셉터나 미들웨어에서 헤더를 추가하는 방법도 있다.

```typescript
@Injectable()
export class SseHeaderInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const response = context.switchToHttp().getResponse();
    response.setHeader('X-Accel-Buffering', 'no');
    response.setHeader('Cache-Control', 'no-cache');
    return next.handle();
  }
}
```

`proxy_read_timeout` 기본값은 60초다. SSE는 연결을 오래 유지하므로 타임아웃을 늘려야 한다. 그렇지 않으면 60초마다 연결이 끊기고 브라우저가 재연결을 시도하는 패턴이 반복된다.

## 하트비트

네트워크 장비(로드 밸런서, 방화벽)는 일정 시간 동안 트래픽이 없으면 연결을 끊기도 한다. 주기적으로 더미 이벤트를 보내는 하트비트로 연결을 유지한다.

```typescript
import { merge, interval } from 'rxjs';
import { map, filter } from 'rxjs/operators';

@Sse('stream')
stream(@Request() req): Observable<MessageEvent> {
  const userId = req.user.id;
  const events$ = this.notificationService.getStream(userId).asObservable();

  const heartbeat$ = interval(30000).pipe(
    map(() => ({ data: { type: 'PING' } } as MessageEvent)),
  );

  return merge(events$, heartbeat$).pipe(
    finalize(() => {
      this.notificationService.removeStream(userId);
    }),
  );
}
```

클라이언트에서 `PING` 타입은 무시하도록 처리한다.

```javascript
source.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  if (payload.type === 'PING') return;
  // 실제 이벤트 처리
};
```

## 주의사항

Node.js의 기본 HTTP 서버는 연결당 하나의 스레드가 아니라 이벤트 루프에서 처리하므로, SSE 연결이 많아도 WebSocket처럼 연결 자체의 오버헤드는 크지 않다. 하지만 Subject를 Map으로 관리하는 구조는 메모리를 직접 관리하는 것이므로 cleanup 로직을 꼼꼼히 짜야 한다.

수평 확장 환경에서는 Subject가 프로세스 메모리에 있으므로 문제가 생긴다. 사용자가 인스턴스 A에 SSE로 연결하고, 이벤트가 인스턴스 B에서 발생하면 해당 이벤트가 클라이언트에 전달되지 않는다. Redis Pub/Sub을 써서 인스턴스 간 이벤트를 브로드캐스트하거나, Sticky Session으로 같은 인스턴스에 연결을 고정해야 한다.
