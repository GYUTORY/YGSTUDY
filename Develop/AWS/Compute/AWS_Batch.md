---
title: AWS Batch 대량 배치 작업 처리
tags:
  - AWS
  - Batch
  - ECS
  - Fargate
  - EC2
  - Spot
  - Compute
updated: 2026-06-16
---

# AWS Batch 대량 배치 작업 처리

야간에 수천 건의 영상 인코딩을 돌려야 하거나, 매일 새벽 누적된 로그를 파싱해서 집계하거나, 머신러닝 학습 데이터를 전처리하는 잡을 수백 개 병렬로 던져야 할 때가 있다. 이런 걸 EC2 한 대 띄워놓고 셸 스크립트로 돌리면 처음엔 굴러가지만, 잡이 실패했을 때 재시도 처리, 동시 실행 개수 제어, 끝나면 인스턴스 끄기 같은 걸 전부 손으로 만들게 된다. 그러다 보면 결국 자체 배치 스케줄러를 만들고 있는 자신을 발견한다.

AWS Batch는 이 부분을 대신 처리한다. 잡을 큐에 던지면 알아서 컴퓨팅 자원을 띄우고, 잡을 실행하고, 다 끝나면 자원을 회수한다. 내부적으로는 ECS 위에서 돈다. 그래서 컨테이너 기반이고, ECS를 알면 Batch 개념도 빨리 잡힌다.

## 구성 요소 세 가지

Batch를 쓰려면 세 가지를 만들어야 한다. 이 셋의 관계를 이해하지 못하면 설정이 어디서 꼬였는지 못 찾는다.

```mermaid
graph LR
    A[Job 제출] --> B[Job Queue]
    B --> C[Compute Environment]
    C --> D[EC2 / Fargate 인스턴스]
    E[Job Definition] -.템플릿 참조.-> A
```

**Job Definition**은 잡의 템플릿이다. 어떤 컨테이너 이미지를 쓸지, vCPU와 메모리를 얼마나 줄지, 환경변수, 명령어, IAM 역할, 재시도 횟수 같은 걸 정의한다. 도커 컨테이너 실행 명세라고 보면 된다. 한 번 만들어두고 잡을 제출할 때마다 참조한다.

**Job Queue**는 제출된 잡이 대기하는 곳이다. 큐에는 우선순위가 있고, 하나의 큐가 여러 Compute Environment를 바라볼 수 있다. 잡이 큐에 들어오면 Batch 스케줄러가 연결된 Compute Environment에 자리가 있는지 보고 잡을 배치한다.

**Compute Environment**는 실제로 잡이 도는 컴퓨팅 자원이다. EC2를 쓸지 Fargate를 쓸지, On-Demand인지 Spot인지, 최소/최대 vCPU는 몇인지를 여기서 정한다.

제출 흐름은 단순하다. Job Definition으로 잡을 정의 → Job Queue에 제출 → 큐가 연결된 Compute Environment에서 실행. 잡 하나가 결국 ECS Task 하나로 변환되어 돌아간다.

## Compute Environment 선택

여기가 실무에서 가장 많이 고민하는 부분이다. EC2냐 Fargate냐, Spot이냐 On-Demand냐.

### Fargate

서버를 관리하기 싫으면 Fargate를 쓴다. 인스턴스 타입을 고를 필요도 없고, AMI 패치도 신경 안 써도 된다. 잡 하나당 vCPU와 메모리를 지정하면 그만큼 격리된 환경이 뜬다.

단점은 분명하다. vCPU와 메모리 조합에 제약이 있고(4 vCPU면 메모리 8~30GB 범위 같은 식), GPU를 못 쓴다. 잡 시작까지 걸리는 시간도 EC2보다 길게 느껴질 때가 있다. 잡이 짧고 가벼우면서 동시 실행 개수가 들쭉날쭉하면 Fargate가 편하다.

```json
{
  "computeEnvironmentName": "fargate-batch-env",
  "type": "MANAGED",
  "computeResources": {
    "type": "FARGATE",
    "maxvCpus": 256,
    "subnets": ["subnet-aaaa", "subnet-bbbb"],
    "securityGroupIds": ["sg-xxxx"]
  }
}
```

### EC2

잡이 무겁거나, GPU가 필요하거나, 인스턴스 단위로 비용을 깎고 싶으면 EC2다. 인스턴스 타입을 `optimal`로 두면 Batch가 큐에 쌓인 잡의 요구사항을 보고 적당한 타입을 고른다. 특정 타입을 강제하고 싶으면 직접 지정한다.

EC2 모드는 한 인스턴스에 여러 잡이 빽빽하게 들어갈 수 있다. 8 vCPU 인스턴스에 2 vCPU 잡 4개가 같이 도는 식이라 자원 활용률이 높다. Fargate는 잡마다 독립 환경이라 이런 식의 빽빽한 패킹이 안 된다.

```json
{
  "computeEnvironmentName": "ec2-spot-env",
  "type": "MANAGED",
  "computeResources": {
    "type": "SPOT",
    "allocationStrategy": "SPOT_CAPACITY_OPTIMIZED",
    "minvCpus": 0,
    "maxvCpus": 1024,
    "instanceTypes": ["c5", "c5a", "m5"],
    "spotIamFleetRole": "arn:aws:iam::123456789012:role/aws-ec2-spot-fleet-role",
    "subnets": ["subnet-aaaa", "subnet-bbbb"],
    "securityGroupIds": ["sg-xxxx"],
    "instanceRole": "arn:aws:iam::123456789012:instance-profile/ecsInstanceRole"
  }
}
```

### Spot

비용을 가장 크게 줄이는 방법이다. On-Demand 대비 70% 가까이 싸진다. 대신 AWS가 자원을 회수하면 잡이 중간에 죽는다. 그래서 Spot은 잡이 중간에 죽어도 재시도하면 되는, 멱등성 있는 작업에만 쓴다. 영상 인코딩, 데이터 전처리처럼 다시 돌려도 결과가 같은 작업이 해당된다.

Spot 회수가 잦으면 재시도 때문에 오히려 전체 처리 시간이 늘어난다. `allocationStrategy`를 `SPOT_CAPACITY_OPTIMIZED`로 두면 회수 가능성이 낮은 풀에서 인스턴스를 가져와서 중단 빈도가 줄어든다. `instanceTypes`에 여러 타입을 넣어주는 것도 같은 이유다. 한 타입만 지정하면 그 풀이 마르는 순간 잡이 다 멈춘다.

`minvCpus`를 0으로 두면 큐가 비었을 때 인스턴스가 전부 내려간다. 잡이 없는데도 인스턴스가 계속 떠 있어서 비용이 새는 사고를 막으려면 이 값을 0으로 둬야 한다. 다만 매번 인스턴스를 새로 띄우면 시작 지연이 생기므로, 잡이 끊임없이 들어오는 환경이면 약간의 최소값을 두기도 한다.

## 의존성 있는 작업 체이닝

배치 작업은 단독으로 끝나는 경우가 드물다. 전처리 → 학습 → 후처리 같은 단계가 줄줄이 엮인다. Batch는 잡 제출 시 `dependsOn`으로 선행 잡을 지정한다.

```bash
# 1단계: 전처리
PRE=$(aws batch submit-job \
  --job-name preprocess \
  --job-queue main-queue \
  --job-definition preprocess-def \
  --query jobId --output text)

# 2단계: 전처리가 끝나야 학습 시작
TRAIN=$(aws batch submit-job \
  --job-name train \
  --job-queue main-queue \
  --job-definition train-def \
  --depends-on jobId=$PRE \
  --query jobId --output text)

# 3단계: 학습이 끝나야 후처리
aws batch submit-job \
  --job-name postprocess \
  --job-queue main-queue \
  --job-definition postprocess-def \
  --depends-on jobId=$TRAIN
```

선행 잡이 `SUCCEEDED` 상태가 돼야 다음 잡이 `RUNNABLE`로 넘어간다. 선행 잡이 실패하면 의존하는 잡은 영영 실행되지 않고 `PENDING`에 멈춰 있다가 결국 실패 처리된다. 이걸 모르면 "왜 학습 잡이 안 도냐"고 한참 헤매는데, 원인은 전처리 잡이 조용히 죽어 있던 거다.

### 배열 잡과 N_TO_N 의존성

같은 잡을 인덱스만 바꿔 대량으로 돌릴 땐 배열 잡(array job)을 쓴다. `--array-properties size=1000`으로 제출하면 자식 잡 1000개가 생기고, 각 잡은 `AWS_BATCH_JOB_ARRAY_INDEX` 환경변수로 자기 인덱스를 받는다. 데이터를 1000조각으로 나눠 병렬 처리할 때 쓴다.

배열 잡끼리 의존성을 걸 때 `N_TO_N` 타입이 있다. A 배열 잡의 인덱스 5번이 끝나야 B 배열 잡의 인덱스 5번이 도는 식으로 인덱스 단위로 묶인다. 전체가 다 끝나길 기다리지 않고 짝이 맞는 것부터 진행하므로 파이프라인 전체가 빨라진다.

```bash
aws batch submit-job \
  --job-name stage-b \
  --job-queue main-queue \
  --job-definition stage-b-def \
  --array-properties size=1000 \
  --depends-on jobId=$STAGE_A_ID,type=N_TO_N
```

## 재시도 정책

잡은 실패한다. Spot 회수로 죽기도 하고, 네트워크 일시 장애로 죽기도 하고, 코드 버그로 죽기도 한다. 이걸 구분 없이 무조건 재시도하면 버그 있는 잡이 5번 돌면서 자원만 태운다.

Batch는 `retryStrategy`에 `evaluateOnExit`를 두고 종료 사유별로 재시도 여부를 다르게 줄 수 있다.

```json
{
  "jobDefinitionName": "encode-def",
  "type": "container",
  "retryStrategy": {
    "attempts": 5,
    "evaluateOnExit": [
      {
        "onStatusReason": "Host EC2*",
        "action": "RETRY"
      },
      {
        "onReason": "CannotPullContainerError*",
        "action": "EXIT"
      },
      {
        "onExitCode": "1",
        "action": "EXIT"
      },
      {
        "onExitCode": "*",
        "action": "RETRY"
      }
    ]
  }
}
```

위 설정의 의도는 이렇다. Spot 회수(`Host EC2*`)는 재시도한다. 이미지를 못 받아오는 건(`CannotPullContainerError`) 재시도해봐야 똑같이 실패하니 바로 종료한다. 종료 코드 1은 애플리케이션 로직 에러로 보고 재시도하지 않는다. 그 외 종료 코드는 일시 장애일 수 있으니 재시도한다.

`evaluateOnExit`는 위에서부터 순서대로 평가하고 처음 매칭되는 규칙을 적용한다. 그래서 구체적인 규칙을 위에, `onExitCode: "*"` 같은 포괄 규칙을 맨 아래에 둔다. 순서를 잘못 두면 모든 게 첫 규칙에 걸려서 의도와 다르게 동작한다.

재시도 횟수만 늘리고 `evaluateOnExit`를 안 쓰면, 코드 버그로 죽는 잡도 `attempts`만큼 꼬박꼬박 재시도하면서 비용과 시간을 낭비한다. 종료 코드로 영구 실패와 일시 실패를 구분하는 게 핵심이다.

타임아웃도 같이 건다. 잡이 무한 루프에 빠지거나 외부 의존성 때문에 멈춰 있으면 인스턴스를 계속 점유한다. `timeout.attemptDurationSeconds`를 걸어두면 그 시간을 넘긴 잡을 강제 종료한다. 최소 60초 이상이어야 한다.

## 실패한 잡 디버깅

Batch 잡이 실패했는데 원인을 못 찾는 경우가 자주 있다. 순서대로 확인한다.

**1. 잡 상태와 statusReason 확인.** `describe-jobs`로 잡의 상태 전이와 실패 사유를 본다.

```bash
aws batch describe-jobs --jobs <job-id> \
  --query 'jobs[0].{status:status, reason:statusReason, container:container.reason, exitCode:container.exitCode}'
```

`statusReason`에 "Host EC2 instance-id ... terminated"가 보이면 Spot 회수다. "CannotPullContainerError"면 이미지 경로나 ECR 권한 문제다. "ResourceInitializationError"면 보통 IAM 역할이나 네트워크(서브넷에서 ECR/S3 접근 불가) 문제다.

**2. 잡이 RUNNABLE에서 안 넘어가는 경우.** 이게 제일 헷갈린다. 잡이 `RUNNABLE` 상태로 계속 멈춰 있으면 실패가 아니라 자원을 못 잡은 거다. 흔한 원인:

- Compute Environment의 `maxvCpus`보다 잡이 요구하는 vCPU가 커서 영영 못 들어감
- Fargate인데 vCPU/메모리 조합이 유효하지 않음
- 서브넷에 가용 IP가 없음
- Compute Environment가 `INVALID` 상태(보통 IAM 역할이나 인스턴스 프로파일 설정 오류)
- Spot 가격 한도에 걸려서 인스턴스가 안 떠짐

`describe-compute-environments`로 상태가 `VALID`인지, `statusReason`에 뭐가 찍혔는지부터 본다.

**3. CloudWatch Logs 확인.** 잡이 실제로 실행됐다면 stdout/stderr가 CloudWatch Logs의 `/aws/batch/job` 로그 그룹에 쌓인다. `describe-jobs` 응답의 `container.logStreamName`으로 정확한 스트림을 찾아 들어간다. 컨테이너 안에서 무슨 에러가 났는지는 결국 여기서 봐야 한다.

```bash
LOG_STREAM=$(aws batch describe-jobs --jobs <job-id> \
  --query 'jobs[0].container.logStreamName' --output text)

aws logs get-log-events \
  --log-group-name /aws/batch/job \
  --log-stream-name "$LOG_STREAM" \
  --query 'events[*].message' --output text
```

로그 스트림이 아예 안 생겼다면 컨테이너가 시작조차 못 한 거다. 이미지 풀 실패, 명령어 오타, 진입점 문제를 의심한다.

## ECS RunTask와의 차이, 언제 Batch를 쓰나

Batch가 내부적으로 ECS를 쓰니 "그냥 ECS RunTask로 잡 던지면 안 되나" 하는 의문이 든다. 둘 다 컨테이너로 작업을 돌리지만 책임 범위가 다르다.

`ECS RunTask`는 태스크 하나를 실행하는 API다. 호출하면 즉시 태스크를 띄운다. 자원이 없으면 그냥 실패한다(EC2 모드 기준). 큐도 없고, 재시도도 없고, 자원이 부족하면 알아서 인스턴스를 늘려주지도 않는다. 동시 실행 개수 제어, 우선순위, 의존성 같은 건 직접 만들어야 한다.

`AWS Batch`는 그 위에 잡 스케줄링 계층을 얹은 것이다. 큐에 잡을 쌓아두고, 자원이 부족하면 Compute Environment를 스케일 업하고, 자원이 나면 큐에서 잡을 꺼내 배치하고, 끝나면 스케일 다운한다. 재시도 정책, 의존성 체이닝, 배열 잡, 우선순위 큐가 다 내장돼 있다.

판단 기준은 이렇다.

- **단발성 또는 상시 실행 서비스** → ECS 서비스나 RunTask. API 서버, 워커 데몬처럼 계속 떠 있어야 하는 건 Batch가 아니다. Batch는 잡이 끝나면 자원을 내리는 게 전제다.
- **이벤트 하나에 짧은 처리 하나** → Lambda 또는 RunTask. S3 업로드되면 썸네일 만드는 정도는 Lambda가 낫다.
- **대량의 잡을 큐에 쌓아 자원 한도 안에서 순차/병렬 처리** → Batch. 수천 개 잡을 던져두고 "동시 256 vCPU 안에서 알아서 다 처리해줘"가 필요한 순간이 Batch의 영역이다.
- **잡 간 의존성, 단계별 파이프라인** → Batch. 의존성을 직접 관리하기 시작하면 Batch나 Step Functions를 봐야 한다.

복잡한 분기와 상태 머신이 필요하면 Step Functions로 오케스트레이션하고 각 단계를 Batch 잡으로 실행하는 조합을 쓰기도 한다. Step Functions가 흐름을 제어하고, Batch가 무거운 컴퓨팅을 담당하는 식이다.

정리하면, "잡이 잠깐 떴다가 끝나고, 그런 잡이 대량으로 들어오고, 자원을 한도 안에서 굴리면서 다 끝나면 비용을 0으로 내리고 싶다" — 이 조건이면 Batch다. 상시 떠 있는 서비스이거나 이벤트당 가벼운 처리면 Batch는 과하다.
