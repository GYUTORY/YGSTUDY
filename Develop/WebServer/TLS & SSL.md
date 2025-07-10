# TLS & SSL 보안 프로토콜

## 📋 개요

웹에서 데이터를 안전하게 전송하기 위한 보안 프로토콜에 대해 알아보겠습니다.

---

## 🔐 SSL (Secure Sockets Layer)

### 정의
- **SSL**은 웹사이트와 브라우저 간의 통신을 암호화하는 보안 프로토콜입니다
- 1995년 Netscape에서 처음 개발했습니다
- 개인정보나 금융정보 같은 민감한 데이터를 해커로부터 보호합니다

### 작동 원리
```javascript
// SSL 연결 과정 예시
const sslConnection = {
  client: "브라우저",
  server: "웹사이트",
  process: [
    "1. 클라이언트가 서버에 연결 요청",
    "2. 서버가 SSL 인증서 전송",
    "3. 클라이언트가 인증서 검증",
    "4. 암호화 키 교환",
    "5. 암호화된 통신 시작"
  ]
};
```

---

## 🛡️ TLS (Transport Layer Security)

### 정의
- **TLS**는 SSL의 개선된 버전입니다
- 더 안전하고 현대적인 보안 프로토콜입니다
- 현재 웹에서 사용되는 표준 보안 프로토콜입니다

### SSL과 TLS의 관계
```javascript
// 프로토콜 발전 과정
const protocolEvolution = {
  "1995": "SSL 1.0 (Netscape 개발)",
  "1996": "SSL 2.0",
  "1996": "SSL 3.0",
  "1999": "TLS 1.0 (SSL 3.1)",
  "2006": "TLS 1.1",
  "2008": "TLS 1.2",
  "2018": "TLS 1.3"
};
```

---

## 🔍 SSL vs TLS 주요 차이점

### 1. 메시지 인증 방식

#### SSL의 인증 방식
```javascript
// SSL에서 사용하는 HMAC 방식
const sslAuthentication = {
  method: "HMAC (Hash-based Message Authentication Code)",
  hashFunctions: ["MD5", "SHA-1"],
  process: [
    "1. 메시지와 비밀키로 해시 생성",
    "2. 전송된 메시지의 무결성 검증",
    "3. 변조 여부 확인"
  ]
};
```

#### TLS의 인증 방식
```javascript
// TLS 1.3에서 사용하는 AEAD 방식
const tlsAuthentication = {
  method: "AEAD (Authenticated Encryption with Associated Data)",
  encryptionModes: ["GCM", "CCM", "ChaCha20-Poly1305"],
  advantages: [
    "암호화와 인증을 동시에 수행",
    "더 효율적이고 안전함",
    "최신 해시 함수 사용 (SHA-256)"
  ]
};
```

### 2. 레코드 프로토콜

| 구분 | SSL | TLS |
|------|-----|-----|
| 패킷당 레코드 | 여러 개 가능 | 하나만 가능 |
| 압축 기능 | 없음 | 있음 |
| 패딩 옵션 | 제한적 | 다양한 옵션 |

### 3. 암호화 알고리즘 (Cipher Suite)

```javascript
// TLS에서 지원하는 암호화 알고리즘 예시
const tlsCipherSuites = {
  keyExchange: [
    "ECDHE (Elliptic Curve Diffie-Hellman Ephemeral)",
    "DHE (Diffie-Hellman Ephemeral)",
    "RSA"
  ],
  encryption: [
    "AES-256-GCM",
    "ChaCha20-Poly1305",
    "AES-128-GCM"
  ],
  hash: [
    "SHA-256",
    "SHA-384"
  ]
};
```

---

## 🔄 SSL에서 TLS로의 전환

### 전환이 필요한 이유

#### 1. 보안 취약점
```javascript
// SSL의 알려진 보안 취약점
const sslVulnerabilities = {
  "POODLE": "SSL 3.0 취약점 (2014)",
  "BEAST": "SSL/TLS 1.0 취약점 (2011)",
  "Heartbleed": "OpenSSL 라이브러리 취약점 (2014)",
  "FREAK": "SSL/TLS 취약점 (2015)"
};
```

#### 2. 호환성 문제
```javascript
// 프로토콜 호환성 예시
const protocolCompatibility = {
  modernBrowser: {
    supports: ["TLS 1.2", "TLS 1.3"],
    deprecated: ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"]
  },
  oldServer: {
    supports: ["SSL 3.0", "TLS 1.0"],
    result: "연결 실패 또는 보안 경고"
  }
};
```

---

## 📜 SSL/TLS 인증서

### 인증서의 역할
```javascript
// SSL/TLS 인증서 구조
const sslCertificate = {
  purpose: "웹사이트 신원 확인 및 암호화 키 제공",
  components: {
    publicKey: "암호화에 사용되는 공개키",
    privateKey: "복호화에 사용되는 개인키 (서버에만 보관)",
    domainName: "인증서가 적용되는 도메인",
    issuer: "인증서 발급 기관",
    validityPeriod: "유효기간"
  }
};
```

### 인증서 작동 과정
```javascript
// 인증서를 통한 암호화 과정
const encryptionProcess = {
  step1: "클라이언트가 서버에 연결 요청",
  step2: "서버가 SSL/TLS 인증서 전송",
  step3: "클라이언트가 인증서 검증",
  step4: "공개키로 세션키 암호화하여 전송",
  step5: "서버가 개인키로 세션키 복호화",
  step6: "세션키로 데이터 암호화 통신"
};
```

---

## 🌐 실제 사용 예시

### HTTPS 연결 확인
```javascript
// 브라우저에서 HTTPS 연결 확인
const checkHttpsConnection = () => {
  const url = window.location.href;
  const isSecure = url.startsWith('https://');
  
  if (isSecure) {
    console.log('🔒 안전한 HTTPS 연결');
    console.log('프로토콜:', navigator.userAgent);
  } else {
    console.log('⚠️ HTTP 연결 - 보안에 취약');
  }
};

// Node.js에서 HTTPS 서버 생성
const https = require('https');
const fs = require('fs');

const options = {
  key: fs.readFileSync('private-key.pem'),
  cert: fs.readFileSync('certificate.pem')
};

const server = https.createServer(options, (req, res) => {
  res.writeHead(200);
  res.end('안전한 HTTPS 연결입니다!');
});

server.listen(443);
```

---

## 📚 주요 용어 정리

| 용어 | 설명 |
|------|------|
| **프로토콜** | 컴퓨터 간 통신 규칙 |
| **암호화** | 데이터를 읽을 수 없게 변환하는 과정 |
| **복호화** | 암호화된 데이터를 원래 형태로 되돌리는 과정 |
| **인증서** | 웹사이트 신원을 증명하는 디지털 문서 |
| **공개키** | 암호화에 사용되는 공개된 키 |
| **개인키** | 복호화에 사용되는 비공개 키 |
| **해시 함수** | 데이터를 고정 길이의 문자열로 변환하는 함수 |
| **무결성** | 데이터가 전송 중에 변조되지 않았음을 보장 |

---

## 🔗 참고 자료

- [DigiCert SSL/TLS 가이드](https://www.digicert.com/kr/what-is-ssl-tls-and-https)
- [SSL/TLS 프로토콜 비교](https://kanoos-stu.tistory.com/46)