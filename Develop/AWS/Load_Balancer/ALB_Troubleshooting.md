---
title: ALB 5xx 트러블슈팅
tags: [aws, alb, troubleshooting, http5xx, accesslog, athena, xray]
updated: 2026-05-20
---

# ALB 5xx 트러블슈팅

ALB에서 5xx가 떴을 때 제일 먼저 봐야 할 건 `elb_status_code`와 `target_status_code`가 다른지 같은지다. 둘이 다르면 ALB가 자체적으로 응답을 만들어 낸 거고, 같으면 백엔드가 5xx를 줬는데 ALB가 그대로 전달한 거다. 이 차이를 먼저 가르지 않고 메트릭만 보면 원인을 한참 헤맨다.

운영하면서 가장 자주 만나는 케이스가 502, 503, 504다. 셋 다 "백엔드 문제"라고 뭉뜽그리는데, 실제로는 발생 위치도 다르고 처방도 다르다. 여기서는 재현 가능한 시나리오와 함께 액세스 로그 어디를 봐야 하는지 정리했다.

## elb_status_code vs target_status_code

ALB 액세스 로그에는 두 개의 상태 코드가 찍힌다.

- `elb_status_code`: ALB가 클라이언트에게 최종 응답한 코드
- `target_status_code`: 타겟이 ALB에게 응답한 코드. 타겟에 요청이 도달조차 못 했으면 `-`로 찍힌다

```
elb_status_code=502  target_status_code=-     → ALB가 타겟 응답을 파싱 못 했거나 연결 자체가 안 됨
elb_status_code=502  target_status_code=502   → 백엔드 앱이 502를 반환. ALB는 그대로 전달
elb_status_code=503  target_status_code=-     → healthy 타겟이 0개거나 매칭 규칙 없음
elb_status_code=504  target_status_code=-     → 타겟이 idle timeout 안에 응답을 못 줌
elb_status_code=500  target_status_code=500   → 백엔드 앱의 unhandled exception
```

`target_status_code=-`인 5xx는 거의 항상 ALB 단에서 결론을 낸 것이고, 둘 다 숫자가 찍히면 백엔드 코드를 봐야 한다. 메트릭에서도 `HTTPCode_ELB_5XX_Count`와 `HTTPCode_Target_5XX_Count`가 따로 있다. CloudWatch 알람을 걸 때 둘을 합쳐서 걸면 원인 추적이 어려워진다. 분리해서 걸어야 한다.

## 502: ALB가 타겟 응답을 못 받았다

502는 ALB가 타겟에게 요청은 보냈는데 정상적인 HTTP 응답을 못 받았을 때 뜬다. `target_status_code=-`로 찍힌다. 원인은 세 가지가 가장 흔하다.

### keepalive timeout 불일치

이게 운영 환경에서 압도적으로 많다. ALB의 `idle_timeout`은 기본 60초고, 그 안에 ALB는 타겟과의 TCP 연결을 재사용한다. 그런데 타겟 쪽 keepalive timeout이 ALB보다 짧으면, 타겟이 먼저 FIN을 보내고 연결을 닫는다. ALB는 그 사실을 모른 채 이미 닫힌 연결로 다음 요청을 흘려보낸다. 그러면 RST가 돌아오고 ALB는 502를 만들어낸다.

```
ALB idle_timeout: 60s
Nginx keepalive_timeout: 5s ← 문제
Node.js server.keepAliveTimeout: 5000 ← 문제
```

Node.js는 기본 keepAliveTimeout이 5초다. ALB 뒤에 Node를 그냥 띄우면 매일 502가 산발적으로 뜬다. 트래픽이 적은 시간대일수록 더 자주 발생한다. 연결을 한참 안 쓰다가 다시 쓸 때 이미 끊긴 상태인 확률이 높아져서다.

처방은 백엔드의 keepalive를 ALB보다 길게 잡는다. 보통 75초 정도가 안전 마진이다.

```javascript
// Node.js Express
const server = app.listen(3000);
server.keepAliveTimeout = 75000;  // ALB idle_timeout(60s)보다 길게
server.headersTimeout = 76000;    // keepAliveTimeout보다 길게 (안 그러면 ECONNRESET)
```

```nginx
# Nginx
keepalive_timeout 75s;
```

재현 시나리오는 간단하다. ALB idle_timeout을 60초로 두고, 타겟의 keepalive를 5초로 설정한 뒤 1분에 한 번씩 요청을 보내면 502가 산발적으로 뜬다. 액세스 로그에서 `target_processing_time=-1`이면 100% 이 케이스다.

### 타겟 응답 헤더 손상

타겟이 ALB가 파싱할 수 없는 응답을 주는 경우다. 예를 들어 응답 헤더에 한글 같은 non-ASCII가 들어가거나, `Content-Length`가 실제 바디 길이와 다르거나, chunked encoding을 잘못 만들면 ALB는 응답을 폐기하고 502로 처리한다.

```python
# 헤더에 한글 들어가서 502
response.headers["X-User-Name"] = "김철수"  # 인코딩 안 하면 ALB가 거부

# Content-Length 불일치
response.headers["Content-Length"] = "100"
response.body = "x" * 200  # 실제로는 200바이트
```

이건 액세스 로그만 봐서는 안 보인다. ALB Access Log의 `target_status_code`는 `-`로 찍히고 메시지도 없다. 의심되면 타겟에서 직접 curl로 응답을 받아보고, 그 응답을 nc나 httpie로 raw로 확인해야 한다. 한 번 데이고 나면 응답 헤더에 사용자 입력을 그대로 넣지 않게 된다.

### 컨테이너 OOM

ECS나 EKS 위에서 돌리면 컨테이너가 OOM으로 죽었을 때도 502가 뜬다. 타겟이 응답 중에 죽으면 ALB는 TCP 연결이 끊긴 상태에서 502를 만든다. 이 경우 액세스 로그의 `target_processing_time`은 작은 값으로 찍히다가 어느 순간부터 `-1`로 바뀐다.

CloudWatch에서 봐야 할 메트릭은 두 개다.

- `TargetResponseTime` 평균이 갑자기 떨어진다 (응답 자체가 안 오니까)
- `HTTPCode_ELB_502_Count`가 burst로 튄다

여기에 컨테이너의 메모리 메트릭을 겹쳐 보면 명확하다. ECS 태스크 정의의 메모리 한계가 워크로드 실제 사용량보다 작으면 GC pressure로 죽는다. JVM 같이 자체 힙 관리하는 런타임에서는 `Xmx`를 컨테이너 메모리 한계보다 작게 잡지 않으면 cgroup이 죽인다. 보통 컨테이너 메모리의 75% 정도를 `Xmx`로 잡는다.

## 503: ALB가 보낼 곳이 없다

503은 ALB가 요청을 받았지만 어디로도 못 보낼 때 뜬다. `target_status_code=-`로 찍힌다. 두 가지 케이스가 거의 전부다.

### Target Group의 healthy 타겟이 0

가장 흔하다. 새 배포가 헬스체크를 통과하지 못해서 healthy가 0이 되거나, 기존 타겟이 deep health check 의존성 때문에 줄줄이 빠지는 경우다.

```
HealthyHostCount: 0
UnHealthyHostCount: 3
```

이런 상태일 때 ALB는 모든 요청에 503을 준다. `target_processing_time=-1`, `target_status_code=-`, `actions_executed=forward`로 찍힌다.

이게 신규 환경 배포에서 가장 자주 일어난다. 헬스체크가 통과 못 하는 흔한 원인을 정리하면 다음 네 가지다.

**보안 그룹 체인 문제**: ALB SG에서 타겟 SG로의 인바운드가 막혀있다. 헬스체크는 ALB SG에서 오는 트래픽이지 ALB의 ENI IP에서 오는 게 아니다. SG 참조 방식(sg-xxxxx로 참조)으로 열어두는 게 안전하다. CIDR로 열면 ALB가 새 IP로 scale 될 때 막힌다.

**헬스체크 경로 응답 코드 매칭**: `success_codes` 기본값이 `200`인데 백엔드가 `/health`에서 204를 주거나, 인증 미들웨어가 먼저 동작해서 401을 주는 경우가 있다. 매처를 `200-299` 같이 범위로 잡거나 명시적으로 `200,204`로 잡아야 한다.

```hcl
health_check {
  path    = "/health/live"
  matcher = "200-299"
  port    = "traffic-port"   # 명시 안 하면 타겟 포트와 다른 포트로 갈 수 있다
}
```

**컨테이너 startup 시간 vs 헬스체크 grace period**: ECS Service의 `healthCheckGracePeriodSeconds` 기본값은 0이다. JVM처럼 부팅이 30초씩 걸리는 앱은 부팅 중에 헬스체크 실패로 ECS가 태스크를 죽이고, 새로 띄우고, 또 죽이는 무한 루프에 빠진다. 부팅 시간 + 충분한 마진으로 잡아야 한다. JVM 기반 서비스는 보통 120초 이상 둔다.

```json
{
  "healthCheckGracePeriodSeconds": 120
}
```

**경로 자체가 틀림**: 라우터에서 `/health`로 설정했는데 앱은 `/api/health`에서 응답하는 경우. 또는 컨테이너 안에서는 응답하는데 sidecar(istio-proxy 등)가 막는 경우. 의심되면 `curl http://<container-ip>:<port>/health/live`를 컨테이너 내부에서 직접 쳐본다.

### Listener Rule 매칭 실패 + default 미설정

요청 경로가 어떤 Listener Rule에도 매칭되지 않으면 default action으로 떨어진다. default action이 forward인데 그 타겟 그룹이 비어있거나, default가 아예 설정 안 된 상태에서 ALB가 503을 만든다.

이걸 운영 사고에서 한 번 겪고 나면 default action을 `fixed-response 503`으로 명시하게 된다. 잘못된 도메인으로 ALB에 요청이 오거나, 라우팅 규칙이 의도치 않게 사라져도 정해진 응답이 떨어진다. 진단도 쉽다.

```hcl
resource "aws_lb_listener" "https" {
  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "application/json"
      status_code  = "503"
      message_body = "{\"error\":\"no route\"}"
    }
  }
}
```

액세스 로그에서 `actions_executed=fixed-response`, `target_status_code=-`로 찍힌다. forward되는 503과 구분이 된다. 이게 의외로 큰 차이다.

## 504: 타겟이 제때 응답을 못 줬다

504는 ALB가 타겟에게 요청을 보냈고 연결도 살아있는데, `idle_timeout` 안에 응답이 안 와서 ALB가 끊은 경우다. `target_status_code=-`, `target_processing_time`에는 idle_timeout 값에 가까운 숫자가 찍힌다.

### slow query가 가장 흔함

원인의 9할은 백엔드의 slow query다. 인덱스 안 탄 쿼리, N+1 쿼리, 외부 API 호출이 직렬로 묶인 경우. 평소엔 500ms에 끝나던 요청이 데이터가 쌓이면서 70초가 걸린다. ALB idle_timeout(기본 60초)에 걸려서 504.

```
elb_status_code: 504
target_status_code: -
target_processing_time: 60.001
request_processing_time: 0.000
response_processing_time: -1
```

`target_processing_time`이 idle_timeout 근처면 거의 확정이다. 백엔드 슬로우 쿼리 로그나 APM(X-Ray, Datadog APM 등)에서 어떤 쿼리가 길어졌는지를 본다.

처방은 둘 중 하나다.

1. 쿼리 자체를 고친다 (인덱스 추가, 페이지네이션, 비동기 처리로 분리)
2. ALB idle_timeout을 늘린다. 단, 백엔드도 같이 늘려야 한다

idle_timeout을 무조건 늘리는 건 답이 아니다. 사용자는 60초 넘게 기다리지 못한다. 길어진 요청은 비동기로 빼서 202 + 폴링 또는 WebSocket으로 결과를 받게 한다.

### ALB idle_timeout과 백엔드 timeout의 관계

idle_timeout은 ALB가 클라이언트, 그리고 타겟 양쪽 모두에 적용된다. 클라이언트가 idle_timeout 동안 아무것도 안 보내거나 타겟이 그동안 응답을 안 주면 끊는다.

긴 응답이 필요한 엔드포인트(파일 다운로드, 리포트 생성 등)는 별도 ALB나 별도 Listener Rule로 분리해서 idle_timeout을 길게 잡는 게 낫다. ALB 전체의 idle_timeout을 늘리면 좀비 연결이 쌓인다.

## Access Log 필드 해석

ALB 액세스 로그의 시간 관련 필드 세 개를 정확히 구분해야 한다.

```
request_processing_time  response_processing_time  target_processing_time
       ↑                          ↑                         ↑
   ALB가 요청 받고            타겟 응답 받고             타겟에게 보내고
   타겟에게 보낼 때까지       클라이언트에 보낼 때까지   응답이 올 때까지
```

- `request_processing_time`: 요청이 ALB에 들어와서 타겟으로 출발하기까지. 보통 거의 0. 길어지면 ALB 내부 처리 지연(드물게 발생, AWS 측 문제일 가능성).
- `target_processing_time`: 타겟이 처리하는 데 걸린 시간. 백엔드 성능을 보는 핵심 지표.
- `response_processing_time`: 타겟 응답을 클라이언트에게 흘려보내는 데 걸린 시간. 응답이 클라이언트로 느리게 빨려나가는 경우(클라이언트가 느린 네트워크) 길어진다.

여기서 자주 헷갈리는 게 응답 시간 측정이다. `TargetResponseTime` 메트릭은 `target_processing_time`만 본다. 클라이언트가 응답을 받는 데 걸리는 체감 시간은 `request_processing_time + target_processing_time + response_processing_time`이다. 모바일 클라이언트가 느린 네트워크에서 응답을 받으면 `target_processing_time`은 짧은데 체감은 느리다. APM 지표와 ALB 지표가 안 맞는다는 얘기가 나오면 보통 여기서 시작된다.

### request_creation_time과 time_to_first_byte 분리

`request_creation_time`은 ALB가 요청을 받은 시각이고, 로그가 기록되는 시각(`time`)은 응답을 끝낸 시각이다. 둘의 차이로 전체 처리 시간을 본다.

`time_to_first_byte`(TTFB)는 액세스 로그 자체에는 직접 필드로 없다. CloudFront를 앞단에 두면 CloudFront 로그에 찍히지만 ALB 로그에서는 `target_processing_time`이 사실상 TTFB에 가깝다. 정확한 TTFB는 클라이언트에서 측정해야 한다(브라우저 Performance API의 `responseStart - requestStart`).

지연이 어디서 발생했는지 구분하려면 다음과 같이 나눠 본다.

- `request_processing_time` 큼 → ALB 자체 지연 또는 클라이언트가 요청 본문을 느리게 보냄
- `target_processing_time` 큼 → 백엔드 처리 느림 (slow query, GC, 외부 API)
- `response_processing_time` 큼 → 응답이 크고 클라이언트 다운로드가 느림

## Athena로 액세스 로그 분석

ALB 액세스 로그는 S3에 떨어진다. Athena에서 테이블을 만들어두면 SQL로 조회할 수 있다.

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
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
  'serialization.format' = '1',
  'input.regex' = '([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) \"([^ ]*) (.*) (- |[^ ]*)\" \"([^\"]*)\" ([A-Z0-9-_]+) ([A-Za-z0-9.-]*) ([^ ]*) \"([^\"]*)\" \"([^\"]*)\" \"([^\"]*)\" ([-.0-9]*) ([^ ]*) \"([^\"]*)\" \"([^\"]*)\" \"([^ ]*)\" \"([^\\s]+?)\" \"([^\\s]+)\" \"([^ ]*)\" \"([^ ]*)\"'
)
LOCATION 's3://my-alb-logs/AWSLogs/123456789012/elasticloadbalancing/ap-northeast-2/';
```

평소 자주 쓰는 쿼리 몇 개.

```sql
-- 최근 1시간 5xx 분포 (ALB가 만든 5xx와 백엔드가 만든 5xx 분리)
SELECT
  elb_status_code,
  target_status_code,
  COUNT(*) AS cnt,
  AVG(target_processing_time) AS avg_target_time
FROM alb_logs
WHERE from_iso8601_timestamp(time) > current_timestamp - interval '1' hour
  AND elb_status_code >= 500
GROUP BY elb_status_code, target_status_code
ORDER BY cnt DESC;

-- 504 발생한 요청의 URL별 빈도
SELECT
  request_url,
  COUNT(*) AS cnt,
  AVG(target_processing_time) AS avg_time
FROM alb_logs
WHERE elb_status_code = 504
  AND from_iso8601_timestamp(time) > current_timestamp - interval '1' day
GROUP BY request_url
ORDER BY cnt DESC
LIMIT 20;

-- 특정 trace_id로 X-Ray와 매칭
SELECT *
FROM alb_logs
WHERE trace_id = 'Root=1-5f9d3c8a-1234567890abcdef';

-- keepalive 502 의심 (target_processing_time이 -1로 찍힘)
SELECT
  target_ip,
  COUNT(*) AS cnt
FROM alb_logs
WHERE elb_status_code = 502
  AND target_processing_time = -1
  AND from_iso8601_timestamp(time) > current_timestamp - interval '1' day
GROUP BY target_ip
ORDER BY cnt DESC;
```

타겟 IP별로 502를 집계하면 특정 인스턴스에서만 발생하는지 아니면 전체에서 발생하는지 알 수 있다. 한쪽 인스턴스에만 몰리면 그 인스턴스를 retire 시키고 다시 본다.

## X-Ray 연동

ALB는 요청에 `X-Amzn-Trace-Id` 헤더를 자동으로 붙여준다. 액세스 로그의 `trace_id` 필드와 같은 값이다. 백엔드 앱이 X-Ray SDK를 쓰고 있다면 이 ID로 ALB → 백엔드 → DB까지 전체 흐름을 본다.

```
액세스 로그: trace_id = "Root=1-5f9d3c8a-1234567890abcdef"
                          ↓
X-Ray 콘솔에서 이 ID로 검색
                          ↓
세그먼트: ALB (요청 받음) → 백엔드 서비스 → DB query → 응답
```

X-Ray가 가장 빛나는 순간이 504 추적이다. 어디서 시간을 다 썼는지 segment timeline으로 한눈에 본다. DB 쿼리에서 50초를 썼는지, 외부 API 호출에서 늘어졌는지, GC pause로 응답 자체가 묶였는지가 보인다.

다만 X-Ray는 샘플링을 한다. 기본 1초당 1건 + 5%다. 5xx 추적용으로는 부족하다. 5xx는 100% 샘플링되도록 규칙을 따로 만든다.

```json
{
  "rule_name": "5xx-full-sampling",
  "priority": 1,
  "fixed_target": 0,
  "rate": 1.0,
  "service_name": "*",
  "service_type": "*",
  "host": "*",
  "http_method": "*",
  "url_path": "*",
  "attributes": {}
}
```

응답 코드 기반 샘플링 규칙은 X-Ray 자체에는 없다. 대신 5xx가 발생하면 SDK 레벨에서 강제로 트레이스를 기록하도록 코드에서 처리한다.

## 신규 환경 배포 시 헬스체크 점검 순서

새 환경(staging, 신규 클러스터)을 띄우는데 헬스체크가 안 통과하면 다음 순서로 본다. 순서가 중요하다. 위에서부터 한 단계씩 좁혀가야 시간이 안 든다.

**1단계: 컨테이너 내부에서 직접 응답을 받는다.**

```bash
# ECS 컨테이너에 들어가서
curl -i http://localhost:<port>/health/live
```

여기서 응답이 안 오면 앱 자체 문제다. 컨테이너 안에서도 안 되는데 ALB 탓을 하면 안 된다.

**2단계: 같은 VPC의 다른 인스턴스에서 타겟 IP로 직접 친다.**

```bash
# bastion이나 다른 EC2에서
curl -i http://<container-private-ip>:<port>/health/live
```

여기서 응답이 안 오면 SG 문제다. 타겟 SG의 인바운드가 닫혀있다.

**3단계: ALB의 SG에서 타겟 SG로 인바운드가 열려있는지 확인한다.**

타겟 SG 인바운드에 ALB SG ID가 source로 등록되어 있어야 한다. CIDR로 등록되어 있으면 ALB가 새 IP로 옮겨질 때 막힌다.

**4단계: 헬스체크 경로와 매처를 본다.**

`/health`인지 `/api/health`인지, 응답 코드가 200인지 204인지. 매처를 `200-299`로 잡으면 웬만한 케이스는 다 통과한다.

**5단계: 헬스체크 grace period가 컨테이너 부팅 시간보다 긴지 본다.**

JVM 기반 앱이 부팅에 60초 걸리는데 grace period가 30초면 무한히 재시작된다. ECS 콘솔에서 태스크가 계속 stopped → started를 반복하면 이 케이스다. 부팅 로그에서 "Server started" 같은 메시지까지 걸리는 시간을 재서 그 두 배 정도로 잡는다.

**6단계: 그래도 안 되면 ALB의 헬스체크 IP가 타겟에 도달하는지 패킷 캡처.**

여기까지 오면 흔치 않다. 보통은 1~3단계에서 다 잡힌다. tcpdump로 ALB SG 대역에서 들어오는 요청을 보면 ALB가 정말 요청을 보내고 있는지 확인이 된다.

```bash
sudo tcpdump -i eth0 -nn 'tcp port <health-check-port>'
```

ALB가 요청을 보내고 있고 타겟이 200을 응답하고 있는데도 unhealthy로 찍힌다면 응답 코드 매처를 다시 본다. 거의 매처 문제다.

## 정리하면

5xx가 떴을 때 액세스 로그에서 봐야 할 첫 두 필드는 `elb_status_code`와 `target_status_code`다. `target_status_code=-`이면 ALB 단에서 결론났다는 뜻이고, 그때 `target_processing_time`이 음수(-1)면 연결 자체가 안 됐거나 깨졌다는 뜻이다. 양수면 타겟이 처리 중에 timeout 같은 사유로 끊겼다는 뜻이다.

CloudWatch 메트릭만 봐서는 502, 503, 504 원인을 못 가른다. 액세스 로그를 S3에 떨어뜨려두고 Athena 테이블을 미리 만들어두면 사고 났을 때 5분 안에 원인 영역을 좁힐 수 있다. 사고가 나기 전에 만들어두는 게 낫다.
