---
title: DNS (Domain Name System)
tags: [network, domain, dns, name-resolution, internet-infrastructure]
updated: 2026-05-14
---

# DNS (Domain Name System)

## 개요

DNS는 도메인 이름을 IP 주소로 푸는 분산 데이터베이스다. 1983년 RFC 1034/1035로 정의됐고, 그 이후 RFC 수십 개가 덧붙어 지금의 형태가 됐다. 서비스 운영 입장에서는 단순한 이름풀이를 넘어서 트래픽 라우팅, 메일 인증, TLS 발급, 장애 격리까지 묶여 있는 기반 인프라다.

운영 중 마주치는 문제는 대부분 "DNS는 분산 캐시 시스템이다"라는 점에서 출발한다. 레코드 한 줄 바꿔도 전 세계 리졸버 캐시가 만료되기 전까지는 옛날 값을 본다. TTL을 깜빡 잊고 24시간으로 두면 장애 복구가 24시간 걸리고, 30초로 두면 권한 서버 부하가 폭증한다. 이 균형을 잡는 게 DNS 운영의 핵심이다.

## DNS 계층 구조와 위임

### 계층은 점(.)으로 끊는다

`api.shop.example.com.` 끝의 점은 root를 의미한다. 평소엔 생략하지만 zone 파일에선 명시적으로 써야 절대 이름(FQDN)이 된다. 점이 없으면 BIND가 자동으로 `$ORIGIN`을 붙인다.

```
. (root)
└── com (TLD)
    └── example.com (registered domain)
        └── shop.example.com (subdomain)
            └── api.shop.example.com (host)
```

각 계층은 NS 레코드로 다음 계층의 권한 서버를 가리킨다. root는 com의 NS를, com은 example.com의 NS를, example.com은 shop의 NS를 (만약 위임했다면) 가리키는 식이다.

### dig로 위임 추적하기

`+trace` 옵션을 쓰면 root부터 한 단계씩 위임을 따라간다. 캐시를 거치지 않고 권한 서버에 직접 묻기 때문에 위임이 깨졌는지 확인할 때 가장 정확하다.

```bash
$ dig +trace api.shop.example.com

;; Received 525 bytes from 198.41.0.4#53(a.root-servers.net) in 18 ms

com.                    172800  IN  NS  a.gtld-servers.net.
;; Received 1180 bytes from 192.5.6.30#53(a.gtld-servers.net) in 24 ms

example.com.            172800  IN  NS  ns1.example.com.
example.com.            172800  IN  NS  ns2.example.com.
;; Received 287 bytes from 192.43.172.30#53(c.gtld-servers.net) in 31 ms

api.shop.example.com.   300     IN  A   203.0.113.45
;; Received 75 bytes from 198.51.100.10#53(ns1.example.com) in 12 ms
```

각 단계에서 어느 서버가 어떤 NS를 돌려줬는지 보인다. 위임이 깨진 도메인이면 중간 단계에서 `connection timed out` 같은 메시지가 나온다.

### 레지스트라에서 NS 바꿨는데 글루(glue)가 빠진 경우

도메인을 처음 등록하고 권한 서버를 자체 호스팅한다면, NS 레코드를 `ns1.example.com`으로 지정하는 경우가 있다. 그러면 `example.com`을 풀려면 `ns1.example.com`을 알아야 하고, `ns1.example.com`을 풀려면 `example.com`을 알아야 하는 닭-달걀 문제가 생긴다. 이를 푸는 게 글루 레코드(glue record)다.

레지스트라 콘솔에서 NS 이름만 바꾸고 그 NS의 IP는 따로 등록(register host / glue record / host registration)하지 않으면, TLD에서 NS 이름은 받았는데 IP를 모르는 상태가 된다. 이 경우 외부에서 도메인을 풀 수 없다. 보통 등록 직후엔 캐시에 옛 글루가 남아있어서 멀쩡해 보이다가, TTL이 지나면서 갑자기 죽는다.

확인하려면 TLD 서버에 직접 묻는다.

```bash
$ dig @a.gtld-servers.net example.com NS +norec
;; ADDITIONAL SECTION:
ns1.example.com.    172800  IN  A   198.51.100.10
ns2.example.com.    172800  IN  A   198.51.100.11
```

`ADDITIONAL SECTION`에 IP가 같이 나와야 글루가 정상이다. 비어 있으면 레지스트라에서 글루 등록을 해야 한다. 외부 DNS 서비스(Route53, Cloudflare 등)를 쓸 땐 NS 이름이 그 서비스 도메인(`ns-123.awsdns-15.com` 같은)이므로 글루 문제는 그쪽에서 알아서 처리한다.

## 레코드 타입별 실전

### A / AAAA

호스트 이름을 IPv4(A)와 IPv6(AAAA)로 매핑한다. 가장 단순하지만 멀티 A 레코드를 쓰면 round-robin DNS가 된다. 단, 리졸버나 클라이언트마다 순서를 다르게 처리하므로 로드 밸런싱 용도로 신뢰할 만한 건 아니다.

```
@           IN  A       203.0.113.10
@           IN  A       203.0.113.11
www         IN  A       203.0.113.10
@           IN  AAAA    2001:db8::10
```

`@`는 zone의 apex(루트, 즉 `example.com.` 자체)를 가리킨다. 동일 이름에 A와 AAAA를 같이 두면 dual-stack 클라이언트가 둘 다 받아서 Happy Eyeballs로 빠른 쪽을 쓴다.

### CNAME과 apex 문제

CNAME은 한 이름을 다른 이름으로 별칭 처리한다. RFC 1034에 따르면 **CNAME이 있는 이름엔 다른 레코드를 같이 둘 수 없다**. 그래서 apex(`example.com.`)엔 CNAME을 못 쓴다. apex엔 이미 SOA와 NS가 있기 때문이다.

```
; 잘못된 zone 파일
@           IN  CNAME   d123.cloudfront.net.   ; SOA/NS와 충돌, 거부됨
www         IN  CNAME   d123.cloudfront.net.   ; OK
```

이 제약 때문에 CDN이나 ELB를 apex에 붙이려면 곤란해진다. Route53의 ALIAS, Cloudflare의 CNAME flattening, DNSimple의 ANAME 같은 기능이 이걸 우회한다. 동작 원리는 같다. 권한 서버가 CNAME을 클라이언트에 돌려주는 대신, 서버 측에서 한번 더 풀어서 A/AAAA로 응답한다. zone 파일에는 CNAME처럼 적지만 응답은 A다. 따라서 다른 권한 서버로 zone을 옮기면 ALIAS는 깨질 수 있다. 호환되는 곳으로만 옮겨야 한다.

### CNAME 체이닝과 TTL 누적

`a.example.com CNAME b.example.com CNAME c.example.com A 1.2.3.4`처럼 체이닝되면 리졸버는 매번 체인 전체를 따라간다. 각 단계마다 TTL이 다르면, 클라이언트가 보는 실효 TTL은 가장 짧은 값에 묶이지만 권한 서버 부하는 길이에 비례해서 늘어난다.

체인이 5단 이상 길어지면 일부 리졸버는 더 안 따라가고 끊어버린다. 또 CNAME 응답 자체가 패킷 크기를 키워서 EDNS0 fragmentation 문제를 일으키기도 한다. 운영 입장에선 체인 깊이는 2단 이하로 유지하는 게 안전하다. CDN 위에 또 다른 별칭 도메인을 얹는 식의 구조는 가급적 피한다.

### MX

메일 서버를 지정한다. priority(preference) 값이 작을수록 우선이다.

```
@   IN  MX  10  mail1.example.com.
@   IN  MX  10  mail2.example.com.
@   IN  MX  20  backup.example.com.
```

priority가 같으면 라운드로빈, 다르면 낮은 쪽 먼저 시도하고 실패 시 다음으로 넘어간다. 흔한 실수는 MX의 우변에 IP를 직접 쓰는 것. MX는 호스트 이름만 받는다. IP를 쓰면 RFC 위반이고, 일부 메일 서버는 거부한다. CNAME을 가리키는 것도 RFC 2181에서 금지한다(실제론 동작하지만 권장하지 않음).

apex에 MX가 없으면 메일이 거부된다(혹은 일부 서버는 A 레코드로 폴백한다). 메일 안 받는 도메인이라면 `null MX`(RFC 7505)를 명시한다.

```
@   IN  MX  0   .
```

### NS

zone을 누가 관리하는지 가리킨다. apex의 NS는 위임 정보 그 자체다. 서브 zone을 위임하려면 부모 zone에 NS 레코드를 둔다.

```
; example.com zone 파일
shop    IN  NS  ns1.shop-provider.net.
shop    IN  NS  ns2.shop-provider.net.
```

이렇게 두면 `shop.example.com` 이하의 풀이는 전부 `ns1.shop-provider.net`이 담당한다. 부모와 자식 zone 양쪽에 NS를 두는 게 정석이지만, 실제론 부모(위임자) 쪽 NS만 보고 위임이 결정된다. 이 둘이 다르면 lame delegation이 된다. `dig +norec @ns.parent`와 `dig +norec @ns.child`를 같은 NSSET으로 비교해서 일치하는지 봐야 한다.

### TXT와 255바이트 분할

TXT는 임의의 문자열을 넣는 레코드다. SPF, DKIM, DMARC, 도메인 소유권 검증(Google Search Console, AWS ACM, Let's Encrypt DNS-01 챌린지 등) 용도로 쓴다.

문제는 **TXT 한 string의 최대 길이가 255바이트**라는 점이다. DKIM 키 같은 긴 값은 분할해야 한다. zone 파일에선 큰따옴표로 끊어서 여러 string을 한 레코드에 넣는다.

```
default._domainkey  IN  TXT  ( "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA"
                                "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc"
                                "..." )
```

dig 결과는 각 string을 따로 보여준다.

```bash
$ dig default._domainkey.example.com TXT +short
"v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA" "1234567890abcdef..."
```

수신 측 메일 서버는 string들을 그대로 이어붙여서 해석한다. 사이에 공백이나 줄바꿈을 넣으면 키가 깨진다. 클라우드 DNS 콘솔에 붙여 넣을 땐 따옴표 처리 방식이 제공자마다 달라서, 분할 안 하고 통째로 입력해도 자동으로 잘라주는 곳이 있고 그대로 토해내는 곳이 있다. 입력 후 반드시 `dig +short`로 결과를 다시 확인한다.

### SRV

서비스 위치를 지정한다. 이름 형식은 `_service._proto.name`이다. SIP, XMPP, LDAP, Minecraft 같은 곳에서 쓴다. HTTPS는 RFC 9460의 HTTPS 레코드로 따로 빠졌다.

```
_sip._tcp   IN  SRV  10  60  5060  sip1.example.com.
_sip._tcp   IN  SRV  10  40  5060  sip2.example.com.
_sip._tcp   IN  SRV  20  100 5060  sip-backup.example.com.
```

필드는 `priority weight port target`이다. priority는 MX와 같고, weight는 같은 priority 안에서의 가중치다. 위 예에선 priority 10인 두 서버 중 sip1이 60%, sip2가 40% 비율로 선택된다. priority 20은 위쪽이 다 죽어야 쓴다.

weight 0의 의미가 특이하다. RFC 2782에 따르면 다른 0이 아닌 weight가 있을 때 weight 0은 "선택될 확률 거의 0"이고, 모든 weight가 0이면 균등 분포다. 가중치 라운드로빈처럼 쓰지만 클라이언트 구현에 따라 동작이 다르므로 정확한 분배가 필요하면 LB를 쓴다.

### CAA

`Certificate Authority Authorization`. 어떤 CA가 이 도메인의 인증서를 발급할 수 있는지 제한한다.

```
@   IN  CAA  0  issue       "letsencrypt.org"
@   IN  CAA  0  issue       "amazon.com"
@   IN  CAA  0  issuewild   ";"
@   IN  CAA  0  iodef       "mailto:security@example.com"
```

CA는 발급 직전에 도메인의 CAA를 조회하고, 자기 이름이 없으면 거부한다. `issuewild ";"`는 와일드카드 인증서를 누구에게도 허용하지 않는다는 뜻이다. CAA를 잘못 설정하면 인증서 갱신이 조용히 실패한다. ACM이나 Let's Encrypt 자동 갱신을 쓴다면 CA 이름을 정확히 적어야 한다(예: ACM은 `amazon.com`, `amazontrust.com`, `awstrust.com`, `amazonaws.com` 모두).

### SOA와 negative caching

SOA(Start of Authority)는 zone마다 정확히 하나, apex에 둔다.

```
@   IN  SOA  ns1.example.com. hostmaster.example.com. (
                2026051401  ; serial
                3600        ; refresh
                900         ; retry
                1209600     ; expire
                300         ; minimum (negative cache TTL)
            )
```

각 필드의 운영적 의미:

- **serial**: secondary(slave) 서버가 zone 변경을 감지하는 기준. 변경할 때마다 올린다. 관습적으로 `YYYYMMDDnn` 형식. 안 올리면 secondary가 동기화 안 한다.
- **refresh**: secondary가 primary에 변경 여부를 묻는 주기. AXFR/IXFR 또는 NOTIFY로 트리거된다.
- **retry**: refresh 실패 시 재시도 간격.
- **expire**: secondary가 primary와 연결 못한 채로 zone을 유효하다고 간주하는 한계 시간. 초과하면 권한 응답을 거부한다.
- **minimum**: 원래 의미는 모든 레코드의 기본 TTL이었으나, RFC 2308 이후로 **negative caching TTL**로 재정의됐다. 존재하지 않는 이름(NXDOMAIN)이나 빈 응답을 캐시할 시간.

minimum을 86400으로 두면, 한 번 `NXDOMAIN`이 캐시된 이름은 하루 동안 그대로 캐시된다. 새 서브도메인을 추가했는데 "왜 아직 안 보이지" 하는 상황이 여기서 자주 발생한다. 신규 추가가 잦은 zone은 minimum을 300~900초로 짧게 둔다.

## TTL 운영

### 변경 전 단축 → 변경 → 복원

도메인이 가리키는 IP를 옮긴다고 하자. 현재 TTL이 86400(1일)이면 변경 후 최대 1일 동안 전 세계 일부 리졸버는 옛 IP를 응답한다. 이걸 줄이려면 변경 작업 전에 TTL을 미리 낮춰둔다.

표준 절차:

1. 변경 작업 D-2일에 TTL을 86400에서 300으로 낮춘다. 옛 캐시는 최대 86400초 동안 살아 있으니, 최소 1일은 기다려야 캐시가 새 TTL로 갈린다.
2. 1일 이상 경과 후, 실제 레코드 값을 변경한다. 이제 캐시는 5분 안에 만료된다.
3. 안정화되면 TTL을 원래대로 86400으로 복원한다.

이 절차를 무시하고 TTL 86400 상태에서 그냥 바꾸면, 일부 사용자는 24시간 동안 옛 서버로 트래픽이 간다. 옛 서버를 그동안 띄워두지 않으면 그 사용자는 장애를 본다.

### 음수 캐시(negative caching)

존재하지 않는 이름도 캐시된다. 어떤 사용자가 오타로 `api2.example.com`을 조회했고 그게 없으면, 그 결과(NXDOMAIN)가 SOA의 minimum만큼 캐시된다. 나중에 `api2`를 진짜로 추가해도 그 캐시가 만료될 때까지 사용자는 NXDOMAIN을 받는다.

서브도메인을 새로 추가할 때 "이게 왜 안 보이지" 디버깅에 시간을 쓰는 일이 많은데, 거의 다 minimum TTL 때문이다. 8.8.8.8이나 1.1.1.1에서 풀어보면 잘 나오는데 회사 리졸버에서만 안 나오면, 회사 리졸버가 NXDOMAIN을 캐시하고 있을 가능성이 높다.

## Zone 파일 BIND 문법

BIND 형식은 RFC 1035 표준 형식이다. 다른 권한 서버(NSD, Knot, PowerDNS)도 대부분 같은 문법을 지원한다.

```
$ORIGIN example.com.
$TTL 3600

@           IN  SOA   ns1.example.com. hostmaster.example.com. (
                       2026051401   ; serial
                       3600         ; refresh
                       900          ; retry
                       1209600      ; expire
                       300 )        ; minimum

            IN  NS    ns1.example.com.
            IN  NS    ns2.example.com.

@           IN  A     203.0.113.10
@           IN  MX    10 mail.example.com.

ns1         IN  A     198.51.100.10
ns2         IN  A     198.51.100.11

www         IN  CNAME @
api         IN  A     203.0.113.20
mail        IN  A     203.0.113.30

; wildcard
*.dev       IN  A     203.0.113.99
```

핵심 문법:

- `$ORIGIN`: 이후 등장하는 상대 이름이 어떤 도메인 아래에 붙는지 지정. 없으면 zone 로딩 명령으로 지정된 이름이 origin이 된다.
- `$TTL`: 명시 TTL이 없는 레코드에 적용될 기본 TTL.
- `@`: 현재 `$ORIGIN`.
- 이름이 비어 있는 줄: 직전 줄과 같은 이름을 이어 쓴다.
- 끝에 `.` 없는 이름은 상대 이름. `$ORIGIN`이 자동으로 붙는다. `www`는 `www.example.com.`이 된다.
- `.`이 있으면 절대 이름. 그대로 쓴다.

zone 파일에서 `mail` 같은 이름 뒤에 점을 빠뜨리면 `mail.example.com.mail.example.com.` 같은 괴상한 결과가 나온다. MX, CNAME, NS의 우변은 절대 이름이어야 하니 끝의 점을 꼭 확인한다.

### 와일드카드 레코드

`*.dev.example.com`은 `dev.example.com` 아래의 임의 이름 한 단계에 매치된다.

```
*.dev       IN  A     203.0.113.99
```

이때 헷갈리기 쉬운 부분:

- 와일드카드는 **존재하지 않는 이름**에만 매치된다. `foo.dev.example.com`을 명시적으로 정의했으면 그 이름은 와일드카드를 무시한다.
- 와일드카드는 한 단계만 매치한다. `*.dev`는 `x.dev`엔 매치되지만 `y.x.dev`엔 안 매치된다. `y.x.dev`도 잡으려면 `*.x.dev`를 따로 둬야 한다.
- 와일드카드 아래의 하위 노드 존재 자체가 와일드카드 매치를 막는다. `x.dev`를 명시했으면 `something.x.dev`는 와일드카드에 안 잡히고 NXDOMAIN이 된다(empty non-terminal 문제).

와일드카드와 CNAME, MX를 섞으면 의도와 다른 결과가 자주 나온다. 가능하면 와일드카드 zone과 명시적 zone을 섞지 말고, 와일드카드만 쓰는 zone을 따로 빼는 게 낫다.

## Anycast와 GeoDNS

### Anycast

같은 IP 주소를 여러 지역의 서버가 BGP로 동시에 광고한다. 클라이언트는 자기 ISP의 BGP 경로상 가장 가까운 서버로 라우팅된다. 8.8.8.8, 1.1.1.1 같은 공용 리졸버, root 서버, 대부분의 권한 서버 서비스(Route53, Cloudflare DNS)가 이 방식이다.

장점은 단일 IP로 전 세계 분산을 얻고, 어느 한 노드가 죽으면 BGP가 자동으로 트래픽을 다른 노드로 흘려준다는 것. 단점은 라우팅이 BGP 경로에 의존하므로 "지리적으로 가까운 서버"가 보장되지 않는다. 트랜짓 사정에 따라 한국 사용자가 일본 노드로 가는 경우도 있다.

Anycast는 권한 서버나 리졸버 자체의 가용성을 위한 것이다. 응답 내용은 지역과 무관하게 동일하다.

### GeoDNS

권한 서버가 쿼리 출발지 IP를 보고 다른 응답을 내려준다. CDN이 사용자별로 가장 가까운 엣지 IP를 돌려주는 게 대표적인 예다.

```bash
# 한국에서
$ dig www.example.com
www.example.com.   60   IN   A   203.0.113.10   ; 서울 엣지

# 미국에서
$ dig www.example.com
www.example.com.   60   IN   A   198.51.100.20  ; 버지니아 엣지
```

문제는 출발지 IP가 리졸버의 IP라는 점이다. 클라이언트가 8.8.8.8을 쓰면 권한 서버는 8.8.8.8이 어디 있는지로 판단한다. EDNS Client Subnet(ECS, RFC 7871)을 켜면 리졸버가 클라이언트의 서브넷을 권한 서버에 전달해서 정확도를 높인다. Google과 Cloudflare는 ECS를 일부만 지원한다(1.1.1.1은 프라이버시 이유로 기본 비활성).

GeoDNS는 응답이 클라이언트마다 다르므로 캐싱이 어렵다. TTL을 짧게(60초 이하) 유지하는 게 일반적이고, 그래서 권한 서버 부하가 높다. Anycast로 권한 서버를 분산하는 이유 중 하나가 이거다.

## DNS 보안

### DNSSEC

DNS 응답에 디지털 서명을 붙여서 위변조를 막는다. zone에 RRSIG, DNSKEY, DS, NSEC/NSEC3 레코드가 추가된다. 부모 zone에 DS 레코드를 등록해서 신뢰 체인이 root까지 이어진다.

```bash
$ dig +dnssec example.com A
;; ANSWER SECTION:
example.com.    300  IN  A      203.0.113.10
example.com.    300  IN  RRSIG  A 13 2 300 ...
```

운영 측면에서 DNSSEC은 만만치 않다. 키 롤오버(KSK rollover) 절차를 잘못하면 zone 전체가 검증 실패해서 풀리지 않는다. 2018년 root KSK 롤오버 때 검증 실패한 리졸버가 꽤 있었다. 직접 운영보다는 DNS 서비스 제공자(Route53, Cloudflare 등)의 관리형 DNSSEC을 쓰는 게 안전하다.

### DoH/DoT

전통적인 DNS는 53/UDP 평문이라 ISP나 중간자가 쿼리 내용을 볼 수 있고 변조할 수 있다. DoT(853/TCP, TLS)와 DoH(443/HTTPS)는 쿼리를 암호화한다. DoT는 별도 포트라 차단하기 쉽고, DoH는 일반 HTTPS와 구분이 안 돼서 차단이 어렵다.

회사 네트워크 입장에선 DoH가 골치다. 사내 DNS 정책(특정 도메인 차단, 내부 DNS 우선 등)을 우회하는 통로가 된다. Firefox와 Chrome은 기본적으로 DoH를 켜놓고, 회사 망에서 비활성화하려면 정책 설정이 필요하다.

## dig 활용

dig 옵션 몇 가지는 운영 중 자주 쓴다.

```bash
# 기본 조회
dig example.com

# 특정 타입
dig example.com MX
dig example.com TXT
dig example.com NS

# 특정 리졸버에 묻기
dig @8.8.8.8 example.com
dig @1.1.1.1 example.com

# 권한 서버에 직접 (캐시 우회)
dig @ns1.example.com example.com +norec

# 위임 추적
dig example.com +trace

# 짧은 출력
dig example.com +short

# 응답 전체와 헤더 플래그
dig example.com +noall +answer +authority

# DNSSEC 검증
dig example.com +dnssec
```

응답 헤더의 플래그를 자주 본다.

- `aa`: authoritative answer. 권한 서버가 직접 답한 응답.
- `ra`: recursion available. 리졸버가 재귀 풀이를 지원.
- `ad`: authenticated data. DNSSEC 검증 통과.
- `tc`: truncated. UDP 패킷이 잘렸으니 TCP로 재시도 필요.

`tc` 플래그가 보이는데 클라이언트나 방화벽이 53/TCP를 막아두면 큰 응답을 못 받는다. DNSSEC이나 긴 TXT를 쓰면 응답이 UDP 512바이트를 자주 넘기 때문에 53/TCP를 허용해야 한다.

## 참조

- RFC 1034 / 1035: Domain Names - Concepts/Implementation
- RFC 2181: Clarifications to the DNS Specification
- RFC 2308: Negative Caching of DNS Queries
- RFC 2782: A DNS RR for specifying the location of services (SRV)
- RFC 4033 / 4034 / 4035: DNS Security Extensions (DNSSEC)
- RFC 6844 / 8659: CAA
- RFC 7505: A "Null MX" No Service Resource Record
- RFC 7858: DNS over TLS
- RFC 7871: Client Subnet in DNS Queries
- RFC 8484: DNS Queries over HTTPS
- RFC 9460: Service Binding and Parameter Specification (SVCB/HTTPS)
