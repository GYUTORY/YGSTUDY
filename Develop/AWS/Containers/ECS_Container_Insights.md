---
title: ECS Container Insights
tags: [aws, ecs, container-insights, cloudwatch, monitoring, metrics, observability]
updated: 2026-05-26
---

# ECS Container Insights

## 개요

ECS를 운영하다 보면 "지금 이 서비스가 메모리를 얼마나 쓰고 있나"를 콘솔에서 바로 보고 싶은 순간이 온다. 그런데 기본 CloudWatch 지표로는 이게 잘 안 보인다. ECS가 기본으로 주는 건 클러스터와 서비스 레벨의 `CPUUtilization`, `MemoryUtilization` 두 개뿐이고, 그마저도 "예약량 대비 사용률"이라 실제 컨테이너가 몇 MB를 쓰는지는 알 수 없다. Task 단위로 쪼개 보거나, 네트워크 송수신량을 보거나, Pending Task가 몇 개 쌓였는지 보려면 추가 도구가 필요하다. 그게 Container Insights다.

이 문서는 메트릭과 알람만 다룬다. 컨테이너 stdout/stderr이 어디로 가고 어떻게 라우팅하는지는 [ECS 로그 관리](ECS_로그_관리.md)에서 다룬다. 둘은 자주 한 덩어리로 묶여 "모니터링"이라 불리지만 성격이 다르다. 로그는 "무슨 일이 있었나"를 텍스트로 남기는 것이고, 메트릭은 "지금 얼마나 쓰고 있나"를 숫자로 남기는 것이다. 알람을 거는 대상도 보통 메트릭이다. 로그에 거는 알람(메트릭 필터)은 로그 문서에서 따로 본다.

## 기본 CloudWatch 지표의 한계

Container Insights를 켜기 전에 ECS가 거저 주는 지표가 무엇인지부터 알아야 한다. 이걸 모르면 "이미 메트릭 다 있는데 왜 또 켜?"라고 생각하기 쉽다.

기본 지표는 `AWS/ECS` 네임스페이스에 있다. 종류는 사실상 두 개다.

- `CPUUtilization`: 서비스(또는 클러스터) 단위 CPU 사용률
- `MemoryUtilization`: 서비스(또는 클러스터) 단위 메모리 사용률

문제는 세 가지다.

첫째, **Task 단위가 없다**. 서비스에 태스크가 10개 떠 있어도 지표는 평균값 하나다. 특정 태스크 하나만 메모리를 먹고 있어도 평균에 묻혀 안 보인다. OOM으로 죽는 태스크를 추적할 때 평균 지표는 거의 쓸모가 없다.

둘째, **네트워크, 디스크, 태스크 개수 지표가 없다**. Pending Task가 쌓이는지, 네트워크가 포화됐는지를 기본 지표로는 알 수 없다.

셋째, 그리고 이게 가장 자주 사람을 헷갈리게 하는데, **이 사용률은 예약량 기준이다**. 다음 절에서 자세히 본다.

## Reserved와 Utilized의 차이

`AWS/ECS`의 `MemoryUtilization`이 70%라고 찍혔다고 하자. 많은 사람이 이걸 "컨테이너가 가진 메모리의 70%를 쓰고 있다"로 읽는다. 틀렸다. 정확히는 이렇다.

```
MemoryUtilization = (서비스 내 모든 태스크가 실제 사용 중인 메모리 합)
                  / (서비스 내 모든 태스크가 예약한 메모리 합)
                  × 100
```

분모가 "예약량(Reserved)"이다. Task Definition에 적어둔 `memory`(하드 리밋) 또는 `memoryReservation`(소프트 리밋) 값의 합이다. 실제 호스트 메모리도 아니고, 컨테이너가 가용한 최대치도 아니다. Task Definition에 내가 적어둔 숫자다.

여기서 함정이 나온다. 메모리를 넉넉하게 예약해두면 사용률이 실제보다 낮게 보인다. 2GB를 예약하고 앱이 500MB만 쓰면 사용률은 25%다. "여유 있네" 하고 안심하지만, 만약 일시적으로 1.9GB까지 튀면 그제야 사용률 95%가 찍히고 곧 OOM이다. 예약 기준 사용률은 "내가 잡아둔 방의 몇 퍼센트를 쓰는가"일 뿐, 절대량이 얼마인지는 알려주지 않는다.

Container Insights는 이걸 **절대값으로 쪼개서** 준다. `ECS/ContainerInsights` 네임스페이스에는 다음이 따로 들어온다.

- `CpuUtilized`: 실제 사용 중인 CPU 유닛(절대값)
- `CpuReserved`: 예약한 CPU 유닛
- `MemoryUtilized`: 실제 사용 중인 메모리(MiB 단위 절대값)
- `MemoryReserved`: 예약한 메모리(MiB)

`MemoryUtilized`를 직접 보면 "이 서비스가 지금 500MB를 쓴다"를 그대로 알 수 있다. 라이트사이징(right-sizing)을 할 때 이 절대값이 필요하다. 예약을 2GB에서 1GB로 줄여도 되는지를 판단하려면 실제 사용량의 절대 최대치를 봐야 하는데, 예약 기준 사용률만으로는 그 판단이 안 된다.

Auto Scaling을 메모리 기준으로 걸 때도 이 차이를 알아야 한다. [Service Auto Scaling](ECS_Service_Auto_Scaling.md)의 `ECSServiceAverageMemoryUtilization`은 위의 예약 기준 사용률을 그대로 쓴다. 그래서 메모리를 과다 예약한 서비스는 메모리 기준 스케일링이 영영 안 걸린다. 사용률이 항상 낮게 나오기 때문이다.

## Container Insights를 켜면 생기는 지표

`ECS/ContainerInsights` 네임스페이스에 들어오는 주요 지표를 정리한다. 실무에서 알람이나 대시보드로 자주 쓰는 것 위주다.

| 지표 | 의미 | 주로 쓰는 곳 |
|---|---|---|
| `CpuUtilized` / `CpuReserved` | 실제 사용 / 예약 CPU 유닛 | 라이트사이징, 절대 사용량 추적 |
| `MemoryUtilized` / `MemoryReserved` | 실제 사용 / 예약 메모리(MiB) | OOM 예방 알람, 라이트사이징 |
| `NetworkRxBytes` / `NetworkTxBytes` | 수신 / 송신 바이트 | 네트워크 포화 추적 |
| `RunningTaskCount` | 실행 중 태스크 수 | desired와 비교 알람 |
| `PendingTaskCount` | 배치 대기 중 태스크 수 | 용량 부족 알람 |
| `DesiredTaskCount` | 목표 태스크 수 | running과 비교 |
| `EphemeralStorageUtilized` / `EphemeralStorageReserved` | 임시 스토리지 사용 / 할당(Fargate) | 디스크 폭증 추적 |
| `TaskCount` | 클러스터 태스크 수 | 클러스터 전체 규모 |

`RunningTaskCount`, `PendingTaskCount`, `DesiredTaskCount`는 기본 지표에 아예 없는 것들이라 Container Insights를 켜는 가장 직접적인 이유가 되곤 한다. 특히 `PendingTaskCount`가 0보다 큰 상태로 유지되면 클러스터에 용량이 없어 태스크가 못 뜨고 있다는 신호다. EC2 모드에서 이 알람 하나만 잘 걸어둬도 "왜 스케일 아웃이 안 되지?"를 30분 일찍 알아챈다.

## 활성화 방법

Container Insights는 클러스터 설정이다. 기존 클러스터에 켤 수도 있고, 계정 기본값으로 켜서 이후 만드는 모든 클러스터에 적용할 수도 있다.

특정 클러스터에만 켜기:

```bash
aws ecs update-cluster-settings \
  --cluster prod \
  --settings name=containerInsights,value=enabled
```

계정 전체 기본값으로 켜기(이후 생성되는 클러스터에 적용):

```bash
aws ecs put-account-setting-default \
  --name containerInsights \
  --value enabled
```

여기서 반드시 알아야 할 점: **이미 떠 있는 태스크에는 소급 적용되지 않는다**. 설정을 켠 뒤 새로 뜨는 태스크부터 지표가 수집된다. 그래서 운영 중인 서비스에 켰다면 한 바퀴 배포를 돌리거나 태스크를 교체해야 전체 지표가 채워진다. 켜자마자 대시보드가 비어 있다고 당황하지 않아도 된다.

`value`에는 `enabled`, `disabled` 외에 `enhanced`가 있다. enhanced는 컨테이너 단위, 인스턴스 단위까지 더 잘게 쪼갠 관측을 제공하는데 과금 모델이 다르다. 비용 절에서 다시 짚는다. 일반적인 서비스 단위 모니터링이면 `enabled`로 충분한 경우가 많다.

## Task와 Service 단위로 메트릭 보기

Container Insights 지표는 디멘션(dimension) 조합으로 범위가 정해진다. 같은 `MemoryUtilized`라도 어떤 디멘션을 붙이느냐에 따라 클러스터 전체인지 특정 서비스인지가 갈린다.

ECS에서 제공하는 디멘션 조합은 보통 셋이다.

- `ClusterName` 하나만 — 클러스터 전체 합산
- `ClusterName` + `ServiceName` — 특정 서비스
- `ClusterName` + `ServiceName` + `TaskDefinitionFamily` — 태스크 정의 패밀리 단위

알람이나 쿼리를 짤 때 디멘션을 정확히 맞춰야 한다. 서비스 단위로 알람을 걸려면 `ClusterName`과 `ServiceName`을 둘 다 지정해야 하고, 하나만 넣으면 매칭되는 지표가 없어 알람이 영원히 `INSUFFICIENT_DATA`에 머문다. 콘솔에서는 "메트릭이 없다"고만 보여서 디멘션 누락을 한참 못 찾는 경우가 있다.

순수하게 태스크 ID 단위(태스크 하나하나)로 시계열 지표를 보고 싶다면 표준 메트릭으로는 한계가 있다. CloudWatch 메트릭 디멘션은 위 세 조합까지다. 태스크 개별 추적이 필요하면 Container Insights가 함께 적재하는 **퍼포먼스 로그 이벤트**를 Logs Insights로 쿼리하는 쪽이 맞다. 이건 다음 절에서 본다.

## 퍼포먼스 로그와 Logs Insights

Container Insights는 지표만 만드는 게 아니다. 내부적으로 성능 데이터를 EMF(Embedded Metric Format) 형태의 로그 이벤트로 `/aws/ecs/containerinsights/{클러스터명}/performance` 로그 그룹에 적재하고, 거기서 메트릭을 추출한다. 이 로그 이벤트에는 메트릭으로는 안 보이는 태스크 ID, 컨테이너 단위 데이터까지 들어 있다.

특정 태스크 하나의 메모리 추이를 보고 싶을 때 이 로그 그룹을 Logs Insights로 쿼리한다.

```
fields @timestamp, TaskId, MemoryUtilized, CpuUtilized
| filter Type = "Task"
| filter ServiceName = "order-service"
| sort @timestamp desc
| limit 200
```

이 퍼포먼스 로그 그룹은 애플리케이션 로그 그룹과는 별개다. 여기서 [ECS 로그 관리](ECS_로그_관리.md)에서 다루는 애플리케이션 로그와 역할이 명확히 갈린다. 애플리케이션 로그 그룹(`/ecs/prod/order-service` 같은)은 stdout/stderr이고, 퍼포먼스 로그 그룹은 Container Insights가 자동 생성하는 성능 메트릭 원본이다. 둘을 헷갈려 퍼포먼스 로그 그룹에 Retention을 안 걸어두면 비용이 새는데, 이건 비용 절에서 다시 본다.

## CloudWatch 알람 구성

실제로 운영하면서 거는 알람 몇 가지를 구체적인 명령으로 정리한다.

### 메모리가 예약량에 근접할 때 (OOM 예방)

가장 중요한 알람이다. `MemoryUtilized`와 `MemoryReserved`를 메트릭 수식으로 나눠 실제 사용 비율을 계산한다. 기본 지표의 예약 기준 사용률을 안 믿고 절대값에서 직접 비율을 뽑는 이유는 앞에서 설명한 그대로다.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ecs-order-service-mem-pressure \
  --alarm-description "order-service 메모리가 예약량의 85% 초과" \
  --metrics '[
    {
      "Id": "util",
      "MetricStat": {
        "Metric": {
          "Namespace": "ECS/ContainerInsights",
          "MetricName": "MemoryUtilized",
          "Dimensions": [
            {"Name": "ClusterName", "Value": "prod"},
            {"Name": "ServiceName", "Value": "order-service"}
          ]
        },
        "Period": 60,
        "Stat": "Average"
      },
      "ReturnData": false
    },
    {
      "Id": "rsv",
      "MetricStat": {
        "Metric": {
          "Namespace": "ECS/ContainerInsights",
          "MetricName": "MemoryReserved",
          "Dimensions": [
            {"Name": "ClusterName", "Value": "prod"},
            {"Name": "ServiceName", "Value": "order-service"}
          ]
        },
        "Period": 60,
        "Stat": "Average"
      },
      "ReturnData": false
    },
    {
      "Id": "ratio",
      "Expression": "100 * util / rsv",
      "Label": "MemoryUtilizedPercent",
      "ReturnData": true
    }
  ]' \
  --evaluation-periods 5 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:ops-alerts
```

`Average`로 잡으면 서비스 평균이라 특정 태스크만 튀는 걸 놓친다. 태스크 하나만 OOM나는 패턴을 잡으려면 디멘션을 `TaskDefinitionFamily`까지 좁히고 `Maximum` 통계를 함께 보는 알람을 하나 더 두기도 한다.

### Pending Task가 쌓일 때 (용량 부족)

EC2 모드에서 클러스터 용량이 부족하면 태스크가 PENDING에 쌓인다. 이 상태가 몇 분 이어지면 알람을 울린다.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ecs-prod-pending-tasks \
  --namespace ECS/ContainerInsights \
  --metric-name PendingTaskCount \
  --dimensions Name=ClusterName,Value=prod Name=ServiceName,Value=order-service \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 5 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:ops-alerts
```

`treat-missing-data`를 `notBreaching`로 둔 이유가 있다. 태스크가 정상일 때는 `PendingTaskCount` 데이터 포인트가 0이거나 아예 안 들어오는 구간이 생긴다. 기본값(`missing`)으로 두면 데이터 없는 구간에서 알람 상태가 애매해진다. PENDING이 실제로 쌓일 때만 울리게 하려면 missing을 정상으로 취급해야 한다.

### Running이 Desired에 못 미칠 때

배포가 끝났는데 원하는 만큼 태스크가 안 떠 있거나, 태스크가 계속 죽어 replace되는 상황을 잡는다. `RunningTaskCount`와 `DesiredTaskCount`를 수식으로 빼서 차이가 나면 울린다.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ecs-order-service-under-desired \
  --metrics '[
    {"Id":"running","MetricStat":{"Metric":{"Namespace":"ECS/ContainerInsights","MetricName":"RunningTaskCount","Dimensions":[{"Name":"ClusterName","Value":"prod"},{"Name":"ServiceName","Value":"order-service"}]},"Period":60,"Stat":"Average"},"ReturnData":false},
    {"Id":"desired","MetricStat":{"Metric":{"Namespace":"ECS/ContainerInsights","MetricName":"DesiredTaskCount","Dimensions":[{"Name":"ClusterName","Value":"prod"},{"Name":"ServiceName","Value":"order-service"}]},"Period":60,"Stat":"Average"},"ReturnData":false},
    {"Id":"gap","Expression":"desired - running","Label":"MissingTasks","ReturnData":true}
  ]' \
  --evaluation-periods 5 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:ops-alerts
```

배포 중에는 롤링 교체 때문에 running이 잠깐 desired보다 적은 구간이 정상적으로 생긴다. `evaluation-periods`를 5분 정도로 잡아 일시적인 차이는 무시하고 지속적인 미달만 잡는 게 좋다. 1분으로 두면 배포할 때마다 알람이 운다.

## 비용 주의

Container Insights는 공짜가 아니다. 그리고 청구서가 어디서 나오는지 모르면 "켜기만 했는데 CloudWatch 비용이 늘었다"고 당황한다. 과금은 두 군데서 나온다.

첫째, **커스텀 메트릭**이다. Container Insights가 만드는 지표는 CloudWatch 커스텀 메트릭으로 청구된다. 메트릭 하나 = 메트릭 종류 × 디멘션 조합 하나다. 서비스가 많은 클러스터면 (지표 종류 약 10여 개) × (서비스 수) × (디멘션 조합 수)로 빠르게 수백 개가 된다. 서울 리전 기준 커스텀 메트릭은 개당 월 $0.30(첫 1만 개 구간) 수준이다. 서비스 50개짜리 클러스터면 메트릭만 수백 개라 월 수십 달러가 쉽게 나온다.

둘째, **퍼포먼스 로그 이벤트의 인제스트**다. 앞에서 본 `/aws/ecs/containerinsights/{클러스터}/performance` 로그 그룹에 성능 데이터가 계속 적재되고, 이게 CloudWatch Logs 인제스트로 과금된다. 태스크가 많고 수집 주기가 짧으면 이 인제스트가 메트릭 비용보다 커지기도 한다. 그리고 이 로그 그룹은 기본 Retention이 무제한이라 방치하면 저장 비용도 계속 쌓인다. 켜자마자 Retention부터 거는 게 맞다.

```bash
aws logs put-retention-policy \
  --log-group-name /aws/ecs/containerinsights/prod/performance \
  --retention-in-days 7
```

퍼포먼스 로그 원본을 길게 들고 있을 이유는 거의 없다. 메트릭은 CloudWatch가 별도로 15개월 보관하니, 원본 로그는 7~14일이면 충분하다. 인제스트 비용 구조는 [ECS 로그 관리](ECS_로그_관리.md)에서 다룬 것과 동일하다(서울 리전 GB당 약 $0.76).

`enhanced` 모드는 과금 모델이 또 다르다. 관측 대상(태스크, 인스턴스 등) 단위로 별도 요금이 붙는 구조라, 커스텀 메트릭 개수로 따지던 기존 감각으로 비용을 예측하면 어긋난다. enhanced를 켜기 전에는 대상 규모로 월 비용을 먼저 추산해보고 켜야 한다. 컨테이너 단위 세부 관측이 꼭 필요한 게 아니면 `enabled`로 두는 편이 비용 예측이 쉽다.

비용이 부담되는데 일부 지표만 필요한 경우, Container Insights를 끄고 EMF로 필요한 지표만 직접 내보내는 방식도 있다. 다만 직접 구현 부담이 있어, 처음에는 `enabled`로 켜두고 비용을 보면서 판단하는 쪽을 권한다.

## 로그 관리와의 역할 분리

마지막으로 이 문서와 [ECS 로그 관리](ECS_로그_관리.md)의 경계를 한 번 더 정리한다. 둘 다 CloudWatch를 쓰고 둘 다 "관측성"에 묶이다 보니 어느 문서를 봐야 하는지 헷갈리기 쉽다.

- 메트릭, 수치, 알람, 대시보드, 라이트사이징 → 이 문서(Container Insights)
- stdout/stderr, 로그 드라이버(awslogs/FireLens), 로그 라우팅, 로그 비용 → [ECS 로그 관리](ECS_로그_관리.md)

겹치는 지점이 두 군데 있다. 하나는 비용이다. 퍼포먼스 로그 인제스트는 로그 비용 구조를 따르지만, 그게 Container Insights를 켜서 생기는 것이라 이 문서에서 다뤘다. 다른 하나는 로그 기반 알람이다. "ERROR 로그가 분당 N건 넘으면 알람" 같은 메트릭 필터(metric filter) 알람은 로그에서 메트릭을 뽑아내는 것이라 로그 관리 문서 쪽이다. 알람의 소스가 지표면 여기, 로그면 거기로 보면 된다.

## 정리

Container Insights는 기본 ECS 지표가 못 주는 것들을 채운다. 핵심은 세 가지다. Reserved 기준 사용률만 보던 걸 Utilized 절대값으로 볼 수 있게 되고, 서비스 평균에 묻혀 있던 걸 Task 패밀리 단위로 쪼개 볼 수 있고, 기본 지표에 없던 `PendingTaskCount`, `RunningTaskCount` 같은 태스크 카운트 지표를 알람에 쓸 수 있다.

운영에 켤 때는 비용을 먼저 챙긴다. 켜자마자 퍼포먼스 로그 그룹에 Retention을 걸고, 서비스 수가 많은 클러스터면 커스텀 메트릭 개수로 월 비용을 추산해본다. 알람은 메모리 예약량 대비 사용 비율(OOM 예방), `PendingTaskCount`(용량 부족), Running과 Desired의 차이(태스크 미달) 세 개를 기본으로 깔아두면 대부분의 사고를 조기에 잡는다.
