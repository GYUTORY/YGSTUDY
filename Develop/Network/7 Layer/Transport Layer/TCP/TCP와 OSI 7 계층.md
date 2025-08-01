# TCP와 OSI 7 계층

> 💡 **핵심 개념**
> 
> TCP(Transmission Control Protocol)는 인터넷에서 가장 널리 사용되는 전송 계층 프로토콜입니다. 데이터를 신뢰성 있게 전송하는 데 중점을 두며, OSI(Open Systems Interconnection) 7 계층 모델의 핵심 구성 요소 중 하나로 동작합니다.

---

## 📋 목차
- [OSI 7 계층 모델이란?](#1-osi-7-계층-모델이란)
- [TCP의 위치와 역할](#2-tcp의-위치와-역할)
- [TCP 동작 원리](#3-tcp-동작-원리)
- [TCP vs UDP 비교](#4-tcp-vs-udp-비교)
- [실제 데이터 흐름](#5-실제-데이터-흐름)
- [TCP의 한계와 대안](#6-tcp의-한계와-대안)

---

## 1. OSI 7 계층 모델이란?

### 🔍 OSI 모델이 필요한 이유

인터넷에서 데이터가 어떻게 전송되는지 이해하기 위해서는 복잡한 네트워크 통신 과정을 단계별로 나누어 생각해야 합니다. 마치 택배를 보낼 때 포장 → 배송 → 수령 과정이 있듯이, 네트워크 통신도 여러 단계를 거칩니다.

OSI 7 계층 모델은 이러한 복잡한 네트워크 통신을 7개의 단계로 나누어 각 단계의 역할을 명확히 정의한 표준 모델입니다.

### 📊 OSI 7 계층 구조

| 계층 | 계층 이름 | 주요 역할 | 대표적인 프로토콜 | 간단한 설명 |
|------|-----------|-----------|-------------------|-------------|
| **7** | **응용 계층**<br>(Application Layer) | 사용자와 직접 상호작용 | HTTP, FTP, SMTP, DNS | 웹 브라우저, 이메일 클라이언트 등 사용자가 직접 사용하는 프로그램 |
| **6** | **표현 계층**<br>(Presentation Layer) | 데이터 형식 변환 | JPEG, PNG, ASCII, UTF-8 | 이미지, 텍스트 등 다양한 형태의 데이터를 네트워크에서 전송 가능한 형태로 변환 |
| **5** | **세션 계층**<br>(Session Layer) | 연결 세션 관리 | NetBIOS, RPC | 두 컴퓨터 간의 대화(세션)를 시작하고, 유지하고, 종료 |
| **4** | **전송 계층**<br>(Transport Layer) | **데이터 전송의 신뢰성 보장** | **TCP, UDP** | **데이터가 올바르게 전송되었는지 확인하고, 손실된 데이터를 재전송** |
| **3** | **네트워크 계층**<br>(Network Layer) | 데이터 전송 경로 설정 | IP, ICMP, ARP | 인터넷상에서 데이터가 어떤 경로로 이동할지 결정 |
| **2** | **데이터 링크 계층**<br>(Data Link Layer) | 물리적 연결과 오류 제어 | Ethernet, WiFi, PPP | 실제 네트워크 장비 간의 연결과 데이터 전송 오류 검출 |
| **1** | **물리 계층**<br>(Physical Layer) | 실제 신호 전송 | 케이블, 무선 신호 | 전기 신호나 빛 신호로 데이터를 실제로 전송 |

### 🎯 계층별 데이터 처리 과정

```javascript
// 웹 페이지 요청 시 데이터가 계층을 거치는 과정
const webRequest = {
  // 7계층: 사용자가 "https://example.com" 입력
  application: "GET / HTTP/1.1",
  
  // 6계층: 텍스트를 바이너리로 변환
  presentation: Buffer.from("GET / HTTP/1.1", 'utf8'),
  
  // 5계층: 세션 시작
  session: "Session ID: 12345",
  
  // 4계층: TCP 헤더 추가 (이 문서의 핵심!)
  transport: {
    sourcePort: 54321,
    destPort: 80,
    sequenceNumber: 1000,
    data: "GET / HTTP/1.1"
  },
  
  // 3계층: IP 헤더 추가
  network: {
    sourceIP: "192.168.1.100",
    destIP: "93.184.216.34",
    data: "TCP 패킷"
  },
  
  // 2계층: 이더넷 헤더 추가
  dataLink: {
    sourceMAC: "AA:BB:CC:DD:EE:FF",
    destMAC: "11:22:33:44:55:66",
    data: "IP 패킷"
  },
  
  // 1계층: 전기 신호로 변환
  physical: "1010101010101010..."
};
```

---

## 2. TCP의 위치와 역할

### 🎯 TCP는 4계층(전송 계층)에서 동작

TCP는 OSI 모델의 **4번째 계층(전송 계층)**에서 동작합니다. 이 계층은 데이터를 송신지에서 수신지로 안전하고 신뢰성 있게 전송하는 데 중점을 둡니다.

### 🔧 TCP의 핵심 기능

#### 1️⃣ **연결 지향(Connection-Oriented)**
- 데이터를 전송하기 전에 먼저 연결을 설정합니다
- 마치 전화를 걸 때 먼저 연결이 되고 나서 대화를 시작하는 것과 같습니다

#### 2️⃣ **신뢰성 보장(Reliability)**
- 데이터가 손실되면 다시 전송합니다
- 데이터의 순서를 보장합니다

#### 3️⃣ **흐름 제어(Flow Control)**
- 수신자가 처리할 수 있는 속도에 맞춰 데이터를 전송합니다

#### 4️⃣ **혼잡 제어(Congestion Control)**
- 네트워크가 혼잡할 때 전송 속도를 조절합니다

### 💡 TCP 헤더 구조 이해하기

```javascript
// TCP 헤더의 주요 필드들
const tcpHeader = {
  // 포트 정보
  sourcePort: 54321,        // 출발지 포트
  destinationPort: 80,      // 목적지 포트 (80 = HTTP)
  
  // 순서 제어
  sequenceNumber: 1000,     // 데이터 순서 번호
  acknowledgmentNumber: 2000, // 확인 응답 번호
  
  // 제어 플래그
  flags: {
    SYN: false,  // 연결 시작
    ACK: true,   // 확인 응답
    FIN: false,  // 연결 종료
    RST: false,  // 연결 재설정
    PSH: true,   // 즉시 전송
    URG: false   // 긴급 데이터
  },
  
  // 윈도우 크기 (흐름 제어용)
  windowSize: 65535,
  
  // 체크섬 (오류 검출용)
  checksum: 0xABCD
};
```

---

## 3. TCP 동작 원리

### 🤝 3-Way Handshake (연결 설정)

TCP는 데이터를 전송하기 전에 클라이언트와 서버 간의 연결을 설정합니다. 이 과정을 **3-Way Handshake**라고 합니다.

```javascript
// 3-Way Handshake 과정을 JavaScript로 시뮬레이션
class TCPConnection {
  constructor() {
    this.sequenceNumber = Math.floor(Math.random() * 10000);
    this.ackNumber = 0;
  }
  
  // 1단계: SYN (연결 요청)
  sendSYN() {
    console.log("클라이언트 → 서버: SYN (연결 요청)");
    console.log(`시퀀스 번호: ${this.sequenceNumber}`);
    return {
      type: 'SYN',
      sequenceNumber: this.sequenceNumber
    };
  }
  
  // 2단계: SYN-ACK (연결 수락 + 확인)
  sendSYNACK(clientSeq) {
    this.ackNumber = clientSeq + 1;
    this.sequenceNumber = Math.floor(Math.random() * 10000);
    console.log("서버 → 클라이언트: SYN-ACK (연결 수락 + 확인)");
    console.log(`시퀀스 번호: ${this.sequenceNumber}, 확인 번호: ${this.ackNumber}`);
    return {
      type: 'SYN-ACK',
      sequenceNumber: this.sequenceNumber,
      acknowledgmentNumber: this.ackNumber
    };
  }
  
  // 3단계: ACK (확인 응답)
  sendACK(serverSeq) {
    this.ackNumber = serverSeq + 1;
    console.log("클라이언트 → 서버: ACK (확인 응답)");
    console.log(`확인 번호: ${this.ackNumber}`);
    console.log("✅ 연결이 성공적으로 설정되었습니다!");
    return {
      type: 'ACK',
      acknowledgmentNumber: this.ackNumber
    };
  }
}

// 연결 설정 과정 실행
const client = new TCPConnection();
const server = new TCPConnection();

console.log("=== TCP 3-Way Handshake 시작 ===");
const syn = client.sendSYN();
const synAck = server.sendSYNACK(syn.sequenceNumber);
const ack = client.sendACK(synAck.sequenceNumber);
```

### 📦 데이터 전송 과정

```javascript
// TCP 데이터 전송 시뮬레이션
class TCPDataTransfer {
  constructor() {
    this.sequenceNumber = 1000;
    this.ackNumber = 0;
  }
  
  // 데이터를 패킷으로 분할하여 전송
  sendData(data) {
    const packets = this.splitIntoPackets(data);
    
    packets.forEach((packet, index) => {
      console.log(`📦 패킷 ${index + 1} 전송: ${packet}`);
      console.log(`시퀀스 번호: ${this.sequenceNumber}`);
      
      // 가상의 네트워크 지연
      setTimeout(() => {
        this.receiveAcknowledgment(packet, index + 1);
      }, Math.random() * 1000);
      
      this.sequenceNumber += packet.length;
    });
  }
  
  // 데이터를 작은 패킷으로 분할
  splitIntoPackets(data) {
    const packetSize = 10; // 실제로는 보통 1460바이트
    const packets = [];
    
    for (let i = 0; i < data.length; i += packetSize) {
      packets.push(data.slice(i, i + packetSize));
    }
    
    return packets;
  }
  
  // 확인 응답 수신
  receiveAcknowledgment(packet, packetNumber) {
    console.log(`✅ 패킷 ${packetNumber} 확인 응답 수신`);
    this.ackNumber += packet.length;
  }
}

// 데이터 전송 예시
const tcpTransfer = new TCPDataTransfer();
const message = "Hello, this is a TCP data transfer example!";
console.log("=== TCP 데이터 전송 시작 ===");
tcpTransfer.sendData(message);
```

### 👋 4-Way Handshake (연결 종료)

```javascript
// 4-Way Handshake 과정
class TCPDisconnection {
  // 1단계: FIN (연결 종료 요청)
  sendFIN() {
    console.log("클라이언트 → 서버: FIN (연결 종료 요청)");
    return { type: 'FIN' };
  }
  
  // 2단계: ACK (종료 요청 확인)
  sendACK() {
    console.log("서버 → 클라이언트: ACK (종료 요청 확인)");
    return { type: 'ACK' };
  }
  
  // 3단계: FIN (서버도 종료 요청)
  sendServerFIN() {
    console.log("서버 → 클라이언트: FIN (서버도 종료 요청)");
    return { type: 'FIN' };
  }
  
  // 4단계: ACK (최종 확인)
  sendFinalACK() {
    console.log("클라이언트 → 서버: ACK (최종 확인)");
    console.log("🔚 연결이 완전히 종료되었습니다.");
    return { type: 'ACK' };
  }
}

// 연결 종료 과정 실행
const disconnection = new TCPDisconnection();
console.log("=== TCP 4-Way Handshake 시작 ===");
disconnection.sendFIN();
disconnection.sendACK();
disconnection.sendServerFIN();
disconnection.sendFinalACK();
```

---

## 4. TCP vs UDP 비교

### 📊 상세 비교표

| 특징 | TCP | UDP |
|------|-----|-----|
| **연결 방식** | 연결 지향 (전화처럼) | 비연결 지향 (편지처럼) |
| **신뢰성** | ✅ 높음 (손실 시 재전송) | ❌ 없음 (손실 허용) |
| **순서 보장** | ✅ 보장 (순서 번호 사용) | ❌ 보장 안함 |
| **속도** | 🐌 상대적으로 느림 | ⚡ 빠름 |
| **오버헤드** | 높음 (헤더 크기 20-60바이트) | 낮음 (헤더 크기 8바이트) |
| **용도** | 웹, 이메일, 파일 전송 | 스트리밍, 게임, DNS |

### 💻 JavaScript로 보는 TCP vs UDP 차이점

```javascript
// TCP 방식 (신뢰성 중시)
class TCPExample {
  sendMessage(message) {
    console.log("🔒 TCP: 연결 설정 중...");
    
    // 1. 연결 설정
    this.establishConnection();
    
    // 2. 데이터 전송 (순서 보장)
    const packets = this.splitIntoOrderedPackets(message);
    packets.forEach((packet, index) => {
      this.sendPacket(packet, index);
      this.waitForAcknowledgment(index);
    });
    
    // 3. 연결 종료
    this.closeConnection();
    
    console.log("✅ TCP: 메시지 전송 완료 (신뢰성 보장)");
  }
  
  establishConnection() {
    console.log("🤝 3-Way Handshake 수행");
  }
  
  splitIntoOrderedPackets(message) {
    return message.split('').map((char, index) => ({
      data: char,
      sequenceNumber: index,
      order: index
    }));
  }
  
  sendPacket(packet, index) {
    console.log(`📦 패킷 ${index} 전송: ${packet.data} (순서: ${packet.order})`);
  }
  
  waitForAcknowledgment(index) {
    console.log(`⏳ 패킷 ${index} 확인 응답 대기 중...`);
  }
  
  closeConnection() {
    console.log("👋 4-Way Handshake로 연결 종료");
  }
}

// UDP 방식 (속도 중시)
class UDPExample {
  sendMessage(message) {
    console.log("🚀 UDP: 즉시 전송 시작!");
    
    // 연결 설정 없이 바로 전송
    const packets = this.splitIntoPackets(message);
    packets.forEach((packet, index) => {
      this.sendPacket(packet, index);
      // 확인 응답 대기 없음
    });
    
    console.log("⚡ UDP: 메시지 전송 완료 (빠른 속도)");
  }
  
  splitIntoPackets(message) {
    return message.split('').map((char, index) => ({
      data: char,
      index: index
    }));
  }
  
  sendPacket(packet, index) {
    console.log(`📤 패킷 ${index} 전송: ${packet.data} (순서 보장 안함)`);
  }
}

// 사용 예시
const tcpExample = new TCPExample();
const udpExample = new UDPExample();

console.log("=== TCP vs UDP 비교 ===");
console.log("\n--- TCP 방식 ---");
tcpExample.sendMessage("Hello World");

console.log("\n--- UDP 방식 ---");
udpExample.sendMessage("Hello World");
```

---

## 5. 실제 데이터 흐름

### 🌐 웹 브라우저에서 웹사이트 접속 과정

```javascript
// 웹 브라우저가 "https://example.com"에 접속하는 과정
class WebBrowser {
  constructor() {
    this.url = "https://example.com";
    this.data = "GET / HTTP/1.1";
  }
  
  // 전체 과정 시뮬레이션
  async accessWebsite() {
    console.log("🌐 웹사이트 접속 시작:", this.url);
    
    // 1. DNS 조회 (7계층)
    const ipAddress = await this.resolveDNS();
    console.log("📍 DNS 조회 완료:", ipAddress);
    
    // 2. TCP 연결 설정 (4계층)
    const tcpConnection = await this.establishTCPConnection(ipAddress);
    console.log("🔗 TCP 연결 완료");
    
    // 3. HTTP 요청 전송 (7계층)
    const response = await this.sendHTTPRequest(tcpConnection);
    console.log("📄 HTTP 응답 수신");
    
    // 4. 연결 종료
    this.closeConnection(tcpConnection);
    console.log("✅ 웹사이트 접속 완료");
    
    return response;
  }
  
  // DNS 조회 (7계층 - 응용 계층)
  async resolveDNS() {
    console.log("🔍 DNS 서버에 도메인 조회 중...");
    // 실제로는 DNS 서버에 쿼리를 보내는 과정
    return "93.184.216.34";
  }
  
  // TCP 연결 설정 (4계층 - 전송 계층)
  async establishTCPConnection(ipAddress) {
    console.log("🤝 TCP 3-Way Handshake 시작");
    
    // SYN 전송
    console.log("📤 SYN 패킷 전송");
    await this.delay(100);
    
    // SYN-ACK 수신
    console.log("📥 SYN-ACK 패킷 수신");
    await this.delay(100);
    
    // ACK 전송
    console.log("📤 ACK 패킷 전송");
    await this.delay(100);
    
    return {
      sourceIP: "192.168.1.100",
      destIP: ipAddress,
      sourcePort: 54321,
      destPort: 443, // HTTPS
      established: true
    };
  }
  
  // HTTP 요청 전송
  async sendHTTPRequest(connection) {
    console.log("📤 HTTP 요청 전송:", this.data);
    
    // TCP를 통해 데이터 전송
    const tcpPacket = {
      sourcePort: connection.sourcePort,
      destPort: connection.destPort,
      sequenceNumber: 1000,
      data: this.data,
      flags: { SYN: false, ACK: true, FIN: false }
    };
    
    console.log("📦 TCP 패킷 생성:", tcpPacket);
    
    // 가상의 응답
    await this.delay(200);
    return {
      status: 200,
      data: "<html><body><h1>Hello World!</h1></body></html>"
    };
  }
  
  // 연결 종료
  closeConnection(connection) {
    console.log("👋 TCP 연결 종료");
  }
  
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// 웹 브라우저 사용 예시
const browser = new WebBrowser();
browser.accessWebsite();
```

---

## 6. TCP의 한계와 대안

### ⚠️ TCP의 한계점

#### 1️⃣ **높은 오버헤드**
```javascript
// TCP 헤더 크기 계산
const tcpHeaderSize = {
  basicHeader: 20, // 기본 헤더 20바이트
  options: 40,     // 옵션 필드 최대 40바이트
  total: 60        // 최대 60바이트
};

// UDP 헤더 크기
const udpHeaderSize = {
  total: 8         // 고정 8바이트
};

console.log("TCP 헤더 오버헤드:", tcpHeaderSize.total, "바이트");
console.log("UDP 헤더 오버헤드:", udpHeaderSize.total, "바이트");
console.log("차이:", tcpHeaderSize.total - udpHeaderSize.total, "바이트");
```

#### 2️⃣ **단방향 전송의 비효율성**
```javascript
// TCP는 양방향 통신을 기본으로 설계
class TCPLimitation {
  // 브로드캐스트 시 비효율적
  broadcastMessage(message, recipients) {
    console.log("📢 브로드캐스트 시작");
    
    recipients.forEach(recipient => {
      // 각 수신자마다 개별 TCP 연결 필요
      this.establishConnection(recipient);
      this.sendMessage(message);
      this.closeConnection(recipient);
    });
    
    console.log("❌ 비효율적: 연결 설정/종료 오버헤드");
  }
  
  establishConnection(recipient) {
    console.log(`🤝 ${recipient}와 연결 설정`);
  }
  
  sendMessage(message) {
    console.log(`📤 메시지 전송: ${message}`);
  }
  
  closeConnection(recipient) {
    console.log(`👋 ${recipient}와 연결 종료`);
  }
}
```

### 🚀 대안 프로토콜들

#### 1️⃣ **UDP (User Datagram Protocol)**
- 실시간 스트리밍, 게임에 적합
- 빠른 속도, 낮은 지연시간

#### 2️⃣ **QUIC (Quick UDP Internet Connections)**
- HTTP/3에서 사용
- UDP 기반이지만 TCP의 신뢰성 기능 추가

```javascript
// QUIC vs TCP 비교
class ProtocolComparison {
  comparePerformance() {
    const tcpPerformance = {
      connectionTime: "100ms",
      dataTransfer: "안정적",
      latency: "높음",
      suitableFor: "파일 전송, 웹 브라우징"
    };
    
    const quicPerformance = {
      connectionTime: "0ms (0-RTT)",
      dataTransfer: "빠름",
      latency: "낮음",
      suitableFor: "실시간 스트리밍, 모바일 앱"
    };
    
    console.log("TCP 성능:", tcpPerformance);
    console.log("QUIC 성능:", quicPerformance);
  }
}
```

---

## 📝 정리

### 🎯 핵심 포인트

1. **TCP는 OSI 7계층의 4계층(전송 계층)에서 동작**
2. **신뢰성 있는 데이터 전송을 보장**
3. **3-Way Handshake로 연결 설정, 4-Way Handshake로 연결 종료**
4. **UDP보다 느리지만 신뢰성이 높음**
5. **웹 브라우징, 이메일, 파일 전송에 적합**

### 🔗 관련 개념들

- **IP (Internet Protocol)**: 3계층에서 동작, 패킷의 경로 설정
- **HTTP/HTTPS**: 7계층에서 동작, 웹 통신 프로토콜
- **DNS**: 7계층에서 동작, 도메인 이름을 IP 주소로 변환
- **SSL/TLS**: 6계층에서 동작, 데이터 암호화

### 💡 실무에서의 활용

- **웹 개발**: HTTP는 TCP를 기반으로 동작
- **API 개발**: REST API도 TCP를 사용
- **데이터베이스**: MySQL, PostgreSQL 등도 TCP 연결 사용
- **파일 전송**: FTP, SFTP 모두 TCP 기반

---

> 🔍 **추가 학습 키워드**
> 
> - TCP/IP 프로토콜 스위트
> - 네트워크 패킷 분석 (Wireshark)
> - 포트 번호와 서비스
> - 네트워크 보안과 방화벽

---
