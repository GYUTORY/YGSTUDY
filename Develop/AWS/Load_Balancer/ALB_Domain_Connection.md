---
title: ALB에 커스텀 도메인 연결 (Route 53 + ACM)
tags: [aws, alb, route53, acm, dns, tls, domain]
updated: 2026-05-26
---

# ALB에 커스텀 도메인 연결 (Route 53 + ACM)

ALB를 만들면 `myapp-123456.ap-northeast-2.elb.amazonaws.com` 같은 DNS 이름이 나온다. 사용자가 이 주소로 접속하지는 않는다. `example.com`이나 `api.example.com`을 이 ALB에 붙이는 작업이 따로 필요하다. 작업은 두 축으로 나뉜다. 하나는 Route 53에서 도메인 이름을 ALB로 향하게 하는 레코드, 다른 하나는 HTTPS를 위한 ACM 인증서다. 이 둘은 별개라서 한쪽만 해두고 나머지를 빠뜨려 SSL 오류나 연결 실패를 보는 경우가 흔하다.

이 문서는 도메인을 ALB에 연결하는 과정만 다룬다. ALB의 리스너 규칙·타깃 그룹·SNI 내부 동작은 [ALB.md](./ALB.md)에, DNS 레코드 일반론과 쿠키 스코프는 [Subdomain.md](../../Network/Domain/Subdomain.md)에, 요청이 흐르는 전체 경로는 [ALB_ECS_S3_Request_Flow.md](../Network/ALB_ECS_S3_Request_Flow.md)에 있다. 여기서는 그쪽과 겹치지 않게 연결 작업 자체만 본다.

## Route 53 alias로 ALB 연결

### zone apex에서 CNAME을 못 쓴다

`api.example.com` 같은 서브도메인은 CNAME으로 ALB DNS 이름을 가리켜도 동작한다. 문제는 `example.com` 자체, 즉 zone apex(루트 도메인)다. apex에는 CNAME을 둘 수 없다. apex에는 SOA와 NS 레코드가 반드시 있어야 하는데, CNAME은 같은 이름에 다른 레코드와 공존하지 못한다는 DNS 규칙 때문이다. 자세한 배경은 [Subdomain.md](../../Network/Domain/Subdomain.md)에 정리해 뒀다.

그래서 `example.com`을 ALB에 붙이려면 Route 53의 alias 레코드를 쓴다. alias는 타입이 A(또는 AAAA)지만 IP 대신 AWS 리소스를 가리킨다. apex에서도 쓸 수 있고, 조회 시점에 ALB DNS 이름을 실제 IP 묶음으로 풀어서 A 레코드처럼 응답한다. 클라이언트는 CNAME 추적 없이 IP를 바로 받는다.

### alias vs CNAME — 비용과 TTL 차이

서브도메인은 CNAME으로도 ALB를 가리킬 수 있어서 둘 중 뭘 쓸지 고민이 생긴다. 실무에서는 ALB를 가리킬 때 서브도메인이든 apex든 alias로 통일하는 편이 낫다. 이유는 두 가지다.

비용. Route 53은 ELB·CloudFront·S3·API Gateway 같은 AWS 리소스를 가리키는 alias 레코드의 조회에는 요금을 매기지 않는다. CNAME 조회는 일반 쿼리로 과금된다. 트래픽이 많으면 이 차이가 쌓인다.

TTL. alias로 ALB를 가리키면 TTL을 직접 정할 수 없다. Route 53이 ALB의 TTL(60초)을 그대로 따른다. CNAME은 우리가 TTL을 직접 박는다. ALB IP가 스케일링이나 AZ 장애로 바뀌는 상황을 생각하면 60초 고정이 안전하다. CNAME에 TTL을 길게 박아두면 ALB IP가 바뀐 뒤에도 옛 IP를 오래 캐싱한다.

### ALB DNS는 IP가 여러 개고, alias가 이를 따라간다

ALB DNS 이름을 dig으로 찍으면 IP가 보통 AZ 수만큼 나온다. ALB가 가용 영역마다 ENI를 하나씩 들고 있어서다. 이 IP는 고정이 아니다. 스케일링이나 장애 복구로 ENI가 새로 뜨면 IP가 갈린다. alias는 조회마다 ALB DNS 이름을 다시 풀기 때문에 IP가 바뀌어도 자동으로 따라간다. 우리가 IP를 박아두는 게 아니라 "이 ALB"를 가리키는 구조라서 신경 쓸 게 없다.

여기서 절대 하면 안 되는 게 `dig`으로 나온 IP를 A 레코드에 직접 박는 일이다. 그 순간 IP가 바뀌면 도메인이 죽은 IP를 가리킨다. ALB IP는 고정이 아니라는 걸 모르고 한 번씩 사고가 난다.

### CLI로 alias 레코드 만들기

alias의 타깃 `HostedZoneId`는 ALB의 IP 호스티드 존이 아니라 ELB의 리전별 정규 호스티드 존 ID다. 리전마다 값이 정해져 있다. 헷갈리면 `describe-load-balancers`로 ALB의 `CanonicalHostedZoneId`를 직접 가져온다.

```bash
# ALB의 DNS 이름과 정규 호스티드 존 ID 확인
aws elbv2 describe-load-balancers \
  --names myapp-alb \
  --query 'LoadBalancers[0].{DNS:DNSName,ZoneId:CanonicalHostedZoneId}'
# {
#   "DNS": "myapp-alb-123456.ap-northeast-2.elb.amazonaws.com",
#   "ZoneId": "ZWKZPGTI48KDX"   # ap-northeast-2 ALB의 고정 값
# }

# apex(example.com)를 ALB로 향하게
aws route53 change-resource-record-sets \
  --hosted-zone-id Z0123456789ABCDEFGHIJ \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "ZWKZPGTI48KDX",
          "DNSName": "dualstack.myapp-alb-123456.ap-northeast-2.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

`DNSName` 앞에 `dualstack.`을 붙인 데 주목한다. ALB는 IPv4·IPv6를 같이 받는데, `dualstack.` 접두사를 붙여야 A·AAAA 양쪽으로 올바르게 풀린다. IPv6까지 받으려면 같은 이름으로 `Type: AAAA` alias를 하나 더 만들어야 한다. A 하나만 만들어 두면 IPv6 클라이언트가 도메인을 못 푼다.

### Terraform

```hcl
resource "aws_route53_record" "apex" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "example.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# IPv6용 AAAA alias (필요하면)
resource "aws_route53_record" "apex_v6" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "example.com"
  type    = "AAAA"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# 서브도메인도 같은 방식
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.example.com"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
```

Terraform에서는 `aws_lb.main.zone_id`가 ELB의 정규 호스티드 존 ID로 자동으로 들어가서 리전별 값을 외울 필요가 없다. `evaluate_target_health = true`는 뒤에 다룰 헬스체크 기반 페일오버에서 쓴다.

## ACM 인증서 발급과 DNS 검증

HTTPS 리스너를 붙이려면 인증서가 필요하다. ALB에는 ACM(AWS Certificate Manager)에서 발급한 인증서를 붙인다. ACM 인증서는 무료고 갱신도 자동이라 외부 CA에서 받아 IAM에 임포트하는 것보다 운영이 편하다.

### 리전 제약 — ALB와 같은 리전의 ACM만 된다

이게 가장 먼저 막히는 지점이다. ALB에 붙일 인증서는 ALB와 같은 리전에서 발급해야 한다. 서울 리전(`ap-northeast-2`)의 ALB에는 서울 리전 ACM 인증서만 붙는다. `us-east-1`에서 발급한 인증서는 안 보인다.

CloudFront는 반대로 무조건 `us-east-1` 인증서를 요구하는데(이건 [Subdomain.md](../../Network/Domain/Subdomain.md)에 정리해 뒀다), 그래서 CloudFront와 ALB를 같이 쓰는 구조면 같은 도메인 인증서를 `us-east-1`과 ALB 리전 양쪽에 각각 발급하게 된다. 인증서 ARN이 두 개가 된다. 헷갈리지 말아야 한다.

### DNS 검증 CNAME

인증서를 받으려면 도메인 소유를 증명해야 한다. 검증 방식은 DNS와 이메일 두 가지인데, 자동 갱신을 생각하면 DNS 검증을 써야 한다. ACM이 검증용 CNAME 레코드 하나를 알려주고, 그 레코드를 도메인의 DNS에 넣으면 ACM이 확인 후 발급한다.

```bash
# 인증서 요청 — apex와 와일드카드를 한 인증서에
CERT_ARN=$(aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" \
  --validation-method DNS \
  --region ap-northeast-2 \
  --query CertificateArn --output text)

# ACM이 요구하는 검증 레코드 확인
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region ap-northeast-2 \
  --query 'Certificate.DomainValidationOptions[*].ResourceRecord'
```

나오는 검증 레코드는 이런 모양이다.

```
이름:  _3639ac514e785e898d2646601fa951d5.example.com.
타입:  CNAME
값:    _f5a3cba0e7c9ad7bf6b8b6e6f3.acm-validations.aws.
```

이 CNAME을 Route 53에 넣으면 ACM이 몇 분 안에 확인하고 인증서가 `ISSUED`로 바뀐다. 도메인이 Route 53에 있으면 콘솔의 "Create records in Route 53" 버튼이나 CLI로 한 번에 만들 수 있다.

한 가지 알아둘 점. `example.com`과 `*.example.com`을 같이 요청하면 두 도메인의 검증 CNAME 이름이 같다. ACM이 같은 검증 레코드 하나로 둘을 처리하기 때문이다. 그래서 검증 레코드는 도메인 수만큼이 아니라 그보다 적게 나올 수 있다.

### 와일드카드 vs SAN 다중 도메인

인증서 하나에 도메인을 어떻게 담을지는 운영 방식에 따라 갈린다.

와일드카드(`*.example.com`)는 서브도메인이 동적으로 늘어나는 경우에 쓴다. `api.example.com`, `admin.example.com`, `app.example.com`이 모두 한 인증서로 커버된다. 단 와일드카드는 한 단계만 커버한다. `*.example.com`은 `v1.api.example.com`에는 유효하지 않다. apex(`example.com`)도 커버하지 않아서 apex를 쓸 거면 SAN에 `example.com`을 따로 넣어야 한다.

SAN 다중 도메인은 도메인을 명시적으로 나열하는 방식이다. `example.com`, `api.example.com`, `admin.example.com`을 SAN에 박는다. 서브도메인이 고정돼 있고 개수가 적으면 이쪽이 관리가 명확하다. 어떤 도메인이 이 인증서로 보호되는지 ARN만 봐도 안다.

실무에서는 둘을 섞는다. apex는 명시하고 나머지는 와일드카드로 받는 식이다.

```bash
aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names "*.example.com" "*.api.example.com" \
  --validation-method DNS \
  --region ap-northeast-2
```

### 검증 레코드를 지우면 갱신이 깨진다

ACM 인증서는 13개월짜리고 만료 전에 자동 갱신된다. 갱신할 때 ACM은 처음 검증에 썼던 그 CNAME을 다시 확인한다. 인증서를 받고 나면 검증 레코드가 더는 필요 없어 보여서 지우는 경우가 있는데, 지우면 안 된다. 자동 갱신 시점(만료 약 60일 전부터 시도)에 검증 레코드가 없으면 갱신이 실패하고 인증서가 그대로 만료된다. 만료된 순간 ALB가 SSL 오류를 뱉기 시작한다.

검증 CNAME은 한 번 넣으면 영구히 둔다. Route 53 정리할 때 `_xxxx.acm-validations.aws`로 끝나는 레코드는 건드리지 않는다.

### Terraform — 발급부터 검증 완료까지

Terraform으로는 인증서 요청, 검증 레코드 생성, 검증 완료 대기를 한 번에 묶는다. `aws_acm_certificate_validation`이 검증이 끝날 때까지 apply를 잡아 둬서, 검증 전에 리스너가 인증서를 참조하다 깨지는 걸 막는다.

```hcl
resource "aws_acm_certificate" "main" {
  domain_name               = "example.com"
  subject_alternative_names = ["*.example.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id         = aws_route53_zone.main.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}
```

`allow_overwrite = true`가 빠지면 apply가 깨지는 경우가 있다. apex와 와일드카드의 검증 레코드 이름이 같아서 `for_each`가 같은 Route 53 레코드를 두 번 만들려다 충돌하기 때문이다. 이 한 줄이 그 충돌을 덮어쓰기로 처리한다. 처음 이 패턴을 짤 때 자주 밟는 지뢰다.

리스너에서는 검증 완료 리소스의 ARN을 참조한다. `aws_acm_certificate.main.arn`이 아니라 `aws_acm_certificate_validation.main.certificate_arn`을 써야 검증이 끝난 뒤에 리스너가 만들어진다.

```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn
  # ...
}
```

## 하나의 ALB로 여러 도메인 받기 (host-header 라우팅)

ALB 하나로 `api.example.com`과 `admin.example.com`을 받아서 서로 다른 타깃 그룹으로 보낼 수 있다. 도메인마다 ALB를 따로 만들 필요가 없다. 두 가지를 맞춰야 한다. 인증서(SNI)와 라우팅 규칙(host-header)이다.

### 인증서 쪽 — SNI와 default certificate

443 리스너 하나에 인증서를 여러 개 붙일 수 있다. 클라이언트가 TLS 핸드셰이크에서 보내는 SNI(접속하려는 도메인 이름)를 보고 ALB가 맞는 인증서를 골라 내려준다. `api.example.com`으로 오면 그 도메인이 든 인증서를, `admin.example.com`으로 오면 그쪽 인증서를 준다. SNI 다중 인증서의 내부 동작은 [ALB.md](./ALB.md)에 정리돼 있으니 여기서는 도메인 연결 관점만 본다.

핵심은 default certificate다. SNI가 없거나(아주 오래된 클라이언트) 어떤 인증서에도 매칭되지 않으면 ALB는 default 인증서를 내려준다. 와일드카드(`*.example.com`)나 가장 범용적인 도메인 인증서를 default로 두는 게 안전하다. default가 엉뚱한 도메인 인증서면 일부 클라이언트가 인증서 불일치 오류를 받는다.

```bash
# 첫 인증서가 default가 된다
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS --port 443 \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --certificates CertificateArn=$WILDCARD_CERT_ARN \
  --default-actions Type=fixed-response,FixedResponseConfig='{StatusCode=503,ContentType=text/plain,MessageBody=No route}' \
  --query 'Listeners[0].ListenerArn' --output text)

# 추가 인증서는 SNI용으로 따로 붙인다
aws elbv2 add-listener-certificates \
  --listener-arn $LISTENER_ARN \
  --certificates CertificateArn=$ADMIN_CERT_ARN
```

### 라우팅 쪽 — host-header 규칙과 우선순위

인증서를 골라 핸드셰이크가 끝나면, ALB는 들어온 요청의 Host 헤더를 보고 어느 타깃 그룹으로 보낼지 정한다. host-header 조건 규칙을 도메인마다 만든다.

```bash
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 100 \
  --conditions '[{"Field":"host-header","Values":["api.example.com"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"'$API_TG_ARN'"}]'

aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 200 \
  --conditions '[{"Field":"host-header","Values":["admin.example.com"]}]' \
  --actions '[{"Type":"forward","TargetGroupArn":"'$ADMIN_TG_ARN'"}]'
```

우선순위가 라우팅을 좌우한다. 규칙은 priority 숫자가 낮은 것부터 평가되고, 먼저 매칭되는 규칙에서 멈춘다. host-header와 path-pattern을 섞어 쓸 때 순서가 꼬이기 쉽다. 예를 들어 `priority 50`에 `path-pattern: /admin/*`이 있고 `priority 100`에 `host-header: api.example.com`이 있으면, `api.example.com/admin/...` 요청이 50번 규칙에 먼저 걸려 admin 타깃으로 가버린다. 의도가 "도메인 우선"이면 host-header 규칙을 더 낮은 priority(앞쪽)에 둬야 한다.

host-header 조건도 와일드카드를 받는다. `*.example.com`으로 한 규칙에서 모든 서브도메인을 받고 백엔드에서 분기하는 방식도 가능하다.

```hcl
resource "aws_lb_listener_certificate" "admin" {
  listener_arn    = aws_lb_listener.https.arn
  certificate_arn = aws_acm_certificate.admin.arn
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  condition {
    host_header {
      values = ["api.example.com"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener_rule" "admin" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 200

  condition {
    host_header {
      values = ["admin.example.com"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.admin.arn
  }
}
```

Route 53에서는 `api.example.com`과 `admin.example.com` 둘 다 같은 ALB를 가리키는 alias 레코드를 만든다. 도메인은 둘이지만 ALB는 하나라서 alias 타깃이 같다.

## HTTP를 HTTPS로 돌리는 301 리다이렉트

도메인을 붙이면 사용자가 `http://example.com`으로 들어오는 경우가 반드시 생긴다. 주소창에 프로토콜 없이 입력하면 브라우저가 http로 먼저 붙기 때문이다. 80 리스너를 따로 두고, 들어온 요청을 443으로 301 리다이렉트한다.

```bash
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions \
    'Type=redirect,RedirectConfig={Protocol=HTTPS,Port=443,Host="#{host}",Path="/#{path}",Query="#{query}",StatusCode=HTTP_301}'
```

```hcl
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      protocol    = "HTTPS"
      port        = "443"
      status_code = "HTTP_301"
      # host, path, query는 생략 시 원래 값 그대로 유지된다
    }
  }
}
```

301과 302 중 301을 쓴다. 301은 영구 이동이라 브라우저가 결과를 캐싱하고, 다음부터는 http로 요청조차 안 하고 바로 https로 간다. 302는 매번 80으로 한 번 들렀다 간다. http로 서비스할 일이 없으면 301이 맞다. `#{host}`, `#{path}`, `#{query}` 자리표시자를 쓰면 원래 도메인·경로·쿼리스트링을 유지한 채 프로토콜만 바꿔서 보낸다. 이걸 빼먹고 고정 경로로 리다이렉트하면 `http://example.com/orders/123`이 `https://example.com`으로 떨어져서 딥링크가 다 깨진다.

리다이렉트는 ALB가 직접 응답하므로 80 리스너에는 타깃 그룹이 필요 없다. 80에서 백엔드까지 패킷이 가지 않는다.

## 도메인 전환·연결 트러블슈팅

### 전환 전에 TTL을 낮춰 둔다

기존 도메인을 다른 곳에서 ALB로 옮기는 상황이라면 전환 전에 기존 레코드의 TTL을 낮춘다. 옛 서버를 가리키던 A 레코드의 TTL이 86400(하루)이면, ALB로 바꿔도 전 세계 리졸버 캐시가 만료될 때까지 최대 하루 동안 옛 서버로 트래픽이 간다. 전환 며칠 전에 TTL을 60~300초로 내려두고, 캐시가 빠질 때를 기다린 뒤 레코드를 ALB alias로 바꾼다. 안정화되면 다시 올린다. alias로 바꾼 뒤에는 TTL이 ALB의 60초로 고정돼서 우리가 신경 쓸 게 없어진다.

레지스트라의 네임서버를 Route 53으로 옮기는 전환이면 NS 레코드 TTL도 같은 식으로 본다. 도메인을 Route 53으로 옮길 때 레지스트라 쪽 NS를 Route 53 NS로 바꾸지 않으면 hosted zone에 레코드를 아무리 박아도 외부에서는 안 보인다. 이건 [ALB_ECS_S3_Request_Flow.md](../Network/ALB_ECS_S3_Request_Flow.md)의 DNS STEP에서도 다룬 흔한 함정이다.

### ACM이 PENDING_VALIDATION에서 멈춤

인증서를 요청했는데 `ISSUED`로 안 넘어가고 `PENDING_VALIDATION`에 한참 머물면 검증 CNAME이 실제로 조회되는지부터 본다.

```bash
# 검증 레코드가 제대로 퍼졌는지 직접 조회
dig +short _3639ac514e785e898d2646601fa951d5.example.com CNAME
# 값이 안 나오면 레코드가 없거나 NS 위임이 안 된 것
```

멈추는 원인은 보통 이렇다. 검증 CNAME을 안 넣었거나 오타가 있는 경우. 도메인의 NS가 Route 53을 가리키지 않아서 ACM이 검증 레코드를 못 읽는 경우(레코드는 Route 53에 있는데 권한 네임서버가 다른 곳이면 소용없다). 그리고 의외로 자주 놓치는 게 CAA 레코드다. 도메인에 CAA 레코드가 걸려 있는데 그 목록에 `amazon.com`이 없으면 ACM은 발급 자체를 거부한다.

```bash
# CAA 레코드 확인 — amazon.com이 허용 목록에 있어야 ACM이 발급한다
dig +short example.com CAA
# 0 issue "amazon.com"  같은 항목이 있어야 한다
```

CAA를 걸어둔 도메인이면 `0 issue "amazon.com"`을 추가해야 ACM이 인증서를 내준다. 이걸 모르고 검증 레코드만 계속 들여다보다 시간을 버리는 경우가 있다.

### SSL handshake 실패

도메인은 ALB로 잘 풀리는데 HTTPS 접속에서 핸드셰이크가 깨지는 경우다.

클라이언트가 받은 인증서가 접속 도메인과 안 맞는 경우. SNI로 매칭되는 인증서가 없으면 ALB는 default 인증서를 내려준다. default가 `*.example.com`인데 `another-domain.com`으로 접속하면 도메인 불일치로 핸드셰이크가 거부된다. 새 도메인을 붙였으면 그 도메인 인증서를 리스너에 add 했는지부터 본다.

```bash
# 특정 도메인으로 SNI를 보내 ALB가 어떤 인증서를 주는지 확인
openssl s_client -connect example.com:443 -servername api.example.com 2>/dev/null \
  | openssl x509 -noout -subject -ext subjectAltName
# 내려온 인증서의 도메인이 접속하려는 도메인을 커버하는지 본다
```

SNI를 안 보내는 아주 오래된 클라이언트(구형 안드로이드, 일부 IoT)는 ALB가 무조건 default 인증서를 준다. 이런 클라이언트까지 받아야 하면 default를 가장 범용적인 인증서로 둬야 한다. 요즘 브라우저는 다 SNI를 보내서 일반 웹 트래픽에서는 거의 안 겪는다.

### Route 53 헬스체크와 페일오버

ALB 한 대가 죽거나 리전 장애가 났을 때 도메인을 다른 ALB로 자동으로 넘기려면 Route 53 헬스체크와 failover 라우팅을 건다. alias 레코드의 `evaluate_target_health = true`는 ALB 자체의 상태를 보고 그 alias를 응답에서 뺄지 정하는 옵션이다. 여기에 failover 정책으로 primary/secondary를 나누면 primary가 unhealthy일 때 secondary로 응답이 넘어간다.

```hcl
resource "aws_route53_health_check" "primary" {
  fqdn              = aws_lb.primary.dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health/live"
  failure_threshold = 3
  request_interval  = 30
}

resource "aws_route53_record" "primary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "example.com"
  type    = "A"

  set_identifier = "primary"
  failover_routing_policy {
    type = "PRIMARY"
  }
  health_check_id = aws_route53_health_check.primary.id

  alias {
    name                   = aws_lb.primary.dns_name
    zone_id                = aws_lb.primary.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "secondary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "example.com"
  type    = "A"

  set_identifier = "secondary"
  failover_routing_policy {
    type = "SECONDARY"
  }

  alias {
    name                   = aws_lb.secondary.dns_name
    zone_id                = aws_lb.secondary.zone_id
    evaluate_target_health = true
  }
}
```

헬스체크 경로는 ALB.md에서 다룬 shallow check(`/health/live`)를 본다. DB까지 확인하는 deep check를 Route 53 헬스체크에 걸면, DB가 잠깐 흔들릴 때 멀쩡한 ALB 전체가 unhealthy로 판정돼 도메인이 통째로 secondary로 넘어간다. 페일오버는 ALB나 리전이 진짜로 죽었을 때만 일어나야 한다.

페일오버가 일어나도 클라이언트 캐시 때문에 즉시 넘어가지는 않는다. alias의 TTL은 ALB의 60초라서 최악의 경우 60초 정도는 옛 ALB로 트래픽이 갈 수 있다. failover가 RTO 0초가 아니라는 걸 알고 설계해야 한다.

## 정리

도메인을 ALB에 붙이는 작업은 Route 53 alias 레코드와 ACM 인증서 두 축이다. apex는 CNAME을 못 쓰니 alias를 쓰고, 인증서는 ALB와 같은 리전 ACM에서 DNS 검증으로 받되 검증 CNAME은 갱신을 위해 영구히 둔다. 하나의 ALB로 여러 도메인을 받을 때는 SNI 인증서와 host-header 규칙을 도메인마다 짝지어 맞추고, default 인증서를 범용 도메인으로 둔다. 전환할 때는 기존 레코드 TTL을 미리 낮추고, 발급이 안 풀리면 검증 CNAME·NS 위임·CAA 순으로 확인한다.

## 참고 링크

- [Route 53로 ELB 라우팅 (alias)](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-elb-load-balancer.html)
- [ACM DNS 검증](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)
- [ACM 관리형 갱신](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html)
- [ELB 리전별 정규 호스티드 존 ID](https://docs.aws.amazon.com/general/latest/gr/elb.html)
- [Route 53 failover 라우팅](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-failover.html)
