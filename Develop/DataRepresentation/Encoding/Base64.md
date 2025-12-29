---
title: Base64 인코딩
tags: [datarepresentation, encoding, base64, data-encoding, binary-to-text]
updated: 2025-12-29
---

# Base64 인코딩

## 정의

Base64는 바이너리 데이터를 ASCII 텍스트로 안전하게 변환하는 인코딩 방식입니다.

### 특징
- 8비트 바이너리 데이터를 6비트 단위로 재구성
- 64개의 안전한 ASCII 문자로 표현
- 원본 데이터 대비 약 33% 크기 증가

### 사용 목적
- 텍스트 기반 프로토콜에서 바이너리 데이터 전송
- 이메일 첨부파일, 데이터 URL, JWT 토큰

## 동작 원리

### 인코딩 과정

**1. 바이너리 데이터를 3바이트(24비트) 그룹으로 분할**
```
원본: [01001000] [01100101] [01101100]
      H          e          l
```

**2. 24비트를 4개의 6비트 그룹으로 재구성**
```
[010010] [000110] [010101] [101100]
   18       6       21       44
```

**3. 각 6비트 값을 Base64 문자로 변환**
```
18 → S
6  → G
21 → V
44 → s
```

**4. 패딩 추가 (필요한 경우)**
- 원본이 3의 배수가 아니면 `=` 로 패딩
- 1바이트 부족: `==`
- 2바이트 부족: `=`

### Base64 문자셋

```
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/
```

- A-Z: 인덱스 0-25
- a-z: 인덱스 26-51
- 0-9: 인덱스 52-61
- +: 인덱스 62
- /: 인덱스 63
- =: 패딩

## 사용법

### JavaScript 기본 API

```javascript
// 인코딩
const text = 'Hello, World!';
const encoded = Buffer.from(text).toString('base64');
console.log(encoded); // SGVsbG8sIFdvcmxkIQ==

// 디코딩
const decoded = Buffer.from(encoded, 'base64').toString('utf8');
console.log(decoded); // Hello, World!
```

### 브라우저 API

```javascript
// 인코딩
const text = 'Hello, World!';
const encoded = btoa(text);
console.log(encoded); // SGVsbG8sIFdvcmxkIQ==

// 디코딩
const decoded = atob(encoded);
console.log(decoded); // Hello, World!

// 유니코드 처리
const unicodeText = '안녕하세요';
const encoded = btoa(encodeURIComponent(unicodeText));
const decoded = decodeURIComponent(atob(encoded));
```

### 파일 인코딩

```javascript
const fs = require('fs');

// 이미지를 Base64로 인코딩
const imageBuffer = fs.readFileSync('image.png');
const base64Image = imageBuffer.toString('base64');

// Data URL 생성
const dataUrl = `data:image/png;base64,${base64Image}`;
console.log(dataUrl);
```

## 실전 예제

### JWT 토큰

```javascript
// JWT는 Header, Payload, Signature를 Base64로 인코딩
const header = { alg: 'HS256', typ: 'JWT' };
const payload = { userId: 123, exp: 1234567890 };

const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64');
const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64');

console.log(`${encodedHeader}.${encodedPayload}.signature`);
```

### API 인증

```javascript
// Basic Authentication
const username = 'user';
const password = 'pass';
const credentials = `${username}:${password}`;
const encodedCredentials = Buffer.from(credentials).toString('base64');

const headers = {
  'Authorization': `Basic ${encodedCredentials}`
};
```

### 이미지 임베딩

```html
<!-- Base64로 인코딩된 이미지를 HTML에 직접 삽입 -->
<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..." />
```

## Base64 변형

### Base64URL (URL-safe)

URL이나 파일명에 사용할 수 있도록 변형된 버전입니다.

**차이점:**
- `+` → `-`
- `/` → `_`
- `=` 패딩 제거

```javascript
function base64ToBase64Url(base64) {
  return base64
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

function base64UrlToBase64(base64url) {
  let base64 = base64url
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  
  // 패딩 복원
  while (base64.length % 4) {
    base64 += '=';
  }
  
  return base64;
}
```

## 성능 고려사항

### 인코딩 비용

| 연산 | 비용 | 설명 |
|------|------|------|
| Base64 인코딩 | 중간 | CPU 연산 필요 |
| 크기 증가 | 33% | 대역폭 증가 |
| 메모리 사용 | 높음 | 원본 + 인코딩 결과 |

### 최적화 팁

```javascript
// 스트리밍 인코딩 (대용량 파일)
const fs = require('fs');
const { Transform } = require('stream');

class Base64EncodeStream extends Transform {
  _transform(chunk, encoding, callback) {
    const encoded = chunk.toString('base64');
    this.push(encoded);
    callback();
  }
}

// 사용
fs.createReadStream('large-file.bin')
  .pipe(new Base64EncodeStream())
  .pipe(fs.createWriteStream('output.txt'));
```

## 참고

### Base64 vs 다른 인코딩

| 인코딩 | 문자 수 | 크기 증가 | 사용 사례 |
|--------|---------|----------|----------|
| Base64 | 64 | 33% | 일반적 사용 |
| Base32 | 32 | 60% | 대소문자 구분 불가 환경 |
| Base16 (Hex) | 16 | 100% | 디버깅, 표시 |
| Base85 | 85 | 25% | PDF, Git |

### 관련 문서
- RFC 4648 - The Base16, Base32, and Base64 Data Encodings
- [MDN - btoa()](https://developer.mozilla.org/en-US/docs/Web/API/btoa)
- [Node.js Buffer Documentation](https://nodejs.org/api/buffer.html)
