# Base64와 UTF-8 인코딩

## 📚 인코딩이란?

**인코딩(Encoding)**은 정보를 다른 형태나 형식으로 변환하는 과정입니다. 쉽게 말해서, 컴퓨터가 이해할 수 있는 언어로 바꾸는 작업이라고 생각하면 됩니다.

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

---

## 🌐 UTF-8 인코딩

**UTF-8**은 전 세계의 모든 문자를 표현할 수 있는 문자 인코딩 방식입니다. 현재 웹에서 가장 널리 사용되는 표준입니다.

### UTF-8의 핵심 특징

#### 1️⃣ 가변 길이 인코딩
- 영어, 숫자, 특수문자: **1바이트**
- 유럽 언어: **2바이트** 
- 한글, 한자: **3바이트**
- 특수 이모지: **4바이트**

#### 2️⃣ ASCII 호환성
- 기존 영어 텍스트는 그대로 사용 가능
- 새로운 시스템 도입 시 기존 데이터 손실 없음

### UTF-8 인코딩 구조

| 문자 종류 | 바이트 수 | 비트 패턴 | 예시 |
|-----------|-----------|-----------|------|
| ASCII 문자 | 1바이트 | `0xxxxxxx` | A, B, C, 1, 2, 3 |
| 라틴 확장 | 2바이트 | `110xxxxx 10xxxxxx` | é, ñ, ü |
| 한글/한자 | 3바이트 | `1110xxxx 10xxxxxx 10xxxxxx` | 안, 漢, 字 |
| 특수 문자 | 4바이트 | `11110xxx 10xxxxxx 10xxxxxx 10xxxxxx` | 🚀, 🎉, 🌟 |

### JavaScript에서 UTF-8 확인하기

```javascript
// 문자열의 UTF-8 바이트 길이 확인
function getUTF8Length(str) {
    return new TextEncoder().encode(str).length;
}

console.log(getUTF8Length("A"));        // 1 (영어)
console.log(getUTF8Length("안녕"));     // 6 (한글 2글자 = 3바이트 × 2)
console.log(getUTF8Length("🚀"));       // 4 (이모지)

// UTF-8 바이트 배열로 변환
const text = "안녕하세요";
const encoder = new TextEncoder();
const bytes = encoder.encode(text);
console.log(bytes); // Uint8Array(15) [236, 149, 136, 235, 133, 149, 237, 149, 152, 236, 132, 184, 236, 154, 148]
```

---

## 🔢 Base64 인코딩

**Base64**는 바이너리 데이터(이미지, 파일 등)를 텍스트로 변환하는 인코딩 방식입니다.

### Base64가 필요한 이유
- 이메일로 파일을 첨부할 때
- 웹페이지에 이미지를 직접 포함할 때
- JSON에 바이너리 데이터를 포함할 때
- HTTP 헤더에 바이너리 데이터를 전송할 때

### Base64 인코딩 과정

#### 1단계: 3바이트씩 묶기
```
원본: "Man"
바이너리: 01001101 01100001 01101110
```

#### 2단계: 6비트씩 분할
```
010011 010110 000101 101110
```

#### 3단계: Base64 테이블로 변환
```
010011 → 19 → T
010110 → 22 → W  
000101 → 5  → F
101110 → 46 → u
```

#### 4단계: 결과
```
"Man" → "TWFu"
```

### Base64 색인표

| 값 | 문자 | 값 | 문자 | 값 | 문자 | 값 | 문자 |
|----|------|----|------|----|------|----|------|
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

### JavaScript에서 Base64 사용하기

```javascript
// 문자열을 Base64로 인코딩
const text = "Hello, World!";
const encoded = btoa(text);
console.log(encoded); // "SGVsbG8sIFdvcmxkIQ=="

// Base64를 문자열로 디코딩
const decoded = atob(encoded);
console.log(decoded); // "Hello, World!"

// 한글 Base64 인코딩 (UTF-8 처리)
function encodeKorean(text) {
    const encoder = new TextEncoder();
    const bytes = encoder.encode(text);
    const binary = Array.from(bytes, byte => String.fromCharCode(byte)).join('');
    return btoa(binary);
}

function decodeKorean(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    const decoder = new TextDecoder();
    return decoder.decode(bytes);
}

const koreanText = "안녕하세요";
const koreanEncoded = encodeKorean(koreanText);
console.log(koreanEncoded); // "7JWI64WV7ZWY7IS47JqU"

const koreanDecoded = decodeKorean(koreanEncoded);
console.log(koreanDecoded); // "안녕하세요"

// 이미지를 Base64로 변환
function imageToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Base64 이미지를 화면에 표시
function displayBase64Image(base64String) {
    const img = document.createElement('img');
    img.src = base64String;
    document.body.appendChild(img);
}
```

---

## 🔄 UTF-8과 Base64 조합 사용

실제 웹 개발에서는 UTF-8과 Base64를 함께 사용하는 경우가 많습니다.

### 일반적인 사용 시나리오

#### 1. JWT 토큰 생성
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

#### 2. 데이터 URL 생성
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
```

#### 3. 파일 업로드 처리
```javascript
// 파일을 Base64로 변환하여 서버 전송
async function uploadFileAsBase64(file) {
    const base64 = await imageToBase64(file);
    
    // 서버로 전송
    const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            filename: file.name,
            data: base64
        })
    });
    
    return response.json();
}
```

---

## ⚖️ Base64의 장단점

### ✅ 장점
- **시스템 독립성**: 어떤 시스템에서도 동일하게 처리
- **텍스트 기반 전송**: HTTP, 이메일 등 텍스트 프로토콜에서 바이너리 전송 가능
- **특수 문자 안전**: URL이나 JSON에서 문제없이 사용
- **간단한 구현**: 대부분의 프로그래밍 언어에서 기본 지원

### ❌ 단점
- **크기 증가**: 원본보다 약 33% 크기 증가
- **성능 오버헤드**: 인코딩/디코딩에 추가 연산 필요
- **가독성 저하**: 사람이 읽기 어려운 형태

### 크기 비교 예시
```javascript
const originalText = "안녕하세요! Hello World! 🚀";
const utf8Bytes = new TextEncoder().encode(originalText);
const base64String = btoa(String.fromCharCode(...utf8Bytes));

console.log(`원본 텍스트: ${originalText}`);
console.log(`UTF-8 바이트 수: ${utf8Bytes.length}`);
console.log(`Base64 문자열 길이: ${base64String.length}`);
console.log(`크기 증가율: ${((base64String.length / utf8Bytes.length - 1) * 100).toFixed(1)}%`);
```

---

## 🛠️ 실무 활용 팁

### 1. URL-Safe Base64
```javascript
// 일반 Base64는 +, /, = 문자가 URL에서 문제가 될 수 있음
function toUrlSafeBase64(str) {
    return btoa(str)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

function fromUrlSafeBase64(str) {
    // 패딩 추가
    str = str + '='.repeat((4 - str.length % 4) % 4);
    return atob(str.replace(/-/g, '+').replace(/_/g, '/'));
}

const urlSafe = toUrlSafeBase64("Hello World!");
console.log(urlSafe); // "SGVsbG8gV29ybGQh"
```

### 2. Base64 유효성 검사
```javascript
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
    
    // 디코딩 시도
    try {
        atob(str);
        return true;
    } catch {
        return false;
    }
}

console.log(isValidBase64("SGVsbG8=")); // true
console.log(isValidBase64("Invalid!")); // false
```

### 3. 대용량 데이터 처리
```javascript
// 큰 파일을 청크 단위로 Base64 변환
async function largeFileToBase64(file, chunkSize = 1024 * 1024) {
    const chunks = [];
    
    for (let i = 0; i < file.size; i += chunkSize) {
        const chunk = file.slice(i, i + chunkSize);
        const base64Chunk = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.readAsDataURL(chunk);
        });
        chunks.push(base64Chunk);
    }
    
    return chunks.join('');
}
```

---

## 📖 참고 자료
- [Base64 인코딩이란?](https://effectivesquid.tistory.com/entry/Base64-%EC%9D%B8%EC%BD%94%EB%94%A9%EC%9D%B4%EB%9E%80)
- [UTF-8 위키피디아](https://en.wikipedia.org/wiki/UTF-8)
- [Base64 위키피디아](https://en.wikipedia.org/wiki/Base64)
- [RFC 4648 - Base64 인코딩 표준](https://tools.ietf.org/html/rfc4648)