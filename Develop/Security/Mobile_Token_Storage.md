---
title: 모바일 앱 토큰 저장 보안
tags: [Mobile, ios, android, keychain, keystore, token, security, authentication, pkce]
updated: 2026-08-01
---

# 모바일 앱 토큰 저장 보안

## 왜 모바일이 다른가

웹 브라우저에서는 Access Token을 메모리에, Refresh Token을 httpOnly 쿠키로 관리하면 기본 보안은 확보된다. 모바일 앱에는 httpOnly 쿠키 개념이 없다. 앱이 꺼지면 메모리도 사라진다. 토큰을 어딘가 파일에 저장해야 하는데, 그 어딘가가 어디냐에 따라 보안 수준이 완전히 달라진다.

iOS와 Android 모두 OS 차원의 보안 저장소를 제공한다. 이 저장소를 쓰지 않고 편의상 일반 설정 저장소에 넣는 경우가 생각보다 많다는 게 문제다.

---

## iOS Keychain

iOS Keychain은 암호화된 하드웨어 기반 저장소다. Secure Enclave와 연동되어 키 자체가 앱 외부에서 관리된다. 앱이 삭제되어도 Keychain 데이터는 남는다. 앱 재설치 후에도 토큰을 복원할 수 있어서 UX 관점에서도 유리하다.

Keychain 항목마다 접근 가능 시점을 설정할 수 있다:

```swift
import Security

func saveToken(_ token: String, key: String) {
    let data = token.data(using: .utf8)!
    
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: key,
        kSecValueData as String: data,
        kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
    ]
    
    SecItemDelete(query as CFDictionary)
    SecItemAdd(query as CFDictionary, nil)
}

func loadToken(key: String) -> String? {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: key,
        kSecReturnData as String: true,
        kSecMatchLimit as String: kSecMatchLimitOne
    ]
    
    var result: AnyObject?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    
    guard status == errSecSuccess,
          let data = result as? Data else { return nil }
    
    return String(data: data, encoding: .utf8)
}
```

`kSecAttrAccessible` 값 선택이 핵심이다:

| 값 | 접근 시점 | iCloud 백업 | 다른 기기 이전 |
|---|---|---|---|
| `kSecAttrAccessibleWhenUnlocked` | 기기 잠금 해제 시 | 가능 | 가능 |
| `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` | 기기 잠금 해제 시 | 불가 | 불가 |
| `kSecAttrAccessibleAfterFirstUnlock` | 첫 잠금 해제 이후 항상 | 가능 | 가능 |
| `kSecAttrAccessibleAlways` | 항상 (잠금 중에도) | 가능 | 가능 |

토큰 저장에는 `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`를 쓰는 게 맞다. `kSecAttrAccessibleAlways`는 기기가 잠긴 상태에서도 접근이 가능해서, 탈옥 환경에서 악성 앱이 토큰을 읽을 수 있는 경로가 된다.

고보안 토큰에는 `SecAccessControl`로 생체 인증을 추가로 요구할 수 있다:

```swift
let access = SecAccessControlCreateWithFlags(
    nil,
    kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
    .biometryCurrentSet, // Face ID / Touch ID 필수
    nil
)!

let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccount as String: "refresh_token",
    kSecValueData as String: tokenData,
    kSecAttrAccessControl as String: access
]

SecItemAdd(query as CFDictionary, nil)
```

---

## Android Keystore

Android Keystore System은 암호화 키를 앱 프로세스 밖에서 관리한다. TEE(Trusted Execution Environment) 또는 StrongBox(별도 보안 칩)가 있는 기기에서는 키가 하드웨어에 격리된다. 앱이 키를 직접 꺼낼 수 없고, Keystore를 통해 암호화/복호화만 요청한다.

토큰 자체는 EncryptedSharedPreferences에 저장하고, 암호화 키만 Keystore에서 관리하는 패턴이 일반적이다:

```kotlin
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class TokenStorage(private val context: Context) {
    
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "secure_token_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    fun saveToken(key: String, token: String) {
        prefs.edit().putString(key, token).apply()
    }
    
    fun loadToken(key: String): String? = prefs.getString(key, null)
    
    fun deleteToken(key: String) {
        prefs.edit().remove(key).apply()
    }
}
```

`EncryptedSharedPreferences`는 Jetpack Security 라이브러리가 Keystore 연동과 암호화를 묶어서 처리한다. 내부적으로 AES-256-GCM으로 값을 암호화하고, 암호화 키는 Keystore가 관리한다.

StrongBox를 명시적으로 요구하면 지원 기기에서 더 강한 보호를 받는다:

```kotlin
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .setRequestStrongBoxBacked(true)
    .build()
```

StrongBox가 없는 기기에서는 예외가 발생하므로, 지원 여부 확인 후 fallback 처리가 필요하다.

---

## SharedPreferences / UserDefaults에 저장하면 안 되는 이유

Android의 일반 SharedPreferences와 iOS의 UserDefaults는 평문 파일이다.

Android SharedPreferences 파일은 `/data/data/<package_name>/shared_prefs/<name>.xml`에 XML로 저장된다. 앱 샌드박스가 다른 앱의 접근을 막아주지만, root 권한이 있으면 그냥 읽힌다:

```xml
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <string name="access_token">eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...</string>
    <string name="refresh_token">dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...</string>
</map>
```

`adb backup` 명령으로 앱 데이터를 추출할 수 있는 기기도 있다. 앱 매니페스트에서 `android:allowBackup="true"`면 SharedPreferences 파일도 백업에 포함된다. 기본값이 true인 경우가 많아서 의도치 않게 노출된다.

iOS UserDefaults는 `Library/Preferences/<bundle_id>.plist`에 저장되고 iCloud 백업에 포함된다. 탈옥 기기에서는 파일 시스템에 직접 접근해 plist를 읽을 수 있다.

---

## 루팅/탈옥 환경에서의 토큰 탈취 경로

루팅과 탈옥이 위험한 이유는 OS 샌드박스가 무력화되기 때문이다.

**Android 루팅:**

Root 권한을 얻으면 모든 앱의 데이터 디렉토리에 접근할 수 있다. EncryptedSharedPreferences의 경우 파일 자체는 암호화되어 있지만, TEE가 없는 저가형 기기에서는 소프트웨어 Keystore를 쓰기 때문에 루팅 후 키 추출 가능성이 있다.

Frida 같은 동적 분석 도구를 루팅 기기에서 실행하면 앱 프로세스에 인젝션해서 메모리에서 직접 토큰을 읽을 수도 있다. 앱이 메모리에서 토큰을 복호화해 사용하는 순간에 후킹이 가능하다.

**iOS 탈옥:**

탈옥 환경에서 `kSecAttrAccessibleAlways` 또는 `kSecAttrAccessibleAfterFirstUnlock`으로 설정된 Keychain 항목은 Keychain Dumper 같은 도구로 전체 덤프가 가능하다.

`kSecAttrAccessibleWhenUnlockedThisDeviceOnly`도 완벽하지 않다. 탈옥 도구가 iOS 내부 API를 직접 호출해 Keychain에 접근하는 경우가 있다. 생체 인증 제약(`kSecAccessControlBiometryCurrentSet`)을 건 항목은 Face ID/Touch ID 하드웨어 모듈이 별도로 처리하기 때문에 탈옥 후에도 접근하기 어렵다.

**루팅/탈옥 감지:**

완벽한 방어는 없다. 감지를 우회하는 도구도 함께 발전한다. 공격 비용을 높이는 차원에서 구현하되, 감지 결과를 앱 내부에서만 처리하면 후킹으로 우회된다. 반드시 백엔드로 감지 토큰을 전달하고 서버에서 검증해야 한다.

Android는 Play Integrity API를 쓴다:

```kotlin
val integrityManager = IntegrityManagerFactory.create(context)
val request = StandardIntegrityManager.StandardIntegrityTokenRequest.builder()
    .setRequestHash(hashOfRequest)
    .build()

integrityManager.requestIntegrityToken(request)
    .addOnSuccessListener { response ->
        val integrityToken = response.token()
        // 이 토큰을 백엔드로 전송해 검증
        sendToBackend(integrityToken)
    }
```

루팅 기기나 에뮬레이터에서는 `MEETS_BASIC_INTEGRITY` 플래그가 내려오지 않는다. 백엔드에서 Google의 Play Integrity API로 검증하면 기기 무결성 상태를 확인할 수 있다.

iOS는 App Attest를 쓴다:

```swift
import DeviceCheck

DCAppAttestService.shared.generateKey { keyId, error in
    guard let keyId = keyId else { return }
    // keyId를 서버로 전송해 Attestation 요청
    requestAttestation(keyId: keyId)
}
```

---

## 백엔드 API 설계: 모바일 클라이언트를 고려한 토큰 수명

웹 SPA와 모바일 앱의 토큰 관리 방식은 다르다. 모바일을 별도로 고려해야 하는 부분이 있다.

**Access Token 수명:**

SPA에서는 메모리에 저장하고 15분~1시간이면 충분하다. 모바일 앱은 백그라운드에서 잠든 후 다시 열릴 때 토큰을 재사용하는 경우가 있다. Access Token이 너무 짧으면 네트워크 상태가 좋지 않은 환경(지하철, 터널)에서 재발급 요청이 실패할 때 사용자가 갑자기 로그아웃 상태가 된다. 모바일은 1~2시간 정도가 현실적이다.

**Refresh Token 수명과 디바이스별 관리:**

모바일 Refresh Token은 30~90일 이상으로 길게 쓰는 경우가 많다. 긴 Refresh Token은 탈취 시 위험 시간이 길기 때문에 Refresh Token Rotation과 디바이스별 관리가 필수다:

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL,  -- SHA-256 해시로 저장
    device_id VARCHAR(255),
    device_name VARCHAR(255),         -- "iPhone 15 Pro", "Galaxy S24"
    created_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP
);
```

```python
@router.post("/auth/token/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hash_token(request.refresh_token),
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    device_id = http_request.headers.get("X-Device-ID")
    if token_record.device_id and device_id != token_record.device_id:
        # 다른 기기에서 사용 시도 — 탈취 가능성
        notify_suspicious_activity(token_record.user_id, device_id)
    
    # Rotation: 기존 토큰 폐기, 새 토큰 발급
    token_record.revoked = True
    token_record.revoked_at = datetime.utcnow()
    
    new_refresh_token = generate_secure_token()
    db.add(RefreshToken(
        user_id=token_record.user_id,
        token_hash=hash_token(new_refresh_token),
        device_id=device_id,
        device_name=http_request.headers.get("X-Device-Name"),
        expires_at=datetime.utcnow() + timedelta(days=60)
    ))
    db.commit()
    
    return {
        "access_token": create_access_token(token_record.user_id),
        "refresh_token": new_refresh_token
    }
```

**Client Secret 문제:**

OAuth2 Confidential Client는 Client Secret을 앱에 포함하면 안 된다. APK를 역공학하면 추출된다. 모바일 앱은 Public Client로 취급하고 PKCE(Proof Key for Code Exchange)를 사용한다:

```
# 인증 요청 시
code_verifier = <랜덤 고엔트로피 문자열>
code_challenge = BASE64URL(SHA256(code_verifier))

# Authorization Request에 포함
?code_challenge=<code_challenge>&code_challenge_method=S256

# 토큰 요청 시
code_verifier=<원본 code_verifier>
```

백엔드에서 `code_verifier` 없이 Authorization Code만으로 토큰을 발급하는 엔드포인트를 열면 안 된다. PKCE를 강제로 요구해야 한다.

**디바이스 관리 API:**

사용자가 로그인된 디바이스 목록을 보고 특정 디바이스의 세션을 종료할 수 있어야 한다. 기기를 분실했을 때 원격 로그아웃이 가능해야 한다:

```python
@router.get("/auth/devices")
async def list_devices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).all()
    
    return [
        {
            "device_id": t.device_id,
            "device_name": t.device_name,
            "last_used_at": t.last_used_at,
        }
        for t in tokens
    ]

@router.delete("/auth/devices/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.device_id == device_id
    ).update({"revoked": True, "revoked_at": datetime.utcnow()})
    db.commit()
```

---

## 저장 방식 요약

| 저장소 | OS | 암호화 | 루팅/탈옥 시 | 권장 용도 |
|---|---|---|---|---|
| Keychain (`WhenUnlockedThisDeviceOnly`) | iOS | 하드웨어 | 일부 노출 가능 | Access/Refresh Token |
| Keychain + BiometryCurrentSet | iOS | 하드웨어 + 생체 | 노출 어려움 | 고보안 토큰 |
| EncryptedSharedPreferences | Android | AES-256-GCM | TEE 없는 기기는 위험 | Access/Refresh Token |
| SharedPreferences | Android | 없음 | 즉시 노출 | 사용 금지 |
| UserDefaults | iOS | 없음 | 즉시 노출 | 사용 금지 |
| 메모리 변수 | 공통 | N/A | 앱 종료 시 소멸 | Access Token (단기) |
