---
title: 호스트 방화벽 (iptables / nftables)
tags: [network, firewall, iptables, nftables, netfilter, packet-filter, troubleshooting]
updated: 2026-06-21
---

# 호스트 방화벽 (iptables / nftables)

## 정의

방화벽은 네트워크 인터페이스를 드나드는 패킷을 헤더 정보로 보고 통과시킬지 떨굴지 결정하는 장치다. 여기서 다루는 건 라우터나 클라우드 보안 그룹 같은 경계 장비가 아니라 리눅스 서버 한 대 안에서 도는 호스트 레벨 방화벽이다. 클라우드를 쓰면 보안 그룹이 인스턴스 앞단을 막아주지만, 보안 그룹은 클라우드 사업자의 가상 네트워크 계층에서 동작하고 호스트 방화벽은 OS 커널 안에서 동작한다. 둘은 다른 층위라 한쪽이 허용해도 다른 쪽이 막으면 패킷은 못 들어온다. 온프레미스 서버나 보안 그룹을 못 쓰는 환경에서는 호스트 방화벽이 유일한 차단 수단이 된다.

리눅스에서 패킷 필터링은 커널의 netfilter 프레임워크가 한다. iptables와 nftables는 그 netfilter에 룰을 집어넣는 사용자 공간 도구일 뿐이다. iptables가 오래된 인터페이스고 nftables가 후속이다. 최근 배포판(RHEL 8+, Debian 10+, Ubuntu 20.04+)은 nftables를 기본 백엔드로 쓰지만 `iptables` 명령은 호환 레이어(`iptables-nft`)를 통해 그대로 동작한다. 그래서 실무에서는 두 문법을 다 마주치게 된다.

---

## 테이블과 체인의 구조

netfilter는 룰을 테이블(table)로 묶고, 각 테이블 안에 체인(chain)을 둔다. 테이블은 "무슨 종류의 처리를 하느냐"로 나뉜다.

- `filter`: 패킷을 통과/차단하는 본래의 방화벽 테이블. 디폴트 테이블이라 `iptables -t filter`를 생략하면 여기에 룰이 들어간다.
- `nat`: 주소·포트 변환. SNAT, DNAT, MASQUERADE가 여기 있다. 자세한 동작은 [NAT 문서](../NAT.md)에서 다룬다.
- `mangle`: 패킷 헤더 필드(TOS, TTL, 마킹) 조작.
- `raw`: conntrack을 타기 전에 패킷을 처리. `NOTRACK`으로 특정 트래픽을 연결 추적에서 빼는 용도.

호스트 방화벽 룰을 쓸 때 99%는 `filter` 테이블만 건드린다. 나머지 테이블은 NAT을 하거나 특수한 패킷 마킹이 필요할 때만 손댄다.

체인은 패킷이 커널을 지나가는 길목이다. `filter` 테이블에는 세 개의 기본 체인이 있다.

- `INPUT`: 이 호스트 자신이 최종 목적지인 패킷. 외부에서 우리 서버의 22번, 80번 포트로 들어오는 게 여기 걸린다.
- `OUTPUT`: 이 호스트가 만들어 내보내는 패킷. 서버가 외부 API를 호출하거나 DB에 접속하는 게 여기.
- `FORWARD`: 이 호스트를 거쳐 다른 곳으로 지나가는 패킷. 라우터나 게이트웨이, 도커 호스트, 쿠버네티스 노드에서 중요하다. 일반 애플리케이션 서버는 패킷을 포워딩하지 않으니 FORWARD 체인이 비어 있는 경우가 많다.

## 패킷이 어느 체인을 타는지

패킷이 어느 체인을 통과하느냐는 그 패킷의 목적지가 어디냐로 갈린다. 라우팅 판단(routing decision)을 기준으로 갈라진다.

```
                    들어온 패킷
                        │
                  ┌─────┴─────┐
                  │ 라우팅 판단 │
                  └─────┬─────┘
            목적지가 나 자신   목적지가 다른 호스트
                  │                   │
               INPUT              FORWARD
                  │                   │
              로컬 프로세스            │
                  │                   │
               OUTPUT ───────────────┤
                  │                   │
                  └────────┬──────────┘
                           │
                      나가는 패킷
```

여기서 자주 헷갈리는 지점이 있다. 외부에서 우리 서버로 들어와서 응답을 돌려보내는 경우, 들어오는 패킷은 INPUT, 응답 패킷은 OUTPUT을 탄다. INPUT만 열고 OUTPUT을 안 봤다가 응답이 막히는 실수가 가끔 나온다. 그래서 OUTPUT 체인 정책을 함부로 DROP으로 두면 안 된다.

또 하나, 들어오는 트래픽을 막는다고 FORWARD를 건드리는 경우가 있는데, 서버 자신으로 들어오는 트래픽은 FORWARD가 아니라 INPUT을 탄다. FORWARD는 그 서버를 경유만 하는 패킷용이다. 도커를 깔면 도커가 FORWARD 체인에 자기 룰을 잔뜩 집어넣는데, 컨테이너로 들어가는 트래픽이 호스트 입장에서는 "지나가는 패킷"이라 FORWARD를 타기 때문이다. 호스트에서 컨테이너 트래픽이 이상하면 INPUT이 아니라 FORWARD를 봐야 한다.

---

## 룰의 구조와 매칭 방식

체인은 룰의 목록이고, 패킷은 체인에 들어오면 룰을 위에서부터 순서대로 본다. 어떤 룰의 조건에 매칭되면 그 룰의 타겟(target)대로 처리하고, 보통 거기서 체인 평가가 끝난다. 매칭되는 룰이 하나도 없으면 체인의 기본 정책(policy)을 따른다.

타겟 중 자주 쓰는 것:

- `ACCEPT`: 통과. 이 체인에서의 평가가 끝난다.
- `DROP`: 조용히 떨군다. 송신자에게 아무 응답도 안 준다. 포트 스캔에 정보를 안 주려고 쓴다.
- `REJECT`: 떨구되 ICMP로 거부됐다고 알려준다. 클라이언트가 타임아웃까지 기다리지 않고 바로 실패한다. 내부망에서는 REJECT가 디버깅이 편하다.
- `LOG`: 패킷 정보를 커널 로그에 남기고 다음 룰로 넘어간다. 평가를 끝내지 않는 게 특징이라 LOG 다음에 실제 차단 룰이 와야 한다.

룰 하나를 보자.

```bash
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.0/8 -j ACCEPT
```

- `-A INPUT`: INPUT 체인 맨 뒤에 추가(append).
- `-p tcp`: 프로토콜이 TCP인 패킷만.
- `--dport 22`: 목적지 포트가 22.
- `-s 10.0.0.0/8`: 출발지 IP가 10.x 대역.
- `-j ACCEPT`: 매칭되면 통과.

즉 "10.x 대역에서 우리 서버 22번으로 들어오는 TCP를 허용한다"는 뜻이다. 조건은 AND로 묶인다. 하나라도 안 맞으면 이 룰은 건너뛴다.

기본 정책은 이렇게 건다.

```bash
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
```

INPUT을 DROP으로 두면 명시적으로 허용한 것만 들어온다. 화이트리스트 방식이다. 이걸 SSH 허용 룰보다 먼저 적용하면 원격 서버에서 자기 자신을 잠가버리니, 정책을 DROP으로 바꾸기 전에 SSH 허용 룰을 먼저 넣어야 한다. 이 실수로 서버에 못 들어가는 사고가 실제로 자주 난다.

---

## stateless 필터링과 stateful 필터링

초창기 패킷 필터는 패킷 하나하나를 독립적으로 봤다. 출발지/목적지 IP와 포트, 프로토콜만 보고 판단한다. 이걸 stateless라고 한다. 문제는 TCP 연결의 응답 패킷을 어떻게 허용하느냐다. 우리 서버가 외부 80번 포트로 나간 요청의 응답은 출발지 포트가 80, 목적지 포트가 우리 쪽 임의 포트(예: 54321)로 돌아온다. stateless로는 "들어오는 패킷 중 출발지 포트가 80인 건 다 허용" 같은 룰을 써야 하는데, 이러면 공격자가 출발지 포트를 80으로 위조한 패킷을 다 통과시키게 된다.

stateful 필터는 이 문제를 conntrack(연결 추적)으로 푼다. 커널이 오가는 패킷을 보고 "연결"을 식별해 상태 테이블에 올린다. 새 연결의 첫 패킷은 `NEW`, 이미 추적 중인 연결에 속하면 `ESTABLISHED`, 그 연결과 관련된 보조 연결(FTP 데이터 채널 등)이면 `RELATED`로 분류한다. conntrack의 내부 동작과 테이블 관리는 [NAT 문서](../NAT.md)에서 다루므로 여기서는 방화벽 룰에서 어떻게 쓰는지만 본다.

stateful 룰의 핵심은 이 한 줄이다.

```bash
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
```

"이미 성립된 연결과 거기 딸린 패킷은 전부 허용"이라는 뜻이다. 이 룰을 INPUT 맨 위에 두면, 우리가 내보낸 요청의 응답은 출발지 포트가 뭐든 상관없이 통과한다. 응답이 ESTABLISHED 상태로 식별되기 때문이다. 그 아래에는 새 연결(NEW)을 어떤 포트로 받을지만 정의하면 된다.

```bash
iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
```

이 다섯 줄이 호스트 방화벽의 기본 골격이다. 루프백 허용, 기존 연결 허용, 그리고 새로 받을 포트(SSH, HTTPS)만 NEW로 연다. 나머지는 기본 정책 DROP에 걸린다. 첫 번째 ESTABLISHED 룰이 위에 있어야 응답 트래픽이 빨리 통과하고, 대부분의 패킷이 이 한 룰에서 끝나서 성능에도 유리하다.

nftables로 같은 걸 쓰면 이렇게 된다.

```bash
nft add table inet filter
nft 'add chain inet filter input { type filter hook input priority 0; policy drop; }'
nft add rule inet filter input iif lo accept
nft add rule inet filter input ct state established,related accept
nft add rule inet filter input tcp dport 22 ct state new accept
nft add rule inet filter input tcp dport 443 ct state new accept
```

nftables는 한 룰에서 여러 포트·주소를 set으로 묶을 수 있고, IPv4/IPv6를 `inet` 패밀리로 한 번에 처리한다는 게 iptables와 다르다. iptables는 IPv6용으로 `ip6tables`를 따로 돌려야 한다. 이걸 잊으면 IPv4만 막고 IPv6는 뻥 뚫린 상태가 되는 사고가 난다.

---

## NAT 테이블과의 관계

filter 테이블만으로는 주소 변환을 못 한다. 포트 포워딩이나 마스커레이딩은 `nat` 테이블에서 한다. 호스트 방화벽 관점에서 알아둘 건 두 가지 체인의 처리 순서다.

들어오는 패킷은 `nat` 테이블의 `PREROUTING` 체인에서 DNAT(목적지 변환)을 먼저 거치고, 그 다음 라우팅 판단을 해서 INPUT 또는 FORWARD로 간다. 나가는 패킷은 라우팅 후 `POSTROUTING`에서 SNAT/MASQUERADE를 거친다. 그래서 filter 룰을 쓸 때는 DNAT이 끝난 뒤의 주소를 기준으로 매칭해야 한다.

예를 들어 외부 8080 포트로 들어온 걸 내부 컨테이너 192.168.1.10:80으로 DNAT한다면, FORWARD 체인의 filter 룰은 변환 후 목적지인 192.168.1.10:80을 봐야 통과시킬 수 있다. 변환 전 주소(8080)로 룰을 쓰면 매칭이 안 돼서 막힌다. 도커 포트 매핑이 안 될 때 이 순서를 모르면 한참 헤맨다. NAT 변환 자체의 동작은 [NAT 문서](../NAT.md)를 보면 된다.

전체 흐름을 한 장으로 보면 이렇다.

```
PREROUTING(nat: DNAT) → 라우팅 판단 → INPUT(filter) → 로컬 프로세스
                                    └→ FORWARD(filter) → POSTROUTING(nat: SNAT) → 나감
로컬 프로세스 → OUTPUT(filter) → POSTROUTING(nat: SNAT) → 나감
```

---

## 룰 순서 때문에 트래픽이 막히는 사례

방화벽 트러블슈팅의 절반은 룰 순서 문제다. 체인은 위에서부터 평가하고 첫 매칭에서 끝나기 때문에, 차단 룰이 허용 룰보다 위에 있으면 허용 룰은 영원히 평가되지 않는다.

흔한 사례. 운영 중에 특정 악성 IP를 급하게 막으려고 이렇게 친다.

```bash
iptables -A INPUT -s 203.0.113.50 -j DROP
```

`-A`는 맨 뒤에 추가다. 그런데 INPUT 체인 위쪽에 이미 "443번 포트 NEW 허용" 룰이 있으면, 그 악성 IP가 443으로 들어오는 트래픽은 위쪽 ACCEPT 룰에서 이미 통과돼버린다. DROP 룰까지 도달하지 못한다. 차단이 안 먹는다. 이럴 때는 맨 뒤가 아니라 앞에 넣어야 한다.

```bash
iptables -I INPUT 1 -s 203.0.113.50 -j DROP
```

`-I INPUT 1`은 1번 위치에 삽입(insert)이다. 차단 룰은 보통 허용 룰보다 위에 있어야 한다.

반대 방향 사례도 있다. 어떤 IP만 SSH를 허용하려고 했는데 전부 막히는 경우.

```bash
iptables -A INPUT -p tcp --dport 22 -j DROP
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.5 -j ACCEPT
```

순서가 거꾸로다. 첫 줄에서 22번은 출발지 무관하게 다 DROP되니 두 번째 ACCEPT 룰은 도달하지 못한다. 허용을 위에, 차단을 아래에 둬야 한다.

```bash
iptables -A INPUT -p tcp --dport 22 -s 10.0.0.5 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j DROP
```

또 한 가지, 클라우드 인스턴스에서는 호스트 방화벽 룰이 맞는데도 트래픽이 안 통하면 보안 그룹을 확인해야 한다. 보안 그룹과 호스트 방화벽은 별개 층위라 둘 다 열려 있어야 한다. iptables를 아무리 들여다봐도 답이 안 나오면 보안 그룹 쪽을 의심한다.

---

## 디버깅 방법

룰이 막는지 통과시키는지 추측하지 말고 패킷 카운터로 확인해야 한다. iptables의 모든 룰에는 그 룰에 매칭된 패킷 수와 바이트 수가 기록된다. `-v`로 보면 된다.

```bash
iptables -L -v -n --line-numbers
```

- `-L`: 룰 목록.
- `-v`: 패킷/바이트 카운터 표시.
- `-n`: IP와 포트를 이름이 아닌 숫자로(DNS 역조회 안 함, 빠르다).
- `--line-numbers`: 룰 번호 표시. `-I`로 삽입할 때 위치 잡는 데 쓴다.

출력은 이렇게 나온다.

```
Chain INPUT (policy DROP 12 packets, 720 bytes)
num   pkts bytes target  prot opt in  out source       destination
1      450 27000 ACCEPT  all  --  lo  *   0.0.0.0/0    0.0.0.0/0
2    18302  2.1M ACCEPT  all  --  *   *   0.0.0.0/0    0.0.0.0/0   ctstate ESTABLISHED,RELATED
3       42  2520 ACCEPT  tcp  --  *   *   0.0.0.0/0    0.0.0.0/0   tcp dpt:22 ctstate NEW
4        0     0 ACCEPT  tcp  --  *   *   0.0.0.0/0    0.0.0.0/0   tcp dpt:443 ctstate NEW
```

여기서 읽을 것. 헤더의 `policy DROP 12 packets`는 어떤 룰에도 안 걸려 기본 정책으로 떨어진 패킷이 12개라는 뜻이다. 이 숫자가 자꾸 올라가면 막혀야 할 게 막히는 게 아니라 통과돼야 할 게 막히고 있을 수 있다.

4번 룰의 카운터가 0이라는 게 핵심 단서다. 443번으로 들어오는 새 연결이 있는데도 4번이 0이면, 그 트래픽이 4번에 도달하기 전에 위쪽 어딘가에서 처리됐거나 애초에 도착을 안 한 거다. 반대로 막았다고 생각한 IP의 DROP 룰 카운터가 안 올라가면, 그 패킷이 DROP 룰 위의 ACCEPT 룰에 먼저 걸린 것이다. 카운터를 보면 룰 순서 문제가 바로 드러난다.

디버깅 절차는 이렇게 잡는다. 문제의 트래픽을 일부러 한 번 흘려보낸 뒤(curl이든 telnet이든), 카운터를 다시 본다. 카운터가 0에서 안 변한 룰은 그 패킷이 거기까지 안 간 거고, 어디서 멈췄는지는 위에서부터 카운터가 증가한 마지막 룰을 보면 된다.

카운터를 0으로 초기화하고 깨끗한 상태에서 보고 싶으면 이렇게 한다.

```bash
iptables -Z          # 모든 카운터 0으로
iptables -Z INPUT 3  # INPUT 3번 룰만 0으로
```

특정 패킷이 어느 룰에 걸리는지 더 정밀하게 봐야 하면 LOG 타겟을 임시로 넣는다.

```bash
iptables -I INPUT 1 -s 203.0.113.50 -j LOG --log-prefix "FW-DEBUG: "
```

이러면 그 IP에서 온 패킷이 커널 로그(`dmesg`나 `/var/log/kern.log`)에 찍힌다. LOG는 평가를 끝내지 않으니 다음 룰로 계속 넘어간다. 패킷 헤더 전체를 볼 수 있어서 출발지 포트, 플래그까지 확인된다. 디버깅 끝나면 이 LOG 룰은 지워야 한다. 트래픽 많은 서버에 LOG를 켜두면 로그가 폭주한다.

nftables에서 카운터를 보려면 룰에 `counter`를 명시하거나 룰 추가 시 자동으로 붙는 핸들로 조회한다.

```bash
nft list ruleset
nft list table inet filter -a   # -a로 핸들 번호 표시
```

nftables는 iptables와 달리 모든 룰이 자동으로 카운터를 갖지는 않는다. 카운터를 보려면 룰에 `counter` 키워드를 넣어야 한다.

```bash
nft add rule inet filter input tcp dport 22 ct state new counter accept
```

---

## 룰 저장과 재부팅

iptables 룰은 메모리에만 있어서 재부팅하면 날아간다. 운영 서버에서 룰을 잘 만들어 놓고 재부팅 후 전부 초기화되는 사고가 흔하다. 저장해야 한다.

```bash
# Debian/Ubuntu - iptables-persistent 패키지
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6

# RHEL 계열
iptables-save > /etc/sysconfig/iptables
```

nftables는 `/etc/nftables.conf`에 룰셋을 쓰고 systemd 서비스로 부팅 때 로드한다.

```bash
nft list ruleset > /etc/nftables.conf
systemctl enable nftables
```

원격 서버에서 룰을 새로 적용할 때는 자기 자신을 잠그는 걸 항상 조심해야 한다. SSH 세션이 끊기면 복구할 방법이 없다. 안전장치로, 룰을 적용하기 전에 "N분 뒤 룰을 전부 초기화하라"는 예약 작업을 걸어두고 작업한다.

```bash
echo "iptables -F; iptables -P INPUT ACCEPT" | at now + 5 minutes
```

룰을 적용해보고 SSH가 멀쩡하면 그 `at` 작업을 취소하고, 잘못돼서 세션이 끊겨도 5분 뒤 룰이 풀려 다시 들어갈 수 있다. 원격에서 방화벽을 만질 때 이 습관 하나가 서버를 잠그는 사고를 막아준다.
