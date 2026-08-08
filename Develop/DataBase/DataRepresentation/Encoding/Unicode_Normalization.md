---
title: 유니코드 정규화 (Unicode Normalization)
tags: [rdbms, database, security]
updated: 2026-08-05
---

# 유니코드 정규화

같은 문자를 바이트 수준에서 다르게 표현할 수 있다는 것이 정규화 문제의 핵심이다. '가'는 완성형 코드 포인트(U+AC00) 하나로 표현할 수도 있고, 초성 ㄱ(U+1100)과 중성 ㅏ(U+1161) 두 코드 포인트로 표현할 수도 있다. 화면에 보이는 결과는 같지만 바이트가 다르다. `str1 === str2`는 false다.

## NFC / NFD / NFKC / NFKD 차이

### NFD (Canonical Decomposition)

조합된 문자를 기저 문자와 결합 문자(diacritic)로 분해한다.

```
é (U+00E9)  →  e (U+0065) + ◌́ (U+0301)
가 (U+AC00)  →  ㄱ (U+1100) + ㅏ (U+1161)
```

### NFC (Canonical Decomposition, then Canonical Composition)

NFD로 분해한 뒤 다시 조합한다. 결합 문자 시퀀스를 미리 조합된 단일 코드 포인트로 바꾼다.

```
e (U+0065) + ◌́ (U+0301)  →  é (U+00E9)
ㄱ (U+1100) + ㅏ (U+1161)  →  가 (U+AC00)
```

### NFKD / NFKC

K(Compatibility) 분해를 추가한다. 시각적으로 비슷하지만 의미상 다른 문자들을 표준 형태로 변환한다. NFKD는 분해만, NFKC는 호환성 분해 후 재조합한다.

```
① (U+2460)       →  1 (U+0031)
ＡＢＣ (전각)      →  ABC (반각)
½ (U+00BD)       →  1/2 (세 글자)
㎡ (U+33A1)       →  m² (세 글자)
fi (리가처 U+FB01) →  fi (두 글자)
```

NFKC/NFKD는 정보를 손실한다. 분해 후 원래 형태로 복원이 불가능하다.

## 선택 기준

대부분의 경우 NFC를 쓴다. 웹, DB, API 간 데이터를 주고받을 때 NFC로 통일하면 비교 로직이 단순해진다. HTTP/JSON API 스펙 대부분이 NFC를 기본으로 가정한다.

NFD는 macOS HFS+ 파일 시스템이 파일명에 강제로 적용한다. 파일명을 다루는 코드에서 NFD를 만나는 상황은 이 경우가 대부분이다.

NFKC는 검색 엔진 인덱싱, 사용자 입력 정규화, 보안 필터링에 쓴다. '①'과 '1', 전각 공백과 반각 공백을 같은 것으로 취급하거나, 전각 문자를 이용한 필터 우회를 막을 때 필요하다. 정보 손실이 있으므로 원본 표시용 데이터에는 적용하면 안 된다.

---

## macOS / Linux 파일명 불일치

HFS+(macOS 기본 파일 시스템)는 파일명을 NFD로 강제 변환해서 저장한다. ext4(Linux)는 입력받은 바이트를 그대로 저장한다. 같은 '가.txt'를 만들어도 OS마다 파일명 바이트가 다르다.

```
macOS HFS+  →  ㄱ + ㅏ (NFD, 6바이트: E1 84 80 E1 85 A1)
Linux ext4  →  가 (NFC, 3바이트: EA B0 80)
```

Git 저장소를 macOS-Linux 환경에서 공유할 때 이 문제가 생긴다. macOS에서 한글 파일명 파일을 커밋하면 Git이 NFD 바이트로 추적한다. Linux에서 체크아웃하면 NFD 바이트로 파일명이 생성되는데, NFC 파일명을 기대하는 스크립트나 툴이 "파일 없음" 에러를 낸다.

```bash
# macOS에서 저장소 설정
git config core.precomposeUnicode true
```

`core.precomposeUnicode`를 true로 설정하면 Git이 HFS+의 NFD 파일명을 NFC로 변환해서 인덱스에 저장한다. macOS와 Linux를 섞어 쓰는 팀은 저장소 `.git/config`에 이 설정을 넣어두는 게 낫다.

파일명을 프로그래밍으로 비교하는 코드에서는 명시적으로 정규화해야 한다.

```python
import unicodedata
import os

def normalize_path(path: str) -> str:
    return unicodedata.normalize('NFC', path)

# macOS에서 os.listdir()로 받은 파일명이 NFD일 수 있음
for filename in os.listdir('.'):
    nfc_filename = normalize_path(filename)
    if nfc_filename == '가.txt':
        print("found")
```

---

## DB 검색 불일치 버그

사용자 입력이 NFD고 DB에 저장된 데이터가 NFC면 `=` 비교가 실패한다.

```sql
-- DB에 저장된 값: NFC '가' (3바이트: EA B0 80)
-- 검색 입력: NFD '가' (6바이트: E1 84 80 E1 85 A1)
SELECT * FROM users WHERE name = '가';  -- 결과 없음
```

PostgreSQL은 바이트 비교로 처리한다. 같은 문자가 정규화 형식만 달라도 다른 값으로 취급한다. MySQL의 `utf8mb4_unicode_ci` 콜레이션도 정규화를 자동으로 맞춰주지 않는다.

버그 리포트가 들어오는 전형적인 시나리오는 이렇다. macOS 사용자가 한글 이름을 입력하면 HFS+가 NFD로 변환한다. 서버에서 정규화 없이 DB에 저장하면 NFD로 쌓인다. 나중에 다른 클라이언트(Linux, Windows)에서 같은 이름으로 검색하면 NFC로 전송돼서 결과가 없다.

입력을 받는 시점에 NFC로 정규화하면 이 문제가 사라진다.

```python
import unicodedata

def normalize_text(text: str) -> str:
    return unicodedata.normalize('NFC', text)

@app.post("/users")
async def create_user(body: UserBody):
    name = normalize_text(body.name)
    email = normalize_text(body.email).lower()
    await db.insert(name=name, email=email)
```

기존 DB 데이터에 NFC/NFD가 혼재하면 마이그레이션이 필요하다.

```sql
-- PostgreSQL (pg_unicode_normalize 함수, 버전 13+)
UPDATE users
SET name = normalize(name, NFC)
WHERE name IS DISTINCT FROM normalize(name, NFC);
```

---

## 비밀번호 해싱 전 정규화

같은 문자로 보이는 비밀번호가 정규화 형식에 따라 다른 바이트 시퀀스가 된다. 해싱 전에 정규화하지 않으면 같은 비밀번호인데 로그인이 실패하는 상황이 생긴다.

시나리오: 사용자가 'paßwörd'로 비밀번호를 설정한다. 가입 시 클라이언트 A가 NFC로 전송하면 서버는 NFC 바이트를 해싱해서 저장한다. 로그인 시 클라이언트 B가 NFD로 전송하면 해시가 달라서 인증 실패가 난다. 사용자는 비밀번호를 올바르게 입력했다고 생각하는데 로그인이 안 되는 상황이다.

```python
import unicodedata
import bcrypt

def hash_password(password: str) -> bytes:
    # 해싱 전 NFKC로 정규화
    normalized = unicodedata.normalize('NFKC', password)
    return bcrypt.hashpw(normalized.encode('utf-8'), bcrypt.gensalt())

def verify_password(password: str, hashed: bytes) -> bool:
    normalized = unicodedata.normalize('NFKC', password)
    return bcrypt.checkpw(normalized.encode('utf-8'), hashed)
```

비밀번호에 NFC가 아닌 NFKC를 쓰는 이유가 있다. '①'과 '1', 전각·반각 영문자를 같은 문자로 취급해서 예측 불가능한 비밀번호 변형을 차단한다. RFC 7613(Precis 프레임워크)에서 비밀번호 처리 시 NFKC 기반 정규화를 권고한다.

레거시 시스템에서 해싱 전 정규화를 하지 않았다면, 기존 사용자 비밀번호를 건드리지 않고 재로그인 시 정규화된 해시로 교체하는 방식으로 마이그레이션한다.

---

## NFKC와 보안: 전각 문자 필터 우회

NFKC를 적용하지 않으면 전각 문자를 이용한 필터 우회가 가능하다.

'SELECT'를 블랙리스트로 막는 SQL 인젝션 필터가 있다고 가정한다.

```python
# 취약한 필터
def check_sql_injection(text: str) -> bool:
    return 'SELECT' in text.upper()

check_sql_injection('ＳＥＬＥＣＴ * FROM users')  # False → 통과
```

전각 라틴 문자 `ＳＥＬＥＣＴ`(U+FF33 U+FF25 U+FF2C U+FF25 U+FF23 U+FF34)는 NFC/NFD 정규화를 해도 전각 그대로다. 블랙리스트가 반각 'SELECT'만 막으면 전각으로 우회된다. DB 드라이버나 ORM이 전각 문자를 SQL로 해석하는 상황이면 공격이 성립한다.

```python
import unicodedata

def check_sql_injection_safe(text: str) -> bool:
    # 필터링 전 NFKC 정규화
    normalized = unicodedata.normalize('NFKC', text)
    keywords = ['SELECT', 'DROP', 'INSERT', 'UPDATE', 'DELETE', 'UNION']
    upper = normalized.upper()
    return any(kw in upper for kw in keywords)

check_sql_injection_safe('ＳＥＬＥＣＴ * FROM users')  # True → 차단
```

비슷한 문제로 유니코드 동형이의 문자(homograph) 공격이 있다. 키릴 문자 'а'(U+0430)는 라틴 'a'(U+0061)와 시각적으로 동일하다. 'аdmin'(키릴 а + 라틴 dmin)은 'admin' 필터를 통과한다. NFKC는 이 케이스를 처리하지 못한다. 동형이의 문자 방어는 별도 Unicode Confusables 처리가 필요하다.

---

## 언어별 정규화 API

### Python

```python
import unicodedata

text = 'e\u0301'  # e + 결합 악센트 (NFD 형태)

unicodedata.normalize('NFC', text)   # 'é' (U+00E9)
unicodedata.normalize('NFD', text)   # 'e\u0301'
unicodedata.normalize('NFKC', text)  # 'é'
unicodedata.normalize('NFKD', text)  # 'e\u0301'

# 정규화 여부 확인 (Python 3.8+)
unicodedata.is_normalized('NFC', 'é')       # True
unicodedata.is_normalized('NFC', 'e\u0301') # False
```

### Java

```java
import java.text.Normalizer;

String nfd = "e\u0301";  // e + 결합 악센트

String nfc  = Normalizer.normalize(nfd, Normalizer.Form.NFC);
String nfkc = Normalizer.normalize(nfd, Normalizer.Form.NFKC);

// 정규화 여부 확인
boolean isNFC = Normalizer.isNormalized(nfd, Normalizer.Form.NFC);  // false
```

### Go

표준 라이브러리에 정규화 API가 없다. `golang.org/x/text/unicode/norm` 패키지를 써야 한다.

```go
import "golang.org/x/text/unicode/norm"

nfd := "e\u0301"

nfc  := norm.NFC.String(nfd)
nfkc := norm.NFKC.String(nfd)

// 바이트 슬라이스
nfcBytes := norm.NFC.Bytes([]byte(nfd))

// 정규화 여부 확인
isNFC := norm.NFC.IsNormalString(nfd)  // false

// io.Writer 래핑 (스트림 정규화)
w := norm.NFC.Writer(os.Stdout)
fmt.Fprint(w, nfd)
w.(io.Closer).Close()
```

### JavaScript

```javascript
const nfd = 'e\u0301';  // e + 결합 악센트

nfd.normalize('NFC');   // 'é'
nfd.normalize('NFD');   // 'e\u0301'
nfd.normalize('NFKC');  // 'é'
nfd.normalize('NFKD');  // 'e\u0301'

// 인수 없으면 NFC (기본값)
nfd.normalize();  // 'é'

// 정규화 여부 확인
nfd === nfd.normalize('NFC');  // false
```

ES2015부터 브라우저와 Node.js 모두 `String.prototype.normalize()`를 지원한다. Internet Explorer는 지원하지 않는다.

---

## 입력 처리 시 정규화 시점

정규화는 입력이 시스템 경계를 넘어오는 시점에 한 번 한다. API 엔드포인트, 폼 제출, 파일 업로드 처리 시점이다.

입력 → 정규화 → 저장 → 출력 순서로 저장 전 한 번만 처리하는 게 원칙이다. 저장 후 읽을 때마다 정규화하면 쿼리마다 비용이 추가되고, 인덱스가 정규화된 값과 달라서 인덱스를 못 쓴다.

```python
# 저장 전 정규화 (권장)
class UserService:
    def create_user(self, name: str, email: str, password: str):
        name = unicodedata.normalize('NFC', name)
        email = unicodedata.normalize('NFC', email).lower()
        password_hash = hash_password(password)  # 내부에서 NFKC 정규화
        return self.db.insert(name=name, email=email, password_hash=password_hash)

# 조회 시마다 정규화 (비권장: 인덱스를 못 쓴다)
def find_user_bad(self, name: str):
    return self.db.query(
        "SELECT * FROM users WHERE normalize(name, 'NFC') = $1", name
    )
```

기존 DB에 정규화 전 데이터가 쌓여 있으면, 마이그레이션 스크립트로 전체 정규화한 후 애플리케이션 레이어 정규화를 추가하는 순서로 진행한다.

정규화 형식은 나중에 바꾸기 어렵다. 처음부터 결정해야 한다. 특별한 이유 없으면 NFC를 쓰고, 비밀번호에는 NFKC, 보안 필터링에는 NFKC를 추가 적용한다.
