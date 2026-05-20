---
title: AWS Application Load Balancer (ALB)
tags: [aws, alb, loadbalancer, networking, http, microservices]
updated: 2026-05-20
---

# AWS Application Load Balancer (ALB)

ALB는 L7 로드밸런서다. HTTP/HTTPS 요청을 보고 경로, 호스트 헤더, 메서드, 쿼리스트링까지 따져서 라우팅한다. 같은 ELB 계열인 NLB(L4)와 가장 큰 차이가 여기다. NLB는 TCP 패킷 그대로 흘려보내지만 ALB는 헤더를 뜯어본다.

운영하면서 가장 자주 마주치는 게 라우팅 규칙 우선순위, 헬스체크 오작동, TLS 종료 후 백엔드 인증, 그리고 롤링 배포 중 스티키 세션 깨짐이다. 아래는 그동안 실제로 겪은 함정들과 처리 방법이다.

## 구성 요소

ALB는 크게 세 덩어리다.

- **Listener**: 포트와 프로토콜을 묶어 요청을 받는 진입점. 80/443이 가장 흔하다.
- **Listener Rule**: 조건(경로, 헤더 등)과 액션(forward, redirect, fixed-response, authenticate-*)을 매칭. 우선순위 숫자가 낮을수록 먼저 평가된다.
- **Target Group**: 실제 트래픽이 닿는 백엔드 집합. EC2, ECS Task, IP, Lambda 중 하나의 타입을 가진다.

여기서 자주 놓치는 점이 Listener Rule의 우선순위 운영이다.

## Listener Rule 우선순위

우선순위는 1부터 50000까지 정수다. 같은 리스너 안에서 중복 불가다. 처음에는 10, 20, 30처럼 띄워두는 게 정석이다. 5씩 띄우면 중간에 끼워넣을 자리가 부족해서 나중에 전체 재배치를 하게 된다.

```bash
# 우선순위 한꺼번에 재정렬 (이게 가능하다는 걸 모르고 하나씩 지웠다 다시 만드는 사람이 많다)
aws elbv2 set-rule-priorities \
  --rule-priorities \
    RuleArn=arn:aws:...:rule/abc,Priority=100 \
    RuleArn=arn:aws:...:rule/def,Priority=200
```

운영하다 보면 카나리 규칙(특정 헤더가 있으면 v2 타겟그룹) 같은 걸 임시로 끼워넣는데, 이때 priority를 1~9 사이 같은 좁은 구간으로 잡아두면 나중에 정리하기 편하다. 영구 규칙은 100, 200, 300 단위, 임시 규칙은 1~99 단위 같은 식의 약속이 있어야 한다.

기본 동작(default action)은 priority가 없다. 어떤 규칙에도 매칭되지 않으면 default로 떨어진다. 그래서 default를 503 fixed-response로 잡아두고, 정상 트래픽은 명시적 규칙으로만 받게 하는 패턴이 한 번 사고를 막아준다. 잘못 배포해서 규칙이 사라져도 503이 떨어질 뿐 엉뚱한 타겟으로 가지 않는다.

## Target Group 헬스체크 함정

가장 흔한 사고가 헬스체크다. 기본값이 위험하다.

```
HealthCheckIntervalSeconds: 30
HealthCheckTimeoutSeconds: 5
HealthyThresholdCount: 5
UnhealthyThresholdCount: 2
```

`HealthyThresholdCount: 5`이고 `Interval: 30s`면 새 인스턴스가 등록되고 트래픽을 받기까지 최소 150초가 걸린다. 오토스케일링으로 인스턴스가 추가되는 상황에서 이건 너무 길다. 스케일아웃이 트래픽 폭증을 따라잡지 못한다. 보통 `Interval: 10s`, `HealthyThreshold: 2`로 줄여서 20초 안에 등록되게 한다.

반대로 `UnhealthyThresholdCount: 2`는 너무 공격적일 수 있다. 백엔드가 일시적으로 GC pause 같은 걸로 한두 번 5초 타임아웃이 나면 바로 대상에서 빠진다. DB 커넥션 풀이 잠깐 마르거나, 외부 API 의존성이 흔들리는 순간 줄줄이 빠진다. 보통 `UnhealthyThreshold: 3` 정도로 늘리고, 타임아웃은 백엔드의 p99보다 충분히 크게 잡는다.

### Deep check와 shallow check 분리

가장 큰 함정은 헬스체크 엔드포인트에 DB나 외부 의존성 점검까지 다 넣는 경우다.

```python
# 안티패턴
@app.get("/health")
def health():
    db.execute("SELECT 1")  # DB 죽으면 ALB가 전 인스턴스를 빼버린다
    redis.ping()
    requests.get("https://payment-api/health")
    return "ok"
```

DB가 잠깐 한쪽 AZ에서 흔들리면 전체 타겟 그룹의 모든 인스턴스가 동시에 UNHEALTHY가 된다. ALB는 갈 곳이 없어서 503을 뱉기 시작한다. 정작 인스턴스 자체는 멀쩡한데 트래픽을 못 받는다.

운영 환경에서는 두 갈래로 나눠야 한다.

- `/health/live`: 프로세스가 살아있는지만 본다. ALB 헬스체크가 여기를 본다. 거의 항상 200을 반환한다.
- `/health/ready`: DB, Redis 등 의존성을 본다. 쿠버네티스 readinessProbe나 별도 모니터링이 여기를 본다.

ALB 헬스체크에는 절대 deep check를 걸지 마라. 한 번 데여보면 안다.

### `success_codes` 매처

기본값은 200이지만, 백엔드가 인증 미통과 시 401을 주거나 헬스체크 자체가 204를 주는 경우가 있다. 그때는 매처를 명시한다.

```hcl
health_check {
  path     = "/health/live"
  matcher  = "200-299"  # 또는 "200,204"
  interval = 10
  timeout  = 3
  healthy_threshold   = 2
  unhealthy_threshold = 3
}
```

## Sticky Session 한계

ALB의 sticky session은 두 가지가 있다.

- **Duration-based**: ALB가 `AWSALB`/`AWSALBCORS` 쿠키를 만들어 클라이언트에 내려준다.
- **Application-based**: 백엔드 앱이 직접 발급한 쿠키를 ALB가 참조한다.

문제는 롤링 배포다. 스티키로 묶여있던 타겟이 종료되면 다음 요청은 다른 타겟으로 가는데, 그 순간 세션이 끊긴다. 로그인 상태가 풀리거나, 멀티스텝 폼에서 입력값이 날아간다.

```
사용자 A → 인스턴스 1 (스티키 묶임)
[배포로 인스턴스 1 종료]
사용자 A → 인스턴스 2 (세션 없음 → 로그인 풀림)
```

근본 해결은 세션을 Redis 같은 외부 저장소로 빼는 거다. 스티키는 캐시 hit율 같은 부수적 이득을 노릴 때만 쓰고, 정합성에 의존하지 마라. 굳이 써야 한다면 배포 전에 deregistration delay(connection draining)를 충분히 길게 잡는다.

```hcl
resource "aws_lb_target_group" "api" {
  # ...
  deregistration_delay = 60  # 기본 300초, 트래픽 패턴에 맞게 조정

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }
}
```

deregistration_delay 동안 ALB는 새 요청은 안 보내지만 in-flight 요청은 끝까지 처리하도록 둔다. WebSocket 같은 long-lived 연결이 있으면 이 값을 더 늘려야 하고, 반대로 짧은 REST 요청만 있으면 30초로도 충분하다.

## TLS Termination과 X-Forwarded-Proto 위조 방지

ALB에서 HTTPS를 종료하면 백엔드까지는 보통 HTTP다. 그러면 백엔드 입장에서는 들어온 요청이 원래 HTTPS였는지 HTTP였는지 모른다. `X-Forwarded-Proto` 헤더로 알려준다.

```
GET /api/users HTTP/1.1
Host: example.com
X-Forwarded-Proto: https
X-Forwarded-For: 203.0.113.10
X-Forwarded-Port: 443
```

여기서 위험한 패턴이 있다. 백엔드 앱이 `X-Forwarded-Proto: https`만 보고 "이 요청은 HTTPS다"라고 판단하는 경우다. 만약 ALB를 우회해서 누군가 백엔드에 직접 요청을 보내면서 `X-Forwarded-Proto: https`를 위조해 넣으면, 백엔드는 속는다. 보안 쿠키 정책이나 HSTS 판정이 깨진다.

```python
# 위험: 헤더를 그대로 신뢰
if request.headers.get("X-Forwarded-Proto") == "https":
    # secure cookie 처리
```

방어는 두 가지로 한다.

1. 백엔드 인스턴스의 보안 그룹은 **ALB의 보안 그룹에서만** 인바운드를 받는다. 0.0.0.0/0이나 VPC 전체를 열어두면 안 된다.
2. ALB가 도착한 요청에 대해 자체적으로 `X-Forwarded-*` 헤더를 덮어쓰도록 한다. 클라이언트가 보낸 같은 이름의 헤더는 ALB가 자동으로 무시한다(append 안 함, overwrite 함). 그래도 백엔드에 직접 가는 경로가 없는지 보안 그룹으로 한 번 더 막는다.

`X-Forwarded-For`는 다르다. ALB가 append 한다. 그래서 클라이언트가 보낸 값이 앞쪽에 남는다. 실제 클라이언트 IP는 보통 마지막에서 두 번째다(맨 끝이 ALB가 본 직전 hop). 여기를 잘못 파싱하면 IP 기반 rate limit이 망가진다.

## HTTP/2와 gRPC 타겟 그룹

ALB는 클라이언트와는 HTTP/2를 자동으로 처리하지만, 백엔드와의 통신 프로토콜은 별도로 설정한다. gRPC를 쓰려면 Target Group의 `ProtocolVersion`을 `GRPC`로 명시한다.

```hcl
resource "aws_lb_target_group" "grpc_api" {
  name             = "grpc-tg"
  port             = 50051
  protocol         = "HTTP"
  protocol_version = "GRPC"  # 기본은 HTTP1
  vpc_id           = aws_vpc.main.id

  health_check {
    path                = "/grpc.health.v1.Health/Check"
    matcher             = "0"  # gRPC status code 0 = OK
    protocol            = "HTTP"
    port                = "traffic-port"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}
```

gRPC 헬스체크는 HTTP status code가 아니라 gRPC status code(0~16)로 판정한다. `matcher = "0"`이 OK다. 처음 설정할 때 `200`으로 넣으면 절대 healthy가 안 된다. 한참 헤맨다.

HTTP/2 백엔드(gRPC 아닌)도 `protocol_version = "HTTP2"`로 설정 가능하다. 다만 ALB 자체가 백엔드에 보내는 keep-alive 동작이 HTTP/1.1과 다르니, 백엔드의 `MaxConcurrentStreams`나 idle timeout을 확인해야 한다.

## mTLS (Mutual TLS)

2023년 후반부터 ALB가 mTLS를 직접 지원한다. 이전에는 NLB로 받아서 nginx로 클라이언트 인증서를 검증하는 패턴이 일반적이었는데, 이제 ALB에서 끝낸다.

두 모드가 있다.

- **Passthrough**: ALB가 클라이언트 인증서를 검증하지 않고, 인증서 정보를 HTTP 헤더(`X-Amzn-Mtls-Clientcert`)에 담아 백엔드로 넘긴다. 검증은 백엔드가 한다.
- **Verify**: ALB가 Trust Store에 등록된 CA로 검증한다. 통과한 인증서만 백엔드로 넘어간다.

```bash
# Trust Store 생성 (CA 번들을 S3에 올려둬야 한다)
aws elbv2 create-trust-store \
  --name partner-cas \
  --ca-certificates-bundle-s3-bucket my-bucket \
  --ca-certificates-bundle-s3-key partner-ca-bundle.pem

# Listener에 mTLS 적용
aws elbv2 modify-listener \
  --listener-arn $LISTENER_ARN \
  --mutual-authentication Mode=verify,TrustStoreArn=$TRUST_STORE_ARN,IgnoreClientCertificateExpiry=false
```

운영 시 함정은 인증서 만료다. `IgnoreClientCertificateExpiry=false`로 두면 클라이언트 인증서가 만료된 순간 즉시 거부되는데, 파트너사가 인증서를 갱신 안 한 채로 새벽에 만료되면 그대로 전체 통신이 끊긴다. 만료 30일 전 알림 자동화는 필수다.

## SNI 다중 인증서

하나의 HTTPS 리스너에 여러 인증서를 붙일 수 있다. SNI를 보고 도메인별로 다른 인증서를 내려준다.

```bash
# 기본 인증서는 create-listener 시점에 설정
# 추가 인증서는 별도 명령
aws elbv2 add-listener-certificates \
  --listener-arn $LISTENER_ARN \
  --certificates \
    CertificateArn=arn:aws:acm:...:certificate/cert-for-api \
    CertificateArn=arn:aws:acm:...:certificate/cert-for-admin
```

```hcl
resource "aws_lb_listener_certificate" "extra" {
  listener_arn    = aws_lb_listener.https.arn
  certificate_arn = aws_acm_certificate.admin.arn
}
```

기본 인증서(default certificate)는 SNI가 없거나 매칭 안 되는 클라이언트에게 내려준다. 이게 잘못 잡혀 있으면 일부 오래된 클라이언트가 SSL 오류를 받는다. 와일드카드 인증서나 가장 범용적인 도메인 인증서를 default로 두는 게 안전하다.

ACM 인증서가 갱신될 때 ARN이 그대로 유지되니까 ALB 설정을 다시 건드릴 필요는 없다. 다만 외부에서 발급한 인증서를 IAM에 임포트해서 쓰는 경우는 갱신할 때마다 새 ARN이라 ALB 인증서 매핑을 다시 잡아야 한다.

## ALB Access Log와 Athena 쿼리

액세스 로그는 S3에 gzip된 텍스트로 떨어진다. CloudWatch Logs로는 안 간다. 분석은 보통 Athena를 쓴다.

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS alb_logs (
    type string,
    time string,
    elb string,
    client_ip string,
    client_port int,
    target_ip string,
    target_port int,
    request_processing_time double,
    target_processing_time double,
    response_processing_time double,
    elb_status_code int,
    target_status_code string,
    received_bytes bigint,
    sent_bytes bigint,
    request_verb string,
    request_url string,
    request_proto string,
    user_agent string,
    ssl_cipher string,
    ssl_protocol string,
    target_group_arn string,
    trace_id string,
    domain_name string,
    chosen_cert_arn string,
    matched_rule_priority string,
    request_creation_time string,
    actions_executed string,
    redirect_url string,
    lambda_error_reason string,
    target_port_list string,
    target_status_code_list string,
    classification string,
    classification_reason string
)
PARTITIONED BY (day string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
    'serialization.format' = '1',
    'input.regex' = '([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[^ ]*) ([-0-9]*) ([-0-9]*) \"([^ ]*) (.*) (- |[^ ]*)\" \"([^\"]*)\" ([A-Z0-9-_]+) ([A-Za-z0-9.-]*) ([^ ]*) \"([^\"]*)\" \"([^\"]*)\" \"([^\"]*)\" ([-.0-9]*) ([^ ]*) \"([^\"]*)\" \"([^\"]*)\" \"([^ ]*)\" \"([^\\s]+?)\" \"([^\\s]+)\" \"([^ ]*)\" \"([^ ]*)\"'
)
LOCATION 's3://my-alb-logs-bucket/AWSLogs/123456789012/elasticloadbalancing/ap-northeast-2/'
TBLPROPERTIES ('projection.enabled' = 'true',
  'projection.day.type' = 'date',
  'projection.day.range' = '2024/01/01,NOW',
  'projection.day.format' = 'yyyy/MM/dd',
  'projection.day.interval' = '1',
  'projection.day.interval.unit' = 'DAYS',
  'storage.location.template' = 's3://my-alb-logs-bucket/AWSLogs/123456789012/elasticloadbalancing/ap-northeast-2/${day}');
```

테이블을 만들었으면 자주 쓰는 쿼리들이다.

```sql
-- 5xx 폭증 구간 찾기
SELECT
    date_trunc('minute', from_iso8601_timestamp(time)) AS minute,
    elb_status_code,
    count(*) AS cnt
FROM alb_logs
WHERE day = '2026/05/19'
  AND elb_status_code >= 500
GROUP BY 1, 2
ORDER BY 1 DESC, cnt DESC;

-- target_processing_time이 긴 상위 요청 (느린 백엔드 추적)
SELECT
    request_url,
    target_ip,
    target_processing_time,
    elb_status_code,
    time
FROM alb_logs
WHERE day = '2026/05/19'
  AND target_processing_time > 3.0
ORDER BY target_processing_time DESC
LIMIT 100;

-- 특정 클라이언트 IP의 요청 패턴 (abuse 추적)
SELECT
    request_verb,
    request_url,
    count(*) AS cnt
FROM alb_logs
WHERE day = '2026/05/19'
  AND client_ip = '203.0.113.99'
GROUP BY 1, 2
ORDER BY cnt DESC;

-- matched_rule_priority별 트래픽 분포 (어떤 규칙이 가장 많이 쓰이나)
SELECT
    matched_rule_priority,
    count(*) AS cnt
FROM alb_logs
WHERE day = '2026/05/19'
GROUP BY 1
ORDER BY cnt DESC;

-- ALB는 정상이지만 target_status_code가 5xx인 케이스 (백엔드 문제)
SELECT
    target_ip,
    target_status_code,
    count(*) AS cnt
FROM alb_logs
WHERE day = '2026/05/19'
  AND elb_status_code = 200
  AND target_status_code LIKE '5%'
GROUP BY 1, 2
ORDER BY cnt DESC;
```

`elb_status_code`와 `target_status_code`를 구분해서 봐야 한다. ALB가 백엔드까지 못 갔으면 `target_status_code`가 `-`다. 이때 `elb_status_code`만 보면 5xx만 보이는데 원인은 ALB-백엔드 연결 자체에 있다. 보안 그룹이나 헬스체크 문제일 가능성이 크다.

파티션 프로젝션(`projection.enabled = true`)을 쓰면 `MSCK REPAIR TABLE`을 안 돌려도 된다. 로그가 매일 새 파티션을 만드는데, 옛날 방식으로는 매일 새벽에 REPAIR를 돌려야 했다.

## ALB 자체에서 봐야 할 CloudWatch 지표

- `HTTPCode_ELB_5XX_Count`: ALB가 백엔드 접속을 못 했거나 직접 5xx를 뱉은 횟수. 헬스체크 실패, 보안 그룹 오류, 백엔드 부재 같은 시그널이다.
- `HTTPCode_Target_5XX_Count`: 백엔드 앱이 5xx를 반환한 횟수. 애플리케이션 문제.
- `TargetResponseTime`: 백엔드의 응답 시간. p99로 봐야 의미가 있다. Average는 거의 쓸모없다.
- `RejectedConnectionCount`: ALB의 연결 제한에 걸려서 거부된 연결 수. 동시 연결이 ALB 인스턴스 capacity를 넘어선다는 신호다.
- `TargetConnectionErrorCount`: ALB가 백엔드에 연결을 못 한 횟수. 백엔드 OOM이나 포트 listen 실패 같은 상황.

`UnHealthyHostCount`가 0보다 크면 알람을 걸어야 하는데, 그 전에 `HealthyHostCount`도 같이 본다. 전체 5대 중 1대가 빠진 거랑 5대 중 4대가 빠진 거랑 의미가 다르다. 비율 알람을 같이 두는 게 안전하다.

## ALB CLI 예제

```bash
TG_ARN=$(aws elbv2 create-target-group \
  --name "myapp-tg" \
  --protocol HTTP --port 8080 \
  --vpc-id vpc-xxxxxxxx \
  --target-type instance \
  --health-check-path "/health/live" \
  --health-check-interval-seconds 10 \
  --health-check-timeout-seconds 3 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

aws elbv2 register-targets \
  --target-group-arn $TG_ARN \
  --targets Id=i-1234567890abcdef0,Port=8080

aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{ID:Target.Id,Health:TargetHealth.State,Reason:TargetHealth.Reason}'

ALB_ARN=$(aws elbv2 create-load-balancer \
  --name "myapp-alb" \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-xxxxxxxx \
  --scheme internet-facing \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS --port 443 \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --certificates CertificateArn=arn:aws:acm:...:certificate/xxx \
  --default-actions Type=fixed-response,FixedResponseConfig='{StatusCode=503,ContentType=text/plain,MessageBody=Service Unavailable}' \
  --query 'Listeners[0].ListenerArn' --output text)

aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions \
    Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 100 \
  --conditions '[{"Field":"path-pattern","Values":["/api/orders/*"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"'$ORDER_TG_ARN'"}]'

aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 200 \
  --conditions '[{"Field":"host-header","Values":["admin.example.com"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"'$ADMIN_TG_ARN'"}]'
```

default action을 503 fixed-response로 두는 패턴에 주목한다. 명시적 규칙이 모두 사라져도 트래픽이 엉뚱한 곳으로 가지 않는다.

## Terraform 예제

```hcl
resource "aws_lb" "main" {
  name               = "myapp-alb"
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]

  drop_invalid_header_fields = true
  enable_http2               = true
  idle_timeout               = 60

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    prefix  = "myapp-alb"
    enabled = true
  }
}

resource "aws_lb_target_group" "api" {
  name             = "myapp-api-tg"
  port             = 8080
  protocol         = "HTTP"
  protocol_version = "HTTP1"
  vpc_id           = aws_vpc.main.id

  deregistration_delay = 60

  health_check {
    path                = "/health/live"
    interval            = 10
    timeout             = 3
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }
}

resource "aws_lb_target_group" "grpc" {
  name             = "myapp-grpc-tg"
  port             = 50051
  protocol         = "HTTP"
  protocol_version = "GRPC"
  vpc_id           = aws_vpc.main.id

  health_check {
    path                = "/grpc.health.v1.Health/Check"
    matcher             = "0"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Service Unavailable"
      status_code  = "503"
    }
  }
}

resource "aws_lb_listener_certificate" "admin" {
  listener_arn    = aws_lb_listener.https.arn
  certificate_arn = aws_acm_certificate.admin.arn
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener_rule" "orders" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  condition {
    path_pattern {
      values = ["/api/orders/*"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener_rule" "canary" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 50

  condition {
    http_header {
      http_header_name = "X-Canary"
      values           = ["true"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api_v2.arn
  }
}
```

`drop_invalid_header_fields = true`는 RFC 7230에 어긋나는 헤더(컨트롤 문자 포함 등)를 ALB가 자동으로 떨어뜨리게 한다. 백엔드까지 이상한 헤더가 가서 파서가 깨지는 일을 막는다. 기본값이 false라서 명시적으로 켜야 한다.

## 비용 관련

ALB 요금은 시간당 고정 비용 + LCU(Load Balancer Capacity Unit) 기반이다. LCU는 새 연결 수, 활성 연결 수, 처리 바이트, 규칙 평가 횟수 중 가장 큰 값으로 청구된다. 

특히 규칙 평가 횟수가 무섭다. 리스너 규칙이 많아질수록 한 요청당 평가되는 조건 수가 늘어난다. 무료 한도가 요청당 10개 조건이고, 그 이후는 LCU에 잡힌다. 규칙을 50개씩 늘어놓는 경우는 priority를 조정해서 트래픽 많은 규칙을 앞쪽에 두는 게 LCU 비용에 영향을 준다.

## 참고 링크

- [ALB 공식 문서](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [ALB Access Log 포맷](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html)
- [ALB mTLS 가이드](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html)
- [ALB 가격 안내](https://aws.amazon.com/elasticloadbalancing/pricing/)
