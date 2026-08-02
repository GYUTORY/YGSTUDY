---
title: NestJS OpenTelemetry 분산 추적
tags: [nestjs, opentelemetry, 분산추적, jaeger, tempo, 마이크로서비스]
updated: 2026-07-10
---

# NestJS OpenTelemetry 분산 추적

마이크로서비스에서 요청이 실패하거나 응답이 느릴 때, 어느 서비스에서 얼마나 걸렸는지 파악하기가 어렵다. 로그만으로는 서비스 간 요청 흐름을 추적할 수 없고, 각 서비스의 로그를 상호 연관 짓는 것도 번거롭다. OpenTelemetry는 이 문제를 하나의 trace ID로 요청 전체 흐름을 연결해서 해결한다.

## 설치와 초기화

```bash
npm install @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-otlp-grpc \
  @opentelemetry/exporter-jaeger \
  @opentelemetry/resources \
  @opentelemetry/semantic-conventions
```

초기화 코드는 NestJS 앱보다 먼저 실행되어야 한다. `main.ts`에서 import 순서가 중요한 이유가 여기에 있다. SDK가 Node.js 모듈 로딩 시점에 인스트루멘테이션을 주입하는 방식이라, NestJS 모듈이 로드된 후에 SDK를 초기화하면 HTTP나 DB 쿼리 자동 계측이 동작하지 않는다.

```typescript
// tracing.ts - main.ts보다 먼저 실행되어야 함
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-otlp-grpc';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

const exporter = new OTLPTraceExporter({
  url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4317',
});

export const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: process.env.SERVICE_NAME || 'my-service',
    [SemanticResourceAttributes.SERVICE_VERSION]: process.env.npm_package_version || '1.0.0',
  }),
  traceExporter: exporter,
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': {
        ignoreIncomingRequestHook: (req) => {
          // 헬스체크 경로는 트레이싱에서 제외
          return req.url === '/health' || req.url === '/metrics';
        },
      },
      '@opentelemetry/instrumentation-fs': {
        // fs 계측은 노이즈가 많아서 끄는 경우가 많다
        enabled: false,
      },
    }),
  ],
});

sdk.start();

process.on('SIGTERM', () => {
  sdk.shutdown().finally(() => process.exit(0));
});
```

```typescript
// main.ts
import './tracing'; // 반드시 첫 번째 import
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000);
}
bootstrap();
```

## 자동 계측 vs 수동 스팬

`getNodeAutoInstrumentations()`를 사용하면 HTTP 요청, TypeORM/Prisma 쿼리, Redis 명령어, gRPC 호출 등이 자동으로 계측된다. 대부분의 경우 이것만으로 충분하고, 추가 코드가 필요 없다.

자동 계측으로 잡히는 것들:
- `@opentelemetry/instrumentation-http`: Express/Fastify HTTP 요청·응답
- `@opentelemetry/instrumentation-pg`: PostgreSQL 쿼리
- `@opentelemetry/instrumentation-redis`: Redis 명령어
- `@opentelemetry/instrumentation-grpc`: gRPC 스트림
- `@opentelemetry/instrumentation-mongoose`: MongoDB 쿼리

자동 계측이 잡지 못하는 영역은 수동으로 스팬을 추가한다. 외부 API 호출 묶음, 복잡한 비즈니스 로직 안에서 어느 단계가 느린지 측정할 때 쓴다.

```typescript
import { Injectable } from '@nestjs/common';
import { trace, context, SpanStatusCode } from '@opentelemetry/api';

@Injectable()
export class OrderService {
  private tracer = trace.getTracer('order-service');

  async processOrder(orderId: string): Promise<void> {
    const span = this.tracer.startSpan('processOrder', {
      attributes: {
        'order.id': orderId,
        'order.source': 'api',
      },
    });

    // 현재 컨텍스트에 스팬을 연결해야 자식 스팬과 연결됨
    const ctx = trace.setSpan(context.active(), span);

    try {
      await context.with(ctx, async () => {
        await this.validateInventory(orderId);
        await this.chargePayment(orderId);
        await this.sendNotification(orderId);
      });

      span.setStatus({ code: SpanStatusCode.OK });
    } catch (err) {
      span.recordException(err);
      span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
      throw err;
    } finally {
      span.end();
    }
  }

  private async validateInventory(orderId: string): Promise<void> {
    const span = this.tracer.startSpan('validateInventory');
    try {
      // 재고 확인 로직
      span.setAttribute('inventory.check', 'passed');
    } finally {
      span.end();
    }
  }
}
```

인터셉터로 만들면 매 핸들러마다 반복 코드를 줄일 수 있다.

```typescript
import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { trace, context, SpanStatusCode } from '@opentelemetry/api';
import { Observable, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

@Injectable()
export class TracingInterceptor implements NestInterceptor {
  private tracer = trace.getTracer('nestjs-interceptor');

  intercept(ctx: ExecutionContext, next: CallHandler): Observable<any> {
    const request = ctx.switchToHttp().getRequest();
    const spanName = `${request.method} ${ctx.getClass().name}.${ctx.getHandler().name}`;

    const span = this.tracer.startSpan(spanName, {
      attributes: {
        'http.method': request.method,
        'http.route': request.route?.path,
        'http.url': request.url,
      },
    });

    const activeCtx = trace.setSpan(context.active(), span);

    return context.with(activeCtx, () =>
      next.handle().pipe(
        tap(() => {
          span.setStatus({ code: SpanStatusCode.OK });
          span.end();
        }),
        catchError((err) => {
          span.recordException(err);
          span.setStatus({ code: SpanStatusCode.ERROR, message: err.message });
          span.end();
          return throwError(() => err);
        }),
      ),
    );
  }
}
```

## Jaeger / Tempo로 내보내기

### Jaeger

로컬 개발 환경에서 Jaeger All-in-One을 도커로 띄우는 것이 가장 빠르다.

```yaml
# docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - '16686:16686' # UI
      - '4317:4317'   # OTLP gRPC
      - '4318:4318'   # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

`OTLPTraceExporter`의 endpoint를 `http://localhost:4317`로 설정하면 Jaeger가 수신한다. `http://localhost:16686`에서 UI를 확인할 수 있다.

### Grafana Tempo

프로덕션 환경에서는 Tempo + Grafana 조합을 많이 쓴다. Tempo는 트레이스를 오브젝트 스토리지에 저장하고, Grafana에서 TraceQL로 조회한다. Loki(로그)와 Prometheus(메트릭)를 함께 쓰면 Grafana에서 로그-메트릭-트레이스를 하나의 화면에서 연결해서 볼 수 있다.

```typescript
// Tempo를 위한 OTLP exporter 설정 (Jaeger와 동일한 방식)
const exporter = new OTLPTraceExporter({
  url: process.env.TEMPO_ENDPOINT || 'http://tempo:4317',
});
```

환경별로 exporter를 분리할 때는 환경 변수 하나로 제어하는 것이 관리하기 편하다.

```typescript
function createExporter() {
  if (process.env.NODE_ENV === 'production') {
    return new OTLPTraceExporter({
      url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
      headers: {
        'x-honeycomb-team': process.env.HONEYCOMB_API_KEY,
      },
    });
  }
  // 로컬에서는 콘솔로 출력해서 확인
  const { ConsoleSpanExporter } = require('@opentelemetry/sdk-trace-node');
  return new ConsoleSpanExporter();
}
```

## W3C TraceContext와 서비스 간 전파

마이크로서비스에서 분산 추적이 의미 있으려면 서비스 경계를 넘어도 같은 trace ID가 유지되어야 한다. W3C TraceContext 표준은 HTTP 헤더 `traceparent`와 `tracestate`로 이를 전달한다.

`@opentelemetry/instrumentation-http`는 이 전파를 자동으로 처리한다. 서비스 A에서 axios나 fetch로 서비스 B를 호출하면, `traceparent` 헤더가 자동으로 주입된다. 서비스 B는 이 헤더를 읽어서 동일한 trace의 자식 스팬으로 연결한다.

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^  ^                                ^                ^
             버전 trace-id(128bit)              parent-span-id   flags
```

axios를 직접 사용하는 경우 별도 설정 없이 자동 주입된다. 단, `HttpModule`(NestJS의 axios 래퍼)도 동일하게 동작한다.

```typescript
// 서비스 A: 다른 서비스 호출
@Injectable()
export class ProductService {
  constructor(private readonly httpService: HttpService) {}

  async getInventory(productId: string) {
    // traceparent 헤더가 자동으로 추가됨
    const response = await this.httpService.axiosRef.get(
      `http://inventory-service/api/inventory/${productId}`,
    );
    return response.data;
  }
}
```

gRPC 통신에서도 `@opentelemetry/instrumentation-grpc`가 메타데이터에 trace context를 자동으로 주입한다.

Kafka나 RabbitMQ 같은 메시지 브로커는 자동 주입이 안 되는 경우가 있다. 이때는 메시지 헤더에 수동으로 주입해야 한다.

```typescript
import { propagation, context } from '@opentelemetry/api';
import { W3CTraceContextPropagator } from '@opentelemetry/core';

@Injectable()
export class EventPublisher {
  async publishOrderCreated(orderId: string): Promise<void> {
    const carrier: Record<string, string> = {};

    // 현재 컨텍스트의 trace 정보를 carrier에 주입
    propagation.inject(context.active(), carrier);

    await this.kafkaProducer.send({
      topic: 'order-created',
      messages: [
        {
          value: JSON.stringify({ orderId }),
          headers: carrier, // traceparent, tracestate 포함
        },
      ],
    });
  }
}

// 컨슈머 쪽에서 복원
@Injectable()
export class EventConsumer {
  @EventPattern('order-created')
  async handleOrderCreated(data: any, @Ctx() context: KafkaContext): Promise<void> {
    const headers = context.getMessage().headers;
    const carrier: Record<string, string> = {};

    // Kafka 헤더를 문자열 맵으로 변환
    for (const [key, value] of Object.entries(headers)) {
      if (value) carrier[key] = value.toString();
    }

    // carrier에서 trace context 복원
    const parentCtx = propagation.extract(otelContext.active(), carrier);

    await otelContext.with(parentCtx, async () => {
      // 이 안에서 생성한 스팬은 발행자의 trace와 연결됨
      await this.processOrder(data.orderId);
    });
  }
}
```

## 실무에서 병목 찾는 방법

분산 추적을 도입한 후 실제로 유용한 경우는 대부분 다음 상황이다.

**느린 API 응답 원인 분석**

P99 응답 시간이 갑자기 튀는데 어디서 발생하는지 모를 때, Jaeger UI에서 해당 시간대의 느린 트레이스를 찾으면 어느 스팬이 오래 걸렸는지 바로 보인다. DB 쿼리 스팬에 실제 SQL이 `db.statement` 속성으로 찍혀 있어서, 슬로우 쿼리를 찾는 데도 쓴다.

**캐스케이딩 장애 추적**

서비스 C가 실패하는데 원인이 서비스 A의 타임아웃이었던 경우, 트레이스가 없으면 로그를 수동으로 연결해야 한다. trace ID 하나로 전체 호출 체인을 볼 수 있으면 원인 서비스를 바로 특정할 수 있다.

**N+1 쿼리 탐지**

TypeORM의 자동 계측이 쿼리를 스팬으로 기록하기 때문에, 트레이스를 보면 루프 안에서 쿼리가 반복 실행되는 패턴이 보인다. 같은 테이블에 대한 SELECT 스팬이 수십 개 찍혀 있으면 N+1 의심이다.

스팬 속성에 비즈니스 데이터를 추가하면 더 유용하다.

```typescript
span.setAttributes({
  'user.id': userId,
  'order.amount': orderAmount,
  'order.item_count': items.length,
  'payment.provider': 'stripe',
});
```

속성이 풍부할수록 나중에 특정 조건의 트레이스를 필터링하기가 쉽다. 단, PII(개인정보)는 스팬 속성에 넣지 않는다. 트레이스 데이터는 보통 오래 보관되고 접근 제어가 로그보다 느슨한 경우가 많다.

## 샘플링

모든 요청을 트레이스하면 수집기와 스토리지 부담이 크다. 프로덕션에서는 샘플링 비율을 조정한다.

```typescript
import { TraceIdRatioBasedSampler } from '@opentelemetry/sdk-trace-node';

const sdk = new NodeSDK({
  sampler: new TraceIdRatioBasedSampler(0.1), // 10%만 트레이스
  // ...
});
```

에러가 발생한 요청은 샘플링에서 제외하지 않도록 주의한다. 에러 트레이스를 항상 수집하려면 ParentBased 샘플러와 조합해서 사용한다.

```typescript
import {
  ParentBasedSampler,
  TraceIdRatioBasedSampler,
  AlwaysOnSampler,
} from '@opentelemetry/sdk-trace-node';

// 부모 컨텍스트가 있으면 부모의 샘플링 결정을 따르고,
// 루트 스팬은 10% 확률로 샘플링
const sdk = new NodeSDK({
  sampler: new ParentBasedSampler({
    root: new TraceIdRatioBasedSampler(0.1),
  }),
  // ...
});
```

에러 트레이스는 별도 커스텀 샘플러를 구현해서 항상 수집할 수 있다.

```typescript
import { Sampler, SamplingDecision, SamplingResult } from '@opentelemetry/sdk-trace-node';
import { SpanKind, Attributes, Link, Context } from '@opentelemetry/api';

class ErrorAwareSampler implements Sampler {
  private baseSampler: Sampler;

  constructor(ratio: number) {
    this.baseSampler = new TraceIdRatioBasedSampler(ratio);
  }

  shouldSample(
    ctx: Context,
    traceId: string,
    spanName: string,
    spanKind: SpanKind,
    attributes: Attributes,
    links: Link[],
  ): SamplingResult {
    // 에러 관련 요청은 무조건 수집
    if (attributes['http.status_code'] >= 400) {
      return { decision: SamplingDecision.RECORD_AND_SAMPLED };
    }
    return this.baseSampler.shouldSample(ctx, traceId, spanName, spanKind, attributes, links);
  }

  toString(): string {
    return 'ErrorAwareSampler';
  }
}

---
이 문서는 [관측성 허브](../../../_hub/관측성.md)의 일부입니다.
```
