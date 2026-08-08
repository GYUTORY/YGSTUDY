---
title: 모바일 앱 토큰 저장 보안
tags: [security, auth]
updated: 2026-08-07
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

enum KeychainError: Error {
    case itemNotFound
    case duplicateItem
    case unexpectedStatus(OSStatus)
}

final class TokenKeychain {
    private let service: String
    private let accessGroup: String?

    init(service: String = Bundle.main.bundleIdentifier ?? "app", accessGroup: String? = nil) {
        self.service = service
        self.accessGroup = accessGroup
    }

    func save(_ token: String, for key: String) throws {
        guard let data = token.data(using: .utf8) else { return }

        var query = baseQuery(for: key)
        query[kSecValueData as String] = data

        let status = SecItemAdd(query as CFDictionary, nil)

        if status == errSecDuplicateItem {
            try update(data, for: key)
        } else if status != errSecSuccess {
            throw KeychainError.unexpectedStatus(status)
        }
    }

    func load(key: String) throws -> String {
        var query = baseQuery(for: key)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw KeychainError.itemNotFound
        }
        return token
    }

    func delete(key: String) throws {
        let query = baseQuery(for: key)
        let status = SecItemDelete(query as CFDictionary)
        if status != errSecSuccess && status != errSecItemNotFound {
            throw KeychainError.unexpectedStatus(status)
        }
    }

    private func update(_ data: Data, for key: String) throws {
        let query = baseQuery(for: key)
        let attributes: [String: Any] = [kSecValueData as String: data]
        let status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status != errSecSuccess {
            throw KeychainError.unexpectedStatus(status)
        }
    }

    private func baseQuery(for key: String) -> [String: Any] {
        var query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        if let group = accessGroup {
            query[kSecAttrAccessGroup as String] = group
        }
        return query
    }
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

`kSecAttrAccessGroup`을 지정하면 같은 Team ID의 앱과 App Extension 간에 Keychain을 공유할 수 있다. 위젯이나 Share Extension에서 토큰이 필요한 경우에 쓴다. 공유 그룹 범위가 넓어질수록 공격 표면도 넓어지니 최소한으로 설정해야 한다.

고보안 토큰에는 `SecAccessControl`로 생체 인증을 추가로 요구할 수 있다:

```swift
import LocalAuthentication

func saveWithBiometry(_ token: String, key: String) throws {
    guard let data = token.data(using: .utf8) else { return }

    var error: Unmanaged<CFError>?
    guard let access = SecAccessControlCreateWithFlags(
        nil,
        kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
        .biometryCurrentSet,
        &error
    ) else {
        throw error!.takeRetainedValue() as Error
    }

    let context = LAContext()
    context.localizedReason = "토큰 저장 보안 인증"

    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: "com.example.app",
        kSecAttrAccount as String: key,
        kSecValueData as String: data,
        kSecAttrAccessControl as String: access,
        kSecUseAuthenticationContext as String: context
    ]

    let status = SecItemAdd(query as CFDictionary, nil)
    if status != errSecSuccess {
        throw KeychainError.unexpectedStatus(status)
    }
}
```

`.biometryCurrentSet`은 등록된 생체 정보가 변경되면 자동으로 접근을 차단한다. Face ID 재등록이나 지문 추가 후 재인증이 강제되므로, 기기를 타인에게 넘겨준 뒤 생체 정보를 교체해도 기존 토큰에 접근할 수 없다.

`LAContext`를 미리 생성해서 `kSecUseAuthenticationContext`에 넘기면 저장/조회 시 보여주는 생체 인증 팝업의 문구를 제어할 수 있다. 넘기지 않으면 시스템 기본 문구가 나온다.

---

## Android Keystore

Android Keystore System은 암호화 키를 앱 프로세스 밖에서 관리한다. TEE(Trusted Execution Environment) 또는 StrongBox(별도 보안 칩)가 있는 기기에서는 키가 하드웨어에 격리된다. 앱이 키를 직접 꺼낼 수 없고, Keystore를 통해 암호화/복호화만 요청한다.

토큰 자체는 EncryptedSharedPreferences에 저장하고, 암호화 키만 Keystore에서 관리하는 패턴이 일반적이다:

```kotlin
import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class TokenStorage(private val context: Context) {

    private val prefs by lazy { buildPrefs(strongBoxBacked = true) }

    private fun buildPrefs(strongBoxBacked: Boolean) = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .setRequestStrongBoxBacked(strongBoxBacked)
            .build()

        EncryptedSharedPreferences.create(
            context,
            "secure_token_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        if (strongBoxBacked) {
            // StrongBox 미지원 기기: TEE fallback
            buildPrefs(strongBoxBacked = false)
        } else {
            throw e
        }
    }

    fun save(key: String, token: String) = prefs.edit().putString(key, token).apply()

    fun load(key: String): String? = prefs.getString(key, null)

    fun delete(key: String) = prefs.edit().remove(key).apply()

    fun clear() = prefs.edit().clear().apply()
}
```

StrongBox가 없는 기기에서 `setRequestStrongBoxBacked(true)`를 설정하면 예외가 발생한다. 위 코드처럼 `strongBoxBacked = false`로 재시도하면 TEE로 자동 fallback된다.

실제 키가 하드웨어에 올라갔는지 확인하는 방법:

```kotlin
import android.security.keystore.KeyInfo
import java.security.KeyStore
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory

fun isKeyHardwareBacked(keyAlias: String): Boolean {
    return try {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val key = keyStore.getKey(keyAlias, null) as? SecretKey ?: return false
        val factory = SecretKeyFactory.getInstance(key.algorithm, "AndroidKeyStore")
        val keyInfo = factory.getKeySpec(key, KeyInfo::class.java) as KeyInfo
        keyInfo.securityLevel == KeyProperties.SECURITY_LEVEL_TRUSTED_ENVIRONMENT
                || keyInfo.securityLevel == KeyProperties.SECURITY_LEVEL_STRONGBOX
    } catch (e: Exception) {
        false
    }
}
```

`SECURITY_LEVEL_STRONGBOX`면 물리적으로 분리된 보안 칩에 키가 있다. `SECURITY_LEVEL_TRUSTED_ENVIRONMENT`면 TEE다. `SECURITY_LEVEL_SOFTWARE`가 나오면 소프트웨어 Keystore다. 루팅 기기에서 소프트웨어 Keystore를 쓰면 키 추출 가능성이 있다.

고보안 토큰은 BiometricPrompt와 Keystore를 직접 연동해 암호화한다:

```kotlin
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.biometric.BiometricPrompt
import androidx.fragment.app.FragmentActivity
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

class BiometricTokenStorage(private val activity: FragmentActivity) {

    private val KEY_ALIAS = "biometric_token_key"
    private val KEYSTORE = "AndroidKeyStore"

    fun generateKey() {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        if (keyStore.containsAlias(KEY_ALIAS)) return

        KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).apply {
            init(
                KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
                )
                    .setBlockModes(KeyProperties.BLOCK_MODE_CBC)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_PKCS7)
                    .setUserAuthenticationRequired(true)
                    .setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
                    .setInvalidatedByBiometricEnrollment(true)
                    .build()
            )
            generateKey()
        }
    }

    fun encryptWithBiometric(plaintext: String, onSuccess: (ByteArray, ByteArray) -> Unit) {
        val cipher = getCipher()
        val secretKey = getSecretKey()
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)

        val cryptoObject = BiometricPrompt.CryptoObject(cipher)
        val prompt = BiometricPrompt(activity, activity.mainExecutor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    val encryptedBytes = result.cryptoObject?.cipher?.doFinal(
                        plaintext.toByteArray(Charsets.UTF_8)
                    ) ?: return
                    onSuccess(encryptedBytes, cipher.iv)
                }
            }
        )

        prompt.authenticate(
            BiometricPrompt.PromptInfo.Builder()
                .setTitle("토큰 저장 인증")
                .setNegativeButtonText("취소")
                .build(),
            cryptoObject
        )
    }

    private fun getCipher() = Cipher.getInstance(
        "${KeyProperties.KEY_ALGORITHM_AES}/${KeyProperties.BLOCK_MODE_CBC}/${KeyProperties.ENCRYPTION_PADDING_PKCS7}"
    )

    private fun getSecretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        return keyStore.getKey(KEY_ALIAS, null) as SecretKey
    }
}
```

`setInvalidatedByBiometricEnrollment(true)`를 설정하면 새 지문이나 얼굴 등록 시 기존 키가 자동으로 무효화된다. iOS의 `.biometryCurrentSet`과 동일한 효과다.

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
| Keystore + BiometricPrompt | Android | 하드웨어 + 생체 | 노출 어려움 | 고보안 토큰 |
| SharedPreferences | Android | 없음 | 즉시 노출 | 사용 금지 |
| UserDefaults | iOS | 없음 | 즉시 노출 | 사용 금지 |
| 메모리 변수 | 공통 | N/A | 앱 종료 시 소멸 | Access Token (단기) |
