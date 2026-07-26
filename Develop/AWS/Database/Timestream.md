---
title: Amazon Timestream
tags: [aws, timestream, timeseries, database, iot, metrics, grafana, cloudwatch, kinesis, scheduled-queries]
updated: 2026-07-26
---

# Amazon Timestream

시계열 데이터를 RDS나 DynamoDB에 쌓다 보면 공통적으로 겪는 문제가 있다. 시간이 지날수록 디스크가 찬다. 오래된 데이터를 지우는 배치 잡을 따로 만들어야 하고, 인덱스가 비대해져 최근 데이터 조회 속도도 느려진다. "최근 1시간 평균"같은 집계 쿼리는 매번 풀스캔에 가까워진다.

Timestream은 이 문제에 특화된 완전 관리형 시계열 데이터베이스다. 시간 범위 기반 쿼리, 데이터 자동 만료, 핫/콜드 스토리지 티어링이 기본으로 내장되어 있다.

AWS는 현재 두 가지 Timestream 제품을 제공한다. Amazon Timestream for LiveAnalytics(기존 Timestream)와 Amazon Timestream for InfluxDB다. 이 둘은 단순한 버전 차이가 아니라 용도와 쿼리 방식이 완전히 다르다. 선택 기준은 뒤에서 별도로 다룬다.

## 저장 구조

Timestream for LiveAnalytics는 테이블을 두 개의 스토리지 티어로 나눠 관리한다.

**메모리 스토어(Memory Store)**

최근에 수집된 데이터를 SSD 기반 인메모리 레이어에 보관한다. 최소 1시간부터 최대 몇 시간까지 유지 기간을 설정한다. 비용이 높지만 쓰기와 읽기 모두 빠르다. IoT 센서나 애플리케이션 메트릭처럼 실시간으로 들어오는 데이터가 처음 착지하는 곳이다.

**마그네틱 스토어(Magnetic Store)**

메모리 스토어의 보존 기간이 지난 데이터는 자동으로 마그네틱 스토어로 내려간다. S3 기반 컬럼형 스토리지다. 비용은 훨씬 저렴하지만 쿼리 지연이 길다. 수개월~수년치 이력 데이터를 장기 보관할 때 쓴다.

두 티어의 보존 기간은 테이블마다 독립적으로 설정한다. 메모리 스토어를 6시간, 마그네틱 스토어를 365일로 설정하면 6시간이 지난 데이터는 자동으로 마그네틱으로 이동하고, 365일이 지난 데이터는 자동으로 삭제된다. 별도의 배치 잡 없이도 디스크가 무한정 차는 문제가 사라진다.

```
데이터 흐름:
애플리케이션 → 메모리 스토어(최근 N시간) → 마그네틱 스토어(장기) → 자동 삭제
```

마그네틱 스토어에는 "쓰기 지연 허용" 옵션도 있다. 네트워크 단절로 IoT 기기가 오프라인 상태였다가 나중에 밀린 데이터를 올려야 할 때 사용한다. 기본적으로 Timestream은 현재 시각 기준 일정 범위 밖의 과거 데이터 쓰기를 거부하는데, 마그네틱 스토어의 지연 허용 범위를 넓히면 수일 전 데이터도 수용한다.

## 데이터 모델

Timestream의 데이터는 레코드 단위로 저장된다. 각 레코드는 세 가지 요소로 구성된다.

- **Dimensions**: 시계열을 식별하는 메타데이터. 서버명, 리전, 인스턴스 타입 같은 변하지 않는 속성이다.
- **Measure**: 실제 측정값. CPU 사용률, 응답 시간, 온도 같은 수치 데이터다.
- **Time**: 타임스탬프.

```python
import boto3
import time

client = boto3.client('timestream-write', region_name='us-east-1')

records = [
    {
        'Dimensions': [
            {'Name': 'server_id', 'Value': 'web-01'},
            {'Name': 'region', 'Value': 'ap-northeast-2'},
        ],
        'MeasureName': 'cpu_utilization',
        'MeasureValue': '72.5',
        'MeasureValueType': 'DOUBLE',
        'Time': str(int(time.time() * 1000)),
        'TimeUnit': 'MILLISECONDS',
    }
]

client.write_records(
    DatabaseName='metrics-db',
    TableName='server-metrics',
    Records=records,
)
```

한 레코드에 여러 측정값을 동시에 쓰려면 `MULTI` 타입을 쓴다. CPU, 메모리, 네트워크를 하나의 레코드로 묶어 쓰면 타임스탬프 하나에 여러 측정값이 붙어 저장된다.

```python
records = [
    {
        'Dimensions': [
            {'Name': 'server_id', 'Value': 'web-01'},
        ],
        'MeasureName': 'server_metrics',
        'MeasureValueType': 'MULTI',
        'MeasureValues': [
            {'Name': 'cpu', 'Value': '72.5', 'Type': 'DOUBLE'},
            {'Name': 'memory', 'Value': '8192', 'Type': 'BIGINT'},
            {'Name': 'network_in', 'Value': '1024', 'Type': 'BIGINT'},
        ],
        'Time': str(int(time.time() * 1000)),
        'TimeUnit': 'MILLISECONDS',
    }
]
```

## Dimension 설계 — 초기에 잘못하면 돌이킬 수 없다

Timestream에서 가장 자주 나오는 실수가 Dimension 설계다. 나중에 고치면 되겠지 싶지만, 실제로는 마이그레이션이 거의 불가능하다.

**왜 마이그레이션이 안 되나**

Timestream은 스키마 변경을 지원하지 않는다. Dimension은 시계열의 식별자 역할을 하는데, 이미 쓴 레코드의 Dimension 구조를 바꿀 수 없다. 새로운 Dimension을 추가하려면 새 테이블에 데이터를 다시 써야 한다.

마그네틱 스토어에 수개월치 데이터가 쌓인 상태에서 Dimension을 하나 추가해야 한다면, 그 데이터를 전부 읽어 새 테이블에 다시 써야 한다. 수억 건이라면 시간과 비용 모두 감당하기 어렵다. 결국 구 테이블과 신 테이블을 UNION으로 조회하는 임시 방편을 쓰거나, 그냥 포기하고 기존 구조를 유지하는 경우가 많다.

**설계 원칙**

Dimension에는 해당 시계열을 구분하는 데 반드시 필요한 속성만 넣어야 한다. "나중에 필터링할 수도 있으니까"라는 이유로 속성을 추가하면 안 된다.

잘못된 설계의 전형적인 패턴이 있다. 환경(prod/dev/staging), 서버명, 리전, 가용영역, 인스턴스 타입, 팀명, 서비스명을 전부 Dimension에 넣는 경우다. 이렇게 하면 Dimension 조합의 카디널리티(고유 시계열 수)가 폭발한다. 저장 비용이 오르고, 쿼리에서 GROUP BY할 때 집계 단위가 지나치게 세분화된다.

반대로 Dimension이 너무 적으면 같은 측정값이 서로 다른 서버에서 온 데이터가 뒤섞인다.

적정 설계는 시계열을 고유하게 식별하는 최소한의 속성이다. 서버 메트릭이라면 `server_id`와 `environment` 정도로 충분한 경우가 많다. 나머지 메타데이터(인스턴스 타입, 팀명)는 Measure로 넣거나, 외부 시스템에서 조인해서 보강한다.

```python
# 나쁜 예: Dimension 과다 — 나중에 못 바꿈
'Dimensions': [
    {'Name': 'server_id', 'Value': 'web-01'},
    {'Name': 'region', 'Value': 'ap-northeast-2'},
    {'Name': 'az', 'Value': 'ap-northeast-2a'},
    {'Name': 'instance_type', 'Value': 't3.medium'},
    {'Name': 'team', 'Value': 'platform'},
    {'Name': 'service', 'Value': 'api-server'},
    {'Name': 'environment', 'Value': 'prod'},
]

# 좋은 예: 식별에 필요한 최소만
'Dimensions': [
    {'Name': 'server_id', 'Value': 'web-01'},
    {'Name': 'environment', 'Value': 'prod'},
]
```

## 쓰기 에러 처리

### RejectedRecordsException

배치로 레코드를 쓸 때 일부 레코드가 거부되면 `RejectedRecordsException`이 발생한다. 전체 배치가 실패하는 게 아니라, 거부된 레코드 목록이 예외 안에 포함되어 있다.

거부되는 주요 원인 두 가지가 있다.

**타임스탬프가 허용 범위 밖인 경우**: 기본적으로 메모리 스토어 보존 시간보다 오래된 과거 데이터나 미래 데이터(현재보다 15분 이상 미래)는 거부된다. IoT 기기 시계가 틀렸거나, 오프라인 동안 쌓인 데이터를 뒤늦게 올릴 때 발생한다.

**중복 타임스탬프**: 같은 Dimension 조합과 MeasureName으로 완전히 동일한 타임스탬프를 가진 레코드를 다시 쓰면 거부된다. Timestream은 중복 쓰기를 허용하지 않는다. 멱등성을 위해 같은 데이터를 재전송하는 패턴은 동작하지 않는다. 이미 쓴 레코드를 수정하는 것도 불가능하다.

```python
from botocore.exceptions import ClientError

try:
    response = client.write_records(
        DatabaseName='metrics-db',
        TableName='server-metrics',
        Records=records,
    )
except ClientError as e:
    if e.response['Error']['Code'] == 'RejectedRecordsException':
        rejected = e.response['Error']['RejectedRecords']
        for r in rejected:
            print(f"레코드 인덱스 {r['RecordIndex']}: {r['Reason']}")
        # 거부되지 않은 레코드는 이미 기록된 상태
    else:
        raise
```

중복 타임스탬프 문제는 타임스탬프 단위를 조정해서 완화할 수 있다. 밀리초(MILLISECONDS) 대신 나노초(NANOSECONDS)를 쓰면 같은 순간에 여러 측정이 들어와도 충돌 가능성이 낮아진다. 데이터 수집 측에서 타임스탬프에 시퀀스 번호를 합산하는 방법도 쓴다.

과거 데이터를 뒤늦게 써야 하는 상황(오프라인 IoT 기기, 레거시 데이터 마이그레이션)이라면 테이블 생성 시 마그네틱 스토어의 지연 허용(Enable Magnetic Store Writes)을 켜야 한다. 이 옵션이 꺼진 상태에서는 메모리 스토어 보존 시간 이전의 데이터를 아예 쓸 수 없다.

## 쿼리

Timestream은 SQL과 비슷한 쿼리 언어를 쓴다. 시계열 데이터에 특화된 함수들이 추가되어 있다.

```sql
-- 최근 1시간 동안 서버별 평균 CPU
SELECT server_id,
       AVG(measure_value::double) AS avg_cpu
FROM "metrics-db"."server-metrics"
WHERE measure_name = 'cpu_utilization'
  AND time BETWEEN ago(1h) AND now()
GROUP BY server_id
ORDER BY avg_cpu DESC
```

```sql
-- 5분 단위로 집계 (bin 함수)
SELECT bin(time, 5m) AS five_min_bucket,
       server_id,
       AVG(measure_value::double) AS avg_cpu
FROM "metrics-db"."server-metrics"
WHERE measure_name = 'cpu_utilization'
  AND time > ago(3h)
GROUP BY bin(time, 5m), server_id
ORDER BY five_min_bucket DESC
```

`ago()`, `bin()`, `interpolate_linear()` 같은 함수들이 Timestream에 내장되어 있다. RDS에서라면 날짜 연산 함수를 조합해야 할 쿼리를 훨씬 짧게 표현한다.

## Scheduled Queries — 집계 비용 절감

Scheduled Queries는 집계 쿼리를 주기적으로 실행해서 결과를 다른 Timestream 테이블에 저장하는 기능이다.

**왜 필요한가**

마그네틱 스토어는 스캔 바이트 기준으로 과금된다. Grafana 대시보드가 5분마다 "지난 30일 시간별 평균 CPU"를 쿼리한다고 하면, 매번 수억 건의 원시 데이터를 스캔한다. 이 쿼리가 하루에 수백 번 실행되면 마그네틱 스토어 쿼리 비용이 상당히 나온다.

Scheduled Queries로 이미 시간별로 집계된 테이블을 만들어두면, 대시보드는 그 테이블만 조회한다. 원시 데이터 대신 하루 24개짜리 집계 행을 스캔하므로 비용이 1/N 수준으로 떨어진다.

**설정 방법**

AWS 콘솔 또는 SDK로 Scheduled Query를 생성할 때 집계 쿼리 SQL, 실행 주기(cron 표현식), 결과를 쓸 테이블과 열 매핑을 지정한다.

```sql
-- Scheduled Query에 등록할 집계 쿼리 예시
-- 1시간 단위 CPU 평균을 집계 테이블에 저장
SELECT bin(time, 1h)              AS scheduled_runtime,
       server_id,
       environment,
       AVG(measure_value::double) AS avg_cpu,
       MAX(measure_value::double) AS max_cpu
FROM "metrics-db"."server-metrics"
WHERE measure_name = 'cpu_utilization'
  AND time BETWEEN @scheduled_runtime - 1h AND @scheduled_runtime
GROUP BY bin(time, 1h), server_id, environment
```

`@scheduled_runtime`은 Scheduled Query가 실행될 때 자동으로 주입되는 변수다. 매 실행마다 이전 1시간 범위 데이터를 집계해서 결과 테이블에 쓴다.

주의할 점이 있다. Scheduled Query 결과 테이블도 Timestream 테이블이므로 Dimension 설계를 따로 해야 하고, 집계된 데이터는 원본 데이터와 별도 보존 기간을 갖는다. 집계 테이블의 마그네틱 스토어 보존 기간을 원본보다 길게 설정하는 경우가 많다. 원본은 1년 보관, 집계는 5년 보관하는 식이다.

## IoT Core → Timestream 직접 연동

AWS IoT Core에는 MQTT 메시지를 직접 Timestream에 쓰는 Rule Action이 있다. Lambda를 거치지 않고 IoT Core 룰 엔진이 직접 Timestream API를 호출한다.

**IoT Core Rule 설정**

IoT Core 콘솔에서 Rule을 만들 때 Action 타입으로 "Timestream"을 선택한다. SQL 쿼리로 어떤 메시지를 처리할지 필터링하고, 메시지 페이로드의 필드를 Dimension과 Measure에 매핑한다.

```sql
-- IoT Core Rule SQL (토픽 필터)
SELECT * FROM 'sensors/+/telemetry'
```

Rule Action에서 설정하는 항목은 다음과 같다.

- **DatabaseName**: 타겟 Timestream 데이터베이스
- **TableName**: 타겟 테이블
- **Dimensions**: 메시지 필드를 Dimension에 매핑. `${device_id}` 같은 치환 템플릿을 쓴다.
- **Timestamp**: 메시지의 타임스탬프 필드. 없으면 IoT Core가 수신한 시각을 쓴다.

IAM 역할이 필요하다. IoT Core가 Timestream에 쓸 수 있도록 `timestream:WriteRecords`와 `timestream:DescribeEndpoints` 권한을 부여한 역할을 Role ARN에 지정한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "timestream:WriteRecords",
        "timestream:DescribeEndpoints"
      ],
      "Resource": "*"
    }
  ]
}
```

직접 연동의 한계도 있다. 메시지 페이로드에서 Measure 값을 하나씩만 매핑할 수 있고, MULTI 타입으로 여러 Measure를 한번에 쓰는 건 Rule Action에서 지원하지 않는다. 여러 측정값을 가진 디바이스 데이터를 효율적으로 쓰려면 Lambda를 거쳐야 한다. 데이터 변환이 필요하거나 복잡한 로직이 있는 경우도 마찬가지다.

## Kinesis Data Streams → Timestream Lambda 패턴

IoT Core 대신 Kinesis를 허브로 쓰는 경우가 많다. IoT 디바이스뿐 아니라 여러 소스에서 데이터가 모일 때, 또는 Kinesis 소비자를 여러 대상(Timestream, S3, OpenSearch)에 동시에 연결해야 할 때다.

**구조**

```
데이터 소스 → Kinesis Data Streams → Lambda(소비자) → Timestream
```

Lambda를 Kinesis 트리거로 설정하면 Lambda가 샤드에서 배치로 레코드를 읽어 처리한다.

```python
import boto3
import json
import base64
import time

timestream_client = boto3.client('timestream-write', region_name='ap-northeast-2')

def lambda_handler(event, context):
    records_to_write = []

    for kinesis_record in event['Records']:
        payload = json.loads(base64.b64decode(kinesis_record['kinesis']['data']))

        records_to_write.append({
            'Dimensions': [
                {'Name': 'device_id', 'Value': payload['device_id']},
                {'Name': 'environment', 'Value': payload.get('env', 'prod')},
            ],
            'MeasureName': 'sensor_data',
            'MeasureValueType': 'MULTI',
            'MeasureValues': [
                {'Name': 'temperature', 'Value': str(payload['temperature']), 'Type': 'DOUBLE'},
                {'Name': 'humidity', 'Value': str(payload['humidity']), 'Type': 'DOUBLE'},
            ],
            'Time': str(int(payload['timestamp'] * 1000)),
            'TimeUnit': 'MILLISECONDS',
        })

    # Timestream은 배치당 최대 100건
    for i in range(0, len(records_to_write), 100):
        batch = records_to_write[i:i+100]
        try:
            timestream_client.write_records(
                DatabaseName='iot-db',
                TableName='sensor-metrics',
                Records=batch,
            )
        except timestream_client.exceptions.RejectedRecordsException as e:
            # 거부된 레코드만 로그, 나머지는 정상 기록됨
            for rejected in e.response['RejectedRecords']:
                print(f"Rejected: index={rejected['RecordIndex']}, reason={rejected['Reason']}")
```

Kinesis 트리거 설정 시 배치 크기(Batch Size)를 Timestream 최대 배치인 100에 맞추거나 그 배수로 설정하는 게 자연스럽다. 배치 윈도우(Batching Window)를 설정하면 Lambda가 최대 N초 기다렸다가 레코드를 모아 호출하므로 Lambda 호출 횟수가 줄어든다.

Lambda의 동시 실행 수는 Kinesis 샤드 수와 같다. 샤드가 4개면 Lambda가 최대 4개 동시 실행된다. Timestream 쓰기 처리량 제한(기본 1,000 레코드/초)을 고려해서 샤드 수를 잡아야 한다.

## Grafana 연동

Grafana에는 Timestream 공식 데이터소스 플러그인이 있다. Grafana Cloud나 자체 호스팅 Grafana 모두 지원한다.

플러그인을 설치한 뒤 AWS 자격증명과 리전을 설정하면 된다. Grafana의 쿼리 에디터에서 데이터베이스와 테이블을 선택하고 SQL을 작성한다. 시간 범위 필터는 Grafana가 자동으로 주입하는 `$__timeFilter` 매크로를 쓰면 대시보드의 시간 범위 선택기와 연동된다.

```sql
SELECT bin(time, $__interval) AS time,
       AVG(measure_value::double) AS cpu
FROM "metrics-db"."server-metrics"
WHERE measure_name = 'cpu_utilization'
  AND $__timeFilter
GROUP BY bin(time, $__interval)
ORDER BY time
```

IAM 권한은 `timestream:Select`, `timestream:DescribeEndpoints`, `timestream:ListDatabases`, `timestream:ListTables`가 필요하다. Grafana 서버에 인스턴스 프로파일을 붙이거나 액세스 키를 직접 입력한다.

## CloudWatch와의 관계

CloudWatch는 AWS 서비스가 내보내는 메트릭(EC2 CPU, RDS 연결 수, Lambda 실행 시간 등)을 수집하는 데 특화되어 있다. 알람, SNS 연동, AWS 콘솔 대시보드가 CloudWatch 중심으로 돌아간다. AWS 서비스 모니터링이라면 CloudWatch가 기본이다.

Timestream은 직접 수집하는 커스텀 데이터에 적합하다. IoT 기기의 센서 데이터, 자체 개발 애플리케이션의 비즈니스 메트릭, 외부 시스템에서 가져오는 데이터처럼 AWS가 자동으로 수집해주지 않는 데이터를 쌓을 때 사용한다.

CloudWatch는 기본 보존 기간이 15개월이고 고해상도 메트릭은 3시간까지만 무료다. 수억 건의 시계열 포인트를 장기간 저장하면 CloudWatch 비용이 예상보다 많이 나온다. 이런 경우 Timestream이 더 저렴하다.

실무에서는 AWS 서비스 메트릭은 CloudWatch에, 애플리케이션 레벨 커스텀 메트릭은 Timestream에 분리해서 쌓는 구성을 많이 쓴다.

## Timestream for LiveAnalytics vs Timestream for InfluxDB

AWS가 제공하는 두 Timestream 제품은 이름만 비슷하고 내부가 완전히 다르다.

**Timestream for LiveAnalytics**

기존에 Timestream이라고 불리던 제품이다. AWS가 자체 개발한 시계열 스토리지 엔진을 쓴다. 쿼리 언어는 SQL 기반이고, 메모리/마그네틱 스토어 자동 티어링이 핵심이다. AWS 서비스(IoT Core, Kinesis, Lambda)와의 통합이 잘 되어 있다.

**Timestream for InfluxDB**

InfluxDB OSS를 AWS에서 관리형으로 실행해주는 서비스다. InfluxDB의 쿼리 언어(InfluxQL, Flux)를 그대로 쓴다. 기존에 InfluxDB를 쓰던 팀이 서버 운영 부담 없이 AWS로 옮기고 싶을 때 적합하다.

**선택 기준**

Timestream for InfluxDB를 선택하는 경우는 명확하다. 이미 InfluxDB를 쓰고 있고, Flux나 InfluxQL로 짠 쿼리와 대시보드가 많을 때다. 코드베이스를 SQL 기반으로 전면 교체할 여건이 안 되면 InfluxDB 호환 제품을 쓰는 편이 낫다. 멀티클라우드 환경이라 AWS 종속을 최소화해야 할 때도 InfluxDB 쪽이 이식성이 높다.

반대로 처음 시계열 데이터베이스를 도입하는 경우, 팀이 SQL에 익숙한 경우, AWS 생태계와의 통합이 중요한 경우라면 LiveAnalytics가 맞다. Scheduled Queries나 IoT Core 직접 연동 같은 기능은 LiveAnalytics에만 있다.

한 가지 주의할 점이 있다. Timestream for InfluxDB는 EC2 인스턴스 기반이라 용량을 미리 선택해야 한다. LiveAnalytics처럼 서버리스로 자동 확장되지 않는다. 트래픽 패턴이 일정하지 않거나 초기 규모를 예측하기 어렵다면 LiveAnalytics가 운영 부담이 적다.

## InfluxDB, TimescaleDB와 비교

Timestream for LiveAnalytics를 외부 오픈소스 제품과 비교할 때 자주 언급되는 두 가지다.

**InfluxDB**

OSS 버전은 직접 서버를 운영해야 한다. InfluxDB Cloud는 관리형이다. 자체 쿼리 언어(Flux)가 있어 SQL을 쓰던 팀에서는 러닝커브가 있다. 쓰기 성능이 높고 데이터 모델이 시계열에 최적화되어 있다. AWS 생태계 외부 환경이거나 멀티클라우드라면 InfluxDB가 선택지가 된다.

**TimescaleDB**

PostgreSQL 위에서 동작하는 시계열 확장이다. 기존 PostgreSQL 쿼리와 완벽히 호환되고, 조인이나 복잡한 분석 쿼리를 그대로 쓸 수 있다. 팀이 PostgreSQL에 익숙하거나 관계형 데이터와 시계열 데이터를 같이 다뤄야 한다면 TimescaleDB가 낫다. 다만 서버를 직접 관리해야 하고, AWS RDS for PostgreSQL에 TimescaleDB 확장을 올리면 일부 기능 제한이 생긴다.

Timestream을 선택하는 경우는 AWS 환경에서 운영 부담 없이 시계열 데이터를 다루고 싶을 때다. 서버 용량을 계획하거나 스케일링을 신경 쓸 필요가 없다. IoT Core나 Kinesis와 연동이 간단하다. SQL 문법을 그대로 써서 쿼리 학습 비용도 낮다.

반면 Timestream은 초당 수십만 건의 극단적 고처리량 쓰기에서는 InfluxDB 대비 한계가 있다. 요금도 처리량에 따라 예측이 어렵다. 쓰기 비용은 레코드 수가 아닌 바이트 기준이라 Dimension 수를 줄이면 비용이 내려간다.

## 비용 절감 시 주의사항

Dimension 값을 너무 많이 붙이면 저장 공간이 늘어난다. "환경(prod/dev)", "서버명", "리전" 정도로 최소화하고 나머지는 Measure로 분리한다.

마그네틱 스토어 쿼리는 스캔된 데이터 양 기준으로 과금된다. 시간 범위를 반드시 명시해야 한다. 시간 필터 없이 전체 테이블을 스캔하면 수백만 건의 레코드를 다 읽고 요금이 나온다.

```sql
-- 나쁜 예: 시간 범위 없음 (전체 스캔)
SELECT * FROM "metrics-db"."server-metrics"
WHERE server_id = 'web-01'

-- 좋은 예: 시간 범위 명시
SELECT * FROM "metrics-db"."server-metrics"
WHERE server_id = 'web-01'
  AND time > ago(7d)
```

배치 쓰기를 활용하면 쓰기 비용을 줄일 수 있다. 레코드를 한 건씩 쓰는 대신 최대 100건씩 묶어서 `write_records`를 호출한다. 처리량은 같아도 API 호출 횟수와 오버헤드가 줄어든다.

자주 조회하는 집계 패턴은 Scheduled Queries로 미리 계산해두는 것이 마그네틱 스토어 스캔 비용을 낮추는 가장 확실한 방법이다.
