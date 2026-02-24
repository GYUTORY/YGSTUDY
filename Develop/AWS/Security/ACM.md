---
title: AWS ACM (Certificate Manager)
tags: [aws, acm, ssl, tls, certificate, https, security]
updated: 2026-01-18
---

# AWS ACM (Certificate Manager)

## 개요

ACM은 SSL/TLS 인증서를 관리하는 서비스다. 인증서를 무료로 발급한다. 자동으로 갱신한다. ALB, CloudFront, API Gateway에 쉽게 연결한다. Let's Encrypt처럼 무료지만 AWS 서비스에 통합되어 있어서 더 편하다.

### 왜 필요한가

HTTPS는 필수다. 인증서 관리는 번거롭다.

**문제 상황: 수동 인증서 관리**

**전통적인 방법:**
1. 인증서 구매 (연 $50-200)
2. 도메인 소유권 증명
3. 인증서 파일 다운로드
4. 서버에 설치
5. 90일마다 갱신
6. 서버 재시작

**문제:**
- 비용 발생
- 매번 수동 작업
- 갱신을 잊으면 서비스 중단
- 여러 서버에 배포 복잡

**ACM의 해결:**
1. ACM에서 인증서 요청 (무료)
2. 도메인 소유권 자동 검증 (Route 53 사용 시)
3. ALB/CloudFront에 연결
4. 자동 갱신
5. 서버 재시작 불필요

**간단하고 무료다.**

## 인증서 요청

### 공인 인증서

인터넷에 공개된 웹사이트용이다.

**콘솔:**
1. ACM 콘솔
2. "Request a certificate" 클릭
3. "Request a public certificate" 선택
4. 도메인 이름 입력: `example.com`
5. 와일드카드 추가: `*.example.com`
6. 검증 방법 선택: DNS 또는 Email
7. 요청

**CLI:**
```bash
aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names *.example.com \
  --validation-method DNS \
  --region us-west-2
```

**도메인 이름:**
- `example.com`: 메인 도메인
- `*.example.com`: 모든 서브도메인 (api.example.com, www.example.com 등)

하나의 인증서로 메인과 서브도메인을 모두 커버한다.

### 도메인 검증

인증서를 발급받으려면 도메인 소유권을 증명해야 한다.

**DNS 검증 (권장):**

**Route 53 사용 시:**
자동으로 CNAME 레코드를 추가한다. 클릭 한 번이면 된다.

**다른 DNS 사용 시:**
ACM이 CNAME 레코드 정보를 제공한다. DNS 제공업체에 수동으로 추가한다.

**예시:**
```
Name: _abc123.example.com
Type: CNAME
Value: _def456.acm-validations.aws.
```

DNS에 추가하면 몇 분 내에 검증이 완료된다.

**Email 검증:**
도메인 관리자 이메일로 검증 링크를 보낸다.

**이메일 주소:**
- admin@example.com
- administrator@example.com
- hostmaster@example.com
- postmaster@example.com
- webmaster@example.com

이메일을 받아서 링크를 클릭한다.

**단점:**
갱신할 때마다 이메일 검증을 다시 해야 한다. DNS 검증을 사용하는 것이 좋다.

### 검증 완료

검증이 완료되면 인증서 상태가 "Issued"가 된다. 이제 사용할 수 있다.

**확인:**
```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-west-2:123456789012:certificate/abcd1234-5678-90ab-cdef-1234567890ab
```

`Status: "ISSUED"`를 확인한다.

## 인증서 연결

### ALB에 연결

**콘솔:**
1. EC2 콘솔 → Load Balancers
2. ALB 선택
3. Listeners 탭
4. HTTPS:443 Listener 추가
5. Default SSL certificate 선택
6. ACM 인증서 선택
7. 저장

**CLI:**
```bash
# HTTPS Listener 생성
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-alb/1234567890abcdef \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-west-2:123456789012:certificate/abcd1234-5678-90ab-cdef-1234567890ab \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-targets/1234567890abcdef
```

**SSL Policy:**
최신 보안 정책을 사용한다.

```bash
--ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06
```

TLS 1.3과 1.2를 지원한다. 이전 버전은 차단한다.

**HTTP to HTTPS 리다이렉트:**
HTTP 요청을 HTTPS로 리다이렉트한다.

```bash
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:...:loadbalancer/... \
  --protocol HTTP \
  --port 80 \
  --default-actions \
    Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}"
```

모든 트래픽이 HTTPS로 간다.

### CloudFront에 연결

**주의:** CloudFront는 us-east-1 리전의 인증서만 사용한다.

**us-east-1에서 인증서 요청:**
```bash
aws acm request-certificate \
  --domain-name example.com \
  --subject-alternative-names *.example.com \
  --validation-method DNS \
  --region us-east-1
```

**CloudFront Distribution 설정:**
```bash
aws cloudfront update-distribution \
  --id E123456789ABCD \
  --distribution-config file://distribution-config.json
```

**distribution-config.json:**
```json
{
  "ViewerCertificate": {
    "ACMCertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-5678-90ab-cdef-1234567890ab",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "Aliases": {
    "Items": ["example.com", "www.example.com"]
  }
}
```

**SNI vs Dedicated IP:**
- **sni-only**: 무료, 최신 브라우저 지원
- **vip**: $600/월, 구형 브라우저 지원

대부분 SNI로 충분하다.

### API Gateway에 연결

**Custom Domain 생성:**
```bash
aws apigatewayv2 create-domain-name \
  --domain-name api.example.com \
  --domain-name-configurations \
    CertificateArn=arn:aws:acm:us-west-2:123456789012:certificate/abcd1234-5678-90ab-cdef-1234567890ab
```

**API Mapping:**
```bash
aws apigatewayv2 create-api-mapping \
  --domain-name api.example.com \
  --api-id abc123 \
  --stage prod
```

**Route 53 설정:**
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://change-batch.json
```

**change-batch.json:**
```json
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "d-abc123.execute-api.us-west-2.amazonaws.com",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
```

`api.example.com`으로 API에 접근할 수 있다.

## 자동 갱신

ACM 인증서는 자동으로 갱신된다.

### 동작 방식

**갱신 시점:**
만료 60일 전에 자동으로 갱신을 시도한다. 30일 전부터 매일 시도한다.

**DNS 검증:**
검증 CNAME 레코드가 그대로 있으면 자동으로 갱신된다. 레코드를 삭제하지 않는다.

**Email 검증:**
갱신할 때마다 이메일을 다시 받는다. 링크를 클릭해야 한다. 자동 갱신이 아니다. **DNS 검증을 사용해야 한다.**

**ALB/CloudFront:**
인증서가 갱신되면 자동으로 새 인증서를 사용한다. 수동 작업 불필요.

### 갱신 실패

DNS 검증 레코드를 삭제하면 갱신이 실패한다.

**알림:**
갱신 실패 시 이메일을 보낸다. 도메인 소유자에게 알림이 간다.

**해결:**
DNS 검증 레코드를 다시 추가한다. ACM이 자동으로 재시도한다.

## 프라이빗 인증서

내부 서비스용 인증서다. Private CA를 사용한다.

### Private CA 생성

**비용:** $400/월

Private CA를 만들어야 프라이빗 인증서를 발급할 수 있다.

```bash
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration file://ca-config.json \
  --certificate-authority-type ROOT
```

**ca-config.json:**
```json
{
  "KeyAlgorithm": "RSA_2048",
  "SigningAlgorithm": "SHA256WITHRSA",
  "Subject": {
    "Country": "US",
    "Organization": "MyCompany",
    "OrganizationalUnit": "IT",
    "CommonName": "MyCompany Root CA"
  }
}
```

### 프라이빗 인증서 발급

```bash
aws acm request-certificate \
  --domain-name internal.mycompany.com \
  --certificate-authority-arn arn:aws:acm-pca:us-west-2:123456789012:certificate-authority/abcd1234-5678-90ab-cdef-1234567890ab
```

**사용 사례:**
- 내부 API
- 마이크로서비스 간 통신
- VPN
- 개발/테스트 환경

공인 CA보다 안전하다. 내부에서만 신뢰한다.

## 인증서 가져오기

외부에서 구매한 인증서를 ACM에 가져온다.

**사용 사례:**
- 이미 구매한 인증서가 있다
- 특정 CA의 인증서가 필요하다
- Extended Validation (EV) 인증서

**가져오기:**
```bash
aws acm import-certificate \
  --certificate fileb://certificate.pem \
  --private-key fileb://private-key.pem \
  --certificate-chain fileb://certificate-chain.pem
```

**파일:**
- `certificate.pem`: 인증서
- `private-key.pem`: 개인 키
- `certificate-chain.pem`: 인증서 체인 (중간 CA)

**주의:**
가져온 인증서는 자동 갱신되지 않는다. 만료 전에 수동으로 갱신해야 한다.

**만료 알림:**
만료 45일 전에 이메일을 보낸다.

## 모니터링

### 만료 알림

ACM은 인증서 만료 전에 이메일을 보낸다.

**타이밍:**
- 45일 전: 첫 알림
- 30일 전: 두 번째 알림
- 15일 전: 세 번째 알림
- 7일 전: 마지막 알림

**수신자:**
- AWS 계정 관리자
- 도메인 WHOIS 연락처
- 인증서 요청 시 지정한 이메일

### CloudWatch Events

인증서 상태 변경 시 이벤트를 발생시킨다.

**EventBridge 규칙:**
```bash
aws events put-rule \
  --name acm-certificate-expiring \
  --event-pattern file://event-pattern.json \
  --state ENABLED
```

**event-pattern.json:**
```json
{
  "source": ["aws.acm"],
  "detail-type": ["ACM Certificate Approaching Expiration"]
}
```

**SNS 연결:**
```bash
aws events put-targets \
  --rule acm-certificate-expiring \
  --targets Id=1,Arn=arn:aws:sns:us-west-2:123456789012:certificate-alerts
```

만료 45일 전에 SNS로 알림을 받는다. Slack이나 PagerDuty에 연동한다.

### AWS Config

인증서 상태를 추적한다.

**규칙:**
- 인증서가 90일 내 만료되는지
- 인증서가 사용 중인지
- 인증서가 ACM 모범 사례를 따르는지

비준수 인증서를 자동으로 탐지한다.

## 비용

### 공인 인증서

**무료**

ACM이 발급한 공인 인증서는 완전히 무료다.
- 발급 무료
- 갱신 무료
- 개수 제한 없음

### 프라이빗 인증서

**Private CA:**
$400/월

**인증서 발급:**
- 처음 1,000개: $0.75/개
- 1,001-10,000개: $0.35/개
- 10,001개 이상: $0.001/개

**예시:**
- Private CA 1개: $400/월
- 인증서 100개 발급: $75
- 합계: $475/월

비싸다. 꼭 필요한 경우에만 사용한다.

### 가져온 인증서

**무료**

외부 인증서를 가져와서 사용하는 것은 무료다. 하지만 인증서 구매 비용은 별도다.

## 실무 팁

### DNS 검증 사용

Email 검증은 수동이다. DNS 검증을 사용한다.

**이유:**
- 자동 갱신
- 수동 작업 불필요
- 여러 인증서를 한 번에 검증

### Route 53 사용

Route 53을 사용하면 DNS 검증이 자동이다.

**과정:**
1. ACM에서 인증서 요청
2. "Create record in Route 53" 클릭
3. 끝

CNAME 레코드가 자동으로 추가된다. 몇 분 내에 검증 완료.

### 와일드카드 인증서

서브도메인이 많으면 와일드카드 인증서를 사용한다.

**예시:**
- `*.example.com`
- api.example.com, www.example.com, admin.example.com 모두 커버

하나의 인증서로 모든 서브도메인을 처리한다.

**주의:**
메인 도메인 (`example.com`)은 별도로 추가해야 한다.

```bash
--domain-name example.com \
--subject-alternative-names *.example.com
```

### 인증서 만료 모니터링

가져온 인증서는 자동 갱신되지 않는다. CloudWatch Events로 모니터링한다.

```bash
aws events put-rule \
  --name acm-expiring-certificates \
  --schedule-expression "rate(1 day)" \
  --state ENABLED
```

매일 만료 상태를 확인한다. 만료 30일 전에 알림을 보낸다.

### 여러 리전에서 사용

인증서는 리전별로 발급된다.

**ALB (us-west-2):**
us-west-2에서 인증서 요청

**CloudFront:**
us-east-1에서 인증서 요청

**여러 리전:**
각 리전에서 인증서를 따로 요청한다. DNS 검증 레코드는 동일하다. 한 번만 추가하면 모든 리전에서 검증된다.

### 무료 이모지 감사 금지

ACM은 완전히 무료다. AWS의 큰 혜택이다. Let's Encrypt와 달리 AWS 서비스에 완벽하게 통합되어 있다. 적극적으로 사용한다.

## 참고

- AWS ACM 개발자 가이드: https://docs.aws.amazon.com/acm/
- ACM 요금: https://aws.amazon.com/certificate-manager/pricing/
- SSL/TLS 모범 사례: https://docs.aws.amazon.com/acm/latest/userguide/acm-bestpractices.html
- Private CA: https://docs.aws.amazon.com/acm-pca/

