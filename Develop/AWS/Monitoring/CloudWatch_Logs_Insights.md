---
title: AWS CloudWatch Logs Insights
tags: [aws, cloudwatch, logs, insights, query, search, monitoring]
updated: 2026-01-22
---

# AWS CloudWatch Logs Insights

## 개요

CloudWatch Logs Insights는 로그 분석 서비스다. SQL과 비슷한 쿼리 언어를 사용한다. 수백만 개 로그를 빠르게 검색한다. 집계, 필터링, 통계를 계산한다. 대시보드로 시각화한다.

### 왜 필요한가

CloudWatch Logs는 로그를 저장한다. 하지만 검색과 분석이 제한적이다.

**문제 상황:**

**에러 로그 찾기:**
지난 1시간 동안 500 에러가 몇 번 발생했는지 확인하고 싶다.

**일반 검색:**
```
"status":500
```

모든 500 에러 로그를 찾는다. 하지만 개수는 수동으로 세야 한다. 느리고 불편하다.

**Logs Insights:**
```sql
fields @timestamp, @message
| filter status = 500
| stats count() as error_count by bin(5m)
```

5분 단위로 에러 개수를 자동 집계한다. 그래프로 시각화한다.

**문제 상황 2: 느린 API 찾기**

평균 응답 시간이 1초 이상인 API 엔드포인트를 찾고 싶다.

**일반 검색:**
각 로그를 확인하고 수동으로 계산한다. 불가능에 가깝다.

**Logs Insights:**
```sql
fields @timestamp, api, duration
| filter duration > 1000
| stats avg(duration) as avg_duration, count() as slow_requests by api
| sort avg_duration desc
```

엔드포인트별로 평균 응답 시간과 개수를 자동 계산한다.

## 쿼리 언어

### 기본 구조

```sql
fields <필드 목록>
| filter <조건>
| stats <집계 함수>
| sort <정렬>
| limit <개수>
```

파이프(`|`)로 명령을 연결한다.

### fields

표시할 필드를 선택한다.

**예시:**
```sql
fields @timestamp, @message
```

타임스탬프와 메시지만 표시한다.

**자동 필드:**
- `@timestamp`: 로그 시간
- `@message`: 로그 내용
- `@logStream`: 로그 스트림 이름

**JSON 파싱:**
로그가 JSON이면 자동으로 파싱된다.

```json
{"level":"ERROR","api":"/orders","duration":1500,"user":"user_123"}
```

```sql
fields @timestamp, level, api, duration, user
```

JSON 필드를 직접 사용한다.

### filter

조건에 맞는 로그만 선택한다.

**예시:**
```sql
fields @timestamp, level, @message
| filter level = "ERROR"
```

ERROR 로그만 선택한다.

**연산자:**
- `=`, `!=`: 같음, 다름
- `>`, `>=`, `<`, `<=`: 비교
- `like`: 패턴 매칭
- `in`: 목록 포함
- `and`, `or`, `not`: 논리 연산

**복합 조건:**
```sql
| filter level = "ERROR" and api like "/orders%"
```

`/orders`로 시작하는 API의 에러만 선택한다.

**IN 사용:**
```sql
| filter status in [500, 502, 503]
```

### stats

집계 함수를 사용한다.

**count:**
```sql
| stats count() as total
```

**count by:**
```sql
| stats count() as error_count by level
```

레벨별로 개수를 센다.

**출력:**
```
level   error_count
ERROR   150
WARN    80
INFO    1200
```

**avg, sum, min, max:**
```sql
| stats avg(duration) as avg_duration,
        max(duration) as max_duration,
        count() as requests
  by api
```

API별로 평균, 최대 응답 시간과 요청 수를 계산한다.

**bin (시간 단위 집계):**
```sql
| stats count() as requests by bin(5m)
```

5분 단위로 요청 수를 집계한다.

**출력:**
```
bin(5m)              requests
2026-01-18 10:00:00  1200
2026-01-18 10:05:00  1350
2026-01-18 10:10:00  1100
```

### sort

결과를 정렬한다.

```sql
| sort duration desc
```

응답 시간이 긴 순서로 정렬한다.

```sql
| sort @timestamp asc
```

시간 순서로 정렬한다.

### limit

결과 개수를 제한한다.

```sql
| limit 100
```

상위 100개만 표시한다.

## 실무 쿼리

### 에러 분석

**시간대별 에러 개수:**
```sql
fields @timestamp, level
| filter level = "ERROR"
| stats count() as error_count by bin(10m)
```

10분 단위로 에러 개수를 확인한다. 트래픽 패턴을 파악한다.

**에러 타입별 분석:**
```sql
fields @timestamp, error_type, error_message
| filter level = "ERROR"
| stats count() as count by error_type
| sort count desc
```

가장 많이 발생하는 에러 타입을 찾는다.

**특정 에러 상세:**
```sql
fields @timestamp, @message, stack_trace
| filter error_type = "DatabaseConnectionError"
| sort @timestamp desc
| limit 10
```

최근 10개 DB 연결 에러를 확인한다.

### 성능 분석

**느린 API Top 10:**
```sql
fields @timestamp, api, duration
| filter duration > 1000
| stats avg(duration) as avg_duration,
        max(duration) as max_duration,
        count() as slow_count
  by api
| sort avg_duration desc
| limit 10
```

평균 응답 시간이 1초 이상인 API를 찾는다.

**p95, p99 응답 시간:**
```sql
fields duration
| filter api = "/orders"
| stats avg(duration) as avg,
        pct(duration, 95) as p95,
        pct(duration, 99) as p99
```

`pct` 함수로 백분위수를 계산한다.

**시간대별 응답 시간:**
```sql
fields @timestamp, duration
| stats avg(duration) as avg_duration by bin(15m)
```

15분 단위로 평균 응답 시간을 추적한다. 트래픽 증가 시 성능 저하를 파악한다.

### 사용자 분석

**사용자별 요청 수:**
```sql
fields @timestamp, user_id, api
| stats count() as request_count by user_id
| sort request_count desc
| limit 20
```

가장 많이 요청한 사용자 20명을 찾는다. Rate Limiting이 필요한지 확인한다.

**특정 사용자 활동:**
```sql
fields @timestamp, api, status, duration
| filter user_id = "user_123"
| sort @timestamp desc
```

특정 사용자의 모든 활동을 확인한다. 고객 지원에 유용하다.

### 비즈니스 메트릭

**주문 성공/실패 비율:**
```sql
fields @timestamp, order_status
| filter api = "/orders/create"
| stats count() as total,
        sum(case order_status = "success" when 1 else 0 end) as success,
        sum(case order_status = "failed" when 1 else 0 end) as failed
```

**결제 금액 집계:**
```sql
fields @timestamp, amount, payment_method
| filter event_type = "payment_completed"
| stats sum(amount) as total_amount,
        avg(amount) as avg_amount
  by payment_method
```

결제 수단별 총액과 평균을 계산한다.

## 고급 쿼리

### 정규 표현식

**parse:**
로그에서 패턴을 추출한다.

**예시 로그:**
```
2026-01-18 10:30:45 [ERROR] Failed to connect to database: timeout
```

**쿼리:**
```sql
fields @message
| parse @message /(?<timestamp>\S+\s+\S+)\s+\[(?<level>\w+)\]\s+(?<message>.*)/
| filter level = "ERROR"
| stats count() by message
```

정규 표현식으로 필드를 추출한다.

### 여러 로그 그룹 검색

```sql
-- 콘솔에서 여러 로그 그룹 선택
/aws/lambda/order-service
/aws/lambda/payment-service
/aws/lambda/notification-service
```

```sql
fields @logStream, @message
| filter level = "ERROR"
| stats count() as error_count by @logStream
```

모든 서비스의 에러를 한 번에 분석한다.

### 서브쿼리

**예시:**
평균보다 느린 요청을 찾는다.

```sql
fields @timestamp, duration, api
| filter duration > (
    stats avg(duration) as avg_duration
  )
```

(실제로는 서브쿼리가 제한적. 두 번의 쿼리로 나눈다.)

**방법 1:**
```sql
-- 1단계: 평균 계산
fields duration
| stats avg(duration) as avg_duration
```

평균: 500ms

**2단계: 평균 이상 찾기**
```sql
fields @timestamp, duration, api
| filter duration > 500
```

## 시각화

### 그래프

쿼리 결과를 그래프로 표시한다.

**Line Graph:**
```sql
fields @timestamp
| stats count() as requests by bin(5m)
```

시간별 요청 수를 선 그래프로 표시한다.

**Bar Chart:**
```sql
fields api
| stats count() as requests by api
| sort requests desc
| limit 10
```

API별 요청 수를 막대 그래프로 표시한다.

**Pie Chart:**
```sql
fields status
| stats count() as count by status
```

상태 코드 분포를 파이 차트로 표시한다.

### 대시보드 추가

**쿼리 저장:**
1. 쿼리 실행
2. "Actions" → "Add to dashboard"
3. 대시보드 선택 또는 생성
4. 위젯 타입 선택 (Line, Bar, Table)
5. 추가

**대시보드:**
여러 쿼리를 한 화면에 표시한다.

**예시 대시보드:**
- 요청 수 (시간별)
- 에러율 (시간별)
- 평균 응답 시간 (API별)
- Top 10 에러 메시지

## 저장된 쿼리

자주 사용하는 쿼리를 저장한다.

**저장:**
1. 쿼리 작성
2. "Actions" → "Save query"
3. 이름 입력: "Error count by time"
4. 저장

**사용:**
1. "Saved queries" 선택
2. 쿼리 클릭
3. 실행

팀원과 공유한다.

## 비용

### 쿼리 비용

**가격:**
$0.005 per GB of data scanned

**예시:**
- 로그 그룹 크기: 10 GB
- 쿼리 실행: 1회
- 비용: 10 × $0.005 = $0.05

**시간 범위 제한:**
- 1시간 쿼리: 1 GB 스캔
- 24시간 쿼리: 24 GB 스캔

시간 범위를 좁힌다. 비용이 절감된다.

### 로그 저장 비용

**Standard:**
$0.50/GB-월

**Infrequent Access:**
$0.03/GB-월 (저장), $0.005/GB (검색)

자주 검색하지 않는 로그는 IA로 이동한다.

### 최적화

**필터 먼저:**
```sql
-- Bad: 모든 데이터 스캔 후 필터
fields @timestamp, level
| stats count() by level
| filter level = "ERROR"
```

10 GB를 모두 스캔한다.

**Good:**
```sql
fields @timestamp, level
| filter level = "ERROR"
| stats count()
```

ERROR 로그만 스캔한다. 1 GB만 스캔. **90% 절감**

**로그 보관 기간:**
- 중요 로그: 90일
- 일반 로그: 30일
- 디버그 로그: 7일

오래된 로그는 삭제한다.

## 실무 팁

### 필드 자동 발견

JSON 로그는 자동으로 파싱된다. 별도 설정 불필요.

**로그:**
```json
{"timestamp":"2026-01-18T10:30:00Z","level":"INFO","api":"/orders","duration":150,"user":"user_123"}
```

**쿼리:**
```sql
fields @timestamp, level, api, duration, user
```

JSON 키가 자동으로 필드가 된다.

### 중첩 JSON

점(`.`) 표기법을 사용한다.

**로그:**
```json
{"user":{"id":"user_123","name":"김철수"},"order":{"id":"order_456","amount":100}}
```

**쿼리:**
```sql
fields @timestamp, user.id, user.name, order.id, order.amount
```

### 템플릿 활용

자주 사용하는 패턴을 템플릿으로 만든다.

**에러 분석 템플릿:**
```sql
fields @timestamp, error_type, error_message
| filter level = "ERROR"
| stats count() as count by error_type
| sort count desc
| limit 10
```

다른 로그 그룹에도 동일하게 적용한다.

## CloudWatch Logs Insights vs Athena

**Logs Insights:**
- 실시간 쿼리
- 빠른 응답 (초 단위)
- CloudWatch Logs 전용
- 간단한 쿼리 언어

**Athena:**
- S3 데이터 쿼리
- 복잡한 SQL 지원
- 대용량 데이터 (TB)
- JOIN, 서브쿼리 지원

**선택:**
- 실시간 로그 분석: Logs Insights
- 장기 로그 분석: S3 + Athena

**함께 사용:**
- 최근 7일: CloudWatch Logs (Insights로 쿼리)
- 7일 이상: S3로 내보내기 (Athena로 쿼리)

## 참고

- CloudWatch Logs Insights 가이드: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html
- 쿼리 문법: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html
- CloudWatch Logs 요금: https://aws.amazon.com/cloudwatch/pricing/
- 샘플 쿼리: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html

