

# NFS (Network File System)

## 1️⃣ NFS란?
**NFS(Network File System)**는 **네트워크를 통해 파일을 공유하는 분산 파일 시스템**입니다.  
로컬 디스크에 있는 것처럼 **원격 서버의 파일을 마운트(Mount)하여 사용**할 수 있습니다.

> **👉🏻 NFS를 사용하면 여러 시스템 간에 파일을 쉽게 공유할 수 있습니다.**

---

## 2️⃣ NFS의 주요 특징

### ✅ 1. **원격 파일 시스템 지원**
- 서버의 파일을 **클라이언트에서 로컬 파일처럼 사용 가능**

### ✅ 2. **다중 클라이언트 지원**
- 여러 클라이언트가 **동시에 같은 파일을 액세스 가능**

### ✅ 3. **파일 및 디렉토리 권한 관리**
- UNIX/Linux의 **파일 권한 및 사용자 계정 기반 접근 제어 가능**

### ✅ 4. **자동 마운트(Auto Mount) 지원**
- 클라이언트 부팅 시 자동으로 NFS 디렉토리를 마운트 가능

### ✅ 5. **Cross-Platform 지원**
- Linux, UNIX, macOS, Windows에서도 NFS 사용 가능

---

## 3️⃣ NFS 동작 방식

### ✨ NFS 서버 - 클라이언트 구조

```plaintext
[NFS Server] ←→ [NFS Client1]
               ←→ [NFS Client2]
```

| 구성 요소 | 설명 |
|----------|------|
| **NFS Server** | 공유할 파일 시스템을 제공 |
| **NFS Client** | 서버의 파일 시스템을 마운트하여 사용 |
| **Export File** | NFS 서버에서 공유할 디렉토리를 정의한 파일 (`/etc/exports`) |

> **👉🏻 클라이언트는 NFS 서버의 파일을 로컬 디스크처럼 사용할 수 있습니다.**

---

## 4️⃣ NFS 설치 및 설정 (Linux)

### ✅ 1. NFS 서버 설치
```bash
sudo apt update && sudo apt install -y nfs-kernel-server
```

### ✅ 2. 공유할 디렉토리 생성 및 권한 설정
```bash
sudo mkdir -p /nfs/shared
sudo chown nobody:nogroup /nfs/shared
sudo chmod 777 /nfs/shared
```

### ✅ 3. NFS 공유 설정 (`/etc/exports` 수정)
```bash
echo "/nfs/shared *(rw,sync,no_root_squash,no_subtree_check)" | sudo tee -a /etc/exports
```

> **옵션 설명**
> - `rw`: 읽기/쓰기 가능
> - `sync`: 데이터가 즉시 저장됨
> - `no_root_squash`: 클라이언트의 root 권한을 유지

### ✅ 4. NFS 서비스 재시작 및 적용
```bash
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
```

---

## 5️⃣ NFS 클라이언트 설정

### ✅ 1. NFS 클라이언트 설치
```bash
sudo apt update && sudo apt install -y nfs-common
```

### ✅ 2. NFS 서버 공유 디렉토리 확인
```bash
showmount -e <NFS_SERVER_IP>
```

### ✅ 3. NFS 공유 디렉토리 마운트
```bash
sudo mount <NFS_SERVER_IP>:/nfs/shared /mnt
```

### ✅ 4. 자동 마운트 설정 (`/etc/fstab` 수정)
```bash
echo "<NFS_SERVER_IP>:/nfs/shared /mnt nfs defaults 0 0" | sudo tee -a /etc/fstab
```

> **👉🏻 클라이언트가 부팅될 때 자동으로 NFS 디렉토리를 마운트할 수 있습니다.**

---

## 6️⃣ NFS 보안 설정

### ✅ 1. 특정 IP 또는 네트워크만 접근 허용 (`/etc/exports`)
```bash
/nfs/shared 192.168.1.0/24(rw,sync,no_subtree_check)
```

### ✅ 2. 방화벽에서 NFS 포트 허용
```bash
sudo ufw allow from 192.168.1.0/24 to any port nfs
```

### ✅ 3. NFS over TLS 사용 (NFSv4.2 이상)

```bash
sudo mount -o tls <NFS_SERVER_IP>:/nfs/shared /mnt
```

> **👉🏻 TLS를 적용하면 데이터 암호화가 가능하여 보안성이 향상됩니다.**

---

## 7️⃣ NFS의 장점과 단점

| 장점 | 단점 |
|------|------|
| **중앙 집중식 파일 관리 가능** | **보안이 상대적으로 취약** |
| **여러 클라이언트에서 공유 가능** | **인터넷을 통한 사용 시 속도 저하** |
| **설정이 비교적 간단** | **네트워크 장애 시 파일 접근 불가** |
| **Cross-Platform 지원** | **권한 설정이 복잡할 수 있음** |

> **👉🏻 NFS는 내부 네트워크에서 파일 공유 및 중앙화된 데이터 관리에 유용합니다.**

---

## 8️⃣ NFS vs SMB vs FTP 비교

| 비교 항목 | NFS | SMB | FTP |
|-----------|-----|-----|-----|
| **주요 용도** | UNIX/Linux 파일 공유 | Windows 파일 공유 | 파일 전송 |
| **운영 체제** | Linux, UNIX, macOS, Windows | Windows, Linux, macOS | 모든 OS |
| **보안 수준** | 기본적으로 낮음 (TLS 적용 가능) | 상대적으로 강함 | 암호화 필요 |
| **속도** | 빠름 (로컬 마운트 방식) | 중간 | 느림 (파일 단위 전송) |
| **연결 방식** | 네트워크 파일 시스템 | 네트워크 파일 공유 | 클라이언트-서버 파일 전송 |

> **👉🏻 NFS는 리눅스/유닉스 환경에서 네트워크 파일 공유에 최적화된 시스템입니다.**

---

## 9️⃣ NFS 활용 사례

✅ **사내 서버 간 파일 공유**
- 개발 및 운영 서버에서 파일을 공유하는 용도로 사용

✅ **컨테이너 및 Kubernetes 환경에서 파일 스토리지**
- 여러 Pod가 같은 볼륨을 사용할 때 NFS 활용

✅ **백업 및 로그 저장소**
- 여러 서버의 로그 데이터를 한 곳에서 저장 및 관리

✅ **클러스터 환경에서 데이터 공유**
- 고성능 컴퓨팅(Cluster) 시스템에서 데이터 공유

