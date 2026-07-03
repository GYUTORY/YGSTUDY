---
title: DID (Decentralized Identifier)
tags: [did, ssi, verifiable-credential, decentralized-identity, security]
updated: 2026-03-27
---

# DID (Decentralized Identifier)

## DID란

DID는 중앙 기관 없이 개인이 스스로 생성하고 관리하는 식별자다. W3C에서 표준화했고, 기존 OAuth처럼 Google이나 Kakao 같은 IdP(Identity Provider)에 의존하지 않는다.

핵심은 **자기주권신원(Self-Sovereign Identity, SSI)** 개념이다. 내 신원 정보를 내가 직접 관리하고, 필요한 만큼만 상대방에게 제시한다.

```
did:web:example.com:users:alice
 │   │        │
 │   │        └── method-specific-id (식별 대상)
 │   └── DID Method (해석 방법)
 └── DID scheme (고정값)
```

DID 자체는 그냥 문자열이다. 이 문자열을 **DID Document**로 resolve해야 실제로 쓸 수 있다.

---

## DID Document 구성

DID를 resolve하면 JSON-LD 형식의 DID Document가 나온다. 실제로 인증에 필요한 정보가 여기 들어있다.

```json
{
  "@context": "https://www.w3.org/ns/did/v1",
  "id": "did:web:example.com:users:alice",
  "verificationMethod": [
    {
      "id": "did:web:example.com:users:alice#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:web:example.com:users:alice",
      "publicKeyMultibase": "z6Mkf5rGMoatrSj1f..."
    }
  ],
  "authentication": [
    "did:web:example.com:users:alice#key-1"
  ],
  "service": [
    {
      "id": "did:web:example.com:users:alice#api",
      "type": "LinkedDomains",
      "serviceEndpoint": "https://example.com/api"
    }
  ]
}
```

주요 필드:

- **verificationMethod**: 공개키 목록. 서명 검증에 쓴다.
- **authentication**: 본인 인증에 사용할 키를 지정한다. verificationMethod 중 하나를 참조한다.
- **assertionMethod**: VC(Verifiable Credential) 발급 시 서명에 사용할 키.
- **service**: 이 DID와 연관된 서비스 엔드포인트.

DID Document에 개인정보는 들어가지 않는다. 공개키와 서비스 엔드포인트 정도만 포함한다.

---

## DID Resolution

DID 문자열을 받아서 DID Document를 찾아오는 과정이 DID Resolution이다.

```
클라이언트 → DID Resolver → DID Method별 처리 → DID Document 반환
```

DID Method마다 resolve 방식이 다르다:

- `did:web` → HTTPS로 `https://example.com/.well-known/did.json` 또는 `https://example.com/users/alice/did.json` 요청
- `did:key` → DID 문자열 자체에 공개키가 인코딩되어 있어서 네트워크 호출 없이 로컬에서 파싱
- `did:ion` → Bitcoin 블록체인 기반의 Sidetree 프로토콜로 resolve

백엔드에서 DID Resolver를 직접 구현할 일은 거의 없다. `universal-resolver` 같은 오픈소스를 쓰거나, 각 DID Method 라이브러리를 붙인다.

```java
// Java - did:web resolver 예시 (uni-resolver 라이브러리 사용)
DIDResolver resolver = new WebDIDResolver();
DIDDocument didDoc = resolver.resolve("did:web:example.com:users:alice");

// 공개키 추출
VerificationMethod vm = didDoc.getVerificationMethod().get(0);
PublicKey publicKey = vm.getPublicKey();
```

---

## 주요 DID Method 비교

### did:web

도메인 기반. HTTPS로 DID Document를 서빙한다.

```
did:web:example.com → https://example.com/.well-known/did.json
did:web:example.com:team:backend → https://example.com/team/backend/did.json
```

- 장점: 기존 웹 인프라 그대로 사용. DNS + TLS 기반이라 운영이 쉽다.
- 단점: 도메인 소유자가 DID Document를 변조할 수 있다. 진짜 탈중앙은 아니다.
- 적합한 곳: 기업 간 B2B 인증, 조직 단위 DID 발급.

### did:key

공개키를 DID 문자열 자체에 인코딩한다.

```
did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK
```

- 장점: 네트워크 의존성 없음. 생성과 resolve가 즉시 가능.
- 단점: 키 로테이션 불가. 키를 바꾸려면 DID 자체가 바뀐다.
- 적합한 곳: 일회성 인증, 테스트, 단기 세션.

### did:ion (did:btc)

Bitcoin 블록체인 위에 Sidetree 프로토콜로 동작한다. Microsoft가 주도했다.

- 장점: 완전한 탈중앙화. 누구도 DID Document를 임의로 변경할 수 없다.
- 단점: resolve 속도가 느리다(수 초). 노드 운영 비용이 든다.
- 적합한 곳: 공공 신원 인증, 높은 신뢰 수준이 필요한 서비스.

### did:ethr

Ethereum 블록체인 기반. ERC-1056 레지스트리 컨트랙트를 사용한다.

- 장점: Ethereum 생태계와 통합이 쉽다. 스마트 컨트랙트로 키 로테이션 지원.
- 단점: 가스비 발생. 네트워크 상태에 따라 트랜잭션 지연.
- 적합한 곳: DeFi, Web3 서비스 연동.

실무에서 가장 먼저 고려하는 건 `did:web`이다. 기존 인프라를 활용할 수 있고, 대부분의 B2B 시나리오에서 충분하다. 블록체인 기반은 탈중앙화가 반드시 필요한 경우에만 검토한다.

---

## Verifiable Credential과 Verifiable Presentation

### VC (Verifiable Credential)

발급자가 주체에 대해 "이 사람은 ~이다"라고 서명한 증명서다.

```
발급자(Issuer) → VC 발급 → 보유자(Holder) → VP 생성 → 검증자(Verifier)
```

VC 구조:

```json
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiableCredential", "EmployeeCredential"],
  "issuer": "did:web:hr.example.com",
  "issuanceDate": "2026-03-27T00:00:00Z",
  "credentialSubject": {
    "id": "did:web:example.com:users:alice",
    "employeeId": "EMP-12345",
    "department": "Backend Engineering",
    "role": "Senior Engineer"
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "created": "2026-03-27T00:00:00Z",
    "verificationMethod": "did:web:hr.example.com#key-1",
    "proofValue": "z3FXQjecWufY46..."
  }
}
```

### VP (Verifiable Presentation)

보유자가 검증자에게 VC를 제시할 때, VC를 감싸서 자신의 서명을 추가한 것이 VP다. 이렇게 하면 "이 VC의 주체가 정말 이 사람인지" 확인할 수 있다.

```json
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "type": ["VerifiablePresentation"],
  "holder": "did:web:example.com:users:alice",
  "verifiableCredential": [
    { /* 위의 VC */ }
  ],
  "proof": {
    "type": "Ed25519Signature2020",
    "verificationMethod": "did:web:example.com:users:alice#key-1",
    "challenge": "9a8b7c6d...",
    "proofValue": "zABCDEF123..."
  }
}
```

`challenge` 필드가 중요하다. 검증자가 매 요청마다 랜덤 challenge를 발급하고, 보유자가 이걸 서명에 포함해야 한다. replay attack을 막는 용도다.

### 발급-검증 흐름

```
1. Holder → Issuer: "직원 증명서 발급해주세요" (DID 인증)
2. Issuer → Holder: VC 발급 (Issuer의 서명 포함)
3. Holder: VC를 지갑(Wallet)에 보관
4. Verifier → Holder: "직원 증명 보여주세요" + challenge 발급
5. Holder → Verifier: VP 제출 (VC + Holder 서명 + challenge)
6. Verifier: 검증 수행
   - Issuer의 DID resolve → 공개키로 VC 서명 검증
   - Holder의 DID resolve → 공개키로 VP 서명 검증
   - challenge 일치 확인
   - VC 만료/폐기 여부 확인
```

---

## OAuth/JWT 인증과의 차이

| | OAuth 2.0 + JWT | DID + VC |
|---|---|---|
| 신뢰 구조 | 중앙 IdP에 의존 | 발급자-보유자-검증자 3자 구조 |
| 토큰/증명서 관리 | 서버가 발급하고 서버가 검증 | 보유자가 증명서를 보관하고 선택적으로 제시 |
| 개인정보 노출 | IdP가 사용자 로그인 사실을 안다 | 발급자는 검증 시점을 모른다 |
| 취소/폐기 | 토큰 만료 또는 revocation list | VC Status List 또는 revocation registry |
| 선택적 공개 | 불가 (토큰에 포함된 claim 전체 노출) | ZKP 결합 시 특정 필드만 공개 가능 |

실무에서 중요한 차이점:

**OAuth**: 사용자가 "Google로 로그인"하면, 서비스 A와 서비스 B 모두 Google에 토큰 검증을 요청한다. Google은 사용자가 어디에 로그인하는지 전부 파악할 수 있다.

**DID**: 발급자(예: 정부기관)가 VC를 발급하면, 보유자가 직접 들고 다닌다. 서비스 A에 제시할 때 발급자에게 알릴 필요 없다. 발급자는 사용자의 행동을 추적할 수 없다.

---

## 백엔드에서 DID 기반 인증 구현

### 키 관리

DID 인증의 핵심은 비밀키 관리다. 서버 사이드에서 DID를 운영하려면 키를 어디에 보관할지 결정해야 한다.

```java
// HSM 또는 KMS 연동 예시
@Configuration
public class DIDKeyConfig {

    @Bean
    public KeyPair didKeyPair(KmsClient kmsClient) {
        // AWS KMS에서 비대칭 키 관리
        // 비밀키는 KMS 밖으로 나오지 않는다
        String keyId = "arn:aws:kms:ap-northeast-2:123456:key/abc-def";

        GetPublicKeyResponse response = kmsClient.getPublicKey(
            GetPublicKeyRequest.builder().keyId(keyId).build()
        );

        return new KmsBackedKeyPair(keyId, response.publicKey());
    }
}
```

- 개발/테스트: 파일 시스템에 키 저장해도 된다.
- 운영: AWS KMS, GCP Cloud KMS, HashiCorp Vault 같은 KMS 사용이 필수다.
- 비밀키가 유출되면 그 DID로 서명한 모든 VC의 신뢰가 깨진다.

### DID Resolver 연동

```java
@Service
public class DIDAuthService {

    private final DIDResolver resolver;
    private final Cache<String, DIDDocument> cache;

    public DIDAuthService(DIDResolver resolver) {
        this.resolver = resolver;
        // DID Document 캐싱 — did:web은 매번 HTTP 호출이 필요하므로
        this.cache = Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(5))
            .build();
    }

    public boolean verifyPresentation(VerifiablePresentation vp, String challenge) {
        // 1. challenge 검증
        if (!challenge.equals(vp.getProof().getChallenge())) {
            return false;
        }

        // 2. Holder DID resolve → VP 서명 검증
        DIDDocument holderDoc = resolveDID(vp.getHolder());
        PublicKey holderKey = extractKey(holderDoc, vp.getProof().getVerificationMethod());

        if (!verifySignature(vp, holderKey)) {
            return false;
        }

        // 3. 각 VC에 대해 Issuer DID resolve → VC 서명 검증
        for (VerifiableCredential vc : vp.getVerifiableCredentials()) {
            DIDDocument issuerDoc = resolveDID(vc.getIssuer());
            PublicKey issuerKey = extractKey(issuerDoc, vc.getProof().getVerificationMethod());

            if (!verifySignature(vc, issuerKey)) {
                return false;
            }

            // 4. VC 상태 확인 (만료, 폐기)
            if (isRevoked(vc) || isExpired(vc)) {
                return false;
            }
        }

        return true;
    }

    private DIDDocument resolveDID(String did) {
        return cache.get(did, key -> resolver.resolve(key));
    }
}
```

### VC 검증 로직에서 빠뜨리기 쉬운 것들

1. **Issuer 신뢰 목록 확인**: VC 서명이 유효해도 Issuer를 신뢰할 수 있는지는 별도 판단이 필요하다. 아무나 VC를 발급할 수 있기 때문이다.

```java
// Issuer 허용 목록 관리
private final Set<String> trustedIssuers = Set.of(
    "did:web:gov.example.com",
    "did:web:university.example.com"
);

if (!trustedIssuers.contains(vc.getIssuer())) {
    throw new UntrustedIssuerException(vc.getIssuer());
}
```

2. **VC Status List 확인**: VC가 폐기되었는지 확인해야 한다. W3C Bitstring Status List를 주로 쓴다.

```java
// Status List 확인
public boolean isRevoked(VerifiableCredential vc) {
    CredentialStatus status = vc.getCredentialStatus();
    if (status == null) return false;

    // Status List는 비트맵이다
    // 특정 인덱스의 비트가 1이면 폐기된 상태
    BitString statusList = fetchStatusList(status.getStatusListCredential());
    return statusList.get(status.getStatusListIndex());
}
```

3. **시간 검증**: `issuanceDate`가 미래면 아직 유효하지 않은 VC다. `expirationDate`가 과거면 만료된 VC다. 서버 시간 동기화(NTP)가 틀어지면 문제가 된다.

---

## 실무에서 마주치는 문제들

### 키 분실 복구

사용자가 비밀키를 잃어버리면 해당 DID로는 더 이상 인증할 수 없다. OAuth처럼 "비밀번호 재설정" 같은 게 없다.

대응 방법:

- **키 로테이션 사전 설정**: DID Document에 recovery key를 미리 등록해둔다. `did:ion`은 recovery key와 update key를 분리해서 관리한다.
- **소셜 리커버리**: 신뢰할 수 있는 다수의 지인이 합의하면 키를 복구하는 방식. 아직 표준화가 덜 되어 있다.
- **Custodial Wallet**: 서비스 제공자가 키를 대신 관리한다. 편하지만 자기주권 개념과 충돌한다.

실무에서는 `did:web`을 쓰면 서버 측에서 DID Document를 직접 업데이트할 수 있어서 키 로테이션이 비교적 간단하다. 블록체인 기반 DID는 복구 절차가 복잡하다.

### DID Method 선택 기준

프로젝트에 맞는 DID Method를 고르는 기준:

- **기존 인프라 활용 가능한가**: 웹 서버만 있으면 `did:web`으로 시작할 수 있다. 블록체인 노드를 운영할 여력이 있는가.
- **키 로테이션이 필요한가**: 장기 운영 서비스면 키 로테이션이 필수다. `did:key`는 안 된다.
- **resolve 속도 요구사항**: API 응답 시간에 DID resolution이 포함된다. `did:ion`은 수 초 걸릴 수 있다.
- **규제 요구사항**: 특정 국가/산업에서 요구하는 DID Method가 있을 수 있다. 한국은 DID 관련 법제화가 진행 중이다.

### 성능 이슈

DID 기반 인증은 OAuth보다 검증 비용이 높다.

```
OAuth JWT 검증:
  1. JWT 파싱
  2. 서명 검증 (공개키는 로컬 캐시)
  → 수 ms

DID VP 검증:
  1. VP 파싱
  2. Holder DID resolve (HTTP 또는 블록체인 조회)
  3. VP 서명 검증
  4. 각 VC의 Issuer DID resolve
  5. 각 VC 서명 검증
  6. 각 VC Status List 확인
  → 수십~수백 ms (캐싱 없으면 더 걸림)
```

완화 방법:

- **DID Document 캐싱**: `did:web`의 경우 HTTP Cache-Control 헤더를 활용한다. 5분~1시간 정도 캐싱하는 게 일반적이다.
- **검증 결과 캐싱**: 동일한 VP에 대해 challenge 유효 기간 내에는 재검증을 생략한다.
- **비동기 검증**: 즉시 응답이 필요한 API에서는 VC 검증을 비동기로 처리하고, 검증 완료 전까지 제한된 접근만 허용하는 방식을 쓸 수 있다.
- **Batch resolve**: 여러 DID를 한 번에 resolve하는 Universal Resolver의 batch API를 활용한다.

### 아직 불안정한 부분들

DID/VC 생태계는 표준은 있지만 구현 성숙도가 낮다.

- **라이브러리 호환성**: Java 쪽은 `walt.id`, `Sphereon` 라이브러리가 있지만, 버전 간 호환이 안 되는 경우가 잦다. VC Data Model v1과 v2가 혼재하는 상황이다.
- **DID Method 간 상호운용성**: `did:web`으로 발급한 VC를 `did:ion` 기반 시스템에서 검증할 때, DID Resolver 설정이 제대로 안 되어 있으면 resolve 실패가 난다.
- **지갑 표준화**: 사용자 측 DID 지갑이 아직 표준화되지 않았다. 각 지갑마다 지원하는 DID Method, VC 포맷, 키 알고리즘이 다르다.

당장 프로덕션에 DID를 도입하려면 `did:web` + 특정 라이브러리 조합을 정하고, 그 범위 안에서 동작을 검증하는 게 현실적이다. 여러 DID Method를 동시에 지원하는 건 복잡도만 올라간다.
