---
title: 네트워크 스위치 (Network Switch)
tags: [network, network-switch, data-link-layer, mac-address, vlan, stp]
updated: 2026-06-04
---

# 네트워크 스위치 (Network Switch)

## 정의와 동작 위치

스위치는 OSI 2계층(데이터 링크 계층)에서 동작하는 장비다. 들어온 이더넷 프레임의 목적지 MAC 주소를 보고, 그 MAC이 학습된 포트로만 프레임을 내보낸다. 학습되지 않은 MAC이면 들어온 포트를 제외한 모든 포트로 플러딩한다.

L2에서 끝나는 게 보통이지만, L3 스위치라 부르는 장비는 라우팅 테이블도 들고 있다. 같은 박스에서 ASIC으로 라우팅까지 처리하기 때문에 라우터보다 패킷당 지연이 짧다. 데이터센터의 코어/디스트리뷰션 계층은 거의 L3 스위치다.

허브와의 결정적인 차이는 포트마다 충돌 도메인이 분리되어 있다는 점이다. 허브는 들어온 신호를 모든 포트에 그대로 흘리기 때문에 두 호스트가 동시에 송신하면 충돌이 난다. 스위치는 각 포트가 독립이라 풀듀플렉스가 가능하고, 1Gbps 포트면 송신/수신이 각각 1Gbps다.

## MAC 주소 학습과 포워딩

### CAM 테이블

스위치 내부의 MAC-포트 매핑 테이블을 흔히 CAM(Content Addressable Memory) 테이블 또는 MAC 어드레스 테이블이라 부른다. 이 테이블은 다음 두 가지 동작으로 채워진다.

1. **소스 학습**: 프레임이 도착하면 송신자 MAC을 받은 포트와 매핑해 저장한다.
2. **목적지 조회**: 목적지 MAC을 키로 테이블을 조회해 해당 포트로만 내보낸다. 없으면 플러딩.

Aging timer가 있어서 일정 시간(시스코 기본 300초) 동안 트래픽이 없으면 항목이 만료된다. 호스트가 다른 포트로 이동하거나, 가상머신이 호스트 간에 라이브 마이그레이션될 때 이게 빠르게 갱신되지 않으면 트래픽이 옛 포트로 가버린다. 그래서 라이브 마이그레이션 직후 가상머신은 보통 RARP/Gratuitous ARP를 쏴서 MAC 위치를 강제로 갱신시킨다.

CAM 테이블 크기는 모델마다 정해져 있다. 액세스 스위치는 보통 8K~16K, 데이터센터 스위치는 100K 이상이다. 이 크기를 알고 있어야 다음에 나올 MAC 플러딩 공격을 이해할 수 있다.

### 유니캐스트 / 멀티캐스트 / 브로드캐스트

| 종류 | 목적지 MAC | 스위치 동작 |
|---|---|---|
| 유니캐스트 | 특정 MAC | CAM 테이블 조회, 해당 포트로만 전달 (없으면 플러딩) |
| 브로드캐스트 | FF:FF:FF:FF:FF:FF | 같은 VLAN의 모든 포트로 전달 |
| 멀티캐스트 | 01:00:5E:xx:xx:xx 등 | 기본은 브로드캐스트처럼 전달, IGMP Snooping이 켜져 있으면 가입 포트로만 전달 |

브로드캐스트 도메인을 나누려면 VLAN을 쓰거나 라우터를 거쳐야 한다. ARP 요청, DHCP DISCOVER 같은 게 전부 브로드캐스트라 같은 VLAN에 호스트가 너무 많으면(보통 250~500대 이상) 이 트래픽만으로도 부담이 된다. 그래서 VLAN 분할은 보안만이 아니라 브로드캐스트 도메인 축소 용도이기도 하다.

### 스위칭 방식

| 방식 | 동작 | 지연 | 오류 프레임 차단 |
|---|---|---|---|
| Store-and-Forward | 프레임 전체 수신 후 FCS 검사하고 전달 | 가장 큼 | 됨 |
| Cut-Through | 목적지 MAC만 읽고 즉시 전달 시작 | 가장 작음 | 안 됨 |
| Fragment-Free | 앞 64바이트만 수신 후 전달 (충돌 프레임 차단) | 중간 | 부분적 |

요즘 일반적인 액세스 스위치는 Store-and-Forward를 쓴다. 데이터센터의 저지연 트레이딩, HPC, RDMA 환경에서는 Cut-Through 모드를 켜기도 한다. 단 입출력 포트 속도가 다르면(예: 25G in, 10G out) Cut-Through가 불가능해서 자동으로 Store-and-Forward로 떨어진다.

## VLAN

### 왜 쓰는가

VLAN은 같은 물리 스위치를 논리적으로 여러 개의 L2 네트워크로 쪼개는 기술이다. 쪼개는 이유는 셋 중 하나다.

- **브로드캐스트 도메인 축소**: 한 VLAN 안의 브로드캐스트가 다른 VLAN으로 새지 않는다.
- **격리**: 영업팀 PC와 서버존이 같은 스위치에 꽂혀 있어도 L2에서 서로 못 본다. VLAN 간 통신은 라우터/L3 스위치를 거쳐야 하고, 거기서 ACL을 걸 수 있다.
- **물리 토폴로지와 분리**: 사람이 자리 이동해도 포트 VLAN만 바꾸면 같은 네트워크에 그대로 붙는다.

### 802.1Q 태깅

VLAN 정보를 이더넷 프레임에 어떻게 넣을지에 대한 표준이 802.1Q다. 이더넷 헤더 중간에 4바이트 태그를 끼워 넣고, 그 중 12비트가 VLAN ID라서 1~4094까지 쓸 수 있다(0과 4095는 예약).

- **Access 포트**: 단말기(PC, 서버, IP폰)가 꽂히는 포트. 태그 없이 송수신한다. 들어올 때 access vlan으로 태그를 붙이고, 나갈 때 태그를 떼서 내보낸다.
- **Trunk 포트**: 스위치-스위치, 스위치-라우터, 스위치-하이퍼바이저 간 연결. 여러 VLAN의 프레임이 태그를 단 채로 흘러간다.
- **Native VLAN**: 트렁크에서 태그 없이 흐르는 VLAN. 양쪽 스위치의 Native VLAN이 다르면 VLAN 누수(VLAN hopping)가 생긴다. 보안 관점에서 Native VLAN은 사용하지 않는 VLAN 번호로 지정하는 게 관례다.

### 운영하며 자주 보는 문제

- **Trunk allowed VLAN 누락**: 트렁크에 `switchport trunk allowed vlan add` 안 하고 새 VLAN 만들면 그 VLAN만 통신이 안 된다. "왜 VLAN 30만 안 되지?" 하는 케이스의 9할.
- **하이퍼바이저 vSwitch 태그 설정**: ESXi/Proxmox에서 가상 스위치 포트그룹을 VLAN 0/4095(VGT)로 설정하면 VM이 직접 태깅한다. VLAN ID(VST)로 설정하면 하이퍼바이저가 붙인다. 둘이 섞이면 트래픽이 사라진다.
- **Voice VLAN**: IP폰을 꽂는 포트는 보통 Access VLAN(데이터)과 Voice VLAN 두 개를 동시에 운영한다. PC는 IP폰 뒤에 직렬로 꽂히고 데이터 VLAN을 태그 없이, IP폰은 음성 VLAN을 태그로 쏜다.

## STP (Spanning Tree Protocol)

### 왜 필요한가

스위치 두 대를 두 가닥 케이블로 묶으면 L2 루프가 생긴다. 누군가 브로드캐스트 한 번 쏘면 그 프레임이 루프를 무한히 돌면서 증식한다. 이게 브로드캐스트 스톰이고, 몇 초 만에 스위치 CPU가 100%를 찍고 네트워크가 죽는다. 이걸 막으려고 스위치 사이에 BPDU(Bridge Protocol Data Unit)를 주고받아 논리적인 트리를 만들고, 루프를 만드는 포트를 차단(blocking) 상태로 둔다. 이게 STP다.

### 동작 흐름

1. **루트 브리지 선출**: Bridge ID(Priority + MAC)가 가장 낮은 스위치가 루트가 된다. Priority 기본값은 32768이고, 일부러 코어 스위치에 낮은 값(예: 4096)을 박아서 루트로 만든다. 안 그러면 MAC이 우연히 가장 낮은 스위치(보통 가장 오래된 장비)가 루트가 된다.
2. **루트 포트 선정**: 루트가 아닌 각 스위치는 루트로 가는 비용이 가장 낮은 포트를 루트 포트로 잡는다.
3. **지정 포트 선정**: 각 세그먼트마다 그 세그먼트를 책임지는 지정 포트가 하나씩 정해진다.
4. **나머지는 차단**: 루트도 지정도 아닌 포트는 BLK(blocking) 상태가 되어 데이터 프레임을 전달하지 않는다.

### RSTP, MSTP, PVST+

오리지널 802.1D STP는 토폴로지 변경 후 수렴에 30~50초가 걸린다. 요즘 누구도 이걸 쓰지 않는다.

- **RSTP (802.1w)**: 수렴 시간을 수 초 이내로 단축. 거의 표준.
- **MSTP (802.1s)**: 여러 VLAN을 묶어 STP 인스턴스 수를 줄임. 멀티벤더 환경에서 일관적.
- **PVST+ / Rapid-PVST+**: 시스코 전용. VLAN마다 STP 인스턴스를 따로 돌린다. VLAN별로 루트를 다르게 둬서 트래픽을 분산할 수 있지만, VLAN이 많아지면 CPU를 많이 먹는다.

### 운영 팁

- **루트 브리지는 코어로**: 의도적으로 priority를 박아 두지 않으면 어느 날 액세스 스위치 한 대를 새로 꽂았을 때 그게 루트가 되어 트래픽이 이상한 경로로 흐른다.
- **PortFast + BPDU Guard**: 단말기가 꽂히는 액세스 포트는 PortFast로 STP 대기를 건너뛴다. 단, 누가 거기에 스위치를 잘못 꽂으면 루프가 생기므로 BPDU Guard로 BPDU 들어오면 즉시 err-disable 처리한다. 이 한 줄이 네트워크를 살린다.
- **Root Guard**: 다른 스위치가 자신보다 낮은 priority의 BPDU를 보내 루트가 되려 하면 그 포트를 차단한다. 코어→디스트리뷰션 라인에 거는 게 관례.
- **UDLD**: 광케이블 한쪽만 끊어진 단방향 장애를 STP가 못 잡는 경우가 있다. UDLD는 양방향이 살아 있는지 직접 확인한다.

## 포트 미러링 (SPAN / RSPAN / ERSPAN)

운영하다 보면 "이 서버 트래픽 패킷 단위로 좀 봐야겠다"는 순간이 온다. 서버에 tcpdump를 못 띄우는 환경(보안 정책, 어플라이언스 장비 등)이면 스위치 포트 미러링이 답이다.

- **SPAN (Switched Port Analyzer)**: 한 스위치 안에서 특정 포트의 트래픽을 다른 포트로 복사한다. 분석기는 그 포트에 직결.
- **RSPAN**: 미러링된 트래픽을 전용 VLAN에 실어 다른 스위치까지 보낸다.
- **ERSPAN**: GRE로 캡슐화해 L3 너머로 보낸다. 분석기가 데이터센터 다른 동에 있어도 된다.

### 주의할 점

- **대역폭**: 10G 포트 두 개를 1G 분석 포트로 미러하면 당연히 드롭난다. 미러 대상의 총합이 미러 포트 속도를 넘으면 안 된다.
- **방향**: rx(들어오는 것), tx(나가는 것), both 중 골라야 한다. 디버깅 목적이면 both가 보통.
- **세션 수 제한**: 모델별로 동시에 띄울 수 있는 SPAN 세션 수가 정해져 있다(흔히 2~4개).

```
! Cisco IOS - SPAN 세션 1: Gi0/1 양방향을 Gi0/24로 복사
SW-Core(config)# monitor session 1 source interface gigabitEthernet 0/1 both
SW-Core(config)# monitor session 1 destination interface gigabitEthernet 0/24

! 확인
SW-Core# show monitor session 1
```

## MAC 플러딩 공격과 방어

### 공격 원리

CAM 테이블 크기가 정해져 있다는 사실을 악용한다. 공격자가 위조된 송신 MAC 주소로 프레임을 수만~수십만 개 쏘면 CAM 테이블이 가짜 항목으로 가득 찬다. 정상 호스트의 MAC 항목이 밀려 나가고, 새로 학습되지도 못한다. 이 상태가 되면 스위치는 알 수 없는 유니캐스트를 전부 플러딩하는데, 이게 사실상 허브처럼 동작하는 상태(fail-open)다. 공격자는 자기가 받지 말아야 할 다른 호스트의 트래픽까지 보게 된다.

`macof` 같은 도구로 몇 초 만에 가능하고, 옛날 액세스 스위치 중에는 1초도 안 되어 다운되는 모델도 있다.

### 방어

핵심은 **포트 보안(port-security)**으로 포트당 학습 가능한 MAC 개수를 제한하는 것이다.

```
SW-Core(config)# interface fa0/5
SW-Core(config-if)# switchport mode access
SW-Core(config-if)# switchport port-security
SW-Core(config-if)# switchport port-security maximum 2
SW-Core(config-if)# switchport port-security mac-address sticky
SW-Core(config-if)# switchport port-security violation shutdown
```

`violation` 모드는 세 가지다.

- **protect**: 초과 MAC의 프레임을 조용히 드롭. 로그도 카운터도 없음.
- **restrict**: 드롭 + 로그 + SNMP 트랩. 포트는 계속 살아 있음.
- **shutdown**: 포트를 err-disable로 떨궈 버림. 가장 강함.

서버존이나 사무실 액세스처럼 한 포트에 호스트가 한두 개만 붙는 자리에는 maximum 2~4 정도, violation은 restrict 또는 shutdown으로 두는 게 일반적이다. 가상화 환경처럼 한 포트에 VM이 수십 개씩 붙는 곳은 maximum을 넉넉히 둬야 한다.

추가로 **DHCP Snooping** + **Dynamic ARP Inspection(DAI)**까지 켜면 ARP 스푸핑, DHCP 스푸핑까지 막을 수 있다. 운영망에서는 같이 묶어서 적용한다.

## 스위치 분류

실무에서 자주 마주치는 분류는 두 축이다.

### 관리 가능성

- **Unmanaged**: 설정 인터페이스가 없다. 꽂으면 그냥 동작한다. 회의실, 가정.
- **Smart (Web-managed)**: 웹 UI로 VLAN, QoS 정도만 만진다. SMB.
- **Managed (Fully managed)**: CLI/API로 거의 모든 설정 가능. 기업 표준.

### 계층

- **Access**: 사용자/서버 단말이 꽂히는 말단. 1G 포트가 주력. 24~48포트.
- **Distribution**: 액세스 스위치들을 모은다. L3 라우팅, ACL, QoS 정책이 주로 여기 박힌다.
- **Core**: 디스트리뷰션끼리 묶는다. 단순함과 속도가 미덕. 10G/25G/40G/100G.

데이터센터에서는 이 3계층 모델 대신 Spine-Leaf를 쓴다. 모든 Leaf가 모든 Spine과 풀메쉬로 묶여서 어느 호스트끼리 통신해도 hop 수가 같다. East-West 트래픽이 많은 환경에 맞다.

## 스위치 vs 라우터 vs L3 스위치

| 항목 | L2 스위치 | L3 스위치 | 라우터 |
|---|---|---|---|
| 동작 계층 | L2 | L2/L3 | L3 |
| 주소 기준 | MAC | MAC + IP | IP |
| 처리 방식 | ASIC | ASIC | ASIC + 일부 SW |
| 라우팅 프로토콜 | 없음 | 일부 (OSPF, BGP까지 가능한 모델) | 전부 |
| WAN 인터페이스 | 없음 | 거의 없음 | 있음 (PPP, MPLS 등) |
| 패킷당 지연 | 가장 작음 | 작음 | 큼 |

캠퍼스/데이터센터 내부 라우팅은 L3 스위치가 처리하고, 라우터는 인터넷/WAN 경계에 두는 게 표준 구성이다.

## CLI 설정 예제 (Cisco IOS)

### 기본 설정

```
Switch> enable
Switch# configure terminal
Switch(config)# hostname SW-Core

! 관리 IP (VLAN 1 인터페이스)
SW-Core(config)# interface vlan 1
SW-Core(config-if)# ip address 192.168.1.10 255.255.255.0
SW-Core(config-if)# no shutdown
SW-Core(config)# ip default-gateway 192.168.1.1

! SSH만 허용, telnet 차단
SW-Core(config)# line vty 0 15
SW-Core(config-line)# transport input ssh
SW-Core(config-line)# login local
SW-Core(config)# username admin privilege 15 secret <password>

! 설정 저장
SW-Core# copy running-config startup-config
```

### VLAN과 트렁크

```
! VLAN 정의
SW-Core(config)# vlan 10
SW-Core(config-vlan)# name SALES
SW-Core(config)# vlan 20
SW-Core(config-vlan)# name ENGINEERING
SW-Core(config)# vlan 99
SW-Core(config-vlan)# name NATIVE_UNUSED

! 액세스 포트
SW-Core(config)# interface range fastEthernet 0/1 - 10
SW-Core(config-if-range)# switchport mode access
SW-Core(config-if-range)# switchport access vlan 10
SW-Core(config-if-range)# spanning-tree portfast
SW-Core(config-if-range)# spanning-tree bpduguard enable

! 트렁크 포트
SW-Core(config)# interface gigabitEthernet 0/1
SW-Core(config-if)# switchport trunk encapsulation dot1q
SW-Core(config-if)# switchport mode trunk
SW-Core(config-if)# switchport trunk native vlan 99
SW-Core(config-if)# switchport trunk allowed vlan 10,20
SW-Core(config-if)# switchport nonegotiate

! 확인
SW-Core# show vlan brief
SW-Core# show interfaces trunk
```

`switchport nonegotiate`로 DTP(Dynamic Trunking Protocol)를 꺼두는 게 보안 권고다. DTP가 켜져 있으면 공격자가 트렁크를 협상해 다른 VLAN에 접근하는 VLAN hopping이 가능하다.

### STP 튜닝

```
! 코어 스위치를 VLAN 10, 20의 루트로 강제
SW-Core(config)# spanning-tree vlan 10 priority 4096
SW-Core(config)# spanning-tree vlan 20 priority 4096

! Rapid-PVST 모드
SW-Core(config)# spanning-tree mode rapid-pvst

! 액세스 포트는 PortFast + BPDU Guard
SW-Core(config)# interface range fa0/1 - 20
SW-Core(config-if-range)# spanning-tree portfast
SW-Core(config-if-range)# spanning-tree bpduguard enable

! 디스트리뷰션→액세스 라인에 Root Guard
SW-Core(config)# interface gi0/2
SW-Core(config-if)# spanning-tree guard root

! 확인
SW-Core# show spanning-tree vlan 10
SW-Core# show spanning-tree summary
```

### LACP (포트 채널)

```
! 양쪽 스위치 모두 동일하게 설정
SW-A(config)# interface range gigabitEthernet 0/1 - 2
SW-A(config-if-range)# channel-group 1 mode active
SW-A(config-if-range)# channel-protocol lacp

SW-A(config)# interface port-channel 1
SW-A(config-if)# switchport mode trunk
SW-A(config-if)# switchport trunk allowed vlan 10,20

! 확인
SW-A# show etherchannel summary
SW-A# show lacp neighbor
```

`mode active`는 LACP를 능동적으로 협상하고, `mode passive`는 상대방이 시작할 때만 응답한다. 양쪽 다 passive면 채널이 안 올라온다. 양쪽 active 또는 한쪽 active/한쪽 passive로 둔다.

### 포트 보안

```
SW-Core(config)# interface fa0/1
SW-Core(config-if)# switchport mode access
SW-Core(config-if)# switchport access vlan 10
SW-Core(config-if)# switchport port-security
SW-Core(config-if)# switchport port-security maximum 2
SW-Core(config-if)# switchport port-security mac-address sticky
SW-Core(config-if)# switchport port-security violation restrict

! 확인
SW-Core# show port-security interface fa0/1
SW-Core# show port-security address
```

### MAC 테이블 조회

```
SW-Core# show mac address-table
SW-Core# show mac address-table vlan 10
SW-Core# show mac address-table interface fa0/1
SW-Core# show mac address-table count          ! 학습된 MAC 개수와 CAM 한계

! 특정 MAC을 정적 등록 (이동을 막고 싶을 때)
SW-Core(config)# mac address-table static 0050.5600.0002 vlan 10 interface fa0/2

! 동적 항목 초기화
SW-Core# clear mac address-table dynamic
```

`show mac address-table count`로 현재 학습된 MAC 수와 모델 한계를 같이 보면 CAM 사용률을 가늠할 수 있다. 한계의 80%를 넘기 시작하면 토폴로지 점검 시점이다.

## 운영하며 실제로 자주 보는 장애

- **루프**: 청소하다 케이블 한 가닥이 다른 포트에 잘못 꽂혀 루프가 났는데 PortFast/BPDU Guard가 없어서 스위치가 다운된다. 대책은 위에 적은 BPDU Guard.
- **트렁크 VLAN 누락**: 새 VLAN을 만들고 트렁크에 `allowed vlan add`를 안 해서 특정 VLAN만 통신 불가.
- **MAC flapping 로그**: `%MAC_MOVE` 로그가 반복적으로 찍히면 같은 MAC이 두 포트에 동시에 학습되고 있다는 뜻. 보통 (1) 어딘가 루프, (2) 가상머신 라이브 마이그레이션, (3) HSRP/VRRP 활성 라우터 변경 중 하나다.
- **포트 err-disable**: BPDU Guard나 port-security violation으로 포트가 떨어졌다. `show interfaces status err-disabled`로 원인 확인 후 `shutdown` → `no shutdown` 또는 `errdisable recovery cause ...`로 자동 복구 설정.
- **CRC 에러 증가**: `show interfaces`의 input errors / CRC가 계속 증가하면 케이블, SFP, 패치판넬 중 하나가 문제다. 일단 케이블 교체부터.
- **유니캐스트 플러딩**: ARP 타이머와 MAC 에이징 타이머가 어긋나면 ARP 캐시에는 MAC이 있는데 CAM에는 없어서, 스위치가 모든 포트로 플러딩하는 현상이 생긴다. 비대칭 라우팅 환경에서 자주 본다. ARP 타이머를 MAC 에이징보다 짧게 맞추는 게 표준 대처.

## 표준 참고

- IEEE 802.3: 이더넷
- IEEE 802.1Q: VLAN 태깅
- IEEE 802.1D / 802.1w / 802.1s: STP / RSTP / MSTP
- IEEE 802.3ad (현 802.1AX): 링크 애그리게이션
- IEEE 802.1X: 포트 기반 인증
