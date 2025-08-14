---
title: Base64와 UTF-8 인코딩
tags: [datarepresentation, encoding, base64, utf8, data-encoding]
updated: 2025-08-14
---

# Base64와 UTF-8 인코딩

## 배경

인코딩(Encoding)은 정보를 다른 형태나 형식으로 변환하는 과정입니다. 컴퓨터가 이해할 수 있는 언어로 바꾸는 작업으로, 데이터의 안전한 전송과 저장을 위해 사용됩니다.

### 인코딩이 필요한 이유
- **데이터 호환성**: 서로 다른 시스템 간에 데이터를 주고받을 때
- **데이터 보안**: 민감한 정보를 안전하게 전송할 때  
- **데이터 압축**: 저장 공간을 절약할 때
- **데이터 표준화**: 일관된 형식으로 유지할 때

### 실생활 예시
우리가 일상에서 사용하는 인코딩의 예:
- **모스 부호**: SOS → ... --- ... (점과 선으로 변환)
- **바코드**: 숫자를 검은색과 흰색 막대로 변환
- **QR코드**: 텍스트를 정사각형 패턴으로 변환

### UTF-8과 Base64의 관계
- **UTF-8**: 유니코드 문자를 바이트로 인코딩하는 방식
- **Base64**: 바이너리 데이터를 텍스트로 인코딩하는 방식
- UTF-8로 인코딩된 데이터를 Base64로 다시 인코딩하여 전송

## 핵심

### UTF-8 인코딩

#### UTF-8의 특징
- **가변 길이 인코딩**: 문자에 따라 1~4바이트 사용
- **하위 호환성**: ASCII 문자는 1바이트로 표현
- **범용성**: 전 세계 모든 언어 지원

#### UTF-8 인코딩 규칙
```javascript
// UTF-8 인코딩 예시
function utf8Encode(str) {
    const encoder = new TextEncoder();
    return encoder.encode(str);
}

function utf8Decode(bytes) {
    const decoder = new TextDecoder('utf-8');
    return decoder.decode(bytes);
}

// 사용 예시
const text = "Hello, 世界!";
const bytes = utf8Encode(text);
console.log(bytes); // Uint8Array [72, 101, 108, 108, 111, 44, 32, 228, 184, 150, 231, 149, 140, 33]

const decoded = utf8Decode(bytes);
console.log(decoded); // "Hello, 世界!"
```

### Base64 인코딩

#### Base64의 특징
- **64개 문자 사용**: A-Z, a-z, 0-9, +, /
- **패딩 문자**: = (길이가 3의 배수가 아닐 때)
- **33% 크기 증가**: 3바이트 → 4바이트

#### Base64 인코딩 과정
```javascript
// Base64 인코딩 과정
function base64Encode(str) {
    // 1. 문자열을 UTF-8 바이트로 변환
    const encoder = new TextEncoder();
    const bytes = encoder.encode(str);
    
    // 2. 바이트를 Base64로 인코딩
    return btoa(String.fromCharCode(...bytes));
}

function base64Decode(base64Str) {
    // 1. Base64를 바이트로 디코딩
    const binaryStr = atob(base64Str);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
    }
    
    // 2. 바이트를 UTF-8 문자열로 변환
    const decoder = new TextDecoder('utf-8');
    return decoder.decode(bytes);
}

// 사용 예시
const original = "Hello, 世界!";
const encoded = base64Encode(original);
console.log(encoded); // "SGVsbG8sIOS4lOWkqSE="

const decoded = base64Decode(encoded);
console.log(decoded); // "Hello, 世界!"
```

## 예시

### JWT 토큰 생성

#### JWT 헤더 인코딩
```javascript
// JWT 헤더 (UTF-8 → Base64)
const header = {
    "alg": "HS256",
    "typ": "JWT"
};

const headerBase64 = btoa(JSON.stringify(header));
console.log(headerBase64); // "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"

// JWT 페이로드 (한글 포함)
const payload = {
    "name": "김철수",
    "email": "kim@example.com"
};

const payloadBase64 = btoa(JSON.stringify(payload));
console.log(payloadBase64); // "eyJuYW1lIjoi6rmA7ZmU7IisIiwiZW1haWwiOiJraW1AZXhhbXBsZS5jb20ifQ"
```

#### 완전한 JWT 토큰 생성
```javascript
class JWTGenerator {
    static generateToken(payload, secret) {
        // 1. 헤더 생성
        const header = {
            alg: 'HS256',
            typ: 'JWT'
        };
        
        // 2. 페이로드에 만료시간 추가
        const now = Math.floor(Date.now() / 1000);
        const fullPayload = {
            ...payload,
            iat: now,
            exp: now + (60 * 60) // 1시간 후 만료
        };
        
        // 3. Base64 인코딩
        const headerBase64 = btoa(JSON.stringify(header));
        const payloadBase64 = btoa(JSON.stringify(fullPayload));
        
        // 4. 서명 생성 (실제로는 HMAC-SHA256 사용)
        const signature = this.createSignature(headerBase64, payloadBase64, secret);
        
        // 5. JWT 토큰 조합
        return `${headerBase64}.${payloadBase64}.${signature}`;
    }
    
    static createSignature(header, payload, secret) {
        // 실제 구현에서는 HMAC-SHA256 사용
        const data = `${header}.${payload}`;
        return btoa(data + secret);
    }
}

// 사용 예시
const userData = {
    userId: 123,
    username: "김철수",
    role: "user"
};

const token = JWTGenerator.generateToken(userData, "my-secret-key");
console.log(token);
```

### 데이터 URL 생성

#### SVG를 Base64로 인코딩
```javascript
// SVG를 Base64로 인코딩하여 데이터 URL 생성
const svgContent = `
<svg width="100" height="100">
    <circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red"/>
</svg>`;

const svgBase64 = btoa(svgContent);
const dataUrl = `data:image/svg+xml;base64,${svgBase64}`;

// 이미지 요소에 적용
const img = document.createElement('img');
img.src = dataUrl;
document.body.appendChild(img);
```

#### 이미지 파일을 Base64로 변환
```javascript
// 파일을 Base64로 변환하는 함수
function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = () => {
            // data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ... 형태에서 base64 부분만 추출
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        
        reader.onerror = () => {
            reject(new Error('파일 읽기 실패'));
        };
        
        reader.readAsDataURL(file);
    });
}

// 사용 예시
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        try {
            const base64 = await fileToBase64(file);
            console.log('Base64 데이터:', base64);
        } catch (error) {
            console.error('변환 실패:', error);
        }
    }
});
```

### 파일 업로드 처리

#### Base64로 파일 업로드
```javascript
// 파일을 Base64로 변환하여 서버 전송
async function uploadFileAsBase64(file) {
    try {
        const base64 = await fileToBase64(file);
        
        // 서버로 전송
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: file.name,
                data: base64,
                size: file.size,
                type: file.type
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('업로드 실패:', error);
        throw error;
    }
}

// 사용 예시
const uploadButton = document.getElementById('uploadButton');
uploadButton.addEventListener('click', async () => {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (file) {
        try {
            const result = await uploadFileAsBase64(file);
            console.log('업로드 성공:', result);
        } catch (error) {
            console.error('업로드 실패:', error);
        }
    }
});
```

### 이메일 첨부파일 처리

#### 이메일에 Base64 첨부파일 추가
```javascript
// 이메일 첨부파일을 Base64로 처리
class EmailAttachment {
    constructor(filename, data, contentType) {
        this.filename = filename;
        this.data = data;
        this.contentType = contentType;
        this.base64Data = null;
    }
    
    async toBase64() {
        if (this.data instanceof File) {
            this.base64Data = await fileToBase64(this.data);
        } else if (typeof this.data === 'string') {
            this.base64Data = btoa(this.data);
        } else {
            throw new Error('지원하지 않는 데이터 타입입니다.');
        }
        return this.base64Data;
    }
    
    toEmailFormat() {
        return {
            filename: this.filename,
            content: this.base64Data,
            encoding: 'base64',
            contentType: this.contentType
        };
    }
}

// 사용 예시
async function sendEmailWithAttachment() {
    const attachment = new EmailAttachment(
        'document.pdf',
        pdfFile,
        'application/pdf'
    );
    
    await attachment.toBase64();
    
    const emailData = {
        to: 'recipient@example.com',
        subject: '첨부파일이 있는 이메일',
        body: '첨부파일을 확인해주세요.',
        attachments: [attachment.toEmailFormat()]
    };
    
    // 이메일 전송 로직
    console.log('이메일 데이터:', emailData);
}
```

## 운영 팁

### 성능 최적화

#### 대용량 파일 처리
```javascript
// 대용량 파일을 청크 단위로 처리
class ChunkedBase64Encoder {
    constructor(chunkSize = 1024 * 1024) { // 1MB 청크
        this.chunkSize = chunkSize;
    }
    
    async encodeLargeFile(file) {
        const chunks = [];
        const totalChunks = Math.ceil(file.size / this.chunkSize);
        
        for (let i = 0; i < totalChunks; i++) {
            const start = i * this.chunkSize;
            const end = Math.min(start + this.chunkSize, file.size);
            const chunk = file.slice(start, end);
            
            const base64Chunk = await this.chunkToBase64(chunk);
            chunks.push(base64Chunk);
            
            // 진행률 표시
            const progress = ((i + 1) / totalChunks) * 100;
            console.log(`인코딩 진행률: ${progress.toFixed(1)}%`);
        }
        
        return chunks.join('');
    }
    
    async chunkToBase64(chunk) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => {
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.readAsDataURL(chunk);
        });
    }
}

// 사용 예시
const encoder = new ChunkedBase64Encoder();
const largeFile = document.getElementById('largeFile').files[0];

if (largeFile) {
    const base64Data = await encoder.encodeLargeFile(largeFile);
    console.log('대용량 파일 인코딩 완료');
}
```

### 메모리 효율성

#### 스트림 기반 인코딩
```javascript
// 스트림 기반 Base64 인코딩
class StreamBase64Encoder {
    constructor() {
        this.buffer = '';
        this.output = '';
    }
    
    encode(chunk) {
        this.buffer += chunk;
        
        // 3바이트씩 처리
        while (this.buffer.length >= 3) {
            const threeBytes = this.buffer.slice(0, 3);
            this.buffer = this.buffer.slice(3);
            
            const base64 = this.threeBytesToBase64(threeBytes);
            this.output += base64;
        }
        
        return this.output;
    }
    
    finish() {
        // 남은 바이트 처리
        if (this.buffer.length > 0) {
            const padding = 3 - this.buffer.length;
            const padded = this.buffer + '\0'.repeat(padding);
            const base64 = this.threeBytesToBase64(padded);
            
            // 패딩 추가
            this.output += base64.slice(0, 4 - padding) + '='.repeat(padding);
        }
        
        return this.output;
    }
    
    threeBytesToBase64(bytes) {
        const b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        let result = '';
        
        for (let i = 0; i < 3; i++) {
            const byte = bytes.charCodeAt(i) || 0;
            const index = (byte >> 2) & 0x3F;
            result += b64chars[index];
            
            if (i < 2) {
                const nextByte = bytes.charCodeAt(i + 1) || 0;
                const index2 = ((byte & 0x3) << 4) | ((nextByte >> 4) & 0xF);
                result += b64chars[index2];
            }
        }
        
        return result;
    }
}

// 사용 예시
const encoder = new StreamBase64Encoder();
const text = "Hello, World!";

for (let i = 0; i < text.length; i += 3) {
    const chunk = text.slice(i, i + 3);
    encoder.encode(chunk);
}

const result = encoder.finish();
console.log(result); // "SGVsbG8sIFdvcmxkIQ=="
```

### 보안 고려사항

#### 민감한 데이터 처리
```javascript
// 민감한 데이터의 안전한 Base64 인코딩
class SecureBase64Encoder {
    static encodeSensitiveData(data, salt = '') {
        // 1. 솔트 추가
        const saltedData = data + salt;
        
        // 2. Base64 인코딩
        const base64 = btoa(saltedData);
        
        // 3. 추가 암호화 (실제로는 더 강력한 암호화 사용)
        return this.encrypt(base64);
    }
    
    static decodeSensitiveData(encodedData, salt = '') {
        try {
            // 1. 복호화
            const decrypted = this.decrypt(encodedData);
            
            // 2. Base64 디코딩
            const decoded = atob(decrypted);
            
            // 3. 솔트 제거
            return decoded.slice(0, -salt.length);
        } catch (error) {
            throw new Error('디코딩 실패: 잘못된 데이터 또는 키');
        }
    }
    
    static encrypt(data) {
        // 실제 구현에서는 AES 등 강력한 암호화 사용
        return btoa(data.split('').reverse().join(''));
    }
    
    static decrypt(data) {
        return atob(data).split('').reverse().join('');
    }
}

// 사용 예시
const sensitiveData = "password123";
const salt = "randomSalt123";

const encoded = SecureBase64Encoder.encodeSensitiveData(sensitiveData, salt);
console.log('인코딩된 데이터:', encoded);

const decoded = SecureBase64Encoder.decodeSensitiveData(encoded, salt);
console.log('디코딩된 데이터:', decoded);
```

## 참고

### Base64 표준

#### RFC 4648 표준
- **알파벳**: A-Z, a-z, 0-9
- **특수문자**: +, /
- **패딩**: = (길이가 3의 배수가 아닐 때)
- **줄바꿈**: 76자마다 CRLF 삽입 (MIME 표준)

#### URL 안전 Base64
```javascript
// URL 안전 Base64 인코딩
function urlSafeBase64Encode(str) {
    return btoa(str)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

function urlSafeBase64Decode(str) {
    // 패딩 복원
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    while (str.length % 4) {
        str += '=';
    }
    return atob(str);
}

// 사용 예시
const original = "Hello, World!";
const urlSafe = urlSafeBase64Encode(original);
console.log(urlSafe); // "SGVsbG8sIFdvcmxkIQ"

const decoded = urlSafeBase64Decode(urlSafe);
console.log(decoded); // "Hello, World!"
```

### 인코딩 성능 비교

#### 다양한 인코딩 방식 비교
```javascript
// 인코딩 방식별 성능 테스트
class EncodingBenchmark {
    static async testPerformance(data, iterations = 1000) {
        const results = {};
        
        // Base64 인코딩 테스트
        const base64Start = performance.now();
        for (let i = 0; i < iterations; i++) {
            btoa(data);
        }
        results.base64 = performance.now() - base64Start;
        
        // UTF-8 인코딩 테스트
        const utf8Start = performance.now();
        for (let i = 0; i < iterations; i++) {
            new TextEncoder().encode(data);
        }
        results.utf8 = performance.now() - utf8Start;
        
        return results;
    }
    
    static async testMemoryUsage(data) {
        const before = performance.memory?.usedJSHeapSize || 0;
        
        const base64 = btoa(data);
        const utf8 = new TextEncoder().encode(data);
        
        const after = performance.memory?.usedJSHeapSize || 0;
        
        return {
            base64Size: base64.length,
            utf8Size: utf8.length,
            memoryIncrease: after - before
        };
    }
}

// 사용 예시
const testData = "Hello, 世界! This is a test string with Unicode characters.";
const performance = await EncodingBenchmark.testPerformance(testData);
const memory = await EncodingBenchmark.testMemoryUsage(testData);

console.log('성능 결과:', performance);
console.log('메모리 사용량:', memory);
```

### 결론
Base64와 UTF-8 인코딩은 현대 웹 개발에서 필수적인 기술입니다.
UTF-8은 전 세계 모든 언어를 지원하는 범용 인코딩 방식이고,
Base64는 바이너리 데이터를 텍스트로 안전하게 전송할 수 있게 해줍니다.
JWT 토큰, 파일 업로드, 이메일 첨부파일 등 다양한 분야에서 활용되며,
적절한 성능 최적화와 보안 고려사항을 적용하면 더욱 효과적으로 사용할 수 있습니다.
