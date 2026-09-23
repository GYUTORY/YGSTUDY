---
title: Cloudflare WAF 룰 작성 실무
tags: [security, cloud, network, backend]
updated: 2026-09-23
---

# Cloudflare WAF 룰 작성 실무

Cloudflare WAF는 2022년에 Firewall Rules에서 WAF Custom Rules로 이전됐다. 인터페이스가 바뀌고 API 경로가 달라졌는데, 오래된 문서를 보고 작업하면 엉뚱한 곳을 건드리게 된다. 지금은 Security → WAF → Custom Rules 탭이 맞다.

## 표현식 언어

Cloudflare 표현식은 Wirefilter Expression Language를 쓴다. Wireshark 필터 문법과 구조가 비슷하다. 필드 + 연산자 + 값 조합이고, `and`, `or`, `not`으로 조건을 연결한다.

자주 쓰는 필드:

| 필드 | 설명 |
|---|---|
| `http.request.uri.path` | 쿼리 스트링 제외한 경로 |
| `http.request.uri` | 쿼리 스트링 포함 전체 URI |
| `http.request.method` | GET, POST 등 |
| `ip.src` | 클라이언트 IP |
| `ip.geoip.country` | ISO 국가 코드 (KR, US 등) |
| `cf.threat_score` | Cloudflare 위협 점수 0~100 |
| `http.request.headers["user-agent"]` | User-Agent 헤더 |
| `http.request.body.raw` | 요청 본문 (raw) |
| `http.host` | Host 헤더 |

기본 패턴:

```
# 특정 경로 차단
http.request.uri.path eq "/admin/wp-login.php"

# 경로 접두사 매칭
http.request.uri.path matches "^/api/v1/admin"

# 복수 IP 차단 — 값 사이는 공백으로 구분, 쉼표 쓰면 파싱 오류
ip.src in {203.0.113.1 203.0.113.2 198.51.100.0/24}

# 국가 + 경로 조합
ip.geoip.country eq "CN" and http.request.uri.path contains "/api/"

# POST 본문 검사
http.request.method eq "POST" and http.request.body.raw contains "UNION SELECT"
```

`contains`는 대소문자를 구분한다. 대소문자 무관 매칭이 필요하면 `lower()` 함수를 씌운다:

```
lower(http.request.uri.path) contains "/phpmyadmin"
```

`matches`는 RE2 정규식이다. PCRE가 아니라서 lookahead/lookbehind가 없다. 복잡한 패턴을 쓰다가 "Invalid regular expression" 오류가 나면 이 제약 때문이다.

`http.request.body.raw`는 POST 본문을 검사할 때 쓴다. Content-Type이 `application/x-www-form-urlencoded`면 파싱된 필드를 `http.request.body.form`으로도 접근할 수 있다. JSON 본문은 `http.request.body.raw`에서 문자열 검사만 가능하다. 구조적 파싱은 지원하지 않는다.

위협 점수(`cf.threat_score`)는 0에 가까울수록 안전하다. 통상적으로 10 이상이면 의심, 50 이상이면 차단 대상으로 잡는다. 점수 기준만으로 운영하면 오탐이 많다. 특정 경로나 메서드와 조합해서 써야 실용적이다.

## Rate Limiting 룰

WAF Custom Rules 탭이 아니라 Security → WAF → Rate Limiting Rules 탭에 따로 있다. 표현식 언어는 동일하지만 설정 구조가 다르다.

Rate Limiting 룰은 세 가지를 설정한다:

- 매칭 조건: 어떤 요청에 적용할지 (표현식)
- 임계값: 기간(period) 내 요청 횟수
- 동작: 초과 시 차단 또는 챌린지

```
# /api/login에 IP당 1분에 10회 초과 시 차단
조건:  http.request.uri.path eq "/api/login" and http.request.method eq "POST"
period: 60초
requests: 10
action: Block
```

기본 키는 IP 주소다. `cf.unique_visitor_id`를 키로 쓰면 NAT 뒤에 있는 여러 사용자를 같은 IP로 묶지 않을 수 있다. 단, `cf.unique_visitor_id`는 쿠키 기반이라 쿠키를 안 보내는 API 클라이언트에는 효과가 없다.

Rate Limiting 룰은 정상 트래픽도 걸린다. 배포 직후 정적 파일 CDN 요청이 폭증하거나, 모바일 앱 업데이트로 동시 접속이 몰릴 때 실수로 차단하는 경우가 있다. 처음에는 Log 모드로 설정해서 실제 분포를 본 다음 임계값을 정한다.

mitigation timeout은 차단 상태를 유지하는 시간이다. 기본값이 설정한 period와 같은데, 짧게 맞추면 공격자가 잠시 기다렸다가 재시도한다. API 무차별 대입 공격에는 timeout을 600초 이상으로 잡는다.

## Bot Fight Mode 오탐

Bot Fight Mode(BFM)와 Super Bot Fight Mode(SBFM)는 Pro/Business 플랜에서 쓸 수 있는 자동화 차단 기능이다. JS 챌린지로 브라우저 여부를 검증하는 방식이라, 브라우저가 아닌 클라이언트는 전부 봇으로 판정할 수 있다.

실제로 오탐이 나는 경우가 있다.

**내부 API 클라이언트**: 서버-서버 통신에서 `curl`, `httpx`, Python `requests` 같은 클라이언트는 JS 챌린지를 통과하지 못한다. BFM이 켜진 상태에서 내부 서비스가 Cloudflare를 거쳐 API를 호출하면 403이 난다.

**Googlebot 등 검색 크롤러**: SBFM에는 "Allow search engine crawlers" 옵션이 있다. 이걸 켜도 Googlebot을 사칭하는 봇은 막는다고 하지만, 실제 검색 크롤러가 잘못 차단되는 경우가 간헐적으로 보인다.

**모니터링 도구**: Uptime Robot, Datadog Synthetics 같은 외부 모니터링 툴이 BFM에 걸린다. 해당 IP 대역을 화이트리스트에 넣거나, 모니터링 요청에 커스텀 헤더를 달아서 Skip 룰로 우회한다.

**Cloudflare Workers**: Workers에서 `fetch()`로 같은 존의 도메인을 호출하면 BFM에 걸릴 수 있다. Workers의 outbound 요청은 내부 IP를 쓰지 않고 일반 인터넷으로 나간다.

BFM의 근본적인 한계는 Security Events에서 봇 판정 이유를 명확히 알 수 없다는 점이다. "Bot Fight Mode"가 source로 찍히는 정도가 전부다. 세밀한 제어가 필요하면 Enterprise 플랜의 Bot Management를 써야 한다. `cf.bot_management.score`(0~99) 필드가 노출되고, 점수 기반으로 커스텀 룰을 작성할 수 있다.

## Skip 룰로 화이트리스트 만들기

화이트리스트는 "Allow" 동작이 아니라 "Skip" 동작으로 구현한다. Allow는 그 요청을 통과시키는 게 아니라 WAF 매니지드 룰과 이후 검사를 건너뛰게 한다. Skip은 건너뛸 대상을 더 세밀하게 지정할 수 있다.

Skip의 대상 선택:

- All remaining custom rules
- All WAF Managed Rules
- Specific managed ruleset
- Rate Limiting Rules

특정 IP나 대역을 완전히 신뢰하려면 모든 검사를 Skip한다. 내부 네트워크 대역, CI/CD 에이전트 IP, 파트너사 IP 등이 여기 해당한다.

```
# 내부 네트워크 Skip
ip.src in {10.0.0.0/8 172.16.0.0/12 192.168.0.0/16}
→ Skip: All remaining custom rules, WAF Managed Rules
```

헤더 기반 화이트리스트는 IP가 유동적인 서비스(Lambda, Cloud Run 등)에서 쓴다. 비밀 헤더 값을 공유하고, 그 헤더가 있으면 Skip한다.

```
http.request.headers["x-internal-token"] eq "your-secret-value"
→ Skip: All remaining custom rules
```

이 헤더 값이 외부에 노출되면 WAF 전체를 우회하게 된다. Cloudflare Workers에서 헤더를 추가하거나, Origin 서버에서 이중으로 검증하는 구조가 안전하다.

## 룰 실행 순서

Security Events에서 룰은 위에서 아래로 순서대로 평가된다. 매칭된 룰의 동작이 Block이거나 Challenge면 이후 룰은 실행되지 않는다. Skip도 지정한 범위를 건너뛴 뒤 남은 룰부터 이어간다.

**Skip 룰은 반드시 Block 룰보다 앞에 있어야 한다.** 화이트리스트 IP가 Block 룰 뒤에 있으면, Block 룰이 먼저 매칭돼서 Skip 룰에 도달하지 못한다.

Phase가 다른 룰은 순서가 보장되지 않는다. Custom Rules는 `http_request_firewall_custom` 페이즈, Managed Rules는 `http_request_firewall_managed` 페이즈다. Custom Rules가 항상 Managed Rules보다 먼저 실행된다. Custom Rules의 Skip 룰이 Managed Rules 전체를 건너뛰게 할 수 있는 이유가 여기 있다.

Cloudflare 전체 처리 순서는 대략 다음과 같다:

```
IP Access Rules (방화벽)
  → WAF Custom Rules
    → Rate Limiting Rules
      → WAF Managed Rules
        → Bot Fight Mode
          → Page Rules / Workers
```

IP Access Rules에서 차단된 요청은 WAF Custom Rules에 도달하지 않는다. WAF 레이어에서 허용 룰을 만들어도, IP 레이어에서 이미 막히면 소용없다.

룰 번호는 UI에서 드래그로 바꿀 수 있고, API로도 순서를 지정할 수 있다. Terraform으로 관리할 때는 `cloudflare_ruleset` 리소스에서 룰 배열 순서가 그대로 반영된다.

## 차단 로그 분석

Security → Security Events 탭에서 실시간 로그를 본다. 기본 24시간이고 최대 72시간까지 조회할 수 있다. 더 긴 기간이 필요하면 Cloudflare Logpush로 S3나 R2에 쌓아야 한다.

각 이벤트에서 봐야 할 필드:

- **Action**: 어떤 동작이 취해졌는지 (Managed Challenge, Block, Skip 등)
- **Service**: 어떤 기능이 차단했는지 (Custom Rules, Managed Rules, BFM 등)
- **Rule ID**: 매칭된 룰 ID
- **Ray ID**: Cloudflare 레이어의 요청 고유 ID
- **Expression**: Custom Rules의 경우 매칭된 표현식

Ray ID는 `cf-ray` 응답 헤더에도 들어있다. 사용자가 차단됐다고 신고하면 Ray ID를 받아서 Security Events에서 검색하면 어떤 룰이 매칭됐는지 바로 알 수 있다.

```bash
# 응답 헤더에서 Ray ID 확인
curl -sI https://example.com/path 2>&1 | grep -i cf-ray
```

Managed Rules가 차단한 경우, Rule ID가 `100xxx` 형태로 찍힌다. Security → WAF → Managed Rules에서 해당 Rule ID를 검색하면 어떤 패턴을 감지했는지 설명이 나온다. 오탐이면 해당 룰만 "Disable" 하거나, 특정 URL 경로에서만 Skip할 수 있다.

Rate Limiting에 걸린 경우 Service가 "Rate Limiting"으로 나온다. 어느 IP, 어느 경로가 임계값을 초과했는지 같이 보인다. 정상 트래픽이 걸렸다면 임계값을 올리거나 해당 경로를 조건에서 제외한다.

Logpush를 설정했으면 `http_requests` 데이터셋의 `WafAction`, `WafMatchedVar`, `RuleId` 필드를 쿼리한다. 특정 룰이 얼마나 차단하는지 대용량 로그에서 집계할 때 쓴다. Athena나 BigQuery에 올려서 분석하는 방식을 주로 쓴다.
