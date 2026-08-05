---
title: AWS Glue (서버리스 ETL)
tags: [aws, glue, etl, pyspark, crawler, data-catalog, athena, redshift, job-bookmark, dpu, lake-formation, oom]
updated: 2026-06-21
---

# AWS Glue (서버리스 ETL)

## 개요

Glue는 S3나 RDB에 있는 데이터를 읽어서 변환하고 다시 어딘가에 적재하는 ETL 작업을 서버 없이 돌리는 서비스다. 직접 Spark 클러스터를 EMR로 띄워본 사람이라면 마스터/워커 노드 사이즈 잡고, 부트스트랩 스크립트 깔고, 작업 끝나면 클러스터 내리는 그 과정을 안 해도 된다는 게 Glue의 핵심이다. Job을 등록하고 실행 버튼을 누르면 AWS가 내부에서 Spark 클러스터를 잡아 코드를 돌리고 끝나면 회수한다.

구성 요소가 세 개로 나뉜다. 데이터가 어디에 어떤 스키마로 있는지를 저장하는 Data Catalog, S3 경로를 훑어서 스키마를 자동으로 채워넣는 Crawler, 실제 변환 코드를 돌리는 Glue Job이다. 이 셋이 따로 노는 것처럼 보이지만 실무에서는 Crawler가 Catalog를 채우고 Job이 Catalog를 참조해서 읽는 식으로 엮인다.

처음 접할 때 헷갈리는 부분이 Glue와 Athena의 관계다. 둘 다 Glue Data Catalog를 공유한다. Crawler로 S3 데이터의 스키마를 카탈로그에 등록해두면 Athena에서 그 테이블을 바로 SQL로 조회할 수 있다. 즉 Catalog는 Glue 전용이 아니라 Athena, Redshift Spectrum, EMR이 같이 보는 공용 메타데이터 저장소다. 그래서 Glue Crawler 한 번 돌려두면 Athena 쪽에서 `CREATE EXTERNAL TABLE`을 손으로 안 써도 된다.

## Data Catalog와 Crawler

### Catalog가 뭘 저장하는가

Data Catalog는 데이터베이스(논리적 묶음)와 테이블 메타데이터를 담는다. 테이블에는 컬럼 이름과 타입, S3 위치, 파일 포맷(Parquet/JSON/CSV), 파티션 정보가 들어간다. 실제 데이터는 안 들어간다. Athena 문서에서 본 그 구조와 같다. 테이블을 만들어도 S3 파일은 복사되지 않고 "이 경로에 이런 스키마가 있다"는 정의만 등록된다.

### Crawler로 스키마 추론

S3에 파일이 수백 개 쌓여 있을 때 컬럼 타입을 일일이 손으로 적기 귀찮다. Crawler를 S3 경로에 걸어두면 파일 일부를 샘플링해서 스키마를 추론하고 카탈로그에 테이블을 만들어준다. 파티션 구조(`year=2026/month=06/day=16` 같은 Hive 스타일 경로)도 자동으로 인식한다.

```python
# Crawler가 인식하는 전형적인 S3 파티션 구조
s3://my-bucket/logs/
  year=2026/month=06/day=15/part-0000.parquet
  year=2026/month=06/day=16/part-0000.parquet
```

이렇게 쌓여 있으면 Crawler가 `year`, `month`, `day`를 파티션 컬럼으로 잡는다. Athena에서 `WHERE year='2026' AND month='06'`으로 거르면 해당 경로만 스캔하니 스캔량이 줄고 비용이 내려간다.

### Crawler를 쓸 때 실제로 겪는 문제

스키마 추론이 항상 맞지 않는다. 자주 겪는 상황들이다.

첫째, 타입을 잘못 잡는다. 정수만 들어있는 줄 알았던 컬럼에 어쩌다 문자열이 섞이면 Crawler가 전체를 `string`으로 잡거나, 반대로 일부 파일만 보고 `bigint`로 잡았다가 다른 파일에서 깨진다. JSON에서 빈 값이 `null`로 나오는 컬럼은 타입 추론이 흔들린다. 한번 자동 추론을 맡긴 뒤에는 카탈로그 테이블 정의를 직접 확인하는 습관을 들여야 한다.

둘째, 매번 돌리면 스키마를 덮어쓴다. Crawler를 스케줄로 매일 돌리면 새 파일을 보고 기존 스키마를 바꿔버리는 경우가 있다. 이미 안정화된 테이블이라면 Crawler 설정에서 "테이블 스키마 업데이트 안 함, 새 파티션만 추가" 옵션으로 바꿔두는 게 안전하다. 새 파티션이 매일 생기는 로그 테이블은 Crawler 대신 `MSCK REPAIR TABLE`이나 파티션 프로젝션(Athena 기능)을 쓰는 게 더 깔끔할 때도 있다.

셋째, 파일이 너무 많으면 Crawler 자체가 느리고 돈이 든다. Crawler도 DPU 시간으로 과금된다. 수십만 개 작은 파일이 흩어져 있으면 크롤링에 시간이 오래 걸린다. 이 경우 S3 경로를 좁게 지정하거나, 애초에 작은 파일을 합치는 작업을 먼저 하는 게 낫다.

### 타입 충돌이 났을 때 대처

같은 컬럼인데 파일마다 타입이 다르면 Crawler가 어쩔 수 없이 `string`으로 떨어뜨리는 경우가 있다. 한 파일에서 `price`가 `123`(int)이고 다른 파일에서 `"123.0"`(string)으로 들어오면 카탈로그 컬럼이 `string`이 되고, 그 뒤로 Athena에서 `SUM(price)`를 하면 캐스팅 에러가 난다. 이건 Crawler 설정을 바꾼다고 풀리지 않는다. 근본 원인이 데이터 쪽에 있기 때문에 두 가지 중 하나로 간다.

하나는 적재하는 쪽에서 타입을 고정하는 것이다. Parquet으로 떨어뜨리면 스키마가 파일 자체에 박히니 JSON/CSV처럼 추론이 흔들리지 않는다. 가능하면 raw를 Parquet으로 한 번 정규화한 뒤 그 경로에 Crawler를 거는 게 안전하다.

다른 하나는 Crawler가 정한 타입을 사람이 덮어쓰는 것이다. 카탈로그 테이블 컬럼 타입을 직접 수정하고, 다음 Crawler 실행이 다시 덮어쓰지 못하게 막아야 한다. Crawler의 SchemaChangePolicy를 `UpdateBehavior=LOG`로 두면 변경을 감지만 하고 카탈로그를 건드리지 않는다.

```python
import boto3
glue = boto3.client("glue")

# 안정화된 테이블: 스키마는 손대지 말고 새 파티션만 추가
glue.update_crawler(
    Name="access-log-crawler",
    SchemaChangePolicy={
        "UpdateBehavior": "LOG",      # 스키마 변경은 로그만 남기고 카탈로그 미반영
        "DeleteBehavior": "LOG",      # 사라진 파티션도 함부로 지우지 않음
    },
    Configuration='{"Version":1.0,"CrawlerOutput":{"Partitions":{"AddOrUpdateBehavior":"InheritFromTable"}}}'
)
```

`AddOrUpdateBehavior=InheritFromTable`은 새 파티션이 테이블 스키마를 그대로 물려받게 한다. 이게 없으면 새 파티션마다 Crawler가 따로 스키마를 추론해서, 같은 테이블인데 파티션별로 컬럼 타입이 제각각인 상황이 생긴다. Athena에서 특정 파티션만 쿼리가 깨지면 십중팔구 이 문제다.

### 파티션이 폭증할 때

파티션 컬럼을 잘못 잡으면 파티션 수가 폭발한다. 카디널리티가 높은 값(`user_id`, `request_id`, 타임스탬프 전체)을 경로에 넣어두면 Crawler가 그걸 전부 파티션으로 인식해서 수십만 개가 만들어진다. 카탈로그에는 파티션당 메타데이터가 쌓이고, Athena 쿼리는 파티션 메타데이터를 먼저 읽느라 플래닝 단계에서만 수십 초가 걸린다. 심하면 `HIVE_EXCEEDED_PARTITION_LIMIT` 같은 에러로 막힌다.

경로 설계가 잘못된 거라 Crawler 옵션으로 못 푼다. 파티션 키는 실제 쿼리에서 필터로 쓰는 저카디널리티 컬럼(날짜, 지역, 서비스 코드 정도)만 써야 한다. 이미 폭증한 뒤라면 새 경로 구조로 데이터를 다시 쓰는 게 답이다. 날짜 단위 파티션이 너무 많아 카탈로그가 무거워진 경우엔 Crawler를 빼고 Athena 파티션 프로젝션으로 가는 게 낫다. 파티션을 카탈로그에 물리적으로 등록하지 않고 쿼리 시점에 경로 규칙으로 계산하니 메타데이터가 쌓이지 않는다.

```sql
-- 파티션 프로젝션: 카탈로그에 파티션을 안 쌓고 쿼리 때 경로를 계산
ALTER TABLE access_log SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2024-01-01,NOW',
  'projection.dt.format' = 'yyyy-MM-dd',
  'storage.location.template' = 's3://my-bucket/logs/${dt}/'
);
```

## Glue Job (PySpark) 작성

Glue Job은 보통 PySpark로 쓴다. Python 셸 타입도 있지만 대용량 변환은 Spark가 맞다. Glue는 일반 PySpark 위에 자체 추상화인 DynamicFrame을 얹어놨다. 처음엔 그냥 Spark DataFrame을 쓰면 되는데 왜 DynamicFrame이 따로 있나 싶다.

### Glue 버전과 Spark 호환성

Job을 만들 때 Glue 버전을 고르는데, 이게 그냥 라벨이 아니라 안에 박혀 있는 Spark와 Python 버전을 결정한다. 대략 이렇다.

| Glue 버전 | Spark | Python |
|---|---|---|
| 2.0 | 2.4 | 3.7 |
| 3.0 | 3.1 | 3.7 |
| 4.0 | 3.3 | 3.10 |
| 5.0 | 3.5 | 3.11 |

버전을 올리면 콜드 스타트가 빨라지고 Spark 신기능을 쓸 수 있지만, 코드가 그대로 도는 보장이 없다. 실제로 발목 잡히는 지점들이 있다.

Spark 2.x에서 3.x로 올라갈 때 동작이 바뀐 부분이 가장 많이 터진다. 대표적으로 날짜 파싱이다. Spark 3.0부터 datetime 파서가 엄격해져서, 2.4에서 통과하던 `to_timestamp` 포맷 문자열이 3.x에서는 예외를 던지거나 `null`을 뱉는다. `spark.sql.legacy.timeParserPolicy=LEGACY`로 옛 동작을 살릴 수는 있지만, 임시방편이고 언젠가 포맷을 고쳐야 한다.

```python
# Glue 2.0(Spark 2.4)에서 4.0(Spark 3.3)으로 올린 직후 날짜가 전부 null이 되는 경우
# 둘 중 하나로 푼다

# (1) 옛 파서 동작을 강제 — 빠른 응급 처치
spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")

# (2) 포맷 문자열을 새 표준으로 교정 — 권장
#   소문자 yyyy/dd는 그대로지만, 주(week) 기반 'YYYY'나 'u' 같은 패턴은 의미가 바뀜
df = df.withColumn("ts", to_timestamp(df["ts_str"], "yyyy-MM-dd HH:mm:ss"))
```

또 하나는 라이브러리 버전이다. `--additional-python-modules`로 pandas나 pyarrow를 올려 쓰는 Job이라면, Glue 버전이 바뀌면서 기본으로 깔린 numpy/pyarrow 버전이 달라져 충돌이 난다. Glue 3.0에서 잘 돌던 pandas 코드가 4.0에서 pyarrow 호환성 에러를 내는 식이다. 버전을 올릴 때는 `--additional-python-modules`에 버전을 명시적으로 고정(`pandas==2.0.3`)해서 환경 차이를 줄여야 한다.

운영 Job의 버전을 올릴 때는 Job을 복제해서 새 버전으로 만들고, 같은 입력으로 양쪽을 돌려 출력이 일치하는지 비교한 뒤 교체하는 게 안전하다. 콘솔에서 버전 드롭다운만 바꿔 바로 운영에 반영하면, 날짜나 집계가 미묘하게 틀어진 걸 한참 뒤에 발견한다.

### DynamicFrame과 DataFrame

DynamicFrame은 스키마가 고정되지 않은 데이터를 다루기 위한 Glue 전용 구조다. 같은 컬럼에 정수와 문자열이 섞여 들어오는 더러운 데이터를 만났을 때 Spark DataFrame은 스키마를 강제하다 깨지지만 DynamicFrame은 `choice` 타입으로 양쪽을 다 들고 있다가 `resolveChoice`로 나중에 정리할 수 있다. 카탈로그에서 바로 읽고 쓰는 함수도 DynamicFrame 기준으로 제공된다.

실무에서는 카탈로그에서 DynamicFrame으로 읽은 뒤 곧바로 `.toDF()`로 DataFrame으로 바꿔서 일반 Spark 코드로 변환하고, 적재 직전에 다시 `DynamicFrame.fromDF()`로 되돌리는 패턴을 많이 쓴다. Spark 문법이 더 익숙하고 자료도 많기 때문이다.

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# 카탈로그에서 DynamicFrame으로 읽기 (Crawler가 만든 테이블 참조)
dyf = glueContext.create_dynamic_frame.from_catalog(
    database="raw_logs",
    table_name="access_log",
    transformation_ctx="dyf"  # job bookmark가 이 ctx 이름으로 진행 상태를 기록한다
)

# DataFrame으로 바꿔 일반 Spark로 변환
df = dyf.toDF()
df = df.filter(df["status"] >= 400)  # 에러 응답만 추림
df = df.repartition(10)  # 출력 파일 개수 조절 (작은 파일 폭발 방지)

# 다시 DynamicFrame으로 되돌려 적재
out = DynamicFrame.fromDF(df, glueContext, "out")
glueContext.write_dynamic_frame.from_options(
    frame=out,
    connection_type="s3",
    connection_options={"path": "s3://my-bucket/curated/errors/"},
    format="parquet",
    transformation_ctx="out"  # bookmark는 출력 ctx도 추적한다
)

job.commit()  # 이 호출이 있어야 bookmark가 진행 상태를 저장한다
```

`transformation_ctx`와 `job.commit()`은 job bookmark를 쓸 때 필수다. 뒤에서 다시 다룬다.

### 디버깅이 까다로운 이유

Glue Job 디버깅이 로컬 코드처럼 안 되는 게 가장 답답한 부분이다. 실행하면 클러스터가 떠서 돌고, 에러가 나면 CloudWatch 로그를 뒤져야 한다. 몇 가지 실제로 도움 된 방법들이다.

로컬에서 먼저 돌려본다. AWS가 제공하는 Glue 도커 이미지(`amazon/aws-glue-libs`)를 받아 로컬에서 PySpark 코드를 실행하면 클러스터 띄우는 시간(콜드 스타트가 1분 넘게 걸린다)을 안 기다리고 문법 오류나 로직 오류를 잡을 수 있다. 카탈로그 접근이 필요한 부분만 빼면 대부분 로컬에서 검증된다.

작게 잘라서 확인한다. `df.show()`, `df.printSchema()`, `df.count()`를 중간중간 넣어 CloudWatch 로그로 데이터가 어떻게 흐르는지 본다. 다만 `count()`나 `show()`는 Spark 액션이라 실제 연산을 트리거하니 운영 Job에는 남기지 않는다.

에러 로그는 두 군데를 본다. Glue 콘솔의 Job run 화면에서 Error logs 링크가 드라이버 로그, All logs가 익스큐터까지 포함한 로그다. `OutOfMemoryError`나 셔플 관련 에러는 익스큐터 로그에 찍히는 경우가 많아서 All logs를 봐야 원인이 나온다.

콜드 스타트를 줄이려면 개발용 엔드포인트나 인터랙티브 세션을 쓴다. Glue Interactive Session은 노트북에서 Spark 세션을 한 번 띄워두고 셀 단위로 코드를 붙여가며 테스트할 수 있어서 매번 Job 전체를 재실행하는 것보다 반복 속도가 빠르다.

### 메모리 부족(OOM)과 셔플 스필 디버깅

Job이 한참 돌다가 `java.lang.OutOfMemoryError`나 `Container killed by YARN for exceeding memory limits`로 죽는 게 PySpark Job에서 가장 흔한 고장이다. OOM은 드라이버에서 날 수도 있고 익스큐터에서 날 수도 있는데, 원인과 처방이 다르다.

드라이버 OOM은 결과를 드라이버로 한꺼번에 끌어모을 때 난다. `df.collect()`, `toPandas()`, 인자 없는 `broadcast` 강제 같은 코드가 큰 데이터를 드라이버 메모리로 당기면 바로 터진다. 변환 결과를 코드에서 직접 받아 처리하려 하지 말고 S3로 써서 내보내는 게 원칙이다. 디버깅용으로 데이터를 봐야 하면 `collect()` 대신 `df.limit(20).show()`로 일부만 가져온다.

익스큐터 OOM은 보통 셔플과 데이터 스큐 때문이다. `groupBy`, `join`, `repartition`은 노드 간에 데이터를 다시 섞는(셔플) 연산인데, 특정 키에 데이터가 쏠려 있으면(스큐) 그 키를 받은 익스큐터 하나가 전체를 떠안고 OOM이 난다. 주문 데이터를 `customer_id`로 조인하는데 비회원 주문이 전부 `customer_id=0`으로 들어와 있으면, `0` 파티션 하나가 비대해져서 그 태스크만 죽는 식이다.

먼저 셔플 스필을 확인한다. Spark UI(Glue 콘솔의 Spark UI 링크 또는 활성화한 Spark History Server)의 stage 화면에서 "Shuffle Spill (Memory)"와 "Shuffle Spill (Disk)" 수치가 크면, 메모리에 안 들어가는 데이터를 디스크로 토해내며(스필) 돌고 있다는 뜻이다. 스필이 디스크로 GB 단위로 잡히면 Job이 느려지다 결국 OOM으로 간다.

처방은 원인별로 다르다.

워커 타입을 메모리가 큰 쪽으로 바꾼다. G.1X(16GB)에서 G.2X(32GB)나 메모리 특화인 R 계열로 올리면 익스큐터당 메모리가 늘어 스필이 줄어든다. 데이터 양보다 워커 수를 늘리는 것보다, 스큐로 한 태스크가 비대한 상황에서는 태스크 하나가 쓸 수 있는 메모리를 키우는 게 효과가 있다.

스큐 키는 솔트(salt)로 흩는다. 쏠린 키에 랜덤 접두어를 붙여 인위적으로 파티션을 나눈 뒤 집계하고, 마지막에 접두어를 떼어 다시 합친다. 코드가 번거로워지지만 한 태스크에 몰리는 걸 푸는 직접적인 방법이다.

```python
from pyspark.sql import functions as F

# 스큐 키(customer_id=0)를 0~9 솔트로 흩어서 조인 부하를 분산
n = 10
left = orders.withColumn("salt", (F.rand() * n).cast("int"))
right = customers.withColumn(
    "salt_arr", F.array([F.lit(i) for i in range(n)])
).withColumn("salt", F.explode("salt_arr"))

joined = left.join(right, ["customer_id", "salt"], "inner").drop("salt", "salt_arr")
```

셔플 파티션 수를 데이터에 맞춘다. `spark.sql.shuffle.partitions` 기본값은 200인데, 데이터가 작으면 빈 파티션이 200개 생겨 오버헤드만 늘고, 데이터가 크면 파티션당 데이터가 너무 커서 스필이 난다. 데이터 크기에 맞춰 조정한다. Glue 3.0 이상은 AQE(Adaptive Query Execution)가 켜져 있어 실행 중 파티션 수를 자동으로 합쳐주지만, 그래도 초기값이 터무니없으면 도움이 안 된다.

```python
# 셔플 파티션 수와 AQE 설정 (Job 파라미터 --conf로 넘기거나 코드에서)
spark.conf.set("spark.sql.shuffle.partitions", "64")
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")  # 스큐 조인 자동 분할
```

작은 테이블 조인은 브로드캐스트로 셔플 자체를 없앤다. 한쪽 테이블이 수십 MB 수준으로 작으면 그걸 모든 익스큐터에 통째로 복사해서 셔플 없이 조인한다. `F.broadcast(small_df)`로 명시하거나 `spark.sql.autoBroadcastJoinThreshold`를 키운다. 다만 브로드캐스트할 테이블이 실제로 작아야 한다. 큰 걸 브로드캐스트하면 이번엔 드라이버와 익스큐터 양쪽에서 OOM이 난다.

## Glue Job 운영 — 동시 실행과 재시도

Job 하나만 손으로 돌릴 때는 안 보이다가 스케줄로 묶이고 트리거가 엮이면 드러나는 문제들이 있다.

### 동시 실행 제한(Max concurrency)

Glue Job에는 동시에 몇 개까지 같은 Job을 돌릴지 정하는 Max concurrent runs 설정이 있고 기본값이 1이다. 기본값 그대로면, 앞 실행이 안 끝났는데 다음 스케줄이 돌면 `ConcurrentRunsExceededException`으로 거절된다. 5분마다 도는 Job이 어쩌다 6분 걸리면 다음 실행이 그냥 실패하는 식이다.

여기서 판단이 갈린다. Job이 멱등하지 않다면(같은 데이터를 두 번 처리하면 결과가 깨진다면) 동시 실행을 막는 게 맞으니 1을 유지하고, 대신 실행 주기를 처리 시간보다 넉넉하게 잡거나 앞 실행이 끝났는지 확인하고 트리거하게 만든다. 반대로 입력 파티션이 겹치지 않아 병렬로 돌려도 안전하다면 동시 실행 수를 올린다. 다만 동시에 N개를 돌리면 DPU도 N배로 잡힌다는 걸 잊으면 안 된다.

```python
glue.update_job(
    JobName="daily-aggregation",
    JobUpdate={
        "ExecutionProperty": {"MaxConcurrentRuns": 3},  # 기본 1 → 3
        "MaxRetries": 1,            # 실패 시 1회 자동 재시도
        "Timeout": 60,             # 분 단위. 60분 넘으면 강제 종료(DPU 폭주 방지)
        # ... Role, Command 등 나머지 필드도 update_job에는 함께 넘겨야 함
    }
)
```

### 재시도 설정의 함정

`MaxRetries`로 Job 실패 시 자동 재시도를 걸 수 있는데, 여기에 함정이 있다. 재시도는 Job 전체를 처음부터 다시 돌린다. 중간까지 처리하고 적재까지 한 뒤 마지막에 죽었다면, 재시도가 같은 데이터를 또 적재해서 중복을 만든다. job bookmark를 켜뒀더라도 `job.commit()` 전에 죽었으면 북마크가 진행 상태를 저장하지 않았으니, 재시도가 같은 구간을 다시 읽는다. 즉 재시도와 멱등성은 한 묶음이다. 멱등하지 않은 Job에 `MaxRetries`만 올려두면 실패할 때마다 중복이 쌓인다.

일시적 오류(스팟 회수, 네트워크 순단)에는 재시도가 약이지만, 코드 버그나 잘못된 입력으로 인한 실패는 재시도해봐야 똑같이 죽으면서 DPU만 두 배로 쓴다. 재시도는 1 정도로 낮게 두고, 반복 실패하는 Job은 알람으로 사람이 보게 하는 편이 낫다. CloudWatch에서 `glue.driver.aggregate.numFailedTasks`나 Job run 상태를 EventBridge로 받아 SNS 알람을 거는 식이다.

## Athena·Redshift 연동

### Athena

앞에서 말한 대로 Crawler가 카탈로그에 테이블을 등록하면 Athena가 그대로 본다. Glue Job으로 변환한 결과를 Parquet으로 S3에 떨군 뒤 그 경로에 Crawler를 한 번 더 돌리거나, Job 안에서 `enableUpdateCatalog` 옵션으로 출력 시 카탈로그를 직접 갱신하면 Athena에서 곧바로 조회된다. 원본 JSON/CSV를 Athena로 직접 보면 매 쿼리마다 풀스캔이라 느리고 비싸니, Glue로 Parquet + 파티션 형태로 바꿔두고 Athena가 그걸 보게 하는 흐름이 일반적이다.

### Redshift

Glue Job에서 Redshift로 적재하는 경로가 두 가지다. 하나는 Glue가 제공하는 Redshift 커넥션을 써서 `write_dynamic_frame`으로 직접 쓰는 방법이고, 다른 하나는 S3에 Parquet으로 떨군 뒤 Redshift의 `COPY` 명령으로 당기는 방법이다. 대량 적재는 두 번째가 빠르다. Glue가 Redshift로 직접 쓸 때도 내부적으로는 S3에 임시 파일을 만든 뒤 `COPY`를 쓴다. 그래서 Glue Redshift 커넥션 설정에 임시 S3 디렉토리(`TempDir`) 지정이 들어간다. 이 임시 디렉토리에 파일이 쌓이고 안 지워지는 경우가 있으니 라이프사이클 정책을 걸어두는 게 좋다.

VPC 안에 있는 Redshift에 붙을 때는 Glue Job도 같은 VPC의 서브넷으로 들어가야 한다. Glue 커넥션에 VPC/서브넷/보안그룹을 지정하고, 보안그룹은 자기 자신을 참조하는 인바운드 규칙(self-referencing)이 있어야 Glue 익스큐터끼리, 그리고 Redshift와 통신이 된다. 이 self-referencing 규칙을 빼먹어서 연결 타임아웃이 나는 경우가 흔하다.

### Redshift Spectrum도 같은 카탈로그를 본다

Redshift Spectrum은 S3에 있는 데이터를 Redshift로 옮기지 않고 외부 테이블로 직접 쿼리하는 기능인데, 이때 참조하는 외부 스키마를 Glue Data Catalog에 연결할 수 있다. `CREATE EXTERNAL SCHEMA ... FROM DATA CATALOG`로 카탈로그의 데이터베이스를 Spectrum 외부 스키마로 매핑하면, Glue Crawler가 등록한 테이블을 Redshift에서 그대로 조인해 쓸 수 있다. Athena와 Spectrum이 같은 카탈로그 테이블을 동시에 보는 구조가 된다. 편한 만큼 권한 문제가 여기서 터진다.

## Lake Formation 권한 충돌

카탈로그를 Athena, Spectrum, Glue Job이 같이 쓰기 시작하면 권한이 두 겹으로 쌓인다. 원래 카탈로그 접근은 IAM 정책으로 통제했는데, Lake Formation을 켜는 순간 그 위에 Lake Formation 권한이 한 겹 더 얹힌다. 두 겹을 다 통과해야 데이터가 보인다. IAM에서 `glue:GetTable`, `s3:GetObject`를 다 열어줬는데도 쿼리가 "권한 없음"으로 막히면, 십중팔구 Lake Formation 쪽 권한이 비어 있는 것이다.

증상이 헷갈리는 게, 콘솔에서 테이블 목록은 보이는데 `SELECT`만 빈 결과나 권한 에러로 막히는 식이다. 테이블 메타데이터 권한과 데이터 권한이 따로 놀기 때문이다. Lake Formation에서 해당 principal(Glue Job의 IAM 역할, Athena를 쓰는 사용자 역할)에 테이블·컬럼 단위 `SELECT` 권한을 명시적으로 줘야 한다.

```python
import boto3
lf = boto3.client("lakeformation")

# Glue Job 역할에 특정 테이블의 SELECT 권한을 Lake Formation에서 부여
lf.grant_permissions(
    Principal={"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/glue-etl-role"},
    Resource={"Table": {"DatabaseName": "raw_logs", "Name": "access_log"}},
    Permissions=["SELECT", "DESCRIBE"],
)
```

실무에서 자주 막히는 지점들이 있다.

Glue Job의 IAM 역할에 Lake Formation 권한을 안 줘서 Job이 카탈로그 읽기에 실패한다. IAM 역할에 `lakeformation:GetDataAccess`가 있어야 Job이 Lake Formation을 거쳐 S3 데이터에 접근할 수 있고, 그와 별개로 그 역할에 테이블 `SELECT` 권한도 부여돼 있어야 한다. 둘 중 하나만 있으면 `AccessDeniedException`이 난다.

`IAMAllowedPrincipals`라는 기본 권한이 남아 있어 혼란이 생긴다. Lake Formation을 처음 켜면 기존 IAM 동작과 호환되도록 모든 테이블에 `IAMAllowedPrincipals` 그랜트가 깔려 있다. 이게 있는 동안은 IAM만 통과하면 데이터가 보여서 Lake Formation이 작동하지 않는 것처럼 느껴진다. 본격적으로 Lake Formation으로 통제하려면 이 기본 그랜트를 떼야 하는데, 떼는 순간 명시적으로 권한을 안 준 모든 Job과 사용자가 한꺼번에 막힌다. 운영 중인 데이터레이크에서 이걸 모르고 제거하면 파이프라인이 줄줄이 멈춘다. 떼기 전에 어떤 역할이 어떤 테이블을 쓰는지 먼저 다 그랜트해두고 마지막에 기본 그랜트를 제거해야 한다.

크로스 계정에서 더 까다롭다. 데이터 계정의 카탈로그를 분석 계정의 Athena/Spectrum이 보는 구조면, Lake Formation에서 리소스를 다른 계정에 공유(grant)하고, 받는 계정에서 RAM(Resource Access Manager) 초대를 수락한 뒤, 다시 그 계정 안에서 사용자에게 권한을 재부여하는 단계를 다 거쳐야 한다. 한 단계라도 빠지면 테이블이 안 보이거나 보여도 쿼리가 막힌다. 크로스 계정 카탈로그 공유에서 안 보이는 문제는 거의 이 체인 중 한 칸이 비어 있는 것이다.

Glue Job으로 카탈로그에 테이블을 새로 만드는 경우(`enableUpdateCatalog`)에도 Lake Formation 권한이 필요하다. Job 역할에 데이터베이스 단위 `CREATE_TABLE`, 테이블 `ALTER` 권한이 없으면, 변환은 끝났는데 카탈로그 갱신에서 실패해 Job이 마지막에 죽는다. 데이터는 S3에 다 써놓고 카탈로그만 못 만든 어정쩡한 상태가 남는다.

## DPU 비용 — 가장 조심해야 할 부분

Glue 과금의 단위는 DPU(Data Processing Unit)다. 1 DPU는 대략 vCPU 4개, 메모리 16GB에 해당한다. 과금은 `DPU 개수 × 실행 시간(시간 단위, 초 단위 환산) × 단가`로 계산된다. 여기서 비용 폭탄이 터지는 지점들이 있다.

### DPU를 어떻게 세는가

콘솔에서는 워커 타입과 워커 수를 고르지 워커 수가 곧 DPU는 아니다. 환산이 들어간다. G.1X는 워커 1개가 1 DPU, G.2X는 워커 1개가 2 DPU다. 여기에 Spark에서 코드를 조율하는 드라이버 몫 1 DPU가 더 붙는다. 그래서 실제 DPU는 이렇게 잡힌다.

```text
G.1X 워커 10개  →  드라이버 1 + 워커 10×1 = 11 DPU
G.2X 워커 10개  →  드라이버 1 + 워커 10×2 = 21 DPU
```

비용은 `DPU × 실행 시간(시간) × 단가`다. G.1X 워커 10개짜리 Job이 12분 돌면 `11 DPU × 0.2시간 × 단가`다. 청구서에서 "분명 작은 Job인데 왜 이렇게 나오지" 싶을 때, 워커 수만 보고 드라이버 +1과 G.2X의 ×2 환산을 빼먹은 경우가 많다.

워커를 많이 잡는다고 빨라지는 것도 아니다. 데이터가 10개 파티션으로만 나뉘는데 워커를 20개 잡으면, 10개는 일하고 10개는 놀면서 DPU만 잡아먹는다. Spark UI에서 익스큐터별 태스크 수를 보고 노는 워커가 많으면 워커 수를 줄여야 한다. Auto Scaling을 켜면(Glue 3.0 이상) 부하에 따라 워커를 자동으로 늘렸다 줄여주니, 데이터 양이 들쭉날쭉한 Job은 고정 워커보다 이쪽이 비용이 덜 든다.


기본 워커 수가 생각보다 크다. Glue Job을 만들면 기본 워커 타입과 개수가 잡혀 있는데, G.1X 워커 10개면 10 DPU다. 데이터가 몇 MB밖에 안 되는데 워커 10개를 1시간 돌리면 그만큼 돈이 나간다. 작은 데이터를 다루는 Job은 워커 수를 2~3개로 줄여야 한다. 데이터 양에 맞춰 워커를 잡는 감각이 필요하다.

최소 과금 시간이 있다. Glue 2.0 이상은 최소 1분 과금이라 짧은 Job도 어느 정도 비용이 잡힌다(예전 1.0은 최소 10분이라 더 심했다). 그래도 콜드 스타트로 클러스터 뜨는 시간까지 포함되니 아주 짧은 작업을 Glue로 자주 돌리는 건 비효율이다. 가벼운 처리는 Lambda나 Python 셸 Job이 나을 때가 있다.

Job이 안 끝나고 매달려 있는다. 무한 루프나 셔플 폭증으로 Job이 멈추지 않고 몇 시간씩 도는 경우 DPU × 시간이 그대로 청구된다. Job 타임아웃을 반드시 설정해둬야 한다. 기본 타임아웃이 길게 잡혀 있으니 처리 시간을 알면 거기에 여유를 더한 값으로 줄여둔다.

Crawler도 과금된다는 걸 잊는다. Crawler를 빈번한 스케줄로 돌리면 그것도 DPU 시간으로 쌓인다. 위에서 말한 작은 파일 수십만 개를 매시간 크롤링하면 Job 안 돌려도 비용이 나간다.

개발 중 반복 실행이 누적된다. 디버깅하느라 Job을 수십 번 재실행하면 매번 클러스터가 뜨고 콜드 스타트 시간까지 과금된다. 그래서 위에서 말한 로컬 도커나 Interactive Session으로 먼저 검증하고 실제 Job 실행 횟수를 줄이는 게 비용에도 직결된다.

비용을 추적하려면 Job마다 태그를 붙이고 Cost Explorer에서 Glue 비용을 Job 단위로 본다. 어느 Job이 DPU를 잡아먹는지 모르면 손을 못 댄다.

## Job Bookmark — 중복 처리 방지

매일 새 데이터가 S3에 쌓이는데 Glue Job이 매번 전체를 다시 읽으면 처리량도 늘고 결과도 중복된다. Job bookmark는 Glue가 "지난번에 어디까지 처리했는지"를 기억해서 이번 실행에는 새로 들어온 데이터만 처리하게 하는 기능이다.

동작 방식은 입력 소스의 진행 상태(S3는 객체의 마지막 수정 시각과 경로, JDBC는 기준 컬럼 값)를 북마크에 저장해두는 것이다. 다음 실행 때 그 지점 이후의 데이터만 읽는다. 매일 어제치 로그만 증분 처리하는 파이프라인에서 이게 없으면 중복 적재가 일어난다.

쓰려면 세 가지를 맞춰야 한다.

첫째, Job 설정에서 북마크를 Enable로 켠다. 기본은 꺼져 있다(Disable).

둘째, 코드에서 `transformation_ctx`를 모든 입출력에 지정한다. 북마크는 이 ctx 이름을 키로 진행 상태를 추적한다. ctx 이름이 없거나 중간에 바뀌면 북마크가 추적을 못 해서 전체를 다시 읽는다. 위 예제에서 `from_catalog`와 `write_dynamic_frame` 양쪽에 `transformation_ctx`를 넣은 이유가 이것이다.

셋째, 마지막에 `job.commit()`을 호출한다. 이 호출이 있어야 이번 실행에서 처리한 지점이 북마크에 저장된다. `job.commit()`을 안 부르면 다음 실행에서 같은 데이터를 또 읽는다. 디버깅하다가 `job.commit()`을 빼먹고 돌려놓고는 "북마크를 켰는데 왜 매번 전체를 읽지" 하고 헤매는 일이 자주 있다.

### 중복 적재가 났던 사례

북마크를 켜뒀는데도 중복이 쌓인 경우를 몇 번 봤다. 패턴이 정해져 있다.

`transformation_ctx`를 출력에만 빼먹은 경우다. 입력 `from_catalog`에는 ctx를 넣었는데 출력 `write_dynamic_frame`에는 안 넣었다. 북마크는 입력만 추적해서 새 데이터만 읽기는 하는데, 출력 쪽 ctx가 없으면 Glue가 출력 경로의 상태를 추적하지 못해 일부 시나리오에서 같은 출력을 다시 쓰는 일이 생긴다. 입출력 양쪽 ctx를 다 채워야 한다.

리파티션이나 셔플 뒤에서 출력 ctx가 입력과 끊긴 경우도 있다. 입력에서 받은 DynamicFrame을 `toDF()`로 바꿔 `groupBy`, `join`을 거치면 데이터 계보가 한 번 끊긴다. 이 상태에서 출력 ctx만 있다고 북마크가 입력-출력을 자동으로 이어주지 않는다. 변환이 복잡한 파이프라인은 북마크가 입력 증분만 보장한다고 보고, 출력 중복은 적재 단계에서 따로 막아야 한다.

가장 흔한 건 동일 파일을 다시 올린 경우다. 데이터 제공 쪽이 어제 파일을 정정해서 같은 경로에 다시 업로드하면, S3 객체의 LastModified가 갱신돼 북마크가 "새 파일"로 보고 다시 읽는다. 원본은 한 번 처리됐는데 정정본이 또 적재되니 그날치가 두 번 들어간다. 이건 북마크의 정상 동작이라 막을 수 없고, 적재를 멱등하게 만들어야 한다. 파티션 단위로 덮어쓰는 방식이면 같은 날짜가 다시 들어와도 그 파티션만 교체되니 중복이 안 쌓인다.

```python
# 파티션 덮어쓰기로 중복 적재를 멱등하게 만든다 (북마크가 헛돌아도 결과는 안 깨짐)
spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

df.write \
    .mode("overwrite") \
    .partitionBy("dt") \
    .parquet("s3://my-bucket/curated/orders/")
# dynamic 모드: 이번에 들어온 dt 파티션만 교체. 안 건드린 과거 파티션은 그대로 둠
```

`partitionOverwriteMode=dynamic`이 없으면 `overwrite`가 출력 경로 전체를 날려버린다. 어제까지 쌓아둔 모든 파티션이 사라지고 오늘치만 남는 사고가 여기서 난다. 동적 모드를 반드시 같이 켜야 한다.

### 북마크 쓸 때 주의할 점

북마크 상태는 콘솔이나 CLI에서 리셋할 수 있다(`reset-job-bookmark`). 로직을 바꿔서 과거 데이터를 다시 처리해야 할 때 리셋한다. 다만 리셋하면 전체를 처음부터 다시 읽으니 비용과 시간이 든다.

S3 소스에서 북마크는 객체의 마지막 수정 시각을 기준으로 한다. 그래서 이미 처리한 파일을 누가 다시 업로드하거나 덮어쓰면 수정 시각이 갱신돼서 다시 처리 대상이 된다. 반대로 과거 날짜로 백필한 파일을 나중에 올리면 수정 시각은 최신이라 잡히지만, 경로 기반 파티션과 어긋나는 상황이 생길 수 있다. 백필을 자주 한다면 북마크만 믿지 말고 결과 쪽에서 중복을 거르는 안전장치(적재 시 멱등성, dedup)를 같이 둬야 한다.

JDBC 소스에서 북마크는 지정한 기준 컬럼(보통 자동 증가 ID나 타임스탬프)이 단조 증가해야 정상 동작한다. 기준 컬럼이 중간에 거꾸로 가거나 같은 값이 반복되면 누락이나 중복이 생긴다.

북마크는 만능이 아니다. 증분 처리의 정확성을 최종적으로 보장하는 건 적재 단계의 멱등성이다. 북마크로 읽는 양을 줄이되, 같은 데이터가 두 번 적재돼도 결과가 깨지지 않도록 키 기반 upsert나 파티션 덮어쓰기를 같이 설계하는 게 운영에서 사고를 막는 방법이다.

## 정리

Glue는 Spark 클러스터 관리를 떼어낸 ETL 도구다. Catalog는 Athena·Redshift와 공유하는 공용 메타데이터, Crawler는 스키마 자동 등록기, Job은 PySpark 변환 실행기로 보면 된다.

실무에서 발목을 잡는 건 코드 문법보다 운영 쪽이다. 워커 수와 드라이버 몫, 실행 시간을 방치해서 나오는 DPU 비용, `transformation_ctx`와 `job.commit()`을 빠뜨리거나 동일 파일 재업로드로 헛도는 job bookmark, 버전 올리면서 미묘하게 틀어지는 Spark 동작, 스큐 키 하나로 익스큐터가 OOM으로 죽는 셔플, 카탈로그를 여럿이 공유하면서 한 겹 더 쌓이는 Lake Formation 권한이 반복해서 나온다. 공통점이 하나 있다. 북마크든 재시도든 증분 처리든, 정확성의 마지막 보루는 결국 적재 단계의 멱등성이라는 것이다. 파티션 덮어쓰기나 키 기반 upsert로 같은 데이터가 두 번 들어와도 결과가 안 깨지게 설계해두면, 위쪽 단계가 가끔 헛돌아도 사고로 번지지 않는다.
