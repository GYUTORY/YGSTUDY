---
title: Buffer
tags: [datarepresentation, buffer, java, nodejs, python]
updated: 2026-03-25
---

# Buffer (버퍼)

## 정의

버퍼는 데이터를 임시로 저장하는 메모리 공간이다. CPU는 나노초 단위로 동작하고 디스크는 밀리초 단위로 동작하는데, 이 속도 차이를 메꾸는 중간 저장소가 버퍼다.

네트워크 소켓에서 데이터를 읽을 때, 파일을 쓸 때, 스트림을 처리할 때 — 결국 I/O가 끼는 곳이면 어디든 버퍼가 있다.

## 버퍼의 동작 방식

### 순환 버퍼 (Ring Buffer)

고정 크기 메모리를 원형으로 돌려쓰는 구조다. 네트워크 패킷 수신, 로그 수집, 오디오 스트리밍 같은 곳에서 쓴다. 커널의 소켓 버퍼도 내부적으로 이 구조다.

```java
// Java로 구현한 Ring Buffer (개념 이해용)
public class RingBuffer<T> {
    private final Object[] buffer;
    private int head = 0;
    private int tail = 0;
    private int count = 0;

    public RingBuffer(int capacity) {
        this.buffer = new Object[capacity];
    }

    public void write(T data) {
        if (count == buffer.length) {
            throw new BufferOverflowException();
        }
        buffer[tail] = data;
        tail = (tail + 1) % buffer.length;
        count++;
    }

    @SuppressWarnings("unchecked")
    public T read() {
        if (count == 0) {
            throw new BufferUnderflowException();
        }
        T data = (T) buffer[head];
        head = (head + 1) % buffer.length;
        count--;
        return data;
    }
}
```

### 더블 버퍼링 (Double Buffering)

두 개의 버퍼를 번갈아 쓰는 방식이다. 한쪽에서 읽는 동안 다른 쪽에 쓴다. GPU 렌더링의 프레임 버퍼가 대표적인 예시고, 데이터베이스 WAL(Write-Ahead Log)도 비슷한 원리다.

---

## Java NIO ByteBuffer

Java에서 네트워크/파일 I/O를 다룰 때 가장 많이 쓰는 버퍼다. Netty, Kafka, Elasticsearch 같은 프레임워크 내부를 보면 전부 ByteBuffer 기반이다.

### Heap vs Direct

```java
// Heap Buffer — JVM 힙에 할당. GC 대상.
ByteBuffer heapBuf = ByteBuffer.allocate(1024);

// Direct Buffer — OS 네이티브 메모리에 할당. GC 대상 아님.
ByteBuffer directBuf = ByteBuffer.allocateDirect(1024);
```

Heap Buffer는 JVM이 관리하는 byte[] 배열 위에 만들어진다. 할당/해제가 빠르고 디버깅도 쉽다.

Direct Buffer는 JVM 힙 밖 네이티브 메모리에 할당된다. 커널과 데이터를 주고받을 때 복사가 한 번 줄어든다(zero-copy). 대신 할당 비용이 크고, 메모리 누수가 나면 원인 찾기가 어렵다.

### position, limit, capacity

ByteBuffer에는 세 가지 포인터가 있다. 이걸 제대로 이해하지 않으면 데이터가 잘리거나 빈 값을 읽는 버그가 생긴다.

```java
ByteBuffer buf = ByteBuffer.allocate(10);  // capacity=10, position=0, limit=10

buf.put((byte) 0x41);  // 'A' 쓰기. position=1
buf.put((byte) 0x42);  // 'B' 쓰기. position=2

// 쓰기 → 읽기 전환. 이걸 빼먹으면 position~limit 사이에 아무것도 없어서 빈 값을 읽는다.
buf.flip();  // position=0, limit=2

byte a = buf.get();  // 0x41, position=1
byte b = buf.get();  // 0x42, position=2

// 다시 쓰기 모드로 돌리려면
buf.clear();     // position=0, limit=capacity — 데이터 덮어쓸 때
buf.compact();   // 아직 안 읽은 데이터를 앞으로 밀고 그 뒤부터 쓸 때
```

`flip()` 빼먹는 건 ByteBuffer 입문자가 가장 많이 하는 실수다. 네트워크 코드에서 이걸 빼먹으면 빈 패킷이 나가서 상대방이 아무 데이터도 못 받는다.

### 파일 I/O — FileChannel과 함께

```java
try (FileChannel channel = FileChannel.open(
        Path.of("data.bin"), StandardOpenOption.READ)) {

    ByteBuffer buf = ByteBuffer.allocate(8192);

    while (channel.read(buf) != -1) {
        buf.flip();
        // buf에서 데이터 처리
        processData(buf);
        buf.compact();  // 처리 안 된 잔여 데이터 보존
    }
}
```

`clear()` 대신 `compact()`를 쓰는 이유가 있다. 한 번의 read로 메시지가 딱 맞게 들어오는 경우는 드물다. 메시지 경계가 버퍼 중간에 걸리면 뒷부분을 보존해야 다음 read에서 이어붙일 수 있다.

### 네트워크 I/O — SocketChannel과 함께

```java
SocketChannel channel = SocketChannel.open();
channel.configureBlocking(false);
channel.connect(new InetSocketAddress("example.com", 8080));

ByteBuffer sendBuf = ByteBuffer.wrap("GET / HTTP/1.1\r\n\r\n".getBytes());
ByteBuffer recvBuf = ByteBuffer.allocate(4096);

// Non-blocking write — 한 번에 다 안 나갈 수 있다
while (sendBuf.hasRemaining()) {
    channel.write(sendBuf);
}

// Non-blocking read
int bytesRead = channel.read(recvBuf);
if (bytesRead > 0) {
    recvBuf.flip();
    byte[] data = new byte[recvBuf.remaining()];
    recvBuf.get(data);
    System.out.println(new String(data));
}
```

### MappedByteBuffer — 대용량 파일 처리

수 GB짜리 파일을 읽어야 할 때, 전부 메모리에 올리면 OOM이 난다. `MappedByteBuffer`는 파일을 메모리에 매핑해서 OS의 가상 메모리 시스템이 페이지 단위로 알아서 로드/언로드하게 한다.

```java
try (FileChannel channel = FileChannel.open(Path.of("huge_file.dat"))) {
    // 파일 전체를 메모리 매핑 — 실제로 메모리를 다 쓰지는 않는다
    MappedByteBuffer mapped = channel.map(
        FileChannel.MapMode.READ_ONLY, 0, channel.size());

    // 특정 오프셋의 데이터에 바로 접근
    mapped.position(1024);
    int value = mapped.getInt();
}
```

Kafka가 로그 세그먼트를 읽을 때 이 방식을 쓴다. 다만 `MappedByteBuffer`는 명시적으로 해제하는 API가 없어서(Java 19 이전), 매핑한 파일을 삭제하려고 하면 Windows에서 파일 락이 걸리는 문제가 있다.

---

## Node.js Buffer

Node.js의 Buffer는 V8 힙 밖에 할당되는 고정 크기 바이너리 데이터 컨테이너다. 문자열 인코딩 변환, 바이너리 프로토콜 파싱, 스트림 처리에서 쓴다.

### 생성

```javascript
// 0으로 초기화된 버퍼
const buf1 = Buffer.alloc(1024);

// 초기화 안 된 버퍼 — 이전 메모리 값이 남아있을 수 있다
// 성능이 중요하고, 어차피 바로 덮어쓸 때만 사용
const buf2 = Buffer.allocUnsafe(1024);

// 문자열/배열로부터 생성
const buf3 = Buffer.from('Hello', 'utf8');
const buf4 = Buffer.from([0x48, 0x65, 0x6c, 0x6c, 0x6f]);
```

`Buffer.allocUnsafe()`는 이름 그대로 안전하지 않다. 이전에 다른 프로세스가 쓴 메모리 내용이 남아있을 수 있어서, 초기화 없이 외부로 보내면 메모리 내용이 유출될 수 있다. 성능이 중요하고 바로 데이터를 채울 때만 쓴다.

### 스트림에서의 버퍼 처리

```javascript
const fs = require('fs');
const crypto = require('crypto');

// 파일을 스트림으로 읽으면서 해시 계산
const hash = crypto.createHash('sha256');
const stream = fs.createReadStream('large_file.dat');

stream.on('data', (chunk) => {
    // chunk는 Buffer 인스턴스
    hash.update(chunk);
});

stream.on('end', () => {
    console.log(hash.digest('hex'));
});
```

### 바이너리 프로토콜 파싱

```javascript
// 네트워크에서 받은 패킷 파싱 예시
// 프로토콜: [타입 1byte][길이 2byte][페이로드 N bytes]
function parsePacket(buf) {
    const type = buf.readUInt8(0);
    const length = buf.readUInt16BE(1);  // Big Endian
    const payload = buf.subarray(3, 3 + length);

    return { type, length, payload };
}

// 패킷 생성
function createPacket(type, payload) {
    const buf = Buffer.alloc(3 + payload.length);
    buf.writeUInt8(type, 0);
    buf.writeUInt16BE(payload.length, 1);
    payload.copy(buf, 3);
    return buf;
}
```

### Buffer.concat의 함정

TCP 스트림에서 데이터를 모을 때 `Buffer.concat()`을 반복 호출하는 패턴이 있는데, 매번 새 버퍼를 할당하고 복사하기 때문에 데이터가 많으면 심각하게 느려진다.

```javascript
// 나쁜 예 — O(n^2) 복사 발생
let result = Buffer.alloc(0);
socket.on('data', (chunk) => {
    result = Buffer.concat([result, chunk]);  // 매번 전체 복사
});

// 나은 예 — 배열에 모아두고 마지막에 한 번만 합치기
const chunks = [];
let totalLength = 0;
socket.on('data', (chunk) => {
    chunks.push(chunk);
    totalLength += chunk.length;
});
socket.on('end', () => {
    const result = Buffer.concat(chunks, totalLength);
});
```

---

## Python bytes, bytearray, memoryview

Python에서 바이너리 데이터를 다루는 세 가지 타입이 있다.

### bytes와 bytearray

```python
# bytes — 불변(immutable). 한번 만들면 수정 불가.
data = b'\x48\x65\x6c\x6c\x6f'
data = bytes.fromhex('48656c6c6f')

# bytearray — 가변(mutable). 수정 가능.
buf = bytearray(1024)         # 0으로 초기화된 1KB 버퍼
buf[0:5] = b'Hello'
buf.append(0x21)
```

bytes와 bytearray 중 뭘 쓸지는 간단하다. 수정할 필요 없으면 `bytes`, 수정해야 하면 `bytearray`.

### memoryview — 복사 없이 버퍼 접근

`memoryview`는 기존 바이너리 데이터의 일부를 복사 없이 참조할 수 있게 해주는 객체다. 대용량 데이터에서 슬라이싱할 때 `bytes` 슬라이싱과 결정적인 차이가 있다.

```python
data = bytearray(1024 * 1024)  # 1MB

# 슬라이싱하면 복사가 일어난다 — 500KB 복사
chunk = data[0:512 * 1024]

# memoryview는 복사 없이 같은 메모리를 참조한다
view = memoryview(data)
chunk_view = view[0:512 * 1024]  # 복사 없음, 같은 메모리 참조
```

네트워크 서버에서 패킷을 파싱할 때, 매번 슬라이싱으로 복사하면 GC 부담이 커진다. `memoryview`를 쓰면 파싱 단계에서 메모리 할당이 거의 없다.

### struct 모듈 — 바이너리 프로토콜 파싱

```python
import struct

# C 구조체 형태의 바이너리 데이터 파싱
# 프로토콜: [타입 1byte][길이 2byte BE][페이로드]
def parse_packet(data: bytes) -> dict:
    header = struct.unpack('>BH', data[:3])  # Big Endian: unsigned char + unsigned short
    msg_type, length = header
    payload = data[3:3 + length]
    return {'type': msg_type, 'length': length, 'payload': payload}

# 패킷 생성
def create_packet(msg_type: int, payload: bytes) -> bytes:
    header = struct.pack('>BH', msg_type, len(payload))
    return header + payload
```

### 파일 I/O에서의 버퍼 제어

```python
# 기본 — Python이 알아서 버퍼링
with open('data.bin', 'rb') as f:
    data = f.read(8192)

# 버퍼링 비활성화 — 실시간 로그 같은 경우
with open('realtime.log', 'wb', buffering=0) as f:
    f.write(b'event happened\n')  # 즉시 디스크에 쓴다

# 버퍼 크기 지정
with open('data.bin', 'rb', buffering=65536) as f:  # 64KB 버퍼
    for line in f:
        process(line)
```

---

## 실무에서 겪는 버퍼 문제들

### OOM (Out of Memory)

버퍼 관련 OOM은 대부분 "얼마나 들어올지 모르는 데이터를 메모리에 전부 올리려고 할 때" 발생한다.

**Java Direct Buffer OOM**

```
java.lang.OutOfMemoryError: Direct buffer memory
```

Direct ByteBuffer는 JVM 힙이 아닌 네이티브 메모리에 할당된다. `-Xmx`로 힙 크기를 아무리 늘려도 이 에러는 안 잡힌다. `-XX:MaxDirectMemorySize`를 별도로 설정해야 한다.

```bash
# 힙 2GB, Direct 메모리 512MB
java -Xmx2g -XX:MaxDirectMemorySize=512m -jar app.jar
```

Direct Buffer는 GC가 직접 수거하지 않는다. `Cleaner`가 GC 시점에 연동되어 해제하는데, GC 주기가 길면 네이티브 메모리가 꽉 찰 수 있다. Netty 같은 프레임워크가 자체 메모리 풀(`PooledByteBufAllocator`)을 쓰는 이유가 이것이다.

**Node.js 스트림 배압(Backpressure) 무시**

```javascript
// 나쁜 예 — readable에서 읽기만 하고 writable의 처리 속도를 무시
readable.on('data', (chunk) => {
    writable.write(chunk);  // writable이 느리면 내부 버퍼가 계속 쌓인다
});

// 나은 예 — pipe가 알아서 배압 처리
readable.pipe(writable);

// 또는 수동으로 배압 처리
readable.on('data', (chunk) => {
    const canContinue = writable.write(chunk);
    if (!canContinue) {
        readable.pause();
        writable.once('drain', () => readable.resume());
    }
});
```

`pipe()`를 안 쓰고 직접 이벤트로 처리할 때 배압 제어를 빠뜨리면, 소스가 빠르고 대상이 느린 경우 Node.js 프로세스 메모리가 수 GB까지 올라간다.

### 버퍼 크기를 잘못 잡았을 때

**너무 작게 잡은 경우**

```java
// 8바이트 버퍼로 파일 읽기 — syscall이 미친 듯이 호출된다
ByteBuffer buf = ByteBuffer.allocate(8);
while (channel.read(buf) != -1) {
    buf.flip();
    // ...
    buf.clear();
}
```

1MB 파일을 읽는데 syscall이 131,072번 발생한다. 8KB로 바꾸면 128번이면 끝난다. 파일 I/O 버퍼는 최소 8KB, 보통 64KB~256KB가 적절하다.

**너무 크게 잡은 경우**

```java
// 요청마다 10MB 버퍼 할당 — 동시 요청 100개면 1GB
ByteBuffer buf = ByteBuffer.allocateDirect(10 * 1024 * 1024);
```

요청당 필요한 데이터가 평균 1KB인데 최대 10MB까지 올 수 있다는 이유로 10MB씩 할당하면, 동시 요청이 늘어날 때 메모리가 폭발한다. 작은 초기 버퍼에서 시작해서 필요할 때 늘리거나, 풀링을 써야 한다.

### Zero-Copy

일반적인 파일 전송 흐름은 이렇다:

```
디스크 → 커널 버퍼 → 유저 버퍼 → 소켓 버퍼 → NIC
         (1번 복사)    (2번 복사)    (3번 복사)
```

zero-copy는 유저 공간 복사를 건너뛴다:

```
디스크 → 커널 버퍼 → NIC
         (1번 복사만)
```

**Java — FileChannel.transferTo**

```java
// 파일을 소켓으로 전송 — OS의 sendfile() syscall 사용
FileChannel fileChannel = FileChannel.open(Path.of("video.mp4"));
SocketChannel socketChannel = SocketChannel.open(
    new InetSocketAddress("client", 8080));

// 유저 공간 복사 없이 커널에서 바로 전송
long transferred = fileChannel.transferTo(0, fileChannel.size(), socketChannel);
```

Kafka가 컨슈머에게 메시지를 보낼 때 이 방식을 쓴다. 파일 → 소켓 전송에서 CPU 사용량과 메모리 복사를 크게 줄인다.

**Python — os.sendfile**

```python
import os
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('client', 8080))

with open('video.mp4', 'rb') as f:
    # 커널 레벨 zero-copy 전송
    os.sendfile(sock.fileno(), f.fileno(), 0, os.path.getsize('video.mp4'))
```

**Node.js — 스트림 파이프라인**

```javascript
const fs = require('fs');
const http = require('http');

http.createServer((req, res) => {
    // pipe는 내부적으로 가능하면 zero-copy를 시도한다
    const stream = fs.createReadStream('video.mp4');
    stream.pipe(res);
}).listen(8080);
```

### 버퍼 풀링

매번 버퍼를 할당/해제하면 GC 부담이 크다. 서버처럼 요청이 반복되는 환경에서는 미리 만들어둔 버퍼를 돌려쓰는 게 낫다.

```java
// 간단한 ByteBuffer 풀
public class ByteBufferPool {
    private final Queue<ByteBuffer> pool = new ConcurrentLinkedQueue<>();
    private final int bufferSize;

    public ByteBufferPool(int bufferSize, int initialCount) {
        this.bufferSize = bufferSize;
        for (int i = 0; i < initialCount; i++) {
            pool.offer(ByteBuffer.allocateDirect(bufferSize));
        }
    }

    public ByteBuffer acquire() {
        ByteBuffer buf = pool.poll();
        if (buf == null) {
            buf = ByteBuffer.allocateDirect(bufferSize);
        }
        buf.clear();
        return buf;
    }

    public void release(ByteBuffer buf) {
        if (buf.capacity() == bufferSize) {
            pool.offer(buf);
        }
    }
}
```

Netty의 `PooledByteBufAllocator`가 이 패턴의 프로덕션 레벨 구현이다. 직접 풀링을 만들기보다 프레임워크가 제공하는 걸 쓰는 게 맞다.

---

## 참고

| 상황 | 권장 버퍼 크기 |
|------|-------------|
| 파일 읽기/쓰기 | 8KB ~ 256KB. OS 페이지 크기(보통 4KB)의 배수로 맞추면 좋다 |
| TCP 소켓 수신 | 8KB ~ 64KB. `SO_RCVBUF` 소켓 옵션과 맞춰야 의미 있다 |
| UDP 패킷 | 최대 65,507 bytes (IPv4). 보통 MTU 고려해서 1,400 bytes 이하 |
| 대용량 파일 전송 | `transferTo`/`sendfile` 같은 zero-copy 사용. 직접 버퍼 잡지 말 것 |
