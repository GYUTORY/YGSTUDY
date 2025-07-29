# 공인 IP(Public IP)와 사설 IP(Private IP)

## 📋 목차
- [IP 주소란?](#1-ip-주소란)
- [IP 주소 구조 이해하기](#2-ip-주소-구조-이해하기)
- [공인 IP(Public IP)란?](#3-공인-ippublic-ip란)
- [사설 IP(Private IP)란?](#4-사설-ipprivate-ip란)
- [공인 IP vs 사설 IP 비교](#5-공인-ip-vs-사설-ip-비교)
- [NAT (Network Address Translation)이란?](#6-nat-network-address-translation이란)
- [실제 활용 사례](#7-실제-활용-사례)

---

## 1️⃣ IP 주소란?

### 📝 기본 개념
IP(Internet Protocol) 주소는 **네트워크에서 장치를 식별하는 고유한 주소**입니다.  
마치 집 주소처럼, 인터넷에서 특정 컴퓨터나 기기를 찾기 위한 번지수 역할을 합니다.

### 🔍 주요 용어 설명
- **ISP (Internet Service Provider)**: 인터넷 서비스 제공업체 (KT, SK, LG 등)
- **LAN (Local Area Network)**: 근거리 통신망, 같은 건물이나 지역 내의 네트워크
- **WAN (Wide Area Network)**: 광역 통신망, 인터넷 전체를 의미
- **라우터**: 네트워크 간 데이터를 전달하는 장치

> **💡 쉽게 이해하기**: 공인 IP는 집의 실제 주소(도로명주소), 사설 IP는 집 안의 방 번호라고 생각하면 됩니다.

---

## 2️⃣ IP 주소 구조 이해하기

### 🔢 IPv4 주소 구조
IPv4 주소는 **32비트(4바이트)**로 구성되며, **8비트씩 4개 부분**으로 나뉩니다.

```
192.168.001.056
│   │   │   │
│   │   │   └── 호스트 부분 (기기 식별)
│   │   └────── 네트워크 부분
│   └────────── 네트워크 부분
└────────────── 네트워크 부분
```

### 📊 각 옥텟(8비트)의 의미
```javascript
// IP 주소를 8비트씩 나누어 보기
const ipAddress = "192.168.1.56";

// 각 부분을 2진수로 변환
const parts = ipAddress.split('.');
parts.forEach((part, index) => {
    const binary = parseInt(part).toString(2).padStart(8, '0');
    console.log(`부분 ${index + 1}: ${part} (10진수) = ${binary} (2진수)`);
});

// 출력 결과:
// 부분 1: 192 (10진수) = 11000000 (2진수)
// 부분 2: 168 (10진수) = 10101000 (2진수)
// 부분 3: 1 (10진수) = 00000001 (2진수)
// 부분 4: 56 (10진수) = 00111000 (2진수)
```

### 🎯 서브넷 마스크와 CIDR 표기법

#### CIDR 표기법이란?
`192.168.1.56/24`에서 `/24`는 **서브넷 마스크의 비트 수**를 의미합니다.

```javascript
// CIDR 표기법 이해하기
const cidrExamples = {
    "/16": "255.255.0.0",     // 16비트가 네트워크 부분
    "/24": "255.255.255.0",   // 24비트가 네트워크 부분 (가장 일반적)
    "/32": "255.255.255.255"  // 32비트가 네트워크 부분 (단일 호스트)
};

// 192.168.1.56/24의 의미
const ip = "192.168.1.56";
const cidr = 24;

console.log(`IP: ${ip}/${cidr}`);
console.log(`서브넷 마스크: ${cidrExamples["/" + cidr]}`);
console.log(`네트워크 주소: 192.168.1.0`);
console.log(`브로드캐스트 주소: 192.168.1.255`);
console.log(`사용 가능한 호스트: 192.168.1.1 ~ 192.168.1.254 (254개)`);
```

### 📈 IP 클래스별 구분

| 클래스 | 범위 | 기본 서브넷 마스크 | 용도 |
|--------|------|-------------------|------|
| **A 클래스** | `1.0.0.0 ~ 126.255.255.255` | `255.0.0.0` | 대규모 네트워크 |
| **B 클래스** | `128.0.0.0 ~ 191.255.255.255` | `255.255.0.0` | 중간 규모 네트워크 |
| **C 클래스** | `192.0.0.0 ~ 223.255.255.255` | `255.255.255.0` | 소규모 네트워크 |

```javascript
// IP 클래스 판별 함수
function getIPClass(ip) {
    const firstOctet = parseInt(ip.split('.')[0]);
    
    if (firstOctet >= 1 && firstOctet <= 126) return 'A';
    if (firstOctet >= 128 && firstOctet <= 191) return 'B';
    if (firstOctet >= 192 && firstOctet <= 223) return 'C';
    if (firstOctet >= 224 && firstOctet <= 239) return 'D';
    if (firstOctet >= 240 && firstOctet <= 255) return 'E';
    
    return 'Unknown';
}

console.log(getIPClass('192.168.1.56')); // 'C'
console.log(getIPClass('10.0.0.1'));     // 'A'
console.log(getIPClass('172.16.0.1'));   // 'B'
```

---

## 3️⃣ 공인 IP(Public IP)란?

### 📝 개념
- **전 세계에서 유일한 고유한 IP 주소**
- **인터넷에서 직접 접근 가능**
- ISP(인터넷 서비스 제공업체)에서 할당

### ✨ 특징
- **웹사이트, 서버, 클라우드 서비스 등에 사용**
- **외부에서 접근 가능 (공개됨)**
- **고유한 주소이므로 충돌이 없음**
- **유료로 할당받아야 함**

### 🔍 공인 IP 확인 방법
```javascript
// JavaScript로 공인 IP 확인 (브라우저 환경)
fetch('https://api.ipify.org?format=json')
    .then(response => response.json())
    .then(data => {
        console.log('공인 IP:', data.ip);
    })
    .catch(error => {
        console.error('IP 확인 실패:', error);
    });

// Node.js 환경에서 공인 IP 확인
const https = require('https');
https.get('https://api.ipify.org', (res) => {
    let data = '';
    res.on('data', (chunk) => data += chunk);
    res.on('end', () => console.log('공인 IP:', data));
});
```

### 📋 공인 IP 예시
| 버전 | 주소 예시 | 설명 |
|------|----------|------|
| IPv4 | `203.0.113.45` | 일반적인 공인 IPv4 주소 |
| IPv6 | `2001:db8::ff00:42:8329` | 차세대 IPv6 주소 |

---

## 4️⃣ 사설 IP(Private IP)란?

### 📝 개념
- **로컬 네트워크(LAN)에서 사용되는 IP 주소**
- **인터넷에서 직접 접근 불가**
- **공인 IP 없이 내부 네트워크에서 장치 간 통신 가능**

### ✨ 특징
- **네트워크 내부에서만 사용 가능 (인터넷 직접 연결 불가)**
- **NAT(Network Address Translation) 또는 프록시를 통해 인터넷 연결 가능**
- **사설 IP는 여러 네트워크에서 중복 사용 가능**
- **무료로 사용 가능**

### 📊 사설 IP 주소 대역
| 클래스 | 사설 IP 범위 | 서브넷 마스크 | 사용 가능한 호스트 수 |
|--------|------------|--------------|-------------------|
| **A 클래스** | `10.0.0.0 ~ 10.255.255.255` | `255.0.0.0` | 16,777,214개 |
| **B 클래스** | `172.16.0.0 ~ 172.31.255.255` | `255.240.0.0` | 1,048,574개 |
| **C 클래스** | `192.168.0.0 ~ 192.168.255.255` | `255.255.0.0` | 65,534개 |

```javascript
// 사설 IP 판별 함수
function isPrivateIP(ip) {
    const parts = ip.split('.').map(part => parseInt(part));
    
    // A 클래스 사설 IP: 10.0.0.0 ~ 10.255.255.255
    if (parts[0] === 10) return true;
    
    // B 클래스 사설 IP: 172.16.0.0 ~ 172.31.255.255
    if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true;
    
    // C 클래스 사설 IP: 192.168.0.0 ~ 192.168.255.255
    if (parts[0] === 192 && parts[1] === 168) return true;
    
    return false;
}

console.log(isPrivateIP('192.168.1.56')); // true
console.log(isPrivateIP('10.0.0.1'));     // true
console.log(isPrivateIP('172.16.0.1'));   // true
console.log(isPrivateIP('8.8.8.8'));      // false (Google DNS)
```

### 🔍 사설 IP 확인 방법
```javascript
// 브라우저에서 로컬 IP 확인
function getLocalIP() {
    return new Promise((resolve, reject) => {
        const RTCPeerConnection = window.RTCPeerConnection || 
                                 window.webkitRTCPeerConnection || 
                                 window.mozRTCPeerConnection;
        
        if (!RTCPeerConnection) {
            reject('WebRTC not supported');
            return;
        }
        
        const pc = new RTCPeerConnection();
        pc.createDataChannel('');
        pc.createOffer().then(offer => pc.setLocalDescription(offer));
        
        pc.onicecandidate = (ice) => {
            if (!ice || !ice.candidate) return;
            
            const ipRegex = /([0-9]{1,3}(\.[0-9]{1,3}){3})/;
            const match = ipRegex.exec(ice.candidate.candidate);
            if (match) {
                resolve(match[1]);
            }
        };
    });
}

getLocalIP().then(ip => console.log('로컬 IP:', ip));
```

---

## 5️⃣ 공인 IP vs 사설 IP 비교

| 비교 항목 | 공인 IP (Public IP) | 사설 IP (Private IP) |
|----------|-----------------|----------------|
| **사용 범위** | 인터넷에서 사용 | 내부 네트워크에서 사용 |
| **고유성** | 전 세계에서 유일함 | 여러 네트워크에서 동일한 IP 사용 가능 |
| **인터넷 직접 연결** | 가능 | 불가능 (NAT 필요) |
| **ISP 제공 여부** | ISP에서 할당 (유료) | 네트워크 관리자 또는 라우터가 자동 할당 (무료) |
| **보안** | 외부에서 직접 접근 가능 (보안 주의) | 외부에서 직접 접근 불가 (상대적으로 안전) |
| **예시** | `203.0.113.45` | `192.168.1.100` |

```javascript
// IP 타입 판별 및 정보 출력
function analyzeIP(ip) {
    const isPrivate = isPrivateIP(ip);
    const ipClass = getIPClass(ip);
    
    return {
        ip: ip,
        type: isPrivate ? '사설 IP' : '공인 IP',
        class: ipClass,
        description: isPrivate 
            ? '내부 네트워크에서만 사용 가능' 
            : '인터넷에서 직접 접근 가능',
        security: isPrivate 
            ? '상대적으로 안전' 
            : '외부 접근 가능하므로 보안 주의'
    };
}

console.log(analyzeIP('192.168.1.56'));
// { ip: '192.168.1.56', type: '사설 IP', class: 'C', ... }

console.log(analyzeIP('8.8.8.8'));
// { ip: '8.8.8.8', type: '공인 IP', class: 'A', ... }
```

---

## 6️⃣ NAT (Network Address Translation)이란?

### 📝 개념
NAT는 **사설 IP 주소를 공인 IP 주소로 변환하여 인터넷에 연결하는 기술**입니다.

### 🔧 NAT의 역할
- **여러 장치가 하나의 공인 IP를 공유하여 인터넷에 연결 가능**
- **사설 네트워크의 보안 강화 (외부에서 직접 접근 불가)**
- **IP 주소 부족 문제 해결**

### 📊 NAT 유형
| NAT 종류 | 설명 | 사용 사례 |
|---------|------|----------|
| **정적 NAT (Static NAT)** | 사설 IP ↔ 공인 IP를 1:1 매핑 | 웹 서버, 메일 서버 |
| **동적 NAT (Dynamic NAT)** | 여러 개의 사설 IP를 동적으로 공인 IP와 매핑 | 기업 네트워크 |
| **PAT (Port Address Translation)** | 하나의 공인 IP를 여러 장치가 공유 (가장 일반적인 방식) | 가정용 라우터 |

```javascript
// NAT 동작 시뮬레이션
class NATSimulator {
    constructor(publicIP) {
        this.publicIP = publicIP;
        this.portMapping = new Map();
        this.nextPort = 1024;
    }
    
    // 사설 IP를 공인 IP로 변환
    translate(privateIP, privatePort) {
        const key = `${privateIP}:${privatePort}`;
        
        if (!this.portMapping.has(key)) {
            this.portMapping.set(key, this.nextPort++);
        }
        
        const publicPort = this.portMapping.get(key);
        
        return {
            original: `${privateIP}:${privatePort}`,
            translated: `${this.publicIP}:${publicPort}`,
            type: 'PAT (Port Address Translation)'
        };
    }
}

// NAT 시뮬레이션 예시
const nat = new NATSimulator('203.0.113.45');

console.log(nat.translate('192.168.1.100', 3000));
// { original: '192.168.1.100:3000', translated: '203.0.113.45:1024', ... }

console.log(nat.translate('192.168.1.101', 8080));
// { original: '192.168.1.101:8080', translated: '203.0.113.45:1025', ... }
```

### 🔄 NAT 동작 과정
```plaintext
[PC1: 192.168.1.2:3000] → [라우터: NAT 적용] → [공인 IP: 203.0.113.45:1024] → 인터넷
[PC2: 192.168.1.3:8080] → [라우터: NAT 적용] → [공인 IP: 203.0.113.45:1025] → 인터넷
```

---

## 7️⃣ 실제 활용 사례

### 🏠 가정용 네트워크 구성
```javascript
// 가정용 네트워크 시뮬레이션
const homeNetwork = {
    router: {
        publicIP: '203.0.113.45',
        privateIP: '192.168.1.1',
        devices: [
            { name: '노트북', ip: '192.168.1.100', mac: 'AA:BB:CC:DD:EE:01' },
            { name: '스마트폰', ip: '192.168.1.101', mac: 'AA:BB:CC:DD:EE:02' },
            { name: '스마트TV', ip: '192.168.1.102', mac: 'AA:BB:CC:DD:EE:03' },
            { name: '게임기', ip: '192.168.1.103', mac: 'AA:BB:CC:DD:EE:04' }
        ]
    },
    
    // NAT를 통한 인터넷 접속
    connectToInternet(deviceName) {
        const device = this.router.devices.find(d => d.name === deviceName);
        if (device) {
            return {
                device: device.name,
                privateAddress: `${device.ip}:${Math.floor(Math.random() * 65535)}`,
                publicAddress: `${this.router.publicIP}:${Math.floor(Math.random() * 65535)}`,
                message: 'NAT를 통해 인터넷에 연결됨'
            };
        }
        return null;
    }
};

console.log(homeNetwork.connectToInternet('노트북'));
```

### 🏢 기업용 네트워크 구성
```javascript
// 기업용 네트워크 시뮬레이션
const enterpriseNetwork = {
    departments: {
        개발팀: {
            network: '10.1.0.0/24',
            devices: ['10.1.0.1', '10.1.0.2', '10.1.0.3']
        },
        인사팀: {
            network: '10.2.0.0/24',
            devices: ['10.2.0.1', '10.2.0.2']
        },
        마케팅팀: {
            network: '10.3.0.0/24',
            devices: ['10.3.0.1', '10.3.0.2', '10.3.0.3', '10.3.0.4']
        }
    },
    
    publicServers: {
        webServer: '203.0.113.10',
        mailServer: '203.0.113.11',
        dnsServer: '203.0.113.12'
    },
    
    // 부서별 네트워크 정보 출력
    getNetworkInfo() {
        return Object.entries(this.departments).map(([dept, info]) => ({
            department: dept,
            network: info.network,
            deviceCount: info.devices.length,
            firstDevice: info.devices[0],
            lastDevice: info.devices[info.devices.length - 1]
        }));
    }
};

console.log(enterpriseNetwork.getNetworkInfo());
```

### ☁️ 클라우드 환경 (AWS VPC 예시)
```javascript
// AWS VPC 네트워크 구성 시뮬레이션
const awsVPC = {
    vpc: {
        cidr: '10.0.0.0/16',
        region: 'ap-northeast-2'
    },
    
    subnets: {
        public: [
            { cidr: '10.0.1.0/24', az: 'ap-northeast-2a', purpose: '웹 서버' },
            { cidr: '10.0.2.0/24', az: 'ap-northeast-2c', purpose: '로드 밸런서' }
        ],
        private: [
            { cidr: '10.0.10.0/24', az: 'ap-northeast-2a', purpose: '애플리케이션 서버' },
            { cidr: '10.0.11.0/24', az: 'ap-northeast-2c', purpose: '데이터베이스' }
        ]
    },
    
    natGateway: {
        publicIP: '3.34.123.45',
        privateIP: '10.0.1.100'
    },
    
    // NAT Gateway를 통한 프라이빗 서브넷의 인터넷 접속
    connectPrivateToInternet(privateSubnet) {
        return {
            source: `${privateSubnet.cidr}의 인스턴스`,
            natGateway: this.natGateway.publicIP,
            destination: '인터넷',
            message: 'NAT Gateway를 통해 인터넷에 연결됨'
        };
    }
};

console.log(awsVPC.connectPrivateToInternet(awsVPC.subnets.private[0]));
```

### 📱 모바일 네트워크
```javascript
// 모바일 네트워크 시뮬레이션
const mobileNetwork = {
    carrier: 'SKT',
    apn: 'internet',
    
    // 모바일 기기의 IP 할당 과정
    assignIP(deviceId) {
        const privateIP = `10.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`;
        const publicIP = `211.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`;
        
        return {
            deviceId: deviceId,
            privateIP: privateIP,
            publicIP: publicIP,
            connectionType: '4G/5G',
            message: '모바일 네트워크를 통해 인터넷에 연결됨'
        };
    }
};

console.log(mobileNetwork.assignIP('Galaxy-S21'));
```

---

## 📚 추가 학습 포인트

### 🔍 실습 과제
1. **자신의 네트워크 환경 분석**
   - 현재 사용 중인 공인 IP와 사설 IP 확인
   - 네트워크 구성도 그리기

2. **IP 주소 계산 연습**
   - CIDR 표기법으로 네트워크 주소 계산
   - 서브넷 마스크 이해하기

3. **NAT 동작 원리 이해**
   - 라우터 설정 확인
   - 포트 포워딩 실습

### 🛠️ 유용한 도구들
- **IP 계산기**: 온라인 CIDR 계산기
- **네트워크 스캐너**: nmap, Wireshark
- **라우터 관리**: 공유기 설정 페이지 접속

### ⚠️ 주의사항
- **공인 IP는 보안에 민감**: 방화벽 설정 필수
- **사설 IP 충돌 주의**: 같은 네트워크 내 중복 IP 사용 금지
- **NAT 설정 확인**: 인터넷 연결 문제 시 NAT 설정 점검

