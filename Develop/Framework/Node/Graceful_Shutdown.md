---
title: Node.js 그레이스풀 셧다운 실무
tags:
  - nodejs
  - graceful-shutdown
  - sigterm
  - kubernetes
  - http
  - production
updated: 2026-06-04
---

# Node.js 그레이스풀 셧다운 실무

배포 한 번에 5xx 에러 그래프가 솟는 모습을 본 적 있는 사람이라면 그레이스풀 셧다운이 왜 필요한지 굳이 설명할 필요가 없다. 컨테이너가 죽으면서 처리 중이던 요청이 끊기고, 트랜잭션이 중간에 멈추고, 메시지 큐의 ack가 빠지면서 메시지가 재처리된다. 운영 환경에서 무중단 배포라는 말을 쓰려면 프로세스가 종료될 때 진행 중인 일을 마저 끝내고 나가는 코드가 반드시 들어가야 한다.

이 문서는 Node.js 프로세스가 SIGTERM을 받은 순간부터 실제로 메모리에서 사라지기까지의 과정을 추적한다. 단순히 `server.close()`를 부르라는 수준이 아니라, 왜 그것만으로는 부족하고 어디서 ECONNRESET이 튀는지, Kubernetes와 어떻게 협업해야 하는지를 다룬다.

---

## 1. 프로세스에 도착하는 시그널들

Node.js 프로세스를 외부에서 종료시키는 방법은 여러 가지다. 어떤 시그널이 오는지에 따라 처리가 달라진다.

### SIGTERM — 정상 종료 요청

가장 자주 마주치는 시그널이다. `docker stop`, `kubectl delete pod`, `systemctl stop`, PM2의 `reload` 등이 모두 SIGTERM을 먼저 보낸다. 프로세스에게 "정리하고 나갈 시간을 주겠다"는 의미다. Node.js는 기본 핸들러가 없어서 SIGTERM을 받으면 즉시 종료한다. 그래서 직접 핸들러를 등록해야 한다.

```js
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, starting graceful shutdown');
  await shutdown();
});
```

여기서 `process.exit(0)`을 핸들러 끝에 명시적으로 호출하지 않으면 이벤트 루프가 비어야 종료된다. 핸들러를 등록해두면 SIGTERM이 와도 자동 종료가 사라지므로 마무리 후 직접 `exit`을 불러줘야 한다.

### SIGINT — 사용자가 Ctrl+C를 눌렀을 때

터미널에서 직접 띄운 프로세스에 Ctrl+C를 누르면 SIGINT가 전달된다. 개발 중에는 SIGTERM과 똑같이 처리해도 무방하다. 다만 SIGINT가 두 번 연속 오는 경우(사용자가 Ctrl+C를 두 번 눌렀을 때)는 강제 종료로 받아들이는 게 일반적이다.

```js
let shuttingDown = false;
process.on('SIGINT', () => {
  if (shuttingDown) {
    console.log('Forced exit');
    process.exit(1);
  }
  shuttingDown = true;
  shutdown();
});
```

### SIGKILL — 막을 수 없는 종료

`kill -9`나 컨테이너의 grace period가 만료된 뒤 보내는 시그널이다. 프로세스 입장에서는 핸들러를 등록할 수도 없고 이 시그널을 잡을 수도 없다. 운영체제가 즉시 프로세스를 죽인다. 진행 중이던 요청, 열려 있던 DB 커넥션, 디스크에 flush되지 않은 버퍼는 전부 사라진다. 그레이스풀 셧다운의 목표는 SIGKILL이 오기 전에 모든 정리를 끝내는 것이다.

### SIGHUP — 설정 다시 읽기, 또는 터미널 단절

전통적으로 데몬에 설정 재로딩을 요청할 때 쓰던 시그널이다. 요즘 Node.js 백엔드에서는 거의 안 쓰지만, 컨테이너가 아닌 일반 호스트에서 nohup 없이 띄운 프로세스가 터미널 종료와 함께 받는 경우가 있다.

---

## 2. HTTP 서버를 닫는다는 의미

`http.Server.close()`를 부르면 서버가 "더 이상 새 연결을 받지 않는다"는 상태로 바뀐다. 여기서 오해가 많다.

`close()`는 즉시 끝나지 않는다. 새 연결은 거절하지만, 이미 맺어진 TCP 커넥션은 그대로 살아 있다. 진행 중인 요청이 끝나야 그 커넥션이 해제되고, 모든 커넥션이 해제되어야 콜백이 호출된다.

```js
server.close(err => {
  console.log('All connections drained');
});
```

이 콜백이 언제 불릴지 예측이 어렵다. 클라이언트가 keep-alive로 커넥션을 유지하고 있으면 응답이 끝나도 커넥션은 살아 있다. 클라이언트가 다음 요청을 보내지 않아도 idle 상태로 남는다. 즉 keep-alive 커넥션이 하나라도 있으면 `close()`의 콜백은 영원히 안 불릴 수 있다.

이 함정을 처음 만나면 "내 코드 다 짰는데 왜 안 죽지" 하면서 한참 헤맨다. SIGTERM 핸들러에 `server.close()`만 적어두면 keep-alive 커넥션 때문에 종료가 막혀 결국 SIGKILL로 강제 종료되고, 진행 중이던 요청은 끊긴다.

### closeIdleConnections와 closeAllConnections

Node 18.2부터 `Server` 객체에 두 메서드가 추가됐다. 이전에는 keep-alive 커넥션을 끊으려면 별도 라이브러리(`http-terminator`, `stoppable`)를 써야 했는데, 이제 코어 기능으로 들어왔다.

- `server.closeIdleConnections()`: 현재 요청을 처리하지 않고 idle 상태로 있는 keep-alive 커넥션을 즉시 끊는다.
- `server.closeAllConnections()`: 진행 중인 요청까지 포함해 모든 커넥션을 강제로 끊는다.

올바른 호출 순서는 이렇다.

```js
async function shutdown() {
  server.close();
  server.closeIdleConnections();

  const drainTimeout = setTimeout(() => {
    console.warn('Drain timeout, forcing connection close');
    server.closeAllConnections();
  }, 25_000);

  await new Promise(resolve => server.once('close', resolve));
  clearTimeout(drainTimeout);
}
```

`close()`로 신규 연결을 막고, `closeIdleConnections()`로 놀고 있는 커넥션을 즉시 정리한다. 진행 중인 요청은 응답이 끝날 때까지 기다린다. 일정 시간이 지나도 끝나지 않는 요청이 있으면 `closeAllConnections()`로 강제 종료한다.

이 타임아웃은 Kubernetes의 `terminationGracePeriodSeconds`보다 작게 잡아야 한다. 컨테이너의 grace period가 30초인데 Node 안에서 60초를 기다리게 짜면 SIGKILL이 먼저 도착해서 의미가 없다.

### Connection: close 헤더 강제

`closeAllConnections`를 쓰면 진행 중인 응답까지 잘려서 클라이언트가 ECONNRESET을 본다. 더 부드러운 방법은 응답 헤더에 `Connection: close`를 넣어 클라이언트가 자발적으로 커넥션을 끊게 하는 것이다.

```js
let isShuttingDown = false;

app.use((req, res, next) => {
  if (isShuttingDown) {
    res.set('Connection', 'close');
  }
  next();
});

async function shutdown() {
  isShuttingDown = true;
  server.close();
  // 이후 closeIdleConnections, 타임아웃 등 동일
}
```

이 헤더가 응답에 붙으면 클라이언트(브라우저, 다른 서비스의 HTTP 클라이언트)는 응답을 받은 즉시 커넥션을 닫는다. 다음 요청은 새 커넥션으로 새 인스턴스에 간다. 로드밸런서가 앞에 있다면 더 깔끔하게 끊어지고, 클라이언트는 ECONNRESET이 아니라 정상 종료된 커넥션을 본다.

---

## 3. 드레이닝 순서가 왜 중요한가

서버 하나만 닫으면 끝나는 게 아니다. 백엔드 프로세스에는 보통 다음이 같이 살아 있다.

- HTTP 서버 (외부 요청 처리)
- DB 커넥션 풀
- 메시지 큐 consumer (Kafka, SQS, RabbitMQ)
- 스케줄링된 cron job
- 외부 API 호출
- 백그라운드 워커

종료 순서가 잘못되면 진행 중이던 요청이 DB를 못 쓰거나, 큐에서 메시지를 꺼낸 직후 종료되어 메시지가 ack 없이 사라지거나, cron이 종료 직전에 새 작업을 시작해서 데이터가 깨진다.

올바른 순서는 들어오는 일감을 먼저 막고, 그 다음 진행 중인 일을 끝내고, 마지막에 외부 의존성을 닫는 것이다.

1. 헬스체크 엔드포인트가 unhealthy를 반환하기 시작한다. 로드밸런서가 신규 요청을 다른 인스턴스로 보낸다.
2. HTTP 서버가 `close()`로 신규 연결을 차단한다.
3. 큐 consumer가 새 메시지 받기를 중단한다(consumer.pause).
4. cron 스케줄러를 멈춘다.
5. 진행 중인 요청과 처리 중인 메시지가 끝나기를 기다린다.
6. DB 풀, Redis 클라이언트, 외부 SDK를 닫는다.
7. 프로세스 종료.

DB 풀을 먼저 닫으면 진행 중인 요청이 쿼리를 날렸을 때 "pool ended" 에러로 실패한다. 큐 consumer를 먼저 닫지 않으면 셧다운 도중에도 메시지를 계속 꺼내서 처리가 늘어진다.

```js
async function shutdown() {
  isShuttingDown = true;

  // 1. 헬스체크부터 unhealthy로 전환
  healthState.ready = false;

  // 2. 새로 들어오는 일감 차단
  server.close();
  server.closeIdleConnections();
  await kafkaConsumer.pause();
  scheduler.stop();

  // 3. 진행 중인 일이 끝나기를 기다림
  await Promise.race([
    Promise.all([
      waitForServerDrain(server),
      kafkaConsumer.drainInflight(),
      activeJobs.waitAll(),
    ]),
    timeout(25_000),
  ]);

  // 4. 강제로 남은 커넥션 정리
  server.closeAllConnections();

  // 5. 외부 의존성 닫기
  await kafkaConsumer.disconnect();
  await dbPool.end();
  await redis.quit();

  process.exit(0);
}
```

여기서 `healthState.ready = false`로 바꾼 뒤 곧바로 `server.close()`를 부른다고 가정하면 안 된다. Kubernetes의 readiness probe는 보통 몇 초 간격으로 폴링한다. unhealthy 응답을 한 번 보냈다고 해서 즉시 로드밸런서가 트래픽을 끊지는 않는다. 그래서 readiness를 false로 바꾼 뒤 짧게(2~5초) 기다려서 로드밸런서가 인지할 시간을 주는 패턴이 자주 쓰인다.

---

## 4. Kubernetes에서의 셧다운 흐름

컨테이너 환경에서는 그레이스풀 셧다운의 절반이 애플리케이션 코드 바깥에 있다. Pod이 삭제되는 흐름을 알아야 코드를 어떻게 짤지 결정할 수 있다.

Pod에 삭제 명령이 떨어지면 kubelet은 다음을 동시에 시작한다.

- Endpoints에서 해당 Pod의 IP를 제거 (kube-proxy/ingress controller가 라우팅 테이블을 갱신)
- 컨테이너에 `preStop` 훅이 정의되어 있으면 실행
- preStop이 끝나면 컨테이너의 PID 1에 SIGTERM 전송
- `terminationGracePeriodSeconds`(기본 30초)가 지나면 SIGKILL 전송

여기서 함정이 두 개 있다.

### 함정 1: Endpoint 제거가 즉시 반영되지 않는다

Endpoints API에서 Pod IP가 빠졌다고 해도, 클러스터의 모든 노드에 있는 kube-proxy가 iptables를 갱신할 때까지 시간이 걸린다. ingress controller나 사이드카 프록시(Envoy 등)도 마찬가지다. 그래서 Pod에 SIGTERM이 도착한 직후에도 1~3초 동안은 새 요청이 계속 들어올 수 있다.

이 문제 때문에 `preStop`에 짧은 sleep을 넣는 패턴이 표준처럼 자리 잡았다.

```yaml
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 5"]
```

preStop이 실행되는 동안에도 컨테이너는 계속 트래픽을 받는다. 5초 동안 로드밸런서가 라우팅 테이블을 갱신할 시간을 주고, 그 뒤 SIGTERM이 도착해서 애플리케이션이 종료를 시작한다. 애플리케이션 코드 안에서 sleep을 넣는 것보다 preStop으로 빼는 게 깔끔하다. 코드가 단순해지고, 종료 시점을 인프라 레벨에서 통제할 수 있다.

### 함정 2: terminationGracePeriodSeconds는 preStop과 SIGTERM을 합친 시간이다

`terminationGracePeriodSeconds: 30`은 preStop이 시작된 시점부터 SIGKILL이 떨어지기까지의 총 시간이다. preStop에서 sleep 5를 했다면 SIGTERM 이후로는 25초만 남는다. 애플리케이션 안에서 `setTimeout` 값을 25초로 잡았는데 preStop sleep까지 합쳐서 grace period에 맞췄다고 착각하면 안 된다.

권장 구성은 다음과 같다.

- `terminationGracePeriodSeconds`: 60
- preStop sleep: 5초
- 애플리케이션 안의 강제 종료 타임아웃: 50초

여유를 두는 이유는 큐 메시지 처리, 외부 API 응답 대기 같은 게 예상보다 오래 걸리기 때문이다. 짧게 잡으면 SIGKILL이 먼저 도착해서 메시지가 ack 없이 사라진다.

### 함정 3: Job/CronJob의 preStop은 다르게 동작한다

Deployment에서 쓰던 preStop 패턴이 Job이나 CronJob에서는 그대로 안 먹힌다. Job은 처음부터 트래픽을 받지 않으므로 preStop sleep은 의미가 없다. 대신 작업이 끝나면 자발적으로 종료되는 코드가 더 중요하다.

---

## 5. PM2 reload와의 차이

PM2의 `reload`는 그레이스풀 재시작을 지원한다고 광고하지만 동작 방식이 Kubernetes와 다르다. 차이를 모르고 코드를 짜면 한쪽에서만 깔끔하게 동작한다.

PM2 cluster 모드에서 `pm2 reload <app>`을 부르면 PM2는 워커를 하나씩 재시작한다. 새 워커가 뜨고 listen을 시작한 뒤에 기존 워커에 SIGINT(기본값)를 보낸다. 워커는 정해진 시간(`kill_timeout`, 기본 1.6초) 안에 종료되어야 한다. 안 끝나면 SIGKILL이다.

문제는 기본 `kill_timeout`이 너무 짧다는 것이다. 1.6초 안에 진행 중인 요청을 다 끝낼 수 있는 백엔드는 거의 없다.

```js
// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'api',
    script: 'server.js',
    instances: 4,
    exec_mode: 'cluster',
    kill_timeout: 30000,
    wait_ready: true,
    listen_timeout: 10000,
  }],
};
```

`kill_timeout`을 30초로 늘려 충분한 드레인 시간을 주고, `wait_ready: true`로 새 워커가 `process.send('ready')`를 보낼 때까지 PM2가 다음 워커로 넘어가지 않게 한다.

```js
// server.js
server.listen(PORT, () => {
  if (process.send) {
    process.send('ready');
  }
});
```

또 PM2는 기본적으로 SIGINT를 보낸다. SIGTERM 핸들러만 등록하고 SIGINT 핸들러는 없으면 PM2 reload 시에 곧바로 종료된다. 두 시그널 다 같은 핸들러로 처리하거나, PM2 옵션 `kill_signal: 'SIGTERM'`을 명시한다.

Kubernetes와 PM2를 같이 쓰는 경우는 드물지만, 로컬 개발은 PM2고 배포는 K8s라면 두 환경 모두에서 동작하도록 SIGTERM/SIGINT 둘 다 처리해두는 게 안전하다.

---

## 6. ECONNRESET이 발생하는 실제 케이스

운영에서 그레이스풀 셧다운을 제대로 짰는데도 클라이언트 쪽 로그에 ECONNRESET이 찍히는 일이 있다. 원인은 보통 몇 가지 패턴으로 좁혀진다.

### 케이스 1: 로드밸런서가 keep-alive 커넥션을 재사용한다

ALB, NLB, nginx 같은 L4/L7 로드밸런서는 백엔드와 keep-alive 커넥션을 유지한다. 백엔드 Pod이 사라져도 LB는 잠시 동안 그 Pod으로 가는 커넥션을 재사용한다. Pod이 SIGTERM을 받고 `server.close()`를 부르면 신규 연결만 거절하지만, LB는 이미 맺어둔 커넥션으로 요청을 계속 보낸다. Pod이 `closeAllConnections()`를 부르는 순간 LB가 쓰던 커넥션이 끊겨 ECONNRESET이 나는 것이다.

해법은 두 가지다.

첫째, `Connection: close` 헤더를 응답에 강제로 붙인다. LB가 응답을 받은 뒤 즉시 커넥션을 닫고 다음 요청은 새 커넥션으로 다른 백엔드에 간다.

둘째, 종료 직전에 짧은 시간을 둔다. preStop sleep으로 LB가 헬스체크 실패를 감지하고 라우팅 테이블을 갱신할 여유를 준다.

### 케이스 2: 클라이언트가 keep-alive를 재사용해 죽은 커넥션에 요청을 보낸다

서비스 간 통신에서 자주 본다. 클라이언트가 keep-alive로 커넥션을 풀에 넣어두고, 그 커넥션 너머의 서버가 죽었다는 걸 모르고 다음 요청을 보낸다. 서버가 보낸 FIN을 클라이언트가 처리하기 전에 새 요청을 보내면 RST가 돌아오면서 ECONNRESET이 된다.

이건 호출하는 쪽 클라이언트 설정의 문제다. axios의 http agent에 `keepAlive`만 켜두고 idle timeout을 설정 안 하면 서버보다 클라이언트가 더 오래 커넥션을 들고 있다가 이런 일이 생긴다. 클라이언트 keep-alive timeout은 서버보다 짧게 잡는 게 원칙이다.

### 케이스 3: ALB의 idle timeout과 Node의 keepAliveTimeout 차이

AWS ALB의 기본 idle timeout이 60초인 환경에서 Node의 `server.keepAliveTimeout`을 60초보다 짧게(예: 5초 기본값) 두면 ALB가 커넥션을 재사용하려는 순간 서버는 이미 그 커넥션을 닫은 상태일 수 있다. 이때 ALB는 502 또는 504를 클라이언트에 돌려준다. 셧다운과 직접 관련은 없지만 ECONNRESET처럼 보이는 에러의 흔한 원인이다.

해법은 명확하다. `server.keepAliveTimeout`을 ALB idle timeout보다 길게 잡는다.

```js
const server = http.createServer(app);
server.keepAliveTimeout = 65_000;
server.headersTimeout = 66_000;
```

`headersTimeout`은 반드시 `keepAliveTimeout`보다 커야 한다. Node 17 이전에는 헤더 타임아웃이 더 작으면 race condition이 발생해서 정상 요청이 잘리는 일이 있었다. 지금은 자동으로 보정되지만 명시적으로 큰 값을 주는 게 안전하다.

### 케이스 4: closeAllConnections가 너무 일찍 호출된다

타임아웃을 5초로 잡고 `closeAllConnections()`를 부르면, 응답을 보내는 중인 커넥션도 자른다. 이게 진짜 ECONNRESET의 흔한 원인이다. 클라이언트는 응답을 절반쯤 받다가 잘렸으니 ECONNRESET을 본다.

해법은 강제 종료 타임아웃을 충분히 길게 잡고, 그 시간 안에 진짜로 못 끝낼 정도로 느린 요청이 있다면 그 요청 자체에 별도의 타임아웃을 거는 것이다. 30초 안에 끝나야 하는 요청이라면 핸들러 안에서도 30초 타임아웃을 걸어 응답을 보내고 끝낸다. 셧다운 타임아웃이 모든 요청의 maximum 길이가 되어서는 안 된다.

---

## 7. 메시지 큐 consumer의 셧다운

HTTP 서버는 `close()`로 입구를 막는 게 그나마 쉽다. 큐 consumer는 더 까다롭다. 한 번에 여러 메시지를 prefetch 해두고 비동기로 처리하는 구조가 많아 진행 중인 메시지가 정확히 몇 개인지 추적해야 한다.

```js
class MessageConsumer {
  constructor() {
    this.inflight = new Set();
    this.paused = false;
  }

  async onMessage(msg) {
    if (this.paused) {
      await this.requeue(msg);
      return;
    }

    const promise = this.process(msg).finally(() => {
      this.inflight.delete(promise);
    });
    this.inflight.add(promise);
    await promise;
  }

  async pause() {
    this.paused = true;
    await this.consumer.pause();
  }

  async drainInflight() {
    while (this.inflight.size > 0) {
      await Promise.race([
        Promise.all([...this.inflight]),
        new Promise(r => setTimeout(r, 1000)),
      ]);
    }
  }
}
```

`pause`는 새 메시지가 들어오는 걸 막는다. `drainInflight`는 진행 중인 메시지가 끝날 때까지 기다린다. 여기서 중요한 건 ack 타이밍이다. 메시지를 처리한 뒤 ack를 보내기 전에 프로세스가 죽으면 큐는 메시지를 다른 consumer에게 재배달한다. 멱등성이 보장되지 않은 작업이라면 이중 처리가 일어난다.

Kafka처럼 commit offset 방식을 쓰는 경우는 셧다운 직전에 명시적으로 commit을 호출하는 게 안전하다. RabbitMQ의 manual ack라면 메시지 처리 직후 ack를 보내고 다음 메시지로 넘어가는 패턴을 지킨다.

---

## 8. 전체를 묶는 종료 핸들러

지금까지 다룬 내용을 하나의 핸들러로 정리하면 다음과 같다.

```js
const http = require('node:http');
const { setTimeout: sleep } = require('node:timers/promises');

const SHUTDOWN_TIMEOUT_MS = 50_000;
const READINESS_DELAY_MS = 5_000;

let isShuttingDown = false;
const server = http.createServer(app);
server.keepAliveTimeout = 65_000;
server.headersTimeout = 66_000;

app.get('/health/ready', (req, res) => {
  if (isShuttingDown) return res.status(503).send('shutting down');
  res.send('ok');
});

app.use((req, res, next) => {
  if (isShuttingDown) res.set('Connection', 'close');
  next();
});

async function shutdown(signal) {
  if (isShuttingDown) return;
  isShuttingDown = true;
  console.log(`Received ${signal}, shutting down`);

  await sleep(READINESS_DELAY_MS);

  server.close();
  server.closeIdleConnections();

  await kafkaConsumer.pause();
  scheduler.stop();

  const forceCloseTimer = setTimeout(() => {
    console.warn('Force closing remaining connections');
    server.closeAllConnections();
  }, SHUTDOWN_TIMEOUT_MS - 10_000);

  try {
    await Promise.race([
      Promise.all([
        new Promise(resolve => server.once('close', resolve)),
        kafkaConsumer.drainInflight(),
        activeJobs.waitAll(),
      ]),
      sleep(SHUTDOWN_TIMEOUT_MS),
    ]);
  } finally {
    clearTimeout(forceCloseTimer);
  }

  await kafkaConsumer.disconnect();
  await dbPool.end();
  await redis.quit();

  console.log('Shutdown complete');
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```

이 코드는 시작점이지 정답이 아니다. 사용하는 DB 드라이버, 큐 라이브러리, 백그라운드 워커마다 종료 API가 다르고 race condition이 다르게 생긴다. 실제로 운영에 올리기 전에 부하 상태에서 종료를 반복 시도해보면서 ECONNRESET, 502, 메시지 재처리가 일어나는 지점을 직접 확인하는 게 가장 확실하다.

---

## 9. 디버깅과 검증

그레이스풀 셧다운은 한 번 짜두면 잊어버리기 쉽다. 인프라가 바뀌거나 새 의존성이 추가되면 다시 깨진다. 검증 방법을 알아두면 도움이 된다.

부하를 주면서 종료를 반복한다. `wrk`나 `hey`로 초당 수백 요청을 보내면서 컨테이너를 `kubectl delete pod`로 죽인다. 클라이언트 쪽에서 5xx, ECONNRESET, 응답 시간 스파이크가 몇 건 나오는지 본다. 이상적으로는 0이어야 한다.

종료 단계마다 로그를 남긴다. "received SIGTERM", "server closed for new connections", "inflight requests = N", "all drained", "db pool ended" 같은 식으로 단계별 시간을 찍어두면 어느 단계에서 막히는지 추적이 쉽다. 운영 중에 셧다운이 grace period 안에 못 끝나는 일이 생기면 이 로그가 첫 번째 단서다.

`process.exit(0)` 호출 직전 `process._getActiveHandles()`나 `process._getActiveRequests()`로 닫지 않은 리소스를 확인할 수 있다. 정식 API는 아니지만 디버깅에 유용하다. 종료가 안 되는 이유가 누군가 close하지 않은 setInterval인 경우가 의외로 많다.
