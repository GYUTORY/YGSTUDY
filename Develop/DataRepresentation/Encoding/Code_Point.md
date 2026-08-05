---
title: 코드 포인트 (Code Point)
tags: [unicode, code-point, code-unit, grapheme-cluster, general-category, surrogate, pua, noncharacter, python, java, go, javascript]
updated: 2026-08-05
---

# 코드 포인트 (Code Point)

코드 포인트는 유니코드 표준이 문자에 부여한 고유 번호다. `U+` 접두어 뒤에 16진수로 표기한다. `U+0041`은 'A', `U+AC00`은 '가', `U+1F600`은 '😀'다. 범위는 U+0000부터 U+10FFFF까지 총 1,114,112개다.

인코딩(UTF-8/UTF-16/UTF-32)은 이 번호를 바이트로 변환하는 방법이다. 코드 포인트 자체는 인코딩과 무관한 추상 번호다.

---

## 코드 포인트 vs 코드 유닛 vs grapheme cluster

세 개념을 혼동하면 문자열 길이 계산과 자르기에서 조용히 버그가 생긴다.

**코드 포인트(code point)**는 유니코드 번호 하나다. '가' = U+AC00, '😀' = U+1F600. 각각 코드 포인트 1개다.

**코드 유닛(code unit)**은 인코딩 단위다. UTF-16의 코드 유닛은 16비트(2바이트)다. BMP 문자(U+0000~U+FFFF)는 코드 유닛 1개로 표현되지만, SMP 문자(U+10000~U+10FFFF)는 서로게이트 페어로 코드 유닛 2개가 필요하다. Java의 `char`와 JavaScript `String`이 UTF-16 코드 유닛 배열이라 이 차이가 직접 코드에 나타난다.

**grapheme cluster**는 사용자 눈에 보이는 문자 하나다. '가족 이모지' 👨‍👩‍👧‍👦는 코드 포인트 7개(각 이모지 4개 + ZWJ 3개)지만 grapheme cluster는 1개다. 피부색 모디파이어가 붙은 '👋🏽'는 코드 포인트 2개, grapheme cluster 1개다.

```
문자열: "A😀"

바이트(UTF-8) : 41 F0 9F 98 80         (5바이트)
코드 유닛(UTF-16): 0041 D83D DE00       (3개)
코드 포인트      : U+0041 U+1F600       (2개)
grapheme cluster : 'A', '😀'            (2개)
```

실무에서 어떤 단위를 써야 하는지는 목적에 따라 다르다. DB 컬럼 크기는 바이트 기준, 문자 수 제한 UI는 grapheme cluster 기준, 프로토콜 처리나 파싱 로직은 코드 포인트 기준이 맞는 경우가 많다. "이 API는 100자 제한"이라는 스펙을 받으면 반드시 어떤 기준의 '자'인지 확인해야 한다.

---

## 유효한 코드 포인트 범위와 예약 영역

전체 범위 U+0000~U+10FFFF 안에 실제로 문자를 배치할 수 없는 구간이 있다.

### 서로게이트 영역

U+D800~U+DFFF (2,048개)는 UTF-16 서로게이트 페어 전용으로 예약된 구간이다. 이 범위에 있는 값은 단독으로 유효한 코드 포인트가 아니다.

```
High surrogate: U+D800 ~ U+DBFF
Low surrogate : U+DC00 ~ U+DFFF
```

문자열 유효성 검사에서 이 구간이 단독으로 들어오면 잘못된 입력이다. 특히 외부 API나 파일에서 데이터를 받을 때, WTF-8(서로게이트를 허용하는 비표준 UTF-8)로 인코딩된 데이터가 들어오는 경우가 있다. 표준 UTF-8 디코더는 이 값을 거부하지만, 일부 라이브러리는 묵묵히 통과시킨다. Python의 `'surrogatepass'` 에러 핸들러가 대표적이다.

```python
# 서로게이트가 포함된 bytes를 강제로 디코딩
b'\xed\xa0\x80'.decode('utf-8', errors='surrogatepass')  # '\ud800'
# 이 문자열은 표준 UTF-8로 다시 인코딩하면 에러
'\ud800'.encode('utf-8')  # UnicodeEncodeError
'\ud800'.encode('utf-8', errors='surrogatepass')  # b'\xed\xa0\x80'
```

### 비문자 (Noncharacter)

영구적으로 내부 처리용으로 예약된 66개 코드 포인트다.

```
U+FDD0 ~ U+FDEF  (32개)
U+FFFE, U+FFFF
U+1FFFE, U+1FFFF
U+2FFFE, U+2FFFF
...
U+10FFFE, U+10FFFF
```

각 플레인의 마지막 두 포인트(0xFFFE, 0xFFFF)가 비문자다. 유니코드 표준은 이 값을 외부 교환 데이터에 쓰지 말라고 명시한다. 단, 금지는 아니다. 내부 처리에서 센티넬 값으로 쓰는 용도다. U+FFFE는 BOM의 잘못된 바이트 순서를 감지하는 데 쓴다.

외부 사용자 입력에서 비문자가 들어오면 대부분 실수거나 악의적 입력이다. API 레이어에서 걸러내는 게 낫다.

### 사용자 정의 영역 (PUA)

```
BMP PUA: U+E000 ~ U+F8FF       (6,400개)
PUA-A:   U+F0000 ~ U+FFFFD     (65,534개)
PUA-B:   U+100000 ~ U+10FFFD   (65,534개)
```

유니코드 컨소시엄이 의미를 정의하지 않은 영역이다. 개인이나 단체가 사적으로 의미를 부여해서 쓴다. Apple이 macOS에서 시스템 아이콘에 PUA를 쓰고, 레거시 한자 집합 확장에도 PUA가 활용된다. Nerd Fonts 같은 아이콘 폰트는 BMP PUA에 아이콘을 배치한다.

PUA 문자가 들어온 데이터는 합의된 약속 없이는 의미를 알 수 없다. 데이터 교환 포맷에서 PUA를 마주치면 발신 측과 인코딩 약속을 확인해야 한다.

---

## Unicode General_Category

유니코드는 모든 코드 포인트에 General_Category 속성을 부여한다. 정규식 처리, 렉서/파서, 입력 검증에서 카테고리를 기준으로 문자를 분류할 때 쓴다.

```
카테고리 코드   이름                   예시
Lu             Letter, Uppercase      A, B, C, Ä, Ж
Ll             Letter, Lowercase      a, b, c, ä, ж
Lt             Letter, Titlecase      Dž, Lj
Lo             Letter, Other          한, 中, 가나, ء
Nd             Number, Decimal Digit  0-9, ０-９ (전각), ۰-۹ (아라비아)
No             Number, Other          ½, ²,  Ⅷ
Po             Punctuation, Other     . , ! ? 。、
Ps / Pe        Punctuation, Open/Close ( ) [ ] { } 「 」
Zs             Separator, Space       공백, NBSP, 전각 공백
Cc             Other, Control         탭(\t), 개행(\n), NUL
Mn             Mark, Nonspacing       결합 악센트, 결합 자모
```

실무에서 가장 자주 쓰는 경우는 두 가지다.

첫째, 식별자 유효성 검사다. 변수명이나 사용자 아이디에 글자(Letter)와 숫자(Number, Decimal)만 허용하고 싶을 때 카테고리 기준이 단순 ASCII 범위 체크보다 낫다. 전각 문자나 다국어 문자를 올바르게 처리한다.

```python
import unicodedata

def is_identifier_char(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat.startswith('L') or cat.startswith('N') or ch == '_'

is_identifier_char('A')   # True (Lu)
is_identifier_char('가')  # True (Lo)
is_identifier_char('1')   # True (Nd)
is_identifier_char('.')   # False (Po)
is_identifier_char('！')  # False (Po, 전각 느낌표)
```

둘째, 공백 정규화다. `Zs` 카테고리에는 일반 공백 외에도 Non-Breaking Space(U+00A0), 전각 공백(U+3000), 좁은 공백(U+202F) 등 17종이 있다. 단순히 `' '`로만 체크하면 나머지를 다 놓친다. 사용자가 붙여넣은 텍스트에 NBSP가 섞여 있으면 `trim()`이나 `split()`이 의도대로 동작하지 않는다.

```python
# 유니코드 기준 공백 전부 제거
import re
cleaned = re.sub(r'\s', '', text)  # \s는 Zs + Cc 공백류 포함

# 카테고리 기준
def is_whitespace(ch: str) -> bool:
    cat = unicodedata.category(ch)
    return cat == 'Zs' or ch in ('\t', '\n', '\r', '\f', '\v')
```

---

## Block과 Script 속성

Block은 코드 포인트를 구간으로 묶은 분류다. "Basic Latin", "Hangul Syllables", "Emoticons" 같은 블록이 있다. 블록 경계는 코드 포인트 범위로 고정돼 있다.

Script는 문자가 속한 문자 체계다. "Latin", "Hangul", "Arabic", "Han" 등이다. 같은 블록 안에 여러 Script가 섞일 수 있다. 예컨대 "Latin Extended-B" 블록에는 Latin 스크립트 외에도 소수 언어용 문자가 섞여 있다.

실무에서 Script 속성이 유용한 경우는 언어 감지와 혼합 스크립트 공격 탐지다. 피싱 URL에서 키릴 문자 'а'(U+0430)가 라틴 'a'(U+0061)처럼 보이는 국제화 도메인 이름(IDN) 혼동 공격이 있다. 같은 문자열 안에 여러 스크립트가 섞이면 의심 대상이다.

```python
import unicodedata

def detect_scripts(text: str) -> set:
    scripts = set()
    for ch in text:
        # unicodedata.name으로 블록/스크립트 추정
        try:
            name = unicodedata.name(ch)
            if name.startswith('LATIN'):
                scripts.add('Latin')
            elif name.startswith('HANGUL'):
                scripts.add('Hangul')
            elif name.startswith('CYRILLIC'):
                scripts.add('Cyrillic')
        except ValueError:
            pass
    return scripts

# 더 정확한 처리는 icu4c/PyICU 또는 regex 라이브러리의 \p{Script=...} 사용
import regex
regex.findall(r'\p{Script=Cyrillic}', 'аpple')  # ['а'] - 키릴 'а'만 추출
```

`regex` 라이브러리(표준 `re` 아님)는 `\p{Script=Han}`, `\p{Block=Hangul_Syllables}`, `\p{General_Category=Lu}` 같은 유니코드 속성 기반 패턴을 지원한다. 다국어 입력 검증에 표준 `re`보다 훨씬 적합하다.

---

## 언어별 코드 포인트 API

### Python

`ord()`와 `chr()`이 코드 포인트와 문자를 상호 변환한다. Python 3 `str`은 코드 포인트 시퀀스라서 인덱싱이 코드 포인트 기준으로 동작한다.

```python
ord('A')       # 65 (0x41)
ord('가')      # 44032 (0xAC00)
ord('😀')     # 128512 (0x1F600)

chr(44032)     # '가'
chr(0x1F600)   # '😀'

# 코드 포인트 기준 순회
for cp in map(ord, "안녕😀"):
    print(f"U+{cp:04X}")
# U+C548
# U+B155
# U+1F600

# unicodedata로 속성 조회
import unicodedata
unicodedata.name('가')            # 'HANGUL SYLLABLE GA'
unicodedata.category('A')         # 'Lu'
unicodedata.category('1')         # 'Nd'
unicodedata.numeric('½')          # 0.5
unicodedata.decimal('５')         # 5 (전각 숫자)
```

`unicodedata.category()`는 문자 하나를 받는다. 서로게이트 코드 포인트의 카테고리는 'Cs'다.

### Java

`char`는 UTF-16 코드 유닛(16비트)이다. SMP 문자는 `char` 두 개로 이루어진 서로게이트 페어다. 코드 포인트 기준으로 다루려면 `Character` 클래스의 정적 메서드나 `String.codePointAt()`을 써야 한다.

```java
String s = "안녕😀";

// 잘못된 방법: char 단위
s.length();             // 5 (안 녕 D83D DE00)
s.charAt(2);            // '\uD83D' (하이 서로게이트, 반쪽짜리)

// 코드 포인트 단위
s.codePointCount(0, s.length());    // 3 (안, 녕, 😀)
s.codePointAt(4);                   // 128512 (0x1F600)

// 코드 포인트 기준 순회
s.codePoints()
 .forEach(cp -> System.out.printf("U+%04X%n", cp));
// U+C548
// U+B155
// U+1F600

// 코드 포인트로 문자열 생성
String emoji = new String(Character.toChars(0x1F600));  // "😀"
// 또는
String emoji2 = String.valueOf(Character.toChars(0x1F600));

// 카테고리 확인
Character.getType('A');          // Character.UPPERCASE_LETTER (1)
Character.isLetter('가');         // true
Character.isDigit('５');          // true (전각 숫자)
Character.isWhitespace('\u3000'); // false (전각 공백은 isWhitespace 미포함)
Character.isSpaceChar('\u3000');  // true

// 서로게이트 확인
Character.isHighSurrogate('\uD83D');  // true
Character.isSurrogatePair('\uD83D', '\uDE00');  // true
Character.toCodePoint('\uD83D', '\uDE00');       // 128512
```

`Character.isWhitespace()`와 `Character.isSpaceChar()`는 다르다. 전자는 Java가 공백으로 간주하는 ASCII 공백류만 포함하고, 후자는 유니코드 Zs 카테고리 전체를 포함한다. 어떤 공백을 처리하려는지에 따라 다르게 써야 한다.

### Go

Go의 `string`은 UTF-8 바이트 슬라이스다. `rune`은 `int32` 타입 별칭이고, 코드 포인트 하나를 담는다.

```go
package main

import (
    "fmt"
    "unicode"
    "unicode/utf8"
)

func main() {
    s := "안녕😀"

    // 바이트 기준 (잘못된 문자 수 계산)
    fmt.Println(len(s))           // 10 (안:3 녕:3 😀:4)

    // 코드 포인트 기준
    fmt.Println(utf8.RuneCountInString(s))  // 3
    fmt.Println(len([]rune(s)))             // 3

    // rune 순회
    for i, r := range s {
        fmt.Printf("byte offset %d: U+%04X (%c)\n", i, r, r)
    }
    // byte offset 0: U+C548 (안)
    // byte offset 3: U+B155 (녕)
    // byte offset 6: U+1F600 (😀)

    // 코드 포인트 변환
    r := '가'
    fmt.Printf("U+%04X\n", r)  // U+AC00

    // unicode 패키지로 속성 확인
    fmt.Println(unicode.IsLetter('가'))     // true
    fmt.Println(unicode.IsDigit('5'))       // true
    fmt.Println(unicode.IsUpper('A'))       // true
    fmt.Println(unicode.IsSpace('\u3000'))  // true (전각 공백, Go는 포함)
    fmt.Println(unicode.Is(unicode.Hangul, '가'))  // true

    // 바이트 오프셋 기준 rune 추출
    r2, size := utf8.DecodeRuneInString(s)  // 첫 번째 rune
    fmt.Printf("rune: %c, size: %d bytes\n", r2, size)  // 안, 3
}
```

`range` 루프의 인덱스는 rune 인덱스가 아니라 바이트 오프셋이다. 코드 포인트를 N번째 문자로 접근하려면 `[]rune(s)[N]`으로 변환하거나 `utf8.DecodeRuneInString`을 반복해야 한다. 큰 문자열에서 []rune 변환은 메모리를 새로 할당한다.

`unicode` 패키지의 `RangeTable`로 스크립트 단위 검사가 가능하다. `unicode.Hangul`, `unicode.Latin`, `unicode.Han` 등이 내장돼 있다.

### JavaScript

JavaScript `String`은 UTF-16 코드 유닛 시퀀스다. ES2015에서 코드 포인트 관련 API가 추가됐다.

```javascript
// codePointAt: 코드 포인트 반환 (SMP 포함)
'😀'.codePointAt(0)      // 128512 (0x1F600)
'A'.codePointAt(0)        // 65

// fromCodePoint: 코드 포인트로 문자 생성
String.fromCodePoint(0x1F600)   // '😀'
String.fromCodePoint(0xAC00)    // '가'

// 잘못된 방법: fromCharCode는 16비트 값만 처리
String.fromCharCode(0x1F600)    // 잘못된 문자 (0xF600만 처리)
String.fromCharCode(0xD83D, 0xDE00)  // '😀' (수동으로 서로게이트 페어)

// 코드 포인트 기준 순회
for (const char of '안녕😀') {
    console.log(char.codePointAt(0).toString(16).toUpperCase().padStart(4, '0'));
}
// C548
// B155
// 1F600

// 코드 포인트 배열로 변환
const codePoints = [...'안녕😀'].map(c => c.codePointAt(0));
// [50504, 45397, 128512]

// 유효성 확인
function isValidCodePoint(cp) {
    return cp >= 0 && cp <= 0x10FFFF &&
           !(cp >= 0xD800 && cp <= 0xDFFF);  // 서로게이트 제외
}

// 카테고리 검사는 Intl 또는 정규식으로
/\p{L}/u.test('가')    // true (Letter)
/\p{Nd}/u.test('5')   // true (Decimal Number)
/\p{Lu}/u.test('A')   // true (Uppercase Letter)
/\p{Script=Hangul}/u.test('가')  // true
```

`/\p{...}/u` 플래그(유니코드 모드)는 ES2018부터 지원한다. Node.js 10+ / 모던 브라우저에서 쓸 수 있다. `u` 플래그 없이 쓰면 `\p`는 그냥 `p`로 해석된다.

---

## 코드 포인트 기준 문자열 처리

### 길이 계산

```python
# Python: 코드 포인트 기준 길이
def codepoint_len(s: str) -> int:
    return len(s)  # Python str은 이미 코드 포인트 기준

len("안녕😀")   # 3
```

```java
// Java: 코드 포인트 기준 길이
int cpLen = s.codePointCount(0, s.length());
```

```go
// Go: 코드 포인트 기준 길이
import "unicode/utf8"
cpLen := utf8.RuneCountInString(s)
```

```javascript
// JS: 코드 포인트 기준 길이
const cpLen = [...s].length;
// 또는
const cpLen2 = Array.from(s).length;
```

### 코드 포인트 기준 자르기

가장 실수가 많은 부분이다. 서로게이트 페어 중간을 자르면 해당 문자가 깨진다.

```python
# Python: 슬라이싱이 코드 포인트 기준
s = "안녕😀world"
s[:3]    # "안녕😀"
s[2:3]   # "😀"
```

```java
// Java: codePoints로 변환 후 자르기
String s = "안녕😀world";

// 코드 포인트 기준 앞 3개
String first3 = s.codePoints()
    .limit(3)
    .collect(StringBuilder::new,
             StringBuilder::appendCodePoint,
             StringBuilder::append)
    .toString();  // "안녕😀"

// 또는 오프셋 계산
int endOffset = s.offsetByCodePoints(0, 3);
String first3Alt = s.substring(0, endOffset);
```

```go
// Go: []rune 변환 후 슬라이싱
s := "안녕😀world"
runes := []rune(s)
string(runes[:3])  // "안녕😀"

// 메모리 할당 없이 처리할 때
import "unicode/utf8"

func runeSlice(s string, start, end int) string {
    i := 0
    byteStart := 0
    byteEnd := len(s)
    for pos := range s {
        if i == start {
            byteStart = pos
        }
        if i == end {
            byteEnd = pos
            break
        }
        i++
    }
    return s[byteStart:byteEnd]
}
```

```javascript
// JS: 스프레드 후 슬라이싱
const s = "안녕😀world";
[...s].slice(0, 3).join('')  // "안녕😀"
```

### 코드 포인트 유효성 검사

```python
def is_valid_codepoint(cp: int) -> bool:
    if cp < 0 or cp > 0x10FFFF:
        return False
    if 0xD800 <= cp <= 0xDFFF:  # 서로게이트
        return False
    return True

def has_invalid_codepoints(s: str) -> bool:
    for ch in s:
        cp = ord(ch)
        if not is_valid_codepoint(cp):
            return True
    return False

def has_noncharacters(s: str) -> bool:
    for ch in s:
        cp = ord(ch)
        if 0xFDD0 <= cp <= 0xFDEF:
            return True
        if (cp & 0xFFFF) in (0xFFFE, 0xFFFF):
            return True
    return False
```

```java
// Java: 서로게이트 포함 문자열 감지
public static boolean hasSurrogates(String s) {
    for (int i = 0; i < s.length(); i++) {
        if (Character.isSurrogate(s.charAt(i))) {
            return true;
        }
    }
    return false;
}

// 쌍이 맞지 않는 서로게이트 감지
public static boolean hasUnpairedSurrogates(String s) {
    for (int i = 0; i < s.length(); i++) {
        char c = s.charAt(i);
        if (Character.isHighSurrogate(c)) {
            if (i + 1 >= s.length() || !Character.isLowSurrogate(s.charAt(i + 1))) {
                return true;
            }
            i++;  // 페어를 통째로 건너뜀
        } else if (Character.isLowSurrogate(c)) {
            return true;  // 선행 하이 서로게이트 없이 로우 서로게이트
        }
    }
    return false;
}
```

---

## 자주 틀리는 케이스

### `length` 믿기

API 입력 제한을 구현할 때 Java `.length()`, JavaScript `.length`, Go `len()` 중 어느 것도 "사용자가 인식하는 문자 수"를 반환하지 않는다. 이모지가 들어오면 전부 실제보다 크거나 같은 값을 반환한다.

```javascript
// 트위터 방식: 이모지를 2자로 계산
// 우리 서비스 방식: grapheme cluster 기준 1자로 계산
// 어떤 기준인지 스펙 문서에 명시하지 않으면 나중에 논쟁이 생긴다
```

### 전각 숫자와 `isDigit`

```java
Character.isDigit('５')  // true (전각 5, U+FF15)
Integer.parseInt("５")   // NumberFormatException
```

카테고리가 Nd인 문자라도 ASCII 범위가 아니면 `parseInt` 같은 파싱 함수가 거부한다. 입력 정규화 없이 카테고리만 믿으면 이후 파싱 단계에서 터진다.

### 결합 문자 포함 문자열 자르기

```python
s = "e\u0301"  # e + 결합 악센트 = é (NFD)
s[0]           # 'e' (결합 문자 없이 자름, 렌더링하면 반쪽)
s[:1]          # 'e' (마찬가지)

# NFC 정규화 후 자르기
import unicodedata
normalized = unicodedata.normalize('NFC', s)  # 'é' (U+00E9, 1 코드 포인트)
normalized[0]  # 'é'
```

입력 정규화 없이 코드 포인트 기준으로 자르면 결합 문자(Mn 카테고리)가 분리돼서 렌더링이 깨진다. 사용자 입력을 다룰 때는 NFC로 정규화한 뒤 자르는 게 안전하다.
