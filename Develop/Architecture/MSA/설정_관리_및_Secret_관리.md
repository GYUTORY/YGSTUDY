---
title: 설정 관리 및 Secret 관리 (Config Server, Consul, Vault, AWS Secrets Manager)
tags: [msa, config-server, consul, etcd, vault, aws-secrets-manager, configuration, secret-management]
updated: 2026-04-01
---

# 설정 관리 및 Secret 관리

## 왜 중앙 집중식 설정 관리가 필요한가

모놀리식에서는 `application.yml` 하나에 설정을 다 넣는다. 환경별로 `application-dev.yml`, `application-prod.yml` 나눠서 프로파일로 구분하면 된다. 서비스가 하나니까 관리할 설정 파일도 한 벌이다.

MSA에서는 서비스가 20개면 설정 파일이 최소 20벌이다. 환경이 dev, staging, prod 세 개면 60벌이 된다. DB 접속 정보를 바꿔야 하면 20개 서비스의 설정 파일을 각각 수정하고, 각각 배포해야 한다. 공통 설정 하나 바꾸는데 20번 배포하는 건 말이 안 된다.

이 문제를 해결하는 방법이 **중앙 집중식 설정 관리**다. 설정을 한 곳에 모아두고, 각 서비스가 기동할 때 거기서 설정을 가져간다.

---

## 중앙 집중식 설정 관리 패턴

### Spring Cloud Config Server

가장 많이 사용하는 방식이다. Git 저장소에 설정 파일을 저장하고, Config Server가 이를 서빙한다.

**구조:**

```
[Git Repository]     →     [Config Server]     →     [각 서비스]
  application.yml           :8888                    기동 시 설정 fetch
  order-service.yml
  payment-service.yml
```

Config Server는 별도 서비스로 띄워야 한다. Git 저장소의 특정 브랜치나 디렉토리를 바라보게 설정한다.

```yaml
# config-server의 application.yml
spring:
  cloud:
    config:
      server:
        git:
          uri: https://github.com/company/config-repo
          default-label: main
          search-paths: '{application}'
```

클라이언트(각 서비스)는 `bootstrap.yml`에 Config Server 주소를 넣는다.

```yaml
# order-service의 bootstrap.yml
spring:
  application:
    name: order-service
  cloud:
    config:
      uri: http://config-server:8888
      fail-fast: true
      retry:
        max-attempts: 5
        initial-interval: 1000
```

`fail-fast: true`는 Config Server에 연결 못 하면 서비스 기동 자체를 중단시킨다. 설정 없이 뜨는 것보다 아예 안 뜨는 게 낫다. 설정 잘못 가져온 채로 트래픽을 받으면 더 큰 문제가 생긴다.

**문제점:**

Config Server가 단일 장애 지점(SPOF)이 된다. Config Server가 죽으면 새로 기동하는 서비스가 설정을 못 가져간다. 이미 떠있는 서비스는 캐시된 설정으로 동작하지만, 스케일 아웃이 안 된다. Config Server를 이중화하거나, 설정을 로컬에도 캐시해두는 구성이 필요하다.

### Consul KV

HashiCorp Consul은 서비스 디스커버리로 많이 쓰지만, KV(Key-Value) 스토어 기능도 있다. 설정 관리를 Consul KV에서 하면 서비스 디스커버리와 설정 관리를 한 시스템으로 통합할 수 있다.

```bash
# Consul KV에 설정 저장
consul kv put config/order-service/db.host 10.0.1.100
consul kv put config/order-service/db.port 5432
consul kv put config/order-service/max-pool-size 20

# 조회
consul kv get config/order-service/db.host
```

JSON 형태로 한 번에 넣을 수도 있다.

```bash
consul kv put config/order-service/database @db-config.json
```

Spring Boot에서 Consul KV를 설정 소스로 사용하려면 `spring-cloud-consul-config` 의존성을 추가한다.

```yaml
# bootstrap.yml
spring:
  cloud:
    consul:
      host: consul-server
      port: 8500
      config:
        enabled: true
        prefix: config
        default-context: application
        format: YAML
```

Consul의 장점은 **Watch 기능**이다. 설정이 변경되면 이벤트를 받을 수 있어서, 폴링 없이 변경을 감지할 수 있다. 단점은 KV 스토어의 값 하나당 512KB 제한이 있다는 것이다. 대부분의 설정은 이 안에 들어오지만, 대용량 설정 파일에는 적합하지 않다.

### etcd

Kubernetes 환경에서는 etcd를 이미 쓰고 있으니 설정 관리도 etcd에서 하는 경우가 있다. 다만 Kubernetes의 etcd는 클러스터 상태 관리용이라, 애플리케이션 설정을 여기에 직접 넣는 건 권장하지 않는다. 별도 etcd 클러스터를 띄우거나, Kubernetes의 ConfigMap/Secret을 사용하는 게 일반적이다.

```bash
# etcd에 설정 저장
etcdctl put /config/order-service/db-host "10.0.1.100"
etcdctl put /config/order-service/max-connections "50"

# 조회
etcdctl get /config/order-service/db-host

# prefix로 특정 서비스의 전체 설정 조회
etcdctl get /config/order-service/ --prefix
```

etcd는 Watch API를 기본 지원한다. 설정 키가 변경되면 gRPC 스트림으로 알림을 받는다.

```go
// Go 클라이언트에서 Watch
watchChan := client.Watch(context.Background(), "/config/order-service/", clientv3.WithPrefix())
for watchResp := range watchChan {
    for _, event := range watchResp.Events {
        fmt.Printf("변경: %s -> %s\n", event.Kv.Key, event.Kv.Value)
        // 설정 reload 로직
    }
}
```

### 비교

| 항목 | Config Server | Consul KV | etcd |
|------|--------------|-----------|------|
| 저장소 | Git | 내장 KV | 내장 KV |
| 변경 감지 | 수동 refresh 필요 | Watch 지원 | Watch 지원 |
| 버전 관리 | Git 히스토리 | 없음 (별도 구현) | 리비전 기반 |
| 운영 복잡도 | 낮음 | 중간 | 높음 |
| K8s 친화도 | 낮음 | 중간 | 높음 |

Spring 생태계면 Config Server, 서비스 디스커버리도 Consul이면 Consul KV, Kubernetes 네이티브면 ConfigMap + etcd 조합을 쓰게 된다.

---

## Secret 관리

DB 비밀번호, API 키, 인증서 같은 민감한 정보를 일반 설정과 같이 관리하면 안 된다. Git에 평문으로 들어가거나, 환경 변수에 노출되는 건 보안 사고의 시작이다.

### 흔히 저지르는 실수

```yaml
# 이렇게 하면 안 된다
spring:
  datasource:
    password: MyS3cretP@ss!
```

이게 Git에 커밋되면 히스토리에 남는다. force push로 지워도 이미 클론한 사람의 로컬에는 남아있다. GitHub에서 secret scanning 알림이 와도 이미 늦은 경우가 많다.

환경 변수로 빼는 것도 완전하지 않다. `docker inspect`나 `/proc/<pid>/environ`으로 볼 수 있다. 컨테이너 오케스트레이션 도구의 로그에 환경 변수가 찍히는 경우도 있다.

### HashiCorp Vault

Vault는 Secret 전용 관리 도구다. 저장, 접근 제어, 감사 로그, 자동 로테이션까지 처리한다.

**동작 구조:**

```
[서비스] → 인증 → [Vault] → Secret 조회 → 응답 (TTL 설정됨)
                    ↓
              [감사 로그] 누가, 언제, 어떤 Secret을 조회했는지 기록
```

서비스가 Vault에서 Secret을 가져가려면 먼저 인증해야 한다. 인증 방식은 여러 가지다.

```bash
# Vault에 Secret 저장
vault kv put secret/order-service db-password="MyS3cretP@ss" api-key="sk-abc123"

# 조회
vault kv get secret/order-service

# 특정 필드만 조회
vault kv get -field=db-password secret/order-service
```

Spring Boot에서 Vault를 설정 소스로 사용하는 방법:

```yaml
# bootstrap.yml
spring:
  cloud:
    vault:
      host: vault-server
      port: 8200
      scheme: https
      authentication: KUBERNETES  # K8s 환경일 때
      kubernetes:
        role: order-service
        kubernetes-path: auth/kubernetes
      kv:
        enabled: true
        backend: secret
        default-context: order-service
```

Vault에서 중요한 건 **Dynamic Secrets**다. DB 비밀번호를 정적으로 저장하는 게 아니라, Vault가 필요할 때 임시 DB 계정을 생성해주는 방식이다.

```bash
# Database Secret Engine 설정
vault write database/config/mydb \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@db:5432/mydb" \
    allowed_roles="order-service-role" \
    username="vault_admin" \
    password="admin_password"

# Role 설정 (TTL 1시간, 최대 24시간)
vault write database/roles/order-service-role \
    db_name=mydb \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"
```

서비스가 DB 접속이 필요할 때 Vault에 요청하면, Vault가 임시 계정을 만들어서 반환한다. TTL이 지나면 계정이 자동 삭제된다. 비밀번호가 유출되어도 1시간이면 만료된다.

### AWS Secrets Manager

AWS 환경이면 Secrets Manager가 관리 부담이 적다. Vault처럼 직접 운영할 필요가 없다.

```java
// AWS SDK로 Secret 조회
SecretsManagerClient client = SecretsManagerClient.builder()
    .region(Region.AP_NORTHEAST_2)
    .build();

GetSecretValueRequest request = GetSecretValueRequest.builder()
    .secretId("prod/order-service/db")
    .build();

GetSecretValueResponse response = client.getSecretValue(request);
String secret = response.secretString();
// {"username":"admin","password":"MyS3cretP@ss","host":"db.cluster.ap-northeast-2.rds.amazonaws.com"}
```

**자동 로테이션 설정:**

Secrets Manager는 Lambda 함수를 이용한 자동 로테이션을 지원한다. RDS의 경우 AWS에서 제공하는 로테이션 Lambda 템플릿이 있다.

```python
# rotation Lambda (simplified)
def lambda_handler(event, context):
    step = event['Step']
    secret_id = event['SecretId']
    
    if step == "createSecret":
        # 새 비밀번호 생성
        new_password = generate_password()
        secrets_client.put_secret_value(
            SecretId=secret_id,
            ClientRequestToken=event['ClientRequestToken'],
            SecretString=json.dumps({"password": new_password}),
            VersionStage="AWSPENDING"
        )
    elif step == "setSecret":
        # DB에 새 비밀번호 적용
        pending = get_secret(secret_id, "AWSPENDING")
        update_db_password(pending["password"])
    elif step == "testSecret":
        # 새 비밀번호로 접속 테스트
        test_connection(pending["password"])
    elif step == "finishSecret":
        # AWSCURRENT로 전환
        secrets_client.update_secret_version_stage(
            SecretId=secret_id,
            VersionStage="AWSCURRENT",
            MoveToVersionId=event['ClientRequestToken'],
            RemoveFromVersionId=current_version
        )
```

Vault과 Secrets Manager의 차이를 정리하면:

| 항목 | Vault | AWS Secrets Manager |
|------|-------|-------------------|
| 운영 방식 | 직접 설치/운영 | 관리형 서비스 |
| 클라우드 종속 | 없음 | AWS 종속 |
| Dynamic Secrets | 지원 | Lambda로 구현 |
| 비용 | 인프라 비용 | Secret당 $0.40/월 + API 호출 비용 |
| 감사 로그 | 내장 | CloudTrail 연동 |

멀티 클라우드나 온프레미스 환경이면 Vault, AWS에 올인한 환경이면 Secrets Manager가 맞다.

---

## 환경별 설정 분리

### 네이밍 컨벤션

환경별 설정을 구분하는 가장 기본적인 방법은 네이밍 규칙이다.

```
config/
├── application.yml          # 전 환경 공통
├── application-dev.yml      # 개발
├── application-staging.yml  # 스테이징
└── application-prod.yml     # 운영
```

서비스별로 나누면:

```
config/
├── order-service/
│   ├── application.yml
│   ├── application-dev.yml
│   ├── application-staging.yml
│   └── application-prod.yml
├── payment-service/
│   ├── application.yml
│   └── ...
```

공통 설정은 `application.yml`에 넣고, 환경별로 달라지는 것만 환경 프로파일에 넣는다. 환경 프로파일의 값이 공통 설정을 오버라이드한다.

### Kubernetes에서의 환경 분리

Kubernetes 환경에서는 ConfigMap과 Secret으로 설정을 관리한다.

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: order-service-config
  namespace: production
data:
  application.yml: |
    server:
      port: 8080
    spring:
      datasource:
        url: jdbc:postgresql://db-prod:5432/orders
        hikari:
          maximum-pool-size: 30
    logging:
      level:
        root: WARN
        com.company.order: INFO
```

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: order-service-secret
  namespace: production
type: Opaque
data:
  db-password: TXlTM2NyZXRQQHNz    # base64 인코딩
  api-key: c2stYWJjMTIz
```

주의할 점: Kubernetes Secret은 base64 인코딩일 뿐 암호화가 아니다. etcd에 평문으로 저장된다. 실제 암호화가 필요하면 EncryptionConfiguration을 설정하거나, Sealed Secrets, External Secrets Operator를 사용해야 한다.

```yaml
# External Secrets Operator로 Vault/Secrets Manager 연동
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: order-service-secret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: order-service-secret
  data:
    - secretKey: db-password
      remoteRef:
        key: secret/data/order-service
        property: db-password
```

### 환경 간 설정 차이를 최소화하라

dev와 prod의 설정 차이가 크면 "개발에서는 되는데 운영에서는 안 돼요"가 반복된다. 환경별로 달라야 하는 것만 분리한다.

**환경별로 달라야 하는 것:**
- DB 접속 정보 (호스트, 포트, 인증)
- 외부 서비스 URL
- 리소스 크기 (커넥션 풀, 스레드 풀)
- 로그 레벨

**환경별로 달라지면 안 되는 것:**
- 비즈니스 로직에 영향을 주는 설정
- 타임아웃 값 (dev에서 10초, prod에서 3초로 다르면 dev에서 잡히지 않는 타임아웃 버그가 prod에서 터진다)
- 캐시 TTL (다르면 dev에서 재현 안 되는 캐시 관련 버그가 생긴다)

---

## 런타임 설정 변경과 서비스 반영

설정을 바꿀 때마다 서비스를 재배포하면 다운타임이 생긴다. 트래픽이 많은 서비스라면 롤링 배포 중에도 구버전과 신버전이 다른 설정으로 동시에 동작하게 된다. 런타임에 설정을 변경하고 재기동 없이 반영하는 방법이 필요하다.

### Spring Cloud Config + Bus Refresh

Config Server에서 설정을 변경한 후, Spring Cloud Bus를 통해 전체 서비스에 refresh 이벤트를 보내는 방식이다.

```
[Git Push] → [Config Server] → [Message Broker (RabbitMQ/Kafka)]
                                        ↓
                               [서비스 A] [서비스 B] [서비스 C]
                               각각 @RefreshScope 빈 reload
```

```java
@RestController
@RefreshScope
public class OrderController {
    
    @Value("${order.max-items}")
    private int maxItems;  // 설정 변경 시 자동 갱신
    
    @GetMapping("/orders")
    public ResponseEntity<?> createOrder(@RequestBody OrderRequest request) {
        if (request.getItems().size() > maxItems) {
            return ResponseEntity.badRequest().body("최대 주문 수량 초과");
        }
        // ...
    }
}
```

`@RefreshScope`가 붙은 빈만 설정 변경 시 재생성된다. 주의할 점은 refresh 이벤트가 발생하면 해당 빈이 **소멸 후 재생성**된다는 것이다. 빈 내부에 상태를 들고 있으면 날아간다.

refresh를 트리거하는 방법:

```bash
# 특정 서비스에 직접 refresh (개별)
curl -X POST http://order-service:8080/actuator/refresh

# Spring Cloud Bus를 통해 전체 서비스에 broadcast
curl -X POST http://config-server:8888/actuator/busrefresh
```

### Kubernetes ConfigMap 변경 감지

Kubernetes에서 ConfigMap을 변경하면, 볼륨 마운트된 경우 kubelet이 일정 시간(기본 1분) 후에 파일을 업데이트한다. 환경 변수로 주입한 경우에는 Pod를 재시작해야 반영된다.

파일 변경을 감지해서 설정을 reload하는 방식:

```java
@Component
public class ConfigFileWatcher {
    
    @Value("${config.file.path:/etc/config/application.yml}")
    private String configPath;
    
    @PostConstruct
    public void watchConfigFile() {
        WatchService watchService = FileSystems.getDefault().newWatchService();
        Path dir = Paths.get(configPath).getParent();
        dir.register(watchService, StandardWatchEventKinds.ENTRY_MODIFY);
        
        // 별도 스레드에서 감시
        new Thread(() -> {
            while (true) {
                WatchKey key = watchService.take();
                for (WatchEvent<?> event : key.pollEvents()) {
                    if (event.context().toString().equals("application.yml")) {
                        reloadConfig();
                    }
                }
                key.reset();
            }
        }).start();
    }
}
```

실무에서는 [Reloader](https://github.com/stakater/Reloader) 같은 컨트롤러를 쓴다. ConfigMap이나 Secret이 변경되면 관련 Deployment를 자동으로 롤링 재시작해준다.

```yaml
# Reloader annotation 추가
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
  annotations:
    reloader.stakater.com/auto: "true"   # 연관된 ConfigMap/Secret 변경 시 자동 재시작
```

### 설정 변경 시 주의사항

런타임 설정 변경은 배포 없이 동작을 바꾸는 것이라, 잘못하면 배포보다 더 위험하다.

1. **변경 전파에 시간 차이가 있다.** Bus refresh를 보내도 서비스마다 반영 시점이 다르다. 서비스 A는 새 설정, 서비스 B는 구 설정인 상태가 순간적으로 생긴다. 이 차이가 문제를 일으키는 설정이면 런타임 변경이 아니라 배포로 가야 한다.

2. **모든 설정이 런타임 변경에 적합한 건 아니다.** DB 커넥션 풀 크기 같은 건 런타임에 바꿔도 기존 커넥션이 바로 정리되지 않는다. 포트 번호나 서버 설정은 재시작이 필요하다.

3. **롤백할 수 있어야 한다.** 설정 변경 후 문제가 생기면 이전 값으로 즉시 되돌릴 수 있어야 한다. Config Server + Git 조합에서는 Git revert로 가능하지만, KV 스토어에서는 이전 값을 별도로 저장해두지 않으면 롤백이 어렵다.

---

## 설정 변경으로 인한 장애 사례

### 사례 1: 커넥션 풀 크기를 잘못 변경해서 DB가 죽은 경우

서비스가 20개 있고, 각 서비스의 DB 커넥션 풀이 10개였다. 총 200개 커넥션. DB의 max_connections가 300으로 설정되어 있어서 여유가 있었다.

성능 개선한다고 공통 설정에서 커넥션 풀을 50으로 올렸다. 20개 서비스 × 50 = 1,000개 커넥션. DB의 max_connections를 넘어서 커넥션을 못 맺는 서비스가 속출했다. 일부 서비스는 커넥션 획득 타임아웃으로 500 에러를 반환하기 시작했다.

**원인:** 개별 서비스 단위로만 생각하고, 전체 서비스가 공유하는 DB의 커넥션 한도를 고려하지 않았다.

**대응:** 설정 변경 전에 전체 서비스의 리소스 합산 영향도를 계산해야 한다. 커넥션 풀, 스레드 풀처럼 공유 자원에 영향을 주는 설정은 한 서비스씩 단계적으로 변경하고, 모니터링하면서 늘려야 한다.

### 사례 2: 타임아웃 설정 오타로 서비스 전체 장애

결제 서비스의 외부 PG사 호출 타임아웃을 3000ms(3초)에서 5000ms(5초)로 변경하려고 했다. Config Server의 Git 저장소에서 설정을 수정하는데, 실수로 5000000(5000초)을 입력했다.

PG사에서 응답이 안 올 때 서비스가 5000초(약 83분) 동안 대기했다. 스레드가 전부 묶이면서 결제 서비스가 먹통이 됐고, 주문 서비스까지 장애가 전파됐다.

**원인:** 설정값의 유효성 검증이 없었다. 숫자 하나 잘못 입력해도 그대로 반영됐다.

**대응:** 설정에 유효 범위를 두어야 한다. 

```java
@ConfigurationProperties(prefix = "payment.pg")
@Validated
public class PgProperties {
    
    @Min(100)
    @Max(30000)  // 최대 30초
    private int timeoutMs = 3000;
    
    @Min(1)
    @Max(5)
    private int maxRetries = 3;
}
```

`@Validated`와 Bean Validation을 쓰면 범위를 벗어나는 값이 들어올 때 서비스 기동이 실패한다. 잘못된 설정으로 동작하는 것보다 기동 실패가 낫다.

### 사례 3: Secret 로테이션 중 서비스 장애

DB 비밀번호를 정기적으로 변경하는 정책이 있었다. 비밀번호를 변경하는 순서가 문제였다.

1. DB에서 비밀번호 변경
2. Secrets Manager에서 비밀번호 업데이트
3. 서비스에 새 비밀번호 반영

1번과 2번 사이에 서비스가 DB에 새 커넥션을 맺으려고 하면, 구 비밀번호로 접근하니까 인증 실패가 난다. 2번과 3번 사이에도 마찬가지 문제가 생긴다.

**대응:** 비밀번호 로테이션은 **이중 비밀번호(dual password)** 방식으로 해야 한다.

1. DB에 새 비밀번호를 **추가** (기존 비밀번호도 유지)
2. Secrets Manager에 새 비밀번호 업데이트
3. 서비스에 새 비밀번호 반영 확인
4. DB에서 구 비밀번호 삭제

이렇게 하면 어느 시점에서든 구 비밀번호와 새 비밀번호 중 하나는 동작한다. 서비스마다 반영 시점이 달라도 문제가 없다.

### 사례 4: 환경 설정 파일을 잘못 배포

staging 환경의 설정 파일이 prod에 배포된 적이 있다. staging의 DB는 dev 데이터가 들어있는데, prod 서비스가 staging DB를 바라보면서 사용자에게 테스트 데이터가 노출됐다.

**원인:** 설정 파일 배포 프로세스에 환경 검증이 없었다. 파일 이름을 바꿔치기하면 그대로 반영됐다.

**대응:** 설정 파일에 환경 식별자를 넣고, 서비스 기동 시 현재 환경과 설정의 환경이 일치하는지 검증한다.

```java
@Component
public class EnvironmentValidator implements ApplicationRunner {
    
    @Value("${deploy.environment}")
    private String deployEnv;  // 환경 변수나 시스템 프로퍼티로 주입
    
    @Value("${config.environment}")
    private String configEnv;  // 설정 파일에 명시된 환경
    
    @Override
    public void run(ApplicationArguments args) {
        if (!deployEnv.equals(configEnv)) {
            throw new IllegalStateException(
                "환경 불일치: deploy=" + deployEnv + ", config=" + configEnv
            );
        }
    }
}
```

---

## 설정 관리 구성 시 판단 기준

설정 관리 시스템을 구성할 때 다음을 기준으로 판단한다.

**일반 설정과 Secret을 분리하라.** DB URL은 ConfigMap이나 Config Server에 넣고, DB 비밀번호는 Vault나 Secrets Manager에 넣는다. 같은 곳에 넣으면 접근 권한 관리가 어렵다. 개발자 전원이 DB 비밀번호를 볼 수 있는 상태가 된다.

**Git 기반 설정 관리에서는 PR 리뷰를 거쳐라.** 설정 변경도 코드 변경과 같은 수준으로 리뷰한다. 타임아웃 값 하나가 장애를 만들 수 있다. CI에서 설정 파일의 문법 검증과 값 범위 검증을 자동으로 돌린다.

**설정 변경 이력을 추적할 수 있어야 한다.** 장애가 났을 때 "최근에 뭐 바꿨지?"부터 확인한다. Config Server + Git이면 히스토리가 자동으로 남고, KV 스토어라면 변경 이벤트를 별도로 기록해둬야 한다.

**Secret에 접근할 수 있는 범위를 최소화하라.** 주문 서비스는 주문 DB의 비밀번호만 알면 된다. 결제 서비스의 PG사 API 키를 알 이유가 없다. Vault에서는 Policy로, AWS에서는 IAM으로 서비스별 접근 범위를 제한한다.
