---
title: AWS Cost Explorer
tags: [aws, cost, billing, cost-explorer, savings-plans, reserved-instances]
updated: 2026-05-08
---

# AWS Cost Explorer

## 개요

Cost Explorer는 AWS 청구 데이터를 시각화하고 차원별로 자르는 분석 도구다. 콘솔에서 클릭으로 보든, API로 데이터를 빼서 사내 대시보드를 만들든 결국 같은 백엔드(Cost and Usage Report 파이프라인)를 본다. 일별·월별 추이, 서비스·태그·리전·계정별 분해, 미래 비용 예측, Savings Plans/RI 추천까지 한 화면에서 다룬다.

청구서 PDF 한 장으로는 진단이 안 된다. "EC2 1,200달러"라고 적혀 있어도 그게 인스턴스 비용인지 EBS인지 데이터 전송인지 모른다. Cost Explorer는 그 1,200달러를 Usage Type 단위까지 쪼갠다. 운영 중 갑자기 비용이 튀는 상황에서 첫 번째로 여는 도구다.

처음 활성화하면 13개월 과거 데이터를 바로 본다. 활성화 전에 청구가 발생했어도 데이터는 남아 있어서 거슬러 올라가 분석할 수 있다. 단, "활성화 직후"에는 24시간 정도 데이터 갱신 지연이 있다. 신규 계정에서 첫 호출이 비어 보이면 보통 이 지연이다.

### 어디서 돈이 나가는지 모르는 상황

매달 청구서를 받고 같은 패턴이 반복된다. 예상 500달러였는데 실제는 2,800달러가 나온다. EC2가 비싼지, 데이터 전송이 비싼지, 혹은 누가 만들어둔 NAT Gateway가 시간당 과금되고 있는지 청구서만으로는 안 보인다. 특히 NAT Gateway는 시간당 0.045달러에 GB당 처리 요금이 별도로 붙어서, 트래픽이 많은 ECS 태스크가 NAT를 타고 외부 API를 호출하면 한 달에 수백 달러가 조용히 누적된다. Cost Explorer로 Usage Type을 펼치기 전까지는 잘 모른다.

Cost Explorer가 풀어주는 것은 다음 정도다.

- 일별·월별 비용 추이와 급증 구간 식별
- 서비스·리전·계정·태그·Usage Type 차원의 분해
- Resource Optimization, Savings Plans, RI 같은 절감 추천
- 향후 12개월까지의 예측

## 비용 분석 차원

Cost Explorer가 데이터를 자르는 축을 "차원(Dimension)"이라 한다. 콘솔의 Group by 드롭다운, API의 `GroupBy` 파라미터에 들어가는 값이 모두 차원이다. 어떤 차원을 골라 잘라보느냐가 분석의 절반이다.

### 서비스(SERVICE)

가장 흔한 출발점. "EC2-Instances", "Amazon RDS", "AWS Lambda" 같은 서비스 이름이 키가 된다. 같은 EC2라도 인스턴스(BoxUsage), EBS, 데이터 전송이 모두 "Amazon Elastic Compute Cloud - Compute"에 묶이는 점은 처음에 헷갈린다. 더 잘게 보려면 Usage Type 차원으로 한 번 더 그룹핑한다.

### Usage Type / Usage Type Group

`USAGE_TYPE`은 "BoxUsage:t3.medium", "EBS:VolumeUsage.gp3", "DataTransfer-Out-Bytes" 같은 과금 단위다. 비용이 어디서 발생했는지 가장 정밀하게 확인하는 차원이다. 다만 키 이름이 길고 리전 접두어가 붙어서 한눈에 안 들어온다. 운영 환경에서 자주 보는 패턴은 다음 정도다.

| Usage Type 예시 | 의미 |
|---|---|
| `BoxUsage:t3.medium` | t3.medium 온디맨드 시간당 과금 |
| `SpotUsage:m5.large` | Spot 인스턴스 시간당 과금 |
| `EBS:VolumeUsage.gp3` | gp3 볼륨 GB-월 과금 |
| `EBS:SnapshotUsage` | EBS 스냅샷 보관료 |
| `DataTransfer-Out-Bytes` | 인터넷 아웃바운드 |
| `USE1-USW2-AWS-Out-Bytes` | us-east-1 → us-west-2 리전 간 |
| `NatGateway-Hours` | NAT Gateway 시간당 |
| `NatGateway-Bytes` | NAT Gateway 처리 데이터 |

`USAGE_TYPE_GROUP`은 이를 묶어둔 큰 카테고리(예: "EC2: Running Hours")라 추세 파악에는 더 편하다.

### 리전(REGION)

운영 리전이 여러 개일 때 즉시 의미가 생긴다. us-west-2가 메인인데 ap-northeast-2에서 갑자기 비용이 올라가면, 누가 도쿄/서울에 테스트 인스턴스를 띄우고 잊었을 가능성이 높다. 리전이 안 보이는 서비스(IAM, Route 53, CloudFront)는 "global" 또는 "NoRegion"으로 잡힌다.

### 연결된 계정(LINKED_ACCOUNT)

AWS Organizations로 여러 계정을 묶어 쓰는 환경에서는 이 차원이 사실상 "팀별 비용"이 된다. payer 계정의 Cost Explorer에서 Group by: Linked Account를 걸면 계정 단위로 깔끔하게 떨어진다. 계정 ID가 키로 나오기 때문에 사내 위키나 노션에 "계정 ID ↔ 팀명" 매핑을 따로 두는 편이 좋다. 콘솔에서는 계정 별칭(alias)을 같이 보여준다.

### 태그(TAG)

가장 강력한 차원이지만 가장 손이 많이 간다. `Team`, `Environment`, `Project`, `CostCenter` 같은 태그를 모든 리소스에 일관되게 붙이고, 그 태그를 "Cost Allocation Tag"로 활성화해야 Group by 후보로 올라온다. 활성화 절차는 뒤에서 따로 다룬다.

### 구매 옵션(PURCHASE_TYPE)

On-Demand, Reserved, Savings Plans, Spot이 어떤 비율로 섞여 있는지 본다. RI나 Savings Plans 도입 효과를 확인할 때 이 차원을 자주 쓴다. "예약을 샀는데 정작 On-Demand가 줄지 않더라" 같은 상황이 RI 적용 누락(다른 리전, 다른 패밀리) 때문에 생기는데, 이 차원으로 즉시 보인다.

### 그 외 자주 쓰는 차원

- `INSTANCE_TYPE`: 인스턴스 패밀리/사이즈별 분해. Rightsizing 후보 선별에 쓴다.
- `OPERATION`: API 호출 단위. S3에서 PUT vs GET 비용을 분리할 때 유용.
- `AVAILABILITY_ZONE`: AZ 간 분포. 멀티 AZ 트래픽 비용 분석.
- `PLATFORM`: Linux/Windows 라이선스 차이.
- `RECORD_TYPE`: 환불(Refund), 크레딧(Credit), 할인 등 비용 외 항목 분리.

### 메트릭 종류

같은 데이터라도 어떤 금액을 보느냐는 별도다.

- `UnblendedCost`: 결제 계정에서 실제 발생한 비용. 리전·계정 구분 없이 그대로.
- `BlendedCost`: Organizations 단위로 평균을 낸 가격. 여러 계정에서 RI를 공유할 때 평균치로 본다.
- `AmortizedCost`: 선결제 RI/Savings Plans를 일별로 분할 인식한 비용. 월말 청구가 갑자기 튀어 보이는 현상을 없앨 때 쓴다.
- `NetUnblendedCost`, `NetAmortizedCost`: EDP나 PPA 같은 사적 할인이 반영된 금액.

원칙적으로 **운영 모니터링은 `AmortizedCost`로 통일**하는 편이 낫다. RI를 1년 선결제했는데 그 달 한 번에 잡히면 추세 분석이 망가진다.

## Cost Allocation Tags 활성화

태그 자체를 붙이는 일과, 그 태그를 비용 차원으로 쓸 수 있게 만드는 일은 별개다. 후자가 Cost Allocation Tag 활성화다. 활성화하지 않으면 Cost Explorer의 Group by: Tag 드롭다운에 그 키가 안 나타난다. 신규 멤버가 합류해서 "왜 우리 팀 태그가 안 보이지?"라고 묻는 단골 원인이다.

### 두 종류

- **AWS-generated tags**: `aws:createdBy`처럼 AWS가 자동으로 붙이는 태그. `aws:` 접두어가 붙는다.
- **User-defined tags**: 사용자가 직접 붙인 태그(`Team`, `Environment` 등). 활성화 대상의 99%는 이쪽이다.

### 활성화 절차 (콘솔)

1. AWS Billing 콘솔 → 좌측 "Cost allocation tags" 메뉴.
2. "User-defined cost allocation tags" 탭. 지난 12개월 사이에 어떤 리소스에든 붙은 태그 키가 목록에 잡힌다.
3. 활성화할 태그 키를 체크.
4. 우측 상단 "Activate" 버튼.

활성화 후 **데이터에 반영되기까지 최대 24시간** 걸린다. 활성화 시점 이후 발생한 비용에만 적용된다는 점이 함정이다. 과거 데이터에는 소급 적용되지 않으므로, 새 태그를 만들고 바로 분석하려면 안 된다. "월요일에 리소스에 태그 붙이고, 화요일에 활성화하고, 그 다음 주에 비교한다" 정도의 페이스를 잡아야 한다.

### CLI로 일괄 활성화

태그 키가 수십 개면 콘솔에서 일일이 체크하기 번거롭다.

```bash
aws ce update-cost-allocation-tags-status \
  --cost-allocation-tags-status \
    'TagKey=Team,Status=Active' \
    'TagKey=Environment,Status=Active' \
    'TagKey=Project,Status=Active' \
    'TagKey=CostCenter,Status=Active' \
    'TagKey=Owner,Status=Active'
```

활성화 상태는 `list-cost-allocation-tags`로 확인한다.

```bash
aws ce list-cost-allocation-tags --status Active \
  --query 'CostAllocationTags[*].[TagKey,Type]' --output table
```

### 태그 정책으로 강제

태깅을 사람의 선의에 맡기면 결국 누락된다. AWS Organizations의 Tag Policy로 "Production 환경 리소스에는 Team 태그가 반드시 있어야 한다" 같은 규칙을 강제할 수 있다. 직접 차단까지는 안 가더라도 비준수 리소스를 리포트로 받을 수 있다. 운영 규모가 커지면 이쪽으로 옮겨가는 편이 낫다. 태그 누락 자체를 잡고 싶으면 AWS Config의 `required-tags` 규칙으로 비준수 리소스를 알림으로 받는 패턴을 자주 쓴다.

### 태그 정리 시 주의

이미 활성화된 태그 키를 비활성화하면 그 시점 이후 데이터에서 차원이 사라진다. 과거 리포트에는 영향이 없다. 한 번 만든 태그 키는 그대로 두고, 명명 규칙을 바꿀 때는 새 키로 옮겨가면서 한동안 두 키를 병행하는 방식이 현실적이다.

## 필터와 그룹화

콘솔의 좌측 패널이 거의 그대로 API 파라미터에 매핑된다.

- **Filter**: 특정 차원의 값으로 좁히기. `Filter: Service=EC2 AND Region=us-west-2`.
- **Group by**: 결과를 차원별로 분해. 1차/2차 그룹이 가능하지만 콘솔은 1차만 보여준다. API에서는 2개까지 동시에 줄 수 있다.

운영 중 자주 쓰는 조합 몇 개를 정리해 둔다.

### 서비스별 분해

```
Filter: (없음)
Group by: SERVICE
Granularity: MONTHLY
Period: Last 6 months
```

월별로 어떤 서비스가 늘고 줄었는지 한 눈에 본다. 새 서비스 도입 영향을 추적할 때 시작점.

### EC2 내부 분해

```
Filter: Service = "Amazon Elastic Compute Cloud - Compute"
Group by: USAGE_TYPE
Granularity: DAILY
Period: Last 30 days
```

EC2 1,200달러를 인스턴스/EBS/스냅샷/데이터 전송으로 가른다. EBS 스냅샷이 누적돼서 비용이 야금야금 늘어나는 경우가 많다.

### 팀별 일별 추이

```
Filter: Tag(Environment) = Production
Group by: Tag(Team)
Granularity: DAILY
```

배포가 잦은 팀은 일별로 튀어 보인다. 주말에 비용이 안 떨어지는 팀이 있다면 개발 환경을 끄지 않고 있을 가능성.

### 리전 간 데이터 전송

```
Filter: Usage Type Group = "EC2: Data Transfer - Region to Region"
Group by: REGION
```

us-west-2 ↔ us-east-1 트래픽이 비정상적으로 많으면 애플리케이션이 교차 리전 호출을 하고 있을 가능성이 크다. RDS Read Replica가 다른 리전에 있거나, S3 버킷이 엉뚱한 리전에 있는 경우다.

## 세부 분석 사례

### EC2 비용 분해

EC2를 선택하고 Group by: Usage Type을 걸면 다음과 같은 결과가 나온다.

```
BoxUsage:t3.medium     $600
BoxUsage:m5.large      $800
EBS:VolumeUsage.gp3    $250
DataTransfer-Out-Bytes $200
```

인스턴스 1,400달러, EBS 250달러, 데이터 전송 200달러로 나뉜다. 데이터 전송이 200달러면 정적 자산이 EC2에서 직접 나가고 있을 확률이 있다. CloudFront 앞단에 두면 절반 이상 줄어든다.

### RDS 분해

```
Filter: Service = "Amazon Relational Database Service"
Group by: USAGE_TYPE
```

`InstanceUsage:db.m5.large`, `RDS:StorageUsage`, `RDS:GP2-Storage`, `RDS:BackupUsage` 같은 항목이 나온다. 백업이 의외로 비싼 경우가 있다. `BackupUsage`가 인스턴스 비용에 가깝게 잡히면 보존 기간을 검토한다. PITR을 켠 상태에서 트랜잭션 로그가 쌓이면 스토리지가 데이터 자체보다 커진다.

### 데이터 전송

```
Filter: Service = "AWS Data Transfer"
Group by: USAGE_TYPE
```

`DataTransfer-Out-Bytes`(인터넷 아웃바운드)와 리전 간 전송(`USE1-USW2-AWS-Out-Bytes` 같은 키)을 분리해서 본다. 리전 간이 인터넷 아웃바운드보다 비싼 경우는 거의 항상 아키텍처 문제다.

## Resource Optimization 추천

콘솔의 "Cost Explorer → Recommendations → Rightsizing recommendations" 메뉴. AWS Compute Optimizer와 같은 데이터 소스를 쓰지만, Cost Explorer 화면에서는 비용 절감 관점만 추려서 보여준다.

### 추천이 만들어지는 조건

- 인스턴스가 14일 이상 실행 중이어야 한다.
- CloudWatch 기본 메트릭(CPUUtilization, NetworkIn/Out)으로 분석한다.
- 메모리 사용률은 기본적으로 안 본다. CloudWatch Agent로 메모리 메트릭을 수집해 두면 추천 정확도가 올라간다.

### 두 가지 모드

- **Same instance family**: 같은 패밀리(m5) 안에서만 사이즈 다운. 보수적.
- **Cross instance family**: m5 → t3, c5 → c6g 같은 패밀리 변경까지 포함. 절감폭이 크지만 워크로드 검증이 필요하다.

운영 워크로드에 처음 적용할 때는 Same family로 시작하는 편이 안전하다. CPU 외 다른 특성(메모리 대역폭, EBS 대역폭, 네트워크)이 패밀리마다 달라서, 단순히 CPU 사용률만 보고 c 패밀리에서 t 패밀리로 옮기면 burst 크레딧 고갈 같은 함정에 걸린다.

### 콘솔에서 보는 화면

각 추천에 다음이 붙는다.

- 현재 타입과 권장 타입
- 최근 14일 CPU/네트워크 평균·최대
- 월 절감 예상액
- 위험도(Risk): Low/Medium/High

Risk가 High인 추천은 메트릭이 한쪽으로만 쏠려 있어 신뢰도가 낮다는 뜻이다. 일단 보류하고 메트릭을 더 모은다.

### API로 빼서 자동화

```bash
aws ce get-rightsizing-recommendation \
  --service "AmazonEC2" \
  --configuration RecommendationTarget=SAME_INSTANCE_FAMILY,BenefitsConsidered=true
```

응답에서 `RightsizingRecommendations` 배열을 보면 인스턴스별로 현재/권장 타입과 예상 절감액이 들어 있다. 이걸 매주 한 번 Lambda로 뽑아서 슬랙에 떨어뜨리는 식으로 운영하면 사람이 콘솔을 안 들어가도 된다.

## Savings Plans / RI 추천 분석

Cost Explorer는 두 가지 추천을 별도 메뉴로 제공한다.

- **Savings Plans recommendations**: Compute SP, EC2 Instance SP 추천.
- **Reservation recommendations**: EC2/RDS/ElastiCache/Redshift/OpenSearch RI 추천.

### 추천 설정 파라미터

세 가지를 고른다.

- **Term**: 1년 또는 3년.
- **Payment option**: All Upfront, Partial Upfront, No Upfront.
- **Look-back period**: 7일/30일/60일 사용량을 기준으로 계산.

운영 안정성이 검증된 워크로드라면 30일 또는 60일 기준이 합리적이다. 7일은 변동이 크면 과대 추천이 나오고, 60일은 신규 워크로드가 반영이 늦다.

### Savings Plans 추천을 먼저 본다

Savings Plans가 RI보다 유연하다. 같은 절감률에서 인스턴스 패밀리/리전/사이즈를 바꿀 수 있어서 운영 변경에 강하다. 신규 도입이라면 Compute Savings Plans부터 검토한다. EC2 Instance Savings Plans는 절감률이 더 크지만(최대 72%) 패밀리·리전이 고정된다.

추천 화면의 핵심 숫자는 다음.

- **Hourly commitment**: 시간당 약정 금액(예: $5/hr).
- **Estimated monthly savings**: 월 예상 절감액.
- **Estimated ROI**: 투자 회수 비율.
- **Coverage**: 약정이 적용될 사용량 비율.

너무 큰 commitment를 잡으면 사용량이 줄었을 때 약정 금액이 그대로 빠진다. 추천 화면에서 "If you use this much, but actually used less"가 명시되니 보수적인 시나리오를 같이 본다. 보통 추천값의 80~90% 정도로 잡고 출발해서 Coverage 리포트를 보면서 조금씩 올린다.

### RI 추천

Savings Plans가 안 되는 서비스(RDS, ElastiCache, OpenSearch, Redshift, MemoryDB, DynamoDB Reserved Capacity)는 여전히 RI다. 추천 화면에 인스턴스별 과거 사용 시간, 권장 수량, 예상 절감액이 나온다.

RDS RI는 인스턴스 패밀리, 사이즈, 엔진, 라이선스 모델, 리전이 정확히 일치해야 적용된다. db.m5.large MySQL RI를 샀는데 운영 중 db.m6g.large로 옮기면 그 RI는 놀게 된다. 워크로드 마이그레이션 계획이 6개월 안에 있다면 1년 RI도 손해일 수 있다.

### API로 추천 가져오기

```bash
aws ce get-savings-plans-purchase-recommendation \
  --savings-plans-type COMPUTE_SP \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

aws ce get-reservation-purchase-recommendation \
  --service "Amazon Relational Database Service" \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS
```

응답에서 `RecommendationDetails`를 파싱하면 인스턴스 단위 권장 수량과 예상 절감액이 나온다. 결제 시점이 분기 단위라면 이 데이터를 분기마다 한 번 뽑아서 재무팀과 검토하는 흐름이 자연스럽다.

## RI Coverage / Utilization 리포트

RI나 Savings Plans를 산 다음에는 두 가지 지표를 같이 본다.

- **Utilization**: 산 약정이 얼마나 쓰이는가. 100%가 만점.
- **Coverage**: 전체 사용량 중 약정이 덮은 비율. 높을수록 절감률이 좋다.

### Utilization

`get-reservation-utilization`, `get-savings-plans-utilization`로 가져온다. Utilization이 100% 미만이면 산 약정이 놀고 있다는 뜻이다. RDS RI를 샀는데 인스턴스를 죽였거나 패밀리를 바꿨을 때 즉시 떨어진다. 90% 아래로 내려가면 알림이 가도록 Cost Anomaly Detection이나 자체 Lambda를 걸어둔다.

```bash
aws ce get-reservation-utilization \
  --time-period Start=2026-04-01,End=2026-05-01 \
  --granularity MONTHLY
```

응답의 `Total.UtilizationPercentage`가 핵심 숫자.

### Coverage

`get-reservation-coverage`, `get-savings-plans-coverage-utilization`. Coverage는 운영 중 새 인스턴스를 늘리면 떨어진다. 추가 약정 구매를 검토하는 신호다.

```bash
aws ce get-reservation-coverage \
  --time-period Start=2026-04-01,End=2026-05-01 \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE
```

`CoverageHoursPercentage`로 인스턴스 타입별 Coverage를 본다. db.m5.large가 100% 가까이 덮여 있는데 db.r5.large가 0%라면, 새 워크로드가 r5로 옮겨갔다는 신호.

### 운영 패턴

매주 월요일 오전에 다음 네 숫자를 슬랙에 자동으로 떨어뜨려 두면 RI/SP 운영이 거의 자동화된다.

- 전주 RI Utilization
- 전주 RI Coverage
- 전주 Savings Plans Utilization
- 전주 Savings Plans Coverage

Utilization이 떨어지면 약정이 비는 것, Coverage가 떨어지면 새 약정이 필요한 것. 두 신호를 분리해서 본다.

## Cost Categories

태그가 리소스 단위 분류라면 Cost Categories는 비용 단위 분류다. 여러 차원(계정, 태그, 서비스, 리전, 사용 타입)을 조합한 규칙으로 청구 항목을 다시 묶는다. 콘솔의 "Billing → Cost categories" 메뉴.

### 언제 쓰는가

- 계정과 태그가 섞여 있는 환경에서 "팀별 비용"을 단일 차원으로 보고 싶을 때.
- 회사가 인수한 두 조직이 태깅 컨벤션이 달라서 표준화가 어려울 때.
- 공통 비용(공유 NAT, 공통 Route 53)을 특정 팀에 배분하고 싶을 때.

### 룰 예시

"BizOps" 카테고리를 다음 규칙으로 만든다.

- 계정 ID가 `111111111111`이면 → BizOps
- 또는 태그 `Team=BizOps`가 붙어 있으면 → BizOps
- 또는 서비스가 QuickSight면 → BizOps

이렇게 만들고 나면 Cost Explorer의 Group by에 "Cost Category: Department"가 차원으로 추가된다. Cost and Usage Report(CUR)에도 컬럼으로 들어가서 데이터 웨어하우스에서 그대로 쿼리할 수 있다.

### 분할 규칙(Split Charges)

공유 자원 비용을 여러 팀에 나누는 룰. NAT Gateway 비용을 트래픽 비율, 인스턴스 수, 또는 균등 분할로 배분할 수 있다. 사내 정산이 까다로운 조직에서는 거의 필수.

### 활성화 시점

Cost Categories는 만든 시점부터 데이터가 쌓인다. 과거 12개월 데이터에 백필이 가능하지만, 룰을 한 번 정의하면 그 룰이 12개월치 비용에 소급 적용된다. 만들 때 룰을 신중히 짜야 하고, 룰을 바꾸면 과거 리포트도 같이 바뀐다는 점이 함정이다. 재무팀이 보는 리포트라면 룰 변경 시점을 따로 기록해 둔다.

### API

```bash
aws ce list-cost-category-definitions
aws ce describe-cost-category-definition --cost-category-arn <arn>
```

룰 정의를 JSON으로 빼서 git에 넣어 두면, 누가 어떻게 분류 규칙을 바꿨는지 추적이 된다. 콘솔에서만 관리하면 어느 순간 "왜 BizOps 비용이 갑자기 줄었지"의 원인을 찾기 어렵다.

## 비용 예측

Cost Explorer는 과거 사용 패턴 기반으로 향후 12개월까지 예측을 보여준다. 콘솔의 시간 범위에 미래를 포함시키면 점선으로 예측이 그려진다.

### 예측의 한계

- 신규 서비스 도입 직후에는 부정확하다. 과거 데이터가 없거나 짧기 때문이다.
- 일회성 이벤트(블랙프라이데이 트래픽, 마이그레이션 비용)도 미래 예측에 그대로 반영된다.
- 예측 결과는 "이 추세가 그대로 가면 이렇게 된다"는 가정이다. 정책 결정이 아니라 알람용으로 쓴다.

API로는 `get-cost-forecast`. 신뢰 구간(`PredictionIntervalLevel`)을 80% 또는 95%로 지정한다. 예산 알람을 만들 때 이 값을 임계치로 쓰면 "예측이 예산을 넘을 것 같으면 알람"을 만들 수 있다.

```bash
aws ce get-cost-forecast \
  --time-period Start=2026-05-09,End=2026-06-09 \
  --metric UNBLENDED_COST \
  --granularity DAILY \
  --prediction-interval-level 80
```

## Cost Anomaly Detection

머신러닝 기반 이상 탐지. 정상 패턴을 학습해서 임계치를 자동으로 잡는다. 절대 금액 기반 알람(Budgets)과 보완 관계다.

### Monitor 종류

- **AWS services**: 모든 서비스를 한 묶음으로 감시.
- **Linked account**: 계정 단위.
- **Cost category**: 위에서 만든 Cost Category 단위.
- **Cost allocation tag**: 특정 태그 값 단위.

대부분의 경우 Linked account 또는 Cost category Monitor가 신호 대 잡음비가 좋다. 서비스 전체로 잡으면 작은 변동에도 알람이 자주 울린다.

### Subscription

Monitor와 별도로 Subscription이 있다. 어떤 알람을 누구에게 어떻게 보낼지 정한다. 임계치는 절대 금액(`$100 이상 이상치`)과 비율(`40% 이상 증가`) 두 축을 동시에 줄 수 있다. 운영에서 의미 있는 조합은 보통 "절대값 100달러 이상 + 비율 40% 이상"이다. 둘 중 하나만 잡으면 작은 서비스의 큰 비율 변동, 또는 큰 서비스의 미세한 변동까지 다 알람이 온다.

```
정상 범위: $1,000-$1,200
실제 비용: $2,400 (+100%)
원인 후보: BoxUsage:m5.4xlarge (10시간, $96)
```

원인 후보까지 자동 분석해 주기 때문에 알람 한 번으로 어디부터 봐야 할지 좁혀진다.

## API 자동화

콘솔에서 보는 모든 지표는 API로도 같은 값을 가져올 수 있다. 자체 대시보드, 슬랙 봇, 데이터 웨어하우스 적재까지 흐름을 직접 만들 때 핵심 API는 다음 정도.

| API | 용도 |
|---|---|
| `get-cost-and-usage` | 차원별 비용/사용량 |
| `get-cost-and-usage-with-resources` | 리소스 단위(EC2 인스턴스 ID 등). EC2만 지원, 14일 제한 |
| `get-cost-forecast` | 비용 예측 |
| `get-rightsizing-recommendation` | Rightsizing 추천 |
| `get-reservation-utilization` | RI 사용률 |
| `get-reservation-coverage` | RI 커버리지 |
| `get-reservation-purchase-recommendation` | RI 구매 추천 |
| `get-savings-plans-utilization` | SP 사용률 |
| `get-savings-plans-coverage` | SP 커버리지 |
| `get-savings-plans-purchase-recommendation` | SP 구매 추천 |
| `get-anomalies` | 이상 탐지 결과 |
| `get-dimension-values` | 특정 차원의 가능한 값 목록 |
| `get-tags` | 활성화된 태그 키/값 목록 |

### 호출 비용

API 호출당 0.01달러. 작은 숫자처럼 보이지만 매시간 호출하면 720번 × 0.01 = 7.2달러/월. 대시보드를 만들 때 폴링 주기를 너무 짧게 잡지 않는다. Cost Explorer 데이터는 어차피 24시간 내 갱신이라 5~15분 주기로 충분하다.

### 응답 캐싱

같은 쿼리는 캐싱해서 쓴다. Cost Explorer 데이터는 일 단위로 갱신되므로, 같은 날 안에서 같은 쿼리를 다시 부를 이유가 없다. 사내 대시보드를 만들 때 ElastiCache나 DynamoDB에 24시간 TTL로 캐싱해 두는 패턴을 자주 쓴다.

### Python 예시: 서비스별 비용 상위 10개

```python
import boto3
from datetime import datetime, timedelta

ce = boto3.client('ce')
end_date = datetime.utcnow().date()
start_date = end_date - timedelta(days=30)

resp = ce.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.strftime('%Y-%m-%d'),
        'End': end_date.strftime('%Y-%m-%d'),
    },
    Granularity='DAILY',
    Metrics=['AmortizedCost'],
    GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
)

totals = {}
for day in resp['ResultsByTime']:
    for grp in day['Groups']:
        svc = grp['Keys'][0]
        cost = float(grp['Metrics']['AmortizedCost']['Amount'])
        totals[svc] = totals.get(svc, 0) + cost

for svc, cost in sorted(totals.items(), key=lambda x: -x[1])[:10]:
    print(f'{svc:50s} ${cost:>10,.2f}')
```

`Metrics`로 `AmortizedCost`를 쓰는 점에 주의. `BlendedCost`로 받으면 RI/SP 결제 시점에 튀어 보인다.

### Lambda + EventBridge로 일일 리포트

매일 오전 9시에 어제 비용을 슬랙으로 보낸다. 기존 환경에서 자주 쓰이는 패턴.

```python
import boto3
import json
import os
import urllib.request
from datetime import datetime, timedelta

ce = boto3.client('ce')
WEBHOOK = os.environ['SLACK_WEBHOOK_URL']

def lambda_handler(event, context):
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    resp = ce.get_cost_and_usage(
        TimePeriod={
            'Start': yesterday.strftime('%Y-%m-%d'),
            'End': today.strftime('%Y-%m-%d'),
        },
        Granularity='DAILY',
        Metrics=['AmortizedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}],
    )

    groups = resp['ResultsByTime'][0]['Groups']
    rows = sorted(
        ((g['Keys'][0], float(g['Metrics']['AmortizedCost']['Amount'])) for g in groups),
        key=lambda x: -x[1],
    )[:5]

    total = sum(c for _, c in rows)
    lines = [f'*어제({yesterday}) AWS 비용 상위 5개* — 합계 ${total:,.2f}']
    for svc, cost in rows:
        lines.append(f'- {svc}: ${cost:,.2f}')

    payload = json.dumps({'text': '\n'.join(lines)}).encode()
    req = urllib.request.Request(
        WEBHOOK, data=payload, headers={'Content-Type': 'application/json'}
    )
    urllib.request.urlopen(req, timeout=5)
    return {'statusCode': 200}
```

EventBridge 룰로 스케줄을 건다.

```bash
aws events put-rule \
  --name daily-cost-report \
  --schedule-expression "cron(0 9 * * ? *)"

aws events put-targets \
  --rule daily-cost-report \
  --targets "Id=1,Arn=arn:aws:lambda:us-west-2:123456789012:function:cost-report"
```

### CUR과의 분담

대시보드를 진지하게 만들면 결국 Cost and Usage Report(CUR)로 옮겨가게 된다. CUR은 시간 단위 raw 데이터를 S3에 떨어뜨리고, Athena/Redshift/QuickSight로 SQL을 친다. Cost Explorer API는 일 단위까지만 지원하고 호출 비용도 들어서, 본격적인 분석 워크로드에는 한계가 있다. 운영 알람 정도는 Cost Explorer API로 끝내고, 분기 정산이나 임원 보고는 CUR + Athena 조합으로 가는 분리가 현실적이다.

## 비용 절감 사례

### 미사용 EBS 볼륨

Cost Explorer에서 EBS 비용이 500달러/월. 같은 차원에서 Group by Usage Type을 걸면 `EBS:VolumeUsage.gp3`가 대부분을 차지하고 있는데, 인스턴스 수에 비해 너무 크다.

```bash
aws ec2 describe-volumes \
  --filters Name=status,Values=available \
  --query 'Volumes[*].[VolumeId,Size,CreateTime]' \
  --output table
```

20개 볼륨, 합계 2 TB. 모두 분리(detached) 상태. 스냅샷을 떠두고 삭제. 월 500달러 → 100달러.

### 리전 간 데이터 전송

데이터 전송 비용 300달러/월. Group by REGION으로 보면 us-west-2 → us-east-1이 절반 이상. RDS Read Replica가 us-east-1에 있고 us-west-2 애플리케이션이 거기로 읽기 트래픽을 보내고 있었다. Replica를 us-west-2로 옮기고 월 250달러 절감.

### Rightsizing

EC2 비용 1,200달러/월. Rightsizing Recommendations에 m5.xlarge 5개가 m5.large로 다운 권장. CPU 평균 20%, 최대 45%. 인스턴스 타입을 변경하고 월 600달러 절감. 메모리 사용률을 같이 봐야 했기 때문에 변경 전 1주일간 CloudWatch Agent로 메모리 메트릭을 수집해서 검증.

세 사례 합쳐 월 950달러, 연간 약 11,400달러 절감. 분석에 든 시간은 4시간 정도.

## Cost Explorer 자체 비용

콘솔 사용과 기본 리포트는 무료. API 호출만 0.01달러/요청. 하루에 30번 호출해도 9달러/월 수준이라 거의 무시할 수 있는 비용이다. 다만 사내 대시보드에서 사용자마다 매번 API를 호출하는 구조면 호출 수가 빠르게 늘어난다. 한 번 호출한 결과는 캐싱해서 같은 날 안에서는 재사용한다.

## 참고

- Cost Explorer 사용자 가이드: https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- Cost Explorer API 레퍼런스: https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/
- Cost Categories: https://docs.aws.amazon.com/cost-management/latest/userguide/manage-cost-categories.html
- Savings Plans 추천: https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-recommendations.html
- AWS Compute Optimizer: https://aws.amazon.com/compute-optimizer/
