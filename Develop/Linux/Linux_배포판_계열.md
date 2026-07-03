---
title: Linux 배포판 계열
tags: [linux, distribution, redhat, debian, ubuntu, centos, fedora, suse, arch]
updated: 2025-12-08
---

# Linux 배포판 계열

## 개요

Linux 배포판은 패키지 관리자, 설정 파일 위치, 릴리스 주기에서 차이가 있다. 서버 환경에서는 Red Hat 계열과 Debian 계열을 주로 사용한다.

## 주요 계열 비교

### Red Hat vs Debian 계열

| 항목 | Red Hat 계열 | Debian 계열 |
|------|-------------|------------|
| 패키지 관리자 | `yum`/`dnf`, `rpm` | `apt`/`apt-get`, `dpkg` |
| 패키지 포맷 | `.rpm` | `.deb` |
| 네트워크 설정 (7/8+) | `/etc/sysconfig/network-scripts/`, NetworkManager | `/etc/netplan/` (Ubuntu), `/etc/network/` (Debian) |
| 방화벽 | `firewalld` | `ufw` |
| 로그 파일 | `/var/log/messages` | `/var/log/syslog` |
| 리포지토리 설정 | `/etc/yum.repos.d/` | `/etc/apt/sources.list`, `/etc/apt/sources.list.d/` |
| 서비스 관리 | `systemd` (공통) | `systemd` (공통) |
| SELinux | 기본 활성화 | 기본 비활성화 (AppArmor 사용) |
| 지원 주기 | 10년 (RHEL) | 5년 (Ubuntu LTS), 3년 (Debian) |

### 패키지 관리자 명령어 비교

**Red Hat 계열:**
```bash
# 설치
yum install package      # RHEL/CentOS 7
dnf install package      # RHEL/CentOS 8+, Rocky, AlmaLinux

# 업데이트
yum update
dnf update

# 검색
yum search package
dnf search package

# 파일 제공 패키지 찾기
yum provides /usr/bin/command
dnf provides /usr/bin/command
```

**Debian 계열:**
```bash
# 설치
apt install package
apt-get install package

# 업데이트
apt update && apt upgrade
apt-get update && apt-get upgrade

# 검색
apt search package
apt-cache search package

# 파일 제공 패키지 찾기
apt-file search /usr/bin/command
dpkg -S /usr/bin/command
```

## Red Hat 계열

### RHEL (Red Hat Enterprise Linux)

상용 엔터프라이즈 배포판.

**특징:**
- 10년 지원 (EUS 포함 시 13년)
- 상용 라이선스 필요 (개발/테스트 무료)
- 패키지 관리자: `yum` (7), `dnf` (8+)
- 설정 파일: `/etc/sysconfig/`, `/etc/systemd/`

**실무:**
- `subscription-manager register`로 라이선스 등록
- `yum-config-manager --enable rhel-*-optional-rpms`로 옵션 리포지토리 활성화
- RHEL 7과 8+는 네트워크 설정 방식이 다름

### CentOS

RHEL 소스 재컴파일 무료 배포판.

**CentOS 7:**
- RHEL 7과 100% 호환
- 2024년 6월 30일 EOL
- `yum` 사용

**CentOS Stream:**
- RHEL 업스트림 버전
- 롤링 릴리스
- 프로덕션 부적합
- `dnf` 사용

**실무:**
- CentOS 7은 마이그레이션 필요
- Rocky Linux나 AlmaLinux로 이전 권장

### Rocky Linux vs AlmaLinux

둘 다 RHEL 호환 무료 배포판.

**공통점:**
- RHEL과 바이너리 호환
- `dnf` 패키지 관리자
- RHEL 8/9 지원

**차이점:**

| 항목 | Rocky Linux | AlmaLinux |
|------|------------|-----------|
| 주체 | 커뮤니티 | CloudLinux (기업) |
| 지원 | 커뮤니티 | 기업 지원 가능 |
| 마이그레이션 | `migrate2rocky` | `almalinux-deploy` |

**실무:**
- 둘 다 CentOS 대체로 적합
- 기업 지원 필요 시 AlmaLinux, 커뮤니티 선호 시 Rocky Linux

### Fedora

Red Hat 후원 커뮤니티 배포판. 최신 기술 도입.

**특징:**
- 6개월 릴리스 주기
- 최신 패키지
- `dnf` 사용
- RHEL 테스트베드 역할

**실무:**
- 프로덕션 부적합
- 개발 환경이나 최신 기능 테스트용

### Red Hat 계열 내 차이점

**RHEL 7 vs 8+:**

| 항목 | RHEL 7 | RHEL 8+ |
|------|--------|---------|
| 패키지 관리자 | `yum` | `dnf` |
| 네트워크 | `network-scripts` | NetworkManager |
| Python | 2.7 기본 | 3.6+ 기본 |
| OpenSSL | 1.0.2 | 1.1.1 |
| 네트워크 설정 파일 | `/etc/sysconfig/network-scripts/ifcfg-*` | NetworkManager 설정 |

**네트워크 설정 예시:**

RHEL 7:
```bash
# /etc/sysconfig/network-scripts/ifcfg-eth0
DEVICE=eth0
BOOTPROTO=static
IPADDR=192.168.1.100
NETMASK=255.255.255.0
GATEWAY=192.168.1.1
ONBOOT=yes
```

RHEL 8+:
```bash
# NetworkManager 사용
nmcli connection modify eth0 ipv4.addresses 192.168.1.100/24
nmcli connection modify eth0 ipv4.gateway 192.168.1.1
nmcli connection modify eth0 ipv4.method manual
nmcli connection up eth0
```

## Debian 계열

### Debian vs Ubuntu

**차이점:**

| 항목 | Debian | Ubuntu |
|------|--------|--------|
| 릴리스 주기 | 2~3년 | 6개월 (LTS 2년) |
| 지원 기간 | 3년 | 5년 (LTS) |
| 패키지 버전 | 보수적 (안정성) | 최신 (기능) |
| snap | 미사용 | 기본 포함 |
| 네트워크 설정 | `/etc/network/interfaces` | `/etc/netplan/` (18+) |
| 초기화 | `systemd` (8+) | `systemd` |

**Debian 특징:**
- 완전 오픈소스 철학
- 안정성 우선
- 패키지 검증 엄격

**Ubuntu 특징:**
- 사용자 친화적
- 클라우드 환경에서 널리 사용
- `snap` 패키지 시스템

**실무:**
- Debian: 안정성 중시, 오픈소스 철학
- Ubuntu: 최신 기능 필요, 클라우드 환경

### Debian

커뮤니티 주도 배포판.

**특징:**
- 2~3년 릴리스 주기
- 완전 오픈소스
- 패키지 관리자: `apt`, `apt-get`, `dpkg`
- 설정 파일: `/etc/apt/`, `/etc/default/`

**릴리스:**
- Debian 12: Bookworm
- Debian 11: Bullseye
- Debian 10: Buster

**실무:**
- `/etc/apt/sources.list`로 리포지토리 관리
- `apt update && apt upgrade`로 업데이트
- `apt`는 `apt-get`의 사용자 친화적 래퍼

### Ubuntu

Debian 기반, Canonical 개발.

**특징:**
- 6개월 정기 릴리스, 2년마다 LTS
- LTS 5년 지원
- 패키지 관리자: `apt`, `apt-get`, `dpkg`
- `snap` 패키지 시스템

**버전:**
- Ubuntu 22.04 LTS: Jammy Jellyfish
- Ubuntu 20.04 LTS: Focal Fossa
- Ubuntu 18.04 LTS: Bionic Beaver

**Ubuntu Server vs Desktop:**
- Server: GUI 없음, 서버 패키지 중심
- Desktop: GNOME 포함, 데스크톱 앱 포함

**실무:**
- `ubuntu-minimal` 이미지로 최소 설치
- `unattended-upgrades`로 자동 보안 업데이트
- `do-release-upgrade`로 LTS 간 업그레이드
- `snap`은 별도 관리 필요

### Debian 계열 내 차이점

**네트워크 설정:**

Debian:
```bash
# /etc/network/interfaces
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
```

Ubuntu 18+:
```yaml
# /etc/netplan/01-netcfg.yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
```

**패키지 관리:**

Debian은 전통적 패키지만, Ubuntu는 `snap`도 사용:
```bash
# Ubuntu에서 snap 확인
snap list
snap install package

# Debian은 snap 미지원 (수동 설치 가능하나 권장 안 함)
```

## SUSE 계열

### openSUSE vs SUSE Linux Enterprise

| 항목 | openSUSE | SUSE Linux Enterprise |
|------|----------|---------------------|
| 라이선스 | 무료 | 상용 |
| 지원 | 커뮤니티 | 기업 지원 |
| 릴리스 | Leap (정기), Tumbleweed (롤링) | 장기 지원 |
| 패키지 관리자 | `zypper` | `zypper` |
| 설정 도구 | YaST | YaST |

**특징:**
- `zypper`는 `yum`/`apt`와 다른 명령어 구조
- YaST는 GUI/CLI 설정 도구
- 유럽에서 주로 사용

**실무:**
- `zypper refresh`로 리포지토리 갱신
- `zypper install package`로 패키지 설치
- `yast` 명령어로 설정 도구 실행

## Arch 계열

### Arch Linux vs Manjaro

| 항목 | Arch Linux | Manjaro |
|------|-----------|---------|
| 설치 | 최소 설치, 수동 구성 | GUI 설치 프로그램 |
| 안정성 | 롤링 릴리스 | Arch보다 안정성 중시 |
| 패키지 관리자 | `pacman` | `pacman` |
| AUR | 지원 | 지원 |

**특징:**
- 롤링 릴리스
- `pacman -Syu`로 전체 시스템 업데이트
- AUR 패키지는 수동 빌드 필요

**실무:**
- 서버 환경 부적합
- 개발 환경이나 학습 목적

## 실무 차이점

### 방화벽 관리

**Red Hat 계열 (firewalld):**
```bash
# 서비스 추가
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

# 포트 추가
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# 상태 확인
firewall-cmd --list-all
```

**Debian/Ubuntu (ufw):**
```bash
# 서비스 허용
ufw allow http
ufw allow https

# 포트 허용
ufw allow 8080/tcp

# 활성화
ufw enable
ufw status
```

### 로그 위치 차이

**Red Hat 계열:**
- `/var/log/messages`: 시스템 메시지
- `/var/log/secure`: 보안 관련
- `journalctl`: systemd 로그

**Debian/Ubuntu:**
- `/var/log/syslog`: 시스템 로그
- `/var/log/auth.log`: 인증 로그
- `journalctl`: systemd 로그

**공통:**
- `/var/log/`: 애플리케이션 로그
- `journalctl -u service`: 서비스별 로그

### 패키지 검색 방법

**Red Hat:**
```bash
# 파일 제공 패키지 찾기
dnf provides /usr/bin/python3
yum provides /usr/bin/python3

# 패키지 정보
dnf info package
rpm -qi package
```

**Debian:**
```bash
# 파일 제공 패키지 찾기 (apt-file 설치 필요)
apt install apt-file
apt-file update
apt-file search /usr/bin/python3

# 또는 dpkg로
dpkg -S /usr/bin/python3

# 패키지 정보
apt show package
dpkg -s package
```

### 서비스 관리

모든 주요 배포판이 `systemd` 사용:
```bash
# 공통 명령어
systemctl start service
systemctl stop service
systemctl restart service
systemctl reload service
systemctl enable service
systemctl disable service
systemctl status service
systemctl is-active service
systemctl is-enabled service
```

**차이점:**
- Red Hat: `/etc/systemd/system/`에 커스텀 서비스 파일
- Debian/Ubuntu: 동일하나 일부 기본 서비스 위치가 다를 수 있음

### 보안 업데이트

**Red Hat 계열:**
```bash
# 보안 업데이트만
dnf update --security
yum update --security

# 자동 업데이트 설정
dnf install dnf-automatic
systemctl enable --now dnf-automatic.timer

# 설정 파일
/etc/dnf/automatic.conf
```

**Debian/Ubuntu:**
```bash
# 보안 업데이트 확인
apt upgrade -s | grep security

# 자동 업데이트 설정
apt install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# 설정 파일
/etc/apt/apt.conf.d/50unattended-upgrades
/etc/apt/apt.conf.d/20auto-upgrades
```

**실무:**
- 프로덕션은 자동 업데이트보다 수동 검토 후 적용
- 스테이징에서 먼저 테스트
- 롤백 계획 수립

## 배포판 선택 기준

### 서버 환경

**엔터프라이즈 서버:**
- RHEL: 상용 지원 필요
- Rocky/AlmaLinux: RHEL 호환 무료
- Ubuntu LTS: 클라우드, 최신 기능
- Debian: 안정성 우선

**클라우드:**
- AWS: Amazon Linux 2023, Ubuntu, RHEL
- Azure: Ubuntu, RHEL, SUSE
- GCP: Ubuntu, Debian, RHEL

**컨테이너:**
- Alpine: 최소 크기 (5MB)
- Ubuntu: 범용 (100MB+)
- Debian: 안정성
- Red Hat UBI: RHEL 호환

### 개발 환경

- Ubuntu: 널리 사용, 문서 풍부
- Fedora: 최신 기술
- Arch: 커스터마이징

### 데스크톱

- Ubuntu: 사용자 친화적
- Linux Mint: Ubuntu 대체
- Fedora: 최신 데스크톱

## 마이그레이션

### CentOS → Rocky/AlmaLinux

**Rocky Linux:**
```bash
curl -O https://raw.githubusercontent.com/rocky-linux/rocky-tools/main/migrate2rocky/migrate2rocky.sh
chmod +x migrate2rocky.sh
./migrate2rocky.sh -r
```

**AlmaLinux:**
```bash
curl -O https://raw.githubusercontent.com/AlmaLinux/almalinux-deploy/master/almalinux-deploy.sh
chmod +x almalinux-deploy.sh
./almalinux-deploy.sh
```

**주의사항:**
- 백업 필수
- 테스트 환경에서 먼저 검증
- 커스텀 패키지 확인
- 설정 파일 차이점 확인

### 배포판 간 마이그레이션

**가능:**
- 동일 계열 내 (CentOS → Rocky)
- Ubuntu LTS 간 업그레이드

**불가능:**
- Red Hat → Debian (재설치 필요)
- Debian → Arch (재설치 필요)

이유: 패키지 구조, 설정 파일 위치, 초기화 시스템이 다름.

## 클라우드 이미지

### AWS
- Amazon Linux 2023: AWS 최적화
- Ubuntu: 가장 널리 사용
- RHEL: 엔터프라이즈

### Azure
- Ubuntu Server
- RHEL
- SUSE Linux Enterprise

### GCP
- Ubuntu
- Debian
- Container-Optimized OS

**실무:**
- 클라우드 제공 이미지 사용 권장
- 커스텀 이미지는 보안 업데이트 관리 필요
- 이미지 ID는 리전별로 다름

## 컨테이너 베이스 이미지

### Alpine Linux
- 크기: 5MB
- libc: musl
- 패키지: `apk`
- 사용: 프로덕션 컨테이너, 크기 최소화

### Ubuntu/Debian
- 크기: 100MB+
- libc: glibc
- 패키지: `apt`
- 사용: 개발 환경, 복잡한 의존성

### Red Hat UBI
- 기반: RHEL
- 라이선스: 무료 사용 가능
- 사용: RHEL 환경 호환

**실무:**
- 프로덕션: Alpine (크기 최소화)
- 개발: Ubuntu (패키지 풍부)
- RHEL 환경: UBI (호환성)

## 성능 차이

배포판 간 성능 차이는 미미하다. 커널 버전과 설정이 더 중요하다.

**차이가 나는 경우:**
- 컴파일 최적화: Gentoo, Alpine
- 기본 스케줄러 설정
- I/O 스케줄러 설정

**실무:**
- 배포판보다 애플리케이션 최적화가 중요
- 벤치마크로 실제 환경 측정

## 문서 및 커뮤니티

**문서:**
- RHEL: 공식 문서 우수
- Ubuntu: 커뮤니티 문서 풍부
- Debian: 공식 문서 상세
- Arch: Wiki 매우 상세

**커뮤니티:**
- Ubuntu: 가장 큰 커뮤니티
- Red Hat: 엔터프라이즈 지원
- Debian: 개발자 중심
- Arch: 기술적 지원 우수

## 결론

서버 환경에서는 Red Hat 계열(RHEL, Rocky, AlmaLinux)과 Debian 계열(Ubuntu, Debian)을 주로 사용한다.

**권장:**
- 엔터프라이즈: RHEL 또는 Rocky/AlmaLinux
- 클라우드: Ubuntu LTS
- 컨테이너: Alpine (프로덕션), Ubuntu (개발)
- 학습: Ubuntu 또는 Fedora

선택 기준: 지원 정책, 패키지 관리자 선호도, 클라우드 환경, 기존 인프라 호환성.
