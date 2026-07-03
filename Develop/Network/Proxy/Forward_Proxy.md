---
title: 포워드 프록시 (Forward Proxy)
tags: [network, proxy, forward-proxy, squid, no-proxy, pac, ssl-intercept, http-connect]
updated: 2026-05-24
---

# 포워드 프록시 (Forward Proxy)

포워드 프록시는 클라이언트가 바깥으로 나갈 때 대신 나가주는 서버다. 사내망에서 일하다 보면 인터넷이 전부 프록시를 거치도록 강제된 환경을 자주 만난다. 직접 나가는 길은 방화벽이 막아두고, 프록시 포트(보통 3128, 8080)만 열어준다. 그래야 회사가 외부 통신을 한곳에서 통제하고 로그를 남긴다.

여기서는 포워드 프록시를 직접 띄우는 쪽(Squid 설정, ACL, 인증)과 그 프록시를 거쳐 나가야 하는 쪽(환경변수, 애플리케이션별 적용, 인증서 신뢰)을 같이 다룬다. 사내 개발자는 양쪽을 다 겪는다. 프록시를 운영하는 입장과 프록시 뒤에서 `npm install`이 안 되는 입장 둘 다 된다.

요청이 흐르는 기본 모양과 포워드/리버스 구분은 [프록시 개요](Proxy.md)에 정리했다. 이 문서는 포워드 프록시를 실제로 굴릴 때 부딪히는 설정과 장애에 집중한다.

## Squid 설정과 ACL 접근 제어

Squid는 포워드 프록시의 사실상 표준이다. 최소 설정으로 띄우는 법은 개요 문서에 있으니, 여기서는 실제 운영에서 쓰는 ACL을 본다. 사내 프록시를 운영하면 "그냥 다 열어줘"로 끝나는 경우는 거의 없다. 누가, 어디로, 언제 나갈 수 있는지를 ACL로 잘게 나눈다.

ACL은 "조건에 이름을 붙이는 것"이고, `http_access`가 그 이름들을 조합해 허용/거부를 결정한다. 자주 쓰는 ACL 타입은 이렇다.

```
# /etc/squid/squid.conf
http_port 3128

# 출발지 IP 대역
acl localnet src 192.168.0.0/16
acl devnet   src 192.168.10.0/24

# 목적지 도메인 (.facebook.com 은 www.facebook.com, m.facebook.com 모두 매칭)
acl social   dstdomain .facebook.com .instagram.com .youtube.com

# 목적지 포트
acl SSL_ports port 443
acl Safe_ports port 80 443 21 70 210 1025-65535

# 메서드
acl CONNECT method CONNECT

# 근무 시간 (월~금 09:00~18:00)
acl work_hours time MTWHF 09:00-18:00
```

규칙을 거는 순서가 동작을 결정한다. Squid는 `http_access`를 위에서 아래로 읽다가 처음 매칭되는 줄에서 멈추고 거기서 끝낸다. 그래서 좁고 구체적인 규칙을 위에, 넓은 규칙을 아래에 둔다.

```
# CONNECT는 443으로만 허용 (다른 포트 터널링 차단)
http_access deny CONNECT !SSL_ports
http_access deny !Safe_ports

# 근무 시간엔 SNS 차단
http_access deny social work_hours

# 사내망 허용
http_access allow localnet

# 나머지 전부 거부
http_access deny all
```

`http_access deny social work_hours` 줄에서 두 ACL을 나란히 적으면 AND다. 둘 다 참일 때만 매칭된다. 그러니 "근무 시간이면서 목적지가 SNS"일 때만 막고, 점심시간이나 퇴근 후에는 통과시킨다. OR로 묶고 싶으면 한 acl 줄에 값을 여러 개 적거나 acl 이름을 여러 개 만들어 각각 deny 줄을 둔다.

가장 자주 하는 실수가 `http_access deny all`을 위로 올려두는 것이다. 그러면 그 아래 allow는 영원히 평가되지 않아서 사내망 요청까지 전부 403이 된다. 막히면 추측하지 말고 access.log를 본다.

```bash
tail -f /var/log/squid/access.log
# 1716500000.123  0 192.168.0.55 TCP_DENIED/403 ... GET http://example.com/
```

`TCP_DENIED/403`이면 ACL에서 걸린 것이다. 어떤 줄에서 걸렸는지 모르겠으면 `debug_options ALL,1 33,2`를 켜고 cache.log에서 매칭 과정을 본다. 설정을 바꾼 뒤에는 항상 `squid -k parse`로 문법을 검사하고 `squid -k reconfigure`로 무중단 반영한다. `restart`는 진행 중인 연결을 끊으니 운영 중에는 reconfigure를 쓴다.

## 프록시 인증 (basic auth)

회사 정책상 "프록시를 쓰려면 사번/비밀번호를 넣어라"는 환경이 흔하다. Squid는 외부 인증 헬퍼 프로그램에 아이디/비밀번호를 넘겨 검증하는 구조다. 가장 단순한 게 파일 기반 basic 인증이다.

```
# basic_ncsa_auth 헬퍼 + 비밀번호 파일
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwords
auth_param basic realm Corporate Proxy
auth_param basic credentialsttl 2 hours

# 인증된 사용자만 통과
acl authenticated proxy_auth REQUIRED
http_access allow authenticated
http_access deny all
```

헬퍼 경로는 배포판마다 다르다. 데비안 계열은 `/usr/lib/squid/basic_ncsa_auth`, RHEL 계열은 `/usr/lib64/squid/basic_ncsa_auth`인 경우가 많다. 경로가 틀리면 Squid가 뜨긴 하는데 인증만 전부 실패하고, cache.log에 헬퍼 실행 오류가 찍힌다. 비밀번호 파일은 아파치 htpasswd로 만든다.

```bash
# -c 는 파일을 새로 만든다. 이미 있으면 -c 빼고 추가만
htpasswd -c /etc/squid/passwords alice
htpasswd /etc/squid/passwords bob
```

실무에서 basic 인증의 함정은 비밀번호가 평문에 가깝게 흐른다는 점이다. basic은 `사용자:비밀번호`를 Base64로 인코딩만 한 값을 매 요청 `Proxy-Authorization` 헤더에 실어 보낸다. 암호화가 아니라 인코딩이라 프록시까지 가는 구간이 평문이면 그대로 노출된다. 그래서 사내망 안쪽이라는 전제로 쓰거나, 회사 LDAP/AD에 붙이는 `basic_ldap_auth`, 커버로스 같은 다른 헬퍼로 넘어간다.

클라이언트가 인증 정보를 넣는 방법은 도구마다 다른데, 환경변수 URL에 박는 게 가장 범용적이다.

```bash
curl -x http://alice:secret@192.168.0.10:3128 http://example.com
export http_proxy=http://alice:secret@192.168.0.10:3128
```

비밀번호에 `@`나 `:`, `/`가 들어가면 URL 인코딩해야 한다. `@`는 `%40`, `:`은 `%3A`다. 비밀번호에 특수문자가 있는데 인코딩을 안 하면 프록시 호스트를 엉뚱하게 파싱해서 "프록시에 못 붙는다"는 증상으로 나타난다. 인증 실패는 프록시가 `407 Proxy Authentication Required`로 답하니, curl `-v`에서 407이 보이면 인증 문제다. 503이나 연결 거부면 인증 이전의 네트워크 문제다.

## http_proxy / https_proxy / no_proxy 환경변수

프록시 뒤에서 일하는 쪽으로 넘어온다. 리눅스/맥에서 명령행 도구 대부분은 이 세 환경변수를 본다.

```bash
export http_proxy=http://192.168.0.10:3128     # http:// 요청에 쓸 프록시
export https_proxy=http://192.168.0.10:3128    # https:// 요청에 쓸 프록시 (CONNECT)
export no_proxy=localhost,127.0.0.1,.internal.corp,10.0.0.0/8
```

`https_proxy`의 값도 보통 `http://`로 시작한다. 이건 "프록시까지는 평문 HTTP로 붙고, 그 위에서 CONNECT로 HTTPS 터널을 뚫는다"는 뜻이라 모순이 아니다. 프록시 자체가 HTTPS를 받는(`https://` 프록시) 환경은 드물다.

대소문자가 골치다. 역사적으로 소문자 `http_proxy`가 먼저 쓰였고, 많은 도구가 대문자 `HTTP_PROXY`도 같이 본다. 그런데 `HTTP_PROXY`는 CGI 환경에서 클라이언트가 보낸 `Proxy:` 헤더가 환경변수로 둔갑하는 httpoxy 취약점 때문에, 서버 사이드 HTTP 라이브러리 일부는 `HTTP_PROXY`를 의도적으로 무시한다. 그래서 소문자로 통일하는 습관이 안전하다. `https_proxy`는 이 문제와 무관하니 대소문자 둘 다 흔히 인식된다.

`no_proxy`가 사내망 장애의 단골이다. 여기 적은 목적지는 프록시를 거치지 않고 직접 나간다. 형식이 도구마다 미묘하게 다르다.

- 도메인은 보통 suffix 매칭이다. `.internal.corp`로 적으면 `api.internal.corp`, `db.internal.corp`가 다 우회된다. 앞에 점을 찍는 관례가 있는데, 점 없이 `internal.corp`만 적어도 인식하는 도구가 많다.
- `localhost`와 `127.0.0.1`은 명시적으로 넣어야 한다. 자동으로 빠지지 않는 도구가 있다.
- CIDR(`10.0.0.0/8`)은 지원이 들쭉날쭉하다. curl은 비교적 최근 버전부터 CIDR을 받지만, 많은 라이브러리는 CIDR을 못 읽고 정확한 IP 문자열만 매칭한다. 그래서 "no_proxy에 대역을 넣었는데 내부 IP 호출이 여전히 프록시로 샌다"는 일이 생긴다.
- 와일드카드 `*`는 표준이 아니다. `*.internal.corp`처럼 적으면 안 먹는 도구가 더 많다. 점 prefix로 적는 게 호환성이 높다.

## 애플리케이션별 프록시 적용 차이

여기가 사내망에서 가장 많은 시간을 잡아먹는 곳이다. "curl은 되는데 npm은 안 된다", "터미널에선 되는데 sudo로 하면 안 된다" 같은 증상이 전부 도구마다 프록시를 읽는 방식이 다른 데서 온다.

**curl / wget** — 환경변수를 그대로 읽는다. curl은 `http_proxy`/`https_proxy`/`no_proxy`를 보고, `-x`(`--proxy`)와 `--noproxy`로 덮어쓴다. wget은 `http_proxy`/`https_proxy`를 보지만 `use_proxy=on`이 꺼져 있으면 무시하고, `~/.wgetrc`나 `/etc/wgetrc`의 설정이 우선하기도 한다. wget이 환경변수를 무시하는 것 같으면 wgetrc를 먼저 의심한다.

**apt** — 여기서 많이 막힌다. apt는 환경변수가 아니라 자체 설정 파일을 본다.

```
# /etc/apt/apt.conf.d/95proxy
Acquire::http::Proxy  "http://192.168.0.10:3128";
Acquire::https::Proxy "http://192.168.0.10:3128";
```

게다가 apt는 보통 `sudo`로 돌리는데, `sudo`는 기본적으로 환경변수를 자식 프로세스에 안 넘긴다. 그래서 본인 셸에서 `export http_proxy`를 해도 `sudo apt update`는 프록시를 못 본다. 임시로는 `sudo -E apt update`로 환경을 넘기거나, 위처럼 apt.conf에 박는다. 운영 서버는 apt.conf에 고정하는 쪽이 깔끔하다.

**git** — 프로토콜이 둘이라 헷갈린다. `git clone https://...`는 HTTP(S) 위에서 도니까 git 설정을 본다.

```bash
git config --global http.proxy  http://192.168.0.10:3128
git config --global https.proxy http://192.168.0.10:3128
# 특정 호스트만 우회
git config --global http.https://github.example.com.proxy ""
```

git도 `http_proxy` 환경변수를 보긴 하는데, 사내 git 서버는 우회하고 외부 GitHub만 프록시로 보내는 식의 분기가 필요해서 보통 git config로 잡는다. 반면 `git clone git@...` 같은 SSH 프로토콜은 HTTP 프록시 설정과 완전히 무관하다. SSH는 `~/.ssh/config`의 `ProxyCommand`(예: `nc -X connect -x proxy:3128 %h %p`)로 따로 터널링해야 한다. "https clone은 되는데 ssh clone은 안 된다"면 이 차이다.

**npm** — 환경변수도 보지만 `.npmrc`가 우선한다.

```bash
npm config set proxy       http://192.168.0.10:3128
npm config set https-proxy http://192.168.0.10:3128
npm config set noproxy     localhost,.internal.corp
```

npm은 옛날엔 `https-proxy`(하이픈)였다가 환경변수는 `https_proxy`(언더바)라 표기가 헷갈린다. 그리고 사내 레지스트리(`registry` 설정)를 쓰는데 그 레지스트리를 no_proxy에 안 넣으면, 내부 레지스트리 요청까지 외부 프록시로 나가서 실패한다. yarn, pnpm도 각자 설정 키가 따로 있다.

**Java(JVM)** — JVM은 `http_proxy` 환경변수를 보지 않는다. 무조건 시스템 프로퍼티로 넘겨야 한다.

```bash
java -Dhttp.proxyHost=192.168.0.10 -Dhttp.proxyPort=3128 \
     -Dhttps.proxyHost=192.168.0.10 -Dhttps.proxyPort=3128 \
     -Dhttp.nonProxyHosts="localhost|127.0.0.1|*.internal.corp" \
     -jar app.jar
```

여기엔 함정이 셋 있다. `nonProxyHosts`의 구분자는 콤마가 아니라 파이프(`|`)다. 그리고 와일드카드 `*`를 쓸 수 있는데 prefix/suffix에서만 동작한다. 마지막으로 `http.nonProxyHosts`와 `https.nonProxyHosts`가 따로라, https 쪽 우회 목록을 안 넣으면 https 호출만 프록시로 새는 경우가 있다. Gradle/Maven은 빌드 도구가 또 자기 설정(`gradle.properties`의 `systemProp.http.proxyHost`, Maven `settings.xml`)을 따로 보니, 빌드는 프록시를 타는데 실행 중인 앱은 안 타거나 그 반대가 생긴다.

도구마다 프록시 출처가 이렇게 갈린다.

| 도구 | 프록시 출처 | 우선순위 메모 |
|------|------------|--------------|
| curl | 환경변수, `-x` | `-x`가 환경변수보다 우선 |
| wget | 환경변수, wgetrc | `use_proxy` 꺼지면 무시 |
| apt | apt.conf | 환경변수 안 봄, sudo가 env 가로챔 |
| git(https) | git config http.proxy | 환경변수도 보지만 config 우선 |
| git(ssh) | ~/.ssh/config ProxyCommand | HTTP 프록시와 무관 |
| npm | .npmrc, 환경변수 | .npmrc 우선, 사내 registry는 noproxy |
| Java | -D 시스템 프로퍼티 | 환경변수 안 봄, nonProxyHosts는 `\|` 구분 |

## HTTPS는 CONNECT로 터널을 뚫는다

평문 HTTP는 프록시가 요청 라인을 읽고 목적지로 전달한다. HTTPS는 프록시가 내용을 못 읽으니 `CONNECT`로 TCP 통로만 연다. 클라이언트가 `CONNECT example.com:443`을 보내면 프록시가 그 목적지에 TCP를 연결하고 `200 Connection Established`로 답한 뒤, 그때부터 양쪽 바이트를 그대로 중계만 한다. TLS 핸드셰이크와 암호문은 프록시를 통과만 하고 프록시는 안을 못 본다. 동작 흐름과 Squid에서 CONNECT 포트를 443으로 제한하는 이유는 [개요 문서의 CONNECT 절](Proxy.md#https-http-connect)에 자세히 있다.

포워드 프록시 운영에서 기억할 건, CONNECT가 200을 못 받으면 프록시가 그 목적지/포트를 막은 것이고, 200은 받았는데 그 뒤 TLS에서 실패하면 프록시가 아니라 원서버 인증서 문제라는 점이다. 단, 회사 프록시가 SSL 인터셉트를 켜둔 경우는 얘기가 달라지는데, 그게 다음 절이다.

## 투명 프록시와 PAC 파일

지금까지는 클라이언트가 프록시 주소를 직접 아는 명시적(explicit) 프록시였다. 클라이언트가 프록시 존재를 모르게 하거나, 프록시 주소를 일일이 설정하지 않게 하는 방법이 둘 있다.

### 투명(transparent) 프록시

게이트웨이에서 나가는 80/443 트래픽을 방화벽 규칙으로 프록시에 강제로 꺾는 방식이다. 클라이언트는 자기가 직접 나가는 줄 알지만 실제로는 프록시를 거친다. Squid는 intercept 모드로 받는다.

```
# 일반 프록시 포트와 별도로 가로채기용 포트를 둔다
http_port 3128
http_port 3129 intercept
```

```bash
# 라우터/게이트웨이에서 80 트래픽을 Squid로 리다이렉트 (예시)
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 3129
```

투명 프록시의 한계가 HTTPS다. 클라이언트는 자기가 프록시를 거치는 줄 모르니 CONNECT를 보내지 않는다. 그래서 프록시는 TLS의 ClientHello에 담긴 SNI(접속하려는 호스트 이름)를 엿봐서 목적지를 알아내는 정도만 한다. 내용을 보려면 SSL 인터셉트가 필요하고, 그건 인증서 신뢰 문제를 동반한다. 투명 프록시는 인증 헤더를 받을 자리가 없어서 사용자 인증이 어렵다는 점도 알아둬야 한다.

### PAC 파일

PAC(Proxy Auto-Config)는 자바스크립트 함수 하나로 "이 URL은 프록시로, 저 URL은 직접" 같은 규칙을 브라우저/OS에 내려주는 방식이다. 사내 도메인은 직접 나가고 외부만 프록시로 보내는 분기를 한곳에서 관리한다.

```javascript
function FindProxyForURL(url, host) {
    // 점 없는 호스트(intranet)나 사내 도메인은 직접
    if (isPlainHostName(host) || dnsDomainIs(host, ".internal.corp"))
        return "DIRECT";

    // 사내 IP 대역은 직접
    if (isInNet(host, "10.0.0.0", "255.0.0.0"))
        return "DIRECT";

    // 나머지는 프록시로, 실패하면 직접
    return "PROXY 192.168.0.10:3128; DIRECT";
}
```

`FindProxyForURL`이 반환하는 문자열이 결과다. `DIRECT`는 프록시 우회, `PROXY host:port`는 프록시 경유, 세미콜론으로 폴백을 이어 적는다. PAC 파일을 웹서버에 올리고 그 URL을 클라이언트에 지정하거나, WPAD(`http://wpad/wpad.dat`)로 자동 발견하게 한다. 운영하다 보면 PAC를 application/x-ns-proxy-autoconfig MIME 타입으로 서빙해야 일부 클라이언트가 인식하는 점, `isInNet`이 DNS 조회를 유발해 느려질 수 있는 점이 걸린다. 그래서 도메인 매칭(`dnsDomainIs`, `shExpMatch`)을 IP 매칭보다 앞에 둔다.

명령행 도구 대부분은 PAC를 직접 해석하지 못한다. PAC는 브라우저/OS용이고, curl이나 npm은 결국 `http_proxy` 환경변수를 봐야 한다. 그래서 사내 PC는 PAC로 굴러가는데 서버에서 돌리는 스크립트는 환경변수를 따로 잡아줘야 하는 이원화가 생긴다.

## 사내망에서 자주 겪는 문제

### no_proxy 누락으로 내부 호출까지 프록시 경유

가장 흔한 사고다. `http_proxy`만 설정하고 `no_proxy`를 비워두면, 내부 서비스 호출까지 전부 외부 프록시로 나간다. 증상은 둘로 나뉜다. 프록시가 내부 도메인을 DNS로 못 풀어서 즉시 실패하거나, 풀긴 하는데 모든 내부 트래픽이 프록시를 한 번 왕복해서 응답이 느려진다. 헬스체크나 서비스 간 호출이 갑자기 느려졌는데 코드는 안 바뀌었다면 no_proxy를 의심한다.

```bash
# 내부 도메인, 사내 대역, 로컬을 빠짐없이 넣는다
export no_proxy=localhost,127.0.0.1,::1,.internal.corp,.svc.cluster.local,10.0.0.0/8,169.254.169.254
```

쿠버네티스 환경이면 `.svc.cluster.local`(클러스터 내부 도메인)과 파드/서비스 대역을 반드시 no_proxy에 넣는다. 안 넣으면 파드끼리 통신이 외부 프록시로 새서 클러스터가 이상하게 느려진다. 클라우드라면 메타데이터 주소 `169.254.169.254`도 우회시킨다. 이게 프록시로 가면 인스턴스 메타데이터/자격증명 조회가 깨진다.

CIDR을 no_proxy에 넣었는데도 내부 IP 호출이 새면, 그 도구가 CIDR을 해석 못 하는 경우다. 앞서 적었듯 많은 라이브러리는 정확한 IP 문자열만 매칭한다. 이럴 땐 도메인 기반으로 우회시키거나, 애플리케이션 코드에서 no_proxy 처리 라이브러리를 명시적으로 쓴다.

진단은 어디로 나가는지 직접 보는 게 빠르다.

```bash
# 내부 주소가 프록시로 새는지 확인
curl -v http://internal-api.internal.corp/health 2>&1 | grep -i "connected to"
# Connected to internal-api.internal.corp (10.0.1.5) port 80   ← 직접 나감, 정상
# Connected to 192.168.0.10 (192.168.0.10) port 3128           ← 프록시로 샘, no_proxy 누락
```

`Connected to`에 찍힌 게 프록시 IP면 그 요청은 프록시를 타고 있다. no_proxy를 고친 뒤 이 줄이 목적지 IP로 바뀌는지 확인한다.

### SSL 인터셉트 인증서 신뢰 오류

보안 정책이 강한 회사는 프록시가 HTTPS도 들여다본다. 프록시가 클라이언트와 외부 서버 사이에 끼어, 외부 서버와는 자기가 맺은 TLS로 통신하고, 클라이언트에게는 회사 CA로 즉석에서 위조한 인증서를 내민다. 그러면 프록시가 평문을 다 보고 검사·로깅한다. 이걸 SSL 인터셉트(Squid의 ssl_bump, 또는 SSL 검사라고 부른다)라 한다.

```mermaid
sequenceDiagram
    participant C as 클라이언트
    participant P as 프록시(SSL 인터셉트)
    participant S as 외부 서버

    C->>P: CONNECT github.com:443
    P->>S: TLS 핸드셰이크 (프록시가 클라이언트 역할)
    S-->>P: 진짜 github.com 인증서
    P-->>C: 회사 CA로 위조한 github.com 인증서
    Note over C,P: 클라이언트가 회사 CA를 신뢰해야 통과
    C->>P: 암호화 요청 (프록시가 복호화해 검사)
    P->>S: 다시 암호화해서 전달
```

문제는 클라이언트가 그 위조 인증서를 발급한 회사 CA를 신뢰하지 않으면 인증서 검증에 실패한다는 점이다. 브라우저는 회사가 PC에 회사 CA를 미리 깔아둬서 조용히 통과하는데, 명령행 도구와 런타임은 각자 신뢰 저장소가 따로라 깔아준 적이 없어서 깨진다. 증상이 도구마다 다른 에러로 나온다.

```
curl: (60) SSL certificate problem: unable to get local issuer certificate
npm ERR! ... SELF_SIGNED_CERT_IN_CHAIN
git: SSL certificate problem: self signed certificate in certificate chain
Java: PKIX path building failed: ... unable to find valid certification path
Python: certificate verify failed: unable to get local issuer certificate
```

핵심은 OS 신뢰 저장소에 회사 CA를 넣어도 모든 도구가 고쳐지지 않는다는 것이다. 도구마다 보는 신뢰 저장소가 다르다. 우선 회사 CA 인증서(PEM)를 받아서 도구별로 신뢰시킨다.

```bash
# OS 저장소 (데비안 계열) — curl, wget 등 OS 저장소를 보는 도구가 고쳐짐
sudo cp corp-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# curl 개별 지정
curl --cacert /path/corp-ca.pem https://github.com
export CURL_CA_BUNDLE=/path/corp-ca.pem

# git
git config --global http.sslCAInfo /path/corp-ca.pem

# Node/npm — Node는 OS 저장소를 안 본다
export NODE_EXTRA_CA_CERTS=/path/corp-ca.pem
npm config set cafile /path/corp-ca.pem

# Python requests — certifi 번들을 따로 본다
export REQUESTS_CA_BUNDLE=/path/corp-ca.pem

# Java — 별도 truststore(cacerts)에 import 해야 한다
keytool -importcert -alias corp-ca -file corp-ca.crt \
  -keystore $JAVA_HOME/lib/security/cacerts -storepass changeit
```

급할 때 검증을 끄는 옵션(`curl -k`, `npm config set strict-ssl false`, `git -c http.sslVerify=false`)이 있지만, 이건 SSL 인터셉트와 진짜 중간자 공격을 구분 못 하게 만드는 거라 임시 진단 외엔 쓰면 안 된다. 검증을 끄면 당장은 되니까 그대로 방치되는 경우가 많은데, 그러면 프록시가 아닌 다른 누가 가로채도 알 수가 없다. 회사 CA를 제대로 신뢰시키는 게 정답이다.

Node가 OS 저장소를 안 본다는 점, Java가 cacerts라는 완전히 별도의 truststore를 본다는 점 이 둘만 기억해도 사내에서 "왜 curl은 되는데 빌드는 인증서 오류가 나지"의 절반은 설명된다.

## 참고

- [Squid 공식 문서](http://www.squid-cache.org/Doc/)
- [Squid ACL 설정](https://wiki.squid-cache.org/SquidFaq/SquidAcl)
- [PAC 파일 함수 레퍼런스 (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Proxy_servers_and_tunneling/Proxy_Auto-Configuration_PAC_file)
- [RFC 9110 - HTTP Semantics (CONNECT 메서드)](https://datatracker.ietf.org/doc/html/rfc9110#section-9.3.6)
- [프록시 개요 문서](Proxy.md)
