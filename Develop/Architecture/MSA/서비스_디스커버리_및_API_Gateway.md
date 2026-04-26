---
title: 서비스 디스커버리와 API Gateway
tags: [backend, msa, service-discovery, api-gateway, infrastructure]
updated: 2026-03-28
---

# 서비스 디스커버리와 API Gateway

## 개요

MSA 환경에서 서비스 인스턴스는 동적으로 생성되고 사라진다. 오토스케일링으로 인스턴스가 3개에서 10개로 늘어나기도 하고, 배포 중에 기존 인스턴스가 내려가기도 한다. IP와 포트가 고정되지 않는 환경에서 서비스 간 통신을 어떻게 연결할 것인지가 서비스 디스커버리 문제다.

API Gateway는 클라이언트와 내부 서비스 사이의 진입점이다. 라우팅, 인증, 속도 제한 같은 공통 관심사를 한 곳에서 처리한다.

이 문서는 서비스 디스커버리의 동작 방식, API Gateway의 역할과 구조, 실무에서 겪는 문제를 다룬다.

---

## 서비스 디스커버리

### 왜 필요한가

모놀리식에서는 서비스가 하나의 프로세스 안에서 돌아간다. 메서드 호출이니까 주소를 알 필요가 없다.

MSA에서는 다르다. 주문 서비스가 결제 서비스를 호출하려면 결제 서비스의 IP와 포트를 알아야 한다. 문제는 이 정보가 고정되지 않는다는 점이다.

**IP가 바뀌는 상황:**

- 컨테이너가 재시작되면 새 IP를 받는다
- 오토스케일링으로 인스턴스가 추가되면 새 IP가 생긴다
- 다른 노드로 재배치되면 IP가 바뀐다
- 배포 시 기존 인스턴스가 내려가고 새 인스턴스가 올라온다

설정 파일에 IP를 하드코딩하면 인스턴스가 바뀔 때마다 모든 호출자의 설정을 수정해야 한다. 서비스가 수십 개면 관리가 불가능하다.

### 서비스 레지스트리

서비스 레지스트리는 현재 실행 중인 서비스 인스턴스 목록을 관리하는 저장소다. 전화번호부처럼 "결제 서비스"라는 이름으로 조회하면 실행 중인 인스턴스의 주소 목록을 돌려준다.

**동작 흐름:**

1. 서비스 인스턴스가 시작되면 레지스트리에 자신의 주소를 등록한다
2. 주기적으로 헬스체크를 보내서 자신이 살아있음을 알린다
3. 헬스체크가 일정 시간 동안 오지 않으면 레지스트리가 해당 인스턴스를 목록에서 제거한다
4. 서비스가 종료되면 레지스트리에서 등록을 해제한다

### Eureka와 Consul 비교

#### Eureka

Netflix가 만든 서비스 레지스트리다. Spring Cloud 생태계에서 많이 사용한다.

**동작 방식:**

- 서비스가 시작되면 Eureka Server에 REST API로 자신을 등록한다
- 30초마다 하트비트를 보낸다
- 90초 동안 하트비트가 없으면 인스턴스를 제거한다
- 클라이언트가 레지스트리 정보를 로컬에 캐시한다. Eureka Server가 죽어도 캐시된 정보로 통신이 가능하다

```java
// Spring Cloud에서 Eureka 클라이언트 설정
@SpringBootApplication
@EnableDiscoveryClient
public class PaymentServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(PaymentServiceApplication.class, args);
    }
}
```

```yaml
# application.yml
eureka:
  client:
    service-url:
      defaultZone: http://eureka-server:8761/eureka/
  instance:
    prefer-ip-address: true
    lease-renewal-interval-in-seconds: 30    # 하트비트 주기
    lease-expiration-duration-in-seconds: 90  # 만료 시간
```

**Eureka의 자기 보호 모드:**

네트워크 문제로 다수의 인스턴스에서 하트비트가 동시에 끊기면, Eureka는 인스턴스를 제거하지 않고 보호 모드에 들어간다. 네트워크가 복구되면 다시 정상 동작한다.

이 동작 때문에 이미 죽은 인스턴스가 레지스트리에 남아있을 수 있다. 클라이언트에서 호출 실패 시 재시도 로직이 필요한 이유다.

#### Consul

HashiCorp가 만든 서비스 메시 도구다. 서비스 디스커버리 외에 KV Store, 헬스체크, 멀티 데이터센터 지원 같은 기능이 있다.

**동작 방식:**

- 각 노드에 Consul Agent가 실행된다
- 서비스 등록은 로컬 Agent에 한다
- Agent들이 gossip protocol로 서로 정보를 교환한다
- 헬스체크가 더 다양하다. HTTP, TCP, gRPC, 스크립트 실행 등을 지원한다

```json
// Consul 서비스 등록 (JSON 설정)
{
  "service": {
    "name": "payment-service",
    "port": 8080,
    "tags": ["v2", "production"],
    "check": {
      "http": "http://localhost:8080/health",
      "interval": "10s",
      "timeout": "3s"
    }
  }
}
```

**Eureka vs Consul 선택 기준:**

| 항목 | Eureka | Consul |
|------|--------|--------|
| CAP 정리 | AP (가용성 우선) | CP (일관성 우선, Raft 합의) |
| 생태계 | Spring Cloud 중심 | 언어 무관 |
| 헬스체크 | 하트비트 기반 | HTTP, TCP, gRPC, 스크립트 |
| 추가 기능 | 서비스 디스커버리만 | KV Store, 서비스 메시, ACL |
| 멀티 DC | 미지원 | 지원 |

Spring 기반 프로젝트에서 서비스 디스커버리만 필요하면 Eureka가 간단하다. 멀티 언어 환경이거나 KV Store, ACL 같은 부가 기능이 필요하면 Consul을 쓴다.

### 클라이언트 사이드 디스커버리 vs 서버 사이드 디스커버리

서비스 디스커버리에는 두 가지 패턴이 있다. 누가 레지스트리를 조회하고 로드 밸런싱을 결정하는지가 차이점이다.

#### 클라이언트 사이드 디스커버리

호출하는 쪽(클라이언트)이 레지스트리를 직접 조회해서 인스턴스를 고른다.

**흐름:**

1. 주문 서비스가 결제 서비스를 호출하려 한다
2. 주문 서비스가 레지스트리에서 결제 서비스 인스턴스 목록을 가져온다
3. 주문 서비스가 직접 로드 밸런싱 알고리즘(라운드 로빈, 랜덤 등)으로 하나를 선택한다
4. 선택한 인스턴스에 직접 요청을 보낸다

```java
// Spring Cloud LoadBalancer를 사용한 클라이언트 사이드 디스커버리
@Configuration
public class RestClientConfig {
    @Bean
    @LoadBalanced  // 서비스 이름으로 호출하면 자동으로 인스턴스를 선택한다
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}

@Service
public class OrderService {
    private final RestTemplate restTemplate;

    public PaymentResponse requestPayment(Long orderId) {
        // "payment-service"는 Eureka에 등록된 서비스 이름이다
        // LoadBalancer가 실제 IP:Port로 변환한다
        return restTemplate.postForObject(
            "http://payment-service/api/payments",
            new PaymentRequest(orderId),
            PaymentResponse.class
        );
    }
}
```

**장점:**

- 중간 프록시가 없으니 네트워크 홉이 줄어든다
- 클라이언트가 로드 밸런싱 정책을 서비스별로 다르게 적용할 수 있다

**단점:**

- 모든 클라이언트에 디스커버리 로직이 들어간다. 언어별로 구현이 필요하다
- 클라이언트와 레지스트리가 결합된다

#### 서버 사이드 디스커버리

호출자는 로드 밸런서(또는 프록시)에 요청을 보내고, 로드 밸런서가 레지스트리를 조회해서 라우팅한다.

**흐름:**

1. 주문 서비스가 로드 밸런서에 요청을 보낸다
2. 로드 밸런서가 레지스트리에서 결제 서비스 인스턴스 목록을 조회한다
3. 로드 밸런서가 하나를 선택해서 요청을 전달한다

AWS ELB, Kubernetes의 Service가 이 패턴이다. Kubernetes에서 `payment-service`라는 Service를 만들면, kube-proxy가 알아서 Pod 목록을 관리하고 로드 밸런싱한다. 호출하는 쪽은 `http://payment-service:8080`으로 요청하면 된다.

**장점:**

- 클라이언트가 디스커버리 로직을 몰라도 된다. 언어에 상관없이 동작한다
- 디스커버리 로직이 한 곳에 집중되어 관리가 쉽다

**단점:**

- 로드 밸런서가 추가 홉이 된다. 지연 시간이 약간 늘어난다
- 로드 밸런서 자체가 장애 지점이 될 수 있다

**실무에서는:** Kubernetes 환경이면 서버 사이드 디스커버리가 기본으로 제공된다. Spring Cloud 환경에서 Eureka를 쓰면 클라이언트 사이드 디스커버리가 자연스럽다. 환경에 맞는 걸 쓰면 된다.

---

## API Gateway

### 역할

API Gateway는 외부 클라이언트의 모든 요청이 거쳐가는 진입점이다. 내부 서비스 구조를 외부에 노출하지 않으면서, 공통 처리를 한 곳에서 담당한다.

**API Gateway가 없으면 생기는 문제:**

- 클라이언트가 각 서비스의 주소를 모두 알아야 한다. 서비스가 30개면 30개의 엔드포인트를 관리해야 한다
- 인증/인가 로직을 모든 서비스에 각각 구현해야 한다
- CORS, Rate Limiting 같은 정책도 서비스마다 따로 적용해야 한다
- 서비스 분리/병합 시 클라이언트가 영향을 받는다

**API Gateway가 처리하는 것:**

- **라우팅:** `/api/orders/*` 요청을 주문 서비스로, `/api/payments/*` 요청을 결제 서비스로 전달한다
- **인증 위임:** JWT 토큰 검증을 Gateway에서 처리하고, 인증된 사용자 정보를 헤더에 실어서 내부 서비스로 전달한다
- **속도 제한:** 특정 클라이언트의 요청이 초당 100건을 넘으면 429 응답을 돌려준다
- **요청/응답 변환:** 내부 서비스의 응답 형식을 클라이언트에 맞게 변환한다
- **로깅과 모니터링:** 모든 요청의 진입점이니까 여기서 로그를 남기면 전체 트래픽을 한눈에 볼 수 있다

### 라우팅과 인증 위임 구조

실무에서 가장 흔한 구성은 Gateway에서 인증을 처리하고 내부 서비스는 인증을 신뢰하는 구조다.

**요청 흐름:**

```
클라이언트 → API Gateway → 내부 서비스
                │
                ├─ 1. JWT 토큰 검증
                ├─ 2. 토큰에서 사용자 정보 추출
                ├─ 3. Rate Limit 확인
                ├─ 4. 라우팅 규칙에 따라 내부 서비스 선택
                └─ 5. X-User-Id, X-User-Role 헤더에 사용자 정보를 실어서 전달
```

```yaml
# Kong의 라우팅 설정 예시 (declarative config)
_format_version: "3.0"

services:
  - name: order-service
    url: http://order-service:8080
    routes:
      - name: order-route
        paths:
          - /api/orders
        strip_path: false

  - name: payment-service
    url: http://payment-service:8080
    routes:
      - name: payment-route
        paths:
          - /api/payments
        strip_path: false

plugins:
  - name: jwt
    config:
      claims_to_verify:
        - exp
  - name: rate-limiting
    config:
      minute: 60
      policy: redis
      redis_host: redis
```

```yaml
# Spring Cloud Gateway 설정 예시
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service    # lb:// 접두사가 로드 밸런싱을 의미한다
          predicates:
            - Path=/api/orders/**
          filters:
            - name: JwtAuthFilter    # 커스텀 필터로 JWT 검증
            - name: AddRequestHeader
              args:
                name: X-Gateway-Auth
                value: "true"
        - id: payment-service
          uri: lb://payment-service
          predicates:
            - Path=/api/payments/**
```

**인증 위임 시 주의할 점:**

내부 서비스가 Gateway의 인증 결과를 무조건 신뢰하면, Gateway를 우회해서 직접 내부 서비스에 접근하는 경우가 위험하다. 내부 네트워크 정책으로 외부에서 내부 서비스에 직접 접근하는 것을 차단해야 한다. Kubernetes라면 NetworkPolicy로 제어할 수 있다.

### Kong과 AWS API Gateway 비교

#### Kong

오픈소스 API Gateway다. Nginx 기반이라 성능이 좋고, 플러그인으로 기능을 확장한다.

**특징:**

- Lua로 작성된 플러그인 시스템. 커스텀 플러그인을 만들 수 있다
- PostgreSQL이나 Cassandra에 설정을 저장한다. DB 없이 선언적 설정 파일로도 동작한다 (DB-less 모드)
- 자체 호스팅이 필요하다. 인프라 관리 부담이 있다
- 서비스 메시 기능도 제공한다 (Kong Mesh)

**Kong을 선택하는 경우:**

- 플러그인으로 커스텀 로직이 필요할 때
- 멀티 클라우드나 온프레미스 환경일 때
- Gateway 동작을 세밀하게 제어해야 할 때

#### AWS API Gateway

AWS 관리형 서비스다. 인프라 관리 없이 사용할 수 있다.

**특징:**

- REST API, HTTP API, WebSocket API 세 가지 타입이 있다. HTTP API가 가장 가볍고 저렴하다
- Lambda와 연동이 자연스럽다. 서버리스 아키텍처에서 많이 쓴다
- IAM, Cognito와 통합되어 인증/인가 설정이 간단하다
- 사용량 기반 과금이다. 트래픽이 적으면 저렴하고 많으면 비용이 올라간다

**AWS API Gateway를 선택하는 경우:**

- AWS 환경에서 Lambda 기반 서버리스 아키텍처를 사용할 때
- 인프라 관리를 최소화하고 싶을 때
- AWS 서비스(Cognito, IAM, CloudWatch)와 연동이 필요할 때

**비용 관점에서 주의할 점:** AWS API Gateway는 요청 수 기반 과금이다. 트래픽이 월 수억 건을 넘어가면 비용이 Kong 자체 호스팅보다 비싸질 수 있다. 트래픽 규모를 예측하고 비교해봐야 한다.

### Gateway의 Single Point of Failure 문제

모든 트래픽이 Gateway를 거치니까, Gateway가 죽으면 전체 시스템이 멈춘다. 이 문제를 어떻게 다루는지가 중요하다.

#### Gateway 다중화

Gateway 인스턴스를 여러 개 띄우고 앞에 로드 밸런서를 두는 게 기본이다.

```
클라이언트 → L4 로드 밸런서 (NLB)
                ├─ Gateway 인스턴스 1
                ├─ Gateway 인스턴스 2
                └─ Gateway 인스턴스 3
```

AWS 환경이면 NLB(Network Load Balancer) 뒤에 Gateway 인스턴스를 배치한다. NLB 자체는 AWS가 관리하는 고가용성 서비스라서 단일 장애 지점이 되지 않는다.

Kubernetes 환경이면 Gateway를 Deployment로 배포하고 replicas를 3 이상으로 설정한다. HPA(Horizontal Pod Autoscaler)를 걸어서 트래픽에 따라 자동 확장되게 한다.

```yaml
# Kubernetes에서 Kong Gateway 배포 예시
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kong-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kong-gateway
  template:
    metadata:
      labels:
        app: kong-gateway
    spec:
      containers:
        - name: kong
          image: kong:3.6
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
          readinessProbe:
            httpGet:
              path: /status
              port: 8100
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /status
              port: 8100
            initialDelaySeconds: 15
            periodSeconds: 20
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kong-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kong-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

#### Gateway 장애 시 대응 패턴

**Circuit Breaker 설정:**

Gateway에서 내부 서비스 호출이 계속 실패하면 해당 서비스로의 요청을 차단한다. 장애가 전파되는 것을 막는다.

```yaml
# Spring Cloud Gateway + Resilience4j 설정
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: CircuitBreaker
              args:
                name: orderServiceCB
                fallbackUri: forward:/fallback/orders

resilience4j:
  circuitbreaker:
    instances:
      orderServiceCB:
        slidingWindowSize: 10
        failureRateThreshold: 50       # 실패율 50% 넘으면 차단
        waitDurationInOpenState: 30s    # 30초 후 재시도
        permittedNumberOfCallsInHalfOpenState: 3
```

**Timeout 설정:**

Gateway에서 내부 서비스 응답을 무한정 기다리면 커넥션이 쌓이면서 Gateway 자체가 죽는다. 반드시 타임아웃을 설정해야 한다.

```yaml
spring:
  cloud:
    gateway:
      httpclient:
        connect-timeout: 3000    # 연결 타임아웃 3초
        response-timeout: 10s    # 응답 타임아웃 10초
```

**헬스체크와 자동 복구:**

Gateway 인스턴스에 헬스체크를 걸어서 비정상 인스턴스를 자동으로 제거하고 새로 띄운다. Kubernetes의 liveness/readiness probe가 이 역할을 한다.

#### 실무에서 겪는 Gateway 관련 문제

**1. Gateway에 비즈니스 로직이 들어가는 경우:**

처음에는 라우팅과 인증만 하다가, 점점 응답 조합, 데이터 변환, 캐싱 같은 로직이 추가된다. Gateway가 뚱뚱해지면 배포가 어려워지고 장애 영향 범위가 커진다. Gateway는 가능한 한 얇게 유지해야 한다. 비즈니스 로직은 BFF(Backend For Frontend) 레이어를 별도로 두는 게 낫다.

**2. Gateway 설정 변경 시 전체 서비스에 영향:**

라우팅 규칙을 잘못 변경하면 모든 서비스에 영향이 간다. Gateway 설정 변경은 카나리 배포로 점진적으로 적용하거나, Gateway 설정 자체를 코드로 관리(GitOps)해서 리뷰 과정을 거쳐야 한다.

**3. Gateway 로그가 폭발하는 경우:**

모든 요청이 거치니까 로그 양이 많다. 전체 요청을 로깅하면 저장소 비용이 급격히 늘어난다. 샘플링 비율을 조절하거나, 에러 응답만 상세 로깅하는 방식으로 조절한다.

---

## 서비스 디스커버리와 API Gateway의 관계

이 둘은 별개가 아니라 함께 동작한다.

```
클라이언트 → API Gateway → 서비스 디스커버리 → 내부 서비스 인스턴스
```

API Gateway가 내부 서비스로 요청을 전달할 때, 해당 서비스의 주소를 어디서 가져오는지가 서비스 디스커버리의 역할이다.

- Kong + Consul: Kong이 Consul에서 서비스 주소를 조회해서 라우팅한다
- Spring Cloud Gateway + Eureka: Gateway가 Eureka에서 서비스 목록을 가져온다. `lb://service-name` URI가 이 연동을 의미한다
- Kubernetes: Service 리소스가 디스커버리와 로드 밸런싱을 모두 처리한다. Gateway(Ingress Controller)는 Service를 통해 Pod에 접근한다

Kubernetes를 쓴다면 별도의 서비스 디스커버리 도구 없이 Kubernetes 자체 기능으로 충분한 경우가 많다. Eureka나 Consul은 Kubernetes를 사용하지 않는 환경이거나, 멀티 클러스터 간 디스커버리가 필요할 때 도입을 검토한다.
