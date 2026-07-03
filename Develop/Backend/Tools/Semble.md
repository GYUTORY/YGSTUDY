---
title: Semble - 헬스케어 SaaS GraphQL API 백엔드 통합
tags:
  - Backend
  - Tools
  - Semble
  - GraphQL
  - Healthcare
  - API
updated: 2026-04-28
---

# Semble

## 개요

Semble은 영국에서 시작된 클라우드 기반 진료 관리(EHR + Practice Management) SaaS다. 환자 기록, 예약, 청구, 처방, 환자 포털 같은 기능을 한 곳에서 관리한다. 백엔드 개발자 입장에서 의미 있는 부분은 **Public GraphQL API** 와 외부 시스템과의 양방향 동기화 기능이다.

직접적인 사용 경험에서 Semble을 만나는 시나리오는 보통 셋 중 하나다.

1. 클리닉이 이미 Semble을 쓰는데, 별도로 운영하는 자사 예약 페이지·환자 앱·CRM과 데이터를 연동해달라는 요구가 들어온다.
2. 사내 BI 시스템에 Semble의 환자/매출 데이터를 적재해야 한다.
3. 외부 의료 설문지나 검사 결과를 Semble의 환자 차트에 자동 기록해야 한다.

세 시나리오 모두 결국 백엔드에서 GraphQL API를 호출하고, 토큰을 관리하고, 레이트 리밋을 견디고, 웹훅을 받아 우리 시스템과 정합성을 유지하는 작업으로 귀결된다. 이 문서는 그 관점에서 정리한다.

## 주요 기능

API에서 접근할 수 있는 도메인은 크게 다음과 같다.

- 환자(Patient): 인적사항, 알레르기, 의료 기록, 첨부 파일
- 예약(Booking, Appointment): 진료 슬롯, 상태 변경, 캔슬, 노쇼
- 진료 기록(Consultation, Record): 의사가 작성하는 차트 노트, 처방
- 청구(Invoice, Payment): 인보이스 발행, 결제 상태
- 사용자(User, Doctor): 의료진 계정, 진료 가능 시간
- 위치(Location, Practice): 다중 클리닉 운영 시 지점 정보

GraphQL 스키마라서 한 번의 요청으로 여러 도메인을 묶어 가져올 수 있다는 점이 REST 기반 EHR 시스템과 다르다. 특히 환자 한 명의 인적사항·예약 이력·청구서를 한꺼번에 받아오는 케이스에서 라운드트립이 크게 줄어든다.

## 설치 및 설정

설치라고 부를 만한 게 따로 있는 도구는 아니다. 클리닉 측이 Semble 관리자 화면에서 API를 활성화하고, 토큰 발급용 자격 증명을 생성해주는 게 시작점이다.

기본 엔드포인트는 다음과 같다.

```
https://open.semble.io/graphql
```

(실제 환경에 따라 `staging` 같은 별도 도메인을 받을 수 있다. 클리닉 담당자가 알려주는 엔드포인트를 그대로 쓰면 된다.)

### 인증 토큰

Semble은 username/password 방식의 로그인 뮤테이션으로 access token을 발급한다. 이 토큰은 12시간 동안 유효하고, 만료되면 다시 로그인 뮤테이션을 호출해 갱신해야 한다. 일반적인 OAuth2 refresh token 흐름이 아니라는 점을 처음 통합할 때 헷갈리기 쉽다.

```graphql
mutation Login($username: String!, $password: String!) {
  signIn(username: $username, password: $password) {
    token
    expiresAt
    user {
      id
      email
    }
  }
}
```

발급받은 토큰은 Authorization 헤더에 그대로 실어 보낸다.

```
Authorization: <token>
```

`Bearer ` 접두사 없이 토큰 값만 넣는다는 점을 주의해야 한다. 일반적인 API에 익숙해서 자동으로 `Bearer ` 를 붙이면 401이 떨어진다.

### Node.js 클라이언트 기본 셋업

운영에서 가장 자주 쓰는 형태는 Apollo Client + 토큰 캐시 조합이다. 토큰 발급 비용이 0이 아니고 12시간이라는 긴 수명을 가지므로 Redis나 in-memory 캐시에 저장해두고 만료 직전에만 갱신한다.

```ts
import { GraphQLClient, gql } from 'graphql-request';
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL!);
const SEMBLE_URL = 'https://open.semble.io/graphql';
const TOKEN_KEY = 'semble:token';
const SAFETY_MARGIN_SEC = 60 * 10;

async function getToken(): Promise<string> {
  const cached = await redis.get(TOKEN_KEY);
  if (cached) return cached;

  const client = new GraphQLClient(SEMBLE_URL);
  const data = await client.request<{
    signIn: { token: string; expiresAt: string };
  }>(
    gql`
      mutation Login($u: String!, $p: String!) {
        signIn(username: $u, password: $p) {
          token
          expiresAt
        }
      }
    `,
    { u: process.env.SEMBLE_USER, p: process.env.SEMBLE_PASS },
  );

  const ttl =
    Math.floor(
      (new Date(data.signIn.expiresAt).getTime() - Date.now()) / 1000,
    ) - SAFETY_MARGIN_SEC;

  await redis.set(TOKEN_KEY, data.signIn.token, 'EX', Math.max(ttl, 60));
  return data.signIn.token;
}

export async function sembleClient() {
  const token = await getToken();
  return new GraphQLClient(SEMBLE_URL, {
    headers: { Authorization: token },
  });
}
```

만료 10분 전에 미리 갱신하는 안전 마진은 실제 운영에서 토큰이 정확히 만료 시점에 죽지 않고 약간의 클럭 스큐가 있는 경우를 위한 것이다. 이걸 빼면 한밤중 배치에서 갑자기 401 폭탄을 맞는 경우가 생긴다.

## 실제 사용 예제

### 환자 검색과 페이지네이션

GraphQL이지만 페이지네이션은 cursor가 아닌 offset 기반이 기본이다. 환자 수가 많아지면 deep page에서 응답이 급격히 느려지므로, 가능하면 외부 ID나 전화번호 같은 고유 키로 직접 조회해야 한다.

```ts
const query = gql`
  query SearchPatients($search: String, $first: Int, $after: String) {
    patients(search: $search, pagination: { page: 1, pageSize: 50 }) {
      data {
        id
        firstName
        lastName
        email
        phoneNumber
        dateOfBirth
      }
      pageInfo {
        hasMore
        total
      }
    }
  }
`;

const client = await sembleClient();
const result = await client.request(query, { search: '010-1234-5678' });
```

여기서 한 가지 함정은 `phoneNumber` 검색이 정확히 일치하지 않아도 매칭된다는 점이다. 예를 들어 `010-1234-5678` 로 검색하면 `+44 010 1234 5678` 같은 번호도 같이 잡힐 수 있다. 동명이인이나 비슷한 번호가 있는 경우에 잘못된 환자에 데이터를 쓸 위험이 있다. 최종 확정은 우리 쪽 외부 ID와 매칭하는 단계를 한 번 더 거쳐야 한다.

### 예약 생성

예약을 만들 때는 환자 ID, 의사 ID, 위치 ID, 시작/종료 시각, 예약 타입 ID가 모두 필요하다. 이 ID들은 모두 Semble 내부 식별자이므로 우리 쪽 도메인 모델과 매핑 테이블을 따로 두는 게 거의 필수다.

```ts
const mutation = gql`
  mutation CreateBooking($input: BookingInput!) {
    createBooking(bookingData: $input) {
      data {
        id
        start
        end
        status
      }
      error
    }
  }
`;

await client.request(mutation, {
  input: {
    patient: 'patient_xxx',
    doctor: 'doctor_xxx',
    location: 'location_xxx',
    bookingType: 'bt_xxx',
    start: '2026-04-30T09:00:00.000Z',
    end: '2026-04-30T09:30:00.000Z',
  },
});
```

응답에서 `error` 필드를 GraphQL `errors` 배열과 별개로 따로 두는 게 Semble 스타일이다. HTTP 200에 `errors`가 비어 있어도 `error` 필드에 `"Slot already booked"` 같은 메시지가 들어와 있을 수 있다. 항상 둘 다 확인해야 한다.

### 웹훅 수신

Semble Connect를 통해 예약·환자 변경 이벤트를 외부로 푸시받을 수 있다. 페이로드는 JSON이고, 서명 검증을 위해 헤더에 HMAC SHA256 시그니처가 들어온다.

```ts
import crypto from 'crypto';
import express from 'express';

const app = express();
app.use(express.raw({ type: 'application/json' }));

app.post('/webhooks/semble', (req, res) => {
  const signature = req.header('X-Semble-Signature');
  const computed = crypto
    .createHmac('sha256', process.env.SEMBLE_WEBHOOK_SECRET!)
    .update(req.body)
    .digest('hex');

  if (signature !== computed) {
    return res.status(401).end();
  }

  const event = JSON.parse(req.body.toString());

  switch (event.type) {
    case 'booking.created':
    case 'booking.updated':
      enqueue('semble.sync.booking', event.data);
      break;
    case 'patient.updated':
      enqueue('semble.sync.patient', event.data);
      break;
  }

  res.status(204).end();
});
```

여기서 `express.raw` 로 받는 이유는 시그니처 검증이 원본 바이트 기준이기 때문이다. `express.json()` 으로 받으면 객체로 직렬화-역직렬화가 일어나면서 공백·키 순서가 달라져 서명이 깨진다. 이 실수는 첫 통합 때 거의 모든 사람이 한다.

또 하나 주의할 점은 웹훅이 **at-least-once** 라는 점이다. 동일한 이벤트 ID가 두 번 들어오는 경우가 있으니 큐로 옮기기 전에 이벤트 ID 기반 dedupe 키를 Redis에 잠깐 박아두는 게 안전하다.

## 실무에서 겪는 문제와 해결 방법

### 1. 240 req/min 레이트 리밋

공식적으로 분당 240 요청이 한도다. 환자 마이그레이션 같은 대량 작업에서는 단순 직렬 호출이 거의 항상 한도를 넘는다. 더 골치 아픈 건 한도를 넘었을 때 429가 아니라 일시적으로 GraphQL `errors` 배열에 rate limit 메시지가 담긴 200 응답이 온다는 점이다. 표준 HTTP 재시도 라이브러리로는 잡히지 않는다.

해결책은 두 가지다.

- 호출 측에 토큰 버킷을 직접 두고 분당 200 정도로 셀프 스로틀한다.
- GraphQL 응답 본문을 파싱해서 rate limit 메시지가 보이면 백오프 후 재시도하는 미들웨어를 둔다.

```ts
async function callWithRetry<T>(fn: () => Promise<T>): Promise<T> {
  for (let i = 0; i < 5; i++) {
    try {
      return await fn();
    } catch (err: any) {
      const msg = String(err?.response?.errors?.[0]?.message ?? err?.message);
      if (msg.toLowerCase().includes('rate limit')) {
        await new Promise(r => setTimeout(r, 2000 * Math.pow(2, i)));
        continue;
      }
      throw err;
    }
  }
  throw new Error('Semble: retry exhausted');
}
```

### 2. Deep query timeout

GraphQL의 장점을 살려 환자 → 모든 예약 → 각 예약의 진료기록 → 첨부파일까지 한 번에 받으려고 하면 거의 항상 타임아웃이다. 30초 가까이 응답이 안 오다가 게이트웨이 타임아웃이 떨어진다. Semble 백엔드가 Mongo 기반이라는 게 비공식적으로 알려져 있는데, 깊게 들어갈수록 응답 시간이 비선형적으로 늘어난다.

원칙은 한 번의 GraphQL 요청에서 **2단계 깊이까지만** 가져오고, 나머지는 별도 쿼리로 분리하는 것이다. N+1 처럼 보여도 분리하는 쪽이 안정적이다.

### 3. 시간대(time zone) 혼란

API 응답의 모든 datetime은 ISO8601 UTC다. 그런데 클리닉 운영자는 항상 자기 로컬 타임(보통 Europe/London)으로 사고한다. 예약 슬롯을 만들 때 한국에서 보내면 KST와 BST의 차이로 의사가 출근하지 않은 시간에 예약이 들어가는 사고가 종종 난다. 운영팀에서 "왜 새벽 5시에 예약이 잡혀 있냐"는 컴플레인이 들어오면 거의 이 문제다.

내부 도메인에서 datetime을 다룰 때는 `(local datetime, timezone)` 페어로 들고 다니다가, Semble에 보낼 때만 클리닉의 타임존 기준으로 UTC로 변환해야 한다. `Date` 객체 하나로만 들고 다니면 어디선가 한 번 바뀐다.

### 4. 토큰 동시 갱신 race

한 번에 여러 워커가 같은 만료 시점에 동시에 토큰을 갱신하면, Semble은 새 토큰을 발급하면서 이전 토큰 일부를 무효화하는 경우가 있었다. 그러면 갱신을 시도한 인스턴스 중 일부는 이미 받아간 토큰이 즉시 깨져버린다. 이게 주기적인 401 스파이크의 원인이 된다.

Redis 분산 락으로 토큰 갱신을 직렬화하는 게 가장 단순한 해결책이다.

```ts
async function getToken() {
  const cached = await redis.get(TOKEN_KEY);
  if (cached) return cached;

  const lock = await redis.set('semble:token:lock', '1', 'NX', 'EX', 30);
  if (!lock) {
    await new Promise(r => setTimeout(r, 200));
    return getToken();
  }

  try {
    const recheck = await redis.get(TOKEN_KEY);
    if (recheck) return recheck;
    return await refreshToken();
  } finally {
    await redis.del('semble:token:lock');
  }
}
```

### 5. 환자 중복 생성

신규 환자 등록 뮤테이션은 이메일·전화번호 중복 체크를 자동으로 해주지 않는다. 우리 쪽 시스템에서 새 가입자가 들어올 때마다 별다른 검사 없이 `createPatient` 를 호출하면, 같은 사람이 두 번째 예약 시도할 때 또 다른 환자 레코드가 생긴다. 결과적으로 의사 화면에 동일인이 두 명 보이는 사고가 난다.

생성 전에 반드시 검색 쿼리로 기존 환자를 찾고, 없을 때만 만든다. 그리고 우리 쪽 user_id 와 Semble patient_id 매핑은 unique 제약으로 강제해야 한다.

## 다른 유사 도구와의 차이점

같은 영역의 다른 SaaS와 비교하면 선택 기준이 명확해진다.

- **Cliniko**: REST API. 단순한 작업에는 더 직관적이지만, 한 화면에 필요한 데이터를 모으려면 여러 번 요청해야 한다. 데이터 모델이 단순한 만큼 진료 노트나 처방 같은 임상 기록 깊이가 얕다.
- **Doctolib**: 유럽권에서 점유율은 높지만 Public API가 사실상 닫혀 있다. 파트너십 계약 없이는 백엔드 통합이 불가능하다.
- **Athenahealth, Epic**: 대형 병원용. FHIR 기반이라 표준성은 높지만 통합 비용과 인증 절차가 비교 자체가 안 될 정도로 무겁다. 소·중규모 클리닉에는 과한 선택이다.
- **Practice Fusion, Kareo**: 미국 시장 위주. 영국·유럽·중동 클리닉에는 거의 해당 없음.

Semble의 위치는 "GraphQL을 쓸 줄 아는 개발자가 있는 중·소규모 클리닉이 직접 통합 코드를 짤 수 있는 정도의 진입 장벽"이다. FHIR 같은 표준은 아니지만 도큐먼트가 비교적 깔끔하고, 토큰만 있으면 어떤 언어에서든 쉽게 호출이 가능하다.

## 트러블슈팅 사례

### 사례 1: 갑작스런 401 폭증

증상은 평소 잘 돌던 야간 동기화 배치가 어느 날부터 401을 뱉기 시작하는 것이었다. 토큰 갱신 로직도 멀쩡하고, 자격 증명도 그대로였다. 원인은 클리닉 측 어드민이 보안 정책 변경 때문에 비밀번호를 바꾼 것이었다. Semble은 사용자 비밀번호 변경 시 모든 발급 토큰을 무효화한다. 비밀번호 자체를 우리 쪽 환경 변수로 관리하던 구조라 이걸 알아채는 데 시간이 걸렸다.

이후로는 통합 전용 service account 를 만들고, 인사이동·정책 변경에도 비밀번호가 바뀌지 않도록 별도로 관리하는 정책으로 바꿨다.

### 사례 2: 동일 환자 중복 등록

신규 가입자에게 모바일 앱에서 첫 예약을 시도하면 환자가 두 번 만들어지는 버그가 있었다. 원인은 React Native 쪽에서 네트워크 응답이 늦을 때 사용자가 버튼을 두 번 눌렀고, 두 요청이 거의 동시에 백엔드에 도착해 검색 → 없음 → 생성 단계가 두 번 동시에 돌았다는 것이다.

해결은 백엔드에서 `userId` 단위 분산 락을 걸고 환자 등록 코드를 보호하는 것이다. 단순한 idempotent key 헤더만으로는 부족했고, 락 기반 직렬화가 필요했다.

### 사례 3: 잘못된 시간대로 들어간 예약

영국 서머타임 전환 다음 날, 모든 예약이 한 시간씩 앞당겨져 들어가는 문제가 있었다. 원인은 우리 쪽 시간 변환 코드에 BST 오프셋을 하드코딩해뒀던 것이다. UTC + 0 가정으로 짜둔 코드가 BST 기간 내내 기적적으로 잘 돌다가 표준시 전환 직후 깨졌다.

이후로 모든 시간 변환은 IANA 타임존 데이터(`Europe/London`) 기반의 `luxon` 으로 통일했고, 오프셋 자체를 코드에서 다루지 않는 원칙을 정했다.

### 사례 4: 웹훅 누락

특정 시간대에만 웹훅이 일부 누락되는 현상이 있었다. 우리 서버 로그에는 흔적이 아예 없었다. 원인은 우리 쪽 LB 앞에 둔 WAF가 외부 IP에서 들어오는 본문 큰 요청을 일부 차단하고 있던 것이었다. Semble은 첨부파일 메타데이터가 큰 환자 이벤트에서 페이로드 크기가 갑자기 커지는 케이스가 있다.

해결은 두 가지였다. 웹훅 엔드포인트에 대해서는 WAF 룰을 완화했고, 동시에 매시간 단위로 직전 1시간의 변경분을 풀링으로 다시 가져오는 보조 동기화 잡을 추가해 누락을 메꿨다. 외부 시스템의 푸시만 믿지 않는다는 원칙은 어떤 SaaS 통합에서도 유효하다.

## 참고

- 공식 API 문서: `https://docs.semble.io/`
- 헬프 센터: `https://help.semble.io/`
- 레이트 리밋: 분당 240 요청, 토큰 수명 12시간
