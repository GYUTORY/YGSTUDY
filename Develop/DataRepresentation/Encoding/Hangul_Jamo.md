---
title: 한글 자모 분리
tags: [hangul, jamo, unicode, nfd, decomposition, elasticsearch, nori, search, autocomplete, python, java, javascript]
updated: 2026-08-05
---

# 한글 자모 분리

한글 완성형 글자는 유니코드 코드 포인트 U+AC00(가)부터 U+D7A3(힣)까지 11,172개로 구성된다. 이 범위의 코드 포인트는 초성·중성·종성 인덱스를 수식 하나로 분해할 수 있도록 설계되어 있다.

## 완성형 코드 포인트 분해 공식

한글 음절 블록은 다음 공식으로 초성·중성·종성 인덱스를 계산한다.

```
음절 코드 포인트 = U+AC00 + (초성 × 21 × 28) + (중성 × 28) + 종성
```

19개 초성 × 21개 중성 × 28개 종성 자리(종성 없음 포함) = 11,172가지가 이 공식에서 나온다. 역방향으로 분해하면 이렇다.

```
offset = 코드 포인트 - 0xAC00
종성 인덱스 = offset % 28
중성 인덱스 = (offset // 28) % 21
초성 인덱스 = (offset // 28) // 21
```

초성 19자, 중성 21자, 종성 28자리(빈 종성 1개 포함, 실제 자음 27개)는 고정된 배열 순서가 있다.

```python
CHOSEONG  = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
JUNGSEONG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
JONGSEONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

def decompose(char: str) -> tuple[str, str, str]:
    code = ord(char)
    if not (0xAC00 <= code <= 0xD7A3):
        raise ValueError(f"한글 음절이 아님: {char!r}")
    offset = code - 0xAC00
    jong = offset % 28
    jung = (offset // 28) % 21
    cho  = (offset // 28) // 21
    return CHOSEONG[cho], JUNGSEONG[jung], JONGSEONG[jong]

decompose('닭')  # ('ㄷ', 'ㅏ', 'ㄱ')
decompose('가')  # ('ㄱ', 'ㅏ', '')
```

종성 인덱스 0은 빈 문자열이다. '가'처럼 받침이 없는 글자의 종성은 인덱스 0이다.

---

## Jamo 블록 세 가지와 혼동 버그

한글 자모는 유니코드에서 세 영역에 나뉘어 존재한다.

**Jamo 블록 (U+1100~U+11FF)**

조합용 자모(Combining Jamo)가 있는 블록이다. NFD 분해 결과가 이 영역의 코드 포인트로 나온다. 초성 ㄱ은 U+1100, 중성 ㅏ는 U+1161이다. 이 블록의 자모는 단독으로 렌더링되지 않고 인접한 초성·중성·종성이 모여 한 음절 글자를 이룬다. 폰트가 이 자모를 개별 글리프로 합성한다.

**Compatibility Jamo 블록 (U+3130~U+318F)**

키보드 입력, 문자표, 일상적인 복사·붙여넣기에서 나오는 자모는 이 범위다. ㄱ을 타이핑하면 U+3131, ㅏ는 U+3163이다. 화면에 단독으로 표시되도록 설계된 호환 자모다.

**Jamo Extended (U+A960~U+A97F, U+D7B0~U+D7FF)**

현대 한글에서 쓰지 않는 옛 자모와 확장 자모가 있는 블록이다. 고문헌 처리가 아니면 거의 마주칠 일이 없다.

---

### NFD 분해 결과와 호환 자모는 다른 코드 포인트

이걸 모르면 반드시 버그가 난다. '가'를 NFD로 분해하면 U+1100(ᄀ)과 U+1161(ᅡ)로 나온다. U+3131(ㄱ)과 U+3163(ㅏ)가 아니다.

```python
import unicodedata

char = '가'

# NFD 분해 → Jamo 블록 (U+1100대)
nfd = unicodedata.normalize('NFD', char)
[hex(ord(c)) for c in nfd]  # ['0x1100', '0x1161']

# 키보드에서 타이핑한 ㄱ → Compatibility Jamo (U+3131)
compatibility_jamo = 'ㄱ'
hex(ord(compatibility_jamo))  # '0x3131'

# 이 둘은 다른 코드 포인트
nfd[0] == compatibility_jamo  # False
```

이 차이를 무시하면 이런 버그가 생긴다.

```python
# 잘못된 초성 검색 구현
def wrong_choseong_search(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if '\u3131' <= c <= '\u314E'   # Compatibility Jamo 범위로 필터
    )

wrong_choseong_search('가나다')  # '' (빈 문자열)
# NFD 결과가 U+1100대이므로 U+3130대 필터에 걸리지 않음
```

올바른 구현은 NFD 결과물이 Jamo 블록 범위(U+1100~U+11FF)인지 확인하거나, 처음부터 수식 분해를 쓴다.

```python
def choseong_of(char: str) -> str:
    code = ord(char)
    if not (0xAC00 <= code <= 0xD7A3):
        return ''
    cho = (code - 0xAC00) // 28 // 21
    return CHOSEONG[cho]
```

Java에서도 같은 함정이 있다.

```java
String text = "가나다";
String nfd = Normalizer.normalize(text, Normalizer.Form.NFD);

// 잘못된 필터
String wrong = nfd.chars()
    .filter(c -> c >= 0x3131 && c <= 0x314E)  // Compatibility Jamo
    .collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append)
    .toString();
// wrong = "" (비어 있음)

// 올바른 필터: Jamo 블록 초성 범위 (U+1100~U+1112)
String correct = nfd.chars()
    .filter(c -> c >= 0x1100 && c <= 0x1112)
    .collect(StringBuilder::new, StringBuilder::appendCodePoint, StringBuilder::append)
    .toString();
// correct = "ᄀᄂᄃ" (Jamo 블록 초성)
```

JavaScript도 동일하다.

```javascript
const text = '가나다';
const nfd = text.normalize('NFD');

// NFD 결과의 코드 포인트 확인
[...nfd].map(c => c.codePointAt(0).toString(16));
// ['1100', '1161', '1102', '1161', '1103', '1161']
// 0x3131대가 아니라 0x1100대

// Compatibility Jamo로 변환하려면 직접 매핑해야 함
const JAMO_TO_COMPAT = new Map([
    [0x1100, 0x3131], // ᄀ → ㄱ
    [0x1102, 0x3134], // ᄂ → ㄴ
    // ... 나머지 매핑
]);
```

---

## 초성 검색과 자동완성 구현

초성 검색은 사용자가 'ㄱㄴ'을 입력하면 '가나', '기능', '공나루' 같은 결과를 돌려주는 기능이다. 구현은 두 단계로 나뉜다.

**인덱싱 단계**: 텍스트의 각 완성형 음절에서 초성을 추출해서 별도 필드에 저장한다.

```python
def extract_choseong(text: str) -> str:
    result = []
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            cho = (code - 0xAC00) // 28 // 21
            result.append(CHOSEONG[cho])
        else:
            result.append(char)
    return ''.join(result)

extract_choseong('기능 개선')  # 'ㄱㄴ ㄱㅅ'
extract_choseong('가나다라')   # 'ㄱㄴㄷㄹ'
```

**검색 단계**: 사용자 입력을 초성만 남긴 뒤 인덱스 필드와 비교한다.

```python
def choseong_search(query: str, items: list[str]) -> list[str]:
    q_cho = extract_choseong(query)
    results = []
    for item in items:
        item_cho = extract_choseong(item)
        if item_cho.startswith(q_cho):
            results.append(item)
    return results

choseong_search('ㄱㄴ', ['기능', '가나', '공나루', '기억'])
# ['기능', '가나', '공나루']
```

사용자가 완성형 글자와 자모를 섞어 입력하는 경우도 처리해야 한다. '기ㄴ'을 입력하면 '기'는 완성형, 'ㄴ'은 Compatibility Jamo다. 이 경우 '기'에서 초성 'ㄱ'을 뽑고, 중성·종성 여부도 봐야 완전한 자동완성이 된다.

```python
def is_jamo(char: str) -> bool:
    code = ord(char)
    return 0x3131 <= code <= 0x314E or 0x314F <= code <= 0x3163

def normalize_query(query: str) -> str:
    result = []
    for char in query:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            result.append(extract_choseong(char))
        elif is_jamo(char):
            result.append(char)
        else:
            result.append(char)
    return ''.join(result)
```

DB에서 구현하는 경우 초성 컬럼을 별도로 두고 인덱스를 건다.

```sql
-- 초성 컬럼 추가
ALTER TABLE products ADD COLUMN name_choseong VARCHAR(255);
CREATE INDEX idx_name_choseong ON products (name_choseong);

-- 검색 쿼리
SELECT * FROM products
WHERE name_choseong LIKE 'ㄱㄴ%';
```

PostgreSQL의 `LIKE` 연산자는 B-tree 인덱스에서 전방 일치(`LIKE 'xxx%'`)만 인덱스를 쓴다. 중간 검색(`LIKE '%ㄱ%'`)은 전체 테이블 스캔이 일어나므로, 중간 검색이 필요하면 GIN 인덱스나 전문 검색 엔진을 써야 한다.

---

## Elasticsearch nori 분석기 한글 처리

Elasticsearch의 nori 분석기는 한국어 형태소 분석기다. `analysis-nori` 플러그인을 설치해서 쓴다.

```bash
elasticsearch-plugin install analysis-nori
```

nori의 한글 처리 방식은 자모 분리를 직접 하지 않는다. 복합어·어미 분해가 주목적이다. '삼성전자'를 '삼성', '전자'로 나누거나, '먹었다'를 '먹'으로 분해하는 것이 nori의 역할이다.

```json
PUT /products
{
  "settings": {
    "analysis": {
      "analyzer": {
        "korean": {
          "type": "nori",
          "decompound_mode": "mixed"
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "name": {
        "type": "text",
        "analyzer": "korean"
      }
    }
  }
}
```

`decompound_mode`는 세 가지다. `none`은 복합어를 분해하지 않는다. `discard`는 복합어를 분해하고 원형을 버린다. `mixed`는 분해 결과와 원형을 모두 토큰으로 남긴다. 검색 리콜을 높이려면 `mixed`를 쓴다.

nori로는 초성 검색을 구현할 수 없다. nori는 형태소 단위로 토크나이징하지, 자모 단위로 분해하지 않는다. 초성 검색이 필요하면 별도 필드에 초성을 저장하고 `edge_ngram` 분석기를 조합한다.

```json
PUT /products
{
  "settings": {
    "analysis": {
      "tokenizer": {
        "edge_ngram_tokenizer": {
          "type": "edge_ngram",
          "min_gram": 1,
          "max_gram": 20,
          "token_chars": ["letter", "digit"]
        }
      },
      "analyzer": {
        "choseong_index": {
          "type": "custom",
          "tokenizer": "edge_ngram_tokenizer"
        },
        "choseong_search": {
          "type": "custom",
          "tokenizer": "keyword"
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "name_choseong": {
        "type": "text",
        "analyzer": "choseong_index",
        "search_analyzer": "choseong_search"
      }
    }
  }
}
```

인덱싱 시 `name_choseong` 필드에 초성 추출 값을 넣는다. edge_ngram이 'ㄱㄴㄷ'를 'ㄱ', 'ㄱㄴ', 'ㄱㄴㄷ' 세 토큰으로 분리한다. 검색 쿼리는 keyword 분석기로 입력 그대로 보내면 prefix 검색 효과가 난다.

nori 분석기에서 한글 자모가 포함된 텍스트는 주의가 필요하다. 완성형이 아닌 자모 단독 문자(ㄱ, ㅏ)는 nori가 스킵할 수 있다. 사용자 입력 중간 상태에서 검색하는 기능을 nori 단독으로 처리하려 하면 이 문제를 만난다.

---

## 실제 버그 사례: 정규화 형식 혼동

프로덕션에서 실제로 발생한 버그 패턴이다.

**상황**: 사용자 이름 검색이 특정 환경에서만 결과가 없다.

```python
# 검색 로직
def search_user(name: str):
    # macOS에서 입력한 이름: NFD (ᄀ + ᅡ + ... Jamo 블록 코드 포인트)
    # DB에 저장된 이름: NFC (U+AC00대 완성형)
    return db.query("SELECT * FROM users WHERE name = %s", name)
```

macOS HFS+가 파일명을 NFD로 변환하듯, IME 입력이 NFD로 들어오는 경우가 있다. DB에는 NFC로 저장되어 있으면 바이트가 달라서 `=` 비교가 실패한다. NFC로 정규화해서 저장하고, 검색 입력도 NFC로 정규화하면 해결된다.

**상황**: 초성 추출 함수가 일부 글자에서 잘못된 결과를 낸다.

```python
# 잘못된 구현: NFD 결과를 Compatibility Jamo로 오인
def wrong_extract(text: str) -> str:
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if '\u3130' <= c <= '\u318F')

wrong_extract('가나다')  # '' (빈 문자열)
# 원인: NFD 결과는 U+1100대 Jamo, 필터는 U+3130대 Compatibility Jamo
```

NFD 분해 후 추출한 조합 자모(U+1100대)를 Compatibility Jamo(U+3130대)로 변환하거나, 수식 분해로 초성 인덱스를 직접 구하는 방법을 써야 한다.

```python
# Jamo 블록 → Compatibility Jamo 변환 테이블 (초성만)
JAMO_TO_COMPAT = {
    0x1100: 'ㄱ', 0x1101: 'ㄲ', 0x1102: 'ㄴ', 0x1103: 'ㄷ', 0x1104: 'ㄸ',
    0x1105: 'ㄹ', 0x1106: 'ㅁ', 0x1107: 'ㅂ', 0x1108: 'ㅃ', 0x1109: 'ㅅ',
    0x110A: 'ㅆ', 0x110B: 'ㅇ', 0x110C: 'ㅈ', 0x110D: 'ㅉ', 0x110E: 'ㅊ',
    0x110F: 'ㅋ', 0x1110: 'ㅌ', 0x1111: 'ㅍ', 0x1112: 'ㅎ',
}

def extract_choseong_via_nfd(text: str) -> str:
    result = []
    for char in unicodedata.normalize('NFD', text):
        code = ord(char)
        if code in JAMO_TO_COMPAT:
            result.append(JAMO_TO_COMPAT[code])
    return ''.join(result)

extract_choseong_via_nfd('가나다')  # 'ㄱㄴㄷ'
```

수식 분해 방식이 더 빠르고 명확하다. NFD 분해 + 매핑 방식은 중간 문자열 객체를 추가로 생성한다.

**상황**: JavaScript에서 한글 문자 길이 계산 오류.

```javascript
// NFD로 분해된 한글은 length가 2 이상
const nfc = '가';  // U+AC00
const nfd = '가'.normalize('NFD');  // U+1100 + U+1161

nfc.length;  // 1
nfd.length;  // 2

// length로 글자 수를 세면 NFD 문자열에서 틀린 값이 나옴
function countChars(str) {
    return str.length;  // 잘못됨
}

// 올바른 방법: NFC로 정규화 후 카운트
function countCharsCorrect(str) {
    return str.normalize('NFC').length;
}

countCharsCorrect(nfd);  // 1
```

---

## 언어별 자모 분해 구현 비교

### Python

```python
import unicodedata

CHOSEONG  = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
JUNGSEONG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
JONGSEONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

def decompose_all(text: str) -> str:
    result = []
    for char in unicodedata.normalize('NFC', text):
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3:
            offset = code - 0xAC00
            jong = offset % 28
            jung = (offset // 28) % 21
            cho  = (offset // 28) // 21
            result.append(CHOSEONG[cho])
            result.append(JUNGSEONG[jung])
            if jong:
                result.append(JONGSEONG[jong])
        else:
            result.append(char)
    return ''.join(result)

decompose_all('닭볶음')  # 'ㄷㅏㄱㅂㅗㄲㅇㅡㅁ'
```

### Java

```java
public class HangulDecomposer {
    private static final char[] CHOSEONG = {
        'ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ',
        'ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'
    };
    private static final char[] JUNGSEONG = {
        'ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ',
        'ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ'
    };
    private static final char[] JONGSEONG = {
        0,'ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ',
        'ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ',
        'ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'
    };

    public static String decompose(String text) {
        StringBuilder sb = new StringBuilder();
        for (char c : Normalizer.normalize(text, Normalizer.Form.NFC).toCharArray()) {
            int code = (int) c;
            if (code >= 0xAC00 && code <= 0xD7A3) {
                int offset = code - 0xAC00;
                int jong = offset % 28;
                int jung = (offset / 28) % 21;
                int cho  = (offset / 28) / 21;
                sb.append(CHOSEONG[cho]);
                sb.append(JUNGSEONG[jung]);
                if (jong > 0) sb.append(JONGSEONG[jong]);
            } else {
                sb.append(c);
            }
        }
        return sb.toString();
    }

    public static String extractChoseong(String text) {
        StringBuilder sb = new StringBuilder();
        for (char c : Normalizer.normalize(text, Normalizer.Form.NFC).toCharArray()) {
            int code = (int) c;
            if (code >= 0xAC00 && code <= 0xD7A3) {
                int cho = ((code - 0xAC00) / 28) / 21;
                sb.append(CHOSEONG[cho]);
            } else {
                sb.append(c);
            }
        }
        return sb.toString();
    }
}
```

### JavaScript

```javascript
const CHOSEONG  = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
const JUNGSEONG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ'];
const JONGSEONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];

function isHangul(char) {
    const code = char.codePointAt(0);
    return code >= 0xAC00 && code <= 0xD7A3;
}

function extractChoseong(text) {
    return [...text.normalize('NFC')]
        .map(char => {
            if (!isHangul(char)) return char;
            const offset = char.codePointAt(0) - 0xAC00;
            const cho = Math.floor(offset / 28 / 21);
            return CHOSEONG[cho];
        })
        .join('');
}

function decompose(text) {
    return [...text.normalize('NFC')]
        .map(char => {
            if (!isHangul(char)) return char;
            const offset = char.codePointAt(0) - 0xAC00;
            const jong = offset % 28;
            const jung = Math.floor(offset / 28) % 21;
            const cho  = Math.floor(offset / 28 / 21);
            return CHOSEONG[cho] + JUNGSEONG[jung] + JONGSEONG[jong];
        })
        .join('');
}

extractChoseong('기능 개선');  // 'ㄱㄴ ㄱㅅ'
decompose('닭볶음');           // 'ㄷㅏㄱㅂㅗㄲㅇㅡㅁ'
```

`[...text]` 스프레드는 코드 유닛이 아닌 코드 포인트 단위로 순회한다. 이모지나 surrogate pair가 섞인 텍스트에서 `text[i]` 인덱스 접근 방식은 깨진 문자를 처리할 수 있으므로 스프레드나 `Array.from()`을 쓴다.

---

## 주의사항

겹받침(ㄳ, ㄵ 등)은 종성 인덱스에서 단일 값으로 취급한다. '닭'의 종성은 ㄱ(인덱스 1)이 아니라 ㄺ(ㄹ+ㄱ 겹받침, 인덱스 9)다. 초성 검색에서 겹받침을 구성하는 자음 각각으로 분해해야 하는 경우 별도 매핑이 필요하다.

```python
DOUBLE_JONGSEONG = {
    'ㄳ': ('ㄱ', 'ㅅ'),
    'ㄵ': ('ㄴ', 'ㅈ'),
    'ㄶ': ('ㄴ', 'ㅎ'),
    'ㄺ': ('ㄹ', 'ㄱ'),
    'ㄻ': ('ㄹ', 'ㅁ'),
    'ㄼ': ('ㄹ', 'ㅂ'),
    'ㄽ': ('ㄹ', 'ㅅ'),
    'ㄾ': ('ㄹ', 'ㅌ'),
    'ㄿ': ('ㄹ', 'ㅍ'),
    'ㅀ': ('ㄹ', 'ㅎ'),
    'ㅄ': ('ㅂ', 'ㅅ'),
}
```

입력 텍스트가 NFC인지 NFD인지 모르는 상황에서는 처리 전에 NFC로 정규화한다. NFC 완성형 음절에서 수식 분해를 쓰는 것이 가장 신뢰할 수 있다. NFD 결과를 직접 다루면 Jamo 블록과 Compatibility Jamo 혼동 버그를 다시 만난다.
