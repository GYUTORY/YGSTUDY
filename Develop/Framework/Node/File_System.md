---
title: Node.js fs 모듈 실무 심화
tags:
  - nodejs
  - filesystem
  - fs
  - stream
  - chokidar
updated: 2026-06-03
---

# Node.js fs 모듈 실무 심화

Node.js의 `fs` 모듈은 표면적으로는 단순하다. 파일을 읽고 쓰고 감시한다. 그런데 운영 환경에서 파일을 다루다 보면 메모리가 갑자기 치솟고, 파일 디스크립터가 새고, 윈도우에서는 멀쩡히 돌던 코드가 리눅스 컨테이너에서는 동작을 안 한다. 이 문서는 `fs` 모듈을 실무에서 쓰면서 부딪힌 문제들과 해결 방법을 정리한다.

---

## 1. fs.readFile과 fs.createReadStream의 메모리 차이

가장 흔한 실수가 큰 파일을 `fs.readFile`로 한 번에 읽는 것이다. 작은 설정 파일이나 템플릿 파일은 문제없다. 그런데 GB 단위 로그 파일을 그렇게 읽으면 프로세스 RSS가 그대로 그 크기만큼 부풀어 오른다.

### readFile의 동작

```javascript
const fs = require('fs/promises');

async function readBigLog() {
  const data = await fs.readFile('/var/log/app/access.log');
  console.log(data.length);
}
```

`readFile`은 파일 크기만큼 Buffer를 한 번에 할당한다. 4GB 파일이면 4GB짜리 Buffer가 메모리에 잡힌다. V8 힙 제한(기본 1.7GB)을 넘어가는 경우는 더 골치 아프다. `ERR_FS_FILE_TOO_LARGE` 에러가 떨어지는데, 이건 Node.js 내부적으로 `Buffer.kMaxLength`(보통 2GB - 1)를 초과할 때 던지는 에러다. 즉 readFile은 단일 Buffer 크기 한계를 그대로 물려받는다.

### createReadStream의 동작

```javascript
const fs = require('fs');

const stream = fs.createReadStream('/var/log/app/access.log', {
  highWaterMark: 64 * 1024
});

stream.on('data', chunk => {
  // chunk는 highWaterMark 크기 (기본 64KB)
});
stream.on('end', () => console.log('done'));
```

스트림은 내부 버퍼(`highWaterMark` 기본 64KB)만큼만 채우고, 소비자가 데이터를 가져가면 다시 채운다. 1TB 파일을 읽어도 메모리는 64KB 수준에서 유지된다. backpressure 처리가 제대로 되어 있다면.

### 어떤 걸 언제 쓰나

판단 기준은 단순하다. 파일 크기를 사전에 알 수 있고 작다고 확신하면(수 MB 이하) `readFile`을 쓴다. 사용자가 업로드한 파일이거나, 시간이 지나면서 커질 수 있는 로그/덤프 파일이면 무조건 스트림이다. 외부에서 받은 파일은 크기를 못 믿는다고 봐야 한다.

JSON 파싱이 끼면 또 다르다. JSON은 전체 텍스트가 있어야 파싱이 되니까 스트림으로 받아도 결국 한 번에 모아야 한다. 이때는 [`stream-json`](https://www.npmjs.com/package/stream-json) 같은 incremental parser를 써야 한다. JSON 배열을 한 줄씩(NDJSON) 저장하는 식으로 포맷을 바꾸는 게 더 낫다.

---

## 2. high water mark 조정

`highWaterMark`는 스트림 내부 버퍼 크기다. 기본 64KB인데, 이게 항상 최적은 아니다.

### 너무 작을 때

작은 highWaterMark는 read 시스템 콜이 자주 발생한다. 100MB 파일을 4KB 단위로 읽으면 25,000번의 read 콜이 일어난다. 디스크 IO보다 시스템 콜 오버헤드가 더 클 수도 있다.

### 너무 클 때

64MB로 잡아놓으면 한 번에 64MB가 버퍼링된다. 동시에 100개 스트림이 열려있으면 6.4GB가 메모리에 잡힌다. backpressure가 걸려도 이미 채워진 버퍼는 처리해야 한다.

### 실측 기준

```javascript
const stream = fs.createReadStream(path, {
  highWaterMark: 1024 * 1024  // 1MB
});
```

SSD에서 순차 읽기를 한다면 1MB~4MB 정도가 무난하다. NVMe라면 더 키워도 된다. 네트워크 파일시스템(NFS, EFS)이라면 256KB~1MB가 안정적이다. 큰 값일수록 latency는 늘어나고 throughput은 올라간다. 작은 파일을 빠르게 응답해야 하는 API면 작게, 백업이나 ETL 잡이면 크게.

직접 측정하지 않고 추측으로 잡으면 거의 틀린다. `process.memoryUsage()`와 처리 시간을 함께 찍어보고 결정해야 한다.

---

## 3. fsPromises로 콜백 헬 제거

`fs` 모듈은 콜백, sync, promise 세 가지 API를 제공한다. 2020년대 코드에서 콜백 스타일을 쓸 이유는 거의 없다.

### 콜백 스타일

```javascript
const fs = require('fs');

fs.readFile('a.txt', (err, a) => {
  if (err) return handleError(err);
  fs.readFile('b.txt', (err, b) => {
    if (err) return handleError(err);
    fs.writeFile('c.txt', Buffer.concat([a, b]), err => {
      if (err) return handleError(err);
      console.log('done');
    });
  });
});
```

매 단계마다 에러 핸들링이 따라붙고, 들여쓰기가 계단처럼 쌓인다. 트랜잭션 같은 흐름을 만들려면 finally 분기를 직접 끼워 넣어야 한다.

### Promise 스타일

```javascript
const fs = require('fs/promises');

async function merge() {
  const [a, b] = await Promise.all([
    fs.readFile('a.txt'),
    fs.readFile('b.txt')
  ]);
  await fs.writeFile('c.txt', Buffer.concat([a, b]));
}
```

병렬 IO도 `Promise.all`로 자연스럽게 표현된다. try/catch로 일괄 처리도 가능하다. `node:fs/promises`를 import하면 된다.

### 주의할 점

`fs.promises`와 `require('fs/promises')`는 같은 객체다. 단 일부 API는 promise 버전이 없거나 동작이 다르다. `fs.createReadStream`은 promise 버전이 없는 동기 팩토리 함수다. `fs.watch`도 promise 버전이 있지만 async iterator로 동작한다.

```javascript
const watcher = fs.watch('./config');
for await (const event of watcher) {
  console.log(event.eventType, event.filename);
}
```

이 패턴은 보기 좋지만 watcher 종료를 명시적으로 해줘야 한다. `AbortController`로 signal을 넘기는 방식이다.

```javascript
const ac = new AbortController();
setTimeout(() => ac.abort(), 60000);
const watcher = fs.watch('./config', { signal: ac.signal });
```

---

## 4. fs.watch의 플랫폼별 동작 차이

`fs.watch`는 OS의 네이티브 파일 감시 API를 그대로 노출한다. 그래서 플랫폼마다 동작이 다르다. 한 번 데여보지 않으면 절대 모르는 부분이다.

### macOS: FSEvents

macOS는 FSEvents를 쓴다. 디렉토리 단위로 이벤트를 받는데, recursive 옵션을 기본 지원한다. 파일명은 대체로 정상적으로 전달되지만, 빠른 변경이 묶여서 전달될 때가 있다. 짧은 시간에 여러 번 저장하면 이벤트가 합쳐진다.

### Linux: inotify

Linux는 inotify다. recursive 옵션이 동작하지 않는다. 하위 디렉토리는 직접 재귀적으로 watcher를 걸어야 한다. `inotify_add_watch`마다 fd를 소비하고, `/proc/sys/fs/inotify/max_user_watches` 제한에 걸린다. 기본값이 8192~524288 사이로 배포판마다 다른데, `node_modules` 같은 거대 트리를 감시하려고 하면 `ENOSPC` 에러가 떨어진다.

```bash
sudo sysctl fs.inotify.max_user_watches=524288
```

이 값을 올려도 결국 watcher 수만큼 fd가 쓰인다. 대규모 트리는 다른 접근이 필요하다.

### Windows: ReadDirectoryChangesW

Windows는 ReadDirectoryChangesW를 사용한다. recursive를 지원하고, 동작은 비교적 안정적이다. 다만 파일명이 짧은 이름(8.3 형식)으로 들어올 때가 있다. 네트워크 드라이브에서는 이벤트가 아예 안 오는 경우도 있다.

### 공통 문제: 원자적 저장이 두 번의 이벤트로

VSCode나 vim 같은 에디터는 파일을 저장할 때 임시 파일을 만들고 rename으로 교체한다. 이러면 `change` 한 번이 아니라 `rename` + `change` 조합으로 떨어진다. 또 일부 에디터는 저장 직전에 파일을 잠깐 삭제하기도 한다. raw `fs.watch`로 핫 리로드 같은 걸 만들면 한 번의 저장에 핸들러가 2~3번 호출되는 일이 흔하다.

### chokidar로 우회

이런 플랫폼 차이를 일일이 다루기 싫으면 [`chokidar`](https://www.npmjs.com/package/chokidar)를 쓴다. 내부적으로 `fs.watch`와 `fs.watchFile`(폴링) 중 적절한 방식을 골라 쓰고, 이벤트를 debounce하고 정규화한다.

```javascript
const chokidar = require('chokidar');

const watcher = chokidar.watch('./src', {
  ignored: /node_modules|\.git/,
  persistent: true,
  ignoreInitial: true,
  awaitWriteFinish: {
    stabilityThreshold: 200,
    pollInterval: 100
  }
});

watcher
  .on('add', path => console.log('add', path))
  .on('change', path => console.log('change', path))
  .on('unlink', path => console.log('unlink', path));
```

`awaitWriteFinish`가 핵심이다. 파일 쓰기가 끝났다고 판단되는 시점까지 이벤트를 보류한다. 큰 파일이 복사 중일 때 절반만 읽히는 사태를 막아준다.

nodemon, webpack-dev-server, Next.js, Vite 같은 도구들이 전부 chokidar 위에 올라가 있다. 운영 환경에서 자체 watcher가 필요하면 그냥 chokidar를 쓰는 게 시간을 아낀다.

---

## 5. Atomic write 패턴

`fs.writeFile`을 그대로 쓰면 atomic이 아니다. 쓰는 중간에 프로세스가 죽거나, 같은 파일을 동시에 두 프로세스가 쓰면 파일이 깨진다. 설정 파일이나 캐시 메타데이터처럼 일관성이 중요한 파일은 atomic write 패턴을 써야 한다.

### 깨지는 시나리오

```javascript
const fs = require('fs/promises');

async function saveConfig(config) {
  await fs.writeFile('./config.json', JSON.stringify(config));
}
```

이 코드가 1MB짜리 JSON을 쓰는 도중에 프로세스가 SIGKILL을 받으면 파일은 0바이트거나 절반만 쓰인 상태로 남는다. 다음 부팅 때 `JSON.parse`에서 터진다.

### 임시 파일 + rename

POSIX에서 `rename(2)`은 같은 파일시스템 내에서 atomic이다. 그래서 임시 파일에 다 쓴 다음 rename으로 교체하면 안전하다.

```javascript
const fs = require('fs/promises');
const path = require('path');
const crypto = require('crypto');

async function atomicWrite(filePath, data) {
  const dir = path.dirname(filePath);
  const tmpPath = path.join(dir, `.${path.basename(filePath)}.${crypto.randomBytes(6).toString('hex')}.tmp`);

  const fh = await fs.open(tmpPath, 'w');
  try {
    await fh.writeFile(data);
    await fh.sync();  // fsync로 디스크에 강제 flush
  } finally {
    await fh.close();
  }

  await fs.rename(tmpPath, filePath);
}
```

`fh.sync()`(fsync)를 호출해야 OS 버퍼 캐시에서 디스크로 실제로 내려간다. fsync 없이 rename만 하면 메타데이터는 바뀌지만 데이터가 디스크에 없는 상태로 전원이 나갈 수 있다. 다만 fsync는 비싸다. SSD라도 ms 단위 latency가 추가된다. 매번 쓸 때마다 호출하면 성능이 크게 떨어진다.

### 같은 파일시스템 주의

rename은 같은 파일시스템 안에서만 atomic이다. `/tmp`(tmpfs)에 임시 파일을 만들고 `/var/lib/myapp`(ext4)으로 rename하려고 하면 `EXDEV` 에러가 나고 atomic이 아니다. 임시 파일은 반드시 대상 파일과 같은 디렉토리에 만들어야 한다.

### Windows의 제약

Windows에서는 rename 동작이 다르다. 대상 파일이 이미 존재하면 실패한다. `fs.rename` 내부적으로 처리되지만, 파일이 열려있으면 또 실패한다. 운영 환경이 Windows라면 라이브러리 [`write-file-atomic`](https://www.npmjs.com/package/write-file-atomic)을 쓰는 게 안전하다. npm이 내부적으로 쓰는 그 모듈이다.

---

## 6. 파일 디스크립터 누수 디버깅

`open`을 호출하고 `close`를 안 하거나, 에러 경로에서 close를 빠뜨리면 fd가 샌다. 프로세스의 fd 한계(보통 1024~65535)에 도달하면 `EMFILE` 에러가 떨어진다.

### 누수 코드의 전형

```javascript
async function readWithLeak(path) {
  const fh = await fs.open(path, 'r');
  const data = await fh.readFile();  // 여기서 throw하면 fh.close() 못 함
  await fh.close();
  return data;
}
```

`readFile`이 throw하면 fh가 닫히지 않는다. GC가 finalizer로 정리해주긴 하지만 언제 돌지 모른다. 그 사이에 fd가 계속 쌓인다.

### 올바른 패턴

```javascript
async function readSafe(path) {
  const fh = await fs.open(path, 'r');
  try {
    return await fh.readFile();
  } finally {
    await fh.close();
  }
}
```

try/finally를 빼먹지 않아야 한다. 더 짧게는 `fs.readFile(path)`를 그냥 쓰면 내부적으로 처리해준다.

### 스트림도 마찬가지

`createReadStream`이 만든 스트림은 끝까지 소비되면 자동으로 fd가 닫힌다. 그런데 중간에 에러로 끊기거나, `destroy`를 안 부르고 그냥 버리면 fd가 남는다.

```javascript
const stream = fs.createReadStream(path);
try {
  for await (const chunk of stream) {
    process(chunk);
  }
} catch (err) {
  stream.destroy();
  throw err;
}
```

async iterator로 소비하면 정상 종료/에러 모두 fd를 닫아준다. 다만 명시적으로 `destroy`를 호출하는 방어 코드를 넣는 편이 안전하다.

### 누수 추적

운영 중인 프로세스의 fd를 확인하려면 `/proc/<pid>/fd`를 본다.

```bash
ls -l /proc/$(pgrep -f node)/fd | wc -l
ls -l /proc/$(pgrep -f node)/fd | awk '{print $NF}' | sort | uniq -c | sort -rn
```

같은 파일이 수백 개 열려있으면 누수다. macOS에서는 `lsof -p <pid>`를 쓴다.

Node.js 내부에서는 `process.report.writeReport()`로 리포트를 생성하면 열린 핸들 목록이 나온다.

```javascript
process.on('SIGUSR2', () => {
  process.report.writeReport(`/tmp/report-${process.pid}.json`);
});
```

`kill -SIGUSR2 <pid>`로 트리거하면 리포트가 떨어진다. `libuv.handles` 섹션에 활성 핸들이 다 있다. fd 번호와 타입을 확인할 수 있어서 어디서 새는지 좁힐 때 유용하다.

### `graceful-fs` 라이브러리

fd 한계에 자주 부딪히는 워크로드(파일 수천 개를 동시에 처리)는 [`graceful-fs`](https://www.npmjs.com/package/graceful-fs)를 쓴다. `EMFILE`이 발생하면 큐에 넣어두고 fd가 풀릴 때까지 대기시킨다. 내부적으로 monkey-patch라서 호불호가 갈리지만, 빌드 도구나 정적 사이트 생성기처럼 IO가 폭주하는 환경에서는 거의 표준에 가깝다.

---

## 7. 자주 만나는 실수 정리

`fs.existsSync`로 파일 존재 여부를 먼저 확인하고 `fs.readFile`을 부르는 패턴은 race condition을 만든다. 그 사이에 파일이 삭제될 수 있다. 그냥 readFile을 호출하고 `ENOENT` 에러를 잡는 게 맞다.

`fs.stat`의 결과를 캐시해서 쓰면 안 된다. 파일 크기, mtime은 언제든 바뀐다. 매번 다시 stat을 부르거나, watcher와 함께 캐시를 무효화해야 한다.

상대 경로는 `process.cwd()` 기준이다. 데몬으로 돌아가는 프로세스에서 cwd는 예측하기 어렵다. `path.resolve(__dirname, ...)`로 절대 경로를 만들어 쓰는 습관이 필요하다.

`fs.copyFile`은 atomic이 아니다. 큰 파일을 복사하는 도중에 다른 프로세스가 읽으면 절반만 쓰인 상태를 본다. 중요한 파일은 같은 디렉토리에 복사한 다음 rename으로 옮긴다.

대용량 디렉토리에서 `fs.readdir`로 전체 목록을 메모리에 올리면 수십만 개 엔트리에서는 부담이다. Node 12+ 에서는 `withFileTypes: true` 옵션과 함께 `opendir`을 쓰면 async iterator로 받을 수 있다.

```javascript
const dir = await fs.opendir('./huge-dir');
for await (const entry of dir) {
  if (entry.isFile()) {
    // 처리
  }
}
```

`opendir`은 디렉토리를 닫는 책임이 호출자에게 있다. iterator를 끝까지 돌리면 자동으로 닫히지만, 중간에 break하면 명시적으로 `dir.close()`를 호출해야 한다.
