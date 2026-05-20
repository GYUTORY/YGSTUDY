---
title: VPC Flow Logs
tags: [aws, vpc, flow-logs, networking, observability, athena, troubleshooting, nat-gateway, transit-gateway]
updated: 2026-05-20
---

# VPC Flow Logs

## 개요

VPC Flow Logs는 VPC 안의 ENI를 드나드는 IP 트래픽 메타데이터를 캡처하는 기능이다. 페이로드는 잡지 않는다. 출발지/목적지 IP, 포트, 프로토콜, 패킷·바이트 수, ACCEPT/REJECT 결과, 시간 구간 같은 5튜플 기반 요약만 남긴다. 패킷 캡처가 필요하면 Traffic Mirroring을 따로 켜야 한다.

운영하다 보면 "이 RDS로 누가 붙는 거지?", "NAT Gateway 처리 바이트가 왜 어제부터 5배 뛰었지?", "보안 그룹이 막은 트래픽이 도대체 어디서 오는 거야?" 같은 질문이 매주 한 번씩 온다. Flow Logs를 미리 켜두지 않았으면 그 시점의 트래픽을 재현할 방법이 없다. 그래서 신규 VPC 만들 때는 일단 켜놓는 편이 낫다.

다만 켜는 순간 데이터 양이 즉시 늘어난다. 샘플링 옵션이 없어서 1:1 캡처고, S3/CloudWatch Logs 비용이 따라붙는다. "그냥 켜두면 되겠지" 라는 생각으로 모든 VPC에 CloudWatch Logs로 떨궜다가 월말 청구서 보고 놀라는 경우가 많다.

## 캡처 범위 — ENI / 서브넷 / VPC

Flow Logs는 세 가지 단위로 켤 수 있다. 어느 쪽이든 결과 레코드 형식은 동일하지만 캡처 대상이 달라진다.

- **ENI 단위**: 특정 네트워크 인터페이스 하나만 본다. 문제 인스턴스 한 대만 디버깅할 때 쓴다. 가장 좁은 범위, 가장 적은 데이터.
- **서브넷 단위**: 그 서브넷 안의 모든 ENI를 캡처한다. 서브넷에 EC2를 새로 띄우면 자동으로 따라잡힌다.
- **VPC 단위**: VPC 안의 모든 ENI를 캡처한다. 보통 운영 환경에서는 이걸 켠다. 신규 서브넷·신규 인스턴스를 사람이 잊고 누락시킬 일이 없다.

세 단위를 동시에 켜면 같은 트래픽이 중복 기록된다. VPC 단위로 켜둔 상태에서 ENI 단위를 또 켜면 동일 패킷이 두 로그에 모두 찍히고 저장 비용도 두 배가 된다. 디버깅이 끝났는데 ENI 단위 로그를 끄는 걸 깜빡하는 경우가 진짜 자주 있다. 분기 한 번씩 정리하는 게 좋다.

캡처 대상에서 빠지는 트래픽도 정해져 있다. Amazon DNS(169.254.169.253), 메타데이터 서비스(169.254.169.254), Windows 라이선스 활성화, DHCP, 미러링된 트래픽, AWS 예약 IP 대역과의 일부 통신은 Flow Logs에 안 찍힌다. "분명 DNS를 쓰는데 왜 안 보이지" 라는 질문이 나오는 이유다.

## 전송 대상별 트레이드오프

전송 대상은 세 가지다. S3, CloudWatch Logs, Kinesis Data Firehose. 각각 비용·지연·후속 처리 방식이 다르다.

### S3

- **비용**: 가장 싸다. 데이터 인입(ingest) 비용 + S3 저장 비용만 든다. CloudWatch Logs 대비 보통 1/4~1/5 수준.
- **지연**: 5분 간격으로 객체가 떨어진다. 실시간 분석은 못 한다.
- **포맷**: Parquet 선택 가능. Athena 쿼리할 거면 처음부터 Parquet으로 떨구는 게 맞다. plain text로 쌓다가 나중에 변환하면 같은 데이터를 두 번 저장하게 된다.
- **파티셔닝**: Hive 호환 파티셔닝(`year=YYYY/month=MM/day=DD/hour=HH`)을 켤 수 있다. Athena에서 파티션 프루닝이 먹어서 스캔 비용이 크게 줄어든다. 안 켜면 매번 풀 스캔이라 쿼리 한 번에 수 GB씩 나간다.
- **추천 시점**: 장기 보관, 사후 분석, 감사 용도. 99%의 운영 케이스가 여기에 해당한다.

### CloudWatch Logs

- **비용**: 인입 비용이 GB당 0.5~0.76 USD 수준이라 비싸다. 트래픽 많은 VPC에 켜면 한 달에 수천 달러 우습게 나간다.
- **지연**: 수십 초~분 단위. S3보다는 빠르지만 "실시간"이라고 부르긴 애매하다.
- **장점**: CloudWatch Logs Insights로 바로 쿼리할 수 있다. 메트릭 필터를 걸어서 알람도 만들 수 있다. "REJECT가 분당 1만 건 넘으면 알람" 같은 룰을 거기서 바로 짠다.
- **추천 시점**: 알람·실시간 모니터링이 필요한 핵심 VPC. 그것도 전체가 아니라 의심 구간 디버깅용으로 한시적으로 켜는 편이 비용상 안전하다.

### Kinesis Data Firehose

- **비용**: Firehose 인입 비용 + 최종 대상(S3/OpenSearch/Splunk) 비용.
- **지연**: 버퍼링 설정에 따라 60초~몇 분.
- **추천 시점**: OpenSearch나 Datadog·Splunk 같은 SIEM에 실시간으로 흘려보낼 때. S3로 직접 떨굴 거면 굳이 Firehose를 끼울 이유가 없다.

실무에서는 보통 "S3 + Parquet + Hive 파티셔닝 + Athena" 조합을 기본으로 두고, 알람 필요한 곳만 CloudWatch Logs를 추가로 켠다. 같은 트래픽을 두 군데로 보내려면 Flow Log 정의를 두 개 만들면 된다. AWS 콘솔에서는 "Flow log destination"을 두 번 설정한다는 뜻이다.

## 로그 포맷 — default vs custom

기본 포맷 14개 필드는 다음 정도가 들어 있다.

```
version account-id interface-id srcaddr dstaddr srcport dstport protocol
packets bytes start end action log-status
```

처음 켜면 이걸로 시작하지만, 디버깅하다 보면 곧 부족함을 느낀다. 특히 다음 세 상황에서.

### pkt-srcaddr / pkt-dstaddr — NAT 뒤 진짜 출발지 보기

`srcaddr`/`dstaddr`는 ENI 관점의 IP다. NAT Gateway 뒤에 있는 프라이빗 인스턴스가 외부로 나갈 때 Flow Log의 `srcaddr`는 NAT Gateway의 ENI IP로 찍힌다. "어느 인스턴스가 외부 IP X로 트래픽을 보냈는가" 를 추적하려면 `pkt-srcaddr`(실제 패킷의 출발지 IP)가 필요하다.

기본 포맷에는 없다. custom format으로 켜야 한다. NAT Gateway가 끼는 VPC에서는 사실상 필수다.

### traffic-path — 트래픽이 어느 게이트웨이로 나갔는가

`traffic-path`는 송신 트래픽이 어떤 경로로 VPC를 빠져나갔는지 정수 코드로 알려준다. 1=같은 VPC 내, 2=IGW/Egress-Only IGW, 3=VGW, 4=VPC Peering, 5=Transit Gateway, 6=Local Gateway, 7=Gateway Endpoint, 8=PrivateLink Interface Endpoint 등.

라우팅이 복잡한 VPC에서 "이 트래픽 도대체 어디로 나간 거지?" 를 정답으로 알려주는 유일한 필드다. NAT Gateway 비용 폭증 원인 파악할 때 `traffic-path = 2`(IGW로 나간 것) 와 NAT Gateway ENI로 들어온 트래픽을 비교하면 어느 인스턴스가 외부 통신을 일으켰는지 빠르게 좁힌다.

### flow-direction — ingress인가 egress인가

`flow-direction`은 ENI 기준으로 트래픽이 들어오는지(`ingress`) 나가는지(`egress`)를 명시한다. `srcaddr`/`dstaddr`만 보고도 추정은 가능하지만 같은 VPC 내부 통신이나 PrivateLink 트래픽에서는 헷갈리는 경우가 있다. 이 필드를 켜두면 Athena에서 `WHERE flow_direction = 'egress'` 한 줄로 정확히 골라낸다.

### 그 외 자주 켜는 필드

- `vpc-id`, `subnet-id`, `instance-id`: 멀티 VPC 환경에서 여러 로그를 한 테이블로 묶어 보고 싶을 때.
- `tcp-flags`: SYN만 폭주하는지(스캐닝/DDoS) 정상 세션인지 구분할 때.
- `region`, `az-id`: 여러 리전 로그를 한 버킷에 모을 때.
- `sublocation-type`, `sublocation-id`: Wavelength·Outposts·Local Zones 사용 시.

custom format은 한번 정해두면 나중에 필드 추가가 까다롭다. Flow Log 정의를 새로 만들고 기존 것을 지우는 식이라 Athena 테이블 스키마도 재정의해야 한다. 신규 VPC 만들 때 처음부터 `pkt-srcaddr`, `pkt-dstaddr`, `traffic-path`, `flow-direction`, `vpc-id`, `subnet-id`, `instance-id` 까지 넣는 걸 권장한다. 데이터 한 줄당 몇십 바이트 더 늘어나는 비용보다 트러블슈팅할 때 못 보는 비용이 훨씬 크다.

## ACCEPT / REJECT 필터 실수

Flow Log를 만들 때 traffic type을 ACCEPT / REJECT / ALL 중에 고른다. 여기서 실수가 잘 나온다.

- **REJECT만 켠 경우**: 보안 그룹·NACL이 막은 트래픽만 본다. "차단된 게 누가 어디서 왔는가" 를 빠르게 본다는 점에서 보안용으로는 합리적이지만, 운영 트러블슈팅에는 거의 무용지물이다. "내 ALB에서 백엔드로 가는 트래픽이 끊겼다" 류의 문제는 ACCEPT 로그가 있어야 추적된다.
- **ACCEPT만 켠 경우**: 보안 그룹이 막아서 안 들어온 트래픽은 영영 모른다. 보안 사고 조사할 때 가장 답답한 상태.
- **ALL이 정답**: 데이터 양이 늘어나는 게 부담이지만 대부분의 경우 ALL이 맞다. REJECT/ACCEPT를 따로 켜는 건 정말 비용 문제가 심각할 때만.

특히 헷갈리는 케이스 — NACL이 막은 트래픽은 `action = REJECT`로 찍히지만, 보안 그룹이 outbound로 막은 트래픽은 SG가 stateful이라 응답 패킷 자체가 안 생긴다. 그래서 "내 EC2가 응답을 안 한다"는 상황에서 ingress REJECT만 찾으면 영영 못 찾고, ingress ACCEPT는 찍혀 있는데 egress가 없는 패턴을 봐야 답이 나온다. ALL을 켜야 보이는 패턴이다.

`log-status` 필드도 같이 본다. `OK`면 정상, `NODATA`는 캡처 구간에 트래픽이 없었음, `SKIPDATA`는 캡처 한도 초과로 일부 레코드가 빠졌다는 뜻이다. SKIPDATA가 자주 보이면 트래픽이 너무 많아서 일부 손실되고 있다는 신호라 분석 결과가 부정확할 수 있다.

## Athena 테이블 정의

S3에 Parquet으로 떨군다고 가정하고 Athena 테이블을 만든다. Hive 파티셔닝을 켰다고 가정한 예시.

```sql
CREATE EXTERNAL TABLE vpc_flow_logs (
  version int,
  account_id string,
  interface_id string,
  srcaddr string,
  dstaddr string,
  srcport int,
  dstport int,
  protocol bigint,
  packets bigint,
  bytes bigint,
  start_time bigint,
  end_time bigint,
  action string,
  log_status string,
  vpc_id string,
  subnet_id string,
  instance_id string,
  pkt_srcaddr string,
  pkt_dstaddr string,
  traffic_path int,
  flow_direction string,
  tcp_flags int
)
PARTITIONED BY (
  `aws-account-id` string,
  `aws-service` string,
  `aws-region` string,
  year string,
  month string,
  day string,
  hour string
)
STORED AS PARQUET
LOCATION 's3://my-flow-logs-bucket/AWSLogs/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.year.type' = 'integer',
  'projection.year.range' = '2024,2030',
  'projection.month.type' = 'integer',
  'projection.month.range' = '1,12',
  'projection.month.digits' = '2',
  'projection.day.type' = 'integer',
  'projection.day.range' = '1,31',
  'projection.day.digits' = '2',
  'projection.hour.type' = 'integer',
  'projection.hour.range' = '0,23',
  'projection.hour.digits' = '2'
);
```

Partition projection을 쓰면 `MSCK REPAIR TABLE`을 주기적으로 돌릴 필요가 없다. 새 파티션이 자동으로 인식된다.

## 트러블슈팅용 Athena 쿼리

### 특정 ENI로 들어온 거부 트래픽 추적

보안팀에서 "최근 24시간 동안 우리 RDS ENI에 거부된 접속 시도가 어디서 왔는지 보고 싶다" 라는 요청이 자주 들어온다.

```sql
SELECT
  srcaddr,
  dstport,
  protocol,
  COUNT(*) AS attempts,
  SUM(packets) AS total_packets
FROM vpc_flow_logs
WHERE year='2026' AND month='05' AND day BETWEEN '19' AND '20'
  AND interface_id = 'eni-0abcd1234ef567890'
  AND action = 'REJECT'
  AND flow_direction = 'ingress'
GROUP BY srcaddr, dstport, protocol
ORDER BY attempts DESC
LIMIT 50;
```

`srcaddr` 상위 N개를 보면 보통 패턴이 드러난다. 한 IP에서 다양한 포트로 들어오면 포트 스캐닝, 여러 IP에서 같은 포트로 들어오면 의도된 트래픽이 보안 그룹에 빠진 케이스.

### NAT Gateway 비용 폭증 원인 파악

NAT Gateway는 처리 바이트당 과금이라 어느 인스턴스가 외부로 많이 나가는지 찾으면 비용이 잡힌다. NAT Gateway의 ENI ID를 먼저 확인하고 그 ENI를 통과한 트래픽 중 `pkt-srcaddr`(실제 출발 인스턴스 IP) 기준으로 집계한다.

```sql
SELECT
  pkt_srcaddr,
  pkt_dstaddr,
  dstport,
  SUM(bytes) / 1024 / 1024 / 1024 AS gb_transferred,
  COUNT(*) AS flow_count
FROM vpc_flow_logs
WHERE year='2026' AND month='05' AND day='20'
  AND interface_id = 'eni-natgw-0abc...'
  AND flow_direction = 'egress'
  AND action = 'ACCEPT'
GROUP BY pkt_srcaddr, pkt_dstaddr, dstport
ORDER BY gb_transferred DESC
LIMIT 30;
```

`pkt_srcaddr`가 같은 인스턴스가 상위에 몰려 있으면 그 인스턴스의 외부 통신을 줄이거나, 가능하면 VPC Endpoint(S3·DynamoDB는 Gateway Endpoint, 나머지는 Interface Endpoint)로 전환한다. S3·ECR·Secrets Manager 트래픽이 NAT를 타고 있는 경우가 가장 흔하다. Endpoint로 빼면 NAT 처리 비용과 데이터 전송 비용이 동시에 떨어진다.

`traffic_path` 필드를 켜뒀으면 더 빠르다.

```sql
SELECT pkt_srcaddr, SUM(bytes)/1024/1024/1024 AS gb
FROM vpc_flow_logs
WHERE year='2026' AND month='05' AND day='20'
  AND traffic_path = 2  -- IGW로 나간 트래픽
  AND flow_direction = 'egress'
GROUP BY pkt_srcaddr
ORDER BY gb DESC;
```

### 의심 외부 IP와의 통신 전체 추출

```sql
SELECT
  from_unixtime(start_time) AS started_at,
  interface_id,
  pkt_srcaddr,
  pkt_dstaddr,
  srcport,
  dstport,
  action,
  bytes
FROM vpc_flow_logs
WHERE year='2026' AND month='05' AND day='20'
  AND (srcaddr = '203.0.113.45' OR dstaddr = '203.0.113.45')
ORDER BY started_at;
```

### TOP talker 일별 추출

```sql
SELECT
  day,
  pkt_srcaddr,
  pkt_dstaddr,
  SUM(bytes) AS total_bytes
FROM vpc_flow_logs
WHERE year='2026' AND month='05'
  AND flow_direction = 'egress'
GROUP BY day, pkt_srcaddr, pkt_dstaddr
ORDER BY day, total_bytes DESC;
```

## Transit Gateway Flow Logs와의 차이

Transit Gateway에 붙는 트래픽은 VPC Flow Logs로 어느 정도 보이지만, TGW 내부의 어느 attachment를 거쳤는지, 어느 라우팅 테이블이 매칭됐는지는 안 보인다. 그래서 TGW 전용 Flow Logs가 따로 있다.

차이점은 다음과 같다.

- **캡처 대상**: VPC Flow Logs는 ENI 트래픽, TGW Flow Logs는 Transit Gateway를 거치는 모든 트래픽.
- **추가 필드**: TGW Flow Logs는 `tgw-id`, `tgw-attachment-id`, `tgw-src-vpc-account-id`, `tgw-dst-vpc-account-id`, `tgw-src-vpc-id`, `tgw-dst-vpc-id`, `tgw-src-subnet-id`, `tgw-dst-subnet-id`, `tgw-src-eni`, `tgw-dst-eni`, `resource-type`, `packets-lost-no-route` 등이 추가된다. 어느 VPC가 어느 VPC로 흘려보냈는지 한 줄에 다 들어 있다.
- **REJECT 의미**: TGW에서 REJECT는 라우팅 테이블에 경로가 없거나 attachment가 association되지 않아 드롭된 경우다. 보안 그룹과는 무관하다. `packets-lost-no-route`로 따로 카운트된다.
- **전송 대상**: S3, CloudWatch Logs, Firehose 동일.
- **비용 구조**: VPC Flow Logs와 동일하게 처리량 기반. 다만 TGW를 지나는 트래픽은 보통 멀티 VPC를 합친 것이라 한 곳에 모이는 데이터 양이 더 크다.

여러 VPC가 TGW로 연결된 환경에서는 VPC Flow Logs와 TGW Flow Logs를 둘 다 켜는 게 일반적이다. VPC 안의 ENI 단위 디버깅은 VPC 로그, "VPC A의 어느 서브넷이 VPC B로 얼마나 보냈는가" 같은 cross-VPC 분석은 TGW 로그가 답한다.

## 데이터 양 폭증 주의사항

Flow Logs는 샘플링이 없다. 100% 캡처다. 이게 가장 자주 발 등을 찍는 부분이다.

- **트래픽이 많으면 로그가 폭증한다**: 처리량 1 Gbps짜리 VPC에 ALL 트래픽 Flow Log를 켜면 하루에 수십 GB~수백 GB가 쌓인다. CloudWatch Logs로 보내면 월말 청구서가 EC2 비용보다 커지는 일이 진짜로 일어난다.
- **aggregation interval 조정**: 기본 600초(10분), 옵션으로 60초까지 줄일 수 있다. 60초로 줄이면 같은 트래픽이라도 레코드 수가 5~10배 늘어난다. 정밀 분석이 필요한 짧은 구간에만 60초를 쓰고, 평시에는 600초가 합리적이다.
- **VPC 전체에 켜기 전 한 번 추산**: VPC FlowLogs metric (`AWS/Logs:IncomingBytes`나 `AWS/Usage`)으로 일 단위 양을 먼저 본다. 추산 없이 켜고 한 달 뒤에 보면 늦다.
- **로그 자체가 만드는 트래픽**: CloudWatch Logs 전송은 AWS 내부 트래픽이라 데이터 전송 요금은 안 붙지만, S3로 떨궈도 같은 리전 안이면 추가 비용이 없다. 다만 cross-region으로 보내면 데이터 전송 요금이 붙는다. 로그 버킷은 같은 리전에 두는 게 맞다.
- **보관 정책**: S3 Lifecycle로 30일 후 IA, 90일 후 Glacier로 옮긴다. CloudWatch Logs는 retention을 명시적으로 걸지 않으면 영구 보관이라 비용이 누적된다. 의도가 아니라면 보통 14~30일로 자른다.
- **불필요한 Flow Log 정의 중복**: 앞서 말한 것처럼 ENI/서브넷/VPC 단위로 여러 번 켜져 있으면 같은 트래픽이 여러 번 기록된다. 분기마다 `describe-flow-logs`로 전체 목록을 한 번 본다.

```bash
aws ec2 describe-flow-logs \
  --query 'FlowLogs[].[FlowLogId,ResourceId,LogDestination,TrafficType,LogFormat]' \
  --output table
```

이 명령으로 계정 안의 모든 Flow Log 정의를 훑어보고, 의도치 않은 중복이나 잊혀진 정의가 있으면 정리한다. 특히 사라진 ENI나 삭제된 서브넷에 매달려 있던 정의가 남아 있는 경우가 있다.

## 실무에서 자주 만나는 함정

- **Flow Logs는 만든 시점 이후 트래픽만 잡는다**. 사고가 터지고 나서 켜면 그 시점 이전 트래픽은 영영 못 본다. 운영 VPC는 처음부터 켜둔다.
- **REJECT가 안 보인다고 안전한 게 아니다**. SG는 stateful이라 outbound로 막힌 트래픽은 응답이 안 가는 형태로 나타날 뿐 REJECT로 안 찍힌다.
- **Athena 비용도 같이 본다**. 파티션 프루닝 없이 한 달치를 풀스캔하면 한 쿼리에 수십 GB 스캔되어 비용이 나온다. `WHERE year/month/day` 조건을 반드시 넣는 습관을 들인다.
- **계정 간 통합**: 멀티 계정 조직에서는 Organizations 차원에서 모든 계정의 Flow Logs를 중앙 S3 버킷으로 모은다. 계정마다 따로 분석하면 cross-account 트래픽이 짤린다.
- **개인정보**: Flow Logs는 IP·포트 메타데이터지만 그 자체로 식별정보가 될 수 있다. 외부 공유나 장기 보관 시 컴플라이언스 검토가 필요한 경우가 있다.
- **VPC 삭제 시**: VPC를 지우기 전에 Flow Log 정의를 먼저 지운다. VPC 삭제하면 자동으로 따라 사라지긴 하지만, S3에 누적된 로그는 그대로 남아 있다는 점을 잊기 쉽다.
