---
title: Keepalived
tags:
  - infra
  - load-balancer
  - keepalived
  - vrrp
  - high-availability
updated: 2026-06-21
---

# Keepalived

## HAProxy를 이중화해도 남는 문제

HAProxy를 두 대 띄워서 백엔드 장애에 대비했다고 치자. 그런데 클라이언트는 결국 어느 한 대의 HAProxy IP로 접속한다. 그 HAProxy 노드 자체가 죽으면? DNS에 두 IP를 넣어 돌려도 클라이언트가 죽은 IP를 잡으면 타임아웃이 난다. DNS는 장애를 초 단위로 못 따라간다.

로드밸런서 앞단에 또 다른 단일 장애점이 생긴 거다. 클라우드면 그냥 ALB를 쓰면 끝이지만, 온프레미스에서 HAProxy나 nginx를 직접 올렸다면 이 앞단을 누가 책임지냐가 남는다. 여기서 쓰는 게 keepalived다.

keepalived는 VRRP(Virtual Router Redundancy Protocol)로 가상 IP 하나를 두 노드가 공유하게 만든다. 평소엔 master 노드가 그 VIP를 들고 있고, master가 죽으면 backup이 1초 안에 VIP를 가져온다. 클라이언트는 항상 VIP 하나만 바라보면 되고, 뒤에서 어느 물리 노드가 그 IP를 들고 있는지는 몰라도 된다.

```
          클라이언트
              |
          VIP 10.0.0.100   <- 이 IP가 master <-> backup 사이를 떠다닌다
         /            \
   lb-01 (master)   lb-02 (backup)
   HAProxy          HAProxy
   priority 100     priority 90
```

VIP는 어느 물리 NIC에도 고정돼 있지 않다. master로 선출된 노드가 자기 인터페이스에 `10.0.0.100`을 secondary IP로 추가하고, gratuitous ARP를 쏴서 "이 IP는 이제 내 MAC이다"라고 스위치에 알린다. 페일오버는 이 ARP 갱신이 핵심이다.

## VRRP가 도는 방식

master는 주기적으로(기본 1초) VRRP advertisement 패킷을 멀티캐스트로 뿌린다. backup은 이 패킷을 듣고 있다가, 일정 시간(보통 advert 주기의 3배 + skew) 동안 안 들리면 master가 죽었다고 판단하고 자기가 master로 승격한다.

판단 기준은 priority다. 같은 `virtual_router_id`를 가진 노드끼리 priority를 비교해서 제일 높은 쪽이 master가 된다. 그래서 설정에서 master/backup은 사실 `state` 키워드보다 priority 숫자가 실질적인 역할을 한다.

```
lb-01: priority 100  -> master
lb-02: priority 90   -> backup
```

`state MASTER`, `state BACKUP`라고 적는 건 부팅 직후 초기 상태 힌트일 뿐이다. 결국 advert를 주고받으면서 priority 높은 쪽이 master로 수렴한다. 그래서 둘 다 `state BACKUP`으로 적고 priority만 다르게 줘도 정상 동작한다. 오히려 부팅 순서에 따른 혼란을 줄이려고 일부러 둘 다 BACKUP으로 시작시키는 구성도 흔하다.

## 가장 기본 구성

CentOS/RHEL 계열은 `/etc/keepalived/keepalived.conf`, 데비안 계열도 같은 경로다.

master(lb-01):

```
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass 1q2w3e4r
    }

    virtual_ipaddress {
        10.0.0.100/24
    }
}
```

backup(lb-02):

```
vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 90
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass 1q2w3e4r
    }

    virtual_ipaddress {
        10.0.0.100/24
    }
}
```

`virtual_router_id`(VRID), `auth_pass`, `virtual_ipaddress`는 두 노드가 똑같아야 한다. priority만 다르다. 이 상태로 둘 다 `systemctl start keepalived` 하면 lb-01이 VIP를 잡는다.

확인은 `ip addr`로 한다. master에서만 VIP가 보여야 한다.

```bash
# lb-01 (master)
$ ip addr show eth0
2: eth0: ...
    inet 10.0.0.11/24 ...
    inet 10.0.0.100/24 scope global secondary eth0   # <- VIP 붙어있음

# lb-02 (backup)
$ ip addr show eth0
2: eth0: ...
    inet 10.0.0.12/24 ...
    # VIP 없음
```

`ifconfig`로는 secondary IP가 안 보인다. keepalived는 iproute2 방식으로 IP를 붙이기 때문에 반드시 `ip addr`로 확인해야 한다. 처음에 `ifconfig eth0` 쳐보고 VIP가 안 보여서 페일오버가 안 됐다고 착각하는 경우가 많다.

## virtual_router_id 충돌 — 제일 자주 터지는 문제

VRID는 0~255 사이 숫자인데, 같은 L2 네트워크(같은 브로드캐스트 도메인) 안에서 VRRP 인스턴스를 구분하는 ID다. 문제는 이 숫자가 같은 네트워크 안에서 유일해야 한다는 거다.

운영하다 보면 이런 일이 생긴다. A팀이 keepalived로 VIP를 구성하면서 예제를 그대로 복사해 `virtual_router_id 51`을 썼다. B팀도 다른 서비스용으로 keepalived를 올리면서 똑같이 예제의 `51`을 썼다. 두 클러스터가 같은 VLAN에 있으면, 서로의 VRRP advert를 듣고 "어? 나랑 같은 VRID인데 priority가 다르네" 하면서 엉뚱하게 상태가 흔들린다. 한쪽 VIP가 멋대로 내려가거나 양쪽이 서로를 죽었다고 판단하는 식이다.

증상이 묘하다. 평소엔 멀쩡한데 가끔 VIP가 점멸하듯 떴다 사라진다. 로그를 보면 이런 게 찍힌다.

```
Keepalived_vrrp: (VI_1) received an invalid passwd!
Keepalived_vrrp: (VI_1) ignoring advert from 10.0.0.55 (...)
```

`received an invalid passwd`는 VRID는 겹쳤는데 auth_pass가 다를 때 나온다. 이게 보이면 십중팔구 누군가 같은 VRID를 다른 데서 쓰고 있는 거다.

해결은 단순하다. 네트워크 전체에서 VRID를 대장처럼 관리해야 한다. 어떤 클러스터가 몇 번을 쓰는지 표로 적어두고, 새 클러스터는 빈 번호를 받아간다. 멀티캐스트 환경에서 VRRP는 VRID 기준 224.0.0.18 그룹으로 통신하므로, VRID가 같으면 다른 서브넷이어도 L2가 같으면 충돌한다.

## vrrp_script로 HAProxy 헬스체크 연동

기본 VRRP는 노드(keepalived 프로세스)가 살아있는지만 본다. 정작 keepalived는 멀쩡한데 그 위의 HAProxy가 죽으면? VIP는 그대로 master에 붙어있고, 트래픽은 죽은 HAProxy로 들어가서 전부 실패한다. keepalived 입장에선 자기는 살아있으니 페일오버할 이유가 없다.

이걸 막으려고 `vrrp_script`로 실제 서비스 상태를 검사하고, 실패하면 priority를 깎는다.

```
vrrp_script chk_haproxy {
    script "/usr/bin/killall -0 haproxy"   # 프로세스 존재 확인
    interval 2          # 2초마다 검사
    weight -20          # 실패하면 priority 20 깎음
    fall 2              # 2번 연속 실패해야 down 판정
    rise 2              # 2번 연속 성공해야 up 판정
}

vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    authentication {
        auth_type PASS
        auth_pass 1q2w3e4r
    }

    virtual_ipaddress {
        10.0.0.100/24
    }

    track_script {
        chk_haproxy
    }
}
```

`killall -0 haproxy`는 실제로 죽이는 게 아니라 시그널 0을 보내서 프로세스 존재 여부만 확인하는 관용적 방법이다. 프로세스가 없으면 0이 아닌 종료코드를 뱉고, keepalived가 그걸 실패로 본다.

동작은 이렇다. master lb-01에서 HAProxy가 죽으면 `chk_haproxy`가 실패 → priority가 100에서 80으로 떨어진다(weight -20). backup lb-02의 priority는 90이라 이제 lb-02가 더 높아진다 → lb-02가 master로 승격 → VIP가 lb-02로 넘어간다. weight를 깎는 폭이 중요한데, master priority - weight절댓값 < backup priority가 되도록 잡아야 페일오버가 일어난다. 100 - 20 = 80 < 90, 조건 충족.

흔한 실수가 weight를 너무 작게 주는 거다. master 100, backup 90인데 weight를 -5로 주면 95가 돼서 여전히 90보다 높다. HAProxy가 죽어도 페일오버가 안 된다. 검사 스크립트가 실패로 잡혀도 VIP가 안 넘어가면 이 계산부터 다시 봐야 한다.

프로세스 존재만 보는 것보다 실제 포트가 응답하는지 보는 게 낫다. HAProxy가 좀비처럼 떠있지만 포트는 안 받는 경우가 있다.

```
vrrp_script chk_haproxy {
    script "/bin/bash -c '</dev/tcp/127.0.0.1/80'"   # 80포트 TCP 연결 시도
    interval 2
    weight -20
    fall 2
    rise 2
}
```

스크립트 권한도 주의해야 한다. keepalived 2.x부터는 보안상 `script` 실행을 root가 아닌 별도 유저(`keepalived_script`)로 돌리려는 경향이 있어서, 스크립트 파일에 실행 권한이 없거나 해당 유저가 못 읽으면 조용히 실패한다. 로그에 `Disabling track script ... since not found/accessible`가 찍히면 권한 문제다.

## notify 스크립트로 상태 전환 잡기

master/backup 상태가 바뀌는 순간에 뭔가 하고 싶을 때 notify를 쓴다. VIP를 가져왔으니 슬랙 알림을 보낸다든가, 캐시를 워밍한다든가, 모니터링 태그를 바꾼다든가.

```
vrrp_instance VI_1 {
    ...
    notify_master "/etc/keepalived/notify.sh master"
    notify_backup "/etc/keepalived/notify.sh backup"
    notify_fault  "/etc/keepalived/notify.sh fault"
}
```

```bash
#!/bin/bash
# /etc/keepalived/notify.sh
STATE=$1
HOSTNAME=$(hostname)

case $STATE in
    master)
        # VIP를 가져온 직후. 여기서 HAProxy 재시작 같은 건 하지 말 것.
        logger "keepalived: $HOSTNAME became MASTER"
        curl -s -X POST "$SLACK_WEBHOOK" \
            -d "{\"text\":\"$HOSTNAME VIP 인수 (MASTER)\"}"
        ;;
    backup)
        logger "keepalived: $HOSTNAME became BACKUP"
        ;;
    fault)
        # 스크립트 검사 실패 등으로 fault 상태. 알람 띄울 가치 있음.
        logger "keepalived: $HOSTNAME entered FAULT"
        curl -s -X POST "$SLACK_WEBHOOK" \
            -d "{\"text\":\"$HOSTNAME FAULT 상태 진입\"}"
        ;;
esac
```

notify 스크립트 안에서 무거운 작업을 하면 안 된다. 이 스크립트는 상태 전환 경로에서 동기적으로 실행되는데, 여기서 오래 걸리면 VRRP 처리가 밀린다. 알림이나 로깅 정도만 빠르게 하고, 무거운 작업은 백그라운드로 던지거나 별도 프로세스에 신호만 보내야 한다.

fault 상태를 꼭 잡아야 한다. master/backup만 보면 정상 전환만 보이는데, fault는 vrrp_script가 실패해서 그 인스턴스가 선거에서 빠진 상태다. fault가 자주 뜬다는 건 헬스체크가 불안정하다는 신호다.

## unicast vs multicast

VRRP는 기본이 멀티캐스트(224.0.0.18)다. 같은 L2에서 노드들이 별도 설정 없이 서로를 찾는다. 온프레미스 물리 스위치 환경이면 멀티캐스트가 편하다.

문제는 클라우드다. AWS, GCP 같은 환경은 멀티캐스트를 막아놨다. 멀티캐스트 패킷이 아예 안 흐른다. 그래서 클라우드나 멀티캐스트가 차단된 망에선 unicast로 바꿔야 한다. 상대 노드 IP를 명시적으로 적어주는 방식이다.

```
vrrp_instance VI_1 {
    state MASTER
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    unicast_src_ip 10.0.0.11      # 자기 IP
    unicast_peer {
        10.0.0.12                  # 상대 노드 IP
    }

    authentication {
        auth_type PASS
        auth_pass 1q2w3e4r
    }

    virtual_ipaddress {
        10.0.0.100/24
    }
}
```

backup에선 `unicast_src_ip`와 `unicast_peer`를 반대로 적는다. 노드가 셋 이상이면 `unicast_peer`에 나머지 전부를 나열한다.

unicast로 바꾸면 멀티캐스트 그룹 충돌(VRID 충돌)이 줄어드는 부수 효과가 있다. 명시한 peer하고만 통신하니까 옆 클러스터의 advert를 들을 일이 없다. 다만 노드 추가/제거 때마다 모든 노드의 peer 목록을 손봐야 하는 번거로움이 생긴다.

클라우드에서 VIP를 쓸 때 한 가지 더 짚어야 할 게 있다. keepalived가 OS 레벨에서 IP를 옮기고 ARP를 쏴도, 클라우드의 가상 네트워크는 그 ARP를 무시하는 경우가 있다. AWS는 인스턴스에 할당되지 않은 IP로 들어온 패킷을 소스/데스티네이션 체크로 버린다. 이 환경에선 단순 VIP 이동만으론 안 되고, notify_master에서 AWS API를 호출해 Elastic IP를 재연결하거나 secondary private IP를 옮기는 작업을 같이 해야 한다. keepalived의 VRRP 선거만 빌려 쓰고 실제 IP 이동은 클라우드 API로 하는 식이다.

## split-brain과 preempt

split-brain은 양쪽 노드가 동시에 자기가 master라고 믿는 상태다. 둘 다 VIP를 들고 gratuitous ARP를 쏘면 스위치의 MAC 테이블이 두 노드 사이를 왔다 갔다 하면서 트래픽이 엉킨다.

원인은 거의 항상 VRRP advert가 서로 안 닿는 거다. 방화벽이 VRRP 프로토콜(IP protocol 112)을 막았거나, 멀티캐스트가 차단됐거나, 둘 사이 네트워크가 끊겼는데 둘 다 살아있는 경우다. backup이 advert를 못 들으니 master가 죽은 줄 알고 승격하는데, 사실 원래 master도 멀쩡히 살아서 VIP를 들고 있다.

방화벽부터 확인해야 한다.

```bash
# VRRP는 IP 프로토콜 112. TCP/UDP 포트가 아니다.
$ firewall-cmd --add-protocol=vrrp --permanent
$ firewall-cmd --reload

# iptables면
$ iptables -A INPUT -p vrrp -j ACCEPT
# 멀티캐스트 쓰면 224.0.0.18도 허용
$ iptables -A INPUT -d 224.0.0.18 -j ACCEPT
```

VRRP가 TCP나 UDP가 아니라 IP 프로토콜 112라는 걸 모르면 방화벽 설정에서 한참 헤맨다. 포트 기반으로만 열다가 안 돼서 시간을 버린다.

preempt는 split-brain과 직접 관련은 없지만 운영에서 같이 고민하게 되는 설정이다. 기본 동작(preempt)은, 죽었던 원래 master가 복구되면 priority가 더 높으니까 VIP를 도로 가져온다. 문제는 이 되찾는 과정에서 VIP가 한 번 더 이동하면서 짧은 끊김이 생긴다는 거다.

원래 master 서버가 불안정해서 떴다 죽었다를 반복하면, VIP가 계속 lb-01 ↔ lb-02를 오간다(플래핑). 매번 연결이 끊긴다. 이게 싫으면 `nopreempt`를 건다.

```
vrrp_instance VI_1 {
    state BACKUP        # nopreempt 쓸 땐 둘 다 BACKUP으로 시작해야 한다
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1
    nopreempt           # 복구돼도 VIP 도로 안 가져옴

    ...
}
```

`nopreempt`를 걸면, 한 번 backup이 master가 된 뒤로는 원래 master가 복구돼도 VIP를 안 넘겨준다. priority가 낮아도 현재 master가 계속 들고 있는다. 의도적인 페일백을 원할 때만 사람이 수동으로 옮긴다.

주의할 건 `nopreempt`는 `state BACKUP`인 인스턴스에서만 동작한다는 거다. `state MASTER`로 둔 채 nopreempt를 걸면 부팅하자마자 자기가 master라고 우겨서 의미가 없어진다. 그래서 nopreempt 구성에선 두 노드 다 `state BACKUP`으로 시작시킨다. 부팅 후 priority 높은 쪽이 자연스럽게 master가 되고, 한 번 정해지면 그 노드가 계속 잡고 있는다.

`preempt_delay`라는 절충안도 있다. preempt는 하되, 복구 후 일정 시간 기다렸다가 가져온다. 서버가 막 떴는데 아직 HAProxy가 다 준비 안 됐을 때 성급하게 VIP를 가져오는 걸 막는다.

```
    preempt_delay 60    # 복구 후 60초 기다렸다 preempt
```

## 실제 active-standby 구성 전체

lb-01(master)과 lb-02(backup) 앞에 VIP 하나를 두고, HAProxy 헬스체크를 연동한 구성이다.

lb-01 `/etc/keepalived/keepalived.conf`:

```
global_defs {
    router_id lb-01
    enable_script_security
    script_user keepalived_script
}

vrrp_script chk_haproxy {
    script "/bin/bash -c '</dev/tcp/127.0.0.1/80'"
    interval 2
    weight -20
    fall 2
    rise 2
}

vrrp_instance VI_1 {
    state BACKUP
    interface eth0
    virtual_router_id 51
    priority 100
    advert_int 1

    unicast_src_ip 10.0.0.11
    unicast_peer {
        10.0.0.12
    }

    authentication {
        auth_type PASS
        auth_pass 1q2w3e4r
    }

    virtual_ipaddress {
        10.0.0.100/24
    }

    track_script {
        chk_haproxy
    }

    notify_master "/etc/keepalived/notify.sh master"
    notify_backup "/etc/keepalived/notify.sh backup"
    notify_fault  "/etc/keepalived/notify.sh fault"
}
```

lb-02는 `router_id lb-02`, `priority 90`, `unicast_src_ip 10.0.0.12`, `unicast_peer { 10.0.0.11 }`만 바꾸고 나머지는 동일하다. 둘 다 `state BACKUP`으로 시작해서 priority 100인 lb-01이 master가 된다.

`enable_script_security`와 `script_user`를 넣은 이유는, 2.x에서 root로 임의 스크립트를 돌리는 걸 막는 보안 기능 때문이다. 이걸 켜면 스크립트는 `keepalived_script` 유저로 실행된다. 이 유저가 스크립트 파일을 읽고 실행할 수 있어야 한다.

## 장애 전환 검증

설정만 해놓고 실제 페일오버를 안 해보면 정작 장애 때 안 넘어간다. 평소에 검증해둬야 한다.

먼저 VIP가 master에 붙어있는지 본다.

```bash
# lb-01에서
$ ip addr show eth0 | grep 10.0.0.100
    inet 10.0.0.100/24 scope global secondary eth0
```

페일오버 테스트 1 — HAProxy를 죽여본다. vrrp_script 연동이 제대로 되는지 본다.

```bash
# lb-01에서 HAProxy 중단
$ systemctl stop haproxy

# 몇 초 뒤 lb-02에서 확인
$ ip addr show eth0 | grep 10.0.0.100
    inet 10.0.0.100/24 scope global secondary eth0   # VIP가 넘어왔다
```

이때 VIP를 향해 ping이나 curl을 계속 돌려두면 끊김 시간을 잴 수 있다.

```bash
# 별도 클라이언트에서 페일오버 동안 계속 때려본다
$ while true; do curl -s -o /dev/null -w "%{http_code} %{time_total}\n" \
    http://10.0.0.100/ ; sleep 0.2; done
```

정상이면 1~2초 정도 실패하다가 다시 200이 찍힌다. advert_int와 fall 값에 따라 전환 시간이 달라진다. 더 빠르게 넘기고 싶으면 advert_int를 줄이거나 fall을 낮추면 되는데, 너무 공격적으로 잡으면 일시적 부하에도 페일오버가 튀니까 1초/2회 정도가 무난하다.

페일오버 테스트 2 — 노드 자체를 죽여본다. VRRP advert가 끊겼을 때 backup이 승격하는지 본다.

```bash
# lb-01에서 keepalived 자체 중단 (노드 다운 시뮬레이션)
$ systemctl stop keepalived

# lb-02 로그
$ journalctl -u keepalived -f
... (VI_1) Entering MASTER STATE
... (VI_1) setting VIPs.
```

복구 테스트 — lb-01을 살린 뒤 preempt 동작을 확인한다. preempt면 lb-01이 VIP를 도로 가져오고, nopreempt면 lb-02가 계속 들고 있어야 한다. 의도한 대로 동작하는지 본다.

로그는 `journalctl -u keepalived`로 본다. 상태 전환은 다 여기 찍힌다.

```
Keepalived_vrrp[12345]: (VI_1) Entering MASTER STATE
Keepalived_vrrp[12345]: (VI_1) Entering BACKUP STATE
Keepalived_vrrp[12345]: (VI_1) Entering FAULT STATE
```

`Entering FAULT STATE`가 보이면 vrrp_script가 실패한 거다. 스크립트를 직접 손으로 실행해서 종료코드를 확인한다.

```bash
$ /bin/bash -c '</dev/tcp/127.0.0.1/80'; echo $?
0     # 0이면 정상, 0이 아니면 포트가 안 열린 것
```

검증에서 자주 놓치는 게, 페일오버는 되는데 페일백이 안 되거나 반대인 경우다. 장애 전환만 보고 끝내지 말고 복구 시나리오까지 돌려봐야 한다. preempt/nopreempt 설정이 의도와 다르면 여기서 드러난다.

## 정리할 때 자주 보는 것

VRID는 네트워크 전체에서 유일하게. 같은 L2에서 겹치면 점멸하듯 VIP가 흔들린다.

vrrp_script의 weight는 `master priority - weight절댓값 < backup priority`가 성립하도록. 안 그러면 검사가 실패해도 페일오버가 안 일어난다.

VRRP는 IP 프로토콜 112다. 방화벽을 포트로만 열면 안 닿는다.

클라우드면 멀티캐스트가 막혀있으니 unicast로. VIP 이동도 OS ARP만으론 안 되고 클라우드 API 연동이 필요할 수 있다.

`ip addr`로 VIP를 확인한다. `ifconfig`엔 secondary IP가 안 보인다.

페일오버뿐 아니라 페일백까지 평소에 검증해둬야 정작 장애 때 안 당한다.
