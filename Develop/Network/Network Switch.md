---
title: 네트워크 스위치 (Network Switch) 완벽 가이드
tags: [network, network-switch, data-link-layer, mac-address, switching]
updated: 2024-12-19
---

# 네트워크 스위치 (Network Switch) 완벽 가이드

## 배경

### 네트워크 스위치란?
네트워크 스위치는 OSI 모델의 2계층(데이터 링크 계층)에서 동작하는 네트워크 장비입니다. 스위치는 MAC 주소를 기반으로 데이터 프레임을 전달하는 역할을 수행하며, 여러 장치를 연결하고 각 장치 간의 통신을 효율적으로 관리합니다.

### 스위치의 필요성
- **효율적인 데이터 전송**: MAC 주소 기반의 정확한 목적지 전송
- **네트워크 성능 향상**: 충돌 도메인 분리로 성능 개선
- **네트워크 확장성**: 여러 장치를 하나의 네트워크로 연결
- **트래픽 관리**: 스위칭 테이블을 통한 지능적인 패킷 전달

### 기본 개념
- **MAC 주소**: 네트워크 인터페이스의 고유 식별자
- **스위칭 테이블**: MAC 주소와 포트 매핑 정보
- **충돌 도메인**: 네트워크 충돌이 발생할 수 있는 영역
- **브로드캐스트 도메인**: 브로드캐스트가 전파되는 영역

## 핵심

### 1. 스위치의 작동 원리

#### MAC 주소 학습
스위치는 연결된 장치들의 MAC 주소를 자동으로 학습합니다.

```bash
# 스위칭 테이블 예시
MAC Address         Port    Age
00:1A:2B:3C:4D:5E   1       300
00:1A:2B:3C:4D:5F   2       150
00:1A:2B:3C:4D:60   3       600
```

#### 전송 방식
- **유니캐스트**: 특정 목적지에만 데이터를 전송
- **브로드캐스트**: 네트워크의 모든 장치에 데이터를 전송
- **멀티캐스트**: 특정 그룹의 장치들에만 데이터를 전송

#### 충돌 도메인 분리
각 포트는 독립적인 충돌 도메인을 가져 네트워크 성능 향상에 기여합니다.

### 2. 스위치의 종류

#### 관리형 스위치 (Managed Switch)
- VLAN, QoS, 포트 미러링 등 고급 기능 지원
- 네트워크 관리자가 설정을 변경할 수 있음
- 기업 환경에서 주로 사용

```bash
# 관리형 스위치 설정 예시
# VLAN 설정
vlan 10
name Sales
vlan 20
name Engineering

# 포트 할당
interface FastEthernet0/1
switchport mode access
switchport access vlan 10

# QoS 설정
class-map match-all VOICE
match dscp ef
policy-map VOICE-POLICY
class VOICE
priority percent 20
```

#### 비관리형 스위치 (Unmanaged Switch)
- 플러그 앤 플레이 방식으로 작동
- 추가 설정이 필요 없음
- 소규모 네트워크나 가정용으로 적합

#### 스마트 스위치 (Smart Switch)
- 관리형과 비관리형의 중간 기능 제공
- 웹 인터페이스를 통한 기본적인 설정 가능
- 중소규모 기업에 적합

### 3. 스위치 vs 라우터

| 특징 | 스위치 | 라우터 |
|------|--------|--------|
| **작동 계층** | OSI 2계층 (데이터 링크 계층) | OSI 3계층 (네트워크 계층) |
| **주소 처리** | MAC 주소 기반 통신 | IP 주소 기반 통신 |
| **통신 범위** | 동일 네트워크 내 통신 | 서로 다른 네트워크 간 통신 |
| **브로드캐스트 처리** | 브로드캐스트 도메인 내에서 전파 | 브로드캐스트를 차단 |

## 예시

### 1. 실제 사용 사례

#### 기업 네트워크
여러 부서 간의 효율적인 통신 관리, VLAN을 통한 네트워크 분리, QoS를 통한 중요 트래픽 우선 처리가 가능합니다.

```bash
# 기업 네트워크 구성 예시
# VLAN 구성
vlan 10
name Sales
vlan 20
name Engineering
vlan 30
name Management

# 포트 할당
interface range FastEthernet0/1-10
switchport mode access
switchport access vlan 10

interface range FastEthernet0/11-20
switchport mode access
switchport access vlan 20

# QoS 설정
class-map match-all VOICE
match dscp ef
policy-map VOICE-POLICY
class VOICE
priority percent 20
```

#### 데이터 센터
서버 간의 고속 통신 지원, 대용량 데이터 처리, 네트워크 가용성 보장이 가능합니다.

```bash
# 데이터 센터 스위치 설정
# 포트 채널링 (Link Aggregation)
interface Port-channel1
switchport mode trunk
switchport trunk allowed vlan 1-100

interface range GigabitEthernet0/1-2
channel-group 1 mode active

# 스패닝 트리 설정
spanning-tree mode rapid-pvst
spanning-tree vlan 1-100 priority 4096
```

#### 가정/소규모 사무실
여러 장치 연결, 간단한 네트워크 구성, 비용 효율적인 솔루션을 제공합니다.

### 2. 스위치 구성 예시

#### 기본 스위치 설정
```bash
# 스위치 초기 설정
enable
configure terminal
hostname SW-CORE-01

# 관리 인터페이스 설정
interface vlan 1
ip address 192.168.1.10 255.255.255.0
no shutdown

# 기본 게이트웨이 설정
ip default-gateway 192.168.1.1

# SSH 설정
username admin privilege 15 secret password123
line vty 0 15
login local
transport input ssh
```

#### VLAN 구성
```bash
# VLAN 생성
vlan 10
name Sales
vlan 20
name Engineering
vlan 30
name Management

# 트렁크 포트 설정
interface GigabitEthernet0/1
switchport mode trunk
switchport trunk allowed vlan 10,20,30

# 액세스 포트 설정
interface FastEthernet0/1
switchport mode access
switchport access vlan 10
```

## 운영 팁

### 1. 스위치 관리

#### 모니터링 및 로깅
```bash
# 로깅 설정
logging host 192.168.1.100
logging trap informational
logging facility local6

# SNMP 설정
snmp-server community public ro
snmp-server location "Data Center"
snmp-server contact "admin@company.com"
```

#### 백업 및 복구
```bash
# 설정 백업
copy running-config tftp://192.168.1.100/switch-config.txt

# 설정 복원
copy tftp://192.168.1.100/switch-config.txt running-config
```

### 2. 성능 최적화

#### 포트 보안
```bash
# 포트 보안 설정
interface FastEthernet0/1
switchport port-security
switchport port-security maximum 1
switchport port-security violation shutdown
switchport port-security mac-address sticky
```

#### 스패닝 트리 최적화
```bash
# 스패닝 트리 설정
spanning-tree mode rapid-pvst
spanning-tree vlan 1-100 priority 4096
spanning-tree vlan 200-300 priority 8192
```

### 3. 문제 해결

#### 일반적인 문제 및 해결책
```bash
# 포트 상태 확인
show interface status
show interface FastEthernet0/1

# MAC 주소 테이블 확인
show mac address-table
show mac address-table interface FastEthernet0/1

# VLAN 정보 확인
show vlan brief
show interface trunk
```

## 참고

### MAC 주소와 IP 주소의 차이점

#### MAC 주소 (Media Access Control Address)
- 48비트로 구성된 물리적 주소
- 16진수로 표현 (예: 00:1A:2B:3C:4D:5E)
- 제조사에서 할당하는 고유한 주소
- 네트워크 인터페이스 카드(NIC)에 고정되어 있음
- 데이터 링크 계층에서 사용
- 로컬 네트워크 내에서만 사용

#### IP 주소 (Internet Protocol Address)
- 32비트(IPv4) 또는 128비트(IPv6)로 구성된 논리적 주소
- 네트워크 관리자가 할당
- 네트워크 계층에서 사용
- 인터넷 전역에서 사용 가능
- 동적 할당(DHCP) 또는 정적 할당 가능
- 네트워크 위치를 식별하는 주소

### 스위치 선택 가이드

| 요구사항 | 권장 스위치 타입 | 주요 고려사항 |
|----------|------------------|---------------|
| **소규모 네트워크** | 비관리형 스위치 | 비용, 간편성 |
| **중소규모 기업** | 스마트 스위치 | 기본 관리 기능, 비용 |
| **대규모 기업** | 관리형 스위치 | 고급 기능, 확장성 |
| **데이터 센터** | 엔터프라이즈 스위치 | 성능, 안정성, 고급 기능 |

### 결론
네트워크 스위치는 현대 네트워크의 핵심 구성 요소로, 효율적인 데이터 전송과 네트워크 관리를 가능하게 합니다. 적절한 스위치 선택과 구성은 네트워크 성능과 안정성에 직접적인 영향을 미치므로, 요구사항에 맞는 스위치를 선택하고 올바르게 구성하는 것이 중요합니다.

