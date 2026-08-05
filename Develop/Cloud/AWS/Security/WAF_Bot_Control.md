---
title: AWS WAF Bot Control과 봇 방어
tags: [aws, waf, bot-control, captcha, atp, rate-limit, scraping, credential-stuffing, security]
updated: 2026-06-19
---

# AWS WAF Bot Control과 봇 방어

기본 Web ACL 생성, SQLi/XSS, IP 차단 같은 내용은 [WAF.md](WAF.md)에 정리되어 있다. 이 문서는 거기서 다루지 않는 봇 방어만 따로 정리한다. Bot Control 매니지드 룰 그룹, CAPTCHA/Challenge 액션, ATP, Rate-based 규칙과 라벨 체이닝, 그리고 정상 봇을 오탐 없이 통과시키는 운영 작업이 대상이다.

## SQLi/XSS 룰로는 봇을 못 막는 이유

WAF.md의 Core Rule Set이나 SqliMatchStatement는 요청 한 건의 페이로드를 검사한다. 그런데 봇 공격은 페이로드가 정상이다. 크리덴셜 스터핑은 진짜 로그인 폼에 진짜 형식의 아이디/비밀번호를 보낸다. 스크래핑은 `GET /products?page=1` 같은 평범한 요청을 페이지 번호만 바꿔가며 수만 번 보낸다. 페이로드 한 건만 보면 정상 사용자와 구분이 안 된다.

봇은 행위 패턴으로 잡아야 한다. 같은 IP가 1초에 50번 로그인을 시도하는가, User-Agent가 헤드리스 브라우저인가, JavaScript를 실행하는가, 마우스 움직임이 있는가. 이 판단을 WAF에서 하려면 Bot Control 매니지드 룰 그룹이나 CAPTCHA/Challenge 토큰 검증이 필요하다.

## Bot Control 매니지드 룰 그룹

룰 그룹 이름은 `AWSManagedRulesBotControlRuleSet` 하나다. 안에서 Common과 Targeted 두 단계(inspection level)를 고른다.

### Common

User-Agent, 알려진 봇 IP 목록, 요청 헤더 정합성 같은 정적 시그널로 판단한다. 검색엔진 크롤러, 모니터링 서비스, 스크래퍼, 소셜 미디어 봇처럼 자기 정체를 숨기지 않는 봇을 분류한다. 추가 인프라 없이 룰만 켜면 된다.

```json
{
  "Name": "BotControl",
  "Priority": 5,
  "Statement": {
    "ManagedRuleGroupStatement": {
      "VendorName": "AWS",
      "Name": "AWSManagedRulesBotControlRuleSet",
      "ManagedRuleGroupConfigs": [
        {
          "AWSManagedRulesBotControlRuleSet": {
            "InspectionLevel": "COMMON"
          }
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
    "MetricName": "BotControl"
  }
}
```

### Targeted

`InspectionLevel`을 `TARGETED`로 올리면 정체를 숨기는 봇까지 잡는다. 동작 방식이 Common과 완전히 다르다. 클라이언트에 Challenge나 CAPTCHA 토큰을 심고, 그 토큰을 검증해서 진짜 브라우저인지 판별한다. 헤드리스 브라우저 탐지(`TGT_ML_CoordinatedActivityMedium` 같은 머신러닝 시그널), 토큰 재사용 탐지, 세션 단위 행위 분석이 들어간다.

Targeted를 켜면 토큰 발급/검증을 위해 응답에 자동으로 Challenge가 삽입되거나, JS SDK를 직접 붙여야 하는 룰이 생긴다. SDK 없이 켜면 토큰이 없는 요청이 전부 의심 라벨을 받아 오탐이 폭증한다. SDK는 아래에서 따로 다룬다.

Common과 Targeted는 비용 차이가 크다. 처음에는 Common만 켜서 정상 봇 분류가 어떻게 되는지 보고, 자동화 공격이 실제로 들어올 때 Targeted를 올리는 순서가 맞다.

## 라벨과 규칙 체이닝

Bot Control의 핵심은 룰 그룹이 직접 차단하지 않고 라벨(label)만 붙인다는 점이다. `OverrideAction`을 `None`이 아니라 `Count`로 두면 룰 그룹 안의 모든 규칙이 라벨만 달고 통과시킨다. 그 라벨을 뒤따르는 별도 규칙이 읽어서 Block이든 CAPTCHA든 결정한다. 이 구조 덕분에 "검색엔진 봇은 통과, 스크래퍼는 차단" 같은 세밀한 분기가 가능하다.

Bot Control이 다는 주요 라벨:

- `awswaf:managed:aws:bot-control:bot:category:search_engine` — 검색엔진 크롤러
- `awswaf:managed:aws:bot-control:bot:category:monitoring` — 가동 모니터링 봇
- `awswaf:managed:aws:bot-control:bot:category:scraping_framework` — 스크래핑 프레임워크
- `awswaf:managed:aws:bot-control:bot:verified` — 정체가 검증된 봇(역방향 DNS 확인 통과)
- `awswaf:managed:aws:bot-control:signal:non_browser_user_agent` — 브라우저가 아닌 UA
- `awswaf:managed:aws:bot-control:targeted:aggregate:volumetric:session:high` — 세션 단위 고볼륨

체이닝 예시. 룰 그룹은 Count로 두고 라벨만 받은 다음, 검증된 검색엔진은 명시적으로 허용하고 나머지 봇 시그널은 차단한다. 우선순위 숫자가 작을수록 먼저 실행되므로 룰 그룹이 라벨을 단 뒤에 라벨 매칭 규칙이 와야 한다.

```json
[
  {
    "Name": "BotControl",
    "Priority": 5,
    "Statement": {
      "ManagedRuleGroupStatement": {
        "VendorName": "AWS",
        "Name": "AWSManagedRulesBotControlRuleSet",
        "ManagedRuleGroupConfigs": [
          { "AWSManagedRulesBotControlRuleSet": { "InspectionLevel": "COMMON" } }
        ]
      }
    },
    "OverrideAction": { "Count": {} },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "BotControl"
    }
  },
  {
    "Name": "AllowVerifiedSearchEngine",
    "Priority": 6,
    "Statement": {
      "LabelMatchStatement": {
        "Scope": "LABEL",
        "Key": "awswaf:managed:aws:bot-control:bot:category:search_engine"
      }
    },
    "Action": { "Allow": {} },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "AllowVerifiedSearchEngine"
    }
  },
  {
    "Name": "BlockScrapers",
    "Priority": 7,
    "Statement": {
      "LabelMatchStatement": {
        "Scope": "LABEL",
        "Key": "awswaf:managed:aws:bot-control:bot:category:scraping_framework"
      }
    },
    "Action": { "Block": {} },
    "VisibilityConfig": {
      "SampledRequestsEnabled": true,
      "CloudWatchMetricsEnabled": true,
      "MetricName": "BlockScrapers"
    }
  }
]
```

`LabelMatchStatement`의 `Scope`는 `LABEL`이고 `Key`는 콜론으로 연결된 전체 네임스페이스다. 라벨 이름을 한 글자라도 틀리면 매칭이 조용히 실패한다. 차단이 안 될 때 가장 먼저 의심할 부분이 이 오타다. Sampled Requests에서 실제로 어떤 라벨이 붙었는지 확인하고 복사해서 쓰는 편이 안전하다.

검색엔진 봇을 허용 라벨로 빼는 게 중요한 이유가 있다. `search_engine` 카테고리는 단순히 UA가 Googlebot이라서 붙는 게 아니라, 역방향 DNS 조회로 정체가 검증된 경우에만 붙는다. UA만 Googlebot으로 위조한 스크래퍼는 이 라벨을 못 받는다. 그래서 라벨 기반 허용이 UA 문자열 매칭보다 안전하다.

## Rate-based 규칙과 라벨 결합

크리덴셜 스터핑과 스크래핑은 볼륨이 시그널이다. Rate-based 규칙으로 임계치를 잡는다. WAF.md의 단순 IP 기반 Rate Limit과 달리, 봇 방어에서는 집계 키와 스코프를 좁혀야 한다.

로그인 엔드포인트에만 적용하면서 IP로 집계하는 규칙. `ScopeDownStatement`로 `/api/login`만 카운트 대상으로 좁힌다. 사이트 전체 트래픽으로 임계치를 잡으면 로그인 폭주를 못 잡는다.

```json
{
  "Name": "LoginRateLimit",
  "Priority": 10,
  "Statement": {
    "RateBasedStatement": {
      "Limit": 100,
      "EvaluationWindowSec": 60,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "ByteMatchStatement": {
          "SearchString": "/api/login",
          "FieldToMatch": { "UriPath": {} },
          "PositionalConstraint": "STARTS_WITH",
          "TextTransformations": [ { "Priority": 0, "Type": "NONE" } ]
        }
      }
    }
  },
  "Action": { "Block": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "LoginRateLimit"
  }
}
```

`EvaluationWindowSec`는 60/120/300/600 중에서 고른다. 예전에는 5분 고정이었는데 지금은 1분까지 내릴 수 있다. 로그인 무차별 대입은 짧은 창이 잡기 좋다. `Limit`은 1분 창 기준 100이면 정상 사용자가 1분에 로그인을 100번 할 일은 없으니 충분히 여유가 있고, 봇은 금방 넘긴다.

IP 집계는 한계가 있다. 공격자가 수천 개 IP를 돌리면 IP당 횟수가 임계치 아래로 깔린다. 이때는 집계 키를 IP가 아닌 다른 값으로 바꾼다. 헤더나 쿠키, 혹은 라벨로 집계할 수 있다. 예를 들어 로그인 폼에 보내는 username을 키로 잡으면, 한 계정에 대한 분산 공격을 IP와 무관하게 잡는다.

```json
{
  "RateBasedStatement": {
    "Limit": 50,
    "EvaluationWindowSec": 300,
    "AggregateKeyType": "CUSTOM_KEYS",
    "CustomKeys": [
      {
        "Header": {
          "Name": "x-username",
          "TextTransformations": [ { "Priority": 0, "Type": "LOWERCASE" } ]
        }
      }
    ],
    "ScopeDownStatement": {
      "ByteMatchStatement": {
        "SearchString": "/api/login",
        "FieldToMatch": { "UriPath": {} },
        "PositionalConstraint": "STARTS_WITH",
        "TextTransformations": [ { "Priority": 0, "Type": "NONE" } ]
      }
    }
  }
}
```

`CustomKeys`에는 IP와 헤더를 같이 넣어 조합 키로도 만들 수 있다. 키를 여러 개 넣으면 그 조합 단위로 카운트한다.

라벨과 결합하면 더 좁힐 수 있다. Bot Control이 단 `non_browser_user_agent` 라벨이 붙은 요청만 Rate 집계 대상으로 넣으면, 정상 브라우저 사용자는 임계치 계산에서 아예 빠진다. `ScopeDownStatement` 안에 `LabelMatchStatement`를 넣으면 된다. 정상 트래픽이 카운트에서 빠지니 임계치를 훨씬 공격적으로 낮춰도 오탐이 안 난다.

## CAPTCHA와 Challenge 액션

Block은 봇과 사람을 모두 막는다. 의심스럽지만 확신이 없을 때는 CAPTCHA나 Challenge로 사람만 통과시킨다. 둘 다 액션 타입이고 Block 자리에 넣는다.

- **Challenge**: 백그라운드에서 자바스크립트 연산 퍼즐(proof of work)을 풀게 한다. 사용자 화면에는 잠깐 지연만 생기고 보이는 입력은 없다. 진짜 브라우저면 JS를 실행해 토큰을 받고 통과한다. 봇이 JS 엔진이 없으면 막힌다.
- **CAPTCHA**: 사용자에게 퍼즐 화면을 띄운다. 사람이 풀어야 토큰을 받는다. 마찰이 크므로 정말 의심스러운 트래픽에만 쓴다.

```json
{
  "Name": "ChallengeSuspiciousBots",
  "Priority": 8,
  "Statement": {
    "LabelMatchStatement": {
      "Scope": "LABEL",
      "Key": "awswaf:managed:aws:bot-control:signal:non_browser_user_agent"
    }
  },
  "Action": {
    "Challenge": {}
  },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "ChallengeSuspiciousBots"
  }
}
```

한 번 토큰을 받으면 토큰 유효시간(immunity time) 동안 다시 검사하지 않는다. 기본값은 Challenge 300초, CAPTCHA 300초인데 Web ACL이나 규칙 단위로 조절한다. 너무 짧으면 같은 사용자가 계속 퍼즐을 만나고, 너무 길면 토큰 탈취 위험이 커진다.

### 토큰이 API/SPA에서 깨지는 문제

CAPTCHA/Challenge는 토큰을 쿠키(`aws-waf-token`)에 담아 응답한다. 브라우저로 직접 페이지를 받으면 쿠키가 자동으로 저장되고 다음 요청에 실린다. 그런데 SPA에서 `fetch`로 API를 부르거나 모바일 앱이 호출할 때는 이 흐름이 끊긴다. fetch가 토큰 쿠키를 안 들고 가거나, 애초에 토큰을 받을 페이지 로드 과정이 없어서 API 요청이 전부 CAPTCHA 응답(405 + 본문)을 받는다.

여기서 JS SDK가 필요하다. SDK를 페이지에 붙이면 백그라운드에서 Challenge를 풀어 토큰을 미리 확보하고, `fetch` 요청 헤더에 토큰을 자동으로 끼워준다.

```html
<script type="text/javascript"
  src="https://XXXX.cloudfront.net/challenge.js"
  defer></script>
```

SDK가 로드되면 `window.AwsWafIntegration` 객체가 생긴다. fetch를 직접 쓰는 대신 SDK가 감싼 fetch를 쓰거나, 토큰을 직접 꺼내 헤더에 넣는다.

```javascript
// SDK가 토큰을 확보할 때까지 기다린 뒤 요청
await AwsWafIntegration.getToken();

const res = await fetch('/api/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-aws-waf-token': await AwsWafIntegration.getToken()
  },
  body: JSON.stringify({ username, password })
});
```

SDK URL은 Web ACL의 Application Integration URL에서 가져온다. CloudFront 도메인 형태로 발급되며 Web ACL마다 다르다. SDK를 붙이고도 토큰이 안 실리면 SDK 도메인과 보호 대상 도메인이 달라 쿠키가 SameSite 정책에 걸리는 경우가 많다. 같은 사이트 도메인에서 서빙되도록 맞춰야 한다.

## ATP (Account Takeover Prevention)

크리덴셜 스터핑 전용 매니지드 룰 그룹이다. 이름은 `AWSManagedRulesATPRuleSet`. Rate 기반 방어가 "너무 많이 시도하는가"를 보는 반면, ATP는 "탈취된 자격증명을 쓰는가", "응답이 로그인 성공인가 실패인가"까지 본다.

ATP는 로그인 엔드포인트 경로와 요청 본문에서 username/password 필드 위치를 알려줘야 동작한다. 응답까지 보고 로그인 실패가 반복되는 패턴, 유출된 자격증명 데이터베이스와 일치하는 자격증명(stolen credentials)을 라벨로 분류한다.

```json
{
  "Name": "ATP",
  "Priority": 4,
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
              "UsernameField": { "Identifier": "/username" },
              "PasswordField": { "Identifier": "/password" }
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

`RequestInspection`의 `Identifier`는 JSON 본문일 때 JSON 포인터(`/username`)로 쓴다. 폼 인코딩이면 `PayloadType`을 `FORM_ENCODED`로 두고 필드명을 쓴다. `ResponseInspection`은 ATP가 로그인 성공/실패를 구분하는 근거다. 상태 코드 외에 본문 문자열이나 헤더로도 판별할 수 있다. 이걸 잘못 설정하면 ATP가 성공/실패를 거꾸로 학습해서 정상 로그인을 공격으로 본다.

ATP가 다는 라벨로 다시 체이닝한다.

- `awswaf:managed:aws:atp:signal:credential_compromised` — 유출된 자격증명과 일치
- `awswaf:managed:aws:atp:aggregate:volumetric:session:high` — 세션 단위 로그인 시도 과다
- `awswaf:managed:aws:atp:signal:missing_credential` — 자격증명 누락(폼 스캔)

`credential_compromised`는 막아야 하지만 바로 Block보다 비밀번호 재설정을 강제하는 쪽이 사용자 보호에 맞는 경우가 있다. 그래서 ATP도 Count로 두고 라벨을 애플리케이션이 읽어 처리하는 패턴을 많이 쓴다. WAF가 라벨을 요청 헤더로 백엔드에 전달하므로 애플리케이션 단에서 "이 로그인은 유출 자격증명이니 추가 인증" 같은 분기를 넣는다.

ATP는 Bot Control과 별개 룰 그룹이고 요금도 따로 붙는다. 둘 다 켜면 WCU와 비용이 합산된다.

## WCU와 요금

Bot Control과 ATP는 Web ACL 기본 1,500 WCU 예산을 크게 먹는다. WCU 개념 자체는 [WAF.md](WAF.md)에 있다.

- Bot Control Common: 약 50 WCU
- Bot Control Targeted: 룰 그룹 전체로 수백 WCU. Targeted를 켜면 Common 대비 훨씬 많이 쓴다.
- ATP: 수십~수백 WCU

기본 1,500 WCU 안에서 Bot Control Targeted + ATP + 기존 Core Rule Set + 커스텀 규칙을 다 넣으면 한도를 넘기 쉽다. 넘으면 Web ACL 생성/수정이 거부된다. 한도는 요청하면 상향되지만 WCU가 늘수록 요청당 처리 비용도 늘어난다.

요금(us-east-1 기준 대략):

- Web ACL $5/월, 규칙당 $1/월, 요청 100만당 $0.60 — 여기까지는 WAF.md와 동일
- Bot Control: 추가 $10/월 + Bot Control이 검사한 요청 100만당 $1.00
- ATP: 추가 $10/월 + 검사 요청 100만당 추가 과금
- Targeted 단계는 머신러닝 분석분이 요청당 비용에 더 얹힌다

요청 과금이 핵심이다. 트래픽이 많은 사이트에 Bot Control을 전체 경로에 켜면 검사 요청 100만당 $1.00이 곱해져 청구서가 빠르게 커진다. 그래서 Bot Control 룰에 `ScopeDownStatement`를 걸어 로그인/결제/검색 같은 봇 표적 경로에만 적용하는 게 일반적이다. 정적 자산(`/static`, 이미지)까지 검사하면 돈만 나가고 잡을 게 없다.

```json
{
  "ManagedRuleGroupStatement": {
    "VendorName": "AWS",
    "Name": "AWSManagedRulesBotControlRuleSet",
    "ManagedRuleGroupConfigs": [
      { "AWSManagedRulesBotControlRuleSet": { "InspectionLevel": "TARGETED" } }
    ],
    "ScopeDownStatement": {
      "OrStatement": {
        "Statements": [
          {
            "ByteMatchStatement": {
              "SearchString": "/api/login",
              "FieldToMatch": { "UriPath": {} },
              "PositionalConstraint": "STARTS_WITH",
              "TextTransformations": [ { "Priority": 0, "Type": "NONE" } ]
            }
          },
          {
            "ByteMatchStatement": {
              "SearchString": "/checkout",
              "FieldToMatch": { "UriPath": {} },
              "PositionalConstraint": "STARTS_WITH",
              "TextTransformations": [ { "Priority": 0, "Type": "NONE" } ]
            }
          }
        ]
      }
    }
  }
}
```

## 정상 봇을 오탐 없이 통과시키는 디버깅

Bot Control을 켜고 가장 많이 받는 항의가 "구글 색인이 빠졌다", "결제 모니터링 봇이 막혔다"다. 정상 봇을 차단하면 매출과 운영에 바로 영향이 간다. Block을 켜기 전에 누가 오탐될지 데이터로 봐야 한다.

### Count 모드로 먼저 본다

Bot Control 룰 그룹 전체의 `OverrideAction`을 `Count`로 두고 최소 며칠 돌린다. 차단은 한 건도 안 일어나고 라벨과 메트릭만 쌓인다. WAF.md의 Count 패턴과 같은 원리인데, 봇 방어는 정상/비정상 경계가 더 흐려서 관찰 기간을 더 길게 잡는다. 주중/주말, 배치 작업 시간대까지 한 주기는 봐야 정기 크롤러가 다 드러난다.

### Sampled Requests로 라벨을 확인한다

콘솔의 Sampled Requests는 최근 3시간 동안 검사된 요청을 최대 100건 샘플로 보여준다. 각 요청에 어떤 라벨이 붙었는지, 어떤 규칙이 매칭됐는지가 그대로 나온다. 여기서 정상 봇이 어떤 라벨을 받는지 직접 확인하고, 허용 규칙의 `LabelMatchStatement` 키를 이 화면 값에서 복사한다. 머리로 라벨 문자열을 추측해서 쓰면 거의 틀린다.

### WAF 로그로 정밀 분석한다

Sampled Requests는 샘플이라 전수가 아니다. 정확히 누가 오탐되는지 보려면 WAF 로그(로깅 설정은 WAF.md 참고)를 S3에 쌓고 Athena로 본다. Count 라벨이 붙은 요청을 IP/UA별로 집계하면 정상 봇을 골라낼 수 있다.

```sql
SELECT
  httprequest.clientip AS ip,
  httprequest.headers_user_agent AS ua,
  label.name AS label,
  COUNT(*) AS cnt
FROM waf_logs
CROSS JOIN UNNEST(labels) AS t(label)
WHERE label.name LIKE 'awswaf:managed:aws:bot-control:%'
GROUP BY httprequest.clientip, httprequest.headers_user_agent, label.name
ORDER BY cnt DESC
LIMIT 50;
```

이 결과에서 모니터링 서비스 IP나 사내 배치 서버가 `non_browser_user_agent` 같은 차단 후보 라벨을 받고 있으면, 그 IP를 IP Set에 넣어 Bot Control 앞 우선순위에서 명시적으로 Allow 처리한다. 우선순위가 앞서면 Bot Control 규칙에 도달하기 전에 통과한다.

```json
{
  "Name": "AllowKnownGoodBots",
  "Priority": 1,
  "Statement": {
    "IPSetReferenceStatement": {
      "Arn": "arn:aws:wafv2:...:ipset/known-good-bots/..."
    }
  },
  "Action": { "Allow": {} },
  "VisibilityConfig": {
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "AllowKnownGoodBots"
  }
}
```

검색엔진은 IP가 자주 바뀌므로 IP Set보다 `bot:category:search_engine` 라벨 허용이 안전하다. 반면 사내 배치나 계약된 모니터링 업체처럼 IP가 고정이고 라벨이 안 붙는 봇은 IP Set으로 빼는 게 확실하다. 둘을 섞어 쓴다.

### 단계적으로 Block을 켠다

Count로 충분히 보고 허용 규칙을 다 깔았으면 한 번에 전체를 Block하지 말고 좁은 라벨부터 Block으로 바꾼다. 예를 들어 `scraping_framework` 같은 확실한 라벨 하나만 Block하고 며칠 보고, 문제 없으면 `non_browser_user_agent`는 Challenge로, 그다음 더 의심스러운 라벨을 Block으로 넓힌다. CloudWatch의 BlockedRequests가 갑자기 튀면 정상 봇이 걸린 신호이니 직전에 바꾼 규칙을 Count로 되돌리고 로그를 다시 본다.

이 순서를 지키면 색인 누락이나 모니터링 단절 같은 사고를 차단 적용 전에 잡는다. 봇 방어는 한 번에 완성하는 게 아니라 Count → 라벨 확인 → 허용 정비 → 좁은 Block → 확대를 반복하면서 임계치와 허용 목록을 다듬는 작업이다.

## 참고

- Bot Control 룰 그룹: https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-bot.html
- ATP 룰 그룹: https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html
- CAPTCHA/Challenge와 JS SDK: https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-and-challenge.html
- WAF 요금: https://aws.amazon.com/waf/pricing/
- 기본 Web ACL/SQLi/XSS는 [WAF.md](WAF.md) 참고
