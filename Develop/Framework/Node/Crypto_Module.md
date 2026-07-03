---
title: Node.js crypto 모듈 심화
tags:
  - nodejs
  - crypto
  - security
  - aes-gcm
  - argon2
  - webcrypto
updated: 2026-06-03
---

# Node.js crypto 모듈 심화

`crypto` 모듈은 무심코 쓰다가 가장 큰 사고를 내는 코어 모듈이다. 해시 결과가 같으니 잘 동작한다고 믿었다가 인코딩이 달라 검증이 깨지고, AES-GCM을 직접 구현했더니 nonce를 재사용해서 평문이 복원되고, `===`로 토큰 비교하다 타이밍 공격에 노출된다. 이 문서는 운영하면서 실제로 부딪혔거나, 코드 리뷰에서 자주 잡아낸 사고들을 정리한다.

OpenSSL 위에 얹힌 얇은 래퍼라는 사실을 머리 한쪽에 두고 읽으면 좋다. Node가 알아서 안전한 기본값을 잡아주지 않는 경우가 많다.

---

## 1. createHash와 인코딩 함정

가장 자주 보는 코드는 이렇다.

```javascript
const crypto = require('node:crypto');

function hash(input) {
  return crypto.createHash('sha256').update(input).digest('hex');
}
```

`createHash`는 알고리즘 이름만 받는다. OpenSSL이 인식하는 이름이면 다 통과한다. `sha256`, `sha512`, `sha3-256`, `blake2b512` 같은 게 다 들어간다. 문제는 알고리즘이 아니라 `update`와 `digest`에 있다.

### update의 인코딩 인자

`update`는 두 번째 인자로 인코딩을 받는다. 안 주면 문자열은 UTF-8로 처리한다. 그래서 `update('한글')`과 `update('한글', 'utf8')`은 같다. 그런데 가끔 이런 코드를 본다.

```javascript
crypto.createHash('sha256').update('deadbeef', 'hex').digest('hex');
```

문자열을 hex로 해석한 8바이트를 해싱한다. 누가 봐도 hex 문자열이면 의도가 명확하지만, 의도가 아니라면 결과가 완전히 달라진다. 다른 시스템(파이썬, 자바)과 해시 결과를 맞춰야 할 때 인코딩 불일치로 한참 헤맨다. 가능하면 Buffer로 명시적으로 만들어서 넘기는 편이 안전하다.

```javascript
const buf = Buffer.from('deadbeef', 'hex');
crypto.createHash('sha256').update(buf).digest('hex');
```

### digest의 인코딩

`digest()`에 인코딩을 안 주면 Buffer가 나오고, `'hex'`나 `'base64'`를 주면 문자열이 나온다. 여기서 흔한 사고는 `base64`와 `base64url`을 헷갈리는 것이다. JWT나 URL 파라미터로 해시를 실어 보낼 때 일반 base64를 쓰면 `+`, `/`, `=` 때문에 URL 안전 인코딩이 깨진다.

```javascript
const digest = crypto.createHash('sha256').update('payload').digest();

const b64 = digest.toString('base64');       // BCRD8h...g=
const b64url = digest.toString('base64url'); // BCRD8h...g  (= 없고 +/_ 변환)
```

Node 16부터 `base64url` 인코딩이 정식 지원이라 별도 변환 함수를 만들 필요가 없다. 이전 코드베이스를 보면 직접 `replace`로 치환하는 함수가 여기저기 보이는데, 지금은 그냥 `'base64url'`로 통일하면 된다.

### update를 여러 번 호출해도 결과는 같다

스트림 형태로 큰 파일을 해시할 때 `update`를 반복 호출한다.

```javascript
const hash = crypto.createHash('sha256');
fs.createReadStream('big.bin')
  .on('data', chunk => hash.update(chunk))
  .on('end', () => console.log(hash.digest('hex')));
```

`update` 호출 횟수와 청크 경계는 결과에 영향을 주지 않는다. 같은 바이트열을 어떻게 쪼개 넣든 같은 해시가 나온다. 그래도 `digest()`를 한 번 호출하면 그 Hash 객체는 더는 못 쓴다. 다시 해싱하려면 새로 `createHash`를 부른다. 이걸 모르고 같은 객체 재사용하려다 `Digest already called` 에러를 본 적이 있다.

### 비밀번호 검증에 일반 해시 쓰지 마라

`sha256(password + salt)`는 비밀번호 저장에 부적합하다. GPU 한 장이면 초당 수십억 번 시도한다. salt를 줘도 한 명씩 따로 공격하면 그만이다. 비밀번호는 다음 절의 `scrypt`나 `argon2`로 가야 한다. `crypto.createHash`로 만든 해시는 무결성 체크, ETag, 캐시 키, 파일 fingerprint 같은 곳에만 쓴다.

---

## 2. 비밀번호 해싱: scrypt vs argon2id vs bcrypt

비밀번호 해싱 알고리즘 선택은 매번 논쟁거리다. 결론부터 말하면 신규 프로젝트는 **argon2id**, 외부 의존성 없이 빠르게 가야 하면 **scrypt**, 레거시는 **bcrypt**를 그대로 둔다.

### scrypt — 코어 모듈 내장

Node 코어에 들어있다. 별도 패키지가 필요 없다.

```javascript
const crypto = require('node:crypto');
const { promisify } = require('node:util');

const scrypt = promisify(crypto.scrypt);

async function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const N = 2 ** 15;  // CPU/메모리 비용
  const r = 8;
  const p = 1;
  const keylen = 64;

  const derived = await scrypt(password, salt, keylen, { N, r, p, maxmem: 128 * N * r * 2 });
  return `scrypt$${N}$${r}$${p}$${salt.toString('base64')}$${derived.toString('base64')}`;
}

async function verifyPassword(password, stored) {
  const [, N, r, p, saltB64, hashB64] = stored.split('$');
  const salt = Buffer.from(saltB64, 'base64');
  const expected = Buffer.from(hashB64, 'base64');
  const derived = await scrypt(password, salt, expected.length, {
    N: Number(N), r: Number(r), p: Number(p),
    maxmem: 128 * Number(N) * Number(r) * 2
  });
  return crypto.timingSafeEqual(derived, expected);
}
```

scrypt 파라미터에서 가장 헷갈리는 게 `maxmem`이다. 기본값(32MB)이 N을 키우면 금방 초과돼서 `Invalid scrypt parameter` 에러가 난다. `128 * N * r` 바이트가 최소 메모리고, 여유분 2배 정도를 잡아주면 된다. N=2^15, r=8이면 약 32MB라 기본값을 넘는다.

OWASP 권장은 N=2^17, r=8, p=1인데 서버 사양에 따라 응답 시간을 보고 조정한다. 로그인 한 번에 200~400ms 정도면 적당하다. 그보다 빠르면 공격자에게도 쉽다.

### argon2id — 외부 패키지

`argon2` 패키지를 따로 깔아야 한다. 네이티브 모듈이라 빌드 도구가 필요하다. Alpine 컨테이너에서 `python3 make g++` 안 깔려있어서 빌드 실패 보는 게 흔한 사고다.

```javascript
const argon2 = require('argon2');

async function hash(password) {
  return argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: 2 ** 16,   // 64MB
    timeCost: 3,
    parallelism: 1
  });
}

async function verify(stored, password) {
  return argon2.verify(stored, password);
}
```

argon2id가 scrypt보다 나은 이유는 GPU/ASIC 저항성이 더 강하고, 사이드 채널 공격 대응이 명시적이라는 점이다. 2015년 패스워드 해싱 경연(PHC) 우승작이라 학술적 검증도 끝났다. 신규로 만든다면 argon2id가 기본 선택이다.

### bcrypt — 레거시 호환용

10년 전부터 표준이었다. 지금도 잘 동작하지만 두 가지 한계가 있다. 첫째, 비밀번호 길이가 72바이트를 넘으면 잘린다(`password` 뒤에 무엇이 와도 같은 해시가 나옴). 둘째, 메모리 비용을 조절할 수 없다. cost 파라미터로 CPU만 늘린다. GPU 공격에 상대적으로 약하다.

```javascript
const bcrypt = require('bcrypt');

await bcrypt.hash(password, 12);  // cost factor 12
await bcrypt.compare(password, hash);
```

기존 시스템이 bcrypt면 그대로 둔다. 마이그레이션은 사용자가 다음 로그인할 때 argon2id로 다시 해싱하는 방식이 일반적이다.

### 알고리즘 식별자를 같이 저장한다

위 scrypt 예제에서 `scrypt$N$r$p$...` 형태로 저장한 이유가 이거다. 파라미터를 바꾸거나 알고리즘을 마이그레이션할 때 기존 해시를 그대로 검증할 수 있다. argon2 패키지는 `$argon2id$v=19$m=...,t=...,p=...$salt$hash` 형태로 알아서 만들어준다. 직접 만들 때도 같은 포맷을 따라가는 게 안전하다.

---

## 3. AES-GCM: createCipheriv와 nonce 재사용 사고

AES-CBC + HMAC을 직접 조합하는 코드는 이제 거의 없다. AES-GCM이 인증된 암호화(AEAD)를 한 번에 처리해주기 때문이다. 그런데 GCM은 nonce(IV) 관리가 잘못되면 평문 복원, 인증 우회까지 가능한 무서운 모드다.

### 기본 구조

```javascript
const crypto = require('node:crypto');

function encrypt(plaintext, key) {
  const iv = crypto.randomBytes(12);  // GCM 권장 IV는 96비트(12바이트)
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([iv, tag, ciphertext]);
}

function decrypt(blob, key) {
  const iv = blob.subarray(0, 12);
  const tag = blob.subarray(12, 28);
  const ciphertext = blob.subarray(28);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8');
}
```

여기서 중요한 포인트가 몇 개 있다.

### nonce 재사용은 끝장이다

같은 키로 같은 nonce를 두 번 쓰면 GCM의 보안성이 무너진다. 두 평문의 XOR이 그대로 노출되고, 인증 키가 복원되어 위조 메시지를 만들 수 있다. 이론적 위협이 아니라 실제 사고가 자주 난다.

대표적인 패턴이 카운터 기반 nonce를 메모리에만 두는 경우다. 프로세스 재시작 후 카운터가 0으로 돌아가면 이전에 쓴 nonce를 다시 쓴다. Lambda나 컨테이너 환경에서 인스턴스가 죽었다 살았다 하면 자주 발생한다.

가장 안전한 건 매번 `randomBytes(12)`로 뽑는 것이다. 96비트는 2^48번 정도까지는 충돌 확률이 무시할 수준이라 일반적인 트래픽에서는 충분하다. 단일 키로 2^32번 이상 암호화한다면 키를 더 자주 회전해야 한다.

### 인증 태그를 빼먹지 마라

`cipher.final()`만 호출하고 `getAuthTag()`를 안 부르면 GCM의 의미가 없다. 복호화 측에서도 `setAuthTag`를 안 하면 `decipher.final()`에서 `Unsupported state or unable to authenticate data` 에러가 난다. 태그는 16바이트 고정이다. 함께 저장하고 함께 전송한다.

### Additional Authenticated Data(AAD)

GCM은 암호화는 안 하지만 인증은 하고 싶은 데이터를 같이 넣을 수 있다. 예를 들어 메시지의 사용자 ID나 타임스탬프 같은 메타데이터다.

```javascript
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
cipher.setAAD(Buffer.from(userId));
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
const tag = cipher.getAuthTag();

// 복호화 측
const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
decipher.setAAD(Buffer.from(userId));   // 같은 AAD를 줘야 통과
decipher.setAuthTag(tag);
```

AAD가 다르면 `decipher.final()`에서 실패한다. 메시지 평문은 그대로지만 어떤 컨텍스트에 묶여있는지를 검증할 수 있다.

### 키는 32바이트 Buffer로 직접

`aes-256-gcm`은 32바이트 키를 요구한다. 문자열 비밀번호를 그대로 키로 쓰지 마라. 길이가 안 맞을뿐더러 엔트로피가 낮다. KEK는 `randomBytes(32)`로 만들어 KMS나 시크릿 매니저에 저장하고, 데이터 키가 필요하면 envelope encryption 패턴으로 간다.

비밀번호에서 키를 유도해야 한다면 `crypto.scryptSync(password, salt, 32)`를 쓴다. 그냥 SHA-256 한 번 돌린 결과를 키로 쓰는 코드를 종종 보는데, 비밀번호의 엔트로피가 낮으면 그대로 무차별 대입에 노출된다.

---

## 4. timingSafeEqual로 타이밍 공격 막기

토큰, HMAC, 해시를 비교할 때 `===`나 `Buffer.equals`를 쓰지 마라.

```javascript
// 잘못된 코드
if (req.headers['x-api-key'] === process.env.API_KEY) { ... }
```

문자열 비교는 첫 바이트부터 비교해서 다른 바이트가 나오면 즉시 false를 반환한다. 즉, 일치하는 prefix가 길수록 비교 시간이 길어진다. 공격자가 API 키를 한 글자씩 바꿔가며 평균 응답 시간을 측정하면 키를 한 글자씩 복원할 수 있다. 네트워크 노이즈 때문에 어렵다고 생각하지만, 충분히 많이 측정하면 통계적으로 추출이 가능하다.

`crypto.timingSafeEqual`은 길이가 같은 두 Buffer를 항상 같은 시간에 비교한다.

```javascript
const crypto = require('node:crypto');

function safeCompare(a, b) {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}
```

길이가 다르면 즉시 `RangeError`를 던지기 때문에 길이 체크를 먼저 한다. 길이 자체가 비밀이라면 한쪽을 고정 길이로 패딩하거나, 미리 두 값을 같은 길이의 해시로 만든 다음 비교한다.

```javascript
function safeCompareConstantLen(a, b) {
  const hA = crypto.createHash('sha256').update(a).digest();
  const hB = crypto.createHash('sha256').update(b).digest();
  return crypto.timingSafeEqual(hA, hB);
}
```

해시를 한 번 더 거치면 입력 길이와 무관하게 32바이트 비교가 된다. 단, 해시 계산 시간 자체도 입력 길이에 비례하므로 완벽하진 않다. 입력 길이가 외부에서 통제 가능한 경우에는 입력 길이 정규화도 같이 한다.

웹훅 시그니처(GitHub, Stripe) 검증에서 자주 쓴다. Stripe의 SDK는 내부적으로 timingSafeEqual을 쓰는데, 직접 구현하면 이걸 빼먹는 경우가 많다.

---

## 5. KeyObject API와 PEM/DER 변환

비대칭 키를 다룰 때 PEM 문자열이나 DER 바이너리를 직접 만지면 매번 형식이 다르고 헷갈린다. Node 11부터 `KeyObject`가 도입되면서 키를 일급 객체로 다룰 수 있게 됐다.

### 키 생성

```javascript
const { generateKeyPairSync } = require('node:crypto');

const { publicKey, privateKey } = generateKeyPairSync('rsa', {
  modulusLength: 2048,
});
// publicKey, privateKey는 KeyObject 인스턴스
```

`KeyObject`는 `type`(public/private/secret), `asymmetricKeyType`(rsa, ec, ed25519 ...) 같은 메타 정보를 가진다. 내부 표현은 OpenSSL에 있고 우리는 직접 못 본다. 외부로 내보내려면 `export`를 호출한다.

### PEM / DER 변환

```javascript
const pemPublic = publicKey.export({ type: 'spki', format: 'pem' });
const derPublic = publicKey.export({ type: 'spki', format: 'der' });

const pemPrivate = privateKey.export({
  type: 'pkcs8',
  format: 'pem',
  cipher: 'aes-256-cbc',
  passphrase: 'top-secret'
});
```

여기서 `type`이 중요하다. 공개 키는 `spki`(또는 RSA 전용 `pkcs1`), 개인 키는 `pkcs8`(또는 RSA 전용 `pkcs1`)을 쓴다. 다른 언어/라이브러리와 호환이 안 되면 거의 type 불일치가 원인이다. OpenSSL CLI로 만든 PEM이 어느 형식인지 헷갈릴 땐 헤더를 본다.

- `-----BEGIN PUBLIC KEY-----` → SPKI
- `-----BEGIN RSA PUBLIC KEY-----` → PKCS#1
- `-----BEGIN PRIVATE KEY-----` → PKCS#8 (암호화 안 됨)
- `-----BEGIN ENCRYPTED PRIVATE KEY-----` → PKCS#8 암호화
- `-----BEGIN RSA PRIVATE KEY-----` → PKCS#1

### PEM에서 KeyObject로 가져오기

```javascript
const { createPublicKey, createPrivateKey } = require('node:crypto');

const pubKey = createPublicKey(pemPublic);
const privKey = createPrivateKey({ key: pemPrivate, passphrase: 'top-secret' });
```

`createPublicKey`는 인자로 PEM 문자열, DER Buffer, JWK 객체, 또는 다른 `KeyObject`를 받는다. JWT 라이브러리에 키를 넘길 때 PEM을 매번 파싱하면 비용이 든다. `KeyObject`를 한 번 만들어 재사용하면 빠르다. `jsonwebtoken` 5.x 이후는 KeyObject를 직접 받는다.

### JWK 변환

OIDC, JWKS 엔드포인트를 구현할 때 JWK 형식이 필요하다.

```javascript
const jwk = publicKey.export({ format: 'jwk' });
// { kty: 'RSA', n: '...', e: 'AQAB' }
```

`kid`(키 ID)는 JWK에 자동으로 안 들어간다. 직접 추가해야 한다. 보통 키의 SHA-256 해시(RFC 7638 thumbprint)를 쓴다.

### 대칭 키도 KeyObject로

```javascript
const { createSecretKey } = require('node:crypto');
const key = createSecretKey(Buffer.from('32-byte-secret-........'.padEnd(32)));
const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
```

`createCipheriv`에 Buffer 대신 `KeyObject`를 넘길 수 있다. 메모리에서 키를 좀 더 깔끔하게 격리할 수 있고, 키 유출 디버그가 쉬워진다.

---

## 6. randomBytes vs randomUUID 언제 무엇을 쓸까

랜덤 값이 필요할 때 두 함수가 가장 자주 등장한다. 용도가 다르다.

### randomBytes — 임의 길이 보안 난수

```javascript
const token = crypto.randomBytes(32).toString('hex');       // 64자 hex
const session = crypto.randomBytes(32).toString('base64url'); // 43자 base64url
```

OS의 CSPRNG(`/dev/urandom`, Windows의 `BCryptGenRandom`)에서 바이트를 받아온다. 세션 토큰, API 키, CSRF 토큰, 비밀번호 재설정 토큰, AES IV 같은 곳에 쓴다. 길이는 보통 16바이트(128비트) 이상, 비밀이라면 32바이트(256비트)를 잡는다.

동기 함수와 비동기 함수가 둘 다 있다. `randomBytes(size, callback)` 또는 `randomBytes(size)`(동기). 작은 사이즈(수십 바이트)는 동기로 써도 무방하지만, 큰 사이즈(KB 이상)는 비동기로 가야 이벤트 루프가 안 막힌다. 부팅 직후 엔트로피 풀이 부족한 환경(특히 컨테이너)에서는 동기 호출이 수십 ms 블로킹될 수 있다.

### randomUUID — RFC 4122 v4 UUID

```javascript
const id = crypto.randomUUID();  // 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
```

내부적으로는 16바이트 랜덤을 받아서 UUID v4 포맷으로 찍어낸다. 6비트가 버전/변종 고정에 쓰이므로 실제 엔트로피는 122비트다. 그래도 충돌 확률은 무시할 수준이라 식별자 용도로는 충분하다.

DB 기본 키, 요청 트레이스 ID, 로그 상관 ID에 쓴다. 형식이 고정되어 있어서 로그 파싱이나 인덱싱이 일관된다. 보안 토큰으로 쓰면 안 되냐고 묻는다면, 엔트로피는 충분하지만 형식이 노출되는 게 약점이다. 토큰을 본 사람이 "아 이거 UUID v4네"라고 알게 되는 자체가 정보다.

Node 14.17부터 표준에 들어왔다. 그전에는 `uuid` 패키지를 쓰거나 `randomBytes` 결과를 직접 포맷팅했다. 지금은 의존성 없이 코어에서 해결된다.

### 성능 차이

```javascript
// 1백만 회 호출 기준 (M1 Mac)
randomBytes(16)  → 약 300ms
randomUUID()     → 약 600ms
```

randomUUID가 두 배 정도 느리다. UUID 포맷팅 오버헤드 때문이다. 초당 수십만 건 ID를 발급하는 곳이면 차이가 보인다. 그런 곳에서는 ULID나 Snowflake 같은 정렬 가능 ID를 쓰는 게 인덱스 성능에서도 유리하다.

---

## 7. webcrypto 모듈 — 브라우저 호환 표준

Node 15부터 `crypto.webcrypto`가 들어왔다. 브라우저의 `window.crypto.subtle`과 같은 API다. Node 19부터는 글로벌 `crypto`로도 접근 가능하다.

```javascript
const { subtle } = globalThis.crypto;  // Node 19+
// 또는 const { subtle } = require('node:crypto').webcrypto;
```

### Promise 기반, ArrayBuffer 중심

가장 큰 차이는 모든 함수가 Promise를 반환하고, 입출력이 `Buffer`가 아닌 `ArrayBuffer`나 `Uint8Array`라는 점이다.

```javascript
const data = new TextEncoder().encode('hello');
const digest = await subtle.digest('SHA-256', data);
console.log(Buffer.from(digest).toString('hex'));
```

`subtle.digest`는 ArrayBuffer를 돌려준다. Node 쪽에서 쓰려면 Buffer로 한 번 감싸야 편하다.

### AES-GCM 예시

```javascript
const key = await subtle.generateKey(
  { name: 'AES-GCM', length: 256 },
  true,
  ['encrypt', 'decrypt']
);
const iv = crypto.getRandomValues(new Uint8Array(12));
const ciphertext = await subtle.encrypt(
  { name: 'AES-GCM', iv },
  key,
  new TextEncoder().encode('secret')
);
```

`createCipheriv`보다 코드가 깔끔하고, 인증 태그가 ciphertext 뒤에 자동으로 붙는다. 별도로 `getAuthTag`를 부를 필요가 없다. 복호화 측에서도 통째로 넘기면 된다.

### 그래서 언제 쓰나

- 브라우저와 Node에서 같은 코드를 돌려야 하는 경우(엣지 런타임, Service Worker, Cloudflare Workers).
- 표준 API를 쓰고 싶은 경우. WebCrypto는 W3C 표준이라 미래에도 안정적이다.
- 코드를 다른 런타임(Deno, Bun)으로 옮길 가능성이 있는 경우. Deno는 처음부터 WebCrypto만 지원한다.

반대로 Node 전용이고 성능이 중요한 곳에서는 `crypto` 코어 API가 더 빠르다. WebCrypto는 매번 Promise를 만들고 ArrayBuffer 변환이 끼어들어서 오버헤드가 있다. 벤치마크해보면 작은 데이터에 대해 2~3배 차이가 난다. 큰 데이터(MB 이상)는 차이가 줄어든다.

### 알고리즘 이름이 다르다

`crypto`는 `'aes-256-gcm'`, `'sha256'` 같은 OpenSSL 이름을 쓰고, WebCrypto는 `'AES-GCM'`, `'SHA-256'` 같은 W3C 이름을 쓴다. 헷갈리는 부분이다. 한 코드에 둘이 섞이면 가독성이 떨어지니 가능하면 한 쪽으로 통일한다.

---

## 마무리: 직접 구현하지 마라

이 문서 절반은 "직접 하지 마라"는 경고로 채울 수도 있다. 직접 nonce를 관리하지 마라, 직접 비교하지 마라, 직접 키 유도하지 마라. 그래도 동작 원리를 알아야 라이브러리가 뭘 해주는지, 어디가 우리 책임인지 구분이 된다.

운영하면서 본 사고의 대부분은 "암호 알고리즘이 깨져서"가 아니라 "써야 할 함수를 안 써서" 일어났다. timingSafeEqual을 안 쓰고, 인증 태그를 안 검증하고, nonce를 재사용하고, 비밀번호를 SHA-256으로 저장한다. 코어 모듈 문서를 한 번 정독하는 것만으로 막을 수 있는 사고가 많다.
