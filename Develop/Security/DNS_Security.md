---
title: DNS Security
tags:
  - Security
  - DNS
  - DNSSEC
  - DoH
  - DoT
  - Network
updated: 2026-05-06
---

# DNS Security

DNS는 거의 모든 네트워크 통신의 출발점이다. 그런데 평문 UDP 53번에서 동작하고, 응답을 검증할 방법이 기본적으로 없다. 누군가 중간에서 응답을 위조하면 클라이언트는 그대로 믿는다. TLS 인증서 검증이 도입돼서 IP 단계에서의 가로채기는 어느 정도 막을 수 있지만, "어느 IP로 갈 것인가"를 정하는 DNS 단계가 깨지면 그 뒤가 다 흔들린다.

실무에서 DNS 보안이라고 하면 보통 네 갈래로 본다.

1. 응답 무결성 — DNSSEC
2. 질의 기밀성 — DoH/DoT
3. 응답을 악용한 공격 방어 — DNS rebinding, cache poisoning
4. 도메인/레코드 운영 — dangling CNAME, 도메인 탈취

각각 공격 표면과 대응 도구가 다르다. 한 번에 다 해결하는 마스터 키 같은 건 없고, 운영 환경에 맞춰 골라 적용해야 한다.

## DNS 질의 흐름과 신뢰 모델

DNS 질의는 다음 경로를 거친다.

```
stub resolver (브라우저, libc) 
    → recursive resolver (1.1.1.1, 8.8.8.8, ISP DNS, 사내 DNS)
        → root → TLD → authoritative name server
```

이 경로 중 어디든 응답을 위조할 수 있는 위치를 차지하면 공격이 성립한다. 클라이언트와 recursive resolver 사이는 LAN/Wi-Fi 라우터, ISP, 카페 공유기까지 다 노출돼 있다. recursive resolver에서 권위 서버까지의 구간은 BGP 하이재킹이나 캐시 오염 같은 더 깊은 단계 공격 영역이다.

기본 DNS는 응답에 서명이 없다. 즉 "이 응답이 정말 권위 서버에서 온 것인가"를 클라이언트가 확인할 방법이 프로토콜 차원에서 없다. 이게 DNSSEC가 풀려는 문제다.

## DNSSEC 동작 원리

DNSSEC는 DNS 응답에 디지털 서명을 붙인다. 응답이 위조되지 않았는지 공개키로 검증한다는 뜻이다. 핵심 레코드는 네 개다.

| 레코드 | 역할 |
|---|---|
| RRSIG | 특정 RRset(예: example.com A 레코드 묶음)의 서명 |
| DNSKEY | 서명 검증용 공개키 (ZSK, KSK) |
| DS | 부모 존이 자식 존의 KSK 해시를 갖고 있어 신뢰 사슬을 잇는다 |
| NSEC/NSEC3 | "이 레코드는 존재하지 않는다"를 증명 (부재 증명) |

키는 두 종류다. ZSK(Zone Signing Key)는 실제 레코드를 서명하는 데 쓰고 자주 교체한다. KSK(Key Signing Key)는 ZSK를 서명하고 부모 존의 DS와 연결된다. KSK는 잘 안 바꾼다. 분리한 이유는 명확하다. ZSK는 자주 도는데 그때마다 부모 존에 DS를 갱신하려면 운영 비용이 폭발한다.

신뢰 사슬은 root에서 시작한다. root의 KSK 해시(trust anchor)는 OS나 resolver 소프트웨어에 박혀 있다. root → .com → example.com 으로 내려가며 부모의 DS가 자식의 DNSKEY를 보증한다. 어느 한 단계라도 서명이 깨지면 검증 실패다.

### 부재 증명: NSEC와 NSEC3

존재하지 않는 도메인을 물었을 때 "없다"는 응답도 위조될 수 있어야 한다. NSEC는 알파벳 순서로 정렬된 다음 레코드를 가리킨다. `aaa.example.com` 다음이 `ccc.example.com`이라고 서명하면, 그 사이의 `bbb.example.com`은 존재하지 않음이 증명된다.

문제는 NSEC가 존 전체를 그대로 노출시킨다는 점이다. 공격자가 NSEC 응답을 따라가면서 zone walking을 하면 모든 서브도메인 목록을 얻는다. 그래서 NSEC3가 나왔다. 이름을 해시해서 정렬하니까 원본 도메인 이름은 직접 노출되지 않는다. 다만 GPU로 해시 역산을 시도하면 짧은 이름은 풀린다. 최근에는 NSEC3 대신 NSEC에 minimally covering response를 쓰는 흐름도 있다. 어느 쪽이든 부재 증명에는 트레이드오프가 따른다.

### dig로 DNSSEC 확인

`+dnssec` 플래그를 붙이면 RRSIG와 DNSKEY를 같이 받는다.

```bash
dig +dnssec example.com A

;; ANSWER SECTION:
example.com.    300  IN  A      93.184.216.34
example.com.    300  IN  RRSIG  A 13 2 300 20260612000000 (
                                20260522000000 12345 example.com.
                                ABcdEf... )

;; Query time: 23 msec
;; flags: qr rd ra ad; ...
```

여기서 봐야 할 건 두 가지다.

`flags`에 `ad`(Authenticated Data)가 있는지. resolver가 DNSSEC 검증에 성공했다는 표시다. 없으면 검증을 안 했거나 검증 실패다. `cd`(Checking Disabled) 플래그가 켜져 있으면 클라이언트가 검증을 의도적으로 꺼버린 상태다.

RRSIG 레코드에 서명이 같이 왔는지. 권위 서버가 DNSSEC를 적용했다는 증거다. RRSIG가 안 오면 그 도메인은 DNSSEC 미적용이다.

### delv로 직접 검증

`dig`는 resolver의 검증 결과를 그대로 받는다. `delv`는 클라이언트 자체가 root의 trust anchor부터 직접 검증을 수행한다. 신뢰 사슬을 처음부터 따라가서 확인하는 도구다.

```bash
delv +rtrace example.com A

;; resolution succeeded
;; fully validated
example.com.  300  IN  A      93.184.216.34
example.com.  300  IN  RRSIG  A 13 2 300 ...
```

`fully validated`가 뜨면 root → TLD → 도메인까지 신뢰 사슬이 깨끗하게 이어졌다는 의미다. 만약 `; resolution failed: insecurity proof failed` 같은 메시지가 나오면 어딘가에서 DS 등록이 빠졌거나 서명이 깨졌다는 뜻이다.

`+rtrace`는 검증 과정을 단계별로 보여줘서 디버깅에 쓸 만하다. 키 롤오버 직후 검증 실패가 나면 이걸로 어느 키에서 실패했는지 찾는다.

### DNSSEC 운영하면서 자주 깨지는 부분

키 롤오버 사고가 가장 많다. ZSK를 교체하면서 RRSIG는 새 키로 서명했는데 DNSKEY 레코드에 이전 키를 같이 노출하지 않으면 캐시된 RRSIG를 들고 있는 resolver는 검증에 실패한다. 보통 prepublish 방식으로 신키를 먼저 노출하고 충분히 전파된 다음에 서명에 쓰기 시작한다.

DS 등록 누락도 흔하다. 도메인 등록기관(레지스트라)에 DS를 등록하지 않으면 부모 존이 자식 존을 보증하지 못한다. 이 상태에서 DNSSEC를 켜면 검증 자체는 일어나지 않지만, "DNSSEC를 적용했다"고 착각하는 게 더 위험하다.

서명 만료도 문제다. RRSIG에는 inception/expiration 타임스탬프가 박혀 있다. 자동 재서명이 죽거나 시계가 틀어지면 서명이 만료돼서 도메인 전체가 SERVFAIL로 떨어진다. Slack도 2021년에 비슷한 이유로 장애를 겪었다.

DNSSEC가 풀어주는 건 응답 무결성뿐이다. 질의 내용과 응답이 평문으로 다닌다는 사실 자체는 그대로다. 누가 어떤 도메인을 물었는지는 경로상에서 다 보인다. 그래서 별도로 DoH/DoT가 필요하다.

## DoH와 DoT

DoT(DNS over TLS)는 853번 포트에서 TLS로 감싼 DNS 메시지를 주고받는다. RFC 7858. DNS 메시지 형식은 그대로고 전송 계층만 암호화된다. 방화벽이 853번을 보면 "DNS 트래픽이구나" 알 수 있다.

DoH(DNS over HTTPS)는 443번 HTTPS 위에서 DNS 질의를 GET이나 POST로 보낸다. RFC 8484. 방화벽 입장에서는 그냥 HTTPS 트래픽처럼 보인다. 일반 웹 트래픽과 구분이 어렵다.

```bash
# DoH 직접 호출 예시 (Cloudflare)
curl -H "accept: application/dns-json" \
  "https://cloudflare-dns.com/dns-query?name=example.com&type=A"
```

```json
{
  "Status": 0,
  "Answer": [
    {"name": "example.com", "type": 1, "TTL": 268, "data": "93.184.216.34"}
  ]
}
```

### DoH/DoT 도입 시 운영 이슈

브라우저가 OS의 DNS 설정을 무시하고 자체 DoH로 가버리는 문제가 있다. Firefox는 일정 조건에서 Cloudflare DoH를 자동으로 쓴다. Chrome은 OS DNS와 매핑되는 DoH 서버가 있으면 자동 업그레이드한다. 사내 DNS로 내부 도메인을 풀어야 하는 환경에서는 골치 아프다. `corp.internal` 같은 사설 도메인이 외부 DoH 서버로 새서 NXDOMAIN을 받는 상황이 생긴다.

방어선 입장에서도 평가가 갈린다. DoH는 멀웨어가 C2 통신을 숨기는 데 자주 쓰인다. 방화벽이 도메인 단위 차단(DNS sinkhole)을 하던 환경에서는 DoH 트래픽이 그 통제를 우회한다. 그래서 기업 환경에서는 외부 DoH 엔드포인트 자체를 차단하거나, 자체 DoH 서버를 운영해서 강제로 거기로 보내는 방식을 쓴다.

Stub resolver 단에서 DoT만 켜는 것도 부분적인 해결이다. 클라이언트와 recursive resolver 구간만 암호화된다. recursive resolver와 권위 서버 사이는 여전히 평문이다. 이 구간을 위해 ADoT(Authoritative DoT)나 RFC 9539(EncryptedClientHello, ECH 기반)도 논의 중이지만 보급률은 낮다.

### Linux에서 DoT 적용

systemd-resolved를 쓰면 설정 한두 줄로 DoT를 강제할 수 있다.

```ini
# /etc/systemd/resolved.conf
[Resolve]
DNS=1.1.1.1#cloudflare-dns.com 1.0.0.1#cloudflare-dns.com
DNSOverTLS=yes
DNSSEC=yes
```

`DNSOverTLS=yes`는 TLS 실패 시 평문으로 폴백하지 않는다. `DNSOverTLS=opportunistic`은 실패 시 폴백한다. 보안 관점에서는 `yes`가 맞다. `#cloudflare-dns.com` 부분은 TLS 인증서의 SNI/SAN 검증에 쓴다. 이게 빠지면 IP 인증만 되고 MITM 가능성이 생긴다.

## DNS Rebinding 공격

이게 실무에서 잡기 까다로운 공격이다. 핵심 아이디어는 단순하다. 공격자가 자기 도메인의 DNS 응답을 처음에는 자기 IP로 주고, 같은 도메인에 대해 두 번째 질의에는 피해자 내부 IP(예: 192.168.1.1)로 응답한다. TTL을 0이나 1초로 짧게 잡는다.

진행 시나리오는 이렇다.

```
1. 사용자가 attacker.com 방문
2. attacker.com → 198.51.100.10 (공격자 서버) 응답
3. 브라우저가 attacker.com의 JavaScript 로드
4. JS가 attacker.com에 fetch 요청 (Same-Origin이라 허용)
5. TTL 만료, 다시 DNS 질의
6. attacker.com → 192.168.1.1 (피해자 라우터) 응답
7. 브라우저는 여전히 "attacker.com"으로 인식 → Same-Origin 정책 통과
8. JS가 192.168.1.1의 관리 페이지에 요청 가능
```

브라우저의 SOP(Same-Origin Policy)는 도메인 이름 기준으로 동작하지 SOP가 IP를 다시 확인하지는 않는다. 그래서 도메인 이름은 같은데 IP가 바뀌는 순간 내부망 자원에 외부 JS가 접근할 수 있게 된다. IoT 라우터, 로컬에서 도는 개발 서버, Redis/Elasticsearch가 0.0.0.0으로 바인딩된 경우 등이 다 표적이다.

### 방어

서버 측 Host 헤더 검증이 가장 현실적이다. 내부 서비스는 `Host: 192.168.1.1`로 들어오는 요청만 받지 말고, 화이트리스트된 호스트명만 받도록 한다.

```javascript
// Express
const allowedHosts = ['admin.internal.local', 'localhost'];

app.use((req, res, next) => {
  const host = req.headers.host?.split(':')[0];
  if (!allowedHosts.includes(host)) {
    return res.status(403).send('Invalid Host header');
  }
  next();
});
```

Resolver 단에서 Private IP 응답을 필터링하는 방법도 있다. RFC 1918 대역(10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), 링크 로컬(169.254.0.0/16), 루프백(127.0.0.0/8)을 외부 도메인 응답에서 받으면 차단한다. dnsmasq의 `stop-dns-rebind` 옵션, Unbound의 `private-address` 설정이 이걸 한다.

```
# Unbound 설정 예시
server:
    private-address: 10.0.0.0/8
    private-address: 172.16.0.0/12
    private-address: 192.168.0.0/16
    private-address: 169.254.0.0/16
    private-address: 127.0.0.0/8
    private-address: ::1/128
    private-address: fd00::/8
```

내부 서비스가 인증을 강제하고 CSRF 토큰을 요구하면 rebinding이 성공해도 의미 있는 행동을 못 한다. 라우터 관리 페이지가 비밀번호 없이 들어가지는 게 문제의 본질이지, DNS 자체만의 문제는 아니다.

## DNS Cache Poisoning

Recursive resolver의 캐시에 거짓 응답을 심는 공격이다. 2008년 Kaminsky 공격이 가장 유명하다. resolver가 권위 서버에 질의를 보낸 직후, 진짜 응답이 도착하기 전에 위조 응답을 마구 보내서 매칭시키는 방식이다.

매칭 조건은 두 가지였다. 16비트 트랜잭션 ID와 질의한 도메인. ID가 16비트라 65536가지 경우의 수밖에 없고, 짧은 시간에 다량의 위조 응답을 보내면 충돌 가능성이 의외로 높다. Kaminsky는 여기에 서브도메인 무작위 질의를 결합해서 거의 100% 확률로 캐시를 오염시킬 수 있다는 걸 보여줬다.

### 완화

Source port randomization. 질의 출발 포트를 랜덤화해서 16비트 추가 엔트로피를 만든다. 트랜잭션 ID 16비트 + 포트 16비트 = 32비트로 매칭 난도를 올린다. 대부분의 resolver가 이미 적용하고 있다.

0x20 인코딩. 질의 도메인 이름의 대소문자를 랜덤하게 섞어서 보낸다. `eXaMpLe.CoM` 같은 식. 권위 서버가 받은 그대로 응답하기 때문에 응답에서 대소문자 패턴이 안 맞으면 위조로 본다. 추가 엔트로피.

DNSSEC. 응답에 서명이 붙으면 위조된 캐시는 검증에서 떨어진다. 가장 본질적인 해법이다. 다만 권위 서버와 resolver 양쪽이 다 지원해야 한다.

QNAME minimization. resolver가 root에는 root 정보만, TLD에는 TLD 정보만 묻는다. 전체 질의 이름을 모든 단계에 노출하지 않는다. 직접적인 캐시 오염 방어라기보다 정보 노출 최소화 차원이다.

## DNS Hijacking

광범위한 용어다. 보통 다음 중 하나를 가리킨다.

라우터/단말 DNS 설정 변조. 멀웨어가 가정용 라우터의 DNS 서버를 공격자 IP로 바꿔치는 사례가 흔하다. 이러면 모든 도메인 질의가 공격자를 거친다. HTTPS가 깔려있으면 TLS 인증서 검증에서 막히지만, HTTP나 인증서 검증을 안 하는 앱은 그대로 뚫린다.

권위 네임서버 변조. 도메인 등록기관 계정이 탈취되면 NS 레코드 자체를 공격자 서버로 바꾼다. 2018년 MyEtherWallet이 이렇게 당해서 사용자 자금이 탈취됐다. 등록기관 계정에 MFA를 거는 게 첫 단계다. 추가로 registrar lock(transfer lock)을 걸어두면 계정이 뚫려도 도메인을 다른 등록기관으로 옮기지 못한다.

BGP 하이재킹 + DNS. 공격자가 권위 네임서버 IP 대역을 BGP로 가로채면 DNS 응답 자체를 공격자가 만든다. AWS Route 53 IP 대역이 이렇게 당한 사례가 있다(2018년 MyEtherWallet 사건의 또 다른 측면).

CAA 레코드(Certification Authority Authorization)를 같이 걸어두는 게 최근의 흐름이다. 도메인이 어느 CA에서 인증서를 발급받을 수 있는지 DNS에 명시한다. DNS가 일시적으로 탈취돼도 공격자가 임의의 CA에서 인증서를 못 받는다.

```
example.com.  IN  CAA  0 issue "letsencrypt.org"
example.com.  IN  CAA  0 issuewild ";"
example.com.  IN  CAA  0 iodef "mailto:security@example.com"
```

`issuewild ";"`는 와일드카드 인증서 발급을 모두 차단한다는 의미다.

## Dangling CNAME과 서브도메인 Takeover

운영하다 보면 가장 자주 마주치는 DNS 보안 사고다. 흐름은 단순하다.

```
1. blog.example.com  CNAME  myblog.heroku.com
2. Heroku 앱 삭제, DNS 레코드는 그대로 둠
3. 공격자가 myblog.heroku.com 이름을 다시 등록
4. blog.example.com에 접속하면 공격자 콘텐츠가 뜸
5. 게다가 example.com 도메인의 신뢰성이 그대로 묻어감
   - 쿠키 *.example.com 도 공격 가능
   - SSO 콜백 도메인이면 인증 토큰 탈취도 가능
```

문제가 큰 건 단순히 페이지가 바뀌는 데서 끝나지 않는다는 점이다. `*.example.com` 도메인의 쿠키가 같이 노출되고, OAuth redirect URI나 SAML ACS URL이 그 서브도메인을 가리키고 있으면 인증 토큰까지 새 나간다. 이메일 SPF 정책에 그 서브도메인이 포함돼 있으면 피싱 메일 발송에도 쓰인다.

표적이 되는 서비스는 클라우드 호스팅, CDN, 정적 사이트 호스팅 전반이다. AWS S3 버킷, Azure 앱, Heroku, GitHub Pages, Netlify, Vercel, Fastly 등에서 다 사례가 나왔다. 핵심은 "내가 점유했던 서비스 측 이름을 다른 사람이 다시 점유 가능한가"다. S3 버킷 이름은 글로벌 유니크지만 한 번 삭제되면 누구나 다시 만든다.

### 탐지

운영 중인 도메인의 모든 CNAME을 주기적으로 스캔해서 다음을 확인한다. NXDOMAIN으로 떨어지는 CNAME 타깃이 있는가. 타깃 도메인이 알려진 takeover 가능 서비스 목록에 들어가는가. HTTP 응답에 "There isn't a GitHub Pages site here", "NoSuchBucket" 같은 시그니처가 뜨는가.

```bash
# CNAME 체이닝 추적
dig +short blog.example.com CNAME
dig +short myblog.heroku.com

# 응답이 없으면 dangling
dig blog.example.com
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; ANSWER SECTION:
blog.example.com.  300  IN  CNAME  myblog.heroku.com.
;; AUTHORITY SECTION:
heroku.com.  900  IN  SOA  ns1.heroku.com. ...
;; (myblog.heroku.com에 대한 A 레코드 없음)
```

오픈소스로는 `subjack`, `subzy`, `nuclei`의 takeover 템플릿이 자주 쓰인다. 사내 자산 관리 시스템에 도메인/CNAME 인벤토리를 두고 변경 시 자동 검증하는 게 가장 안정적이다.

### 운영 절차로 막기

서비스를 내릴 때 DNS 레코드를 먼저 지우고 그 다음에 호스팅을 해제한다. 순서를 거꾸로 하면 잠깐 사이에 공격자가 끼어들 수 있다. 사내에서 도메인 인벤토리와 호스팅 인벤토리를 같은 시스템에서 관리하면 누락이 줄어든다. 서브도메인을 함부로 안 만드는 것도 방법이다. 일회성 마케팅 페이지가 만든 `event-2024.example.com` 같은 것들이 나중에 dangling 후보가 된다.

## 운영 환경에서의 우선순위

DNS 보안을 한 번에 다 갖추기는 어렵다. 보통 다음 순서로 잡아 나간다.

1. 도메인 등록기관 계정 MFA, registrar lock, CAA 레코드. 이건 비용이 거의 없고 효과는 크다.
2. 모든 서브도메인의 dangling CNAME 인벤토리 점검. 사고 사례가 가장 많은 영역이다.
3. 사내 resolver에 DoT 또는 DoH 적용. private IP 응답 필터링 활성화.
4. 권위 도메인에 DNSSEC 적용. 자동 키 롤오버와 모니터링이 같이 가야 한다.
5. 클라이언트 단 DoH/DoT 정책. 사내 도메인 split-horizon 처리.

DNSSEC를 가장 늦게 두는 이유는 운영 부담 때문이다. 키 롤오버 사고 한 번이면 도메인 전체가 SERVFAIL로 죽는다. 다른 항목을 먼저 잡고 모니터링 체계가 갖춰진 다음에 들어가는 게 안전하다.

## 참고 자료

- RFC 4033, 4034, 4035 — DNSSEC
- RFC 7858 — DNS over TLS
- RFC 8484 — DNS over HTTPS
- RFC 6797 — HSTS (DNS 단독으로 못 막는 부분 보완)
- RFC 6844 — CAA 레코드
- Kaminsky DNS attack (2008) — 캐시 오염 사례
- Slack DNSSEC 장애 (2021-09) — 서명 만료 사례
