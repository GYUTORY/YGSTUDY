---
title: EC2 T 시리즈 인스턴스
tags: [aws, ec2, t-series, burstable, cpu-credit, compute]
updated: 2026-04-01
---

# EC2 T 시리즈 인스턴스

## T 시리즈가 뭔가

EC2 T 시리즈는 버스트 가능(Burstable) 인스턴스다. 평소에는 vCPU의 일정 비율(baseline)만 쓸 수 있고, 남는 CPU 시간은 크레딧으로 쌓인다. 트래픽이 몰리거나 빌드를 돌릴 때 쌓아둔 크레딧을 소비해서 100%까지 CPU를 쓸 수 있다.

핵심은 **baseline CPU**다. 이 수치가 내가 "공짜로" 쓸 수 있는 CPU 비율이고, 이걸 넘기면 크레딧을 태운다.

## 인스턴스 타입별 Baseline CPU

실제 인스턴스 선택할 때 가장 먼저 봐야 하는 테이블이다.

| 인스턴스 | vCPU | 메모리(GiB) | Baseline(vCPU당) | 시간당 크레딧 적립 | 최대 크레딧 잔액 |
|----------|------|-------------|-------------------|-------------------|-----------------|
| t3.nano | 2 | 0.5 | 5% | 6 | 144 |
| t3.micro | 2 | 1 | 10% | 12 | 288 |
| t3.small | 2 | 2 | 20% | 24 | 576 |
| t3.medium | 2 | 4 | 20% | 24 | 576 |
| t3.large | 2 | 8 | 30% | 36 | 864 |
| t3.xlarge | 4 | 16 | 30% | 96 | 2304 |
| t3.2xlarge | 8 | 32 | 30% | 192 | 4608 |

T3a는 AMD 기반이고 baseline 수치는 T3와 동일하다. 가격이 약 10% 싸다.

T4g(Graviton ARM 기반)도 baseline 수치는 T3와 같다. 가격이 T3 대비 약 20% 싸다.

T2는 baseline이 다르다:

| 인스턴스 | vCPU | Baseline(vCPU당) | 시간당 크레딧 적립 | 최대 크레딧 잔액 |
|----------|------|-------------------|-------------------|-----------------|
| t2.micro | 1 | 10% | 6 | 144 |
| t2.small | 1 | 20% | 12 | 288 |
| t2.medium | 2 | 20% | 24 | 576 |
| t2.large | 2 | 30% | 36 | 864 |

## CPU 크레딧 계산법

크레딧 1개 = vCPU 1개를 1분간 100% 사용하는 권리다.

계산할 때 중요한 건 **적립 속도 vs 소비 속도**다.

### 예시: t3.micro에서 CPU 70%를 지속 사용

t3.micro의 baseline은 10%이고, vCPU가 2개다.

- 시간당 크레딧 적립: 12개
- CPU 70% 사용 시 소비: vCPU 2개 × (70% - 10%) × 60분 = 72 크레딧/시간
- 순 소비: 72 - 12 = 시간당 60 크레딧 순감

t3.micro 최대 잔액이 288이니까, 만충 상태에서 시작하면 **288 ÷ 60 = 4.8시간** 후 크레딧이 바닥난다.

### 예시: t3.small에서 CPU 40% 지속 사용

t3.small의 baseline은 20%, vCPU 2개.

- 시간당 적립: 24개
- CPU 40% 사용 시 소비: 2 × (40% - 20%) × 60 = 24 크레딧/시간
- 순 소비: 24 - 24 = 0

baseline의 정확히 2배를 쓰는 셈이라 적립과 소비가 맞아떨어진다. 이 상태면 크레딧이 줄지도 늘지도 않는다.

### 예시: t3.medium에서 평소 10%, 하루 2시간 80% 사용

- 22시간 동안 적립만: 22 × 24 = 528 크레딧 적립 (baseline 이하라 소비 0)
- 2시간 동안 소비: 2 × (80% - 20%) × 60 × 2시간 = 144 크레딧 소비, 적립 24 × 2 = 48
- 하루 순 변화: 528 + 48 - 144 = +432

크레딧이 계속 쌓이는 패턴이다. 이런 워크로드는 T 시리즈에 잘 맞는다.

## T2 Standard vs T3 Unlimited: 기본 동작 차이

여기서 사고가 많이 난다.

**T2의 기본 모드는 Standard다.** 크레딧이 바닥나면 CPU가 baseline으로 강제 제한된다. t2.micro면 10%로 떨어진다. 웹서버가 갑자기 느려지고, SSH 접속도 버벅거린다.

**T3/T3a/T4g의 기본 모드는 Unlimited다.** 크레딧이 바닥나도 CPU 제한이 걸리지 않는다. 대신 초과분에 대해 과금이 된다. 이걸 모르고 T3를 쓰다가 요금 폭탄을 맞는 경우가 있다.

### 과금 사고 사례

개발서버로 t3.medium을 띄워놓고 부하 테스트를 24시간 돌렸다고 치자. CPU를 100% 풀로 쓰면:

- 시간당 초과 크레딧: 2 × (100% - 20%) × 60 - 24 = 72 크레딧/시간
- 24시간이면: 72 × 24 = 1,728 초과 크레딧
- vCPU 초과 크레딧 비용: Linux 기준 vCPU당 시간당 $0.05
- 초과 비용 계산: 초과 크레딧은 vCPU-minute 단위로 과금된다. 1,728 크레딧 = 1,728 vCPU-minutes. 시간당 비용으로 환산하면 **약 $1.44/일** 추가 과금

하루 $1.44면 대수롭지 않아 보이지만, 이걸 모르고 여러 대에서 몇 주간 돌리면 꽤 나온다. 특히 Auto Scaling 그룹에서 T3 인스턴스를 쓰면서 스케일링 이벤트마다 크레딧이 없는 새 인스턴스가 뜨면 초과 과금이 누적된다.

**Unlimited 끄는 방법:**

```bash
aws ec2 modify-instance-credit-specification \
  --instance-credit-specifications "InstanceId=i-1234567890abcdef0,CpuCredits=standard"
```

개발서버나 부하 테스트용 인스턴스는 Standard로 바꿔놓는 게 안전하다.

## Steal Time과 크레딧 소진 모니터링

### Steal Time이 뭔가

T 시리즈는 물리 호스트의 CPU를 다른 인스턴스와 나눠 쓴다. 내 인스턴스가 CPU를 쓰고 싶은데 하이퍼바이저가 다른 인스턴스에 CPU 시간을 할당하면, 그 대기 시간이 steal time이다.

`top` 명령에서 `%st`로 표시된다:

```
%Cpu(s):  5.3 us,  1.2 sy,  0.0 ni, 85.1 id,  0.0 wa,  0.0 hi,  0.2 si,  8.2 st
```

이 예시에서 `8.2 st`는 CPU 시간의 8.2%를 steal당하고 있다는 뜻이다.

T 시리즈에서 steal time이 높아지는 이유는 두 가지다:

1. **크레딧이 바닥나서** baseline으로 제한되는 중 (Standard 모드)
2. **물리 호스트가 과밀**해서 실제로 CPU를 못 받는 경우 (드물지만 있다)

### CloudWatch에서 크레딧 소진 확인하기

크레딧이 소진되면 CloudWatch에서 다음과 같이 보인다:

- `CPUCreditBalance`: 0에 수렴하거나 0 고정
- `CPUCreditUsage`: 적립량과 동일하게 고정 (쓰는 족족 소진)
- `CPUUtilization`: baseline 근처에서 더 이상 안 올라감 (Standard 모드)
- `CPUSurplusCreditBalance`: Unlimited 모드에서 초과 사용 중인 크레딧 수

Standard 모드에서 크레딧이 바닥나면 `CPUUtilization`이 baseline 값에 딱 붙어서 일직선을 그린다. 이게 보이면 인스턴스가 throttle 당하고 있는 거다.

## CloudWatch 알람 설정 (CLI)

크레딧 잔액이 낮아지면 알림을 받도록 설정한다.

```bash
# SNS 토픽 생성 (이미 있으면 스킵)
aws sns create-topic --name ec2-credit-alert

# 이메일 구독 추가
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-northeast-2:123456789012:ec2-credit-alert \
  --protocol email \
  --notification-endpoint ops@example.com

# CPUCreditBalance 알람 생성
aws cloudwatch put-metric-alarm \
  --alarm-name "t3-micro-credit-low" \
  --alarm-description "CPU credit balance below 50" \
  --metric-name CPUCreditBalance \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 50 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:ec2-credit-alert

# Surplus 크레딧 알람 (Unlimited 모드에서 초과 과금 감지)
aws cloudwatch put-metric-alarm \
  --alarm-name "t3-micro-surplus-credit" \
  --alarm-description "Surplus credits accumulating - unexpected charges" \
  --metric-name CPUSurplusCreditBalance \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 6 \
  --dimensions Name=InstanceId,Value=i-1234567890abcdef0 \
  --alarm-actions arn:aws:sns:ap-northeast-2:123456789012:ec2-credit-alert
```

`evaluation-periods 2`는 5분 간격으로 2번 연속 임계값 이하일 때 알람이 울린다는 뜻이다. 일시적인 스파이크에 알람이 울리지 않게 하려면 이 값을 조정한다.

## 인스턴스 Stop/Start 시 크레딧 동작

여기가 T2와 T3의 중요한 차이다.

### T2: Stop하면 크레딧 전부 날아간다

T2 인스턴스를 Stop 했다가 다시 Start하면 쌓아둔 크레딧이 0으로 초기화된다. 주말에 개발서버 끄고 월요일에 키면 크레딧이 없는 상태에서 시작한다. 월요일 아침 빌드가 느린 이유가 이거다.

### T3/T3a/T4g: Stop해도 크레딧이 유지된다

T3 이후 세대는 Stop/Start해도 크레딧 잔액이 보존된다. 7일 이내에 Start하면 크레딧이 그대로 있다. 다만 7일이 지나면 사라진다.

이 차이 때문에 비용 절감 목적으로 야간/주말에 인스턴스를 끄는 운영을 한다면 T3 이상을 써야 한다. T2에서 이 운영을 하면 인스턴스를 켤 때마다 크레딧 없이 시작해서 아침마다 성능이 떨어진다.

### Terminate하면?

T2든 T3든 Terminate하면 크레딧 전부 소멸한다. Auto Scaling에서 인스턴스가 교체되면 새 인스턴스는 크레딧 0에서 시작한다. (Launch Credit이 있었지만 아래에서 설명)

## Launch Credit 동작과 폐지 이력

### T2 Launch Credit

T2 인스턴스를 처음 시작하면 Launch Credit이 지급됐다. t2.micro 기준 30 크레딧이 한 번에 들어왔다. 새 인스턴스가 크레딧 없이 baseline만으로 시작하는 문제를 완화하기 위한 장치였다.

하지만 2017년 12월 이후 생성된 AWS 계정에서는 T2 Launch Credit이 폐지됐다. 기존 계정은 유지됐지만, 신규 계정은 Launch Credit 없이 시작한다.

### T3는 Launch Credit이 없다

T3 이후 세대는 Launch Credit 자체가 없다. 대신 기본 모드가 Unlimited이기 때문에 크레딧이 없어도 CPU 제한이 걸리지 않는다. 초과분은 과금되지만, 처음 24시간 동안 쌓이는 크레딧으로 대부분 상쇄된다.

Auto Scaling에서 T3를 쓸 때 이 동작을 이해해야 한다. 스케일아웃으로 새 인스턴스가 뜨면 크레딧 0에서 시작하고, Unlimited 모드로 초과 크레딧을 쓰면서 baseline 이상의 CPU를 제공한다. 스케일인으로 인스턴스가 빠르게 종료되면 초과 크레딧 비용만 남는다.

## Unlimited 모드 과금 계산

실제로 얼마나 나오는지 계산해보자.

### Unlimited 초과 과금 단가 (us-east-1 기준)

| 플랫폼 | vCPU-hour 당 |
|--------|-------------|
| Linux | $0.05 |
| Windows | $0.096 |

### 계산 예시: t3.micro에서 하루 8시간 CPU 50% 사용

t3.micro baseline 10%, vCPU 2개.

```
시간당 소비 크레딧: 2 × (50% - 10%) × 60 = 48
시간당 적립 크레딧: 12
시간당 순 소비: 36 크레딧

8시간 사용: 36 × 8 = 288 초과 크레딧
나머지 16시간 적립: 12 × 16 = 192 크레딧 적립

하루 순 초과: 288 - 192 = 96 크레딧
96 크레딧 = 96 vCPU-minutes = 1.6 vCPU-hours
추가 과금: 1.6 × $0.05 = $0.08/일

월 추가 과금: $0.08 × 30 = $2.40
```

t3.micro 월 기본 비용이 약 $7.5이니까 Unlimited 추가분이 약 32% 정도 된다. 이 정도면 아직 T 시리즈가 M 시리즈보다 싸다.

### 이게 M 시리즈 비용을 넘는 시점

t3.micro 월 $7.5 + Unlimited 추가분 vs m6i.large 월 약 $70. 단순 비교는 어렵지만, t3.small($15/월)에서 Unlimited 추가분이 월 $30 이상 나오기 시작하면 t3.medium이나 m6i.large를 고려할 시점이다.

## T4g ARM 마이그레이션 주의사항

T4g는 Graviton(ARM) 기반이라 x86 바이너리가 안 돌아간다. 가격 이점은 크지만 마이그레이션 전에 확인할 게 있다.

### Native Extension 호환성

Node.js에서 `node-gyp`으로 빌드하는 네이티브 모듈이 문제가 된다:

- **bcrypt**: ARM 빌드를 별도로 해야 한다. `bcryptjs`(순수 JS 구현)로 바꾸면 호환성 문제가 없다.
- **sharp** (이미지 처리): v0.29 이상에서 ARM 지원. 그 이전 버전은 빌드 실패한다.
- **node-sass**: ARM 미지원. `sass` (Dart Sass)로 교체해야 한다.
- **sqlite3**: ARM 프리빌트 바이너리가 없는 버전이 있다. 빌드 환경에 `build-essential` 필요.

Python 쪽도 비슷하다:

- **numpy**, **pandas**: 최신 버전은 ARM wheel을 제공하지만, 오래된 버전은 소스 컴파일이 필요하다. 빌드 시간이 수십 분 걸릴 수 있다.
- **cryptography**: Rust 컴파일러가 필요한데, ARM에서 빌드 시간이 길다.

### Docker 이미지

x86용으로 빌드한 Docker 이미지는 ARM에서 안 돌아간다. multi-platform 빌드를 해야 한다:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest .
```

base 이미지도 ARM을 지원하는지 확인해야 한다. `node:18-alpine`, `python:3.11-slim` 같은 공식 이미지는 대부분 ARM을 지원한다. 하지만 서드파티 이미지는 x86만 제공하는 경우가 있다.

### 마이그레이션 순서

1. 로컬에서 ARM 환경 테스트 (Apple Silicon Mac이면 네이티브, Intel이면 Docker `--platform linux/arm64`)
2. 의존성 패키지 전부 ARM 빌드 가능한지 확인
3. Docker 이미지 multi-platform 빌드
4. 스테이징에서 T4g 인스턴스로 테스트
5. 문제없으면 프로덕션 전환

## T 시리즈에서 M 시리즈로 갈아타는 시점

구체적인 판단 기준이다.

### CloudWatch 지표 기반 판단

다음 조건 중 하나라도 해당하면 M 시리즈 전환을 검토한다:

1. **CPUCreditBalance가 0인 시간이 하루 4시간 이상** — baseline으로는 워크로드를 감당 못하는 상태다
2. **CPUSurplusCreditBalance가 꾸준히 쌓인다** — Unlimited 모드에서 초과 과금이 계속 발생하는 중
3. **평균 CPUUtilization이 baseline의 2배 이상이 일주일 넘게 지속** — 버스트가 아니라 상시 부하다
4. **Unlimited 추가 비용이 인스턴스 기본 비용의 50%를 넘는 달이 2개월 연속** — M 시리즈가 더 싼 구간에 진입

### 비용 비교 기준

| 현재 인스턴스 | 전환 후보 | 전환 검토 시점 (월 총비용 기준) |
|-------------|----------|-------------------------------|
| t3.micro ($7.5) | t3.small ($15) | Unlimited 추가분 $5+/월 |
| t3.small ($15) | t3.medium ($30) | Unlimited 추가분 $10+/월 |
| t3.medium ($30) | t3.large ($60) 또는 m6i.large ($70) | Unlimited 추가분 $25+/월 |
| t3.large ($60) | m6i.large ($70) | Unlimited 추가분 $10+/월 |

t3.large에서 Unlimited 과금이 $10만 넘어도 m6i.large와 비용이 비슷해진다. 이때는 일관된 성능을 주는 M 시리즈가 낫다.

### 성능 관점

비용만이 아니다. T 시리즈에서 M 시리즈로 갈아타면:

- CPU throttling이 사라진다. 크레딧 신경 쓸 필요가 없다.
- 네트워크 baseline이 올라간다. T 시리즈는 네트워크 대역폭도 버스트 방식이다.
- EBS baseline throughput이 올라간다. I/O 집약적 워크로드에서 차이가 크다.

DB 서버처럼 지속적으로 CPU를 쓰는 워크로드는 처음부터 M 시리즈가 맞다. T 시리즈는 "대부분의 시간은 놀고, 가끔 바쁜" 워크로드에만 쓴다.

## 참조

- [EC2 Burstable Performance Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html)
- [CPU Credits and Baseline Utilization](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html)
- [T3 Instance Pricing](https://aws.amazon.com/ec2/pricing/on-demand/)
- [Graviton Getting Started](https://github.com/aws/aws-graviton-getting-started)
