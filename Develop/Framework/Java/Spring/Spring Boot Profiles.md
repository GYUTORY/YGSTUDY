---
title: Spring Boot Profiles 심화
tags: [framework, java, spring, spring-boot, profiles, configuration, environment]
updated: 2026-06-07
---

# Spring Boot Profiles

환경별로 설정을 바꿔 끼우는 메커니즘이다. 개념 자체는 단순한데, 실제로 운영에 투입해보면 "왜 운영 yml이 안 먹지", "JAR에는 적용되는데 IDE 실행에서는 빠지지" 같은 일이 흔하다. 이 문서는 그 차이가 왜 생기는지, PropertySource 체인 어디서 덮였는지 추적하는 데 필요한 내용을 정리한 것이다.

## 프로파일이 풀어주는 문제

Spring Boot 애플리케이션이 dev·test·staging·prod에서 다르게 동작해야 하는 부분은 보통 세 가지다. 데이터소스 URL과 자격증명, 외부 시스템 엔드포인트(메시지 큐·Redis·외부 API), 그리고 로깅 레벨이나 actuator 노출 범위 같은 운영 정책. 이걸 자바 코드의 분기문으로 처리하면 빌드 산출물이 환경별로 달라지므로 "어떤 빌드가 운영에 올라가는지" 추적이 어려워진다.

프로파일은 하나의 JAR/WAR을 두고, 외부에서 주어지는 활성 프로파일 값에 따라 다른 설정 묶음이 로드되도록 하는 구조다. 결국 핵심은 "어떤 키가 어떤 순서로 머지되어 최종 값이 결정되는가"이며, 이 순서를 모르면 디버깅이 불가능하다.

## 활성 프로파일을 정하는 방법

활성 프로파일은 `spring.profiles.active` 키 하나로 결정된다. 단지 그 키를 어디서 주입하느냐만 다르다.

- `application.yml`에 직접 적기 — `spring.profiles.active: dev`
- JVM 시스템 프로퍼티 — `java -Dspring.profiles.active=prod -jar app.jar`
- OS 환경변수 — `SPRING_PROFILES_ACTIVE=prod` (Spring은 점 표기를 자동으로 언더스코어 대문자로 변환해 매칭한다)
- 커맨드라인 인자 — `java -jar app.jar --spring.profiles.active=prod`
- 코드에서 직접 — `SpringApplication.setAdditionalProfiles("prod")`
- 컨테이너 환경 — Docker `-e`, Kubernetes Pod env, ECS Task Definition

가장 자주 쓰는 건 환경변수다. JVM 옵션은 JAR 실행 명령에 들어가야 해서 컨테이너에서는 빠뜨리기 쉽다.

## PropertySource 우선순위 체인 — 디버깅의 출발점

`spring.profiles.active`도 결국 하나의 프로퍼티 키다. 그래서 여러 곳에서 동시에 정의되면 우선순위가 높은 쪽이 이긴다. 전체 체인은 Spring Boot 공식 레퍼런스의 "Externalized Configuration" 챕터에 정의되어 있고, 높은 쪽이 낮은 쪽을 덮어쓴다.

```
1. DevTools에서 설정한 SpringApplication.setDefaultProperties()의 글로벌 설정
2. @TestPropertySource (테스트 한정)
3. properties 어트리뷰트가 있는 @SpringBootTest (테스트 한정)
4. 커맨드라인 인자 (--key=value)
5. SPRING_APPLICATION_JSON (환경변수 또는 시스템 프로퍼티)
6. ServletConfig init parameters
7. ServletContext init parameters
8. JNDI 속성 (java:comp/env)
9. Java 시스템 프로퍼티 (-D 옵션)
10. OS 환경변수
11. 랜덤 값 (random.*)
12. JAR 외부 profile-specific application properties (application-{profile}.yml)
13. JAR 내부 profile-specific application properties
14. JAR 외부 application properties (application.yml)
15. JAR 내부 application properties
16. @PropertySource로 지정된 파일
17. SpringApplication.setDefaultProperties()로 지정한 기본 속성
```

위에 있을수록 우선순위가 높다. 실무에서 자주 마주치는 충돌은 이 체인의 9~14번 사이에서 일어난다.

### 충돌 사례 1: 환경변수가 yml을 이긴다

운영에서 `application-prod.yml`에 `datasource.url: jdbc:mysql://prod-db:3306/app`을 박아놨는데, 컨테이너에서 누군가 `SPRING_DATASOURCE_URL=jdbc:mysql://stage-db:3306/app` 환경변수를 잘못 주입했다고 하자. 환경변수(10번)가 profile-specific yml(13번)보다 우선순위가 높으므로 stage-db로 붙는다. yml만 보고는 절대 원인을 찾을 수 없다.

진단 방법은 actuator의 `/actuator/env` 엔드포인트다. 어떤 PropertySource에서 어떤 값이 왔는지 출처가 그대로 노출된다. 운영에는 보안상 노출할 수 없으니, 동일 환경변수 세트로 staging에서 띄워서 확인하는 게 현실적이다.

### 충돌 사례 2: 커맨드라인 인자가 다 이긴다

CI/CD에서 `java -jar app.jar --server.port=9090`처럼 인자를 넘기면 yml의 `server.port`는 무시된다. 4번이라 거의 무조건 이긴다. "포트 설정이 자꾸 바뀐다"고 신고가 들어오면 가장 먼저 deployment 스크립트의 `args:` 항목을 본다.

### 충돌 사례 3: 외부 yml이 내부 yml을 덮는다

`-Dspring.config.additional-location=/etc/app/`로 외부 디렉토리를 지정하면 그 안의 `application.yml`이 JAR 내부 yml을 덮는다. Kubernetes ConfigMap을 `/etc/app/application.yml`로 마운트하는 패턴이 이걸 이용한다. JAR을 다시 빌드하지 않고 ConfigMap만 바꿔 값을 갱신할 수 있다.

## spring.profiles.active vs spring.profiles.include

이 둘은 비슷해 보이지만 동작 방식이 완전히 다르다.

### active — 덮어쓰기

`spring.profiles.active`는 활성 프로파일 목록을 "지정"한다. 여러 곳에서 정의되면 우선순위가 높은 쪽이 통째로 이긴다. 예를 들어 `application.yml`에 `active: dev`라고 적혀 있어도, JVM 옵션으로 `-Dspring.profiles.active=prod`를 주면 dev는 흔적도 없이 사라지고 prod만 남는다.

### include — 추가만 가능

`spring.profiles.include`는 "활성 프로파일에 추가로 더 로드"하는 용도다. 예를 들어 prod 환경에서 항상 함께 로드하고 싶은 monitoring·tracing 같은 횡단 설정이 있다면, prod 자체는 `active`로 지정하고 monitoring은 prod yml 안에서 include로 추가한다.

```yaml
# application-prod.yml
spring:
  config:
    activate:
      on-profile: prod
  profiles:
    include:
      - monitoring
      - tracing
```

이 설정으로 prod가 활성화되면 monitoring과 tracing yml도 함께 로드된다. 다른 환경(dev·test)에서는 prod yml 자체가 로드되지 않으므로 include도 따라오지 않는다.

### 중요한 제약: profile-specific 파일 안에서 active 못 쓴다

흔히 빠지는 함정이다. `application-dev.yml` 안에 `spring.profiles.active: dev2`라고 적어도 dev2는 활성화되지 않는다. profile-specific 문서 안에서는 active 키를 무시한다 (Spring Boot 2.4부터 명시적으로 막혔다). 파일이 로드된 시점에 이미 active 결정이 끝났기 때문이다. profile-specific 파일에서는 include만 가능하다.

active를 동적으로 추가하고 싶다면 `application.yml`(루트)에서만 가능하거나, profile group을 써야 한다.

### profile group — active 한 값에 여러 프로파일 묶기

`spring.profiles.group.xxx`로 하나의 그룹명에 여러 프로파일을 묶을 수 있다. group은 active로 지정되었을 때 해당 그룹의 모든 멤버를 함께 활성화한다.

```yaml
# application.yml
spring:
  profiles:
    group:
      production:
        - prod
        - monitoring
        - tracing
      local:
        - dev
        - h2
```

`--spring.profiles.active=production`을 넘기면 prod·monitoring·tracing 세 프로파일이 동시에 활성화된다. 운영에서 `--spring.profiles.active=prod,monitoring,tracing`처럼 쉼표 나열하는 것과 결과는 같지만, 그룹은 yml에 정의되어 있어 운영팀이 외울 필요가 없다.

## @Profile 어노테이션 심화

`@Profile`은 빈 정의를 조건부로 만든다. 내부적으로는 `@Conditional(ProfileCondition.class)`의 메타 어노테이션이라, `@Conditional`과 같은 시점(ConfigurationClassPostProcessor)에 평가된다.

```java
@Service
@Profile("dev")
public class DevMailService implements MailService {
    public void send(String to, String body) {
        log.info("[DEV] {} -> {}", to, body);
    }
}
```

Spring 5.1부터 `@Profile`은 단순 이름 매칭이 아닌 SpEL 형태의 프로파일 표현식을 받는다.

```java
// dev가 아닌 모든 환경
@Profile("!prod")

// dev 또는 test
@Profile({"dev", "test"})           // OR 의미 (배열)
@Profile("dev | test")              // OR 의미 (표현식)

// prod 이면서 monitoring이 함께 켜진 경우만
@Profile("prod & monitoring")

// 복합 표현식
@Profile("(dev | test) & !ci")
```

5.1 이전에는 `,`로 OR을 표현했고 `&`, `|`, `!` 같은 연산자는 지원하지 않았다. 5.1+로 올라온 코드베이스에서는 가급적 표현식 문법으로 통일하는 게 가독성이 좋다.

### @Profile과 @Conditional의 관계

`@Profile`은 결국 `@Conditional`의 특수 케이스다. 더 복잡한 조건(특정 클래스 존재 여부, 프로퍼티 값에 따른 분기 등)이 필요하면 `@ConditionalOnProperty`나 직접 작성한 `Condition` 구현체를 쓴다. 보통 다음처럼 역할 분담한다.

- 환경 자체(dev/prod)로 분기 → `@Profile`
- 특정 라이브러리 존재 여부 → `@ConditionalOnClass`
- 특정 설정값 ON/OFF → `@ConditionalOnProperty`

`@Profile`을 `@ConditionalOnProperty(value="env", havingValue="prod")` 형태로 대체할 수 있지만, 의도가 묻혀버리므로 환경 분기는 그냥 `@Profile`을 쓴다.

### 빈이 아예 만들어지지 않는다는 점

`@Profile`은 빈을 "비활성화"하는 게 아니라 "정의 자체를 컨테이너에 등록하지 않는다". 따라서 활성 프로파일이 아닌 빈을 `@Autowired`로 받으려면 `required = false`로 받거나 `Optional<T>`로 받아야 한다. 그렇지 않으면 컨텍스트 로딩이 실패한다.

```java
@Autowired(required = false)
private DevMailService devMailService;  // dev가 아닌 환경에서는 null
```

## profile-specific 파일 로딩 순서

활성 프로파일이 정해지면 Spring Boot는 다음 순서로 파일을 찾는다.

```
1. application.properties
2. application.yml
3. application-{profile}.properties
4. application-{profile}.yml
```

뒤에 로드되는 파일이 앞 파일의 같은 키를 덮어쓴다. 즉 profile-specific 설정이 공통 설정을 이긴다. 여러 프로파일이 동시에 활성화된 경우(`active=prod,monitoring`)에는 active 목록의 뒤쪽이 앞쪽을 덮어쓴다. 그래서 가장 우선시되어야 할 프로파일을 뒤에 둔다.

확장자도 우선순위가 있다. yml과 properties가 모두 있다면 properties가 yml을 덮는다(properties가 더 명시적이라는 Spring Boot의 입장). 운영에서는 둘 중 하나로 통일하는 게 사고를 줄인다.

## multi-document YAML — 한 파일 안에서 프로파일 분리

파일을 여러 개로 쪼개기 싫을 때, YAML의 `---` 구분자를 써서 단일 파일 안에 여러 문서를 둘 수 있다. 각 문서마다 `spring.config.activate.on-profile`을 다르게 지정한다.

```yaml
# application.yml — 공통 설정
spring:
  application:
    name: order-service
server:
  port: 8080
---
# dev 문서
spring:
  config:
    activate:
      on-profile: dev
  datasource:
    url: jdbc:h2:mem:devdb
logging:
  level:
    root: DEBUG
---
# prod 문서
spring:
  config:
    activate:
      on-profile: prod
  datasource:
    url: jdbc:mysql://${DB_HOST}:3306/${DB_NAME}
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}
logging:
  level:
    root: WARN
```

Spring Boot 2.4부터 `spring.profiles: dev` 같은 짧은 표기는 deprecated 되었다. `spring.config.activate.on-profile` 표기를 써야 한다.

장점은 한 화면에서 환경별 diff를 비교할 수 있다는 것이다. 단점은 운영용 자격증명이 dev·test 설정과 같은 파일에 있으면 안 된다는 보안 정책에 걸린다. 보통 공통 + dev/test는 multi-document로 묶고, prod만 별도 파일이나 외부 마운트로 분리한다.

## Config Data API — Spring Boot 2.4+의 spring.config.import

Spring Boot 2.4에서 Config Data API가 도입되면서 외부 설정 소스를 yml에서 명시적으로 import할 수 있게 됐다. 이전에는 `bootstrap.yml`이나 `spring.config.additional-location` 환경변수에 의존해야 했다.

```yaml
# application.yml
spring:
  config:
    import:
      - optional:file:./config/app.yml
      - optional:configtree:/etc/secrets/
      - optional:configserver:http://config-server:8888
```

- `optional:` 접두어 — 파일이 없어도 부팅 실패 안 함
- `configtree:` — 디렉토리를 트리 구조로 읽어 각 파일을 키-값으로 매핑 (Kubernetes Secret 마운트 패턴)
- `configserver:` — Spring Cloud Config Server에서 받아옴

`configtree`는 Kubernetes에서 가장 흔한 패턴이다. Secret이나 ConfigMap을 `subPath` 없이 디렉토리로 마운트하면 각 키가 파일로 떨어진다. 이 디렉토리를 configtree로 읽으면 파일명이 그대로 프로퍼티 키가 된다.

```
/etc/secrets/
├── spring.datasource.password   (내용: secret123)
└── spring.datasource.username   (내용: appuser)
```

위 구조라면 `spring.datasource.password=secret123`이 자동으로 로드된다. 환경변수로 비밀번호를 노출하지 않아도 되는 이점이 있다.

### spring.config.additional-location과의 차이

`spring.config.additional-location`은 디렉토리를 추가 검색 경로로 등록한다. 그 안에 `application.yml`이 있으면 자동으로 읽는다. `spring.config.import`는 더 명시적이며 파일 단위 지정이 가능하다. 새로운 코드베이스는 import 쪽을 권장하지만, 기존 운영 환경은 additional-location으로 굳어져 있는 경우가 많다.

## 테스트 프로파일

테스트는 프로파일 사용 패턴이 운영과 다르다. 주로 다음 셋이 쓰인다.

### @ActiveProfiles

```java
@SpringBootTest
@ActiveProfiles("test")
class OrderServiceTest {
    // application-test.yml 자동 로딩
}
```

`@ActiveProfiles`는 테스트 컨텍스트가 띄울 활성 프로파일을 강제한다. `application-test.yml`이 클래스패스에 있으면 자동으로 로드된다. 테스트 전용 설정(임베디드 DB·짧은 타임아웃·외부 호출 mock 모드)을 여기 모은다.

### @ActiveProfiles(resolver = ...)

활성 프로파일을 동적으로 결정해야 할 때 쓴다. CI 환경 변수에 따라 프로파일을 바꾸거나, 테스트 클래스의 어노테이션을 보고 결정하는 등 정적 문자열로 부족한 경우다.

```java
public class CiAwareProfileResolver implements ActiveProfilesResolver {
    @Override
    public String[] resolve(Class<?> testClass) {
        String ci = System.getenv("CI");
        return ci != null ? new String[]{"test", "ci"} : new String[]{"test", "local"};
    }
}

@SpringBootTest
@ActiveProfiles(resolver = CiAwareProfileResolver.class)
class IntegrationTest { }
```

흔하게 쓰지는 않지만, 한 번 도입하면 환경별 분기를 코드로 표현할 수 있다.

### @TestPropertySource

특정 키만 테스트에서 덮어쓰고 싶을 때 쓴다. PropertySource 우선순위 체인의 2번 자리에 들어가므로 거의 모든 설정을 이긴다.

```java
@SpringBootTest
@ActiveProfiles("test")
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:override",
    "app.feature.new-checkout.enabled=true"
})
class CheckoutFeatureTest { }
```

`@SpringBootTest(properties = {...})`도 같은 역할을 하지만 우선순위가 한 단계 낮다(3번). 둘 다 쓰면 `@TestPropertySource`가 이긴다.

### ApplicationContext 캐싱과 프로파일

이 부분이 테스트 속도에 크게 영향을 준다. Spring TestContext Framework는 동일한 설정(빈 정의 + 활성 프로파일 + 프로퍼티 + 설정 클래스 조합)의 ApplicationContext를 캐시하고 재사용한다. 즉 `@ActiveProfiles("test")`만 쓰는 테스트들끼리는 컨텍스트를 공유하므로 빠르다.

문제는 매 테스트마다 다른 `@ActiveProfiles`나 `@TestPropertySource`를 쓰는 경우다. 캐시 키가 달라져 매번 새 컨텍스트를 띄운다. 5천 줄짜리 통합 테스트 묶음에서 이게 누적되면 빌드 시간이 두 배 이상 늘어난다.

```java
// 컨텍스트 두 개 생김 — 느림
class A { @ActiveProfiles("test") }
class B { @ActiveProfiles("test"); @TestPropertySource(properties = "a=1") }

// 컨텍스트 하나 — 빠름
class A { @ActiveProfiles("test") }
class B { @ActiveProfiles("test") }  // 같은 yml만 사용
```

테스트가 느리다 싶으면 `@ContextHierarchy`나 `@DirtiesContext`를 점검하기 전에, 활성 프로파일·프로퍼티 조합이 몇 가지나 만들어지는지부터 본다.

## 실무 트러블슈팅

### 사례 1: "profile이 활성화되지 않는다"

가장 흔한 오해. profile-specific yml(`application-prod.yml`)을 만들고 그 안에 `spring.profiles.active: prod`라고 적은 케이스. 위에서 설명한 대로 profile-specific 문서 안에서 active 키는 무시된다. active는 외부에서(환경변수·JVM 옵션·`application.yml`) 들어와야 한다.

확인 방법: 부팅 로그에서 다음 줄을 찾는다.

```
The following 1 profile is active: "prod"
```

이 줄이 없거나 다른 프로파일이 찍혀 있다면 active 주입 방법부터 다시 본다.

### 사례 2: IDE에서는 되는데 JAR에서는 안 됨

IDE는 `src/main/resources`와 `src/test/resources`를 동시에 클래스패스에 둔다. 테스트 리소스에 있는 `application-dev.yml`이 IDE 실행에서는 잡히지만, JAR 빌드 시에는 테스트 리소스가 빠진다. dev yml을 `src/main/resources`로 옮기거나, 운영용은 외부 디렉토리로 마운트한다.

### 사례 3: Gradle bootRun과 java -jar 동작 차이

Gradle `bootRun`은 `bootRun { args = [...] }` 또는 `bootRun { systemProperty 'spring.profiles.active', 'dev' }` 형태로 별도 설정해야 한다. 그냥 `gradle bootRun`만 실행하면 환경변수만 잡아간다. JAR을 직접 실행할 때 동작하는 옵션이 bootRun에서는 무시되는 경우가 있다.

Maven은 `mvn spring-boot:run -Dspring-boot.run.profiles=dev` 형태다. `-Dspring.profiles.active`가 아니라 `-Dspring-boot.run.profiles`다. 자주 헷갈리는 부분이다.

### 사례 4: 환경변수 명명 규칙

`spring.profiles.active`를 환경변수로 주입할 때는 `SPRING_PROFILES_ACTIVE`다. 점은 언더스코어로, 모두 대문자로. Kubernetes Pod env에서 `spring.profiles.active`라는 키로 줘도 동작은 한다(Spring이 알아서 매핑한다). 다만 일관성을 위해 환경변수는 대문자 형태로 통일하는 게 좋다.

### 사례 5: actuator로 디버깅

문제가 안 잡힐 때는 `/actuator/env`와 `/actuator/configprops`를 본다. env는 어떤 PropertySource에서 어떤 키가 왔는지, configprops는 `@ConfigurationProperties`로 바인딩된 최종 값이 무엇인지 보여준다. 운영 노출은 막아야 하지만, 동일 yml로 staging에서 띄우면 바로 확인 가능하다.

```
GET /actuator/env/spring.datasource.url

{
  "property": {
    "source": "applicationConfig: [classpath:/application-prod.yml]",
    "value": "jdbc:mysql://prod-db:3306/app"
  },
  "activeProfiles": ["prod"],
  ...
}
```

`source`가 `systemEnvironment`로 찍혔다면 yml이 아니라 환경변수에서 왔다는 뜻이다.

### 사례 6: default 프로파일과 활성 프로파일

활성 프로파일을 지정하지 않으면 Spring은 "default" 프로파일이 활성화된 것으로 간주한다. 그래서 `application-default.yml`이라는 파일이 있으면 그게 로드된다. 모르고 만들면 의도치 않게 로드된다. `spring.profiles.default` 키로 이름을 바꿀 수 있지만 거의 안 쓴다.

## 환경별 yml 분리 패턴

실무에서 자주 쓰이는 yml 분리 패턴 몇 가지.

### 패턴 1: 공통 + 환경별 분리

```
application.yml         # 모든 환경 공통 (애플리케이션 이름, common port 등)
application-dev.yml     # 개발용 (H2, 자세한 로그)
application-staging.yml # 스테이징 (운영과 비슷한 DB, 디버그 로그)
application-prod.yml    # 운영 (외부 비밀로 받는 자격증명)
```

가장 단순하고 흔한 패턴. 다만 prod yml에 비밀번호 placeholder(`${DB_PASSWORD}`)만 두고 실제 값은 외부에서 주입한다.

### 패턴 2: 횡단 관심사 분리

```
application-monitoring.yml  # 메트릭·트레이싱 설정
application-cache.yml       # Redis·캐시 설정
application-async.yml       # 비동기 처리 설정
```

이런 횡단 관심사를 별도 프로파일로 빼두고, 환경별로 include 한다.

```yaml
# application-prod.yml
spring:
  config:
    activate:
      on-profile: prod
  profiles:
    include:
      - monitoring
      - cache
      - async
```

dev에서는 monitoring만 빼고 켜는 식의 조합이 가능하다.

### 패턴 3: ConfigMap/Secret 외부화

```yaml
# application.yml (JAR 내부)
spring:
  config:
    import:
      - optional:configtree:/etc/config/
      - optional:configtree:/etc/secrets/
  profiles:
    active: ${APP_PROFILE:dev}
```

Kubernetes에서 ConfigMap과 Secret을 각각 디렉토리로 마운트한다. JAR을 다시 빌드하지 않고 ConfigMap 변경만으로 설정을 갱신할 수 있다. 운영용 패턴.

## Spring Boot 버전별 차이

| 버전 | 변화 |
|------|------|
| 2.3 이하 | `spring.profiles: dev`로 profile-specific 문서 활성화 |
| 2.4+ | Config Data API 도입. `spring.profiles: dev`는 deprecated, `spring.config.activate.on-profile: dev`로 표기. `spring.config.import` 지원. `bootstrap.yml` 의존도 감소 |
| 2.4+ | `spring.profiles.include`가 profile-specific 문서에서만 동작하도록 제약 강화 |
| 3.0+ | 명세는 2.4와 동일. Jakarta EE 9 마이그레이션이 더 큰 변화 |

2.4 이전 코드를 마이그레이션할 때 가장 자주 깨지는 게 profile-specific 문서의 active 키와 `spring.profiles:` 짧은 표기다. 부팅 시 경고 로그가 찍히니 빌드 직후 한 번 훑어본다.

## 정리

프로파일 디버깅은 결국 PropertySource 체인의 어느 자리에서 값이 결정되었는지 추적하는 것이다. yml만 보고 추론하면 환경변수·시스템 프로퍼티·커맨드라인 인자가 덮은 경우를 절대 찾을 수 없다. actuator의 `/env`를 띄울 수 있는 환경(staging·로컬)을 하나 만들어두고, 의심스러우면 거기서 확인하는 습관이 핵심이다.

active와 include의 차이, profile-specific 문서 안에서 active 사용 불가 제약, profile group의 동작 방식 — 이 세 가지를 정확히 알면 90%의 함정은 피한다. 나머지 10%는 IDE·Gradle·Maven·JAR 실행 방식별로 환경변수가 다르게 전달되는 케이스고, 이건 부팅 로그의 "active profile" 라인 하나만 확인하면 잡힌다.
