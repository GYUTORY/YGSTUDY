---
title: 장애 주입 테스트 (Chaos Engineering)
tags: [backend, resilience, chaos-engineering, chaos-monkey, toxiproxy, litmus, kubernetes, fault-injection]
updated: 2026-03-30
---

# 장애 주입 테스트 (Chaos Engineering)

## 개요

Circuit Breaker를 설정하고, Retry를 붙이고, Timeout을 잡았다. 그런데 이게 실제 장애 상황에서 제대로 동작하는지 어떻게 아는가? 장애 대응 패턴을 코드로 작성하는 것과, 그게 프로덕션에서 실제로 동작하는 것은 다른 문제다.

Chaos Engineering은 의도적으로 장애를 주입해서 시스템이 장애 상황에서 어떻게 반응하는지 검증하는 방법이다. 단위 테스트로는 확인할 수 없는 것들 — 타임아웃 설정이 실제로 맞는지, Circuit Breaker가 정말 열리는지, Fallback이 제대로 작동하는지 — 을 실제 환경에서 확인한다.

### 장애 주입 테스트가 필요한 상황

개발 환경에서는 잘 되는데 프로덕션에서 장애가 나면 다르게 동작하는 경우가 많다.

**흔한 사례:**

- Resilience4j Circuit Breaker 설정을 했는데, 실제 장애에서 Open 상태로 전환이 안 됐다. 원인은 예외 타입이 설정한 것과 달랐기 때문.
- Retry를 3회로 설정했는데, 원격 서비스 타임아웃이 30초라 Retry 3회면 90초를 기다렸다. 그 사이 스레드 풀이 다 찼다.
- Fallback을 구현했는데, Fallback 자체가 다른 외부 서비스를 호출하고 있었다. 그 서비스도 같이 죽어서 Fallback도 실패했다.

이런 문제는 실제로 장애를 만들어봐야 알 수 있다.


## Spring Boot Chaos Monkey

Spring Boot 애플리케이션에 장애를 주입하는 라이브러리다. 애플리케이션 레벨에서 지연, 예외, 메모리 부족 같은 장애를 만든다.

### 설정

```xml
<!-- pom.xml -->
<dependency>
    <groupId>de.codecentric</groupId>
    <artifactId>chaos-monkey-spring-boot</artifactId>
    <version>3.1.0</version>
</dependency>
```

```yaml
# application-chaos.yml
# chaos-monkey 프로파일에서만 활성화한다
spring:
  profiles: chaos

chaos:
  monkey:
    enabled: true
    watcher:
      controller: true
      restController: true
      service: true
      repository: true
    assaults:
      level: 5                    # 1~10, 숫자가 낮을수록 공격 빈도가 높다
      latencyActive: true
      latencyRangeStart: 1000     # ms
      latencyRangeEnd: 5000       # ms
      exceptionsActive: false
      killApplicationActive: false
```

`level`이 헷갈리는데, level 5면 약 20%의 요청에 장애가 주입된다. level 1이면 100%다. 직관과 반대라서 처음에 실수하기 쉽다.

### 런타임에서 장애 조작

Spring Boot Actuator 엔드포인트로 런타임에 장애를 켜고 끌 수 있다.

```bash
# 현재 상태 확인
curl http://localhost:8080/actuator/chaosmonkey/status

# 장애 활성화
curl -X POST http://localhost:8080/actuator/chaosmonkey/enable

# 지연 장애 설정 변경
curl -X POST http://localhost:8080/actuator/chaosmonkey/assaults \
  -H 'Content-Type: application/json' \
  -d '{
    "latencyActive": true,
    "latencyRangeStart": 3000,
    "latencyRangeEnd": 10000,
    "exceptionsActive": false,
    "level": 3
  }'

# 특정 서비스에만 장애 주입
curl -X POST http://localhost:8080/actuator/chaosmonkey/watchers \
  -H 'Content-Type: application/json' \
  -d '{
    "controller": false,
    "restController": false,
    "service": true,
    "repository": false
  }'
```

### 테스트 시나리오 예시

```java
@SpringBootTest
@ActiveProfiles("chaos")
class PaymentServiceChaosTest {

    @Autowired
    private OrderService orderService;

    @Test
    void 결제_서비스_지연시_타임아웃이_동작하는지_확인() {
        // Chaos Monkey가 PaymentService에 3~5초 지연을 주입한 상태
        // OrderService의 타임아웃이 2초로 설정되어 있다면
        // 타임아웃 예외가 발생해야 한다

        assertThatThrownBy(() -> orderService.createOrder(request))
            .isInstanceOf(TimeoutException.class);

        // Circuit Breaker 상태 확인
        CircuitBreaker cb = circuitBreakerRegistry.circuitBreaker("payment");
        // 연속 실패 후 OPEN 상태가 되어야 한다
        assertThat(cb.getState()).isEqualTo(CircuitBreaker.State.OPEN);
    }
}
```

Chaos Monkey의 한계는 애플리케이션 레벨에서만 동작한다는 점이다. 네트워크 장애, DNS 문제, 디스크 I/O 장애 같은 인프라 수준의 장애는 만들 수 없다. 그때는 Toxiproxy가 필요하다.


## Toxiproxy — 네트워크 장애 시뮬레이션

Shopify에서 만든 네트워크 프록시 도구다. 애플리케이션과 외부 시스템 사이에 프록시를 두고, 그 프록시에서 네트워크 장애를 만든다.

### 동작 방식

```
애플리케이션 → Toxiproxy (여기서 장애 주입) → 실제 서비스
                 ↓
           지연, 패킷 손실, 연결 끊김 등
```

### 설치와 기본 사용

```bash
# macOS
brew install toxiproxy

# 서버 시작
toxiproxy-server &

# 프록시 생성: 애플리케이션이 localhost:26379로 접속하면
# 실제 Redis(localhost:6379)로 전달
toxiproxy-cli create redis -l localhost:26379 -u localhost:6379

# 프록시 생성: DB 연결
toxiproxy-cli create mysql -l localhost:23306 -u localhost:3306
```

### 장애 주입 (Toxic 추가)

```bash
# 1. 지연 추가: 모든 요청에 2초 지연
toxiproxy-cli toxic add redis -t latency -a latency=2000

# 2. 대역폭 제한: 초당 1KB로 제한
toxiproxy-cli toxic add redis -t bandwidth -a rate=1

# 3. 연결 끊김: 5초 후 연결 종료
toxiproxy-cli toxic add redis -t timeout -a timeout=5000

# 4. 패킷 손실: 슬라이스 중 일부 데이터 손상
toxiproxy-cli toxic add redis -t slicer -a average_size=1 -a size_variation=1

# toxic 제거
toxiproxy-cli toxic remove redis -n latency_downstream
```

### Java 테스트 코드에서 사용

```java
// build.gradle
// testImplementation 'eu.rekawek.toxiproxy:toxiproxy-java:2.1.7'

@Testcontainers
class RedisResilienceTest {

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7")
        .withExposedPorts(6379);

    @Container
    static ToxiproxyContainer toxiproxy = new ToxiproxyContainer("ghcr.io/shopify/toxiproxy:2.7.0")
        .dependsOn(redis);

    static ToxiproxyContainer.ContainerProxy redisProxy;

    @BeforeAll
    static void setUp() {
        redisProxy = toxiproxy.getProxy(redis, 6379);
    }

    @Test
    void Redis_연결이_끊기면_캐시_미스로_처리되는지_확인() throws Exception {
        RedisTemplate<String, String> template = createRedisTemplate(
            redisProxy.getContainerIpAddress(),
            redisProxy.getProxyPort()
        );

        // 정상 상태에서 캐시 저장
        template.opsForValue().set("key", "value");

        // 네트워크 장애 주입: 연결 끊김
        redisProxy.toxics()
            .timeout("redis-timeout", ToxicDirection.DOWNSTREAM, 0);

        // Redis 장애 상태에서 서비스 호출
        // 캐시 미스로 처리되고, DB에서 직접 조회해야 한다
        String result = cacheService.get("key");
        assertThat(result).isEqualTo("value-from-db");

        // 장애 제거
        redisProxy.toxics().get("redis-timeout").remove();
    }

    @Test
    void Redis_지연_발생시_타임아웃_후_DB_폴백_확인() throws Exception {
        // 3초 지연 주입
        redisProxy.toxics()
            .latency("redis-latency", ToxicDirection.DOWNSTREAM, 3000);

        // Redis 타임아웃이 1초로 설정되어 있으면
        // 1초 후 타임아웃 → DB 폴백
        long start = System.currentTimeMillis();
        String result = cacheService.get("key");
        long elapsed = System.currentTimeMillis() - start;

        // 3초를 기다리지 않고 1초 근처에서 DB 폴백이 되어야 한다
        assertThat(elapsed).isLessThan(2000);
        assertThat(result).isEqualTo("value-from-db");

        redisProxy.toxics().get("redis-latency").remove();
    }
}
```

Toxiproxy의 장점은 애플리케이션 코드를 수정하지 않아도 된다는 점이다. 프록시 주소만 바꾸면 된다. Testcontainers와 조합하면 CI에서도 네트워크 장애 테스트를 자동화할 수 있다.


## Kubernetes에서 장애 주입

Kubernetes 환경이면 Pod 수준에서 장애를 만들 수 있다. Pod kill, 네트워크 파티션, 리소스 제한 같은 인프라 수준 장애를 테스트한다.

### Pod Kill 테스트

```bash
# 특정 Pod 삭제 — Deployment가 자동으로 새 Pod를 생성하는지 확인
kubectl delete pod payment-service-7d4b8c9f5-x2k9m

# 랜덤 Pod 삭제
kubectl get pods -l app=payment-service -o name | shuf -n 1 | xargs kubectl delete

# Pod 삭제 후 서비스 상태 확인
# 새 Pod가 뜨는 동안 요청이 다른 Pod로 라우팅되는지 확인
while true; do
  curl -s -o /dev/null -w "%{http_code}\n" http://payment-service:8080/health
  sleep 0.5
done
```

### 네트워크 파티션 시뮬레이션

```yaml
# NetworkPolicy로 특정 서비스 간 통신 차단
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-payment-to-db
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: payment-service
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: api-gateway    # DB로의 통신만 차단, 나머지는 허용
```

```bash
# 네트워크 정책 적용
kubectl apply -f block-payment-to-db.yaml

# payment-service가 DB 연결 실패 시 어떻게 반응하는지 관찰
kubectl logs -f deployment/payment-service

# 테스트 후 정책 제거
kubectl delete networkpolicy block-payment-to-db
```

### 리소스 제한 테스트

```yaml
# Pod의 CPU/메모리를 극단적으로 제한해서 리소스 부족 상황 시뮬레이션
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service-chaos
spec:
  template:
    spec:
      containers:
        - name: payment-service
          resources:
            limits:
              cpu: "50m"        # 극단적으로 낮은 CPU
              memory: "64Mi"    # 극단적으로 낮은 메모리
```

이 정도 수동 테스트는 간단하지만, 반복하기 어렵고 자동화가 안 된다. 체계적으로 하려면 Litmus Chaos 같은 도구가 필요하다.


## Litmus Chaos

CNCF 프로젝트로, Kubernetes 환경에서 장애 주입을 체계적으로 관리하는 도구다. ChaosEngine이라는 CRD(Custom Resource Definition)로 장애 실험을 정의하고 실행한다.

### 설치

```bash
# Litmus 설치 (Helm)
helm repo add litmuschaos https://litmuschaos.github.io/litmus-helm/
helm install litmus litmuschaos/litmus \
  --namespace litmus --create-namespace

# ChaosHub에서 실험 다운로드 (기본 실험 세트)
kubectl apply -f https://hub.litmuschaos.io/api/chaos/3.0.0?file=charts/generic/experiments.yaml -n litmus
```

### Pod Kill 실험 정의

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-kill
  namespace: default
spec:
  appinfo:
    appns: default
    applabel: app=payment-service
    appkind: deployment
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: "60"           # 60초 동안 실험
            - name: CHAOS_INTERVAL
              value: "10"           # 10초마다 Pod 삭제
            - name: FORCE
              value: "false"        # graceful 종료
        probe:
          - name: payment-health-check
            type: httpProbe
            httpProbe/inputs:
              url: http://payment-service:8080/health
              method:
                get:
                  criteria: ==
                  responseCode: "200"
            mode: Continuous
            runProperties:
              probeTimeout: 5
              interval: 2
              retry: 3
```

`probe`가 핵심이다. 장애를 주입하면서 동시에 서비스가 정상인지 확인한다. Pod를 10초마다 죽이는 동안 health check가 계속 200을 반환하는지 검증한다. probe가 실패하면 실험도 실패로 기록된다.

### 네트워크 장애 실험

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-network-chaos
  namespace: default
spec:
  appinfo:
    appns: default
    applabel: app=payment-service
    appkind: deployment
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-network-latency
      spec:
        components:
          env:
            - name: NETWORK_INTERFACE
              value: "eth0"
            - name: NETWORK_LATENCY
              value: "2000"         # 2초 지연
            - name: TOTAL_CHAOS_DURATION
              value: "120"
            - name: DESTINATION_IPS
              value: "10.0.0.50"    # DB IP만 대상
```

### 실험 결과 확인

```bash
# 실험 상태 확인
kubectl get chaosengine payment-pod-kill -o yaml

# 결과 요약
kubectl get chaosresult payment-pod-kill-pod-delete -o yaml

# 주요 확인 항목:
# spec.experimentStatus.verdict: Pass/Fail
# spec.experimentStatus.probeSuccessPercentage: "100"
```


## 실무에서 장애 주입 테스트 시 주의사항

### 프로덕션에서 하면 안 되는 것들

처음 Chaos Engineering을 도입할 때 가장 흔한 실수는 프로덕션에서 바로 시작하는 것이다.

**단계별로 접근해야 한다:**

1. **개발/테스트 환경에서 먼저** — 장애 주입 테스트의 기본 동작을 확인한다
2. **스테이징 환경에서 검증** — 프로덕션과 비슷한 환경에서 시스템 반응을 확인한다
3. **프로덕션에서 제한적으로** — 트래픽의 일부에만 적용하고, 즉시 중단할 수 있는 킬 스위치를 준비한다

### Blast Radius 제한

장애 주입의 영향 범위를 반드시 제한해야 한다.

```yaml
# 나쁜 예: 전체 서비스에 장애 주입
chaos:
  monkey:
    assaults:
      level: 1              # 모든 요청에 장애

# 좋은 예: 특정 조건에서만 장애 주입
chaos:
  monkey:
    assaults:
      level: 8              # 약 12%의 요청에만 장애
    watcher:
      service: true
      controller: false     # API 컨트롤러에는 장애 주입 안 함
```

### 킬 스위치 준비

장애 주입 중 예상치 못한 문제가 발생하면 즉시 중단해야 한다.

```bash
# Chaos Monkey 즉시 비활성화
curl -X POST http://localhost:8080/actuator/chaosmonkey/disable

# Litmus 실험 즉시 중단
kubectl delete chaosengine payment-pod-kill

# Toxiproxy toxic 전부 제거
toxiproxy-cli toxic remove redis -n latency_downstream
```

킬 스위치 없이 장애 주입을 시작하면 안 된다. 자동 롤백 조건도 미리 정해야 한다. 에러율이 5%를 넘으면 자동 중단, 응답 시간이 기준치의 3배를 넘으면 자동 중단, 이런 식이다.

### 실패 사례에서 배운 것

**사례 1: Fallback이 같은 장애 도메인에 있었다**

결제 서비스의 Fallback으로 다른 결제 서비스를 설정했는데, 두 서비스가 같은 네트워크 존에 있었다. 네트워크 장애 시 둘 다 먹통이 됐다. Fallback을 설정할 때 장애 도메인이 겹치는지 확인해야 한다.

**사례 2: Circuit Breaker 설정이 실제 장애 패턴과 맞지 않았다**

Circuit Breaker의 `failureRateThreshold`를 50%로, `slidingWindowSize`를 10으로 설정했다. 그런데 실제 장애 패턴은 간헐적으로 발생해서 10개 요청 중 4개만 실패했다(40%). Circuit Breaker가 열리지 않았고, 장애가 계속됐다. 장애 주입 테스트로 실제 장애 패턴을 파악하고 그에 맞게 설정을 조정해야 한다.

**사례 3: 타임아웃 설정이 Retry와 맞물려 전체 응답 시간이 폭발했다**

```
외부 API 타임아웃: 10초
Retry: 3회
전체 대기 시간: 최대 30초
```

서비스 간 호출이 체인으로 연결되면 더 심하다.

```
서비스 A → 서비스 B → 서비스 C
  10초        10초       10초
A의 전체 대기: 최대 30초 × 3(Retry) = 90초
```

타임아웃과 Retry를 설정할 때 전체 호출 체인의 누적 시간을 계산해야 한다. 장애 주입 테스트에서 이런 누적 지연을 실제로 확인할 수 있다.

**사례 4: 장애 주입 테스트 자체가 장애를 일으켰다**

스테이징 환경에서 Litmus로 Pod kill 실험을 했는데, 장애 주입 대상 Pod의 셀렉터를 잘못 설정해서 모니터링 시스템의 Pod까지 죽었다. 장애 상황을 모니터링할 수단이 사라져서 상황 파악이 안 됐다. 장애 주입 대상의 레이블 셀렉터를 정확하게 지정하고, 모니터링/로깅 시스템은 반드시 대상에서 제외해야 한다.


## 도구 비교

| 구분 | Chaos Monkey | Toxiproxy | Kubernetes 수동 | Litmus Chaos |
|------|-------------|-----------|-----------------|--------------|
| 장애 수준 | 애플리케이션 | 네트워크 | 인프라 | 인프라 |
| 설정 난이도 | 낮음 | 중간 | 낮음 | 높음 |
| 자동화 | Actuator API | CLI/API | 스크립트 | CRD 기반 |
| CI 통합 | 쉬움 | Testcontainers | kubectl | ChaosEngine |
| 프로덕션 사용 | 가능 | 가능 | 위험 | 가능 |
| 모니터링 연동 | Spring 메트릭 | 없음 | 없음 | probe 내장 |

개발/테스트 단계에서는 Chaos Monkey와 Toxiproxy를 CI에 통합해서 매 배포마다 장애 대응이 동작하는지 확인한다. Kubernetes 환경에서 스테이징/프로덕션 수준의 장애 테스트를 하려면 Litmus Chaos를 쓴다.

장애 주입 테스트를 처음 시작한다면 Toxiproxy + Testcontainers 조합을 추천한다. 로컬에서 바로 실행할 수 있고, CI에 넣기도 쉽고, 네트워크 장애라는 가장 흔한 장애 유형을 테스트할 수 있다.
