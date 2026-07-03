---
title: FCM (Firebase Cloud Messaging)
tags: [backend, messaging, fcm, push, firebase, apns, node, firebase-admin]
updated: 2026-06-15
---

# FCM (Firebase Cloud Messaging)

## 개요

FCM은 구글이 운영하는 푸시 메시지 전송 인프라다. 서버에서 모바일 기기나 웹 브라우저로 푸시를 보내려면 직접 APNs(애플)나 자체 웹 푸시 게이트웨이를 다루는 대신 FCM에 메시지를 던지고, FCM이 각 플랫폼의 푸시 채널로 중계한다.

서버 입장에서 다뤄야 하는 건 크게 세 가지다. 인증(서버가 FCM에 어떻게 신원을 증명하나), 토큰 관리(어느 기기로 보낼지 식별하는 registration token), 페이로드 구성(notification이냐 data냐, 우선순위와 TTL을 어떻게 줄 것이냐). 이 셋이 실무에서 거의 모든 문제의 출처다.

## 인증: Legacy 서버 키 vs HTTP v1 API

오래된 코드와 새 코드가 섞여 있으면 가장 먼저 헷갈리는 부분이다. 전송 방식이 두 가지였고, 인증 체계가 완전히 다르다.

### Legacy 서버 키 (deprecated)

예전 방식은 프로젝트마다 발급되는 고정 문자열인 서버 키를 HTTP 헤더에 그대로 박아 보냈다.

```
POST https://fcm.googleapis.com/fcm/send
Authorization: key=AAAA....(서버 키)
Content-Type: application/json
```

키 하나만 있으면 누구나 전송할 수 있어서 유출되면 그대로 악용된다. 구글이 2024년에 Legacy HTTP/XMPP API를 종료했기 때문에 신규 구축에서는 쓸 일이 없다. 기존 서비스가 아직 `key=...` 방식을 쓰고 있다면 v1으로 마이그레이션해야 한다. 응답 포맷도 다르고(`results` 배열에 `error` 문자열), 엔드포인트도 `/fcm/send`라 v1과 코드를 공유할 수 없다.

### HTTP v1 API (현재 표준)

v1은 OAuth2 액세스 토큰으로 인증한다. 서비스 계정 JSON으로 짧게 유효한 액세스 토큰을 발급받아 Bearer로 보낸다.

```
POST https://fcm.googleapis.com/v1/projects/{project-id}/messages:send
Authorization: Bearer ya29.....(OAuth2 access token, 약 1시간 유효)
Content-Type: application/json
```

액세스 토큰은 1시간이면 만료되므로 발급·갱신을 직접 관리해야 한다. firebase-admin SDK를 쓰면 이 토큰 캐싱과 갱신을 알아서 처리하기 때문에 직접 OAuth2 흐름을 구현할 일은 거의 없다. SDK 없이 REST를 직접 호출하는 환경(예: 다른 언어, 서버리스 함수에서 의존성 줄이기)에서만 google-auth 라이브러리로 토큰을 발급받아 캐싱하면 된다.

두 방식의 페이로드 구조도 다르다. Legacy는 `to`, `data`, `notification`이 최상위에 있었지만 v1은 모든 게 `message` 객체 안으로 들어가고 플랫폼별 설정이 `android`, `apns`, `webpush`로 분리된다.

```json
{
  "message": {
    "token": "디바이스_registration_token",
    "notification": { "title": "제목", "body": "내용" },
    "android": { "priority": "high" },
    "apns": { "headers": { "apns-priority": "10" } }
  }
}
```

## 서비스 계정 JSON으로 인증

Firebase 콘솔의 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성에서 JSON 파일을 받는다. 이 파일에 `private_key`가 들어있어서 사실상 서버 권한 전체를 가진 비밀이다. Git에 커밋하면 안 되고, 환경변수나 시크릿 매니저로 주입한다.

```javascript
const admin = require('firebase-admin');

// 방법 1: 파일 경로 (GOOGLE_APPLICATION_CREDENTIALS 환경변수)
// export GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/fcm-sa.json
admin.initializeApp({
  credential: admin.credential.applicationDefault(),
});

// 방법 2: JSON 문자열을 환경변수로 주입해서 파싱
const serviceAccount = JSON.parse(process.env.FCM_SERVICE_ACCOUNT);
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});
```

방법 2를 쓸 때 `private_key`의 줄바꿈 처리에서 한 번씩 막힌다. 환경변수에 넣으면 `\n`이 literal 두 글자로 들어가서 키 파싱이 깨진다. 그럴 때는 복원해줘야 한다.

```javascript
const raw = JSON.parse(process.env.FCM_SERVICE_ACCOUNT);
raw.private_key = raw.private_key.replace(/\\n/g, '\n');
admin.initializeApp({ credential: admin.credential.cert(raw) });
```

`initializeApp`은 프로세스당 한 번만 호출한다. 람다나 서버리스에서 콜드 스타트마다 호출되면 `app/duplicate-app` 에러가 나므로 이미 초기화됐는지 확인하는 가드를 둔다.

```javascript
if (!admin.apps.length) {
  admin.initializeApp({ credential: admin.credential.cert(raw) });
}
```

## 토큰 발급과 갱신·만료 처리

registration token은 앱 인스턴스(설치된 앱 + 기기 조합) 하나를 가리키는 식별자다. 클라이언트 SDK가 발급하고, 클라이언트가 서버로 보내 저장한다. 서버는 이 토큰으로만 특정 기기를 지정해 보낼 수 있다.

토큰은 영구적이지 않다. 앱 재설치, 데이터 삭제, 일정 기간 미사용, 기기 복원 등으로 무효화되거나 새 토큰으로 갱신된다. 클라이언트는 갱신 콜백(`onTokenRefresh` 계열)에서 새 토큰을 받아 서버에 다시 등록하고, 서버는 갱신을 반영한다.

플랫폼별로 발급 경로가 조금씩 다르다.

- Android/iOS: Firebase SDK의 `getToken()`으로 발급. iOS는 APNs 토큰을 FCM이 내부적으로 매핑하므로 앱에 APNs 인증 키(.p8)를 Firebase 콘솔에 등록해둬야 토큰이 정상 발급된다. 이 설정이 빠지면 iOS만 푸시가 안 와서 한참 헤맨다.
- Web: Service Worker + VAPID 키 기반으로 `getToken({ vapidKey })`로 발급. 브라우저 알림 권한을 사용자가 거부하면 토큰이 안 나온다.

서버가 알아둘 핵심은, 토큰 무효화는 클라이언트가 알려주기 전에 전송 시점에 발견되는 경우가 많다는 점이다. 갱신 콜백이 항상 도달하는 건 아니라서, 전송 실패 응답을 보고 DB를 정리하는 로직이 토큰 관리의 실질적인 본체가 된다.

## data 메시지 vs notification 메시지

이 차이를 모르고 넘어가면 "포그라운드에서는 푸시가 오는데 백그라운드에서는 안 온다" 또는 그 반대 증상으로 디버깅에 시간을 버린다.

`notification` 메시지는 title/body가 들어간 표시용 메시지다. 앱이 백그라운드나 종료 상태일 때 OS(또는 Android의 경우 FCM SDK)가 자동으로 알림 트레이에 표시한다. 이때 앱 코드는 실행되지 않는다.

`data` 메시지는 키-값 쌍만 들어간 메시지로, 표시는 OS가 자동으로 하지 않는다. 항상 앱 코드(핸들러)로 전달돼서, 알림을 띄울지 말지, 어떤 화면으로 보낼지를 앱이 직접 결정한다.

동작 차이를 정리하면 이렇다.

| 상태 | notification만 | data만 | 둘 다 |
|------|---------------|--------|-------|
| 포그라운드 | 앱 핸들러로 전달 (자동 표시 안 함) | 앱 핸들러로 전달 | 앱 핸들러로 전달 |
| 백그라운드/종료 | OS가 자동 표시, 탭하면 앱 실행 | 백그라운드 핸들러로 전달 (Android), iOS는 제약 있음 | notification은 자동 표시, data는 탭 시 함께 전달 |

실무 결론은 보통 둘 중 하나다. 알림 표시는 OS에 맡기고 클릭 시 라우팅 정보만 필요하면 `notification` + `data`를 같이 보낸다. 표시 여부와 모양을 앱이 완전히 통제해야 하면 `data`만 보내고 클라이언트에서 로컬 알림으로 띄운다.

iOS에서 백그라운드 data 메시지를 받으려면 `apns.payload.aps.content-available = 1`(content-available 플래그)을 줘야 하고, 그래도 OS가 전달을 보장하지는 않는다. 백그라운드 data 전달을 자주 놓치는 게 iOS의 알려진 제약이다.

## Node.js firebase-admin로 전송

### 단건 전송

```javascript
const admin = require('firebase-admin');

async function sendToDevice(token, { title, body, data }) {
  const message = {
    token,
    notification: { title, body },
    data: data ?? {}, // data 값은 모두 문자열이어야 한다
    android: { priority: 'high' },
    apns: {
      headers: { 'apns-priority': '10' },
      payload: { aps: { sound: 'default' } },
    },
  };
  const messageId = await admin.messaging().send(message);
  return messageId; // projects/.../messages/0:1500...
}
```

`data`의 값은 반드시 문자열이다. 숫자나 객체를 넣으면 전송 단계에서 에러가 난다. 객체를 보내야 하면 `JSON.stringify`해서 넣고 클라이언트에서 파싱한다.

### 배치 전송 (멀티캐스트)

같은 메시지를 여러 토큰에 보낼 때 `sendEachForMulticast`를 쓴다. 한 호출에 토큰 최대 500개까지 받는다. 더 많으면 500개 단위로 쪼갠다.

```javascript
async function sendMulticast(tokens, payload) {
  const results = [];
  for (let i = 0; i < tokens.length; i += 500) {
    const chunk = tokens.slice(i, i + 500);
    const res = await admin.messaging().sendEachForMulticast({
      tokens: chunk,
      notification: { title: payload.title, body: payload.body },
      data: payload.data ?? {},
      android: { priority: 'high' },
    });
    results.push({ chunk, res });
  }
  return results;
}
```

`sendEachForMulticast`는 토큰별로 개별 전송을 묶어 처리하기 때문에 일부만 실패하는 게 정상이다. 응답의 `responses` 배열이 입력 토큰 순서와 1:1로 대응하고, 각 항목에 `success` 불리언과 실패 시 `error`가 들어있다. 전체가 실패하지 않는 한 예외를 던지지 않으므로, 반환값을 반드시 순회해서 실패를 처리해야 한다.

서로 다른 메시지를 여러 개 보낼 때는 `sendEach(messages[])`를 쓴다. 메시지 객체 배열을 받고 역시 토큰당 부분 실패가 가능하다. 과거의 `sendMulticast`/`sendAll`은 내부적으로 batch 엔드포인트를 쓰는 구버전이고, 현재는 `sendEachForMulticast`/`sendEach`가 권장된다.

## 전송 실패 응답 처리와 만료 토큰 DB 정리

부분 실패를 어떻게 처리하느냐가 토큰 위생을 좌우한다. 만료된 토큰을 계속 들고 있으면 전송량이 불필요하게 늘고, 통계가 왜곡되고, 일부 한도에도 영향을 준다.

핵심 에러 코드 두 개를 구분해야 한다.

- `messaging/registration-token-not-registered` (v1의 `UNREGISTERED`): 토큰이 더는 유효하지 않다. 앱 삭제, 토큰 만료 등. **DB에서 삭제한다.**
- `messaging/invalid-registration-token` / `messaging/invalid-argument`: 토큰 형식 자체가 잘못됨. 역시 **삭제 대상**이지만, 우리 코드가 토큰을 잘못 저장했을 가능성도 봐야 한다.
- `messaging/mismatched-credential` (`SENDER_ID_MISMATCH`): 토큰이 다른 Firebase 프로젝트(다른 발신자 ID)에서 발급된 것. 보통 앱의 google-services 설정과 서버의 서비스 계정 프로젝트가 어긋났을 때 난다. 토큰을 지우기 전에 **설정 불일치부터 의심**해야 한다. 멀쩡한 토큰을 다 지워버리는 사고가 여기서 난다.
- `messaging/quota-exceeded`, 일시적 5xx, `messaging/server-unavailable`: 토큰 문제가 아니라 일시 장애. **삭제하지 말고 재시도** 대상이다.

```javascript
const DELETE_CODES = new Set([
  'messaging/registration-token-not-registered',
  'messaging/invalid-registration-token',
  'messaging/invalid-argument',
]);

async function sendAndCleanup(tokens, payload, db) {
  const res = await admin.messaging().sendEachForMulticast({
    tokens,
    notification: { title: payload.title, body: payload.body },
    android: { priority: 'high' },
  });

  const toDelete = [];
  const toRetry = [];
  res.responses.forEach((r, idx) => {
    if (r.success) return;
    const code = r.error?.code;
    if (DELETE_CODES.has(code)) {
      toDelete.push(tokens[idx]);
    } else if (code === 'messaging/mismatched-credential') {
      // 설정 불일치 의심 — 자동 삭제하지 말고 로깅 후 알림
      console.warn('SENDER_ID_MISMATCH', tokens[idx]);
    } else {
      toRetry.push(tokens[idx]); // 일시 장애로 보고 재시도 큐로
    }
  });

  if (toDelete.length) {
    await db.deleteTokens(toDelete); // DELETE FROM device_tokens WHERE token IN (...)
  }
  return { sent: res.successCount, deleted: toDelete.length, retry: toRetry };
}
```

`mismatched-credential`을 삭제 목록에 넣지 않은 게 핵심이다. 이 코드가 대량으로 뜨면 토큰이 잘못된 게 아니라 배포 설정이 어긋난 것이다. 자동 삭제하면 정상 사용자 토큰을 전부 날린다.

## 우선순위와 iOS APNs 헤더

`priority`는 메시지를 즉시 깨워 전달할지(`high`), 기기 상태에 맞춰 미룰지(`normal`)를 정한다. `normal`은 도즈 모드 등에서 배터리를 아끼려고 전달이 지연될 수 있다. 채팅 메시지, OTP처럼 즉시성이 필요하면 `high`, 마케팅·요약 알림이면 `normal`을 쓴다. `high`를 남발하면 구글이 전달을 조절하기도 하고 배터리 영향도 커진다.

플랫폼별로 헤더 위치가 다르다.

- Android: `android.priority = "high" | "normal"`
- iOS(APNs): `apns.headers["apns-priority"]`. `"10"`이 즉시(high), `"5"`가 절전(normal)에 대응한다. content-available로 백그라운드만 깨우는 무음 푸시는 `apns-priority`를 `"5"`로 줘야 한다(애플이 `"10"`을 거부하는 경우가 있다).

```javascript
// 무음 백그라운드 데이터 푸시 (iOS)
const silent = {
  token,
  data: { type: 'sync', payload: '...' },
  apns: {
    headers: { 'apns-priority': '5' },
    payload: { aps: { 'content-available': 1 } }, // notification 없이 앱만 깨움
  },
  android: { priority: 'high' },
};
```

content-available 푸시는 사용자에게 보이지 않게 앱을 깨워 백그라운드 작업을 시키는 용도다. iOS는 이 무음 푸시의 빈도를 시스템이 제한하므로 자주 보내도 다 전달되지 않는다는 걸 전제로 설계해야 한다.

## 페이로드 크기 제한과 TTL

전체 메시지 페이로드는 4KB(notification + data 합산, 일부 무음 푸시 케이스는 더 작음)로 제한된다. 큰 데이터를 통째로 푸시에 실으면 안 되고, 넘으면 전송 단계에서 에러가 난다. 실무에서는 푸시에 식별자(예: `postId`)만 넣고 앱이 그걸로 API를 호출해 본문을 가져오는 방식을 쓴다. 푸시는 "이벤트가 났다"는 신호로 보고, 데이터 동기화는 별도 API로 분리하는 게 안전하다.

TTL은 메시지가 전달되지 못할 때 FCM이 얼마나 보관·재시도할지를 정한다. 기본값은 약 4주다. 기기가 오프라인이면 그동안 보관했다가 온라인이 되면 전달한다. 시의성이 짧은 메시지(실시간 위치, 잠깐 유효한 코드)는 TTL을 짧게 줘서 늦게 도착하는 걸 막는다.

```javascript
const message = {
  token,
  data: { code: '123456' },
  android: { ttl: 300 * 1000 }, // 밀리초 단위, 5분
  apns: { headers: { 'apns-expiration': String(Math.floor(Date.now() / 1000) + 300) } }, // 유닉스 초
};
```

플랫폼마다 단위가 달라서 한 번씩 틀린다. Android `ttl`은 밀리초, APNs `apns-expiration`은 만료 시각의 유닉스 초(epoch)다. 0을 주면 "지금 전달 못 하면 버려라"는 뜻이라 오프라인 기기에는 안 간다.

## 토픽 구독과 멀티캐스트의 선택

토픽은 클라이언트가 특정 주제를 구독해두면 서버가 토큰 목록 없이 주제 이름만으로 전체 구독자에게 보내는 방식이다. "공지사항", "지역_서울" 같은 브로드캐스트성 푸시에 맞는다.

```javascript
// 서버에서 토큰을 토픽에 구독시키기 (또는 클라이언트 SDK에서 직접)
await admin.messaging().subscribeToTopic(tokens, 'notice');

// 토픽으로 전송
await admin.messaging().send({
  topic: 'notice',
  notification: { title: '점검 안내', body: '오늘 02시 점검' },
});

// 조건식도 가능 (구독 토픽 조합)
await admin.messaging().send({
  condition: "'notice' in topics && 'seoul' in topics",
  notification: { title: '...', body: '...' },
});
```

토픽은 서버가 토큰을 관리하지 않아도 되는 대신, 누구에게 보냈는지 추적하거나 개인화하기 어렵다. 토픽 구독 반영에 지연이 있어서 방금 구독한 기기가 바로 다음 푸시를 못 받기도 한다. 정확히 이 사용자들에게만, 사용자별로 다른 내용을 보내야 하면 토큰 기반 멀티캐스트가 맞다. 불특정 다수에게 같은 내용을 보내면 토픽이 운영 부담이 적다.

## 토큰 저장·중복·디바이스 단위 관리

실무에서 가장 지저분해지는 부분이다. 토큰을 단순히 user당 하나로 저장하면 금방 문제가 생긴다.

한 사용자가 폰, 태블릿, 웹 등 여러 기기를 쓰면 토큰이 여러 개다. user당 토큰 하나로 덮어쓰면 마지막 로그인 기기에만 푸시가 간다. 그래서 (user_id, token) 또는 (user_id, device_id, token) 단위로 저장하고 한 사용자에게 보낼 때 그 사용자의 모든 토큰으로 멀티캐스트해야 한다.

중복도 골칫거리다. 같은 기기가 토큰을 갱신하면 옛 토큰과 새 토큰이 둘 다 DB에 남아 한 번 보낼 걸 두 번 보낸다. 사용자에게 알림이 두 개씩 오는 증상이 여기서 나온다. 가능하면 클라이언트가 안정적인 기기 식별자(`device_id`)를 같이 보내서 (user_id, device_id)를 유니크 키로 잡고 토큰을 upsert한다.

```sql
CREATE TABLE device_tokens (
  user_id     BIGINT      NOT NULL,
  device_id   VARCHAR(64) NOT NULL,
  token       TEXT        NOT NULL,
  platform    VARCHAR(16) NOT NULL, -- android | ios | web
  updated_at  TIMESTAMP   NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, device_id)
);
-- 같은 기기가 토큰을 갱신하면 토큰만 교체 (중복 행이 안 생긴다)
INSERT INTO device_tokens (user_id, device_id, token, platform, updated_at)
VALUES ($1, $2, $3, $4, now())
ON CONFLICT (user_id, device_id)
DO UPDATE SET token = EXCLUDED.token, updated_at = now();
```

device_id를 못 받는 환경(웹 일부, 토큰만 오는 레거시 클라이언트)이면 차선으로 토큰 자체를 유니크 키로 잡는다. 다만 토큰은 갱신될 때 새 값이라서, 옛 토큰 정리는 결국 전송 실패의 `UNREGISTERED`에 의존하게 된다. 그래서 정기적으로 오래 미사용된 토큰을 솎아내는 배치(예: `updated_at`이 일정 기간 지난 행 정리)와 전송 실패 기반 삭제를 같이 돌리는 게 현실적이다.

토큰 정리에서 한 가지 더. `UNREGISTERED`로 토큰을 지울 때 그 토큰이 막 갱신된 직후라면, 새 토큰은 살리고 옛 토큰만 지워야 한다. (user_id, device_id) 키로 관리하면 새 토큰이 같은 행을 덮어써서 옛 토큰이 자연히 사라지므로 이 문제가 줄어든다. 토큰 자체를 키로 쓰면 삭제 시 "방금 등록된 새 토큰"을 실수로 지우지 않도록 삭제 대상 토큰이 현재 DB의 그 토큰과 일치하는지 확인하고 지운다.
