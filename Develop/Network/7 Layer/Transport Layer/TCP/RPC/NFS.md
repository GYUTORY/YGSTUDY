---
title: NFS Network File System
tags: [network, 7-layer, transport-layer, tcp, rpc]
updated: 2025-09-22
---

# NFS (Network File System)

## 목차
- [NFS란?](#nfs란)
- [핵심 개념과 용어](#핵심-개념과-용어)
- [NFS의 주요 특징](#nfs의-주요-특징)
- [NFS 동작 원리](#nfs-동작-원리)
- [NFS 버전별 특징](#nfs-버전별-특징)
- [실제 사용 사례](#실제-사용-사례)
- [설치 및 설정](#설치-및-설정)
- [보안 고려사항](#보안-고려사항)
- [장단점 분석](#장단점-분석)
- [대안 기술](#대안-기술)

---

## NFS란?

**NFS(Network File System)**는 네트워크를 통해 원격 파일 시스템을 로컬 파일 시스템처럼 사용할 수 있게 해주는 분산 파일 시스템 프로토콜입니다.

### 간단한 비유
- **구글 드라이브나 드롭박스**와 비슷하지만, 더 직접적이고 빠른 방식
- 마치 **USB를 여러 컴퓨터에 동시에 꽂아서 사용하는 것**과 같은 개념
- 여러 사람이 **같은 서랍장을 동시에 사용하는 것**과 같음

---

## 핵심 개념과 용어

| 용어 | 설명 | 비유 |
|------|------|------|
| **마운트(Mount)** | 원격 디스크를 로컬 디스크처럼 연결하는 것 | USB를 컴퓨터에 꽂는 것과 같음 |
| **Export** | NFS 서버에서 공유할 디렉토리를 설정하는 것 | 공유 폴더를 만드는 것 |
| **클라이언트** | NFS 서버의 파일을 사용하는 컴퓨터 | 파일을 받아서 사용하는 쪽 |
| **서버** | 파일을 공유해주는 컴퓨터 | 파일을 제공해주는 쪽 |
| **분산 파일 시스템** | 여러 컴퓨터에 흩어져 있는 파일을 하나처럼 관리하는 시스템 | 여러 창고의 물건을 하나의 매장에서 관리하는 것 |
| **RPC (Remote Procedure Call)** | 원격 프로시저 호출, NFS의 기본 통신 방식 | 다른 컴퓨터의 함수를 직접 호출하는 것 |

---

## NFS의 주요 특징

### 🚀 투명성 (Transparency)
- 서버의 파일을 클라이언트에서 **로컬 파일처럼 사용 가능**
- 파일을 복사할 필요 없이 **직접 접근 가능**
- 사용자는 파일이 어디에 있는지 알 필요 없음

### 🔄 동시성 (Concurrency)
- 여러 클라이언트가 **동시에 같은 파일에 접근 가능**
- 마치 여러 사람이 같은 문서를 동시에 편집하는 것과 같음
- 파일 잠금(File Locking) 메커니즘으로 충돌 방지

### 🔐 권한 관리
- UNIX/Linux의 파일 권한 시스템 활용
- 사용자별로 읽기/쓰기 권한 제어 가능
- UID/GID 기반의 사용자 매핑

### 🌐 크로스 플랫폼
- Linux, UNIX, macOS, Windows에서 모두 사용 가능
- 다양한 운영체제 간 파일 공유 지원

---

## NFS 동작 원리

### 기본 아키텍처

```plaintext
┌─────────────────┐    네트워크    ┌─────────────────┐
│   NFS Server    │ ←──────────→ │  NFS Client 1   │
│                 │               │                 │
│ /shared/files   │               │ /mnt/nfs        │
└─────────────────┘               └─────────────────┘
         │                                   │
         │                                   │
         └───────────┐                       │
                     ▼                       │
         ┌─────────────────┐                 │
         │  NFS Client 2   │                 │
         │                 │                 │
         │ /mnt/nfs        │                 │
         └─────────────────┘                 │
                     ▲                       │
                     └───────────────────────┘
```

### 동작 과정

1. **서버 설정**: NFS 서버가 특정 디렉토리를 공유하도록 설정
2. **클라이언트 연결**: 클라이언트가 서버의 공유 디렉토리를 로컬에 마운트
3. **파일 접근**: 클라이언트가 마운트된 디렉토리를 통해 서버 파일에 접근
4. **동기화**: 여러 클라이언트가 동시에 같은 파일에 접근 가능

### RPC 기반 통신
- NFS는 RPC(Remote Procedure Call)를 기반으로 동작
- 클라이언트가 서버의 파일 시스템 함수를 원격으로 호출
- TCP/UDP 프로토콜을 사용하여 네트워크 통신

---

## NFS 버전별 특징

### NFSv2 (1989)
- **특징**: 최초의 NFS 버전
- **제한사항**: 32비트 파일 크기 제한, 보안 기능 부족
- **현재 상태**: 거의 사용되지 않음

### NFSv3 (1995)
- **개선사항**: 64비트 파일 크기 지원, 비동기 I/O 지원
- **성능**: NFSv2 대비 성능 향상
- **현재 상태**: 일부 레거시 시스템에서 사용

### NFSv4 (2000)
- **주요 개선**: 상태 기반 프로토콜, 강화된 보안
- **새로운 기능**: 파일 잠금, 디렉토리 위임, 복합 작업
- **보안**: Kerberos 인증 지원
- **현재 상태**: 가장 널리 사용되는 버전

### NFSv4.1 (2010)
- **주요 기능**: 병렬 NFS (pNFS), 세션 트렁킹
- **성능**: 대역폭 집계, 로드 밸런싱
- **확장성**: 대규모 클러스터 환경 지원

### NFSv4.2 (2016)
- **새로운 기능**: 서버 사이드 복사, 스파스 파일 지원
- **성능**: 효율적인 데이터 전송
- **현재 상태**: 최신 버전, 점진적 도입

---

## 실제 사용 사례

### 1. 개발 환경
- **소스 코드 공유**: 여러 개발자가 같은 소스 코드에 접근
- **빌드 결과물 공유**: 컴파일된 바이너리 파일 공유
- **설정 파일 중앙 관리**: 환경별 설정 파일 통합 관리

### 2. 로그 수집 및 분석
- **중앙 집중식 로그**: 여러 서버의 로그를 한 곳에 저장
- **실시간 모니터링**: 로그 분석 및 모니터링 시스템
- **백업 및 아카이빙**: 로그 파일의 장기 보관

### 3. 컨테이너 환경
- **Docker 볼륨**: Docker 컨테이너 간 데이터 공유
- **Kubernetes PV**: 여러 Pod가 같은 데이터 접근
- **마이크로서비스**: 서비스 간 공유 데이터 저장소

### 4. 백업 시스템
- **중앙 백업**: 여러 서버의 백업을 중앙 저장소에 저장
- **백업 관리**: 백업 정책 및 복구 관리
- **재해 복구**: 백업 데이터를 통한 시스템 복구

### 5. 미디어 서버
- **파일 서버**: 대용량 미디어 파일 공유
- **스트리밍**: 여러 클라이언트가 동시에 미디어 접근
- **콘텐츠 관리**: 미디어 라이브러리 중앙 관리

---

## 설치 및 설정

### NFS 서버 설정 (Ubuntu/Debian)

#### 1단계: NFS 서버 설치
```bash
# 패키지 업데이트 및 NFS 서버 설치
sudo apt update
sudo apt install -y nfs-kernel-server
```

#### 2단계: 공유 디렉토리 생성
```bash
# 공유할 디렉토리 생성
sudo mkdir -p /nfs/shared

# 권한 설정
sudo chown nobody:nogroup /nfs/shared
sudo chmod 777 /nfs/shared
```

#### 3단계: NFS 공유 설정
```bash
# /etc/exports 파일에 공유 설정 추가
echo "/nfs/shared *(rw,sync,no_root_squash,no_subtree_check)" | sudo tee -a /etc/exports
```

**설정 옵션 설명:**
- `rw`: 읽기/쓰기 모두 가능
- `sync`: 데이터 변경사항을 즉시 디스크에 저장
- `no_root_squash`: 클라이언트의 root 권한을 그대로 유지
- `no_subtree_check`: 성능 향상을 위한 옵션

#### 4단계: NFS 서비스 시작
```bash
# NFS 서비스 시작 및 활성화
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server
```

### NFS 클라이언트 설정

#### 1단계: NFS 클라이언트 설치
```bash
# NFS 클라이언트 패키지 설치
sudo apt update
sudo apt install -y nfs-common
```

#### 2단계: 서버 공유 확인
```bash
# NFS 서버에서 공유 중인 디렉토리 확인
showmount -e <NFS_SERVER_IP>
```

#### 3단계: NFS 디렉토리 마운트
```bash
# 마운트 포인트 생성
sudo mkdir -p /mnt/nfs

# NFS 디렉토리 마운트
sudo mount <NFS_SERVER_IP>:/nfs/shared /mnt/nfs
```

#### 4단계: 자동 마운트 설정
```bash
# /etc/fstab에 추가하여 부팅 시 자동 마운트
echo "<NFS_SERVER_IP>:/nfs/shared /mnt/nfs nfs defaults 0 0" | sudo tee -a /etc/fstab
```

---

## 보안 고려사항

### 네트워크 보안
```bash
# 특정 IP만 접근 허용
# /etc/exports 파일 수정
/nfs/shared 192.168.1.0/24(rw,sync,no_subtree_check)

# 방화벽 설정
sudo ufw allow from 192.168.1.0/24 to any port nfs
```

### 암호화
```bash
# NFS over TLS (NFSv4.2 이상)
sudo mount -o tls <NFS_SERVER_IP>:/nfs/shared /mnt/nfs
```

### 인증 및 권한
- **Kerberos 인증**: NFSv4에서 지원하는 강력한 인증
- **사용자 매핑**: UID/GID 기반의 사용자 권한 관리
- **파일 권한**: UNIX 파일 권한 시스템 활용

---

## 장단점 분석

### 장점
- ✅ **중앙 집중식 파일 관리**: 모든 파일을 한 곳에서 관리
- ✅ **여러 클라이언트 동시 접근**: 팀 작업에 유리
- ✅ **설정 간단**: 비교적 쉬운 설정
- ✅ **크로스 플랫폼**: 다양한 운영체제 지원
- ✅ **투명성**: 로컬 파일처럼 사용 가능
- ✅ **확장성**: 대규모 환경에서도 사용 가능

### 단점
- ❌ **보안 취약**: 기본적으로 암호화되지 않음
- ❌ **네트워크 의존성**: 네트워크 장애 시 접근 불가
- ❌ **속도 제한**: 네트워크 속도에 따라 성능 제한
- ❌ **권한 관리 복잡**: 세밀한 권한 설정이 어려움
- ❌ **단일 장애점**: 서버 장애 시 모든 클라이언트 영향
- ❌ **캐싱 문제**: 파일 변경 시 캐시 일관성 문제

---

## 대안 기술

### SMB/CIFS
- **특징**: Windows 파일 공유 프로토콜
- **장점**: Windows 환경에서 최적화
- **단점**: Linux 환경에서 성능 제한

### SSHFS
- **특징**: SSH를 통한 파일 시스템 마운트
- **장점**: 강력한 보안, 간단한 설정
- **단점**: 성능 제한, 단일 연결

### GlusterFS
- **특징**: 분산 파일 시스템
- **장점**: 고가용성, 확장성
- **단점**: 복잡한 설정, 높은 리소스 사용

### Ceph
- **특징**: 분산 스토리지 시스템
- **장점**: 대규모 확장성, 다양한 인터페이스
- **단점**: 복잡한 아키텍처, 높은 학습 곡선

### FTP/SFTP
- **특징**: 파일 전송 프로토콜
- **장점**: 간단한 설정, 널리 지원
- **단점**: 실시간 접근 제한, 보안 취약

---

## 참조

1. **RFC 3530** - Network File System (NFS) version 4 Protocol
2. **RFC 5661** - Network File System (NFS) Version 4 Minor Version 1 Protocol
3. **RFC 7862** - Network File System (NFS) Version 4 Minor Version 2 Protocol
4. **Sun Microsystems** - NFS: Network File System Protocol Specification
5. **Linux NFS-HOWTO** - Linux NFS Administration Guide
6. **Red Hat Enterprise Linux** - Managing NFS and NIS
7. **Oracle Solaris** - NFS Administration Guide
8. **IBM AIX** - NFS Configuration and Use
9. **Microsoft Windows** - Services for NFS Administration Guide
10. **OpenBSD** - NFS Implementation and Configuration