---
title: 비밀번호 해싱과 저장
tags: [backend, authentication, password, bcrypt, argon2, scrypt, security]
updated: 2026-05-08
---

# 비밀번호 해싱과 저장

## 시작하기 전에

비밀번호는 암호화(encryption)하면 안 된다. 암호화는 복호화 키만 있으면 원문이 나오기 때문에, DB가 털리고 키 관리 서버까지 같이 털리면 평문이 노출된다. 비밀번호는 단방향 해시(one-way hash)로 저장해야 한다. 사용자가 입력한 값을 같은 함수로 해시해서 저장된 값과 비교하는 식으로 검증한다.

그런데 SHA-256 같은 일반 해시 함수를 그대로 쓰면 안 된다. SHA 계열은 빠르게 계산하도록 설계된 함수다. RTX 4090 한 장으로 SHA-256은 초당 200억 회 이상 시도가 가능하다. 8자 영숫자 비밀번호는 며칠이면 전수 조회가 끝난다. 비밀번호 해싱은 의도적으로 느린 함수, 즉 KDF(Key Derivation Function)를 써야 한다. bcrypt, scrypt, argon2가 그래서 만들어졌다.

## 핵심 개념

### 단방향 해시 + 솔트 + 반복

비밀번호 해싱 함수가 갖춰야 할 조건은 세 가지다.

첫째, 단방향이어야 한다. 해시값에서 원문을 복구할 수 없어야 한다.

둘째, 솔트(salt)가 자동으로 들어가야 한다. 솔트는 사용자마다 다른 무작위 값으로, 같은 비밀번호라도 해시 결과가 다르게 나오도록 만든다. 솔트가 없으면 미리 계산해 둔 레인보우 테이블로 매칭해서 뚫을 수 있다.

셋째, 의도적으로 느려야 한다. cost factor라는 파라미터로 연산량을 늘려서, 한 번의 검증에 수십~수백 ms가 걸리도록 만든다. 정상 로그인은 사용자가 한 번만 기다리면 되지만, 공격자는 수십억 번 시도해야 하므로 비용이 천문학적으로 늘어난다.

### 메모리 hardness가 왜 중요해졌나

bcrypt가 1999년에 나왔을 때는 CPU 연산량을 늘리는 것만으로 충분했다. 그런데 GPU와 ASIC이 등장하면서 상황이 바뀌었다. GPU는 단순 반복 연산을 병렬로 어마어마하게 돌릴 수 있다. bcrypt도 GPU에서 가속이 가능하다. RTX 4090 기준 bcrypt cost 12로 초당 약 18만 회 시도가 가능하다고 알려져 있다. 평범한 비밀번호는 여전히 위험하다.

그래서 메모리를 많이 쓰도록 강제하는 함수가 나왔다. scrypt(2009)와 argon2(2015)다. GPU는 코어는 많지만 코어당 메모리 대역폭이 좁아서, 메모리를 GB 단위로 쓰는 함수는 병렬화 효율이 급격히 떨어진다. ASIC도 마찬가지다. 메모리 hardness가 GPU 저항성의 핵심이다.

## 알고리즘 비교

### bcrypt

1999년에 나온 가장 오래된 KDF 중 하나다. 지금도 가장 많이 쓰인다. Spring Security의 기본값이고, Django, Rails, Laravel 등 대부분의 웹 프레임워크가 기본 지원한다.

특징:

- cost factor: 4~31 (실제로는 10~14 사이를 쓴다). cost가 1 증가하면 연산량이 2배가 된다.
- 입력 길이 제한 72바이트. 이걸 모르고 긴 비밀번호를 받으면 잘려서 들어간다. 사전에 SHA-512로 한 번 돌려서 64바이트로 줄여 넣는 우회법이 있는데, 라이브러리마다 처리가 다르므로 확인하고 써야 한다.
- 메모리 사용량 4KB 정도로 매우 적다. GPU 저항성이 약한 편이다.
- 해시 길이 60자 고정. `$2a$12$...` 형식으로 알고리즘 버전과 cost가 해시 안에 들어간다.

신규 프로젝트에 무난한 선택이다. 라이브러리 지원이 압도적으로 좋고, 검증된 지 25년 가까이 됐다. cost를 12 이상으로 잡으면 평범한 사용자 인증에는 충분하다.

### scrypt

2009년에 BIP38(비트코인 지갑 암호화)에 쓰려고 만들어졌다. 메모리 hardness를 처음으로 도입했다.

특징:

- 파라미터 세 개: N(CPU/메모리 cost), r(블록 크기), p(병렬화)
- 메모리 사용량을 N과 r로 조절. 보통 N=2^15=32768, r=8, p=1로 32MB 정도 쓴다.
- 메모리 hardness가 좋지만 argon2id에 비하면 부족하다.
- Node.js 표준 라이브러리(`crypto.scrypt`)에 기본 포함되어 있다.

bcrypt보다 GPU 저항성은 좋은데, argon2id가 나온 이후로는 신규 채택이 줄었다. 이미 scrypt로 운영 중이면 굳이 마이그레이션할 필요는 없다.

### argon2id

2015년 Password Hashing Competition 우승작이다. 현재 OWASP가 1순위로 권장한다. RFC 9106으로 표준화되어 있다.

argon2에는 세 가지 변종이 있다.

- argon2d: 데이터 의존적 메모리 접근. GPU 저항성 최고지만 사이드 채널 공격에 약함.
- argon2i: 데이터 독립적 메모리 접근. 사이드 채널 안전하지만 GPU 저항성 떨어짐.
- argon2id: 둘을 섞은 하이브리드. 비밀번호 해싱 용도로는 이걸 쓴다.

특징:

- 파라미터 세 개: m(메모리 KB), t(반복 횟수, time cost), p(병렬화)
- OWASP 권장값 한 가지 예: m=19456 (19MB), t=2, p=1
- 메모리 hardness가 가장 강하다. GPU/ASIC 저항성이 압도적이다.
- 해시 형식은 `$argon2id$v=19$m=19456,t=2,p=1$<salt>$<hash>`

신규 프로젝트라면 argon2id가 정답이다. 단, 메모리를 사용자당 19MB씩 쓰니까 동시 로그인이 많으면 메모리 압박이 있을 수 있다. 초당 100명이 동시에 로그인하면 약 2GB가 필요하다는 계산이 나온다. 인증 서버 메모리를 보고 m을 조절해야 한다.

### 빠른 비교

| 항목 | bcrypt | scrypt | argon2id |
|------|--------|--------|----------|
| 발표년도 | 1999 | 2009 | 2015 |
| 메모리 hardness | 약함 (4KB) | 중간 (보통 32MB) | 강함 (보통 19MB+) |
| GPU 저항성 | 약함 | 중간 | 강함 |
| 입력 길이 제한 | 72 bytes | 없음 | 없음 |
| 표준화 | de facto | RFC 7914 | RFC 9106 |
| OWASP 권장순위 | 3순위 | 4순위 | 1순위 |
| 라이브러리 지원 | 매우 좋음 | 좋음 | 좋음 (점점 늘어남) |

OWASP가 argon2id를 1순위로 두지만 bcrypt를 여전히 권장 목록에 둔 이유는 호환성과 검증 이력 때문이다. argon2 라이브러리가 없는 환경에서는 bcrypt를 쓰면 된다.

## cost factor 튜닝

서버 CPU에서 한 번 해시하는 데 100ms 걸리도록 잡는 게 보통의 기준이다. 이유는 두 가지다. 사용자가 로그인할 때 100ms 정도는 체감하지 않는다. 공격자가 한 비밀번호를 시도하는 데도 100ms가 걸리니까, 초당 시도 횟수가 10회로 제한된다.

### 측정 방법

운영 서버와 동일한 사양에서 측정해야 한다. 노트북에서 측정한 값을 그대로 운영에 쓰면 너무 빠르거나 너무 느릴 수 있다.

bcrypt cost factor 측정 예제:

```java
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class CostMeasurement {
    public static void main(String[] args) {
        String password = "test_password_for_measurement";

        for (int cost = 10; cost <= 14; cost++) {
            BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(cost);
            long start = System.currentTimeMillis();
            encoder.encode(password);
            long elapsed = System.currentTimeMillis() - start;
            System.out.printf("cost=%d, %dms%n", cost, elapsed);
        }
    }
}
```

출력 예시 (M1 Pro 기준):

```
cost=10, 65ms
cost=11, 130ms
cost=12, 260ms
cost=13, 520ms
cost=14, 1040ms
```

이 서버에서 100ms 기준이라면 cost=10이나 11을 쓰면 된다. 운영 서버가 더 빠른 EC2 c7i.large라면 cost를 한두 단계 더 올린다.

argon2id 파라미터 측정:

```java
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;

public class Argon2Measurement {
    public static void main(String[] args) {
        String password = "test_password_for_measurement";

        // saltLength=16, hashLength=32, parallelism=1, memory=19456KB, iterations=2
        Argon2PasswordEncoder encoder = new Argon2PasswordEncoder(16, 32, 1, 19456, 2);

        long start = System.currentTimeMillis();
        encoder.encode(password);
        long elapsed = System.currentTimeMillis() - start;
        System.out.printf("memory=19MB, t=2, %dms%n", elapsed);
    }
}
```

argon2id는 memory(m)와 iterations(t)를 같이 조절한다. 메모리가 빠듯하면 m을 줄이고 t를 늘려서 시간을 맞춘다. OWASP 권장 조합 몇 개:

- m=47104(46MB), t=1, p=1
- m=19456(19MB), t=2, p=1
- m=12288(12MB), t=3, p=1
- m=9216(9MB), t=4, p=1
- m=7168(7MB), t=5, p=1

### 운영 환경에서 주의할 점

해싱은 CPU bound 작업이다. cost를 높이면 동시 로그인 처리량이 떨어진다. cost=12로 100ms 걸리는 서버에서 4 vCPU라면 이론상 초당 40회밖에 처리 못 한다. 로그인 요청이 몰리는 서비스면 인증 서버를 따로 분리하거나 인스턴스를 늘려야 한다.

해싱을 비동기로 돌리고 싶다면 별도 스레드 풀을 써야 한다. Spring 환경에서 톰캣 워커 스레드를 그대로 쓰면 해싱 중에 요청 처리가 막힌다. `@Async` + 전용 `Executor`로 분리하는 게 안전하다.

## 솔트 자동 생성

bcrypt, scrypt, argon2id 모두 솔트를 자동으로 생성한다. 라이브러리 호출만 하면 내부에서 무작위 솔트를 만들고 해시 문자열에 같이 인코딩해 준다. 별도로 솔트 컬럼을 따로 둘 필요가 없다.

bcrypt 출력 형식을 뜯어 보면 솔트가 어디 들어가 있는지 보인다.

```
$2a$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
 │  │  │                      │
 │  │  │                      └── 31자 해시
 │  │  └── 22자 솔트 (Base64)
 │  └── cost=12
 └── 알고리즘 버전 (2a, 2b, 2y)
```

argon2id 출력 형식:

```
$argon2id$v=19$m=19456,t=2,p=1$c2FsdHN0cmluZ2hlcmU$hashstringhere
```

알고리즘, 버전, 파라미터, 솔트, 해시가 모두 하나의 문자열에 들어간다. DB에는 이 문자열만 통째로 저장하면 된다. VARCHAR(255)면 충분하다.

직접 솔트를 만들어서 넣으려는 사람이 가끔 있는데, 자기가 짠 코드보다 라이브러리 기본 동작을 믿는 게 낫다. 솔트는 길이 16바이트 이상의 CSPRNG(암호학적 의사난수 생성기) 출력이어야 하고, 라이브러리는 OS의 `/dev/urandom`이나 `SecureRandom`을 정확히 쓴다.

## peppering

솔트는 DB에 같이 저장되니까, DB가 통째로 털리면 솔트도 같이 노출된다. peppering은 추가로 서버 측 시크릿을 비밀번호와 함께 해시해서, DB만 털려서는 오프라인 크래킹이 불가능하도록 만드는 방법이다.

원리:

```
hash = bcrypt(password + pepper, salt)
```

pepper는 모든 사용자에게 동일한 시크릿이고, DB가 아닌 별도 저장소(환경변수, KMS, HashiCorp Vault 등)에 둔다. DB만 유출되면 pepper를 모르니 크래킹 시도 자체가 의미가 없다.

장점은 명확하지만 단점도 있다.

- pepper가 유출되면 다시 모든 비밀번호를 마이그레이션해야 한다.
- pepper 변경(rotation)이 어렵다. 기존 해시를 다시 만들 방법이 없으니, 사용자가 다음에 로그인할 때 새 pepper로 재해싱하는 마이그레이션 패턴을 써야 한다.
- pepper를 어디 둘지가 또 다른 보안 문제다. 환경변수에 두면 메모리 덤프나 프로세스 권한 탈취로 새는 경우가 있다.

peppering이 항상 답은 아니다. argon2id를 m=19MB, t=2로 잘 쓰고 있고 DB 접근 권한이 충분히 격리되어 있다면 굳이 안 써도 된다. 금융권처럼 DB 유출 시나리오를 정말 심각하게 보는 환경에서 추가 방어선으로 쓴다.

HMAC 방식의 peppering도 있다. 비밀번호를 먼저 HMAC-SHA256으로 한 번 처리한 뒤 그 결과를 bcrypt에 넣는 방식이다. 이렇게 하면 bcrypt 72바이트 제한도 우회된다.

```java
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class PepperedHasher {
    private final BCryptPasswordEncoder bcrypt = new BCryptPasswordEncoder(12);
    private final byte[] pepper;

    public PepperedHasher(byte[] pepper) {
        this.pepper = pepper;
    }

    public String hash(String password) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(pepper, "HmacSHA256"));
        byte[] preHashed = mac.doFinal(password.getBytes("UTF-8"));
        String prepared = Base64.getEncoder().encodeToString(preHashed);
        return bcrypt.encode(prepared);
    }

    public boolean verify(String password, String stored) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(pepper, "HmacSHA256"));
        byte[] preHashed = mac.doFinal(password.getBytes("UTF-8"));
        String prepared = Base64.getEncoder().encodeToString(preHashed);
        return bcrypt.matches(prepared, stored);
    }
}
```

## 알고리즘 마이그레이션

해싱 알고리즘은 시간이 지나면 약해진다. 5년 전에 bcrypt cost=10이 적정선이었다면 지금은 cost=12가 권장된다. argon2id로 갈아타고 싶을 수도 있다. 그런데 비밀번호는 평문을 모르니까 일괄 재해싱이 불가능하다.

해법은 로그인 시점 재해싱이다. 사용자가 로그인할 때 평문 비밀번호가 잠시 메모리에 올라온다. 이때 검증 후 새 알고리즘으로 다시 해시해서 DB를 갱신한다.

흐름:

1. 사용자가 로그인 요청, 평문 비밀번호 전송
2. DB에서 저장된 해시 조회. 해시 prefix(`$2a$`, `$argon2id$` 등)로 알고리즘 판별
3. 해당 알고리즘으로 검증
4. 검증 성공 시, 현재 권장 알고리즘/파라미터인지 확인
5. 구버전이면 평문을 새 알고리즘으로 해시하고 DB 업데이트

```java
public class PasswordService {
    private final UserRepository userRepository;
    private final PasswordEncoder currentEncoder;  // argon2id

    public PasswordService(UserRepository userRepository, PasswordEncoder currentEncoder) {
        this.userRepository = userRepository;
        this.currentEncoder = currentEncoder;
    }

    public boolean authenticate(String username, String rawPassword) {
        User user = userRepository.findByUsername(username);
        if (user == null) {
            // 타이밍 공격 방어. 가짜 해시를 한 번 돌린다.
            currentEncoder.encode(rawPassword);
            return false;
        }

        if (!currentEncoder.matches(rawPassword, user.getPasswordHash())) {
            return false;
        }

        // 마이그레이션 필요 여부 확인
        if (currentEncoder.upgradeEncoding(user.getPasswordHash())) {
            String newHash = currentEncoder.encode(rawPassword);
            user.setPasswordHash(newHash);
            userRepository.save(user);
        }
        return true;
    }
}
```

Spring Security의 `PasswordEncoder` 인터페이스에 `upgradeEncoding()` 메서드가 있다. 현재 해시가 권장 파라미터를 만족하는지 검사해서, 못 미치면 true를 반환한다. 이걸 보고 재해싱하면 된다.

마이그레이션 기간 중에는 두 알고리즘이 DB에 공존한다. 사용자가 한 번도 로그인 안 하면 영영 구버전으로 남는다. 일정 기간(예: 1년) 후에는 비활성 사용자에게 비밀번호 재설정을 강제하거나 계정을 잠가야 한다.

## 비밀번호 정책 (NIST SP 800-63B)

NIST가 2017년에 SP 800-63B를 개정하면서 비밀번호 정책에 관한 통념이 많이 바뀌었다. 한국 KISA 가이드라인도 일부 따라가는 추세다. 핵심 변화:

### 길이가 복잡도보다 중요하다

기존: 8자 이상, 대소문자/숫자/특수문자 조합 강제

NIST 권장: 최소 8자, 권장 15자 이상. 복잡도 강제 없음.

복잡도 규칙을 강제하면 사용자는 `Password1!` 같은 예측 가능한 패턴을 만든다. 길이가 늘어나는 게 엔트로피 측면에서 훨씬 강하다. `correcthorsebatterystaple` 같은 긴 passphrase가 `P@ssw0rd!`보다 훨씬 안전하다.

### 주기적 변경 강제 폐지

기존: 90일마다 강제 변경

NIST 권장: 강제 변경 안 함. 단, 유출 정황이 있으면 즉시 변경.

주기적 변경을 강제하면 사용자는 `Password1!` → `Password2!` 같이 한 글자만 바꾸거나, 어디 적어 둔다. 보안이 오히려 약해진다. 변경은 유출이 의심될 때만 한다.

### 모든 인쇄 가능 문자 허용

특수문자나 이모지, 공백을 막으면 안 된다. 사용자가 만들 수 있는 비밀번호 공간을 줄이는 셈이다. 입력 가능한 모든 유니코드 문자를 허용하고, 길이 상한은 64자 이상으로 둔다.

### 차단 목록(blocklist) 검사

신규 가입이나 비밀번호 변경 시, 자주 쓰이는 비밀번호와 유출된 비밀번호를 막아야 한다. `password`, `123456`, `qwerty`, 회사 이름, 사용자 이메일에서 파생된 단어 등을 차단한다.

### 힌트 질문 폐지

"어머니의 결혼 전 성씨" 같은 힌트 질문은 폐지 대상이다. SNS에서 다 찾을 수 있다.

### 정리하면

- 최소 길이 8자, 권장 12~15자
- 최대 길이 64자 이상 허용
- 복잡도 규칙 강제 안 함
- 주기적 변경 강제 안 함
- 유출/일반 비밀번호 차단
- 모든 문자 허용
- 힌트 질문 안 씀

레거시 시스템에서 NIST 권장으로 옮길 때, 보안팀이나 컴플라이언스 부서를 설득하는 게 가장 어려운 부분이다. 금융감독원이나 ISMS-P 인증 요구사항이 NIST보다 더 엄격할 때가 있어서 따르기 전에 확인이 필요하다.

## HaveIBeenPwned로 유출 비밀번호 차단

[HaveIBeenPwned](https://haveibeenpwned.com)는 Troy Hunt가 운영하는 유출 데이터베이스다. 누적 유출 비밀번호 약 8억 5천만 건의 SHA-1 해시를 공개 API로 제공한다. NIST가 권장하는 차단 목록 검사를 이걸로 구현할 수 있다.

### k-Anonymity 방식

비밀번호를 그대로 보내면 안 되므로 k-Anonymity라는 방식을 쓴다. 비밀번호의 SHA-1 해시 앞 5자만 서버에 보내면, 그 prefix로 시작하는 모든 해시 suffix와 발견 횟수를 받는다. 클라이언트에서 자기 해시 suffix와 비교해서 일치하는지 본다.

```
사용자 비밀번호: "password"
SHA-1: 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
prefix (앞 5자): 5BAA6
suffix: 1E4C9B93F3F0682250B6CF8331B7EE68FD8

API 호출: GET https://api.pwnedpasswords.com/range/5BAA6
응답:
003D68EB55068C33ACE09247EE4C639306B:3
0083C5B7AF96D8DEEDDB1FD9F69E1C16F25:2
...
1E4C9B93F3F0682250B6CF8331B7EE68FD8:9659365
...

→ 일치하는 suffix가 있으면 유출된 비밀번호. 9,659,365회 발견.
```

서버에 전체 해시를 보내지 않으니까 프라이버시가 보장된다.

Java 구현 예제:

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.security.MessageDigest;

public class PwnedPasswordChecker {
    private final HttpClient client = HttpClient.newHttpClient();

    public boolean isPwned(String password) throws Exception {
        String sha1 = sha1Hex(password);
        String prefix = sha1.substring(0, 5);
        String suffix = sha1.substring(5);

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("https://api.pwnedpasswords.com/range/" + prefix))
            .header("Add-Padding", "true")  // 응답 길이 패딩
            .timeout(java.time.Duration.ofSeconds(3))
            .GET()
            .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

        for (String line : response.body().split("\n")) {
            String[] parts = line.split(":");
            if (parts[0].equalsIgnoreCase(suffix)) {
                int count = Integer.parseInt(parts[1].trim());
                return count > 0;
            }
        }
        return false;
    }

    private String sha1Hex(String input) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-1");
        byte[] bytes = md.digest(input.getBytes("UTF-8"));
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02X", b));
        }
        return sb.toString();
    }
}
```

### 운영에서 주의할 점

API 응답이 느리거나 실패하면 회원가입이 막힌다. 타임아웃을 짧게(3초 이내) 잡고, 실패 시 fallback 동작을 정해 둬야 한다. 보통은 fail-open(차단 못 해도 가입은 받음)으로 하고, 백그라운드에서 재검사한다. fail-closed로 하면 외부 API 장애가 자기 서비스 장애가 된다.

API 호출이 부담스러우면 전체 데이터셋(약 40GB)을 다운로드 받아서 자체 서버에 두는 방법도 있다. 한 달에 한 번 갱신한다.

## Spring Security DelegatingPasswordEncoder

Spring Security 5부터 `DelegatingPasswordEncoder`가 기본값이 됐다. 여러 알고리즘 해시를 동시에 DB에 저장하고, 해시 prefix로 어떤 인코더를 쓸지 결정하는 구조다.

### 동작 원리

DB에 저장되는 해시 형식:

```
{bcrypt}$2a$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
{argon2id}$argon2id$v=19$m=19456,t=2,p=1$c2FsdC4uLg$aGFzaC4uLg
{noop}plaintext_password   ← 테스트용. 운영에선 절대 쓰면 안 됨
```

`{알고리즘ID}` prefix로 어떤 인코더로 검증할지 알 수 있다. `matches()` 호출 시 prefix를 보고 적절한 인코더로 위임한다. `encode()`는 현재 디폴트로 설정된 인코더를 쓴다.

### 설정 예제

```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.DelegatingPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class PasswordEncoderConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        String defaultEncoder = "argon2id";

        Map<String, PasswordEncoder> encoders = new HashMap<>();
        encoders.put("bcrypt", new BCryptPasswordEncoder(12));
        encoders.put("argon2id", new Argon2PasswordEncoder(16, 32, 1, 19456, 2));

        DelegatingPasswordEncoder delegating = new DelegatingPasswordEncoder(defaultEncoder, encoders);

        // 구버전 해시(prefix 없음)에 대한 fallback
        delegating.setDefaultPasswordEncoderForMatches(new BCryptPasswordEncoder(10));

        return delegating;
    }
}
```

이렇게 두면 새 비밀번호는 argon2id로 저장되고, 기존 bcrypt 해시는 그대로 검증된다. 로그인 시점 재해싱과 결합하면 자연스럽게 마이그레이션이 진행된다.

### 마이그레이션 시나리오

운영 중인 서비스를 bcrypt에서 argon2id로 옮기는 흐름.

1. 디폴트 인코더를 argon2id로 변경 후 배포
2. 신규 가입자는 argon2id로 저장
3. 기존 사용자는 로그인 시 bcrypt로 검증, 검증 성공하면 argon2id로 재해싱
4. 모니터링에서 bcrypt prefix 비율 추적
5. 비활성 사용자는 일정 기간 후 비밀번호 재설정 메일 발송
6. 모든 해시가 argon2id로 전환되면 bcrypt 인코더 제거

prefix 통계 쿼리:

```sql
SELECT
    SUBSTRING_INDEX(SUBSTRING_INDEX(password_hash, '}', 1), '{', -1) AS algorithm,
    COUNT(*) AS user_count
FROM users
WHERE password_hash IS NOT NULL
GROUP BY algorithm;
```

이 쿼리로 마이그레이션 진행률을 모니터링한다.

## 자주 마주치는 함정

### 비밀번호를 로그에 찍는 실수

스택 트레이스나 디버그 로그에 평문 비밀번호가 남는 경우가 의외로 많다. DTO를 통째로 `toString()` 했다가 비밀번호 필드까지 찍히는 식이다. Lombok `@ToString(exclude = "password")`를 거는 게 안전하다. JSON 직렬화도 `@JsonIgnore`로 막는다.

### HTTPS 안 거치는 로그인

요즘은 거의 없지만 여전히 가끔 본다. 평문 비밀번호가 네트워크에 노출되면 해싱이 무의미하다. HTTPS는 필수다.

### 클라이언트에서 해시한 값을 보내는 것

"클라이언트에서 SHA-256 해시해서 보내면 안전한 거 아니냐"는 질문을 받는다. 안전하지 않다. 클라이언트가 보낸 해시값이 새로운 "비밀번호"가 될 뿐이고, 공격자가 그 해시를 가로채면 그대로 로그인할 수 있다. 해싱은 서버에서 받은 평문에 대해서만 의미가 있다.

### 타이밍 공격

존재하지 않는 사용자에 대해 즉시 false를 반환하면, 응답 시간 차이로 사용자 존재 여부가 새어 나간다. 사용자가 없을 때도 가짜 해시를 한 번 돌려서 같은 시간을 쓰도록 해야 한다. 위 `PasswordService` 예제에 그 처리가 들어 있다.

### 최대 길이 검증 안 함

argon2id는 입력 길이 제한이 사실상 없다. 사용자가 100MB짜리 비밀번호를 보내면 메모리/CPU가 동시에 터진다. 입력 길이 상한(보통 1024 bytes)을 두고 사전에 거른다.

### 비밀번호 변경 시 기존 비밀번호 확인 안 함

세션 탈취된 상태에서 비밀번호가 바뀌면 정당한 사용자가 들어올 수 없다. 비밀번호 변경 시 기존 비밀번호를 한 번 더 받아서 검증해야 한다.
