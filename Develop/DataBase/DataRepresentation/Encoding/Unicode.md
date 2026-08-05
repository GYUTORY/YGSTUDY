---
title: 유니코드 (Unicode)
tags: [unicode, utf-8, utf-16, utf-32, encoding, surrogate-pair, normalization, emoji, collation]
updated: 2026-08-05
---

# 유니코드 (Unicode)

## 코드 포인트 구조

유니코드는 전 세계 모든 문자에 고유 번호를 부여하는 표준이다. 이 번호를 코드 포인트(code point)라고 하고, `U+XXXX` 형태로 표기한다. `U+0041`은 대문자 A, `U+AC00`은 한글 '가'다.

코드 포인트는 U+0000부터 U+10FFFF까지 총 1,114,112개다. 이 범위를 17개 플레인(plane)으로 나눈다. 플레인 하나당 65,536개(0x10000개)의 코드 포인트를 담는다.

```
플레인 0: U+0000 ~ U+FFFF   (BMP, Basic Multilingual Plane)
플레인 1: U+10000 ~ U+1FFFF (SMP, Supplementary Multilingual Plane)
플레인 2: U+20000 ~ U+2FFFF (SIP, Supplementary Ideographic Plane)
플레인 3~13: 현재 대부분 미할당
플레인 14: U+E0000 ~ U+EFFFF (SSP, 태그 문자)
플레인 15~16: 사용자 정의 영역 (PUA)
```

실무에서 BMP와 SMP 구분이 중요한 이유는 인코딩 방식에 따라 BMP 문자는 2바이트로 처리되지만 SMP 문자는 4바이트 또는 서로게이트 페어가 필요하기 때문이다. 이모지 대부분은 U+1F000대 이상이라 SMP에 속한다. 시스템이 BMP만 가정하고 짜여 있으면 이모지에서 터진다.

BMP 안에도 U+D800~U+DFFF 구간(2,048개)은 서로게이트 영역이라 일반 문자로 쓸 수 없다. 이 구간에 실제 문자를 배치하려 하면 인코딩 표준 위반이다.

---

## UTF-8, UTF-16, UTF-32 바이트 레벨

### UTF-8

가변 길이 인코딩이다. 코드 포인트 값 범위에 따라 1~4바이트를 쓴다.

```
U+0000 ~ U+007F   : 0xxxxxxx                          (1바이트)
U+0080 ~ U+07FF   : 110xxxxx 10xxxxxx                 (2바이트)
U+0800 ~ U+FFFF   : 1110xxxx 10xxxxxx 10xxxxxx        (3바이트)
U+10000 ~ U+10FFFF: 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx (4바이트)
```

한글 '가' (U+AC00)를 UTF-8로 인코딩하면:
```
U+AC00 = 1010 1100 0000 0000 (이진수)

3바이트 패턴: 1110xxxx 10xxxxxx 10xxxxxx
                   xxxx   xxxxxx   xxxxxx
             1110 1010  10 110000  10 000000
             = 0xEA    0xB0      0x80

결과: EA B0 80
```

UTF-8은 ASCII와 하위 호환된다. U+0000~U+007F는 UTF-8에서도 그대로 1바이트다. 이 때문에 레거시 ASCII 파일을 UTF-8 시스템에서 그냥 읽어도 깨지지 않는다.

멀티바이트 시퀀스의 첫 바이트는 항상 10xxxxxx 패턴이 아니다(연속 바이트는 10xxxxxx). 이 구조 덕분에 스트림 중간 어디서든 다음 문자 경계를 찾을 수 있다. 손상된 데이터에서 복구할 때 유용하다.

### UTF-16

BMP 문자는 2바이트, SMP 문자는 서로게이트 페어로 4바이트를 쓴다.

```
BMP (U+0000 ~ U+D7FF, U+E000 ~ U+FFFF): 코드 포인트를 그대로 2바이트로 저장
SMP (U+10000 ~ U+10FFFF): 서로게이트 페어 사용 (4바이트)
```

바이트 순서가 있어서 BOM(Byte Order Mark)이 필요하다. UTF-16 LE는 낮은 바이트 먼저, UTF-16 BE는 높은 바이트 먼저다. BOM 없이 받은 UTF-16 데이터는 바이트 순서를 추측해야 해서 버그의 원인이 된다.

Windows 내부 API와 Java `char`가 UTF-16 기반이다. 파일을 저장할 때는 UTF-8이지만 메모리에서는 UTF-16으로 다루는 경우가 많아, 변환 과정에서 서로게이트 페어를 잘못 처리하면 문자가 잘린다.

### UTF-32

모든 문자를 4바이트 고정 길이로 저장한다. 코드 포인트를 그대로 32비트 정수에 담는다.

```
'A' (U+0041) = 00 00 00 41
'가' (U+AC00) = 00 00 AC 00
'😀' (U+1F600) = 00 01 F6 00
```

장점은 인덱싱이 단순하다는 것이다. N번째 문자는 항상 `4*N` 오프셋에 있다. 단점은 공간 낭비가 크다. ASCII만 다뤄도 문자당 4바이트를 쓴다. 실무에서 파일 포맷이나 네트워크 전송에 UTF-32를 쓰는 경우는 거의 없다. Python 3 내부 표현이나 일부 유닉스 시스템의 `wchar_t`가 UTF-32다.

---

## 서로게이트 페어

U+10000 이상의 SMP 문자를 UTF-16으로 표현하는 방법이다. 코드 포인트에서 0x10000을 빼서 20비트 값을 얻고, 상위 10비트는 하이 서로게이트(U+D800~U+DBFF), 하위 10비트는 로우 서로게이트(U+DC00~U+DFFF)에 넣는다.

이모지 '😀' (U+1F600)를 서로게이트 페어로 변환하면:

```
U+1F600 - 0x10000 = 0xF600

0xF600 = 0000 1111 01 | 10 0000 0000
                  ^^               ^^
         상위 10비트: 0x3D         하위 10비트: 0x200 (틀림, 다시 계산)

0xF600 이진수: 0000 1111 0110 0000 0000

상위 10비트: 0000 1111 01 = 0x3D
하위 10비트: 10 0000 0000 = 0x200

하이 서로게이트: 0xD800 + 0x3D = 0xD83D
로우 서로게이트: 0xDC00 + 0x200 = 0xDE00 (틀림, 0x00이 맞음)
```

정확하게 다시:
```
U+1F600 - 0x10000 = 0xF600

0xF600 = 1111 0110 0000 0000 0000 (20비트)

상위 10비트: 11 1101 1000 = 0x1D8... 잘못됨, 다시

0xF600 = 0000 1111 0110 0000 0000 0000 (24비트)

0x1F600 - 0x10000 = 0xF600

0xF600 이진: 0000 1111 0110 0000 0000

20비트로:  00 0011 1101 | 10 0000 0000
상위 10:  0b0000111101 = 0x3D
하위 10:  0b1000000000 = 0x200

하이: 0xD800 + 0x3D = 0xD83D
로우: 0xDC00 + 0x200 = 0xDE00 (0x200 = 512 = 0x200이므로 DC00 + 200 = DE00)

결과: D83D DE00 → 실제 이모지 '😀'의 UTF-16 서로게이트 페어는 D83D DE00
```

### JavaScript에서 charAt vs codePointAt

JavaScript의 `String`은 UTF-16 코드 유닛 배열이다. 서로게이트 페어 문자 하나가 코드 유닛 2개를 차지한다.

```javascript
const emoji = '😀'; // U+1F600

// charAt: UTF-16 코드 유닛 인덱스 기준
emoji.charAt(0);  // '\uD83D' (하이 서로게이트, 깨진 문자)
emoji.charAt(1);  // '\uDE00' (로우 서로게이트, 깨진 문자)
emoji.length;     // 2 (코드 유닛 2개로 인식)

// codePointAt: 실제 코드 포인트 반환
emoji.codePointAt(0);  // 128512 (0x1F600)
emoji.codePointAt(1);  // 56832 (로우 서로게이트 단독, 잘못된 위치)

// 올바른 순회
for (const char of emoji) {
  console.log(char);  // '😀' 하나만 출력
}

// 코드 포인트 배열
[...emoji].length;  // 1
```

`length`를 문자 수로 쓰면 이모지가 있을 때 2배로 나온다. `[...str].length`나 `Array.from(str).length`를 써야 실제 문자 수를 얻는다.

`String.fromCodePoint()`는 SMP 코드 포인트를 받아 올바른 서로게이트 페어로 변환한다. `String.fromCharCode()`는 16비트 값만 다루므로 SMP에는 쓰면 안 된다.

---

## 유니코드 정규화

같은 문자를 다른 바이트 시퀀스로 표현할 수 있다는 게 정규화 문제의 핵심이다. '가'를 예로 들면:

```
방법 1: U+AC00 (완성형 '가' 한 글자)
방법 2: U+1100 U+1161 (ㄱ + ㅏ, 초성+중성 조합형)
```

두 시퀀스는 렌더링 결과가 같지만 바이트가 다르다. `str1 === str2`는 false다.

### NFC / NFD / NFKC / NFKD

- NFD (Canonical Decomposition): 문자를 기저 형태와 결합 문자로 분해한다. 'é'(U+00E9)를 'e'(U+0065) + 결합 악센트(U+0301)로 쪼갠다.
- NFC (Canonical Decomposition + Canonical Composition): NFD 분해 후 다시 조합한다. 'e' + 결합 악센트가 다시 'é' 하나로 합쳐진다.
- NFKD (Compatibility Decomposition): 호환성 분해까지 포함한다. ＡＢＣ(전각 문자)를 ABC(반각)로, ㎡를 m²로 바꾼다.
- NFKC: NFKD 분해 후 재조합한다.

macOS 파일 시스템(HFS+)은 파일명을 NFD로 저장하고, Linux(ext4)는 NFC 그대로 저장한다. macOS에서 만든 '가.txt'를 Linux로 옮기면 파일명 바이트가 달라진다. Git이 이를 처리하는 방식이 OS마다 달라서 한글 파일명이 있는 저장소를 macOS-Linux 환경에서 공유하면 파일이 변경된 것처럼 보이는 문제가 생긴다.

```python
import unicodedata

s1 = '\u00e9'          # é (NFC, 1글자)
s2 = 'e\u0301'         # e + 결합 악센트 (NFD, 2코드 포인트)

s1 == s2               # False
len(s1), len(s2)       # 1, 2

unicodedata.normalize('NFC', s2) == s1   # True
unicodedata.normalize('NFD', s1) == s2   # True
```

DB에서 문자열 검색할 때도 마찬가지다. 사용자가 입력한 문자열이 NFD고 저장된 데이터가 NFC면 `=` 비교가 실패한다. API를 받을 때 정규화를 명시적으로 해두지 않으면 나중에 찾기 어려운 버그가 된다.

---

## 이모지의 문자열 길이 문제

이모지가 복잡한 이유는 코드 포인트 하나가 아닌 여러 코드 포인트의 조합으로 하나의 이모지를 만들기 때문이다.

### ZWJ 시퀀스

ZWJ(Zero Width Joiner, U+200D)는 여러 이모지를 결합해서 새로운 이모지를 만드는 투명 문자다.

```
👨‍👩‍👧‍👦 (가족 이모지)
= 👨 U+1F468
+ ZWJ U+200D
+ 👩 U+1F469
+ ZWJ U+200D
+ 👧 U+1F467
+ ZWJ U+200D
+ 👦 U+1F466

코드 포인트 7개, UTF-16 코드 유닛 11개, 화면에는 1개
```

```javascript
const family = '👨‍👩‍👧‍👦';

family.length;              // 11 (UTF-16 코드 유닛)
[...family].length;         // 7 (코드 포인트)
// 사람 눈에 보이는 문자 수: 1
```

### 스킨톤 모디파이어

U+1F3FB~U+1F3FF (5가지 피부색)가 이모지 뒤에 붙어 피부색을 바꾼다.

```
👋 (U+1F44B) + 🏽 (U+1F3FD) = 👋🏽

코드 포인트 2개, 화면에 1개
```

### Emoji_Presentation과 변형 선택자

같은 코드 포인트가 텍스트 형태와 이모지 형태 중 어느 쪽으로 렌더링될지 U+FE0E(텍스트 변형 선택자)와 U+FE0F(이모지 변형 선택자)로 결정한다.

```
# (U+0023) 만 있으면 텍스트 '#'
# + U+FE0F = '#️' (이모지 스타일로 렌더링 요청)
# + U+FE0F + U+20E3 = '#️⃣' (키캡 이모지)
```

실용적인 의미는 이렇다. 사용자가 입력한 문자열의 "길이"를 계산하거나 자르는 로직을 짤 때, 단순히 코드 유닛이나 코드 포인트를 세면 안 된다. grapheme cluster 단위로 쪼개야 한다. 이를 처리하는 라이브러리(Python의 `grapheme`, JavaScript의 `Intl.Segmenter`)를 써야 한다.

```javascript
// Intl.Segmenter (모던 JavaScript)
const segmenter = new Intl.Segmenter('ko', { granularity: 'grapheme' });
const segments = [...segmenter.segment('👨‍👩‍👧‍👦안녕')];
segments.length;  // 3 (가족 이모지 1 + '안' 1 + '녕' 1)
```

문자 수 제한을 구현할 때 서버도 같은 기준으로 세야 한다. 클라이언트는 grapheme 기준으로 100자 제한을 걸었는데 서버는 UTF-8 바이트 기준으로 검사하면 불일치가 생긴다.

---

## 언어별 처리 방식

### Java

`char`는 UTF-16 코드 유닛 하나(2바이트)다. BMP 문자는 `char` 하나에 들어가지만 SMP 문자는 `char` 두 개가 필요하다.

```java
String emoji = "😀";  // U+1F600

emoji.length();           // 2 (char 개수)
emoji.codePointCount(0, emoji.length());  // 1 (코드 포인트 개수)

// charAt: char 반환 (서로게이트 페어를 두 개로 쪼갠다)
emoji.charAt(0);          // '\uD83D' (하이 서로게이트)

// codePointAt: 실제 코드 포인트 반환
emoji.codePointAt(0);     // 128512 (0x1F600)

// 코드 포인트 기준 순회
emoji.codePoints().forEach(cp -> System.out.println(Integer.toHexString(cp)));
// 출력: 1f600
```

레거시 Java 코드에서 `str.length()`를 문자 수로 쓰는 곳이 있으면 이모지 입력 시 잘못된 값을 준다. 문자열 자르기에서 `substring(0, n)`을 쓰면 서로게이트 페어 중간을 자를 수 있다. `Character.isHighSurrogate()` / `Character.isLowSurrogate()`로 확인하거나 코드 포인트 기준 API를 써야 한다.

### Go

Go의 `string`은 UTF-8 바이트 시퀀스다. 인덱싱하면 바이트를 가져온다. 문자(rune)를 다루려면 `rune` 타입을 써야 한다.

```go
s := "안녕"

len(s)          // 6 (UTF-8 바이트 수, 한글 1글자 = 3바이트)
len([]rune(s))  // 2 (유니코드 코드 포인트 수)

// 바이트 인덱싱 (위험)
s[0]   // 0xEC (안의 첫 번째 바이트)

// rune 순회 (올바름)
for i, r := range s {
    fmt.Printf("index %d: %c (U+%04X)\n", i, r, r)
}
// index 0: 안 (U+C548)
// index 3: 녕 (U+B155)
```

`range` 루프는 rune 단위로 순회하고, `i`는 바이트 오프셋이다. 바이트 오프셋과 rune 인덱스가 다른 경우가 생기니 주의해야 한다.

이모지는 rune 하나지만 grapheme cluster는 여전히 별도 라이브러리가 필요하다. `golang.org/x/text/unicode/norm` 패키지로 정규화, `rivo/uniseg`로 grapheme 처리를 한다.

### Python 3

Python 3의 `str`은 유니코드 코드 포인트 시퀀스다. 내부적으로 코드 포인트 범위에 따라 Latin-1, UCS-2, UCS-4 중 하나를 골라 저장한다.

```python
s = "안녕"

len(s)     # 2 (코드 포인트 수)
s[0]       # '안'
s[1]       # '녕'

emoji = "😀"
len(emoji)  # 1 (코드 포인트 하나)
emoji[0]    # '😀'

# grapheme 처리는 별도 라이브러리 필요
import grapheme
len(list(grapheme.graphemes("👨‍👩‍👧‍👦")))  # 1
```

Python 3의 `str`은 Java나 JavaScript보다 직관적이다. 그래도 ZWJ 시퀀스 이모지의 grapheme cluster는 `len()`으로 구분 못 한다.

파일을 열 때 `open(filename, 'r', encoding='utf-8')`처럼 인코딩을 명시해야 한다. 명시하지 않으면 OS의 기본 인코딩을 따르는데, Windows에서는 CP949나 CP1252가 기본이라 UTF-8 파일을 읽다가 깨진다.

---

## DB 콜레이션과 이모지 저장 실패

MySQL에서 이모지를 저장하려다 막히는 경우가 많다. 원인은 `utf8` 콜레이션이다.

MySQL의 `utf8`은 표준 UTF-8이 아니다. 3바이트까지만 지원한다. U+10000 이상의 문자(이모지 포함)는 4바이트라서 `utf8` 컬럼에 넣으면 다음 에러가 난다.

```
Incorrect string value: '\xF0\x9F\x98\x80' for column 'content' at row 1
```

`utf8mb4`가 진짜 UTF-8이다. 4바이트까지 지원한다.

```sql
-- 테이블 전체 변환
ALTER TABLE posts 
  CONVERT TO CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

-- 특정 컬럼만 변환
ALTER TABLE posts 
  MODIFY content TEXT 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;
```

연결 설정도 바꿔야 한다. 테이블이 utf8mb4여도 연결이 utf8이면 드라이버가 4바이트 문자를 잘라서 보낸다.

```python
# SQLAlchemy
engine = create_engine(
    'mysql+pymysql://user:pass@host/db',
    connect_args={'charset': 'utf8mb4'}
)
```

```java
// JDBC URL에 characterEncoding 추가
String url = "jdbc:mysql://host/db?characterEncoding=utf8mb4&useUnicode=true";
```

콜레이션에도 신경 써야 한다. `utf8mb4_unicode_ci`는 대소문자를 구분하지 않고 유니코드 표준 정렬을 따른다. `utf8mb4_bin`은 바이트 단위 비교라 대소문자를 구분한다. 이모지 비교는 `utf8mb4_unicode_ci`에서도 동작하지만, 정규화 차이로 같은 이모지인데 다른 코드 포인트 시퀀스인 경우(피부톤 모디파이어 포함 여부 등)는 DB 레벨에서 구분하기 어렵다.

PostgreSQL은 UTF-8을 그대로 지원하므로 이런 문제가 없다. 이모지 관련 트러블슈팅 비용이 MySQL보다 훨씬 적다.

### 인덱스 크기 주의

`utf8mb4`로 변환할 때 VARCHAR(255) 컬럼에 인덱스가 있으면 인덱스 크기 초과 에러가 날 수 있다.

```
Specified key was too long; max key length is 767 bytes
```

`utf8`은 문자당 최대 3바이트라 VARCHAR(255) 인덱스는 765바이트. `utf8mb4`는 최대 4바이트라 255 × 4 = 1020바이트로 767바이트 한계를 넘는다.

해결 방법은 MySQL 5.7.7+에서 `innodb_large_prefix`를 활성화하거나, MySQL 8.0 이상에서 `innodb_default_row_format = DYNAMIC` 설정을 확인하거나, 인덱스에 prefix length를 지정하는 것이다.

```sql
-- prefix 인덱스
CREATE INDEX idx_email ON users (email(191));
-- 191 * 4 = 764 바이트로 767 이하
```

---

## 주의해야 할 실무 상황

문자열 자르기 로직은 항상 바이트 기준인지 코드 유닛 기준인지 코드 포인트 기준인지 grapheme 기준인지 명확히 해야 한다. SMS 140자 제한처럼 외부 서비스 기준에 맞춰야 하는 경우도 있고, 화면 표시 기준으로 잘라야 하는 경우도 있다. 이 네 가지 기준이 서로 다른 값을 줄 수 있다.

정규화는 입력을 받는 시점에 한 번만 하는 게 낫다. NFC로 통일하면 비교나 저장에서 발생하는 불일치 문제를 대부분 막는다. 나중에 검색이 안 된다는 버그 리포트를 받고 나서 고치는 것보다 처음부터 적용하는 편이 낫다.

UTF-8 파일 앞에 BOM(Byte Order Mark, EF BB BF)이 붙은 경우가 있다. 주로 Windows 메모장이 만든 파일이다. 파일 파싱 로직에서 BOM을 처리하지 않으면 첫 줄 첫 번째 문자가 이상하게 보이거나, CSV 파싱 시 첫 번째 컬럼명이 BOM 포함 문자열이 된다. Python에서는 `encoding='utf-8-sig'`를 쓰면 BOM을 자동으로 제거한다.
