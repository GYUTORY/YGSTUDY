

# 🚀 Node.js Stream 개념 및 설명

## 1️⃣ Node.js Stream이란?
**Stream(스트림)**은 **데이터를 작은 조각(Chunk) 단위로 읽고 쓰는 방식**입니다.  
일반적인 파일이나 데이터를 처리할 때 한꺼번에 메모리에 로드하는 방식이 아니라, **데이터를 스트리밍하여 처리 속도와 메모리 효율을 극대화**할 수 있습니다.

> **👉🏻 스트림을 사용하면 대용량 데이터 처리 시 성능을 향상시킬 수 있습니다.**

---

## 2️⃣ Node.js에서 제공하는 스트림의 유형
Node.js의 스트림은 크게 **4가지 유형**으로 나뉩니다.

### ✅ 1. Readable Stream (읽기 스트림)
- 데이터를 **읽어들이는 역할**을 하는 스트림
- 예제: 파일을 읽거나, HTTP 요청에서 데이터를 받을 때 사용

### ✅ 2. Writable Stream (쓰기 스트림)
- 데이터를 **쓰기 위한 스트림**
- 예제: 파일에 데이터를 쓰거나, HTTP 응답을 보낼 때 사용

### ✅ 3. Duplex Stream (양방향 스트림)
- **읽기와 쓰기가 동시에 가능한 스트림**
- 예제: 네트워크 소켓 (Socket) 통신

### ✅ 4. Transform Stream (변환 스트림)
- 입력 데이터를 받아 **변환하여 출력하는 스트림**
- 예제: 파일 압축(Gzip), 데이터 암호화

---

## 3️⃣ Readable Stream (읽기 스트림) 예제

### ✨ 파일을 읽어 스트림으로 출력
```javascript
const fs = require('fs');

// fs.createReadStream을 사용하여 파일을 읽기 스트림으로 열기
const readableStream = fs.createReadStream('example.txt', { encoding: 'utf8' });

// 데이터가 읽힐 때마다 실행되는 이벤트 리스너
readableStream.on('data', chunk => {
    console.log('읽은 데이터:', chunk);
});

// 스트림이 끝났을 때 실행되는 이벤트 리스너
readableStream.on('end', () => {
    console.log('파일 읽기 완료!');
});
```
> **👉🏻 위 코드는 "example.txt" 파일을 스트리밍 방식으로 읽고, 데이터가 들어올 때마다 출력하는 예제입니다.**

---

## 4️⃣ Writable Stream (쓰기 스트림) 예제

### ✨ 파일에 데이터를 스트림으로 쓰기
```javascript
const fs = require('fs');

// fs.createWriteStream을 사용하여 파일 쓰기 스트림 생성
const writableStream = fs.createWriteStream('output.txt');

// 스트림을 통해 데이터 쓰기
writableStream.write('안녕하세요, Node.js Stream!');
writableStream.write('데이터를 스트리밍 방식으로 기록합니다.
');

// 스트림 종료
writableStream.end(() => {
    console.log('파일 쓰기 완료!');
});
```
> **👉🏻 위 코드는 "output.txt" 파일에 데이터를 스트리밍 방식으로 기록하는 예제입니다.**

---

## 5️⃣ Pipe를 사용한 스트림 연결

### ✅ Pipe란?
- `pipe()` 메서드를 사용하면 **Readable Stream에서 Writable Stream으로 데이터를 바로 전달**할 수 있습니다.
- **버퍼(Buffer) 없이 효율적인 데이터 처리**가 가능함

### ✨ 예제: 파일 읽고 쓰기
```javascript
const fs = require('fs');

// 읽기 스트림 생성
const readableStream = fs.createReadStream('input.txt');

// 쓰기 스트림 생성
const writableStream = fs.createWriteStream('output.txt');

// pipe()를 사용하여 읽은 데이터를 그대로 출력 파일에 쓰기
readableStream.pipe(writableStream);

writableStream.on('finish', () => {
    console.log('파일 복사 완료!');
});
```
> **👉🏻 위 코드는 "input.txt" 파일을 읽어서 "output.txt"에 그대로 저장하는 예제입니다.**

---

## 6️⃣ Duplex Stream (양방향 스트림) 예제

### ✨ 예제: Duplex Stream 구현
```javascript
const { Duplex } = require('stream');

// 새로운 Duplex 스트림 생성
const myDuplexStream = new Duplex({
    write(chunk, encoding, callback) {
        console.log('쓰기:', chunk.toString());
        callback();
    },
    read(size) {
        this.push('읽기 스트림에서 보낸 데이터');
        this.push(null); // 스트림 종료
    }
});

// 데이터 쓰기
myDuplexStream.write('안녕하세요!');
myDuplexStream.end();

// 데이터 읽기
myDuplexStream.on('data', chunk => {
    console.log('읽기:', chunk.toString());
});
```
> **👉🏻 Duplex Stream을 사용하면 데이터를 읽고 쓸 수 있는 스트림을 직접 구현할 수 있습니다.**

---

## 7️⃣ Transform Stream (변환 스트림) 예제

### ✨ 예제: 대문자로 변환하는 Transform Stream
```javascript
const { Transform } = require('stream');

// 새로운 Transform 스트림 생성
const upperCaseTransform = new Transform({
    transform(chunk, encoding, callback) {
        this.push(chunk.toString().toUpperCase()); // 대문자로 변환
        callback();
    }
});

// 스트림을 사용하여 변환 실행
process.stdin.pipe(upperCaseTransform).pipe(process.stdout);
```
> **👉🏻 위 코드는 입력된 데이터를 대문자로 변환하여 출력하는 Transform Stream 예제입니다.**

---

## 8️⃣ Node.js Stream 사용 시 주의할 점

| 문제 | 발생 원인 | 해결 방법 |
|------|----------|----------|
| 메모리 누수 | 스트림이 제대로 종료되지 않음 | `.on('end', callback)` 사용 |
| 속도 불균형 | Readable과 Writable 속도 차이 발생 | `.pipe()`를 사용하여 자동 조정 |
| 데이터 손실 | 비정상적인 종료 | `.on('error', callback)`을 사용하여 예외 처리 |

> **👉🏻 스트림을 올바르게 사용하면 성능을 최적화할 수 있습니다!**

