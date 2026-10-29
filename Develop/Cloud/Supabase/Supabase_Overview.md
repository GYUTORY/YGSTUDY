---
title: Supabase 구조와 도입 판단
tags: [cloud, backend, database, postgresql, security, auth, api]
updated: 2026-10-29
---

# Supabase 구조와 도입 판단

Supabase를 "오픈소스 Firebase"라고 소개하는 글이 많은데, 쓰다 보면 이 설명이 오해를 만든다. Firebase는 NoSQL 문서 저장소 위에 SDK를 얹은 제품이고, Supabase는 평범한 PostgreSQL 앞에 HTTP API 계층을 여러 개 붙여 놓은 구성이다. DB는 진짜 Postgres라서 psql로도 붙고 Flyway도 돌아간다. 대신 그 앞에 붙은 계층들이 어떻게 인증을 처리하는지 모르고 쓰면, 키 유출이나 권한 구멍 같은 사고가 DB가 아니라 계층 사이에서 난다.

이 문서는 Supabase가 어떤 컴포넌트로 이루어졌는지, 프로젝트를 만들면 받는 키가 각각 무엇을 뜻하는지, 클라이언트에서 직접 쿼리하는 방식과 서버에서 DB에 붙는 방식을 섞으면 무엇이 깨지는지, 그리고 무료 티어에서 언제 Pro로 넘어가야 하는지를 정리한다. 수치와 요금은 2026년 10월 기준이고, 요금 페이지는 수시로 바뀌므로 결제 전에 콘솔에서 다시 본다.

## Supabase가 실제로 무엇으로 이루어졌나

프로젝트 하나를 만들면 컨테이너 여러 개가 한 묶음으로 뜬다. 각각은 독립된 오픈소스 프로젝트이고, Supabase는 이것들을 한 도메인 뒤에 묶고 JWT 하나로 인증을 통일한 것이다.

```mermaid
flowchart LR
    C["클라이언트 (supabase-js)"] --> K["Kong 게이트웨이"]
    K -->|"/rest/v1"| P["PostgREST"]
    K -->|"/auth/v1"| G["GoTrue (Auth)"]
    K -->|"/realtime/v1"| R["Realtime"]
    K -->|"/storage/v1"| S["Storage API"]
    K -->|"/functions/v1"| E["Edge Functions (Deno)"]
    P --> DB[("Postgres")]
    G --> DB
    R --> DB
    S --> DB
    E -.->|"service_role 또는 사용자 JWT"| K
    ST["Studio (대시보드)"] --> M["postgres-meta"]
    M --> DB
    S --> OBJ[("객체 저장소 (S3 호환)")]
```

모든 외부 요청은 Kong 한 곳으로 들어온다. 경로 접두사(`/rest/v1`, `/auth/v1` 등)로 뒤쪽 서비스가 갈리고, 뒤쪽 서비스는 전부 같은 Postgres 인스턴스를 바라본다. 이 구조에서 중요한 점은 인증 정보가 별도 사용자 DB에 있는 게 아니라 `auth` 스키마 안의 테이블(`auth.users`)로 같은 Postgres에 들어 있다는 것이다. 그래서 `public.profiles.user_id`에서 `auth.users.id`로 외래키를 걸 수 있고, RLS 정책에서 현재 사용자를 곧바로 참조할 수 있다.

| 컴포넌트 | 역할 | 알아둘 것 |
|---|---|---|
| Postgres | 모든 데이터와 권한의 실체 | 확장(pgvector, pg_cron, pg_net 등)을 대시보드에서 켠다. 슈퍼유저는 주지 않는다 |
| PostgREST | 테이블·뷰·함수를 REST로 자동 노출 | 요청마다 JWT의 `role` 클레임으로 Postgres 롤을 바꿔서 쿼리한다 |
| GoTrue (Auth) | 가입·로그인·OAuth·매직링크, JWT 발급 | 사용자는 `auth.users`에 저장된다. 이메일 발송은 기본 SMTP 제한이 빡빡해서 운영에선 SMTP를 따로 붙인다 |
| Realtime | 테이블 변경 구독, 브로드캐스트, 프레즌스 | 변경 구독도 RLS를 따른다. Elixir로 만들어져 있고 Postgres 논리 복제 슬롯을 읽는다 |
| Storage | 파일 업로드·다운로드 | 파일 본체는 객체 저장소, 메타데이터와 권한은 `storage.objects` 테이블. 권한도 RLS다 |
| Kong | API 게이트웨이, 키 검증, 라우팅 | 호스팅 환경에서는 직접 만질 일이 없다. 셀프호스팅할 때만 설정 파일을 본다 |
| Edge Functions | Deno 런타임의 서버리스 함수 | TypeScript로 쓴다. Node 패키지는 `npm:` 접두사로 가져오며 호환 안 되는 것이 있다 |
| Studio | 웹 대시보드 | 내부적으로 postgres-meta를 통해 DB를 조회한다. SQL Editor에서 쓴 쿼리는 `postgres` 롤로 실행된다 |

여기에 커넥션 풀러(Supavisor)가 따로 붙는다. 풀러는 HTTP 계층이 아니라 DB 포트 앞에 놓이는 것이라 위 도식에는 넣지 않았다. 서버 애플리케이션이 직접 접속할 때 지나가는 길이 이쪽이고, 뒤에서 다시 다룬다.

### PostgREST가 권한을 처리하는 방식

이 구조의 핵심이 PostgREST라서, 한 번은 원리를 알고 가야 RLS 사고를 피한다. PostgREST는 자기만의 사용자 개념이 없다. 요청이 들어오면 JWT의 `role` 클레임 값(`anon`, `authenticated`, `service_role`)을 읽어 같은 이름의 Postgres 롤로 `SET LOCAL ROLE`을 한 뒤 쿼리를 실행하고, JWT 전체를 `request.jwt.claims`라는 세션 설정에 넣는다. `auth.uid()`는 이 설정에서 `sub`를 꺼내는 함수일 뿐이다.

```sql
-- PostgREST가 요청마다 사실상 이렇게 실행한다
BEGIN;
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub":"5f1c...","role":"authenticated"}';
SELECT * FROM public.orders;   -- RLS 정책이 auth.uid()를 평가한다
COMMIT;
```

권한 판단을 전부 Postgres의 롤과 RLS에 맡기는 구조라서 API 서버에 `if (user.id !== order.userId)` 같은 코드가 없다. 반대로 말하면 RLS를 안 걸어 둔 테이블은 `anon` 키만 있으면 누구나 읽는다. 대시보드 Table Editor로 만든 테이블은 RLS가 기본으로 켜지지만, SQL Editor나 마이그레이션 파일로 `CREATE TABLE`을 하면 꺼진 채로 만들어진다. 이 차이로 "로컬 마이그레이션으로 만든 테이블이 전부 공개 상태"인 프로젝트를 여러 번 봤다.

## 요청 하나가 지나가는 길

`supabase.from('orders').select()` 한 줄이 응답으로 돌아오기까지의 순서다. 도식에서 볼 부분은 두 군데다. Kong이 키를 검증하는 단계와, Postgres가 RLS로 행을 걸러내는 단계는 서로 다른 곳이고, 앞이 통과했다고 뒤가 허용된 게 아니라는 점이다.

```mermaid
sequenceDiagram
    participant App as supabase-js
    participant Kong as Kong
    participant PgRest as PostgREST
    participant PG as Postgres

    App->>Kong: GET /rest/v1/orders (apikey, Authorization Bearer JWT)
    activate Kong
    Kong->>Kong: apikey 검증 (anon 또는 service_role)
    Kong->>PgRest: 요청 전달
    deactivate Kong
    activate PgRest
    PgRest->>PgRest: JWT 서명 검증 (JWT secret)
    PgRest->>PG: SET LOCAL ROLE authenticated, request.jwt.claims 설정
    activate PG
    PG->>PG: RLS 정책 평가 (auth.uid() = user_id)
    PG-->>PgRest: 정책을 통과한 행만 반환
    deactivate PG
    PgRest-->>App: 200 OK (JSON)
    deactivate PgRest
```

헤더가 두 개인 것이 처음엔 헷갈린다. `apikey` 헤더에는 anon 키가 들어가고, 이건 "이 프로젝트의 API를 호출할 자격"을 확인하는 용도다. `Authorization: Bearer`에는 로그인한 사용자의 access token이 들어가고, 이것이 실제 `role`과 `sub`를 결정한다. 로그인 전에는 Bearer 자리에도 anon 키가 들어가서 롤이 `anon`이 된다. supabase-js가 이 둘을 알아서 채우기 때문에 코드에서는 보이지 않지만, curl로 디버깅할 때는 둘 다 직접 넣어야 한다.

```bash
curl "https://<project-ref>.supabase.co/rest/v1/orders?select=id,status" \
  -H "apikey: <anon key>" \
  -H "Authorization: Bearer <user access token>"
```

RLS가 켜져 있는데 정책이 없으면 에러가 나지 않고 빈 배열이 돌아온다. 이 증상 때문에 "쿼리가 잘못됐나", "데이터가 안 들어갔나"를 한참 의심하게 되는데, 대개 정책이 없거나 `TO authenticated`를 빠뜨린 것이다. 빈 배열이 오면 SQL Editor에서 `SET ROLE authenticated`와 `request.jwt.claims` 설정을 직접 하고 같은 쿼리를 돌려보면 원인이 바로 갈린다.

## 프로젝트를 만들면 받는 키

프로젝트를 만들면 대시보드에 값이 여러 개 나온다. 이름이 비슷해서 섞어 쓰는 경우가 많으니 한 번 구분해 둔다.

| 값 | 무엇인가 | 어디에 둘 수 있나 |
|---|---|---|
| project ref | 프로젝트 고유 ID (20자 안팎 문자열). URL이 `https://<ref>.supabase.co` | 공개돼도 상관없다 |
| anon key | `role: anon` 클레임을 가진 JWT. 로그인 전 사용자의 신분 | 클라이언트 번들에 들어가도 된다. 단 RLS가 전제다 |
| service_role key | `role: service_role` 클레임을 가진 JWT. RLS를 우회한다 | 서버 환경변수에만. 브라우저·앱 번들 금지 |
| JWT secret | 위 두 키와 사용자 access token을 서명하는 키 | 서버에서 토큰을 직접 검증할 때만. 유출되면 아무 사용자나 위조할 수 있다 |
| DB 비밀번호 | `postgres` 롤의 비밀번호 | 서버에서 DB에 직접 붙을 때만 |
| DB 접속 URL | 직접 접속(`db.<ref>.supabase.co:5432`)과 풀러(`...pooler.supabase.com:6543`) 두 종류 | 서버 환경변수 |

최근에 만든 프로젝트는 콘솔에 publishable key(`sb_publishable_...`)와 secret key(`sb_secret_...`)가 따로 표시되는 경우가 있다. anon과 service_role의 새 형태이고 권한 모델은 같다. publishable은 anon 자리, secret은 service_role 자리에 대응한다고 보면 된다. 기존 JWT 형태의 키도 계속 동작하므로 어느 쪽이든 아래 내용은 그대로 적용된다.

anon 키는 "공개해도 된다"고 문서에 적혀 있는데, 이 말은 RLS를 전제로 한다. anon 키는 프런트엔드 번들에서 누구나 꺼내 볼 수 있다. 그 키로 할 수 있는 일이 RLS 정책이 허용한 범위로 제한되니 안전하다는 논리다. 정책이 구멍이면 anon 키는 그대로 DB 읽기·쓰기 권한이다.

### 가입은 열려 있다

anon 키로 `supabase.auth.signUp()`을 호출하면 누구나 `authenticated` 롤을 얻는다. 가입을 막지 않았다면 정책을 `TO authenticated USING (true)`로 쓴 테이블은 사실상 전체 공개다. "로그인한 사용자만"이라는 말은 가입이 닫혀 있거나 이메일 도메인으로 제한돼 있을 때만 접근 제어가 된다. 내부 도구라면 대시보드에서 Sign-ups를 끄고 관리자가 초대하는 방식으로 쓴다.

## service_role 키가 번들에 들어가는 경로

`service_role` 키는 `BYPASSRLS` 속성을 가진 롤이다. 이 키로 요청하면 모든 RLS 정책이 평가되지 않고, 모든 테이블의 모든 행을 읽고 지울 수 있다. 정책을 아무리 잘 짜 놔도 이 키 하나가 나가면 소용없다.

실제로 유출되는 경로는 거의 환경변수 접두사 하나로 귀결된다. Next.js는 `NEXT_PUBLIC_`으로 시작하는 변수를 빌드 시점에 클라이언트 번들에 문자열로 박아 넣는다. 서버 코드에서 쓰려고 만든 변수 이름에 습관적으로 접두사를 붙이면 그대로 나간다.

```bash
# .env.local
NEXT_PUBLIC_SUPABASE_URL=https://abcdefghij.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOi...        # 괜찮다
NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi... # 번들에 박힌다. 이 줄이 사고 원인이다
```

접두사를 빼면 서버에서만 보이는데, 이때도 함정이 있다. Next.js에서 `"use client"` 파일이 service_role 키를 쓰는 모듈을 import하면 빌드 에러 대신 `undefined`가 들어가서 "왜 인증이 안 되지" 하며 접두사를 붙여 버리는 일이 생긴다. 다른 프레임워크도 같은 부류다.

| 프레임워크 | 클라이언트에 노출되는 접두사 |
|---|---|
| Next.js | `NEXT_PUBLIC_` |
| Vite (React, Vue, Svelte) | `VITE_` |
| Create React App | `REACT_APP_` |
| Expo | `EXPO_PUBLIC_` |
| Nuxt | `runtimeConfig.public` 아래 값 |

유출 여부는 빌드 결과물에서 확인한다. JWT는 `header.payload.signature` 구조이고 payload는 단순 base64라서 `role` 값을 디코딩해 보면 anon인지 service_role인지 바로 나온다.

```bash
# 빌드 산출물에서 JWT 모양 문자열을 모아 role 클레임을 확인한다
grep -rhoE 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}' .next/static \
  | sort -u \
  | while read -r jwt; do
      payload=$(echo "$jwt" | cut -d. -f2 | tr '_-' '/+')
      # base64 패딩 보정
      while [ $(( ${#payload} % 4 )) -ne 0 ]; do payload="${payload}="; done
      echo "$payload" | base64 -d 2>/dev/null | grep -o '"role":"[a-z_]*"'
    done | sort | uniq -c
```

`service_role`이 한 건이라도 나오면 이미 배포된 번들에 박힌 것이다. 이후 대응은 순서가 있다.

1. 키를 지우고 재배포하는 것만으로는 부족하다. 이전 번들이 CDN 캐시나 브라우저에 남아 있고, 이미 누가 가져갔는지 알 수 없다.
2. 대시보드에서 JWT secret을 재발급(rotate)한다. service_role과 anon 키가 둘 다 바뀌고, 발급된 모든 사용자 세션이 무효화된다. 로그인 중인 사용자가 전부 로그아웃되는 비용을 감수해야 한다.
3. 새 키로 서버·클라이언트 환경변수를 갱신하고 재배포한다.
4. `auth.users`, 결제·개인정보 테이블에 대해 접근 로그가 있는지 본다. 호스팅 플랜에서 보존되는 로그 기간이 짧다.

JWT secret을 돌리면 anon 키도 같이 바뀌므로 모바일 앱처럼 배포 주기가 긴 클라이언트는 구버전이 한동안 전부 실패한다. 이런 앱을 운영한다면 처음부터 service_role을 앱 코드에 넣지 않는 것이 유일한 방어다.

## 클라이언트 직접 쿼리와 서버 직접 접속

Supabase를 쓰는 방식은 크게 두 가지이고, 신뢰 경계의 위치가 다르다.

```mermaid
flowchart LR
    subgraph A["방식 A, 클라이언트 직접 쿼리"]
        direction LR
        A1["브라우저 / 앱"] -->|"anon key + 사용자 JWT"| A2["Kong → PostgREST"]
        A2 --> A3[("Postgres")]
        A3 -.->|"RLS가 행을 걸러낸다"| A2
    end
    subgraph B["방식 B, 서버가 DB에 직접 접속"]
        direction LR
        B1["브라우저 / 앱"] -->|"자체 API 호출"| B2["Spring / Node 서버"]
        B2 -->|"JDBC, 풀러 6543 포트"| B3[("Postgres")]
        B2 -.->|"권한 검사는 서버 코드에서"| B1
    end
```

방식 A는 API 서버가 사라진다. 권한 검사가 전부 RLS 정책에 있고, 서버 배포도 없다. CRUD 중심의 앱, 프로토타입, 사용자별 데이터 격리가 단순한 서비스(내 메모, 내 주문)에서 개발 속도가 가장 빠르다. 대가로 비즈니스 규칙이 두 군데로 쪼개진다. "주문은 재고가 있을 때만 생성된다" 같은 규칙을 넣을 서버가 없으니 DB 함수(RPC)나 트리거, Edge Function으로 간다.

방식 B는 Supabase를 "비밀번호로 접속하는 관리형 Postgres"로만 쓴다. Spring이 HikariCP로 붙고 JPA도 그대로 쓴다. 인증을 Supabase Auth에 맡기더라도 서버가 JWT를 검증하는 쪽이다. 기존 백엔드가 있는 팀이 DB 호스팅만 옮길 때 이쪽이다.

### 둘을 섞을 때 생기는 문제

실무에서 가장 자주 하는 건 섞는 것이다. 프런트는 supabase-js로 단순 조회를 하고, 복잡한 쓰기는 Spring이 처리한다. 이 구성에서 만나는 문제를 정리한다.

**서버 접속은 RLS를 타지 않는다.** Spring이 `postgres` 계정으로 JDBC 접속하면 이 롤은 RLS를 우회한다. 정책이 아무리 있어도 서버 코드에서 `WHERE user_id = ?`를 빼먹으면 남의 데이터가 나간다. RLS를 지키는 건 PostgREST를 거치는 경로뿐이고, 서버 경로의 격리는 서버 코드가 책임진다. 보호막이 둘이 아니라 경로마다 하나씩이다. 서버용 롤을 별도로 만들어 `BYPASSRLS`를 주지 않고 필요한 테이블에만 GRANT하면 서버 경로도 정책을 타게 할 수 있지만, 그러려면 서버가 요청마다 `request.jwt.claims`를 세팅하는 코드를 직접 짜야 한다. 거기까지 가는 팀은 드물다.

**스키마 소유권이 둘로 갈린다.** Spring 쪽은 Flyway나 JPA `ddl-auto`로 테이블을 바꾸고, Supabase 쪽은 대시보드나 `supabase db diff`로 바꾸는 상황이 생긴다. 한쪽이 컬럼을 바꿨는데 다른 쪽은 모르고, RLS 정책이 걸린 컬럼 이름이 바뀌어 정책이 깨지는 경우도 있다. 마이그레이션 도구를 하나로 정해야 한다. 서버가 있다면 보통 Flyway를 원본으로 두고, Supabase CLI는 쓰지 않는다. 주의할 점은 `ddl-auto: update`가 `auth`, `storage` 스키마까지 건드리지 않게 `default_schema`를 `public`으로 고정하는 것이다.

**커넥션 수가 모자란다.** 무료·소형 플랜의 `max_connections`는 낮다. PostgREST, Realtime, Auth, Storage가 각자 풀을 잡고 있어서 서버에 쓸 수 있는 연결은 그보다 적다. Spring 인스턴스 3개에 `maximum-pool-size: 10`이면 30개를 잡는데, 여기에 대시보드 쿼리까지 합쳐지면 `remaining connection slots are reserved` 에러가 난다. 서버는 풀러(트랜잭션 모드)를 쓰고, 풀 크기는 인스턴스당 3~5개로 낮춘다.

```yaml
# application.yml, 풀러 트랜잭션 모드 (6543)
spring:
  datasource:
    url: jdbc:postgresql://aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?prepareThreshold=0
    username: postgres.abcdefghij        # postgres.<project-ref> 형식이다
    password: ${SUPABASE_DB_PASSWORD}
    hikari:
      maximum-pool-size: 4
      max-lifetime: 600000
```

풀러 사용자 이름이 `postgres`가 아니라 `postgres.<project-ref>`인 것을 놓치면 "Tenant or user not found"가 난다. 트랜잭션 모드에서는 서버 측 prepared statement를 재사용할 수 없어서 pgjdbc의 `prepareThreshold=0`을 붙여야 한다. 안 붙이면 평소엔 멀쩡하다가 부하가 올라 같은 SQL이 5번 넘게 반복될 때쯤 `prepared statement "S_1" already exists` 에러가 튀어나온다. 이 에러는 재현이 불규칙해서 원인 찾는 데 시간이 오래 걸린다.

직접 접속 주소(`db.<ref>.supabase.co:5432`)는 기본이 IPv6 전용이다. IPv4만 되는 환경(일부 VPC, 사내망, 한동안의 GitHub Actions 러너)에서는 DNS는 풀리는데 접속이 안 된다. 풀러 주소는 IPv4로도 열려 있어서 이 문제가 없다. Railway에서 붙을 때 풀러 URL을 쓰는 이유가 이것이기도 하다. 구체적인 연결 문자열은 [Railway 데이터베이스 서비스](../Railway/Railway_Database.md)의 Supabase 항목에 있다.

**서버가 Supabase 사용자를 알아본다.** 프런트가 Supabase Auth로 로그인하고 같은 JWT를 Spring API에 보내는 구성은 흔하다. Spring은 JWT secret(HS256)으로 서명을 검증하고 `sub`를 사용자 ID로 쓴다.

```java
@Bean
JwtDecoder jwtDecoder(@Value("${supabase.jwt-secret}") String secret) {
    SecretKeySpec key = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
    return NimbusJwtDecoder.withSecretKey(key)
            .macAlgorithm(MacAlgorithm.HS256)
            .build();
}
```

이 방식은 서버가 JWT secret을 알아야 한다는 뜻이다. 서버 한 곳이 털리면 모든 사용자 토큰을 위조할 수 있다. 프로젝트 설정에서 비대칭 서명 키(JWKS 공개키 방식)를 쓸 수 있는 경우라면 서버는 공개키만 가지면 되므로 그쪽이 안전하다. 어느 쪽이든 토큰의 `aud`가 `authenticated`인지, `role`이 `anon`이 아닌지를 서버가 확인해야 한다. anon 키도 서명은 유효한 JWT라서 검증만 통과하면 그냥 지나간다.

## 무료 티어와 Pro 전환 기준

무료 플랜에서 막히는 건 대개 용량이 아니라 운영 쪽 제약이다. 개인 프로젝트에서 직접 겪은 순서대로 적는다.

```mermaid
stateDiagram-v2
    [*] --> Active: 프로젝트 생성
    Active --> Paused: 7일간 활동 없음
    Paused --> Active: 대시보드에서 Restore
    Paused --> Expired: 보존 기간 초과
    Expired --> [*]: 복원 불가, 백업 다운로드만
    Active --> ReadOnly: DB 500MB 초과
    ReadOnly --> Active: 데이터 정리 또는 Pro 전환
```

| 항목 | 무료 | Pro (월 $25~) |
|---|---|---|
| 비활성 일시 중지 | 7일 비활성 시 중지 | 없음 |
| DB 용량 | 500MB | 8GB 포함, 초과분 과금 |
| 백업 | 제공하지 않음 | 일 단위 백업 (보존 7일), PITR은 유료 애드온 |
| 활성 프로젝트 수 | 조직당 2개 | 제한 없음 (프로젝트마다 컴퓨트 요금) |
| 월 사용자(MAU) | 5만 | 10만 포함 |
| 파일 저장 | 1GB | 100GB 포함 |

일시 중지는 "요청이 없는 7일"로 판정되기 때문에 사이드 프로젝트가 가장 잘 걸린다. 중지된 프로젝트에 접속하면 연결이 거부되고 앱에서는 타임아웃이나 `fetch failed`로 보인다. 복원은 대시보드에서 버튼 한 번이지만, 복원 중에는 몇 분간 접속이 안 되고, 일정 기간이 지난 뒤에는 복원 자체가 안 돼서 백업 파일을 내려받는 것으로 끝난다. cron으로 주기적으로 가벼운 쿼리를 보내 중지를 피하는 방법이 알려져 있지만, 서비스 약관상 허용되는 방식인지 그때그때 확인해야 하고 무엇보다 이 방법에 의존하는 서비스는 이미 Pro 대상이다.

백업이 없다는 점이 일시 중지보다 위험하다. 무료 플랜에서 `DELETE FROM users;`를 where 없이 날리면 복구할 방법이 없다. 무료로 쓰는 동안에는 `pg_dump`를 직접 돌려야 한다.

```bash
# 풀러가 아니라 직접 접속(5432)으로 받는다. IPv6가 안 되면 세션 모드 풀러(5432)를 쓴다
pg_dump "postgresql://postgres:${SUPABASE_DB_PASSWORD}@db.abcdefghij.supabase.co:5432/postgres" \
  --schema=public --no-owner -Fc -f "backup_$(date +%F).dump"
```

`--schema=public`을 주면 `auth.users`가 빠져서 복원 후 로그인 사용자가 사라진다. 사용자까지 보존해야 하면 `auth` 스키마도 같이 받는다. 풀러 트랜잭션 모드(6543)로는 `pg_dump`가 동작하지 않으니 이 포트로 시도하지 않는다.

Pro로 넘어가는 기준은 요금이 아니라 상황이다. 사용자 데이터가 들어오기 시작했다면 그 순간이다. 잃으면 안 되는 데이터가 생긴 뒤에는 백업 없는 DB를 쓸 수 없다. 일시 중지가 한 번이라도 서비스 장애로 이어졌을 때, 개발·스테이징·운영을 분리해야 해서 프로젝트 2개 제한에 걸릴 때도 같다. DB가 300~400MB를 넘어 읽기 전용 전환이 가까워진 경우도 해당한다. 500MB를 넘으면 쓰기가 막혀 앱이 에러를 내고, 복구하려고 데이터를 지우는 쿼리조차 막히는 경우가 있다.

Pro도 만능은 아니다. 기본 컴퓨트가 작아서 쿼리 부하가 올라가면 컴퓨트 애드온을 따로 올려야 하고, 이 비용이 기본 $25보다 먼저 커진다. 월 청구서가 예상보다 많이 나오는 원인은 대개 Egress(전송량)와 컴퓨트 업그레이드다.

## 다른 선택지와 비교

같은 목적(앱의 백엔드를 빨리 갖추기)에서 자주 같이 놓고 비교하는 것들이다. 이름은 비슷하지만 성격이 꽤 다르다.

| 항목 | Supabase | Firebase | AWS RDS | Neon |
|---|---|---|---|---|
| DB 종류 | PostgreSQL | Firestore (문서형 NoSQL) | PostgreSQL, MySQL 등 | PostgreSQL |
| 인증 | 내장 (GoTrue) | 내장 (Firebase Auth) | 없음. Cognito 등을 따로 붙인다 | 없음 (Neon Auth는 별도 기능) |
| API 자동 생성 | PostgREST, GraphQL | SDK가 직접 접근 | 없음 | 없음 (HTTP용 서버리스 드라이버는 있다) |
| 권한 모델 | Postgres RLS | Security Rules | IAM + DB 계정 | DB 롤 |
| 실시간 구독 | 내장 | 내장 (가장 성숙) | 없음 | 없음 |
| 파일 저장 | 내장 | Cloud Storage | S3를 따로 | 없음 |
| 과금 기준 | 프로젝트 단위 월정액 + 초과분 | 읽기·쓰기 횟수, 사용량 | 인스턴스 시간 + 스토리지 + I/O | 컴퓨트 사용 시간 + 스토리지 |
| 아무도 안 쓸 때 | 무료는 중지, Pro는 상시 과금 | 사용량만큼 | 인스턴스는 계속 과금 | 컴퓨트를 0으로 내린다 (cold start 있음) |
| 데이터 이식성 | `pg_dump`로 어디든 | 내보내기 후 모델 변환 필요 | `pg_dump` | `pg_dump` |

이 표에서 읽어야 할 선택 기준을 몇 개로 줄이면 이렇다.

Firebase와 비교하면 데이터 모델이 첫 번째 갈림길이다. 관계가 있는 데이터(주문-상품-사용자 조인, 집계)가 중심이면 Firestore는 비정규화와 다중 쿼리를 감수해야 한다. 반대로 채팅이나 문서 단위 읽기가 대부분이고 오프라인 동기화가 필요한 모바일 앱은 Firebase가 낫다. Firestore는 읽기 횟수로 과금해서 목록 화면 하나가 문서 수백 건을 읽는 구조면 청구서가 예상 밖으로 오른다. Supabase에는 이런 건당 과금이 없는 대신 쿼리 하나가 DB를 오래 점유하면 전체가 느려진다.

RDS와 비교하면 책임 범위의 차이다. RDS는 DB만 준다. 인증, API, 스토리지는 직접 만들거나 다른 AWS 서비스로 조립해야 하고, 그만큼 VPC·보안 그룹·IAM으로 네트워크를 닫을 수 있다. Supabase는 DB가 공개 인터넷에 열려 있는 것이 기본이다(IP 제한 옵션은 있다). 보안 요건상 DB가 사설망 안에 있어야 하거나, 컴플라이언스 때문에 리전과 접근 경로를 통제해야 하면 RDS 쪽이 맞다.

Neon과 비교하면 Supabase는 "Postgres + 백엔드 기능 일체"이고 Neon은 "Postgres만, 대신 브랜칭과 scale-to-zero". 이미 서버 코드가 있고 DB만 필요하다면 Neon이 더 좁고 단순하다. PR마다 DB 브랜치를 만들어 마이그레이션을 검증하는 흐름은 Neon의 강점이다. Supabase도 브랜칭 기능이 있지만 별도 프로젝트 단위로 과금된다.

Railway 내장 Postgres와는 앞서 링크한 [Railway 데이터베이스 서비스](../Railway/Railway_Database.md)에서 다뤘듯이 백업, 풀링, 대시보드 차이다. 앱이 Railway에 있고 DB만 Supabase에 둘 때는 리전을 맞춘다. 앱이 미국 리전이고 DB가 도쿄면 쿼리마다 왕복 지연이 붙어서, 한 요청에서 쿼리를 10번 날리는 ORM 코드가 눈에 띄게 느려진다.

## 쓰지 말아야 할 경우

도입 판단에서 가장 중요한 부분이다. 아래 상황은 처음엔 잘 돌아가다가 몇 달 뒤 비용이 커진다.

```mermaid
flowchart TD
    Q1{"권한이 행 소유자 기준으로<br/>단순하게 정리되는가"} -->|"아니오"| X1["서버에 권한 로직을 둔다<br/>방식 B 또는 다른 DB 선택"]
    Q1 -->|"예"| Q2{"도메인 규칙이 복잡한가<br/>(재고, 정산, 상태 전이 등)"}
    Q2 -->|"예"| X2["서버 코드로 구현한다<br/>Supabase는 DB와 Auth만 사용"]
    Q2 -->|"아니오"| Q3{"1년 뒤 이전할 가능성이<br/>있는가"}
    Q3 -->|"예"| X3["Auth, Storage, Realtime 의존을<br/>어댑터 뒤로 숨긴다"]
    Q3 -->|"아니오"| OK["Supabase를 그대로 쓴다"]
```

**도메인 로직이 전부 DB 함수로 이사 가는 경우.** 방식 A로 시작하면 서버가 없으니 복잡한 쓰기는 PL/pgSQL 함수(RPC)나 트리거로 들어간다. 처음 몇 개는 편하다. 주문 생성에 재고 차감, 쿠폰 사용 처리, 포인트 적립, 알림 큐 적재가 붙고 그게 함수 하나에 200줄이 되면 문제가 시작된다. PL/pgSQL은 단위 테스트가 어렵고, 디버거가 없고, 에러 메시지가 불친절하며, 코드 리뷰도 마이그레이션 SQL 파일 diff로 해야 한다. 배포는 함수 교체라서 롤백이 코드 롤백만큼 쉽지 않다. 트랜잭션이 여러 단계에 걸쳐 외부 API 호출(결제 승인)과 섞이는 도메인은 DB 안에서 끝낼 수 없어서 결국 Edge Function이나 서버가 하나 필요해진다. 그 시점에는 로직이 DB와 서버 양쪽에 흩어져 있다. 도메인 규칙이 복잡할 것이 처음부터 보이면, 방식 B로 서버에 로직을 두고 Supabase는 Postgres와 Auth 용도로만 쓴다.

**RLS 정책이 행 소유자 이상으로 복잡해지는 경우.** `user_id = auth.uid()` 수준은 읽기 쉽다. 조직-팀-역할 계층에서 "팀원은 읽기, 팀장은 쓰기, 조직 관리자는 전체" 같은 정책은 서브쿼리가 중첩되고, 정책 안의 서브쿼리가 같은 테이블의 RLS를 다시 타서 재귀 에러가 나거나 쿼리마다 느려진다. 정책에서 쓰는 컬럼에 인덱스가 없으면 행마다 서브쿼리를 평가해서 테이블이 커지면 급격히 느려진다. 이런 구조는 `SECURITY DEFINER` 함수로 감싸야 하는데, 이 함수가 곧 보안 구멍이 되기 쉽다. 정책 수정 하나가 테스트 없이 전 사용자의 접근 범위를 바꾼다는 점도 부담이다.

**뷰를 만들었는데 RLS가 안 먹는 경우.** Postgres에서 뷰는 기본적으로 뷰 소유자(보통 `postgres`) 권한으로 실행돼서 하위 테이블의 RLS를 우회한다. PostgREST로 노출된 뷰가 소유자의 권한으로 전체 데이터를 돌려주는 사고가 있다. PostgreSQL 15 이상에서는 `CREATE VIEW ... WITH (security_invoker = true)`로 호출자 권한을 쓰게 해야 한다. 대시보드가 이 문제를 경고하지만 무시하기 쉽다.

**벤더 락인을 얼마나 감수하는가.** Postgres 자체는 이식이 쉽다. 락인은 그 위의 것들이다.

| 의존 대상 | 이식 비용 |
|---|---|
| 테이블, 인덱스, 일반 SQL 함수 | 거의 없음. `pg_dump`로 끝난다 |
| RLS 정책 | `auth.uid()`가 Supabase 전용이라 다른 곳에서는 대체 함수를 만들어야 한다 |
| `auth.users`와 비밀번호 해시 | 해시 형식(bcrypt)을 새 시스템이 받아줘야 한다. 소셜 로그인 연결 정보도 옮겨야 한다 |
| Storage 객체와 정책 | 파일은 S3 호환이라 옮기기 쉽지만 접근 제어 정책은 다시 짜야 한다 |
| Realtime 구독 | 클라이언트 코드를 전부 교체해야 한다 |
| supabase-js 호출이 컴포넌트 곳곳에 | 쿼리 문법이 PostgREST 전용이라 전부 다시 쓴다 |

가장 비싼 건 마지막 행이다. `supabase.from('orders').select('*, items(*)')` 같은 호출이 프런트 전체에 퍼져 있으면 DB를 옮기는 게 아니라 데이터 접근 계층을 전부 다시 짜는 일이 된다. 이전 가능성이 조금이라도 있으면 데이터 접근을 한 모듈(repository 계층)에 모아 두고, 컴포넌트에서는 supabase-js를 직접 부르지 않는다.

**셀프호스팅으로 락인을 피하려는 경우.** 오픈소스라서 직접 띄울 수 있지만 컨테이너 10개 안팎을 운영해야 하고, 호스팅 버전에 있는 기능 일부(브랜칭, 대시보드의 일부 관리 기능)가 빠져 있다. 락인을 피하려고 셀프호스팅을 택하면 DB 운영이 필요 없어지는 이점이 사라진다. 이 경우는 처음부터 RDS나 직접 띄운 Postgres에 필요한 컴포넌트만 붙이는 편이 낫다.

Supabase가 잘 맞는 쪽은 이런 경우다. 사용자별로 데이터가 갈리는 CRUD 중심 앱, 1~3인 규모의 초기 제품, 인증·파일·실시간을 한 번에 갖춰야 하는 MVP, 이미 Postgres를 쓰고 있어서 호스팅과 부가 기능만 필요한 팀. 도메인 규칙이 두꺼운 서비스나 DB를 사설망에 가둬야 하는 서비스는 Supabase를 DB 호스팅과 Auth 정도로 좁혀 쓰거나 쓰지 않는다.
