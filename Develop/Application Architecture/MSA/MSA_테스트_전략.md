---
title: MSA 테스트
tags: [MSA, Testing, Contract Testing, Pact, Testcontainers, E2E]
updated: 2026-04-01
---

# MSA 테스트

## 왜 MSA 테스트가 어려운가

모놀리스에서는 단위 테스트 돌리고 통합 테스트 한 번 돌리면 대부분의 문제를 잡았다. MSA에서는 그게 안 된다. 서비스 A가 정상이고, 서비스 B도 정상인데, 둘을 붙이면 터진다. 이유는 보통 이렇다:

- 서비스 A가 응답 필드명을 바꿨는데, 서비스 B는 옛날 필드명을 기대하고 있다
- 서비스 A의 API 스펙이 문서에는 업데이트됐지만, 실제 코드는 다르다
- 배포 순서 때문에 잠깐 동안 호환이 안 되는 상태가 생긴다

서비스 수가 10개를 넘어가면 전체를 한번에 띄워서 테스트하는 것 자체가 비현실적이다. 여기서 Contract Testing이 등장한다.


## Contract Testing

Contract Testing은 서비스 간 API 호출의 "약속"을 검증하는 방식이다. 실제 서비스를 띄우지 않아도, 요청/응답의 형식이 서로 맞는지 확인할 수 있다.

### Consumer-Driven Contract

핵심 아이디어는 간단하다: API를 호출하는 쪽(Consumer)이 "나는 이런 요청을 보내고, 이런 응답을 기대한다"는 계약(Contract)을 작성한다. API를 제공하는 쪽(Provider)은 그 계약을 만족시키는지 검증한다.

```
Consumer(주문 서비스) → "상품 ID 123을 조회하면 name, price 필드가 와야 한다"
                          ↓
                    Contract(Pact 파일)
                          ↓
Provider(상품 서비스) → 이 계약을 실행해서 실제 응답이 맞는지 확인
```

이 방식의 장점은 Provider가 API를 변경하기 전에, 어떤 Consumer가 영향을 받는지 미리 알 수 있다는 것이다. 필드 하나 지우려고 할 때 "이 필드를 쓰는 Consumer가 3개 있습니다"라고 알려주니까, 깨지는 걸 배포 전에 잡는다.

### Pact 사용법

Pact는 Contract Testing의 사실상 표준 도구다. Java(Spring Boot) 기준으로 설명한다.

**Consumer 쪽 테스트 작성:**

```java
@ExtendWith(PactConsumerTestExt.class)
@PactTestFor(providerName = "product-service", port = "8080")
class OrderServiceContractTest {

    @Pact(consumer = "order-service")
    public V4Pact createPact(PactDslWithProvider builder) {
        return builder
            .given("상품 123이 존재한다")
            .uponReceiving("상품 조회 요청")
                .path("/api/products/123")
                .method("GET")
            .willRespondWith()
                .status(200)
                .body(newJsonBody(body -> {
                    body.numberType("id", 123);
                    body.stringType("name", "노트북");
                    body.numberType("price", 1500000);
                }).build())
            .toPact(V4Pact.class);
    }

    @Test
    @PactTestFor(pactMethod = "createPact")
    void 상품_조회_시_id_name_price가_포함된다(MockServer mockServer) {
        // mockServer.getUrl()로 실제 HTTP 호출
        ProductResponse response = productClient.getProduct(
            mockServer.getUrl(), 123L
        );

        assertThat(response.getName()).isNotNull();
        assertThat(response.getPrice()).isGreaterThan(0);
    }
}
```

이 테스트를 실행하면 Pact 파일(JSON)이 생성된다. 이 파일이 계약서 역할을 한다.

**Provider 쪽 검증:**

```java
@Provider("product-service")
@PactBroker(url = "https://pact-broker.company.com")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ProductServiceContractVerificationTest {

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider.class)
    void verifyPact(PactVerificationContext context) {
        context.verifyInteraction();
    }

    @State("상품 123이 존재한다")
    void setupProduct() {
        productRepository.save(new Product(123L, "노트북", 1500000));
    }
}
```

Provider는 Pact Broker에서 자기와 관련된 계약을 가져와서, 실제 API가 그 계약을 만족하는지 확인한다. `@State`로 테스트 데이터를 세팅하는 게 핵심이다.

### Pact Broker

팀이 2~3개일 때는 Pact 파일을 Git에 넣어도 된다. 그 이상이면 Pact Broker를 쓴다. Pact Broker는 계약을 중앙에서 관리하고, 어떤 버전끼리 호환되는지 추적한다.

```bash
# can-i-deploy로 배포 전 호환성 확인
pact-broker can-i-deploy \
  --pacticipant product-service \
  --version 2.1.0 \
  --to-environment production
```

CI/CD에 이 명령을 넣으면, 호환 안 되는 버전이 프로덕션에 나가는 걸 막을 수 있다. 실제로 이게 없으면 금요일 저녁에 한 서비스 배포 후 다른 서비스가 터지는 일이 생긴다.

### Contract Testing에서 자주 하는 실수

**1. 응답 값을 정확히 매칭하려고 한다**

```java
// 잘못된 예 - 정확한 값을 비교
body.stringValue("name", "노트북");

// 올바른 예 - 타입만 확인
body.stringType("name", "노트북");
```

`stringValue`는 "노트북"이라는 정확한 값을 기대한다. 테스트 데이터가 바뀌면 깨진다. `stringType`은 문자열이기만 하면 된다. Contract Testing의 목적은 "필드가 있고 타입이 맞는가"를 확인하는 거지, 비즈니스 로직을 검증하는 게 아니다.

**2. Provider 상태 관리를 대충 한다**

`@State` 메서드에서 테스트 데이터를 제대로 세팅하지 않으면, Provider 검증이 실패한다. 특히 여러 Consumer가 같은 Provider를 테스트할 때, State 이름이 충돌하거나 데이터가 겹치는 경우가 있다. State 이름을 구체적으로 짓는 게 중요하다.


## 서비스 간 통합 테스트와 Test Double

서비스 A가 서비스 B를 호출하는 코드를 테스트할 때, 실제 서비스 B를 띄울 수 없는 경우가 많다. 이때 Test Double을 쓴다.

### WireMock으로 외부 서비스 모킹

WireMock은 HTTP 서비스를 모킹하는 도구다. 실제 서비스 대신 정해진 응답을 돌려주는 가짜 서버를 띄운다.

```java
@SpringBootTest
@AutoConfigureWireMock(port = 0)
class PaymentServiceIntegrationTest {

    @Test
    void 결제_처리_시_외부_PG사_호출() {
        // PG사 API 모킹
        stubFor(post(urlEqualTo("/api/payments"))
            .withRequestBody(matchingJsonPath("$.amount", equalTo("50000")))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBody("""
                    {
                        "transactionId": "tx-001",
                        "status": "APPROVED"
                    }
                """)
            )
        );

        PaymentResult result = paymentService.processPayment(
            new PaymentRequest("order-1", 50000)
        );

        assertThat(result.getStatus()).isEqualTo("APPROVED");

        // 요청이 실제로 갔는지 검증
        verify(postRequestedFor(urlEqualTo("/api/payments"))
            .withRequestBody(matchingJsonPath("$.amount"))
        );
    }
}
```

WireMock을 쓸 때 주의할 점이 있다. stub 응답을 너무 단순하게 만들면 실제 서비스와 다른 동작을 테스트하게 된다. 예를 들어 실제 PG사는 타임아웃이 5초인데, WireMock은 즉시 응답한다. 타임아웃 시나리오를 빼먹으면 장애 시 동작을 검증 못 한다.

```java
// 타임아웃 시나리오 테스트
stubFor(post(urlEqualTo("/api/payments"))
    .willReturn(aResponse()
        .withStatus(200)
        .withFixedDelay(6000)  // 6초 지연 → 타임아웃 발생
    )
);

assertThatThrownBy(() -> paymentService.processPayment(request))
    .isInstanceOf(PaymentTimeoutException.class);
```

### 메시지 기반 통신의 Test Double

Kafka나 RabbitMQ로 통신하는 경우, 메시지 브로커를 직접 띄우기 어렵다. Spring Boot에서는 `@EmbeddedKafka`나 인메모리 채널로 테스트한다.

```java
@SpringBootTest
@EmbeddedKafka(
    partitions = 1,
    topics = {"order-events"},
    brokerProperties = {"listeners=PLAINTEXT://localhost:9092"}
)
class OrderEventConsumerTest {

    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    @Autowired
    private OrderEventConsumer consumer;

    @Test
    void 주문_생성_이벤트를_수신하면_재고를_차감한다() throws Exception {
        String event = """
            {
                "orderId": "order-1",
                "productId": 123,
                "quantity": 2,
                "type": "ORDER_CREATED"
            }
        """;

        kafkaTemplate.send("order-events", event).get();

        // Consumer가 처리할 시간을 준다
        await().atMost(Duration.ofSeconds(5)).untilAsserted(() -> {
            Stock stock = stockRepository.findByProductId(123L);
            assertThat(stock.getQuantity()).isEqualTo(8); // 10 - 2
        });
    }
}
```

`@EmbeddedKafka`는 테스트용 Kafka 브로커를 프로세스 내에 띄운다. 테스트가 끝나면 자동으로 정리된다. 다만 실제 Kafka와 미묘하게 다른 동작을 하는 경우가 있어서, 중요한 시나리오는 Testcontainers로 실제 Kafka를 띄우는 게 낫다.


## Testcontainers 활용

Testcontainers는 Docker 컨테이너를 테스트 코드에서 직접 관리하는 라이브러리다. 실제 DB, 메시지 브로커, 캐시를 테스트에서 띄울 수 있다.

### 기본 사용법

```java
@SpringBootTest
@Testcontainers
class ProductRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private ProductRepository productRepository;

    @Test
    void 상품_저장_및_조회() {
        Product product = new Product("노트북", 1500000);
        productRepository.save(product);

        Product found = productRepository.findByName("노트북");
        assertThat(found.getPrice()).isEqualTo(1500000);
    }
}
```

H2 같은 인메모리 DB로 테스트하면 PostgreSQL 고유 기능(JSONB, 배열 타입 등)을 검증 못 한다. Testcontainers는 실제 PostgreSQL을 띄우니까 이런 문제가 없다.

### 여러 서비스를 한번에 띄우기

서비스 간 통합 테스트에서 DB와 메시지 브로커를 동시에 필요로 하는 경우가 있다.

```java
@SpringBootTest
@Testcontainers
class OrderIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withDatabaseName("orderdb");

    @Container
    static KafkaContainer kafka = new KafkaContainer(
        DockerImageName.parse("confluentinc/cp-kafka:7.5.0")
    );

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7")
        .withExposedPorts(6379);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.kafka.bootstrap-servers", kafka::getBootstrapServers);
        registry.add("spring.data.redis.host", redis::getHost);
        registry.add("spring.data.redis.port", () -> redis.getMappedPort(6379));
    }

    @Test
    void 주문_생성_시_DB_저장_후_이벤트_발행_후_캐시_갱신() {
        // 전체 흐름을 실제 인프라로 검증
        OrderCreateRequest request = new OrderCreateRequest(
            "user-1", 123L, 2
        );

        orderService.createOrder(request);

        // DB 저장 확인
        Order order = orderRepository.findByUserId("user-1");
        assertThat(order).isNotNull();

        // Kafka 이벤트 발행 확인
        ConsumerRecord<String, String> record = KafkaTestUtils.getSingleRecord(
            consumer, "order-events"
        );
        assertThat(record.value()).contains("ORDER_CREATED");

        // Redis 캐시 확인
        String cached = redisTemplate.opsForValue().get("order:" + order.getId());
        assertThat(cached).isNotNull();
    }
}
```

### Testcontainers 사용 시 주의사항

**컨테이너 시작 시간 문제:** PostgreSQL은 보통 2~3초, Kafka는 10초 이상 걸린다. 테스트가 수십 개면 매번 컨테이너를 띄우고 내리면 CI가 느려진다.

해결 방법은 `static` 필드로 선언해서 테스트 클래스 단위로 재사용하거나, `singleton container` 패턴을 쓰는 것이다.

```java
// Singleton Container 패턴
public abstract class IntegrationTestBase {

    static final PostgreSQLContainer<?> POSTGRES;
    static final KafkaContainer KAFKA;

    static {
        POSTGRES = new PostgreSQLContainer<>("postgres:15")
            .withDatabaseName("testdb");
        POSTGRES.start();

        KAFKA = new KafkaContainer(
            DockerImageName.parse("confluentinc/cp-kafka:7.5.0")
        );
        KAFKA.start();
    }

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.kafka.bootstrap-servers", KAFKA::getBootstrapServers);
    }
}
```

이렇게 하면 전체 테스트 스위트에서 컨테이너를 한 번만 띄운다. JVM이 종료될 때 Ryuk 컨테이너가 자동으로 정리한다.

**Docker 소켓 접근 권한:** CI/CD 환경에서 Docker-in-Docker(DinD)나 Docker 소켓 마운트가 안 되면 Testcontainers가 동작하지 않는다. GitHub Actions에서는 기본적으로 Docker가 사용 가능하지만, 사내 CI에서는 설정이 필요한 경우가 많다.


## E2E 테스트 구성

MSA에서 E2E 테스트는 "실제 사용자 시나리오를 전체 서비스를 대상으로 검증"하는 테스트다. 필요하지만, 범위를 잘 잡아야 한다.

### Docker Compose로 테스트 환경 구성

```yaml
# docker-compose.test.yml
services:
  api-gateway:
    image: api-gateway:test
    ports:
      - "8080:8080"
    depends_on:
      - order-service
      - product-service

  order-service:
    image: order-service:test
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://order-db:5432/orders
      SPRING_KAFKA_BOOTSTRAP_SERVERS: kafka:9092
    depends_on:
      - order-db
      - kafka

  product-service:
    image: product-service:test
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://product-db:5432/products
    depends_on:
      - product-db

  order-db:
    image: postgres:15
    environment:
      POSTGRES_DB: orders

  product-db:
    image: postgres:15
    environment:
      POSTGRES_DB: products

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
```

```bash
# E2E 테스트 실행
docker compose -f docker-compose.test.yml up -d
./gradlew e2eTest
docker compose -f docker-compose.test.yml down
```

### E2E 테스트 코드 예시

```java
@SpringBootTest
@TestPropertySource(properties = {
    "gateway.url=http://localhost:8080"
})
class OrderE2ETest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Value("${gateway.url}")
    private String gatewayUrl;

    @Test
    void 주문_생성부터_조회까지_전체_흐름() {
        // 1. 상품 등록
        ProductRequest product = new ProductRequest("노트북", 1500000, 10);
        ResponseEntity<ProductResponse> productResponse = restTemplate.postForEntity(
            gatewayUrl + "/api/products", product, ProductResponse.class
        );
        assertThat(productResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Long productId = productResponse.getBody().getId();

        // 2. 주문 생성
        OrderRequest order = new OrderRequest("user-1", productId, 2);
        ResponseEntity<OrderResponse> orderResponse = restTemplate.postForEntity(
            gatewayUrl + "/api/orders", order, OrderResponse.class
        );
        assertThat(orderResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        String orderId = orderResponse.getBody().getOrderId();

        // 3. 비동기 처리 대기 (이벤트 기반이라 바로 반영 안 될 수 있음)
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> {
            ResponseEntity<OrderResponse> result = restTemplate.getForEntity(
                gatewayUrl + "/api/orders/" + orderId, OrderResponse.class
            );
            assertThat(result.getBody().getStatus()).isEqualTo("CONFIRMED");
        });

        // 4. 재고 차감 확인
        ResponseEntity<ProductResponse> updatedProduct = restTemplate.getForEntity(
            gatewayUrl + "/api/products/" + productId, ProductResponse.class
        );
        assertThat(updatedProduct.getBody().getStock()).isEqualTo(8);
    }
}
```

### E2E 테스트에서 자주 겪는 문제

**비동기 처리 때문에 테스트가 불안정하다.** 이벤트가 전파되는 시간이 매번 다르기 때문에 `Thread.sleep(3000)` 같은 코드가 들어간다. 이러면 가끔 실패하거나, 느리다. `Awaitility` 라이브러리로 폴링 방식으로 바꾸는 게 맞다.

**테스트 데이터 정리가 어렵다.** 여러 서비스의 DB에 데이터가 흩어져 있어서, 테스트 간 격리가 안 된다. 테스트마다 고유한 식별자(UUID)를 쓰거나, 테스트 전에 DB를 초기화하는 방법을 쓴다.

**E2E 테스트를 너무 많이 만들지 않는다.** 느리고, 깨지기 쉽고, 원인 파악이 어렵다. 핵심 사용자 시나리오 5~10개 정도만 유지하는 게 현실적이다. 나머지는 Contract Testing과 서비스별 통합 테스트로 커버한다.


## 테스트 환경 격리

MSA 테스트에서 가장 골치 아픈 문제 중 하나가 환경 격리다. 여러 개발자가 같은 테스트 환경을 쓰면 서로의 테스트가 영향을 준다.

### 문제 상황

```
개발자 A: 주문 서비스 테스트 중 → 상품 123의 재고를 0으로 변경
개발자 B: 동시에 주문 테스트 → 상품 123의 재고가 0이라 주문 실패
```

이런 일은 공용 테스트 DB를 쓸 때 매일 일어난다.

### 해결 방법 1: 네임스페이스 격리

Kubernetes 환경이면 개발자별 네임스페이스를 만들어 서비스를 배포한다.

```bash
# 개발자별 네임스페이스 생성
kubectl create namespace test-dev-a
kubectl create namespace test-dev-b

# Helm으로 서비스 배포
helm install order-service ./charts/order-service \
  --namespace test-dev-a \
  --set database.name=orders_dev_a
```

비용이 많이 든다. 서비스가 20개면 개발자마다 20개씩 띄워야 한다.

### 해결 방법 2: 테스트 데이터 격리

공용 환경을 쓰되, 테스트 데이터를 격리한다. 테스트마다 고유한 tenant ID나 prefix를 붙인다.

```java
public abstract class IsolatedIntegrationTest {

    protected String testId;

    @BeforeEach
    void setupTestIsolation() {
        testId = UUID.randomUUID().toString().substring(0, 8);
    }

    protected String uniqueName(String base) {
        return base + "-" + testId;
    }

    @AfterEach
    void cleanupTestData() {
        // testId로 시작하는 데이터만 정리
        testDataCleaner.cleanByPrefix(testId);
    }
}

class OrderServiceTest extends IsolatedIntegrationTest {

    @Test
    void 주문_생성() {
        String productName = uniqueName("노트북");
        ProductRequest product = new ProductRequest(productName, 1500000, 10);
        // 이 테스트의 데이터는 다른 테스트와 절대 겹치지 않는다
    }
}
```

### 해결 방법 3: 테스트 전용 DB 인스턴스

CI에서는 파이프라인마다 DB를 새로 만들고, 테스트가 끝나면 삭제한다.

```groovy
// Jenkinsfile
pipeline {
    stages {
        stage('Setup Test DB') {
            steps {
                sh """
                    docker run -d --name test-db-${BUILD_NUMBER} \
                        -e POSTGRES_DB=testdb \
                        postgres:15
                """
            }
        }
        stage('Test') {
            steps {
                sh "./gradlew test -DdbHost=test-db-${BUILD_NUMBER}"
            }
        }
        stage('Cleanup') {
            steps {
                sh "docker rm -f test-db-${BUILD_NUMBER}"
            }
        }
    }
}
```

이 방법이 가장 깔끔하지만, CI 리소스를 많이 쓴다. Testcontainers를 쓰면 이 과정을 코드 레벨에서 자동화할 수 있어서, CI 파이프라인이 단순해진다.


## 테스트 피라미드 정리

MSA에서 테스트 비율을 어떻게 가져갈지 정리한다.

| 테스트 종류 | 비중 | 실행 시간 | 범위 |
|-------------|------|-----------|------|
| 단위 테스트 | 70% | 수 ms | 단일 클래스/메서드 |
| 서비스 통합 테스트 | 15% | 수 초 | 단일 서비스 + 실제 DB |
| Contract 테스트 | 10% | 수 초 | 서비스 간 API 계약 |
| E2E 테스트 | 5% | 수 분 | 전체 시스템 |

단위 테스트를 많이 작성하고, E2E 테스트는 최소한으로 유지한다. Contract Testing은 서비스 간 연동 문제를 단위 테스트 수준의 속도로 잡아주기 때문에, MSA에서는 반드시 도입하는 게 좋다.

E2E 테스트가 자꾸 실패하면 "E2E를 더 만들어야 하나?"가 아니라 "Contract 테스트가 부족한 건 아닌가?"를 먼저 확인한다. 대부분의 서비스 간 문제는 Contract 테스트로 잡을 수 있다.
