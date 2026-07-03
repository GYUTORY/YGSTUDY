---
title: AWS 로드 밸런서 — ALB / NLB / CLB 선택과 운영
tags: [aws, loadbalancer, lb, alb, nlb, clb, elb]
updated: 2026-05-20
---

# AWS 로드 밸런서 — ALB / NLB / CLB 선택과 운영

AWS 콘솔에서 로드 밸런서를 만들 때 처음 마주치는 선택지가 ALB, NLB, GWLB, CLB다. 문서만 보면 "HTTP는 ALB, TCP는 NLB"로 끝나지만, 실제로 운영하다 보면 같은 HTTP 워크로드라도 NLB로 빠지는 경우가 있고 NLB를 골랐다가 클라이언트 IP가 깨져서 ALB로 되돌리는 경우도 있다. 여기서는 5년 정도 굴려보면서 어떤 트래픽 패턴에 어느 로드 밸런서를 골랐고, 어디서 데였는지를 정리한다.

## ELB 패밀리 — 같은 가족이지만 성격이 다르다

AWS가 부르는 공식 명칭은 ELB(Elastic Load Balancing)다. 그 아래에 ALB, NLB, GWLB, CLB가 들어간다. 그런데 현장에서 "ELB"라고 하면 보통 CLB(Classic Load Balancer)를 가리킨다. CLB가 처음 ELB라는 이름으로 출시됐고, ALB·NLB가 나오면서 Classic이라는 접두어가 붙었기 때문이다. AWS Support 티켓에서 "ELB"라고 쓰면 "어떤 ELB를 말씀하시는지" 되묻는다.

| 약어 | 정식 명칭 | 동작 계층 | 주력 프로토콜 |
|---|---|---|---|
| CLB | Classic Load Balancer | L4/L7 혼합 | HTTP, HTTPS, TCP |
| ALB | Application Load Balancer | L7 | HTTP, HTTPS, gRPC, WebSocket |
| NLB | Network Load Balancer | L4 | TCP, UDP, TLS |
| GWLB | Gateway Load Balancer | L3 | IP (방화벽·IDS 어플라이언스 체이닝 전용) |

GWLB는 보안 어플라이언스를 투명하게 끼워 넣는 용도라 일반 서비스 트래픽에는 쓰지 않는다. 이 문서에서는 다루지 않는다.

## 트래픽 패턴별 실제 선택

### HTTP API 서버 + 경로 라우팅 → ALB

마이크로서비스 N개를 하나의 도메인 뒤에 묶을 때는 ALB 외에 답이 없다. `/api/users/*`는 User 서비스, `/api/orders/*`는 Order 서비스로 보내는 규칙을 리스너 룰로 박을 수 있다. 룰 우선순위가 낮은 숫자부터 평가되니까, 더 구체적인 패턴을 위에 두는 걸 잊지 말아야 한다. 더 일반적인 룰을 위에 두면 그 아래 룰은 영원히 매칭되지 않는다.

ECS Fargate나 EKS를 쓴다면 ALB가 디폴트다. 컨테이너 포트가 동적으로 바뀌어도 타겟 그룹이 알아서 추적한다. EKS에서는 AWS Load Balancer Controller가 Ingress 리소스를 ALB로 만들어주기 때문에 별도로 콘솔에서 만지는 일이 거의 없다.

### gRPC 백엔드 → ALB

gRPC는 HTTP/2 위에서 도는데, ALB는 2020년부터 gRPC 타겟 그룹 프로토콜을 정식 지원한다. NLB로도 gRPC를 흘릴 수는 있지만, 그 경우 클라이언트가 TLS 종료를 직접 다뤄야 하고 헬스체크가 TCP 레벨에 머물러서 서비스가 살았는지 죽었는지 정확히 모른다. gRPC는 ALB로 가는 게 맞다.

### 게임 서버, MQTT 브로커, 실시간 미디어 → NLB

UDP를 쓰는 워크로드는 NLB만 가능하다. ALB는 UDP를 안 받는다. 게임 매치메이커, WebRTC TURN 서버, 영상 스트리밍 같은 게 여기 해당된다.

TCP라도 커넥션 단위가 길거나(예: 24시간 유지되는 MQTT), 초당 신규 커넥션이 폭증하는 경우(고빈도 트레이딩 API) NLB가 유리하다. ALB는 HTTP 요청 단위로 토큰 버킷 계산이 들어가서 신규 커넥션 폭증에 약하다. NLB는 패킷 수준에서 처리하니까 신규 커넥션 수십만 RPS도 자동 확장 없이 받아낸다.

### 고정 IP가 필요한 경우 → NLB

ALB는 DNS 이름만 주고 IP는 시간이 지나면 바뀐다. 클라이언트가 IP를 화이트리스트에 박는 B2B 환경, 또는 사내 방화벽이 IP 기반인 환경에서는 ALB를 못 쓴다. NLB는 가용영역별로 Elastic IP를 붙일 수 있어서 IP가 고정된다.

이걸 우회하기 위해 ALB 앞에 NLB를 두는 패턴도 있다(NLB → ALB 체이닝). 2021년부터 NLB가 ALB를 타겟으로 받을 수 있게 되면서 가능해졌다. 클라이언트는 NLB의 고정 IP를 보고, 내부적으로는 ALB의 L7 라우팅 기능을 그대로 쓴다. 단점은 비용이 두 배로 든다는 것과, X-Forwarded-For 헤더 처리가 한 단계 더 들어간다는 것.

### 인증서를 클라이언트에 종단까지 보존해야 하는 경우 → NLB (TLS 패스스루)

PCI-DSS, 의료 데이터, 또는 mTLS 같이 ALB에서 TLS를 종료할 수 없는 워크로드는 NLB의 TCP 리스너로 받아서 백엔드까지 암호화된 채로 흘려보낸다. ALB는 무조건 TLS를 종료한다. 인증서가 ALB에 등록되고, 거기서 평문으로 풀린 다음 백엔드로 다시 HTTPS를 맺든 HTTP로 보내든 한다. mTLS 클라이언트 인증서를 백엔드에서 검증해야 한다면 ALB로는 안 된다.

### 레거시 EC2-Classic → CLB

EC2-Classic은 2022년 8월에 모든 신규 계정에서 사라졌고, 기존 계정도 마이그레이션이 강제됐다. 그래도 아직 CLB를 쓰는 환경이 남아 있다면 그건 마이그레이션을 미룬 결과지 새로 만들 일은 없다. AWS도 CLB에 새 기능을 안 넣은 지 한참 됐다.

## NLB 클라이언트 IP 보존 — SNAT에서 깨지는 사례

NLB의 "클라이언트 IP 보존"은 자주 오해되는 기능이다. NLB는 기본적으로 클라이언트 IP를 백엔드에 그대로 전달한다. 백엔드 인스턴스에서 `tcpdump`를 떠 보면 외부 클라이언트 IP가 source로 찍힌다. ALB나 CLB와 다른 점이다 — ALB는 자기 자신의 IP를 source로 박고 원본은 `X-Forwarded-For` 헤더에 넣는다.

문제는 이 동작이 "타겟 등록 방식"에 따라 달라진다는 점이다.

### Instance 타겟 vs IP 타겟

NLB 타겟 그룹은 `target_type`을 instance 또는 ip로 만들 수 있다. EC2 인스턴스 ID로 등록하면 instance 타입, ENI IP로 등록하면 ip 타입이다.

- instance 타입: 클라이언트 IP 보존됨. 백엔드에서 진짜 클라이언트 IP가 보인다.
- ip 타입: NLB가 자기 IP를 source로 박는다(SNAT). 클라이언트 IP는 사라진다.

ECS Fargate는 EC2 인스턴스가 없으므로 무조건 ip 타입이다. 그래서 Fargate 뒤에 NLB를 두면 클라이언트 IP가 NLB IP로 바뀌어서 도착한다. 이걸 모르고 Fargate 컨테이너 안에서 `request.remoteAddr`로 클라이언트 IP를 로깅하면 죄다 NLB IP만 찍힌다.

### Proxy Protocol v2로 우회

이 경우 해법은 Proxy Protocol v2를 켜는 것이다. NLB 타겟 그룹 속성에서 `proxy_protocol_v2`를 true로 설정하면, 매 TCP 연결의 첫 패킷에 원본 클라이언트 IP·포트 정보가 박힌 헤더가 붙어서 백엔드로 간다. 백엔드 애플리케이션이 이 헤더를 파싱해야 한다 — nginx면 `proxy_protocol` 디렉티브, HAProxy면 `accept-proxy`, Node.js·Spring은 라이브러리를 따로 붙여야 한다.

Proxy Protocol을 켜는 것을 잊고 백엔드에서 일반 TCP로 받으면, 첫 패킷의 PROXY 헤더가 정상 페이로드로 해석돼서 파싱 에러가 난다. 반대로 백엔드는 PROXY를 기대하는데 NLB에서 안 켜져 있으면 연결이 늘어진다. 양쪽을 동시에 켜야 한다.

### Cross-Zone과 묶이는 함정

NLB는 기본적으로 Cross-Zone Load Balancing이 꺼져 있다. ALB는 기본 켜짐, NLB는 기본 꺼짐 — 이 차이를 자주 까먹는다. Cross-Zone이 꺼진 NLB에서 가용영역 A에는 인스턴스가 1개, B에는 4개가 있다면, A로 들어온 트래픽은 그 1개에 다 몰리고 B로 들어온 건 4개에 균등 분산된다. 클라이언트가 어느 AZ DNS로 붙느냐에 따라 부하가 완전히 비대칭해진다.

Cross-Zone을 켜면 균등해지지만, AZ 간 데이터 전송 비용이 추가로 붙는다(GB당 약 $0.01). 트래픽이 큰 서비스에서는 켜고 끄고가 비용에 직결되니까 그래프 그려보고 결정한다.

## CLB → ALB 마이그레이션 — 동작 차이

CLB에서 ALB로 옮길 때 단순히 새 LB를 만들고 Route 53 레코드만 바꿔주면 될 것 같지만, 실제로는 몇 가지가 다르게 동작해서 마이그레이션 직후 장애가 난다.

### 헬스체크가 더 엄격해진다

CLB의 HTTP 헬스체크는 기본값이 2xx, 3xx까지 healthy로 본다. ALB는 200만 healthy로 본다(기본값). 백엔드가 302 리다이렉트를 헬스체크 경로에서 뱉고 있었다면 CLB에서는 통과하던 게 ALB에서는 전부 unhealthy로 떨어진다. `matcher = "200-399"` 같이 명시적으로 늘려주거나, 백엔드의 헬스체크 핸들러를 200만 뱉도록 고쳐야 한다.

또한 CLB는 인스턴스 단위로 헬스체크하지만 ALB는 타겟 그룹의 포트 단위로 한다. 같은 인스턴스에서 두 포트를 동시에 띄우고 있다면 한쪽이 죽어도 다른 쪽은 그대로 받는다.

### 스티키 세션 쿠키 이름이 다르다

CLB가 발급하는 세션 쿠키 이름은 `AWSELB`다. ALB는 `AWSALB`(또는 `AWSALBAPP`로 시작하는 추가 쿠키). 마이그레이션 직후에 사용자 브라우저에 `AWSELB`만 남아 있어서 세션이 끊긴 것처럼 보이는 일이 자주 있다. JSESSIONID 같은 애플리케이션 쿠키를 따로 쓰고 있었다면 큰 문제는 아니지만, LB 쿠키에만 의존했다면 한 번씩 로그인이 풀린다.

추가로 ALB는 "application-based cookie"라는 모드를 지원한다 — 애플리케이션이 자기 쿠키를 발급하면 ALB가 그걸 보고 스티키를 유지한다. CLB에는 없던 기능이라 마이그레이션 전에 알 필요는 없지만, 이참에 적용하면 LB 종속을 줄일 수 있다.

### Connection Draining → Deregistration Delay

CLB에서는 "Connection Draining"이라고 부르고 ALB·NLB에서는 "Deregistration Delay"라고 부른다. 같은 기능인데 이름만 다르다. 기본값도 둘 다 300초로 동일하다. 단, ALB는 HTTP 요청 단위로 정리하고 NLB는 TCP 연결 단위로 정리해서 동작 시점이 다르다. 긴 polling이나 WebSocket을 쓰는 백엔드라면 ALB 쪽에서도 끊김이 발생한다.

### Idle Timeout

CLB의 idle timeout 기본값은 60초. ALB도 60초. NLB는 350초로 훨씬 길고, 변경할 수 없다(2024년부터 일부 변경 가능). WebSocket 연결이 50초마다 ping을 안 보내고 있다면 ALB나 CLB에서 끊긴다. 마이그레이션 자체와는 무관하지만 NLB→ALB로 옮길 때 갑자기 끊김이 보이기 시작하면 idle timeout부터 의심한다.

## LCU 비용 — 차원별로 누적되는 함정

ALB와 NLB는 시간당 고정 요금과 별도로 LCU(Load Balancer Capacity Unit) 기반 사용량 요금이 붙는다. LCU는 4개 차원 중 가장 큰 값으로 정해진다 — 그래서 한 차원만 튀어도 비용이 같이 튄다.

### ALB의 4가지 LCU 차원

| 차원 | 단위당 LCU 1 |
|---|---|
| 신규 연결 | 초당 25개 |
| 활성 연결 | 분당 3,000개 |
| 처리 바이트 | EC2 타겟 1GB/h, Lambda 0.4GB/h |
| 룰 평가 | 초당 1,000회 (앞 10개 룰은 무료) |

룰 평가가 의외로 자주 함정이다. 리스너 룰을 50개쯤 박아놓고 매 요청마다 평가시키면 RPS가 그렇게 높지 않아도 룰 평가 차원이 최대값이 돼서 비용이 튀어 오른다. 호스트 기반 + 경로 기반 + 헤더 기반 룰을 마구 섞어놓은 ALB는 청구서를 보고 놀라는 일이 잦다.

처리 바이트 차원은 응답이 큰 API나 이미지 서버에서 1등을 한다. CloudFront를 앞에 두는 식으로 빼낼 수 있다.

활성 연결 차원은 WebSocket이 켜지면 폭발한다. 사용자 만 명이 WebSocket을 유지하면 활성 연결이 1만 = LCU 3.3. 신규 연결 RPS는 낮은데도 활성이 비싸진다.

### NLB의 3가지 LCU 차원

NLB는 룰 평가가 없고 신규/활성/처리 바이트만 있다. 대신 활성 연결의 단위가 다르다 — 분당 3,000개가 아니라 100,000개라서 같은 활성 연결 수면 NLB가 훨씬 싸다. 그래서 long-lived TCP 연결이 많으면 NLB가 유리하다.

처리 바이트도 NLB가 시간당 6GB로 ALB보다 단위가 크다. 단순 트래픽 양이 크면 NLB 쪽이 LCU가 덜 쌓인다.

### 실제 청구서에서 본 패턴

| 워크로드 | 지배적 LCU 차원 | 월 비용 추정 |
|---|---|---|
| 일반 REST API (RPS 200, 평균 응답 5KB) | 신규 연결 + 처리 바이트 | $30~50 |
| WebSocket 채팅(동접 5만) | 활성 연결 | $200~400 |
| 이미지 응답 API (RPS 50, 평균 1MB) | 처리 바이트 | $300~500 |
| 마이크로서비스 ALB (룰 80개, RPS 100) | 룰 평가 | $80~150 |
| MQTT 브로커 NLB(동접 30만) | 활성 연결 | $150~300 |

ALB 룰 평가가 비용을 잡아먹는 게 보이면 룰을 줄이고 백엔드에서 라우팅하게 옮기거나, 호스트 기반으로 ALB 자체를 쪼개는 방법이 있다.

## 헬스체크 운영 — 자주 데이는 지점

헬스체크 엔드포인트를 만들 때 DB 연결까지 확인하는 코드가 자주 들어간다. "DB가 안 되면 어차피 죽은 거니까"라는 논리인데, 이게 캐스케이드 장애를 만든다. DB가 잠깐 느려지면 모든 인스턴스의 헬스체크가 동시에 실패해서 ALB가 인스턴스를 전부 unhealthy로 처리한다. 그 순간 LB 뒤에 healthy 타겟이 0이 되고 503이 반환된다. DB는 곧 복구되는데 LB가 인스턴스를 다시 healthy로 올리는 데 2~3번의 성공이 필요하니까 그 시간 동안 추가 다운타임이 쌓인다.

헬스체크 엔드포인트는 프로세스 자체가 살아있다는 것만 확인하는 게 안전하다. DB 접속이 깨지면 그건 readiness 프로브로 별도로 처리하거나, 서킷 브레이커로 응답을 5xx 대신 503에 적절한 retry-after를 붙여 돌려준다.

`Interval`은 30초, `Timeout`은 5초, `HealthyThreshold`는 2, `UnhealthyThreshold`는 3 정도가 무난한 시작점이다. Interval 10초 같이 짧게 잡으면 헬스체크가 만드는 트래픽 자체가 무시할 수 없는 부하가 된다. ALB 타겟 그룹에 인스턴스 50개가 있고 Interval 10초면 초당 5번 헬스체크가 들어간다.

## Terraform으로 비교 — ALB와 NLB

같은 워크로드를 ALB와 NLB로 각각 만들 때 무엇이 달라지는지 보면 차이가 분명해진다.

### ALB 구성

```hcl
resource "aws_lb" "app" {
  name               = "app-alb"
  load_balancer_type = "application"
  internal           = false
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]

  enable_deletion_protection = true
  idle_timeout               = 60
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "app" {
  name        = "app-tg"
  port        = 8080
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/healthz"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }

  deregistration_delay = 60
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.app.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_lb_listener_rule" "api_users" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.user_service.arn
  }

  condition {
    path_pattern {
      values = ["/api/users/*"]
    }
  }
}
```

ALB는 보안 그룹이 필요하다. 인바운드 443, 백엔드 방향 아웃바운드를 열어줘야 한다. 리스너에서 TLS를 종료하니까 인증서가 ALB에 붙는다. 룰을 추가할 때마다 `priority`를 다르게 줘야 한다.

### NLB 구성

```hcl
resource "aws_lb" "app" {
  name               = "app-nlb"
  load_balancer_type = "network"
  internal           = false

  enable_cross_zone_load_balancing = true

  subnet_mapping {
    subnet_id     = aws_subnet.public_a.id
    allocation_id = aws_eip.nlb_a.id
  }
  subnet_mapping {
    subnet_id     = aws_subnet.public_b.id
    allocation_id = aws_eip.nlb_b.id
  }
}

resource "aws_lb_target_group" "app" {
  name        = "app-nlb-tg"
  port        = 8080
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  proxy_protocol_v2 = true

  health_check {
    protocol            = "HTTP"
    path                = "/healthz"
    port                = "8080"
    interval            = 30
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }

  deregistration_delay = 120
}

resource "aws_lb_listener" "tls" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "TLS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.app.arn
  alpn_policy       = "HTTP2Preferred"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
```

NLB는 보안 그룹이 없다(2023년부터 옵션으로 붙일 수 있게 됐지만 기본은 없음). 대신 백엔드 인스턴스의 보안 그룹에서 클라이언트 IP를 직접 받는다 — 0.0.0.0/0을 백엔드에 열어야 하는 사태가 벌어질 수 있어서 보안 그룹 설계를 다시 해야 한다.

가용영역별로 Elastic IP를 붙이려면 `subnet_mapping`을 명시한다. ALB에서는 그냥 `subnets`만 주면 됐던 게, NLB에서는 AZ마다 어떤 EIP를 쓸지 일일이 박는다.

`proxy_protocol_v2 = true`를 켰으니 백엔드도 이걸 파싱하게 만들어야 한다. 안 그러면 첫 패킷 파싱이 깨진다.

`alpn_policy = "HTTP2Preferred"`는 NLB TLS 리스너에서 HTTP/2를 협상할지 결정한다. gRPC를 NLB로 받을 거면 이게 필요하다. ALB는 자동으로 HTTP/2를 처리하니까 신경 쓸 일이 없다.

### NLB → ALB 체이닝 구성

고정 IP가 필요한데 L7 라우팅도 필요할 때 NLB 뒤에 ALB를 둔다.

```hcl
resource "aws_lb_target_group" "alb_chain" {
  name        = "nlb-to-alb"
  target_type = "alb"
  port        = 443
  protocol    = "TCP"
  vpc_id      = aws_vpc.main.id

  health_check {
    protocol = "HTTPS"
    path     = "/healthz"
    port     = "443"
    matcher  = "200-399"
  }
}

resource "aws_lb_target_group_attachment" "alb_chain" {
  target_group_arn = aws_lb_target_group.alb_chain.arn
  target_id        = aws_lb.app_alb.arn
  port             = 443
}
```

`target_type = "alb"`는 비교적 최근에 추가된 옵션이다. ALB의 ARN을 NLB 타겟 그룹에 직접 등록할 수 있다. 클라이언트 입장에서는 NLB의 고정 IP를 보지만, 실제 L7 라우팅은 ALB가 한다.

## 운영 중에 자주 들여다보는 CloudWatch 지표

ALB는 `HTTPCode_Target_5XX_Count`와 `HTTPCode_ELB_5XX_Count`를 분리해서 본다. 전자는 백엔드가 뱉은 5xx고, 후자는 ALB 자체가 만든 5xx다. 후자가 튀면 백엔드 코드를 봐도 답이 안 나온다 — 타겟 그룹에 healthy 타겟이 없거나, ALB가 백엔드와 연결 자체를 못 맺은 경우다. `TargetConnectionErrorCount`도 같이 본다.

`TargetResponseTime`의 p99가 헬스체크 timeout보다 커지면 정상 응답인데도 LB가 끊을 위험이 생긴다.

NLB는 `TCP_Client_Reset_Count`와 `TCP_Target_Reset_Count`를 본다. 백엔드 쪽에서 RST를 자주 보내면 keepalive 설정이나 idle timeout이 안 맞는다는 신호다.

`UnHealthyHostCount`는 알람에 무조건 박아둔다. 1 이상이 5분 지속되면 즉시 알림이 가야 한다.

## 정리

ALB는 HTTP/HTTPS·gRPC·WebSocket을 다루는 일반적인 웹 트래픽의 디폴트다. NLB는 UDP·고정 IP·TLS 패스스루·초저지연이 필요할 때, 또는 long-lived TCP 연결이 많을 때 고른다. CLB는 새 프로젝트에서 쓸 일이 없다.

선택보다 운영이 더 까다롭다. NLB의 클라이언트 IP 보존이 ip 타입 타겟에서 깨지는 것, ALB와 NLB의 idle timeout 차이, Cross-Zone 기본값 차이, LCU의 어느 차원이 비용을 끌어올리는지 — 이런 디테일이 청구서와 장애 빈도를 결정한다.
