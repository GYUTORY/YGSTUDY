---
title: APNs (Apple Push Notification service) 직접 연동
tags: [backend, messaging, apns, push, ios, jwt, http2, node]
updated: 2026-06-15
---

# APNs (Apple Push Notification service) 직접 연동

## 개요

APNs는 애플이 운영하는 푸시 게이트웨이다. iOS, iPadOS, macOS, watchOS 기기로 가는 모든 푸시는 결국 여기를 거친다. FCM을 써도 iOS 푸시는 FCM이 뒤에서 APNs로 다시 던지는 구조라, 애플 채널을 직접 들고 있느냐 FCM에 위임하느냐의 차이일 뿐 종착지는 같다.

이 문서는 서버가 APNs에 직접 붙는 경우를 다룬다. [FCM 문서](FCM.md)는 FCM 중계를 기준으로 하고 `apns` 헤더를 일부만 건드리는데, 직접 연동에서는 인증·엔드포인트·헤더·페이로드·에러 응답을 전부 서버가 책임진다.

서버가 다뤄야 하는 건 네 덩어리다. 인증(.p8 토큰 vs .p12 인증서), HTTP/2 연결과 엔드포인트, 요청 헤더(`apns-topic`, `apns-push-type` 등), 그리고 응답 코드와 reason 처리. 토큰 발급/캐싱과 410 만료 토큰 정리가 실무에서 가장 자주 사고가 나는 지점이다.

## 인증: .p8 토큰 vs .p12 인증서

두 방식이 있고, 신규 구축이면 거의 항상 .p8을 쓴다.

### .p8 (토큰 기반 JWT 인증)

Apple Developer 계정에서 발급하는 인증 키 파일이다. `AuthKey_XXXXXXXXXX.p8` 형태로 한 번 다운로드되고 재다운로드가 안 되므로, 받는 즉시 시크릿 매니저에 넣어둬야 한다. 분실하면 키를 폐기하고 새로 발급받는 수밖에 없다.

이 키로 ES256 서명한 JWT(provider token)를 만들어 매 요청 `authorization: bearer <jwt>` 헤더에 싣는다. 키 하나로 한 팀(Team)의 모든 앱, development/production 양쪽을 다 커버한다. 인증서 방식과 달리 만료가 없다(키를 사람이 폐기하기 전까지).

JWT에 필요한 값은 세 가지다.

- Key ID (`kid`): .p8 키의 10자리 식별자. 파일명에도 들어있다.
- Team ID (`iss`): Apple Developer 계정의 팀 식별자, 10자리.
- 발급 시각 (`iat`): 유닉스 초.

```javascript
const jwt = require('jsonwebtoken');
const fs = require('fs');

const key = fs.readFileSync('./AuthKey_ABC1234567.p8');

function makeProviderToken() {
  return jwt.sign(
    { iss: 'TEAMID1234', iat: Math.floor(Date.now() / 1000) },
    key,
    {
      algorithm: 'ES256',
      header: { alg: 'ES256', kid: 'ABC1234567' },
    },
  );
}
```

### .p12 (인증서 기반 인증)

예전 방식이다. 앱마다 별도의 푸시 인증서를 발급받아 .p12로 내보내고, TLS 클라이언트 인증서로 연결을 맺는다. 인증서가 앱(번들 ID)에 묶여 있어서 앱이 늘어나면 인증서도 늘어나고, 1년마다 만료돼서 갱신을 까먹으면 그날 푸시가 통째로 멈춘다. 만료 모니터링을 따로 걸어둬야 하는 게 가장 큰 부담이다.

VoIP 푸시처럼 .p12에서만 쓰던 별도 인증서가 있었지만, 지금은 .p8 토큰 + `apns-push-type: voip`로 다 처리된다. 기존 서비스가 .p12를 쓰고 있는 게 아니라면 새로 .p12를 도입할 이유는 없다.

### 어느 쪽을 쓰나

- 신규: .p8. 키 하나로 끝나고 만료 갱신 사고가 없다.
- 기존 .p12 운영 중: 굳이 급하게 바꿀 필요는 없지만, 인증서 만료 알림이 잘 걸려 있는지부터 확인한다. 앱이 여러 개로 늘어나는 시점이 .p8 전환의 적기다.

## provider 토큰 발급과 캐싱

여기서 사고가 자주 난다. JWT는 매 요청 새로 만들면 안 된다. 애플이 토큰 생성 빈도에 제한을 두고 있어서, 너무 자주 새 JWT를 만들어 보내면 `429 TooManyProviderTokenUpdates`로 거절당한다.

규칙은 단순하다. **토큰은 발급 후 한동안 재사용하고, 일정 주기로만 갱신한다.** 애플은 토큰이 발급 시각(`iat`) 기준 1시간을 넘으면 `403 ExpiredProviderToken`으로 거절한다. 그래서 보통 **20~50분 주기로 한 번씩만 새로 만들어 캐싱**하는 식으로 잡는다. 매 요청 생성(거절)과 1시간 초과(거절) 사이의 안전 구간이다.

```javascript
let cached = { token: null, iat: 0 };

function getProviderToken() {
  const now = Math.floor(Date.now() / 1000);
  // 발급 후 ~50분 지났으면 갱신
  if (!cached.token || now - cached.iat > 50 * 60) {
    cached = { token: makeProviderToken(), iat: now };
  }
  return cached.token;
}
```

멀티 인스턴스로 띄우면 인스턴스마다 각자 토큰을 캐싱한다. 인스턴스 수만큼 토큰이 생기는 건 정상이고, 문제되지 않는다. 문제는 한 인스턴스 안에서 요청마다 새로 만드는 경우다.

`iat`를 미래로 주면 `403 InvalidProviderToken` 비슷하게 거절되니, 서버 시계가 틀어져 있으면 멀쩡한 키도 안 먹는다. NTP가 맞는지 한 번 의심해볼 가치가 있다.

## HTTP/2 엔드포인트와 development/production 분리

APNs는 HTTP/2로만 받는다. HTTP/1.1로는 연결 자체가 안 된다. 그리고 환경이 두 개로 갈린다.

- production: `https://api.push.apple.com` (포트 443 또는 2197)
- development(sandbox): `https://api.sandbox.push.apple.com`

이 둘은 **디바이스 토큰이 호환되지 않는다.** 이게 APNs 직접 연동에서 가장 흔하게 발 헛디디는 부분이다. 개발 빌드(Xcode에서 직접 설치, 또는 Development 프로비저닝)에서 받은 토큰은 sandbox로만 가고, 앱스토어/TestFlight 빌드의 토큰은 production으로만 간다. 환경이 안 맞으면 `400 BadDeviceToken`이 떨어진다.

토큰만 보고는 어느 환경 건지 알 수 없다. 그래서 클라이언트가 토큰을 서버에 올릴 때 빌드 환경(`sandbox`/`production`)을 같이 보내서 DB에 박아두고, 전송할 때 그 값으로 엔드포인트를 고른다. 이걸 안 해두면 "특정 사용자만 푸시가 안 온다"를 디버깅하느라 하루를 날린다.

`.p8` 키는 development/production 구분 없이 양쪽 다 서명에 쓸 수 있다. 환경을 가르는 건 키가 아니라 엔드포인트와 디바이스 토큰이다.

HTTP/2라 연결 하나에 여러 요청을 멀티플렉싱해서 보낼 수 있다. 연결을 매번 새로 맺지 말고 재사용해야 처리량이 나온다. node 기본 `http2` 모듈을 직접 쓸 때는 `http2.connect()`로 만든 세션을 들고 다니면서 요청마다 `session.request()`만 한다.

## 요청 헤더

전송 요청은 `POST /3/device/{deviceToken}`이고, 본문이 aps 페이로드 JSON이다. 동작을 결정하는 건 헤더다.

| 헤더 | 의미 |
|---|---|
| `apns-topic` | 대상 앱의 번들 ID. push-type에 따라 접미사가 붙는다 |
| `apns-push-type` | alert / background / voip / liveactivity 등. iOS 13+에서 사실상 필수 |
| `apns-id` | 이 푸시의 UUID. 안 주면 APNs가 만들어 응답 헤더로 돌려준다. 멱등/추적용 |
| `apns-collapse-id` | 같은 값끼리는 최신 것만 남기고 합쳐진다(최대 64바이트) |
| `apns-expiration` | 만료 시각의 유닉스 초. 0이면 한 번만 시도하고 버린다 |
| `apns-priority` | `10` 즉시, `5` 절전. background 푸시는 `5` |

`apns-topic`은 push-type별로 값이 달라진다.

- alert/background: 번들 ID 그대로 (`com.example.app`)
- voip: `com.example.app.voip`
- liveactivity: `com.example.app.push-type.liveactivity`

`apns-collapse-id`는 "채팅방 X에 안 읽은 메시지 N개" 같은 갱신형 알림에서 유용하다. 같은 collapse-id로 여러 번 보내면 잠금화면에 하나로 합쳐져서, 알림이 도배되지 않는다.

`apns-expiration`은 FCM의 TTL과 같은 개념인데 단위가 만료 "시각"의 유닉스 초다. FCM Android `ttl`이 "남은 시간(밀리초)"인 것과 헷갈리기 쉽다. 5분 뒤 만료는 `Math.floor(Date.now()/1000) + 300`이다. 0을 주면 오프라인 기기에는 안 들어간다.

## aps 페이로드 구조

본문 JSON의 최상위 `aps` 키가 OS가 해석하는 예약 영역이고, 그 바깥은 앱이 받는 커스텀 데이터다.

```json
{
  "aps": {
    "alert": { "title": "새 메시지", "body": "안녕하세요" },
    "badge": 3,
    "sound": "default",
    "thread-id": "room-42"
  },
  "roomId": "42",
  "type": "chat"
}
```

`aps` 안의 주요 필드.

- `alert`: 화면에 뜨는 내용. 문자열로 주면 본문만, 객체로 주면 `title`/`subtitle`/`body` 분리. 로컬라이즈 키(`loc-key`, `loc-args`)도 여기 들어간다.
- `badge`: 앱 아이콘 숫자. **0을 주면 뱃지가 사라진다.** 안 주면 기존 뱃지 유지. 서버가 안 읽은 개수를 계산해 넣는 게 보통이다.
- `sound`: `default` 또는 번들에 포함된 사운드 파일명. critical alert면 객체(`{ "critical": 1, "name": "...", "volume": 1.0 }`)로 준다.
- `content-available`: `1`이면 무음 백그라운드 푸시. 화면 표시 없이 앱을 깨워 데이터만 받게 한다.
- `mutable-content`: `1`이면 Notification Service Extension이 가로채 페이로드를 가공할 수 있다(이미지 첨부, 본문 복호화 등).

`aps` 바깥 커스텀 키는 앱이 알아서 읽는다. 단, 전체 페이로드가 크기 제한을 넘으면 안 된다(아래).

## push-type별 동작 차이

`apns-push-type`은 단순 분류가 아니라 OS가 푸시를 다루는 방식 자체를 바꾼다.

### alert

화면에 뜨는 일반 알림. `aps.alert`가 있어야 하고 `apns-push-type: alert`, `apns-priority: 10`이 기본이다. 가장 흔한 케이스.

### background

`aps.content-available: 1`만 있고 `alert`/`sound`/`badge`가 없는 무음 푸시. 화면에 아무것도 안 뜨고 앱을 백그라운드에서 깨워 데이터를 갱신하게 한다. `apns-push-type: background`, `apns-priority: 5`로 보내야 한다. **`priority`를 `10`으로 주면 `400 BadMessageId` 비슷한 거절이나 무시가 발생한다.** background는 절전 우선이라 즉시 전송을 요구할 수 없다.

OS가 전달을 보장하지 않는 것도 중요하다. 배터리·기기 상태에 따라 OS가 background 푸시를 미루거나 합치거나 버린다. "조용히 데이터 동기화"는 best effort일 뿐이고, 꼭 받아야 하는 데이터를 background 푸시에만 의존하면 안 된다.

### voip

PushKit으로 받는 인터넷 전화용 푸시. 앱이 꺼져 있어도 즉시 깨워서 CallKit 수신 화면을 띄울 수 있다. `apns-topic`에 `.voip` 접미사가 붙고 `apns-push-type: voip`다. 일반 푸시보다 강력한 권한이라, 애플이 **VoIP 푸시를 받으면 반드시 CallKit으로 수신 화면을 띄우도록 강제**한다(iOS 13+). 전화 아닌 일반 알림을 voip로 보내 백그라운드 실행을 우회하려던 꼼수를 막은 것이라, 어기면 앱이 죽거나 심사에서 걸린다.

### liveactivity

잠금화면/다이내믹 아일랜드의 라이브 액티비티를 갱신하는 푸시. `apns-topic`이 `.push-type.liveactivity`로 끝나고, 페이로드에 `aps.event`(`update`/`end`)와 `aps.content-state`, `aps.timestamp`가 들어간다. 일반 alert와 페이로드 구조가 꽤 다르다.

## 응답 코드와 reason 처리

요청 하나당 응답 하나다. 상태 코드와, 실패 시 본문 JSON의 `reason` 문자열을 같이 봐야 한다.

| 상태 | 의미 | 처리 |
|---|---|---|
| 200 | 전송 접수 성공 | 정상. 응답 `apns-id` 헤더로 추적 |
| 400 | 요청이 잘못됨 | `reason`별로 분기 (아래) |
| 403 | 인증 실패 | provider 토큰/인증서 문제. 재시도 무의미 |
| 410 | 토큰이 더는 유효하지 않음 | **DB에서 토큰 삭제** |
| 429 | 토큰 갱신 과다 | provider 토큰 캐싱 점검 |
| 500/503 | APNs 일시 장애 | 백오프 후 재시도 |

주요 `reason` 값.

- `BadDeviceToken` (400): 토큰 형식이 잘못됐거나 환경(sandbox/production)이 안 맞는다. 환경 불일치가 압도적으로 많다. 토큰을 무조건 지우기 전에 엔드포인트가 맞는지부터 의심한다.
- `Unregistered` (410): 앱이 삭제됐거나 토큰이 폐기됐다. **확실한 삭제 신호다.** 응답 본문의 `timestamp`(밀리초)가 토큰이 무효화된 시각이다.
- `TopicDisallowed` (400): `apns-topic`이 인증 키/인증서의 권한 밖이다. 번들 ID 오타나, voip 접미사를 빠뜨렸을 때 자주 본다.
- `DeviceTokenNotForTopic` (400): 토큰과 topic의 앱이 안 맞는다. 토큰을 엉뚱한 앱으로 보낸 경우.
- `ExpiredProviderToken` (403): JWT가 1시간을 넘었다. 캐싱 주기를 줄인다.
- `TooManyProviderTokenUpdates` (429): JWT를 너무 자주 새로 만들었다. 위 캐싱이 안 되고 있다는 신호.
- `PayloadTooLarge` (400): 크기 제한 초과(아래).

403/400 인증·topic 계열은 같은 요청을 재시도해봐야 똑같이 실패한다. 재시도는 500/503/타임아웃 같은 일시 오류에만 건다.

## 410 timestamp로 만료 토큰 정리

410 `Unregistered`는 토큰을 지우라는 가장 명확한 신호라 놓치면 안 된다. 만료된 토큰을 계속 들고 전송하면 매번 410을 받고, 무효 토큰 비율이 높아지면 전체 전송 품질도 떨어진다.

응답 본문에 `timestamp`가 함께 온다.

```json
{ "reason": "Unregistered", "timestamp": 1718000000000 }
```

이 값은 토큰이 무효화된 시각(유닉스 밀리초)이다. 단순히 410이니까 지운다가 아니라, **그 토큰이 `timestamp` 이후로 갱신된 적 없을 때만 지운다.** 사용자가 앱을 지웠다 다시 깔아서 새 토큰을 막 등록한 직후라면, 옛 토큰의 410이 뒤늦게 도착해 새 토큰을 실수로 지울 수 있다. DB의 토큰 등록 시각과 `timestamp`를 비교해 등록이 더 최근이면 살린다.

```javascript
async function handleUnregistered(deviceToken, timestampMs) {
  const row = await db.getToken(deviceToken);
  if (!row) return;
  // 토큰이 무효화 시점 이후에 다시 등록됐으면 살린다
  if (row.registeredAt && row.registeredAt.getTime() > timestampMs) return;
  await db.deleteToken(deviceToken);
}
```

이 (등록시각 vs timestamp) 비교는 FCM의 `UNREGISTERED` 정리에서 "방금 갱신된 새 토큰을 실수로 지우지 말 것"과 같은 문제다. APNs는 `timestamp`를 명시적으로 줘서 판단이 더 쉽다.

## 페이로드 크기 제한

- 일반(alert/background/liveactivity): **4KB(4096바이트)**
- voip: **5KB(5120바이트)**

`aps`뿐 아니라 커스텀 키까지 합친 전체 JSON 바이트 기준이다. 초과하면 `400 PayloadTooLarge`로 통째로 거절된다. 한글은 UTF-8에서 글자당 3바이트라 본문에 한글을 길게 넣으면 생각보다 빨리 찬다.

커스텀 데이터에 큰 객체(JSON 덩어리, base64 이미지)를 통째로 실으려다 터지는 경우가 많다. 푸시 본문에는 식별자만 싣고, 실제 데이터는 앱이 푸시를 받은 뒤 API로 따로 받아오게 설계하는 게 안전하다. 이미지 같은 리치 콘텐츠는 `mutable-content: 1` + Notification Service Extension에서 URL로 받아 붙이는 방식이 정석이다.

## Node 전송 예제

### node-apn (apn 패키지)

연결·HTTP/2·토큰 갱신을 알아서 처리해줘서 직접 붙기 편하다.

```javascript
const apn = require('apn');

const provider = new apn.Provider({
  token: {
    key: './AuthKey_ABC1234567.p8',
    keyId: 'ABC1234567',
    teamId: 'TEAMID1234',
  },
  production: process.env.NODE_ENV === 'production', // 엔드포인트 선택
});

const note = new apn.Notification();
note.topic = 'com.example.app';      // apns-topic
note.pushType = 'alert';             // apns-push-type
note.priority = 10;
note.expiry = Math.floor(Date.now() / 1000) + 300;
note.alert = { title: '새 메시지', body: '안녕하세요' };
note.badge = 3;
note.sound = 'default';
note.payload = { roomId: '42', type: 'chat' }; // aps 바깥 커스텀

const result = await provider.send(note, deviceToken);

for (const f of result.failed) {
  // f.status: '410' 등, f.response.reason: 'Unregistered'
  if (f.status === '410' || f.response?.reason === 'Unregistered') {
    await handleUnregistered(f.device, f.response.timestamp);
  }
}
```

`production` 불리언으로 엔드포인트가 갈리니, 이 값이 빌드 환경별 토큰과 어긋나지 않게 신경 쓴다. 한 서버에서 sandbox/production 토큰을 섞어 보내야 하면 Provider 인스턴스를 둘로 나눠 들고, 토큰의 환경 값에 따라 골라 쓴다.

### http2 직접 호출

의존성을 줄이거나 동작을 완전히 통제하고 싶으면 기본 `http2`로 붙는다.

```javascript
const http2 = require('http2');

const host = isProd
  ? 'https://api.push.apple.com'
  : 'https://api.sandbox.push.apple.com';
const client = http2.connect(host); // 세션 재사용

function send(deviceToken, payload) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const req = client.request({
      ':method': 'POST',
      ':path': `/3/device/${deviceToken}`,
      'authorization': `bearer ${getProviderToken()}`,
      'apns-topic': 'com.example.app',
      'apns-push-type': 'alert',
      'apns-priority': '10',
      'content-type': 'application/json',
      'content-length': Buffer.byteLength(body),
    });

    let status, data = '';
    req.on('response', (h) => { status = h[':status']; });
    req.on('data', (c) => { data += c; });
    req.on('end', () => {
      if (status === 200) return resolve({ ok: true });
      const reason = data ? JSON.parse(data).reason : null;
      resolve({ ok: false, status, reason, body: data });
    });
    req.on('error', reject);
    req.setEncoding('utf8');
    req.end(body);
  });
}
```

세션(`client`)은 한 번 맺고 재사용한다. 끊기면(`client.on('close')`) 재연결 로직을 둬야 한다. 운영에서는 GOAWAY 프레임으로 애플이 연결을 닫는 일이 정기적으로 있어서, 재연결 처리를 안 하면 어느 순간 전송이 멈춘다.

## 무음 푸시 throttling 주의

`content-available: 1` background 푸시는 애플이 빈도를 제한한다. 짧은 시간에 같은 기기로 무음 푸시를 연달아 던지면 OS가 뒤엣것을 버리거나 한참 미룬다. 문서상 "시간당 일정 횟수" 정도로만 안내되고 정확한 수치는 공개돼 있지 않은데, 체감상 분 단위로 계속 쏘면 안 들어온다.

그래서 background 푸시를 실시간 동기화 트리거로 남발하면 안 된다. 꼭 받아야 하는 갱신이면 alert 푸시에 데이터를 같이 싣거나, 앱이 포그라운드로 올라올 때 능동적으로 동기화하게 설계한다. background는 "기회가 되면 미리 받아두기" 정도의 보조 수단으로 본다.

`apns-priority: 5`를 지키는 것과 별개의 문제다. priority는 거절을 피하는 것이고, throttling은 보내도 OS가 안 깨우는 것이라 헤더만 맞춰도 해결되지 않는다.

## FCM 경유 vs 직접 연동, 어느 쪽

| 기준 | FCM 경유 | APNs 직접 |
|---|---|---|
| 대상 플랫폼 | iOS + Android + 웹 한 번에 | iOS/애플 기기만 |
| 인증 관리 | 서비스 계정 JSON 하나 | .p8 키 + JWT 캐싱 직접 |
| 토큰 정리 | FCM의 `UNREGISTERED`에 의존 | 410 `timestamp` 직접 처리 |
| 통계/대시보드 | Firebase 콘솔 제공 | 직접 집계 |
| 지연/장애점 | FCM 한 단계 더 거침 | 애플로 직행 |
| 세밀한 제어 | FCM이 추상화한 범위 | 헤더·push-type 전부 직접 |

대부분의 서비스는 **iOS·Android를 같이 쓰니 FCM으로 통일**하는 게 운영 부담이 적다. 인증·토큰·통계를 한 곳에서 보고, iOS도 FCM이 APNs로 알아서 중계한다.

APNs 직접 연동이 합리적인 경우는 따로 있다.

- 애플 기기만 대상이고 Firebase 의존성을 두기 싫을 때.
- VoIP, Live Activity처럼 FCM 추상화로는 다루기 까다롭거나 직접 제어가 필요한 푸시 비중이 클 때.
- FCM이 한 단계 더 끼는 지연·장애점을 없애고 애플로 직행하고 싶을 때.
- 무음 푸시 빈도, collapse-id, expiration 같은 헤더를 세밀하게 컨트롤해야 할 때.

iOS 일반 알림만 보낼 거라면 FCM으로도 충분하고, 직접 연동은 위 같은 이유가 분명할 때 택한다. 둘을 섞어, 일반 알림은 FCM, VoIP/Live Activity만 APNs 직접으로 가는 구성도 현실에서 흔하다.
