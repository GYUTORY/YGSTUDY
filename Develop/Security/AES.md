---
title: AES (Advanced Encryption Standard)
tags: [security, encryption, java, spring]
updated: 2026-05-26
---

# AES (Advanced Encryption Standard)

## 개요

AES는 2001년 NIST에서 채택한 대칭키 암호화 알고리즘이다. 암호화와 복호화에 같은 키를 사용하고, 128비트 블록 단위로 데이터를 처리한다.

## 키 길이와 라운드 수

| 키 길이 | 라운드 수 | 용도 |
|---------|-----------|------|
| 128비트 | 10라운드 | 일반 서비스 |
| 192비트 | 12라운드 | 금융/의료 데이터 |
| 256비트 | 14라운드 | 군사/기밀 정보 |

키 길이에 따라 라운드 수만 달라지고 블록 크기는 셋 다 128비트로 같다. 그래서 같은 코드에서 키 길이만 바꿔도 동작한다.

## AES-128과 AES-256 선택

AES-256을 기본값으로 잡는 팀이 많지만, 규정이나 감사에서 256을 명시하지 않는 한 AES-128로 충분하다.

AES-128의 키 공간은 2^128이다. 초당 10억 개 키를 시도하는 장비를 10억 대 동원해도 전수 탐색에 우주 나이를 한참 넘는 시간이 걸린다. 고전 컴퓨터로 키를 무차별 대입해서 깨는 시나리오는 현실에 없다. 256으로 올린다고 이 부분이 실질적으로 더 안전해지지는 않는다. 둘 다 못 깨는 건 마찬가지다.

256을 골라야 하는 상황은 정해져 있다.

| 상황 | 권장 |
|------|------|
| 일반 웹 서비스, API, DB 컬럼 암호화 | AES-128로 충분 |
| 금융·공공 규정에서 256 명시 | AES-256 (선택지 없음) |
| 수십 년 보관해야 하는 데이터 | AES-256 (양자 대비) |
| 처리량이 빡빡한 대용량 암호화 | AES-128 |

규정 문서에 "256-bit" 같은 문구가 박혀 있으면 논쟁할 필요 없이 256을 쓴다. 감사에서 키 길이를 따지는 경우가 실제로 있다. 반대로 그런 요구가 없는데 "더 안전할 것 같아서" 256을 기본으로 까는 건 근거가 약하다.

### 성능 차이

AES-128은 10라운드, AES-256은 14라운드를 돈다. 라운드가 40% 더 많으니 같은 데이터를 처리할 때 256이 그만큼 느리다. 벤치마크를 돌려보면 128의 처리량이 256보다 30~40% 높게 나온다.

AES-NI 같은 하드웨어 가속이 붙어도 이 차이는 그대로 남는다. AES-NI는 라운드 한 번을 `AESENC` 명령어 하나로 처리하는 방식이라, 라운드가 4개 더 많으면 블록당 명령어도 4개 더 들어간다. 가속이 라운드 수를 줄여주는 게 아니라 각 라운드를 빠르게 처리할 뿐이라, 라운드 수 차이는 처리량에 그대로 반영된다. 대용량 파일을 암호화하거나 초당 수만 건을 처리하는 구간에서 이 차이가 체감된다.

### AES-256의 안전 마진 (related-key / biclique)

직관과 다르게, AES-256이 AES-128보다 라운드 수 대비 안전 마진이 더 낮다는 분석이 있다.

2009년 Biryukov와 Khovratovich가 AES-192·AES-256에 대한 related-key 공격을 발표했다. AES-256의 키 스케줄이 단순해서, 키들 사이의 관계를 알면 라운드를 상당 부분 뚫을 수 있다는 내용이다. AES-128에는 이 공격이 통하지 않는다. 2011년 biclique 공격은 세 변종 모두 전수 탐색보다 약간 빠르게 키를 복구하지만(AES-128은 2^126.1, AES-256은 2^254.4 수준) 여전히 현실적으로 불가능한 수치다.

실무에서 알아둘 건 두 가지다. related-key 공격은 공격자가 서로 관련된 여러 키로 암호화한 결과를 확보해야 성립한다. 정상적인 키 관리에서는 키마다 독립적인 난수를 쓰므로 이 조건 자체가 만들어지지 않는다. 그래서 "256이 더 위험하다"는 말은 이론적 마진 얘기일 뿐 실제 시스템에는 영향이 없다. 다만 "256이 무조건 더 안전하다"는 통념이 항상 맞지는 않는다는 점은 알아둘 만하다.

### 양자 컴퓨팅 대비

Grover 알고리즘은 무차별 키 탐색을 제곱근으로 줄인다. 2^128 탐색이 2^64 수준이 된다는 뜻이다. 충분히 큰 양자 컴퓨터가 나오면 AES-128의 유효 강도가 64비트로 떨어진다. 64비트는 고전 컴퓨터로도 위협받는 영역이다.

AES-256은 같은 논리로 유효 강도가 128비트로 떨어지는데, 128비트는 양자 컴퓨터로도 깨기 어렵다. 그래서 지금 암호화해서 10년, 20년 뒤에도 비밀이 유지되어야 하는 데이터(의료 기록, 국가 기밀, 장기 백업)는 256으로 가는 게 맞다. 지금 못 깨더라도 공격자가 암호문을 수집해뒀다가 양자 컴퓨터가 나온 뒤 복호화하는 "harvest now, decrypt later" 시나리오 때문이다.

반대로 수명이 짧은 데이터(세션 토큰, TLS 트래픽)는 양자 컴퓨터가 실용화되기 전에 가치가 사라지므로 128로도 문제없다.

### TLS에서 AES-128-GCM이 기본인 이유

TLS 1.3의 cipher suite 목록에서 `TLS_AES_128_GCM_SHA256`이 가장 먼저 나오고, 많은 서버와 브라우저가 이걸 기본으로 고른다. 256이 아니라 128을 기본으로 두는 이유는 성능이다.

TLS는 매 연결마다 핸드셰이크와 대량의 데이터 암호화를 처리한다. 128과 256의 30~40% 성능 차이가 트래픽 규모에서 그대로 비용으로 잡힌다. 128비트가 제공하는 보안은 TLS 세션 수명(짧으면 수 분, 길어야 수 시간) 동안 깨질 수 없으므로, 256으로 올려서 얻는 실익이 없다. 세션 데이터는 양자 위협의 harvest now, decrypt later 대상도 아니다.

규정상 256이 필요한 환경에서는 `TLS_AES_256_GCM_SHA384`를 우선하도록 cipher suite 순서를 바꾸면 된다.

## 블록 암호화 과정

### 전체 흐름

```
┌─────────────────────────────────────────────────────┐
│                    평문 (128비트)                      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   AddRoundKey       │ ← 초기 라운드 키
            │  (평문 XOR 키)       │
            └──────────┬──────────┘
                       │
          ┌────────────▼────────────┐
          │   라운드 1 ~ N-1 반복     │
          │                         │
          │  ┌───────────────────┐  │
          │  │ 1. SubBytes       │  │  S-box로 바이트 치환
          │  │    (바이트 치환)    │  │  → 비선형성 확보
          │  └────────┬──────────┘  │
          │           ▼             │
          │  ┌───────────────────┐  │
          │  │ 2. ShiftRows      │  │  행별로 순환 이동
          │  │    (행 이동)       │  │  → 블록 내 확산
          │  └────────┬──────────┘  │
          │           ▼             │
          │  ┌───────────────────┐  │
          │  │ 3. MixColumns     │  │  열 단위 다항식 곱셈
          │  │    (열 혼합)       │  │  → 바이트 간 혼합
          │  └────────┬──────────┘  │
          │           ▼             │
          │  ┌───────────────────┐  │
          │  │ 4. AddRoundKey    │  │  라운드 키 XOR
          │  │    (키 결합)       │  │
          │  └────────┬──────────┘  │
          └────────────┼────────────┘
                       │
          ┌────────────▼────────────┐
          │   최종 라운드 (N번째)     │
          │                         │
          │  SubBytes → ShiftRows   │  MixColumns 없음
          │  → AddRoundKey          │
          └────────────┬────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   암호문 (128비트)    │
            └─────────────────────┘
```

최종 라운드에서 MixColumns를 빼는 이유가 있다. 복호화 과정에서 라운드 함수의 역변환 구조를 맞추기 위해서다. MixColumns가 있으면 암복호화 대칭 구조가 깨진다.

### 라운드 함수 상세

**SubBytes** — 4x4 상태 행렬의 각 바이트를 S-box 테이블로 치환한다.

```
입력 상태 행렬         S-box 치환 후
┌────┬────┬────┬────┐   ┌────┬────┬────┬────┐
│ 19 │ a0 │ 9a │ e9 │   │ d4 │ e0 │ b8 │ 1e │
│ 3d │ f4 │ c6 │ f8 │ → │ 27 │ bf │ b4 │ 41 │
│ e3 │ e2 │ 8d │ 48 │   │ 11 │ 98 │ 5d │ 52 │
│ be │ 2b │ 2a │ 08 │   │ ae │ f1 │ e5 │ 30 │
└────┴────┴────┴────┘   └────┴────┴────┴────┘
```

**ShiftRows** — 각 행을 왼쪽으로 순환 이동한다.

```
행 0: 이동 없음     [d4, e0, b8, 1e] → [d4, e0, b8, 1e]
행 1: 1칸 이동      [27, bf, b4, 41] → [bf, b4, 41, 27]
행 2: 2칸 이동      [11, 98, 5d, 52] → [5d, 52, 11, 98]
행 3: 3칸 이동      [ae, f1, e5, 30] → [30, ae, f1, e5]
```

**MixColumns** — 각 열을 GF(2^8) 위의 다항식 곱셈으로 혼합한다. 한 바이트가 바뀌면 같은 열의 4바이트 전부가 바뀐다.

**AddRoundKey** — 상태 행렬과 라운드 키를 XOR한다. 키 스케줄링으로 원래 키에서 각 라운드 키를 파생한다.

## 패딩 (Padding)

AES는 128비트(16바이트) 블록 단위로 처리한다. 평문 길이가 16바이트의 배수가 아니면 패딩을 붙여야 한다.

### PKCS5 vs PKCS7

```
평문: "Hello" (5바이트)
블록 크기: 16바이트
부족한 바이트: 11바이트

PKCS7 패딩 결과:
[H][e][l][l][o][0B][0B][0B][0B][0B][0B][0B][0B][0B][0B][0B]
                └── 부족한 바이트 수(11 = 0x0B)를 값으로 채움 ──┘

평문이 정확히 16바이트인 경우:
→ 16바이트짜리 패딩 블록을 하나 더 추가한다
[원본 16바이트][10][10][10]...[10]  (0x10 = 16)
```

| 항목 | PKCS5 | PKCS7 |
|------|-------|-------|
| 블록 크기 | 8바이트 고정 | 1~255바이트 |
| 규격 출처 | PKCS#5 (패스워드 기반) | PKCS#7 (CMS) |
| AES에서 사용 | 불가 (블록 크기 불일치) | 사용 |

Java에서 `PKCS5Padding`이라고 써도 내부적으로 PKCS7과 동일하게 동작한다. Java의 JCE가 이름만 PKCS5로 쓰고 실제로는 PKCS7 로직을 적용하기 때문이다. 헷갈리는 부분이지만, Java에서는 `AES/CBC/PKCS5Padding`으로 쓰면 된다.

### GCM 모드와 패딩

GCM 모드는 스트림 암호 방식(CTR 기반)이라 패딩이 필요 없다. Java에서 GCM을 쓸 때 `NoPadding`을 지정한다.

```
AES/GCM/NoPadding   ← 맞음
AES/GCM/PKCS5Padding ← 틀림, 예외 발생
```

## AES 운영 모드

### 모드별 동작 도식

**ECB (Electronic Codebook) — 사용 금지**

```
평문 블록1    평문 블록2    평문 블록3
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────┐
│AES 암호화│  │AES 암호화│  │AES 암호화│   ← 전부 같은 키
└────┬───┘  └────┬───┘  └────┬───┘
     │            │            │
     ▼            ▼            ▼
암호문 블록1  암호문 블록2  암호문 블록3

문제: 평문 블록1 == 평문 블록2이면 암호문도 동일
→ 이미지 암호화 시 윤곽이 그대로 보이는 현상 발생
```

ECB로 이미지를 암호화하면 원본 이미지의 패턴이 암호문에서도 보인다. 유명한 "ECB 펭귄" 예시가 이 문제를 잘 보여준다. 실무에서 ECB를 쓸 이유는 없다.

**CBC (Cipher Block Chaining)**

```
    IV          암호문 블록1     암호문 블록2
    │               │               │
    ▼               ▼               ▼
평문 블록1─→XOR  평문 블록2─→XOR  평문 블록3─→XOR
              │               │               │
              ▼               ▼               ▼
         ┌────────┐     ┌────────┐     ┌────────┐
         │AES 암호화│     │AES 암호화│     │AES 암호화│
         └────┬───┘     └────┬───┘     └────┬───┘
              │               │               │
              ▼               ▼               ▼
         암호문 블록1     암호문 블록2     암호문 블록3

특징: 이전 암호문 블록을 다음 블록의 입력에 섞음
→ 같은 평문이라도 다른 암호문 생성
→ 병렬 암호화 불가 (순차 처리)
→ 병렬 복호화는 가능
```

**GCM (Galois/Counter Mode) — 실무 권장**

```
     Nonce(96비트) + Counter
              │
              ▼
         ┌────────┐
         │AES 암호화│
         └────┬───┘
              │
              ▼
평문 블록──→XOR──→ 암호문 블록 ──┐
                                │
                                ▼
                         ┌────────────┐
              AAD ──────→│ GHASH 연산  │
                         └──────┬─────┘
                                │
                                ▼
                         인증 태그 (128비트)

AAD: Additional Authenticated Data
→ 암호화하지 않지만 무결성은 검증하는 데이터
→ HTTP 헤더 등을 AAD로 넣는 경우가 있다
```

### 모드 비교

| 모드 | IV/Nonce | 인증 | 병렬 암호화 | 병렬 복호화 | 패딩 |
|------|----------|------|------------|------------|------|
| ECB | 불필요 | 없음 | 가능 | 가능 | 필요 |
| CBC | IV 16바이트 | 없음 | 불가 | 가능 | 필요 |
| CTR | Nonce | 없음 | 가능 | 가능 | 불필요 |
| GCM | Nonce 12바이트 | 있음 | 가능 | 가능 | 불필요 |

GCM이 실무에서 표준이 된 이유: 암호화와 무결성 검증을 한 번에 처리하고, 병렬 처리가 가능해서 성능도 좋다. 별도로 HMAC을 붙일 필요가 없다.

## IV (Initialization Vector)

IV는 암호화 시 사용하는 추가 입력값이다. 같은 키로 여러 메시지를 암호화할 때 결과가 달라지도록 만든다.

- CBC: 16바이트 IV, 암호학적 난수 생성기로 생성
- GCM: 12바이트 Nonce, 카운터나 난수로 생성

IV를 재사용하면 같은 평문이 같은 암호문으로 나온다. GCM에서 Nonce를 재사용하면 인증 키가 노출되어 전체 보안이 무너진다. Nonce 재사용은 GCM에서 치명적이다.

## Salt

Salt는 패스워드 기반 키 유도(PBKDF2 등)에서 사용하는 랜덤 데이터다. 같은 패스워드라도 다른 키를 만들어낸다.

| 항목 | IV | Salt |
|------|-----|------|
| 목적 | 암호화 랜덤성 | 키 유도 랜덤성 |
| 사용처 | AES 블록 암호화 | PBKDF2, scrypt 등 |
| 크기 | 블록/모드에 따라 결정 | 16바이트 이상 |
| 공개 여부 | 공개 가능 | 공개 가능 |
| 재사용 | 금지 | 금지 |

## TypeScript 구현

### AES-GCM (권장)

```typescript
import { randomBytes, createCipheriv, createDecipheriv } from 'crypto';

const GCM_NONCE_LENGTH = 12; // 바이트
const GCM_TAG_LENGTH = 16;   // 바이트 (128비트)

// 키 생성 (256비트 = 32바이트)
function generateKey(): Buffer {
  return randomBytes(32);
}

// 암호화
function encrypt(plaintext: string, key: Buffer): Buffer {
  const nonce = randomBytes(GCM_NONCE_LENGTH);
  const cipher = createCipheriv('aes-256-gcm', key, nonce);

  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag(); // 16바이트 인증 태그

  // nonce(12) + authTag(16) + 암호문
  return Buffer.concat([nonce, authTag, encrypted]);
}

// 복호화
function decrypt(data: Buffer, key: Buffer): string {
  const nonce = data.subarray(0, GCM_NONCE_LENGTH);
  const authTag = data.subarray(GCM_NONCE_LENGTH, GCM_NONCE_LENGTH + GCM_TAG_LENGTH);
  const ciphertext = data.subarray(GCM_NONCE_LENGTH + GCM_TAG_LENGTH);

  const decipher = createDecipheriv('aes-256-gcm', key, nonce);
  decipher.setAuthTag(authTag);

  // 인증 태그 검증 실패 시 decipher.final()에서 예외 발생
  return Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8');
}

// 사용 예
const key = generateKey();
const message = '민감한 개인정보 데이터';
const encrypted = encrypt(message, key);
console.log('암호문:', encrypted.toString('base64'));
console.log('복호문:', decrypt(encrypted, key));
```

`decipher.final()`에서 인증 태그 검증에 실패하면 예외가 발생한다. 이 예외를 잡아서 "복호화 실패"로 처리해야 한다. 구체적인 오류 원인을 클라이언트에 노출하면 안 된다 (Padding Oracle Attack 참고).

### AES-128로 키 생성

위 예제의 `generateKey()`는 256비트 키를 만든다. 128비트로 바꾸려면 `randomBytes(16)`과 알고리즘 문자열(`aes-128-gcm`)만 바꾸면 된다.

```typescript
function generateKey128(): Buffer {
  return randomBytes(16); // 16바이트 = 128비트
}
```

외부에서 받은 키 바이트를 사용할 때는 길이를 미리 검증한다.

```typescript
function toKey128(keyBytes: Buffer): Buffer {
  if (keyBytes.length !== 16) {
    throw new Error(
      `AES-128 키는 16바이트여야 한다. 현재: ${keyBytes.length}바이트`
    );
  }
  return keyBytes;
}
```

길이가 안 맞는 키로 그냥 진행하면 `createCipheriv`에서 `Invalid key length` 에러가 난다. 위처럼 진입 시점에 16바이트를 검증하면 원인이 바로 드러난다.

### AES-CBC (레거시 시스템 호환)

```typescript
import { randomBytes, createCipheriv, createDecipheriv } from 'crypto';

function encryptCbc(plaintext: Buffer, key: Buffer): Buffer {
  const iv = randomBytes(16); // 16바이트 IV
  const cipher = createCipheriv('aes-256-cbc', key, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  // IV + 암호문을 합쳐서 반환
  return Buffer.concat([iv, ciphertext]);
}

function decryptCbc(encrypted: Buffer, key: Buffer): Buffer {
  const iv = encrypted.subarray(0, 16);
  const ciphertext = encrypted.subarray(16);
  const decipher = createDecipheriv('aes-256-cbc', key, iv);
  return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
}
```

새로 만드는 시스템이면 CBC 대신 GCM을 쓴다. CBC는 암호화만 하고 무결성 검증은 하지 않는다. 암호문이 변조되어도 복호화 자체는 진행되고, 잘못된 평문이 나올 수 있다.

### 패스워드 기반 키 유도 (PBKDF2)

사용자가 입력한 패스워드에서 AES 키를 만들어야 하는 경우:

```typescript
import { randomBytes, pbkdf2 } from 'crypto';
import { promisify } from 'util';

const pbkdf2Async = promisify(pbkdf2);

async function deriveKey(password: string, salt: Buffer): Promise<Buffer> {
  // OWASP 2023 권장값: PBKDF2-HMAC-SHA256, 310,000회 반복
  return pbkdf2Async(
    password,
    salt,
    310_000,  // 반복 횟수
    32,       // 키 길이 (바이트, 256비트)
    'sha256'
  );
}

function generateSalt(): Buffer {
  return randomBytes(16);
}
```

Node.js는 GC에 의한 메모리 해제가 언어 수준에서 보장되지 않는다. 패스워드 처리 후 참조를 null로 설정하면 GC 대상이 되지만, 타이밍은 보장되지 않는다. 민감한 환경에서는 `Buffer.alloc`으로 덮어쓰는 방식을 검토한다.

## NestJS에서 AES 적용

### 설정 관리

```typescript
// encryption.service.ts
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { encrypt, decrypt } from './aes-gcm'; // 위의 encrypt/decrypt 함수

@Injectable()
export class EncryptionService {
  private readonly key: Buffer;

  constructor(private readonly config: ConfigService) {
    const keyBase64 = config.getOrThrow<string>('AES_ENCRYPTION_KEY');
    const keyBytes = Buffer.from(keyBase64, 'base64');
    if (keyBytes.length !== 32) {
      throw new Error(
        `AES 키는 32바이트(256비트)여야 한다. 현재: ${keyBytes.length}바이트`
      );
    }
    this.key = keyBytes;
  }

  encryptText(plaintext: string): string {
    try {
      const encrypted = encrypt(plaintext, this.key);
      return encrypted.toString('base64');
    } catch (e) {
      throw new Error('암호화 실패');
    }
  }

  decryptText(encryptedBase64: string): string {
    try {
      const data = Buffer.from(encryptedBase64, 'base64');
      return decrypt(data, this.key);
    } catch {
      // 인증 실패 포함 — 원인을 구체적으로 노출하지 않는다
      throw new Error('복호화 실패');
    }
  }
}
```

### 주의사항

**암호화 함수 재사용 안전성**

Node.js의 `createCipheriv`/`createDecipheriv`는 호출할 때마다 새 인스턴스를 반환하므로 상태 공유 문제가 없다. 단, 같은 (key, nonce) 쌍을 절대 재사용하면 안 된다.

```typescript
// 올바른 예 — 매 호출마다 새 nonce 생성
function encryptSafe(plaintext: string, key: Buffer): Buffer {
  const nonce = randomBytes(12); // 항상 새 nonce
  const cipher = createCipheriv('aes-256-gcm', key, nonce);
  // ...
}
```

**키 로테이션**

운영 환경에서 암호화 키를 교체해야 하는 상황이 온다. 키 버전을 암호문 앞에 붙여두면 교체가 수월하다.

```typescript
// 암호문 형식: [키버전 1바이트][nonce 12바이트][authTag 16바이트][암호문]
function encryptWithVersion(plaintext: string, keyVersion: number, key: Buffer): Buffer {
  const encrypted = encrypt(plaintext, key);
  const result = Buffer.alloc(1 + encrypted.length);
  result[0] = keyVersion;
  encrypted.copy(result, 1);
  return result;
}

function decryptWithVersion(data: Buffer, getKeyByVersion: (v: number) => Buffer): string {
  const keyVersion = data[0];
  const encrypted = data.subarray(1);
  const key = getKeyByVersion(keyVersion);
  return decrypt(encrypted, key);
}
```

**TypeORM Subscriber를 이용한 컬럼 암호화**

TypeORM에서 컬럼 단위로 암호화할 때 EntitySubscriber를 활용한다.

```typescript
import { EntitySubscriberInterface, EventSubscriber, InsertEvent, LoadEvent } from 'typeorm';
import { Injectable } from '@nestjs/common';
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { EncryptionService } from './encryption.service';
import { User } from './user.entity';

@Injectable()
@EventSubscriber()
export class UserSubscriber implements EntitySubscriberInterface<User> {
  constructor(
    @InjectDataSource() readonly dataSource: DataSource,
    private readonly encryptionService: EncryptionService,
  ) {
    dataSource.subscribers.push(this);
  }

  listenTo() { return User; }

  beforeInsert(event: InsertEvent<User>) {
    if (event.entity.phoneNumber) {
      event.entity.phoneNumber = this.encryptionService.encryptText(event.entity.phoneNumber);
    }
  }

  afterLoad(entity: User) {
    if (entity.phoneNumber) {
      entity.phoneNumber = this.encryptionService.decryptText(entity.phoneNumber);
    }
  }
}
```

암호화된 컬럼은 DB에서 `LIKE` 검색이 안 된다. 검색이 필요한 필드는 별도 해시 컬럼을 만들어 인덱싱하는 방식을 쓴다.

## 실무 트러블슈팅

### Padding Oracle Attack

CBC 모드에서 발생하는 공격이다. 서버가 패딩 오류와 다른 오류를 구분해서 응답하면, 공격자가 이 차이를 이용해 암호문을 한 바이트씩 복호화할 수 있다.

```
공격 원리:

1. 공격자가 변조된 암호문을 서버에 보냄
2. 서버가 복호화 시도
3-a. 패딩이 올바르면 → "복호화 성공" 또는 "데이터 오류"
3-b. 패딩이 틀리면 → "패딩 오류"           ← 이 차이가 문제

공격자는 3-a와 3-b의 응답 차이를 이용해
암호문의 중간값(intermediate value)을 알아낸다.
중간값을 알면 평문을 역산할 수 있다.
```

**대응 방법:**

1. GCM 모드를 사용한다 — 인증 태그가 먼저 검증되므로 패딩 단계까지 가지 않는다
2. CBC를 써야 하는 경우, 복호화 실패 시 원인과 무관하게 동일한 오류를 반환한다

```typescript
// 잘못된 예 — 예외 메시지에 따라 다른 응답을 주면 오라클이 생긴다
try {
  return decrypt(ciphertext, key);
} catch (e: any) {
  if (e.message.includes('Unsupported state')) {
    res.status(400).json({ error: '잘못된 패딩' }); // 차이 노출 → 취약
  } else {
    res.status(500).json({ error: '서버 오류' });
  }
}

// 올바른 예 — 모든 복호화 실패를 동일하게 처리
try {
  return decrypt(ciphertext, key);
} catch (e) {
  // 로그에만 상세 원인 기록
  console.warn('복호화 실패:', (e as Error).message);
  res.status(400).json({ error: '복호화 실패' }); // 단일 메시지
}
```

응답 시간도 일정해야 한다. 패딩 검증 실패가 다른 오류보다 빠르게 응답하면 타이밍 공격이 가능하다.

### 키가 바뀌었을 때 기존 데이터 복호화 실패

운영 중에 키를 교체하면 기존 암호문을 복호화할 수 없다. 키 로테이션 시 기존 데이터를 새 키로 재암호화하는 배치 작업이 필요하다. 키 버전 관리를 처음부터 해두면 이 과정이 간단해진다.

### Base64 인코딩 불일치

서버와 클라이언트 간에 Base64 변형이 다른 경우가 있다. 표준 Base64와 URL-safe Base64(`+/` → `-_`)가 섞이면 복호화가 실패한다.

```typescript
// 표준 Base64
data.toString('base64');

// URL-safe Base64 (+ → -, / → _, 패딩 제거)
data.toString('base64url');

// 어느 쪽인지 API 문서에 명시하고, 양쪽이 같은 방식을 써야 한다
```

### SecureRandom 초기화 지연

Linux에서 `SecureRandom`이 `/dev/random`을 읽으면 엔트로피 부족으로 블로킹될 수 있다. 컨테이너 환경에서 서버 기동 시간이 느려지는 원인이 되기도 한다.

```bash
# JVM 옵션으로 /dev/urandom 사용 (실무에서 일반적)
-Djava.security.egd=file:/dev/./urandom
```

`/dev/urandom`은 블로킹하지 않으면서도 암호학적으로 충분히 안전하다. `/dev/random`과의 보안 차이는 현대 Linux 커널에서 사실상 없다.

## Node.js 구현

```javascript
const crypto = require('crypto');

class AesGcmCrypto {
    constructor(key) {
        // key: 32바이트 Buffer
        this.key = Buffer.isBuffer(key) ? key : Buffer.from(key, 'hex');
    }

    encrypt(plaintext) {
        const nonce = crypto.randomBytes(12);
        const cipher = crypto.createCipheriv('aes-256-gcm', this.key, nonce);

        let encrypted = cipher.update(plaintext, 'utf8');
        encrypted = Buffer.concat([encrypted, cipher.final()]);
        const authTag = cipher.getAuthTag();

        // nonce(12) + authTag(16) + ciphertext
        return Buffer.concat([nonce, authTag, encrypted]);
    }

    decrypt(data) {
        const buf = Buffer.isBuffer(data) ? data : Buffer.from(data, 'base64');

        const nonce = buf.subarray(0, 12);
        const authTag = buf.subarray(12, 28);
        const ciphertext = buf.subarray(28);

        const decipher = crypto.createDecipheriv('aes-256-gcm', this.key, nonce);
        decipher.setAuthTag(authTag);

        let decrypted = decipher.update(ciphertext);
        decrypted = Buffer.concat([decrypted, decipher.final()]);
        return decrypted.toString('utf8');
    }
}

const key = crypto.randomBytes(32);
const aes = new AesGcmCrypto(key);

const encrypted = aes.encrypt('Hello, AES-GCM!');
console.log('암호문:', encrypted.toString('base64'));
console.log('복호문:', aes.decrypt(encrypted));
```

128비트로 바꾸려면 알고리즘 문자열을 `aes-128-gcm`으로, 키를 16바이트로 바꾼다. 위 클래스에서 `aes-256-gcm`을 쓴 두 곳(`createCipheriv`, `createDecipheriv`)과 키 생성 부분만 손대면 된다.

```javascript
const key = crypto.randomBytes(16); // 16바이트 = 128비트
const cipher = crypto.createCipheriv('aes-128-gcm', key, nonce);
```

알고리즘 문자열과 키 길이가 안 맞으면 `createCipheriv`에서 `Invalid key length` 에러가 난다. `aes-128-gcm`에 32바이트 키를 넘기는 실수가 흔하다. Node는 문자열로 키 길이를 지정하지 않으므로, 키 버퍼 길이가 알고리즘과 일치하는지 직접 맞춰야 한다.

## 보안 고려사항

### 키 관리

| 방식 | 적합한 상황 | 주의점 |
|------|------------|--------|
| 환경 변수 | 개발/소규모 서비스 | 프로세스 목록에서 노출 가능 |
| AWS KMS / GCP KMS | 클라우드 운영 | API 호출 비용, 레이턴시 |
| HashiCorp Vault | 온프레미스/멀티클라우드 | 운영 복잡도 |
| HSM | 금융/규제 환경 | 비용 높음 |

키를 코드에 하드코딩하면 Git 히스토리에 남는다. 한번 커밋된 키는 히스토리를 정리하더라도 이미 노출된 것으로 간주하고 교체해야 한다.

### AES vs 다른 암호화

| 알고리즘 | 유형 | 특징 | 용도 |
|---------|------|------|------|
| AES | 대칭키 | 빠름, 하드웨어 가속(AES-NI) | 데이터 암호화 |
| RSA | 비대칭키 | 느림, 키 크기 큼 | 키 교환, 서명 |
| ChaCha20-Poly1305 | 대칭키 | AES-NI 없는 환경에서 빠름 | 모바일, TLS |

실무에서는 대용량 데이터를 AES로 암호화하고, AES 키를 RSA로 암호화하는 하이브리드 방식을 쓴다. TLS가 이 방식으로 동작한다.

## 참고

- NIST FIPS 197 — AES Specification
- RFC 5116 — An Interface and Algorithms for Authenticated Encryption
- RFC 3602 — The AES-CBC Cipher Algorithm
- OWASP Cryptographic Storage Cheat Sheet
