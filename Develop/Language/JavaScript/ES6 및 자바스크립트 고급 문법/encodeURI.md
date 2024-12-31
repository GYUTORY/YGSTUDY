

# encodeURI()
- encodeURI() 함수는 URI의 특정한 문자를 UTF-8로 인코딩해 하나, 둘, 셋, 혹은 네 개의 연속된 이스케이프 문자로 나타냅니다. (두 개의 대리 문자로 이루어진 문자만 이스케이프 문자 네 개로 변환됩니다.)

```javascript
const uri = 'https://mozilla.org/?x=шеллы';
const encoded = encodeURI(uri);
console.log(encoded);
// Expected output: "https://mozilla.org/?x=%D1%88%D0%B5%D0%BB%D0%BB%D1%8B"

try {
    console.log(decodeURI(encoded));
    // Expected output: "https://mozilla.org/?x=шеллы"
} catch (e) {
    // Catches a malformed URI
    console.error(e);
}
```
결과

    > "https://mozilla.org/?x=%D1%88%D0%B5%D0%BB%D0%BB%D1%8B"
    > "https://mozilla.org/?x=шеллы"


## 정리
- encodeURI()는 완전한 URI를 형성하는데 필요한 문자는 인코딩 하지 않습니다. 
- 또한, 예약된 목적을 가지지는 않지만 URI가 그대로 포함할 수 있는 몇 가지 문자도 인코딩 하지 않습니다. 

### encodeURI()는 다음 문자를 제외한 문자를 이스케이프

    이스케이프 하지 않는 문자
    A-Z a-z 0-9 ; , / ? : @ & = + $ - _ . ! ~ * ' ( ) #


## encodeURI()와 encodeURIComponent()의 차이

```javascript
var set1 = ";,/?:@&=+$#"; // 예약 문자
var set2 = "-_.!~*'()"; // 비예약 표식
var set3 = "ABC abc 123"; // 알파벳 및 숫자, 공백

console.log(encodeURI(set1)); // ;,/?:@&=+$#
console.log(encodeURI(set2)); // -_.!~*'()
console.log(encodeURI(set3)); // ABC%20abc%20123 (공백은 %20으로 인코딩)

console.log(encodeURIComponent(set1)); // %3B%2C%2F%3F%3A%40%26%3D%2B%24%23
console.log(encodeURIComponent(set2)); // -_.!~*'()
console.log(encodeURIComponent(set3)); // ABC%20abc%20123 (공백은 %20으로 인코딩)
```

> encodeURI() 혼자서는 XMLHttpRequest 등이 사용할, 적합한 HTTP GET과 POST 요청을 구성할 수 없습니다. GET과 POST에서 특별한 문자로 취급하는 "&", "+", "="를 인코딩 하지 않기 때문입니다. 그러나 encodeURIComponent()는 저 세 문자도 인코딩 대상에 포함합니다.


### 상위-하위 쌍을 이루지 않은 단일 대리 문자를 인코딩 시도하면 URIError가 발생
```javascript
// high-low pair ok
console.log(encodeURIComponent("\uD800\uDFFF"));

// lone high surrogate throws "URIError: malformed URI sequence"
console.log(encodeURIComponent("\uD800"));

// lone low surrogate throws "URIError: malformed URI sequence"
console.log(encodeURIComponent("\uDFFF"));
```





