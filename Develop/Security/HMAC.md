---
title: HMAC (Hash-based Message Authentication Code)
tags: [security, hmac, mac, hash, signature, sha256, timing-attack, key-rotation]
updated: 2026-06-30
---

# HMAC

HMAC은 해시 함수에 비밀 키를 끼워 넣어 "이 메시지를 키를 아는 쪽이 보냈고, 중간에 변조되지 않았다"를 증명하는 메시지 인증 코드다. JWT의 HS256, AWS 요청 서명, 웹훅 서명, 쿠키 서명 같은 데서 매일 돌아간다. 평소엔 라이브러리가 알아서 해주니 신경 안 쓰지만, 직접 검증 로직을 짜는 순간 키 길이, 인코딩, 비교 방식에서 사고가 난다.

여기서는 HMAC이 왜 단순 키 프리픽스보다 안전한지, Java `Mac`이나 Python `hmac`을 직접 쓸 때 어디서 깨지는지를 정리한다. 웹훅 서명 흐름 전체는 [Webhook_Security.md](Webhook_Security.md)에, SHA-2 길이 확장 공격의 내부 동작은 [SHA.md](SHA.md)에 따로 있다.

---

## 단순 키 프리픽스가 왜 안 되는가

메시지 인증을 처음 짤 때 가장 직관적인 방식은 키와 메시지를 이어 붙여 해시하는 것이다.

```
MAC = SHA256(key || message)
```

키를 모르면 같은 해시를 못 만들 테니 인증이 될 것 같다. 그런데 SHA-256은 Merkle-Damgård 구조라 이 방식이 길이 확장 공격(Length Extension Attack)에 뚫린다.

Merkle-Damgård 해시는 메시지를 블록 단위로 처리하면서 내부 상태를 갱신한다. 마지막 블록까지 처리한 뒤의 내부 상태가 곧 최종 해시값이다. 문제는 이 최종 해시값이 그대로 "중간 상태"라는 것이다. 공격자가 `SHA256(key || message)` 값을 알면, 그 값을 내부 상태로 삼아 해시 계산을 이어붙일 수 있다. 키를 모르는데도 말이다.

실제로 이렇게 당한다. 어떤 API가 `?user=admin&action=read` 같은 쿼리에 `SHA256(secret || query)`를 붙여 보내고 서버가 검증한다고 하자. 공격자는 `secret`을 모르지만 정상 요청 하나를 가로채면 그 MAC을 안다. 여기에 패딩과 `&action=delete`를 이어붙인 새 메시지를 만들고, 가로챈 MAC을 시작 상태로 삼아 새 MAC을 계산한다. `secret`의 길이만 맞으면(보통 짧으니 몇 번 시도하면 맞는다) 서버는 위조된 `delete` 요청을 정상으로 받아들인다. hashpump 같은 도구로 키 없이 자동화된다.

HMAC은 이 구조적 약점을 막는다. 핵심은 해시를 두 번 중첩하는 것이다.

```
HMAC(key, msg) = hash( (key ⊕ opad) || hash( (key ⊕ ipad) || msg ) )
```

안쪽 해시 `hash((key ⊕ ipad) || msg)`의 결과는 다시 바깥 해시의 입력으로 들어간다. 공격자가 손에 쥐는 최종 HMAC 값은 바깥 해시의 출력이다. 이 값은 안쪽 해시의 중간 상태가 아니라, 안쪽 결과를 한 번 더 키와 섞어 해시한 값이다. 그래서 이 출력을 시작 상태로 삼아 메시지를 이어붙여도 키를 모르면 바깥 해시를 다시 못 돈다. 길이 확장이 통하지 않는다.

길이 확장 공격이 Merkle-Damgård 내부에서 정확히 어떻게 상태를 복원하는지는 [SHA.md](SHA.md)에 더 자세히 있다.

### ipad와 opad가 따로 있는 이유

`ipad`는 바이트 `0x36`을 블록 크기만큼 반복한 값이고, `opad`는 `0x5c`를 반복한 값이다. 이 두 패드를 키와 XOR하면 안쪽 해시와 바깥 해시가 서로 다른 키로 동작하는 효과가 난다. 같은 키 하나를 두 군데에 쓰지만 실질적으로는 키가 둘로 갈라진다.

만약 안팎을 같은 패드로 처리하면 두 해시가 같은 입력 가공을 거치게 돼서 중첩의 의미가 약해진다. `0x36`과 `0x5c`는 비트 패턴이 충분히 다르도록 고른 상수다. 값 자체에 깊은 의미는 없고, 두 패드가 서로 충분히 다르기만 하면 된다. 직접 구현할 일은 없지만(라이브러리가 다 처리한다) 왜 키를 두 번 섞는지는 알아야 디버깅할 때 헷갈리지 않는다.

---

## 키 길이가 블록 크기에 맞춰 조정된다

직접 키를 만들 때 자주 놓치는 부분이다. HMAC은 키를 해시의 블록 크기에 맞춰 정규화한 뒤 ipad/opad와 XOR한다. SHA-256의 블록 크기는 64바이트(512비트)다. 출력 크기 32바이트와 헷갈리면 안 된다.

키 길이에 따라 처리가 갈린다.

- 키가 블록 크기(64바이트)보다 **길면** 먼저 해시해서 32바이트로 줄인 뒤 다시 64바이트로 0 패딩한다.
- 키가 블록 크기보다 **짧으면** 오른쪽에 0을 채워 64바이트로 만든다.
- 정확히 64바이트면 그대로 쓴다.

여기서 실무적으로 걸리는 게 두 가지다.

첫째, 키가 너무 길면 보안이 더 강해지는 게 아니라 그냥 한 번 해시된 32바이트로 축약된다. 200바이트짜리 키를 넣어도 실효 엔트로피는 SHA-256 출력인 256비트가 상한이다. 키를 길게 만든다고 강해지지 않는다.

둘째, 짧은 키가 0 패딩된다는 점 때문에 미묘한 충돌이 생길 수 있다. 키를 hex 문자열로 들고 다니다가 어디선 raw 바이트로, 어디선 hex 디코딩해서 쓰면 같은 키인데 다른 HMAC이 나온다. 키는 raw 바이트로 일관되게 다뤄야 한다.

```java
// 키를 raw 바이트로 일관되게 — 권장 키 길이는 출력과 같은 32바이트 이상
byte[] keyBytes = secretKey.getBytes(StandardCharsets.UTF_8);
SecretKeySpec keySpec = new SecretKeySpec(keyBytes, "HmacSHA256");

Mac mac = Mac.getInstance("HmacSHA256");
mac.init(keySpec);
byte[] result = mac.doFinal(message.getBytes(StandardCharsets.UTF_8));
```

키 길이는 해시 출력 크기와 같은 32바이트(256비트) 이상을 쓴다. 16바이트 미만으로 떨어지면 0 패딩 영역이 커져서 키 공간이 줄어든다.

---

## Java Mac 객체는 상태를 가진다

`Mac.getInstance`로 만든 객체는 stateful하다. 이걸 모르고 싱글톤으로 캐싱했다가 동시성 버그를 만드는 경우가 흔하다.

`mac.update()`로 데이터를 누적하다가 `mac.doFinal()`을 호출하면 그동안 쌓인 데이터로 MAC을 뽑고 객체가 초기 상태(init 직후)로 리셋된다. 그래서 같은 `Mac` 인스턴스로 다음 메시지를 처리하려면 `doFinal` 이후 별도 `init` 없이 바로 `update`/`doFinal`을 다시 호출할 수 있다. 키는 유지된다. 문제는 이 "상태"가 인스턴스 하나에 묶여 있다는 점이다.

```java
// 위험: Mac 인스턴스를 필드로 두고 여러 스레드가 공유
public class SignatureService {
    private final Mac mac; // 공유하면 안 됨

    public SignatureService(byte[] key) throws Exception {
        mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
    }

    public byte[] sign(byte[] msg) {
        return mac.doFinal(msg); // 두 스레드가 동시에 들어오면 update 상태가 섞인다
    }
}
```

스레드 A가 `update`로 데이터를 쌓는 중에 스레드 B가 끼어들면 내부 버퍼가 엉켜 둘 다 틀린 MAC을 만든다. `Mac`은 `MessageDigest`와 마찬가지로 thread-safe하지 않다.

해결은 두 가지다. 매 호출마다 `Mac.getInstance`로 새로 만들거나, `ThreadLocal`로 스레드마다 인스턴스를 분리한다. `getInstance` 비용이 부담되면 후자가 낫다.

```java
private static final ThreadLocal<Mac> MAC_HOLDER = ThreadLocal.withInitial(() -> {
    try {
        return Mac.getInstance("HmacSHA256");
    } catch (NoSuchAlgorithmException e) {
        throw new IllegalStateException(e);
    }
});

public byte[] sign(byte[] key, byte[] msg) throws InvalidKeyException {
    Mac mac = MAC_HOLDER.get();
    mac.init(new SecretKeySpec(key, "HmacSHA256")); // init이 내부 상태를 리셋한다
    return mac.doFinal(msg);
}
```

`init`을 매번 호출하면 키 설정과 함께 내부 상태가 리셋되니 이전 호출의 잔여 데이터가 섞이지 않는다. `update`만 쓰고 `doFinal` 없이 객체를 재사용하다가 이전 데이터가 남아 MAC이 틀어지는 경우도 같은 맥락이다. 한 번 서명을 끝냈으면 반드시 `doFinal`로 닫거나 `init`으로 리셋한다.

---

## 비교는 반드시 constant-time으로

서명 검증에서 가장 많이 나오는 사고다. 받은 서명과 계산한 서명을 `equals`나 `==`로 비교하면 타이밍 공격에 노출된다.

```java
// 위험: 일반 비교는 첫 불일치 바이트에서 즉시 반환된다
if (receivedSignature.equals(computedSignature)) { ... }
```

`String.equals`나 바이트 배열의 일반 비교는 앞에서부터 비교하다가 다른 바이트를 만나면 바로 false를 반환한다. 즉 앞쪽 바이트가 더 많이 맞을수록 비교에 걸리는 시간이 미세하게 길어진다. 공격자가 서명을 한 바이트씩 바꿔가며 응답 시간을 측정하면, 시간이 길어지는 방향으로 정답 서명을 한 바이트씩 복원할 수 있다. 네트워크 너머라 노이즈가 크지만, 요청을 수만 번 반복해 통계를 내면 신호가 드러난다.

constant-time 비교는 길이가 같은 두 값을 끝까지 다 비교한 뒤 결과를 낸다. 어느 바이트에서 틀리든 걸리는 시간이 일정하다.

```java
// Java
if (MessageDigest.isEqual(receivedBytes, computedBytes)) { ... }
```

```python
# Python
import hmac
if hmac.compare_digest(received, computed):
    ...
```

```go
// Go
import "crypto/hmac"
if hmac.Equal(receivedMac, computedMac) {
    ...
}
```

Java의 `MessageDigest.isEqual`은 이름과 달리 HMAC 바이트 비교에도 그대로 쓴다. 옛날 JDK(6 이하)에선 이 메서드가 길이 다르면 일찍 반환하는 버그가 있었지만 현행 버전은 constant-time이다. 직접 XOR 누적 비교를 짜는 사람도 있는데, 검증된 표준 함수를 쓰는 게 안전하다.

한 가지 주의. 두 값의 길이가 다르면 constant-time 함수도 보통 빠르게 false를 낸다. 길이 자체는 비밀이 아니므로 문제는 아니지만, 입력 인코딩이 어긋나 길이가 달라지면 검증이 항상 실패한다. 다음 절의 인코딩 문제와 같이 본다.

---

## hex와 base64 인코딩 불일치로 검증이 실패한다

HMAC 출력은 raw 바이트다. 이걸 헤더나 JSON에 담을 땐 hex나 base64로 인코딩한다. 서명하는 쪽과 검증하는 쪽이 같은 인코딩을 안 쓰면 값은 맞는데 문자열 비교에서 무조건 깨진다.

같은 32바이트 HMAC이라도 표현이 다르다.

```
raw 바이트:  [0x2f, 0xa1, ...]  (32바이트)
hex:        "2fa1c3..."          (64자, 소문자)
base64:     "L6HD..."            (44자, = 패딩 포함)
```

실제로 깨지는 지점.

- 한쪽은 hex, 다른 쪽은 base64. 길이부터 64 vs 44로 달라 무조건 실패한다.
- 둘 다 hex인데 대소문자가 다르다. `2FA1...` vs `2fa1...`. 문자열 비교는 다르다고 본다. hex는 소문자로 통일한다.
- base64인데 한쪽은 표준(`+`, `/`), 다른 쪽은 URL-safe(`-`, `_`). JWT는 URL-safe base64에 패딩을 떼고 쓴다. 표준 base64 디코더로 풀면 깨진다.

깔끔한 해법은 문자열을 비교하지 말고 양쪽을 raw 바이트로 디코딩한 뒤 constant-time 비교하는 것이다.

```java
// 받은 hex 서명을 바이트로 디코딩해서 비교
byte[] received = hexDecode(header.getSignature()); // 소문자/대문자 모두 처리
byte[] computed = mac.doFinal(payload);
if (!MessageDigest.isEqual(received, computed)) {
    throw new SignatureException("서명 불일치");
}
```

바이트로 비교하면 hex 대소문자나 base64 변형 같은 표현 차이를 디코딩 단계에서 흡수한다. 문자열로 비교하려면 양쪽 인코딩을 문서로 못 박고 한쪽으로 통일해야 한다. 외부 서비스 연동이면 그쪽 문서에 적힌 인코딩을 그대로 따른다(GitHub는 `sha256=` 접두어 + hex, Stripe는 hex).

---

## 키 회전은 두 키를 동시에 허용하는 기간이 필요하다

HMAC 키가 유출됐거나 주기적으로 바꿔야 할 때, 키를 한 번에 갈아끼우면 그 순간 이미 발급된 서명이나 진행 중인 요청이 전부 검증 실패한다. 발신자와 수신자가 키를 동시에 교체하는 건 분산 환경에서 불가능에 가깝다.

그래서 두 키를 동시에 받아들이는 겹침 기간(grace period)을 둔다.

```python
# 검증 시 현재 키와 이전 키를 모두 시도
def verify(payload, signature, keys):
    # keys = [current_key, previous_key]
    for key in keys:
        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature):
            return True
    return False
```

운영 순서는 이렇게 간다. 새 키를 검증 목록에 추가(이때 발급은 아직 옛 키) → 발급도 새 키로 전환 → 옛 키로 서명된 요청이 다 빠질 만큼 기다린다(웹훅 재시도 윈도우, 토큰 만료 기간 등을 고려) → 옛 키를 검증 목록에서 제거. 겹침 기간은 가장 긴 토큰/요청 수명보다 길게 잡는다.

검증할 때 키를 여러 개 순회하면 그만큼 HMAC 계산을 반복하니, 어떤 키로 서명됐는지 식별자(key id)를 헤더에 같이 보내면 한 번에 맞출 수 있다. JWT의 `kid` 헤더가 이 역할이다. 식별자가 없으면 위 코드처럼 전부 시도하되, constant-time 비교는 키마다 유지한다. 키 보관 자체는 [Secrets_Management.md](Secrets_Management.md)를 따른다.

---

## SHA-256 / SHA-1 / SHA-3 중 무엇을 쓸까

HMAC은 내부 해시를 갈아끼울 수 있다. 선택 기준은 단순하다.

| 알고리즘 | 상태 | 비고 |
|---|---|---|
| HMAC-SHA256 | 기본값 | 새로 짜면 이걸 쓴다. 호환성·성능·보안 균형이 좋다 |
| HMAC-SHA1 | 레거시 한정 | 기존 시스템 호환용으로만. 신규 채택 금지 |
| HMAC-SHA3-256 | 선택지 | 길이 확장 면역이지만 HMAC에선 이 이점이 무의미 |

HMAC-SHA1을 아직도 보게 되는데(AWS SigV2, 옛날 OAuth 1.0a), SHA-1 자체의 충돌 공격이 HMAC 구조를 곧바로 깨는 건 아니다. HMAC-SHA1이 실전에서 바로 위조되진 않는다. 그래도 새로 설계할 땐 쓰지 않는다. SHA-1 의존성을 남겨둘 이유가 없다.

SHA-3는 스펀지 구조라 길이 확장 공격에 면역이다. 그래서 SHA-3는 HMAC으로 감쌀 필요 없이 키 프리픽스(`SHA3(key || msg)`)만으로도 안전한 MAC이 된다. KMAC이 그 방식이다. 하지만 어차피 HMAC-SHA3로 쓰면 그 이점이 묻힌다. SHA-3를 굳이 쓸 이유는 보통 규제나 알고리즘 다양성 요구이고, 일반적인 서명 검증에선 HMAC-SHA256으로 충분하다.

---

## HMAC을 비밀번호 해싱에 쓰면 안 된다

가끔 "HMAC도 키 들어간 해시니까 비밀번호 저장에 쓰면 되지 않나"라는 얘기가 나온다. 안 된다. 용도가 완전히 다르다.

HMAC은 빠르게 계산되도록 설계됐다. 서명 검증은 요청마다 수없이 일어나니 빨라야 한다. 그런데 비밀번호 해싱에선 이 "빠름"이 곧 약점이다. 비밀번호 DB가 유출되면 공격자는 후보 비밀번호를 대입해 해시를 맞춰본다(brute force). HMAC-SHA256은 GPU로 초당 수십억 번 계산되니 약한 비밀번호는 순식간에 뚫린다.

bcrypt, argon2, scrypt는 일부러 느리고 메모리를 많이 먹도록 설계됐다. work factor를 올려 한 번 해싱에 수백 ms를 쓰게 만든다. 정상 로그인은 한 번뿐이라 수백 ms를 견디지만, 수십억 번 대입하는 공격자에겐 치명적인 비용이 된다. 거기에 솔트가 기본으로 들어가 레인보우 테이블도 막는다.

정리하면 HMAC은 "키를 아는 쪽이 보냈는가"를 빠르게 검증하는 용도고, 비밀번호 해싱은 "유출돼도 원본을 못 캐도록" 느리게 만드는 용도다. 비밀번호 저장은 [Password_Hashing.md](Password_Hashing.md)를 본다.

---

## 실제로 어디에 쓰이나

매일 돌아가는데 의식 못 하는 경우가 많다.

- **JWT HS256**: `HMACSHA256(base64url(header) + "." + base64url(payload), secret)`. 대칭 키라 발급자와 검증자가 같은 비밀을 공유한다. 서비스가 여러 개로 쪼개지면 비대칭(RS256)으로 가는 게 보통이다. [JWT.md](JWT.md) 참고.
- **AWS SigV4**: 요청을 정규화한 문자열을 비밀 키 기반으로 여러 번 HMAC-SHA256 체인해서 서명한다. 날짜·리전·서비스를 단계별로 HMAC해 파생 키를 만드는 구조다.
- **웹훅 서명**: GitHub(`X-Hub-Signature-256`), Stripe(`Stripe-Signature`) 모두 본문에 HMAC-SHA256 서명을 붙인다. 수신 흐름 전체는 [Webhook_Security.md](Webhook_Security.md)에 있다.
- **쿠키·세션 서명**: 쿠키에 담은 값이 변조되지 않았는지 HMAC으로 검증한다. 평문 값 + HMAC을 같이 저장하고 읽을 때 재계산해 맞춘다. [Cookie_Security.md](Cookie_Security.md) 참고.
- **API 요청 서명**: 사내 서비스 간 요청에 `HMAC(secret, method + path + body + timestamp)`를 붙여 위조와 재생을 막는다. 타임스탬프를 서명에 포함해야 replay를 막을 수 있다.

공통적으로, HMAC은 "이 데이터가 키를 아는 쪽에서 나왔고 변조되지 않았다"만 보장한다. 누가 봤는지(기밀성)는 보장하지 않는다. 기밀성이 필요하면 암호화를 따로 건다.

---

## 정리

- 단순 `hash(key || msg)`는 SHA-2 길이 확장 공격에 뚫린다. HMAC의 이중 중첩 구조가 이를 막는다.
- 키는 raw 바이트로 일관되게 다루고 32바이트 이상을 쓴다. 너무 길면 어차피 해시돼 축약된다.
- Java `Mac`은 stateful하고 thread-safe하지 않다. `ThreadLocal`이나 매번 새 인스턴스로 쓰고, `doFinal` 후 `init`으로 리셋한다.
- 서명 비교는 `MessageDigest.isEqual` / `hmac.compare_digest` / `hmac.Equal` 같은 constant-time 함수로 한다.
- hex/base64 인코딩과 대소문자를 양쪽이 맞춰야 한다. 가능하면 raw 바이트로 디코딩해 비교한다.
- 키 회전은 두 키를 동시에 허용하는 겹침 기간을 둔다.
- HMAC을 비밀번호 해싱에 쓰지 않는다. bcrypt/argon2를 쓴다.
