---
title: Node.js Stream
tags: [nodejs, language]
updated: 2026-07-25
---

# Node.js Stream

파일을 한 번에 메모리에 올려서 처리하면, 1GB 파일을 다룰 때 서버 메모리가 그만큼 잡아먹힌다. 스트림은 데이터를 청크(chunk) 단위로 쪼개서 흘려보내는 방식이라, 파일 크기에 상관없이 메모리를 `highWaterMark` 크기로 일정하게 유지한다. Node.js의 `fs.createReadStream`, HTTP 요청/응답 객체, TCP 소켓 모두 스트림 기반이다.

스트림은 네 가지 타입으로 나뉜다. Readable은 데이터를 읽어들이는 쪽, Writable은 데이터를 쓰는 쪽, Duplex는 읽기와 쓰기가 동시에 가능한 양방향, Transform은 Duplex의 일종으로 입력 데이터를 변환해서 출력한다.

## Readable Stream

Readable은 두 가지 모드로 동작한다. `data` 이벤트 리스너를 붙이거나 `pipe()`를 호출하는 순간 flowing 모드가 되어 자동으로 데이터가 흘러나온다. `pause()`를 호출하면 paused 모드로 돌아가고 데이터가 내부 버퍼에 쌓인다.

`highWaterMark`는 내부 버퍼의 임계값이다. 기본값은 **64KB**(65536)다. 이 값을 초과하면 `_read()`가 더 이상 호출되지 않는다. 대용량 파일을 처리할 때는 이 값을 늘려서 I/O 호출 횟수를 줄이고, 메모리가 타이트한 환경에서는 줄여야 한다.

```javascript
new Readable({ read() {} }).readableHighWaterMark;   // 65536
require('fs').createReadStream('/etc/hosts').readableHighWaterMark;  // 65536
```

16KB 로 적힌 자료를 종종 보는데, 그건 소켓 기준이거나 옛 판본이다. **아래 objectMode 절에서 보듯 단위 자체가 바뀌는 경우도 있으니 값을 외우기보다 찍어 보는 게 낫다.**

```javascript
const { Readable } = require('stream');

class DatabaseCursor extends Readable {
  constructor(queryFn, options = {}) {
    super({ objectMode: true, highWaterMark: 100, ...options });
    this.queryFn = queryFn;
    this.offset = 0;
    this.pageSize = 100;
    this.done = false;
  }

  async _read() {
    if (this.done) {
      this.push(null);
      return;
    }

    try {
      const rows = await this.queryFn(this.offset, this.pageSize);
      if (rows.length < this.pageSize) {
        this.done = true;
      }
      this.offset += rows.length;
      for (const row of rows) {
        if (!this.push(row)) {
          // push()가 false면 내부 버퍼가 highWaterMark를 넘었다는 신호다
          // 루프를 중단해서 소비자가 처리할 시간을 줘야 한다
          break;
        }
      }
      if (this.done) this.push(null);
    } catch (err) {
      this.destroy(err);
    }
  }
}
```

객체 모드(`objectMode: true`)를 쓰면 Buffer/String 대신 JS 객체를 흘려보낼 수 있다. DB 커서처럼 레코드를 한 건씩 처리할 때 유용하다.

#### objectMode 에서 highWaterMark 는 바이트가 아니라 개수다

같은 이름의 옵션인데 **단위가 통째로 바뀐다.** 기본값도 함께 바뀐다.

```javascript
new Readable({ read() {} }).readableHighWaterMark;                  // 65536  (바이트)
new Readable({ objectMode: true, read() {} }).readableHighWaterMark; // 16     (개수)
new Writable({ write(c,e,cb){cb();} }).writableHighWaterMark;                  // 65536
new Writable({ objectMode: true, write(c,e,cb){cb();} }).writableHighWaterMark; // 16
```

**`16` 은 16KB 가 아니라 객체 16개**다. 여기서 실무 함의가 나온다 — 객체 하나가 크면 16개만으로도 메모리가 크게 부푼다.

10MB 짜리 객체를 느린 소비자에게 밀어 넣어 보면 이렇게 된다.

```javascript
const w = new Writable({ objectMode: true, write(c, e, cb) { setTimeout(cb, 50); } });
let n = 0, ok = true;
while (ok) { ok = w.write({ payload: 'x'.repeat(10 * 1024 * 1024) }); n++; }
// → 16개째에 false 반환. 그때 버퍼에 약 160MB 가 쌓여 있다
```

바이트 모드였다면 64KB 에서 배압이 걸렸을 텐데, 객체 모드는 **160MB 를 다 받고 나서야** 신호를 준다. DB 커서에서 행을 읽어 흘리는 파이프라인에서 행 하나가 크면(BLOB 컬럼, 큰 JSON) 정확히 이 모양이 된다.

그래서 **객체 크기를 알면 highWaterMark 를 직접 잡아야 한다.**

```javascript
// 행 하나가 수 MB 인 커서 스트림 — 기본값 16 이면 수십 MB 가 버퍼에 뜬다
new Readable({ objectMode: true, highWaterMark: 2, read() {} });

// 작고 가벼운 이벤트 객체라면 오히려 늘려서 처리량을 올린다
new Readable({ objectMode: true, highWaterMark: 256, read() {} });
```

기본값 16 은 "객체 하나가 작다" 를 전제한 숫자다. 그 전제가 안 맞으면 조정하는 게 맞고, **조정 근거는 객체 하나의 실제 크기**다.

## Writable Stream

`write()` 메서드는 내부 버퍼가 `highWaterMark`를 초과하면 `false`를 반환한다. 이 반환값을 무시하고 계속 `write()`를 호출하면 메모리가 무한정 쌓인다. 버퍼가 비워지면 `drain` 이벤트가 발생하고, 그때 쓰기를 재개해야 한다.

```javascript
const { Writable } = require('stream');

class BatchWriter extends Writable {
  constructor(db, options = {}) {
    super({ objectMode: true, highWaterMark: 50, ...options });
    this.db = db;
    this.batch = [];
  }

  async _write(chunk, encoding, callback) {
    this.batch.push(chunk);
    if (this.batch.length >= 50) {
      try {
        await this.db.bulkInsert(this.batch);
        this.batch = [];
        callback();
      } catch (err) {
        callback(err);
      }
    } else {
      callback();
    }
  }

  async _final(callback) {
    if (this.batch.length > 0) {
      try {
        await this.db.bulkInsert(this.batch);
        callback();
      } catch (err) {
        callback(err);
      }
    } else {
      callback();
    }
  }
}
```

`_final()`은 스트림이 끝날 때 한 번 호출된다. 배치 처리처럼 마지막 청크를 남김없이 처리해야 할 때 여기서 마무리한다. `callback()`을 빠뜨리면 `finish` 이벤트가 영원히 발생하지 않는다.

## Backpressure

Backpressure는 생산자가 소비자보다 빠를 때 발생하는 흐름 제어 문제다. Readable에서 Writable로 데이터를 직접 넘길 때 `write()`의 반환값을 확인하지 않으면, Readable은 계속 데이터를 뽑아내고 Writable의 내부 버퍼가 터진다.

```javascript
const fs = require('fs');

function copyWithBackpressure(src, dest) {
  const readable = fs.createReadStream(src);
  const writable = fs.createWriteStream(dest);

  readable.on('data', (chunk) => {
    const canContinue = writable.write(chunk);
    if (!canContinue) {
      // Writable 버퍼가 찼다. 더 이상 데이터를 뽑지 않도록 Readable을 멈춘다.
      readable.pause();
    }
  });

  writable.on('drain', () => {
    // Writable 버퍼가 비워졌다. Readable을 다시 재개한다.
    readable.resume();
  });

  return new Promise((resolve, reject) => {
    writable.on('finish', resolve);
    readable.on('error', reject);
    writable.on('error', reject);
  });
}
```

이 패턴을 매번 직접 구현하는 건 번거롭다. `pipe()`와 `pipeline()`이 이 과정을 자동으로 처리해준다.

## Transform Stream

Transform은 데이터를 받아 가공한 뒤 출력하는 스트림이다. `_transform()`에서 `this.push()`로 변환된 데이터를 내보내고 `callback()`을 호출해야 다음 청크를 받는다. `callback()`을 빠뜨리면 스트림이 그 자리에서 멈춘다.

```javascript
const { Transform } = require('stream');

class LineCounter extends Transform {
  constructor(options = {}) {
    super(options);
    this.lineCount = 0;
    this.remainder = '';
  }

  _transform(chunk, encoding, callback) {
    const str = this.remainder + chunk.toString();
    const lines = str.split('\n');
    // 마지막 요소는 줄바꿈이 없는 불완전한 줄일 수 있다
    this.remainder = lines.pop();
    this.lineCount += lines.length;
    this.push(chunk);
    callback();
  }

  _flush(callback) {
    if (this.remainder) {
      this.lineCount++;
    }
    console.log(`총 ${this.lineCount}줄`);
    callback();
  }
}
```

`_flush()`는 `_transform()`이 모두 끝난 뒤 스트림이 닫히기 전에 한 번 호출된다. 내부에 누적된 데이터가 있을 때 여기서 마지막으로 내보낸다.

## Duplex Stream

Duplex는 읽기와 쓰기 채널이 독립적으로 존재한다. `net.Socket`이 대표적이다. TCP 연결은 데이터를 받으면서 동시에 보낼 수 있는 양방향 채널이기 때문에 Duplex로 구현되어 있다.

```javascript
const net = require('net');

const server = net.createServer((socket) => {
  socket.on('data', (data) => {
    const message = data.toString().trim();
    socket.write(`Echo: ${message}\n`);
  });

  socket.on('end', () => {
    socket.destroy();
  });

  socket.on('error', (err) => {
    console.error('소켓 오류:', err.message);
  });
});

server.listen(3000);
```

직접 Duplex를 구현할 일은 드물다. 커스텀 프로토콜 파서나 WebSocket 클라이언트를 만들 때 사용하는데, `_read()`와 `_write()` 양쪽을 모두 구현해야 한다.

## pipe와 pipeline

`pipe()`는 Readable에 Writable을 연결하고 backpressure를 자동으로 처리한다. 단, 오류가 발생해도 파이프라인이 자동으로 정리되지 않아서 각 스트림에 오류 핸들러를 직접 달아야 한다.

```javascript
const r = fs.createReadStream('input.txt');
const w = fs.createWriteStream('output.txt');
r.on('error', (err) => { w.destroy(err); });
w.on('error', (err) => { r.destroy(err); });
r.pipe(w);
```

`stream/promises`의 `pipeline()`은 어느 한 스트림에서 오류가 나면 나머지 스트림을 자동으로 모두 닫는다. Node.js 15부터 async/await로 쓸 수 있다.

```javascript
const { pipeline } = require('stream/promises');
const fs = require('fs');
const zlib = require('zlib');

async function compressFile(inputPath, outputPath) {
  await pipeline(
    fs.createReadStream(inputPath, { highWaterMark: 64 * 1024 }),
    new LineCounter(),
    zlib.createGzip(),
    fs.createWriteStream(outputPath)
  );
}

compressFile('data.csv', 'data.csv.gz').catch(console.error);
```

중간 Transform에서 오류가 나면 `pipe()` 체이닝만으로는 앞뒤 스트림이 자동으로 닫히지 않는다. 프로덕션 코드에서는 `pipeline()`을 기본으로 써야 한다.

## 주의사항

`readable` 이벤트와 `data` 이벤트를 동시에 달면 동작이 예측 불가능해진다. 두 이벤트는 서로 다른 모드를 가정하기 때문에 하나만 써야 한다.

객체 모드와 버퍼 모드를 연결할 때는 Transform을 끼워서 변환해야 한다. 객체 모드 Readable을 버퍼 모드 Writable에 바로 pipe하면 오류가 난다.

`stream.destroy()`를 호출하면 `close` 이벤트는 발생하지만 `finish`나 `end`는 발생하지 않는다. 정리 코드를 `finish`에만 붙여뒀다면 실행되지 않는다.

`fs.readFile()`로 전체를 읽어서 가공하면 파일 크기만큼 힙에 올라간다. 1GB 파일이라면 1GB가 메모리를 잡는다. `createReadStream()`과 Transform을 조합하면 `highWaterMark` 크기만큼만 유지된다.
