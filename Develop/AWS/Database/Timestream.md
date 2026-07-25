---
title: Amazon Timestream
tags: [aws, timestream, timeseries, database, iot, metrics, grafana, cloudwatch]
updated: 2026-07-25
---

# Amazon Timestream

시계열 데이터를 RDS나 DynamoDB에 쌓다 보면 공통적으로 겪는 문제가 있다. 시간이 지날수록 디스크가 찬다. 오래된 데이터를 지우는 배치 잡을 따로 만들어야 하고, 인덱스가 비대해져 최근 데이터 조회 속도도 느려진다. "최근 1시간 평균"같은 집계 쿼리는 매번 풀스캔에 가까워진다.

Timestream은 이 문제에 특화된 완전 관리형 시계열 데이터베이스다. 시간 범위 기반 쿼리, 데이터 자동 만료, 핫/콜드 스토리지 티어링이 기본으로 내장되어 있다.

## 저장 구조

Timestream은 테이블을 두 개의 스토리지 티어로 나눠 관리한다.

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

CloudWatch도 시계열 메트릭을 저장하는데, Timestream과 목적이 다르다.

CloudWatch는 AWS 서비스가 내보내는 메트릭(EC2 CPU, RDS 연결 수, Lambda 실행 시간 등)을 수집하는 데 특화되어 있다. 알람, SNS 연동, AWS 콘솔 대시보드가 CloudWatch 중심으로 돌아간다. AWS 서비스 모니터링이라면 CloudWatch가 기본이다.

Timestream은 직접 수집하는 커스텀 데이터에 적합하다. IoT 기기의 센서 데이터, 자체 개발 애플리케이션의 비즈니스 메트릭, 외부 시스템에서 가져오는 데이터처럼 AWS가 자동으로 수집해주지 않는 데이터를 쌓을 때 사용한다.

CloudWatch는 기본 보존 기간이 15개월이고 고해상도 메트릭은 3시간까지만 무료다. 수억 건의 시계열 포인트를 장기간 저장하면 CloudWatch 비용이 예상보다 많이 나온다. 이런 경우 Timestream이 더 저렴하다.

실무에서는 AWS 서비스 메트릭은 CloudWatch에, 애플리케이션 레벨 커스텀 메트릭은 Timestream에 분리해서 쌓는 구성을 많이 쓴다.

## InfluxDB, TimescaleDB와 비교

시계열 데이터베이스를 선택할 때 자주 비교하는 세 가지다.

**InfluxDB**

OSS 버전은 직접 서버를 운영해야 한다. InfluxDB Cloud는 관리형이다. 자체 쿼리 언어(Flux)가 있어 SQL을 쓰던 팀에서는 러닝커브가 있다. 쓰기 성능이 높고 데이터 모델이 시계열에 최적화되어 있다. AWS 생태계 외부 환경이거나 멀티클라우드라면 InfluxDB가 선택지가 된다.

**TimescaleDB**

PostgreSQL 위에서 동작하는 시계열 확장이다. 기존 PostgreSQL 쿼리와 완벽히 호환되고, 조인이나 복잡한 분석 쿼리를 그대로 쓸 수 있다. 팀이 PostgreSQL에 익숙하거나 관계형 데이터와 시계열 데이터를 같이 다뤄야 한다면 TimescaleDB가 낫다. 다만 서버를 직접 관리해야 하고, AWS RDS for PostgreSQL에 TimescaleDB 확장을 올리면 일부 기능 제한이 생긴다.

**Timestream을 선택하는 경우**

AWS 환경에서 운영 부담 없이 시계열 데이터를 다루고 싶을 때다. 서버 용량을 계획하거나 스케일링을 신경 쓸 필요가 없다. IoT Core나 Kinesis와 연동이 간단하다. SQL 문법을 그대로 써서 쿼리 학습 비용도 낮다.

반면 Timestream은 쓰기 지연이 있다. 레코드가 실제로 메모리 스토어에 반영되는 시간이 밀리초 단위지만, 초당 수십만 건의 극단적 고처리량 쓰기에서는 InfluxDB 대비 한계가 있다. 요금도 처리량에 따라 예측이 어렵다. 쓰기 비용은 레코드 수가 아닌 바이트 기준이라 Dimension 수를 줄이면 비용이 내려간다.

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
