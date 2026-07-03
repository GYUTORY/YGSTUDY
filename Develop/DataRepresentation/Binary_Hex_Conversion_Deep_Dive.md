---
title: 2진수와 16진수 변환 심화
tags:
  - DataRepresentation
  - Binary
  - Hexadecimal
  - TwosComplement
  - IEEE754
  - Endianness
updated: 2026-04-26
---

# 2진수와 16진수 변환 심화

4비트씩 묶어서 16진수 한 자리로 변환한다는 기본 원리는 학부 수업에서 끝난다. 실무에서 만나는 문제는 거의 다 그 원리 위에 깔려있는 부호 비트, 부동소수점 비트 레이아웃, 엔디언, 언어별 정수 처리 방식의 차이에서 발생한다. 디버거에서 본 16진수가 왜 이상한 음수로 찍히는지, 같은 4바이트 정수를 메모리에서 떠보면 왜 거꾸로 보이는지, 자바스크립트에서 큰 16진수 리터럴이 왜 갑자기 정밀도를 잃는지 같은 문제들이다. 이 문서는 그 함정들을 한 번씩 직접 부딪쳐 본 입장에서 정리한 노트에 가깝다.


## 2의 보수와 부호 확장이 만드는 함정

`0xFFFFFFFF`라는 값을 보면 사람마다 다르게 읽는다. C에서 `unsigned int`면 4294967295로 읽지만, `int`면 -1로 읽는다. 같은 32비트 패턴이지만 타입이 의미를 결정한다. 2의 보수 체계에서 32비트 음수 -1은 모든 비트가 1인 패턴이고, 이 패턴을 16진수로 표현한 게 `0xFFFFFFFF`다. 부호 비트(MSB)가 1이면 음수라는 사실만 외워두면 디버거가 보여주는 16진수와 실제 값을 머릿속에서 변환할 수 있다.

진짜 문제는 폭이 다른 정수 사이를 오갈 때 생긴다. `int8_t`로 -1을 가지고 있다가 `int32_t`로 캐스팅하면 `0xFF`가 `0xFFFFFFFF`로 확장된다. 이게 부호 확장(sign extension)이다. 부호 비트가 1이면 상위 비트를 모두 1로 채우고, 0이면 0으로 채운다. C에서 자주 만나는 버그가 이거다.

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    int8_t  a = -1;             // 0xFF
    uint8_t b = (uint8_t)a;     // 0xFF, 값으로는 255
    int32_t c = a;              // 0xFFFFFFFF, 값으로는 -1 (부호 확장)
    uint32_t d = (uint32_t)a;   // 0xFFFFFFFF, 값으로는 4294967295

    printf("a=0x%02x c=0x%08x d=0x%08x\n", (uint8_t)a, c, d);
    // a=0xff c=0xffffffff d=0xffffffff
    return 0;
}
```

같은 비트 패턴 `0xFFFFFFFF`가 `int32_t`로 보면 -1, `uint32_t`로 보면 4294967295가 된다. 디버거에서 `c == d`인지 묻는 건 무의미하고, 어떤 타입으로 해석해서 보고 있느냐가 전부다. 네트워크 패킷 파싱이나 바이너리 프로토콜 디코딩할 때 이 부호 확장을 놓쳐서 음수가 튀어나오는 사례를 흔하게 본다. 특히 `char`가 플랫폼에 따라 `signed char`인지 `unsigned char`인지 다르기 때문에 바이너리 데이터를 다룰 때는 무조건 `uint8_t`로 받는 습관을 들여야 한다.

자바 진영에서는 `byte`가 항상 부호 있는 8비트라 더 자주 부딪힌다. `byte b = (byte)0xFF`는 -1이고, 이걸 `int`로 끌어올리면 `0xFFFFFFFF`가 된다. 16진수로 dump를 찍을 때 `& 0xFF` 마스킹을 빼먹으면 32자리 짜리 `ffffff80` 같은 게 줄줄이 찍힌다.

```java
byte[] data = {0x12, (byte)0x80, (byte)0xFF};
for (byte b : data) {
    // 잘못된 예: System.out.printf("%02x ", b);  -> 12 ffffff80 ffffffff
    System.out.printf("%02x ", b & 0xFF);          // 12 80 ff
}
```


## 비트 연산 기반 변환 구현

16진수 문자 한 자리는 4비트와 1:1로 매핑된다. 32비트 정수를 16진수 문자열로 바꾸려면 4비트씩 8번 잘라내면 된다. 흔히 두 가지 방식을 쓴다. 하나는 `>> 4`로 시프트하면서 `& 0xF`로 마스킹하는 방식, 다른 하나는 16개짜리 룩업 테이블에서 인덱싱하는 방식이다. 현대 CPU에서는 두 방식 성능 차이가 거의 없지만, 룩업 테이블이 분기가 적어서 미세하게 빠른 경우가 있다.

C로 쓰면 이렇게 된다. 핵심은 상위 니블(nibble)부터 순서대로 뽑아내는 거다.

```c
void to_hex(uint32_t v, char out[9]) {
    static const char hex[] = "0123456789abcdef";
    for (int i = 7; i >= 0; --i) {
        out[i] = hex[v & 0xF];   // 하위 4비트
        v >>= 4;
    }
    out[8] = '\0';
}
```

위에서부터 채우는 방식이 더 직관적이라면 시프트량을 28부터 4씩 줄여가며 처리한다. 어느 쪽이든 `& 0xF`로 4비트만 남기는 게 핵심이다. 마스킹을 안 하면 부호 확장된 상위 비트가 끼어들어 인덱스 범위를 벗어난다.

자바스크립트는 사정이 좀 다르다. 비트 연산자가 32비트 부호 있는 정수로 강제로 변환된다. `0xFFFFFFFF >> 4`는 `0x0FFFFFFF`가 아니라 `-1`이다. 부호 있는 시프트라 부호 비트가 그대로 채워지기 때문이다. 부호 없는 시프트 `>>>`를 써야 한다.

```javascript
function toHex32(v) {
    const hex = "0123456789abcdef";
    let out = "";
    for (let i = 0; i < 8; i++) {
        out = hex[v & 0xF] + out;
        v = v >>> 4;   // >> 가 아니라 >>> 를 써야 한다
    }
    return out;
}

toHex32(0xFFFFFFFF);  // "ffffffff"
toHex32(-1);          // "ffffffff" (같은 비트 패턴)
```

자바는 `Integer.toHexString`이 이미 부호 없는 처리를 해준다. 직접 구현할 일이 거의 없지만, padding이 필요할 때는 `String.format`을 써야 한다. 이건 뒤에서 따로 다룬다.


## IEEE 754 부동소수점의 16진수 분해

`1.0f`를 메모리에서 떠보면 `0x3F800000`이다. 이 숫자가 왜 이렇게 나오는지 한 번 손으로 풀어보면 IEEE 754가 더 이상 미스터리가 아니다. 32비트 single precision은 부호 1비트, 지수 8비트, 가수 23비트로 나뉜다.

```
0 01111111 00000000000000000000000
^ ^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^
| |        |
| |        가수(mantissa) 23비트: 모두 0
| 지수(exponent) 8비트: 127, 즉 bias 127을 빼면 0
부호 비트: 0 (양수)
```

값으로 환산하면 `(-1)^0 * 1.0 * 2^0 = 1.0`이다. 16진수로 묶으면 `0011 1111 1000 0000 0000 0000 0000 0000` = `0x3F800000`. C에서 `union`이나 `memcpy`로 비트 패턴을 직접 떠볼 수 있다.

```c
#include <stdio.h>
#include <string.h>
#include <stdint.h>

int main(void) {
    float f = 1.0f;
    uint32_t bits;
    memcpy(&bits, &f, sizeof(bits));
    printf("0x%08x\n", bits);  // 0x3f800000

    // 분해
    uint32_t sign     = (bits >> 31) & 0x1;
    uint32_t exponent = (bits >> 23) & 0xFF;
    uint32_t mantissa = bits & 0x7FFFFF;
    printf("sign=%u exp=%u mantissa=0x%06x\n", sign, exponent, mantissa);
    // sign=0 exp=127 mantissa=0x000000
    return 0;
}
```

자바에서는 `Float.floatToRawIntBits`가 같은 일을 한다. 자바스크립트는 `Float32Array`와 `Uint32Array`를 같은 `ArrayBuffer`에 얹어서 본다.

```javascript
const buf = new ArrayBuffer(4);
new Float32Array(buf)[0] = 1.0;
const bits = new Uint32Array(buf)[0];
console.log(bits.toString(16));  // "3f800000"
```

부동소수점 비교가 안 맞을 때, `0.1 + 0.2 !== 0.3` 같은 문제를 추적할 때 비트 패턴을 찍어보면 정확히 어디서 어긋나는지 보인다. NaN이 여러 종류라는 점도 같은 맥락이다. quiet NaN과 signaling NaN이 비트 레벨에서 다르고, payload 비트가 들어가면 16진수가 또 달라진다. `Float.intBitsToFloat(0x7FC00000)`은 표준 quiet NaN이고, `0x7F800001` 같은 건 signaling NaN이다.


## 엔디언과 hex dump가 어긋나는 이유

`0x12345678`이라는 32비트 값을 메모리에 쓰고 `xxd`로 떠보면 x86/x86_64에서는 `78 56 34 12`로 나온다. 처음 보면 무조건 당황한다. little-endian에서는 최하위 바이트(LSB)가 낮은 주소에 들어가기 때문이다. 사람이 읽기 좋은 표기 `0x12345678`(MSB가 왼쪽)와 메모리 레이아웃이 정반대다.

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint32_t x = 0x12345678;
    uint8_t *p = (uint8_t *)&x;
    for (int i = 0; i < 4; i++) {
        printf("%02x ", p[i]);
    }
    // x86_64: 78 56 34 12
    // 빅엔디언 머신: 12 34 56 78
    return 0;
}
```

네트워크 프로토콜은 보통 빅엔디언(network byte order)을 쓴다. 그래서 `htonl`, `ntohl` 같은 함수가 존재한다. 패킷 캡처를 분석하다가 `0x00000050`(= 80, HTTP 포트)이 메모리상 `00 00 00 50`으로 찍히는 걸 보고 놀라지 않으려면 엔디언을 의식해야 한다. 반대로 디스크에 저장된 바이너리 파일이 little-endian으로 기록되어 있고, 그걸 빅엔디언 머신에서 읽으면 모든 정수가 뒤집어진다.

자바스크립트의 `DataView`는 엔디언을 명시적으로 받는다. 인자를 빼먹으면 기본이 빅엔디언이라 x86 환경 기대값과 어긋난다.

```javascript
const buf = new ArrayBuffer(4);
const view = new DataView(buf);
view.setUint32(0, 0x12345678, true);  // true = little-endian
new Uint8Array(buf);                   // [0x78, 0x56, 0x34, 0x12]
view.getUint32(0, false);              // 0x78563412 (빅엔디언으로 다시 읽음)
```

엔디언 관련 버그는 코드만 봐서는 거의 안 보인다. 실제 메모리를 떠봐야 잡힌다. `printf("%08x", x)`는 항상 사람이 보기 좋은 순서로 찍어주기 때문에 엔디언 차이를 숨긴다. 바이트 단위로 찍어야 차이가 드러난다.


## 자바스크립트 정수 정밀도와 BigInt

`Number`는 IEEE 754 double이다. 가수가 52비트 + 암묵적 1비트라 안전한 정수 범위는 `Number.MAX_SAFE_INTEGER` = `2^53 - 1` = `9007199254740991`이다. 16진수로 `0x1FFFFFFFFFFFFF`. 이 위로 가면 정밀도가 깨진다.

```javascript
parseInt("FFFFFFFFFFFFFFFF", 16);  // 18446744073709552000 (정밀도 손실)
0xFFFFFFFFFFFFFFFF;                 // 18446744073709552000 (같은 문제)

BigInt("0xFFFFFFFFFFFFFFFF");       // 18446744073709551615n (정확)
0xFFFFFFFFFFFFFFFFn;                 // 18446744073709551615n
```

64비트 정수가 들어있는 외부 시스템(스네이크 ID 같은 분산 ID, 데이터베이스 BIGINT, 일부 unsigned 타임스탬프)을 다룰 때 무심코 `JSON.parse`를 호출하면 끝자리가 0으로 깎인다. 백엔드에서 64비트 ID를 문자열로 직렬화해서 내려주는 관례가 이 때문이다.

`BigInt`의 `toString(16)`은 부호를 그대로 보여준다. 음수면 `-`가 앞에 붙는다. 비트 패턴(2의 보수 표현)이 필요하다면 직접 마스킹을 해야 한다.

```javascript
const n = -1n;
n.toString(16);                          // "-1"
(BigInt.asUintN(64, n)).toString(16);    // "ffffffffffffffff"
(BigInt.asUintN(32, n)).toString(16);    // "ffffffff"
```

`asUintN(bits, value)`은 `value`를 2의 보수 표현으로 해석한 뒤 부호 없는 정수로 잘라낸다. 이게 없으면 음수 BigInt를 16진수로 dump하기 까다롭다.


## Java Integer.toHexString과 String.format

`Integer.toHexString(-1)`은 `"ffffffff"`를 반환한다. 부호 없는 32비트로 해석해서 출력한다는 뜻이다. 하지만 zero-padding은 안 한다. `Integer.toHexString(0xF)`는 `"f"` 한 글자다.

```java
Integer.toHexString(-1);        // "ffffffff"
Integer.toHexString(0xF);       // "f"
Integer.toHexString(0x12345);   // "12345"

String.format("%08x", -1);      // "ffffffff"
String.format("%08x", 0xF);     // "0000000f"  <- padding 됨
String.format("%08X", 0x12345); // "00012345"
```

로그에 16진수를 일정한 폭으로 찍어야 할 때는 `String.format("%08X", value)`를 쓴다. 메모리 주소나 해시값처럼 자릿수가 의미 있는 데이터에서 zero-padding이 빠지면 정렬이 깨지고, 같은 값이 다른 길이로 찍혀서 grep도 어려워진다. 한 가지 더, `Long.toHexString`은 64비트 부호 없는 출력을 한다. `int`와 `long`을 섞어 쓰면 출력 길이가 다르다는 점에 주의해야 한다.

`byte[]`를 hex 문자열로 변환할 때 자주 만드는 실수가 위에서 언급한 부호 확장이다. `& 0xFF`를 빼먹으면 음수 byte가 8자리 hex로 찍힌다.

```java
public static String toHex(byte[] data) {
    StringBuilder sb = new StringBuilder(data.length * 2);
    for (byte b : data) {
        sb.append(String.format("%02x", b & 0xFF));
    }
    return sb.toString();
}
```

JDK 17부터는 `HexFormat`이 추가돼서 직접 구현할 일이 줄었다. `HexFormat.of().formatHex(bytes)`를 쓰면 된다.


## Python의 바이트 단위 변환

파이썬 정수는 임의 정밀도라 자릿수 걱정이 없다. 대신 바이트 시퀀스로 다룰 때 엔디언과 부호를 명시해야 한다. `int.to_bytes`와 `int.from_bytes`가 핵심 API다.

```python
(0x12345678).to_bytes(4, 'big')      # b'\x12\x34\x56\x78'
(0x12345678).to_bytes(4, 'little')   # b'\x78\x56\x34\x12'

int.from_bytes(b'\xff\xff', 'big', signed=False)   # 65535
int.from_bytes(b'\xff\xff', 'big', signed=True)    # -1
```

`signed=True`를 깜빡하면 음수가 들어간 바이너리를 큰 양수로 해석한다. C 구조체와 호환되는 바이너리 포맷을 다룰 때 `struct` 모듈을 쓰는 게 보통 더 안전하다. 포맷 문자에 `<`(little-endian), `>`(big-endian), `=`(native), `!`(network=big-endian)을 명시할 수 있다.

```python
import struct
struct.pack('<I', 0x12345678)   # b'\x78\x56\x34\x12'
struct.pack('>I', 0x12345678)   # b'\x12\x34\x56\x78'
struct.unpack('<i', b'\xff\xff\xff\xff')  # (-1,)  소문자 i는 signed
struct.unpack('<I', b'\xff\xff\xff\xff')  # (4294967295,)  대문자 I는 unsigned
```

hex 문자열과 바이트를 오갈 때는 `bytes.fromhex` / `bytes.hex`가 편하다. 공백이나 콜론 구분자도 처리된다.

```python
bytes.fromhex('12 34 56 78')   # b'\x12\x34\x56\x78'
b'\x12\x34\x56\x78'.hex()      # '12345678'
b'\x12\x34\x56\x78'.hex(' ')   # '12 34 56 78' (Python 3.8+)
```


## 실무에서 hexdump/xxd/od 읽기

바이너리 파일을 분석할 때 가장 먼저 켜는 도구가 `hexdump`나 `xxd`다. `xxd`는 출력이 깔끔해서 선호하는 편이다.

```
$ xxd sample.bin | head -3
00000000: 8950 4e47 0d0a 1a0a 0000 000d 4948 4452  .PNG........IHDR
00000010: 0000 0100 0000 0100 0802 0000 0090 7782  ..............w.
00000020: 6300 0000 1974 4558 7465 5374 6172 7475  c....tEXtStartu
```

왼쪽부터 오프셋(16진수), 데이터(2바이트씩 그룹), ASCII 변환이다. 첫 줄 시작 `89 50 4e 47`이 PNG 매직 넘버다. `xxd -e`는 little-endian으로, `xxd -b`는 2진수로 출력한다. 특정 영역만 보려면 `xxd -s 0x100 -l 64 file` 같은 식으로 오프셋과 길이를 지정한다.

`hexdump -C`도 비슷한 출력을 준다. `od -A x -t x1z -v file`은 GNU 유틸 조합으로 가장 호환성이 좋다. 운영 서버에 `xxd`가 없을 때 쓴다.

`xxd`는 역변환도 된다. `xxd -r`로 hex dump를 다시 바이너리로 복원할 수 있어서, 작은 패치를 손으로 만들 때 쓸만하다. 다만 출력 포맷을 정확히 맞춰야 해서 큰 파일에는 권장하지 않는다.


## RGB와 16진수 변환

`#FF8800` 같은 색상 표기는 24비트(R 8비트, G 8비트, B 8비트)를 16진수로 묶은 거다. 비트 연산으로 합치고 분해하면 직관적이다.

```javascript
function rgbToHex(r, g, b) {
    const v = (r << 16) | (g << 8) | b;
    return "#" + v.toString(16).padStart(6, "0").toUpperCase();
}

function hexToRgb(hex) {
    const v = parseInt(hex.replace("#", ""), 16);
    return {
        r: (v >> 16) & 0xFF,
        g: (v >> 8) & 0xFF,
        b: v & 0xFF,
    };
}
```

`padStart(6, "0")`을 빼먹으면 검정에 가까운 색에서 자릿수가 5자리 이하로 떨어진다. `rgb(0, 0, 1)`이면 `#1`이 나온다는 뜻이다. CSS 파서가 받아주지 않는다.

CSS에는 `#RGB` 단축 표기가 있다. `#F80`은 `#FF8800`과 같다. 각 자리를 두 번 반복하는 규칙이다. 파싱할 때 길이로 분기해야 한다.

```javascript
function parseHexColor(hex) {
    hex = hex.replace("#", "");
    if (hex.length === 3) {
        hex = hex.split("").map(c => c + c).join("");
    }
    if (hex.length !== 6) throw new Error("invalid hex color");
    return parseInt(hex, 16);
}
```

알파 채널이 들어가면 `#RRGGBBAA` 또는 `#RGBA` 형태가 된다. 8자리 hex는 32비트 정수에 들어가는데, 자바스크립트의 비트 연산자는 부호 있는 32비트로 해석하기 때문에 알파 비트가 1로 시작하면 음수가 된다. `>>> 0`을 마지막에 붙여서 부호 없는 값으로 강제 변환하는 트릭을 자주 쓴다.


## UTF-8 다바이트 문자의 16진수

`'한'`이라는 글자를 UTF-8로 인코딩하면 `0xEA 0xB0 0x9C` 3바이트다. 코드포인트 U+D55C를 UTF-8 규칙에 따라 3바이트로 풀어쓴 결과다.

UTF-8 인코딩 규칙은 코드포인트 범위에 따라 다르다.

- U+0000 ~ U+007F: `0xxxxxxx` (1바이트, ASCII와 동일)
- U+0080 ~ U+07FF: `110xxxxx 10xxxxxx` (2바이트)
- U+0800 ~ U+FFFF: `1110xxxx 10xxxxxx 10xxxxxx` (3바이트)
- U+10000 ~ U+10FFFF: `11110xxx 10xxxxxx 10xxxxxx 10xxxxxx` (4바이트)

U+D55C(`한`)는 16진수로 `D55C`, 2진수로 `1101 0101 0101 1100`이다. 3바이트 템플릿 `1110xxxx 10xxxxxx 10xxxxxx`에 16비트를 4-6-6으로 잘라 넣으면 `11101101 10010101 10011100` = `0xED 0x95 0x9C`가 된다.

잠깐, 위에서 `0xEA 0xB0 0x9C`라고 했는데 계산은 `0xED 0x95 0x9C`로 나온다. 이건 한글 음절 `한`(U+D55C)과 음절 `한`(U+D55C)이 다른 게 아니라, 입력 문자열에 어떤 정규화가 들어갔느냐의 차이일 수 있다. 한글은 NFC(완성형)와 NFD(자모 분리형)가 모두 정상으로 받아들여지는데, 두 형태의 UTF-8 바이트 시퀀스가 완전히 다르다. macOS 파일 시스템은 NFD를 쓰고, 대부분의 웹/리눅스는 NFC를 쓴다. 같은 글자인데 hex가 다르게 찍힌다면 정규화 차이를 의심해야 한다.

```python
import unicodedata
unicodedata.normalize('NFC', '한').encode('utf-8').hex()  # 'ed959c'
unicodedata.normalize('NFD', '한').encode('utf-8').hex()  # 'e1848ce185a1e186abe1...' 형태
```

UTF-8 디코딩이 깨지면 보통 `0xC0`, `0xC1`, `0xF5`~`0xFF` 같은 invalid 바이트가 보이거나, 연속 바이트(`10xxxxxx`)가 와야 할 자리에 다른 패턴이 오는 식이다. hex dump를 보면서 첫 바이트의 비트 패턴으로 몇 바이트 시퀀스인지 추정할 수 있어야 한다.


## 매직 넘버로 파일 타입 판별

파일 확장자는 거짓말을 한다. `report.pdf`인데 안에는 ZIP일 수도 있고, `image.jpg`인데 PHP 스크립트가 들어있을 수도 있다. 파일의 첫 몇 바이트(매직 넘버)를 읽으면 진짜 타입을 알 수 있다.

| 포맷 | 매직 넘버 (hex) | 비고 |
|------|-----------------|------|
| JPEG | `FF D8 FF` | 다음 바이트는 마커별로 다양 (`E0`, `E1`, `DB` 등) |
| PNG | `89 50 4E 47 0D 0A 1A 0A` | 8바이트, 끝 4바이트는 라인 종결 검증용 |
| GIF | `47 49 46 38 37 61` 또는 `47 49 46 38 39 61` | "GIF87a" / "GIF89a" |
| ZIP | `50 4B 03 04` | "PK" 시그니처. JAR, DOCX, XLSX 모두 ZIP 기반 |
| PDF | `25 50 44 46` | "%PDF" |
| GZIP | `1F 8B` | |
| ELF | `7F 45 4C 46` | 리눅스 실행 파일 |
| Mach-O | `FE ED FA CE` (32비트) / `FE ED FA CF` (64비트) | macOS 실행 파일 |

ASCII 표현을 같이 외워두면 hex dump를 보자마자 식별이 쉽다. PNG의 `89 50 4E 47`에서 `50 4E 47`은 ASCII로 "PNG"다. 첫 바이트 `89`는 텍스트 파일로 잘못 열렸을 때 깨지는지 확인하려고 일부러 비ASCII 바이트를 박은 것이다.

업로드 받은 파일을 확장자만으로 판별하면 보안 사고가 난다. 백엔드에서는 파일의 첫 N 바이트를 읽어서 매직 넘버로 검증해야 한다. 파이썬 `python-magic`이나 자바 Apache Tika 같은 라이브러리를 쓰는 게 보통이지만, 내부 동작은 결국 매직 넘버 매칭이다.

```python
def sniff_image(data: bytes) -> str:
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if data.startswith(b'PK\x03\x04'):
        return 'zip'  # 또는 docx/xlsx/jar
    return 'unknown'
```

ZIP 매직 넘버를 쓰는 포맷이 많아서, ZIP을 발견했다고 끝이 아니다. 압축 해제 후 내부 구조(`[Content_Types].xml`이 있으면 OOXML, `META-INF/MANIFEST.MF`가 있으면 JAR)를 봐야 정확히 판별된다.


## 변환 시 자주 만드는 버그

손으로 변환하든 코드로 변환하든 반복적으로 만드는 실수가 있다.

**앞자리 0 누락.** 8비트 값 `0x05`를 `5`로 출력하면 두 자리 hex 시퀀스 사이에 들어갔을 때 경계가 무너진다. `0501020304`를 `5 1 2 3 4`로 받았다고 생각해보면 의미가 완전히 달라진다. zero-padding은 옵션이 아니라 필수다. `printf("%02x", b)`, `String.format("%02x", b & 0xFF)`, `value.toString(16).padStart(2, "0")`을 항상 쓴다.

**부호 비트 누락.** 위에서 다룬 부호 확장 문제다. `byte`나 `int8_t` 같은 부호 있는 타입을 부호 없는 hex로 출력할 때 마스킹을 안 하면 8자리짜리 `ffffff80`이 나온다. 출력하기 직전에 `& 0xFF`(또는 `& 0xFFFF`, `& 0xFFFFFFFFL`)를 거는 습관이 안전하다.

**짝수 자릿수 padding 누락.** hex 문자열을 바이트 배열로 다시 변환할 때 길이가 홀수면 보통 에러가 난다. 거꾸로, 바이트 배열을 hex로 만들 때 한 자리만 출력되면 다시 파싱하지 못한다. 파일이나 네트워크로 hex 문자열을 주고받는다면 항상 짝수 자릿수를 보장해야 한다.

**대소문자 혼용.** `0xFF`와 `0xff`는 같은 값이지만, 문자열 비교에서는 다르다. 해시값을 hex로 받아서 DB에 저장한 뒤 비교할 때 한쪽은 대문자 출력, 다른 쪽은 소문자 출력을 쓰면 매칭이 깨진다. 시스템 전체에서 한 가지로 통일하거나, 비교할 때 항상 소문자로 정규화한다.

**0x 접두어 처리.** `parseInt("0x1F", 16)`은 자바스크립트에서 `31`이지만, 자바의 `Integer.parseInt("0x1F", 16)`는 `NumberFormatException`이다. 자바는 접두어를 안 붙인 hex 문자열만 받는다. `Integer.decode("0x1F")`는 받아준다. 언어마다 미묘하게 다르니 외부에서 받은 hex 문자열을 파싱할 때는 접두어를 직접 잘라내고 시작하는 게 안전하다.

**부호 있는/없는 시프트 혼동.** 자바스크립트에서 `>>`와 `>>>`의 차이, 자바에서 `>>`(부호 보존)와 `>>>`(0으로 채움)의 차이를 헷갈리면 음수에서 hex 변환이 폭주한다. 16진수 변환 코드에서는 99% `>>>`(또는 `& 0xF`)가 정답이다.


## 마무리

16진수 변환은 단순해 보이지만, 부호 처리, 비트 폭, 엔디언, 부동소수점 레이아웃, 언어별 정수 모델이 모두 얽혀있는 영역이다. 디버거에서 본 16진수가 이상하게 보일 때 의심할 후보군을 미리 정리해 두면 추적 시간이 크게 줄어든다. 가장 많이 부딪히는 함정은 부호 확장(byte→int 변환에서 마스킹 누락)과 엔디언(메모리 dump가 사람이 보기 좋은 순서와 반대)이고, 두 번째로 많이 부딪히는 함정은 zero-padding 누락과 자바스크립트의 53비트 정밀도 한계다. 이 정도만 의식하면 hex dump 한두 줄로 문제의 절반은 좁힐 수 있다.
