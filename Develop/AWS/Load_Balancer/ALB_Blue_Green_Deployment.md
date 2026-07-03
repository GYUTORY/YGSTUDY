---
title: ALB 기반 Blue/Green 무중단 배포
tags: [aws, alb, bluegreen, codedeploy, ecs, canary, deployment, rollback]
updated: 2026-05-26
---

# ALB 기반 Blue/Green 무중단 배포

ALB로 무중단 배포를 한다는 건 결국 리스너가 어느 타겟그룹을 가리키느냐를 바꾸는 일이다. 새 버전을 띄운 타겟그룹을 미리 healthy 상태로 만들어 두고, 트래픽을 한 번에 또는 단계적으로 옮긴다. 옮기는 방식이 두 갈래다. 하나는 CodeDeploy가 두 타겟그룹 사이에서 리스너 default action을 통째로 스위칭하는 Blue/Green, 다른 하나는 한 리스너 규칙 안에서 두 타겟그룹에 가중치를 줘서 비율로 흘리는 Weighted Target Group 방식이다.

운영하면서 이 둘을 섞어 쓰게 되는데, 함정은 거의 다 "새 타겟그룹이 healthy가 됐다고 ALB가 판단하는 시점"과 "옛 타겟에 붙어있던 in-flight 요청을 언제 끊느냐"에 몰려 있다. 아래는 실제로 깨졌던 지점들 위주로 정리했다.

## 롤링 배포와 뭐가 다른가

롤링 배포는 같은 타겟그룹 안에서 인스턴스를 몇 대씩 빼고 새 버전을 넣는다. ECS rolling update가 대표적이다. 타겟그룹은 하나고, 배포 도중에는 구 버전과 신 버전이 같은 타겟그룹에 공존한다.

```
롤링:   TG-A [v1 v1 v1] → [v1 v1 v2] → [v1 v2 v2] → [v2 v2 v2]   (TG 하나, 점진 교체)
Blue/G: TG-Blue [v1 v1 v1]  +  TG-Green [v2 v2 v2]   (TG 둘, 리스너가 통째로 전환)
```

차이가 운영상 크게 갈리는 지점이 세 가지다.

첫째, 롤백 속도다. 롤링은 되돌리려면 다시 롤링을 돌려야 한다. 구 버전 이미지를 다시 배포하는 시간이 그대로 든다. Blue/Green은 리스너를 옛 타겟그룹으로 다시 가리키기만 하면 되니까 초 단위로 끝난다. 장애가 터졌을 때 이 차이가 결정적이다.

둘째, 리소스 비용이다. Blue/Green은 배포 순간 두 버전의 태스크가 동시에 떠 있다. ECS 기준으로 잠깐이지만 태스크 수가 두 배가 된다. Fargate면 그 시간만큼 vCPU/메모리 요금이 추가로 나간다. 롤링은 minimumHealthyPercent를 100 미만으로 잡으면 추가 용량 없이도 돌아간다. 상시 부하가 높고 마진이 빠듯한 클러스터에서 Blue/Green을 돌리면 배포 때마다 일시적으로 용량이 모자라 ECS가 태스크 배치를 못 하는 일이 생긴다.

셋째, 버전 혼재 여부다. 롤링은 배포 중간에 v1과 v2가 같은 시점에 요청을 받는다. DB 스키마를 바꾸는 배포라면 v1과 v2가 동시에 같은 테이블을 건드려도 깨지지 않게 마이그레이션을 backward-compatible하게 짜야 한다. Blue/Green도 전환 직전엔 두 버전이 떠 있긴 하지만, production 트래픽은 한쪽만 받으므로 혼재 시간이 짧다. 다만 카나리(Weighted)로 가면 다시 혼재가 길어진다는 걸 잊으면 안 된다.

## CodeDeploy ECS Blue/Green 구조

CodeDeploy로 ECS Blue/Green을 하면 ALB 쪽에 타겟그룹 두 개와 리스너 두 개를 미리 만들어 둬야 한다.

- **타겟그룹 2개**: 보통 `tg-blue`, `tg-green`. 둘 다 같은 ALB에 붙고, 배포 때마다 CodeDeploy가 어느 쪽이 production이고 어느 쪽이 대기인지 번갈아 정한다. "blue가 항상 구 버전"이 아니다. 직전 배포 결과에 따라 역할이 뒤집힌다.
- **production listener**: 실제 사용자 트래픽을 받는 리스너(보통 443).
- **test listener**: 배포된 새 버전을 사용자 트래픽 없이 검증하는 용도(보통 8443 같은 별도 포트). 선택이지만 lifecycle hook에서 새 버전을 때려보려면 사실상 필수다.

배포가 시작되면 흐름은 이렇다.

```
1. CodeDeploy가 새 태스크셋(green)을 띄운다
2. green을 대기 타겟그룹(tg-green)에 등록 → 헬스체크 통과 대기
3. test listener를 tg-green으로 연결 → BeforeAllowTraffic 훅 실행 (검증)
4. production listener의 default action을 tg-blue → tg-green으로 rerouting
5. AfterAllowTraffic 훅 실행
6. termination wait 시간만큼 tg-blue(구 버전) 유지 → 이후 구 태스크셋 종료
```

4번의 traffic rerouting이 핵심이다. CodeDeploy 배포 설정(deployment config)에서 `CodeDeployDefault.ECSAllAtOnce`를 쓰면 production listener가 한 번에 green으로 넘어간다. `ECSLinear`나 `ECSCanary`를 쓰면 단계적으로 넘어가는데, 이건 CodeDeploy가 내부적으로 리스너의 forward action 가중치를 조절해서 처리한다. 즉 Weighted Target Group을 CodeDeploy가 대신 굴려주는 셈이다.

6번의 **termination wait**(`terminationWaitTimeInMinutes`)이 실무에서 자주 짧게 잡혀 사고가 난다. 트래픽을 green으로 다 넘긴 뒤에도 구 버전 태스크를 바로 죽이지 않고 일정 시간 살려두는 구간이다. 이 시간 동안은 production listener를 다시 blue로 한 번에 되돌리는 즉시 롤백이 가능하다. 이걸 0~1분으로 잡아두면, 배포 직후 5분쯤 지나서야 드러나는 메모리 누수나 커넥션 풀 고갈 같은 문제를 발견했을 때 이미 구 태스크가 사라져서 빠른 롤백을 못 한다. 최소 5분, 검증이 까다로운 서비스면 15~30분을 권한다. 단 이 시간 내내 두 버전 태스크가 다 떠 있으니 비용은 그만큼 더 든다.

## AppSpec.yaml과 lifecycle hook

ECS Blue/Green의 AppSpec은 어떤 태스크 정의를 어느 컨테이너/포트로 띄울지와, 단계별로 어떤 Lambda를 훅으로 부를지를 적는다.

```yaml
# appspec.yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>   # CodeDeploy가 실제 ARN으로 치환
        LoadBalancerInfo:
          ContainerName: "app"
          ContainerPort: 8080
        PlatformVersion: "1.4.0"
Hooks:
  - BeforeInstall: "LambdaFunctionToValidateBeforeInstall"
  - AfterInstall: "LambdaFunctionToValidateAfterInstall"
  - AfterAllowTestTraffic: "LambdaToRunSmokeTestOnTestListener"
  - BeforeAllowTraffic: "LambdaToValidateBeforeProdTraffic"
  - AfterAllowTraffic: "LambdaToValidateAfterProdTraffic"
```

훅은 전부 Lambda이고, 각 Lambda는 마지막에 반드시 CodeDeploy에 결과를 보고해야 한다. 이걸 빼먹으면 배포가 그 단계에서 멈춘 채 한 시간 타임아웃을 다 기다린다.

```python
import boto3

cd = boto3.client('codedeploy')

def handler(event, context):
    deployment_id = event['DeploymentId']
    lifecycle_event_hook_execution_id = event['LifecycleEventHookExecutionId']

    status = 'Succeeded'
    try:
        # test listener(8443)로 새 버전 스모크 테스트
        run_smoke_test()
    except Exception:
        status = 'Failed'

    # 이 보고를 빼먹으면 배포가 멈춘 채 타임아웃까지 대기한다
    cd.put_lifecycle_event_hook_execution_status(
        deploymentId=deployment_id,
        lifecycleEventHookExecutionId=lifecycle_event_hook_execution_id,
        status=status,
    )
    return {'statusCode': 200}
```

훅별로 트래픽이 어디까지 흘러가 있는지를 정확히 알아야 검증을 제대로 짠다.

- **BeforeInstall / AfterInstall**: 아직 새 태스크가 production 트래픽을 받지 않는다. test listener도 아직 연결 전이다.
- **AfterAllowTestTraffic**: test listener가 green을 가리킨 직후. 사용자 트래픽은 없고 test 포트로만 접근 가능하다. 여기서 스모크 테스트를 돌린다.
- **BeforeAllowTraffic**: production 트래픽을 green으로 넘기기 직전. 마지막으로 막을 수 있는 지점이다. 여기서 Failed를 보고하면 production은 그대로 blue에 남고 배포가 중단된다.
- **AfterAllowTraffic**: production 트래픽이 green으로 넘어간 뒤. 실사용자 응답이 정상인지 본다. 여기서 Failed면 자동 롤백이 돈다.

BeforeAllowTraffic에서 검증을 하려면 test listener를 통해 green에 도달할 수 있어야 한다. 그래서 test listener가 없으면 BeforeAllowTraffic 훅이 사실상 할 수 있는 게 없다. 새 버전을 직접 호출할 경로가 없기 때문이다.

## 함정 1: test listener 포트 보안그룹 누락

이게 첫 Blue/Green 구성 때 거의 모두가 밟는다. production listener는 443이라 보안그룹에 이미 443 인바운드가 열려 있다. test listener를 8443으로 새로 만들면, ALB 보안그룹에 8443 인바운드를 추가로 열어야 하고, 동시에 ALB → 태스크로 가는 경로(태스크 보안그룹 또는 ECS 서비스 보안그룹)에서도 해당 트래픽이 통과돼야 한다.

증상이 헷갈리는 이유는, ALB 자체 헬스체크는 production 트래픽용 컨테이너 포트(예: 8080)로 가기 때문에 healthy로 멀쩡히 뜬다는 점이다. 타겟그룹은 정상인데 test listener로 스모크 테스트만 안 된다. AfterAllowTestTraffic 훅이 8443으로 green을 호출하다 timeout으로 Failed를 보고하고 배포가 굴러떨어진다. 헬스체크가 초록불이라 원인을 한참 엉뚱한 데서 찾는다.

```
production listener :443 ──┐
test listener       :8443 ─┤→ ALB 보안그룹: 443, 8443 둘 다 인바운드 허용 필요
                           └→ ALB → 태스크: 컨테이너 포트(8080)로 forward
```

test listener의 포트가 production 컨테이너 포트와 같아도(둘 다 8080으로 forward) ALB 리스너 포트 자체는 별개라는 걸 짚어둬야 한다. 리스너 포트(8443)와 타겟 포트(8080)를 헷갈려서 보안그룹을 엉뚱한 포트로 여는 경우가 있다. 열어야 하는 건 ALB 리스너 포트 쪽 인바운드다.

## 함정 2: 헬스체크 grace period 부족으로 인한 무한 재시작

ECS 서비스의 `healthCheckGracePeriodSeconds`가 짧으면 Blue/Green이 시작도 못 하고 배포가 계속 실패한다. 새 태스크가 부팅에 오래 걸리는 애플리케이션(JVM 워밍업, 큰 캐시 적재, 마이그레이션 체크 등)에서 자주 터진다.

흐름은 이렇다. green 태스크가 뜬다. 앱이 아직 부팅 중이라 ALB 헬스체크 경로가 503이나 connection refused를 돌려준다. grace period가 짧으면 ECS가 "이 태스크는 unhealthy"라고 판단하고 죽인다. 그리고 새 태스크를 다시 띄운다. 또 부팅 중에 죽인다. 이 루프가 반복되면서 배포는 영원히 끝나지 않고, CodeDeploy는 한 시간 뒤 타임아웃으로 실패한다.

```
green 태스크 기동 → 앱 부팅 50초 소요
ALB 헬스체크: 30초 후 첫 체크 → 503 (아직 부팅 중)
grace period 30초 → 부팅 끝나기 전에 ECS가 태스크 kill
→ 새 green 태스크 기동 → 또 부팅 중 kill → 무한 반복
```

grace period는 "이 시간 동안은 헬스체크가 실패해도 태스크를 죽이지 마라"는 유예다. 앱이 부팅에 50초 걸리면 grace period는 그보다 넉넉하게(예: 120초) 줘야 한다. 헬스체크 간격(interval), 임계 횟수(healthy/unhealthy threshold)와 함께 계산해야 한다.

```
실제 unhealthy 판정까지 = interval × unhealthy threshold
예: interval 15s × unhealthy 3회 = 45초
앱 부팅 50초 > 45초 → grace period 없으면 부팅 중 죽음
→ grace period를 120초 정도로 잡아 부팅 완료 후 첫 정상 응답까지 보호
```

여기에 더해, 헬스체크 경로(`/health`)가 DB나 외부 의존성까지 확인하는 deep check면 더 위험하다. 의존성이 느리거나 일시 장애면 부팅은 끝났는데도 헬스체크가 계속 실패해서 같은 무한 재시작에 빠진다. Blue/Green 배포용 헬스체크 경로는 "이 프로세스가 요청을 받을 준비가 됐나"만 보는 얕은 체크로 두고, 의존성 점검은 별도 경로로 분리하는 게 안전하다.

## Weighted Target Group 카나리

CodeDeploy 없이 ALB 리스너 규칙만으로 카나리를 굴릴 수도 있다. 한 forward action에 타겟그룹 두 개를 넣고 가중치를 준다. 트래픽 비율을 직접 조절하면서 천천히 넘긴다.

```bash
# 10%를 green으로
aws elbv2 modify-listener \
  --listener-arn <PROD_LISTENER_ARN> \
  --default-actions '[{
    "Type": "forward",
    "ForwardConfig": {
      "TargetGroups": [
        {"TargetGroupArn": "<TG_BLUE>", "Weight": 90},
        {"TargetGroupArn": "<TG_GREEN>", "Weight": 10}
      ],
      "TargetGroupStickinessConfig": {"Enabled": false}
    }
  }]'
```

가중치는 비율이 아니라 상대값이다. 90/10이면 합 100 중 10%가 green으로 간다. 50/50, 0/100 식으로 단계를 올린다. 각 단계 사이에 충분히 관찰 시간을 둬야 한다. 10%로 5분, 50%로 10분, 이상 없으면 100%, 이런 식으로 올리되 각 구간에서 에러율과 응답시간 메트릭을 본다.

### 카나리 중 stickiness 처리

여기가 카나리의 가장 미묘한 함정이다. `TargetGroupStickinessConfig`를 켜면, 한번 green으로 라우팅된 클라이언트는 쿠키가 만료될 때까지 계속 green으로 간다. 가중치를 10%로 잡아도, 시간이 지나면 한번 green을 맛본 사용자가 누적되면서 실제 green 트래픽 비율이 10%보다 커진다. 비율 기반 카나리를 정밀하게 하려면 이 stickiness를 꺼야 가중치대로 매 요청이 다시 추첨된다.

반대로, 세션을 타는 애플리케이션(로그인 세션을 로컬 메모리에 들고 있다든지)에서 stickiness를 끄면 같은 사용자의 연속 요청이 blue와 green을 왔다 갔다 한다. v1과 v2의 세션 처리가 호환되지 않으면 사용자가 갑자기 로그아웃되거나 장바구니가 비는 식으로 깨진다. 그러니 두 선택지가 충돌한다.

- **정밀 카나리 우선**: stickiness 끄기 → 세션이 외부(Redis 등)에 있어 v1/v2 어느 쪽이 받아도 무방한 상태여야 함
- **세션 안정 우선**: stickiness 켜기 → 카나리 비율이 시간에 따라 부정확해짐을 감수

세션을 로컬에 들고 있는 레거시 앱이라면 비율 카나리를 쓰지 말고 Blue/Green 한 방 전환(AllAtOnce)으로 가는 게 차라리 깔끔하다. 카나리는 세션을 외부 저장소로 빼둔 stateless 서비스에서 의미가 있다.

ALB의 `TargetGroupStickinessConfig`(타겟그룹 레벨 stickiness, duration 단위)와 타겟그룹 속성의 `stickiness.enabled`(개별 타겟 affinity)는 다른 설정이다. 카나리에서 말하는 건 forward action의 `TargetGroupStickinessConfig` 쪽이다. 둘을 헷갈리면 의도와 반대로 동작한다.

## CloudWatch 알람 기반 자동 롤백

CodeDeploy 배포 그룹에 CloudWatch 알람을 연결하면, 배포 중 알람이 ALARM 상태로 들어가는 순간 자동 롤백이 돈다. production listener가 다시 blue를 가리키고 배포가 실패 처리된다.

가장 많이 거는 두 메트릭이 `HTTPCode_Target_5XX_Count`와 `TargetResponseTime`다.

```bash
# 새 버전이 5xx를 쏟아내면 롤백시킬 알람
aws cloudwatch put-metric-alarm \
  --alarm-name "bg-green-5xx" \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=app/my-alb/abc \
               Name=TargetGroup,Value=targetgroup/tg-green/def \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching
```

알람을 걸 때 주의할 점 몇 가지가 있다.

**타겟그룹 차원을 green으로 잡아야 한다.** ALB 전체(`LoadBalancer` 차원만)로 5xx를 보면 blue가 받는 정상 트래픽의 노이즈까지 섞인다. 새 버전만 격리해서 보려면 `TargetGroup` 차원을 green 타겟그룹으로 좁혀야 카나리 중 green의 문제만 잡힌다.

**`HTTPCode_Target_5XX`와 `HTTPCode_ELB_5XX`는 다르다.** Target은 백엔드가 5xx를 응답한 것, ELB는 ALB가 자체적으로 만든 5xx(healthy 타겟 0개, 타겟 응답 파싱 실패 등)다. 새 버전 코드 버그를 잡으려면 Target_5XX를 본다. 다만 새 버전이 떠서 healthy가 되기 전 짧은 순간에 ELB_5XX가 튈 수 있으니, ELB_5XX로 롤백을 걸 거면 평가 기간을 신중히 잡아야 한다. (관련 5xx 구분은 [ALB 5xx 트러블슈팅](ALB_Troubleshooting.md) 참고)

**`treat-missing-data`를 잘못 잡으면 롤백이 안 돈다.** 트래픽이 적은 시간대에 카나리를 돌리면 1분 내 요청이 0건이라 메트릭 데이터포인트가 안 생긴다. 이때 missing data 처리를 `breaching`으로 잡으면 멀쩡한데도 알람이 울려 롤백이 도는 오작동이 난다. 반대로 5xx 알람은 보통 `notBreaching`으로 둬서 데이터 없음을 정상으로 본다.

**TargetResponseTime은 통계량 선택이 중요하다.** Average로 잡으면 일부 느린 요청이 평균에 묻혀 안 잡힌다. p95나 p99(`ExtendedStatistic`)로 봐야 꼬리 지연을 잡는다.

```bash
# 응답시간 p95가 1초 넘으면 롤백
aws cloudwatch put-metric-alarm \
  --alarm-name "bg-green-latency-p95" \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/my-alb/abc \
               Name=TargetGroup,Value=targetgroup/tg-green/def \
  --extended-statistic p95 \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching
```

자동 롤백이 돌면 CodeDeploy는 production listener를 즉시 blue로 되돌린다. 이때 위에서 말한 termination wait 시간이 살아있어야 blue 태스크가 아직 떠 있어 즉시 복구된다. 알람 기반 롤백을 켜놓고 termination wait를 0으로 두면, 롤백하려는 순간 돌아갈 blue가 이미 없어 복구가 한 박자 늦어진다. 둘은 세트로 봐야 한다.

## 함정 3: deregistration_delay와 in-flight 요청

트래픽을 green으로 넘긴 뒤 blue 타겟을 타겟그룹에서 빼는데(deregister), 이때 blue가 처리 중이던 요청을 중간에 끊으면 사용자에게 5xx나 연결 리셋이 보인다. 이걸 막는 게 타겟그룹의 `deregistration_delay.timeout_seconds`(connection draining)다.

deregister가 시작되면 타겟은 곧장 죽는 게 아니라 `draining` 상태로 들어간다. 이 상태에서는 새 연결은 안 받지만, 이미 받은 in-flight 요청은 draining 시간 동안 끝까지 처리하게 둔다. 기본값이 300초인데, 이게 길면 배포가 그만큼 늘어지고 짧으면 긴 요청이 잘린다.

```
기본 deregistration_delay: 300초
대부분의 API 응답: 1초 이내 → 300초는 과하게 길어 배포가 느려짐
파일 업로드/리포트 생성 등 장시간 요청: 300초도 모자랄 수 있음
```

여기서 자주 어긋나는 게 세 가지 시간의 관계다.

- **deregistration_delay**: ALB가 draining 타겟을 살려두는 시간
- **ECS task stopTimeout / SIGTERM 처리**: ECS가 태스크에 SIGTERM 보낸 뒤 SIGKILL까지의 유예
- **애플리케이션의 graceful shutdown**: SIGTERM 받고 진행 중 요청 마무리 후 종료

ALB는 draining 300초를 기다리는데 ECS의 stopTimeout이 30초면, ALB가 아직 연결을 살려두라고 보는 사이 컨테이너는 이미 SIGKILL로 죽어버린다. in-flight 요청이 거기서 끊긴다. 셋의 시간을 정렬해야 한다. graceful shutdown 시간 ≤ ECS stopTimeout, 그리고 deregistration_delay ≥ 처리 중 요청의 최대 소요 시간으로 맞춘다.

또 하나, 애플리케이션이 SIGTERM을 받아도 무시하고 계속 새 요청을 받으면 의미가 없다. SIGTERM을 받으면 헬스체크를 즉시 unhealthy로 떨어뜨리거나, 최소한 새 요청 수락을 멈추고 진행 중인 것만 마무리하는 코드가 들어 있어야 draining이 제대로 동작한다. 프레임워크 기본값이 SIGTERM에 즉시 죽도록 돼 있는 경우가 많아서 따로 확인해야 한다.

```python
# graceful shutdown 예시 (개념)
import signal, time

shutting_down = False

def on_sigterm(signum, frame):
    global shutting_down
    shutting_down = True   # 헬스체크는 이때부터 unhealthy 반환

signal.signal(signal.SIGTERM, on_sigterm)

def health_check():
    if shutting_down:
        return 503         # ALB가 draining 시작 → 새 요청 안 옴
    return 200
```

## 함정 4: WebSocket·롱폴링과 Blue/Green

지금까지가 일반 HTTP 요청 기준인데, WebSocket이나 SSE, 롱폴링은 연결이 길게 유지된다. green으로 전환하고 blue를 draining 걸어도, blue에 붙은 WebSocket 연결은 deregistration_delay가 끝나는 순간 끊긴다. 클라이언트 입장에서는 배포할 때마다 연결이 한 번씩 끊긴다.

이건 ALB 설정만으로는 해결이 안 된다. 클라이언트에 재연결 로직이 있어야 하고, 재연결 시 자연스럽게 green으로 붙도록 설계해야 한다. deregistration_delay를 길게 잡아 연결을 더 오래 유지할 수는 있지만, 그만큼 배포가 늘어지고 결국 언젠가는 끊긴다. 실시간 연결이 많은 서비스에서 Blue/Green을 쓸 거면 "배포 = 전체 재연결 1회"를 전제로 클라이언트를 만들어야 한다.

## 정리: 어느 방식을 언제 쓰나

- **CodeDeploy ECS Blue/Green (AllAtOnce)**: 빠른 전환, 빠른 롤백이 필요하고 버전 혼재를 최소화하고 싶을 때. 세션을 로컬에 들고 있는 앱도 한 방 전환이라 비교적 안전하다. 단 전환 순간 모든 트래픽이 새 버전으로 가니 검증을 test listener 단계에서 충분히 해야 한다.
- **Weighted 카나리 (Linear/Canary)**: 새 버전 위험도가 높아 실사용자 일부로 먼저 검증하고 싶을 때. stateless하고 세션이 외부에 있어야 한다. CloudWatch 알람 자동 롤백과 묶으면 사람이 안 보고 있어도 문제 시 되돌아간다.
- **롤링**: 추가 용량 여유가 없고, 빠른 롤백보다 비용 절감이 중요하며, 버전 혼재를 견딜 수 있는 backward-compatible한 배포일 때.

세 방식 다 공통으로 깨지는 지점은 헬스체크 타이밍, in-flight 요청 처리, 세션 일관성이다. 배포 방식을 고르기 전에 이 세 가지가 자기 서비스에서 어떻게 동작하는지부터 확인하는 게 순서다.
