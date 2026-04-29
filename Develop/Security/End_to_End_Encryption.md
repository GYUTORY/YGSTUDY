---
title: E2EE 종단간 암호화
tags: [security, e2ee, encryption, signal-protocol, double-ratchet, x3dh, ecdh, forward-secrecy, mls, nodejs]
updated: 2026-04-29
---

# E2EE (End-to-End Encryption, 종단간 암호화)

## 개요

종단간 암호화는 **송신자의 단말에서 수신자의 단말까지** 데이터가 평문으로 노출되지 않도록 보호하는 방식이다. 중간에 메시지를 중계하는 서버, 네트워크 장비, ISP, 클라우드 사업자 누구도 평문을 볼 수 없다. 키를 가진 두 종단(end)만이 메시지를 복호화할 수 있다.

이름이 비슷해서 자주 헷갈리는 게 있다. "E2E 테스팅(End-to-End Testing)"은 시스템 전체 흐름을 테스트하는 QA 용어로, 암호화와 전혀 관련이 없다. 이 문서는 보안 영역의 종단간 암호화를 다룬다.

### TLS와 무엇이 다른가

대부분의 개발자가 처음 E2EE를 접할 때 "TLS도 암호화하는 거 아닌가?" 라고 의문을 가진다. 결정적인 차이는 **누가 평문을 볼 수 있는가** 이다.

```
[전송 구간 암호화 (TLS)]

  Client A ───TLS───▶ Server ───TLS───▶ Client B
                       ▲
                       │
                  서버는 평문을
                  볼 수 있음
                  (저장, 검색, 분석 가능)


[종단간 암호화 (E2EE)]

  Client A ──암호문──▶ Server ──암호문──▶ Client B
                       ▲
                       │
                  서버는 암호문만 보유
                  (복호화 키 없음)
```

TLS는 클라이언트와 서버 사이의 통신 구간만 보호한다. 서버에 도착하면 평문으로 풀린다. 메신저 서버라면 메시지 내용을 데이터베이스에 저장하고, 검색하고, 추천 알고리즘에 활용할 수 있다. 정부 영장에 의해 제출도 가능하다.

E2EE에서는 서버가 **암호문 전달자** 역할만 한다. 서버 운영자가 데이터베이스를 통째로 털려도 평문은 나오지 않는다. 영장이 와도 제출할 평문이 없다.

| 항목 | TLS (전송 구간) | E2EE (종단간) |
|------|----------------|---------------|
| 암호화 범위 | Client ↔ Server | Client ↔ Client |
| 서버에서 평문 접근 | 가능 | 불가능 |
| 키 보관 | 서버에 인증서 키 | 각 단말이 보관 |
| 서버 침해 시 | 평문 유출 위험 | 암호문만 유출 |
| 서비스 측 검색/모더레이션 | 가능 | 어려움 또는 불가 |

실무에서는 두 가지를 같이 쓴다. 클라이언트가 서버에 암호문을 올릴 때 TLS로 한 번 더 감싼다. 메타데이터(누가 누구에게 보냈는지, 시각 등)는 어차피 서버가 알아야 라우팅하므로 TLS만 보호한다. E2EE의 보호 범위는 어디까지나 **메시지 본문**이다.

## 키 교환의 어려움

E2EE의 핵심은 "어떻게 두 사용자가 같은 비밀 키를 공유하느냐" 이다. 서버를 신뢰할 수 없는 환경에서, 처음 만난 두 사람이 도청 없이 공통 키를 만들어야 한다. 여기서 디피-헬만 키 교환이 등장한다.

### Diffie-Hellman 키 교환

수학적으로 단순화하면 이렇다. 두 사람이 공개된 값 `g`, `p`를 공유한 상태에서, 각자 비밀 값 `a`, `b`를 만들고 `g^a mod p`, `g^b mod p`를 교환한다. 그러면 두 사람 모두 `g^(ab) mod p`를 계산할 수 있지만, 도청자는 `a`나 `b`를 모르면 이 값을 구할 수 없다.

```
Alice                                        Bob
  │                                            │
  │  비밀: a                                    │  비밀: b
  │  공개: A = g^a mod p                         │  공개: B = g^b mod p
  │                                            │
  │ ──────────── A 전송 ──────────────────────▶ │
  │ ◀─────────── B 전송 ─────────────────────── │
  │                                            │
  │  공유 키 = B^a = g^(ab) mod p               │  공유 키 = A^b = g^(ab) mod p
  │                                            │
  │       두 사람만 같은 값을 갖게 된다             │
```

이 방식의 한계는 **중간자 공격(MITM)** 에 취약하다는 점이다. Alice가 Bob의 공개값 B를 받았다고 믿지만, 실제로는 공격자가 가로챈 후 자기 값을 끼워넣을 수 있다. 그래서 실무에서는 단순 DH로 끝내지 않고 **인증된 키 교환** 으로 확장한다.

### ECDH (Elliptic Curve Diffie-Hellman)

타원곡선 암호 위에서 동일한 원리를 구현한 것이 ECDH다. 같은 보안 강도를 더 짧은 키로 달성한다. RSA-3072와 비슷한 보안 강도를 ECDH-256(Curve25519 등)로 얻을 수 있다. 모바일 환경에서 배터리와 대역폭을 아끼려면 ECDH가 사실상 유일한 선택지다.

Curve25519는 Daniel Bernstein이 설계한 곡선으로, NSA가 끼어들지 않은 곡선이라는 점 때문에 Signal, WireGuard, OpenSSH 등에서 표준처럼 쓰인다.

### X3DH (Extended Triple Diffie-Hellman)

기본 DH의 두 가지 약점이 있다. 첫째, 중간자 공격. 둘째, **비동기 시작**이 안 된다. 메신저에서는 상대가 오프라인일 때도 첫 메시지를 보낼 수 있어야 한다. 상대가 키를 응답해줘야 진행되는 일반 DH로는 이게 어렵다.

Signal이 도입한 X3DH는 이 두 문제를 동시에 풀었다. 핵심은 사용자가 미리 여러 종류의 키를 서버에 올려두는 것이다.

```
[Bob이 서버에 사전 등록하는 키들]

  IK_B  : Identity Key (장기 키, 잘 안 바뀜)
  SPK_B : Signed PreKey (중기 키, 주기적 교체)
  OPK_B : One-time PreKey (1회용 키, 다량 업로드)


[Alice가 Bob에게 첫 메시지 보낼 때]

  Alice                Server                 Bob (오프라인)
    │                    │                       │
    │ ─Bob 키 번들 요청──▶│                       │
    │ ◀── IK, SPK, OPK ──│                       │
    │                    │                       │
    │  자신의 EK 생성                              │
    │  4개 DH 연산 수행:                            │
    │   DH1 = DH(IK_A, SPK_B)                    │
    │   DH2 = DH(EK_A, IK_B)                     │
    │   DH3 = DH(EK_A, SPK_B)                    │
    │   DH4 = DH(EK_A, OPK_B)                    │
    │  SK = KDF(DH1 || DH2 || DH3 || DH4)        │
    │                    │                       │
    │ ─암호문 + EK ──────▶│ ──── 전달 ───────────▶│
    │                                            │
    │                                            │ 같은 SK 도출 가능
```

DH를 4번 섞는 이유가 있다. IK ↔ IK 조합으로 신원 인증, EK ↔ IK로 송신자 임시성, EK ↔ SPK로 비동기성, EK ↔ OPK로 추가 엔트로피를 얻는다. OPK는 1회만 쓰고 서버에서 삭제하는데, 이게 나중에 다룰 **Forward Secrecy** 의 첫 단추다.

OPK가 다 떨어지면 SPK만으로도 진행되도록 설계되어 있다. Alice가 Bob에게 처음 보내는 메시지는 그 자체로 암호화되어 있고, Bob이 온라인이 되면 받아서 동일한 SK를 도출한다.

## Double Ratchet 알고리즘

X3DH로 초기 공유 키 SK를 만들었다. 이제 본 메시지들은 이 SK로 암호화하면 될까? 아니다. 매번 같은 키를 쓰면 키가 한 번 새면 모든 과거/미래 메시지가 노출된다. 그래서 **메시지마다 키를 바꾸는** 메커니즘이 필요하다. 이게 Double Ratchet이다.

이름 그대로 두 개의 래칫(한쪽으로만 돌아가는 톱니바퀴)으로 구성된다.

### Symmetric Ratchet (대칭 래칫)

같은 방향으로 메시지를 연속해서 보낼 때 동작한다. 현재 체인 키 `CK_n`에서 KDF를 통해 메시지 키 `MK_n`과 다음 체인 키 `CK_{n+1}`을 뽑는다. 메시지 키는 한 번 쓰고 버린다.

```
CK_0
  │
  ├─KDF─▶ MK_0  (메시지 0 암호화에 사용 후 폐기)
  │
  ▼
CK_1
  │
  ├─KDF─▶ MK_1  (메시지 1 암호화)
  │
  ▼
CK_2
  │
  ├─KDF─▶ MK_2
  │
  ▼
 ...
```

KDF는 단방향이라 `MK_2`가 노출되어도 `CK_2`나 `MK_1`을 역산할 수 없다. 이게 **Forward Secrecy** 다. 단말이 털려서 현재 키가 빠져나가도 과거 메시지는 보호된다.

### Diffie-Hellman Ratchet (DH 래칫)

문제는 한쪽이 일방적으로만 보내는 게 아니라는 점이다. 양방향 대화에서는 상대 메시지가 올 때마다 키 자체를 새로 섞어야 한다. 그렇지 않으면 한 번 노출된 체인 키가 영원히 같은 방향으로 흐른다.

DH 래칫은 메시지를 보낼 때마다 새로운 ECDH 키 쌍을 생성해서 공개 부분을 메시지 헤더에 끼워 보낸다. 상대는 받은 공개 키와 자신의 비밀 키로 새 DH를 수행하고, 그 결과를 루트 키에 섞는다. 이렇게 하면 키가 한 번 노출되어도 다음 메시지부터는 다시 안전해진다. 이게 **Post-Compromise Security** 다.

```
Alice                                          Bob
  │                                              │
  │  RK_0 (X3DH 결과)                             │  RK_0
  │                                              │
  │  새 DH 키쌍 생성 → 공개키 DH_A1                │
  │  메시지 1 전송 (헤더에 DH_A1 포함)             │
  │ ──────────────────────────────────────────▶ │
  │                                              │
  │                          Bob: DH(DH_A1, b)로 │
  │                          RK_1 도출, CK_recv 갱신
  │                          새 DH 키쌍 → DH_B1   │
  │                                              │
  │ ◀────────────────────────────────────────── │
  │                                              │  메시지 2 회신 (DH_B1 포함)
  │  Alice: DH(DH_B1, a)로                       │
  │  RK_2 도출, CK_recv 갱신                       │
```

Symmetric Ratchet과 DH Ratchet 두 개가 동시에 돌면서, 같은 방향 연속 메시지는 빠르게(대칭 KDF), 방향이 바뀔 때는 비싼 DH 연산으로 키를 새로 섞는다. 결과적으로 거의 모든 메시지가 다른 키로 암호화된다.

### 메시지 순서 뒤바뀜 처리

UDP 환경처럼 메시지 순서가 바뀌거나 누락될 수 있다. Double Ratchet은 이를 위해 **Skipped Message Keys** 캐시를 유지한다. 4번이 먼저 도착하고 3번이 나중에 도착하면, 4번을 풀기 위해 도출한 중간 키들 중 3번에 해당하는 것을 잠시 보관해두는 방식이다. 무한정 쌓이지 않도록 보통 1000개 정도로 상한을 둔다. 너무 늦게 오는 메시지는 그냥 폐기된다.

## Signal Protocol

X3DH + Double Ratchet 조합을 표준화한 것이 Signal Protocol이다. WhatsApp, Signal, Facebook Messenger 비밀 대화, Skype 비공개 대화 등이 모두 이 프로토콜 또는 변형을 쓴다.

### 전체 흐름

```
[1. 등록 단계]
  Alice/Bob이 각자 IK, SPK, OPK들을 서버에 업로드.

[2. 세션 생성 (X3DH)]
  Alice가 Bob의 키 번들을 받아 SK 도출.
  첫 메시지 헤더에 자신의 EK와 사용한 OPK_id 포함.

[3. 본 통신 (Double Ratchet)]
  SK를 초기 루트 키로 삼아 메시지마다 키 갱신.
  방향 바뀔 때마다 DH 래칫 동작.

[4. 키 갱신]
  SPK는 주기적(주 단위) 갱신 후 서버 재업로드.
  OPK는 소진되는 만큼 보충.
  IK는 거의 안 바뀜 (바뀌면 상대 단말에 경고).
```

### 주요 보안 속성

Signal Protocol이 보장하는 것들:

- **기밀성**: 메시지 본문은 두 단말 외 누구도 못 본다.
- **Forward Secrecy**: 현재 키가 노출되어도 과거 메시지는 안전.
- **Post-Compromise Security**: 노출 이후에도 새 DH 래칫이 돌면 다시 안전해진다.
- **Deniability**: 제3자에게 "이 메시지는 정말 Alice가 보냈다"고 암호학적으로 증명할 수 없다 (양쪽이 공유 키로 MAC을 만들기 때문에 누구든 위조 가능).
- **Authenticity (당사자 사이)**: 대화 당사자끼리는 IK 검증을 통해 상대를 확신할 수 있다.

Deniability는 흥미로운 속성이다. 강력한 인증을 보장하는 기존 PKI 서명 방식과 정반대로, **법적/사회적으로 메시지 송신을 부인할 수 있도록** 일부러 설계되었다. 인권 활동가나 내부고발자가 메시지를 누군가에게 보여줘도, 그것이 위조가 아니라는 보장이 없으므로 보호받는다.

## Node.js로 직접 구현해보기

E2EE의 골격은 ECDH로 공유 키를 만들고 AES-GCM으로 메시지를 암호화하는 것이다. 실제 Signal Protocol은 훨씬 복잡하지만, 핵심 아이디어를 익히려면 이 정도 수준을 직접 짜보는 게 좋다.

### ECDH로 공유 키 만들기

```javascript
const crypto = require('crypto');

// 두 사용자가 각각 키 쌍을 생성한다 (Curve25519 사용)
function createIdentity() {
  const keyPair = crypto.generateKeyPairSync('x25519');
  return {
    publicKey: keyPair.publicKey.export({ type: 'spki', format: 'der' }),
    privateKey: keyPair.privateKey,
  };
}

const alice = createIdentity();
const bob = createIdentity();

// 상대 공개키를 KeyObject로 import해야 diffieHellman 호출 가능
function importPublic(rawDer) {
  return crypto.createPublicKey({
    key: rawDer,
    format: 'der',
    type: 'spki',
  });
}

const aliceShared = crypto.diffieHellman({
  privateKey: alice.privateKey,
  publicKey: importPublic(bob.publicKey),
});

const bobShared = crypto.diffieHellman({
  privateKey: bob.privateKey,
  publicKey: importPublic(alice.publicKey),
});

console.log(aliceShared.equals(bobShared)); // true
```

`crypto.diffieHellman`이 반환하는 raw 결과를 직접 키로 쓰면 안 된다. 항상 KDF(HKDF 등)를 한 번 통과시켜야 한다. 그렇지 않으면 곡선의 작은 그룹 공격이나 키 길이 편향 같은 미묘한 문제가 생긴다.

### HKDF로 메시지 키 도출

```javascript
function hkdf(ikm, salt, info, length = 32) {
  return crypto.hkdfSync('sha256', ikm, salt, info, length);
}

// 공유 비밀에서 송신/수신 키를 분리해서 뽑는다
const rootSalt = Buffer.alloc(32, 0); // 실제로는 X3DH 결과에서 가져옴
const sendKey = Buffer.from(hkdf(aliceShared, rootSalt, 'send-key'));
const recvKey = Buffer.from(hkdf(aliceShared, rootSalt, 'recv-key'));
```

`info` 파라미터로 용도를 분리하면 같은 IKM에서 여러 키를 안전하게 뽑을 수 있다. "send-key", "recv-key" 같은 문자열을 넣어 두 단말이 송수신 방향에 다른 키를 쓰도록 한다.

### AES-256-GCM으로 메시지 암호화

```javascript
function encrypt(key, plaintext, associatedData = Buffer.alloc(0)) {
  const iv = crypto.randomBytes(12); // GCM 표준 IV 길이
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  cipher.setAAD(associatedData);

  const ciphertext = Buffer.concat([
    cipher.update(plaintext, 'utf8'),
    cipher.final(),
  ]);
  const tag = cipher.getAuthTag();

  return { iv, ciphertext, tag };
}

function decrypt(key, { iv, ciphertext, tag }, associatedData = Buffer.alloc(0)) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAAD(associatedData);
  decipher.setAuthTag(tag);

  return Buffer.concat([
    decipher.update(ciphertext),
    decipher.final(),
  ]).toString('utf8');
}

// Alice → Bob
const msg = encrypt(sendKey, '안녕 Bob, 비밀 메시지야');
const recovered = decrypt(sendKey, msg);
```

GCM에서 중요한 점이 있다. **같은 키로 같은 IV를 두 번 쓰면 보안이 즉시 깨진다.** 단순히 노출되는 게 아니라 인증까지 우회된다. 그래서 Double Ratchet처럼 메시지마다 키를 바꾸거나, 적어도 카운터 기반 IV를 단조 증가시켜야 한다. 멀티 디바이스에서 같은 키를 공유하면서 IV 카운터를 동기화하지 않은 구현이 자주 사고를 친다.

`associatedData`(AAD)는 암호화하지는 않지만 인증에 포함되는 데이터다. 송신자 ID, 메시지 번호, 헤더 등을 넣어서 변조를 막는다. 라우팅 정보가 바뀌면 복호화가 실패해서 공격자가 헤더만 조작하는 시나리오를 차단한다.

### 간단한 대칭 래칫

```javascript
class SymmetricRatchet {
  constructor(initialChainKey) {
    this.chainKey = Buffer.from(initialChainKey);
    this.counter = 0;
  }

  next() {
    // 메시지 키와 다음 체인 키를 KDF로 분리
    const messageKey = Buffer.from(
      crypto.hkdfSync('sha256', this.chainKey, Buffer.alloc(0), 'msg', 32)
    );
    const nextChainKey = Buffer.from(
      crypto.hkdfSync('sha256', this.chainKey, Buffer.alloc(0), 'chain', 32)
    );

    // 이전 체인 키는 메모리에서 즉시 제거
    this.chainKey.fill(0);
    this.chainKey = nextChainKey;
    const counter = this.counter++;

    return { messageKey, counter };
  }
}

const ratchet = new SymmetricRatchet(sendKey);
const { messageKey: mk0 } = ratchet.next();
const enc0 = encrypt(mk0, '메시지 1');

const { messageKey: mk1 } = ratchet.next();
const enc1 = encrypt(mk1, '메시지 2');
// mk0과 mk1은 다른 키. 한쪽이 노출되어도 다른 쪽 영향 없음
```

실제 Signal 구현에서는 사용한 메시지 키도 즉시 메모리에서 제거한다(`buffer.fill(0)`). Node.js의 GC 시점은 알 수 없으므로, 키 객체를 명시적으로 0으로 덮어쓰는 게 관례다.

### 파일 E2EE

큰 파일을 통째로 메모리에 올리면 OOM이 난다. 청크 단위로 처리하되, 각 청크를 다른 키나 다른 IV로 암호화한다.

```javascript
const fs = require('fs');

async function encryptFile(inPath, outPath, fileKey) {
  const input = fs.createReadStream(inPath, { highWaterMark: 64 * 1024 });
  const output = fs.createWriteStream(outPath);
  let chunkIndex = 0;

  for await (const chunk of input) {
    // 청크별로 IV를 카운터로 만든다
    const iv = Buffer.alloc(12);
    iv.writeUInt32BE(chunkIndex, 8);

    const cipher = crypto.createCipheriv('aes-256-gcm', fileKey, iv);
    const encrypted = Buffer.concat([cipher.update(chunk), cipher.final()]);
    const tag = cipher.getAuthTag();

    // [길이(4) | 태그(16) | 암호문] 형태로 기록
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32BE(encrypted.length);
    output.write(Buffer.concat([lenBuf, tag, encrypted]));

    chunkIndex++;
  }
  output.end();
}
```

파일 자체는 청크별로 암호화하고, 청크들을 묶는 메타데이터(파일명, 크기, 청크 수, fileKey의 해시 등)는 별도로 메시지 채널에 E2EE로 보낸다. 서버는 암호화된 파일 청크들과 식별자만 본다. 이게 WhatsApp이 미디어 메시지를 처리하는 대략적인 구조다.

## 키 관리

E2EE의 안전성은 **상대의 공개키를 정말 그 사람의 것으로 확신할 수 있는가** 에 달려 있다. 이걸 보장하지 못하면 서버가 가운데서 자기 키를 끼워넣는 중간자 공격을 막을 수 없다.

### Safety Number (안전 번호)

Signal에서는 두 사용자의 IK를 결합해서 사람이 비교할 수 있는 번호로 만든다. 60자리 숫자나 QR 코드로 표시된다. Alice와 Bob이 직접 만나서 화면에 표시된 번호가 같은지 확인하면, 그 시점에 서버가 거짓말을 하고 있지 않다는 걸 검증할 수 있다.

```
[Alice 화면]
  Bob과의 안전 번호
  31429 84017 25683
  92041 75308 41927
  18365 92847 30184
  56291 84730 51928

[Bob 화면]
  Alice와의 안전 번호 (같아야 함)
  31429 84017 25683
  92041 75308 41927
  ...
```

실무에서 모든 사용자가 이 검증을 하지는 않는다. 위협 모델이 높은 사용자(기자, 활동가, 변호사)만 한다. 일반 사용자는 "암호화되어 있다"는 표시 정도만 본다. 그래도 옵션을 노출하는 것 자체가 의미가 있다.

### 키 변경 감지

상대가 단말을 새로 등록하거나 앱을 재설치하면 새 IK가 생성된다. 이때 기존 대화 상대에게 **"안전 번호가 바뀌었습니다"** 같은 경고를 띄워야 한다. 대부분의 사용자는 무시하지만, 위장 공격이 일어나면 이 경고가 유일한 단서다.

서버가 사용자를 사칭해 새 IK를 등록하는 시나리오를 막으려면, 사용자 단말 측에서 자기 IK 변경 이력을 서명된 형태로 추적해야 한다. Signal은 이를 위해 별도의 서명 체인을 둔다.

### 사용자 등록 검증의 한계

근본적인 문제: **처음 등록할 때** 그 IK가 정말 그 사람 것인지 보장할 방법이 사실상 없다. 전화번호 SMS 인증을 거쳐도, SMS 자체가 통신사 영역이고 SS7 같은 프로토콜 취약점이 알려져 있다. 일부 국가에서는 통신사가 정부 협조 하에 SMS를 가로챌 수 있다.

이런 본질적 한계 때문에 E2EE는 "완벽한 보안"이 아니라 "신뢰 이동"이라고 봐야 한다. 서버를 신뢰하지 않는 대신, 처음 키 교환 시점의 채널을 신뢰하는 구조다.

## Forward Secrecy와 Post-Compromise Security

이 두 속성은 비슷해 보이지만 보호하는 시점이 다르다.

```
시간 ──────▶
                  ↑ 키 노출 시점
  ─────────────── │ ───────────────
   과거 메시지       미래 메시지
   (FS가 보호)      (PCS가 보호)
```

### Forward Secrecy

현재 키가 털려도 **과거 메시지** 는 복호화할 수 없도록 한다. Double Ratchet의 KDF가 단방향이라 가능하다. `MK_n`을 알아도 `MK_{n-1}`은 역산 불가다. 사용 후 메시지 키를 즉시 폐기하면, 과거 메시지를 다시 풀려면 그 시점의 키가 필요하다는 보장을 얻는다.

서버 측 구현에서 이걸 망치는 흔한 실수: 디버그 로그에 평문이나 메시지 키를 찍어두는 것이다. 로그가 영원히 남아있다면 FS가 무력화된다. 모든 로깅은 메타데이터에만 한정해야 한다.

### Post-Compromise Security

키가 털린 **이후의 새 메시지** 가 다시 안전해지는 속성이다. DH 래칫이 동작하면서 새로운 임시 키 쌍이 생성되고, 공격자가 이전에 훔친 키 정보로는 새 DH 결과를 계산할 수 없다.

PCS는 **공격자가 패시브하게 통신만 도청** 하는 경우에 한해 성립한다. 공격자가 단말에 상주해서 모든 새 키도 계속 훔쳐 간다면 PCS는 깨진다. 실무에서 이걸 가정하는 위협 모델이 있는지 진지하게 따져봐야 한다.

## 서버 측에서 평문을 못 보는 구조

E2EE 시스템을 설계할 때 자주 나오는 요구사항이 충돌한다.

### 흔한 충돌 사항

| 요구사항 | E2EE와의 충돌 |
|----------|--------------|
| 서버 측 메시지 검색 | 본문이 암호문이라 인덱싱 불가 |
| 신고/모더레이션 | 서버가 신고된 메시지 내용 못 봄 |
| 데이터 분석/통계 | 본문 기반 분석 불가 |
| 백업 (서버 측) | 키 없이는 복원 의미 없음 |
| 광고 타겟팅 | 메시지 내용 활용 불가 |
| 클라우드 OCR/번역 | 클라이언트에서만 가능 |

이 모든 걸 만족하면서 E2EE를 한다고 광고하는 서비스는 의심해봐야 한다. 어딘가에서 평문에 접근할 수 있는 구조라는 뜻이고, 그건 E2EE가 아니다.

### 모더레이션 절충안

신고/모더레이션은 가장 풀기 어려운 문제다. 몇 가지 접근법이 있다:

1. **신고자 자발 제출**: 신고할 때 클라이언트가 메시지 평문과 송신자 서명을 함께 제출. 서버는 받은 본문을 검증할 뿐, 능동적으로 가져올 수는 없다.
2. **클라이언트 사이드 스캔**: 단말에서 알려진 위해 콘텐츠 해시와 비교 후 결과만 서버 보고. Apple이 시도했다가 프라이버시 우려로 철회한 방식.
3. **메타데이터 기반 abuse 탐지**: 본문은 못 보지만 "한 계정이 1분에 100명에게 동일 크기 메시지를 보냄" 같은 패턴은 서버에서 보임.

### 메타데이터 노출

E2EE는 본문은 보호하지만 **메타데이터** 는 그대로 노출된다.

```
[E2EE로 보호되지 않는 정보들]

  - 누가 누구에게 보냈는지 (송수신자 ID)
  - 언제 보냈는지 (타임스탬프)
  - 메시지 크기 (본문 길이로 추론)
  - 통신 빈도와 패턴
  - 사용한 단말 정보
  - IP 주소
  - 그룹 멤버 구성
```

"누가 어느 변호사 사무실과 통신했는지" 만으로도 충분히 민감한 정보가 될 수 있다. Signal은 이를 줄이려 Sealed Sender(송신자 정보를 서버도 모르게 봉인)나 Private Contact Discovery(연락처 매칭을 SGX 안에서 수행) 같은 기술을 추가했다. 완전 해결은 어렵고, 위협 모델에 따라 어디까지 허용할지 결정해야 한다.

## 그룹 채팅 E2EE

1:1 E2EE는 비교적 단순하다. 그룹이 되면 복잡해진다. 멤버가 N명이면 메시지 1개를 N-1번 암호화해야 하나? 멤버가 추가/탈퇴할 때 키를 어떻게 갱신하나?

### Sender Keys (Signal 그룹 방식)

각 송신자가 자신의 **Sender Key Chain** 을 만들어 그룹 멤버 모두에게 1:1 채널로 배포한다. 이후 본 메시지는 한 번만 암호화하고 모두에게 같은 암호문을 뿌린다.

```
[그룹: A, B, C, D]

A의 송신 키 체인 SC_A를
A → B (1:1 E2EE로 SC_A 전달)
A → C (1:1 E2EE로 SC_A 전달)
A → D (1:1 E2EE로 SC_A 전달)

이후 A의 메시지는
  암호문 = AES-GCM(SC_A에서 도출한 MK, 평문)
  서버에 한 번 업로드 → B, C, D에게 fan-out
```

Sender Keys 방식의 약점은 **멤버 변경 시** 다. 누가 나가면 SC를 새로 만들어 남은 멤버들에게 다시 1:1 배포해야 한다. 그룹이 클수록 비싸진다. 또 새 멤버가 들어왔을 때, 그가 과거 메시지를 못 보게 하려면 키 갱신을 강제해야 한다.

### MLS (Messaging Layer Security)

IETF에서 표준화한 그룹 E2EE 프로토콜이다(RFC 9420). 트리 구조를 이용한 **TreeKEM** 으로 멤버 N명이 있을 때 키 갱신 비용을 O(log N)으로 줄였다. Signal의 Sender Keys가 O(N)인 것에 비해 큰 개선이다.

```
[TreeKEM 개념]

         Group Key
         /       \
        K1        K2
       /  \      /  \
      A    B    C    D

A가 키를 갱신하면:
  - A 자기 잎 키 갱신
  - K1 갱신 (B에게만 K1 배포)
  - Group Key 갱신 (K2에게만 배포 → C, D는 K2 잎으로 받음)

총 갱신 메시지 수: O(log N)
```

MLS는 1:1보다 큰 그룹과 회사 단위 E2EE 메신저 같은 기업용 용도를 겨냥했다. WhatsApp, Discord, Cisco Webex 등이 MLS 채택을 발표했다. Signal은 자체 Sender Keys를 계속 쓰지만, 향후 MLS 기반으로 갈 가능성이 있다.

## 멀티 디바이스 환경

사용자가 폰, 태블릿, 데스크톱에서 같은 계정을 쓰고 싶어 한다. 단순한 방법은 모든 디바이스가 같은 IK를 공유하는 것인데, 이러면 한 디바이스가 털렸을 때 모든 디바이스가 노출된다. 또 새 디바이스에 IK를 어떻게 안전하게 옮기나 하는 문제도 있다.

### 디바이스별 키

Signal Desktop, WhatsApp Web, iMessage 같은 시스템은 **각 디바이스가 별도 IK를 가지는** 방식을 쓴다. 한 사용자가 여러 IK를 가진다고 보면 된다. 메시지를 보낼 때는 상대 사용자의 모든 디바이스에 각각 별도로 암호화해서 보낸다.

```
[Alice가 Bob에게 메시지]

Bob의 디바이스: 폰, PC, 태블릿
Alice는 메시지를 3번 암호화한다:
  msg₁ = E2EE(SK_Bob_phone, plaintext)
  msg₂ = E2EE(SK_Bob_pc, plaintext)
  msg₃ = E2EE(SK_Bob_tablet, plaintext)

서버는 (Bob_phone, msg₁), (Bob_pc, msg₂), (Bob_tablet, msg₃)을 각각 라우팅
```

Alice 본인 디바이스끼리도 메시지를 동기화하려면, Alice의 다른 디바이스들에게도 암호화해서 보낸다. 결국 보낸 사람 디바이스 수와 받은 사람 디바이스 수의 곱만큼 암호화가 일어난다.

### Sesame 프로토콜

Signal이 멀티 디바이스를 위해 추가한 레이어가 Sesame이다. 사용자 단위로 "이 사용자가 가진 디바이스 목록"을 추적하고, 디바이스 추가/제거 이벤트를 다른 디바이스들에게 안전하게 전달한다. 새 디바이스를 등록할 때 기존 디바이스에서 QR 코드를 스캔해 인증하는 흐름이 일반적이다.

### 디바이스 간 동기화 함정

새 디바이스에서 **이전 메시지** 를 보고 싶다는 요구가 있다. 자연스러워 보이지만 E2EE 관점에서는 까다롭다. 이전 메시지의 키는 이미 단방향 KDF로 폐기되었기 때문이다(Forward Secrecy 때문에).

해결책은 두 가지뿐이다. 첫째, **이전 메시지를 평문으로 보지 못하게 한다**(Signal 데스크톱이 새로 설치하면 과거 메시지가 안 보이는 이유). 둘째, **암호화된 백업** 을 따로 만들고 새 디바이스에서 복원한다(WhatsApp 방식). 두 번째는 백업 키 관리가 새로운 공격 표면이 된다.

## 키 백업과 복구

사용자가 폰을 잃어버리거나 앱을 재설치하면 키가 사라진다. E2EE의 가장 큰 사용성 문제다.

### 옵션 1: 백업 안 함 (Signal 기본)

키 분실 = 메시지 분실. 새 폰에서 새 IK로 다시 시작한다. 가장 안전하지만 사용자 불만이 크다.

### 옵션 2: 사용자 비밀번호 기반 백업

사용자가 만든 비밀번호로 백업을 암호화해서 서버에 올린다. 서버는 암호문만 보유. 비밀번호를 잊으면 복원 불가. 비밀번호가 약하면 서버가 brute force 가능.

이걸 강화하려면 **PIN/Argon2 + HSM** 조합을 쓴다. Signal의 SVR(Secure Value Recovery)은 PIN을 SGX 같은 신뢰 실행 환경에 넣고, brute force 시도 횟수를 하드웨어 수준에서 제한한다. PIN이 약해도 공격자가 무한 시도할 수 없다.

### 옵션 3: 클라우드 백업 (WhatsApp E2E Backup)

WhatsApp은 사용자가 64자리 키 또는 비밀번호 중 선택해서 백업을 암호화한다. iCloud/Google Drive에 올라가는 건 암호문이고, 키는 별도로 사용자가 보관(또는 비밀번호로 도출). 비밀번호를 까먹으면 백업 못 푼다는 점을 사용자에게 명확히 알려야 한다.

### 옵션 4: 다른 디바이스에서 복원

기존에 로그인된 다른 디바이스가 있으면, 그 디바이스에서 새 디바이스로 키를 직접 전송한다. QR 코드 스캔이나 Bluetooth Pairing 같은 방식. 가장 안전하지만 다른 디바이스가 살아있어야 한다.

### 백업 정책의 본질적 충돌

회사에서 "법적 e-Discovery 요청 시 메시지를 제출해야 한다"는 컴플라이언스 요구가 들어오면, E2EE와 정면 충돌한다. 진짜 E2EE라면 회사가 평문을 못 본다. 회사가 백업 키를 보관하는 구조를 만들면 그건 더 이상 E2EE가 아니다. 이 충돌을 인정하고 어느 쪽을 포기할지 결정해야 한다. 절충은 불가능하다.

## 실무 도입 시 주의사항

### 키 분실은 데이터 분실이다

사용자에게 처음부터 이걸 명확히 알려야 한다. "비밀번호 잊어버리면 메시지가 영원히 사라집니다." UX 동선에 백업 설정을 강하게 유도하거나, 의도적으로 단순화한 PIN 복구 흐름을 제공한다. 안 그러면 고객 지원으로 "메시지 복구 좀 해주세요" 요청이 폭주하고, 진짜 E2EE라면 복구가 불가능하다.

### 검색이 어렵다

서버 측 인덱싱이 안 되므로 클라이언트에서 풀 텍스트 검색을 해야 한다. 모든 메시지를 단말 로컬에 평문으로 보관하고 SQLite FTS 같은 걸 돌리는 방식이다. 단말 저장소가 한정적이면 오래된 메시지를 잘라내야 한다.

### 신고/모더레이션 정책

서비스 출시 전에 어떤 모더레이션을 어떻게 할지 정해야 한다. 출시 후 압력에 굴복해 서버 측 스캔을 도입하면 사용자 신뢰가 깨진다. Apple의 CSAM 클라이언트 사이드 스캔 사례가 좋은 교훈이다. 신고 기반 자발 제출이 가장 무난한 절충점이지만 효과는 제한적이다.

### 알림 노출

푸시 알림이 잠금 화면에 메시지 본문을 띄우면, OS 레벨 푸시 페이로드가 평문이거나, 단말이 메시지를 미리 복호화해서 알림에 표시한다. 잠금 해제 안 한 단말에서 메시지가 보이는 사용성을 원하면 어쩔 수 없는 트레이드오프다. 정말 보안이 중요하면 "새 메시지가 도착했습니다" 같은 일반 알림만 띄우고, 사용자가 앱을 열어야 본문이 보이게 한다.

### 디버깅이 어렵다

문제가 났을 때 서버 측 로그에 메시지가 없다. 사용자가 "메시지가 안 갔다"고 하면 송신자 단말, 서버 큐, 수신자 단말 세 곳을 모두 확인해야 한다. 지원팀이 본문을 못 보니 사용자가 캡처를 보내줘야 한다. CS 비용이 일반 메신저보다 높다.

## WhatsApp, Signal, iMessage 비교

같은 Signal Protocol을 쓰지만 운영 방식과 메타데이터 처리에 차이가 있다.

| 항목 | Signal | WhatsApp | iMessage |
|------|--------|----------|----------|
| 프로토콜 | Signal Protocol (자체) | Signal Protocol (라이선스) | 자체 (Apple 설계) |
| 그룹 E2EE | Sender Keys | Sender Keys | 1:1 N번 (구버전), MLS 도입 중 |
| 백업 | 안 함 (또는 Signal-only PIN/SVR) | iCloud/Google Drive E2E 백업(옵션) | iCloud 백업이 키 포함 (E2E 아님 기본값) |
| 메타데이터 보호 | Sealed Sender, Private Contact Discovery | 메타데이터는 Meta 보유 | Apple 보유, 광고 없음 |
| 신원 검증 | Safety Number | Security Code | iCloud 키체인 기반 |
| 멀티 디바이스 | 디바이스별 IK + Sesame | 폰이 마스터 (linked devices) | iCloud 통합 |
| 소스 공개 | 클라이언트/서버 모두 오픈소스 | 클라이언트 일부 공개, 서버 비공개 | 비공개 |

iMessage의 흥미로운 약점은 기본 iCloud 백업이 켜져 있을 때 Apple이 백업에서 메시지 키를 보관한다는 점이다. 영장에 의해 평문 제출이 가능했다. Advanced Data Protection을 활성화하면 이게 진짜 E2EE 백업으로 바뀐다. 일반 사용자는 이 옵션을 모르고 쓴다.

WhatsApp은 메타데이터가 Meta 광고 시스템과 결합될 수 있다는 우려가 지속적으로 제기된다. 메시지 본문은 못 보지만 "누가 누구와 얼마나 자주 통신하는가"는 광고 타겟팅에 활용 가능하다.

Signal은 메타데이터까지 최소화하는 방향으로 설계되었지만, 그 대가로 사용성(연락처 매칭, 검색, 백업)이 떨어진다. 위협 모델이 높은 사용자에게는 최적이지만 일반 사용자에게는 진입 장벽이 있다.

## 정리

E2EE는 마법처럼 모든 보안 문제를 해결해주는 게 아니라, **신뢰의 위치를 서버에서 단말과 키 교환 시점으로 옮기는** 설계다. 잘 구현된 E2EE는 서버가 털려도 본문이 안전하지만, 메타데이터는 여전히 노출되고, 키 분실은 데이터 분실이며, 모더레이션이 어렵다.

핵심은 X3DH로 비동기 인증된 키 교환을 하고, Double Ratchet으로 메시지마다 키를 바꿔 Forward Secrecy와 Post-Compromise Security를 동시에 얻는 것이다. Node.js의 `crypto` 모듈만으로도 ECDH + AES-GCM 조합의 골격을 짤 수 있지만, 실제 운영 시스템은 Signal Protocol 라이브러리(libsignal)나 MLS 구현체를 가져다 쓰는 게 안전하다. 직접 구현은 키 메모리 관리, 사이드 채널, 리플레이 방어 같은 미묘한 부분에서 사고가 나기 쉽다.
