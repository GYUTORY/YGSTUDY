---
title: Node.js child_process 모듈 실무 심화
tags:
  - nodejs
  - child_process
  - spawn
  - fork
  - ipc
  - signal
updated: 2026-06-03
---

# Node.js child_process 모듈 실무 심화

Node.js로 백엔드를 만들다 보면 결국 외부 프로세스를 띄워야 하는 순간이 온다. ffmpeg로 영상을 변환하고, ImageMagick으로 썸네일을 만들고, git을 호출해 저장소를 클론하고, Python 스크립트로 ML 추론을 돌린다. 처음에는 `exec` 한 줄로 끝나지만, 트래픽이 늘면 메모리가 터지고, 자식 프로세스가 죽지 않고 좀비로 남고, Ctrl+C로도 안 죽는 프로세스가 생긴다. 이 문서는 `child_process` 모듈을 운영하면서 실제로 부딪힌 문제와 그 원인을 정리한다.

---

## 1. spawn, exec, execFile, fork — 어떤 걸 언제 쓰는가

`child_process` 모듈은 자식 프로세스를 만드는 네 가지 함수를 제공한다. 이름만 보면 비슷해 보이지만 내부 동작과 위험성이 다르다. 잘못 고르면 RCE 취약점이 생기거나 메모리가 터진다.

### spawn — 가장 기본이자 가장 안전한 선택

`spawn`은 새 프로세스를 띄우고 그 stdin/stdout/stderr를 스트림으로 노출한다. 셸을 거치지 않고 실행 파일을 직접 fork+exec 하므로 인자가 셸에 의해 재해석되지 않는다. 즉 사용자 입력을 인자로 넘겨도 명령어 주입(command injection) 위험이 거의 없다.

```js
const { spawn } = require('node:child_process');

const child = spawn('ffmpeg', [
  '-i', userProvidedPath,
  '-vcodec', 'libx264',
  'output.mp4'
]);

child.stdout.on('data', chunk => process.stdout.write(chunk));
child.stderr.on('data', chunk => process.stderr.write(chunk));
child.on('exit', code => console.log('exit', code));
```

`userProvidedPath`에 `; rm -rf /` 같은 게 들어가도 셸이 해석하지 않으니 그저 그 문자열이 그대로 파일 경로로 ffmpeg에 전달될 뿐이다. 출력이 큰 작업(영상 변환 로그, 빌드 로그)에서는 거의 무조건 `spawn`을 쓴다. 스트림이라 메모리에 쌓이지 않는다.

### exec — 셸을 거치는 편의 함수

`exec`는 내부적으로 `/bin/sh -c <command>` (윈도우는 `cmd.exe /d /s /c`)를 실행한다. 명령어 한 줄을 셸 문법 그대로 쓸 수 있어 편하다. 파이프, 리다이렉트, 환경 변수 확장, 와일드카드가 다 동작한다.

```js
const { exec } = require('node:child_process');

exec('ls -al | grep node_modules', (err, stdout, stderr) => {
  if (err) return console.error(err);
  console.log(stdout);
});
```

문제는 두 가지다. 첫째, 사용자 입력을 그대로 끼워 넣으면 RCE가 된다. `exec(\`grep ${keyword} log.txt\`)`에 keyword로 `foo; cat /etc/passwd`가 들어오면 그대로 실행된다. 둘째, stdout/stderr를 통째로 메모리에 모았다가 콜백에 넘기기 때문에 출력이 큰 명령에는 부적합하다. 기본 `maxBuffer`가 1MB라 그걸 넘기면 자식 프로세스가 SIGTERM으로 죽는다.

### execFile — 셸 없이 실행 파일 직접 호출

`execFile`은 셸을 거치지 않고 실행 파일을 직접 호출한다. 인자 배열로 넘기므로 명령어 주입 위험이 없다. 출력 처리는 `exec`와 같아서 콜백에 stdout/stderr를 한꺼번에 넘긴다.

```js
const { execFile } = require('node:child_process');

execFile('git', ['log', '--oneline', '-n', '10'], (err, stdout) => {
  if (err) return console.error(err);
  console.log(stdout);
});
```

출력이 작고, 결과를 한 번에 받고 싶고, 셸 기능이 필요 없을 때 `execFile`이 가장 깔끔하다. 예를 들어 git 명령으로 커밋 해시를 가져오거나, `uname -a`로 호스트 정보를 가져올 때 쓴다.

### fork — Node.js 자식 전용, IPC 채널 자동 연결

`fork`는 `spawn`의 특수 형태인데, 자식이 반드시 Node.js 스크립트여야 한다. 부모-자식 사이에 IPC 채널이 자동으로 만들어져서 `process.send()`와 `process.on('message')`로 객체를 주고받을 수 있다. CPU 바운드 작업을 별도 프로세스로 분리할 때 자주 쓴다.

```js
const { fork } = require('node:child_process');

const worker = fork('./worker.js');
worker.send({ task: 'render', payload: data });
worker.on('message', result => {
  console.log('got result', result);
});
```

worker.js는 부모로부터 메시지를 받아 처리한다.

```js
process.on('message', msg => {
  const result = heavyWork(msg.payload);
  process.send({ ok: true, result });
});
```

요지는 이렇다. 사용자 입력이 닿는다면 `exec`는 일단 배제한다. 출력이 크면 `spawn`. 작은 출력 한 번이면 `execFile`. Node.js 자식과 양방향 통신이 필요하면 `fork`.

---

## 2. stdio 옵션과 파이프 버퍼링 데드락

`spawn`의 `stdio` 옵션은 자식의 표준 입출력을 어디에 연결할지 결정한다. 기본값은 `'pipe'`인데, 이게 종종 데드락의 원인이 된다.

### 파이프 버퍼는 의외로 작다

리눅스 파이프 버퍼는 보통 64KB다(`/proc/sys/fs/pipe-max-size` 참고). 자식이 stdout으로 데이터를 토해내는데 부모가 그 데이터를 안 읽으면, 자식의 write가 블로킹된다. 그 상태에서 부모가 자식 종료를 기다리면 둘 다 멈춰버린다.

```js
const { spawn } = require('node:child_process');

const child = spawn('node', ['-e', `
  for (let i = 0; i < 1_000_000; i++) {
    console.log('line', i);
  }
`]);

// stdout을 안 읽고 종료만 기다리면 데드락
child.on('exit', code => console.log('done', code));
```

위 코드는 영원히 끝나지 않는다. 자식의 stdout 버퍼가 가득 차서 `console.log`가 블로킹되고, 부모는 자식이 종료되기만 기다린다. 해결책은 stdout을 소비하거나 아예 무시하도록 설정하는 것이다.

```js
const child = spawn('node', ['-e', script], {
  stdio: ['ignore', 'ignore', 'inherit']
});
```

`'ignore'`는 `/dev/null`로 연결, `'inherit'`는 부모의 fd를 그대로 사용, `'pipe'`는 부모-자식 사이에 파이프를 만든다. 자식 출력을 어차피 쓸 일이 없으면 `'ignore'`로 둬야 한다.

### stdio 배열 순서

`stdio: ['ignore', 'pipe', 'pipe']`는 `[stdin, stdout, stderr]` 순서다. 자식에게 입력을 줄 필요가 없으면 stdin은 `'ignore'`로 두자. 안 그러면 자식이 stdin에서 EOF를 기다리며 종료하지 않는 경우가 생긴다. 예를 들어 `cat`을 인자 없이 spawn 하면 stdin을 무한정 기다린다.

### 파일 디스크립터를 자식에 넘기기

소켓이나 파일을 자식에게 직접 넘길 수도 있다. 4번째 요소부터 추가 fd를 정의할 수 있다.

```js
const fs = require('node:fs');
const logFd = fs.openSync('/var/log/job.log', 'a');

const child = spawn('long_running_job', [], {
  stdio: ['ignore', logFd, logFd]
});

fs.closeSync(logFd);
```

자식 stdout/stderr가 직접 로그 파일로 쓰여진다. 부모가 중간에서 데이터를 받아 다시 쓸 필요가 없으니 성능도 좋고 데드락 위험도 없다.

---

## 3. maxBuffer 초과와 ERR_CHILD_PROCESS_STDIO_MAXBUFFER

`exec`와 `execFile`은 자식의 출력을 메모리에 모은다. 그 한계가 `maxBuffer`다. 기본값이 1024 * 1024 바이트, 즉 1MB다. 출력이 이걸 넘기는 순간 자식은 SIGTERM으로 종료되고, 콜백에는 `ERR_CHILD_PROCESS_STDIO_MAXBUFFER` 에러가 떨어진다.

```js
const { exec } = require('node:child_process');

exec('find / -type f', (err, stdout, stderr) => {
  if (err) {
    console.error(err.code); // ERR_CHILD_PROCESS_STDIO_MAXBUFFER
  }
});
```

흔한 시나리오가 있다. 개발 환경에서는 출력이 작아 잘 동작하다가, 운영 환경에서 데이터가 많아지면 갑자기 깨진다. `git log` 같은 명령도 커밋이 누적되면 1MB를 쉽게 넘긴다. 임시방편으로 `maxBuffer`를 키우는 방법이 있다.

```js
exec('git log --pretty=format:%H', { maxBuffer: 100 * 1024 * 1024 }, cb);
```

그런데 이건 근본 해결책이 아니다. 출력이 얼마나 커질지 모르는 상황이면 결국 한계를 넘는 순간이 온다. 메모리 100MB를 단일 콜백에 쌓는 것도 위험하다. 출력이 큰 게 예상되면 `exec` 대신 `spawn`을 쓰고 스트림으로 처리한다.

```js
const { spawn } = require('node:child_process');
const readline = require('node:readline');

const git = spawn('git', ['log', '--pretty=format:%H']);
const rl = readline.createInterface({ input: git.stdout });

rl.on('line', hash => {
  // 한 줄씩 처리, 메모리는 안 쌓인다
});

git.on('exit', () => rl.close());
```

`maxBuffer`를 만났을 때 자식이 SIGTERM으로 죽는 점도 주의할 필요가 있다. 자식이 파일을 쓰고 있었다면 어중간한 상태로 잘릴 수 있다. 트랜잭션이 필요한 작업에는 더더욱 `exec`/`execFile`을 피해야 한다.

---

## 4. fork와 IPC 채널의 동작

`fork`로 띄운 자식은 부모와 IPC 채널을 자동으로 갖는다. 이 채널은 운영체제 수준의 파이프인데, Node.js가 그 위에 JSON 직렬화를 얹어 객체를 주고받을 수 있게 만들었다.

### message 전송과 직렬화 비용

`process.send(obj)`를 호출하면 `obj`가 JSON으로 직렬화되어 파이프로 전송된다. 받는 쪽에서는 다시 파싱한다. 작은 객체는 빠르지만, 큰 Buffer를 자주 주고받으면 직렬화 비용이 무시할 수 없다. 100MB짜리 Buffer를 그대로 보내면 JSON 변환 과정에서 메모리가 두세 배로 부풀고, base64 인코딩으로 크기까지 커진다.

```js
// 안 좋은 예
worker.send({ buffer: largeBuffer });

// 차라리 파일로 쓰고 경로만 넘기는 게 낫다
fs.writeFileSync('/tmp/data.bin', largeBuffer);
worker.send({ path: '/tmp/data.bin' });
```

대용량 데이터는 공유 메모리 대안인 `worker_threads`의 `SharedArrayBuffer` 쪽이 훨씬 빠르다. `fork`는 프로세스 격리가 필요하거나 자식이 죽어도 부모가 살아남아야 하는 경우에 쓴다.

### 소켓과 서버 핸들 전송

`process.send`의 두 번째 인자로 `net.Socket`이나 `net.Server`를 넘길 수 있다. 운영체제 수준에서 파일 디스크립터가 자식에게 복제된다. 클러스터링의 기본 메커니즘이 이거다.

```js
const server = require('node:http').createServer();
server.listen(0, () => {
  worker.send('server', server);
});
```

자식 쪽에서는 `message` 이벤트의 두 번째 인자로 핸들을 받는다.

```js
process.on('message', (msg, handle) => {
  if (msg === 'server') {
    handle.on('connection', socket => {
      // 같은 포트의 연결을 자식이 직접 처리
    });
  }
});
```

이 메커니즘 덕분에 Node.js의 `cluster` 모듈이 마스터에서 listen하고 워커가 연결을 나눠 받는 구조를 구현할 수 있다.

### IPC가 끊어졌을 때

부모가 갑자기 죽으면 자식의 IPC 채널이 닫히고 `disconnect` 이벤트가 발생한다. 자식 쪽에서 이를 처리하지 않으면 자식이 자기 일을 계속하다가 누구도 결과를 받아가지 않는 좀비 작업이 된다. 일반적으로 자식은 부모가 죽으면 같이 죽도록 설계한다.

```js
// worker.js
process.on('disconnect', () => {
  // 부모가 죽었다, 자식도 정리하고 종료
  cleanup();
  process.exit(0);
});
```

---

## 5. 좀비 프로세스 회피

좀비(`<defunct>`)는 자식 프로세스가 종료했지만 부모가 그 종료 상태를 수거(`wait`)하지 않아서 프로세스 테이블에 남아 있는 상태다. PID만 잡고 자원은 거의 안 먹지만, 수십만 개 쌓이면 PID 고갈이 일어난다.

Node.js가 자식을 `spawn`/`fork`로 만들면 내부적으로 `exit`/`close` 이벤트 핸들러가 SIGCHLD를 처리하면서 자동으로 wait를 호출한다. 그래서 보통은 좀비가 안 생긴다. 문제가 되는 경우는 두 가지다.

### detached로 띄운 자식을 잊는 경우

`spawn`에 `detached: true`를 주면 자식이 부모와 독립된 프로세스 그룹의 리더가 된다. 부모가 죽어도 자식이 살아남는다. 데몬을 띄울 때 쓴다. 그런데 자식의 stdio를 부모와 연결한 채로 두면 부모가 자식을 참조하게 되어 의도가 깨진다.

```js
const child = spawn('node', ['daemon.js'], {
  detached: true,
  stdio: 'ignore'
});

child.unref(); // 부모 이벤트 루프에서 자식 제거
```

`unref`를 호출해야 부모가 자식의 종료를 기다리지 않고 끝낼 수 있다. 반대로 `unref`를 잊으면 부모가 안 죽는 문제가 생긴다.

### 부모가 자식보다 먼저 죽는 경우

부모 Node.js 프로세스가 SIGKILL로 강제 종료되면 자식의 종료 상태를 수거할 누군가가 필요하다. 리눅스에서는 init(PID 1)이 그 역할을 한다. 컨테이너 환경에서는 PID 1이 init이 아니라 애플리케이션 프로세스인 경우가 많은데, 이때 PID 1이 SIGCHLD를 처리하지 않으면 좀비가 쌓인다.

도커에서 Node.js를 PID 1로 띄우면 자식 프로세스가 좀비로 남는 사례가 흔하다. 대처법은 두 가지다.

첫째, `docker run --init` 또는 `docker-compose`의 `init: true`를 켠다. 도커가 `tini`라는 작은 init 프로세스를 PID 1로 띄우고 그 자식으로 Node.js를 둔다. tini가 좀비를 수거해 준다.

둘째, Node.js를 PID 1로 두지 말고 `dumb-init` 같은 init 래퍼로 감싼다. Dockerfile에 이렇게 쓴다.

```dockerfile
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]
```

운영 환경에서 컨테이너 위에 자식 프로세스를 띄우는 서비스라면 이건 거의 필수다. 안 그러면 ffmpeg, ImageMagick 같은 작업이 누적되며 좀비가 쌓이고, `kubectl exec`로 들어가 `ps aux | grep defunct` 하면 수백 줄이 떠 있다.

---

## 6. 시그널 처리와 graceful shutdown

자식 프로세스를 운영하려면 시그널 의미를 정확히 알아야 한다. 잘못 알면 데이터가 깨지거나 프로세스가 안 죽는다.

### SIGTERM, SIGINT, SIGKILL의 차이

- `SIGTERM`(15)은 "정상적으로 종료해 달라"는 요청이다. 프로세스가 가로채서 정리 작업을 할 수 있다.
- `SIGINT`(2)는 Ctrl+C로 발생한다. 보통 SIGTERM과 같게 처리한다.
- `SIGKILL`(9)은 커널이 강제로 죽인다. 프로세스가 가로챌 수 없고, 어떤 정리 작업도 못 한다. 열려 있던 파일, 트랜잭션이 그대로 잘린다.

부모에서 자식을 종료시킬 때는 일단 SIGTERM을 보내고, 일정 시간(예: 10초) 안에 안 죽으면 SIGKILL을 보낸다.

```js
const child = spawn('long_job', []);

function shutdown() {
  child.kill('SIGTERM');
  const t = setTimeout(() => {
    child.kill('SIGKILL');
  }, 10_000);
  child.on('exit', () => clearTimeout(t));
}
```

### Node.js 자식의 graceful shutdown

자식이 Node.js라면 SIGTERM을 받으면 진행 중인 작업을 끝내고 종료해야 한다. HTTP 서버라면 listen을 멈추고 진행 중 요청을 마저 처리한다.

```js
const server = http.createServer(handler);
server.listen(3000);

let shuttingDown = false;

process.on('SIGTERM', () => {
  if (shuttingDown) return;
  shuttingDown = true;

  server.close(err => {
    if (err) process.exit(1);
    process.exit(0);
  });

  setTimeout(() => process.exit(1), 15_000).unref();
});
```

`server.close()`는 새 연결을 거부하지만 기존 연결은 응답이 끝날 때까지 기다린다. keep-alive 연결이 오래 살아 있으면 영원히 안 끝날 수 있어서 강제 종료 타이머를 같이 둔다. 더 정교하게는 `closeAllConnections()`(Node 18.2+) 또는 `closeIdleConnections()`로 keep-alive를 정리한다.

### 자식 프로세스 그룹과 SIGTERM 전파

`spawn`으로 띄운 자식이 다시 자식을 만들면(예: 셸 스크립트가 ffmpeg를 띄움), 자식만 죽여서는 손자가 살아남는다. 셸은 죽지만 셸이 띄운 ffmpeg는 PID 1(또는 init)로 reparenting 되어 계속 돈다.

해결책은 자식을 프로세스 그룹의 리더로 만들고, 그룹 전체에 시그널을 보내는 것이다.

```js
const child = spawn('sh', ['-c', 'ffmpeg -i ... output.mp4'], {
  detached: true
});

// 자식 PID에 음수를 붙이면 같은 그룹 전체에 시그널이 간다
process.kill(-child.pid, 'SIGTERM');
```

`detached: true`로 자식을 새 그룹의 리더로 만들고, `process.kill(-pid, ...)`로 그룹 전체를 죽인다. 이걸 모르면 Docker 컨테이너에서 외부 도구를 띄웠다가 컨테이너 종료가 안 되는 문제로 한참 헤맨다.

### 시그널을 받았는데 코드가 0이 아닌 이유

자식이 시그널로 죽으면 `exit` 이벤트의 첫 인자(code)는 `null`이고, 두 번째 인자(signal)에 시그널 이름이 들어온다. 이걸 모르고 `code === 0`만 체크하면 정상 종료인지 시그널로 죽었는지 구분이 안 된다.

```js
child.on('exit', (code, signal) => {
  if (signal) {
    console.log('killed by', signal);
  } else if (code === 0) {
    console.log('ok');
  } else {
    console.log('failed with code', code);
  }
});
```

운영 코드에서는 시그널로 죽은 경우와 정상 종료를 구분해서 다르게 처리한다. 예를 들어 SIGTERM은 재시도하지 않고, 에러 코드는 재시도하는 식이다.

---

## 7. 정리

`child_process`는 표면적으로는 간단해 보이는데 운영에 들어가면 신경 쓸 게 많다. 핵심은 다음과 같다.

사용자 입력이 닿는 경로에서는 절대 `exec`를 쓰지 않는다. `spawn`이나 `execFile`로 인자 배열을 넘긴다. 출력이 큰 작업은 `spawn`으로 스트림 처리한다. `exec`의 1MB 한계는 운영 환경에서 반드시 터진다.

`stdio` 설정을 신경 써야 한다. 안 읽을 출력은 `'ignore'`. 부모와 같은 로그로 흘릴 거면 `'inherit'`. 파이프로 받으면 반드시 소비한다. 데드락은 거의 항상 stdio를 잘못 다뤄서 생긴다.

자식이 Node.js라면 `fork`로 IPC 채널을 쓴다. 큰 Buffer는 직렬화 비용이 크니 공유 메모리가 필요하면 `worker_threads`를 고려한다.

컨테이너에서 외부 프로세스를 띄우면 좀비 문제가 생긴다. `tini` 또는 `dumb-init`으로 PID 1을 감싼다. 도커는 `--init` 플래그가 있다.

종료는 항상 SIGTERM → timeout → SIGKILL 순서로 한다. 자식이 손자를 만든다면 `detached`로 프로세스 그룹을 잡고 그룹 전체를 죽여야 한다. 그러지 않으면 손자가 살아남아 자원을 잡는다.
