---
title: Base64 인코딩
tags: [datarepresentation, encoding, base64, data-encoding, binary-to-text]
updated: 2026-04-10
---

# Base64 인코딩

## 정의

Base64는 바이너리 데이터를 ASCII 텍스트로 변환하는 인코딩 방식이다. 텍스트만 다룰 수 있는 프로토콜(이메일, HTTP 헤더, JSON)에서 바이너리 데이터를 실어 보내야 할 때 쓴다.

핵심은 단순하다. 8비트 바이너리 데이터를 6비트 단위로 쪼개서, 64개의 안전한 ASCII 문자로 다시 표현하는 것이다. 원본 대비 약 33% 크기가 늘어난다.

## 동작 원리

### 인코딩 과정 다이어그램

`Hello`를 Base64로 인코딩하는 전체 과정이다.

```
┌─────────────────────────────────────────────────────────┐
│  1단계: 원본 문자열을 바이트(8비트)로 변환                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   H         e         l         l         o             │
│   72        101       108       108       111           │
│   01001000  01100101  01101100  01101100  01101111       │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  2단계: 3바이트(24비트)씩 그룹으로 묶기                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   그룹1: [01001000][01100101][01101100]  ← 3바이트 완성   │
│   그룹2: [01101100][01101111][????????]  ← 1바이트 부족   │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  3단계: 24비트를 6비트 4개로 쪼개기                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   그룹1: [010010][000110][010101][101100]                │
│           = 18    = 6     = 21    = 44                  │
│                                                         │
│   그룹2: [011011][000110][111100][??????]                │
│           = 27    = 6     = 60    = 패딩                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  4단계: 인덱스 → Base64 문자 매핑                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   18→S   6→G   21→V   44→s   27→b   6→G   60→8   ?→=  │
│                                                         │
│   결과: "SGVsbG8="                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Base64 문자셋 (인덱스 테이블)

```
인덱스  0-25  : A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
인덱스 26-51  : a b c d e f g h i j k l m n o p q r s t u v w x y z
인덱스 52-61  : 0 1 2 3 4 5 6 7 8 9
인덱스 62     : +
인덱스 63     : /
패딩          : =
```

### 패딩 처리 흐름

Base64 인코딩은 항상 3바이트를 한 단위로 처리한다. 원본 데이터가 3의 배수가 아니면 패딩이 붙는다.

```
원본 길이를 3으로 나눈 나머지로 판단한다:

  원본 바이트 수 % 3 == 0
  ├── 남는 바이트 없음
  └── 패딩 없음
      예: "ABC" (3바이트) → "QUJD"

  원본 바이트 수 % 3 == 1
  ├── 1바이트 남음 → 8비트를 6비트 2개로 분할 (뒤에 0 4개 채움)
  └── 패딩 "==" 추가 (출력 4자리 맞추기)
      예: "A" (1바이트) → "QQ=="

  원본 바이트 수 % 3 == 2
  ├── 2바이트 남음 → 16비트를 6비트 3개로 분할 (뒤에 0 2개 채움)
  └── 패딩 "=" 추가 (출력 4자리 맞추기)
      예: "AB" (2바이트) → "QUI="
```

패딩 `=`의 역할은 디코더에게 "마지막 그룹에서 실제 데이터가 몇 바이트인지" 알려주는 것이다. `=`가 1개면 2바이트, 2개면 1바이트가 실제 데이터다.

## 표준 Base64와 MIME Base64

Base64 구현은 하나가 아니다. RFC가 다르고 동작도 다르다. 실무에서 혼동하면 디코딩 실패로 이어진다.

### 비교

| 구분 | 표준 Base64 (RFC 4648) | MIME Base64 (RFC 2045) | Base64URL (RFC 4648 §5) |
|------|----------------------|----------------------|------------------------|
| 문자셋 | A-Z, a-z, 0-9, +, / | 동일 | A-Z, a-z, 0-9, -, _ |
| 패딩 | 필수 | 필수 | 선택 (보통 생략) |
| 줄바꿈 | 없음 | 76자마다 CRLF 삽입 | 없음 |
| 용도 | 일반적인 인코딩 | 이메일 첨부 (SMTP) | URL, JWT, 파일명 |

### MIME Base64의 줄바꿈 문제

이메일 시스템에서 Base64 데이터를 받으면 76자마다 `\r\n`이 들어가 있다.

```
SGVsbG8sIFdvcmxkIQ0KVGhpcyBpcyBhIHRlc3QgbWVzc2FnZS4NClRo
aXMgaXMgYW5vdGhlciBsaW5lLg==
```

이걸 표준 Base64 디코더에 그대로 넣으면 줄바꿈 문자를 잘못된 입력으로 처리해서 실패하는 경우가 있다. 디코딩 전에 `\r\n`을 제거해야 한다.

```java
// MIME Base64 디코딩 시 줄바꿈 처리
String mimeEncoded = "SGVsbG8s\r\nIFdvcmxk\r\nIQ==";

// 방법 1: Java의 MIME 디코더 사용 (줄바꿈 자동 무시)
byte[] decoded = Base64.getMimeDecoder().decode(mimeEncoded);

// 방법 2: 직접 제거 후 표준 디코더 사용
String cleaned = mimeEncoded.replaceAll("\\r\\n", "");
byte[] decoded2 = Base64.getDecoder().decode(cleaned);
```

### Base64URL이 필요한 이유

표준 Base64의 `+`와 `/`는 URL에서 특수 의미를 가진다. `+`는 공백으로 해석되고, `/`는 경로 구분자다. JWT 토큰이나 URL 파라미터에 Base64를 쓸 때 표준 문자셋을 그대로 쓰면 깨진다.

```
표준:    data+value/end==
URL해석: data value end==   ← + 가 공백으로 바뀜
```

## 사용법

### Java

```java
import java.util.Base64;
import java.nio.charset.StandardCharsets;

public class Base64Example {

    public static void main(String[] args) {
        String text = "Hello, World!";

        // 표준 Base64 인코딩/디코딩
        String encoded = Base64.getEncoder()
                .encodeToString(text.getBytes(StandardCharsets.UTF_8));
        System.out.println(encoded);  // SGVsbG8sIFdvcmxkIQ==

        byte[] decodedBytes = Base64.getDecoder().decode(encoded);
        String decoded = new String(decodedBytes, StandardCharsets.UTF_8);
        System.out.println(decoded);  // Hello, World!

        // URL-safe Base64
        String urlEncoded = Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(text.getBytes(StandardCharsets.UTF_8));
        System.out.println(urlEncoded);  // SGVsbG8sIFdvcmxkIQ

        // MIME Base64 (76자마다 줄바꿈)
        byte[] largeData = new byte[100];
        String mimeEncoded = Base64.getMimeEncoder()
                .encodeToString(largeData);
        // 76자마다 \r\n 삽입된 결과
    }
}
```

Java 8부터 `java.util.Base64`가 표준 라이브러리에 포함됐다. 그 전에는 `sun.misc.BASE64Encoder`를 쓰는 코드가 있는데, 이건 내부 API라 JDK 버전에 따라 동작이 달라진다. 레거시 코드에서 마이그레이션할 때 주의해야 한다.

### Python

```python
import base64

text = "Hello, World!"

# 표준 Base64
encoded = base64.b64encode(text.encode('utf-8'))
print(encoded)  # b'SGVsbG8sIFdvcmxkIQ=='

decoded = base64.b64decode(encoded).decode('utf-8')
print(decoded)  # Hello, World!

# URL-safe Base64
url_encoded = base64.urlsafe_b64encode(text.encode('utf-8'))
print(url_encoded)  # b'SGVsbG8sIFdvcmxkIQ=='

# 파일 인코딩 (이미지 등)
with open('image.png', 'rb') as f:
    image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode('ascii')

# 바이너리 데이터 직접 처리
binary_data = bytes([0xFF, 0xD8, 0xFF, 0xE0])  # JPEG 매직넘버
encoded_binary = base64.b64encode(binary_data)
print(encoded_binary)  # b'/9j/4A=='
```

Python의 `base64` 모듈은 `bytes` 타입을 받는다. 문자열을 넘기면 `TypeError`가 발생한다. `.encode('utf-8')`을 빼먹는 실수가 잦다.

### JavaScript (Node.js)

```javascript
// 인코딩
const text = 'Hello, World!';
const encoded = Buffer.from(text).toString('base64');
console.log(encoded); // SGVsbG8sIFdvcmxkIQ==

// 디코딩
const decoded = Buffer.from(encoded, 'base64').toString('utf8');
console.log(decoded); // Hello, World!

// Base64URL
const urlEncoded = Buffer.from(text).toString('base64url');
console.log(urlEncoded); // SGVsbG8sIFdvcmxkIQ
```

### JavaScript (브라우저)

```javascript
// 기본 인코딩/디코딩
const encoded = btoa('Hello, World!');
const decoded = atob(encoded);

// btoa는 Latin-1만 지원한다. 한글 같은 유니코드를 넣으면 에러 난다.
btoa('안녕하세요');  // InvalidCharacterError 발생

// 유니코드 처리: TextEncoder로 바이트 배열 변환 후 인코딩
function encodeUnicode(str) {
    const bytes = new TextEncoder().encode(str);
    const binString = Array.from(bytes, (byte) =>
        String.fromCodePoint(byte)
    ).join('');
    return btoa(binString);
}

function decodeUnicode(base64) {
    const binString = atob(base64);
    const bytes = Uint8Array.from(binString, (m) => m.codePointAt(0));
    return new TextDecoder().decode(bytes);
}

const encoded2 = encodeUnicode('안녕하세요');
const decoded2 = decodeUnicode(encoded2);
```

## Base64는 암호화가 아니다

실무에서 자주 보이는 오해다. Base64로 인코딩하면 사람이 바로 읽을 수 없으니까 "암호화된 것"이라고 착각하는 경우가 있다.

### 왜 암호화가 아닌가

- Base64에는 **키(key)가 없다**. 누구나 동일한 알고리즘으로 원본을 복원할 수 있다.
- 인코딩 알고리즘이 공개되어 있고, 모든 언어에 디코더가 내장되어 있다.
- 문자열 앞뒤의 `==` 패딩만 봐도 Base64라는 걸 바로 알 수 있다.

```python
import base64

# "비밀번호"를 Base64로 인코딩
secret = base64.b64encode("my_password_123".encode()).decode()
print(secret)  # bXlfcGFzc3dvcmRfMTIz

# 누구나 1초 만에 복원 가능
print(base64.b64decode(secret).decode())  # my_password_123
```

### 실제로 발생하는 보안 사고

- **설정 파일에 Base64로 인코딩한 DB 비밀번호 저장**: `.env`나 `application.yml`에 Base64로 인코딩한 값을 넣어두고 "암호화했다"고 생각하는 경우. Git 히스토리에 남으면 그대로 노출된다.
- **API 응답에 민감 정보를 Base64로 전송**: 클라이언트 개발자 도구에서 바로 디코딩 가능하다.
- **JWT 페이로드를 비공개라고 착각**: JWT의 페이로드는 Base64URL 인코딩일 뿐이다. 서명(Signature)은 위변조 방지용이지 내용 은닉용이 아니다.

```bash
# JWT 페이로드 디코딩 - 터미널에서 한 줄이면 된다
echo "eyJ1c2VySWQiOjEyMywiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIn0" | base64 -d
# {"userId":123,"email":"test@test.com"}
```

민감한 데이터는 AES 같은 대칭 암호화나 RSA 같은 비대칭 암호화를 써야 한다. Base64는 전송 포맷이지 보안 수단이 아니다.

## 실전 예제

### JWT 토큰 구조

```javascript
// JWT는 Header.Payload.Signature 형태
// Header와 Payload는 Base64URL 인코딩이다 (표준 Base64 아님)
const header = { alg: 'HS256', typ: 'JWT' };
const payload = { userId: 123, exp: 1234567890 };

// Base64URL: 패딩 없음, +→-, /→_
const encodedHeader = Buffer.from(JSON.stringify(header))
    .toString('base64url');
const encodedPayload = Buffer.from(JSON.stringify(payload))
    .toString('base64url');

console.log(`${encodedHeader}.${encodedPayload}.signature`);
```

### Basic Authentication

```java
// HTTP Basic Auth: "username:password"를 Base64 인코딩
String credentials = "admin:secret123";
String encoded = Base64.getEncoder()
        .encodeToString(credentials.getBytes(StandardCharsets.UTF_8));

// Authorization: Basic YWRtaW46c2VjcmV0MTIz
// 다시 말하지만, 이건 암호화가 아니다. HTTPS 없이 쓰면 평문 전송과 다를 바 없다.
```

### 이미지 Data URL

```html
<!-- Base64로 인코딩된 이미지를 HTML에 직접 삽입 -->
<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA..." />
```

작은 아이콘(수 KB)에는 HTTP 요청을 줄이는 이점이 있다. 하지만 이미지가 크면 HTML 자체가 비대해지고 브라우저 캐싱도 안 되니까, 실제 이미지 파일로 분리하는 게 낫다.

## 디코딩 실패 트러블슈팅

Base64 디코딩이 실패하는 케이스는 패턴이 정해져 있다.

### 1. 잘못된 문자가 섞여 있는 경우

```
java.lang.IllegalArgumentException: Illegal base64 character 20
```

원인: 공백(ASCII 32, hex 0x20)이나 줄바꿈이 Base64 문자열에 포함되어 있다. HTTP 전송 과정에서 `+`가 공백으로 바뀌는 경우도 흔하다.

```java
// 해결: 공백, 줄바꿈 제거 후 디코딩
String dirty = "SGVsbG8s IFdvcm\nxkIQ==";
String cleaned = dirty.replaceAll("[\\s]", "");
byte[] decoded = Base64.getDecoder().decode(cleaned);
```

### 2. Base64URL과 표준 Base64 혼동

```python
import base64

# JWT에서 가져온 Base64URL 문자열
token_part = "eyJ1c2VySWQiOjEyM30"

# 표준 디코더로 디코딩하면 실패할 수 있다
# base64.b64decode(token_part)  # binascii.Error 발생 가능

# Base64URL 디코더를 써야 한다
decoded = base64.urlsafe_b64decode(token_part + "==")  # 패딩 복원 필요
print(decoded)  # b'{"userId":123}'
```

`-`와 `_`가 보이면 Base64URL이다. `+`와 `/`가 보이면 표준 Base64다. 디코더를 맞춰 써야 한다.

### 3. 패딩 누락

```javascript
// 패딩 없는 Base64 문자열
const noPadding = "SGVsbG8";

// Node.js Buffer는 패딩 없어도 처리한다 (관대한 파서)
Buffer.from(noPadding, 'base64').toString(); // "Hello"

// 하지만 Java 표준 디코더는 패딩을 요구한다
// Base64.getDecoder().decode("SGVsbG8");  // IllegalArgumentException
```

패딩 복원 로직:

```java
// 패딩 복원
String input = "SGVsbG8";
int paddingNeeded = (4 - input.length() % 4) % 4;
String padded = input + "=".repeat(paddingNeeded);
byte[] decoded = Base64.getDecoder().decode(padded);
```

### 4. 인코딩 불일치 (UTF-8 vs Latin-1)

```python
# 한글 데이터가 Base64로 인코딩되어 있는데 디코딩 후 깨지는 경우
encoded = "7ZWc6riA"  # "한글"을 UTF-8로 인코딩한 뒤 Base64

decoded_bytes = base64.b64decode(encoded)

# 잘못된 디코딩: Latin-1으로 해석
print(decoded_bytes.decode('latin-1'))  # íêµì  ← 깨짐

# 올바른 디코딩: UTF-8로 해석
print(decoded_bytes.decode('utf-8'))  # 한글
```

Base64 자체는 바이트를 텍스트로 바꾸는 것뿐이다. 원본 바이트가 어떤 문자 인코딩이었는지는 별도로 알아야 한다. 인코딩 정보가 없으면 UTF-8을 먼저 시도하고, 실패하면 다른 인코딩을 시도하는 수밖에 없다.

### 5. 대용량 데이터 메모리 문제

```java
// 수백 MB 파일을 한 번에 Base64 인코딩하면 OutOfMemoryError 발생
// 원본 + Base64 결과(33% 증가)가 동시에 메모리에 올라간다

// 해결: 스트림 기반 처리
import java.io.*;
import java.util.Base64;

InputStream input = new FileInputStream("large-file.bin");
OutputStream output = Base64.getEncoder().wrap(
        new FileOutputStream("output.b64"));

byte[] buffer = new byte[8192];
int bytesRead;
while ((bytesRead = input.read(buffer)) != -1) {
    output.write(buffer, 0, bytesRead);
}
output.close();
input.close();
```

## 성능 고려사항

| 항목 | 수치 | 비고 |
|------|------|------|
| 크기 증가율 | 33% | 3바이트 → 4문자 |
| 인코딩 속도 | 빠름 | 단순 비트 연산 |
| 메모리 사용 | 원본의 ~2.33배 | 원본 + 인코딩 결과 동시 보유 시 |

대용량 데이터를 다룰 때는 스트림 처리를 써야 한다. 위의 트러블슈팅 섹션 5번 참고.

## Base64 vs 다른 인코딩

| 인코딩 | 문자 수 | 크기 증가 | 주 사용처 |
|--------|---------|----------|----------|
| Base64 | 64 | 33% | 이메일, JWT, Data URL |
| Base32 | 32 | 60% | 대소문자 구분 불가 환경, TOTP |
| Base16 (Hex) | 16 | 100% | 디버깅, 해시값 표시 |
| Base85 (Ascii85) | 85 | 25% | PDF, Git 바이너리 패킹 |

## 참고

- RFC 4648 - The Base16, Base32, and Base64 Data Encodings
- RFC 2045 - MIME Part One (Base64 Content-Transfer-Encoding)
- [MDN - btoa()](https://developer.mozilla.org/en-US/docs/Web/API/btoa)
- [Java Base64 API](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Base64.html)
- [Python base64 모듈](https://docs.python.org/3/library/base64.html)
