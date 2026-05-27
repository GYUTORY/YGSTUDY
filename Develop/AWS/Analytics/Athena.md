---
title: AWS Athena (S3 서버리스 SQL)
tags: [aws, athena, glue, s3, presto, trino, parquet, partitioning, cloudtrail, alb-logs]
updated: 2026-05-27
---

# AWS Athena (S3 서버리스 SQL)

## 개요

Athena는 S3에 있는 파일을 SQL로 조회하는 서비스다. 데이터를 어디 적재하거나 서버를 띄우지 않고, S3 경로만 지정하면 그 안의 CSV·JSON·Parquet 파일을 테이블처럼 쿼리한다. 엔진은 Presto/Trino 기반이고, 쿼리를 던지면 AWS가 내부에서 워커를 띄워 처리한 뒤 결과만 돌려준다. 클러스터를 미리 잡아둘 필요가 없어서 서버리스라고 부른다.

처음 쓰는 사람이 가장 헷갈리는 지점이 여기다. Athena는 데이터를 저장하지 않는다. 데이터는 전부 S3에 있고, Athena는 "이 S3 경로에 이런 스키마의 파일이 있다"는 정의만 들고 쿼리할 때마다 S3를 읽는다. 테이블을 만들어도 데이터가 복사되는 게 아니라 메타데이터만 등록된다. 그래서 테이블을 DROP해도 S3 파일은 그대로 남는다.

쓰는 상황은 정해져 있다. 로그가 S3에 쌓이는데 이걸 가끔 들여다보고 싶을 때다. ALB 액세스 로그, CloudTrail, VPC 플로우 로그, CloudFront 로그 전부 S3에 떨어지고, 평소엔 아무도 안 보다가 장애 분석이나 보안 감사 때 한 번 뒤진다. 이런 데이터를 위해 Redshift 클러스터를 띄워두는 건 낭비다. Athena는 쿼리한 만큼만 돈을 내니까 가끔 보는 데이터에 맞다.

### Redshift Spectrum과 뭐가 다른가

S3를 직접 SQL로 읽는다는 점에서 Redshift Spectrum과 거의 같다. 실제로 엔진 계보도 비슷하고 Glue 카탈로그도 공유한다. 차이는 앞단에 클러스터가 있느냐다.

Spectrum은 Redshift 클러스터가 있어야 동작한다. 클러스터 안의 로컬 데이터와 S3의 외부 테이블을 한 쿼리에서 조인하는 게 강점이다. Athena는 클러스터가 아예 없다. 쿼리를 날릴 때만 컴퓨팅이 생긴다.

판단은 단순하다. 이미 Redshift를 운영 중이고 웨어하우스 데이터랑 S3 로그를 섞어 보고 싶으면 Spectrum, S3 데이터만 가끔 조회하면 Athena다. Redshift가 없는데 Spectrum 쓰겠다고 클러스터부터 띄우는 건 본말이 전도된 거다.

## Glue 데이터 카탈로그

Athena가 테이블을 인식하려면 스키마 정의가 어딘가 있어야 한다. 그 저장소가 Glue 데이터 카탈로그다. "이 S3 경로에 이런 컬럼 구조의 파일이 있다"는 메타데이터를 Glue 카탈로그가 들고 있고, Athena는 쿼리할 때 이걸 참조한다.

카탈로그는 데이터베이스와 테이블로 구성된다. 여기서 데이터베이스는 실제 DB가 아니라 테이블을 묶는 네임스페이스일 뿐이다. 테이블도 데이터를 담지 않고, 컬럼명·타입·S3 위치·파일 포맷 같은 정의만 담는다.

### 스키마 온 리드

일반 RDBMS는 데이터를 넣을 때 스키마에 맞는지 검사한다(schema on write). 타입이 안 맞으면 INSERT가 거부된다. Athena는 반대다. 데이터를 읽는 순간에 스키마를 입힌다(schema on read). S3 파일은 그냥 텍스트 덩어리고, 쿼리 시점에 "1번째 필드는 string, 2번째는 int"라고 해석한다.

이 차이가 실무에서 어떻게 드러나냐면, 스키마를 잘못 정의해도 테이블 생성은 성공한다. 에러는 쿼리할 때 터진다. 컬럼 순서가 어긋나거나 타입이 안 맞으면 엉뚱한 값이 나오거나 NULL이 잔뜩 찍힌다. 데이터가 잘못된 게 아니라 해석을 잘못한 거라, 테이블 정의를 고치면 같은 파일이 멀쩡하게 읽힌다.

### 크롤러로 자동 생성 vs 직접 DDL

Glue 크롤러는 S3를 훑어서 스키마를 추측하고 테이블을 자동으로 만들어준다. 편하지만 추측이라 자주 틀린다. 숫자처럼 보이는 문자열을 bigint로 잡거나, JSON 중첩 구조를 이상하게 펼치는 경우가 있다. 로그처럼 포맷이 고정된 데이터는 크롤러 대신 CREATE TABLE을 직접 쓰는 게 정확하다. AWS가 ALB·CloudTrail 같은 주요 로그의 DDL을 문서로 제공하니 그대로 가져다 쓰면 된다.

크롤러가 쓸모 있는 경우는 컬럼이 계속 바뀌거나 파티션이 수시로 추가되는 데이터다. 정형 로그는 한 번 DDL 짜두면 끝이라 크롤러를 돌릴 이유가 없다. 크롤러도 실행 시간만큼 과금된다는 점도 고려해야 한다.

## 파티셔닝 — 스캔량을 줄이는 핵심

Athena는 스캔한 데이터양으로 과금한다. 1TB 스캔할 때마다 약 $5다(리전마다 차이 있음). 그래서 쿼리 성능보다 스캔량 줄이기가 먼저다. 스캔량을 줄이는 1순위 수단이 파티셔닝이다.

### 파티션이 없으면 전부 읽는다

파티션이 없는 테이블에 WHERE 조건을 걸어도 Athena는 S3 경로의 모든 파일을 읽고 나서 거른다. 하루치만 보고 싶어서 `WHERE dt = '2026-05-27'`을 걸어도, 1년치 로그가 한 경로에 있으면 1년치를 다 스캔한 다음 하루치만 남긴다. 비용은 365배로 나가는데 결과는 똑같다.

파티션은 S3 경로를 디렉터리로 쪼개서 WHERE 조건이 특정 경로만 읽게 만드는 장치다. 로그를 이렇게 쌓아둔다고 하자.

```
s3://my-logs/alb/year=2026/month=05/day=27/...
s3://my-logs/alb/year=2026/month=05/day=26/...
```

`year=2026/month=05/day=27` 형태가 파티션이다. `WHERE year='2026' AND month='05' AND day='27'`을 걸면 Athena가 그 디렉터리만 읽는다. 나머지 날짜는 아예 건드리지 않는다. 이게 파티션 프루닝(partition pruning)이다.

### 연/월/일로 자르는 이유

로그 분석은 거의 항상 기간 조건이 붙는다. "어제 5xx 에러", "지난주 특정 IP 접근" 같은 식이다. 그래서 시간 기준으로 파티션을 자르면 대부분의 쿼리가 좁은 범위만 읽는다.

연/월/일을 따로 두는 이유는 조회 범위의 유연함 때문이다. `year`·`month`·`day`를 분리하면 하루치(`day='27'`), 한 달치(`month='05'`), 일 년치(`year='2026'`)를 골라 읽을 수 있다. 반대로 `dt='2026-05-27'` 하나로 합치면 하루 단위는 깔끔한데 "5월 전체"를 보려면 `dt LIKE '2026-05-%'`처럼 패턴을 써야 하고, 이러면 파티션 프루닝이 안 먹는 경우가 생긴다. 트래픽이 큰 서비스는 시(hour)까지 쪼개기도 한다.

주의할 점은 파티션을 너무 잘게 쪼개면 역효과가 난다는 거다. 분 단위로 파티션을 만들면 디렉터리가 수만 개로 늘어나고, 각 디렉터리에 작은 파일이 흩어진다. Athena가 파티션 목록을 읽는 것 자체가 느려지고, 작은 파일이 많으면 파일 여닫는 오버헤드가 스캔 시간을 잡아먹는다. 일 단위가 무난하고, 정말 양이 많을 때만 시 단위로 내린다.

### 파티션을 카탈로그에 등록하는 방법

파티션 디렉터리를 S3에 만들어두는 것만으로는 Athena가 인식하지 못한다. 카탈로그에 "이런 파티션이 있다"고 등록해야 한다. 방법이 세 가지다.

`MSCK REPAIR TABLE`은 S3를 통째로 스캔해서 모든 파티션을 한 번에 등록한다. 처음 테이블 만들 때 편하지만, 파티션이 수천 개로 늘어나면 이 명령 자체가 느려지고 타임아웃이 난다. 새 파티션이 매일 생기는 로그에 매번 MSCK를 돌리는 건 비효율이다.

`ALTER TABLE ADD PARTITION`은 파티션을 하나씩 명시적으로 등록한다. 매일 자정에 어제 날짜 파티션만 추가하는 식으로 배치를 돌리면 MSCK보다 빠르다. 다만 누가 챙겨서 돌려야 한다.

파티션 프로젝션(partition projection)은 이 등록 자체를 없앤다. 테이블 속성에 "year는 2020부터 2030까지, month는 01~12, day는 01~31"이라고 규칙만 적어두면, Athena가 쿼리 시점에 파티션 경로를 계산해서 바로 읽는다. 카탈로그에 파티션을 등록하지 않으니 MSCK도 ALTER도 필요 없다. 날짜 기반 로그는 이 방식이 제일 손이 안 간다.

```sql
CREATE EXTERNAL TABLE alb_logs (
    -- 컬럼 정의 생략
)
PARTITIONED BY (year string, month string, day string)
-- SERDE, LOCATION 등 생략
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.year.type' = 'integer',
    'projection.year.range' = '2020,2030',
    'projection.month.type' = 'integer',
    'projection.month.range' = '01,12',
    'projection.month.digits' = '2',
    'projection.day.type' = 'integer',
    'projection.day.range' = '01,31',
    'projection.day.digits' = '2',
    'storage.location.template' =
        's3://my-logs/alb/year=${year}/month=${month}/day=${day}'
);
```

프로젝션의 함정은 범위를 넘어서면 결과가 빈다는 거다. range를 `2020,2026`으로 잡아두면 2027년 로그를 쿼리해도 빈 결과가 나온다. 에러가 아니라 빈 결과라 모르고 지나치기 쉽다. 범위는 넉넉하게 잡아두는 게 안전하다.

## 과금 — SELECT * 가 비용을 터뜨린다

다시 강조하면 Athena는 스캔한 바이트로 과금한다. 쿼리가 빠르든 느리든, 결과가 1행이든 100만 행이든, 읽은 데이터양만 본다. 이 모델을 모르고 쓰면 청구서가 예상의 수십 배로 나온다.

### SELECT * 의 두 가지 비용

`SELECT *`이 위험한 이유는 두 갈래다.

첫째, 컬럼을 다 읽는다. Parquet 같은 컬럼 포맷은 필요한 컬럼만 골라 읽을 수 있는데, `SELECT *`은 모든 컬럼을 읽으라는 뜻이라 이 이점을 통째로 버린다. 컬럼 30개짜리 테이블에서 2개만 필요한데 `SELECT *`을 쓰면 15배를 더 스캔한다.

둘째, WHERE에 파티션 조건이 없으면 전체 기간을 읽는다. `SELECT * FROM alb_logs LIMIT 10`을 무심코 날리면, LIMIT 10이라 결과는 10행이지만 스캔은 테이블 전체다. LIMIT은 결과 행만 자르지 스캔량을 줄이지 않는다. 데이터를 처음 구경하려고 `SELECT * LIMIT 10` 한 번 돌렸다가 수 TB를 스캔하는 일이 흔하다.

데이터 미리보기는 Athena 콘솔의 테이블 메뉴에서 제공하는 미리보기를 쓰거나, 파티션 조건을 반드시 붙여서 하루치만 본다. 정 전체 구조만 보고 싶으면 컬럼을 명시하고 좁은 파티션을 건다.

### 비용을 줄이는 실제 수단

- 필요한 컬럼만 SELECT한다. `SELECT *` 대신 `SELECT client_ip, elb_status_code`처럼 적는다.
- WHERE에 파티션 컬럼 조건을 항상 넣는다. 기간을 안 거는 로그 쿼리는 없다고 보면 된다.
- 텍스트 포맷을 Parquet/ORC로 바꾼다(아래에서 다룬다).
- 워크그룹에 쿼리당 스캔 한도(per-query data usage control)를 건다. 실수로 큰 쿼리가 나가도 한도를 넘으면 자동으로 취소된다. 입문자가 있는 팀은 이걸 반드시 걸어둔다.

스캔량은 쿼리 실행 후 콘솔에 "Data scanned"로 찍힌다. 새 쿼리를 운영에 넣기 전에 이 값을 보고 비용을 가늠하는 습관을 들이면 사고가 안 난다.

## 파일 포맷 — Parquet/ORC로 변환

같은 데이터라도 어떤 포맷으로 저장하느냐에 따라 스캔량이 10배 넘게 차이 난다. 비용이 스캔량에 직결되니 포맷 선택이 곧 비용 선택이다.

### 텍스트 포맷의 한계

CSV·JSON·로그 텍스트는 행 기반이다. 한 줄에 모든 컬럼이 붙어 있어서, 컬럼 하나만 필요해도 줄 전체를 읽어야 한다. 압축도 잘 안 된다. ALB 로그 원본이 gzip이어도 텍스트 구조라 컬럼 단위로 건너뛰지 못한다.

Parquet과 ORC는 컬럼 기반 포맷이다. 컬럼별로 데이터를 모아 저장하니 필요한 컬럼만 읽고, 같은 타입 값이 모여 있어 압축률도 높다. Redshift가 컬럼 저장으로 빠른 것과 같은 원리다. Athena에서 `SELECT client_ip`를 돌리면 Parquet은 client_ip 컬럼 블록만 읽지만, CSV는 전체 줄을 다 읽는다.

### 비용 차이의 실제 규모

수치는 데이터 특성마다 다르지만, 텍스트를 Parquet으로 바꾸면 스캔량이 대략 한 자릿수 배에서 많게는 수십 배까지 줄어든다. 이유가 두 겹이다. 첫째, 압축으로 파일 크기 자체가 작아진다. 둘째, 쿼리에서 일부 컬럼만 읽으니 그중에서도 일부만 스캔한다.

여기에 Parquet 내부의 통계 정보가 더해진다. Parquet은 블록마다 컬럼의 min/max 값을 들고 있어서, WHERE 조건에 안 맞는 블록은 건너뛴다(predicate pushdown). 정렬해서 저장하면 이 건너뛰기가 잘 먹어서 스캔량이 더 줄어든다.

ORC와 Parquet은 둘 다 컬럼 포맷이고 성능은 엇비슷하다. AWS 생태계와 도구 호환성을 보면 Parquet이 무난하다. 둘 중 뭘 쓸지 한참 고민할 필요는 없다.

### CTAS로 변환하기

텍스트 테이블을 Parquet으로 바꾸는 가장 간단한 방법이 CTAS(CREATE TABLE AS SELECT)다. 원본 텍스트 테이블을 읽어서 Parquet으로 새 테이블을 만든다.

```sql
CREATE TABLE alb_logs_parquet
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    partitioned_by = ARRAY['year', 'month', 'day'],
    external_location = 's3://my-logs/alb-parquet/'
) AS
SELECT
    client_ip,
    elb_status_code,
    target_status_code,
    request_url,
    request_processing_time,
    year, month, day
FROM alb_logs
WHERE year = '2026' AND month = '05';
```

CTAS를 돌리는 그 순간엔 원본을 스캔하니 비용이 든다. 하지만 한 번 변환해두면 이후 모든 쿼리가 Parquet을 읽어 싸진다. 매일 쌓이는 로그는 어제치를 변환하는 CTAS나 INSERT INTO를 배치로 돌린다. 자주 조회하는 로그일수록 변환 투자 회수가 빠르다.

한 가지 주의는 CTAS의 파티션 개수 제한이다. 한 번에 만들 수 있는 파티션 수에 상한이 있어서, 몇 년치를 한 방에 변환하려 하면 실패한다. 기간을 나눠서 여러 번 돌리거나 INSERT INTO로 이어붙인다.

## 실무 예제 1 — CloudTrail 로그 분석

CloudTrail은 누가 어떤 API를 호출했는지 기록한다. 보안 사고나 "이 리소스 누가 지웠어" 같은 추적에 쓴다. S3에 JSON으로 쌓이는데 양이 많아서 파티션과 포맷 관리가 중요하다.

테이블은 AWS가 제공하는 DDL을 쓴다. CloudTrail 전용 SerDe로 JSON을 파싱한다.

```sql
CREATE EXTERNAL TABLE cloudtrail_logs (
    eventversion STRING,
    useridentity STRUCT<
        type: STRING,
        principalid: STRING,
        arn: STRING,
        accountid: STRING,
        username: STRING>,
    eventtime STRING,
    eventsource STRING,
    eventname STRING,
    awsregion STRING,
    sourceipaddress STRING,
    useragent STRING,
    errorcode STRING,
    errormessage STRING,
    requestparameters STRING,
    responseelements STRING
)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://my-cloudtrail/AWSLogs/123456789012/CloudTrail/'
```

누가 특정 리소스를 삭제했는지 찾는 쿼리는 이렇게 짠다.

```sql
SELECT eventtime, useridentity.arn, eventname, sourceipaddress
FROM cloudtrail_logs
WHERE eventname LIKE 'Delete%'
  AND eventtime > '2026-05-20T00:00:00Z'
ORDER BY eventtime DESC;
```

루트 계정으로 로그인한 흔적을 찾는 것도 보안 점검의 단골이다.

```sql
SELECT eventtime, sourceipaddress, useragent
FROM cloudtrail_logs
WHERE useridentity.type = 'Root'
  AND eventname = 'ConsoleLogin';
```

CloudTrail은 양이 빠르게 불어난다. 위 예제는 파티션 없는 단순 형태라, 운영에서는 파티션 프로젝션을 붙이고 `eventtime` 대신 파티션 컬럼으로 기간을 좁혀야 한다. 안 그러면 삭제 이벤트 하나 찾자고 수년치를 스캔한다.

## 실무 예제 2 — ALB 액세스 로그 분석

ALB 액세스 로그는 어떤 요청이 어디로 가서 몇 번 응답코드를 받았는지 기록한다. 5xx 급증, 특정 엔드포인트 지연, 의심스러운 IP 추적에 쓴다. 포맷이 공백 구분 텍스트라 정규식 SerDe로 파싱한다.

테이블 DDL은 AWS 문서의 것을 쓴다. 컬럼이 30개 넘게 길어서 핵심만 추리면 이런 구조다.

```sql
CREATE EXTERNAL TABLE alb_logs (
    type string,
    time string,
    elb string,
    client_ip string,
    client_port int,
    target_ip string,
    request_processing_time double,
    target_processing_time double,
    response_processing_time double,
    elb_status_code int,
    target_status_code string,
    received_bytes bigint,
    sent_bytes bigint,
    request_verb string,
    request_url string,
    user_agent string
    -- 실제로는 AWS 문서의 전체 컬럼/정규식을 그대로 써야 한다
)
PARTITIONED BY (year string, month string, day string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
    'input.regex' = '...AWS 문서 제공 정규식...'
)
LOCATION 's3://my-logs/alb/'
TBLPROPERTIES ('projection.enabled' = 'true' /* 위 프로젝션 설정 */);
```

5xx 에러가 어느 엔드포인트에서 나는지 보는 쿼리다. 파티션으로 하루만 자른다.

```sql
SELECT request_url, elb_status_code, count(*) AS cnt
FROM alb_logs
WHERE year = '2026' AND month = '05' AND day = '27'
  AND elb_status_code >= 500
GROUP BY request_url, elb_status_code
ORDER BY cnt DESC
LIMIT 50;
```

타겟 응답이 느린 요청을 찾을 때는 `target_processing_time`을 본다. 백엔드 지연과 ALB 지연을 구분할 수 있다.

```sql
SELECT request_url,
       avg(target_processing_time) AS avg_target,
       max(target_processing_time) AS max_target,
       count(*) AS cnt
FROM alb_logs
WHERE year = '2026' AND month = '05' AND day = '27'
GROUP BY request_url
HAVING avg(target_processing_time) > 1.0
ORDER BY avg_target DESC;
```

`target_processing_time`이 -1로 찍히면 ALB가 타겟에 연결조차 못 했다는 신호다(예: 503). 이 값을 조건에 넣어 거르면 진짜 백엔드 지연만 골라 본다.

## 운영에서 자주 겪는 문제

쿼리 결과가 S3에 쌓인다. Athena는 모든 쿼리 결과를 지정한 S3 버킷에 CSV로 저장한다. 이걸 방치하면 결과 파일이 무한정 쌓여서 S3 비용이 슬금슬금 오른다. 결과 버킷에 수명 주기 정책을 걸어 일정 기간 지난 파일을 지운다.

작은 파일이 많으면 느리다. 로그가 1분마다 작은 파일로 떨어지면 하루에 수천 개가 쌓인다. Athena가 파일을 하나씩 여닫는 오버헤드가 스캔 시간을 잡아먹는다. CTAS로 변환할 때 적당한 크기(수백 MB 단위)로 묶이게 만들면 쿼리가 빨라진다. 반대로 한 파일이 너무 크면 병렬 처리가 안 되니 극단도 피한다.

타입 불일치는 쿼리 시점에 터진다. 스키마 온 리드라 CREATE는 성공하고 쿼리할 때 에러가 나거나 NULL이 나온다. 컬럼이 통째로 NULL이면 데이터가 빈 게 아니라 SerDe·컬럼 순서·타입 정의를 의심해야 한다.

파티션 조건을 빼먹으면 비용이 조용히 샌다. 에러가 안 나고 결과도 맞게 나오니 알아채기 어렵다. 콘솔의 "Data scanned" 값과 워크그룹의 스캔 한도, 이 두 가지로 방어선을 친다. 한 번 청구서로 데이지 않으려면 워크그룹 한도를 먼저 걸어두는 게 순서다.
