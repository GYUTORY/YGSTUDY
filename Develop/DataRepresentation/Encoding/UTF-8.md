---
title: UTF-8 심화
tags: [utf-8, encoding, security, overlong-encoding, replacement-character, json, rfc-8259, chardet, java, python, go, postgresql, sqlite, redis]
updated: 2026-08-05
---

# UTF-8 심화

## 유효하지 않은 바이트 시퀀스와 U+FFFD

UTF-8 바이트 시퀀스는 형식이 엄격하다. 멀티바이트 문자의 첫 바이트와 연속 바이트는 각각 정해진 비트 패턴을 따라야 한다.

```
첫 바이트:    0xxxxxxx (1바이트), 110xxxxx (2바이트 시작), 1110xxxx (3바이트 시작), 11110xxx (4바이트 시작)
연속 바이트:  10xxxxxx
```

이 패턴을 벗어난 바이트를 만나면 파서는 U+FFFD(REPLACEMENT CHARACTER, '?')를 삽입한다. 발생 조건별로 정리하면:

- **연속 바이트 누락**: `ED 55`처럼 3바이트 첫 바이트(0xED) 뒤에 10xxxxxx 패턴이 아닌 값이 오면, 0xED를 유효하지 않은 바이트로 처리하고 U+FFFD를 삽입한 뒤 0x55부터 다시 파싱한다.
- **고립된 연속 바이트**: 0x80~0xBF 범위의 바이트가 첫 바이트 없이 단독으로 나타나면 U+FFFD로 대체한다.
- **허용되지 않는 바이트**: 0xC0, 0xC1, 0xF5~0xFF는 UTF-8에서 절대 나타날 수 없는 값이다. 이 바이트들도 U+FFFD로 처리한다.
- **서로게이트 코드 포인트**: U+D800~U+DFFF는 서로게이트 영역으로 예약된 범위라 UTF-8로 직접 인코딩할 수 없다. 이 범위에 해당하는 3바이트 시퀀스(0xED 0xA0~0xBF 0x80~0xBF)는 유효하지 않은 시퀀스로 거부한다.

```python
data = b'\xed\xa0\x80'  # 서로게이트 D800의 UTF-8 표현 시도

data.decode('utf-8', errors='strict')        # UnicodeDecodeError
data.decode('utf-8', errors='replace')       # '\ufffd\ufffd\ufffd' (3개의 U+FFFD)
data.decode('utf-8', errors='ignore')        # '' (바이트를 버림)
data.decode('utf-8', errors='surrogateescape')  # '\udced\udca0\udc80' (PEP 383 방식)
```

U+FFFD가 원본 데이터에 있는 건지 파싱 과정에서 생긴 건지 구분하기 어렵다. 원본 바이트를 보존해야 한다면 디코딩 전에 바이트 레벨에서 유효성 검사를 먼저 해야 한다.

---

## 오버롱 인코딩(Overlong Encoding)

UTF-8은 각 코드 포인트 범위에 대해 최소 바이트 수만 허용한다. 더 긴 시퀀스로 같은 코드 포인트를 표현하는 것이 오버롱 인코딩이다.

'/'(U+002F)는 원래 1바이트(0x2F)로 표현한다. 같은 코드 포인트를 2바이트나 3바이트로도 표현할 수 있다:

```
정상:          0x2F         = 0 0101111
오버롱 2바이트: 0xC0 0xAF   = 110 00000  10 101111
오버롱 3바이트: 0xE0 0x80 0xAF = 1110 0000  10 000000  10 101111
```

세 표현 모두 디코딩하면 '/'가 나온다. RFC 3629(2003년) 이전에는 오버롱 시퀀스가 허용되었고, 초기 UTF-8 파서들이 이를 정상으로 처리했다.

### 실제 공격 사례

2001년 Apache HTTP Server의 디렉터리 트래버설 취약점(CVE-2001-0333)이 이 방식을 이용했다. 파일 경로에서 `../`을 차단하는 로직이 ASCII 0x2F(/)와 0x2E(.)만 검사하고 오버롱 인코딩은 걸러내지 못했다.

```
정상 요청:  /cgi-bin/../../../etc/passwd  → 차단됨
우회 요청:  /cgi-bin/%c0%ae%c0%ae/etc/passwd  → 통과됨
```

%c0%ae는 0xC0 0xAE, '.'(U+002E)의 오버롱 2바이트 표현이다. URL 디코더가 바이트를 먼저 복원하고, 그 바이트를 UTF-8 파서가 디코딩하는 2단계 구조에서 파일 경로 검사가 첫 단계(URL 디코딩) 이후에만 실행되었다.

Microsoft IIS에서도 비슷한 취약점이 발견되었다. 오버롱 시퀀스로 인코딩된 `\`가 디렉터리 구분자로 해석된 경우였다.

현재 표준(RFC 3629)은 오버롱 인코딩을 유효하지 않은 시퀀스로 정의한다. 모던 파서는 오버롱 시퀀스를 거부하거나 U+FFFD로 대체한다. 경로 처리 로직을 직접 구현하는 경우, 정규화 전에 검사하는 게 아니라 정규화 후에 검사해야 한다는 원칙은 여전히 중요하다.

```python
import os

def safe_path(base: str, user_input: str) -> str:
    path = os.path.normpath(os.path.join(base, user_input))
    if not path.startswith(base):
        raise ValueError("경로 트래버설 감지")
    return path
```

---

## JSON RFC 8259와 UTF-8

RFC 8259(2017년)는 JSON 텍스트를 UTF-8로 인코딩해야 한다고 명시한다. 이전 스펙(RFC 4627)에서는 UTF-16, UTF-32도 허용했다.

```
RFC 8259, Section 8.1:
"JSON text exchanged between systems that are not part of a closed ecosystem
MUST be encoded using UTF-8."
```

UTF-16이나 UTF-32로 인코딩된 JSON을 받아서 처리해야 하는 경우는 내부 시스템 연동 외에는 거의 없다. 외부 API 응답이 UTF-8이 아니면 해당 API가 구형 스펙을 따르는 것이다.

### 파서별 BOM 처리

UTF-8 BOM(EF BB BF)이 JSON 파일 앞에 붙어 있을 때 파서별 동작이 다르다.

```python
# Python json 모듈 — BOM 있으면 JSONDecodeError
import json

with open('data.json', 'rb') as f:
    raw = f.read()

if raw.startswith(b'\xef\xbb\xbf'):
    raw = raw[3:]

data = json.loads(raw.decode('utf-8'))

# encoding='utf-8-sig'를 쓰면 BOM을 자동으로 제거한다
with open('data.json', 'r', encoding='utf-8-sig') as f:
    data = json.load(f)
```

```java
// Jackson — 파일 객체로 파싱할 때는 BOM 자동 처리
ObjectMapper mapper = new ObjectMapper();
mapper.readValue(new File("data.json"), MyClass.class);  // BOM 있어도 정상 동작

// 바이트 배열에서 직접 파싱하면 BOM을 제거해야 한다
byte[] bytes = Files.readAllBytes(Path.of("data.json"));
if (bytes.length >= 3 && bytes[0] == (byte)0xEF && bytes[1] == (byte)0xBB && bytes[2] == (byte)0xBF) {
    bytes = Arrays.copyOfRange(bytes, 3, bytes.length);
}
```

```go
// encoding/json — BOM 자동 처리 없음
// json.Unmarshal에 BOM 포함된 바이트를 넣으면 에러
import "bytes"

data, _ := os.ReadFile("data.json")
if bytes.HasPrefix(data, []byte{0xEF, 0xBB, 0xBF}) {
    data = data[3:]
}
var result map[string]interface{}
json.Unmarshal(data, &result)
```

Node.js의 `JSON.parse()`는 BOM이 있는 문자열을 에러 없이 파싱한다. 하지만 `fs.readFileSync`로 파일을 `encoding: 'utf8'` 옵션과 함께 읽으면 BOM이 문자열 맨 앞에 그대로 남아있다. 이 문자열을 HTTP 응답으로 내보내면 BOM이 클라이언트에 노출된다.

### 서로게이트 페어의 JSON 직렬화

JSON spec은 문자열 안에 서로게이트 코드 포인트를 `\uXXXX` 형태로 허용한다. 그 때문에 유효하지 않은 유니코드가 JSON을 통해 전달되는 경우가 생긴다.

```javascript
const invalid = '\uD800';  // 하이 서로게이트 단독
JSON.stringify(invalid);   // '"\ud800"' — 직렬화됨
```

Python에서 이를 파싱하면 `json.JSONDecodeError`가 발생하거나 `surrogateescape` 에러가 발생한다. 구현마다 동작이 다르다. 외부에서 받은 JSON에 `\uD800~\uDFFF` 범위의 이스케이프가 있으면 언어별로 처리 결과가 달라진다. API를 통해 사용자 입력을 JSON으로 받을 때 이 범위를 사전에 차단하거나 정규화하지 않으면 DB 저장이나 다른 시스템 전달에서 예상치 못한 에러가 발생한다.

---

## 인코딩 미지정 바이트스트림의 UTF-8 판별

인코딩이 명시되지 않은 바이트스트림이 들어올 때 UTF-8인지 판별하는 방법이 몇 가지 있다.

### file 명령

```bash
file -bi data.txt
# text/plain; charset=utf-8
# text/plain; charset=iso-8859-1
# text/plain; charset=unknown-8bit
```

`file` 명령은 파일 앞부분의 바이트 패턴을 검사한다. UTF-8 유효성 검사를 수행해서 모든 멀티바이트 시퀀스가 올바르면 utf-8로 보고한다. 파일 전체를 항상 읽지는 않아서 큰 파일의 뒷부분에 있는 유효하지 않은 시퀀스를 놓칠 수 있다.

### chardet

```python
import chardet

with open('unknown.txt', 'rb') as f:
    raw = f.read()

result = chardet.detect(raw)
print(result)
# {'encoding': 'EUC-KR', 'confidence': 0.99, 'language': 'Korean'}
# {'encoding': 'UTF-8-SIG', 'confidence': 1.0, 'language': ''}

if result['confidence'] < 0.7:
    # 판별 신뢰도가 낮다 — 수동 확인이 필요하다
    pass
```

chardet는 통계 기반 휴리스틱을 쓴다. 텍스트가 짧거나 ASCII만 있으면 신뢰도가 낮게 나온다. ASCII만으로 구성된 파일은 UTF-8인지 EUC-KR인지 구분할 수 없다(둘 다 유효한 파싱 결과를 낸다).

`charset-normalizer`가 chardet의 대안으로 많이 쓰인다. 알고리즘이 달라서 같은 파일에 대해 다른 결과를 낼 수 있으므로 프로젝트마다 하나를 선택해서 일관되게 쓰는 게 낫다.

### hex 패턴 분석

UTF-8의 특성상 바이트 패턴만 봐도 인코딩을 추정할 수 있다.

```bash
hexdump -C data.txt | head -5
```

```
# 한글이 있는 UTF-8 파일
00000000  ed 95 9c ea b8 80 0a  |.......|
          ^^^                   0xEA~0xED로 시작하는 3바이트 시퀀스 (한글 U+AC00~U+D7A3 범위)

# EUC-KR 파일
00000000  c7 d1 b1 db 0a  |.....|
          ^^^              0xA1~0xFE 범위의 2바이트 쌍
```

UTF-8 한글의 첫 바이트는 0xEA, 0xEB, 0xEC, 0xED다. EUC-KR 한글은 0xA1~0xFE 범위의 2바이트 쌍이다. 0x80~0x9F 범위 바이트가 없고 0xA1 이상의 바이트가 주를 이루면 EUC-KR로 의심한다.

```python
def is_valid_utf8(data: bytes) -> bool:
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False

# 유효하지 않은 바이트 위치 확인
def find_invalid_position(data: bytes) -> int | None:
    try:
        data.decode('utf-8')
        return None
    except UnicodeDecodeError as e:
        return e.start
```

---

## Java: String.getBytes()와 JVM 기본 인코딩

`String.getBytes()`를 charset 없이 호출하면 JVM 기본 인코딩을 사용한다.

```java
// 위험한 코드
byte[] bytes = someString.getBytes();  // JVM 기본값에 의존

// JVM 기본값은 시작 옵션으로 바뀐다
// java -Dfile.encoding=UTF-8 MyApp
// java -Dfile.encoding=EUC-KR MyApp  ← 결과가 달라진다
```

Linux 서버는 보통 UTF-8이라서 로컬에서 잘 되던 코드가 AWS EC2 인스턴스에서 깨지는 경우는 드물다. 하지만 Jenkins 빌드 서버, Docker 이미지, `LC_ALL`이나 `LANG`이 설정되지 않은 레거시 서버에서는 US-ASCII나 LATIN-1이 기본값이 된다.

Java 17까지는 `file.encoding`이 JVM 기본 charset을 제어했다. Java 18에서 기본값이 UTF-8로 변경되었다(JEP 400). Java 18 미만 환경에서는 항상 charset을 명시해야 한다.

```java
// charset 명시
byte[] bytes = someString.getBytes(StandardCharsets.UTF_8);
String str = new String(bytes, StandardCharsets.UTF_8);

// FileWriter도 마찬가지 (Java 11+)
new FileWriter("file.txt", StandardCharsets.UTF_8);
```

`InputStreamReader`, `OutputStreamWriter`, `FileReader`, `FileWriter`, `PrintStream`도 charset 없이 생성하면 JVM 기본값을 따른다. `FileReader`는 Java 11 이전에는 charset을 지정하는 생성자가 없었다.

```java
// Java 11 이전
BufferedReader reader = new BufferedReader(
    new InputStreamReader(new FileInputStream("file.txt"), StandardCharsets.UTF_8)
);

// Java 11+
BufferedReader reader = new BufferedReader(new FileReader("file.txt", StandardCharsets.UTF_8));
```

JVM 기본 charset 확인은 `Charset.defaultCharset()`으로 한다.

```java
System.out.println(Charset.defaultCharset());
// UTF-8 또는 다른 값
```

---

## Python: open()과 기본 인코딩

Python 3의 `open()`에서 `encoding`을 생략하면 `locale.getpreferredencoding(False)`를 사용한다.

```python
import locale
locale.getpreferredencoding(False)
# Linux:   'UTF-8'
# Windows: 'cp949' (한국어 시스템 기준)
```

Windows 한국어 환경에서 encoding을 생략하면 cp949가 기본이 되어 UTF-8 파일 읽기가 깨진다. Linux CI 환경에서는 UTF-8이 기본이라 CI를 통과하다가 Windows 사용자가 실행하면 에러가 나는 패턴이 자주 발생한다.

```python
# 잘못된 패턴
with open('data.txt') as f:         # Windows에서 cp949로 읽는다
    content = f.read()

# 올바른 패턴
with open('data.txt', encoding='utf-8') as f:
    content = f.read()

# BOM 있는 파일
with open('data.txt', encoding='utf-8-sig') as f:
    content = f.read()
```

Python 3.10부터 `PYTHONUTF8=1` 환경변수 또는 `-X utf8` 플래그로 UTF-8 모드를 활성화할 수 있다.

```bash
PYTHONUTF8=1 python my_script.py
python -X utf8 my_script.py
```

파이프로 연결된 경우 `sys.stdout.encoding`이 ASCII가 될 수 있다. 이 상황에서 한글을 출력하면 `UnicodeEncodeError`가 발생한다.

```python
import sys
sys.flags.utf8_mode  # UTF-8 모드 활성화 여부 (1 = 활성화)

# stdout 인코딩 강제 설정
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
# 또는 환경변수: PYTHONIOENCODING=utf-8
```

---

## Go의 utf8 패키지

Go의 `string`은 UTF-8 바이트 시퀀스이지만 컴파일러가 유효성을 보장하지 않는다. 외부에서 받은 바이트를 `string`으로 변환하면 유효하지 않은 UTF-8 시퀀스가 들어갈 수 있다.

```go
import "unicode/utf8"

// UTF-8 유효성 검사
s := string([]byte{0xED, 0xA0, 0x80})  // 서로게이트 영역 바이트
utf8.ValidString(s)  // false

// 바이트 슬라이스 유효성 검사
b := []byte{0xED, 0xA0, 0x80}
utf8.Valid(b)  // false
```

`utf8.RuneError`(U+FFFD, rune 값으로 `'\uFFFD'`)는 `range` 루프에서 유효하지 않은 바이트를 만났을 때 반환된다.

```go
s := string([]byte{0xED, 0xA0, 0x80})  // 유효하지 않은 UTF-8

for i, r := range s {
    fmt.Printf("byte offset %d: rune %U\n", i, r)
}
// byte offset 0: rune U+FFFD
// byte offset 1: rune U+FFFD
// byte offset 2: rune U+FFFD
```

`range`로 순회할 때 유효하지 않은 바이트 하나당 U+FFFD 하나가 나온다. 하지만 이게 원본 데이터에 U+FFFD가 있는 건지 파싱 오류인지 구분이 안 된다. `utf8.ValidString()`으로 먼저 확인한다.

유효하지 않은 시퀀스 처리:

```go
import (
    "strings"
    "unicode/utf8"
)

// 유효하지 않은 시퀀스 제거 (Go 1.13+)
func removeInvalidUTF8(s string) string {
    return strings.ToValidUTF8(s, "")
}

// 대체 문자로 교체
func replaceInvalidUTF8(s string) string {
    return strings.ToValidUTF8(s, "\uFFFD")
}
```

`encoding/json`은 유효하지 않은 UTF-8을 포함한 문자열을 마샬링하면 에러를 낸다.

```go
type Response struct {
    Name string `json:"name"`
}

r := Response{Name: string([]byte{0xED, 0xA0, 0x80})}
_, err := json.Marshal(r)
// err: json: invalid UTF-8 in string literal
```

외부 HTTP API 응답이나 DB에서 읽은 데이터를 JSON으로 직렬화하기 전에 `utf8.ValidString()`을 거치는 것이 안전하다.

---

## DB별 UTF-8 처리

### PostgreSQL

PostgreSQL은 데이터베이스 생성 시 인코딩을 지정한다. 한번 설정하면 변경이 어렵다.

```sql
CREATE DATABASE mydb
    WITH ENCODING 'UTF8'
    LC_COLLATE 'ko_KR.UTF-8'
    LC_CTYPE 'ko_KR.UTF-8';
```

`UTF8` 인코딩 데이터베이스는 4바이트 유니코드를 그대로 저장한다. MySQL의 utf8 제한(3바이트)이 없어서 이모지도 별도 설정 없이 저장된다.

클라이언트 연결 인코딩은 데이터베이스 인코딩과 별개다.

```sql
SHOW client_encoding;         -- 현재 클라이언트 인코딩
SET client_encoding TO 'UTF8';
```

클라이언트가 EUC-KR인데 데이터베이스가 UTF-8이면 PostgreSQL이 자동 변환한다. 자동 변환이 실패하면 쿼리 에러가 발생한다.

`text` 타입은 길이 제한이 없고 모든 유니코드 코드 포인트를 저장한다. `varchar(n)`의 n은 바이트 수가 아니라 문자 수다. 한글 255자와 영문 255자가 같은 `varchar(255)` 컬럼에 들어간다. MySQL의 `utf8mb4` 인덱스 크기 제한 문제도 없다.

### SQLite

SQLite는 항상 UTF-8로 저장한다(기본값). 인코딩 설정이 따로 없고 모든 텍스트가 UTF-8이다.

```sql
PRAGMA encoding;
-- UTF-8
```

UTF-16 저장도 지원하지만 `CREATE DATABASE` 직후 첫 번째 `PRAGMA encoding = 'UTF-16'`으로만 변경 가능하다. 이미 데이터가 있으면 변경할 수 없다.

Python `sqlite3` 모듈은 Python `str`(유니코드)을 SQLite 텍스트로 투명하게 변환한다.

```python
import sqlite3

conn = sqlite3.connect('data.db')
conn.execute("INSERT INTO t VALUES (?)", ('한글 테스트',))
conn.commit()

row = conn.execute("SELECT * FROM t").fetchone()
type(row[0])  # <class 'str'>
```

SQLite 문자열 비교는 기본적으로 바이너리(바이트 단위 비교)다. `COLLATE NOCASE`는 ASCII 대소문자만 처리하고 유니코드 폴딩은 하지 않는다. 유니코드 정규화 기반 비교가 필요하면 ICU extension을 별도로 로드해야 한다.

### Redis

Redis는 문자열 값에 대해 문자 인코딩 개념이 없다. 바이트 배열을 그대로 저장한다. 클라이언트가 UTF-8로 보내면 UTF-8 바이트로, EUC-KR로 보내면 EUC-KR 바이트로 저장되고 Redis 서버는 이를 구분하지 않는다.

```python
import redis

# decode_responses=True: 받은 바이트를 UTF-8로 디코딩해서 str으로 반환
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
r.set('key', '한글')
value = r.get('key')   # '한글' (str)

# decode_responses=False: 바이트 그대로 반환
r2 = redis.Redis(host='localhost', port=6379, decode_responses=False)
value2 = r2.get('key')  # b'\xed\x95\x9c\xea\xb8\x80' (bytes)
```

`decode_responses=True`를 쓸 때 저장된 값이 UTF-8이 아니면 `UnicodeDecodeError`가 발생한다. 여러 언어로 작성된 서비스가 같은 Redis를 공유하면 인코딩 약속을 명시적으로 관리해야 한다.

`STRLEN` 명령은 문자 수가 아닌 바이트 수를 반환한다.

```
SET key "한글"
STRLEN key   → 6  (한글 1자 = 3바이트, 2자 = 6바이트)
```

Java redis 클라이언트 Jedis와 Lettuce는 기본적으로 UTF-8로 직렬화/역직렬화한다. 클라이언트 기본값을 바꾸지 않는 한 UTF-8이 보장된다.

`OBJECT ENCODING key` 명령은 내부 데이터 구조 인코딩(int, embstr, raw 등)을 반환하는 것으로 문자 인코딩과 무관하다.
