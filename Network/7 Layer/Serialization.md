
## Serialization란?
- 직렬화(Serialization)는 데이터를 바이트 스트림 또는 다른 형태로 변환하여 저장하거나 전송하는 프로세스를 의미합니다. 
- 이는 객체나 데이터를 문자열 또는 이진 형식으로 변환하여, 나중에 다시 해당 객체나 데이터로 역직렬화(Deserialization)할 수 있도록 하는 작업입니다. 

### 직렬화의 장점
- 객체를 효율적으로 저장하거나 전송할 수 있습니다.
- 객체를 다른 플랫폼이나 언어로 이동할 수 있습니다.


### 직렬화의 단점
- 객체의 크기가 커질 수 있습니다.
- 객체의 데이터가 손실될 수 있습니다.

### 직렬화의 종류
#### 1. 문자열 직렬화 
- 데이터를 문자열로 변환하여 저장하거나 전송하는 방식입니다. JSON, XML 등이 대표적인 문자열 직렬화 방식입니다.
#### 2. 이진 직렬화
- 데이터를 이진 형식으로 변환하여 저장하거나 전송하는 방식입니다. 
- 이진 직렬화는 문자열 직렬화보다 효율적이지만, 데이터의 호환성이 떨어질 수 있습니다.


```javascript
/** 직렬화 **/ 

const fs = require('fs');

// 직렬화할 객체
const dataToSerialize = {
  name: 'John Doe',
  age: 30,
  city: 'Example City'
};

// 객체를 JSON 문자열로 직렬화
const serializedData = JSON.stringify(dataToSerialize);

// 직렬화된 데이터를 파일에 저장
fs.writeFileSync('serializedData.json', serializedData);
console.log('Serialization complete.');
```

이 코드는 다음과 같이 동작합니다.

1. dataToSerialize라는 이름의 객체를 생성합니다.
2. dataToSerialize 객체를 JSON 문자열로 직렬화합니다.
3. 직렬화된 데이터를 serializedData.json 파일에 저장합니다.


```javascript
/** 역직렬화 **/
const fs = require('fs');

// 저장된 직렬화된 데이터를 읽어옴
const serializedData = fs.readFileSync('serializedData.json', 'utf8');

// JSON 문자열을 객체로 역직렬화
const deserializedData = JSON.parse(serializedData);

// 역직렬화된 객체 출력
console.log('Deserialized Data:', deserializedData);

```

이 코드는 다음과 같이 동작합니다.

1. serializedData.json 파일에서 직렬화된 데이터를 읽어옵니다.
2. JSON 문자열을 객체로 역직렬화합니다.
3. 역직렬화된 객체를 출력합니다.