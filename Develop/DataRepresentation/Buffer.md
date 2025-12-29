---
title: Buffer 
tags: [datarepresentation, buffer]
updated: 2025-12-29
---

# Buffer (버퍼)

## 정의

버퍼(Buffer)는 컴퓨터 시스템에서 데이터를 임시로 저장하는 메모리 공간입니다. 데이터 생산자와 소비자 간의 속도 차이를 완화하는 중간 저장소 역할을 합니다.

### 버퍼가 필요한 이유

CPU는 나노초 단위로 동작하는 반면, 하드디스크는 밀리초 단위로 동작합니다. 이러한 속도 차이로 인한 병목 현상을 버퍼가 해결합니다.

## 주요 기능

### 1. 속도 차이 완화
빠른 장치에서 나오는 데이터를 임시로 저장했다가, 느린 장치가 처리할 수 있는 속도로 전달합니다.

### 2. 데이터 일관성 보장
네트워크 통신이나 파일 I/O에서 데이터가 손실되거나 순서가 바뀌는 것을 방지합니다.

### 3. 시스템 효율성 향상
CPU가 다른 작업을 수행하는 동안 버퍼에서 데이터를 처리하여 시스템 리소스를 효율적으로 활용합니다.

## 버퍼의 종류

### 하드웨어 레벨

**키보드 버퍼**
- 빠른 타이핑 입력을 임시 저장
- CPU가 처리할 수 있을 때 순차적으로 전달

**프린터 버퍼**
- 컴퓨터의 빠른 전송 속도와 프린터의 느린 처리 속도 조절
- 컴퓨터가 다른 작업을 계속 수행할 수 있게 함

### 소프트웨어 레벨

**파일 I/O 버퍼**
```javascript
const fs = require('fs');

// 버퍼를 사용한 파일 읽기
const buffer = Buffer.alloc(1024);
fs.open('file.txt', 'r', (err, fd) => {
  fs.read(fd, buffer, 0, buffer.length, 0, (err, bytes) => {
    console.log(buffer.toString('utf8', 0, bytes));
  });
});
```

**네트워크 버퍼**
```javascript
const net = require('net');

const server = net.createServer((socket) => {
  // 수신 버퍼
  socket.on('data', (buffer) => {
    console.log('Received:', buffer.toString());
  });
  
  // 송신 버퍼
  socket.write(Buffer.from('Hello'));
});
```

## 버퍼 관리 전략

### 순환 버퍼 (Circular Buffer)

고정된 크기의 메모리를 원형으로 구성하여, 데이터가 버퍼의 끝에 도달하면 다시 시작 부분으로 돌아가는 방식입니다.

```javascript
class CircularBuffer {
  constructor(size) {
    this.buffer = new Array(size);
    this.size = size;
    this.head = 0;
    this.tail = 0;
    this.count = 0;
  }

  write(data) {
    if (this.count === this.size) {
      throw new Error('Buffer overflow');
    }
    this.buffer[this.tail] = data;
    this.tail = (this.tail + 1) % this.size;
    this.count++;
  }

  read() {
    if (this.count === 0) {
      throw new Error('Buffer underflow');
    }
    const data = this.buffer[this.head];
    this.head = (this.head + 1) % this.size;
    this.count--;
    return data;
  }
}
```

### 더블 버퍼링 (Double Buffering)

두 개의 버퍼를 번갈아가며 사용하는 방식으로, 한 버퍼에서 데이터를 읽는 동안 다른 버퍼에 데이터를 씁니다.

## Node.js Buffer API

### Buffer 생성

```javascript
// 크기 지정 (초기화 안됨)
const buf1 = Buffer.alloc(10);

// 문자열로부터 생성
const buf2 = Buffer.from('Hello', 'utf8');

// 배열로부터 생성
const buf3 = Buffer.from([0x48, 0x65, 0x6c, 0x6c, 0x6f]);
```

### Buffer 조작

```javascript
const buf = Buffer.from('Hello World');

// 길이
console.log(buf.length); // 11

// 문자열 변환
console.log(buf.toString()); // 'Hello World'
console.log(buf.toString('hex')); // 48656c6c6f20576f726c64

// 비교
const buf1 = Buffer.from('abc');
const buf2 = Buffer.from('abc');
console.log(buf1.equals(buf2)); // true

// 복사
const buf3 = Buffer.alloc(11);
buf.copy(buf3);
```

## 성능 최적화

### 버퍼 풀링

```javascript
class BufferPool {
  constructor(size, count) {
    this.size = size;
    this.pool = [];
    for (let i = 0; i < count; i++) {
      this.pool.push(Buffer.alloc(size));
    }
  }

  acquire() {
    return this.pool.pop() || Buffer.alloc(this.size);
  }

  release(buffer) {
    if (buffer.length === this.size) {
      this.pool.push(buffer);
    }
  }
}

// 사용 예시
const pool = new BufferPool(1024, 10);
const buf = pool.acquire();
// ... 버퍼 사용 ...
pool.release(buf);
```

## 참고

### 버퍼 크기 최적화

| 사용 사례 | 권장 버퍼 크기 | 이유 |
|----------|---------------|------|
| 파일 읽기 | 64KB - 1MB | I/O 효율성과 메모리 사용 균형 |
| 네트워크 전송 | 16KB - 64KB | TCP 윈도우 크기 고려 |
| 스트리밍 | 256KB - 1MB | 끊김 없는 재생 |

### 관련 문서
- [Node.js Buffer API](https://nodejs.org/api/buffer.html)
- [TCP Window Scaling](https://tools.ietf.org/html/rfc1323)
- Operating System Concepts - Silberschatz
