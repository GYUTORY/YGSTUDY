---
title: 마이크로서비스 환경의 인증/인가
tags: [backend, authentication, authorization, msa, api-gateway, mtls, jwt, spring-cloud-gateway]
updated: 2026-03-26
---

# 마이크로서비스 환경의 인증/인가

## 단일 서비스와 뭐가 다른가

단일 서비스에서는 로그인 → 세션/JWT 발급 → 매 요청 검증, 이게 끝이다. 서비스가 하나니까 인증 정보가 밖으로 나갈 일이 없다.

MSA에서는 문제가 복잡해진다.

```
Client → API Gateway → Order Service → Payment Service → Inventory Service
                           │                  │
                      이 사용자가 누군지     여기서도 알아야 함
                      어디까지 할 수 있는지   여기서도 확인해야 함
```

사용자 요청 하나가 내부 서비스 여러 개를 거치는데, 각 서비스가 "이 요청이 누구 거고, 뭘 할 수 있는지" 알아야 한다. 인증 정보를 서비스 간에 어떻게 전파할 것인지가 핵심이다.

## API Gateway에서의 토큰 검증

모든 외부 요청은 API Gateway를 통과한다. 토큰 검증을 각 서비스에서 개별로 하면 중복 로직이 생기고, 인증 서버에 부하가 몰린다. Gateway에서 한 번 검증하고, 내부 서비스에는 검증된 사용자 정보를 전달하는 구조가 일반적이다.

```
Client ──Bearer Token──▶ API Gateway ──내부 헤더──▶ 각 서비스
                            │
                      1. JWT 서명 검증
                      2. 만료 확인
                      3. 사용자 정보 추출
                      4. 내부 헤더에 담아 전달
```

### NestJS API Gateway 구현

```typescript
import { Injectable, NestMiddleware, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class AuthGatewayMiddleware implements NestMiddleware {
  constructor(private readonly jwtService: JwtService) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const authHeader = req.headers['authorization'];

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).end();
      return;
    }

    const token = authHeader.substring(7);

    try {
      const jwt = await this.jwtService.verifyAsync<{
        sub: string;
        roles: string[];
        email: string;
      }>(token);

      // 검증된 사용자 정보를 내부 헤더로 전달
      req.headers['x-user-id'] = jwt.sub;
      req.headers['x-user-roles'] = jwt.roles.join(',');
      req.headers['x-user-email'] = jwt.email;
      // 원본 Authorization 헤더는 제거
      delete req.headers['authorization'];

      next();
    } catch {
      res.status(401).end();
    }
  }
}
```

원본 `Authorization` 헤더를 제거하는 이유: 내부 서비스가 외부 토큰을 직접 파싱하기 시작하면, Gateway의 검증 로직과 각 서비스의 검증 로직이 따로 놀게 된다. 내부 서비스는 Gateway가 넣어준 `X-User-*` 헤더만 신뢰하도록 통일해야 한다.

### 내부 서비스에서 사용자 정보 수신

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class InternalAuthMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    const userId = req.headers['x-user-id'] as string | undefined;
    const roles = req.headers['x-user-roles'] as string | undefined;

    if (userId) {
      const authorities = (roles ?? '')
        .split(',')
        .filter((r) => r.trim() !== '')
        .map((r) => 'ROLE_' + r);

      // 요청 컨텍스트에 사용자 정보 저장
      (req as Request & { internalUser: { userId: string; roles: string[] } }).internalUser = {
        userId,
        roles: authorities,
      };
    }

    next();
  }
}
```

```typescript
// 컨트롤러에서 사용
import { Controller, Get, Req } from '@nestjs/common';
import { Request } from 'express';

@Controller('orders')
export class OrderController {
  constructor(private readonly orderService: OrderService) {}

  @Get()
  getMyOrders(@Req() req: Request & { internalUser: { userId: string } }): Promise<Order[]> {
    return this.orderService.findByUserId(req.internalUser.userId);
  }
}
```

여기서 중요한 문제가 하나 있다. `X-User-Id` 헤더를 외부에서 직접 보내면? Gateway를 거치지 않고 내부 서비스에 직접 접근하는 경우, 누구든 `X-User-Id: admin`을 넣어서 관리자 행세를 할 수 있다. 내부 서비스는 반드시 내부 네트워크에서만 접근 가능하도록 네트워크 레벨에서 차단해야 한다. Kubernetes라면 NetworkPolicy, AWS라면 Security Group으로 잡는다.

## Service-to-Service 인증

사용자 요청 전파와는 별개로, 서비스끼리 직접 호출하는 경우가 있다. 배치 처리, 이벤트 처리, 헬스 체크 같은 상황이다. 이때는 사용자 토큰이 없으니 서비스 자체를 인증해야 한다.

### mTLS (Mutual TLS)

일반 HTTPS에서는 클라이언트가 서버 인증서를 검증한다. mTLS는 서버도 클라이언트 인증서를 검증한다. 양방향 인증이다.

```
일반 TLS:
Client ────────▶ Server
         서버 인증서 검증

mTLS:
Client ◀───────▶ Server
  서버 인증서 검증    클라이언트 인증서 검증
```

Kubernetes에서는 Istio 같은 서비스 메시가 mTLS를 자동으로 처리한다. 각 Pod에 사이드카 프록시가 붙어서 인증서 발급, 갱신, 검증을 알아서 한다. 애플리케이션 코드를 건드릴 필요가 없다.

```yaml
# Istio PeerAuthentication - 네임스페이스 전체에 mTLS 적용
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: my-namespace
spec:
  mtls:
    mode: STRICT  # mTLS만 허용, 평문 거부
```

서비스 메시 없이 직접 구현하면 인증서 관리가 고역이다. 인증서 만료, 갱신, 배포를 직접 해야 하고, 서비스가 늘어날수록 관리 포인트가 폭발한다.

### Internal JWT

서비스 간 호출에 별도의 JWT를 발급하는 방식이다. mTLS보다 구현이 간단하고, 토큰에 서비스 정보와 권한을 담을 수 있다.

```typescript
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class ServiceTokenProvider {
  constructor(
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {}

  // 서비스 자체 인증용 토큰 발급
  issueServiceToken(sourceService: string): string {
    return this.jwtService.sign(
      {
        sub: sourceService,
        type: 'service',
        permissions: ['order:read', 'payment:process'],
      },
      {
        secret: this.configService.get<string>('AUTH_SERVICE_SIGNING_KEY'),
        expiresIn: 300, // 5분
      },
    );
  }
}
```

```typescript
// 다른 서비스 호출 시 토큰 첨부 (HttpService 인터셉터)
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ServiceTokenProvider } from './service-token.provider';

@Injectable()
export class PaymentServiceClient {
  constructor(
    private readonly httpService: HttpService,
    private readonly tokenProvider: ServiceTokenProvider,
  ) {
    this.httpService.axiosRef.interceptors.request.use((config) => {
      const token = this.tokenProvider.issueServiceToken('order-service');
      config.headers['X-Service-Auth'] = `Bearer ${token}`;
      return config;
    });
  }
}
```

수신 측에서는 `type` 클레임이 `service`인지 확인하고, `permissions`에 해당 API 호출 권한이 있는지 검사한다. 사용자 JWT와 서비스 JWT를 같은 키로 서명하면 안 된다. 서비스 토큰 키가 유출되면 사용자 토큰도 위조할 수 있게 된다.

## 토큰 릴레이와 권한 축소 문제

사용자가 주문을 하면 Order Service가 Payment Service를 호출하는데, 이때 사용자 토큰을 그대로 전달하는 걸 토큰 릴레이라 한다.

```
Client (Admin 권한)
  │
  ▼
Order Service ──사용자 토큰 그대로 전달──▶ Payment Service
                                            │
                                     이 토큰에 Admin 권한이 있네?
                                     Payment의 Admin API도 호출 가능?
```

문제가 보이는가. 사용자가 Order Service에 대해 Admin 권한을 갖고 있으면, 그 토큰이 Payment Service에 전달됐을 때 Payment의 Admin API까지 접근할 수 있다. 의도하지 않은 권한 확대다.

### 해결: 토큰 다운스코핑

Gateway에서 내부 서비스로 요청을 전달할 때, 해당 서비스에 필요한 최소 권한만 담은 토큰으로 교체한다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request, Response, NextFunction } from 'express';

// 서비스별 허용 권한 매핑
const SERVICE_SCOPES: Record<string, Set<string>> = {
  'order-service': new Set(['order:read', 'order:write', 'user:read']),
  'payment-service': new Set(['payment:process', 'user:read']),
  'inventory-service': new Set(['inventory:read']),
};

@Injectable()
export class TokenDownScopingMiddleware implements NestMiddleware {
  constructor(private readonly jwtService: JwtService) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const targetService = this.resolveTargetService(req);
    const allowedScopes = SERVICE_SCOPES[targetService] ?? new Set<string>();

    const auth = (req as Request & { auth?: { userId: string; scopes: string[] } }).auth;
    if (!auth) {
      next();
      return;
    }

    // 원본 토큰의 권한 중 대상 서비스에 허용된 것만 남김
    const originalScopes: string[] = auth.scopes;
    const downScoped = originalScopes.filter((s) => allowedScopes.has(s));

    // 축소된 권한으로 새 토큰 발급
    const scopedToken = this.jwtService.sign(
      {
        sub: auth.userId,
        scopes: downScoped,
        original_scopes: originalScopes, // 디버깅용
      },
      { expiresIn: 30 }, // 짧은 수명
    );

    req.headers['x-scoped-token'] = scopedToken;
    next();
  }

  private resolveTargetService(req: Request): string {
    // URL 경로에서 대상 서비스 이름 추출 (구현에 따라 다를 수 있음)
    return req.headers['x-target-service'] as string ?? '';
  }
}
```

`original_scopes`를 넣는 건 디버깅 용도다. 운영에서 "이 사용자가 원래 어떤 권한이었는데 축소됐는지" 로그로 확인할 때 쓴다. 민감한 환경이면 빼도 된다.

## Gateway와 서비스의 인가 책임 분리

인가(Authorization)를 어디서 처리할지가 MSA에서 가장 논쟁이 많은 부분이다.

### Gateway에서 처리하면 좋은 것

- URL 패턴 기반 접근 제어: `/admin/**`은 ADMIN 역할만 허용
- Rate Limiting: 사용자/API Key별 요청 제한
- IP 화이트리스트/블랙리스트
- 인증 실패 시 일괄 처리 (401, 403)

```yaml
# Spring Cloud Gateway route 설정
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: Auth
            - name: RoleCheck
              args:
                required-role: USER
        - id: admin-service
          uri: lb://admin-service
          predicates:
            - Path=/admin/**
          filters:
            - name: Auth
            - name: RoleCheck
              args:
                required-role: ADMIN
```

### 각 서비스에서 처리해야 하는 것

- 비즈니스 로직에 의존하는 권한 검사: "본인의 주문만 취소 가능", "같은 팀 멤버만 조회 가능"
- 데이터 레벨 접근 제어: 특정 리소스의 소유자인지 확인
- 도메인 규칙에 따른 상태 기반 접근 제어: "배송 시작된 주문은 수정 불가"

```typescript
import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Order, OrderStatus } from './order.entity';

@Injectable()
export class OrderService {
  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
  ) {}

  // Gateway가 ROLE_USER는 확인했지만,
  // "이 주문이 이 사용자의 것인지"는 서비스가 확인해야 한다
  async cancelOrder(orderId: string, userId: string): Promise<Order> {
    const order = await this.orderRepository.findOne({ where: { id: orderId } });
    if (!order) {
      throw new NotFoundException('주문을 찾을 수 없음');
    }

    // 본인 주문인지 확인
    if (order.userId !== userId) {
      throw new ForbiddenException('본인의 주문만 취소할 수 있음');
    }

    // 상태 기반 접근 제어
    if (order.status === OrderStatus.SHIPPED) {
      throw new Error('배송이 시작된 주문은 취소할 수 없음');
    }

    order.cancel();
    return this.orderRepository.save(order);
  }
}
```

원칙을 정리하면: **Gateway는 "누가 어떤 종류의 API에 접근할 수 있는지"를 처리하고, 서비스는 "이 사용자가 이 특정 리소스에 대해 이 작업을 할 수 있는지"를 처리한다.**

Gateway에 비즈니스 로직을 넣기 시작하면 Gateway가 모든 서비스의 도메인을 알아야 하는 상황이 된다. 서비스 하나 바뀔 때마다 Gateway도 수정해야 하고, Gateway가 단일 장애점(SPOF)이 될 위험도 커진다.

## NestJS API Gateway + JWT 조합

전체 구조를 코드로 정리한다.

### Gateway 모듈 설정

```typescript
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AuthGatewayMiddleware } from './auth-gateway.middleware';

@Module({
  imports: [
    ConfigModule.forRoot(),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        secret: configService.get<string>('JWT_SECRET'),
      }),
      inject: [ConfigService],
    }),
  ],
})
export class GatewayModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer
      .apply(AuthGatewayMiddleware)
      .exclude('/api/auth/(.*)', '/health')
      .forRoutes('*');
  }
}
```

### Gateway 글로벌 미들웨어 - 사용자 정보 전파

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'crypto';

@Injectable()
export class UserContextRelayMiddleware implements NestMiddleware {
  constructor(private readonly jwtService: JwtService) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const authHeader = req.headers['authorization'];

    if (authHeader?.startsWith('Bearer ')) {
      const token = authHeader.substring(7);
      try {
        const jwt = await this.jwtService.verifyAsync<{
          sub: string;
          email: string;
          roles: string[];
        }>(token);

        // 외부에서 주입한 내부 헤더 제거 (보안)
        delete req.headers['x-user-id'];
        delete req.headers['x-user-email'];
        delete req.headers['x-user-roles'];

        // 검증된 사용자 정보 설정
        req.headers['x-user-id'] = jwt.sub;
        req.headers['x-user-email'] = jwt.email;
        req.headers['x-user-roles'] = jwt.roles.join(',');
        req.headers['x-request-id'] = randomUUID().substring(0, 8);
      } catch {
        // 인증 실패 시 헤더 제거만 수행
        delete req.headers['x-user-id'];
        delete req.headers['x-user-email'];
        delete req.headers['x-user-roles'];
      }
    }

    next();
  }
}
```

`X-Request-Id`를 여기서 생성하는 이유: 사용자 요청 하나가 내부 서비스 여러 개를 거치는데, 같은 Request ID를 전파하면 분산 로그 추적이 가능하다. 문제 발생 시 이 ID로 관련 로그를 한 번에 검색할 수 있다.

헤더를 먼저 `remove`하고 다시 `header`로 설정하는 순서가 맞나 싶을 수 있다. `mutate().header()`는 추가(add)이고, `headers(h -> h.remove())`가 삭제다. 외부에서 `X-User-Id`를 주입해서 내부 서비스를 속이는 공격을 막으려면, 기존 값을 지우고 Gateway가 검증한 값으로 덮어써야 한다.

### 내부 서비스 Security 설정

```typescript
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { InternalAuthMiddleware } from './internal-auth.middleware';

// Gateway가 아닌 내부 서비스용
// JWT 검증은 Gateway가 했으므로 여기서는 하지 않음
@Module({})
export class InternalServiceModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer
      .apply(InternalAuthMiddleware)
      .forRoutes('*');
  }
}
```

### 서비스 간 호출 시 사용자 컨텍스트 전파

Order Service가 Payment Service를 호출할 때, 원래 사용자 정보를 같이 전달해야 한다. Axios(HttpService)를 쓰는 경우:

```typescript
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ServiceTokenProvider } from './service-token.provider';
import { Request } from 'express';

@Injectable()
export class PaymentServiceClient {
  constructor(
    private readonly httpService: HttpService,
    private readonly serviceTokenProvider: ServiceTokenProvider,
  ) {}

  async chargePayment(
    amount: number,
    req: Request & { internalUser?: { userId: string; roles: string[] } },
  ): Promise<unknown> {
    const userId = req.internalUser?.userId ?? '';
    const roles = req.internalUser?.roles.join(',') ?? '';
    const serviceToken = this.serviceTokenProvider.issueServiceToken('order-service');

    return this.httpService.axiosRef.post(
      'http://payment-service/charge',
      { amount },
      {
        headers: {
          // 사용자 컨텍스트 전파
          'X-User-Id': userId,
          'X-User-Roles': roles,
          // 서비스 인증 토큰 추가
          'X-Service-Auth': `Bearer ${serviceToken}`,
        },
      },
    );
  }
}
```

수신 서비스에서는 `X-Service-Auth`로 호출한 서비스의 신원을 확인하고, `X-User-Id`로 원래 사용자가 누구인지 파악한다. 두 가지 인증이 동시에 필요하다.

## 실무에서 자주 겪는 문제

### 토큰 만료 타이밍

서비스 A가 서비스 B를 호출하는 시점에 토큰이 만료되는 경우가 있다. Access Token 유효시간이 15분인데, Gateway에서 검증한 시점과 내부 서비스에서 사용하는 시점 사이에 1-2초 차이가 나면서 만료되는 거다.

내부 전파용 토큰은 Gateway가 발급하고 수명을 짧게(30초~1분) 잡되, 외부 토큰 만료와는 독립적으로 관리한다.

### Gateway 장애 시 인증 불가

Gateway가 죽으면 모든 인증이 멈춘다. Gateway는 최소 2개 이상의 인스턴스를 띄우고, 로드밸런서 뒤에 두어야 한다. Gateway의 토큰 검증은 가능하면 인증 서버 호출 없이 로컬에서 처리한다(JWT 서명 검증). JWKS(공개키 세트)를 캐시해두면 인증 서버가 잠깐 죽어도 기존 키로 검증이 가능하다.

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: https://auth.example.com/.well-known/jwks.json
          # JWK 캐시 설정 - NimbusJwtDecoder가 기본적으로 캐시하지만
          # 캐시 기간을 직접 제어하려면 커스텀 JwtDecoder를 빈으로 등록
```

### 서비스 간 순환 호출과 토큰 전파

A → B → C → A 같은 순환 호출이 발생하면, 토큰 전파가 무한 루프에 빠질 수 있다. 순환 호출 자체가 설계 문제이지만, 방어 차원에서 `X-Hop-Count` 같은 헤더를 두고 일정 횟수 이상이면 요청을 거부하는 방법이 있다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class HopCountMiddleware implements NestMiddleware {
  private static readonly MAX_HOPS = 5;

  use(req: Request, res: Response, next: NextFunction): void {
    const hopHeader = req.headers['x-hop-count'] as string | undefined;
    const hopCount = hopHeader != null ? parseInt(hopHeader, 10) : 0;

    if (hopCount >= HopCountMiddleware.MAX_HOPS) {
      res.status(508).json({ message: '서비스 호출 깊이 초과' });
      return;
    }

    // 다음 서비스 호출 시 hop count 증가
    req.headers['x-hop-count'] = String(hopCount + 1);
    next();
  }
}
```

### 로그에 사용자 컨텍스트 남기기

분산 환경에서 문제 추적 시 "어떤 사용자의 요청이 어떤 서비스를 거쳤는지" 로그로 남겨야 한다. MDC(Mapped Diagnostic Context)를 쓴다.

```typescript
import { Injectable, NestMiddleware, Logger } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LogContextMiddleware implements NestMiddleware {
  private readonly logger = new Logger('order-service');

  use(req: Request, res: Response, next: NextFunction): void {
    const userId = req.headers['x-user-id'] as string | undefined;
    const requestId = req.headers['x-request-id'] as string | undefined;

    // NestJS Logger에 컨텍스트를 심어서 요청 추적
    (req as Request & { logContext: Record<string, string | undefined> }).logContext = {
      userId,
      requestId,
      service: 'order-service',
    };

    // 예: Logger.log(`[${requestId}] [${userId}] [order-service] 요청 처리`);
    this.logger.log(`[${requestId}] [${userId}] [order-service] ${req.method} ${req.path}`);
    next();
  }
}
```

```typescript
// winston 또는 pino 사용 시 로그 포맷 예시
// {timestamp} [{requestId}] [{userId}] [{service}] {message}
// 14:23:01 [a1b2c3d4] [user-123] [order-service] 주문 생성 요청
```

이렇게 하면 로그가 이렇게 찍힌다:

```
14:23:01 [a1b2c3d4] [user-123] [order-service] 주문 생성 요청
14:23:01 [a1b2c3d4] [user-123] [payment-service] 결제 처리 시작
14:23:02 [a1b2c3d4] [user-123] [inventory-service] 재고 차감
```

같은 `requestId`로 전체 흐름을 추적할 수 있다.

## 참고

- [인증/인가 방식 비교](Authentication_Strategy.md) — 단일 서비스 기준 인증 방식
- [RBAC/ABAC](RBAC_ABAC.md) — 역할/속성 기반 접근 제어
- [API 인증/인가 실무 패턴](../API/API_Security_Patterns.md)

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
