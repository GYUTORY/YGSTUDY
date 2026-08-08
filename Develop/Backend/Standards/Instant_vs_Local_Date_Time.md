---
title: Instant vs LocalDateTime
tags: [java, typescript, backend]
updated: 2026-07-31
---

# Instant vs LocalDateTime

## 두 타입의 근본적인 차이

`Instant`와 `LocalDateTime`을 "타임존 있고 없고"로 구분하는 설명이 많은데, 그것보다 더 정확한 구분이 있다.

`Instant`는 타임라인 위의 절대적인 한 점이다. 1970-01-01T00:00:00Z를 기준으로 경과한 시간(나노초 단위)을 표현하며, 지구 어디서 보든 같은 물리적 순간을 가리킨다. "이 주문이 생성된 정확한 순간"을 기록할 때 쓴다.

`LocalDateTime`은 타임존 없는 달력 읽기다. `2026-07-31T18:00:00`이라는 값이 있을 때, 이것이 서울의 저녁 6시인지 런던의 저녁 6시인지 알 수 없다. 타임라인 위의 어떤 점인지 특정할 수 없고, UTC로 바꾸려면 어떤 타임존인지 외부 정보가 반드시 필요하다.

혼동이 생기는 이유는 "Local"이라는 단어 때문에 "서버 로컬 타임존 기준" 처럼 느껴지기 때문이다. 실제로는 타임존 자체가 없는 값이다. 벽에 걸린 시계를 읽은 것처럼, 숫자는 있지만 어느 지역인지 모른다.

## 언제 무엇을 쓰는가

`Instant`는 시스템 이벤트 기록에 쓴다. `created_at`, `updated_at`, `deleted_at`, 로그 타임스탬프, 결제 발생 시각처럼 "언제 일어났는가"를 기록하는 곳에는 `Instant`가 맞다.

`LocalDateTime`은 타임존 없는 달력 값에 쓴다. 생년월일, 공휴일, 반복 스케줄 표현("매월 1일 오전 9시"), 영수증에 찍히는 점포 현지 시각이 여기에 해당한다. 이 값들은 특정 타임존과 결합되지 않은 채로 의미가 있다.

실무에서 헷갈리는 케이스는 예약 도메인이다. 사용자가 "2026-08-01 오전 10시"에 예약을 잡을 때, 이 값을 `Instant`로 저장하려면 어느 타임존인지 알아야 한다. 서울 사용자라면 UTC 01:00이지만, 뉴욕 사용자라면 UTC 14:00이다. 타임존 정보 없이 `Instant`로 변환하면 나중에 원래 사용자 의도를 복원할 수 없다. 이런 경우는 `LocalDateTime` + 타임존 ID를 분리 저장하거나 `ZonedDateTime`을 쓴다.

## OffsetDateTime, ZonedDateTime과의 관계

실무에서 쓰는 Java 날짜·시간 타입은 네 가지다.

- `Instant`: UTC 기준 절대 시점. 타임존·오프셋 없음.
- `LocalDateTime`: 타임존 없는 달력 값.
- `OffsetDateTime`: LocalDateTime + UTC 오프셋(`+09:00`). 어느 오프셋인지는 알지만 타임존 ID(`Asia/Seoul`)는 없다.
- `ZonedDateTime`: LocalDateTime + 타임존 ID + 오프셋. DST 규칙까지 포함한 가장 완전한 표현.

`Instant`는 `ZonedDateTime`으로 변환 가능하고, `ZonedDateTime`에서 `Instant`를 꺼낼 수 있다. 같은 물리적 순간이므로 정보 손실이 없다.

```java
Instant instant = Instant.now();
ZonedDateTime seoulTime = instant.atZone(ZoneId.of("Asia/Seoul"));
Instant backToInstant = seoulTime.toInstant(); // 동일한 값
```

`OffsetDateTime`과 `Instant` 사이도 상호 변환이 가능하다. 오프셋 정보가 있으면 UTC 기준 절대 시점을 계산할 수 있기 때문이다.

```java
OffsetDateTime odt = OffsetDateTime.now(ZoneOffset.of("+09:00"));
Instant i = odt.toInstant();
```

`LocalDateTime`에서 `Instant`로 바로 변환하는 것은 불가능하다. 반드시 오프셋이나 타임존을 주입해야 한다.

```java
LocalDateTime ldt = LocalDateTime.of(2026, 7, 31, 18, 0);
// ldt.toInstant() -- 컴파일 에러

Instant i = ldt.toInstant(ZoneOffset.of("+09:00")); // 오프셋 주입 필요
```

`ZonedDateTime`이 `OffsetDateTime`보다 필요한 상황은 DST가 있는 타임존을 다룰 때다. `+04:00`이라는 오프셋은 어느 타임존인지 모른다. `America/New_York`은 DST 전환 규칙을 알고 있어서 여름엔 `-04:00`, 겨울엔 `-05:00`을 자동으로 적용한다.

## JPA/Hibernate 매핑 버그 패턴

### LocalDateTime + JDBC 타임존 변환 문제

`LocalDateTime`을 `DATETIME` 컬럼에 매핑할 때, Hibernate는 JDBC 레벨에서 `PreparedStatement.setTimestamp()`를 쓴다. 이 메서드는 JVM 기본 타임존을 기준으로 값을 변환한다.

서버 JVM 타임존이 UTC이면 `2026-07-31T18:00:00`을 그대로 DB에 넣는다. 그런데 JVM 타임존이 KST(UTC+9)인 서버에서는 같은 `LocalDateTime` 값이 UTC 기준으로 처리되면서 실제로 저장되는 값이 달라지는 경우가 있다. Hibernate 버전과 JDBC 드라이버 조합에 따라 동작이 다르다.

이를 피하려면 Hibernate 설정에 JDBC 타임존을 명시한다.

```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          time_zone: UTC
```

이 설정이 없으면 `Instant`를 써도 JVM 타임존에 따라 저장값이 달라질 수 있다.

### @CreationTimestamp와 LocalDateTime 조합

```java
@CreationTimestamp
@Column(name = "created_at")
private LocalDateTime createdAt;
```

이 패턴은 서버 JVM 타임존 기준 현재 시각을 저장한다. JVM이 KST면 KST 기준 현재 시각이 들어간다. 나중에 JVM 타임존이 UTC로 변경되면 이전 데이터는 KST, 이후 데이터는 UTC이지만 컬럼만 봐서는 구분할 수 없다. 마이그레이션 때 반드시 문제가 된다.

```java
@CreationTimestamp
@Column(name = "created_at")
private Instant createdAt; // Hibernate가 UTC epoch 값을 저장
```

### MySQL DATETIME + Hibernate + LocalDateTime

MySQL `DATETIME` 컬럼을 `LocalDateTime`으로 매핑하고 JVM 타임존이 UTC가 아닌 경우, 저장과 조회 시 값이 달라지는 버그가 생긴다. 저장 시점에 JVM 타임존 변환이 일어나고, 조회 시에 다시 변환이 일어나 값이 두 번 변환되는 경우가 있다.

`hibernate.jdbc.time_zone=UTC`를 설정해도 `LocalDateTime`은 오프셋 정보가 없어서 Hibernate가 올바르게 처리하지 못하는 케이스가 있다. 새 테이블을 설계할 때 `Instant`로 선언하고 DB 컬럼도 `DATETIME` 대신 MySQL `DATETIME(6)` + 애플리케이션 UTC 보장 조합을 쓰거나, PostgreSQL이면 `TIMESTAMPTZ`에 매핑한다.

Hibernate 6.x부터는 `Instant`, `OffsetDateTime`을 직접 지원하고 JDBC 레벨 변환을 더 일관되게 처리한다. 레거시 프로젝트에서 `LocalDateTime`으로 저장하던 컬럼을 `Instant`로 전환할 때는 기존 데이터가 어느 타임존 기준이었는지 먼저 파악해야 한다.

### PostgreSQL TIMESTAMP WITHOUT TIME ZONE + OffsetDateTime 조합

PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` 컬럼에 `OffsetDateTime`을 저장하려 하면 드라이버가 오류를 낸다. `OffsetDateTime`은 오프셋 정보를 갖고 있는데, `TIMESTAMP WITHOUT TIME ZONE`은 오프셋을 저장할 수 없어서다.

매핑 조합을 맞춰야 한다.

- `TIMESTAMPTZ` + `Instant` 또는 `OffsetDateTime`
- `TIMESTAMP WITHOUT TIME ZONE` + `LocalDateTime`

타입을 섞으면 드라이버 오류나 의도치 않은 데이터 손실이 생긴다.

## TypeScript Date와의 대응

JavaScript/TypeScript의 `Date` 객체는 내부적으로 UTC 기준 밀리초 타임스탬프를 갖는다. 이 점에서 Java의 `Instant`에 대응한다.

```typescript
const d = new Date('2026-07-31T09:00:00Z'); // UTC 기준
d.getTime(); // 밀리초 epoch 값
```

Java `LocalDateTime`에 직접 대응하는 TypeScript 타입은 없다. `Date`는 항상 절대 시점을 갖는다. "타임존 없는 달력 값"을 표현하려면 문자열(`"2026-07-31T18:00:00"`)로 다루거나, Temporal API의 `PlainDateTime`을 써야 한다.

Temporal API(Node.js 21+ 실험적 지원):

```typescript
// Instant에 대응
const instant = Temporal.Instant.fromEpochMilliseconds(Date.now());

// LocalDateTime에 대응 — 타임존 없음
const plain = Temporal.PlainDateTime.from('2026-07-31T18:00:00');

// ZonedDateTime에 대응
const zoned = plain.toZonedDateTime('Asia/Seoul');
```

Temporal API를 쓸 수 없는 환경에서는 `luxon`의 `DateTime`이 Java `ZonedDateTime`과 가장 유사하게 동작한다. 타임존을 내부에 갖고 있고, DST 전환도 처리한다.

```typescript
import { DateTime } from 'luxon';

// ZonedDateTime처럼
const seoulTime = DateTime.now().setZone('Asia/Seoul');
seoulTime.toISO(); // "2026-07-31T18:00:00.000+09:00"

// Instant에서 변환
const fromUtc = DateTime.fromISO('2026-07-31T09:00:00Z');
fromUtc.setZone('Asia/Seoul').toISO(); // "2026-07-31T18:00:00.000+09:00"
```

`moment`는 새 프로젝트에서 쓰지 않는다. 유지보수가 사실상 종료됐고, DST 처리 예측 가능성도 `luxon`보다 낮다.

## API 레이어 타입 혼용 오류

### 요청 파싱 시 타임존 소실

API 요청에서 `"2026-07-31T18:00:00"` 같은 타임존 없는 문자열을 `LocalDateTime`으로 파싱하면 어느 타임존인지 정보가 사라진다.

```java
// 요청 바디: { "scheduledAt": "2026-07-31T18:00:00" }

public void schedule(@RequestBody ScheduleRequest req) {
    LocalDateTime scheduledAt = req.getScheduledAt();
    // KST인지 UTC인지 알 수 없는 상태
    service.schedule(scheduledAt.toInstant(ZoneOffset.UTC)); // 가정이 틀릴 수 있음
}
```

클라이언트가 `"2026-07-31T18:00:00+09:00"` 형식으로 오프셋을 포함해 보내거나, 별도 `timezone` 파라미터를 요청 스펙에 추가해야 한다.

```java
// OffsetDateTime으로 받으면 오프셋 정보 보존
public void schedule(@RequestBody ScheduleRequest req) {
    OffsetDateTime scheduledAt = req.getScheduledAt(); // "2026-07-31T18:00:00+09:00"
    Instant instant = scheduledAt.toInstant();
    service.schedule(instant);
}
```

### 응답에서 Instant를 LocalDateTime으로 변환 후 반환

DB에서 `Instant`로 꺼낸 값을 응답 DTO에서 `LocalDateTime`으로 변환하면 타임존 정보가 날아간다.

```java
// 잘못된 패턴
public OrderResponse build(Order order) {
    return OrderResponse.builder()
        .createdAt(LocalDateTime.ofInstant(order.getCreatedAt(), ZoneId.of("Asia/Seoul")))
        // 결과: "2026-07-31T18:00:00" — 타임존 정보 없음
        .build();
}
```

클라이언트가 이 값을 받아 다시 서버로 보내면 타임존을 알 수 없다. ISO 8601 오프셋 포함 형식으로 반환해야 한다.

```java
public OrderResponse build(Order order, ZoneId userZone) {
    ZonedDateTime localTime = order.getCreatedAt().atZone(userZone);
    return OrderResponse.builder()
        .createdAt(localTime.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME))
        // "2026-07-31T18:00:00+09:00"
        .build();
}
```

### Jackson 직렬화 기본값

Jackson 기본 설정에서 `Instant`는 `[1753955200, 0]` 같은 배열로 직렬화된다. `JavaTimeModule`을 등록해도 `WRITE_DATES_AS_TIMESTAMPS`가 `true`로 남아 있으면 숫자로 나온다.

```java
objectMapper.registerModule(new JavaTimeModule());
objectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
```

설정 없이 `Instant`를 JSON으로 응답하면 프론트엔드에서 숫자를 받게 되고, 밀리초인지 초인지 혼동이 생긴다. JavaScript `Date` 생성자는 밀리초를 받는데, Java `Instant.getEpochSecond()`는 초 단위 값을 반환한다. 서로 다른 팀이 API를 쓸 때 이 차이로 인해 시각이 1000배 차이 나는 버그가 생긴다.

`LocalDateTime`을 Jackson으로 직렬화하면 `"2026-07-31T18:00:00"` 형식으로 나온다. 타임존 정보가 없어서 클라이언트가 UTC로 처리할지 로컬 타임으로 처리할지 결정할 수 없다. API 응답에서 `LocalDateTime`을 그대로 직렬화하는 패턴은 거의 항상 버그를 내포한다.
