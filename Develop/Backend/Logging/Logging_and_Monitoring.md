---
title: 로깅 & 모니터링 전략 가이드
tags: [backend, logging, monitoring, elk, efk, distributed-tracing, alerting, observability]
updated: 2026-03-01
---

# 로깅 & 모니터링 전략 가이드

## 개요

프로덕션 시스템에서 **관측 가능성(Observability)**은 세 가지 축으로 구성된다.

```
Observability = Logs + Metrics + Traces

Logs    → "무엇이 일어났는가" (이벤트 기록)
Metrics → "얼마나 발생하는가" (수치 측정)
Traces  → "어떤 경로로 흘러갔는가" (요청 추적)
```

| 축 | 도구 | 용도 |
|---|------|------|
| **Logs** | ELK, EFK, Loki | 에러 분석, 디버깅, 감사 |
| **Metrics** | Prometheus + Grafana | 성능 모니터링, 알림 |
| **Traces** | Jaeger, Zipkin, OpenTelemetry | MSA 요청 추적 |

## 핵심

### 1. 구조화된 로깅 (Structured Logging)

#### 기존 방식 vs 구조화 로깅

```
❌ 기존 (텍스트):
2026-03-01 10:30:00 ERROR 주문 처리 실패 - 주문번호: 12345, 사용자: user@email.com

✅ 구조화 (JSON):
{
  "timestamp": "2026-03-01T10:30:00Z",
  "level": "ERROR",
  "message": "주문 처리 실패",
  "orderId": 12345,
  "userId": "user@email.com",
  "errorCode": "PAYMENT_FAILED",
  "traceId": "abc-123-def",
  "service": "order-service"
}
```

📌 구조화된 로그는 **검색, 필터링, 집계**가 가능하다. `orderId=12345`로 관련 로그를 즉시 찾을 수 있다.

#### Spring Boot 구조화 로깅 설정

```xml
<!-- logback-spring.xml -->
<configuration>
    <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <customFields>{"service":"order-service","env":"prod"}</customFields>
        </encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="JSON" />
    </root>
</configuration>
```

```java
// 구조화 로깅 사용
@Slf4j
@Service
public class OrderService {

    public Order createOrder(CreateOrderRequest request) {
        log.info("주문 생성 시작: userId={}, items={}", request.getUserId(), request.getItems().size());

        try {
            Order order = processOrder(request);
            log.info("주문 생성 완료: orderId={}, totalPrice={}", order.getId(), order.getTotalPrice());
            return order;
        } catch (PaymentException e) {
            log.error("결제 실패: userId={}, errorCode={}", request.getUserId(), e.getCode(), e);
            throw e;
        }
    }
}
```

### 2. 로그 수준 가이드

| 수준 | 용도 | 예시 |
|------|------|------|
| **ERROR** | 즉시 대응 필요한 에러 | 결제 실패, DB 연결 끊김, 외부 API 장애 |
| **WARN** | 잠재적 문제, 곧 에러 가능 | 디스크 80% 사용, 재시도 발생, 지연 응답 |
| **INFO** | 비즈니스 이벤트, 정상 흐름 | 주문 생성, 사용자 로그인, 배포 완료 |
| **DEBUG** | 개발/디버깅 정보 | 쿼리 결과, 변수 값, 로직 분기 |
| **TRACE** | 최하위, 매우 상세 | 메서드 진입/반환, 루프 내부 |

```yaml
# application.yml - 환경별 로그 수준
logging:
  level:
    root: INFO
    com.example: INFO                  # 내 코드
    org.hibernate.SQL: WARN            # 프로덕션에서 쿼리 로그 OFF
    org.springframework.web: INFO
```

### 3. 로그 수집 스택

#### ELK (Elasticsearch + Logstash + Kibana)

```
App → Logstash → Elasticsearch → Kibana
      (수집/파싱)    (저장/검색)     (시각화)
```

| 구성 요소 | 역할 | 특징 |
|-----------|------|------|
| **Logstash** | 로그 수집, 파싱, 변환 | 강력한 필터, 무거움 |
| **Elasticsearch** | 로그 저장, 전문 검색 | 빠른 검색, 대용량 |
| **Kibana** | 시각화, 대시보드 | 검색 UI, 알림 |

#### EFK (Elasticsearch + Fluentd + Kibana)

Logstash 대신 **Fluentd**를 사용. Kubernetes 환경에서 표준이다.

```
각 Node의 DaemonSet (Fluentd)
    │  ← 컨테이너 stdout/stderr 수집
    ▼
Elasticsearch Cluster
    │
    ▼
Kibana (시각화)
```

| 비교 | Logstash | Fluentd |
|------|----------|---------|
| **언어** | Java (JRuby) | Ruby + C |
| **메모리** | 무거움 (~1GB) | 경량 (~40MB) |
| **K8s 친화** | 보통 | DaemonSet 표준 |
| **플러그인** | 풍부 | 매우 풍부 |

#### Loki (경량 대안)

Grafana Labs의 경량 로그 수집 시스템. Prometheus와 유사한 **라벨 기반** 접근이다.

```
App → Promtail → Loki → Grafana
      (수집 에이전트)  (저장)   (시각화)

장점: 경량, Grafana 통합, 인덱싱 최소화 → 비용 절감
단점: 전문 검색 미지원 (라벨 기반 필터만)
```

### 4. 분산 트레이싱

마이크로서비스 환경에서 하나의 요청이 여러 서비스를 거칠 때, **전체 흐름을 추적**하는 기술이다.

```
사용자 요청 (traceId: abc-123)
    │
    ▼
API Gateway (spanId: 001)
    │
    ├─▶ User Service (spanId: 002, parentId: 001)
    │
    ├─▶ Order Service (spanId: 003, parentId: 001)
    │       │
    │       └─▶ Payment Service (spanId: 004, parentId: 003)
    │
    └─▶ Notification Service (spanId: 005, parentId: 001)

모든 span이 같은 traceId를 공유 → 하나의 요청 흐름으로 조합
```

| 용어 | 설명 |
|------|------|
| **Trace** | 하나의 요청 전체 흐름 (여러 Span으로 구성) |
| **Span** | 단일 작업 단위 (서비스 호출 1회) |
| **Trace ID** | 전체 요청을 식별하는 고유 ID |
| **Span ID** | 각 Span의 고유 ID |
| **Parent Span ID** | 부모 Span의 ID (호출 관계 표현) |

#### Spring Boot + OpenTelemetry (Micrometer Tracing)

```gradle
// build.gradle
implementation 'io.micrometer:micrometer-tracing-bridge-otel'
implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
```

```yaml
# application.yml
management:
  tracing:
    sampling:
      probability: 1.0    # 전체 샘플링 (프로덕션: 0.1 등 조절)
  otlp:
    tracing:
      endpoint: http://jaeger:4318/v1/traces
```

```java
// traceId가 자동으로 로그에 포함됨
// logback 패턴: %d{yyyy-MM-dd HH:mm:ss} [%X{traceId}] %-5level %msg%n

@Slf4j
@Service
public class OrderService {

    public Order createOrder(CreateOrderRequest request) {
        log.info("주문 생성 시작");  // → 2026-03-01 10:30:00 [abc-123] INFO 주문 생성 시작
        // traceId가 자동으로 포함되어 서비스 간 추적 가능
    }
}
```

### 5. 메트릭 & 알림

#### Prometheus + Grafana

```
App ──/actuator/prometheus──▶ Prometheus ──▶ Grafana
     (메트릭 노출)              (수집/저장)     (시각화/알림)
```

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: prometheus, health, info
  metrics:
    tags:
      application: order-service
```

#### 핵심 모니터링 메트릭

| 카테고리 | 메트릭 | 의미 | 알림 기준 |
|---------|--------|------|----------|
| **응답 시간** | http_server_requests_seconds | API 응답 시간 | p99 > 3초 |
| **에러율** | http_server_requests (status=5xx) | 서버 에러 비율 | > 1% |
| **처리량** | http_server_requests_seconds_count | 초당 요청 수 | 급격한 변화 |
| **JVM** | jvm_memory_used_bytes | 메모리 사용량 | > 80% |
| **DB 커넥션** | hikaricp_connections_active | 활성 커넥션 수 | > 80% |
| **GC** | jvm_gc_pause_seconds | GC 중단 시간 | > 500ms |

#### 알림 설정 (Grafana)

| 수준 | 기준 | 조치 |
|------|------|------|
| **Critical** | 에러율 > 5%, 서비스 다운 | 즉시 대응 (Slack/PagerDuty) |
| **Warning** | 응답시간 p99 > 3s, 메모리 80% | 확인 필요 |
| **Info** | 배포 완료, 스케일 아웃 | 기록용 |

### 6. 로깅 모범 사례

| 원칙 | 설명 |
|------|------|
| **민감 정보 마스킹** | 비밀번호, 카드 번호 로그 금지 |
| **요청 ID 포함** | 모든 로그에 traceId 포함 |
| **구조화 로깅** | JSON 형식으로 검색 가능하게 |
| **적절한 수준** | ERROR 남발 금지 (알림 피로) |
| **로그 보관 정책** | 일반: 30일, 감사: 1년+ |
| **비용 관리** | DEBUG/TRACE는 프로덕션에서 OFF |

```java
// ❌ 나쁜 예
log.error("에러 발생");                          // 정보 없음
log.info("User: " + user.toString());            // 민감 정보 노출 가능
log.debug("Processing...");                      // 의미 없는 로그

// ✅ 좋은 예
log.error("결제 실패: orderId={}, errorCode={}", orderId, e.getCode(), e);
log.info("사용자 로그인: userId={}", user.getId());   // ID만 기록
log.debug("캐시 조회: key={}, hit={}", cacheKey, cacheHit);
```

## 운영 팁

### 스택 선택 가이드

| 상황 | 추천 스택 |
|------|----------|
| 소규모, 빠른 시작 | **Loki + Grafana** |
| 중대규모, 전문 검색 필요 | **ELK / EFK** |
| K8s 환경 | **EFK** (Fluentd DaemonSet) |
| 이미 Grafana 사용 중 | **Loki** (통합 대시보드) |
| AWS 환경 | **CloudWatch** 또는 **OpenSearch** |

### Observability 성숙도

| 수준 | 구현 |
|------|------|
| **Level 1** | 기본 로깅 (파일 기반, 수동 검색) |
| **Level 2** | 중앙 집중 로깅 (ELK/Loki) + 기본 메트릭 |
| **Level 3** | 구조화 로깅 + Prometheus/Grafana + 알림 |
| **Level 4** | 분산 트레이싱 + 자동 알림 + 대시보드 |
| **Level 5** | AIOps (이상 감지, 자동 대응) |

## 참고

- [OpenTelemetry 공식 문서](https://opentelemetry.io/docs/)
- [Elasticsearch 공식 문서](https://www.elastic.co/guide/index.html)
- [Grafana Loki 공식 문서](https://grafana.com/docs/loki/latest/)
- [Prometheus 메트릭 수집 가이드](../../DevOps/Monitoring/Prometheus_메트릭_수집.md)
- [Grafana](../../DevOps/Monitoring/Grafana.md)
- [로깅 전략 (Node.js)](../../Framework/Node/로깅/로깅_전략.md)
