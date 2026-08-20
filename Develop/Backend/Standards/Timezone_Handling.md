---
title: 타임존 처리
tags: [backend]
updated: 2026-07-31
---

# 타임존 처리

## UTC 저장 원칙

DB에는 UTC만 저장한다. 이 원칙을 어기면 서비스가 여러 지역으로 확장될 때 반드시 문제가 생긴다.

KST(UTC+9)로 저장된 `created_at`을 갖는 테이블이 있다고 가정하자. 처음엔 국내 서비스라 아무 문제가 없다. 미국 리전을 추가하는 순간, 기존 데이터는 KST인지 UTC인지 컬럼만 봐서는 알 수 없다. 메타데이터나 코드 히스토리를 뒤져야 한다.

UTC 기준 저장을 지키는 것보다 깨진 데이터를 마이그레이션하는 비용이 훨씬 크다. 수백만 건 이상의 테이블에서 타임존 정보가 잘못된 경우, 어느 시점 이전 데이터가 KST이고 이후가 UTC인지 특정하는 작업 자체가 프로젝트가 된다.

## DB 컬럼 타입 선택

### MySQL: TIMESTAMP vs DATETIME

| | TIMESTAMP | DATETIME |
|---|---|---|
| 저장 범위 | 1970-01-01 ~ 2038-01-19 | 1000-01-01 ~ 9999-12-31 |
| 타임존 변환 | 저장 시 UTC 변환, 조회 시 세션 타임존 적용 | 입력값 그대로 저장 |
| 저장 용량 | 4바이트 | 8바이트 |

`TIMESTAMP`는 저장 시 세션 타임존 기준으로 UTC로 변환하고, 조회 시 다시 세션 타임존으로 변환해서 반환한다. 세션 타임존이 바뀌면 조회 결과도 바뀐다. 의도한 동작처럼 보이지만 함정이 있다.

```sql
-- 세션 타임존이 KST일 때 저장
SET time_zone = '+09:00';
INSERT INTO orders (created_at) VALUES ('2024-03-15 18:00:00'); -- KST 18:00 = UTC 09:00

-- 세션 타임존을 UTC로 변경하면 같은 row가 다르게 보임
SET time_zone = '+00:00';
SELECT created_at FROM orders; -- 2024-03-15 09:00:00 반환
```

Hibernate가 `TIMESTAMP` 컬럼을 읽을 때 세션 타임존 기준으로 변환하는데, 애플리케이션 타임존과 DB 세션 타임존이 다르면 저장/조회 시 변환이 두 번 일어난다. `serverTimezone=UTC`와 JVM `-Duser.timezone=UTC`를 함께 맞춰야 한다.

`DATETIME`은 타임존 변환 없이 입력값을 그대로 저장한다. 애플리케이션에서 UTC `Instant`를 `LocalDateTime`으로 변환한 뒤 저장하고, 꺼낼 때도 UTC 기준의 `LocalDateTime`으로 취급하면 된다. 2038년 제한이 없어서 서비스 만료일, 라이선스 기간 같은 먼 미래 날짜는 `DATETIME`으로 저장하는 경우도 있다.

신규 테이블이라면 `DATETIME` + 애플리케이션 레벨 UTC 보장 조합이 더 예측 가능하다. `TIMESTAMP`의 자동 변환은 세션 설정에 의존하기 때문에 환경이 달라질 때 숨겨진 버그가 생길 수 있다.

### PostgreSQL: TIMESTAMPTZ vs TIMESTAMP

PostgreSQL의 `TIMESTAMPTZ`(`TIMESTAMP WITH TIME ZONE`)는 이름과 다르게 타임존 정보를 컬럼에 저장하지 않는다. 입력값을 UTC로 변환해 저장하고, 조회 시 클라이언트 세션의 `TimeZone` 파라미터에 따라 변환해서 반환한다.

`TIMESTAMP WITHOUT TIME ZONE`은 입력값을 변환 없이 숫자로 저장한다. 어느 타임존 기준인지는 애플리케이션이 알아야 한다.

```sql
-- TIMESTAMPTZ: 세션 타임존 영향 받음
SET TIME ZONE 'Asia/Seoul';
SELECT now(); -- 2024-03-15 18:30:00+09

SET TIME ZONE 'UTC';
SELECT now(); -- 2024-03-15 09:30:00+00

-- TIMESTAMP WITHOUT TIME ZONE: 세션 타임존 무관, 저장된 값 그대로
SELECT created_at FROM events; -- 세션과 무관하게 항상 같은 값
```

PostgreSQL에서 시간 데이터는 `TIMESTAMPTZ`를 쓰는 게 낫다. JDBC 드라이버와 JPA가 `TIMESTAMPTZ`를 `Instant`로 올바르게 매핑해서 애플리케이션 레이어에서 별도 변환 없이 UTC 기준으로 다룰 수 있다.

## API 입출력 변환 시점

변환은 한 지점에서만 해야 한다. 여러 레이어에서 각각 변환하면 이중 변환이 생긴다.

```
DB 조회 → 서비스 레이어(UTC 상태 유지) → 응답 직전 로컬 타임으로 변환
```

서비스 레이어 내부에서는 UTC로만 계산한다. "오늘 오전 9시 이후 주문"을 조회할 때 사용자 로컬 타임을 UTC로 변환해서 쿼리 파라미터로 넘긴다. DB에서 가져온 UTC datetime을 서비스 내부에서 바로 KST로 바꿔서 비즈니스 로직에 쓰면 안 된다.

응답 시점에 변환하는 예시:

```java
String userTimezone = request.getHeader("X-Timezone"); // "Asia/Seoul"
ZoneId zoneId = ZoneId.of(userTimezone);

Instant createdAtUtc = order.getCreatedAt(); // Instant 타입 (UTC)

ZonedDateTime localTime = createdAtUtc.atZone(zoneId);
response.setCreatedAt(localTime.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
```

서비스 레이어 내부에서 `ZonedDateTime`이나 `LocalDateTime`으로 변환하지 말고 `Instant`를 그대로 들고 다닌다. 비즈니스 로직에서 "3일 후"를 계산할 때도 `Instant`나 `OffsetDateTime`을 쓴다.

### ISO 8601 형식

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

유닉스 타임스탬프는 밀리초인지 초인지 헷갈린다. JavaScript `Date.parse()`는 밀리초를 받는데, Python에서 유닉스 타임을 생성하면 초 단위라 1000 곱하는 것을 잊는 경우가 있다.

Jackson에서 `Instant`를 ISO 8601로 직렬화하는 설정:

```java
objectMapper.configure(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);
objectMapper.registerModule(new JavaTimeModule());
```

기본 설정을 건드리지 않으면 `Instant`가 `[1710494400, 0]` 같은 배열로 직렬화된다. 프론트엔드에서 파싱 못 한다고 버그 리포트 올 때까지 모르는 경우가 많다.

### 날짜 경계 계산

"오늘 주문 내역"을 조회할 때 "오늘"이 누구 기준인지가 핵심이다. UTC 기준 "오늘"은 한국 사용자에게 어제일 수 있다.

```java
ZoneId userZone = ZoneId.of("America/Los_Angeles");
LocalDate today = LocalDate.now(userZone);

Instant startOfDay = today.atStartOfDay(userZone).toInstant();
Instant endOfDay = today.plusDays(1).atStartOfDay(userZone).toInstant();

orderRepository.findByCreatedAtBetween(startOfDay, endOfDay);
```

이 계산을 서비스 레이어에서 수행하고, 쿼리 파라미터는 항상 UTC `Instant`로 넘긴다. DB에서 가져온 UTC를 조회 레이어에서 바로 로컬 타임으로 바꿔서 서비스에 넘기면 날짜 범위 계산이 꼬인다.

### 타임존 헤더 검증

헤더 값을 그대로 `ZoneId.of()`에 넘기면 클라이언트가 잘못된 타임존 ID를 보냈을 때 `DateTimeException`이 발생한다.

```java
String tzHeader = request.getHeader("X-Timezone");
ZoneId userZone;
try {
    userZone = ZoneId.of(tzHeader != null ? tzHeader : "UTC");
} catch (DateTimeException e) {
    userZone = ZoneId.of("UTC");
}
```

## JVM 프로세스 타임존 설정

JVM 기본 타임존은 OS 설정을 따른다. 서버 OS가 KST로 설정돼 있으면 `LocalDateTime.now()`가 KST 기준으로 동작한다. 개발 환경(Mac, UTC+9)과 운영 환경(리눅스, UTC)이 다를 때 로컬에선 잘 되던 코드가 운영에서 깨진다.

JVM 프로세스 시작 시 타임존을 명시적으로 설정한다:

```bash
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

MySQL JDBC URL에 `serverTimezone=UTC`를 명시하지 않으면 서버 OS의 타임존을 따른다.

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

타임존 처리가 필요하면 `date-fns-tz` 나 `luxon` 같은 라이브러리를 쓴다. `Temporal` 은 아직 표준 제안 단계라 **Node 24 기준으로도 `--harmony-temporal` 플래그 없이는 전역에 없다**(v18·20·22·24 에서 모두 `undefined` 실측). 플래그를 붙여야 비로소 나타난다. `moment-timezone`은 번들 크기가 크고 유지보수가 사실상 종료된 상태라 새 프로젝트엔 쓰지 않는다.

```typescript
import { formatInTimeZone } from 'date-fns-tz';

const utcDate = new Date('2024-03-15T09:30:00Z');
const formatted = formatInTimeZone(utcDate, 'Asia/Seoul', "yyyy-MM-dd'T'HH:mm:ssxxx");
// "2024-03-15T18:30:00+09:00"
```

## 다중 서버 환경에서의 타임존 불일치 트러블슈팅

서버가 여러 대일 때 각 서버의 타임존 설정이 다르면 로그 분석, 배치 결과, 데이터 정합성에서 문제가 생긴다.

### 증상: 로그 타임스탬프가 서버마다 다름

여러 인스턴스에서 로그를 수집할 때 서버 A는 UTC, 서버 B는 KST로 설정된 경우 같은 시각 이벤트가 9시간 차이로 기록된다. Kibana나 Grafana에서 이벤트 순서가 뒤섞인다.

진단:

```bash
# 각 서버에서 실행해 타임존 설정 확인
date
timedatectl

# JVM 프로세스 타임존 확인 (start 인자에서 -Duser.timezone 여부)
ps aux | grep java

# 환경변수 TZ 확인
printenv TZ
```

서버 인스턴스 간 타임존이 다른 경우 보통 AMI 기반 인스턴스를 특정 리전에서 생성했거나, 컨테이너 이미지의 베이스 이미지가 서로 다를 때 발생한다. 인프라 레벨에서 강제로 통일한다.

```bash
# Amazon Linux 2 / Ubuntu 타임존 설정
sudo timedatectl set-timezone UTC

# Dockerfile에서 명시적 설정
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo UTC > /etc/timezone
ENV TZ=UTC
```

Kubernetes 환경이면 Pod spec에 환경변수를 추가한다.

```yaml
env:
  - name: TZ
    value: "UTC"
  - name: JAVA_OPTS
    value: "-Duser.timezone=UTC"
```

### 증상: 배치가 예상 시간에 실행되지 않음

Spring Batch나 Quartz 스케줄러가 특정 서버에서만 다른 시간에 실행될 때, JVM 타임존이 서버마다 다른 경우다. Quartz 크론 표현식 `0 0 2 * * ?`는 JVM 기본 타임존 기준 오전 2시를 의미한다. 서버 A는 UTC 02:00, 서버 B는 KST 02:00(= UTC 17:00)에 실행된다.

```java
CronTrigger trigger = TriggerBuilder.newTrigger()
    .withSchedule(CronScheduleBuilder
        .cronSchedule("0 0 2 * * ?")
        .inTimeZone(TimeZone.getTimeZone("UTC"))) // 반드시 명시
    .build();
```

크론 표현식에 타임존을 명시하지 않으면 JVM 타임존에 따라 실행 시각이 바뀐다.

### 증상: DB 저장 시간과 애플리케이션 로그 시간이 9시간 차이남

MySQL `TIMESTAMP` 컬럼에 저장된 시간이 애플리케이션 로그와 9시간 차이 나는 경우, JDBC 세션 타임존과 JVM 타임존이 불일치하는 상황이다.

```sql
-- MySQL에서 현재 세션 타임존 확인
SELECT @@session.time_zone;
SELECT @@global.time_zone;
```

세션 타임존이 `SYSTEM`으로 설정돼 있으면 MySQL 서버 OS의 타임존을 따른다. MySQL 서버가 KST로 설정된 서버에 올라가 있으면 `SYSTEM`은 KST다.

JDBC URL에 `serverTimezone=UTC`를 명시해도 해결되지 않는 경우, MySQL 8.x와 Connector/J 버전 조합에 따라 `useLegacyDatetimeCode=false`를 함께 써야 한다.

```
jdbc:mysql://host:3306/db?serverTimezone=UTC&useLegacyDatetimeCode=false&useUnicode=true&characterEncoding=UTF-8
```

### 커넥션 풀에서 세션 타임존 강제

HikariCP 같은 커넥션 풀을 쓸 때, 커넥션 획득 시점에 세션 타임존을 강제로 설정할 수 있다.

```yaml
spring:
  datasource:
    hikari:
      connection-init-sql: "SET time_zone='+00:00'"
```

이렇게 하면 JDBC URL의 `serverTimezone` 설정과 무관하게 커넥션마다 세션 타임존이 UTC로 초기화된다. MySQL 레플리케이션 환경에서 마스터와 레플리카의 글로벌 타임존이 다를 때 가장 확실한 해결책이다.

## DST 전환 시 발생하는 버그 패턴

한국은 DST를 쓰지 않아 국내 서비스에선 DST 버그를 경험하기 어렵다. 미국, 유럽 사용자가 있는 서비스에선 반드시 테스트해야 한다.

DST 전환 타이밍(미국 동부 기준):
- 봄: 2시 → 3시로 점프 (2시~3시 사이 시간이 존재하지 않음)
- 가을: 2시 → 1시로 되돌아감 (1시~2시 사이 시간이 두 번 존재)

**"매일 오전 2시에 배치 실행" 패턴**

봄에 DST 전환이 되는 날, `America/New_York` 기준으로 "02:00"을 스케줄링하면 그 시간 자체가 존재하지 않는다. 스케줄러 구현에 따라 건너뛰거나, 에러를 내거나, 1시간 늦게 실행된다. UTC 기준으로 스케줄링하면 이 문제가 없다.

**"가을 새벽 1:30분" 중복 처리 문제**

가을 전환 시 1:00~1:59 구간이 두 번 나타난다. EST(UTC-5)와 EDT(UTC-4) 양쪽 모두 1:30 AM이 생긴다. 이 시간대에 들어온 주문의 타임스탬프를 로컬 타임으로만 저장했다면 "2024-11-03T01:30:00"가 두 건이 생기고, 어느 것이 먼저인지 알 수 없다. UTC로 저장하면 두 건의 UTC 타임스탬프는 각각 다른 값이 된다.

**오프셋 vs 타임존 ID**

`+09:00`은 오프셋이고, `Asia/Seoul`은 타임존 ID다. 오프셋은 DST 정보를 담지 않는다. `America/New_York`은 여름엔 `-04:00`, 겨울엔 `-05:00`이다. API 요청에서 사용자 타임존을 `+09:00` 같은 오프셋만 받으면 DST 변환을 적용할 수 없다. 타임존 ID를 받아야 DST 전환 시점에 올바른 오프셋을 계산할 수 있다.

```java
// 오프셋만 있으면 DST 적용 불가
ZoneOffset offset = ZoneOffset.of("+04:00"); // 어느 타임존인지 모름

// 타임존 ID가 있어야 DST 처리 가능
ZoneId zoneId = ZoneId.of("America/New_York");
ZonedDateTime zdt = ZonedDateTime.of(localDateTime, zoneId);
```

## 사용자 프로파일에 타임존 저장

가입 시 선택하거나, IP 기반으로 자동 설정한다. DB에 `timezone VARCHAR(64)` 컬럼으로 `Asia/Seoul` 같은 IANA 타임존 ID를 저장한다.

```java
// 인증 필터에서 타임존 컨텍스트 설정
String timezone = userProfile.getTimezone(); // "Europe/London"
ZoneId userZone = ZoneId.of(timezone);
RequestContext.setUserZone(userZone);

// 응답 직렬화 시 사용
ZonedDateTime localTime = event.getStartTime().atZone(RequestContext.getUserZone());
```

모바일 앱이나 SPA에서 클라이언트가 `X-Timezone: America/Chicago` 헤더를 보내는 방식도 있다. 서버가 사용자 타임존 상태를 관리할 필요가 없다. 헤더가 없을 때 기본값(UTC)으로 처리하거나 400 오류를 반환한다.
