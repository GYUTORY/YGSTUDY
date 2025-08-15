---
title: TCP 패킷 구조 상세 설명
tags: [network, 7-layer, transport-layer, tcp, packetstructure, packet-analysis]
updated: 2025-08-10
---

# TCP 패킷 구조 상세 설명

## 배경

TCP 패킷은 인터넷에서 데이터를 안전하게 전송하기 위한 기본 단위입니다. TCP(Transmission Control Protocol)는 신뢰성 있는 데이터 전송을 보장하는 전송 계층 프로토콜로, 웹 브라우징, 이메일, 파일 전송 등에서 널리 사용됩니다.

### TCP 패킷의 중요성
- **데이터 무결성**: 전송 중 데이터 손실 방지
- **순서 보장**: 패킷이 올바른 순서로 도착하도록 보장
- **오류 검출**: 전송 중 발생한 오류를 감지하고 수정
- **흐름 제어**: 송신자와 수신자 간의 데이터 전송 속도 조절

### 실제 활용 분야
- **웹 통신**: HTTP/HTTPS에서 TCP 사용
- **파일 전송**: FTP에서 TCP 사용
- **이메일**: SMTP에서 TCP 사용
- **데이터베이스**: MySQL, PostgreSQL에서 TCP 사용

## 핵심

### 1. TCP 패킷 구조

#### 기본 구성 요소
TCP 패킷은 헤더와 데이터로 구성됩니다. 헤더는 패킷에 대한 제어 정보를 담고, 데이터는 실제 전송할 내용을 포함합니다.

```javascript
// TCP 패킷 구조 시뮬레이션
class TCPPacket {
    constructor(sourcePort, destPort, sequenceNumber, data) {
        this.header = {
            sourcePort: sourcePort,           // 16비트
            destPort: destPort,               // 16비트
            sequenceNumber: sequenceNumber,   // 32비트
            acknowledgmentNumber: 0,          // 32비트
            dataOffset: 5,                    // 4비트 (헤더 길이)
            reserved: 0,                      // 6비트
            flags: {
                URG: 0,                       // 긴급 포인터
                ACK: 0,                       // 확인 응답
                PSH: 0,                       // 푸시
                RST: 0,                       // 재설정
                SYN: 0,                       // 동기화
                FIN: 0                        // 종료
            },
            windowSize: 65535,                // 16비트
            checksum: 0,                      // 16비트
            urgentPointer: 0                  // 16비트
        };
        this.data = data || '';
        this.options = [];
    }
    
    // 패킷 크기 계산
    getPacketSize() {
        const headerSize = this.header.dataOffset * 4; // 32비트 워드 단위
        return headerSize + this.data.length;
    }
    
    // 체크섬 계산 (간단한 예시)
    calculateChecksum() {
        let sum = 0;
        const headerStr = JSON.stringify(this.header);
        
        for (let i = 0; i < headerStr.length; i++) {
            sum += headerStr.charCodeAt(i);
        }
        
        for (let i = 0; i < this.data.length; i++) {
            sum += this.data.charCodeAt(i);
        }
        
        this.header.checksum = sum & 0xFFFF; // 16비트로 제한
        return this.header.checksum;
    }
    
    // 패킷 정보 출력
    printPacketInfo() {
        console.log('=== TCP 패킷 정보 ===');
        console.log(`소스 포트: ${this.header.sourcePort}`);
        console.log(`목적지 포트: ${this.header.destPort}`);
        console.log(`시퀀스 번호: ${this.header.sequenceNumber}`);
        console.log(`확인 응답 번호: ${this.header.acknowledgmentNumber}`);
        console.log(`플래그: ${JSON.stringify(this.header.flags)}`);
        console.log(`윈도우 크기: ${this.header.windowSize}`);
        console.log(`체크섬: ${this.header.checksum}`);
        console.log(`데이터 길이: ${this.data.length} 바이트`);
        console.log(`패킷 크기: ${this.getPacketSize()} 바이트`);
    }
}

// 사용 예시
const packet = new TCPPacket(12345, 80, 1000, "Hello, World!");
packet.calculateChecksum();
packet.printPacketInfo();
```

### 2. TCP 헤더 상세 분석

#### 헤더 필드 설명
```javascript
// TCP 헤더 필드 상세 분석
class TCPHeaderAnalyzer {
    static analyzeHeader(header) {
        console.log('=== TCP 헤더 분석 ===');
        
        // 포트 번호 분석
        console.log(`소스 포트 (${header.sourcePort}): ${this.getPortService(header.sourcePort)}`);
        console.log(`목적지 포트 (${header.destPort}): ${this.getPortService(header.destPort)}`);
        
        // 시퀀스 번호 분석
        console.log(`시퀀스 번호: ${header.sequenceNumber} (${this.formatNumber(header.sequenceNumber)})`);
        console.log(`확인 응답 번호: ${header.acknowledgmentNumber} (${this.formatNumber(header.acknowledgmentNumber)})`);
        
        // 플래그 분석
        console.log('플래그 분석:');
        Object.entries(header.flags).forEach(([flag, value]) => {
            if (value) {
                console.log(`  ${flag}: ${this.getFlagDescription(flag)}`);
            }
        });
        
        // 윈도우 크기 분석
        console.log(`윈도우 크기: ${header.windowSize} 바이트 (${this.formatBytes(header.windowSize)})`);
        
        // 데이터 오프셋 분석
        console.log(`헤더 길이: ${header.dataOffset * 4} 바이트`);
    }
    
    static getPortService(port) {
        const commonPorts = {
            20: 'FTP-DATA',
            21: 'FTP',
            22: 'SSH',
            23: 'TELNET',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            143: 'IMAP',
            443: 'HTTPS',
            3306: 'MySQL',
            5432: 'PostgreSQL'
        };
        return commonPorts[port] || 'Unknown';
    }
    
    static getFlagDescription(flag) {
        const descriptions = {
            URG: '긴급 데이터 포함',
            ACK: '확인 응답',
            PSH: '즉시 전송 요청',
            RST: '연결 재설정',
            SYN: '연결 동기화',
            FIN: '연결 종료'
        };
        return descriptions[flag] || 'Unknown';
    }
    
    static formatNumber(num) {
        return num.toLocaleString();
    }
    
    static formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
}

// 헤더 분석 예시
const sampleHeader = {
    sourcePort: 12345,
    destPort: 80,
    sequenceNumber: 1000,
    acknowledgmentNumber: 0,
    dataOffset: 5,
    reserved: 0,
    flags: {
        URG: 0,
        ACK: 0,
        PSH: 1,
        RST: 0,
        SYN: 0,
        FIN: 0
    },
    windowSize: 65535,
    checksum: 12345,
    urgentPointer: 0
};

TCPHeaderAnalyzer.analyzeHeader(sampleHeader);
```

### 3. 제어 문자와 프레임 구조

#### 제어 문자 처리
```javascript
// TCP 제어 문자 처리 클래스
class TCPControlCharacter {
    static CONTROL_CHARS = {
        SOH: 0x01,  // Start of Header
        STX: 0x02,  // Start of Text
        ETX: 0x03,  // End of Text
        EOT: 0x04,  // End of Transmission
        ENQ: 0x05,  // Enquiry
        ACK: 0x06,  // Acknowledgment
        BEL: 0x07,  // Bell
        BS: 0x08,   // Backspace
        HT: 0x09,   // Horizontal Tab
        LF: 0x0A,   // Line Feed
        VT: 0x0B,   // Vertical Tab
        FF: 0x0C,   // Form Feed
        CR: 0x0D,   // Carriage Return
        SO: 0x0E,   // Shift Out
        SI: 0x0F,   // Shift In
        DLE: 0x10,  // Data Link Escape
        DC1: 0x11,  // Device Control 1
        DC2: 0x12,  // Device Control 2
        DC3: 0x13,  // Device Control 3
        DC4: 0x14,  // Device Control 4
        NAK: 0x15,  // Negative Acknowledgment
        SYN: 0x16,  // Synchronous Idle
        ETB: 0x17,  // End of Transmission Block
        CAN: 0x18,  // Cancel
        EM: 0x19,   // End of Medium
        SUB: 0x1A,  // Substitute
        ESC: 0x1B,  // Escape
        FS: 0x1C,   // File Separator
        GS: 0x1D,   // Group Separator
        RS: 0x1E,   // Record Separator
        US: 0x1F    // Unit Separator
    };
    
    // 제어 문자 검출
    static detectControlChars(data) {
        const detected = [];
        
        for (let i = 0; i < data.length; i++) {
            const charCode = data.charCodeAt(i);
            
            for (const [name, code] of Object.entries(this.CONTROL_CHARS)) {
                if (charCode === code) {
                    detected.push({
                        position: i,
                        name: name,
                        code: code,
                        description: this.getControlCharDescription(name)
                    });
                }
            }
        }
        
        return detected;
    }
    
    // 제어 문자 설명
    static getControlCharDescription(name) {
        const descriptions = {
            SOH: '헤더 시작',
            STX: '텍스트 시작',
            ETX: '텍스트 종료',
            EOT: '전송 종료',
            ENQ: '질문',
            ACK: '확인 응답',
            BEL: '벨 소리',
            BS: '백스페이스',
            HT: '수평 탭',
            LF: '줄 바꿈',
            VT: '수직 탭',
            FF: '폼 피드',
            CR: '캐리지 리턴',
            SO: '시프트 아웃',
            SI: '시프트 인',
            DLE: '데이터 링크 이스케이프',
            DC1: '장치 제어 1',
            DC2: '장치 제어 2',
            DC3: '장치 제어 3',
            DC4: '장치 제어 4',
            NAK: '부정 확인 응답',
            SYN: '동기 유휴',
            ETB: '전송 블록 종료',
            CAN: '취소',
            EM: '매체 종료',
            SUB: '대체',
            ESC: '이스케이프',
            FS: '파일 구분자',
            GS: '그룹 구분자',
            RS: '레코드 구분자',
            US: '단위 구분자'
        };
        return descriptions[name] || '알 수 없음';
    }
    
    // 제어 문자 제거
    static removeControlChars(data) {
        let cleaned = '';
        
        for (let i = 0; i < data.length; i++) {
            const charCode = data.charCodeAt(i);
            let isControlChar = false;
            
            for (const code of Object.values(this.CONTROL_CHARS)) {
                if (charCode === code) {
                    isControlChar = true;
                    break;
                }
            }
            
            if (!isControlChar) {
                cleaned += data[i];
            }
        }
        
        return cleaned;
    }
}

// 제어 문자 처리 예시
const testData = "Hello\x01World\x02\x03Test\x04";
console.log('원본 데이터:', testData);

const detected = TCPControlCharacter.detectControlChars(testData);
console.log('검출된 제어 문자:', detected);

const cleaned = TCPControlCharacter.removeControlChars(testData);
console.log('제어 문자 제거 후:', cleaned);
```

### 4. CRC 오류 검출

#### CRC 계산 및 검증
```javascript
// CRC 오류 검출 클래스
class CRCChecker {
    constructor(polynomial = 0x1021) { // CRC-16-CCITT 다항식
        this.polynomial = polynomial;
        this.table = this.generateCRCTable();
    }
    
    // CRC 테이블 생성
    generateCRCTable() {
        const table = new Array(256);
        
        for (let i = 0; i < 256; i++) {
            let crc = i << 8;
            
            for (let j = 0; j < 8; j++) {
                if (crc & 0x8000) {
                    crc = (crc << 1) ^ this.polynomial;
                } else {
                    crc = crc << 1;
                }
            }
            
            table[i] = crc & 0xFFFF;
        }
        
        return table;
    }
    
    // CRC 계산
    calculateCRC(data) {
        let crc = 0xFFFF;
        
        for (let i = 0; i < data.length; i++) {
            const byte = data.charCodeAt(i);
            crc = (crc << 8) ^ this.table[(crc >> 8) ^ byte];
            crc = crc & 0xFFFF;
        }
        
        return crc;
    }
    
    // CRC 검증
    verifyCRC(data, expectedCRC) {
        const calculatedCRC = this.calculateCRC(data);
        return calculatedCRC === expectedCRC;
    }
    
    // 오류 시뮬레이션
    simulateError(data, position) {
        if (position >= data.length) return data;
        
        const bytes = Buffer.from(data, 'utf8');
        bytes[position] = bytes[position] ^ 0xFF; // 비트 반전으로 오류 생성
        
        return bytes.toString('utf8');
    }
}

// CRC 검증 예시
const crcChecker = new CRCChecker();
const originalData = "Hello, World!";
const crc = crcChecker.calculateCRC(originalData);

console.log('원본 데이터:', originalData);
console.log('계산된 CRC:', crc.toString(16).toUpperCase());

// 정상 데이터 검증
const isValid = crcChecker.verifyCRC(originalData, crc);
console.log('정상 데이터 검증:', isValid);

// 오류가 있는 데이터 검증
const corruptedData = crcChecker.simulateError(originalData, 5);
const isCorruptedValid = crcChecker.verifyCRC(corruptedData, crc);
console.log('오류 데이터 검증:', isCorruptedValid);
```

## 예시

### 실제 TCP 패킷 분석

#### 패킷 캡처 시뮬레이션
```javascript
// TCP 패킷 캡처 시뮬레이터
class TCPPacketCapture {
    constructor() {
        this.capturedPackets = [];
        this.packetCounter = 0;
    }
    
    // 패킷 캡처
    capturePacket(sourceIP, destIP, sourcePort, destPort, data, flags = {}) {
        const packet = {
            id: ++this.packetCounter,
            timestamp: new Date(),
            sourceIP: sourceIP,
            destIP: destIP,
            sourcePort: sourcePort,
            destPort: destPort,
            sequenceNumber: Math.floor(Math.random() * 1000000),
            acknowledgmentNumber: 0,
            flags: flags,
            data: data,
            size: data.length,
            checksum: 0
        };
        
        // 체크섬 계산
        packet.checksum = this.calculateSimpleChecksum(packet);
        
        this.capturedPackets.push(packet);
        return packet;
    }
    
    // 간단한 체크섬 계산
    calculateSimpleChecksum(packet) {
        let sum = 0;
        const data = JSON.stringify(packet);
        
        for (let i = 0; i < data.length; i++) {
            sum += data.charCodeAt(i);
        }
        
        return sum & 0xFFFF;
    }
    
    // 패킷 분석
    analyzePacket(packetId) {
        const packet = this.capturedPackets.find(p => p.id === packetId);
        
        if (!packet) {
            console.log('패킷을 찾을 수 없습니다.');
            return;
        }
        
        console.log('=== 패킷 분석 결과 ===');
        console.log(`패킷 ID: ${packet.id}`);
        console.log(`캡처 시간: ${packet.timestamp}`);
        console.log(`소스: ${packet.sourceIP}:${packet.sourcePort}`);
        console.log(`목적지: ${packet.destIP}:${packet.destPort}`);
        console.log(`시퀀스 번호: ${packet.sequenceNumber}`);
        console.log(`확인 응답 번호: ${packet.acknowledgmentNumber}`);
        console.log(`플래그: ${JSON.stringify(packet.flags)}`);
        console.log(`데이터 크기: ${packet.size} 바이트`);
        console.log(`체크섬: ${packet.checksum.toString(16).toUpperCase()}`);
        console.log(`데이터: ${packet.data}`);
        
        // 프로토콜 분석
        this.analyzeProtocol(packet);
    }
    
    // 프로토콜 분석
    analyzeProtocol(packet) {
        console.log('\n=== 프로토콜 분석 ===');
        
        // HTTP 분석
        if (packet.destPort === 80 || packet.destPort === 443) {
            if (packet.data.startsWith('GET') || packet.data.startsWith('POST')) {
                console.log('프로토콜: HTTP');
                console.log('요청 타입:', packet.data.split(' ')[0]);
                console.log('요청 경로:', packet.data.split(' ')[1]);
            }
        }
        
        // FTP 분석
        if (packet.destPort === 21) {
            console.log('프로토콜: FTP');
        }
        
        // SSH 분석
        if (packet.destPort === 22) {
            console.log('프로토콜: SSH');
        }
        
        // SMTP 분석
        if (packet.destPort === 25) {
            console.log('프로토콜: SMTP');
        }
    }
    
    // 모든 패킷 목록 출력
    listPackets() {
        console.log('=== 캡처된 패킷 목록 ===');
        this.capturedPackets.forEach(packet => {
            console.log(`[${packet.id}] ${packet.sourceIP}:${packet.sourcePort} -> ${packet.destIP}:${packet.destPort} (${packet.size} bytes)`);
        });
    }
}

// 패킷 캡처 시뮬레이션
const capture = new TCPPacketCapture();

// HTTP 요청 패킷 캡처
capture.capturePacket(
    '192.168.1.100',
    '93.184.216.34',
    12345,
    80,
    'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n',
    { PSH: 1, ACK: 1 }
);

// HTTP 응답 패킷 캡처
capture.capturePacket(
    '93.184.216.34',
    '192.168.1.100',
    80,
    12345,
    'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html>...</html>',
    { PSH: 1, ACK: 1 }
);

// 패킷 목록 출력
capture.listPackets();

// 첫 번째 패킷 분석
capture.analyzePacket(1);
```

## 운영 팁

### 성능 최적화

#### 패킷 크기 최적화
```javascript
// TCP 패킷 크기 최적화 클래스
class TCPPacketOptimizer {
    constructor() {
        this.maxSegmentSize = 1460; // 일반적인 MSS
        this.windowSize = 65535;    // 기본 윈도우 크기
    }
    
    // 데이터를 최적 크기로 분할
    splitData(data) {
        const segments = [];
        
        for (let i = 0; i < data.length; i += this.maxSegmentSize) {
            segments.push(data.slice(i, i + this.maxSegmentSize));
        }
        
        return segments;
    }
    
    // 윈도우 크기 조정
    adjustWindowSize(currentWindow, networkCondition) {
        switch (networkCondition) {
            case 'excellent':
                return Math.min(currentWindow * 2, 65535);
            case 'good':
                return currentWindow;
            case 'poor':
                return Math.max(currentWindow / 2, 1024);
            case 'congested':
                return 1024;
            default:
                return currentWindow;
        }
    }
    
    // 패킷 전송 속도 계산
    calculateTransmissionRate(packetSize, rtt) {
        // RTT (Round Trip Time) 기반 전송 속도 계산
        const packetsPerSecond = 1000 / rtt;
        const bytesPerSecond = packetsPerSecond * packetSize;
        
        return {
            packetsPerSecond: packetsPerSecond,
            bytesPerSecond: bytesPerSecond,
            bitsPerSecond: bytesPerSecond * 8
        };
    }
    
    // 네트워크 상태 진단
    diagnoseNetwork(packets) {
        const stats = {
            totalPackets: packets.length,
            totalBytes: 0,
            averageSize: 0,
            retransmissions: 0,
            errors: 0
        };
        
        packets.forEach(packet => {
            stats.totalBytes += packet.size;
            
            if (packet.flags.RST) {
                stats.errors++;
            }
            
            // 재전송 감지 (간단한 예시)
            if (packet.retransmitted) {
                stats.retransmissions++;
            }
        });
        
        stats.averageSize = stats.totalBytes / stats.totalPackets;
        
        return stats;
    }
}

// 최적화 예시
const optimizer = new TCPPacketOptimizer();
const largeData = "A".repeat(10000); // 10KB 데이터

const segments = optimizer.splitData(largeData);
console.log(`데이터를 ${segments.length}개 세그먼트로 분할`);

const transmissionRate = optimizer.calculateTransmissionRate(1460, 50); // 50ms RTT
console.log('전송 속도:', transmissionRate);
```

### 보안 고려사항

#### 패킷 보안 검증
```javascript
// TCP 패킷 보안 검증 클래스
class TCPPacketSecurity {
    constructor() {
        this.suspiciousPatterns = [
            /script/i,
            /javascript/i,
            /<.*>/,
            /union.*select/i,
            /drop.*table/i
        ];
        
        this.blockedIPs = new Set();
        this.rateLimits = new Map();
    }
    
    // 패킷 보안 검사
    securityCheck(packet) {
        const results = {
            isSafe: true,
            threats: [],
            riskLevel: 'low'
        };
        
        // 1. IP 차단 확인
        if (this.blockedIPs.has(packet.sourceIP)) {
            results.isSafe = false;
            results.threats.push('Blocked IP address');
            results.riskLevel = 'high';
        }
        
        // 2. 의심스러운 패턴 검사
        for (const pattern of this.suspiciousPatterns) {
            if (pattern.test(packet.data)) {
                results.isSafe = false;
                results.threats.push(`Suspicious pattern: ${pattern.source}`);
                results.riskLevel = 'medium';
            }
        }
        
        // 3. 속도 제한 확인
        if (this.isRateLimited(packet.sourceIP)) {
            results.isSafe = false;
            results.threats.push('Rate limit exceeded');
            results.riskLevel = 'medium';
        }
        
        // 4. 체크섬 검증
        if (!this.verifyChecksum(packet)) {
            results.isSafe = false;
            results.threats.push('Checksum verification failed');
            results.riskLevel = 'high';
        }
        
        return results;
    }
    
    // 속도 제한 확인
    isRateLimited(sourceIP) {
        const now = Date.now();
        const window = 60000; // 1분 윈도우
        
        if (!this.rateLimits.has(sourceIP)) {
            this.rateLimits.set(sourceIP, []);
        }
        
        const requests = this.rateLimits.get(sourceIP);
        
        // 윈도우 밖의 요청 제거
        const validRequests = requests.filter(time => now - time < window);
        this.rateLimits.set(sourceIP, validRequests);
        
        // 새 요청 추가
        validRequests.push(now);
        
        // 분당 100개 요청 제한
        return validRequests.length > 100;
    }
    
    // 체크섬 검증
    verifyChecksum(packet) {
        const calculatedChecksum = this.calculateChecksum(packet);
        return calculatedChecksum === packet.checksum;
    }
    
    // 체크섬 계산
    calculateChecksum(packet) {
        let sum = 0;
        const data = JSON.stringify({
            sourceIP: packet.sourceIP,
            destIP: packet.destIP,
            sourcePort: packet.sourcePort,
            destPort: packet.destPort,
            sequenceNumber: packet.sequenceNumber,
            data: packet.data
        });
        
        for (let i = 0; i < data.length; i++) {
            sum += data.charCodeAt(i);
        }
        
        return sum & 0xFFFF;
    }
    
    // IP 차단
    blockIP(ip) {
        this.blockedIPs.add(ip);
        console.log(`IP ${ip}가 차단되었습니다.`);
    }
    
    // IP 차단 해제
    unblockIP(ip) {
        this.blockedIPs.delete(ip);
        console.log(`IP ${ip}의 차단이 해제되었습니다.`);
    }
}

// 보안 검사 예시
const security = new TCPPacketSecurity();

// 정상 패킷
const normalPacket = {
    sourceIP: '192.168.1.100',
    destIP: '93.184.216.34',
    sourcePort: 12345,
    destPort: 80,
    sequenceNumber: 1000,
    data: 'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n',
    checksum: 12345
};

const normalResult = security.securityCheck(normalPacket);
console.log('정상 패킷 검사 결과:', normalResult);

// 의심스러운 패킷
const suspiciousPacket = {
    sourceIP: '192.168.1.100',
    destIP: '93.184.216.34',
    sourcePort: 12345,
    destPort: 80,
    sequenceNumber: 1001,
    data: 'SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords',
    checksum: 12346
};

const suspiciousResult = security.securityCheck(suspiciousPacket);
console.log('의심스러운 패킷 검사 결과:', suspiciousResult);
```

## 참고

### 네트워크 모니터링

#### 실시간 패킷 모니터링
```javascript
// 실시간 TCP 패킷 모니터링 클래스
class TCPPacketMonitor {
    constructor() {
        this.stats = {
            totalPackets: 0,
            totalBytes: 0,
            connections: new Map(),
            protocols: new Map(),
            errors: 0,
            startTime: Date.now()
        };
        
        this.alerts = [];
    }
    
    // 패킷 모니터링
    monitorPacket(packet) {
        this.stats.totalPackets++;
        this.stats.totalBytes += packet.size;
        
        // 연결 추적
        this.trackConnection(packet);
        
        // 프로토콜 통계
        this.updateProtocolStats(packet);
        
        // 이상 징후 감지
        this.detectAnomalies(packet);
        
        // 실시간 통계 출력
        this.printStats();
    }
    
    // 연결 추적
    trackConnection(packet) {
        const connectionKey = `${packet.sourceIP}:${packet.sourcePort}-${packet.destIP}:${packet.destPort}`;
        
        if (!this.stats.connections.has(connectionKey)) {
            this.stats.connections.set(connectionKey, {
                startTime: Date.now(),
                packets: 0,
                bytes: 0,
                lastActivity: Date.now()
            });
        }
        
        const connection = this.stats.connections.get(connectionKey);
        connection.packets++;
        connection.bytes += packet.size;
        connection.lastActivity = Date.now();
    }
    
    // 프로토콜 통계 업데이트
    updateProtocolStats(packet) {
        let protocol = 'Unknown';
        
        if (packet.destPort === 80 || packet.destPort === 443) protocol = 'HTTP/HTTPS';
        else if (packet.destPort === 21) protocol = 'FTP';
        else if (packet.destPort === 22) protocol = 'SSH';
        else if (packet.destPort === 25) protocol = 'SMTP';
        else if (packet.destPort === 53) protocol = 'DNS';
        else if (packet.destPort === 3306) protocol = 'MySQL';
        else if (packet.destPort === 5432) protocol = 'PostgreSQL';
        
        if (!this.stats.protocols.has(protocol)) {
            this.stats.protocols.set(protocol, { packets: 0, bytes: 0 });
        }
        
        const protocolStats = this.stats.protocols.get(protocol);
        protocolStats.packets++;
        protocolStats.bytes += packet.size;
    }
    
    // 이상 징후 감지
    detectAnomalies(packet) {
        // 1. 비정상적으로 큰 패킷
        if (packet.size > 1500) {
            this.addAlert('Large packet detected', packet);
        }
        
        // 2. 비정상적인 포트
        if (packet.destPort < 1024 && packet.destPort !== 80 && packet.destPort !== 443) {
            this.addAlert('Unusual destination port', packet);
        }
        
        // 3. RST 플래그가 있는 패킷
        if (packet.flags.RST) {
            this.addAlert('Connection reset detected', packet);
        }
        
        // 4. 높은 전송 속도
        const connectionKey = `${packet.sourceIP}:${packet.sourcePort}-${packet.destIP}:${packet.destPort}`;
        const connection = this.stats.connections.get(connectionKey);
        
        if (connection && connection.packets > 1000) {
            this.addAlert('High packet rate detected', packet);
        }
    }
    
    // 알림 추가
    addAlert(message, packet) {
        const alert = {
            timestamp: Date.now(),
            message: message,
            packet: {
                sourceIP: packet.sourceIP,
                destIP: packet.destIP,
                sourcePort: packet.sourcePort,
                destPort: packet.destPort,
                size: packet.size
            }
        };
        
        this.alerts.push(alert);
        console.log(`🚨 ALERT: ${message}`, alert.packet);
    }
    
    // 통계 출력
    printStats() {
        const uptime = Date.now() - this.stats.startTime;
        const packetsPerSecond = this.stats.totalPackets / (uptime / 1000);
        const bytesPerSecond = this.stats.totalBytes / (uptime / 1000);
        
        console.log('\n=== 네트워크 통계 ===');
        console.log(`총 패킷: ${this.stats.totalPackets.toLocaleString()}`);
        console.log(`총 바이트: ${this.formatBytes(this.stats.totalBytes)}`);
        console.log(`패킷/초: ${packetsPerSecond.toFixed(2)}`);
        console.log(`바이트/초: ${this.formatBytes(bytesPerSecond)}`);
        console.log(`활성 연결: ${this.stats.connections.size}`);
        console.log(`오류: ${this.stats.errors}`);
        console.log(`알림: ${this.alerts.length}`);
        
        // 프로토콜별 통계
        console.log('\n=== 프로토콜별 통계 ===');
        for (const [protocol, stats] of this.stats.protocols) {
            console.log(`${protocol}: ${stats.packets} packets, ${this.formatBytes(stats.bytes)}`);
        }
    }
    
    // 바이트 포맷팅
    formatBytes(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    }
}

// 모니터링 예시
const monitor = new TCPPacketMonitor();

// 여러 패킷 모니터링
for (let i = 0; i < 10; i++) {
    const packet = {
        sourceIP: '192.168.1.100',
        destIP: '93.184.216.34',
        sourcePort: 12345 + i,
        destPort: 80,
        sequenceNumber: 1000 + i,
        data: 'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n',
        size: 100 + i * 10,
        flags: { PSH: 1, ACK: 1 }
    };
    
    monitor.monitorPacket(packet);
}
```

### 결론
TCP 패킷 구조는 인터넷 통신의 핵심 요소입니다.
헤더와 데이터로 구성된 패킷은 신뢰성 있는 데이터 전송을 보장합니다.
제어 문자와 CRC 검증을 통해 데이터 무결성을 유지합니다.
실제 네트워크 환경에서는 보안과 성능 최적화가 중요합니다.
패킷 분석과 모니터링을 통해 네트워크 상태를 파악할 수 있습니다.

