# TCP 패킷 구조 상세 설명

## 📋 목차
- [1. TCP 패킷이란?](#1-tcp-패킷이란)
- [2. TCP 헤더 구조](#2-tcp-헤더-구조)
- [3. 제어 문자와 프레임 구조](#3-제어-문자와-프레임-구조)
- [4. CRC 오류 검출](#4-crc-오류-검출)
- [5. 실제 적용 예시](#5-실제-적용-예시)
- [6. 보안 고려사항](#6-보안-고려사항)

---

## 1. TCP 패킷이란?

### 1.1 TCP란?
**TCP(Transmission Control Protocol)**는 인터넷에서 데이터를 안전하게 전송하기 위한 규칙입니다. 

📧 **우리가 편지를 보낼 때를 생각해보세요:**
- 편지를 보내면 우체부가 배달합니다
- 하지만 편지가 도착했는지 확인이 필요합니다
- 편지가 손상되었는지도 확인해야 합니다

TCP는 이런 역할을 인터넷에서 수행합니다.

### 1.2 패킷이란?
**패킷(Packet)**은 큰 데이터를 작은 조각으로 나눈 것입니다.

🍕 **피자를 배달할 때를 생각해보세요:**
- 큰 피자를 그대로 배달하기 어렵습니다
- 작은 조각으로 나누어 배달합니다
- 각 조각에 번호를 붙여서 순서대로 조립할 수 있게 합니다

패킷도 마찬가지로 큰 데이터를 작은 조각으로 나누어 전송합니다.

### 1.3 TCP 패킷의 구성
```
┌─────────────────────────────────────────┐
│              TCP 패킷                    │
├─────────────────────────────────────────┤
│  헤더 (20바이트)  │  데이터 (가변 길이)   │
└─────────────────────────────────────────┘
```

- **헤더**: 패킷에 대한 정보 (주소, 순서, 상태 등)
- **데이터**: 실제 전송할 내용

---

## 2. TCP 헤더 구조

### 2.1 헤더의 기본 구조 (20바이트)
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Data |           |U|A|P|R|S|F|                               |
| Offset| Reserved  |R|C|S|S|Y|I|            Window             |
|       |           |G|K|H|T|N|N|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |         Urgent Pointer        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options (if any)                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Data (if any)                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 2.2 주요 필드 설명

#### 2.2.1 포트 번호 (Port Number)
- **Source Port (출발지 포트)**: 데이터를 보내는 프로그램의 번호
- **Destination Port (목적지 포트)**: 데이터를 받는 프로그램의 번호

🔢 **포트 번호의 의미:**
- 0~1023: 잘 알려진 포트 (HTTP: 80, HTTPS: 443)
- 1024~49151: 등록된 포트
- 49152~65535: 동적 포트

#### 2.2.2 시퀀스 번호 (Sequence Number)
- 데이터의 순서를 나타내는 번호
- 첫 번째 바이트의 위치를 나타냄

📚 **책의 페이지 번호와 같습니다:**
- 1페이지, 2페이지, 3페이지...
- 순서대로 읽어야 내용을 이해할 수 있습니다

#### 2.2.3 확인 응답 번호 (Acknowledgment Number)
- 다음에 받고 싶은 데이터의 시퀀스 번호
- "이것까지 잘 받았으니, 다음 것은 이것부터 보내줘"라는 의미

#### 2.2.4 데이터 오프셋 (Data Offset)
- TCP 헤더의 길이를 나타냄
- 4바이트 단위로 표현 (예: 5 = 20바이트)

#### 2.2.5 제어 플래그 (Control Flags)
- **URG (Urgent)**: 긴급 데이터가 있음
- **ACK (Acknowledgment)**: 확인 응답이 포함됨
- **PSH (Push)**: 즉시 데이터를 상위 계층으로 전달
- **RST (Reset)**: 연결을 강제로 끊음
- **SYN (Synchronize)**: 연결 시작 요청
- **FIN (Finish)**: 연결 종료 요청

#### 2.2.6 윈도우 크기 (Window Size)
- 수신할 수 있는 데이터의 크기
- 흐름 제어에 사용

#### 2.2.7 체크섬 (Checksum)
- 데이터가 손상되었는지 확인하는 값
- 오류 검출에 사용

#### 2.2.8 긴급 포인터 (Urgent Pointer)
- 긴급 데이터의 위치를 나타냄

---

## 3. 제어 문자와 프레임 구조

### 3.1 제어 문자란?
**제어 문자(Control Character)**는 데이터 전송을 제어하는 특별한 문자입니다.

🎭 **연극의 신호와 같습니다:**
- "시작!" 신호
- "끝!" 신호
- "잠깐!" 신호

### 3.2 STX (Start of Text) - 시작 신호

#### 3.2.1 STX란?
- **STX**는 데이터 전송의 시작을 알리는 신호입니다
- ASCII 코드: `0x02` (2진수: `00000010`)

#### 3.2.2 STX의 역할
1. **데이터 시작 표시**: "이제부터 데이터가 시작됩니다"
2. **동기화**: 송신자와 수신자의 타이밍 맞추기
3. **프레임 경계**: 데이터의 시작점 식별

#### 3.2.3 JavaScript 예시
```javascript
// STX 문자 정의
const STX = 0x02; // 2진수: 00000010

// 데이터 전송 시작 함수
function sendData(data) {
    const buffer = new ArrayBuffer(data.length + 1);
    const view = new Uint8Array(buffer);
    
    // STX 추가 (시작 신호)
    view[0] = STX;
    
    // 실제 데이터 추가
    for (let i = 0; i < data.length; i++) {
        view[i + 1] = data.charCodeAt(i);
    }
    
    return buffer;
}

// 사용 예시
const message = "Hello World";
const packet = sendData(message);
console.log("전송 패킷:", new Uint8Array(packet));
```

### 3.3 ETX (End of Text) - 종료 신호

#### 3.3.1 ETX란?
- **ETX**는 데이터 전송의 종료를 알리는 신호입니다
- ASCII 코드: `0x03` (2진수: `00000011`)

#### 3.3.2 ETX의 역할
1. **데이터 종료 표시**: "데이터 전송이 끝났습니다"
2. **처리 완료 신호**: 수신자가 데이터 처리를 시작할 수 있음
3. **프레임 경계**: 데이터의 종료점 식별

#### 3.3.3 JavaScript 예시
```javascript
// ETX 문자 정의
const ETX = 0x03; // 2진수: 00000011

// 데이터 전송 종료 함수
function endData(data) {
    const buffer = new ArrayBuffer(data.length + 1);
    const view = new Uint8Array(buffer);
    
    // 실제 데이터 추가
    for (let i = 0; i < data.length; i++) {
        view[i] = data.charCodeAt(i);
    }
    
    // ETX 추가 (종료 신호)
    view[data.length] = ETX;
    
    return buffer;
}

// 사용 예시
const message = "Hello World";
const packet = endData(message);
console.log("종료 패킷:", new Uint8Array(packet));
```

### 3.4 프레임 구조

#### 3.4.1 기본 프레임 구조
```
┌─────┬──────────┬─────┬──────────┐
│ STX │  데이터   │ ETX │   CRC    │
└─────┴──────────┴─────┴──────────┘
```

#### 3.4.2 JavaScript로 프레임 생성
```javascript
// 프레임 생성 함수
function createFrame(data) {
    const STX = 0x02;
    const ETX = 0x03;
    
    // 데이터를 바이트 배열로 변환
    const dataBytes = new TextEncoder().encode(data);
    
    // 프레임 크기 계산 (STX + 데이터 + ETX + CRC)
    const frameSize = 1 + dataBytes.length + 1 + 2;
    const frame = new ArrayBuffer(frameSize);
    const view = new Uint8Array(frame);
    
    let offset = 0;
    
    // STX 추가
    view[offset++] = STX;
    
    // 데이터 추가
    view.set(dataBytes, offset);
    offset += dataBytes.length;
    
    // ETX 추가
    view[offset++] = ETX;
    
    // CRC 계산 및 추가 (간단한 예시)
    const crc = calculateSimpleCRC(view.slice(0, offset));
    view[offset++] = (crc >> 8) & 0xFF; // 상위 바이트
    view[offset++] = crc & 0xFF;        // 하위 바이트
    
    return frame;
}

// 간단한 CRC 계산 함수
function calculateSimpleCRC(data) {
    let crc = 0;
    for (let i = 0; i < data.length; i++) {
        crc ^= data[i];
        for (let j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

// 사용 예시
const message = "Hello World";
const frame = createFrame(message);
console.log("완성된 프레임:", new Uint8Array(frame));
```

---

## 4. CRC 오류 검출

### 4.1 CRC란?
**CRC(Cyclic Redundancy Check)**는 데이터 전송 중 발생한 오류를 찾아내는 방법입니다.

🔍 **우편물의 봉인과 같습니다:**
- 봉인이 깨져있으면 내용이 바뀌었을 가능성이 있습니다
- 봉인이 온전하면 내용이 그대로일 가능성이 높습니다

### 4.2 CRC의 원리

#### 4.2.1 기본 개념
1. **송신측**: 데이터를 특정 규칙에 따라 계산하여 CRC 값을 만듦
2. **전송**: 데이터와 CRC 값을 함께 전송
3. **수신측**: 받은 데이터로 같은 계산을 하여 CRC 값을 확인
4. **비교**: 계산된 CRC와 받은 CRC가 다르면 오류 발생

#### 4.2.2 수학적 원리
- 다항식 나눗셈을 사용
- 2진수 연산 (XOR 사용)
- 나머지를 CRC 값으로 사용

### 4.3 CRC 종류

#### 4.3.1 CRC-16
- 16비트 CRC 값 생성
- 일반적인 통신에서 사용
- 다항식: x^16 + x^15 + x^2 + 1

#### 4.3.2 CRC-32
- 32비트 CRC 값 생성
- 이더넷, ZIP 파일에서 사용
- 더 정확한 오류 검출

### 4.4 JavaScript로 CRC 구현

#### 4.4.1 CRC-16 구현
```javascript
// CRC-16 계산 함수
function calculateCRC16(data) {
    let crc = 0xFFFF; // 초기값
    
    for (let i = 0; i < data.length; i++) {
        crc ^= (data[i] << 8); // 상위 바이트와 XOR
        
        for (let j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021; // 다항식
            } else {
                crc <<= 1;
            }
        }
    }
    
    return crc & 0xFFFF;
}

// 사용 예시
const message = "Hello World";
const data = new TextEncoder().encode(message);
const crc = calculateCRC16(data);
console.log(`메시지: ${message}`);
console.log(`CRC-16: 0x${crc.toString(16).toUpperCase()}`);
```

#### 4.4.2 CRC-32 구현
```javascript
// CRC-32 계산 함수
function calculateCRC32(data) {
    let crc = 0xFFFFFFFF; // 초기값
    
    for (let i = 0; i < data.length; i++) {
        crc ^= data[i];
        
        for (let j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >>> 1) ^ 0xEDB88320; // 다항식
            } else {
                crc >>>= 1;
            }
        }
    }
    
    return (crc ^ 0xFFFFFFFF) >>> 0; // 최종 XOR 및 부호 없는 정수로 변환
}

// 사용 예시
const message = "Hello World";
const data = new TextEncoder().encode(message);
const crc = calculateCRC32(data);
console.log(`메시지: ${message}`);
console.log(`CRC-32: 0x${crc.toString(16).toUpperCase()}`);
```

### 4.5 CRC 검증

#### 4.5.1 오류 검출 예시
```javascript
// 데이터 전송 시뮬레이션
function simulateDataTransmission(originalData) {
    // 1. 원본 데이터로 CRC 계산
    const originalCRC = calculateCRC16(originalData);
    
    // 2. 데이터 전송 (오류 발생 시뮬레이션)
    const transmittedData = new Uint8Array(originalData);
    transmittedData[0] ^= 1; // 첫 번째 비트 오류 발생
    
    // 3. 수신측에서 CRC 검증
    const receivedCRC = calculateCRC16(transmittedData);
    
    // 4. 오류 검출
    const hasError = receivedCRC !== originalCRC;
    
    return {
        originalData: Array.from(originalData),
        transmittedData: Array.from(transmittedData),
        originalCRC: originalCRC,
        receivedCRC: receivedCRC,
        hasError: hasError
    };
}

// 사용 예시
const message = "Hello World";
const data = new TextEncoder().encode(message);
const result = simulateDataTransmission(data);

console.log("=== 데이터 전송 시뮬레이션 ===");
console.log("원본 데이터:", result.originalData);
console.log("전송된 데이터:", result.transmittedData);
console.log("원본 CRC:", result.originalCRC);
console.log("수신 CRC:", result.receivedCRC);
console.log("오류 발생:", result.hasError);
```

---

## 5. 실제 적용 예시

### 5.1 시리얼 통신에서의 사용

#### 5.1.1 시리얼 통신이란?
**시리얼 통신**은 데이터를 한 번에 하나씩 순차적으로 전송하는 방식입니다.

🔌 **전화선과 같습니다:**
- 한 번에 한 사람만 말할 수 있습니다
- 순서대로 말해야 합니다
- 시작과 끝을 명확히 해야 합니다

#### 5.1.2 시리얼 통신 프레임 구조
```
┌─────┬──────────┬─────┬──────────┐
│ STX │  데이터   │ ETX │ CRC-16   │
└─────┴──────────┴─────┴──────────┘
```

#### 5.1.3 JavaScript 시리얼 통신 시뮬레이션
```javascript
// 시리얼 통신 클래스
class SerialCommunication {
    constructor() {
        this.STX = 0x02;
        this.ETX = 0x03;
    }
    
    // 데이터 전송
    send(data) {
        const frame = this.createFrame(data);
        console.log("전송 프레임:", Array.from(new Uint8Array(frame)));
        return frame;
    }
    
    // 데이터 수신
    receive(frame) {
        const view = new Uint8Array(frame);
        
        // STX 확인
        if (view[0] !== this.STX) {
            throw new Error("STX 오류: 프레임 시작이 올바르지 않습니다");
        }
        
        // ETX 찾기
        let etxIndex = -1;
        for (let i = 1; i < view.length - 3; i++) {
            if (view[i] === this.ETX) {
                etxIndex = i;
                break;
            }
        }
        
        if (etxIndex === -1) {
            throw new Error("ETX 오류: 프레임 종료가 올바르지 않습니다");
        }
        
        // 데이터 추출
        const data = view.slice(1, etxIndex);
        
        // CRC 검증
        const receivedCRC = (view[view.length - 2] << 8) | view[view.length - 1];
        const calculatedCRC = calculateCRC16(view.slice(0, etxIndex + 1));
        
        if (receivedCRC !== calculatedCRC) {
            throw new Error("CRC 오류: 데이터가 손상되었습니다");
        }
        
        return new TextDecoder().decode(data);
    }
    
    // 프레임 생성
    createFrame(data) {
        const dataBytes = new TextEncoder().encode(data);
        const frameSize = 1 + dataBytes.length + 1 + 2; // STX + 데이터 + ETX + CRC
        const frame = new ArrayBuffer(frameSize);
        const view = new Uint8Array(frame);
        
        let offset = 0;
        
        // STX
        view[offset++] = this.STX;
        
        // 데이터
        view.set(dataBytes, offset);
        offset += dataBytes.length;
        
        // ETX
        view[offset++] = this.ETX;
        
        // CRC
        const crc = calculateCRC16(view.slice(0, offset));
        view[offset++] = (crc >> 8) & 0xFF;
        view[offset++] = crc & 0xFF;
        
        return frame;
    }
}

// 사용 예시
const serial = new SerialCommunication();

try {
    // 데이터 전송
    const message = "Hello Serial World!";
    const frame = serial.send(message);
    
    // 데이터 수신
    const receivedMessage = serial.receive(frame);
    console.log("수신된 메시지:", receivedMessage);
    
} catch (error) {
    console.error("통신 오류:", error.message);
}
```

### 5.2 이더넷 프레임에서의 사용

#### 5.2.1 이더넷 프레임 구조
```
┌──────────┬─────┬──────────────┬──────────────┬──────┬──────────┬──────────┐
│ 프리앰블  │ SFD │ 목적지 MAC   │ 출발지 MAC    │ 타입 │  데이터   │ CRC-32   │
└──────────┴─────┴──────────────┴──────────────┴──────┴──────────┴──────────┘
```

#### 5.2.2 각 필드 설명
- **프리앰블**: 7바이트, 프레임 동기화
- **SFD**: 1바이트, 프레임 시작 구분자
- **목적지 MAC**: 6바이트, 받는 장치의 주소
- **출발지 MAC**: 6바이트, 보내는 장치의 주소
- **타입**: 2바이트, 상위 계층 프로토콜 식별
- **데이터**: 46~1500바이트, 실제 전송 데이터
- **CRC-32**: 4바이트, 오류 검출

#### 5.2.3 JavaScript 이더넷 프레임 시뮬레이션
```javascript
// 이더넷 프레임 클래스
class EthernetFrame {
    constructor() {
        this.PREAMBLE = new Uint8Array([0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA]);
        this.SFD = 0xAB;
    }
    
    // 프레임 생성
    createFrame(sourceMAC, destMAC, data, type = 0x0800) {
        // 최소 데이터 크기 (46바이트)
        const minDataSize = 46;
        let paddedData = data;
        
        if (data.length < minDataSize) {
            const padding = new ArrayBuffer(minDataSize - data.length);
            paddedData = new Uint8Array(data.length + padding.byteLength);
            paddedData.set(data);
        }
        
        // 프레임 크기 계산
        const frameSize = 7 + 1 + 6 + 6 + 2 + paddedData.length + 4;
        const frame = new ArrayBuffer(frameSize);
        const view = new Uint8Array(frame);
        
        let offset = 0;
        
        // 프리앰블
        view.set(this.PREAMBLE, offset);
        offset += 7;
        
        // SFD
        view[offset++] = this.SFD;
        
        // 목적지 MAC
        view.set(this.parseMAC(destMAC), offset);
        offset += 6;
        
        // 출발지 MAC
        view.set(this.parseMAC(sourceMAC), offset);
        offset += 6;
        
        // 타입
        view[offset++] = (type >> 8) & 0xFF;
        view[offset++] = type & 0xFF;
        
        // 데이터
        view.set(paddedData, offset);
        offset += paddedData.length;
        
        // CRC-32
        const crc = calculateCRC32(view.slice(0, offset));
        view[offset++] = (crc >> 24) & 0xFF;
        view[offset++] = (crc >> 16) & 0xFF;
        view[offset++] = (crc >> 8) & 0xFF;
        view[offset++] = crc & 0xFF;
        
        return frame;
    }
    
    // MAC 주소 파싱
    parseMAC(macString) {
        return new Uint8Array(macString.split(':').map(byte => parseInt(byte, 16)));
    }
    
    // MAC 주소 포맷팅
    formatMAC(macArray) {
        return Array.from(macArray).map(byte => byte.toString(16).padStart(2, '0')).join(':').toUpperCase();
    }
    
    // 프레임 파싱
    parseFrame(frame) {
        const view = new Uint8Array(frame);
        
        // 프리앰블 확인
        for (let i = 0; i < 7; i++) {
            if (view[i] !== this.PREAMBLE[i]) {
                throw new Error("프리앰블 오류");
            }
        }
        
        // SFD 확인
        if (view[7] !== this.SFD) {
            throw new Error("SFD 오류");
        }
        
        let offset = 8;
        
        // 목적지 MAC
        const destMAC = this.formatMAC(view.slice(offset, offset + 6));
        offset += 6;
        
        // 출발지 MAC
        const sourceMAC = this.formatMAC(view.slice(offset, offset + 6));
        offset += 6;
        
        // 타입
        const type = (view[offset] << 8) | view[offset + 1];
        offset += 2;
        
        // 데이터 (CRC 제외)
        const data = view.slice(offset, view.length - 4);
        
        // CRC 검증
        const receivedCRC = (view[view.length - 4] << 24) | 
                           (view[view.length - 3] << 16) | 
                           (view[view.length - 2] << 8) | 
                           view[view.length - 1];
        
        const calculatedCRC = calculateCRC32(view.slice(0, view.length - 4));
        
        if (receivedCRC !== calculatedCRC) {
            throw new Error("CRC 오류: 프레임이 손상되었습니다");
        }
        
        return {
            destMAC: destMAC,
            sourceMAC: sourceMAC,
            type: type,
            data: data
        };
    }
}

// 사용 예시
const ethernet = new EthernetFrame();

try {
    // 프레임 생성
    const sourceMAC = "00:11:22:33:44:55";
    const destMAC = "AA:BB:CC:DD:EE:FF";
    const data = new TextEncoder().encode("Hello Ethernet!");
    
    const frame = ethernet.createFrame(sourceMAC, destMAC, data);
    console.log("생성된 이더넷 프레임 크기:", frame.byteLength, "바이트");
    
    // 프레임 파싱
    const parsed = ethernet.parseFrame(frame);
    console.log("목적지 MAC:", parsed.destMAC);
    console.log("출발지 MAC:", parsed.sourceMAC);
    console.log("타입:", "0x" + parsed.type.toString(16));
    console.log("데이터:", new TextDecoder().decode(parsed.data));
    
} catch (error) {
    console.error("이더넷 프레임 오류:", error.message);
}
```

---

## 6. 보안 고려사항

### 6.1 CRC의 한계

#### 6.1.1 보안적 한계
- **의도적 변조 검출 불가**: 누군가 고의로 데이터를 바꾸면 CRC만으로는 검출할 수 없음
- **암호화 기능 없음**: 데이터가 평문으로 전송됨
- **인증 기능 없음**: 누가 보냈는지 확인할 수 없음

#### 6.1.2 해결 방안
- **암호화와 함께 사용**: 데이터를 암호화하여 전송
- **해시 함수 사용**: SHA-256 등으로 무결성 검증
- **디지털 서명**: 발신자 인증 및 무결성 보장

### 6.2 보안 강화 방안

#### 6.2.1 데이터 암호화
```javascript
// 간단한 XOR 암호화 예시 (실제로는 AES 등 사용)
function simpleEncrypt(data, key) {
    const encrypted = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
        encrypted[i] = data[i] ^ key[i % key.length];
    }
    return encrypted;
}

function simpleDecrypt(encryptedData, key) {
    return simpleEncrypt(encryptedData, key); // XOR은 대칭적
}

// 사용 예시
const message = "Secret Message";
const data = new TextEncoder().encode(message);
const key = new TextEncoder().encode("MySecretKey");

const encrypted = simpleEncrypt(data, key);
const decrypted = simpleDecrypt(encrypted, key);

console.log("원본:", message);
console.log("암호화:", new TextDecoder().decode(encrypted));
console.log("복호화:", new TextDecoder().decode(decrypted));
```

#### 6.2.2 해시 함수 사용
```javascript
// SHA-256 해시 계산 (브라우저 환경)
async function calculateSHA256(data) {
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

// 사용 예시
const message = "Important Data";
const data = new TextEncoder().encode(message);

calculateSHA256(data).then(hash => {
    console.log("메시지:", message);
    console.log("SHA-256 해시:", hash);
});
```

#### 6.2.3 보안 통신 예시
```javascript
// 보안 통신 클래스
class SecureCommunication {
    constructor() {
        this.STX = 0x02;
        this.ETX = 0x03;
    }
    
    // 보안 프레임 생성
    async createSecureFrame(data, key) {
        // 1. 데이터 암호화
        const encryptedData = simpleEncrypt(data, key);
        
        // 2. 해시 계산
        const hash = await calculateSHA256(data);
        const hashBytes = new TextEncoder().encode(hash);
        
        // 3. 프레임 생성
        const frameSize = 1 + encryptedData.length + 1 + hashBytes.length + 2;
        const frame = new ArrayBuffer(frameSize);
        const view = new Uint8Array(frame);
        
        let offset = 0;
        
        // STX
        view[offset++] = this.STX;
        
        // 암호화된 데이터
        view.set(encryptedData, offset);
        offset += encryptedData.length;
        
        // ETX
        view[offset++] = this.ETX;
        
        // 해시
        view.set(hashBytes, offset);
        offset += hashBytes.length;
        
        // 길이 정보
        view[offset++] = (encryptedData.length >> 8) & 0xFF;
        view[offset++] = encryptedData.length & 0xFF;
        
        return frame;
    }
    
    // 보안 프레임 파싱
    async parseSecureFrame(frame, key) {
        const view = new Uint8Array(frame);
        
        // STX 확인
        if (view[0] !== this.STX) {
            throw new Error("STX 오류");
        }
        
        // 길이 정보 읽기
        const dataLength = (view[view.length - 2] << 8) | view[view.length - 1];
        
        // 암호화된 데이터 추출
        const encryptedData = view.slice(1, 1 + dataLength);
        
        // ETX 확인
        if (view[1 + dataLength] !== this.ETX) {
            throw new Error("ETX 오류");
        }
        
        // 해시 추출
        const hashStart = 1 + dataLength + 1;
        const hashBytes = view.slice(hashStart, view.length - 2);
        const receivedHash = new TextDecoder().decode(hashBytes);
        
        // 데이터 복호화
        const decryptedData = simpleDecrypt(encryptedData, key);
        
        // 해시 검증
        const calculatedHash = await calculateSHA256(decryptedData);
        
        if (receivedHash !== calculatedHash) {
            throw new Error("해시 오류: 데이터가 변조되었습니다");
        }
        
        return decryptedData;
    }
}

// 사용 예시
async function secureCommunicationExample() {
    const secure = new SecureCommunication();
    const message = "Top Secret Message";
    const data = new TextEncoder().encode(message);
    const key = new TextEncoder().encode("SecretKey123");
    
    try {
        // 보안 프레임 생성
        const frame = await secure.createSecureFrame(data, key);
        console.log("보안 프레임 생성 완료");
        
        // 보안 프레임 파싱
        const decryptedData = await secure.parseSecureFrame(frame, key);
        const decryptedMessage = new TextDecoder().decode(decryptedData);
        
        console.log("원본 메시지:", message);
        console.log("복호화된 메시지:", decryptedMessage);
        
    } catch (error) {
        console.error("보안 통신 오류:", error.message);
    }
}

// 실행
secureCommunicationExample();
```

---

## 📝 정리

### 핵심 개념
1. **TCP 패킷**: 데이터를 안전하게 전송하기 위한 구조
2. **제어 문자**: 데이터 전송의 시작과 끝을 나타내는 신호
3. **CRC**: 데이터 오류를 검출하는 방법
4. **보안**: 암호화, 해시, 인증을 통한 데이터 보호

### 실제 활용
- **웹 통신**: HTTP/HTTPS에서 TCP 사용
- **파일 전송**: FTP에서 TCP 사용
- **이메일**: SMTP에서 TCP 사용
- **데이터베이스**: MySQL, PostgreSQL에서 TCP 사용

### 주의사항
- CRC는 우연한 오류만 검출 가능
- 의도적 변조 방지에는 암호화 필요
- 실제 프로덕션에서는 검증된 보안 라이브러리 사용 권장
