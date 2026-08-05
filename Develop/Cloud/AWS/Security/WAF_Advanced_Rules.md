---
title: AWS WAF 고급 규칙 운영 (CAPTCHA·라벨 체이닝·JSON 검사·Firewall Manager)
tags: [aws, waf, wafv2, captcha, challenge, json-body, atp, firewall-manager, false-positive, security]
updated: 2026-06-21
---

# AWS WAF 고급 규칙 운영

기본 Web ACL, SQLi/XSS, IP 차단은 [WAF.md](WAF.md)에, Bot Control 룰 그룹과 봇 방어 흐름은 [WAF_Bot_Control.md](WAF_Bot_Control.md)에 정리돼 있다. 이 문서는 그 두 문서를 운영하면서 부딪히는 다음 단계 주제만 모았다. CAPTCHA/Challenge의 토큰 도메인과 면제 시간을 어떻게 잡는지, 내가 만든 규칙에 라벨을 달아 뒤 규칙이 받게 하는 체이닝, GraphQL·REST 본문을 JSON으로 파고드는 검사와 본문 크기 한계, ATP 로그인 페이로드 매핑, Firewall Manager로 여러 계정에 Web ACL을 한 번에 까는 방법, 그리고 오탐이 났을 때 어떤 규칙이 막았는지 추적하는 디버깅 순서다.

## CAPTCHA와 Challenge — 토큰 도메인과 면제 시간

CAPTCHA와 Challenge의 동작 차이 자체는 Bot Control 문서에 있다. 사람이 퍼즐을 푸는 게 CAPTCHA, 브라우저가 백그라운드에서 JS 연산을 푸는 게 Challenge다. 여기서는 둘 다 토큰을 발급한다는 점에서 생기는 두 가지 운영 설정만 본다. 토큰이 어느 도메인에서 유효한가(TokenDomains), 한 번 통과하면 얼마 동안 다시 안 묻는가(ImmunityTime)다.

### 면제 시간(ImmunityTime)

토큰을 받은 클라이언트는 면제 시간 동안 같은 액션을 다시 만나지 않는다. 기본값은 CAPTCHA 300초, Challenge 300초다. 이 값을 Web ACL 전체 기본값으로 둘 수도 있고, 규칙 하나에만 다르게 줄 수도 있다.

Web ACL 레벨 기본값:

```json
{
  "Name": "my-web-acl",
  "DefaultAction": { "Allow": {} },
  "CaptchaConfig": {
    "ImmunityTimeProperty": { "ImmunityTime": 600 }
  },
  "ChallengeConfig": {
    "ImmunityTimeProperty": { "ImmunityTime": 300 }
  }
}
```

규칙 단위로 덮어쓰는 경우. 결제 같은 민감한 경로만 면제 시간을 짧게 줘서 토큰을 자주 갱신하게 만든다.

```json
{
  "Name": "CaptchaOnCheckout",
  "Priority": 20,
  "Statement": {
    "ByteMatchStatement": {
      "SearchString": "/checkout",
      "FieldToMatch": { "UriPath": {} },
      "TextTransformations": [{ "Priority": 0, "Type": "NONE" }],
      "PositionalConstraint": "STARTS_WITH"
    }
  },
  "Action": { "Captcha": {} },
  "CaptchaConfig": {
    "ImmunityTimeProperty": { "ImmunityTime": 60 }
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "CaptchaOnCheckout"
  }
}
```

면제 시간을 길게 잡으면 사용자 마찰은 줄지만 한 번 푼 토큰을 들고 다니는 시간이 길어져 토큰 탈취 시 악용 창이 커진다. 짧게 잡으면 보안은 올라가는데 정상 사용자가 페이지를 옮길 때마다 퍼즐을 만나 이탈한다. 로그인·결제는 60~120초, 일반 페이지는 기본 300초 정도로 차등을 두는 편이 무난하다.

### 토큰 도메인(TokenDomains)

토큰은 `aws-waf-token` 쿠키에 담겨 발급된다. 쿠키는 기본적으로 토큰을 발급한 정확한 호스트에서만 유효하다. 문제는 서비스가 `www.example.com`과 `api.example.com`처럼 서브도메인으로 갈리는 경우다. 사용자가 `www`에서 Challenge를 풀어 토큰을 받아도 `api`로 요청을 보내면 쿠키가 안 실려 다시 막힌다.

Web ACL의 `TokenDomains`에 상위 도메인을 넣으면 그 도메인과 모든 서브도메인이 같은 토큰을 공유한다.

```bash
aws wafv2 update-web-acl \
  --name my-web-acl \
  --scope CLOUDFRONT \
  --id 0123abcd-... \
  --lock-token <lock-token> \
  --default-action Allow={} \
  --token-domains example.com \
  --visibility-config ... \
  --rules ...
```

`example.com`을 넣으면 `www.example.com`, `api.example.com`, `app.example.com`이 모두 토큰을 공유한다. SPA가 `www`에서 로드된 뒤 `api`로 `fetch`를 날리는 구조라면 이 설정 없이는 API 호출이 전부 CAPTCHA 응답을 받는다. 토큰이 안 실리는 오탐의 상당수가 이 도메인 불일치다.

주의할 점은 `update-web-acl`이 전체 설정을 덮어쓴다는 것이다. `--token-domains`만 바꾸려 해도 기존 `--rules`와 `--default-action`을 전부 다시 넘겨야 한다. 빼먹으면 규칙이 통째로 날아간다. 콘솔에서 바꾸거나, `get-web-acl`로 현재 설정을 받아 토큰 도메인만 끼워 다시 넣는 방식으로 작업해야 안전하다. `lock-token`은 동시 수정 충돌을 막는 값이라 `get-web-acl`이 준 최신 값을 그대로 넘긴다.

## 내가 만든 규칙으로 라벨 체이닝

Bot Control 문서의 라벨 체이닝은 매니지드 룰 그룹이 자동으로 다는 `awswaf:managed:...` 라벨을 받는 구조였다. 내 커스텀 규칙도 똑같이 라벨을 달 수 있다. 앞 규칙이 조건을 만족하면 라벨만 붙이고 통과시키고, 뒤 규칙이 그 라벨을 `LabelMatchStatement`로 읽어 최종 액션을 결정한다.

언제 쓰냐면, 한 요청에 대해 여러 조건을 조합해서 판단하고 싶을 때다. WAF 규칙 하나의 Statement는 AND/OR/NOT으로 묶을 수 있지만, 조건이 많아지면 한 규칙 안에서 가독성이 떨어지고 재사용이 안 된다. "특정 경로 + 특정 국가 외 + 비로그인"을 라벨 여러 개로 쪼개 달고, 마지막에 라벨 조합으로 차단하면 각 조건을 독립적으로 켜고 끌 수 있다.

규칙에 라벨을 다는 건 `RuleLabels` 필드다. 액션은 라벨만 달고 흘려보내야 하므로 보통 이 단계 규칙의 액션은 평가를 계속하도록 둔다. 라벨을 다는 규칙은 매칭돼도 요청을 끝내지 않고 다음 규칙으로 넘긴다(Block/Allow 같은 종료 액션을 주지 않는 한).

```json
[
  {
    "Name": "TagAdminPath",
    "Priority": 10,
    "Statement": {
      "ByteMatchStatement": {
        "SearchString": "/admin",
        "FieldToMatch": { "UriPath": {} },
        "TextTransformations": [{ "Priority": 0, "Type": "LOWERCASE" }],
        "PositionalConstraint": "STARTS_WITH"
      }
    },
    "Action": { "Count": {} },
    "RuleLabels": [{ "Name": "path:admin" }],
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "TagAdminPath"
    }
  },
  {
    "Name": "TagForeignIp",
    "Priority": 11,
    "Statement": {
      "NotStatement": {
        "Statement": {
          "GeoMatchStatement": { "CountryCodes": ["KR"] }
        }
      }
    },
    "Action": { "Count": {} },
    "RuleLabels": [{ "Name": "geo:foreign" }],
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "TagForeignIp"
    }
  },
  {
    "Name": "BlockForeignAdmin",
    "Priority": 12,
    "Statement": {
      "AndStatement": {
        "Statements": [
          { "LabelMatchStatement": { "Scope": "LABEL", "Key": "path:admin" } },
          { "LabelMatchStatement": { "Scope": "LABEL", "Key": "geo:foreign" } }
        ]
      }
    },
    "Action": { "Block": {} },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "BlockForeignAdmin"
    }
  }
]
```

여기서 막히기 쉬운 부분이 두 가지다.

첫째, 우선순위 순서다. 라벨은 그 라벨을 단 규칙이 실행된 뒤에야 매칭 대상이 된다. `BlockForeignAdmin`(Priority 12)이 `TagAdminPath`(10)·`TagForeignIp`(11)보다 뒤에 있어야 한다. 라벨 매칭 규칙을 앞에 두면 아직 아무도 라벨을 안 단 상태라 항상 매칭에 실패한다. 차단이 안 될 때 우선순위 숫자부터 확인한다.

둘째, 커스텀 라벨 이름이다. 매니지드 라벨은 `awswaf:managed:` 접두사가 붙지만 내가 `RuleLabels`에 넣는 라벨은 접두사 없이 내가 쓴 문자열 그대로다. `path:admin`으로 달았으면 `LabelMatchStatement`의 `Key`도 정확히 `path:admin`이다. `Scope`는 라벨 전체 이름을 매칭할 때 `LABEL`, 네임스페이스 접두사로 매칭할 때 `NAMESPACE`다. 라벨이 실제로 어떤 문자열로 붙었는지는 콘솔 Sampled Requests의 Labels 칸에서 그대로 복사하는 게 가장 확실하다. 손으로 추측해서 쓰면 조용히 매칭이 안 된다.

## JSON 본문 검사 (GraphQL·REST)

기본 문자열·정규식 매칭은 본문을 통째로 평문 취급한다. GraphQL이나 JSON REST API는 본문이 구조화돼 있어서, "본문 전체"가 아니라 "특정 필드 값"만 검사하고 싶을 때가 많다. 예를 들어 GraphQL은 모든 요청이 `POST /graphql`로 오고 본문의 `query` 필드 안에 실제 쿼리가 들어간다. 본문 전체를 평문으로 SQLi 검사하면 정상 GraphQL 스키마 문자열이 패턴에 걸려 오탐이 난다.

`JsonBody`를 `FieldToMatch`로 쓰면 WAF가 본문을 JSON으로 파싱하고 지정한 경로만 검사한다.

```json
{
  "Name": "SqliOnGraphqlVariables",
  "Priority": 30,
  "Statement": {
    "SqliMatchStatement": {
      "FieldToMatch": {
        "JsonBody": {
          "MatchPattern": {
            "IncludedPaths": ["/variables/id", "/variables/email"]
          },
          "MatchScope": "VALUE",
          "InvalidFallbackBehavior": "EVALUATE_AS_STRING",
          "OversizeHandling": "CONTINUE"
        }
      },
      "TextTransformations": [{ "Priority": 0, "Type": "URL_DECODE" }]
    }
  },
  "Action": { "Block": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "SqliOnGraphqlVariables"
  }
}
```

각 필드의 의미를 짚어둔다.

- `MatchPattern`: 검사 범위. `{"All": {}}`이면 본문 전체를 JSON으로 보고 모든 키/값을 검사한다. `IncludedPaths`에 JSON 포인터 경로 배열을 넣으면 그 경로만 본다. 위 예는 `variables` 객체의 `id`와 `email` 값만 검사한다. GraphQL이면 `/query`만 잘라서 보거나, REST면 `/user/email`처럼 구체 경로를 지정한다.
- `MatchScope`: `KEY`는 JSON 키 이름을, `VALUE`는 값을, `ALL`은 둘 다 검사한다. SQLi는 보통 값에 들어오므로 `VALUE`가 맞다. 키 이름까지 검사하면 정상 필드명이 걸릴 수 있다.
- `InvalidFallbackBehavior`: 본문이 깨진 JSON일 때 처리. `MATCH`는 매칭으로 간주(차단 규칙이면 차단), `NO_MATCH`는 통과, `EVALUATE_AS_STRING`은 파싱 실패해도 평문 문자열로라도 검사한다. JSON 파싱을 우회하려고 일부러 깨진 JSON을 보내는 공격을 막으려면 `MATCH`나 `EVALUATE_AS_STRING`을 쓴다. `NO_MATCH`로 두면 깨진 JSON이 검사를 통째로 빠져나간다.

### OversizeHandling과 본문 크기 한계

`OversizeHandling`은 본문이 WAF 검사 한계를 넘었을 때 어떻게 할지다. 이게 함정이 많다.

WAF가 검사하는 본문 크기에는 상한이 있다. 기본값은 CloudFront 16KB, ALB·API Gateway·App Runner는 8KB다. 이 한계를 넘는 본문은 넘은 부분이 검사되지 않는다. `OversizeHandling`은 이 초과 상황의 처리를 강제로 지정하게 만든다.

- `CONTINUE`: 한계까지만 검사하고 계속 진행. 초과분은 검사 안 함.
- `MATCH`: 초과하면 매칭으로 간주.
- `NO_MATCH`: 초과해도 매칭 아님으로 간주.

`OversizeHandling`은 본문(Body)이나 JSON 본문을 `FieldToMatch`로 쓸 때 필수 필드다. 안 넣으면 규칙 생성이 거부된다. 큰 파일 업로드나 큰 GraphQL 배치 쿼리가 들어오는 API에서 `CONTINUE`로 두면, 공격 페이로드를 16KB 뒤쪽에 숨겨 보내는 우회가 가능하다. 반대로 `MATCH`로 두면 정상적인 큰 본문이 전부 걸린다. 정상 본문이 한계를 넘는다면 검사 한계 자체를 올려야 한다.

검사 한계는 `AssociationConfig`로 키운다. CloudFront는 최대 64KB까지 올릴 수 있고, 올린 만큼 WCU와 요청당 비용이 늘어난다.

```json
{
  "AssociationConfig": {
    "RequestBody": {
      "CLOUDFRONT": { "DefaultSizeInspectionLimit": "KB_64" }
    }
  }
}
```

`KB_16`, `KB_32`, `KB_48`, `KB_64` 중에서 고른다. 본문 검사가 안 먹는다는 신고가 들어오면 거의 이 한계를 넘는 본문이거나 `OversizeHandling`을 `NO_MATCH`로 둔 경우다. 로그의 `requestBodySize`와 `nonTerminatingMatchingRules`를 보면 본문이 잘려 검사됐는지 확인된다.

## ATP 로그인 페이로드 보호

ATP(`AWSManagedRulesATPRuleSet`) 룰 그룹 자체와 라벨 체이닝은 [WAF_Bot_Control.md](WAF_Bot_Control.md)에서 다뤘다. 여기서는 ATP가 동작하려면 반드시 맞춰야 하는 페이로드 매핑만 본다. 이 매핑이 틀리면 ATP가 켜져도 아무것도 학습하지 못한다.

ATP는 로그인 엔드포인트 경로, 요청 본문의 username/password 위치, 그리고 응답이 로그인 성공인지 실패인지를 알아야 한다. 이 세 가지를 `ManagedRuleGroupConfigs`로 넘긴다.

```json
{
  "Name": "ATP",
  "Priority": 40,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesATPRuleSet",
      "ManagedRuleGroupConfigs": [
        {
          "AWSManagedRulesATPRuleSet": {
            "LoginPath": "/api/login",
            "RequestInspection": {
              "PayloadType": "JSON",
              "UsernameField": { "Identifier": "/user/email" },
              "PasswordField": { "Identifier": "/user/password" }
            },
            "ResponseInspection": {
              "StatusCode": {
                "SuccessCodes": [200],
                "FailureCodes": [401, 403]
              }
            }
          }
        }
      ]
    }
  },
  "OverrideAction": { "Count": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "ATP"
  }
}
```

`PayloadType`이 `JSON`이면 `Identifier`는 JSON 포인터(`/user/email`)다. 폼 인코딩 로그인이면 `PayloadType`을 `FORM_ENCODED`로 바꾸고 `Identifier`에 폼 필드명(`email`)을 쓴다. 이 경로가 실제 본문 구조와 한 글자라도 다르면 ATP는 username/password를 못 찾아 자격증명 분석을 못 한다. 라벨이 하나도 안 붙으면 이 매핑부터 의심한다.

`ResponseInspection`이 ATP의 핵심이다. 같은 IP가 로그인을 반복하는데 계속 실패한다면 크리덴셜 스터핑이고, 가끔 성공이 섞이면 자격증명이 실제로 유효하다는 신호다. ATP는 이 성공/실패 비율로 공격을 판별한다. 그래서 응답 판별을 거꾸로 설정하면 ATP가 정상 로그인(200)을 실패로 보고, 실패 로그인을 성공으로 학습한다. 결과적으로 정상 사용자를 공격자로 분류한다. `StatusCode` 외에 응답 본문 문자열(`BodyContains`)이나 헤더, 헤더 존재 여부로도 판별할 수 있는데, 상태 코드가 가장 단순하고 안전하다. SPA처럼 로그인 실패도 200으로 내려주는 API라면 상태 코드로는 구분이 안 되니 본문 문자열로 판별해야 한다.

`ResponseInspection`은 CloudFront, ALB에 연결된 Web ACL에서만 동작한다. 응답을 봐야 하기 때문이다. 응답 검사 자체도 요청당 추가 비용이 붙는다.

## Firewall Manager로 다계정 일괄 배포

계정이 여러 개고 ALB·CloudFront가 수십 개로 늘어나면, Web ACL을 리소스마다 손으로 만들고 연결하는 게 불가능해진다. 새 ALB가 생길 때마다 누군가 WAF 연결을 깜빡하면 그 ALB는 무방비다. Firewall Manager는 조직(AWS Organizations) 단위로 정책을 정의하고, 조건에 맞는 리소스에 Web ACL을 자동으로 만들어 붙인다. 새로 생기는 리소스에도 자동 적용된다.

전제 조건이 있다. AWS Organizations가 켜져 있어야 하고, Firewall Manager 관리자 계정을 지정해야 하며, 모든 멤버 계정에 AWS Config가 켜져 있어야 한다. Config가 리소스 변경을 감지해야 정책이 새 리소스에 적용되기 때문이다.

정책은 `fms put-policy`로 만든다. 핵심은 `SecurityServicePolicyData`의 `ManagedServiceData`에 Web ACL 규칙을 JSON 문자열로 박는 것이다.

```bash
aws fms put-policy --policy '{
  "PolicyName": "org-waf-baseline",
  "SecurityServicePolicyData": {
    "Type": "WAFV2",
    "ManagedServiceData": "{\"type\":\"WAFV2\",\"defaultAction\":{\"type\":\"ALLOW\"},\"preProcessRuleGroups\":[{\"managedRuleGroupIdentifier\":{\"vendorName\":\"AWS\",\"managedRuleGroupName\":\"AWSManagedRulesCommonRuleSet\"},\"overrideAction\":{\"type\":\"NONE\"},\"ruleGroupType\":\"ManagedRuleGroup\",\"excludeRules\":[]}],\"postProcessRuleGroups\":[],\"overrideCustomerWebACLAssociation\":false}"
  },
  "ResourceType": "AWS::ElasticLoadBalancingV2::LoadBalancer",
  "ResourceTypeList": [
    "AWS::ElasticLoadBalancingV2::LoadBalancer",
    "AWS::ApiGatewayV2::Api"
  ],
  "ExcludeResourceTags": false,
  "RemediationEnabled": true,
  "IncludeMap": {
    "ORGUNIT": ["ou-xxxx-1a2b3c4d"]
  }
}'
```

읽어둘 필드.

- `preProcessRuleGroups` / `postProcessRuleGroups`: 계정 소유자가 직접 추가한 규칙 기준으로 앞/뒤에 들어가는 규칙 그룹이다. Firewall Manager가 깐 베이스라인 규칙과 각 팀이 추가한 규칙이 한 Web ACL에 공존하게 만든다.
- `overrideCustomerWebACLAssociation`: `false`면 멤버 계정이 이미 다른 Web ACL을 연결해 둔 리소스는 건드리지 않는다. `true`면 강제로 이 정책의 Web ACL로 덮어쓴다. 처음에는 `false`로 시작해 충돌을 확인하고 넘어간다.
- `RemediationEnabled`: `true`여야 조건에 맞는 리소스에 자동으로 Web ACL을 만들고 붙인다. `false`면 위반만 보고하고 적용은 안 한다. 처음 도입할 때 `false`로 두고 영향 범위(어떤 리소스가 대상인지)를 본 다음 `true`로 켜는 순서가 안전하다.
- `IncludeMap` / `ExcludeMap`: 정책을 적용할 계정이나 OU를 지정한다. `ORGUNIT` 키에 OU ID를, `ACCOUNT` 키에 계정 ID 배열을 넣는다.

함정은 `ManagedServiceData`가 JSON을 다시 문자열로 escape한 중첩 JSON이라는 점이다. 따옴표 escape를 틀리기 쉬워서, JSON 객체로 따로 작성하고 변환해서 넣는 편이 낫다. 그리고 Firewall Manager가 만든 Web ACL은 멤버 계정에서 직접 수정하면 안 된다. Firewall Manager가 주기적으로 정책 상태로 되돌려(remediate) 손댄 변경이 사라진다. 멤버 계정에서 규칙을 추가하려면 Firewall Manager가 자기 규칙을 pre/post 중 어디에 넣는지 알고, 그 반대편에 추가해야 충돌하지 않는다.

## False Positive 디버깅 — 누가 막았는지 추적

정상 요청이 막혔다는 신고가 들어왔을 때 순서가 있다. 어떤 규칙이 막았는지 특정하고, 그 규칙만 일단 Count로 떨어뜨려 영향을 멈추고, 로그로 원인을 확정한 다음, 룰을 좁히거나 예외를 넣는다. 한 번에 전체 규칙을 끄거나 Web ACL을 떼면 안 된다.

### 1단계: SampledRequests로 매칭 규칙 찾기

콘솔 Sampled Requests나 `get-sampled-requests`로 최근 3시간 동안 검사된 요청 샘플을 받는다. 각 샘플에 어떤 규칙이 매칭됐는지(`ruleNameWithinRuleGroup` 또는 매칭 규칙 이름)와 붙은 라벨이 그대로 나온다. 막혔다고 신고된 요청의 특징(URI, IP, User-Agent)으로 샘플을 찾아 어떤 규칙에 걸렸는지 확인한다.

```bash
aws wafv2 get-sampled-requests \
  --web-acl-arn arn:aws:wafv2:us-east-1:111122223333:global/webacl/my-web-acl/0123abcd-... \
  --rule-metric-name CommonRuleSet \
  --scope CLOUDFRONT \
  --time-window StartTime=2026-06-21T00:00:00Z,EndTime=2026-06-21T03:00:00Z \
  --max-items 100
```

대부분의 오탐은 매니지드 룰 그룹 안의 특정 규칙 하나가 범인이다. Core Rule Set의 `SizeRestrictions_BODY`나 `CrossSiteScripting_BODY`가 정상 요청을 잡는 경우가 흔하다.

### 2단계: 그 규칙만 Count로 전환

범인을 특정했으면 룰 그룹 전체가 아니라 그 규칙 하나만 Count로 바꾼다. 매니지드 룰 그룹에서 개별 규칙의 액션을 덮어쓰는 건 `RuleActionOverrides`다.

```json
{
  "Name": "CommonRuleSet",
  "Priority": 1,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesCommonRuleSet",
      "RuleActionOverrides": [
        { "Name": "SizeRestrictions_BODY", "ActionToUse": { "Count": {} } }
      ]
    }
  },
  "OverrideAction": { "None": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "CommonRuleSet"
  }
}
```

예전 API에는 `ExcludedRules`라는 필드가 있었다. `ExcludedRules`에 규칙 이름을 넣으면 그 규칙이 Count로 바뀐다. 동작은 비슷하지만 `RuleActionOverrides`가 후속 필드고 Count 말고 Challenge·CAPTCHA 등 다른 액션으로도 덮어쓸 수 있어 더 쓸 일이 많다. 새로 짤 때는 `RuleActionOverrides`를 쓴다.

룰 그룹 레벨의 `OverrideAction`을 `Count`로 두는 것과 헷갈리면 안 된다. `OverrideAction: Count`는 룰 그룹 안의 모든 규칙을 통째로 Count로 만든다. 오탐 디버깅에서 원하는 건 문제 규칙 하나만 Count로 빼는 것이므로 `OverrideAction`은 `None`으로 두고 `RuleActionOverrides`로 한 규칙만 지정한다.

### 3단계: 로그의 terminatingRuleId로 확정

WAF 로그(S3·CloudWatch Logs·Firehose)에는 요청별로 어떤 규칙이 최종 처리했는지가 남는다. 핵심 필드가 `terminatingRuleId`다. 요청을 Block 또는 Allow로 끝낸 규칙의 ID가 들어간다. 매니지드 룰 그룹이 막았으면 그룹 이름이 찍히고, `terminatingRuleMatchDetails`에 그룹 안의 어떤 규칙이 어느 필드에서 매칭됐는지 들어간다.

CloudWatch Logs Insights로 막힌 요청을 추리는 쿼리:

```sql
fields @timestamp, terminatingRuleId, action, httpRequest.uri, httpRequest.clientIp
| filter action = "BLOCK"
| stats count() as blocked by terminatingRuleId, httpRequest.uri
| sort blocked desc
| limit 20
```

`terminatingRuleId`가 `Default_Action`으로 찍히면 어떤 규칙도 매칭 안 됐는데 Default Action이 Block이라 막힌 것이고, 특정 규칙 이름이 찍히면 그 규칙이 범인이다. 매니지드 룰 그룹 이름이 찍혔다면 같은 로그의 `ruleGroupList` 안에서 실제 매칭된 하위 규칙(`terminatingRule`)을 본다. 여기까지 보면 어떤 필드의 어떤 값 때문에 걸렸는지 나오므로, 룰을 통째로 끄는 대신 `ScopeDownStatement`로 그 경로만 검사에서 빼거나 `RuleActionOverrides`를 유지할지 판단할 수 있다.

확정 후에는 Count로 며칠 더 돌려 정말 정상 트래픽만 걸리는지 본다. 정상만 걸린다면 예외(Scope-down)나 영구 Override를 적용하고, 공격이 섞여 있으면 룰은 살리고 정상 트래픽 쪽을 화이트리스트로 빼는 방향으로 간다. CloudWatch에서 해당 규칙의 `CountedRequests`가 정상 사용량과 맞아떨어지는지 확인하는 게 마지막 점검이다.

## 참고

- JSON 본문 검사: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-fields-list.html
- 본문 검사 크기 한계와 OversizeHandling: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-statement-request-component-body.html
- 라벨과 규칙 체이닝: https://docs.aws.amazon.com/waf/latest/developerguide/waf-rule-label-match.html
- ATP 룰 그룹: https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html
- Firewall Manager WAF 정책: https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html
- WAF 로그 필드: https://docs.aws.amazon.com/waf/latest/developerguide/logging-fields.html
