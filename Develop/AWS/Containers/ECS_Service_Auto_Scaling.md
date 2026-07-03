---
title: ECS Service Auto Scaling
tags: [aws, ecs, auto-scaling, application-auto-scaling, fargate, cloudwatch]
updated: 2026-04-20
---

# ECS Service Auto Scaling

## 개요

ECS Service Auto Scaling은 실제로는 ECS가 직접 수행하는 기능이 아니다. 내부적으로 **Application Auto Scaling(AAS)** 이라는 별도 AWS 서비스가 ECS 서비스의 `desiredCount`를 조정한다. 이 구조를 모르면 디버깅할 때 한참을 헤맨다. 예를 들어 "스케일링이 안 된다"고 할 때 봐야 할 로그는 ECS 서비스 이벤트가 아니라 Application Auto Scaling의 활동(Scaling Activity)이고, CloudWatch 경보 상태다.

용어부터 정리하자.

- **Scalable Target**: 스케일링 대상 자체. ECS 서비스 하나당 하나 등록한다. `service/{clusterName}/{serviceName}` 형태의 Resource ID를 가진다.
- **Scalable Dimension**: `ecs:service:DesiredCount`로 고정이다.
- **Scaling Policy**: 실제 스케일링 규칙. Target Tracking, Step Scaling, Scheduled 중 하나.
- **MinCapacity / MaxCapacity**: Scalable Target에 등록한 하한과 상한. 서비스의 desiredCount는 이 범위를 벗어날 수 없다.

초보자가 자주 헷갈리는 지점은 ECS 서비스 자체에 min/max 설정이 있는 게 아니라는 점이다. ECS 서비스가 가진 건 `desiredCount` 하나뿐이고, min/max는 Scalable Target 쪽 속성이다.

## 스케일링 정책 3종의 차이

Application Auto Scaling이 지원하는 ECS 서비스 대상 정책은 세 가지다. 실무에서 선택 기준이 꽤 명확하니 외워두자.

### Target Tracking Scaling

가장 많이 쓰는 방식이다. "CPU 사용률 60%를 유지해라" 같이 **목표값 하나만** 지정하면 AAS가 알아서 CloudWatch 경보를 만들고 스케일 인/아웃을 수행한다. 내부적으로는 `TargetTrackingScaling-...`이라는 경보가 자동 생성된다(직접 수정하면 안 된다. 정책 업데이트할 때 덮어써진다).

```json
{
  "PolicyName": "cpu-target-tracking",
  "PolicyType": "TargetTrackingScaling",
  "ServiceNamespace": "ecs",
  "ResourceId": "service/my-cluster/my-service",
  "ScalableDimension": "ecs:service:DesiredCount",
  "TargetTrackingScalingPolicyConfiguration": {
    "TargetValue": 60.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300,
    "DisableScaleIn": false
  }
}
```

Target Tracking은 속도가 **대칭적이지 않다**. 스케일 아웃은 빠르게(CloudWatch 경보가 일반적으로 3분 내 발생), 스케일 인은 보수적으로 동작한다. 일부러 그렇게 설계되어 있다. 트래픽이 튈 때 과소 프로비저닝으로 장애나는 쪽이 더 치명적이기 때문이다.

`DisableScaleIn: true`로 두고 스케일 인을 막고 Step Scaling 정책을 따로 붙여 수동 제어하는 패턴도 실무에서 종종 본다. 예측이 가능한 워크로드에서 의도적으로 비대칭 정책을 만들 때 쓴다.

### Step Scaling

경보 임계치와 조정 단계를 직접 설계한다. "CPU 70% 넘으면 1대, 85% 넘으면 3대 늘려라" 같은 **비선형 반응** 이 가능하다.

```json
{
  "PolicyType": "StepScaling",
  "StepScalingPolicyConfiguration": {
    "AdjustmentType": "ChangeInCapacity",
    "Cooldown": 60,
    "MetricAggregationType": "Average",
    "StepAdjustments": [
      { "MetricIntervalLowerBound": 0,  "MetricIntervalUpperBound": 15, "ScalingAdjustment": 1 },
      { "MetricIntervalLowerBound": 15, "MetricIntervalUpperBound": 30, "ScalingAdjustment": 2 },
      { "MetricIntervalLowerBound": 30, "ScalingAdjustment": 4 }
    ]
  }
}
```

`MetricIntervalLowerBound`는 **경보 임계치 대비 상대값**이다. 즉 경보가 CPU 70%에서 울리면 위 구간은 각각 70~85%, 85~100%, 100% 이상이 된다. 이 개념을 잘못 이해하면 "구간이 이상한데 왜 안 울리지?" 하는 문제를 겪는다.

Step Scaling은 CloudWatch 경보를 직접 만들어 정책에 연결한다. 그래서 커스텀 지표(RabbitMQ 큐 깊이, SQS 메시지 수, 애플리케이션 내부 지표 등)로 스케일링하려면 Step Scaling을 선택해야 한다.

### Scheduled Scaling

특정 시각에 min/max를 조정한다. 매일 아침 9시에 5 → 20으로 올리고 저녁 9시에 20 → 5로 내리는 식이다. **desiredCount를 직접 건드리는 게 아니라 min/max를 바꾸는 것** 임을 알아두자.

```bash
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --scheduled-action-name morning-scale-up \
  --resource-id service/my-cluster/my-service \
  --scalable-dimension ecs:service:DesiredCount \
  --schedule "cron(0 9 * * ? *)" \
  --scalable-target-action MinCapacity=10,MaxCapacity=30
```

Scheduled Scaling은 Target Tracking과 같이 쓰는 게 일반적이다. 스케줄로 min을 밀어올려 베이스라인을 확보한 뒤, Target Tracking이 그 위에서 트래픽에 맞춰 조정하는 구조다. 아침에 갑자기 트래픽이 몰려서 스케일 아웃이 따라가지 못하는 문제를 피할 때 유용하다.

## 지표 선택 기준

ECS 서비스에 쓸 수 있는 Predefined Metric은 셋이다. 선택을 잘못하면 스케일링이 엉뚱하게 동작한다.

### ECSServiceAverageCPUUtilization

Task 레벨 CPU 사용률을 서비스 전체로 평균낸 값이다. 태스크 정의의 `cpu` 값 대비 사용률이다. 범용적이지만 다음 경우에는 부적합하다.

- CPU를 거의 안 쓰고 네트워크 I/O나 디스크 I/O가 지배적인 워크로드(예: 프록시, 파일 서버)
- Java 워크로드에서 JIT 워밍업 때문에 시작 직후 CPU가 튀어 스케일 아웃이 과도하게 도는 경우
- 멀티코어 태스크인데 단일 스레드 위주라 전체 CPU는 낮게 보이는 경우

후자는 현장에서 많이 본 삽질이다. vCPU 4인 태스크에서 1코어만 100% 써도 평균 CPU는 25%다. 이럴 땐 CPU 기준이 아니라 응답 시간이나 요청 수 기반 지표가 맞다.

### ECSServiceAverageMemoryUtilization

메모리 사용률이다. JVM처럼 **메모리를 선점적으로 잡아두는 런타임** 에서는 쓸모가 없다. 트래픽과 무관하게 메모리 사용률이 일정 수준에서 고정되기 때문이다. 또 메모리는 스케일 인 트리거로 쓰기 곤란하다. GC가 돌기 전까지는 해제되지 않아 실제 부하가 줄어도 지표는 그대로다. 메모리 지표는 "누수가 의심되는 서비스에 안전장치로 거는 보조 정책" 정도가 적절하다.

### ALBRequestCountPerTarget

ALB 타겟 그룹 기준 요청 수를 **타겟 하나당** 값으로 환산한 지표다. 웹 API 서비스에 가장 잘 맞는 지표다. 트래픽과 선형관계라 예측 가능하고, CPU 같은 간접 지표와 달리 직접 부하를 반영한다.

전제 조건: ECS 서비스가 ALB에 붙어 있어야 하고, Scalable Target에 ALB 타겟 그룹 ARN을 연결해줘야 한다.

```json
{
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ALBRequestCountPerTarget",
    "ResourceLabel": "app/my-alb/50dc6c495c0c9188/targetgroup/my-targets/73e2d6bc24d8a067"
  },
  "TargetValue": 100
}
```

`ResourceLabel`은 ALB ARN과 타겟 그룹 ARN의 suffix를 `/`로 연결한 형태다. 형식이 안 맞으면 등록 자체가 거부된다. 이 지표는 타겟 기준이라서 스케일 인/아웃이 아주 깔끔하게 동작한다. 태스크 수가 늘면 분모가 커지므로 지표가 즉시 낮아지고, 반대도 마찬가지다.

### 커스텀 지표 기반 스케일링

SQS 큐 길이, Kafka consumer lag, DB 커넥션 수 같은 외부 지표로 스케일링하려면 CloudWatch 경보를 만들고 Step Scaling 정책을 붙이는 방식이 일반적이다. Target Tracking에서도 `CustomizedMetricSpecification`으로 가능하지만 튜닝이 까다로워 경보 + Step이 더 관리하기 쉽다.

```json
{
  "CustomizedMetricSpecification": {
    "MetricName": "ApproximateNumberOfMessagesVisible",
    "Namespace": "AWS/SQS",
    "Dimensions": [{"Name": "QueueName", "Value": "job-queue"}],
    "Statistic": "Average"
  },
  "TargetValue": 100
}
```

SQS 큐 기반 스케일링에서 자주 놓치는 부분: **백로그 per task** 개념이다. 예를 들어 태스크 하나가 분당 100개를 처리하고 백로그 허용치가 60초라면 목표 값은 `태스크당 100개`여야 한다. 큐 전체 길이를 목표로 삼으면 태스크가 많아져도 지표가 안 떨어져 상한까지 치고 올라간다.

## 쿨다운과 스케일링 지연 튜닝

쿨다운은 스케일링 활동이 한 번 발생한 뒤 다음 활동까지의 대기 시간이다. 너무 짧으면 덜컹거리고 너무 길면 반응이 느리다.

- **ScaleOutCooldown**: 스케일 아웃 후 대기 시간. 보통 60~120초. 새로 뜬 태스크가 안정화되고 지표에 반영될 시간이 필요하다.
- **ScaleInCooldown**: 스케일 인 후 대기 시간. 300~600초 권장. 공격적으로 줄이면 트래픽 파동에 따라 태스크가 떴다 사라졌다 반복한다.

ECS 태스크가 뜨는 데 실제로 걸리는 시간을 측정해보고 쿨다운을 설정해야 한다. 이미지 pull에 2분, 애플리케이션 부팅에 1분 걸리면 ScaleOutCooldown을 120초 아래로 두면 안 된다. 새 태스크가 실제 트래픽을 받기도 전에 다음 스케일 아웃이 트리거될 수 있기 때문이다.

Target Tracking은 내부적으로 **3분짜리 CloudWatch 경보 두 개**(High/Low)를 쓴다. 즉 지표가 임계를 넘긴 뒤 경보가 울리는 데만 최소 3분이 걸린다. 쿨다운을 0으로 맞춰도 3분 주기 아래로는 못 내려간다. 더 빠른 반응이 필요하면 Step Scaling + 1분 주기 경보 조합을 고려하자.

## Fargate vs EC2 모드에서의 동작 차이

같은 Auto Scaling 정책이라도 실행 모드에 따라 체감이 완전히 다르다.

### Fargate

- 용량 고민이 없다. Scalable Target만 조정하면 AWS가 태스크 실행 인프라를 즉시 제공한다.
- 스케일 아웃 속도는 보통 20~60초 수준(이미지 pull 시간이 지배적).
- 단점: 태스크당 비용이 EC2보다 비싸고, 스폿/온디맨드 혼합이 제한적이다(Fargate Spot 있으나 중단 가능성).
- Capacity Provider Strategy로 Fargate/Fargate Spot을 비율 할당하는 방식이 일반적이다.

### EC2

- 두 층의 스케일링이 필요하다. **서비스 레벨**(desiredCount)과 **클러스터 레벨**(EC2 인스턴스 수).
- 클러스터에 빈 용량이 없으면 서비스 스케일 아웃이 **Pending 상태로 정체**된다. 이게 실무에서 가장 많이 발생하는 문제다.
- 해법: **Cluster Auto Scaling(Capacity Provider + ASG)** 을 구성해 서비스 수요에 따라 EC2도 자동으로 늘어나게 한다.
- Cluster Auto Scaling은 `CapacityProviderReservation` 지표를 기반으로 ASG를 조정한다. `targetCapacity=100`이면 클러스터 사용률을 100%로 맞추려 하고, `80`이면 20% 여유를 두려 한다. 여유 없이 100으로 두면 스케일 아웃 시 **매번 EC2 기동을 기다려야 한다**(2~3분 추가 지연).
- 실무에서는 80~90 사이가 무난하다.

EC2 모드에서 스케일 아웃이 느리다는 이슈를 받으면 먼저 물어야 할 것은 "Capacity Provider가 걸려 있는가, 클러스터에 여유 용량이 있는가"다.

## desiredCount 충돌: 배포 중 스케일링

실무에서 한 번씩 부딪히는 치명적인 함정이다.

ECS 서비스 배포는 내부적으로 `UpdateService`를 호출해 task definition revision을 바꾼다. 이 과정에서 롤링 배포가 진행되고, 새 태스크가 뜨는 동안 기존 태스크가 유지되므로 일시적으로 desiredCount × 2에 가까운 태스크가 돈다(기본 `maximumPercent: 200`).

이때 Auto Scaling이 동시에 작동하면 다음 문제가 생긴다.

- 배포 중에 지표가 튀어서 스케일 아웃이 발생 → desiredCount가 바뀜 → 배포 컨트롤러와 경합
- 반대로 스케일 인이 발생해 desiredCount가 내려가면 방금 새로 띄운 태스크가 즉시 종료

해결책은 두 가지다.

1. **CodeDeploy Blue/Green** 을 쓰면 배포 중 스케일링이 자동으로 **일시 정지**된다. 배포가 끝나면 다시 활성화.
2. **Rolling Update** 를 쓴다면 배포 시작 시 AAS 정책을 `suspend`하거나 `MinCapacity`를 현재값으로 고정해야 한다.

CI/CD 파이프라인에서 배포 전 `register-scalable-target --suspended-state DynamicScalingInSuspended=true,DynamicScalingOutSuspended=true`로 잠그고, 배포 후 해제하는 패턴을 쓰면 안전하다.

또 하나 주의할 점: Terraform으로 ECS Service와 AAS를 같이 관리할 때 `desired_count`를 Terraform이 계속 덮어쓰는 문제다. Auto Scaling이 desiredCount를 바꿔도 Terraform은 코드상 값으로 되돌리려 한다. 해결은 `lifecycle { ignore_changes = [desired_count] }`를 ecs_service 리소스에 넣는 것. 이걸 빼먹으면 `terraform apply` 칠 때마다 서비스가 원래 태스크 수로 리셋된다.

## 스케일 아웃이 느릴 때 원인 분석

"스케일 아웃은 도는데 체감이 안 난다"는 이슈의 전형적인 원인들이다. 위에서부터 순서대로 체크한다.

### CloudWatch 경보 지연

지표 수집 주기와 경보 평가 주기를 확인한다. 기본 1분 주기 지표에 3분 연속 임계 초과 경보면 최소 3분 지연이 불가피하다. 빠른 반응이 필요하면 Period 60s + EvaluationPeriods 1로 조정.

### 이미지 pull 시간

Fargate에서 가장 흔한 원인이다. 이미지가 크거나 ECR이 다른 리전이면 pull에만 1~2분이 걸린다. 해결 방법:

- 이미지 슬리밍(multi-stage build, distroless)
- 같은 리전 ECR 사용
- Fargate 1.4.0 이상에서 제공되는 이미지 캐싱 사용(같은 AZ 내 워커가 pull 결과 공유)

EC2 모드라면 인스턴스에 이미지가 이미 있으면 pull이 스킵되니 Warm 상태에서는 빠르다.

### ENI 어태치 시간

Fargate의 각 태스크에는 자체 ENI가 붙는다. VPC 환경에서 ENI를 프로비저닝하고 Security Group을 붙이고 IP를 할당하는 데 **수십 초**가 걸린다. 과거엔 1분 가까이 걸린 적도 있고, 현재는 빠르지만 여전히 측정 가능한 지연이다. `awsvpc` 네트워크 모드를 쓰는 EC2 태스크도 마찬가지다.

진단은 ECS Task 이벤트에서 각 상태 전이 타임스탬프를 본다. `PROVISIONING → PENDING → ACTIVATING → RUNNING` 각 단계 소요 시간이 찍힌다. `PROVISIONING` 체류가 길면 ENI가 범인이다.

### 헬스체크 Grace Period

ALB에 연결된 서비스에서 `healthCheckGracePeriodSeconds`가 너무 길면, 태스크가 RUNNING 상태가 되어도 일정 시간 동안 타겟 그룹에 Unhealthy 판정이 유예된다. 반대로 너무 짧으면 부팅 중에 Unhealthy로 찍혀 재기동된다. 애플리케이션 부팅 시간보다 30~60초 여유를 둔다.

### Target Capacity 부족 (EC2 모드)

위에서 언급한 대로, Capacity Provider의 `targetCapacity`가 100이면 서비스 스케일 아웃마다 EC2 기동을 기다려야 한다. EC2 시작 → ECS 에이전트 등록 → 태스크 배치 → 컨테이너 기동 순이라 3~5분이 쉽게 소요된다.

### Task Definition의 리소스 설정

태스크에 CPU/메모리를 과다 할당하면 클러스터 여유가 있어도 배치가 실패한다. 반대로 과소 할당이면 태스크는 뜨지만 실제 처리가 안 된다. 클러스터 이벤트에 `insufficient CPU` 또는 `insufficient memory`가 찍힌다면 이 경우다.

## min/max 설정 실수 사례

실무에서 반복해서 본 실수들이다.

- **MaxCapacity를 너무 낮게 설정**: 트래픽이 몰려도 상한에 걸려 못 늘어난다. CloudWatch Alarm은 INSUFFICIENT_DATA 또는 ALARM 상태로 지속되지만 desiredCount는 그대로라 디버깅이 어렵다. AAS Scaling Activity 로그에 `Failed to scale because the maximum capacity has been reached`라고 찍힌다.
- **MinCapacity=0 설정**: 비용 절감 목적으로 쓰는데 위험하다. 태스크 0 상태에서 트래픽이 들어오면 첫 요청은 최소 수십 초~수 분 대기한다(콜드 스타트). 배치 작업이나 이벤트 드리븐 워크로드가 아니면 min=1이 안전선이다.
- **MinCapacity=MaxCapacity**: 스케일링이 완전히 무력화된다. 같은 값을 넣고 "왜 안 늘어나지?"를 묻는 케이스가 많다.
- **여러 정책의 상한이 경합**: Target Tracking은 desiredCount를 올리려 하는데 Scheduled Action이 MaxCapacity를 내려놓은 상태면 올라가지 않는다. 우선순위는 MinCapacity/MaxCapacity 경계가 항상 이긴다.
- **배포 시 MaximumPercent와 desiredCount 조합 고려 누락**: `desiredCount=100, maximumPercent=200`이면 배포 중 최대 200 태스크. 클러스터 용량이나 타겟 그룹 한도가 이걸 못 받치면 배포 자체가 멈춘다.

## 운영 중 자주 쓰는 명령어

Scalable Target 확인:

```bash
aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids service/my-cluster/my-service
```

최근 스케일링 활동 조회(스케일링이 안 될 때 가장 먼저 볼 곳):

```bash
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/my-cluster/my-service \
  --max-items 20
```

정책 일시 중단(배포 중 사용):

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/my-cluster/my-service \
  --scalable-dimension ecs:service:DesiredCount \
  --suspended-state '{
    "DynamicScalingInSuspended": true,
    "DynamicScalingOutSuspended": true,
    "ScheduledScalingSuspended": false
  }'
```

강제로 태스크 수 조정(Auto Scaling 범위 내에서만 유효):

```bash
aws ecs update-service \
  --cluster my-cluster \
  --service my-service \
  --desired-count 10
```

이 명령은 min/max 범위를 벗어나지 못한다. 넘어가면 다음번 스케일링 평가 시 AAS가 강제로 되돌린다. MaxCapacity를 먼저 올리고 desiredCount를 조정해야 반영된다.

## 정리

ECS Service Auto Scaling은 단순해 보여도 실제로는 AAS, CloudWatch, Capacity Provider, 배포 파이프라인이 서로 엮여 있다. 이슈가 생겼을 때 체크할 순서는 보통 이렇다.

1. Scaling Activities 로그를 먼저 본다(경보 상태 말고).
2. MinCapacity/MaxCapacity 경계에 걸렸는지 확인.
3. 배포 중이라면 desiredCount 경합을 의심.
4. 스케일링이 돌긴 하는데 태스크가 늦게 뜨면 Task 이벤트 타임라인에서 PROVISIONING/PENDING 체류 시간을 본다.
5. EC2 모드면 Capacity Provider와 ASG 상태를 확인.

Target Tracking + ALBRequestCountPerTarget 조합이 가장 많이 쓰이는 기본값이지만, 워크로드 특성에 따라 Step Scaling + 커스텀 지표나 Scheduled + Target Tracking 복합 구성이 필요하다. 지표 선택과 쿨다운 튜닝을 실제 태스크 기동 시간 측정에 근거해 잡아야 한다.
