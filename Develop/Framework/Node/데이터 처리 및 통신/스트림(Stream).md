
# Node.js의 스트림 (Streams)

## 스트림이란 무엇인가?
Node.js의 스트림(Stream)은 대량의 데이터를 처리하기 위해 사용되는 추상 인터페이스입니다.  
파일 읽기/쓰기, HTTP 요청/응답, TCP 소켓, 압축 작업 등 데이터가 연속적으로 처리되는 작업에서 효율적으로 사용할 수 있습니다.

### 스트림의 주요 특징
1. 데이터를 작은 청크(chunk) 단위로 처리.
2. 메모리 효율성 향상.
3. 비동기적으로 데이터 처리.

## 대분류와 중분류
Node.js 스트림은 **비동기 프로그래밍** 및 **데이터 처리** 분야에 속합니다.

### 대분류
- 비동기 프로그래밍

### 중분류
- 데이터 스트리밍
- 파일 입출력
- 네트워크 통신

## 스트림의 종류
Node.js 스트림은 4가지 유형으로 분류됩니다.
1. **Readable Stream**: 데이터를 읽을 수 있는 스트림.  
   예: 파일 읽기 스트림, HTTP 요청.
2. **Writable Stream**: 데이터를 쓸 수 있는 스트림.  
   예: 파일 쓰기 스트림, HTTP 응답.
3. **Duplex Stream**: 데이터를 읽고 쓸 수 있는 스트림.  
   예: TCP 소켓.
4. **Transform Stream**: 데이터를 읽고 변환하여 출력하는 스트림.  
   예: 압축, 암호화.

## 스트림의 이벤트
Node.js 스트림은 다양한 이벤트를 제공합니다.
- `data`: 새로운 데이터 청크를 읽을 때 발생.
- `end`: 읽기가 완료되었을 때 발생.
- `error`: 오류가 발생했을 때 발생.
- `finish`: 쓰기가 완료되었을 때 발생.

## 스트림 사용 예제

### 파일 읽기 스트림과 쓰기 스트림
```javascript
const fs = require('fs');

// 읽기 스트림 생성
const readableStream = fs.createReadStream('input.txt', { encoding: 'utf8' });

// 쓰기 스트림 생성
const writableStream = fs.createWriteStream('output.txt');

// 데이터 처리
readableStream.on('data', (chunk) => {
    console.log('읽은 데이터:', chunk);
    writableStream.write(chunk.toUpperCase()); // 데이터를 대문자로 변환하여 저장
});

readableStream.on('end', () => {
    console.log('읽기가 완료되었습니다.');
    writableStream.end(); // 쓰기 종료
});

readableStream.on('error', (err) => {
    console.error('오류 발생:', err);
});
```

### 파이프와 체이닝
Node.js 스트림은 파이프(pipe) 메서드를 사용해 데이터를 다른 스트림으로 쉽게 전달할 수 있습니다.

#### 예: 파일 압축
```javascript
const fs = require('fs');
const zlib = require('zlib');

// 읽기 스트림, 쓰기 스트림, 변환 스트림 생성
const readableStream = fs.createReadStream('input.txt');
const gzipStream = zlib.createGzip();
const writableStream = fs.createWriteStream('input.txt.gz');

// 파이프를 사용한 데이터 처리
readableStream.pipe(gzipStream).pipe(writableStream);

writableStream.on('finish', () => {
    console.log('파일 압축 완료');
});
```

## 스트림의 장점
1. **메모리 효율성**: 대량의 데이터를 한꺼번에 메모리에 로드하지 않음.
2. **성능 향상**: 데이터 처리와 전송을 동시에 수행.
3. **확장성**: 네트워크 애플리케이션과 같은 대규모 시스템에서 효율적.

## 스트림을 사용해야 하는 경우
- 대용량 파일 처리.
- 실시간 데이터 전송.
- 네트워크 통신(예: HTTP 요청/응답).
- 데이터 변환(압축, 암호화 등).

## 결론
Node.js 스트림은 대량의 데이터를 효율적으로 처리할 수 있는 강력한 도구입니다.  
이를 통해 메모리와 CPU 사용량을 최적화하고, 비동기 처리의 이점을 극대화할 수 있습니다.
