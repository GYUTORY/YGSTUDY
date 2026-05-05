---
title: Buffer
tags: [datarepresentation, buffer, java, nodejs, python, netty, zero-copy]
updated: 2026-05-06
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

### 멀티스레드 환경에서의 ByteBuffer 공유

ByteBuffer는 스레드 안전하지 않다. 두 스레드가 동시에 한 ByteBuffer를 읽기만 해도 position이 망가진다. 서로 다른 영역을 동시에 처리하고 싶다면 `duplicate()`, `slice()`, `asReadOnlyBuffer()`로 뷰를 만들어 써야 한다.

```java
ByteBuffer original = ByteBuffer.allocate(1024);
fillData(original);
original.flip();

// 메모리는 같지만 position/limit/mark가 독립인 새 ByteBuffer
ByteBuffer dup = original.duplicate();

// 현재 position부터 limit까지를 잘라서 새 ByteBuffer로
ByteBuffer slc = original.slice();

// 읽기 전용 뷰 — 데이터 보호
ByteBuffer ro = original.asReadOnlyBuffer();

executor.submit(() -> readRange(dup));
executor.submit(() -> readRange(slc));
```

주의해야 할 점이 하나 있다. 메모리는 공유한다. 한쪽에서 `put()`으로 데이터를 변경하면 다른 쪽에도 보인다. 동시 쓰기는 그대로 데이터 레이스다. "한 스레드가 쓰고 끝난 뒤 여러 스레드가 읽는다" 같은 happens-before 보장이 있어야 한다(volatile, synchronized, CountDownLatch, Phaser 등).

내부적으로 `slice()`와 `duplicate()`는 같은 native address나 byte[] 참조를 공유하지만 인덱싱 메타데이터만 새로 만든다. 그래서 거의 비용이 없다. 성능 손해 걱정 말고 자유롭게 만들어 쓰면 된다.

---

## Netty ByteBuf

Netty를 직접 쓰지 않더라도 Spring WebFlux, Reactor Netty, gRPC Java를 쓰면 결국 내부에서 만난다. ByteBuf는 ByteBuffer가 가진 답답한 점을 해결하려고 만든 버퍼다.

### ByteBuf vs ByteBuffer

| 항목 | ByteBuffer | ByteBuf |
|------|-----------|---------|
| 포인터 | position 1개 — flip()으로 모드 전환 | readerIndex/writerIndex 분리 — flip 불필요 |
| 크기 변경 | 고정. 모자라면 새 버퍼 만들고 복사 | 자동 확장 (writeXxx 호출 시) |
| 메모리 관리 | GC + Cleaner | 참조 카운트 기반 수동 release |
| 풀링 | 직접 구현 | PooledByteBufAllocator 기본 제공 |
| 메서드 체이닝 | 일부만 | 전부 가능 |

```java
// ByteBuf는 flip이 없다. write 후 read를 바로 한다.
ByteBuf buf = Unpooled.buffer(256);
buf.writeInt(42);
buf.writeBytes("hello".getBytes());

int value = buf.readInt();  // readerIndex가 자동 증가
String str = buf.readCharSequence(5, StandardCharsets.UTF_8).toString();
```

### Pooled vs Unpooled, Heap vs Direct

조합이 4가지다.

```java
// Unpooled — 매번 new. 짧은 코드, 테스트, 단발성 작업에 쓴다.
ByteBuf u1 = Unpooled.buffer(1024);          // unpooled heap
ByteBuf u2 = Unpooled.directBuffer(1024);    // unpooled direct

// Pooled — 풀에서 빌리고 반납. 운영 코드는 거의 이걸 쓴다.
ByteBufAllocator alloc = PooledByteBufAllocator.DEFAULT;
ByteBuf p1 = alloc.heapBuffer(1024);
ByteBuf p2 = alloc.directBuffer(1024);
```

Netty 4.1부터 `PooledByteBufAllocator`가 기본 allocator다. jemalloc 스타일의 arena/chunk 기반 풀이라 sub-microsecond 단위로 할당이 끝난다. 동일한 처리량에서 GC 부담이 1/10 수준으로 떨어진다.

### refCnt — 참조 카운트 수동 관리

ByteBuf의 가장 큰 함정이다. 풀에서 빌린 버퍼를 반납 안 하면 풀이 고갈된다.

```java
ByteBuf buf = alloc.directBuffer(1024);
// refCnt = 1
buf.writeBytes(data);

ByteBuf retained = buf.retain();  // refCnt = 2 — 다른 곳에서도 쓴다고 표시
processAsync(retained);

buf.release();  // refCnt = 1
// processAsync 내부에서 release()를 또 호출하면 refCnt = 0이 되어 풀로 반납
```

`release()`를 빼먹으면 처음에는 멀쩡해 보인다. 그러다 트래픽이 일정 수준을 넘으면 갑자기 `LEAK: ByteBuf.release() was not called` 경고가 로그에 쏟아지고 응답 지연이 치솟는다. Netty의 누수 탐지기는 샘플링으로 동작하는데 운영 기본값은 SIMPLE 레벨(약 1%)이다.

```bash
# 누수 의심 상황에서는 PARANOID(100%)로 올려서 재현한다
-Dio.netty.leakDetection.level=PARANOID
```

ChannelHandler에서 ByteBuf를 받으면 처리 후 release할지 다음 핸들러로 넘길지 명확히 해야 한다. `SimpleChannelInboundHandler`는 자동으로 release하지만, `ChannelInboundHandlerAdapter`는 직접 호출해야 한다. 이 차이를 모르면 누수가 난다.

```java
public class MyHandler extends ChannelInboundHandlerAdapter {
    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) {
        ByteBuf buf = (ByteBuf) msg;
        try {
            // 처리
        } finally {
            buf.release();  // 빼먹으면 풀 누수
        }
    }
}
```

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

### Off-heap 메모리 누수 디버깅

Direct ByteBuffer 누수는 힙 덤프로 안 보인다. RSS는 계속 늘어나는데 힙 사용량은 정상이라면 십중팔구 네이티브 메모리 누수다. 이런 상황에서 쓸 수 있는 도구들이 있다.

**Native Memory Tracking 활성화**

NMT를 켜고 시작한다. 운영 부하 영향은 5~10% 정도라 일시적으로는 켜도 된다.

```bash
java -XX:NativeMemoryTracking=detail \
     -XX:+UnlockDiagnosticVMOptions \
     -jar app.jar
```

부하를 받기 전에 베이스라인을 잡아둔다.

```bash
jcmd <pid> VM.native_memory baseline
```

시간이 흐른 뒤 차이를 본다.

```bash
jcmd <pid> VM.native_memory summary.diff
```

`Internal` 카테고리가 계속 증가하면 Direct Buffer 또는 JNI 할당이 의심된다. `Other`가 늘어나면 외부 라이브러리(JNI 모듈, GZIP 인플레이터 등)다.

**Direct Buffer 사용량 직접 확인**

JMX의 `BufferPoolMXBean`이 가장 정확하다.

```java
List<BufferPoolMXBean> pools =
    ManagementFactory.getPlatformMXBeans(BufferPoolMXBean.class);

for (BufferPoolMXBean pool : pools) {
    System.out.printf("%s: count=%d, used=%d, capacity=%d%n",
        pool.getName(), pool.getCount(),
        pool.getMemoryUsed(), pool.getTotalCapacity());
}
// direct: count=247, used=129826816, capacity=129826816
// mapped: count=3, used=2147483648, capacity=2147483648
```

Prometheus의 `jvm_buffer_pool_used_bytes` 메트릭으로 그래프를 그려두면 누수 시점을 잡기 쉽다. 누수가 있으면 톱니 모양이 아니라 우상향 선이 나온다.

**pmap으로 RSS 해부**

JVM 외부에서 보면 결국 OS가 보는 메모리는 RSS다. 프로세스가 실제 점유한 메모리 영역을 보려면 pmap이 가장 빠르다.

```bash
pmap -x <pid> | sort -k 3 -n -r | head -30
```

JVM 힙은 한 덩어리의 큰 매핑으로 보인다. 작은 anon 매핑이 수십~수백 개 늘어난다면 풀링 안 된 Direct Buffer가 의심스럽다. `64MB` 단위 매핑이 점점 늘어나는 패턴은 glibc의 `MALLOC_ARENA`가 의심된다 — 이때는 `MALLOC_ARENA_MAX=2`로 제한해본다.

**그 외 도구**

- `async-profiler --alloc` — Direct Buffer 할당 스택 트레이스
- Netty의 `ResourceLeakDetector` — ByteBuf 누수만 잡아낸다
- jemalloc 프로파일러 — `MALLOC_CONF=prof:true` 환경변수로 켜고 jeprof로 분석

대부분의 사례에서 원인은 셋 중 하나다. 풀링을 안 쓰거나, refCnt 관리가 잘못됐거나, JNI 라이브러리 버그다.

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

**sendfile의 한계**

sendfile은 만능이 아니다. 쓸 수 있는 경우가 좁다.

- 파일 → 소켓 단방향만 된다. 메모리 → 소켓이나 소켓 → 파일은 안 된다.
- TLS가 끼면 유저 공간으로 데이터를 가져와 암호화해야 하니 zero-copy 효과가 사라진다. kTLS(커널 TLS)를 켜면 다시 살아나지만 인증서/세션 셋업은 여전히 유저 공간 몫이다.
- HTTP/2처럼 한 TCP 연결로 여러 스트림을 다중화하면 작은 청크가 많아져 sendfile 호출 비용이 복사 비용을 잡아먹는다.
- 파일 내용을 변형해서 보내야 한다면 (압축, 삽입, 헤더 부착) 결국 유저 공간을 거쳐야 한다.

**splice — 파이프 경유 zero-copy**

sendfile이 못 하는 조합을 splice로 해결한다. 양쪽 fd가 무엇이든 pipe를 중간에 끼우면 된다.

```c
int pipefd[2];
pipe(pipefd);
splice(src_fd, NULL, pipefd[1], NULL, len, SPLICE_F_MOVE);
splice(pipefd[0], NULL, dst_fd, NULL, len, SPLICE_F_MOVE);
```

socket → file이나 socket → socket 같은 패턴을 유저 공간 복사 없이 처리할 수 있다. nginx의 일부 빌드와 HAProxy가 splice를 사용한다.

**MSG_ZEROCOPY (Linux 4.14+)**

`send()`에 `MSG_ZEROCOPY` 플래그를 넘기면 유저 공간 버퍼를 복사 없이 NIC로 보낸다. 비동기다. 커널이 NIC 전송 완료를 알리기 전에 버퍼를 수정하면 데이터가 깨진다. 완료 알림은 errqueue로 받아야 한다.

```c
int one = 1;
setsockopt(sock, SOL_SOCKET, SO_ZEROCOPY, &one, sizeof(one));
send(sock, buf, len, MSG_ZEROCOPY);
// recvmsg(sock, &msg, MSG_ERRQUEUE)로 완료 폴링
```

64KB 미만 버퍼에서는 페이지 핀/언핀 비용이 복사 비용보다 커서 오히려 느려진다. CDN처럼 큰 청크를 많이 보내는 워크로드에서만 의미가 있다.

**io_uring (Linux 5.1+)**

진짜 비동기 I/O 인터페이스다. SQ(Submission Queue)와 CQ(Completion Queue) 두 개의 링 버퍼를 커널과 공유한다. 한 syscall로 수백 개의 I/O를 큐잉할 수 있어서 syscall 자체가 거의 사라진다.

```c
struct io_uring ring;
io_uring_queue_init(256, &ring, 0);

struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
io_uring_prep_read(sqe, fd, buf, len, offset);
io_uring_submit(&ring);

struct io_uring_cqe *cqe;
io_uring_wait_cqe(&ring, &cqe);
// cqe->res에 실제 read 결과
```

JVM에는 표준 io_uring API가 없다. Netty 5의 incubator 모듈(`netty-incubator-transport-io_uring`)이나 Helidon Níma가 사용한다. PostgreSQL 17부터 io_uring 기반 비동기 I/O가 들어왔다. 운영체제 커널 버전이 5.6 이상이면 stable, 그 이하라면 보안 패치 이슈로 비활성화된 배포판도 있다.

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

### 버퍼 오버플로와 보안

C/C++의 클래식한 버퍼 오버플로는 Java/Node.js에서는 메모리 안전성 덕분에 거의 안 일어난다. 대신 다른 종류의 함정이 있다.

**Node.js Buffer.allocUnsafe — 메모리 내용 유출**

`Buffer.allocUnsafe()`는 초기화 안 된 메모리를 그대로 반환한다. V8 힙 외부의 메모리 풀에서 가져오는데, 이전 요청이 사용한 데이터가 그대로 남아있다. 인증 토큰, 다른 사용자 응답 조각이 그대로 클라이언트에게 흘러갈 수 있다.

```javascript
// 위험한 패턴
function buildResponse(userId) {
    const buf = Buffer.allocUnsafe(1024);
    const written = buf.write(`user:${userId}\n`, 0, 'utf8');
    // written 바이트만 새로 쓰였다. 그 뒤는 이전 메모리 그대로.
    return buf;  // 이 버퍼를 그대로 응답으로 보내면 메모리 유출
}
```

실제로 2017~2018년 사이 Node.js 생태계에서 비슷한 케이스의 CVE가 여러 건 났다. `ws`(WebSocket 라이브러리), `bson`, `mongodb` 드라이버의 일부 버전에서 unsafe 버퍼를 외부로 노출하는 버그가 있었다. Node.js 8.x부터 `Buffer()` 생성자가 deprecated된 이유 중 하나다.

```javascript
// 안전한 패턴
const buf = Buffer.allocUnsafe(1024);
const written = buf.write(`user:${userId}\n`, 0, 'utf8');
return buf.subarray(0, written);  // 실제 쓴 영역만 잘라서 반환
```

원칙은 단순하다. 외부로 나가는 데이터 만들기에는 `Buffer.alloc()`을 쓴다. `allocUnsafe()`는 바로 전체를 덮어쓰는 경우(파일 read 결과를 받는 버퍼 등)에만 쓴다.

**Java DirectByteBuffer — JNI 경계 검증**

JNI에서 Direct ByteBuffer를 raw 포인터로 받아 처리할 때, capacity 검증을 빼먹으면 다른 객체의 메모리를 덮어쓸 수 있다. `(*env)->GetDirectBufferAddress()`가 반환한 주소는 그냥 포인터다. 항상 `(*env)->GetDirectBufferCapacity()`로 한계를 확인해야 한다.

**프로토콜 길이 필드 검증**

직접 짠 바이너리 프로토콜 파서에서 가장 흔한 보안 버그다.

```java
// 위험한 코드
int length = buf.getInt();              // 클라이언트가 보낸 길이
byte[] payload = new byte[length];      // length가 -1이거나 1GB라면?
buf.get(payload);
```

상한선 검증을 빼먹으면, 악의적 클라이언트가 4바이트만 보내고 length=Integer.MAX_VALUE를 박아 OOM을 유발하거나, 음수를 보내서 `NegativeArraySizeException`으로 핸들러를 죽일 수 있다.

```java
// 방어 코드
int length = buf.getInt();
if (length < 0 || length > MAX_PAYLOAD_SIZE) {
    throw new ProtocolException("invalid length: " + length);
}
byte[] payload = new byte[length];
buf.get(payload);
```

Netty의 `LengthFieldBasedFrameDecoder`처럼 검증된 디코더를 쓰면 이런 실수를 막아준다. 직접 길이 기반 프레이밍을 짜야 한다면 항상 max length 파라미터를 받도록 설계한다.

### 데이터베이스와 메시지 큐의 버퍼

서버 코드 안의 버퍼만 보면 절반만 본 것이다. 운영에서는 DB와 미들웨어의 버퍼가 시스템 성능을 좌우한다.

**PostgreSQL shared_buffers**

PostgreSQL은 자체 버퍼 풀(`shared_buffers`)에 페이지를 캐싱한다. 기본값은 128MB로 매우 작다. 8KB 페이지 기준 16,384개 페이지밖에 못 담는다.

```ini
# postgresql.conf
shared_buffers = 8GB        # 보통 RAM의 25%
effective_cache_size = 24GB # OS 페이지 캐시까지 합쳐서 옵티마이저에게 알려주는 값
work_mem = 64MB             # 정렬/해시조인 작업 메모리. 쿼리당 할당
maintenance_work_mem = 1GB  # VACUUM, CREATE INDEX 등에 쓰는 메모리
```

`shared_buffers`를 너무 크게 잡으면 OS 페이지 캐시와 이중 캐싱이 일어나 메모리 효율이 떨어진다. 25% 권장값은 이 이중 캐싱을 고려한 수치다. 32GB 이상부터는 효과가 점점 떨어진다는 보고가 많다.

**Kafka — page cache 의존**

Kafka 브로커는 자체 버퍼 캐시를 만들지 않는다. 프로듀서가 보낸 메시지는 segment 파일에 append되고, OS 페이지 캐시가 그 데이터를 캐싱한다. 컨슈머가 읽을 때도 sendfile zero-copy로 page cache → 소켓으로 직접 보낸다.

```bash
# 브로커 JVM heap은 작아도 된다 (보통 6GB면 충분)
# 대신 호스트 RAM을 충분히 줘서 page cache가 넉넉해야 한다
free -h
```

Kafka 호스트의 메모리 이슈는 JVM heap이 아니라 page cache가 줄어들 때 생긴다. 동일 호스트의 다른 프로세스가 메모리를 점유하면 page cache가 evict되고, 컨슈머가 디스크에서 읽기 시작하면서 latency가 수 ms → 수십 ms로 치솟는다. 그래서 Kafka 브로커는 보통 다른 프로세스와 안 섞는다.

**Redis — client output buffer limit**

Redis 클라이언트마다 출력 버퍼가 따로 있다. pub/sub 구독자가 메시지를 못 따라가거나, replica 동기화가 늦어지면 이 버퍼가 무한정 커진다. 메모리 폭발을 막으려면 limit을 설정해야 한다.

```
# redis.conf
client-output-buffer-limit normal 0 0 0
client-output-buffer-limit replica 256mb 64mb 60
client-output-buffer-limit pubsub 32mb 8mb 60
```

`replica 256mb 64mb 60`는 하드 리밋 256MB, 소프트 리밋 64MB가 60초 이상 지속되면 연결을 끊는다는 뜻이다. replica의 lag가 커지면 마스터에서 강제로 끊고 풀 리싱크를 다시 시작한다. 이 동작을 모르면 "왜 멀쩡하던 replica가 갑자기 끊어지지?" 로 한참 헤맨다.

`CLIENT LIST` 명령으로 현재 클라이언트별 출력 버퍼 사용량을 볼 수 있다.

```
> CLIENT LIST
id=42 addr=10.0.0.5:43210 ... omem=10485760 oll=128 ...
```

`omem`이 출력 버퍼 바이트, `oll`이 큐에 쌓인 명령 수다. `omem`이 꾸준히 늘어나는 클라이언트가 있다면 그쪽 컨슈머가 못 따라오고 있다는 신호다.

### 캐시 라인 정렬과 false sharing

CPU는 메모리를 바이트 단위가 아니라 캐시 라인 단위로 읽는다. 일반 x86은 64바이트, 일부 ARM 서버는 128바이트다. 두 스레드가 별개의 변수를 수정해도 같은 캐시 라인에 있으면 캐시 라인이 코어 사이를 핑퐁한다. 이게 false sharing이다.

```java
class BadCounter {
    long count1;  // 같은 캐시 라인에 들어감
    long count2;
}
```

두 스레드가 각각 count1, count2를 갱신하면 락은 안 걸려도 캐시 라인은 공유된다. 한 코어가 자기 캐시를 갱신할 때마다 다른 코어의 캐시 라인은 invalidate된다. 멀티코어인데 싱글 스레드보다 느려진다.

```java
// 패딩으로 직접 해결
class PaddedCounter {
    long count1;
    long p1, p2, p3, p4, p5, p6, p7;  // 56바이트 패딩 → 64바이트 경계
    long count2;
}

// 또는 Java 8+의 @Contended (-XX:-RestrictContended 필요)
class GoodCounter {
    @sun.misc.Contended long count1;
    @sun.misc.Contended long count2;
}
```

대형 ByteBuffer를 여러 스레드가 영역을 나눠 쓸 때도 같은 문제다. 스레드 A가 0~63바이트, B가 64~127바이트를 쓰면 안전하다. A가 0~50, B가 51~100이면 51~63 부분이 같은 캐시 라인이라 false sharing이 일어난다. 영역 분할은 항상 64바이트 단위로 끊어야 한다.

운영에서는 perf로 잡는다.

```bash
perf c2c record -- java -jar app.jar
perf c2c report
```

`HITM`(remote cache hit modified) 비율이 높은 라인이 false sharing 후보다. LMAX Disruptor가 RingBuffer 시퀀스 변수에 패딩을 넣는 이유가 이 문제 때문이다.

### 백프레셔 수치 모니터링

스트림 백프레셔는 개념만 알면 안 되고 수치로 본 적이 있어야 한다.

**Node.js highWaterMark**

스트림 내부 버퍼의 임계값이다.

| 스트림 종류 | 기본값 |
|------------|--------|
| Readable (Buffer 모드) | 16 KB |
| Readable (Object 모드) | 16 |
| Writable (Buffer 모드) | 16 KB |
| Writable (Object 모드) | 16 |

`writable.write()`가 false를 반환하는 시점이 highWaterMark 초과 시점이다. 디스크 쓰기가 느린 환경에서 16KB는 너무 작아서 일시정지/재개가 너무 자주 반복된다.

```javascript
const stream = fs.createWriteStream('output.bin', {
    highWaterMark: 1024 * 1024,  // 1MB로 늘림
});

let backpressureCount = 0;
const wrap = stream.write.bind(stream);
stream.write = (chunk) => {
    const ok = wrap(chunk);
    if (!ok) backpressureCount++;
    return ok;
};
```

운영 환경에서는 `stream.writableLength`(현재 버퍼 사용량)와 `stream.writableHighWaterMark` 비율을 prom-client로 메트릭으로 노출하면 백프레셔 패턴이 보인다.

**Project Reactor (Java)**

Reactor의 `Flux`는 `onBackpressureBuffer`, `onBackpressureDrop`, `onBackpressureLatest` 중 어느 걸 쓰는지에 따라 동작이 다르다.

```java
flux
    .onBackpressureBuffer(10_000,
        dropped -> log.warn("dropped: {}", dropped),
        BufferOverflowStrategy.DROP_OLDEST)
    .subscribe(consumer);
```

버퍼가 10,000개를 넘으면 가장 오래된 것부터 drop한다. drop 콜백에서 카운터를 올려 메트릭으로 노출하면 운영 중 데이터 유실량이 보인다.

**튜닝 기준**

백프레셔 발생 자체는 비정상이 아니다. 시스템이 살아 있고 흐름 제어가 작동한다는 신호다. 문제가 되는 패턴은 따로 있다.

- 1초에 수백~수천 회 발생 — highWaterMark가 너무 작거나 컨슈머가 비정상적으로 느리다.
- 한 번 발생하면 회복이 안 됨 — 컨슈머 처리량이 프로듀서보다 영구적으로 작다. 스케일링 또는 큐 분리가 필요하다.
- drop이 임계치 이상 — 데이터 유실이다. 정합성 요구가 있는 서비스라면 SLO 위반이다.

`writableLength / writableHighWaterMark` 비율이 80% 이상에 머물면 highWaterMark를 키워도 의미 없다. 컨슈머 자체를 손봐야 한다. highWaterMark를 키우는 건 일시적 burst 흡수에는 도움이 되지만 장기 처리량 부족은 못 막는다.

---

## 언어별 버퍼 타입 선택

같은 작업이라도 언어마다 어떤 버퍼를 쓸지가 다르다. 프로젝트 초기에 정해두지 않으면 코드베이스가 일관성을 잃는다.

| 상황 | Java | Node.js | Python |
|------|------|---------|--------|
| 일반 파일/소켓 I/O | ByteBuffer.allocate | Buffer.alloc | bytes/bytearray |
| 고성능 네트워크 (Netty 사용) | PooledByteBuf (direct) | — | — |
| 대용량 파일 매핑 | MappedByteBuffer | mmap-io | mmap 모듈 |
| 복사 없이 슬라이싱 | ByteBuffer.slice | Buffer.subarray | memoryview |
| 외부로 나가는 데이터 | ByteBuffer.allocate | Buffer.alloc (allocUnsafe 금지) | bytes |
| 바이너리 프로토콜 파싱 | Netty ByteBuf 또는 ByteBuffer | Buffer + readUInt* | struct.unpack |
| 멀티스레드 공유 읽기 | duplicate / slice / asReadOnlyBuffer | (단일 스레드) | memoryview + Lock |
| zero-copy 파일 전송 | FileChannel.transferTo | stream.pipe | os.sendfile |
| 풀링 필요한 고처리량 | PooledByteBufAllocator | bl(buffer-list) | 직접 풀 구현 |
| 짧은 단발성 처리 | byte[] 또는 ByteBuffer.wrap | Buffer.from | bytes |

선택할 때 기억할 만한 점.

- Java에서 응답 속도가 중요하다면 처음부터 Netty ByteBuf로 가는 게 낫다. ByteBuffer로 시작했다가 나중에 옮기면 손이 너무 간다.
- Node.js에서 외부로 나가는 데이터에는 `allocUnsafe`를 쓰지 않는다. 보안 취약점이다.
- Python에서 대용량 데이터를 슬라이싱하며 다룬다면 함수 시그니처를 처음부터 `memoryview`로 받게 짠다. 그래야 호출자가 복사 없이 넘길 수 있다.
- 단발성 짧은 처리라면 풀링/Direct를 따지지 말고 가장 단순한 타입을 쓴다. 풀링은 GC 부담이 측정될 만큼 클 때만 의미가 있다.

---

## 참고

| 상황 | 권장 버퍼 크기 |
|------|-------------|
| 파일 읽기/쓰기 | 8KB ~ 256KB. OS 페이지 크기(보통 4KB)의 배수로 맞추면 좋다 |
| TCP 소켓 수신 | 8KB ~ 64KB. `SO_RCVBUF` 소켓 옵션과 맞춰야 의미 있다 |
| UDP 패킷 | 최대 65,507 bytes (IPv4). 보통 MTU 고려해서 1,400 bytes 이하 |
| 대용량 파일 전송 | `transferTo`/`sendfile` 같은 zero-copy 사용. 직접 버퍼 잡지 말 것 |
