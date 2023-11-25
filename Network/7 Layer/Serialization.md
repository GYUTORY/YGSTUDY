
## Serialization란?
- 직렬화(Serialization)는 데이터를 바이트 스트림 또는 다른 형태로 변환하여 저장하거나 전송하는 프로세스를 의미합니다. 
- 이는 객체나 데이터를 문자열 또는 이진 형식으로 변환하여, 나중에 다시 해당 객체나 데이터로 역직렬화(Deserialization)할 수 있도록 하는 작업입니다. 


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
