---
title: Node.js Permission Model 심화
tags:
  - nodejs
  - permission-model
  - security
  - sandboxing
  - node20
updated: 2026-06-06
---

# Node.js Permission Model 심화

Node 20에서 `--permission` 플래그가 처음 들어왔다. 한 마디로 "프로세스가 무엇을 만질 수 있는지" 를 부팅 시점에 화이트리스트로 묶어두는 기능이다. 파일 시스템·네트워크·자식 프로세스·워커 스레드를 따로따로 잠근다. 실험적이라는 꼬리표가 22 LTS 시점에도 붙어 있고, 23~24를 거치며 깎이고는 있지만 아직 "운영 첫 줄에 켜고 끝" 수준은 아니다.

기존에는 같은 일을 Docker나 systemd, seccomp, AppArmor, capability drop 같은 OS 레이어로 했다. 컨테이너 격리는 그대로 두고, 그 안에서 Node 프로세스 자체가 한 번 더 자기 한계를 그어두는 그림이다. npm install로 들어온 의존성이 `child_process.spawn('curl', ...)`을 시도할 때, 컨테이너는 막지 못해도 권한 모델은 막는다. 그게 이 기능의 1차 동기다.

여기서는 5년차쯤 된 개발자가 운영에 적용하면서 부딪힌 지점을 정리한다. 옵션 표 나열보다는 "켜면 뭐가 깨지는가, 컨테이너랑 뭐가 다른가, 거부됐을 때 어떻게 잡아내는가" 를 본다.

---

## 1. `--permission`이라는 스위치

플래그 하나로 모드를 켠다.

```bash
node --permission app.js
```

이 순간부터 프로세스는 거의 모든 외부 부수효과가 막힌다. 파일 읽기·쓰기, `net.connect`, `child_process.fork`, `new Worker(...)`, 네이티브 애드온 로딩까지 전부 차단이다. 그래서 보통은 `--allow-*` 플래그로 필요한 것만 다시 열어준다.

```bash
node \
  --permission \
  --allow-fs-read=/app \
  --allow-fs-read=/etc/ssl/certs \
  --allow-fs-write=/var/log/app \
  --allow-child-process \
  app.js
```

여기서 자주 놓치는 부분 두 개를 짚어둔다.

첫째, `--allow-fs-read=*` 와 `--allow-fs-read=/` 는 다르다. `*`는 와일드카드 자체, `/`는 루트 디렉터리부터 전부다. 운영에서 권한 모델을 켜는 의미를 살리려면 `*`나 `/`로 통째로 여는 건 의미가 없다. 디렉터리를 끊어서 명시한다.

둘째, 경로는 절대 경로다. 상대 경로는 받아주지 않는다. CI에서 working directory가 바뀌면 그대로 깨진다.

셋째, 이 플래그는 `NODE_OPTIONS` 환경 변수에도 들어간다. 다만 22까지는 `--permission` 자체를 `NODE_OPTIONS`로 못 넣는 제약이 있었다. 23부터 풀렸지만, 컨테이너 이미지에서 이를 가정하지 말고 ENTRYPOINT에 직접 박는 게 낫다.

---

## 2. 파일 시스템 권한 — read와 write의 비대칭

`--allow-fs-read`, `--allow-fs-write` 둘로 갈라진다. 둘은 독립적이다. write를 열면 read도 열리는 게 아니다. 로그 디렉터리를 쓰기로 열어두고 읽기는 안 열면, `fs.writeFile`은 되지만 같은 파일을 `fs.readFile`로 읽는 건 막힌다.

```bash
node \
  --permission \
  --allow-fs-read=/app \
  --allow-fs-write=/var/log/app \
  --allow-fs-read=/var/log/app \
  server.js
```

운영에서 자주 깨지는 지점이 `require` 와 dynamic import다. 모듈 해석은 `node_modules` 트리를 위로 거슬러 올라가며 stat을 친다. `/app/node_modules` 만 열어두면 충분할 것 같지만, npm workspace나 pnpm 같은 도구가 `../../..` 까지 올라가면서 심볼릭 링크를 따라가는 경우가 있다. 이때 부모 경로 stat 자체가 차단된다.

`os.tmpdir()` 도 함정이다. `tmp` 모듈, `multer`, `sharp` 같은 패키지가 `/tmp` 밑에 임시 파일을 만든다. 그래서 보통 `--allow-fs-read=/tmp --allow-fs-write=/tmp` 가 필요하다. 단, `/tmp`를 통째로 여는 건 보안적으로 거의 의미가 없다는 점도 같이 봐야 한다. 같은 컨테이너 안의 다른 프로세스가 쓴 파일을 그대로 읽을 수 있다.

심볼릭 링크는 따로 신경 써야 한다. `/app/data → /mnt/storage` 라면 `--allow-fs-read=/app/data` 만으로는 부족하다. 실제 타깃인 `/mnt/storage` 도 같이 열어야 한다. 권한 모델은 경로 정규화 후의 실제 경로를 기준으로 본다.

`process.cwd()` 가 권한 안에 들어있지 않으면 `require('node:fs').readdirSync('.')` 같은 호출이 즉시 막힌다. CI에서 `node --permission --allow-fs-read=/app dist/index.js` 를 실행했는데 cwd가 `/home/runner/work/...` 인 경우 같은 이유로 ERR_ACCESS_DENIED가 난다.

---

## 3. 네트워크와 자식 프로세스 — 24 시점의 한계

22까지 `--allow-net` 은 그라뉼한 IP·포트 제어가 없었다. 23에서 호스트 화이트리스트가 일부 들어왔지만, 24 시점에서도 IP CIDR이나 포트 범위 같은 세밀한 제어는 빠져 있다. 실무에서는 사실상 `--allow-net` 한 줄로 네트워크를 통째로 열거나, 안 열거나의 둘 중 하나다.

```bash
node --permission --allow-net app.js
```

이게 컨테이너 격리와 권한 모델을 같이 써야 하는 이유다. 네트워크 화이트리스트는 NetworkPolicy나 egress proxy에 맡기고, Node 레벨에서는 "네트워크를 쓰는가, 안 쓰는가" 만 잠그는 식으로 계층을 나눈다.

`--allow-child-process` 도 비슷하다. 켜면 `child_process` 모듈 전체가 풀린다. 어떤 실행 파일만 허용하는 식의 제어는 없다. 그래서 권한 모델은 "이 마이크로서비스는 자식 프로세스를 절대 안 띄운다" 같은 가정을 코드로 강제하는 용도로 쓰는 게 가장 잘 맞는다. 의존성이 몰래 `execSync('id')` 같은 걸 호출하면 곧바로 막힌다.

`--allow-worker` 는 워커 스레드용이다. `worker_threads.Worker` 생성을 차단·허용한다. 워커는 같은 프로세스 안의 V8 인스턴스라 권한 모델 입장에서는 부모와 동일한 권한이 자동으로 상속된다. 워커 안에서 별도 `--allow-fs-read` 를 거는 방법은 24 기준으로 아직 없다.

네이티브 애드온은 별도 정책이다. 기본적으로 `--permission` 켜면 `.node` 바이너리 로딩이 막힌다. `--allow-addons` 로 풀어야 한다. 단, 한 번 풀면 어떤 애드온이든 다 로드된다. 특정 모듈만 허용은 못 한다. `bcrypt`, `sharp`, `node-canvas` 같은 게 깔린 프로젝트면 이 플래그를 무조건 켜야 하고, 그 순간 권한 모델로 얻는 격리 효과가 상당히 줄어든다는 사실은 받아들여야 한다.

---

## 4. `process.permission.has` — 런타임 검사

권한 모델이 켜져 있으면 `process.permission` 객체가 노출된다. 코드에서 직접 권한을 물어볼 수 있다.

```javascript
if (process.permission.has('fs.read', '/etc/app/config.yaml')) {
  const cfg = fs.readFileSync('/etc/app/config.yaml', 'utf8');
}

if (!process.permission.has('child_process')) {
  console.warn('child_process not permitted, skipping ffmpeg encoder');
}
```

플래그가 안 켜진 환경에서는 `process.permission` 자체가 `undefined` 다. 그래서 라이브러리 코드는 보통 이런 형태가 된다.

```javascript
function canReadSecret(path) {
  const p = process.permission;
  if (!p) return true;
  return p.has('fs.read', path);
}
```

권한 모델 없이 돌릴 때는 "권한 있다" 로 가정하고 평소처럼 동작시키는 패턴이다. 라이브러리가 권한 모델을 인지하고 사전 검사로 분기를 태우면 ERR_ACCESS_DENIED 예외를 안 던지고 우회 경로로 빠질 수 있다.

`has`의 첫 번째 인자는 권한 토큰이다. `fs.read`, `fs.write`, `net`, `child_process`, `worker`, `addon` 같은 문자열이다. 두 번째 인자는 리소스 단위가 있는 경우(fs.read·fs.write)에만 의미가 있다. 네트워크는 24 시점에서 리소스 인자를 줘도 그냥 무시한다. 즉 `process.permission.has('net', 'redis.internal:6379')` 와 `process.permission.has('net')` 이 같은 결과를 돌려준다.

런타임 검사의 함정 하나. 권한은 부팅 시 결정되고 런타임 중에 절대 변하지 않는다. 권한을 추가로 부여하거나 회수하는 API는 없다. `process.permission` 은 read-only 뷰일 뿐이다. 부팅 후에 "특정 작업만 잠시 권한을 풀고 싶다" 같은 요구는 권한 모델로 해결이 안 된다. 그건 별도 자식 프로세스를 띄우거나 sudo 비슷한 헬퍼 프로세스로 가는 방식이 맞다.

---

## 5. ERR_ACCESS_DENIED 처리

권한 모델이 거부하면 `ERR_ACCESS_DENIED` 코드의 예외가 던져진다. 일반 `Error` 객체에 `code` 프로퍼티가 붙는다.

```javascript
try {
  fs.readFileSync('/etc/shadow');
} catch (err) {
  if (err.code === 'ERR_ACCESS_DENIED') {
    console.error('permission denied:', err.permission, err.resource);
  }
}
```

`err.permission` 은 어떤 권한 토큰이 부족했는지(`FileSystemRead` 같은 문자열), `err.resource` 는 어떤 리소스 경로가 막혔는지 들어있다. 둘은 24부터 안정적으로 채워진다. 22에서는 `err.resource` 가 비어있는 경우가 있어 디버깅이 고됐다.

운영에서 자주 보는 시나리오는 비동기 콜백 안에서 ERR_ACCESS_DENIED가 터지는 경우다. 예: `fs.promises.readFile(...).catch(...)`. 권한 모델은 동기·비동기 가리지 않고 같은 코드로 거부하므로, 비동기 경로의 reject도 동일하게 잡아야 한다.

EventEmitter 기반 API에서는 `error` 이벤트로 흘러간다.

```javascript
const stream = fs.createReadStream('/forbidden/file');
stream.on('error', (err) => {
  if (err.code === 'ERR_ACCESS_DENIED') {
    logger.warn({ resource: err.resource }, 'fs read blocked by permission model');
  }
});
```

여기서 `error` 이벤트를 빠뜨리면 unhandled error로 프로세스가 죽는다. 권한 모델을 처음 켜면 이렇게 평소에는 안 일어나던 에러 경로가 자주 활성화된다. 스트림 단의 error handler가 빠진 코드가 통째로 드러난다. 권한 모델 도입은 이런 에러 핸들링 부채를 정리하는 계기도 된다.

`uncaughtException` 핸들러를 권한 거부 전용으로 다는 패턴도 종종 쓴다. 의존성 내부에서 터진 ERR_ACCESS_DENIED를 한 곳에서 잡아 권한 정책의 누락을 빠르게 발견하기 위해서다.

```javascript
process.on('uncaughtException', (err) => {
  if (err.code === 'ERR_ACCESS_DENIED') {
    logger.fatal({
      permission: err.permission,
      resource: err.resource,
      stack: err.stack,
    }, 'permission model rejected an operation');
  }
  process.exit(1);
});
```

권한 거부는 거의 항상 정책 설계의 실수다. "정상적인 경로인데 막혔다" 가 대부분이지 "공격이 들어왔다" 가 아니다. 그래서 로그를 일단 풍부하게 남기고, 막힌 리소스를 보고 `--allow-fs-read` 에 추가하거나, 그 코드 경로 자체를 안 타게 막거나를 선택한다.

---

## 6. 컨테이너 격리와의 비교

권한 모델을 처음 보면 "Docker 안에서 굳이 이걸 또 켤 이유가 있나" 라는 의문이 든다. 다른 결로 봐야 한다.

| 격리 레이어 | 막는 것 | 우회 가능성 |
|---|---|---|
| 컨테이너 (namespace + cgroup) | 호스트 자원·다른 컨테이너 침투 | 컨테이너 내부 공격은 못 막음 |
| seccomp/AppArmor | 위험한 시스템 콜·파일 경로 | 정책 정의가 어렵고 OS에 묶임 |
| Node Permission Model | 같은 프로세스 안의 자바스크립트 코드가 fs·net·child_process를 만지는 일 | 부팅 플래그로 결정, 런타임 변경 불가 |

권한 모델의 위협 모델은 "악의적이거나 취약한 npm 의존성이 프로세스를 장악하려 할 때" 다. 컨테이너는 의존성 하나가 `fs.readFile('/etc/passwd')` 하는 걸 굳이 막지 않는다. 권한 모델은 막는다. 반대로 권한 모델은 호스트의 다른 프로세스나 네트워크 인터페이스를 손대는 걸 막지 못한다. 그건 컨테이너의 몫이다.

그래서 진지하게 권한 모델을 운영에 쓰는 팀은 둘을 같이 둔다. 컨테이너로 호스트와 분리하고, seccomp로 위험한 syscall을 끊고, 그 안에서 Node 권한 모델로 의존성 행동을 잠근다. 비용은 디버깅 난이도. 한 군데서 막혀도 어느 레이어인지 추적이 필요하다.

비교 포인트 하나 더. Deno는 처음부터 권한 모델을 코어 기능으로 둔다. `--allow-net`, `--allow-read` 같은 의미가 거의 똑같다. Node 권한 모델은 Deno의 영향을 받았다고 봐도 무방하다. 다만 Deno는 의존성을 url import로 명시적으로 들이는 반면 Node는 `node_modules` 트리가 거대해서, 같은 권한 모델이라도 운영 디버깅 부담은 Node가 훨씬 크다.

---

## 7. 실험적 단계의 실제 제약

24 시점에 권한 모델은 여전히 `--experimental-permission` 의 잔향이 남아 있다. 22에서 정식 플래그가 `--permission` 으로 자리잡았지만, 깨지는 영역이 꽤 있다.

`--require` 또는 `-r` 으로 들어오는 사전 로딩 스크립트는 권한 체크 이전에 실행된다. 즉 preload 스크립트는 권한 모델의 영향을 안 받는다. APM agent나 sourcemap 등록을 preload로 거는 패턴이 많은데, 그 코드들은 권한과 무관하게 돌아간다는 점을 알고 있어야 한다. 거꾸로 말하면, preload 안에 위험한 동작을 넣는 건 권한 모델로 못 막는다.

`Worker` 스레드 안에서 `--allow-*` 플래그를 별도로 잡고 싶다는 요구가 자주 나오는데 24 기준으로 미지원이다. 부모와 같은 권한을 그대로 받는다. 워커 격리를 권한 모델로 풀려는 계획이 있다면 시점을 다시 봐야 한다.

`vm.runInNewContext` 같은 V8 컨텍스트 격리도 권한 모델로는 별도 제어가 안 된다. vm 모듈이 제공하는 격리는 "보안 경계가 아니다" 라는 게 Node 코어 팀의 공식 입장이고, 권한 모델도 거기에 손을 대지 않는다. 외부에서 들어온 코드를 안전하게 실행하고 싶다면 vm 모듈이 아니라 별도 프로세스 + seccomp로 가는 게 맞다.

inspector 프로토콜은 권한 모델과 직교한다. `--inspect` 가 켜져 있으면 디버거가 붙어 임의 코드를 실행할 수 있고, 그건 권한 모델을 우회한다. 운영 컨테이너에서 `--inspect` 가 켜진 채 떠 있으면 권한 모델은 사실상 무의미하다.

`process.binding` 같은 내부 API는 점차 권한 모델에 잡히고 있지만, 22~23 사이에는 우회 가능한 경로가 있었다. 패치 릴리스 노트를 꾸준히 따라가야 한다.

---

## 8. 운영 적용 시 주의점

권한 모델을 실제 트래픽 받는 서비스에 켤 때 고려한 것들이다.

가장 먼저 부딪히는 건 의존성이 뭘 만지는지 모른다는 점이다. `npm install` 로 들어온 300개 패키지 중 어떤 게 `os.tmpdir()` 을 건드리는지, 어떤 게 `dns.lookup` 을 호출하는지 사전에 다 알 수 없다. 그래서 보통 로컬에서 권한 모델을 켜고 통합 테스트를 한 번 통째로 돌린다. 떨어지는 ERR_ACCESS_DENIED를 모아서 정책을 깎아간다. 한 번에 안 끝난다. 카나리 단계에서도 새로운 코드 경로가 처음 타면서 권한 거부가 나는 일이 흔하다.

두 번째는 dev/prod 정책 동기화다. 개발 환경에서 권한 모델을 끄고 운영에서만 켜면 어차피 거부 케이스를 운영에서 처음 본다. CI에 통합 테스트를 권한 모델로 돌리는 단계를 두고, 거부가 새로 생기면 빌드를 깨는 정책이 안전하다.

세 번째는 hot reload 도구와의 충돌이다. nodemon, tsx, ts-node-dev 같은 도구가 파일 시스템을 광범위하게 감시한다. 감시 대상 디렉터리가 권한 안에 안 들어있으면 watcher가 죽거나 무한 재시작에 빠진다. 개발 환경에서는 권한 모델을 끄거나, 감시 디렉터리를 정확히 열어두는 식으로 우회한다.

네 번째는 PaaS·서버리스에서의 제약이다. Vercel·Lambda·Cloud Run 같은 환경은 런타임 플래그를 직접 설정 못 하는 경우가 많다. `NODE_OPTIONS` 환경 변수를 받아주는 곳에서만 권한 모델이 의미가 있다. AWS Lambda는 24 시점에서 `NODE_OPTIONS` 로 `--permission` 을 허용하긴 하지만, 핸들러 부팅 전 초기화 코드가 권한 거부로 죽으면 cold start 실패만 잔뜩 쌓인다.

다섯 번째는 관측이다. 권한 거부가 늘면 그게 보안 사고인지 정책 누락인지 빨리 구분할 필요가 있다. ERR_ACCESS_DENIED를 별도 메트릭으로 분리하고, 거부 리소스를 라벨로 붙여 대시보드에 둔다. 평소에 0이다가 갑자기 튀면 둘 중 하나다. 새 코드 배포로 인한 정책 누락이거나, 누가 새로운 경로로 침투를 시도하거나.

마지막으로, 실험적 단계라는 점이 운영 의사결정에 영향을 준다. 메이저 릴리스마다 옵션 이름·동작이 바뀌었다. 22 LTS 기준으로 정책을 작성했다가 24로 올리면서 다시 손봐야 한 경험이 흔하다. 정책을 코드와 같이 버전 관리하고, Node 업그레이드 시 권한 모델 변경 로그를 별도로 보는 절차가 필요하다.

---

## 9. 작은 통합 예제

ESM 진입점에서 권한 상태를 부팅 시 한 번 검사하고 로그를 남기는 패턴이다.

```javascript
// boot.mjs
import process from 'node:process';
import { readFile } from 'node:fs/promises';

function snapshotPermissions() {
  const p = process.permission;
  if (!p) return { enabled: false };
  return {
    enabled: true,
    fsRead: p.has('fs.read'),
    fsWrite: p.has('fs.write'),
    net: p.has('net'),
    childProcess: p.has('child_process'),
    worker: p.has('worker'),
    addon: p.has('addon'),
  };
}

const perms = snapshotPermissions();
console.log(JSON.stringify({ kind: 'boot.permissions', perms }));

try {
  const cfg = await readFile('/app/config/app.yaml', 'utf8');
  // ...
} catch (err) {
  if (err.code === 'ERR_ACCESS_DENIED') {
    console.error(JSON.stringify({
      kind: 'boot.permission_denied',
      permission: err.permission,
      resource: err.resource,
    }));
    process.exit(78);
  }
  throw err;
}
```

부팅 단계에서 권한 거부가 나면 종료 코드를 일반 에러와 구분해 둔다. 위 예제는 `EX_CONFIG` 에 해당하는 78을 썼다. 컨테이너 오케스트레이터가 재시작 정책으로 무한 루프 도는 걸 막거나, 알람을 별도로 거는 데 쓴다.

이 정도면 권한 모델을 켜고 운영에서 부딪히는 1차 케이스는 대부분 다룬다. 24 이후로 정책 그라뉼이 더 들어올 가능성이 높으니 릴리스 노트를 정기적으로 본다. 특히 네트워크 호스트·포트 그라뉼, 워커별 권한 분리, 애드온 화이트리스트가 나오면 운영 활용도가 크게 올라간다.
