---
title: DST (일광 절약 시간)
tags: [backend, python]
updated: 2026-07-31
---

# DST (일광 절약 시간)

한국은 DST를 쓰지 않아 국내 서비스만 운영하면 평생 직접 안 만날 수도 있다. 미국이나 유럽 사용자가 생기는 순간 DST 버그가 한꺼번에 터진다. 이미 운영 중인 서비스에 미국 리전을 추가하거나 글로벌 확장을 하는 시점에서 레거시 코드에 DST 가정이 얼마나 많이 박혀 있는지 깨닫게 된다.

## DST 전환이 시스템에 미치는 영향

봄 전환(예: 미국 동부 EST → EDT)은 2:00 AM에 시계를 3:00 AM으로 앞당긴다. 2:00~2:59 구간이 통째로 사라진다. 가을 전환(EDT → EST)은 2:00 AM을 다시 1:00 AM으로 되돌린다. 1:00~1:59 구간이 두 번 존재한다.

이 두 현상이 서비스 레이어에서 각각 다른 종류의 버그를 만든다.

```
봄 전환 (2024-03-10, America/New_York)
  EST 1:59 AM (UTC 06:59) → EDT 3:00 AM (UTC 07:00)
  "2:00 AM ~ 2:59 AM"이 존재하지 않음

가을 전환 (2024-11-03, America/New_York)
  EDT 1:59 AM (UTC 05:59) → EST 1:00 AM (UTC 06:00)
  "1:00 AM ~ 1:59 AM"이 두 번 반복됨
```

## tzdata 업데이트와 정치적 DST 변경

tzdata는 IANA가 관리하는 타임존 데이터베이스다. 각 국가·지역이 DST 시작/종료 날짜, 오프셋 등을 법으로 정하고, 그 법이 바뀌면 tzdata가 업데이트된다. 운영 서버가 이 업데이트를 반영하지 않으면 올바른 IANA 타임존 ID를 써도 과거 규칙으로 계산한다.

실제로 문제가 생기는 패턴은 이렇다.

2023년 멕시코가 DST를 폐지했다. `America/Mexico_City` 기준으로 스케줄링된 배치가 있다면, tzdata를 업데이트하기 전까지 시스템은 계속 DST 전환을 적용한다. 배치 실행 시각이 1시간씩 어긋나는데 원인을 찾기 어렵다. 알림 발송 시각이 어긋나거나, 통계 집계 기준이 틀어지는 식으로 증상이 나타난다.

tzdata 업데이트 주기를 확인하는 방법:

```bash
# Linux
cat /usr/share/zoneinfo/+VERSION
# tzdata2024a 같은 형태로 버전 표시

# Ubuntu/Debian tzdata 패키지 버전 확인
dpkg -l tzdata

# Java의 경우 JVM 내장 tzdata 버전 확인
java -XshowSettings:all -version 2>&1 | grep timezone

# Python
python3 -c "from zoneinfo import ZoneInfo; import importlib.resources; print(importlib.resources.files('tzdata'))"
```

tzdata 정치적 변경이 생기는 경로가 두 가지라 둘 다 관리해야 한다. OS 레벨 tzdata와 런타임(JVM, Python, Node.js) 내장 tzdata가 분리돼 있다. JVM은 자체 tzdata를 갖고 있어서 OS tzdata를 업데이트해도 JVM은 그대로다. Java 8u161부터 `TZUpdater` 툴이나 `--patch-module` 방식으로 JVM tzdata를 별도 업데이트해야 한다.

```bash
# Oracle JDK TZUpdater
java -jar tzupdater.jar -u

# Amazon Corretto나 Eclipse Temurin는 배포판에서 직접 업데이트 패키지 제공
# 예: Amazon Corretto 업데이트 채널
yum update java-17-amazon-corretto-headless
```

자체 배포 Docker 이미지를 쓰는 환경에서는 이미지를 새로 빌드할 때까지 업데이트가 반영 안 된다. 베이스 이미지를 주기적으로 업데이트하거나, 이미지 빌드 시 tzdata 최신 버전 설치를 명시한다.

```dockerfile
FROM openjdk:21-slim
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=UTC
```

## 봄/가을 전환 시 스케줄러와 배치 처리

### 스케줄러

로컬 타임 기준으로 스케줄을 잡으면 봄 전환일에 실행 누락이 생기고, 가을 전환일에 이중 실행이 생길 수 있다.

"매일 오전 2:00 AM `America/New_York` 기준 실행"을 Quartz나 Spring Scheduler로 구현하면 봄 전환일에 2:00 AM 자체가 없어서 스케줄러마다 반응이 다르다. Quartz는 해당 트리거를 미스파이어(misfire)로 처리하고 다음 실행 시각으로 넘어가는데, 미스파이어 정책이 `MISFIRE_INSTRUCTION_FIRE_NOW`면 즉시 실행, `MISFIRE_INSTRUCTION_DO_NOTHING`이면 건너뛴다.

가장 안전한 방법은 UTC 기준으로 스케줄을 잡는 것이다. 비즈니스 요구사항이 "뉴욕 현지 오전 2시 실행"이라면 UTC 기준 등가 시각을 계산해서 크론에 박아 넣는 대신, 현지 자정(UTC 05:00 또는 06:00)을 기준으로 얼마 후인지로 정의한다. 아니면 크론 표현식에 타임존을 명시한다.

```java
// Quartz: 타임존 명시
CronScheduleBuilder.cronSchedule("0 0 2 * * ?")
    .inTimeZone(TimeZone.getTimeZone("UTC"))

// Spring @Scheduled: zone 속성
@Scheduled(cron = "0 0 7 * * *", zone = "UTC")  // UTC 07:00 = 뉴욕 겨울 2:00 AM
public void dailyBatch() { ... }
```

zone에 "UTC"를 명시하면 DST와 무관하게 항상 같은 UTC 시각에 실행된다. 비즈니스 요구사항이 현지 시각 고정이라면 UTC로 고정하는 대신, 현지 타임존을 명시하고 미스파이어 정책을 명확히 설정한다.

```java
// 뉴욕 현지 2:00 AM 고정 (DST 전환 시 UTC 시각이 달라짐)
CronScheduleBuilder.cronSchedule("0 0 2 * * ?")
    .inTimeZone(TimeZone.getTimeZone("America/New_York"))
    .withMisfireHandlingInstructionDoNothing()  // 봄 전환일 건너뜀
```

### 배치 잡 중복 실행 방어

가을 전환 시 배치를 현지 타임 기준으로 스케줄링하면 1:00~1:59 구간이 두 번 나타나면서 배치가 두 번 트리거될 수 있다. DB 락이나 Redis 분산 락으로 중복 실행을 막는다.

```java
// Redis를 이용한 배치 중복 실행 방어
public void runDailyReport(LocalDate date, ZoneId zone) {
    String lockKey = "batch:daily-report:" + date.toString() + ":" + zone.getId();
    Boolean acquired = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, "1", Duration.ofHours(25));

    if (!acquired) {
        log.warn("배치 이미 실행됨: {}", lockKey);
        return;
    }
    // 실제 배치 로직
}
```

락 키에 날짜를 넣을 때 로컬 날짜 기준인지 UTC 기준인지 일관성을 유지한다. 두 가지를 섞으면 락 키가 달라져 중복 방어가 뚫린다.

### 캐시 TTL과 DST

캐시 TTL을 "오늘 자정까지"로 계산할 때 현지 타임존 자정을 UTC로 변환해서 남은 시간을 TTL로 쓴다. DST 전환일에는 자정까지 남은 시간이 23시간 또는 25시간이 된다.

```java
public Duration ttlUntilMidnight(ZoneId zone, Clock clock) {
    ZonedDateTime now = ZonedDateTime.now(clock.withZone(zone));
    ZonedDateTime midnight = now.toLocalDate().plusDays(1).atStartOfDay(zone);
    return Duration.between(now.toInstant(), midnight.toInstant());
}
```

가을 전환일에 TTL이 25시간이 되는 게 맞는 동작이다. 현지 기준 "오늘까지"를 보장하려면 현지 타임존 자정을 기준으로 계산해야 한다.

### 알림 발송 타이밍

"매일 오전 9시에 리마인더 발송" 기능에서 사용자 타임존 기준 9시를 UTC로 변환해서 발송 큐에 넣는 방식을 쓰면, 발송 시각 계산 시점에 따라 DST 전환 날짜를 걸쳐가는 경우가 생긴다.

내일 오전 9시를 오늘 예약할 때 계산:

```python
from zoneinfo import ZoneInfo
from datetime import datetime, date, timedelta

def schedule_next_morning(user_timezone: str) -> datetime:
    tz = ZoneInfo(user_timezone)
    tomorrow = date.today() + timedelta(days=1)
    # 내일 9시 (현지 타임존 기준)
    local_9am = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 0, tzinfo=tz)
    # UTC로 변환
    return local_9am.astimezone(ZoneInfo('UTC'))
```

`datetime(year, month, day, 9, 0, tzinfo=tz)` 방식은 fold 처리를 안 한다. 봄 전환일 존재하지 않는 시각을 지정하면 `zoneinfo`는 DST 이후 오프셋으로 조정한다. 가을 전환일 1:30 AM처럼 중복 시각은 fold 파라미터로 구분한다.

```python
# 가을 전환 중복 시각: fold=0이 EDT(앞), fold=1이 EST(뒤)
from datetime import datetime
from zoneinfo import ZoneInfo

tz = ZoneInfo('America/New_York')
# 첫 번째 1:30 AM (EDT, UTC-4)
first_130 = datetime(2024, 11, 3, 1, 30, fold=0, tzinfo=tz)
# 두 번째 1:30 AM (EST, UTC-5)
second_130 = datetime(2024, 11, 3, 1, 30, fold=1, tzinfo=tz)

print(first_130.utcoffset())   # -1 day, 20:00:00 (-04:00)
print(second_130.utcoffset())  # -1 day, 19:00:00 (-05:00)
```

## Python zoneinfo vs pytz DST 핸들링

### pytz의 문제점

`pytz`는 Python 2 시절부터 쓰던 라이브러리인데, `tzinfo` 객체를 `datetime`의 `tzinfo` 파라미터에 직접 넣으면 DST 처리가 올바르게 되지 않는다.

```python
import pytz
from datetime import datetime

seoul = pytz.timezone('Asia/Seoul')

# 잘못된 방식 — LMT(Local Mean Time) 오프셋이 적용됨
wrong = datetime(2024, 3, 15, 9, 0, tzinfo=seoul)
print(wrong.utcoffset())  # 8:27:52 (LMT, 역사적 오프셋)

# pytz 올바른 방식 — localize 사용
correct = seoul.localize(datetime(2024, 3, 15, 9, 0))
print(correct.utcoffset())  # 9:00:00 (KST)
```

`pytz`는 반드시 `localize()`를 써야 올바른 오프셋이 적용된다. `datetime(..., tzinfo=pytz.timezone(...))`는 LMT(1800년대 역사적 평균 태양시)를 쓰는 버그가 있다. 이걸 모르고 쓴 레거시 코드에서 서울 기준으로 8:27:52라는 오프셋이 나온다.

DST가 있는 타임존에서 `localize()`로 변환 후 날짜 연산을 하면 DST 처리가 제대로 된다.

```python
import pytz
from datetime import datetime, timedelta

eastern = pytz.timezone('America/New_York')

# 2024-03-09 2:00 AM EST (봄 전환 하루 전)
dt = eastern.localize(datetime(2024, 3, 9, 2, 0))
print(dt.utcoffset())  # -1 day, 19:00:00 (-05:00, EST)

# 하루 후 = 2024-03-10 2:00 AM인데 이 시각은 존재하지 않음
next_day = dt + timedelta(days=1)
# normalize()가 없으면 여전히 EST 오프셋 (-05:00)으로 고정된 채 결과 나옴
print(next_day.utcoffset())  # -1 day, 19:00:00 (DST 적용 안 됨!)

# normalize()로 DST 재계산
correct = eastern.normalize(dt + timedelta(days=1))
print(correct.utcoffset())  # -1 day, 20:00:00 (-04:00, EDT)
```

`timedelta` 연산 후 `normalize()`를 빠뜨리면 DST 전환을 넘어도 오프셋이 업데이트 안 된다.

### zoneinfo (Python 3.9+)

Python 3.9부터 표준 라이브러리에 `zoneinfo`가 추가됐다. `pytz`의 `localize()`/`normalize()` 이중 단계 없이 일반적인 `tzinfo` 인터페이스로 DST를 올바르게 처리한다.

```python
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

tz = ZoneInfo('America/New_York')

# tzinfo 파라미터로 직접 전달해도 올바르게 동작
dt = datetime(2024, 3, 9, 2, 0, tzinfo=tz)
print(dt.utcoffset())  # -1 day, 19:00:00 (-05:00, EST)

# 날짜 연산 후 자동으로 DST 재계산
next_day = dt + timedelta(days=1)
print(next_day.utcoffset())  # -1 day, 20:00:00 (-04:00, EDT)
```

`zoneinfo`는 OS tzdata를 사용한다. `pip install tzdata`로 별도 데이터 패키지를 설치하면 OS tzdata 없이도 동작한다. Docker Alpine 같이 tzdata가 설치 안 된 이미지에서 `zoneinfo`를 쓰면 `ZoneInfoNotFoundError`가 뜨는데, `tzdata` 패키지 설치로 해결한다.

```bash
pip install tzdata
```

신규 프로젝트에서는 `pytz` 대신 `zoneinfo`를 쓴다. `pytz`는 `localize()`/`normalize()` 패턴을 모르면 DST 버그를 만들기 쉽고, `zoneinfo`가 더 직관적이다.

## Windows 타임존 이름 vs IANA 타임존 ID

Windows는 자체 타임존 이름 체계를 쓴다. "Eastern Standard Time", "Pacific Standard Time" 같은 형태다. IANA 타임존 ID("America/New_York", "America/Los_Angeles")와 다르다.

이 문제가 실제로 터지는 경우는 두 가지다. 클라이언트가 Windows이고 시스템 API에서 타임존을 읽어 서버에 보낼 때, 그리고 .NET 백엔드나 SQL Server를 섞어 쓸 때다.

```python
# Python에서 Windows 타임존 이름으로 ZoneInfo를 만들려고 하면 에러
from zoneinfo import ZoneInfo
ZoneInfo('Eastern Standard Time')  # ZoneInfoNotFoundError
ZoneInfo('America/New_York')       # 정상
```

`pytz`도 마찬가지다. `pytz.timezone('Eastern Standard Time')`은 `UnknownTimeZoneError`를 던진다.

변환 라이브러리를 쓰면 Windows 이름을 IANA ID로 매핑할 수 있다.

```python
# Python: python-dateutil의 win_tz 매핑
from dateutil.tz import gettz
tz = gettz('Eastern Standard Time')  # 내부적으로 America/New_York으로 처리

# 직접 매핑 딕셔너리를 관리하는 방식
WINDOWS_TO_IANA = {
    'Eastern Standard Time': 'America/New_York',
    'Pacific Standard Time': 'America/Los_Angeles',
    'Central Standard Time': 'America/Chicago',
    'Mountain Standard Time': 'America/Denver',
    'UTC': 'UTC',
    'Korea Standard Time': 'Asia/Seoul',
    # ...
}
```

Java에서는 `ZoneId.of("Eastern Standard Time")`이 동작하지 않는다. `java.util.TimeZone.getTimeZone("Eastern Standard Time")`은 에러 없이 GMT를 반환하는 silent failure 동작이 있어서 더 위험하다.

```java
// TimeZone.getTimeZone()의 silent failure
TimeZone tz = TimeZone.getTimeZone("Eastern Standard Time");
System.out.println(tz.getID()); // "GMT" — 잘못된 ID면 GMT를 반환
System.out.println(tz.getRawOffset()); // 0 (UTC와 같음)
```

인식하지 못한 타임존 ID를 받으면 GMT로 fallback해서 버그가 조용히 생긴다. 클라이언트로부터 받은 타임존 ID를 처리할 때는 `ZoneId.of()` 또는 IANA ID 유효성 검사를 명시적으로 한다.

```java
// 명시적 검증
try {
    ZoneId zone = ZoneId.of(userProvidedId);
} catch (DateTimeException e) {
    // IANA ID 아님 — Windows 이름이거나 잘못된 값
    throw new IllegalArgumentException("유효하지 않은 타임존 ID: " + userProvidedId);
}
```

클라이언트가 Windows 시스템이라면 클라이언트 쪽에서 IANA ID로 변환해서 보내도록 계약을 잡는 게 낫다. JavaScript에서는 `Intl.DateTimeFormat().resolvedOptions().timeZone`이 항상 IANA ID를 반환한다.

```javascript
// 브라우저/Node.js: 항상 IANA ID
const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
// "America/New_York", "Asia/Seoul" 같은 형태
```

서버가 받아서 변환하는 방향보다 클라이언트가 처음부터 IANA ID를 보내는 방향이 안전하다.

## DST 예외 지역 처리

### Arizona

미국에서 DST를 적용하지 않는 대표적인 예외 지역이다. IANA 타임존 ID `America/Phoenix`를 쓴다. 연중 UTC-7 고정이다.

주의할 점은 Navajo Nation이다. Arizona 내에 있지만 Navajo Nation은 DST를 적용한다. Navajo Nation 타임존은 `America/Shiprock`(또는 `America/Denver`와 같음)이다. Arizona 주소를 보고 무조건 `America/Phoenix`로 처리하면 Navajo Nation 주민에게 1시간 오차가 생긴다.

```python
# Arizona 주 내 두 타임존
from zoneinfo import ZoneInfo
from datetime import datetime

phoenix = ZoneInfo('America/Phoenix')    # Arizona 대부분 지역 (DST 없음)
navajo  = ZoneInfo('America/Denver')     # Navajo Nation (DST 있음)

# 2024년 여름 (DST 기간)
summer = datetime(2024, 7, 1, 12, 0)

dt_phoenix = summer.replace(tzinfo=phoenix)
dt_navajo  = summer.replace(tzinfo=navajo)

print(dt_phoenix.utcoffset())  # -07:00 (연중 고정)
print(dt_navajo.utcoffset())   # -06:00 (MDT)
```

실무에서 Arizona 지역을 처리할 때는 주 단위가 아닌 IANA 타임존 ID를 기준으로 판단한다. 도시나 우편번호 기반으로 타임존을 결정하려면 GeoIP 데이터베이스나 Google Maps Time Zone API 같은 외부 서비스를 쓴다.

### DST를 폐지한 지역

최근 들어 DST를 폐지하는 국가가 늘고 있다. 멕시코(2023년), 이집트(2011년 폐지 후 부활 등) 같이 정치적 결정으로 DST 규칙이 바뀌는 경우 tzdata 업데이트 전후로 동작이 달라진다.

```python
# 멕시코 DST 폐지 전후 비교
# tzdata 업데이트 전: 2023년 여름에 CDT(UTC-5) 적용
# tzdata 업데이트 후: 2023년 여름에 CST(UTC-6) 고정

from zoneinfo import ZoneInfo
from datetime import datetime

mexico_city = ZoneInfo('America/Mexico_City')
summer_2023 = datetime(2023, 7, 1, 12, 0, tzinfo=mexico_city)

# tzdata 최신 버전에서는 UTC-6 반환
print(summer_2023.utcoffset())  # -06:00
```

이런 변경이 생기면 과거 데이터와 현재 계산 결과가 달라진다. 2023년 이전 저장된 `America/Mexico_City` 기준 데이터는 DST가 적용된 채 저장됐을 수 있고, 현재 tzdata로 재계산하면 다른 UTC 시각이 나온다. 과거 데이터는 당시 규칙 기준으로 저장됐다는 전제 하에 처리해야 한다.

## 레거시 데이터의 DST 버그 진단

### UTC로 저장되지 않은 데이터 식별

가장 먼저 확인할 것은 저장된 데이터가 실제로 UTC인지 여부다. UTC가 아닌 로컬 타임이 저장된 경우, DST 전환 날짜 주변에서 이상한 패턴이 나온다.

가을 전환일에 동일한 1:30 AM 타임스탬프가 두 건 존재한다면 로컬 타임으로 저장된 증거다. UTC라면 두 건의 타임스탬프가 달라야 한다.

```sql
-- 가을 전환일 주변 중복 타임스탬프 확인
-- 2024-11-03이 뉴욕 가을 전환일
SELECT created_at, COUNT(*) as cnt
FROM orders
WHERE created_at BETWEEN '2024-11-03 01:00:00' AND '2024-11-03 01:59:59'
GROUP BY created_at
HAVING COUNT(*) > 1;

-- UTC로 저장된 경우 이 구간에 중복 타임스탬프가 없어야 함
-- 로컬 타임(EST/EDT)으로 저장된 경우 중복이 생길 수 있음
```

봄 전환일에 2:00~2:59 구간 데이터가 아예 없다면 의심스럽다. 해당 구간에 실제 이벤트가 없었을 수도 있지만, 로컬 타임으로 저장하다가 전환 시각을 넘어서 저장이 건너뛰어진 경우도 있다.

```sql
-- 봄 전환일 2시대 데이터 공백 확인
-- 2024-03-10이 뉴욕 봄 전환일
SELECT COUNT(*) as cnt
FROM events
WHERE event_time BETWEEN '2024-03-10 02:00:00' AND '2024-03-10 02:59:59';
-- UTC 기준이라면 이 구간에 데이터가 있을 수 있음
-- 뉴욕 로컬 타임 기준이라면 이 구간이 존재하지 않으므로 cnt = 0이어야 함
```

### 타임존 정보가 없는 타임스탬프 추정

타임존 정보 없이 저장된 datetime 컬럼에서 어느 타임존 기준인지 추정해야 하는 경우가 있다.

우선 배포 이력과 코드 히스토리를 뒤진다. 특정 날짜부터 UTC로 바뀌었다면, 그 날짜를 기준으로 두 구간으로 나눠야 한다. git log와 deploy history를 맞춰보면 대략적인 전환 시점을 찾을 수 있다.

두 번째는 이미 타임존이 확실한 이벤트와 비교하는 방법이다. 사용자 로그인 이벤트가 따로 UTC로 기록돼 있다면, 같은 사용자의 주문 타임스탬프와 비교해서 오프셋 패턴을 확인한다.

```python
import pandas as pd
from zoneinfo import ZoneInfo

# 두 컬럼 중 하나가 UTC 확실, 다른 것은 불명
df = pd.read_sql("""
    SELECT login_at_utc, order_at_unknown
    FROM user_activity
    WHERE user_id = 123
    ORDER BY login_at_utc
""", conn)

# 두 시각의 차이 분포 확인
df['diff_hours'] = (df['login_at_utc'] - df['order_at_unknown']).dt.total_seconds() / 3600
print(df['diff_hours'].value_counts())
# 차이가 -9 또는 0으로 몰린다면 KST 또는 UTC로 추정 가능
```

차이가 특정 값으로 몰리면 그 오프셋을 가진 타임존일 가능성이 높다.

### 마이그레이션 시 DST 처리

레거시 로컬 타임 데이터를 UTC로 마이그레이션할 때, DST 전환일 주변 데이터는 어느 오프셋을 적용할지 결정해야 한다.

```python
from zoneinfo import ZoneInfo
from datetime import datetime

def localize_legacy_datetime(naive_dt: datetime, timezone_str: str) -> datetime:
    """
    타임존 정보 없는 datetime을 특정 타임존으로 해석해서 UTC 변환
    DST 모호 구간은 fold=0(DST 적용, 앞쪽 시각) 기본값
    """
    tz = ZoneInfo(timezone_str)
    # fold=0: 가을 전환 중복 구간에서 DST 시간(앞쪽) 선택
    # fold=1: 표준 시간(뒤쪽) 선택
    localized = naive_dt.replace(tzinfo=tz, fold=0)
    return localized.astimezone(ZoneInfo('UTC'))

# 사용 예
legacy_dt = datetime(2024, 11, 3, 1, 30)  # 뉴욕 가을 전환일 1:30 AM (모호)
utc_dt = localize_legacy_datetime(legacy_dt, 'America/New_York')
# fold=0이므로 EDT 기준 (UTC 05:30)으로 변환됨
```

비즈니스적으로 어느 쪽을 선택해야 하는지 기준이 없으면 fold=0(앞쪽 시각, DST 적용)을 기본으로 선택하거나, 모호한 데이터는 별도 플래그로 표시하고 수동 검토 대상으로 분리한다.

```sql
-- 모호한 데이터 별도 처리
ALTER TABLE orders ADD COLUMN dst_ambiguous BOOLEAN DEFAULT FALSE;

UPDATE orders
SET dst_ambiguous = TRUE
WHERE created_at_local BETWEEN '2024-11-03 01:00:00' AND '2024-11-03 01:59:59'
  AND user_timezone = 'America/New_York';
```

마이그레이션 스크립트를 돌리기 전 DST 전환 날짜 목록을 뽑아서 해당 날짜 데이터를 별도 검토한다. 한 번에 수백만 건 마이그레이션할 때 DST 예외 케이스를 처음부터 분리해두지 않으면 나중에 찾아내기가 매우 어렵다.
