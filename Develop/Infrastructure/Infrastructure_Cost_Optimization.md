---
title: 클라우드 인프라 비용 최적화
tags: [infrastructure, cost-optimization, finops, aws, reserved-instance, spot, savings-plan, right-sizing, s3, nat-gateway, cost-anomaly]
updated: 2026-06-04
---

# 클라우드 인프라 비용 최적화

## 1. 비용 최적화는 청구서를 읽는 일에서 시작한다

처음 클라우드 비용 최적화를 맡았을 때 내가 가장 먼저 한 실수는 "어디서부터 줄일까"부터 고민한 것이었다. 그게 아니다. 청구서를 읽을 줄 모르면 어디를 줄여도 다음 달 청구서가 왜 또 늘었는지 모른다. 인프라 비용 최적화는 절약이 목적이 아니라 "비용이 어디로 흘러가는지를 한 줄도 빠짐없이 설명할 수 있게 되는 것"이 목적이다. 설명할 수 있어야 다음 결정을 한다.

5년차쯤 인프라를 보면서 배운 건 세 가지다. 첫째, 비싼 항목은 보통 EC2가 아니다. EC2는 눈에 잘 띄어서 모두가 신경 쓰는데, 정작 큰 구멍은 NAT Gateway 데이터 처리비, 리전 간 트래픽, 방치된 EBS 스냅샷, CloudWatch 로그 보존 같은 데서 난다. 둘째, Reserved/Savings Plan은 "남으면 손해, 모자라면 의미 없음"이라는 비대칭이 있어서 약정 비율을 보수적으로 잡아야 한다. 셋째, idle 리소스는 사람이 안 보면 무한히 자란다. 자동으로 찾아내고 자동으로 알리는 파이프라인이 없으면 분기마다 손으로 청소해야 하는데, 그건 결국 안 한다.

이 문서는 AWS를 기준으로 쓰지만 GCP, Azure도 이름만 다를 뿐 구조는 거의 같다. 약정 할인, 스팟, 스토리지 클래스, 데이터 전송 함정, 청구서 분석, anomaly 탐지를 순서대로 본다.

```
                    클라우드 비용
                         │
        ┌────────────┬───┴────┬─────────────┐
        │            │        │             │
      컴퓨트       스토리지   네트워크      관리/기타
        │            │        │             │
   ┌────┼────┐    ┌──┴──┐  ┌──┴──┐    CloudWatch
   │    │    │    │     │  │     │    Logs / KMS
 On-    RI   Spot S3   EBS NAT   Cross-
Demand  /SP       /Glac     GW   Region
                                  Egress
```

---

## 2. 약정 할인 — Reserved Instance, Savings Plan, Spot

### 2.1 세 가지 할인 모델의 차이

AWS만 봐도 컴퓨트 비용을 줄이는 약정 모델이 세 가지다. Reserved Instance(RI), Savings Plan(SP), Spot Instance. 이름만 들으면 비슷해 보이는데 실제로는 약정의 단위와 유연성이 다르다.

| 구분 | 약정 단위 | 유연성 | 할인율 | 중단 위험 |
|---|---|---|---|---|
| Standard RI | 인스턴스 타입·리전·플랫폼 | 낮음 | 최대 ~72% | 없음 |
| Convertible RI | 패밀리 안에서 타입 변경 | 중간 | 최대 ~66% | 없음 |
| Compute Savings Plan | "시간당 $X" 약정, 리전/타입 무관 | 높음 | 최대 ~66% | 없음 |
| EC2 Instance SP | 패밀리·리전 고정 | 중간 | 최대 ~72% | 없음 |
| Spot | 약정 없음, 입찰 | 매우 높음 | 최대 ~90% | 2분 전 통보 후 회수 |

내가 실무에서 쓴 기준은 단순하다. **변하지 않는 baseline은 Savings Plan, baseline을 넘는 변동분은 On-Demand, 중단 가능한 워크로드는 Spot.** RI는 거의 안 쓴다. Compute SP가 RI보다 유연한데 할인율 차이가 크지 않기 때문이다. 굳이 RI를 쓰는 경우는 RDS, ElastiCache, OpenSearch처럼 SP가 적용되지 않는 매니지드 서비스뿐이다.

### 2.2 약정 비율은 보수적으로

처음에는 욕심이 나서 baseline의 100%를 약정으로 덮으려 한다. 그러면 안 된다. 약정은 사용량이 줄어도 그대로 청구된다. 트래픽이 줄거나 아키텍처가 바뀌어 인스턴스 패밀리를 옮기면 약정만 남아 떠다닌다.

내가 쓰는 비율은 이렇다.

- **컴퓨트 baseline의 60~70%**만 SP로 덮는다.
- baseline 산정 기준은 최근 90일의 시간당 사용량 중 25퍼센타일 정도다. 평균이 아니라 하위 25% 지점을 잡으면 "최소 이만큼은 항상 쓴다"가 보장된다.
- 약정 기간은 가능하면 1년. 3년 약정은 할인율이 더 크지만 3년 뒤의 아키텍처를 예측할 수 없다. 회사가 EKS에서 Fargate로 옮기거나 ARM(Graviton)으로 전환하면 3년 RI가 묶인다.
- payment 옵션은 No Upfront 또는 Partial Upfront를 선호한다. All Upfront는 할인율이 1~2%p 정도 더 크지만 현금 흐름과 회계 처리(선급 비용 자산화)가 복잡해진다.

### 2.3 Spot은 "회수돼도 괜찮은 일"에만

Spot은 가격이 매력적이지만 2분 전 통보 후 회수된다. 회수 빈도는 인스턴스 타입과 가용 영역에 따라 다르고, AWS Spot Instance Advisor에서 frequency of interruption을 미리 확인할 수 있다.

Spot에 올리기 적합한 워크로드는 명확하다.

- 배치 처리, ETL, 데이터 가공
- CI/CD 빌드 러너
- 학습용 ML training (체크포인트 저장이 있는 경우)
- stateless 웹 서버 중 일부 (ALB 뒤에서 다른 capacity와 섞어서)

Spot에 올리면 망하는 워크로드도 명확하다.

- stateful 서비스 (DB, 메시지 브로커의 leader)
- 세션이 살아있어야 하는 long-running 작업 (회수 시 세션 끊김)
- 응답 지연이 1초도 용납 안 되는 결제 같은 critical 경로

실무에서 Spot을 안전하게 쓰는 트릭은 **여러 인스턴스 타입을 한 ASG에 섞어 넣는 것**이다. m5.large 하나만 입찰하면 그 타입이 부족할 때 한꺼번에 회수되는데, m5/m5a/m5n/m6i를 large부터 xlarge까지 10개쯤 후보로 넣어두면 동시 회수 확률이 크게 떨어진다. EKS에서는 Karpenter가 이런 다중 타입 선택을 자동으로 해준다.

### 2.4 Graviton(ARM) 전환의 비용 효과

같은 워크로드를 x86에서 ARM(Graviton2/3/4)으로 옮기면 시간당 가격이 약 20% 싸고, 성능도 비슷하거나 더 빠른 경우가 많다. 컨테이너 이미지를 multi-arch로 빌드하고, 의존 라이브러리가 ARM을 지원하는지 확인하기만 하면 된다. Node.js, Python, Go는 거의 문제없다. JVM도 OpenJDK 17 이후는 잘 돈다. 골치 아픈 건 네이티브 의존성을 가진 일부 Python 패키지나 오래된 C 확장 모듈인데, 이건 빌드 단계에서 한 번만 잡으면 된다.

ARM 전환은 코드 한 줄 안 바꾸고 컴퓨트 비용 20%를 깎는 거의 유일한 방법이라 우선순위가 높다. 다만 모든 매니지드 서비스가 Graviton을 지원하는 건 아니라서, RDS·ElastiCache·OpenSearch는 인스턴스 클래스에 `g`가 붙은 것만 ARM이다.

---

## 3. Idle 리소스 — 안 쓰는 게 가장 비싸다

### 3.1 가장 흔한 idle 리소스 목록

처음 비용을 정리할 때 가장 어이없었던 건 "분명히 안 쓰는데 돈은 나가는" 것들이었다. 목록은 거의 정해져 있다.

| 리소스 | idle 판단 기준 | 비용 누수 |
|---|---|---|
| 미연결 EBS 볼륨 | `attached` 상태가 아닌 볼륨 | gp3 1TB ≈ 월 $80 |
| 미사용 EIP | 인스턴스에 연결되지 않은 Elastic IP | 1개당 월 $3.6 |
| 미사용 NAT Gateway | 트래픽이 거의 없는데 살아있음 | 시간당 $0.045 + 처리량 |
| 미사용 Load Balancer | target group이 비었거나 트래픽 0 | ALB 월 ~$18 + LCU |
| 오래된 EBS 스냅샷 | 6개월 이상 된 스냅샷 | GB당 월 $0.05 |
| 오래된 AMI | 더 이상 안 쓰는 커스텀 AMI의 스냅샷 | 위와 동일 |
| 미사용 RDS 스냅샷 | manual 스냅샷이 안 지워짐 | GB당 월 $0.095 |
| stopped EC2의 EBS | 인스턴스는 꺼두었지만 디스크는 계속 청구 | gp3 기준 위와 동일 |
| 미사용 CloudWatch Log Group | retention 무한, 트래픽 없는 그룹 | GB당 월 $0.03 |

이 중 가장 많이 새는 건 보통 EBS 스냅샷과 CloudWatch 로그다. 스냅샷은 AMI를 만들 때마다 같이 생기는데 AMI를 지워도 스냅샷은 안 지워지는 경우가 많다. 1년쯤 운영하면 수천 개씩 쌓인다.

### 3.2 idle 리소스를 찾는 쿼리

수동으로 찾으면 안 된다. 한 번 청소해도 다음 분기에 또 쌓인다. AWS Config나 Cost Explorer, 또는 직접 CLI로 정기 스캔 파이프라인을 만든다.

```bash
# 미연결 EBS 볼륨 찾기
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].[VolumeId,Size,CreateTime,Tags]' \
  --output table

# 미사용 EIP 찾기
aws ec2 describe-addresses \
  --query 'Addresses[?AssociationId==null].[AllocationId,PublicIp]' \
  --output table

# 6개월 이상 된 EBS 스냅샷
aws ec2 describe-snapshots --owner-ids self \
  --query "Snapshots[?StartTime<='$(date -v-6m +%Y-%m-%d)'].[SnapshotId,VolumeSize,StartTime,Description]" \
  --output table
```

이걸 Lambda에 올려서 매주 돌리고, 결과를 Slack으로 보낸다. 더 적극적으로는 14일 이상 미연결된 EBS 볼륨에 `auto-delete=true` 태그를 자동으로 붙이고, 30일 후에도 태그가 그대로면 삭제하는 정책을 만든다. 손으로 청소하는 건 결국 안 하기 때문이다.

### 3.3 dev/staging 환경의 야간 정지

dev/staging 환경은 평일 9~7시만 켜두면 비용이 약 70% 줄어든다. 한 달 720시간 중 50시간 정도만 살아있게 된다. AWS Instance Scheduler나 자체 Lambda + EventBridge로 ASG의 desired capacity를 0으로 만들면 된다. RDS는 stop이 7일까지만 유지되니까, 더 길게 끌 거면 매주 한 번 자동 재시작-재정지 사이클이 필요하다. Aurora Serverless v2로 옮기면 이 문제가 없어진다.

---

## 4. Right-sizing — 정말로 그 사이즈가 필요한가

### 4.1 right-sizing의 함정

right-sizing은 "안 쓰는 만큼 작은 인스턴스로 옮기자"인데, 막상 해보면 CPU 사용률 30%를 보고 인스턴스를 절반으로 줄였더니 p99 지연이 두 배가 되는 일이 종종 있다. 평균 CPU는 의미가 없다. 봐야 할 건 다음 네 가지다.

1. **CPU의 p95 또는 p99** — 평균이 아니라 피크. 평균 30%여도 피크가 90%면 못 줄인다.
2. **메모리 사용률 p95** — JVM, Node는 메모리가 더 먼저 터진다. CloudWatch 기본 메트릭에는 메모리가 없으니 CloudWatch Agent로 따로 수집해야 한다.
3. **네트워크 throughput** — 작은 인스턴스는 네트워크 대역폭도 작다. m5.large는 최대 10Gbps burstable이지만 baseline은 ~0.75Gbps다.
4. **EBS throughput과 IOPS** — 인스턴스 타입별로 EBS 처리량 한도가 있다. 작은 인스턴스로 옮기면 디스크 I/O가 병목이 된다.

### 4.2 도구별 right-sizing 접근

AWS Compute Optimizer가 자동으로 추천을 준다. 14일치 CloudWatch 메트릭을 보고 "이 인스턴스는 한 단계 작은 타입으로 가도 됨" 같은 권고를 한다. 무료고, 정확도는 70% 정도다. 메모리 메트릭이 없으면 권고가 보수적으로 나온다.

EKS/ECS에서는 Vertical Pod Autoscaler(VPA)의 recommendation 모드를 켜두고 일주일쯤 관찰한 뒤 requests/limits를 조정한다. VPA를 auto 모드로 켜는 건 추천하지 않는다. Pod이 재시작되면서 의도치 않게 트래픽이 끊긴다.

right-sizing은 한 번 하면 끝이 아니라 분기마다 한 번씩 봐야 한다. 트래픽 패턴이 바뀌고 코드도 바뀐다. 자동화하지 않으면 분기 때마다 며칠씩 묶인다.

### 4.3 다운사이징 전 안전장치

작은 인스턴스로 옮기기 전에 항상 한 번은 사전 검증을 한다.

- staging이나 canary에 먼저 같은 사이즈를 적용하고 24시간 관찰
- 부하 테스트로 평소 트래픽의 1.5~2배를 흘려보고 응답 시간이 깨지지 않는지 확인
- 메모리 swap이 발생하지 않는지 확인. swap이 시작되면 응답 시간이 절벽처럼 망가진다.

다운사이징은 가역적이라 망가지면 되돌리면 되지만, 그 사이 5분 동안 들어온 사용자가 본 503은 되돌릴 수 없다.

---

## 5. 데이터 전송 비용 — 가장 자주 빠지는 함정

### 5.1 NAT Gateway가 비용의 절반을 먹는다

NAT Gateway는 두 줄로 요약된다. **시간당 $0.045 + 처리한 GB당 $0.045**. 시간당 비용은 한 달이면 약 $33이다. 큰돈은 아니다. 진짜 문제는 GB당 $0.045인 데이터 처리비다.

흔한 시나리오. private subnet에 있는 EKS 노드들이 S3, ECR, DynamoDB에 매일 수 TB씩 접근한다. 이 트래픽이 전부 NAT Gateway를 거치면 한 달에 수천 달러가 나간다. S3는 가까이에 있고 무료처럼 보이는데, NAT를 거치는 순간 트래픽 처리비가 붙는다.

해결은 VPC Endpoint다.

| 대상 서비스 | Endpoint 종류 | NAT 우회 효과 |
|---|---|---|
| S3 | Gateway Endpoint | 무료, NAT 완전 우회 |
| DynamoDB | Gateway Endpoint | 무료, NAT 완전 우회 |
| ECR (api, dkr) | Interface Endpoint | 시간당 ~$0.01 × AZ |
| Secrets Manager | Interface Endpoint | 위와 동일 |
| STS, KMS, SSM | Interface Endpoint | 위와 동일 |
| CloudWatch Logs | Interface Endpoint | 위와 동일 |

Gateway Endpoint(S3, DynamoDB)는 무료라서 안 만들 이유가 없다. Interface Endpoint는 AZ당 시간 비용이 붙어서 트래픽 양에 따라 NAT보다 비싼지 따져야 한다. ECR은 컨테이너 이미지 pull 트래픽이 크기 때문에 거의 항상 Interface Endpoint가 이득이다.

EKS 클러스터를 처음 셋업할 때 이 Endpoint들을 같이 만들지 않으면 첫 청구서가 충격적으로 나온다. 한 번 겪고 나면 다시는 잊지 않는다.

### 5.2 리전 간 트래픽과 AZ 간 트래픽

데이터 전송 비용 표는 외워둘 가치가 있다. (AWS 기준, 대략값)

| 경로 | 비용 (GB당) |
|---|---|
| 인터넷 → AWS (inbound) | 무료 |
| AWS → 인터넷 (outbound) | $0.09 (첫 10TB) |
| 같은 AZ 안, private IP | 무료 |
| 같은 리전, 다른 AZ | $0.01 (양방향 각각) |
| 같은 리전, 같은 AZ, public IP/Elastic IP 경유 | $0.01 |
| 다른 리전 | $0.02 |
| CloudFront → 인터넷 | $0.085 (첫 10TB) |

가장 자주 새는 건 **AZ 간 트래픽**이다. 멀티 AZ로 띄운 RDS와 EKS 노드가 다른 AZ에 있으면 모든 쿼리가 AZ 간 트래픽이 된다. 트래픽이 큰 서비스는 application과 DB를 같은 AZ에 두는 zone-aware 라우팅을 고려한다. Kubernetes에서는 topology-aware hints로 같은 AZ 안의 Pod로 우선 라우팅하게 만든다.

다른 리전으로의 cross-region replication도 비용 함정이다. S3 Cross-Region Replication을 켜면 데이터가 한 번 더 복제되는 것뿐 아니라 리전 간 전송비가 GB당 $0.02씩 붙는다. DR 목적이라면 정말 필요한 버킷만 복제 대상으로 한정한다.

### 5.3 인터넷 outbound는 CloudFront로 우회

서비스 응답을 직접 ALB에서 인터넷으로 내보내면 GB당 $0.09인데, CloudFront를 앞에 두면 origin → CloudFront 사이는 무료고, CloudFront → 인터넷은 $0.085다. 거의 같아 보이지만 CloudFront는 캐시 히트율이 30~80%라 실제로는 origin 부하와 비용이 같이 줄어든다. 정적 자산이 많은 서비스라면 CloudFront를 안 쓸 이유가 없다.

---

## 6. S3 스토리지 클래스 — 접근 패턴별로 옮긴다

### 6.1 클래스별 가격과 사용처

S3는 한 버킷 안에 여러 스토리지 클래스를 섞을 수 있다. 가격은 (us-east-1 기준 대략) 이렇다.

| 클래스 | 저장 비용 (GB/월) | 검색 비용 | 최소 보관 | 검색 시간 |
|---|---|---|---|---|
| Standard | $0.023 | 없음 | 없음 | 즉시 |
| Standard-IA | $0.0125 | GB당 $0.01 | 30일 | 즉시 |
| One Zone-IA | $0.01 | GB당 $0.01 | 30일 | 즉시 |
| Intelligent-Tiering | $0.023 (Frequent) ~ $0.0036 (Archive) | 없음 | 없음 | 즉시 또는 분/시간 |
| Glacier Instant Retrieval | $0.004 | GB당 $0.03 | 90일 | 즉시 |
| Glacier Flexible | $0.0036 | GB당 $0.01 | 90일 | 1분~12시간 |
| Glacier Deep Archive | $0.00099 | GB당 $0.02 | 180일 | 12~48시간 |

핵심은 **접근 패턴을 모르면 Intelligent-Tiering**이다. 접근 빈도에 따라 자동으로 클래스를 옮긴다. 모니터링 수수료(객체당 월 ~$0.0025/1000개)가 있지만 객체 크기가 128KB를 넘으면 거의 항상 이득이다. 작은 객체가 수억 개라면 모니터링 수수료가 의외로 크게 나오니 그 경우는 직접 라이프사이클을 짠다.

### 6.2 라이프사이클 규칙의 실전 예

로그 같은 데이터에 자주 쓰는 라이프사이클:

```json
{
  "Rules": [{
    "Id": "logs-tiering",
    "Status": "Enabled",
    "Filter": { "Prefix": "logs/" },
    "Transitions": [
      { "Days": 30,  "StorageClass": "STANDARD_IA" },
      { "Days": 90,  "StorageClass": "GLACIER_IR" },
      { "Days": 365, "StorageClass": "DEEP_ARCHIVE" }
    ],
    "Expiration": { "Days": 2555 },
    "NoncurrentVersionExpiration": { "NoncurrentDays": 30 },
    "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
  }]
}
```

여기서 빠뜨리기 쉬운 두 줄이 `NoncurrentVersionExpiration`과 `AbortIncompleteMultipartUpload`다. 버전 관리가 켜진 버킷에서 이전 버전을 안 지우면 객체를 지워도 비용이 줄지 않는다. 미완성 멀티파트 업로드는 실패한 업로드가 부분 파일로 남아 영원히 청구된다. 이 두 규칙은 모든 버킷에 기본으로 넣어두는 게 안전하다.

### 6.3 클래스 전환의 함정

전환에도 비용이 든다. 객체 1000개당 약 $0.01. 작은 객체가 수억 개면 전환 비용만 수백 달러가 나간다. 작은 객체는 차라리 묶어서 큰 객체로 만들거나, 전환 없이 Standard로 두는 게 싸다.

검색 비용도 잊으면 안 된다. Standard-IA에 둔 데이터를 다시 자주 읽기 시작하면 GB당 $0.01의 검색 비용이 쌓인다. 저장 비용은 절반이지만 검색이 잦으면 Standard보다 비싸진다. **접근 빈도가 월 1회 이하**가 IA의 손익분기점이다.

---

## 7. 로그 보존 정책 — CloudWatch Logs가 의외로 비싸다

### 7.1 CloudWatch Logs 비용 구조

CloudWatch Logs는 세 가지로 청구된다.

- **수집(ingestion)**: GB당 $0.50
- **저장**: GB당 월 $0.03
- **분석(Logs Insights 쿼리)**: 스캔된 GB당 $0.005

가장 큰 항목은 수집이다. 한 서비스에서 디버그 로그를 모두 INFO 레벨로 흘리면 일일 수십 GB가 쌓이는데, 한 달에 1TB만 수집해도 수집 비용이 $500이 된다. 게다가 저장은 retention을 설정하지 않으면 무한이라 매달 누적된다.

내가 쓰는 정책은 단순하다.

- 모든 Log Group에 retention을 **기본 30일**로 박는다. retention 없는 Log Group이 만들어지면 CloudFormation/Terraform에서 막거나 Lambda로 자동 30일 retention을 부여한다.
- 감사·보안 로그는 별도 Log Group으로 분리해 1년 또는 7년 retention.
- 30일 후에 더 길게 보관해야 하는 로그는 S3 export로 옮긴다. S3 IA/Glacier가 CloudWatch Logs 저장보다 훨씬 싸다.

### 7.2 로그 양 자체를 줄이기

저장 비용보다 수집 비용이 크니까, 로그 양을 줄이는 게 더 효과적이다.

- 로그 레벨을 production은 WARN 또는 INFO로 고정. DEBUG는 일시적 트러블슈팅에만.
- access log는 ALB → S3 직접 저장. CloudWatch Logs에 보내지 않는다. S3가 10배 이상 싸다.
- 헬스 체크 로그를 제외한다. Kubernetes 환경에서는 readiness/liveness probe 로그가 양의 절반을 차지하는 경우가 흔하다.
- 동일한 메시지를 반복하는 로그는 샘플링한다. 1000번에 1번만 기록해도 디버깅에 충분한 경우가 많다.

### 7.3 다른 로그 백엔드를 고려할 시점

CloudWatch Logs는 편하지만 양이 일정 수준을 넘으면 비싸다. 일일 100GB가 넘어가면 OpenSearch나 Loki를 자체 운영하는 게 싸진다. 운영 부담을 감안하면 일일 300~500GB 정도가 실질적인 손익분기점이다.

S3 + Athena 조합은 거의 항상 싸다. 수집 시 Firehose로 S3에 떨어뜨리고, 쿼리는 Athena로 한다. 검색 빈도가 낮으면 이 조합이 가장 경제적이다. 대신 인덱스가 없어서 자유 검색은 느리다. on-call이 새벽에 직접 grep할 일이 많은 로그는 CloudWatch Logs나 OpenSearch에 두는 게 낫다.

---

## 8. 청구서 분석 — Cost Explorer와 CUR

### 8.1 Cost Explorer로 매주 시작

매주 월요일 아침에 Cost Explorer를 연다. 본 시점은 두 군데다.

1. **지난 7일 vs 그 전 7일**의 일일 비용 비교. 갑자기 튄 날이 있는지 본다.
2. **서비스별 / 태그별** 비용. EC2, S3, RDS, NAT Gateway, CloudWatch 순서로 보고 전주 대비 변동이 큰 항목을 찾는다.

Cost Explorer의 그룹화 기준 중 가장 자주 쓰는 건 `Usage Type`이다. EC2 → BoxUsage/m5.large(인스턴스 비용)인지 DataTransfer-Out-Bytes(아웃바운드 트래픽)인지 NatGateway-Bytes(NAT 처리량)인지 한 줄로 보여준다. "EC2 비용이 늘었다"가 아니라 "EC2의 NAT Gateway 처리량이 늘었다"까지 봐야 원인을 안다.

### 8.2 비용 할당 태그는 첫날부터 박는다

태그 없이 운영하다가 나중에 붙이려면 끔찍하다. 최소한 다음 세 개는 모든 리소스에 강제로 박는다.

- `team` — 어느 팀 소유인지
- `service` — 어느 서비스에 쓰이는지
- `env` — production, staging, dev

Terraform이나 CloudFormation에서 default tags로 강제하고, 태그가 없는 리소스는 SCP(Service Control Policy)나 Config Rule로 차단한다. 태그가 있어야 Cost Explorer에서 팀별·서비스별 비용 리포트가 의미를 갖는다.

이 태그 없이 청구서를 받아본 적이 있다면 다시는 미루지 않게 된다. "EC2 $40,000"이 청구되는데 어느 팀의 어느 서비스 것인지 누구도 모른다.

### 8.3 CUR — 가장 자세한 청구 데이터

Cost Explorer가 보여주는 건 사실 가공된 요약이다. 원시 데이터는 **CUR(Cost and Usage Report)**이다. S3에 parquet으로 떨어지는 시간당 청구 내역이고, 한 라인이 하나의 사용 단위다. 컬럼이 200개쯤 된다.

Athena로 CUR를 쿼리하면 Cost Explorer로 못 보는 분석이 가능하다.

```sql
-- 이번 달 NAT Gateway 데이터 처리비를 VPC별로
SELECT
  resource_tags_user_vpc AS vpc,
  SUM(line_item_unblended_cost) AS cost_usd
FROM cur_table
WHERE bill_billing_period_start_date = DATE '2026-06-01'
  AND line_item_usage_type LIKE '%NatGateway-Bytes%'
GROUP BY 1
ORDER BY 2 DESC;
```

```sql
-- 가장 비싼 RI/SP 미적용 EC2 사용
SELECT
  line_item_usage_type,
  SUM(line_item_unblended_cost) AS on_demand_cost
FROM cur_table
WHERE bill_billing_period_start_date = DATE '2026-06-01'
  AND product_servicecode = 'AmazonEC2'
  AND line_item_line_item_type = 'Usage'  -- DiscountedUsage 제외
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20;
```

CUR로 한 번 분석을 해두면 다음 달 같은 분석을 자동화하기 쉽다. 매월 같은 쿼리를 돌려 변동분이 큰 항목을 알림으로 받는다.

---

## 9. 비용 Anomaly 탐지

### 9.1 AWS Cost Anomaly Detection

AWS가 제공하는 기본 anomaly 탐지 서비스가 있다. 머신러닝 모델이 지난 90일치 비용 패턴을 학습하고, 통계적으로 벗어난 지출이 감지되면 알림을 보낸다. 무료고 셋업이 5분이다.

설정은 두 가지를 만든다.

1. **Monitor** — 어디를 감시할지. "전체 서비스", "AWS 서비스별", "비용 카테고리별", "비용 할당 태그별" 중 선택.
2. **Subscription** — 어떻게 알릴지. 이메일, SNS, 임계값.

team 태그별로 monitor를 만들고 각 팀 채널로 SNS → Lambda → Slack 라우팅을 두면 비용이 튀었을 때 해당 팀이 바로 본다. 임계값은 처음에는 일일 $100 정도로 시작하고, false positive가 많으면 올린다.

### 9.2 자체 anomaly 탐지가 더 나은 경우

AWS Cost Anomaly Detection은 편하지만 단점이 둘 있다. 첫째, 알림이 최대 24시간 늦게 온다. 청구 데이터가 그만큼 늦게 확정되기 때문이다. 둘째, 서비스 단위라서 "S3가 평소보다 비싸졌다"는 알 수 있어도 "어느 버킷이 원인인지"는 모른다.

더 빠르고 세밀한 탐지가 필요하면 CUR을 매시간 Athena로 쿼리해서 직접 임계값 알림을 만든다.

```sql
-- 어제 NAT Gateway 처리 비용 vs 지난 14일 평균
WITH daily AS (
  SELECT
    DATE(line_item_usage_start_date) AS d,
    SUM(line_item_unblended_cost) AS cost
  FROM cur_table
  WHERE line_item_usage_type LIKE '%NatGateway-Bytes%'
    AND line_item_usage_start_date >= CURRENT_DATE - INTERVAL '15' DAY
  GROUP BY 1
)
SELECT
  (SELECT cost FROM daily WHERE d = CURRENT_DATE - INTERVAL '1' DAY) AS yesterday,
  AVG(cost) AS avg_14d,
  (SELECT cost FROM daily WHERE d = CURRENT_DATE - INTERVAL '1' DAY) / AVG(cost) AS ratio
FROM daily
WHERE d BETWEEN CURRENT_DATE - INTERVAL '15' DAY AND CURRENT_DATE - INTERVAL '2' DAY;
```

비율이 1.5 이상이면 알림. 이런 쿼리 10~20개를 Lambda에서 매일 돌리면 "왜 청구서가 두 배가 됐는지"를 월말이 아니라 다음 날 알 수 있다.

### 9.3 알림이 와도 행동으로 이어져야 한다

anomaly 알림을 받았는데 "그렇구나" 하고 넘어가면 의미가 없다. 알림에는 항상 다음 정보가 같이 와야 한다.

- 어떤 서비스의 어떤 usage type인가
- 평소 대비 몇 배인가
- 가장 가능성 있는 책임 리소스/태그
- 다음에 해야 할 액션 (예: "이 버킷의 라이프사이클 확인", "이 NAT의 VPC Endpoint 추가 검토")

Slack 메시지에 이 네 줄이 들어가 있으면 받은 사람이 5분 안에 첫 대응을 한다. 정보가 부족하면 미뤄지고, 미뤄지면 한 달이 지난다.

---

## 10. 마무리 — 비용 최적화는 운영 프로세스다

비용 최적화는 한 번 큰 작업을 해서 끝내는 일이 아니다. 약정은 매 분기 갱신을 검토해야 하고, idle 리소스는 매주 청소되어야 하고, anomaly 알림은 24시간 깨어 있어야 한다. 코드로 자동화하지 않으면 결국 사람이 손으로 따라가야 하는데 사람은 손이 비어 있지 않다.

5년 동안 비용 작업을 하면서 가장 확실하게 효과가 컸던 것들을 다시 정리하면 이렇다. 첫째, VPC Endpoint를 처음부터 잘 깔아두는 것. NAT Gateway 청구서가 절반으로 준다. 둘째, 모든 리소스에 team/service/env 태그를 강제하는 것. 책임이 분명해지면 자연스럽게 절약이 일어난다. 셋째, dev/staging의 야간 정지. 코드 한 줄로 70%를 깎는다. 넷째, S3 라이프사이클의 미완료 멀티파트 정리. 잊혀진 부분 업로드가 의외로 큰돈이다. 다섯째, CloudWatch Logs retention을 기본 30일로 박는 것.

세부 기술과 가격은 매년 바뀌지만 원칙은 그대로다. 청구서를 끝까지 읽고, 누가 어디서 쓰고 있는지를 한 줄도 빠짐없이 설명할 수 있게 만들고, 발견한 누수는 자동화로 막는다. 이 셋이 잡혀 있으면 어떤 클라우드로 옮겨도 비용은 통제된다.
