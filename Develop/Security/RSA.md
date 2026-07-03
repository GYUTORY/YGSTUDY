---
title: RSA
tags: [security, rsa, encryption, digital-signature]
updated: 2026-03-30
---

# RSA (Rivest-Shamir-Adleman)

## 개요

RSA는 공개 키 암호화 알고리즘이다. 안전한 데이터 전송과 디지털 서명에 사용한다. 1977년 Ron Rivest, Adi Shamir, Leonard Adleman이 개발했다.

비대칭 키 암호화 방식으로, 공개 키와 개인 키 쌍을 사용한다. 소인수분해의 수학적 난이도에 보안이 기반한다.

## 동작 원리

### 비대칭 암호화

- 공개 키(Public Key): 데이터를 암호화하는 데 사용
- 개인 키(Private Key): 데이터를 복호화하는 데 사용

누구나 공개 키로 데이터를 암호화할 수 있지만, 개인 키 없이는 복호화할 수 없다.

### 키 생성 과정

1. 두 개의 큰 소수 p와 q를 선택
2. 두 소수의 곱 n = p × q를 계산
3. 오일러 함수 계산: φ(n) = (p-1) × (q-1)
4. 공개 키(e)와 개인 키(d) 계산

**키 생성 예제:**
```python
# 두 개의 큰 소수 선택
p = 61
q = 53

# 오일러 함수 계산
phi = (p - 1) * (q - 1)  # 3120

# n 계산
n = p * q  # 3233

# 공개 키 e 선택 (1 < e < phi, gcd(e, phi) == 1)
e = 17

# 개인 키 d 계산 — 확장 유클리드 알고리즘 사용
# d는 e의 모듈러 역원이다: (e * d) mod phi == 1
def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def mod_inverse(e, phi):
    gcd, x, _ = extended_gcd(e % phi, phi)
    if gcd != 1:
        raise ValueError("모듈러 역원이 존재하지 않는다")
    return x % phi

d = mod_inverse(e, phi)  # 2753

print(f"공개 키: (n={n}, e={e})")
print(f"개인 키: (n={n}, d={d})")
```

> 위 예제는 원리를 설명하기 위한 코드다. 실무에서는 반드시 검증된 라이브러리(OpenSSL, JCA 등)를 사용한다. 직접 구현한 RSA는 사이드 채널 공격에 취약하다.

### 암호화 및 복호화

**암호화 공식:**
```
C = M^e mod n
```

**복호화 공식:**
```
M = C^d mod n
```

**예제:**
```python
# 메시지 암호화 — pow()의 세 번째 인자로 모듈러 거듭제곱 수행
M = 65
C = pow(M, e, n)

# 메시지 복호화
decrypted_M = pow(C, d, n)

print(f"원본 메시지: {M}")
print(f"암호화된 메시지: {C}")
print(f"복호화된 메시지: {decrypted_M}")
```

## PKCS 패딩

RSA로 평문을 그대로 암호화하면 동일한 평문에 대해 항상 같은 암호문이 나온다. 이걸 결정적(deterministic) 암호화라고 하는데, 보안상 심각한 문제다. 패딩은 평문에 랜덤 데이터를 추가해서 이 문제를 해결한다.

### PKCS#1 v1.5

RSA 초기부터 사용된 패딩 방식이다. 구조가 단순하다.

```
0x00 | 0x02 | [랜덤 바이트 (최소 8바이트)] | 0x00 | [평문]
```

랜덤 바이트가 들어가므로 같은 평문이라도 매번 다른 암호문이 나온다. 문제는 이 패딩 구조가 복호화 시 검증 과정에서 정보를 노출할 수 있다는 것이다(패딩 오라클 공격, 아래에서 설명).

### OAEP (Optimal Asymmetric Encryption Padding)

PKCS#1 v2에서 도입된 패딩이다. 내부적으로 해시 함수와 MGF(Mask Generation Function)를 사용해서 평문을 변환한다.

```
패딩 = OAEP(평문, label, seed)
    → 해시, MGF를 거쳐 복호화 시 구조적 정보 노출을 방지
```

OAEP는 패딩 오라클 공격에 대한 수학적 증명이 있다. 새로 만드는 시스템에서는 반드시 OAEP를 사용한다.

### 어떤 패딩을 쓸 것인가

| 항목 | PKCS#1 v1.5 | OAEP |
|------|-------------|------|
| 보안성 | 패딩 오라클 취약 | 증명된 안전성 |
| 호환성 | 레거시 시스템 대부분 지원 | Java 5+, OpenSSL 0.9.8+ |
| 암호화 가능한 최대 크기 | 키 크기 - 11바이트 | 키 크기 - 2*해시크기 - 2바이트 |
| 신규 시스템 | 사용 금지 | 사용해야 함 |

2048비트 RSA 키(256바이트) 기준으로, OAEP(SHA-256)는 최대 190바이트까지 암호화할 수 있다. 그래서 RSA로 직접 대량 데이터를 암호화하지 않고, AES 키(32바이트)만 RSA로 암호화하는 하이브리드 방식을 쓴다.

## PEM / DER 키 포맷

### DER (Distinguished Encoding Rules)

ASN.1 구조를 바이너리로 인코딩한 형식이다. 사람이 읽을 수 없다. Java의 `KeyFactory`가 기본으로 처리하는 포맷이다.

### PEM (Privacy-Enhanced Mail)

DER 바이너리를 Base64로 인코딩하고, 헤더/푸터를 붙인 텍스트 형식이다.

```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA2a2rwplBQL...
(Base64 인코딩된 DER 데이터)
-----END RSA PRIVATE KEY-----
```

PEM 파일에서 자주 보는 헤더 종류:

| 헤더 | 설명 |
|------|------|
| `BEGIN RSA PRIVATE KEY` | PKCS#1 형식의 RSA 개인 키 |
| `BEGIN PRIVATE KEY` | PKCS#8 형식의 개인 키 (알고리즘 정보 포함) |
| `BEGIN PUBLIC KEY` | X.509 SubjectPublicKeyInfo 형식 |
| `BEGIN CERTIFICATE` | X.509 인증서 |

PKCS#1과 PKCS#8의 차이: PKCS#1은 RSA 전용이고, PKCS#8은 알고리즘 식별자(OID)를 포함해서 RSA/EC/DSA 등 여러 알고리즘의 키를 같은 구조로 담을 수 있다. 최근 라이브러리는 대부분 PKCS#8을 기본으로 사용한다.

### OpenSSL CLI 사용법

**키 생성:**
```bash
# RSA 2048비트 개인 키 생성 (PKCS#8, PEM 형식)
openssl genpkey -algorithm RSA -out private.pem -pkeyopt rsa_keygen_bits:2048

# 개인 키에서 공개 키 추출
openssl pkey -in private.pem -pubout -out public.pem
```

> `openssl genrsa`는 PKCS#1 형식으로 생성한다. `genpkey`가 더 범용적이고 권장되는 명령어다.

**키 정보 확인:**
```bash
# 개인 키 정보 확인 (모듈러스, 지수 등)
openssl pkey -in private.pem -text -noout

# 공개 키 정보 확인
openssl pkey -in public.pem -pubin -text -noout

# PEM → DER 변환
openssl pkey -in private.pem -outform DER -out private.der

# DER → PEM 변환
openssl pkey -in private.der -inform DER -out private.pem
```

**암호화/복호화:**
```bash
# OAEP 패딩으로 파일 암호화
openssl pkeyutl -encrypt -inkey public.pem -pubin \
  -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
  -in plaintext.txt -out encrypted.bin

# 복호화
openssl pkeyutl -decrypt -inkey private.pem \
  -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
  -in encrypted.bin -out decrypted.txt
```

**디지털 서명:**
```bash
# SHA-256 해시 후 PSS 패딩으로 서명
openssl dgst -sha256 -sigopt rsa_padding_mode:pss \
  -sign private.pem -out signature.bin data.txt

# 서명 검증
openssl dgst -sha256 -sigopt rsa_padding_mode:pss \
  -verify public.pem -signature signature.bin data.txt
```

## 구현 예제

### Node.js

```javascript
const crypto = require('crypto');

// RSA 키 쌍 생성
const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
  modulusLength: 2048,
  publicKeyEncoding: {
    type: 'spki',
    format: 'pem'
  },
  privateKeyEncoding: {
    type: 'pkcs8',
    format: 'pem'
  }
});

// OAEP 패딩으로 암호화
const message = 'Hello, RSA!';
const encrypted = crypto.publicEncrypt(
  {
    key: publicKey,
    padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
    oaepHash: 'sha256'
  },
  Buffer.from(message)
);

// 복호화
const decrypted = crypto.privateDecrypt(
  {
    key: privateKey,
    padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
    oaepHash: 'sha256'
  },
  encrypted
);
console.log(decrypted.toString()); // 'Hello, RSA!'
```

### Java (JCA)

```java
import javax.crypto.Cipher;
import java.security.*;
import java.security.spec.*;
import java.util.Base64;

public class RsaExample {

    // 키 쌍 생성
    public static KeyPair generateKeyPair() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        return generator.generateKeyPair();
    }

    // OAEP 패딩으로 암호화
    public static byte[] encrypt(PublicKey publicKey, byte[] plaintext) throws Exception {
        Cipher cipher = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, publicKey);
        return cipher.doFinal(plaintext);
    }

    // 복호화
    public static byte[] decrypt(PrivateKey privateKey, byte[] ciphertext) throws Exception {
        Cipher cipher = Cipher.getInstance("RSA/ECB/OAEPWithSHA-256AndMGF1Padding");
        cipher.init(Cipher.DECRYPT_MODE, privateKey);
        return cipher.doFinal(ciphertext);
    }

    public static void main(String[] args) throws Exception {
        KeyPair keyPair = generateKeyPair();

        String message = "Hello, RSA!";
        byte[] encrypted = encrypt(keyPair.getPublic(), message.getBytes());
        byte[] decrypted = decrypt(keyPair.getPrivate(), encrypted);

        System.out.println("암호문 (Base64): " + Base64.getEncoder().encodeToString(encrypted));
        System.out.println("복호문: " + new String(decrypted));
    }
}
```

JCA에서 `RSA/ECB/OAEPWithSHA-256AndMGF1Padding`을 지정하면 OAEP 패딩이 적용된다. "ECB"라고 적혀 있지만, RSA는 블록 암호가 아니라서 실제로 ECB 모드가 동작하지는 않는다. JCA의 Cipher 문자열 규칙 때문에 저렇게 적는 것이다.

주의할 점: `Cipher.getInstance("RSA")`만 적으면 프로바이더에 따라 PKCS#1 v1.5 패딩이 적용될 수 있다. 패딩을 명시적으로 지정해야 한다.

#### PEM 키 파일 로드 (Java)

외부에서 생성한 PEM 키를 Java에서 로드하는 경우가 많다.

```java
import java.nio.file.*;
import java.security.*;
import java.security.spec.*;
import java.util.Base64;

public class PemKeyLoader {

    // PEM 형식의 개인 키 로드 (PKCS#8)
    public static PrivateKey loadPrivateKey(String pemPath) throws Exception {
        String pem = Files.readString(Path.of(pemPath));
        String base64 = pem
            .replace("-----BEGIN PRIVATE KEY-----", "")
            .replace("-----END PRIVATE KEY-----", "")
            .replaceAll("\\s", "");

        byte[] der = Base64.getDecoder().decode(base64);
        PKCS8EncodedKeySpec spec = new PKCS8EncodedKeySpec(der);
        return KeyFactory.getInstance("RSA").generatePrivate(spec);
    }

    // PEM 형식의 공개 키 로드
    public static PublicKey loadPublicKey(String pemPath) throws Exception {
        String pem = Files.readString(Path.of(pemPath));
        String base64 = pem
            .replace("-----BEGIN PUBLIC KEY-----", "")
            .replace("-----END PUBLIC KEY-----", "")
            .replaceAll("\\s", "");

        byte[] der = Base64.getDecoder().decode(base64);
        X509EncodedKeySpec spec = new X509EncodedKeySpec(der);
        return KeyFactory.getInstance("RSA").generatePublic(spec);
    }
}
```

`BEGIN RSA PRIVATE KEY` (PKCS#1 형식) PEM을 Java에서 로드하려면 BouncyCastle 같은 추가 라이브러리가 필요하다. OpenSSL로 PKCS#8로 변환하는 게 간단하다:

```bash
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt \
  -in pkcs1_private.pem -out pkcs8_private.pem
```

## 디지털 서명

RSA의 또 다른 핵심 용도는 디지털 서명이다. 암호화와 반대 방향으로 키를 사용한다.

- 서명: 개인 키로 메시지 해시에 서명
- 검증: 공개 키로 서명을 검증

### 서명 과정

```
1. 원본 데이터의 해시를 계산한다 (SHA-256 등)
2. 해시 값을 개인 키로 암호화한다 → 이게 서명이다
3. 원본 데이터 + 서명을 함께 전송한다
4. 수신자는 공개 키로 서명을 복호화해서 해시를 꺼낸다
5. 원본 데이터의 해시를 직접 계산해서 비교한다
6. 두 해시가 같으면 위변조가 없다는 의미다
```

### 서명 패딩: PKCS#1 v1.5 vs PSS

암호화에 OAEP가 있다면, 서명에는 PSS(Probabilistic Signature Scheme)가 있다. PSS는 랜덤 salt를 사용해서 같은 메시지에 대해 매번 다른 서명이 나온다.

| 항목 | PKCS#1 v1.5 서명 | PSS |
|------|------------------|-----|
| 결정적 여부 | 결정적 (같은 입력 → 같은 서명) | 확률적 (매번 다른 서명) |
| 보안 증명 | 없음 | 있음 |
| 호환성 | 대부분의 레거시 시스템 | TLS 1.3에서 필수 |

### Java 서명 구현

```java
import java.security.*;

public class RsaSignature {

    // PSS 패딩으로 서명
    public static byte[] sign(PrivateKey privateKey, byte[] data) throws Exception {
        Signature signature = Signature.getInstance("RSASSA-PSS");
        signature.setParameter(new PSSParameterSpec(
            "SHA-256",           // 해시 알고리즘
            "MGF1",              // MGF
            MGF1ParameterSpec.SHA256,  // MGF 해시
            32,                  // salt 길이 (해시 출력 크기와 동일하게)
            1                    // trailer field
        ));
        signature.initSign(privateKey);
        signature.update(data);
        return signature.sign();
    }

    // 서명 검증
    public static boolean verify(PublicKey publicKey, byte[] data, byte[] sig)
            throws Exception {
        Signature signature = Signature.getInstance("RSASSA-PSS");
        signature.setParameter(new PSSParameterSpec(
            "SHA-256", "MGF1", MGF1ParameterSpec.SHA256, 32, 1
        ));
        signature.initVerify(publicKey);
        signature.update(data);
        return signature.verify(sig);
    }

    public static void main(String[] args) throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        KeyPair keyPair = generator.generateKeyPair();

        byte[] data = "서명할 데이터".getBytes();
        byte[] sig = sign(keyPair.getPrivate(), data);

        boolean valid = verify(keyPair.getPublic(), data, sig);
        System.out.println("서명 검증: " + valid);  // true
    }
}
```

### Node.js 서명 구현

```javascript
const crypto = require('crypto');

// 서명 생성
const sign = crypto.createSign('RSA-SHA256');
sign.update('서명할 데이터');
const signature = sign.sign(privateKey);

// 서명 검증
const verify = crypto.createVerify('RSA-SHA256');
verify.update('서명할 데이터');
const isValid = verify.verify(publicKey, signature);
console.log('서명 검증:', isValid);  // true
```

## 인증서(X.509)와 RSA

SSL/TLS에서 RSA를 쓸 때, 공개 키를 그냥 전달하면 "이 공개 키가 정말 이 서버의 것인가?"를 확인할 방법이 없다. 중간자(MITM)가 자기 공개 키를 대신 보낼 수 있다.

X.509 인증서는 이 문제를 해결한다. 인증서 안에는 다음이 들어 있다:

- 소유자 정보 (도메인, 조직 등)
- 소유자의 공개 키
- 인증 기관(CA)의 디지털 서명

CA가 "이 공개 키는 이 도메인의 것이 맞다"고 서명해준 것이다. 브라우저는 CA의 공개 키를 미리 가지고 있으므로, 인증서의 서명을 검증할 수 있다.

### 인증서 체인

```
Root CA (브라우저에 내장)
  └── Intermediate CA (Root CA가 서명)
        └── 서버 인증서 (Intermediate CA가 서명)
```

서버 인증서를 직접 Root CA가 서명하지 않는 이유: Root CA의 개인 키는 오프라인에 보관하고, 일상적인 서명은 Intermediate CA가 처리한다. Intermediate CA가 유출되면 그것만 폐기(revoke)하면 된다.

### OpenSSL로 인증서 확인

```bash
# 서버의 인증서 체인 확인
openssl s_client -connect example.com:443 -showcerts

# 인증서 내용 확인
openssl x509 -in cert.pem -text -noout

# 인증서의 공개 키 추출
openssl x509 -in cert.pem -pubkey -noout > pubkey.pem

# 인증서 만료일 확인
openssl x509 -in cert.pem -enddate -noout
```

### 자체 서명 인증서 생성 (개발용)

```bash
# 개인 키 + 자체 서명 인증서 한 번에 생성
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem \
  -days 365 -nodes -subj "/CN=localhost"
```

`-nodes`는 개인 키를 암호화하지 않겠다는 의미다. 운영 환경에서는 개인 키에 반드시 암호를 걸어야 한다.

## 보안 위협과 트러블슈팅

### 패딩 오라클 공격 (Bleichenbacher's Attack)

1998년 Bleichenbacher가 발표한 공격이다. PKCS#1 v1.5 패딩을 사용하는 서버에서 복호화 실패 시 "패딩이 잘못됨" vs "다른 오류" 같은 서로 다른 에러를 반환하면, 공격자가 이 차이를 이용해서 암호문을 복호화할 수 있다.

**공격 원리:**

1. 공격자가 변조된 암호문을 서버에 보낸다
2. 서버가 복호화를 시도하고, 패딩 검증 결과에 따라 다른 에러를 반환한다
3. 이 에러 차이(오라클)를 수천~수백만 번 반복해서, 수학적으로 평문을 역산한다

**방어 방법:**

- 신규 시스템에서는 OAEP 패딩만 사용한다
- 레거시 시스템에서 PKCS#1 v1.5를 써야 하면, 패딩 실패와 다른 실패를 구분할 수 없게 만든다. 복호화 실패 시 랜덤 값을 반환하는 방식을 쓰기도 한다
- 에러 메시지에 패딩 관련 정보를 노출하지 않는다

### 키 사이즈 마이그레이션

1024비트 RSA는 이미 안전하지 않다. NIST는 2013년부터 1024비트 사용을 금지했다. 2048비트로 마이그레이션해야 하는 경우 실무에서 겪는 문제들:

**레거시 클라이언트 호환성:**
오래된 하드웨어(결제 단말기, IoT 디바이스 등)가 2048비트를 지원하지 않는 경우가 있다. 이때는 이중 인증서를 운영하거나, 해당 디바이스를 먼저 업그레이드해야 한다.

**성능 영향:**
키 크기가 커지면 연산이 느려진다. 2048비트는 1024비트 대비 서명 생성이 약 4~8배 느리다. TLS 핸드셰이크에서 체감되는 수준은 아니지만, 초당 수만 건의 TLS 연결을 처리하는 서버에서는 고려해야 한다.

**마이그레이션 순서:**
서버 키를 먼저 바꾸고, 클라이언트 인증서를 교체하고, 마지막으로 CA 인증서를 교체한다. 한꺼번에 바꾸면 장애 범위를 특정하기 어렵다.

### 키 저장

개인 키가 유출되면 해당 키로 암호화된 모든 데이터가 노출된다. 실무에서 키를 저장하는 방법:

**파일 시스템:**
```bash
# 키 파일 권한 설정 — 소유자만 읽기 가능
chmod 600 private.pem

# 키 파일에 암호 설정
openssl pkey -in private.pem -aes256 -out private_encrypted.pem
```

파일 시스템에 키를 그냥 두는 건 개발/테스트 환경에서만 해야 한다.

**운영 환경에서의 키 저장:**

- HSM(Hardware Security Module): 키가 하드웨어 내부에서만 존재하고, 외부로 절대 나오지 않는다. 금융/결제 시스템에서 사용한다
- AWS KMS, GCP Cloud KMS: 클라우드 관리형 HSM이다. API로 암호화/서명 요청만 하고, 키 자체에는 접근하지 않는다
- HashiCorp Vault: 키를 중앙에서 관리하고, 접근 로그를 남긴다

**Java KeyStore:**
```java
// PKCS12 키스토어에 개인 키와 인증서 저장
KeyStore ks = KeyStore.getInstance("PKCS12");
ks.load(null, null);
ks.setKeyEntry("mykey", privateKey, "password".toCharArray(),
    new Certificate[]{certificate});
ks.store(new FileOutputStream("keystore.p12"), "password".toCharArray());
```

JKS(Java KeyStore) 포맷은 Java 전용이다. PKCS12는 표준 포맷이라 OpenSSL 등 다른 도구와 호환된다. Java 9부터 PKCS12가 기본 키스토어 타입이다.

### 기타 보안 위협

**소인수분해 공격:**
큰 숫자를 소인수분해해 개인 키를 계산한다. 2048비트 이상의 키를 사용하면 현재 기술로는 불가능하다.

**타이밍 공격:**
RSA 연산 시간 차이를 측정해서 키를 추측한다. 검증된 라이브러리는 상수 시간(constant-time) 연산을 구현하고 있다.

**양자 컴퓨팅:**
Shor 알고리즘으로 소인수분해를 다항 시간에 풀 수 있다. 현재 양자 컴퓨터는 RSA를 위협할 수준에 도달하지 않았지만, NIST는 2024년에 양자 내성 암호화 표준(ML-KEM 등)을 발표했다. 장기적으로 RSA에서 이관이 필요하다.

## RSA vs AES

| 항목 | RSA | AES |
|------|-----|-----|
| 방식 | 비대칭 (공개키) | 대칭 |
| 속도 | 느림 | 빠름 |
| 용도 | 키 교환, 디지털 서명 | 데이터 암호화 |
| 키 관리 | 공개키 배포 쉬움 | 키 공유 어려움 |

### 하이브리드 암호화

실무에서는 RSA와 AES를 함께 사용한다.

1. RSA로 AES 키를 암호화해 전송
2. AES로 실제 데이터를 암호화
3. RSA의 키 교환 + AES의 속도

TLS가 정확히 이 방식이다. TLS 핸드셰이크에서 RSA(또는 ECDHE)로 대칭 키를 교환하고, 이후 데이터는 AES로 암호화한다.

```javascript
const crypto = require('crypto');

// 1. AES 키 생성
const aesKey = crypto.randomBytes(32);
const iv = crypto.randomBytes(16);

// 2. RSA-OAEP로 AES 키 암호화
const encryptedKey = crypto.publicEncrypt(
  { key: publicKey, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING },
  aesKey
);

// 3. AES로 데이터 암호화
const cipher = crypto.createCipheriv('aes-256-cbc', aesKey, iv);
let encrypted = cipher.update(data, 'utf8', 'hex');
encrypted += cipher.final('hex');

// 전송: encryptedKey + iv + encrypted
```

## 키 길이 권장사항

| 키 길이 | 보안 수준 | 비고 |
|---------|-----------|------|
| 1024비트 | 안전하지 않음 | 2013년부터 NIST 금지 |
| 2048비트 | 2030년까지 안전 | 현재 표준 |
| 3072비트 | 2030년 이후 | 128비트 대칭키 수준 |
| 4096비트 | 장기 보안 | 성능 저하 고려 |

일반적인 웹 서비스는 2048비트면 충분하다. 10년 이상 보존해야 하는 데이터가 있다면 3072비트 이상을 고려한다.

## 참고

- RFC 8017 - PKCS #1: RSA Cryptography Specifications
- NIST SP 800-57 - Key Management Recommendations
- NIST FIPS 186-5 - Digital Signature Standard
- [Node.js Crypto Documentation](https://nodejs.org/api/crypto.html)
- [Java Security Standard Algorithm Names](https://docs.oracle.com/en/java/javase/17/docs/specs/security/standard-names.html)
