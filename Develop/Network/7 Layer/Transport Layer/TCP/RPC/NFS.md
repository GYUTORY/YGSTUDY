---
title: NFS Network File System
tags: [network, 7-layer, transport-layer, tcp, rpc]
updated: 2025-08-10
---
# NFS (Network File System)

## 배경
- [NFS란?](#nfs란)
- [핵심 용어 정리](#핵심-용어-정리)
- [NFS의 주요 특징](#nfs의-주요-특징)
- [NFS 동작 방식](#nfs-동작-방식)
- [실제 사용 예시](#실제-사용-예시)
- [설치 및 설정](#설치-및-설정)
- [보안 설정](#보안-설정)
- [장단점 및 활용 사례](#장단점-및-활용-사례)

---

- **구글 드라이브나 드롭박스**와 비슷하지만, 더 직접적이고 빠른 방식
- 마치 **USB를 여러 컴퓨터에 동시에 꽂아서 사용하는 것**과 같은 개념

---


| 용어 | 설명 | 비유 |
|------|------|------|
| **마운트(Mount)** | 원격 디스크를 로컬 디스크처럼 연결하는 것 | USB를 컴퓨터에 꽂는 것과 같음 |
| **Export** | NFS 서버에서 공유할 디렉토리를 설정하는 것 | 공유 폴더를 만드는 것 |
| **클라이언트** | NFS 서버의 파일을 사용하는 컴퓨터 | 파일을 받아서 사용하는 쪽 |
| **서버** | 파일을 공유해주는 컴퓨터 | 파일을 제공해주는 쪽 |
| **분산 파일 시스템** | 여러 컴퓨터에 흩어져 있는 파일을 하나처럼 관리하는 시스템 | 여러 창고의 물건을 하나의 매장에서 관리하는 것 |

---

- 서버의 파일을 클라이언트에서 **로컬 파일처럼 사용 가능**
- 파일을 복사할 필요 없이 **직접 접근 가능**

- 여러 클라이언트가 **동시에 같은 파일에 접근 가능**
- 마치 여러 사람이 같은 문서를 동시에 편집하는 것과 같음

- UNIX/Linux의 파일 권한 시스템 활용
- 사용자별로 읽기/쓰기 권한 제어 가능

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

1. **서버 설정**: NFS 서버가 특정 디렉토리를 공유하도록 설정
2. **클라이언트 연결**: 클라이언트가 서버의 공유 디렉토리를 로컬에 마운트
3. **파일 접근**: 클라이언트가 마운트된 디렉토리를 통해 서버 파일에 접근
4. **동기화**: 여러 클라이언트가 동시에 같은 파일에 접근 가능

---


### JavaScript 개발 환경에서의 활용

```javascript
// 개발 서버에서 공유 디렉토리 사용 예시
const fs = require('fs');
const path = require('path');

// NFS로 마운트된 공유 디렉토리 경로
const sharedDir = '/mnt/nfs/shared';
const logDir = path.join(sharedDir, 'logs');
const dataDir = path.join(sharedDir, 'data');

// 여러 서버에서 같은 로그 파일에 동시 접근
function writeLog(message) {
    const timestamp = new Date().toISOString();
    const logFile = path.join(logDir, `app-${new Date().toISOString().split('T')[0]}.log`);
    
    const logEntry = `[${timestamp}] ${message}\n`;
    
    // NFS를 통해 공유된 로그 파일에 쓰기
    fs.appendFileSync(logFile, logEntry);
}

// 공유 데이터 읽기
function readSharedData(filename) {
    const filePath = path.join(dataDir, filename);
    
    try {
        const data = fs.readFileSync(filePath, 'utf8');
        return JSON.parse(data);
    } catch (error) {
        console.error('파일 읽기 실패:', error.message);
        return null;
    }
}

// 사용 예시
writeLog('서버 시작됨');
const config = readSharedData('config.json');
```

### 웹 애플리케이션에서의 활용

```javascript
// Express.js에서 NFS 공유 디렉토리 활용
const express = require('express');
const multer = require('multer');
const path = require('path');

const app = express();

// NFS 공유 디렉토리를 업로드 경로로 설정
const uploadDir = '/mnt/nfs/uploads';

// Multer 설정 - NFS 디렉토리에 파일 저장
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueName = Date.now() + '-' + file.originalname;
        cb(null, uniqueName);
    }
});

const upload = multer({ storage: storage });

// 파일 업로드 API
app.post('/upload', upload.single('file'), (req, res) => {
    if (req.file) {
        res.json({
            success: true,
            filename: req.file.filename,
            path: req.file.path
        });
    } else {
        res.status(400).json({ success: false, message: '파일 업로드 실패' });
    }
});

// 공유 파일 목록 조회
app.get('/files', (req, res) => {
    const fs = require('fs');
    
    fs.readdir(uploadDir, (err, files) => {
        if (err) {
            res.status(500).json({ error: '파일 목록 조회 실패' });
        } else {
            res.json({ files: files });
        }
    });
});
```

---


```javascript
// Express.js에서 NFS 공유 디렉토리 활용
const express = require('express');
const multer = require('multer');
const path = require('path');

const app = express();

// NFS 공유 디렉토리를 업로드 경로로 설정
const uploadDir = '/mnt/nfs/uploads';

// Multer 설정 - NFS 디렉토리에 파일 저장
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueName = Date.now() + '-' + file.originalname;
        cb(null, uniqueName);
    }
});

const upload = multer({ storage: storage });

// 파일 업로드 API
app.post('/upload', upload.single('file'), (req, res) => {
    if (req.file) {
        res.json({
            success: true,
            filename: req.file.filename,
            path: req.file.path
        });
    } else {
        res.status(400).json({ success: false, message: '파일 업로드 실패' });
    }
});

// 공유 파일 목록 조회
app.get('/files', (req, res) => {
    const fs = require('fs');
    
    fs.readdir(uploadDir, (err, files) => {
        if (err) {
            res.status(500).json({ error: '파일 목록 조회 실패' });
        } else {
            res.json({ files: files });
        }
    });
});
```

---


### NFS 서버 설정 (Ubuntu/Debian)

#### 1단계: NFS 서버 설치
```bash

sudo mkdir -p /nfs/shared

sudo chown nobody:nogroup /nfs/shared
sudo chmod 777 /nfs/shared
```

#### 3단계: NFS 공유 설정
```bash

sudo exportfs -a
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server
```

### NFS 클라이언트 설정

#### 1단계: NFS 클라이언트 설치
```bash

sudo mkdir -p /mnt/nfs


### 특정 IP만 접근 허용
```bash

```bash


### 장점
- ✅ **중앙 집중식 파일 관리**: 모든 파일을 한 곳에서 관리
- ✅ **여러 클라이언트 동시 접근**: 팀 작업에 유리
- ✅ **설정 간단**: 비교적 쉬운 설정
- ✅ **크로스 플랫폼**: 다양한 운영체제 지원

### 단점
- ❌ **보안 취약**: 기본적으로 암호화되지 않음
- ❌ **네트워크 의존성**: 네트워크 장애 시 접근 불가
- ❌ **속도 제한**: 네트워크 속도에 따라 성능 제한
- ❌ **권한 관리 복잡**: 세밀한 권한 설정이 어려움

### 실제 활용 사례

#### 1. 개발 환경
- 여러 개발자가 같은 소스 코드에 접근
- 빌드 결과물 공유
- 설정 파일 중앙 관리

#### 2. 로그 수집
- 여러 서버의 로그를 한 곳에 저장
- 로그 분석 및 모니터링

#### 3. 컨테이너 환경
- Docker/Kubernetes에서 볼륨 공유
- 여러 Pod가 같은 데이터 접근

#### 4. 백업 시스템
- 여러 서버의 백업을 중앙 저장소에 저장
- 백업 관리 및 복구

---

- ✅ **중앙 집중식 파일 관리**: 모든 파일을 한 곳에서 관리
- ✅ **여러 클라이언트 동시 접근**: 팀 작업에 유리
- ✅ **설정 간단**: 비교적 쉬운 설정
- ✅ **크로스 플랫폼**: 다양한 운영체제 지원

- ❌ **보안 취약**: 기본적으로 암호화되지 않음
- ❌ **네트워크 의존성**: 네트워크 장애 시 접근 불가
- ❌ **속도 제한**: 네트워크 속도에 따라 성능 제한
- ❌ **권한 관리 복잡**: 세밀한 권한 설정이 어려움


#### 1. 개발 환경
- 여러 개발자가 같은 소스 코드에 접근
- 빌드 결과물 공유
- 설정 파일 중앙 관리

#### 2. 로그 수집
- 여러 서버의 로그를 한 곳에 저장
- 로그 분석 및 모니터링

#### 3. 컨테이너 환경
- Docker/Kubernetes에서 볼륨 공유
- 여러 Pod가 같은 데이터 접근

#### 4. 백업 시스템
- 여러 서버의 백업을 중앙 저장소에 저장
- 백업 관리 및 복구

---


- **SMB/CIFS**: Windows 파일 공유 프로토콜
- **FTP**: 파일 전송 프로토콜
- **SSHFS**: SSH를 통한 파일 시스템 마운트
- **GlusterFS**: 분산 파일 시스템
- **Ceph**: 분산 스토리지 시스템







```javascript
// Express.js에서 NFS 공유 디렉토리 활용
const express = require('express');
const multer = require('multer');
const path = require('path');

const app = express();

// NFS 공유 디렉토리를 업로드 경로로 설정
const uploadDir = '/mnt/nfs/uploads';

// Multer 설정 - NFS 디렉토리에 파일 저장
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueName = Date.now() + '-' + file.originalname;
        cb(null, uniqueName);
    }
});

const upload = multer({ storage: storage });

// 파일 업로드 API
app.post('/upload', upload.single('file'), (req, res) => {
    if (req.file) {
        res.json({
            success: true,
            filename: req.file.filename,
            path: req.file.path
        });
    } else {
        res.status(400).json({ success: false, message: '파일 업로드 실패' });
    }
});

// 공유 파일 목록 조회
app.get('/files', (req, res) => {
    const fs = require('fs');
    
    fs.readdir(uploadDir, (err, files) => {
        if (err) {
            res.status(500).json({ error: '파일 목록 조회 실패' });
        } else {
            res.json({ files: files });
        }
    });
});
```

---


```javascript
// Express.js에서 NFS 공유 디렉토리 활용
const express = require('express');
const multer = require('multer');
const path = require('path');

const app = express();

// NFS 공유 디렉토리를 업로드 경로로 설정
const uploadDir = '/mnt/nfs/uploads';

// Multer 설정 - NFS 디렉토리에 파일 저장
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueName = Date.now() + '-' + file.originalname;
        cb(null, uniqueName);
    }
});

const upload = multer({ storage: storage });

// 파일 업로드 API
app.post('/upload', upload.single('file'), (req, res) => {
    if (req.file) {
        res.json({
            success: true,
            filename: req.file.filename,
            path: req.file.path
        });
    } else {
        res.status(400).json({ success: false, message: '파일 업로드 실패' });
    }
});

// 공유 파일 목록 조회
app.get('/files', (req, res) => {
    const fs = require('fs');
    
    fs.readdir(uploadDir, (err, files) => {
        if (err) {
            res.status(500).json({ error: '파일 목록 조회 실패' });
        } else {
            res.json({ files: files });
        }
    });
});
```

---


- ✅ **중앙 집중식 파일 관리**: 모든 파일을 한 곳에서 관리
- ✅ **여러 클라이언트 동시 접근**: 팀 작업에 유리
- ✅ **설정 간단**: 비교적 쉬운 설정
- ✅ **크로스 플랫폼**: 다양한 운영체제 지원

- ❌ **보안 취약**: 기본적으로 암호화되지 않음
- ❌ **네트워크 의존성**: 네트워크 장애 시 접근 불가
- ❌ **속도 제한**: 네트워크 속도에 따라 성능 제한
- ❌ **권한 관리 복잡**: 세밀한 권한 설정이 어려움


#### 1. 개발 환경
- 여러 개발자가 같은 소스 코드에 접근
- 빌드 결과물 공유
- 설정 파일 중앙 관리

#### 2. 로그 수집
- 여러 서버의 로그를 한 곳에 저장
- 로그 분석 및 모니터링

#### 3. 컨테이너 환경
- Docker/Kubernetes에서 볼륨 공유
- 여러 Pod가 같은 데이터 접근

#### 4. 백업 시스템
- 여러 서버의 백업을 중앙 저장소에 저장
- 백업 관리 및 복구

---

- ✅ **중앙 집중식 파일 관리**: 모든 파일을 한 곳에서 관리
- ✅ **여러 클라이언트 동시 접근**: 팀 작업에 유리
- ✅ **설정 간단**: 비교적 쉬운 설정
- ✅ **크로스 플랫폼**: 다양한 운영체제 지원

- ❌ **보안 취약**: 기본적으로 암호화되지 않음
- ❌ **네트워크 의존성**: 네트워크 장애 시 접근 불가
- ❌ **속도 제한**: 네트워크 속도에 따라 성능 제한
- ❌ **권한 관리 복잡**: 세밀한 권한 설정이 어려움


#### 1. 개발 환경
- 여러 개발자가 같은 소스 코드에 접근
- 빌드 결과물 공유
- 설정 파일 중앙 관리

#### 2. 로그 수집
- 여러 서버의 로그를 한 곳에 저장
- 로그 분석 및 모니터링

#### 3. 컨테이너 환경
- Docker/Kubernetes에서 볼륨 공유
- 여러 Pod가 같은 데이터 접근

#### 4. 백업 시스템
- 여러 서버의 백업을 중앙 저장소에 저장
- 백업 관리 및 복구

---


- **SMB/CIFS**: Windows 파일 공유 프로토콜
- **FTP**: 파일 전송 프로토콜
- **SSHFS**: SSH를 통한 파일 시스템 마운트
- **GlusterFS**: 분산 파일 시스템
- **Ceph**: 분산 스토리지 시스템










## 🎯 NFS란?

**NFS(Network File System)**는 네트워크를 통해 파일을 공유하는 분산 파일 시스템입니다.

쉽게 말해서, **다른 컴퓨터에 있는 파일을 내 컴퓨터에 있는 것처럼 사용할 수 있게 해주는 시스템**입니다.

## ✨ NFS의 주요 특징

### 🚀 자동 마운트(Auto Mount) 지원
- 컴퓨터를 켤 때마다 자동으로 NFS 디렉토리 연결
- 수동으로 연결할 필요 없음

### 🌐 Cross-Platform 지원
- Linux, UNIX, macOS, Windows에서 모두 사용 가능

---

## 🔄 NFS 동작 방식

# 패키지 업데이트 및 NFS 서버 설치
sudo apt update
sudo apt install -y nfs-kernel-server
```

#### 2단계: 공유 디렉토리 생성
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
# NFS 디렉토리 마운트
sudo mount <NFS_SERVER_IP>:/nfs/shared /mnt/nfs
```

#### 4단계: 자동 마운트 설정
```bash
# /etc/fstab에 추가하여 부팅 시 자동 마운트
echo "<NFS_SERVER_IP>:/nfs/shared /mnt/nfs nfs defaults 0 0" | sudo tee -a /etc/fstab
```

---

# /etc/exports 파일 수정
/nfs/shared 192.168.1.0/24(rw,sync,no_subtree_check)
```

# 특정 네트워크에서만 NFS 접근 허용
sudo ufw allow from 192.168.1.0/24 to any port nfs
```

### NFS over TLS (암호화)
```bash
# NFSv4.2 이상에서 TLS 적용
sudo mount -o tls <NFS_SERVER_IP>:/nfs/shared /mnt/nfs
```

---

