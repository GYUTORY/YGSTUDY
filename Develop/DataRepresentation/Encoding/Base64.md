---
title: Base64 인코딩 완벽 가이드
tags: [datarepresentation, encoding, base64, data-encoding, binary-to-text]
updated: 2024-12-19
---

# Base64 인코딩 완벽 가이드

## 배경

### Base64 인코딩의 필요성
Base64는 바이너리 데이터를 텍스트로 인코딩하는 방식으로, 8비트 바이너리 데이터를 6비트 단위로 나누어 64개의 ASCII 문자로 표현합니다. 이메일 첨부파일, 웹 API, 데이터베이스 등에서 바이너리 데이터를 안전하게 전송하고 저장하는 데 사용됩니다.

### 기본 개념
- **64개 문자**: A-Z (26개), a-z (26개), 0-9 (10개), +, / (2개)
- **패딩**: = 문자로 길이를 4의 배수로 맞춤
- **크기 증가**: 원본 데이터보다 약 33% 크기 증가
- **6비트 단위**: 8비트 데이터를 6비트씩 나누어 처리

## 핵심

### 1. Base64 인코딩 원리

#### 인코딩 과정
1. 바이너리 데이터를 6비트씩 나눕니다
2. 각 6비트를 Base64 문자로 변환합니다
3. 길이가 4의 배수가 되도록 = 패딩을 추가합니다

#### Base64 문자 테이블
| 인덱스 | 문자 | 인덱스 | 문자 | 인덱스 | 문자 | 인덱스 | 문자 |
|--------|------|--------|------|--------|------|--------|------|
| 0 | A | 16 | Q | 32 | g | 48 | w |
| 1 | B | 17 | R | 33 | h | 49 | x |
| 2 | C | 18 | S | 34 | i | 50 | y |
| 3 | D | 19 | T | 35 | j | 51 | z |
| 4 | E | 20 | U | 36 | k | 52 | 0 |
| 5 | F | 21 | V | 37 | l | 53 | 1 |
| 6 | G | 22 | W | 38 | m | 54 | 2 |
| 7 | H | 23 | X | 39 | n | 55 | 3 |
| 8 | I | 24 | Y | 40 | o | 56 | 4 |
| 9 | J | 25 | Z | 41 | p | 57 | 5 |
| 10 | K | 26 | a | 42 | q | 58 | 6 |
| 11 | L | 27 | b | 43 | r | 59 | 7 |
| 12 | M | 28 | c | 44 | s | 60 | 8 |
| 13 | N | 29 | d | 45 | t | 61 | 9 |
| 14 | O | 30 | e | 46 | u | 62 | + |
| 15 | P | 31 | f | 47 | v | 63 | / |

#### 수동 인코딩 예시
```javascript
// "Man" 문자열을 Base64로 인코딩하는 과정
function manualBase64Encode(text) {
    // 1. 문자열을 바이트로 변환
    const bytes = new TextEncoder().encode(text);
    console.log('바이트:', Array.from(bytes));
    
    // 2. 바이트를 2진수로 변환
    const binary = bytes.map(b => b.toString(2).padStart(8, '0')).join('');
    console.log('2진수:', binary);
    
    // 3. 6비트씩 나누기
    const chunks = [];
    for (let i = 0; i < binary.length; i += 6) {
        chunks.push(binary.slice(i, i + 6));
    }
    console.log('6비트 청크:', chunks);
    
    // 4. 각 청크를 10진수로 변환
    const decimals = chunks.map(chunk => parseInt(chunk.padEnd(6, '0'), 2));
    console.log('10진수:', decimals);
    
    // 5. Base64 문자로 변환
    const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    const result = decimals.map(d => base64Chars[d]).join('');
    console.log('Base64:', result);
    
    return result;
}

// "Man" → "TWFu"
manualBase64Encode('Man');
```

### 2. 프로그래밍 언어별 Base64 구현

#### JavaScript
```javascript
// 기본 Base64 인코딩/디코딩
function base64Encode(str) {
    return btoa(str);
}

function base64Decode(base64Str) {
    return atob(base64Str);
}

// 바이너리 데이터용 Base64
function base64EncodeBinary(data) {
    const bytes = new Uint8Array(data);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64DecodeBinary(base64Str) {
    const binary = atob(base64Str);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

// 사용 예시
console.log(base64Encode('Hello, World!')); // "SGVsbG8sIFdvcmxkIQ=="
console.log(base64Decode('SGVsbG8sIFdvcmxkIQ==')); // "Hello, World!"

// 바이너리 데이터 예시
const binaryData = new Uint8Array([72, 101, 108, 108, 111]);
console.log(base64EncodeBinary(binaryData)); // "SGVsbG8="
```

#### Python
```python
import base64

# 기본 Base64 인코딩/디코딩
def base64_encode(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')

def base64_decode(base64_str):
    return base64.b64decode(base64_str).decode('utf-8')

# 바이너리 데이터용 Base64
def base64_encode_binary(data):
    return base64.b64encode(data).decode('utf-8')

def base64_decode_binary(base64_str):
    return base64.b64decode(base64_str)

# 사용 예시
print(base64_encode('Hello, World!'))  # "SGVsbG8sIFdvcmxkIQ=="
print(base64_decode('SGVsbG8sIFdvcmxkIQ=='))  # "Hello, World!"

# 바이너리 데이터 예시
binary_data = b'Hello'
print(base64_encode_binary(binary_data))  # "SGVsbG8="
```

#### Java
```java
import java.util.Base64;

public class Base64Example {
    // 기본 Base64 인코딩/디코딩
    public static String base64Encode(String text) {
        return Base64.getEncoder().encodeToString(text.getBytes());
    }
    
    public static String base64Decode(String base64Str) {
        byte[] decoded = Base64.getDecoder().decode(base64Str);
        return new String(decoded);
    }
    
    // 바이너리 데이터용 Base64
    public static String base64EncodeBinary(byte[] data) {
        return Base64.getEncoder().encodeToString(data);
    }
    
    public static byte[] base64DecodeBinary(String base64Str) {
        return Base64.getDecoder().decode(base64Str);
    }
    
    public static void main(String[] args) {
        String text = "Hello, World!";
        String encoded = base64Encode(text);
        System.out.println(encoded); // "SGVsbG8sIFdvcmxkIQ=="
        
        String decoded = base64Decode(encoded);
        System.out.println(decoded); // "Hello, World!"
    }
}
```

### 3. 고급 Base64 기능

#### URL 안전 Base64
```javascript
// URL 안전 Base64 (+, / 대신 -, _ 사용)
function base64UrlEncode(str) {
    return btoa(str)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

function base64UrlDecode(base64UrlStr) {
    // 패딩 추가
    const padded = base64UrlStr + '='.repeat((4 - base64UrlStr.length % 4) % 4);
    // URL 안전 문자를 일반 Base64 문자로 변환
    const base64Str = padded.replace(/-/g, '+').replace(/_/g, '/');
    return atob(base64Str);
}

// 사용 예시
const urlSafe = base64UrlEncode('Hello, World!');
console.log(urlSafe); // "SGVsbG8sIFdvcmxkIQ"
console.log(base64UrlDecode(urlSafe)); // "Hello, World!"
```

#### 스트리밍 Base64 인코딩
```javascript
// 스트리밍 Base64 인코딩 (대용량 데이터용)
class StreamingBase64Encoder {
    constructor() {
        this.buffer = '';
        this.result = '';
    }
    
    // 데이터 청크를 추가
    write(data) {
        this.buffer += data;
        this.processBuffer();
    }
    
    // 버퍼 처리
    processBuffer() {
        // 3바이트씩 처리
        while (this.buffer.length >= 3) {
            const chunk = this.buffer.slice(0, 3);
            this.buffer = this.buffer.slice(3);
            this.result += this.encodeChunk(chunk);
        }
    }
    
    // 3바이트 청크를 Base64로 인코딩
    encodeChunk(chunk) {
        const bytes = new TextEncoder().encode(chunk);
        const binary = bytes.map(b => b.toString(2).padStart(8, '0')).join('');
        
        const base64Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        let result = '';
        
        for (let i = 0; i < binary.length; i += 6) {
            const sixBits = binary.slice(i, i + 6).padEnd(6, '0');
            const index = parseInt(sixBits, 2);
            result += base64Chars[index];
        }
        
        return result;
    }
    
    // 완료 및 패딩 추가
    finish() {
        if (this.buffer.length > 0) {
            this.result += this.encodeChunk(this.buffer);
        }
        return this.result;
    }
}

// 사용 예시
const encoder = new StreamingBase64Encoder();
encoder.write('Hello');
encoder.write(', World!');
console.log(encoder.finish()); // "SGVsbG8sIFdvcmxkIQ=="
```

## 예시

### 1. 실제 사용 사례

#### 이메일 첨부파일 인코딩
```javascript
// 파일을 Base64로 인코딩하여 이메일로 전송
async function encodeFileForEmail(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = function() {
            const base64 = btoa(reader.result);
            resolve({
                filename: file.name,
                contentType: file.type,
                data: base64,
                size: file.size
            });
        };
        
        reader.onerror = reject;
        reader.readAsBinaryString(file);
    });
}

// 사용 예시
const fileInput = document.getElementById('fileInput');
fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) {
        const encoded = await encodeFileForEmail(file);
        console.log('인코딩된 파일:', encoded);
        
        // 이메일 본문에 포함
        const emailBody = `
            첨부파일: ${encoded.filename}
            크기: ${encoded.size} bytes
            타입: ${encoded.contentType}
            데이터: ${encoded.data}
        `;
    }
});
```

#### 웹 API에서 이미지 전송
```javascript
// 이미지를 Base64로 인코딩하여 API로 전송
async function uploadImageAsBase64(imageFile) {
    const base64 = await fileToBase64(imageFile);
    
    const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filename: imageFile.name,
            data: base64,
            contentType: imageFile.type
        })
    });
    
    return response.json();
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// 사용 예시
const imageInput = document.getElementById('imageInput');
imageInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
        try {
            const result = await uploadImageAsBase64(file);
            console.log('업로드 성공:', result);
        } catch (error) {
            console.error('업로드 실패:', error);
        }
    }
});
```

### 2. 고급 패턴

#### 데이터베이스에 바이너리 데이터 저장
```javascript
// 바이너리 데이터를 Base64로 인코딩하여 데이터베이스에 저장
class BinaryDataManager {
    constructor(database) {
        this.db = database;
    }
    
    async saveBinaryData(filename, data, metadata = {}) {
        const base64Data = this.arrayBufferToBase64(data);
        
        const record = {
            id: this.generateId(),
            filename,
            data: base64Data,
            size: data.byteLength,
            contentType: metadata.contentType || 'application/octet-stream',
            createdAt: new Date(),
            ...metadata
        };
        
        await this.db.collection('binary_data').insertOne(record);
        return record.id;
    }
    
    async getBinaryData(id) {
        const record = await this.db.collection('binary_data').findOne({ id });
        if (!record) {
            throw new Error('Data not found');
        }
        
        return {
            filename: record.filename,
            data: this.base64ToArrayBuffer(record.data),
            contentType: record.contentType,
            size: record.size
        };
    }
    
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
    
    base64ToArrayBuffer(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }
    
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// 사용 예시
const dataManager = new BinaryDataManager(database);

// 파일 저장
const fileData = new ArrayBuffer(1024); // 예시 데이터
const id = await dataManager.saveBinaryData('example.bin', fileData, {
    contentType: 'application/octet-stream',
    description: 'Example binary file'
});

// 파일 불러오기
const retrieved = await dataManager.getBinaryData(id);
console.log('불러온 파일:', retrieved);
```

#### JWT 토큰에서 Base64 사용
```javascript
// JWT 토큰 생성 및 검증 (Base64 사용)
class JWTManager {
    constructor(secret) {
        this.secret = secret;
    }
    
    createToken(payload) {
        const header = {
            alg: 'HS256',
            typ: 'JWT'
        };
        
        const now = Math.floor(Date.now() / 1000);
        const claims = {
            ...payload,
            iat: now,
            exp: now + 3600 // 1시간 후 만료
        };
        
        const headerB64 = this.base64UrlEncode(JSON.stringify(header));
        const payloadB64 = this.base64UrlEncode(JSON.stringify(claims));
        
        const signature = this.createSignature(headerB64 + '.' + payloadB64);
        const signatureB64 = this.base64UrlEncode(signature);
        
        return `${headerB64}.${payloadB64}.${signatureB64}`;
    }
    
    verifyToken(token) {
        const parts = token.split('.');
        if (parts.length !== 3) {
            throw new Error('Invalid token format');
        }
        
        const [headerB64, payloadB64, signatureB64] = parts;
        const expectedSignature = this.createSignature(headerB64 + '.' + payloadB64);
        const actualSignature = this.base64UrlDecode(signatureB64);
        
        if (!this.compareSignatures(expectedSignature, actualSignature)) {
            throw new Error('Invalid signature');
        }
        
        const payload = JSON.parse(this.base64UrlDecode(payloadB64));
        
        if (payload.exp < Math.floor(Date.now() / 1000)) {
            throw new Error('Token expired');
        }
        
        return payload;
    }
    
    base64UrlEncode(str) {
        return btoa(str)
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '');
    }
    
    base64UrlDecode(str) {
        const padded = str + '='.repeat((4 - str.length % 4) % 4);
        const base64 = padded.replace(/-/g, '+').replace(/_/g, '/');
        return atob(base64);
    }
    
    createSignature(data) {
        // 간단한 해시 함수 (실제로는 HMAC-SHA256 사용)
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
            const char = data.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // 32비트 정수로 변환
        }
        return hash.toString();
    }
    
    compareSignatures(sig1, sig2) {
        return sig1 === sig2;
    }
}

// 사용 예시
const jwtManager = new JWTManager('my-secret-key');

const token = jwtManager.createToken({
    userId: 123,
    username: 'john_doe'
});

console.log('JWT 토큰:', token);

try {
    const payload = jwtManager.verifyToken(token);
    console.log('토큰 검증 성공:', payload);
} catch (error) {
    console.error('토큰 검증 실패:', error.message);
}
```

## 운영 팁

### 1. 성능 최적화

#### 메모리 효율적인 Base64 처리
```javascript
// 스트림 기반 Base64 처리 (대용량 데이터용)
class StreamBase64Processor {
    constructor(chunkSize = 1024) {
        this.chunkSize = chunkSize;
        this.buffer = '';
    }
    
    *processStream(inputStream) {
        for await (const chunk of inputStream) {
            this.buffer += chunk;
            
            while (this.buffer.length >= this.chunkSize) {
                const processChunk = this.buffer.slice(0, this.chunkSize);
                this.buffer = this.buffer.slice(this.chunkSize);
                
                yield this.encodeChunk(processChunk);
            }
        }
        
        // 남은 버퍼 처리
        if (this.buffer.length > 0) {
            yield this.encodeChunk(this.buffer);
        }
    }
    
    encodeChunk(chunk) {
        return btoa(chunk);
    }
}

// 사용 예시
async function processLargeFile(file) {
    const processor = new StreamBase64Processor();
    const stream = file.stream();
    
    for await (const encodedChunk of processor.processStream(stream)) {
        // 각 청크를 처리 (예: 네트워크로 전송)
        console.log('인코딩된 청크:', encodedChunk);
    }
}
```

#### 캐싱을 활용한 Base64 변환
```javascript
// Base64 변환 결과 캐싱
class CachedBase64Converter {
    constructor() {
        this.encodeCache = new Map();
        this.decodeCache = new Map();
    }
    
    encode(data) {
        const key = this.generateKey(data);
        if (this.encodeCache.has(key)) {
            return this.encodeCache.get(key);
        }
        
        const result = btoa(data);
        this.encodeCache.set(key, result);
        return result;
    }
    
    decode(base64Str) {
        if (this.decodeCache.has(base64Str)) {
            return this.decodeCache.get(base64Str);
        }
        
        const result = atob(base64Str);
        this.decodeCache.set(base64Str, result);
        return result;
    }
    
    generateKey(data) {
        // 간단한 해시 함수
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
            const char = data.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString();
    }
    
    clearCache() {
        this.encodeCache.clear();
        this.decodeCache.clear();
    }
}
```

### 2. 에러 처리

#### Base64 유효성 검사
```javascript
// Base64 문자열 유효성 검사
function isValidBase64(str) {
    // Base64 패턴 검사
    const base64Pattern = /^[A-Za-z0-9+/]*={0,2}$/;
    
    if (!base64Pattern.test(str)) {
        return false;
    }
    
    // 길이 검사 (4의 배수)
    if (str.length % 4 !== 0) {
        return false;
    }
    
    // 패딩 검사
    const paddingIndex = str.indexOf('=');
    if (paddingIndex !== -1) {
        // = 문자는 끝에만 있어야 함
        if (paddingIndex < str.length - 2) {
            return false;
        }
        // 패딩은 최대 2개
        if (str.slice(paddingIndex).length > 2) {
            return false;
        }
    }
    
    return true;
}

// 안전한 Base64 디코딩
function safeBase64Decode(base64Str) {
    try {
        if (!isValidBase64(base64Str)) {
            throw new Error('Invalid Base64 format');
        }
        
        return atob(base64Str);
    } catch (error) {
        console.error('Base64 디코딩 오류:', error.message);
        return null;
    }
}

// 사용 예시
console.log(isValidBase64('SGVsbG8sIFdvcmxkIQ==')); // true
console.log(isValidBase64('SGVsbG8sIFdvcmxkIQ'));   // true (패딩 없음)
console.log(isValidBase64('SGVsbG8sIFdvcmxkIQ===')); // false (패딩 초과)
console.log(isValidBase64('SGVsbG8sIFdvcmxkIQ!=')); // false (잘못된 문자)
```

## 참고

### Base64 vs 다른 인코딩 방식

| 인코딩 | 문자셋 | 크기 증가 | 사용 분야 |
|--------|--------|-----------|-----------|
| **Base64** | A-Z, a-z, 0-9, +, / | ~33% | 이메일, 웹 API |
| **Base32** | A-Z, 2-7 | ~60% | DNS, 파일명 |
| **Base16** | 0-9, A-F | ~100% | 16진수 표기 |
| **Base85** | ASCII 33-117 | ~25% | PDF, PostScript |

### Base64 변형

| 변형 | 특징 | 사용 분야 |
|------|------|-----------|
| **URL Safe Base64** | +, / 대신 -, _ 사용 | URL, 파일명 |
| **MIME Base64** | 표준 Base64 | 이메일 첨부 |
| **Base64URL** | 패딩 제거 | JWT, URL |

### 결론
Base64는 바이너리 데이터를 텍스트로 안전하게 변환하는 표준 방식으로, 다양한 분야에서 널리 사용됩니다. 적절한 에러 처리와 성능 최적화를 통해 안정적인 Base64 인코딩/디코딩 시스템을 구축하고, URL 안전 Base64나 스트리밍 처리를 통해 특수한 요구사항에 맞는 솔루션을 제공하세요.
