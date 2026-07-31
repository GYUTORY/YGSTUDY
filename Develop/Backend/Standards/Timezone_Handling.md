---
title: 타임존 처리
tags: [timezone, utc, dst, iso8601, datetime, backend]
updated: 2026-07-31
---

# 타임존 처리

## UTC 저장 원칙

DB에는 UTC만 저장한다. 이 원칙을 어기면 서비스가 여러 지역으로 확장될 때 반드시 문제가 생긴다.

KST(UTC+9)로 저장된 `created_at`을 갖는 테이블이 있다고 가정하자. 처음엔 국내 서비스라 아무 문제가 없다. 미국 리전을 추가하는 순간, 기존 데이터는 KST인지 UTC인지 컬럼만 봐서는 알 수 없다. 메타데이터나 코드 히스토리를 뒤져야 한다.

MySQL의 `DATETIME` 타입은 타임존 정보를 저장하지 않는다. 애플리케이션이 KST datetime 객체를 그대로 삽입하면 DB엔 KST 값이 들어가지만, 나중에 읽어서 UTC로 해석하면 9시간 차이가 발생한다. `TIMESTAMP` 타입은 내부적으로 UTC로 변환해서 저장하지만, `@@session.time_zone` 설정에 따라 조회 결과가 달라진다. 이 차이를 모르고 쓰다가 `DATETIME`과 `TIMESTAMP` 컬럼을 혼용하면 시간 계산이 완전히 틀어진다.

PostgreSQL의 `TIMESTAMPTZ`는 타임존 offset을 함께 저장하지 않고, UTC로 변환해서 저장한다. `TIMESTAMP WITHOUT TIME ZONE`은 그냥 숫자만 저장한다. PostgreSQL을 쓴다면 시간 데이터엔 무조건 `TIMESTAMPTZ`를 쓰는 게 낫다.

## 변환 시점 설계: DB → 서비스 → 응답

변환은 한 지점에서만 해야 한다. 여러 레이어에서 각각 변환하면 이중 변환이 생긴다.

```
DB 조회 → 서비스 레이어(UTC 상태 유지) → 응답 직전 로컬 타임으로 변환
```

서비스 레이어 내부에서는 UTC로만 계산한다. "오늘 오전 9시 이후 주문"을 조회할 때 사용자 로컬 타임을 UTC로 변환해서 쿼리 파라미터로 넘긴다. 반대로 DB에서 가져온 UTC datetime을 서비스 내부에서 바로 KST로 바꿔서 비즈니스 로직에 쓰면 안 된다.

응답 시점에 변환하는 예시:

```java
// 사용자 요청에서 타임존 정보 추출
String userTimezone = request.getHeader("X-Timezone"); // "Asia/Seoul"
ZoneId zoneId = ZoneId.of(userTimezone);

// DB에서 조회한 UTC 시간
Instant createdAtUtc = order.getCreatedAt(); // Instant 타입 (UTC)

// 응답 직전에만 변환
ZonedDateTime localTime = createdAtUtc.atZone(zoneId);
response.setCreatedAt(localTime.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
```

서비스 레이어 내부에서 `ZonedDateTime`이나 `LocalDateTime`으로 변환하지 말고 `Instant`를 그대로 들고 다닌다. 비즈니스 로직에서 "3일 후"를 계산할 때도 `Instant`나 `OffsetDateTime`을 쓴다.

## ISO 8601 형식 강제

API 응답의 날짜·시간 필드는 반드시 ISO 8601 형식을 쓴다.

```
# 올바른 형식
2024-03-15T09:30:00Z          # UTC
2024-03-15T18:30:00+09:00     # KST (오프셋 포함)
2024-03-15T09:30:00.123Z      # 밀리초 포함

# 쓰면 안 되는 형식
2024-03-15 09:30:00           # 타임존 정보 없음
2024/03/15 09:30:00           # ISO 형식 아님
1710494400                    # 유닉스 타임스탬프 단독 사용
```

유닉스 타임스탬프는 사람이 읽기 어렵고, 밀리초인지 초인지 헷갈린다. JavaScript에서 `Date.parse()`는 밀리초 타임스탬프를 받는데, Python에서 유닉스 타임을 생성하면 초 단위라 1000 곱하는 것을 잊는 경우가 있다. ISO 8601 문자열로 통일하면 이런 혼란이 없다.

Jackson (Java)에서 `Instant`를 ISO 8601로 직렬화하는 설정:

```java
@JsonSerialize(using = InstantSerializer.class)
// 또는 ObjectMapper 전역 설정
objectMapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
objectMapper.registerModule(new JavaTimeModule());
```

기본 설정을 건드리지 않으면 `Instant`가 `[1710494400, 0]` 같은 배열로 직렬화된다. 프론트엔드에서 파싱 못 한다고 버그 리포트 올 때까지 모르는 경우가 많다.

## JVM 프로세스 타임존 설정

JVM 기본 타임존은 OS 설정을 따른다. 서버 OS가 KST로 설정돼 있으면 `LocalDateTime.now()`가 KST 기준으로 동작한다. 개발 환경(Mac, UTC+9)과 운영 환경(리눅스, UTC)이 다를 때 로컬에선 잘 되던 코드가 운영에서 깨진다.

JVM 프로세스 시작 시 타임존을 명시적으로 설정한다:

```bash
# JVM 옵션
-Duser.timezone=UTC

# 또는 환경변수
TZ=UTC java -jar app.jar
```

코드 레벨에서도 방어적으로 설정할 수 있다:

```java
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
        SpringApplication.run(Application.class, args);
    }
}
```

DB 커넥션도 타임존을 맞춰야 한다. MySQL JDBC URL에 `serverTimezone=UTC`를 명시하지 않으면 서버 OS의 타임존을 따른다. Hibernate가 `TIMESTAMP` 컬럼을 읽을 때 세션 타임존 기준으로 변환하는데, 애플리케이션 타임존과 DB 세션 타임존이 다르면 저장/조회 시 변환이 두 번 일어난다.

```
spring.datasource.url=jdbc:mysql://host:3306/db?serverTimezone=UTC&useLegacyDatetimeCode=false
```

## Node.js 프로세스 타임존

Node.js는 환경변수 `TZ`로 타임존을 설정한다. 코드 내에서 변경하는 방법은 공식적으로 지원하지 않는다.

```bash
TZ=UTC node server.js

# Docker 환경
ENV TZ=UTC
```

`new Date()`는 항상 UTC 기반 유닉스 타임스탬프를 갖지만, `toString()`이나 `toLocaleString()` 같은 출력 메서드는 로컬 타임존을 따른다. `TZ=UTC`로 설정하지 않은 상태에서 `new Date().toString()`을 로그에 찍으면 서버 OS 타임존 기준으로 출력된다.

타임존 처리가 필요하면 `Temporal` API(Node.js 21+)나 `date-fns-tz`, `luxon` 같은 라이브러리를 쓴다. `moment-timezone`은 번들 크기가 크고 유지보수가 사실상 종료된 상태라 새 프로젝트엔 쓰지 않는다.

```typescript
import { formatInTimeZone } from 'date-fns-tz';

// DB에서 가져온 UTC Date 객체
const utcDate = new Date('2024-03-15T09:30:00Z');

// 사용자 타임존으로 변환해서 응답
const formatted = formatInTimeZone(utcDate, 'Asia/Seoul', "yyyy-MM-dd'T'HH:mm:ssxxx");
// "2024-03-15T18:30:00+09:00"
```

## DST 전환 시 발생하는 버그 패턴

한국은 DST를 쓰지 않아 국내 서비스에선 DST 버그를 경험하기 어렵다. 미국, 유럽 사용자가 있는 서비스에선 반드시 테스트해야 한다.

DST 전환이 일어나는 대표적인 타이밍(미국 동부 기준):
- 봄: 2시 → 3시로 점프 (2시~3시 사이 시간이 존재하지 않음)
- 가을: 2시 → 1시로 되돌아감 (1시~2시 사이 시간이 두 번 존재)

**"매일 오전 2시에 배치 실행" 패턴**

봄에 DST 전환이 되는 날, `America/New_York` 기준으로 "02:00"을 스케줄링하면 그 시간 자체가 존재하지 않는다. 스케줄러 구현에 따라 건너뛰거나, 에러를 내거나, 1시간 늦게 실행된다.

이 문제는 UTC 기준으로 스케줄링하면 해결된다. 로컬 타임이 아니라 UTC 크론 표현식을 쓴다.

**"가을 새벽 1:30분" 중복 처리 문제**

가을 전환 시 1:00~1:59 구간이 두 번 나타난다. EST(UTC-5)와 EDT(UTC-4) 양쪽 모두 1:30 AM이 생긴다. 이 시간대에 들어온 주문의 타임스탬프를 로컬 타임으로만 저장했다면 "2024-11-03T01:30:00"가 두 건이 생긴다. 어느 것이 먼저인지 알 수 없다.

UTC 저장이 이 문제를 해결한다. 두 건의 UTC 타임스탬프는 각각 다른 값이 된다.

**오프셋 vs 타임존 ID**

`+09:00`은 오프셋이고, `Asia/Seoul`은 타임존 ID다. 오프셋은 DST 정보를 담지 않는다. `America/New_York`은 여름엔 `-04:00`, 겨울엔 `-05:00`이다. API 요청에서 사용자 타임존을 받을 때 `+09:00` 같은 오프셋만 받으면 DST 변환을 적용할 수 없다. 타임존 ID를 받아야 DST 전환 시점에 올바른 오프셋을 계산할 수 있다.

```java
// 오프셋만 있으면 DST 적용 불가
ZoneOffset offset = ZoneOffset.of("+04:00"); // 어느 타임존인지 모름

// 타임존 ID가 있어야 DST 처리 가능
ZoneId zoneId = ZoneId.of("America/New_York");
ZonedDateTime zdt = ZonedDateTime.of(localDateTime, zoneId);
// ZonedDateTime이 자동으로 DST 오프셋을 적용
```

## 다국가 서비스에서 로컬 타임 변환 시점 설계

사용자 로컬 타임으로의 변환은 응답 레이어에서만 한다. 변환 기준이 되는 타임존 정보는 어디서 가져오는지에 따라 설계가 달라진다.

**사용자 프로파일에 타임존 저장**

가입 시 선택하거나, IP 기반으로 자동 설정한다. DB에 `timezone VARCHAR(64)` 컬럼으로 `Asia/Seoul` 같은 IANA 타임존 ID를 저장한다. 로그인한 사용자 요청이면 프로파일의 타임존을 쓴다.

```java
// 인증 필터에서 타임존 컨텍스트 설정
String timezone = userProfile.getTimezone(); // "Europe/London"
ZoneId userZone = ZoneId.of(timezone);
RequestContext.setUserZone(userZone);

// 응답 직렬화 시 사용
ZonedDateTime localTime = event.getStartTime().atZone(RequestContext.getUserZone());
```

**요청 헤더에서 타임존 수신**

모바일 앱이나 SPA에서 클라이언트가 `X-Timezone: America/Chicago` 헤더를 보내는 방식이다. 서버가 사용자 타임존 상태를 관리할 필요가 없다. 헤더가 없을 때 기본값(UTC)으로 처리하거나 400 오류를 반환한다.

헤더 값을 그대로 `ZoneId.of()`에 넘기면 클라이언트가 잘못된 타임존 ID를 보냈을 때 `DateTimeException`이 발생한다. 유효성 검사를 반드시 한다.

```java
String tzHeader = request.getHeader("X-Timezone");
ZoneId userZone;
try {
    userZone = ZoneId.of(tzHeader != null ? tzHeader : "UTC");
} catch (DateTimeException e) {
    userZone = ZoneId.of("UTC");
}
```

**날짜 경계 계산 문제**

"오늘 주문 내역"을 조회할 때 "오늘"이 누구 기준인지가 핵심이다. UTC 기준 "오늘"은 한국 사용자에게 어제일 수 있다.

```java
// 사용자 로컬 기준 오늘의 시작과 끝을 UTC로 변환
ZoneId userZone = ZoneId.of("America/Los_Angeles");
LocalDate today = LocalDate.now(userZone);

Instant startOfDay = today.atStartOfDay(userZone).toInstant();
Instant endOfDay = today.plusDays(1).atStartOfDay(userZone).toInstant();

// DB 쿼리는 UTC Instant 범위로
orderRepository.findByCreatedAtBetween(startOfDay, endOfDay);
```

이 계산을 서비스 레이어에서 수행하고, 쿼리 파라미터는 항상 UTC `Instant`로 넘긴다. 반대로 DB에서 가져온 UTC를 조회 레이어에서 바로 로컬 타임으로 바꿔서 서비스에 넘기면 날짜 범위 계산이 꼬인다.
