---
title: UTC 저장
tags: [utc, timezone, datetime, spring, mysql, postgresql, java, backend]
updated: 2026-07-31
---

# UTC 저장

## 핵심 원칙

모든 시각 데이터는 UTC로 저장한다. 사용자에게 보여줄 때만 변환한다.

DB에 KST로 저장하는 경우를 자주 본다. 국내 서비스만 하는 동안은 아무 문제가 없다. 로컬 타임존이 항상 KST이고, 서버도 KST이고, DB도 KST다. 문제는 서비스 확장이나 서버 마이그레이션 때 터진다. DB 서버의 타임존이 UTC로 바뀌거나, 앱 서버를 다른 리전에 올리는 순간 기존 데이터가 어떤 타임존인지 알 방법이 없다. 컬럼 타입에 타임존 정보가 없기 때문이다.

저장 시점에 타임존을 통일해두지 않으면, 마이그레이션 때 "언제부터 UTC였는지"를 코드 히스토리와 배포 로그를 뒤져가며 추적해야 한다.

## Java 타입 선택

### LocalDateTime vs ZonedDateTime vs Instant

세 타입 중 어떤 걸 써야 하는지 매번 혼란이 생긴다.

`LocalDateTime`은 타임존 정보가 없다. 2026-07-31T10:00:00이 UTC인지 KST인지 코드만 봐서는 알 수 없다. DB에서 읽어온 값을 그대로 쓰거나, 시각 계산 없이 단순 저장·조회만 할 때 문제가 드러나지 않는다. 타임존이 섞이기 시작하면 버그가 생긴다.

`ZonedDateTime`은 타임존 정보를 포함한다. `2026-07-31T10:00:00+09:00[Asia/Seoul]`처럼 어느 타임존인지 명확하다. 사용자 입력을 받아 타임존을 보존해야 하거나, 타임존별 로직이 필요할 때 쓴다. DB에 저장할 때는 UTC로 변환해서 넣는다.

`Instant`는 UTC 기준 에포크 타임이다. 타임존 개념이 없고 항상 UTC다. 내부 처리나 DB 저장용으로 가장 명확하다. 사용자에게 보여줄 때는 `ZoneId`를 적용해서 변환한다.

실무에서 쓰는 패턴은 다음과 같다.

- 내부 저장·처리: `Instant`
- 사용자 입력 수신·표시: `ZonedDateTime`
- 타임존 없는 단순 날짜(생년월일, 공휴일 등): `LocalDate`
- `LocalDateTime`은 타임존이 애플리케이션 전체에서 고정되어 있고 바뀔 일이 없다고 100% 확신할 때만 쓴다

```java
// 저장
Instant now = Instant.now(); // UTC 기준
entity.setCreatedAt(now);

// 사용자 표시
ZoneId userZone = ZoneId.of("Asia/Seoul");
ZonedDateTime display = now.atZone(userZone);
// 2026-07-31T19:00:00+09:00[Asia/Seoul]
```

## DB 레이어 설정

### MySQL

MySQL의 `TIMESTAMP` 타입은 저장 시 세션 타임존을 기준으로 UTC 변환하고, 조회 시 세션 타임존으로 되돌려 반환한다. 세션 타임존이 달라지면 조회 결과가 달라진다.

`DATETIME` 타입은 입력값을 그대로 저장한다. 타임존 변환을 하지 않는다. DB 서버 타임존과 무관하게 항상 같은 값을 반환하지만, 그 값이 어떤 타임존인지는 애플리케이션이 알아서 관리해야 한다.

UTC 저장 원칙 기준으로 정리하면:

- `DATETIME` + 애플리케이션에서 UTC로 변환 후 저장: 가장 명확하다. DB 서버 타임존에 영향을 받지 않는다.
- `TIMESTAMP`: DB 서버 타임존을 반드시 UTC로 설정해야 한다. 세션 타임존도 UTC로 고정해야 한다.

```sql
-- DB 서버 타임존 확인
SELECT @@global.time_zone, @@session.time_zone;

-- UTC로 설정 (my.cnf)
-- [mysqld]
-- default-time-zone = '+00:00'
```

JDBC 연결 시 타임존을 명시한다.

```
jdbc:mysql://host/db?serverTimezone=UTC&useLegacyDatetimeCode=false
```

`serverTimezone=UTC`를 빠뜨리면 JVM 타임존과 MySQL 서버 타임존이 다를 때 저장값이 틀어진다. 로컬 개발 환경은 KST, 운영 서버는 UTC인 경우 로컬에서 정상 동작하다가 운영에서 9시간 차이가 생기는 문제가 발생한다.

### PostgreSQL

PostgreSQL은 `TIMESTAMP WITH TIME ZONE`(timestamptz)과 `TIMESTAMP WITHOUT TIME ZONE`(timestamp) 두 타입이 있다.

`timestamptz`는 입력값을 UTC로 변환해서 저장하고, 조회 시 세션 타임존으로 변환해 반환한다. MySQL `TIMESTAMP`와 비슷하다.

`timestamp`는 입력값을 그대로 저장한다. 타임존 변환 없이 입력한 값 그대로 나온다.

UTC 저장 원칙 기준으로 `timestamptz`를 쓰면서 세션 타임존을 UTC로 고정하거나, `timestamp`를 쓰면서 애플리케이션에서 UTC 변환 후 저장한다.

```sql
-- 세션 타임존 확인
SHOW timezone;

-- UTC 설정 (postgresql.conf)
-- timezone = 'UTC'

-- 또는 연결 시
SET TIME ZONE 'UTC';
```

## Spring Boot 설정

JVM 타임존을 UTC로 고정한다. 코드에서 `TimeZone.setDefault()`를 쓰는 방법도 있지만, JVM 옵션으로 설정하는 게 더 안전하다. 코드 실행 순서에 따라 `setDefault()` 이전에 타임존을 읽어가는 경우가 있다.

```bash
# JVM 옵션
-Duser.timezone=UTC
```

```java
// 또는 애플리케이션 진입점
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
        SpringApplication.run(Application.class, args);
    }
}
```

JPA/Hibernate를 쓰는 경우 `application.yml`에 추가한다.

```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          time_zone: UTC
```

이 설정 없이 `Instant`나 `ZonedDateTime`을 DB에 저장하면 Hibernate가 JVM 타임존을 기준으로 변환하는 경우가 있다. Hibernate 버전마다 동작이 다르기 때문에 명시적으로 설정하는 게 낫다.

## 캐시 레이어

Redis나 Memcached에 시각 데이터를 캐시할 때 직렬화 방식을 확인해야 한다.

`Instant`를 JSON으로 직렬화하면 기본적으로 에포크 초(epoch seconds) 또는 ISO 8601 형식으로 저장된다. 역직렬화할 때 타임존 정보가 없으면 JVM 기본 타임존으로 처리하는 라이브러리가 있다.

Jackson 기준으로 설정한다.

```java
ObjectMapper mapper = new ObjectMapper();
mapper.registerModule(new JavaTimeModule());
mapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
mapper.configure(DeserializationFeature.ADJUST_DATES_TO_CONTEXT_TIME_ZONE, false);
```

`ADJUST_DATES_TO_CONTEXT_TIME_ZONE`을 `false`로 설정하지 않으면 역직렬화 시 컨텍스트 타임존으로 변환한다. Redis에 UTC로 저장했는데 꺼낼 때 KST로 나오는 문제가 생길 수 있다.

## 사용자 표시 시점 변환

변환은 응답 직전 한 곳에서만 한다. 서비스 레이어에서 변환하면 내부 로직이 타임존에 의존하게 된다. 컨트롤러 응답을 만들 때 변환하거나, DTO 변환 레이어에서 처리한다.

```java
// 내부 처리: Instant
public Order findOrder(Long id) {
    return orderRepository.findById(id).orElseThrow();
    // Order.createdAt은 Instant
}

// 사용자 응답 변환
public OrderResponse toResponse(Order order, ZoneId userZone) {
    return OrderResponse.builder()
        .createdAt(order.getCreatedAt().atZone(userZone)
            .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME))
        .build();
}
```

사용자 타임존은 요청 헤더나 사용자 설정에서 가져온다. `X-User-Timezone: Asia/Seoul` 같은 커스텀 헤더를 쓰거나, 사용자 프로필에 저장한 타임존 설정을 조회한다.

```java
@GetMapping("/orders/{id}")
public OrderResponse getOrder(@PathVariable Long id,
                               @RequestHeader(value = "X-User-Timezone",
                                              defaultValue = "UTC") String timezone) {
    ZoneId zoneId = ZoneId.of(timezone);
    Order order = orderService.findOrder(id);
    return orderMapper.toResponse(order, zoneId);
}
```

`ZoneId.of()`에 유효하지 않은 타임존 문자열이 들어오면 `ZoneRulesException`이 발생한다. 사용자 입력이므로 예외 처리가 필요하다.

## 흔한 실수

### DB 서버와 앱 서버 타임존 불일치

개발 환경에서 가장 자주 발생하는 문제다. 로컬 맥북은 KST, CI/CD와 운영 서버는 UTC인 상황에서 발생한다.

증상은 특정 환경에서만 시각이 9시간 어긋나는 것이다. 로컬에서 `created_at`이 10:00으로 저장되면 운영에서는 01:00으로 조회되거나, 반대 방향으로 어긋난다.

원인을 찾으려면 다음 순서로 확인한다.

```sql
-- MySQL: 서버 타임존 확인
SELECT @@global.time_zone, @@session.time_zone, NOW(), UTC_TIMESTAMP();

-- PostgreSQL: 타임존 확인
SHOW timezone;
SELECT NOW(), NOW() AT TIME ZONE 'UTC';
```

```bash
# JVM 타임존 확인
java -XshowSettings:all -version 2>&1 | grep timezone
# 또는 애플리케이션 로그에서
echo $TZ
```

JDBC URL, JVM 옵션, DB 서버 타임존 세 곳을 모두 UTC로 맞춰야 한다. 하나라도 다르면 변환이 중첩되거나 어긋난다.

### TIMESTAMP 2038년 문제

MySQL `TIMESTAMP` 타입의 저장 범위는 2038-01-19 03:14:07 UTC까지다. 예약 시스템이나 만료 일자를 다루는 서비스에서 이 범위를 넘는 날짜를 저장하면 에러가 발생한다. `DATETIME` 타입으로 바꾸고 애플리케이션에서 UTC를 관리하는 방식이 낫다.

### `NOW()` vs `UTC_TIMESTAMP()`

MySQL에서 `NOW()`는 세션 타임존 기준 현재 시각을 반환한다. 세션 타임존이 KST면 KST 기준 현재 시각이다. `DATETIME` 컬럼에 `DEFAULT NOW()`를 쓰면 DB 서버 타임존 설정에 따라 저장되는 값이 달라진다.

`UTC_TIMESTAMP()`는 항상 UTC 기준 현재 시각을 반환한다. `DATETIME` 컬럼의 기본값을 UTC로 고정하려면 `DEFAULT (UTC_TIMESTAMP())`를 쓰거나, 애플리케이션에서 UTC 값을 직접 넣는다.

PostgreSQL에서는 `NOW()`가 트랜잭션 시작 시각을 반환하고 타임존 정보를 포함한다(`timestamptz`). `CURRENT_TIMESTAMP`도 동일하다. `timestamptz` 컬럼에 저장하면 내부적으로 UTC로 변환된다.
