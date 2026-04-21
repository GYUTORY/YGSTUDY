---
title: Istio와 Service Mesh
tags: [infra, service-mesh, istio, envoy, kubernetes, observability]
updated: 2026-04-21
---

# Istio와 Service Mesh

## 1. Service Mesh가 왜 필요한가

마이크로서비스로 쪼개고 나면 서비스끼리 부르는 네트워크 호출이 폭증한다. 이때 애플리케이션 코드에서 해결해야 하는 문제가 늘어난다.

- 서비스 간 인증/암호화 (서로 정말 그 서비스인지 확인)
- 재시도, 타임아웃, 서킷브레이커 같은 장애 격리
- 카나리 배포, A/B 테스트를 위한 트래픽 분기
- 누가 누구를 얼마나 호출하는지 추적 (분산 트레이싱)
- 특정 서비스가 느릴 때 어디가 병목인지 파악

예전에는 이걸 전부 라이브러리(Spring Cloud의 Hystrix, Netflix Ribbon 같은)로 해결했다. 문제는 언어마다 똑같은 기능을 다시 만들어야 하고, 라이브러리 버전이 올라갈 때마다 모든 서비스를 재배포해야 한다는 점이다. Node.js, Go, Python, Java 서비스가 섞여 있으면 유지보수가 악몽이 된다.

Service Mesh는 이 공통 기능을 **애플리케이션 밖으로 빼낸다**. 각 파드 옆에 프록시(사이드카)를 붙여서 모든 네트워크 트래픽을 대신 처리하게 만든다. 애플리케이션은 `localhost:8080`으로 요청만 보내면 되고, 나머지는 프록시가 알아서 한다.

```
기존 방식 (라이브러리 기반):
┌─────────────────────┐
│  App (Java)         │
│  + Hystrix          │
│  + Ribbon           │
│  + Sleuth           │──── mTLS, retry, 트레이싱을
│  + Eureka Client    │     애플리케이션이 직접 처리
└─────────────────────┘

Service Mesh 방식:
┌─────────────┐    ┌──────────────┐
│  App        │───▶│  Sidecar     │──── 네트워크 기능은
│  (아무 언어)  │    │  (Envoy)     │     프록시가 처리
└─────────────┘    └──────────────┘
```

실무에서 Istio를 도입하는 시점은 보통 마이크로서비스가 10~20개를 넘어가면서 공통 네트워크 로직을 중앙에서 관리하고 싶어지는 때다. 그 이하라면 Istio의 복잡도가 오히려 손해다.

---

## 2. Istio 아키텍처

Istio는 두 개의 평면으로 나뉜다.

### 2.1 데이터 플레인 (Data Plane)

실제 트래픽이 흐르는 경로다. 각 파드마다 **Envoy 프록시**가 사이드카 컨테이너로 붙어서, 파드의 모든 인바운드/아웃바운드 트래픽을 가로챈다.

트래픽이 Envoy로 흘러들어가는 원리는 `iptables` 룰이다. Istio가 사이드카를 주입할 때 `istio-init` initContainer를 먼저 실행하는데, 이게 파드 네트워크 네임스페이스 안에서 iptables 룰을 설정해 모든 TCP 트래픽을 Envoy 포트(15001, 15006)로 리다이렉트한다.

```
파드 네트워크 네임스페이스 내부:

  App 컨테이너 ──(localhost:8080)──▶ 외부 호출
                                        │
                                        ▼
                              iptables 룰이 가로챔
                                        │
                                        ▼
                              Envoy (15001 포트)
                                        │
                                        ▼
                              실제 목적지로 전송
                              (mTLS, 재시도, 로깅 후)
```

Envoy를 쓰는 이유는 C++ 기반으로 빠르고, xDS라는 API로 런타임 설정 변경이 가능하기 때문이다. 재시작 없이 라우팅 룰을 바꿀 수 있는 게 핵심이다.

### 2.2 컨트롤 플레인 (Control Plane)

`istiod`라는 단일 바이너리다. 1.5 이전에는 Pilot, Citadel, Galley 등으로 쪼개져 있었는데 통합됐다. 하는 일은 세 가지다.

- **Pilot 역할**: VirtualService, DestinationRule 같은 Istio 리소스를 읽어서 각 Envoy가 이해할 수 있는 설정(xDS)으로 변환해서 배포
- **Citadel 역할**: 서비스마다 인증서를 자동 발급하고 회전 (mTLS의 기반)
- **Galley 역할**: Kubernetes API로부터 설정을 받아 검증

실무에서 istiod가 죽으면 어떻게 되느냐 하면, **이미 배포된 Envoy 설정은 계속 동작한다**. 다만 새로운 파드가 뜨거나 설정 변경이 반영되지 않을 뿐이다. 그래서 istiod는 HA 구성(replica 2~3)이 권장된다.

```
┌─────────────────────────────────────────────────┐
│              Control Plane                      │
│  ┌──────────────────────────────────┐          │
│  │  istiod                          │          │
│  │  - Config 관리                    │          │
│  │  - 인증서 발급                     │          │
│  │  - xDS로 Envoy에 설정 푸시          │          │
│  └──────────────────────────────────┘          │
└────────────────┬────────────────────────────────┘
                 │ xDS (gRPC 스트리밍)
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│ Pod A  │  │ Pod B  │  │ Pod C  │
│ ┌────┐ │  │ ┌────┐ │  │ ┌────┐ │
│ │App │ │  │ │App │ │  │ │App │ │
│ └────┘ │  │ └────┘ │  │ └────┘ │
│ ┌────┐ │  │ ┌────┐ │  │ ┌────┐ │
│ │Envoy│─┼──┼▶│Envoy│─┼──┼▶│Envoy│ │
│ └────┘ │  │ └────┘ │  │ └────┘ │
└────────┘  └────────┘  └────────┘
         Data Plane
```

---

## 3. 핵심 리소스: VirtualService, DestinationRule, Gateway

Istio를 쓴다는 건 결국 이 세 리소스로 라우팅을 제어한다는 뜻이다. 각 리소스가 담당하는 계층이 다르다.

### 3.1 Gateway

클러스터 외부에서 들어오는 트래픽의 진입점을 정의한다. 쿠버네티스의 `Ingress`와 비슷하지만 L4/L7 세밀한 제어가 가능하다. 실제로는 `istio-ingressgateway`라는 Envoy 파드가 Gateway 설정을 받아서 동작한다.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: shop-gateway
  namespace: shop
spec:
  selector:
    istio: ingressgateway  # 어떤 게이트웨이 파드가 처리할지
  servers:
    - port:
        number: 443
        name: https
        protocol: HTTPS
      tls:
        mode: SIMPLE
        credentialName: shop-tls-cert  # Secret 이름
      hosts:
        - shop.example.com
```

Gateway 자체는 "어떤 포트/호스트/TLS로 받을지"만 정의한다. 받은 트래픽을 어느 서비스로 보낼지는 VirtualService가 결정한다.

### 3.2 VirtualService

라우팅 규칙을 정의한다. 경로, 헤더, 쿼리 스트링, 쿠키 등 다양한 기준으로 트래픽을 분기할 수 있다.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: shop-vs
  namespace: shop
spec:
  hosts:
    - shop.example.com
  gateways:
    - shop-gateway    # 외부 진입은 이 Gateway
    - mesh            # 클러스터 내부 호출도 같이 처리
  http:
    - match:
        - uri:
            prefix: /api/v1
      route:
        - destination:
            host: shop-service
            subset: v1
          weight: 90
        - destination:
            host: shop-service
            subset: v2
          weight: 10
    - match:
        - headers:
            x-user-group:
              exact: internal
      route:
        - destination:
            host: shop-service
            subset: canary
```

이 설정은 `/api/v1`으로 오는 요청의 90%를 v1, 10%를 v2로 보내고, `x-user-group: internal` 헤더가 있으면 무조건 canary로 보낸다.

`gateways: mesh`를 넣으면 클러스터 내부의 서비스 간 호출에도 이 라우팅이 적용된다. 넣지 않으면 외부 진입 트래픽만 대상이 된다. 이 차이 때문에 "내부 호출 카나리가 왜 안 먹히지?" 하고 디버깅했던 적이 있다.

### 3.3 DestinationRule

VirtualService가 "어디로 보낼지"를 결정한다면, DestinationRule은 "보낸 뒤 어떻게 처리할지"를 결정한다. 서브셋 정의, 로드밸런싱 정책, 커넥션 풀, 서킷브레이커 설정 등이 여기 들어간다.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: shop-dr
  namespace: shop
spec:
  host: shop-service
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http2MaxRequests: 1000
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
    - name: canary
      labels:
        version: canary
```

서브셋은 서비스의 논리적 구분이고, 라벨 셀렉터로 실제 파드와 매칭한다. VirtualService에서 `subset: v1`이라고 쓴 게 여기 정의된 서브셋을 참조하는 것이다.

세 리소스의 관계를 정리하면 이렇다.

```
외부 요청
  │
  ▼
Gateway (어느 포트/호스트로 받을지)
  │
  ▼
VirtualService (어느 서비스/서브셋으로 보낼지)
  │
  ▼
DestinationRule (서브셋 정의, 로드밸런싱, 커넥션 풀)
  │
  ▼
실제 Pod
```

---

## 4. mTLS 자동화

Istio의 가장 큰 매력 중 하나가 mTLS(상호 TLS) 자동화다. 애플리케이션 코드는 HTTP 평문을 보내지만, Envoy가 알아서 TLS로 감싸서 보내고 상대편 Envoy가 복호화해서 HTTP로 전달한다.

인증서 발급과 회전은 istiod가 담당한다. 각 서비스 계정(ServiceAccount)마다 SPIFFE ID 기반 인증서를 자동 발급하고, 24시간마다 갱신한다.

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: shop
spec:
  mtls:
    mode: STRICT   # 반드시 mTLS, 평문 거부
```

모드는 세 가지다.

- `PERMISSIVE`: mTLS와 평문 둘 다 허용. 점진적 전환 시 사용
- `STRICT`: mTLS만 허용. 사이드카 없는 파드는 통신 불가
- `DISABLE`: mTLS 비활성화

실무에서 처음부터 STRICT로 가면 사이드카가 없는 레거시 서비스나 모니터링 에이전트가 통신을 못 하는 사고가 난다. 보통 PERMISSIVE로 시작해서 모든 서비스가 사이드카를 갖게 되면 STRICT로 넘어간다.

mTLS가 실제 동작하는지 확인은 `istioctl authn tls-check` 명령으로 가능하다.

```bash
istioctl authn tls-check shop-service.shop.svc.cluster.local
```

또 하나 함정은 **mTLS는 같은 메쉬 내부에서만 동작한다**는 점이다. 외부에서 들어오는 트래픽은 Gateway에서 일반 TLS로 종료되고, 메쉬 내부로 들어올 때 mTLS로 다시 포장된다.

---

## 5. 트래픽 분할과 카나리

Istio를 도입하는 가장 흔한 이유가 카나리 배포다. Kubernetes의 `Deployment` 전략으로도 되긴 하지만, 비율 제어가 파드 수에 종속되어 정밀하지 않다. 파드 10개 중 1개가 v2면 10%지만, 3%로 가고 싶으면 파드를 30개 이상 만들어야 한다.

Istio는 라우팅 레벨에서 비율을 제어하므로 파드 수와 무관하게 1%도 가능하다.

```yaml
# 초기: 전부 v1
spec:
  http:
    - route:
        - destination: { host: shop-service, subset: v1 }
          weight: 100
---
# 카나리 시작: v2로 5%
spec:
  http:
    - route:
        - destination: { host: shop-service, subset: v1 }
          weight: 95
        - destination: { host: shop-service, subset: v2 }
          weight: 5
---
# 점진적 확대: 50/50
spec:
  http:
    - route:
        - destination: { host: shop-service, subset: v1 }
          weight: 50
        - destination: { host: shop-service, subset: v2 }
          weight: 50
---
# 완료: v2 전환
spec:
  http:
    - route:
        - destination: { host: shop-service, subset: v2 }
          weight: 100
```

헤더 기반 라우팅과 조합하면 "내부 직원에게만 먼저 신버전 노출" 같은 시나리오도 쉽다.

```yaml
http:
  - match:
      - headers:
          x-internal-user: { exact: "true" }
    route:
      - destination: { host: shop-service, subset: v2 }
  - route:
      - destination: { host: shop-service, subset: v1 }
```

Argo Rollouts와 Istio를 묶어 쓰면 비율 조정과 메트릭 검증을 자동화할 수 있다. 운영 단계에서는 이 조합이 거의 표준처럼 쓰인다.

---

## 6. 서킷브레이커, 재시도, 타임아웃

### 6.1 타임아웃

VirtualService에 `timeout`을 설정한다. 기본값은 없음(무한)이라 반드시 지정해야 한다. 이걸 안 걸어두면 다운스트림 서비스가 느려질 때 호출 스레드가 전부 대기에 빠져 전체 서비스가 마비된다.

```yaml
http:
  - route:
      - destination: { host: payment-service }
    timeout: 3s
```

### 6.2 재시도

네트워크 일시 오류에 대응한다. 주의할 점은 **POST 같은 비멱등 요청에 무조건 재시도를 걸면 중복 결제 같은 사고가 난다**는 것이다. `retryOn`으로 재시도 조건을 명시해야 한다.

```yaml
http:
  - route:
      - destination: { host: payment-service }
    timeout: 3s
    retries:
      attempts: 3
      perTryTimeout: 1s
      retryOn: 5xx,reset,connect-failure
```

`perTryTimeout`은 각 재시도의 타임아웃이다. 전체 `timeout`(3s) 안에 3번 시도(각 1s)가 들어가야 하므로 계산이 맞는지 확인해야 한다.

### 6.3 서킷브레이커

DestinationRule의 `outlierDetection`으로 구성한다. 정확히는 이상치 탐지 기반 이젝션이라 엄밀한 서킷브레이커와는 다르지만, 실무에서는 같은 용도로 쓴다.

```yaml
trafficPolicy:
  outlierDetection:
    consecutive5xxErrors: 5      # 연속 5번 5xx면
    interval: 30s                # 30초 간격으로 검사
    baseEjectionTime: 30s        # 30초간 트래픽 차단
    maxEjectionPercent: 50       # 최대 절반까지만 이젝션
```

동작 방식은 간단하다. 특정 엔드포인트(파드 IP)가 연속으로 에러를 내면, 로드밸런싱 풀에서 잠시 빼버린다. 30초 뒤 다시 풀에 넣어보고, 여전히 에러면 더 오래 뺀다(`baseEjectionTime` × 이젝션 횟수).

`maxEjectionPercent`는 중요하다. 이걸 100으로 두면 장애 전파 시 모든 파드가 이젝션되어 서비스가 완전히 끊긴다. 절반 정도로 제한해 두는 게 안전하다.

커넥션 풀 제한도 같이 설정하는 게 좋다. 다운스트림이 처리 가능한 수준을 넘는 요청이 쌓이면 메모리 폭주로 이어진다.

```yaml
trafficPolicy:
  connectionPool:
    tcp:
      maxConnections: 100
    http:
      http1MaxPendingRequests: 50    # 대기 큐 크기
      http2MaxRequests: 1000
      maxRequestsPerConnection: 10
```

---

## 7. Observability: Kiali와 Jaeger

Istio 자체가 메트릭/로그/트레이싱을 쏟아내므로, 이를 수집/시각화하는 스택을 붙여야 한다. 기본 조합은 Prometheus + Grafana + Jaeger + Kiali다.

### 7.1 Kiali

메쉬 토폴로지 뷰어다. 어떤 서비스가 어떤 서비스를 호출하고, 실시간 RPS/에러율이 얼마인지 그래프로 보여준다. 장애 발생 시 "어느 서비스가 빨간색인지" 가장 먼저 보는 도구다.

Kiali는 Prometheus에서 메트릭을 읽고, Istio 리소스는 Kubernetes API에서 읽어서 조합한다. 그래서 Prometheus가 없으면 빈 화면만 나온다.

실무에서 Kiali를 쓸 때 주의할 점은 **네임스페이스에 `istio-injection=enabled` 라벨이 없으면 메쉬에 포함 안 되어 토폴로지에 안 나타난다**는 것이다. "왜 우리 서비스가 Kiali에 안 보이지?" 디버깅 1순위다.

### 7.2 Jaeger 분산 트레이싱

마이크로서비스에서 한 요청이 여러 서비스를 거칠 때, 각 구간에 얼마나 걸렸는지 보여준다. Istio가 자동으로 트레이스 헤더(B3, W3C Trace Context)를 생성하긴 하지만, **애플리케이션이 헤더를 다음 호출에 전달해야 한다**. 이게 누락되면 트레이스가 끊긴다.

전달해야 할 헤더는 이 정도다.

```
x-request-id
x-b3-traceid
x-b3-spanid
x-b3-parentspanid
x-b3-sampled
x-b3-flags
x-ot-span-context
traceparent  (W3C)
tracestate   (W3C)
```

Spring Cloud Sleuth나 OpenTelemetry 에이전트를 붙이면 자동으로 전달된다. 자체 HTTP 클라이언트로 호출하는 코드라면 수동으로 헤더를 복사해야 한다.

트레이스 샘플링은 기본이 100%가 아니다. `meshConfig.defaultConfig.tracing.sampling`으로 조절하는데, 프로덕션에서는 1~10% 정도가 현실적이다. 100%로 두면 Jaeger 스토리지 비용이 폭발한다.

---

## 8. 사이드카 주입 이슈

사이드카 자동 주입은 네임스페이스에 라벨을 붙이는 방식이다.

```bash
kubectl label namespace shop istio-injection=enabled
```

이후 네임스페이스에서 생성되는 파드는 `MutatingAdmissionWebhook`을 거쳐 자동으로 `istio-proxy` 컨테이너가 추가된다. 기존 파드는 영향받지 않으므로, 라벨을 붙인 뒤 재배포해야 한다.

### 8.1 주입이 안 되는 경우

여러 함정이 있다.

- **`hostNetwork: true` 파드**: 네트워크 네임스페이스가 호스트라 iptables 룰이 의미 없다. 주입되어도 동작 안 함
- **`istio-system` 네임스페이스**: 시스템 자체는 주입 대상이 아님
- **Job/CronJob**: 사이드카가 무한 실행 상태라 Job 완료가 감지 안 됨. `holdApplicationUntilProxyStarts`와 `EXIT_ON_ZERO_ACTIVE_CONNECTIONS` 설정 필요
- **Pod 템플릿에 `sidecar.istio.io/inject: "false"` 애노테이션**: 명시적으로 제외됨

### 8.2 Job에서의 사이드카 문제

CronJob을 Istio 메쉬 안에서 돌리면 가장 자주 만나는 문제다. 메인 컨테이너가 할 일을 끝내도 `istio-proxy`는 계속 돌고 있어서 Job이 Completed 상태가 되지 않는다.

해결책은 Istio 1.12+부터 지원하는 `EXIT_ON_ZERO_ACTIVE_CONNECTIONS`다.

```yaml
spec:
  template:
    metadata:
      annotations:
        proxy.istio.io/config: |
          terminationDrainDuration: 0s
    spec:
      containers:
        - name: worker
          env:
            - name: EXIT_ON_ZERO_ACTIVE_CONNECTIONS
              value: "true"
```

또는 애플리케이션이 끝날 때 `curl -X POST localhost:15020/quitquitquit`을 호출해서 사이드카를 명시적으로 종료시키는 방법도 있다.

### 8.3 시작 순서 문제

사이드카보다 애플리케이션이 먼저 뜨면, 애플리케이션의 초기 외부 호출이 실패한다. `holdApplicationUntilProxyStarts: true`를 글로벌로 설정하거나 파드 애노테이션으로 지정해서 Envoy가 준비될 때까지 앱 컨테이너 시작을 지연시킨다.

```yaml
annotations:
  proxy.istio.io/config: |
    holdApplicationUntilProxyStarts: true
```

---

## 9. 성능 오버헤드와 리소스 튜닝

Istio를 얹으면 공짜가 아니다. 실제 운영에서 측정되는 오버헤드는 이 정도다.

- **레이턴시**: 파드 한 쌍당 왕복 2~5ms 추가 (단순 HTTP 기준)
- **CPU**: Envoy가 요청 1000 RPS 처리 시 0.1~0.2 vCPU 정도 사용
- **메모리**: Envoy 기본 40~80MB, 엔드포인트가 많은 클러스터에서는 수백 MB까지 증가

### 9.1 Envoy 리소스 제한

사이드카의 기본 리소스 요청이 꽤 낮게 잡혀 있어서, 트래픽이 많은 서비스에서는 Envoy가 throttle 되거나 OOM으로 죽는다. 서비스별로 조정할 수 있다.

```yaml
annotations:
  sidecar.istio.io/proxyCPU: "200m"
  sidecar.istio.io/proxyMemory: "256Mi"
  sidecar.istio.io/proxyCPULimit: "1000m"
  sidecar.istio.io/proxyMemoryLimit: "512Mi"
```

### 9.2 엔드포인트 폭발 문제

기본 설정으로는 각 Envoy가 **클러스터 전체의 모든 서비스 정보**를 받는다. 서비스가 수백 개가 넘어가면 istiod가 뿜어내는 xDS 설정이 거대해지고, 각 Envoy의 메모리가 급격히 늘어난다.

`Sidecar` 리소스로 각 네임스페이스가 알아야 할 범위를 제한할 수 있다.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
metadata:
  name: default
  namespace: shop
spec:
  egress:
    - hosts:
        - "./*"              # 같은 네임스페이스
        - "istio-system/*"   # 컨트롤 플레인
        - "common/*"         # 공용 서비스 네임스페이스
```

이걸 적용하면 `shop` 네임스페이스의 Envoy는 저 세 네임스페이스의 엔드포인트만 알게 되어 메모리 사용량이 크게 줄어든다. 큰 클러스터에서는 필수 설정에 가깝다.

### 9.3 프로토콜 감지 비용

Istio는 새 커넥션의 첫 몇 바이트를 보고 HTTP인지 TCP인지 감지하는데, 이 과정에서 커넥션 초기 지연이 생긴다. Service의 포트 이름에 프로토콜을 명시하면 감지 단계를 건너뛴다.

```yaml
# 권장
ports:
  - name: http-api        # http-, grpc-, tcp- 등 접두사
    port: 8080
# 비권장
ports:
  - name: api             # Istio가 감지해야 함
    port: 8080
```

### 9.4 Telemetry 설정 줄이기

기본 텔레메트리가 꽤 무겁다. 불필요한 메트릭 디멘션을 제거하거나 샘플링을 낮춰서 비용을 줄일 수 있다.

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: reduce-metrics
  namespace: istio-system
spec:
  metrics:
    - providers:
        - name: prometheus
      overrides:
        - match:
            metric: REQUEST_COUNT
          tagOverrides:
            request_protocol:
              operation: REMOVE   # 불필요한 태그 제거
```

---

## 10. 도입 전 고려사항

Istio는 강력한 만큼 복잡하다. 실무에서 도입 전 체크해 볼 점들이다.

- 서비스 수가 적으면 오버엔지니어링이다. 10개 미만이면 Kubernetes NetworkPolicy + 애플리케이션 레벨 재시도로 충분한 경우가 많다
- mTLS, 카나리 배포, 분산 트레이싱 중 최소 두 개 이상 실제 필요한가
- 운영 인력이 Envoy 설정을 디버깅할 수 있는가. `istioctl proxy-config` 계열 명령을 쓸 줄 알아야 한다
- 기존 서비스들이 HTTP/2, gRPC, 헤더 전달 등 Istio가 기대하는 동작과 호환되는가
- 인프라 비용 증가(노드 리소스 + 관측 스택)를 감당할 수 있는가

결국 Service Mesh는 **공통 기능의 중앙화**이고, 중앙화된 만큼 **중앙의 복잡도**를 관리할 여력이 있어야 쓸 수 있다. 처음 도입할 때는 PERMISSIVE mTLS + 관측성만 먼저 켜고, 라우팅/카나리/서킷브레이커 같은 고급 기능은 팀이 익숙해진 뒤에 하나씩 얹는 방식이 안전하다.
