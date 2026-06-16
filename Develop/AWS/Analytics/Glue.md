---
title: AWS Glue (서버리스 ETL)
tags: [aws, glue, etl, pyspark, crawler, data-catalog, athena, redshift, job-bookmark, dpu]
updated: 2026-06-16
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

## Glue Job (PySpark) 작성

Glue Job은 보통 PySpark로 쓴다. Python 셸 타입도 있지만 대용량 변환은 Spark가 맞다. Glue는 일반 PySpark 위에 자체 추상화인 DynamicFrame을 얹어놨다. 처음엔 그냥 Spark DataFrame을 쓰면 되는데 왜 DynamicFrame이 따로 있나 싶다.

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

## Athena·Redshift 연동

### Athena

앞에서 말한 대로 Crawler가 카탈로그에 테이블을 등록하면 Athena가 그대로 본다. Glue Job으로 변환한 결과를 Parquet으로 S3에 떨군 뒤 그 경로에 Crawler를 한 번 더 돌리거나, Job 안에서 `enableUpdateCatalog` 옵션으로 출력 시 카탈로그를 직접 갱신하면 Athena에서 곧바로 조회된다. 원본 JSON/CSV를 Athena로 직접 보면 매 쿼리마다 풀스캔이라 느리고 비싸니, Glue로 Parquet + 파티션 형태로 바꿔두고 Athena가 그걸 보게 하는 흐름이 일반적이다.

### Redshift

Glue Job에서 Redshift로 적재하는 경로가 두 가지다. 하나는 Glue가 제공하는 Redshift 커넥션을 써서 `write_dynamic_frame`으로 직접 쓰는 방법이고, 다른 하나는 S3에 Parquet으로 떨군 뒤 Redshift의 `COPY` 명령으로 당기는 방법이다. 대량 적재는 두 번째가 빠르다. Glue가 Redshift로 직접 쓸 때도 내부적으로는 S3에 임시 파일을 만든 뒤 `COPY`를 쓴다. 그래서 Glue Redshift 커넥션 설정에 임시 S3 디렉토리(`TempDir`) 지정이 들어간다. 이 임시 디렉토리에 파일이 쌓이고 안 지워지는 경우가 있으니 라이프사이클 정책을 걸어두는 게 좋다.

VPC 안에 있는 Redshift에 붙을 때는 Glue Job도 같은 VPC의 서브넷으로 들어가야 한다. Glue 커넥션에 VPC/서브넷/보안그룹을 지정하고, 보안그룹은 자기 자신을 참조하는 인바운드 규칙(self-referencing)이 있어야 Glue 익스큐터끼리, 그리고 Redshift와 통신이 된다. 이 self-referencing 규칙을 빼먹어서 연결 타임아웃이 나는 경우가 흔하다.

## DPU 비용 — 가장 조심해야 할 부분

Glue 과금의 단위는 DPU(Data Processing Unit)다. 1 DPU는 대략 vCPU 4개, 메모리 16GB에 해당한다. 과금은 `DPU 개수 × 실행 시간(시간 단위, 초 단위 환산) × 단가`로 계산된다. 여기서 비용 폭탄이 터지는 지점들이 있다.

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

### 북마크 쓸 때 주의할 점

북마크 상태는 콘솔이나 CLI에서 리셋할 수 있다(`reset-job-bookmark`). 로직을 바꿔서 과거 데이터를 다시 처리해야 할 때 리셋한다. 다만 리셋하면 전체를 처음부터 다시 읽으니 비용과 시간이 든다.

S3 소스에서 북마크는 객체의 마지막 수정 시각을 기준으로 한다. 그래서 이미 처리한 파일을 누가 다시 업로드하거나 덮어쓰면 수정 시각이 갱신돼서 다시 처리 대상이 된다. 반대로 과거 날짜로 백필한 파일을 나중에 올리면 수정 시각은 최신이라 잡히지만, 경로 기반 파티션과 어긋나는 상황이 생길 수 있다. 백필을 자주 한다면 북마크만 믿지 말고 결과 쪽에서 중복을 거르는 안전장치(적재 시 멱등성, dedup)를 같이 둬야 한다.

JDBC 소스에서 북마크는 지정한 기준 컬럼(보통 자동 증가 ID나 타임스탬프)이 단조 증가해야 정상 동작한다. 기준 컬럼이 중간에 거꾸로 가거나 같은 값이 반복되면 누락이나 중복이 생긴다.

북마크는 만능이 아니다. 증분 처리의 정확성을 최종적으로 보장하는 건 적재 단계의 멱등성이다. 북마크로 읽는 양을 줄이되, 같은 데이터가 두 번 적재돼도 결과가 깨지지 않도록 키 기반 upsert나 파티션 덮어쓰기를 같이 설계하는 게 운영에서 사고를 막는 방법이다.

## 정리

Glue는 Spark 클러스터 관리를 떼어낸 ETL 도구다. Catalog는 Athena·Redshift와 공유하는 공용 메타데이터, Crawler는 스키마 자동 등록기, Job은 PySpark 변환 실행기로 보면 된다. 실무에서 발목을 잡는 건 코드보다 두 가지다. 워커 수와 실행 시간을 방치해서 나오는 DPU 비용, 그리고 `transformation_ctx`와 `job.commit()`을 빠뜨려서 동작 안 하는 job bookmark다. 이 두 개만 손에 익으면 나머지는 일반 Spark 작업과 크게 다르지 않다.
