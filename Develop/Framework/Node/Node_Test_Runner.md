---
title: node:test 빌트인 테스트 러너 실무
tags:
  - nodejs
  - test-runner
  - node-test
  - jest
  - vitest
  - ci
updated: 2026-06-04
---

# node:test 빌트인 테스트 러너 실무

Node.js 18에서 `node:test`가 안정 단계로 들어왔다. 처음 공개된 건 16.17이지만 그때는 실험적 단계라 production에서 쓰기 부담스러웠다. 20부터는 `--experimental` 플래그 없이 커버리지가 동작하고, 22부터는 그 플래그 자체도 사라졌다. 이제는 의존성 추가 없이 테스트 러너를 쓸 수 있게 됐다.

Jest를 5년 넘게 써온 입장에서 처음에는 회의적이었다. 굳이 Node에 테스트 러너가 필요한가 싶었다. 그런데 최근 사이드 프로젝트와 CLI 도구 한두 개를 `node:test`로 옮기면서 인상이 바뀌었다. Cold start가 빠르고, ESM 호환성 문제로 시간을 잃는 일이 없고, `node_modules`가 가볍다. 대신 Jest가 제공하던 편의 기능 일부가 비어 있어서 마이그레이션을 결정하기 전에 깊게 살펴봐야 한다.

이 문서는 `node:test`를 실무에서 쓰면서 막혔던 지점과 우회 방법을 정리한 것이다. 공식 문서가 다루지 않는 운영 경험 위주로 적었다.

---

## 기본 구조 — describe/it/before/after

API는 Jest와 거의 동일하다. `node:test`에서 `describe`, `it`, `before`, `after`, `beforeEach`, `afterEach`를 가져와 쓴다.

```js
import { describe, it, before, after, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { UserService } from '../src/user-service.js';

describe('UserService', () => {
  let service;

  before(async () => {
    await prepareTestDatabase();
  });

  after(async () => {
    await cleanupTestDatabase();
  });

  beforeEach(() => {
    service = new UserService();
  });

  it('returns null when user is missing', async () => {
    const result = await service.findById('does-not-exist');
    assert.equal(result, null);
  });
});
```

`assert/strict`를 쓰는 게 중요하다. 그냥 `node:assert`만 import 하면 느슨한 비교가 기본이라 `0 == false`가 통과한다. 실무에서 가장 자주 보는 실수다.

`it` 대신 `test`를 써도 동일하다. 두 이름은 동일한 함수의 별칭이다. Jest 출신은 `describe + it`을, Tap 출신은 `test`만 쓰는 편이다. 같은 파일에 섞어 쓰면 가독성이 나빠지니 한 가지로 통일한다.

서브테스트 구조는 `describe`를 중첩하면 그대로 표현된다. 다만 `node:test`는 Jest와 달리 서브테스트 안에서 부모 컨텍스트를 자동으로 공유하지 않는다. 부모 `describe`의 `beforeEach`는 자식 `it`에서도 실행되지만, 부모에서 만든 변수는 클로저로 명시적으로 잡아야 한다.

### t 객체 — 컨텍스트 기반 API

콜백 인자로 받는 `t` 객체가 Jest에는 없는 개념이다. 테스트 컨텍스트라고 부르고, 서브테스트나 모킹, 후처리 등록을 여기서 한다.

```js
import { test } from 'node:test';

test('parent', async (t) => {
  await t.test('subtest 1', () => { /* ... */ });
  await t.test('subtest 2', () => { /* ... */ });

  t.after(() => {
    // 이 테스트 끝나면 실행
  });
});
```

`t.after`는 해당 테스트 범위 내에서만 동작한다. 파일 전체의 `after`와 다르다. 서브테스트마다 다른 정리 동작이 필요할 때 깔끔하다.

### skip, only, todo

세 가지 방식이 있다. 데코레이터처럼 옵션으로 넘기거나, `t.skip()`처럼 컨텍스트 메서드로 부르거나, `it.skip`처럼 메서드 체이닝으로 쓰는 형태다.

```js
it.skip('아직 미구현', () => { /* ... */ });
it.todo('내일 작성 예정');
it.only('이거만 돌리고 싶다', () => { /* ... */ });
```

`only`를 쓰려면 `--test-only` 플래그가 필요하다. Jest처럼 자동으로 `only`를 인식해서 다른 테스트를 건너뛰지 않는다. 이거 모르면 `only`를 붙여놓고 왜 모든 테스트가 다 도는지 한참 헤맨다.

---

## 실행 명령과 동시성

`node --test`로 돌린다. 인자 없이 부르면 현재 디렉터리에서 정해진 패턴(`*.test.js`, `*-test.js`, `test/**/*.js` 등)을 찾아 실행한다.

```bash
node --test
node --test tests/unit
node --test --test-name-pattern="UserService"
node --test --test-only
node --test --watch
```

기본적으로 각 테스트 파일을 별도 자식 프로세스에서 돈다. Jest와 비슷한 격리 모델이지만 구현은 더 가볍다. 한 파일이 글로벌 상태를 오염시켜도 다른 파일에 영향을 주지 않는다.

동시성은 `--test-concurrency`로 조절한다. 기본값은 CPU 코어 수에 맞춰 잡힌다.

```bash
node --test --test-concurrency=4
```

CI에서 메모리가 빠듯할 때 줄이고, 로컬에서는 기본값으로 둔다. 한 파일 안에서 `describe`나 `test`의 `concurrency` 옵션으로 서브테스트 단위 병렬도 켤 수 있는데, DB를 공유하는 통합 테스트에서는 같이 켜면 데드락이 난다. 단위 테스트에서만 켜는 게 안전하다.

`--test-name-pattern`은 정규식이다. 부분 일치라 `"User"`만 줘도 `UserService`, `UserController`가 모두 잡힌다. CI에서 특정 테스트만 재실행하고 싶을 때 자주 쓴다.

`--watch`는 파일 변경 감지를 켠다. Jest의 watch 모드처럼 인터랙티브 인터페이스를 제공하지는 않고, 단순히 다시 돌릴 뿐이다.

---

## 리포터 — spec, tap, junit

기본 리포터는 터미널이 TTY면 `spec`, 아니면 `tap`이다. CI 로그에 색상이 들어가 보기 힘들었던 경험이 있다면 명시적으로 지정한다.

```bash
node --test --test-reporter=spec
node --test --test-reporter=tap
node --test --test-reporter=junit --test-reporter-destination=junit.xml
```

`junit`은 22부터 빌트인이다. GitLab CI나 Jenkins에서 테스트 결과 표시용으로 쓴다. 그 전 버전에서는 별도 패키지(`node-test-reporter-junit` 등)를 설치하거나 직접 변환 스크립트를 짜야 했다.

여러 리포터를 동시에 쓸 수도 있다. 사람이 보는 출력은 콘솔에, JUnit XML은 파일에 떨어뜨리는 식이다.

```bash
node --test \
  --test-reporter=spec --test-reporter-destination=stdout \
  --test-reporter=junit --test-reporter-destination=junit.xml
```

`destination` 옵션은 리포터와 같은 개수로 짝을 맞춰야 한다. 하나만 쓰면 인자 매핑이 어긋나서 의도와 다른 결과가 나온다.

커스텀 리포터를 짤 수도 있다. 리포터는 비동기 이터러블을 받아 문자열을 yield하는 함수다. Slack에 결과 요약을 보내거나, 사내 대시보드에 결과를 쏘는 경우에 직접 만든다.

---

## 커버리지 — --experimental-test-coverage

22.10부터 `--experimental` 플래그 없이 `--test-coverage`가 들어왔지만, LTS 환경 호환을 위해 아직은 두 플래그를 다 알아두는 게 낫다.

```bash
node --test --experimental-test-coverage
node --test --test-coverage --test-coverage-include="src/**" --test-coverage-exclude="src/migrations/**"
```

c8이나 nyc 같은 외부 도구 없이 V8의 내장 커버리지를 직접 쓴다. 빠른 편이고 설정이 거의 필요 없다. 다만 출력 형식이 제한적이다. 기본은 텍스트 테이블이고, 22에서 `lcov` 출력이 들어와 Codecov 같은 외부 서비스와 연동할 수 있게 됐다.

```bash
node --test --test-coverage --test-coverage-reporter=lcov --test-coverage-reporter=text
```

lcov 파일은 기본적으로 `coverage/lcov.info`에 떨어진다. 위치를 바꾸려면 `--test-coverage-reporter-destination`을 쓴다.

실무에서 한 가지 까다로운 점은 **TypeScript 소스 매핑**이다. tsx나 ts-node로 트랜스파일된 코드의 커버리지는 변환된 JavaScript 기준으로 측정된다. 소스맵 지원이 들어가긴 했지만 완벽하지 않다. 경계 조건이나 데코레이터가 많이 들어간 NestJS 코드는 보고된 커버리지가 의심스럽게 낮게 나오는 경우가 있다. 이런 환경에서는 아직 Vitest의 v8 커버리지가 더 정확하다.

또 한 가지, **임포트되지 않은 파일은 0%로 잡히지 않고 아예 보고서에서 빠진다**. 모든 파일이 어딘가에서 import되도록 인덱스를 만들거나 `--test-coverage-include` 패턴을 명시해야 한다.

---

## mock — fn, method, timers, module

`node:test`의 mock은 t 컨텍스트에서 접근한다. 가장 흔히 쓰는 셋은 함수 mock, 메서드 교체, 타이머 제어다.

### t.mock.fn

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';

test('mock.fn 기본', (t) => {
  const callback = t.mock.fn();
  callback('hello');
  callback('world');

  assert.equal(callback.mock.callCount(), 2);
  assert.deepEqual(callback.mock.calls[0].arguments, ['hello']);
});
```

`callback.mock.calls`로 호출 이력을 본다. `arguments`, `result`, `error`, `target` 등이 들어 있다. Jest의 `mock.calls`와 구조가 약간 다르다. Jest는 calls가 `[[arg1, arg2], [arg1, arg2]]` 형태인데, `node:test`는 각 호출이 객체로 감싸진다.

### t.mock.method

객체의 메서드를 임시로 교체한다. 테스트가 끝나면 자동으로 원복된다.

```js
test('외부 시간 함수 교체', (t) => {
  t.mock.method(Date, 'now', () => 1_700_000_000_000);
  assert.equal(Date.now(), 1_700_000_000_000);
});
```

후처리 없이도 다음 테스트에서 `Date.now()`가 원래 동작으로 돌아온다. 이게 t 컨텍스트의 큰 장점이다. 전역 mock을 깜박하고 안 되돌려서 다음 테스트가 깨지는 일이 거의 없다.

### t.mock.timers

`setTimeout`, `setInterval`, `setImmediate`, `Date`를 가짜로 만든다. Jest의 fake timers와 거의 같은 역할이다.

```js
test('지연 동작 검증', (t) => {
  t.mock.timers.enable({ apis: ['setTimeout', 'Date'] });

  let called = false;
  setTimeout(() => { called = true; }, 5000);

  t.mock.timers.tick(4999);
  assert.equal(called, false);

  t.mock.timers.tick(1);
  assert.equal(called, true);
});
```

`enable`의 `apis` 옵션을 빼먹으면 모든 타이머와 Date가 다 가짜가 된다. 의존하는 라이브러리가 내부적으로 `setImmediate`를 쓰는 경우(예: pg 클라이언트의 일부 경로) 이런 변경이 예기치 않은 행동을 만든다. 필요한 것만 골라 켜는 게 안전하다.

22.3부터 `setInterval`도 정상 동작한다. 그 이전 버전에서는 두 번째 tick부터 발화 시점이 어긋나는 버그가 있었다.

### 모듈 mock — t.mock.module

이게 `node:test`로 옮기면서 가장 고생하는 부분이다. 22.3부터 `t.mock.module()`이 들어왔는데, ESM 모듈 자체를 교체할 수 있다.

```js
test('외부 모듈 교체', async (t) => {
  t.mock.module('node:fs', {
    namedExports: {
      readFileSync: () => 'mocked content',
    },
  });

  const { readFileSync } = await import('node:fs');
  assert.equal(readFileSync('any-path'), 'mocked content');
});
```

`--experimental-test-module-mocks` 플래그를 켜야 동작한다. Jest의 `jest.mock()`처럼 자동 호이스팅되지 않으므로 mock 등록 후에 동적 import로 가져와야 한다. 이게 결과적으로 코드 모양을 강제로 바꾸기 때문에 마이그레이션할 때 가장 큰 진통이다. Jest의 `jest.mock()`이 자동으로 모든 import를 갈아끼우던 것에 비하면 명시적이지만 손이 많이 간다.

CJS 모듈 mock은 더 제한적이다. require 캐시를 직접 건드리지 않는 한 깔끔한 방법이 없어서, 모듈 mock이 많은 코드는 아직 Jest나 Vitest가 낫다.

---

## snapshot — 22.3부터 안정화

`assert.snapshot()`이 22.3부터 들어왔다. 그 이전에는 sinon-chai snapshot이나 jest-snapshot을 끌어다 썼지만, 이제 빌트인으로 해결된다.

```js
import { test, snapshot } from 'node:test';
import assert from 'node:assert/strict';

test('응답 형식 스냅샷', (t) => {
  const response = renderUser({ id: 1, name: '김철수' });
  t.assert.snapshot(response);
});
```

스냅샷 파일은 테스트 파일과 같은 디렉터리에 `.snapshot` 확장자로 저장된다. 첫 실행 때 자동 생성되고, 이후 실행에서는 비교한다. 업데이트하려면 `--test-update-snapshots` 플래그를 쓴다.

스냅샷 직렬화기를 커스터마이즈하려면 `snapshot.setDefaultSnapshotSerializers()`를 호출한다. 날짜 객체를 ISO 문자열로 통일하거나, UUID를 마스킹하는 용도로 쓴다. 이걸 안 해두면 매 실행마다 변경되는 값 때문에 스냅샷이 깨진다.

---

## ESM과 TypeScript 통합

대부분의 신규 프로젝트는 ESM이라 별도 설정 없이 잘 돈다. CJS 프로젝트라면 `require('node:test')`로 가져와도 동작한다.

TypeScript는 두 가지 경로가 있다.

### tsx로 실행

가장 흔한 방식이다. `tsx`는 esbuild 기반으로 빠르고 설정이 거의 없다.

```bash
node --import tsx --test "tests/**/*.test.ts"
```

`--import`는 20부터 들어온 플래그다. 모듈 로더 훅을 등록한다. 그전에는 `--loader tsx`를 썼는데 deprecated 됐다.

문제는 **glob 확장**이다. node 22.6 이전에는 `node --test` 자체가 glob을 인식하지 못해서 셸이 확장하거나, 명시적으로 디렉터리를 줘야 했다. zsh에서는 매치되는 파일이 없으면 에러가 나는 기본 동작 때문에 CI에서 헛다리를 짚는 경우가 잦다. 22.6부터는 Node 내장 glob을 쓰니 따옴표로 감싸면 그대로 작동한다.

### Node 22.6의 빌트인 TS 지원

22.6부터 `--experimental-strip-types` 플래그로 타입 제거만 하는 모드가 들어왔고, 23부터는 기본 동작이 됐다. 타입 검증은 안 하고 그냥 타입 어노테이션만 떼고 실행한다.

```bash
node --test "tests/**/*.test.ts"
```

별도 도구 없이 돌아간다는 점은 매력적인데, 한계가 명확하다.

- 데코레이터 미지원 (NestJS는 안 된다)
- enum 미지원
- `tsconfig.json`의 path alias 미지원
- 타입 검사를 안 하므로 컴파일 에러는 잡지 못한다

라이브러리 수준의 작은 프로젝트면 충분하지만, 실무 백엔드에서는 아직 tsx나 ts-node를 거치는 경우가 많다.

### path alias 문제

`tsconfig.json`의 `paths` 설정은 런타임에서는 무시된다. `@/services/user` 같은 경로를 쓰던 코드는 그대로 옮기면 `Cannot find module` 에러가 난다. 해결책 세 가지가 있다.

첫째, `tsconfig-paths/register`를 `--import`로 등록한다. ESM 환경에서는 `tsconfig-paths`가 깔끔하게 동작하지 않는 경우가 많아 추천하지 않는다.

둘째, `node --import`에 직접 변환 훅을 만들어 박는다. esbuild의 path 해석기를 가져와 쓰는 방식이다. 가장 안정적이지만 손이 간다.

셋째, alias를 포기하고 상대 경로로 마이그레이션한다. 의외로 이게 정답일 때가 많다. ESLint 규칙으로 깊이 3 이상의 상대 경로만 금지하고, 나머지는 상대 경로로 유지하는 식이다.

마이그레이션할 때 alias가 200군데 이상 박혀 있다면 자동 변환 스크립트를 짜는 게 낫다. ts-morph로 import 구문만 골라 변환한다.

---

## 전역 setup의 부재

Jest의 `globalSetup`, `globalTeardown`, `setupFilesAfterEach`에 해당하는 표준 메커니즘이 `node:test`에는 없다. 이게 마이그레이션할 때 두 번째로 큰 진통이다.

우회 방법은 `--import`로 setup 파일을 미리 로드하는 것이다.

```bash
node --import ./test-setup.js --test
```

`test-setup.js`에서 환경 변수를 박고, 글로벌 DB 커넥션을 만들고, fixtures를 깐다. 그런데 이건 **테스트 파일마다 실행된다**. 자식 프로세스로 격리되니까 한 번만 실행되는 방법이 없다.

DB 준비처럼 비용이 큰 작업은 별도 스크립트로 빼서 `npm test` 안에서 순차 실행한다.

```json
{
  "scripts": {
    "test": "node ./scripts/setup-db.js && node --test && node ./scripts/teardown-db.js"
  }
}
```

CI에서는 셸 트랩으로 teardown을 보장한다.

```bash
node ./scripts/setup-db.js
trap 'node ./scripts/teardown-db.js' EXIT
node --test
```

`set -e` 환경에서 테스트가 실패해도 teardown은 돌도록 trap을 쓰는 게 안전하다.

---

## Jest, Vitest 대비 장단점

5년 가까이 Jest를 쓰다가 일부 프로젝트를 `node:test`나 Vitest로 옮기면서 정리한 현재 시점의 비교다.

### node:test가 유리한 경우

- CLI 도구나 라이브러리. 사용자가 깔 의존성을 줄이고 싶을 때.
- Node 버전 호환이 중요한 프로젝트. 빌트인이라 Node 업그레이드와 함께 자연스럽게 따라간다.
- ESM 네이티브 프로젝트. Jest의 ESM 지원은 여전히 실험적이고 가끔 깨진다.
- cold start가 중요한 환경. CI에서 매번 새 컨테이너로 도는 경우 1~2초 차이가 누적되면 무시 못 한다.
- 단순한 단위 테스트 위주. mock이 적고 fixture가 가볍다면 부족함을 못 느낀다.

### Jest나 Vitest가 유리한 경우

- mock이 많은 코드. 특히 모듈 단위 자동 mock이 필요한 코드.
- 스냅샷이 중심인 테스트. Jest의 직렬화기 생태계가 훨씬 풍부하다.
- React, Vue 같은 프런트엔드 테스트. JSDOM 통합이 거의 표준이다.
- 큰 모노레포에서 `--changed` 같은 변경 기반 실행이 필요한 경우.
- 팀에 Jest 경험자가 많고 마이그레이션 비용이 큰 경우.

Vitest는 Jest와 호환 API를 유지하면서 ESM과 esbuild 기반 트랜스파일을 처음부터 고려한 도구다. 새 프로젝트에서 Jest 대신 Vitest를 골랐다면 `node:test`로 옮길 동기가 약하다. 둘은 비슷한 진영에 속한다.

성능은 케이스마다 다르다. 적은 수의 테스트(100개 미만)에서는 `node:test`가 빠르다. 수천 개 이상의 테스트에서는 Vitest가 worker thread 기반 병렬화로 더 빠른 경우가 많다. Jest는 셋 중 가장 느리지만 안정성과 생태계는 여전히 가장 깊다.

---

## CI 통합 예제

GitHub Actions에서 `node:test`를 쓰는 워크플로다.

```yaml
name: test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
          cache: 'npm'
      - run: npm ci
      - name: Run tests
        run: |
          node --test \
            --test-reporter=spec --test-reporter-destination=stdout \
            --test-reporter=junit --test-reporter-destination=junit.xml \
            --test-coverage --test-coverage-reporter=lcov \
            "tests/**/*.test.js"
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
      - name: Publish test results
        if: always()
        uses: mikepenz/action-junit-report@v4
        with:
          report_paths: 'junit.xml'
```

`if: always()`로 테스트가 실패해도 결과 리포트를 올리도록 한다. 실패 원인 분석에서 가장 자주 보는 게 결과 업로드 단계 자체가 스킵되는 상황이다.

GitLab CI에서는 JUnit XML을 `artifacts.reports.junit`로 넘기면 머지 리퀘스트 화면에 실패 테스트가 표시된다.

```yaml
test:
  image: node:22-alpine
  script:
    - npm ci
    - node --test --test-reporter=junit --test-reporter-destination=junit.xml
  artifacts:
    when: always
    reports:
      junit: junit.xml
    paths:
      - coverage/
```

Docker 이미지에서 돌릴 때 Alpine 이미지 안의 OpenSSL 버전 차이로 `crypto.randomUUID()` 호출이 느려지거나 멈추는 경우가 있다. Node 20.10 이전 버전에서 자주 보던 문제다. 22 LTS에서는 거의 사라졌지만, 옛 이미지를 계속 쓰는 프로젝트는 의심해볼 만한 지점이다.

테스트 시간이 길어지면 `--test-shard` 옵션을 본다. 22부터 들어온 기능으로, `--test-shard=1/4` 형태로 테스트를 N등분해 일부만 돈다. CI 매트릭스로 병렬화할 때 쓴다.

```yaml
jobs:
  test:
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - run: node --test --test-shard=${{ matrix.shard }}/4
```

각 shard가 독립적으로 돌고, 마지막에 결과를 합친다. 1000개 넘는 테스트가 있는 모노레포에서 빌드 시간을 절반으로 줄여본 경험이 있다.

---

## 마이그레이션 시 자주 막히는 지점

지난 6개월 동안 두 개 프로젝트를 Jest에서 `node:test`로 옮기면서 정리한 함정들이다.

**자동 mock 부재**. `jest.mock('./module')` 한 줄로 끝나던 게 `t.mock.module()`을 명시적으로 등록한 뒤 동적 import로 다시 가져오는 패턴으로 바뀐다. 한 파일당 수십 줄이 늘어난다. mock이 많은 파일은 마이그레이션을 보류하거나 의존성 주입 구조로 리팩터링하는 게 낫다.

**`expect`의 부재**. `assert/strict`는 직설적이지만 매처가 빈약하다. `toContainEqual`, `toMatchObject`, `toHaveBeenCalledWith` 같은 매처가 그립다면 `node:assert`만으로는 코드가 장황해진다. 별도 매처 라이브러리(`chai`, `expect`)를 가져다 쓰는 사람도 있다.

**환경 변수 격리 없음**. Jest는 파일별로 환경 변수가 격리되는 옵션이 있지만 `node:test`는 그런 게 없다. `process.env`를 직접 건드리면 같은 파일 내 다른 테스트가 영향을 받는다. `t.mock.method(process, 'env', ...)` 같은 방식으로 우회한다.

**행이 멈췄을 때 디버깅이 어렵다**. Jest는 hang된 핸들을 추적해주는 `--detectOpenHandles`가 있는데, `node:test`는 비슷한 기능이 없다. 테스트가 종료되지 않으면 `--test-force-exit`로 강제 종료할 수는 있지만 근본 원인을 찾으려면 직접 `process._getActiveHandles()`를 로그로 찍어 봐야 한다.

**커버리지 누락**. 앞서 적었듯 import되지 않은 파일은 리포트에 안 잡힌다. CI에서 커버리지 게이트를 운영한다면 `--test-coverage-include` 패턴을 명시적으로 박아둔다.

**서드파티 도구의 부재**. ESLint 룰, IDE 통합, allure 같은 리포트 도구가 Jest 중심으로 만들어져 있다. `node:test`용 인텔리제이 플러그인이 존재하긴 하지만 Jest 플러그인만큼 성숙하지 않다. IDE에서 테스트 하나를 클릭으로 돌리는 워크플로가 중요한 팀이면 체감 비용이 크다.

마이그레이션은 신규 테스트 파일부터 점진적으로 적용하는 방식을 추천한다. Jest와 `node:test`를 한 프로젝트 안에서 공존시킬 수 있다. `npm test`가 두 러너를 순차 실행하면 된다. 모든 파일을 한 번에 옮기려고 들면 mock 패턴이나 alias 처리에서 시간을 잃기 쉽다.
