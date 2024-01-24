

# Buffer
- Node.js의 Buffer는 이진 데이터를 다루는데 사용되는 객체입니다.
- 이진 데이터는 텍스트나 이미지와 같은 파일에서 읽거나 네트워크를 통해 전송할 때 주로 사용됩니다.
- Buffer는 고정 크기의 이진 데이터 배열을 나타내며, 메모리에서 할당된 버퍼의 크기는 변경할 수 없습니다.

```javascript
// ASCII 문자열을 Buffer로 변환
const asciiString = "Hello, World!";
const bufferFromAscii = Buffer.from(asciiString, 'ascii');

console.log("Buffer from ASCII: ", bufferFromAscii);

// Buffer를 ASCII 문자열로 변환
const buffer = Buffer.from([72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33]);
const asciiStringFromBuffer = buffer.toString('ascii');

console.log("ASCII string from Buffer: ", asciiStringFromBuffer);
```


# Binary Data ?
- 우리는 컴퓨터가 이진수로 데이터를 저장하고 표현한다는걸 이미 알고있습니다. 이진수는 단순히 1과 0의 집합입니다.
- 예를들어, 다음은 서로 다른 이진수 5개이며, 이 이진수들은 서로다른 1과 0의 집합입니다.

> 10, 01, 001, 1110, 00101011

- 각각 이진수에서 1 혹은 0으로 되어있는 자리를 비트(bit)라고 합니다. 이는 Binary digIT의 약자입니다.


# Stream
- Node.js 에서의 스트림은 간단하게 한 지점에서 다른 지점으로 이동하는 일련의 데이터를 의미합니다.
- 전체적인 의미로는, 만약 우리가 어떤 방대한 양의 데이터를 처리해야 할때, 모든 데이터가 전부다 사용가능 할때까지 기다리지 않아도 된다는 것입니다.
- 기본적으로 큰 데이터는 청크단위로 세분화되어 전송됩니다. 이말은, 처음 설명했던 Buffer의 정의에 따르면, 파일시스템에서 바이너리 데이터들이 이동한다는걸 의미합니다.
- 예를들어, file1.txt의 텍스트를 file2.txt로 옮기는 걸 의미합니다.
- 하지만, Streaming 하는동안에 buffer라는 것이 어떻게 바이너리 데이터를 다룰 수 있게 도와준다는 것일까요? 정확히 buffer는 무엇일까요?

# Buffer
- 일반적으로 데이터의 이동은 그 데이터를 가지고 작업을 하거나, 그 데이터를 읽거나, 무언가를 하기 위해 일어납니다. 
- 하지만 한 작업이 특정시간동안 데이터를 받을 수 있는 데이터의 최소량과 최대량이 존재합니다. 그래서 만약에 한 작업이 데이터를 처리하는 시간보다 데이터가 도착하는 게 더 빠르다면, 초과된 데이터는 어디에선가 처리되기를 기다리고 있어야 합니다.
- 데이터를 처리하는 시간보다 훨씬빠르게 계속해서 새로운 데이터가 도착하면 어딘가에는 도착한 데이터들이 미친듯이 쌓일것이기 때문이죠.

> 바로 그 기다리는 영역이 buffer


# 버퍼다루기
```javascript
// size가 10인 빈 buffer를 만듭니다.  
// 이 버퍼는 오직 10 byte만 담을 수 있습니다.
const buf1 = Buffer.alloc(10);

// buffer 에 데이터를 담아 만듭니다.
const buf2 = Buffer.from("hello buffer");
```

```javascript
// 버퍼구조를 조사합니다.

buf1.toJSON();
// { type: 'Buffer', data: [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 ] }
// 빈 버퍼입니다

buf2.toJSON();
//  { type: 'Buffer',
      data: [ 
        104, 101, 108, 108, 111, 32, 98, 117, 102, 102, 101, 114 
      ] 
    }

// toJSON 메서드는 데이터를 Unicode Code Points 로 표현합니다.

// 버퍼의 크기를 조사합니다.

buf1.length // 10

buf2.length // 12. 파라미터로 넣어주었던 content에 따라 자동으로 크기가 할당됩니다.

// 버퍼에 쓰기
buf1.write("Buffer really rocks!");


// 버퍼를 Decoding 합니다.

buf1.toString(); // 'Buffer rea'

// buf1 은 10 byte 밖에 담을 수 없기 때문에, 나머지 문자들은 할당할 수 없습니다.

```


> 출처 : https://tk-one.github.io/2018/08/28/nodejs-buffer/