---
title: OAuth 2.0 / OIDC Flow 종류별 심화 구현
tags: [backend, auth, jwt]
updated: 2026-10-28
---

# OAuth 2.0 / OIDC Flow 종류별 심화 구현

## 들어가며

`Auth_Strategy_Deep_Dive.md`에서는 OAuth2와 OIDC가 왜 분리됐는지, ID Token과 Access Token을 왜 섞어 쓰면 안 되는지를 다뤘다. 이 문서는 그 다음 단계 - 실제로 어떤 Flow를 골라야 하고, 골랐으면 어디서 발이 걸리는지를 정리한다.

OAuth2 스펙은 RFC 6749 하나만 보면 끝나는 것처럼 보이지만, 실제 구현에서는 RFC 7636(PKCE), RFC 8628(Device Code), RFC 8414(Authorization Server Metadata), RFC 7517(JWK), OIDC Core 1.0까지 같이 봐야 한다. 그리고 2025년 기준으로 Implicit Flow와 ROPC는 이미 OAuth 2.1 초안에서 빠졌다. 즉 "공식적으로 쓰지 말라"가 됐다.

여기서는 살아있는 Flow 세 개(Authorization Code + PKCE, Client Credentials, Device Code)를 어떻게 구현하는지, 죽은 Flow 두 개(Implicit, ROPC)는 왜 죽었는지, ID Token 검증과 JWKS 키 회전을 실제로 어떻게 처리해야 하는지를 다룬다. 마지막에는 Keycloak으로 OAuth2 서버를 직접 띄우고 Spring Boot 클라이언트와 붙이는 예제까지 간다.

## Flow 선택 의사결정

먼저 어떤 Flow를 써야 하는지부터 정리한다. 클라이언트 종류와 사용자 개입 여부에 따라 갈린다.

```
사용자가 직접 로그인하는가?
├─ 예
│   ├─ 클라이언트가 Secret을 안전하게 보관할 수 있는가?
│   │   ├─ 예 (서버 사이드 웹앱) → Authorization Code
│   │   └─ 아니오 (SPA, 모바일 앱)  → Authorization Code + PKCE
│   └─ 입력 장치가 제한적인가? (TV, CLI, IoT)
│       └─ 예 → Device Code
└─ 아니오 (서버 → 서버)
    └─ Client Credentials
```

이 트리에 한 가지 가정이 깔려있다. 클라이언트가 신뢰할 수 있는 환경에서 도는지(Confidential Client) 아니면 사용자 단말에서 도는지(Public Client)에 따라 보안 모델이 완전히 달라진다.

- Confidential Client: 백엔드 서버처럼 Secret을 노출 없이 보관할 수 있는 환경. `client_secret`으로 자기 정체를 증명한다.
- Public Client: SPA, 모바일 앱처럼 코드와 메모리가 사용자에게 노출되는 환경. `client_secret`을 박아넣어도 디컴파일이나 DevTools로 추출된다. 그래서 PKCE가 필수다.

이 구분을 잘못하면 모바일 앱에 client_secret을 박아 배포하는 사고가 난다. 실제로 깃허브에 client_secret이 노출된 안드로이드 앱 APK를 디컴파일해 토큰 발급한 사례가 매년 여러 건 보고된다.

## Authorization Code + PKCE

가장 많이 쓰는 Flow다. 2025년 기준 SPA, 모바일 앱, 심지어 서버 사이드 웹앱에서도 PKCE를 항상 켜는 것이 사실상 표준이 됐다.

### 전체 흐름

```mermaid
sequenceDiagram
    participant U as 사용자
    participant C as 클라이언트(SPA/모바일)
    participant AS as 인가 서버
    participant RS as 리소스 서버

    C->>C: code_verifier 생성 (랜덤 43~128자)
    C->>C: code_challenge = BASE64URL(SHA256(code_verifier))
    U->>C: 로그인 클릭
    C->>AS: /authorize?response_type=code&code_challenge=...&code_challenge_method=S256
    AS->>U: 로그인 화면
    U->>AS: 자격증명 입력
    AS->>C: redirect_uri?code=AUTHZ_CODE (302)
    C->>AS: /token (code + code_verifier)
    AS->>AS: SHA256(code_verifier) == 저장된 code_challenge?
    AS->>C: access_token + refresh_token + id_token
    C->>RS: GET /api/me (Authorization: Bearer ...)
    RS->>C: 200 OK
```

### code_verifier와 code_challenge가 푸는 문제

Authorization Code Flow의 원래 위협 모델은 이렇다. 인가 서버가 `redirect_uri`로 인가 코드를 던질 때, 이 코드가 중간에 탈취될 수 있다. 모바일 환경에서는 더 심각하다. 안드로이드의 Custom URL Scheme(`myapp://callback?code=...`)은 같은 스킴을 등록한 다른 앱이 가로챌 수 있다.

코드만 탈취해도 공격자가 `/token` 엔드포인트로 가서 토큰을 받을 수 있냐? 원래는 `client_secret`이 막아줬다. 그런데 Public Client는 secret이 없다. 그래서 Authorization Code의 진정한 소유자임을 증명할 다른 수단이 필요했고, 그게 PKCE다.

PKCE 동작:

```python
import secrets
import hashlib
import base64

def generate_pkce_pair():
    # code_verifier: 43~128자 랜덤
    code_verifier = secrets.token_urlsafe(64)[:128]

    # code_challenge: SHA256 해시 + Base64URL
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

    return code_verifier, code_challenge
```

핵심은 단방향 해시다. 공격자가 `code_challenge`를 봐도 `code_verifier`를 역산할 수 없다. 그래서 인가 코드가 탈취돼도 `code_verifier`가 없으면 토큰 교환이 안 된다.

`code_challenge_method`는 두 가지가 있다.

- `plain`: `code_challenge = code_verifier`. 의미가 없으니 쓰지 마라.
- `S256`: SHA256 해시. 무조건 이걸 써라.

인가 서버가 `plain`만 받는다면 그 서버는 PKCE를 흉내만 낸 것이다.

<div class="ygd-pkce-code-interception" id="ygd-pkce-code-interception">
<style>
.ygd-pkce-code-interception{--ygd-fg:#24292f;--ygd-muted:#5b636d;--ygd-card:#f7f7f5;--ygd-line:#9aa1a9;--ygd-acc:#1f6f8b;--ygd-acc-bg:#dcecf2;--ygd-bad:#b42318;--ygd-bad-bg:#fde4e1;--ygd-ok:#0f7a3d;--ygd-ok-bg:#dff3e6;--ygd-warn:#8a5a00;--ygd-warn-bg:#fdf0cf;--ygd-btn:#ffffff;max-width:760px;margin-left:auto;margin-right:auto;margin-top:16px;margin-bottom:16px;padding:12px;border:1px solid var(--ygd-line);border-radius:10px;background:var(--ygd-card);color:var(--ygd-fg);font-size:14px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-pkce-code-interception{--ygd-fg:#ece8e4;--ygd-muted:#a8a29a;--ygd-card:#26232a;--ygd-line:#6f6a72;--ygd-acc:#6fc0dc;--ygd-acc-bg:#17384a;--ygd-bad:#ff8a80;--ygd-bad-bg:#4a1f1c;--ygd-ok:#6fd49a;--ygd-ok-bg:#17402a;--ygd-warn:#f0c060;--ygd-warn-bg:#4a3a10;--ygd-btn:#322e36}
.ygd-pkce-code-interception *{box-sizing:border-box}
.ygd-pkce-code-interception .ygd-row{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px 0}
.ygd-pkce-code-interception .ygd-btn{font:inherit;font-size:14px;min-height:40px;padding:6px 14px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-btn);color:var(--ygd-fg);cursor:pointer}
.ygd-pkce-code-interception .ygd-btn:hover{border-color:var(--ygd-acc)}
.ygd-pkce-code-interception .ygd-btn:focus-visible{outline:3px solid var(--ygd-acc);outline-offset:2px}
.ygd-pkce-code-interception .ygd-btn:disabled{opacity:.5;cursor:not-allowed}
.ygd-pkce-code-interception .ygd-tg[aria-pressed="true"]{background:var(--ygd-acc-bg);border-color:var(--ygd-acc);font-weight:700}
.ygd-pkce-code-interception .ygd-play{font-weight:700}
.ygd-pkce-code-interception .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-pkce-code-interception .ygd-life{stroke:var(--ygd-line);stroke-width:1.2;stroke-dasharray:4 4}
.ygd-pkce-code-interception .ygd-hdr{fill:var(--ygd-btn);stroke:var(--ygd-line);stroke-width:1.2}
.ygd-pkce-code-interception .ygd-hn{fill:var(--ygd-fg);font-size:13px;font-weight:700;text-anchor:middle}
.ygd-pkce-code-interception .ygd-hs{fill:var(--ygd-muted);font-size:11px;text-anchor:middle}
.ygd-pkce-code-interception .ygd-brect{fill:transparent;stroke:var(--ygd-line);stroke-dasharray:3 3;stroke-width:1.2;transition:fill .3s}
.ygd-pkce-code-interception .ygd-bk,.ygd-pkce-code-interception .ygd-bs{font-size:11px;fill:var(--ygd-muted)}
.ygd-pkce-code-interception .ygd-b1 .ygd-brect{fill:var(--ygd-acc-bg);stroke:var(--ygd-acc);stroke-dasharray:none}
.ygd-pkce-code-interception .ygd-b2 .ygd-brect{fill:var(--ygd-warn-bg);stroke:var(--ygd-warn);stroke-dasharray:none}
.ygd-pkce-code-interception .ygd-b3 .ygd-brect{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad);stroke-dasharray:none}
.ygd-pkce-code-interception .ygd-b1 .ygd-bk,.ygd-pkce-code-interception .ygd-b1 .ygd-bs,.ygd-pkce-code-interception .ygd-b2 .ygd-bk,.ygd-pkce-code-interception .ygd-b2 .ygd-bs,.ygd-pkce-code-interception .ygd-b3 .ygd-bk,.ygd-pkce-code-interception .ygd-b3 .ygd-bs{fill:var(--ygd-fg)}
.ygd-pkce-code-interception .ygd-b1 .ygd-bs,.ygd-pkce-code-interception .ygd-b2 .ygd-bs,.ygd-pkce-code-interception .ygd-b3 .ygd-bs{font-weight:700}
.ygd-pkce-code-interception .ygd-ar{transition:opacity .3s}
.ygd-pkce-code-interception .ygd-future{opacity:.45}
.ygd-pkce-code-interception .ygd-past{opacity:.8}
.ygd-pkce-code-interception .ygd-now{opacity:1}
.ygd-pkce-code-interception .ygd-off{display:none}
.ygd-pkce-code-interception .ygd-ln{stroke-width:2;fill:none;stroke-dasharray:1}
.ygd-pkce-code-interception .ygd-now .ygd-ln{animation:ygd-pkce-code-interception-draw .7s ease-out both}
@keyframes ygd-pkce-code-interception-draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.ygd-pkce-code-interception .ygd-c-acc{stroke:var(--ygd-acc)}
.ygd-pkce-code-interception .ygd-c-bad{stroke:var(--ygd-bad)}
.ygd-pkce-code-interception .ygd-c-ok{stroke:var(--ygd-ok)}
.ygd-pkce-code-interception .ygd-mk-acc{fill:var(--ygd-acc)}
.ygd-pkce-code-interception .ygd-mk-bad{fill:var(--ygd-bad)}
.ygd-pkce-code-interception .ygd-mk-ok{fill:var(--ygd-ok)}
.ygd-pkce-code-interception .ygd-lb{font-size:12px;font-weight:600;text-anchor:middle;stroke:var(--ygd-card);stroke-width:4px;paint-order:stroke}
.ygd-pkce-code-interception .ygd-t-acc{fill:var(--ygd-acc)}
.ygd-pkce-code-interception .ygd-t-bad{fill:var(--ygd-bad)}
.ygd-pkce-code-interception .ygd-t-ok{fill:var(--ygd-ok)}
.ygd-pkce-code-interception .ygd-pill{stroke-width:1.5}
.ygd-pkce-code-interception .ygd-pill-warn{fill:var(--ygd-warn-bg);stroke:var(--ygd-warn)}
.ygd-pkce-code-interception .ygd-pill-ok{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok)}
.ygd-pkce-code-interception .ygd-pt{fill:var(--ygd-fg);font-size:11.5px;text-anchor:middle}
.ygd-pkce-code-interception .ygd-panel{margin:10px 0 0 0;padding:10px 12px;border-left:4px solid var(--ygd-acc);background:var(--ygd-btn);border-radius:0 8px 8px 0;min-height:9.5em}
.ygd-pkce-code-interception .ygd-step{font-size:15px;font-weight:700;margin:0}
.ygd-pkce-code-interception .ygd-desc{font-size:14px;margin:4px 0 0 0}
.ygd-pkce-code-interception .ygd-legend,.ygd-pkce-code-interception .ygd-note{font-size:14px;color:var(--ygd-muted);margin:10px 0 0 0}
@media (prefers-reduced-motion:reduce){.ygd-pkce-code-interception .ygd-now .ygd-ln{animation:none}.ygd-pkce-code-interception .ygd-ar,.ygd-pkce-code-interception .ygd-brect{transition:none}}
</style>
<div class="ygd-row" role="group" aria-label="PKCE 적용 여부 선택">
<button type="button" class="ygd-btn ygd-tg" data-mode="n" aria-pressed="true">PKCE 없음</button>
<button type="button" class="ygd-btn ygd-tg" data-mode="p" aria-pressed="false">PKCE 적용</button>
</div>
<div class="ygd-row" role="group" aria-label="재생 컨트롤">
<button type="button" class="ygd-btn ygd-play" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전</button>
<button type="button" class="ygd-btn" data-act="next">다음</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
<svg class="ygd-svg" viewBox="0 0 400 420" role="img" aria-label="인가 코드가 탈취됐을 때 PKCE 유무에 따라 결과가 달라지는 흐름도. 클라이언트, 공격자, 인가 서버가 각각 code, challenge, verifier, token을 가졌는지 단계마다 보여준다.">
<defs>
<marker id="ygd-pkce-code-interception-mk-acc" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-acc" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-pkce-code-interception-mk-bad" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-bad" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-pkce-code-interception-mk-ok" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-ok" d="M0 0L10 5L0 10z"/></marker>
</defs>
<line class="ygd-life" x1="66" y1="164" x2="66" y2="416"/>
<line class="ygd-life" x1="200" y1="164" x2="200" y2="416"/>
<line class="ygd-life" x1="334" y1="164" x2="334" y2="416"/>
<rect class="ygd-hdr" x="4" y="6" width="124" height="44" rx="8"/>
<text class="ygd-hn" x="66" y="25">클라이언트</text>
<text class="ygd-hs" x="66" y="41">정상 앱</text>
<rect class="ygd-hdr" x="138" y="6" width="124" height="44" rx="8"/>
<text class="ygd-hn" x="200" y="25">공격자</text>
<text class="ygd-hs" x="200" y="41">악성 앱</text>
<rect class="ygd-hdr" x="272" y="6" width="124" height="44" rx="8"/>
<text class="ygd-hn" x="334" y="25">인가 서버</text>
<text class="ygd-hs" x="334" y="41">/authorize, /token</text>
<g class="ygd-layer"></g>
<g class="ygd-ar" data-m="n" data-s="1"><line class="ygd-ln ygd-c-acc" pathLength="1" x1="72" y1="194" x2="328" y2="194" marker-end="url(#ygd-pkce-code-interception-mk-acc)"/><text class="ygd-lb ygd-t-acc" x="200" y="186">/authorize</text></g>
<g class="ygd-ar" data-m="p" data-s="1"><line class="ygd-ln ygd-c-acc" pathLength="1" x1="72" y1="194" x2="328" y2="194" marker-end="url(#ygd-pkce-code-interception-mk-acc)"/><text class="ygd-lb ygd-t-acc" x="200" y="186">/authorize + code_challenge</text></g>
<g class="ygd-ar" data-m="np" data-s="2"><line class="ygd-ln ygd-c-acc" pathLength="1" x1="328" y1="236" x2="72" y2="236" marker-end="url(#ygd-pkce-code-interception-mk-acc)"/><text class="ygd-lb ygd-t-acc" x="200" y="228">302 redirect + code</text></g>
<g class="ygd-ar" data-m="np" data-s="2"><line class="ygd-ln ygd-c-bad" pathLength="1" x1="328" y1="266" x2="206" y2="266" marker-end="url(#ygd-pkce-code-interception-mk-bad)"/><text class="ygd-lb ygd-t-bad" x="267" y="258">code 가로챔</text></g>
<g class="ygd-ar" data-m="np" data-s="3"><line class="ygd-ln ygd-c-bad" pathLength="1" x1="206" y1="308" x2="328" y2="308" marker-end="url(#ygd-pkce-code-interception-mk-bad)"/><text class="ygd-lb ygd-t-bad" x="267" y="300">/token (code)</text></g>
<g class="ygd-ar" data-m="n" data-s="4"><rect class="ygd-pill ygd-pill-warn" x="270" y="326" width="128" height="42" rx="8"/><text class="ygd-pt" x="334" y="344">code 유효성만 확인</text><text class="ygd-pt" x="334" y="360">비교 대상 없음</text></g>
<g class="ygd-ar" data-m="p" data-s="4"><rect class="ygd-pill ygd-pill-ok" x="270" y="326" width="128" height="42" rx="8"/><text class="ygd-pt" x="334" y="344">SHA256(verifier)</text><text class="ygd-pt" x="334" y="360">≠ 저장된 challenge</text></g>
<g class="ygd-ar" data-m="n" data-s="5"><line class="ygd-ln ygd-c-bad" pathLength="1" x1="328" y1="408" x2="206" y2="408" marker-end="url(#ygd-pkce-code-interception-mk-bad)"/><text class="ygd-lb ygd-t-bad" x="267" y="400">access_token 발급</text></g>
<g class="ygd-ar" data-m="p" data-s="5"><line class="ygd-ln ygd-c-ok" pathLength="1" x1="328" y1="408" x2="206" y2="408" marker-end="url(#ygd-pkce-code-interception-mk-ok)"/><text class="ygd-lb ygd-t-ok" x="267" y="400">토큰 교환 거부</text></g>
</svg>
<div class="ygd-panel" aria-live="polite"><p class="ygd-step"></p><p class="ygd-desc"></p></div>
<p class="ygd-legend">범례: 보유는 해당 값을 실제로 가지고 있다는 뜻이고, 노출은 값을 볼 수는 있지만 그것만으로는 쓸 수 없다는 뜻이다. 점선 칸은 없음이다.</p>
<p class="ygd-note">비유: 인가 코드는 택배 송장번호이고, code_verifier는 주문자만 아는 수령 비밀번호다. 업체가 비밀번호 자체가 아니라 그 해시만 저장해 두면, 송장번호만 훔친 사람은 비밀번호를 대지 못한다. 실제 보장은 단방향 해시에서 나온다.</p>
<script>
(function(){
var root=document.getElementById('ygd-pkce-code-interception');
if(!root){return;}
var $=function(s){return root.querySelector(s);};
var $$=function(s){return Array.prototype.slice.call(root.querySelectorAll(s));};
var mode='n',step=0,timer=null,LAST=5;
var TXT=['없음','보유','노출','보유'];
var KEYS=['code','challenge','verifier','token'];
var COLS=[66,200,334];
var H={
n:[['0000','0000','0000'],['0000','0000','0000'],['1000','1000','1000'],['1000','1000','1000'],['1000','1000','1000'],['1000','1003','1000']],
p:[['0110','0000','0000'],['0110','0000','0100'],['1110','1200','1100'],['1110','1200','1100'],['1110','1200','1100'],['1110','1200','1100']]
};
var D={
n:[
['준비','Public Client는 client_secret이 없다. 그래서 인가 서버는 /token에서 code를 가져온 쪽이 원래 요청자인지 확인할 수단이 없다. 이 상태에서 code가 탈취되면 어떻게 되는지 따라가 본다.'],
['/authorize 요청','클라이언트가 code_challenge 없이 /authorize를 호출한다. 인가 서버는 나중에 대조할 값을 아무것도 저장하지 않는다.'],
['code가 가로채임','인가 서버가 redirect_uri로 code를 보낸다. 같은 Custom URL Scheme을 등록한 악성 앱이 이 code를 함께 가져간다.'],
['공격자가 /token 호출','공격자가 가로챈 code로 /token을 직접 호출한다. client_secret이 없는 Public Client라 요청에 붙일 수 있는 값은 code가 전부다.'],
['서버 검증','인가 서버는 code가 유효한지만 확인한다. 소유자를 증명할 값이 요청에 없어도 거부할 근거가 없다.'],
['토큰 발급: 탈취 성공','인가 서버가 공격자에게 access_token을 발급한다. 공격자는 사용자 로그인 없이 토큰을 손에 넣었다.']
],
p:[
['준비: verifier와 challenge 생성','클라이언트가 랜덤한 code_verifier를 만들고 code_challenge를 BASE64URL(SHA256(code_verifier))로 계산한다. verifier는 클라이언트만 가진다.'],
['/authorize + code_challenge','클라이언트는 code_challenge와 S256 방식만 /authorize에 실어 보낸다. verifier 자체는 보내지 않는다. 인가 서버는 challenge를 code와 묶어 저장한다.'],
['code가 가로채임','인가 서버가 code를 보내고 악성 앱이 이를 가로챈다. 공격자는 code를 갖고 challenge도 볼 수 있지만, 단방향 해시라 verifier를 역산할 수 없다.'],
['공격자가 /token 호출','공격자가 code만 들고 /token을 호출한다. 요청에 붙일 code_verifier가 없다.'],
['SHA256 대조','인가 서버가 SHA256(code_verifier)와 저장된 code_challenge를 비교한다. 공격자 요청에는 verifier가 없어 값이 일치하지 않는다.'],
['거부: 토큰 없음','인가 서버가 토큰 교환을 거부한다. 공격자는 code를 갖고 있어도 토큰을 받지 못한다. 정상 클라이언트는 자기 verifier를 보내 교환할 수 있다.']
]
};
var layer=$('.ygd-layer'),h='',a,r,x,y;
for(a=0;a<3;a++){for(r=0;r<4;r++){x=COLS[a]-56;y=58+r*26;
h+='<g class="ygd-badge" data-a="'+a+'" data-r="'+r+'"><rect class="ygd-brect" x="'+x+'" y="'+y+'" width="112" height="22" rx="6"/><text class="ygd-bk" x="'+(x+6)+'" y="'+(y+15)+'">'+KEYS[r]+'</text><text class="ygd-bs" x="'+(x+106)+'" y="'+(y+15)+'" text-anchor="end"></text></g>';}}
layer.innerHTML=h;
var playBtn=$('[data-act="play"]'),prevBtn=$('[data-act="prev"]'),nextBtn=$('[data-act="next"]');
function render(){
var st=H[mode][step];
$$('.ygd-badge').forEach(function(g){
var d=st[+g.getAttribute('data-a')].charAt(+g.getAttribute('data-r'));
g.setAttribute('class','ygd-badge ygd-b'+d);
g.querySelector('.ygd-bs').textContent=TXT[+d];
});
$$('.ygd-ar').forEach(function(g){
var on=g.getAttribute('data-m').indexOf(mode)>-1;
var s=+g.getAttribute('data-s');
g.setAttribute('class','ygd-ar '+(on?'':'ygd-off ')+(s<step?'ygd-past':(s===step?'ygd-now':'ygd-future')));
});
$('.ygd-step').textContent='단계 '+step+' / '+LAST+' · '+D[mode][step][0];
$('.ygd-desc').textContent=D[mode][step][1];
$$('.ygd-tg').forEach(function(b){b.setAttribute('aria-pressed',b.getAttribute('data-mode')===mode?'true':'false');});
prevBtn.disabled=step<=0;
nextBtn.disabled=step>=LAST;
playBtn.textContent=timer?'일시정지':'재생';
}
function stop(){if(timer){clearInterval(timer);timer=null;}}
function play(){
if(timer){stop();render();return;}
if(step>=LAST){step=0;}
timer=setInterval(function(){
step++;
if(step>=LAST){stop();}
render();
},2800);
render();
}
root.addEventListener('click',function(e){
var t=e.target;
if(!t||!t.closest){return;}
var b=t.closest('button');
if(!b||!root.contains(b)){return;}
var m=b.getAttribute('data-mode'),act=b.getAttribute('data-act');
if(m){stop();mode=m;step=0;render();}
else if(act==='play'){play();}
else if(act==='prev'){stop();if(step>0){step--;}render();}
else if(act==='next'){stop();if(step<LAST){step++;}render();}
else if(act==='reset'){stop();step=0;render();}
});
render();
})();
</script>
</div>

### 인가 코드 재사용 방지

`/token` 호출에서 인가 코드는 1회만 사용 가능해야 한다. 두 번째 사용이 들어오면 인가 서버는 다음을 모두 해야 한다.

1. 두 번째 토큰 교환 거부
2. 첫 번째 교환에서 발급된 토큰 모두 무효화 (refresh token 포함)

이게 RFC 6749 §10.5에 권장으로 적혀있는데, 실제로는 거의 모든 인가 서버가 이렇게 한다. 인가 코드 재사용은 코드 탈취의 강한 신호다.

### redirect_uri는 정확히 일치해야 한다

흔한 함정이다. 인가 서버에 등록된 `redirect_uri`가 `https://app.example.com/callback`인데, `/authorize`에 `https://app.example.com/callback/`(슬래시 추가) 또는 `https://app.example.com/callback?foo=bar`(쿼리 추가)로 보내면 거부된다. RFC 6749는 정확한 문자열 일치를 요구한다.

이걸 느슨하게 처리하는 인가 서버는 Open Redirect 공격에 취약하다. 예를 들어 prefix 매칭을 한다면 `https://app.example.com/callback.attacker.com`으로 우회 가능하다.

### code_verifier 저장 위치

SPA에서 `/authorize`로 리다이렉트된 후 콜백이 돌아올 때까지 `code_verifier`를 보관해야 한다. 이걸 어디에 둘지가 문제다.

- `sessionStorage`: 가장 흔한 선택. 탭 닫으면 사라지고, 다른 탭과 격리된다.
- `localStorage`: 다른 탭에서도 접근 가능해 멀티탭 시나리오가 깔끔하지만 XSS에 더 취약하다.
- 메모리 변수: 새로고침이나 리다이렉트 후 사라지므로 OAuth 콜백에는 못 쓴다.

`sessionStorage`가 표준 선택이다. 단, OAuth 콜백 직후 `code_verifier`를 즉시 삭제해야 한다. 토큰 교환 끝나면 더 이상 필요 없다.

```javascript
// 콜백 페이지
async function handleCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const state = params.get('state');

  const savedState = sessionStorage.getItem('oauth_state');
  const codeVerifier = sessionStorage.getItem('pkce_verifier');

  if (state !== savedState) throw new Error('CSRF detected');

  try {
    const tokens = await fetch('/oauth/token', {
      method: 'POST',
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        code_verifier: codeVerifier,
        client_id: CLIENT_ID,
        redirect_uri: REDIRECT_URI,
      }),
    }).then(r => r.json());

    return tokens;
  } finally {
    sessionStorage.removeItem('pkce_verifier');
    sessionStorage.removeItem('oauth_state');
  }
}
```

`state` 파라미터는 CSRF 방지용이다. `/authorize` 호출 시 랜덤 값을 넣고, 콜백에서 동일한지 확인한다. PKCE가 코드 탈취를 막는다면, `state`는 사용자가 의도하지 않은 OAuth 콜백을 막는다. OIDC에서는 `nonce`도 추가로 쓴다(이건 ID Token 검증 절에서 다룬다).

## Client Credentials (M2M)

서버가 다른 서버를 호출할 때, 사용자가 개입하지 않는 경우다. 배치 작업이 외부 API를 호출한다거나, 마이크로서비스끼리 토큰을 주고받을 때 쓴다.

### 흐름

```
POST /oauth/token
Authorization: Basic BASE64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&scope=read:orders write:invoices

→ 200 OK
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read:orders write:invoices"
}
```

Refresh Token이 없다는 점이 중요하다. 만료되면 그냥 Client Credentials로 다시 발급받는다. 사용자 컨텍스트가 없으니 `id_token`도 없다.

### 클라이언트 인증 방식

`client_secret`을 어떻게 보내느냐에 따라 종류가 갈린다.

- `client_secret_basic`: HTTP Basic 헤더로 전송. 가장 흔하다.
- `client_secret_post`: 본문에 `client_id`와 `client_secret`을 같이 넣음. 일부 서버에서만 지원.
- `client_secret_jwt`: HMAC으로 서명한 JWT를 `client_assertion`으로 보냄. Secret 자체를 네트워크에 노출하지 않음.
- `private_key_jwt`: RSA/EC 개인키로 서명한 JWT. Secret 자체가 없음. 가장 안전.
- `tls_client_auth` (mTLS): TLS 클라이언트 인증서로 인증.

금융권이나 헬스케어처럼 규제가 강한 환경에서는 `private_key_jwt`나 mTLS를 요구한다. 일반 서비스에서는 `client_secret_basic`으로 충분하다.

### Scope 설계가 핵심이다

Client Credentials의 가장 흔한 실수가 모든 클라이언트에게 같은 스코프를 주는 것이다. 그러면 토큰 하나가 유출됐을 때 피해 범위가 무제한이다.

서비스 단위로 클라이언트를 분리하고, 각 클라이언트별로 필요한 최소 scope만 부여해야 한다. 예를 들어 결제 정산 배치는 `read:payments`만, 알림 발송 서비스는 `write:notifications`만.

### 토큰 캐싱

Client Credentials 토큰은 만료까지 재사용 가능하다. 매 요청마다 발급받으면 인가 서버에 부하를 준다. 보통 만료 시간의 80% 정도까지 캐시하다가 갱신한다.

```typescript
interface CachedToken {
  token: string;
  expiresAt: number;
}

interface TokenResponse {
  accessToken: string;
  expiresIn: number;
}

class TokenCache {
  private cache: CachedToken | null = null;
  private refreshing: Promise<string> | null = null;

  async getToken(): Promise<string> {
    const now = Date.now();
    if (this.cache && this.cache.expiresAt > now + 60_000) {
      return this.cache.token;
    }

    // 동시 갱신 방지
    if (this.refreshing) {
      return this.refreshing;
    }

    this.refreshing = this.fetchNewToken().then((fresh) => {
      this.cache = {
        token: fresh.accessToken,
        expiresAt: now + fresh.expiresIn * 1000,
      };
      this.refreshing = null;
      return this.cache.token;
    });

    return this.refreshing;
  }

  private async fetchNewToken(): Promise<TokenResponse> {
    // Client Credentials 토큰 발급 로직
    throw new Error('구현 필요');
  }
}
```

만료 60초 전에 갱신하는 이유는 시계 차이와 네트워크 지연을 흡수하려는 것이다. 너무 빠르게 갱신하면 토큰 발급이 잦아지고, 너무 늦게 갱신하면 만료된 토큰으로 호출했다가 401을 받는다.

## Device Code Flow

TV, 게임 콘솔, CLI 도구처럼 키보드가 없거나 입력이 불편한 장치에서 OAuth 로그인을 처리하는 Flow다. RFC 8628이다.

### 흐름

```mermaid
sequenceDiagram
    participant D as 디바이스(TV/CLI)
    participant U as 사용자(폰/노트북)
    participant AS as 인가 서버

    D->>AS: POST /device_authorization
    AS->>D: device_code, user_code, verification_uri, interval
    D->>U: "https://example.com/device 에 접속해서 ABCD-1234 입력"
    loop 사용자 인증 대기 (interval 초마다)
        D->>AS: POST /token (grant_type=device_code, device_code=...)
        AS->>D: authorization_pending 또는 slow_down
    end
    U->>AS: verification_uri 접속, user_code 입력, 로그인, 동의
    D->>AS: POST /token
    AS->>D: access_token + refresh_token (+ id_token if OIDC)
```

### 두 종류의 코드

- `device_code`: 디바이스가 토큰 폴링할 때 쓰는 긴 랜덤 문자열. 사람이 보지 않는다.
- `user_code`: 사용자가 폰에 입력하는 짧은 코드(예: `WDJB-MJHT`). 8자 정도가 표준.

`user_code`는 사람이 입력하므로 시각적으로 구분되는 문자만 써야 한다. `0/O`, `1/I/l` 같은 헷갈리는 문자는 빼는 것이 권장 사항이다(RFC 8628 §6.1).

### 폴링 간격과 백오프

디바이스는 `interval` 초마다 `/token`을 폴링한다. 이때 인가 서버 응답 두 가지를 처리해야 한다.

- `authorization_pending`: 사용자가 아직 인증 안 했다. 그대로 기다린다.
- `slow_down`: 폴링이 너무 빠르다. interval에 5초를 더한다(RFC 8628 §3.5).

너무 자주 폴링하면 `slow_down`을 받게 되고, 그래도 안 늘리면 차단당할 수 있다.

### 보안 고려사항

Device Code Flow는 피싱에 취약하다. 공격자가 자기 디바이스에서 인증 요청을 시작한 뒤, 거기서 받은 `user_code`를 피해자에게 보내 입력하게 만들 수 있다. 피해자가 입력하는 순간 공격자 디바이스가 토큰을 받는다.

이걸 막으려면 사용자 동의 화면에서 디바이스 정보를 명확히 보여줘야 한다. "Smart TV in living room이 당신의 계정에 접근하려 합니다" 같은 식으로. 그래도 사용자가 조심성 없으면 막기 어렵다.

추가로 `verification_uri_complete`라는 필드가 있다. `verification_uri?user_code=WDJB-MJHT` 형태로 사용자가 코드 입력 단계를 건너뛰게 해준다. QR 코드로 만들어 보여주기 좋다. 단, 이걸 쓰면 피싱이 더 쉬워진다는 점은 같다.

## 폐기된 Flow들

### Resource Owner Password Credentials (ROPC)

```
POST /oauth/token
grant_type=password&username=...&password=...&client_id=...
```

사용자의 ID/비번을 클라이언트가 직접 받아서 인가 서버에 넘기는 Flow다. OAuth 2.1에서 완전히 빠졌다. 이유는 명확하다.

- OAuth의 핵심 가치인 "비밀번호를 클라이언트에 노출하지 않는다"를 정면으로 위배한다.
- 클라이언트가 비밀번호를 메모리/로그/네트워크에 노출시킬 수 있다.
- MFA, 캡챠, 위험 기반 인증을 우회한다.
- SSO 시나리오와 호환되지 않는다.

그럼에도 레거시 모바일 앱 마이그레이션 같은 시나리오에서 임시로 쓰는 경우가 있다. 새로 짓는 코드라면 절대 선택하지 마라. Authorization Code + PKCE로 가야 한다.

### Implicit Flow

```
GET /authorize?response_type=token&client_id=...&redirect_uri=...
→ redirect_uri#access_token=...
```

토큰을 URL 프래그먼트로 직접 받는 Flow다. 인가 코드 단계가 없다. 한때는 SPA의 표준 Flow였다.

문제는 토큰이 브라우저 히스토리, Referer 헤더, 서버 액세스 로그 등 여러 곳에 새는 것이었다. 그리고 PKCE가 등장하면서 SPA도 Authorization Code + PKCE를 쓸 수 있게 됐다. 그래서 OAuth 2.0 Security Best Current Practice(RFC 8252의 후속)에서 권장하지 않는 것으로 분류됐고, OAuth 2.1에서 빠졌다.

OIDC에서는 Hybrid Flow(`response_type=code id_token`)에서 `id_token`을 프래그먼트로 받는 변형이 있긴 한데, 이것도 점점 줄어들고 있다.

### 정리

| Flow | 2025년 상태 | 대체재 |
|------|-----------|--------|
| Authorization Code | 권장 | 그대로 사용 |
| Authorization Code + PKCE | 권장 (사실상 표준) | 그대로 사용 |
| Client Credentials | 권장 | 그대로 사용 |
| Device Code | 권장 | 그대로 사용 |
| Refresh Token | 권장 | 그대로 사용 (회전 필수) |
| Implicit | 폐기 | Authorization Code + PKCE |
| Resource Owner Password | 폐기 | Authorization Code + PKCE |

## OIDC ID Token 검증 절차

OIDC를 쓰면 토큰 응답에 `id_token`이 포함된다. 이걸 검증하지 않고 그냥 `sub`만 꺼내 쓰는 코드가 의외로 많다. 검증 안 한 ID Token은 공격자가 만든 위조 토큰일 수도 있다.

### 검증 단계

```
1. JWT 구조 검증 (header.payload.signature)
2. signature 검증
   - header.alg 확인 (none, HS256은 거부 - 최소 RS256/ES256)
   - header.kid로 JWKS에서 공개키 조회
   - 공개키로 signature 검증
3. 클레임 검증
   - iss == 발급자 URL (인가 서버)
   - aud에 우리 client_id 포함
   - exp > 현재 시간
   - iat, nbf 정상 범위
   - nonce == 우리가 보낸 값 (Authorization Code Flow)
   - azp == client_id (aud가 여러 개일 때)
4. at_hash 검증 (Hybrid Flow에서)
```

각 단계가 왜 있는지 보자.

### iss 검증

`iss`(issuer)는 토큰 발급자 URL이다. Discovery 문서의 `issuer` 값과 정확히 일치해야 한다. 한 글자라도 다르면 거부.

흔한 실수는 trailing slash다. Discovery에서 `https://auth.example.com`인데 토큰의 `iss`가 `https://auth.example.com/`이면 거부해야 한다.

### aud 검증

`aud`(audience)는 토큰의 대상 클라이언트다. 여기에 우리 `client_id`가 없으면 다른 클라이언트용으로 발급된 토큰이 우리 시스템에 흘러들어온 것이다. 거부.

`aud`가 배열일 수 있다. 그럴 때는 `azp`(authorized party)도 확인해야 한다. `azp`는 실제로 토큰을 받은 클라이언트를 가리킨다.

### exp 검증

`exp`는 만료 시각(Unix timestamp). 현재 시각보다 작으면 만료. 단, 시계 차이를 흡수하려고 보통 ±60초 정도 leeway를 둔다. 이걸 너무 길게(예: 5분) 두면 만료된 토큰을 더 오래 받게 된다.

### nonce 검증

Authorization Code Flow에서 `/authorize` 호출 시 `nonce` 파라미터를 보낸다. 인가 서버는 이걸 ID Token의 `nonce` 클레임에 그대로 넣어준다. 클라이언트는 받은 ID Token의 nonce가 자기가 보낸 값과 같은지 확인한다.

이건 재생 공격(replay attack) 방지용이다. PKCE가 인가 코드 탈취를 막는다면, nonce는 ID Token 자체의 재사용을 막는다. PKCE와 nonce는 둘 다 켜야 한다.

```javascript
// /authorize 호출 전
const nonce = crypto.getRandomValues(new Uint8Array(32))
  .reduce((s, b) => s + b.toString(16).padStart(2, '0'), '');
sessionStorage.setItem('oidc_nonce', nonce);

const authUrl = `${ISSUER}/authorize?` + new URLSearchParams({
  response_type: 'code',
  client_id: CLIENT_ID,
  redirect_uri: REDIRECT_URI,
  scope: 'openid profile email',
  state,
  nonce,
  code_challenge,
  code_challenge_method: 'S256',
});

// 토큰 받은 후
const idTokenPayload = decodeIdToken(tokens.id_token);
if (idTokenPayload.nonce !== sessionStorage.getItem('oidc_nonce')) {
  throw new Error('Nonce mismatch');
}
```

### alg 검증

`header.alg`가 `none`이면 무조건 거부. 옛날 JWT 라이브러리 중에 `alg: none`을 그대로 받아들이는 버그가 있었다. 지금도 직접 검증 코드를 짜면 실수하기 쉽다.

`HS256`(HMAC)도 인가 서버 공개키를 모르는 외부 클라이언트 입장에서는 거부해야 한다. HS256은 대칭키라 검증할 수 있다는 건 서명도 만들 수 있다는 뜻이다. 인가 서버와 클라이언트 모두 같은 secret을 알아야 검증이 되니, 이런 secret을 노출시키지 않으려면 RS256/ES256을 써야 한다.

라이브러리 설정에서 허용 알고리즘을 명시적으로 지정하라.

```typescript
// jose 예시 - 허용 알고리즘 화이트리스트
import { jwtVerify, createRemoteJWKSet, JWTPayload } from 'jose';

const JWKS = createRemoteJWKSet(new URL('https://auth.example.com/.well-known/jwks.json'));

async function verifyIdToken(
  idToken: string,
  expectedIssuer: string,
  expectedClientId: string,
): Promise<JWTPayload> {
  const { payload } = await jwtVerify(idToken, JWKS, {
    issuer: expectedIssuer,
    audience: expectedClientId,
    algorithms: ['RS256', 'ES256'], // none, HS256 등 거부
  });
  return payload;
}
```

## Discovery 엔드포인트

OIDC는 `.well-known/openid-configuration` 엔드포인트로 인가 서버의 모든 엔드포인트와 능력을 한 번에 알 수 있다. RFC 8414에 OAuth2 버전(`.well-known/oauth-authorization-server`)도 있다.

### Discovery 문서 예시

```bash
$ curl https://auth.example.com/.well-known/openid-configuration
```

```json
{
  "issuer": "https://auth.example.com",
  "authorization_endpoint": "https://auth.example.com/authorize",
  "token_endpoint": "https://auth.example.com/token",
  "userinfo_endpoint": "https://auth.example.com/userinfo",
  "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
  "registration_endpoint": "https://auth.example.com/register",
  "scopes_supported": ["openid", "profile", "email", "offline_access"],
  "response_types_supported": ["code", "id_token", "code id_token"],
  "grant_types_supported": [
    "authorization_code",
    "refresh_token",
    "client_credentials",
    "urn:ietf:params:oauth:grant-type:device_code"
  ],
  "subject_types_supported": ["public"],
  "id_token_signing_alg_values_supported": ["RS256", "ES256"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": [
    "client_secret_basic",
    "client_secret_post",
    "private_key_jwt"
  ]
}
```

### Discovery 활용

이걸 매번 파싱해서 쓰면 인가 서버 URL이 바뀌어도 클라이언트 코드를 안 고쳐도 된다. 단, Discovery 응답을 캐싱해야 한다. 매 요청마다 가져오면 인가 서버에 부하를 준다. 보통 1시간 정도 캐시한다.

캐싱과 키 회전이 충돌하는 경우가 있다. 예를 들어 Discovery는 1시간 캐시, JWKS도 1시간 캐시인데 인가 서버가 30분 만에 키를 회전시키면 그 사이 발급된 토큰을 클라이언트가 검증 못 한다. 이건 다음 절에서 다룬다.

### NestJS Passport OAuth2 Client 설정

NestJS에서는 passport-openidconnect 또는 openid-client를 사용해 Discovery URL을 통해 엔드포인트를 자동으로 가져올 수 있다.

```typescript
// .env
// OAUTH_CLIENT_ID=my-app
// OAUTH_CLIENT_SECRET=...
// OAUTH_ISSUER=https://auth.example.com/realms/myrealm
// OAUTH_REDIRECT_URI=https://app.example.com/login/oauth2/code/keycloak
```

`issuer-uri`만 주면 Spring이 부팅 시 `${issuer-uri}/.well-known/openid-configuration`을 한 번 호출해서 나머지를 채운다. 이때 인가 서버가 다운되어 있으면 부팅이 실패한다. 운영에서 이게 골치 아플 때가 있어서, lazy initialization을 쓰거나 Discovery를 직접 캐시해서 주입하는 방식도 쓴다.

## JWKS 키 회전

JWKS(JSON Web Key Set)는 인가 서버의 공개키 모음이다. 클라이언트는 ID Token을 받으면 `header.kid`로 어떤 키로 서명됐는지 식별하고, JWKS에서 해당 키를 찾아 검증한다.

### 키 회전이 필요한 이유

서명 키는 정기적으로 교체해야 한다. 키 유출 시 피해를 제한하고, 알고리즘 침해(예: 누군가 RSA 2048을 깬다)에 대비하려는 것이다. 보통 6개월~1년 주기로 회전한다.

회전 시 문제는 이미 발급된 토큰들이다. 어제 발급한 ID Token은 어제 키로 서명됐는데, 오늘 키를 바꾸면 어제 토큰을 검증 못 한다. 그래서 이중화가 필요하다.

### 회전 동작

```
T0:    [key_A (active)]
T0+1d: [key_B (active), key_A (rotating)]  ← 새 토큰은 key_B로 서명. 이전 토큰 검증용으로 key_A 유지
T0+2d: [key_B (active), key_A (rotating)]  ← key_A로 서명된 토큰 만료까지 대기
T0+3d: [key_B (active)]                    ← key_A 제거
```

JWKS는 활성 키와 회전 중인 키를 모두 포함한다.

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "key-2026-05",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "key-2025-11",
      "use": "sig",
      "alg": "RS256",
      "n": "...",
      "e": "AQAB"
    }
  ]
}
```

토큰의 `header.kid`가 `key-2025-11`이면 옛날 키로, `key-2026-05`이면 새 키로 검증한다.

<div class="ygd-jwks-key-rotation-timeline" id="ygd-jwks-key-rotation-timeline">
<style>
.ygd-jwks-key-rotation-timeline{--ygd-fg:#2B2622;--ygd-muted:#665F58;--ygd-card:#F6F4F1;--ygd-line:#A8A097;--ygd-active:#3D7387;--ygd-onactive:#FFFFFF;--ygd-ok:#1E7A46;--ygd-ok-bg:#E3F3E9;--ygd-bad:#B3261E;--ygd-bad-bg:#FBE6E3;--ygd-onbad:#FFFFFF;--ygd-chip-bg:#FFFFFF;--ygd-chip-active:#D9EAF0;--ygd-chip-rot:#FFEFC9;--ygd-warn:#8A5A00;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;color:var(--ygd-fg);font-size:14px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-jwks-key-rotation-timeline{--ygd-fg:#F0EDE9;--ygd-muted:#B5AFA7;--ygd-card:#2A2729;--ygd-line:#7A736C;--ygd-active:#7FB8CC;--ygd-onactive:#1F1C1E;--ygd-ok:#6FCF97;--ygd-ok-bg:#1F3A2A;--ygd-bad:#FF8A80;--ygd-bad-bg:#4A2523;--ygd-onbad:#1F1C1E;--ygd-chip-bg:#1F1C1E;--ygd-chip-active:#24424D;--ygd-chip-rot:#4A3A17;--ygd-warn:#F2C35B}
.ygd-jwks-key-rotation-timeline *{box-sizing:border-box}
.ygd-jwks-key-rotation-timeline .ygd-bar{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}
.ygd-jwks-key-rotation-timeline .ygd-btn{font:inherit;font-size:14px;line-height:1.3;min-height:40px;padding:6px 14px;border:1px solid var(--ygd-line);border-radius:6px;background:var(--ygd-card);color:var(--ygd-fg);cursor:pointer;transition:background .2s}
.ygd-jwks-key-rotation-timeline .ygd-btn:hover{border-color:var(--ygd-active)}
.ygd-jwks-key-rotation-timeline .ygd-btn:focus-visible{outline:3px solid var(--ygd-active);outline-offset:2px}
.ygd-jwks-key-rotation-timeline .ygd-btn:disabled{opacity:.5;cursor:not-allowed}
.ygd-jwks-key-rotation-timeline .ygd-btn.ygd-on{background:var(--ygd-active);border-color:var(--ygd-active);color:var(--ygd-onactive);font-weight:700}
.ygd-jwks-key-rotation-timeline .ygd-svg{display:block;width:100%;height:auto;max-width:100%;margin:8px 0}
.ygd-jwks-key-rotation-timeline .ygd-row{opacity:.5;transition:opacity .3s}
.ygd-jwks-key-rotation-timeline .ygd-row.ygd-past{opacity:.85}
.ygd-jwks-key-rotation-timeline .ygd-row.ygd-cur{opacity:1}
.ygd-jwks-key-rotation-timeline .ygd-card{fill:var(--ygd-card);stroke:var(--ygd-line);stroke-width:1}
.ygd-jwks-key-rotation-timeline .ygd-card.ygd-cur{stroke:var(--ygd-active);stroke-width:2.5}
.ygd-jwks-key-rotation-timeline .ygd-card.ygd-bad{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad)}
.ygd-jwks-key-rotation-timeline .ygd-card.ygd-bad.ygd-cur{stroke-width:2.5}
.ygd-jwks-key-rotation-timeline .ygd-tx{fill:var(--ygd-fg);font-size:12px;font-family:inherit}
.ygd-jwks-key-rotation-timeline .ygd-tb{fill:var(--ygd-fg);font-size:15px;font-weight:700;font-family:inherit}
.ygd-jwks-key-rotation-timeline .ygd-tm{fill:var(--ygd-muted);font-size:12px;font-family:inherit}
.ygd-jwks-key-rotation-timeline .ygd-tc{text-anchor:middle}
.ygd-jwks-key-rotation-timeline .ygd-bold{font-weight:700}
.ygd-jwks-key-rotation-timeline .ygd-c-active{fill:var(--ygd-chip-active);stroke:var(--ygd-active);stroke-width:1.5}
.ygd-jwks-key-rotation-timeline .ygd-c-rot{fill:var(--ygd-chip-rot);stroke:var(--ygd-warn);stroke-width:1.5}
.ygd-jwks-key-rotation-timeline .ygd-c-none{fill:none;stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:4 3}
.ygd-jwks-key-rotation-timeline .ygd-c-bad{fill:none;stroke:var(--ygd-bad);stroke-width:1.5;stroke-dasharray:4 3}
.ygd-jwks-key-rotation-timeline .ygd-pill{fill:var(--ygd-chip-bg);stroke:var(--ygd-line);stroke-width:1}
.ygd-jwks-key-rotation-timeline .ygd-v-ok{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok);stroke-width:1.5}
.ygd-jwks-key-rotation-timeline .ygd-v-bad{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad);stroke-width:1.5}
.ygd-jwks-key-rotation-timeline .ygd-v-exp{fill:var(--ygd-chip-bg);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-jwks-key-rotation-timeline .ygd-t-ok{fill:var(--ygd-ok)}
.ygd-jwks-key-rotation-timeline .ygd-t-bad{fill:var(--ygd-bad)}
.ygd-jwks-key-rotation-timeline .ygd-tag{fill:var(--ygd-bad)}
.ygd-jwks-key-rotation-timeline .ygd-tag-t{fill:var(--ygd-onbad);font-size:12px;font-weight:700;text-anchor:middle;font-family:inherit}
.ygd-jwks-key-rotation-timeline .ygd-ln{stroke:var(--ygd-line);stroke-width:3;stroke-linecap:round}
.ygd-jwks-key-rotation-timeline .ygd-ln-p{stroke:var(--ygd-active);stroke-width:3;stroke-linecap:round}
.ygd-jwks-key-rotation-timeline .ygd-dot{fill:var(--ygd-card);stroke:var(--ygd-line);stroke-width:2.5}
.ygd-jwks-key-rotation-timeline .ygd-dot.ygd-reach{fill:var(--ygd-active);stroke:var(--ygd-active)}
.ygd-jwks-key-rotation-timeline .ygd-dot.ygd-reach.ygd-bad{fill:var(--ygd-bad);stroke:var(--ygd-bad)}
.ygd-jwks-key-rotation-timeline .ygd-step{border:1px solid var(--ygd-line);border-left:4px solid var(--ygd-active);border-radius:6px;background:var(--ygd-card);padding:10px 14px;min-height:7.5em}
.ygd-jwks-key-rotation-timeline .ygd-step-t{display:block;font-size:15px;font-weight:700;color:var(--ygd-fg)}
.ygd-jwks-key-rotation-timeline .ygd-step-d{margin:4px 0 0;font-size:15px;line-height:1.6;color:var(--ygd-fg)}
.ygd-jwks-key-rotation-timeline .ygd-analogy{margin:10px 0 0;font-size:14px;line-height:1.6;color:var(--ygd-muted)}
@media (prefers-reduced-motion:reduce){.ygd-jwks-key-rotation-timeline .ygd-row,.ygd-jwks-key-rotation-timeline .ygd-btn{transition:none}}
</style>
<div class="ygd-bar" role="group" aria-label="시나리오 선택">
<button type="button" class="ygd-btn ygd-on" data-ygd-mode="normal" aria-pressed="true">정상 회전</button>
<button type="button" class="ygd-btn" data-ygd-mode="early" aria-pressed="false">key_A를 너무 일찍 제거</button>
</div>
<div class="ygd-bar" role="group" aria-label="재생 제어">
<button type="button" class="ygd-btn ygd-on" data-ygd-act="play">재생</button>
<button type="button" class="ygd-btn" data-ygd-act="prev">이전 단계</button>
<button type="button" class="ygd-btn" data-ygd-act="next">다음 단계</button>
</div>
<svg class="ygd-svg" viewBox="0 0 400 558" role="img" aria-label="JWKS 키 회전 타임라인. T0부터 T0+3일까지 JWKS에 든 key_A와 key_B의 상태, 새 토큰의 kid, key_A로 서명된 기존 토큰의 검증 결과를 보여준다." preserveAspectRatio="xMidYMid meet"><g class="ygd-layer"></g></svg>
<div class="ygd-step" aria-live="polite"><span class="ygd-step-t"></span><p class="ygd-step-d"></p></div>
<p class="ygd-analogy">비유: 도장 견본첩. 문서에 찍힌 도장이 진짜인지 확인하려면 견본첩(JWKS)에 그 도장 견본이 있어야 한다. 새 도장으로 바꾼 뒤에도 옛 도장이 찍힌 문서가 유효한 동안은 옛 견본을 빼면 안 된다. 실제로는 도장이 아니라 개인키로 서명하고 공개키로 검증한다.</p>
<script>
(function(){
var root=document.getElementById('ygd-jwks-key-rotation-timeline');
if(!root){return;}
var NS='http://www.w3.org/2000/svg';
var svg=root.querySelector('.ygd-svg');
var layer=root.querySelector('.ygd-layer');
var stepT=root.querySelector('.ygd-step-t');
var stepD=root.querySelector('.ygd-step-d');
var playBtn=root.querySelector('[data-ygd-act="play"]');
var prevBtn=root.querySelector('[data-ygd-act="prev"]');
var nextBtn=root.querySelector('[data-ygd-act="next"]');
var modeBtns=root.querySelectorAll('[data-ygd-mode]');
var TIMES=['T0','T0+1d','T0+2d','T0+3d'];
var DATA={
normal:[
{ev:'key_A 단독 운용',a:'active',b:'none',kid:'key_A',v:'ok',vt:'✓ 검증 성공'},
{ev:'key_B 활성 · key_A rotating',a:'rot',b:'active',kid:'key_B',v:'ok',vt:'✓ 검증 성공'},
{ev:'key_A 토큰 만료까지 대기',a:'rot',b:'active',kid:'key_B',v:'ok',vt:'✓ 검증 성공'},
{ev:'key_A 제거',a:'gone',b:'active',kid:'key_B',v:'exp',vt:'키 없음 · 이미 만료'}
],
early:[
{ev:'key_A 단독 운용',a:'active',b:'none',kid:'key_A',v:'ok',vt:'✓ 검증 성공'},
{ev:'key_A 너무 일찍 제거',a:'goneBad',b:'active',kid:'key_B',v:'bad',vt:'✗ 검증 실패',tag:true},
{ev:'key_A 없음 · 실패 지속',a:'goneBad',b:'active',kid:'key_B',v:'bad',vt:'✗ 검증 실패'},
{ev:'key_A 없음',a:'goneBad',b:'active',kid:'key_B',v:'bad',vt:'✗ 만료 전 토큰은 실패'}
]};
var DESC={
normal:[
'JWKS에는 key_A 하나뿐이다. 새 토큰도 key_A로 서명하고, 이미 발급된 토큰도 key_A로 검증한다.',
'key_B가 활성 키가 되어 새 토큰은 key_B로 서명된다. key_A는 rotating 상태로 JWKS에 남아 있어서, key_A로 서명된 기존 토큰이 계속 검증된다.',
'JWKS 구성은 그대로다. key_A로 서명된 토큰이 만료될 때까지 기다리는 구간이다.',
'key_A를 JWKS에서 제거한다. key_A로 서명된 토큰이 만료된 뒤에 지우기 때문에 검증이 깨지는 토큰이 없다.'
],
early:[
'JWKS에는 key_A 하나뿐이다. 여기까지는 정상 회전과 같다.',
'key_B로 바꾸면서 key_A를 곧바로 JWKS에서 지웠다. kid가 key_A인 기존 토큰은 아직 만료 전이어도 JWKS에서 키를 찾지 못해 검증에 실패한다.',
'key_A는 여전히 없다. 만료까지 기다렸어야 할 key_A 토큰이 계속 검증을 통과하지 못한다.',
'key_A 제거 시점이 T0+3d였다면 문제없었을 텐데, 이 시나리오에서는 그 전에 이미 깨졌다. 두 시나리오의 차이는 key_A를 지운 시점뿐이다.'
]};
var mode='normal',step=0,timer=null;
function el(n,a,t){var e=document.createElementNS(NS,n);for(var k in a){e.setAttribute(k,a[k]);}if(t!==undefined&&t!==null){e.textContent=t;}return e;}
function chip(g,x,y,key,state){
var cls='ygd-c-none',txt=key+' 아직 없음',tcls='ygd-tm ygd-tc';
if(state==='active'){cls='ygd-c-active';txt=key+' (active)';tcls='ygd-tx ygd-tc ygd-bold';}
else if(state==='rot'){cls='ygd-c-rot';txt=key+' (rotating)';tcls='ygd-tx ygd-tc ygd-bold';}
else if(state==='gone'){cls='ygd-c-none';txt=key+' 제거됨';}
else if(state==='goneBad'){cls='ygd-c-bad';txt=key+' 제거됨';tcls='ygd-tx ygd-tc ygd-bold ygd-t-bad';}
g.appendChild(el('rect',{x:x,y:y,width:128,height:26,rx:6,'class':cls}));
g.appendChild(el('text',{x:x+64,y:y+17,'class':tcls},txt));
}
function render(){
var d=DATA[mode];
while(layer.firstChild){layer.removeChild(layer.firstChild);}
var PITCH=138,H=128,X0=48,W=344;
function dy(i){return 8+i*PITCH+19;}
layer.appendChild(el('line',{x1:24,y1:dy(0),x2:24,y2:dy(3),'class':'ygd-ln'}));
if(step>0){layer.appendChild(el('line',{x1:24,y1:dy(0),x2:24,y2:dy(step),'class':'ygd-ln-p'}));}
for(var i=0;i!==4;i++){
var r=d[i],y0=8+i*PITCH,x0=X0;
var g=el('g',{'class':'ygd-row'+(i===step?' ygd-cur':(i!==step&&i<step?' ygd-past':''))});
var bad=(r.v==='bad');
g.appendChild(el('rect',{x:x0,y:y0,width:W,height:H,rx:8,'class':'ygd-card'+(bad?' ygd-bad':'')+(i===step?' ygd-cur':'')}));
g.appendChild(el('text',{x:x0+12,y:y0+24,'class':'ygd-tb'},TIMES[i]));
g.appendChild(el('text',{x:x0+76,y:y0+24,'class':'ygd-tx'},r.ev));
if(r.tag){
g.appendChild(el('rect',{x:x0+256,y:y0+8,width:80,height:22,rx:5,'class':'ygd-tag'}));
g.appendChild(el('text',{x:x0+296,y:y0+23,'class':'ygd-tag-t'},'깨지는 지점'));
}
g.appendChild(el('text',{x:x0+12,y:y0+52,'class':'ygd-tm'},'JWKS'));
chip(g,x0+56,y0+34,'key_A',r.a);
chip(g,x0+192,y0+34,'key_B',r.b);
g.appendChild(el('text',{x:x0+12,y:y0+85,'class':'ygd-tm'},'새 토큰 kid'));
g.appendChild(el('rect',{x:x0+138,y:y0+68,width:72,height:24,rx:6,'class':'ygd-pill'}));
g.appendChild(el('text',{x:x0+174,y:y0+85,'class':'ygd-tx ygd-tc ygd-bold'},r.kid));
g.appendChild(el('text',{x:x0+12,y:y0+115,'class':'ygd-tm'},'key_A 서명 토큰'));
g.appendChild(el('rect',{x:x0+138,y:y0+98,width:198,height:22,rx:6,'class':'ygd-v-'+r.v}));
g.appendChild(el('text',{x:x0+237,y:y0+113,'class':'ygd-tx ygd-tc ygd-bold'+(r.v==='ok'?' ygd-t-ok':(r.v==='bad'?' ygd-t-bad':''))},r.vt));
layer.appendChild(g);
}
for(var j=0;j!==4;j++){
var isBadDot=(d[j].v==='bad');
layer.appendChild(el('circle',{cx:24,cy:dy(j),r:7,'class':'ygd-dot'+(j<=step?' ygd-reach':'')+(isBadDot?' ygd-bad':'')}));
}
var cur=d[step];
stepT.textContent=TIMES[step]+' · '+cur.ev;
stepD.textContent=DESC[mode][step];
svg.setAttribute('aria-label','JWKS 키 회전 타임라인('+(mode==='normal'?'정상 회전':'key_A를 너무 일찍 제거')+'). 현재 '+TIMES[step]+': '+cur.ev+'. 새 토큰 kid는 '+cur.kid+', key_A 서명 토큰 검증 결과는 '+cur.vt.replace('✓ ','').replace('✗ ','')+'.');
playBtn.textContent=timer?'일시정지':(step===3?'다시 재생':'재생');
prevBtn.disabled=(step===0);
nextBtn.disabled=(step===3);
for(var m=0;m!==modeBtns.length;m++){
var on=(modeBtns[m].getAttribute('data-ygd-mode')===mode);
modeBtns[m].setAttribute('aria-pressed',on?'true':'false');
modeBtns[m].className='ygd-btn'+(on?' ygd-on':'');
}
}
function halt(){if(timer){clearInterval(timer);timer=null;}}
playBtn.addEventListener('click',function(){
if(timer){halt();render();return;}
if(step===3){step=0;}
timer=setInterval(function(){
step++;
if(step>=3){halt();}
render();
},2400);
render();
});
prevBtn.addEventListener('click',function(){halt();if(step>0){step--;}render();});
nextBtn.addEventListener('click',function(){halt();if(step!==3){step++;}render();});
for(var k=0;k!==modeBtns.length;k++){
modeBtns[k].addEventListener('click',function(){mode=this.getAttribute('data-ygd-mode');render();});
}
render();
})();
</script>
</div>

### 클라이언트가 해야 할 일

JWKS를 캐시하되, 모르는 `kid`가 들어오면 즉시 갱신해야 한다. 단순히 1시간 캐시만 하면 회전 직후 새 `kid`로 서명된 토큰을 검증 못 한다.

```typescript
import { createRemoteJWKSet, JWTVerifyGetKey } from 'jose';

const MIN_REFETCH_INTERVAL_MS = 5 * 60 * 1000;

class JwksCache {
  private jwks: JWTVerifyGetKey;
  private lastFetched = 0;

  constructor(private readonly jwksUri: string) {
    this.jwks = createRemoteJWKSet(new URL(jwksUri), {
      cacheMaxAge: MIN_REFETCH_INTERVAL_MS,
    });
  }

  // jose의 createRemoteJWKSet이 kid 기반 캐시 + 자동 갱신을 처리해 준다
  // 모르는 kid가 들어오면 자동으로 JWKS를 다시 가져온다
  // MIN_REFETCH_INTERVAL 이내에 재요청이 오면 캐시된 결과를 반환
  getJwks(): JWTVerifyGetKey {
    return this.jwks;
  }
}
```

`MIN_REFETCH_INTERVAL_MS`가 중요하다. 공격자가 가짜 `kid`를 가진 토큰을 대량으로 보내면 클라이언트가 매번 JWKS를 갱신하려 하고, 인가 서버에 DoS가 된다. 이걸 막으려고 갱신을 제한한다.

Spring Security의 `NimbusJwtDecoder`는 이미 이런 로직이 들어있어서 직접 짤 일은 거의 없다. 단, 자체 검증 코드를 짜면 빠뜨리기 쉬운 부분이다.

## Keycloak으로 OAuth2 서버 직접 띄우기

이론을 봤으니 실제로 띄워본다. Keycloak은 가장 흔한 오픈소스 인가 서버다. Spring Authorization Server도 옵션이지만 Keycloak이 관리 UI가 있어서 학습용으로 더 편하다.

### Docker로 띄우기

```bash
docker run -d \
  --name keycloak \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:25.0.0 \
  start-dev
```

`start-dev`는 개발용 모드다. HTTPS 없이 동작하고 메모리 DB를 쓴다. 운영에는 절대 쓰지 마라.

`http://localhost:8080`에 접속해 admin/admin으로 로그인. Realm을 만들고(예: `myrealm`), Client를 등록한다(예: `my-spring-app`).

### Realm과 Client 설정

Keycloak 용어:

- Realm: 격리된 인증 영역. 회사별, 환경별로 분리한다.
- Client: 인가 서버 입장에서 본 애플리케이션. SPA, 백엔드, 모바일 앱 각각이 별도 Client.
- User: Realm 안에 등록된 사용자.
- Role: 권한. Realm 단위, Client 단위로 정의 가능.

Client 만들 때 중요한 설정.

```
Client ID: my-spring-app
Client authentication: ON  (Confidential Client)
Authentication flow:
  - Standard flow: ON  (Authorization Code)
  - Direct access grants: OFF  (ROPC 차단)
  - Implicit flow: OFF
  - Service accounts roles: ON (Client Credentials 쓸 거면)
Valid redirect URIs: http://localhost:8081/login/oauth2/code/keycloak
Web origins: http://localhost:8081
```

Direct access grants를 OFF 하는 게 중요하다. ON으로 두면 ROPC가 활성화된다. 기본값이 ON인 Keycloak 버전이 있어서 매번 확인해야 한다.

### Discovery URL 확인

```bash
$ curl http://localhost:8080/realms/myrealm/.well-known/openid-configuration | jq
```

`issuer`, `authorization_endpoint`, `token_endpoint`, `jwks_uri`가 다 나온다. 이게 클라이언트 설정의 기준이다.

### NestJS 클라이언트

`package.json` 의존성:

```json
{
  "dependencies": {
    "@nestjs/passport": "^10.0.0",
    "passport": "^0.7.0",
    "openid-client": "^5.0.0",
    "@nestjs/jwt": "^10.0.0"
  }
}
```

`auth.module.ts`:

```typescript
import { Module } from '@nestjs/common';
import { PassportModule } from '@nestjs/passport';
import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { OidcStrategy } from './oidc.strategy';
import { JwtAuthGuard } from './jwt-auth.guard';

@Module({
  imports: [
    PassportModule,
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        // Keycloak JWKS를 통해 공개키로 검증
        secret: configService.get<string>('JWT_SECRET'),
      }),
      inject: [ConfigService],
    }),
  ],
  providers: [OidcStrategy, JwtAuthGuard],
  exports: [JwtAuthGuard],
})
export class AuthModule {}
```

`jwt-auth.guard.ts` (리소스 서버 역할):

```typescript
import { Injectable } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {}

// 역할 기반 Guard
import { CanActivate, ExecutionContext, Injectable as Inj } from '@nestjs/common';
import { Reflector } from '@nestjs/core';

@Inj()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.get<string[]>('roles', context.getHandler());
    if (!requiredRoles) return true;

    const { user } = context.switchToHttp().getRequest<{ user: { roles: string[] } }>();
    return requiredRoles.some((role) => user.roles?.includes(role));
  }
}
```

`me.controller.ts`:

```typescript
import { Controller, Get, UseGuards, Req } from '@nestjs/common';
import { JwtAuthGuard } from './jwt-auth.guard';
import { RolesGuard } from './roles.guard';
import { Roles } from './roles.decorator';
import { Request } from 'express';

interface OidcUser {
  sub: string;
  email: string;
  name: string;
  roles: string[];
}

@Controller()
export class MeController {
  @Get('/me')
  @UseGuards(JwtAuthGuard)
  me(@Req() req: Request & { user: OidcUser }): Record<string, unknown> {
    const user = req.user;
    return {
      sub: user.sub,
      email: user.email,
      name: user.name,
      roles: user.roles,
    };
  }

  @Get('/api/protected')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles('user')
  protectedEndpoint(): string {
    return 'ok';
  }
}
```

부팅하고 `http://localhost:8081/me`에 접속하면 Keycloak 로그인 화면으로 리다이렉트되고, 로그인 후 사용자 정보가 나온다. 네트워크 탭에서 `/realms/myrealm/protocol/openid-connect/auth`로 가는 호출에 `code_challenge`가 붙어있는지 확인하라(Spring Security 6 이상은 PKCE를 자동 활성화).

### Client Credentials 테스트

Keycloak에서 별도 Client를 만들고 Service accounts roles를 ON 한 뒤:

```bash
$ curl -X POST http://localhost:8080/realms/myrealm/protocol/openid-connect/token \
  -d "grant_type=client_credentials" \
  -d "client_id=batch-service" \
  -d "client_secret=${BATCH_SECRET}"
```

응답으로 받은 `access_token`을 디코딩하면(`jwt.io`에서) `aud`, `azp`, `realm_access.roles`가 보인다. 이걸 다른 서비스에서 `Authorization: Bearer ...`로 호출하면 Spring Security의 Resource Server 부분이 자동으로 검증한다.

## Node.js 자체 인가 서버를 직접 쓰는 경우

Keycloak이 무겁다거나, Node.js 안에서 인가 서버를 돌리고 싶을 때 `node-oidc-provider`를 쓴다. 2023년 이후 정식 릴리즈됐고, OAuth2와 OIDC를 모두 지원한다.

```typescript
import Provider from 'oidc-provider';
import { generateKeyPair, exportJWK } from 'jose';

async function createOidcProvider(): Promise<Provider> {
  // RSA 키 쌍 생성
  const { privateKey } = await generateKeyPair('RS256');
  const jwk = await exportJWK(privateKey);
  jwk.kid = crypto.randomUUID();
  jwk.use = 'sig';

  return new Provider('https://auth.example.com', {
    clients: [
      {
        client_id: 'my-spa',
        client_secret: undefined,       // Public Client (비밀 없음)
        token_endpoint_auth_method: 'none',
        grant_types: ['authorization_code', 'refresh_token'],
        redirect_uris: ['http://localhost:3000/callback'],
        response_types: ['code'],
        scope: 'openid profile',
        require_pkce: true,             // PKCE 강제
      },
    ],
    jwks: { keys: [jwk] },
    pkce: { required: () => true },     // 모든 클라이언트에 PKCE 강제
    ttl: {
      AccessToken: 15 * 60,             // 15분
      RefreshToken: 7 * 24 * 60 * 60,  // 7일
    },
    rotateRefreshToken: true,           // Refresh Token 회전
  });
}
// 운영 환경에서는 jwks를 메모리 키쌍이 아니라 KMS/HSM에서 관리
```

`requireProofKey(true)`가 PKCE 강제, `reuseRefreshTokens(false)`가 회전이다. 이 두 가지를 빠뜨리면 인가 서버를 직접 만들었음에도 보안이 약해진다.

운영 환경에서는 `InMemoryRegisteredClientRepository`를 `JdbcRegisteredClientRepository`로 바꾸고, JWK도 메모리 키쌍이 아니라 KMS나 HSM에서 관리되는 키를 써야 한다.

## 운영에서 자주 마주치는 문제

### Refresh Token Rotation이 깨진다

Refresh Token 회전을 켰는데 모바일 앱에서 가끔 토큰 갱신이 실패한다는 리포트가 들어온다. 원인은 보통 동시 요청이다. 두 개의 API 호출이 동시에 만료된 Access Token을 발견하면 둘 다 Refresh Token으로 갱신을 시도한다. 첫 번째 요청이 새 토큰을 받으면 두 번째 요청은 이미 회전된 옛 Refresh Token으로 갱신을 시도하다 거부된다.

해결은 클라이언트 쪽에서 갱신을 직렬화하는 것이다. Refresh 진행 중이면 다른 요청은 그 결과를 기다리게 한다.

```typescript
class TokenManager {
  private currentAccessToken: string | null = null;
  private expiresAt = 0;
  private refreshing: Promise<string> | null = null;

  async getValidAccessToken(): Promise<string> {
    if (this.currentAccessToken && !this.isExpired()) {
      return this.currentAccessToken;
    }

    // 진행 중인 갱신이 있으면 그 결과를 기다린다 (직렬화)
    if (this.refreshing) {
      return this.refreshing;
    }

    this.refreshing = this.doRefresh().then((token) => {
      this.currentAccessToken = token;
      this.refreshing = null;
      return token;
    }).catch((err) => {
      this.refreshing = null;
      throw err;
    });

    return this.refreshing;
  }

  private isExpired(): boolean {
    return Date.now() >= this.expiresAt;
  }

  private async doRefresh(): Promise<string> {
    // Refresh Token으로 새 Access Token 발급
    throw new Error('구현 필요');
  }
}
```

<div class="ygd-refresh-rotation-race" id="ygd-refresh-rotation-race" style="max-width:760px;margin-left:auto;margin-right:auto">
<style>
.ygd-refresh-rotation-race{--ygd-bg:#FDFBFA;--ygd-panel:#F3EFEC;--ygd-fg:#2B2826;--ygd-muted:#736E68;--ygd-line:#B9B1AA;--ygd-acc:#356577;--ygd-acc-bg:#E4EEF2;--ygd-ok:#1A6B3C;--ygd-ok-bg:#E3F3E9;--ygd-bad:#B3261E;--ygd-bad-bg:#FBE6E4;--ygd-on-acc:#FFFFFF;--ygd-node-bg:#EFEAE6;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1.5em;margin-bottom:1.5em;padding:12px;box-sizing:border-box;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:15px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-refresh-rotation-race{--ygd-bg:#1F1C1E;--ygd-panel:#2A2629;--ygd-fg:#F0EDE9;--ygd-muted:#B0AAA2;--ygd-line:#5A5458;--ygd-acc:#7FC0D8;--ygd-acc-bg:#20343B;--ygd-ok:#6FD39A;--ygd-ok-bg:#1F3A2B;--ygd-bad:#FF9A92;--ygd-bad-bg:#4A2523;--ygd-on-acc:#10222A;--ygd-node-bg:#332E31}
.ygd-refresh-rotation-race .ygd-bar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.ygd-refresh-rotation-race .ygd-grp{display:flex;flex-wrap:wrap;gap:8px;min-width:0}
.ygd-refresh-rotation-race .ygd-btn{box-sizing:border-box;min-height:44px;padding:8px 14px;border:1px solid var(--ygd-acc);border-radius:6px;background:var(--ygd-bg);color:var(--ygd-acc);font:inherit;font-size:15px;font-weight:600;line-height:1.2;cursor:pointer}
.ygd-refresh-rotation-race .ygd-btn:hover{background:var(--ygd-acc-bg)}
.ygd-refresh-rotation-race .ygd-btn:focus-visible{outline:3px solid var(--ygd-acc);outline-offset:2px}
.ygd-refresh-rotation-race .ygd-btn[aria-pressed="true"],.ygd-refresh-rotation-race .ygd-btn.ygd-primary{background:var(--ygd-acc);color:var(--ygd-on-acc)}
.ygd-refresh-rotation-race .ygd-btn[disabled]{opacity:.5;cursor:default}
.ygd-refresh-rotation-race .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-refresh-rotation-race .ygd-svg text{font-family:inherit;font-size:13px;fill:var(--ygd-fg);text-anchor:middle}
.ygd-refresh-rotation-race .ygd-node{fill:var(--ygd-node-bg);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-refresh-rotation-race .ygd-node-t{font-weight:700}
.ygd-refresh-rotation-race .ygd-life{stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:4 4}
.ygd-refresh-rotation-race .ygd-el{opacity:.45;transition:opacity .35s}
.ygd-refresh-rotation-race .ygd-el.ygd-on{opacity:1}
.ygd-refresh-rotation-race .ygd-flow{fill:none;stroke:var(--ygd-acc);stroke-width:2}
.ygd-refresh-rotation-race .ygd-cur .ygd-flow{stroke-width:3.5}
.ygd-refresh-rotation-race .ygd-cur rect{stroke-width:3}
.ygd-refresh-rotation-race .ygd-f-ok{stroke:var(--ygd-ok)}
.ygd-refresh-rotation-race .ygd-f-bad{stroke:var(--ygd-bad)}
.ygd-refresh-rotation-race .ygd-f-dash{stroke-dasharray:6 4}
.ygd-refresh-rotation-race .ygd-ah-a{fill:var(--ygd-acc)}
.ygd-refresh-rotation-race .ygd-ah-ok{fill:var(--ygd-ok)}
.ygd-refresh-rotation-race .ygd-ah-bad{fill:var(--ygd-bad)}
.ygd-refresh-rotation-race .ygd-chip{fill:var(--ygd-node-bg);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-refresh-rotation-race .ygd-t-acc .ygd-chip{fill:var(--ygd-acc-bg);stroke:var(--ygd-acc)}
.ygd-refresh-rotation-race .ygd-t-acc text{fill:var(--ygd-acc);font-weight:700}
.ygd-refresh-rotation-race .ygd-t-ok .ygd-chip{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok)}
.ygd-refresh-rotation-race .ygd-t-ok text{fill:var(--ygd-ok);font-weight:700}
.ygd-refresh-rotation-race .ygd-t-bad .ygd-chip{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad)}
.ygd-refresh-rotation-race .ygd-t-bad text{fill:var(--ygd-bad);font-weight:700}
.ygd-refresh-rotation-race .ygd-lbl-ok{fill:var(--ygd-ok)}
.ygd-refresh-rotation-race .ygd-lbl-bad{fill:var(--ygd-bad)}
.ygd-refresh-rotation-race .ygd-pkt{fill:var(--ygd-acc);stroke:var(--ygd-bg);stroke-width:1.5}
.ygd-refresh-rotation-race[data-mode="none"] .ygd-m-serial{display:none}
.ygd-refresh-rotation-race[data-mode="serial"] .ygd-m-none{display:none}
.ygd-refresh-rotation-race .ygd-panel{box-sizing:border-box;margin-top:10px;padding:10px 12px;border-left:4px solid var(--ygd-acc);border-radius:4px;background:var(--ygd-panel);min-height:9em}
.ygd-refresh-rotation-race .ygd-step-n{margin:0 0 2px 0;font-size:14px;color:var(--ygd-muted)}
.ygd-refresh-rotation-race .ygd-step-t{margin:0 0 4px 0;font-size:16px;font-weight:700;color:var(--ygd-fg)}
.ygd-refresh-rotation-race .ygd-step-d{margin:0;font-size:15px;color:var(--ygd-fg)}
.ygd-refresh-rotation-race .ygd-note{margin:10px 0 0 0;font-size:14px;color:var(--ygd-muted)}
@media (prefers-reduced-motion: reduce){.ygd-refresh-rotation-race .ygd-el{transition:none}}
</style>
<div class="ygd-bar">
<div class="ygd-grp" role="group" aria-label="시나리오 선택">
<button type="button" class="ygd-btn" data-mode-btn="none" aria-pressed="true">직렬화 없음</button>
<button type="button" class="ygd-btn" data-mode-btn="serial" aria-pressed="false">직렬화 적용</button>
</div>
<div class="ygd-grp" role="group" aria-label="재생 제어">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="next">다음 단계</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
</div>
<svg class="ygd-svg" viewBox="0 0 380 356" role="img" aria-label="Refresh Token 회전 경쟁 상태 시퀀스 다이어그램. 요청 A, 요청 B, 인가 서버 세 참여자가 같은 Refresh Token RT1로 갱신을 시도하는 흐름을 직렬화 없음과 직렬화 적용 두 경우로 보여준다.">
<defs>
<marker id="ygd-refresh-rotation-race-ah-a" viewBox="0 0 10 10" refX="8" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path class="ygd-ah-a" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="ygd-refresh-rotation-race-ah-ok" viewBox="0 0 10 10" refX="8" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path class="ygd-ah-ok" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="ygd-refresh-rotation-race-ah-bad" viewBox="0 0 10 10" refX="8" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path class="ygd-ah-bad" d="M0,0 L10,5 L0,10 z"/></marker>
</defs>
<line class="ygd-life" x1="56" y1="36" x2="56" y2="354"/>
<line class="ygd-life" x1="190" y1="36" x2="190" y2="354"/>
<line class="ygd-life" x1="324" y1="36" x2="324" y2="354"/>
<rect class="ygd-node" x="6" y="6" width="100" height="30" rx="6"/>
<text class="ygd-node-t" x="56" y="26">요청 A</text>
<rect class="ygd-node" x="140" y="6" width="100" height="30" rx="6"/>
<text class="ygd-node-t" x="190" y="26">요청 B</text>
<rect class="ygd-node" x="274" y="6" width="100" height="30" rx="6"/>
<text class="ygd-node-t" x="324" y="26">인가 서버</text>
<g class="ygd-el" data-step="0">
<rect class="ygd-chip" x="6" y="52" width="100" height="26" rx="6"/>
<text x="56" y="70">AT 만료 발견</text>
<rect class="ygd-chip" x="140" y="52" width="100" height="26" rx="6"/>
<text x="190" y="70">AT 만료 발견</text>
</g>
<g class="ygd-el" data-step="1">
<path class="ygd-flow" d="M62,116 H318" marker-end="url(#ygd-refresh-rotation-race-ah-a)"/>
<text x="123" y="108">RT1로 갱신 요청</text>
</g>
<g class="ygd-el ygd-m-none" data-step="2" data-mode="none">
<path class="ygd-flow" d="M196,154 H318" marker-end="url(#ygd-refresh-rotation-race-ah-a)"/>
<text x="257" y="146">RT1로 갱신 요청</text>
</g>
<g class="ygd-el ygd-m-serial" data-step="2" data-mode="serial">
<path class="ygd-flow ygd-f-dash" d="M184,154 H62" marker-end="url(#ygd-refresh-rotation-race-ah-a)"/>
<text x="123" y="146">같은 Promise 대기</text>
</g>
<g class="ygd-el ygd-t-acc" data-step="3">
<rect class="ygd-chip" x="230" y="176" width="144" height="26" rx="6"/>
<text x="302" y="194">RT1 폐기 · RT2 발급</text>
</g>
<g class="ygd-el" data-step="4">
<path class="ygd-flow ygd-f-ok" d="M318,240 H62" marker-end="url(#ygd-refresh-rotation-race-ah-ok)"/>
<text class="ygd-lbl-ok" x="123" y="232">성공 · RT2 수신</text>
</g>
<g class="ygd-el ygd-t-ok" data-step="4">
<rect class="ygd-chip" x="6" y="252" width="100" height="26" rx="6"/>
<text x="56" y="270">갱신 성공</text>
</g>
<g class="ygd-el ygd-m-none" data-step="5" data-mode="none">
<path class="ygd-flow ygd-f-bad ygd-f-dash" d="M318,308 H196" marker-end="url(#ygd-refresh-rotation-race-ah-bad)"/>
<text class="ygd-lbl-bad" x="257" y="300">거부 · 옛 RT1</text>
</g>
<g class="ygd-el ygd-m-none ygd-t-bad" data-step="5" data-mode="none">
<rect class="ygd-chip" x="140" y="320" width="100" height="26" rx="6"/>
<text x="190" y="338">갱신 실패</text>
</g>
<g class="ygd-el ygd-m-serial" data-step="5" data-mode="serial">
<path class="ygd-flow ygd-f-ok ygd-f-dash" d="M62,308 H184" marker-end="url(#ygd-refresh-rotation-race-ah-ok)"/>
<text class="ygd-lbl-ok" x="123" y="300">Promise 결과 공유</text>
</g>
<g class="ygd-el ygd-m-serial ygd-t-ok" data-step="5" data-mode="serial">
<rect class="ygd-chip" x="140" y="320" width="100" height="26" rx="6"/>
<text x="190" y="338">갱신 성공</text>
</g>
<circle class="ygd-pkt" id="ygd-refresh-rotation-race-pkt" r="5" cx="0" cy="0" style="display:none"/>
</svg>
<div class="ygd-panel" aria-live="polite">
<p class="ygd-step-n" data-role="n"></p>
<p class="ygd-step-t" data-role="t"></p>
<p class="ygd-step-d" data-role="d"></p>
</div>
<p class="ygd-note">비유: 한 번 쓰면 새것으로 바뀌는 일회용 교환권 한 장을 두 사람이 나눠 들고 창구에 가는 상황과 비슷하다. 각자 따로 가면 먼저 낸 쪽만 새 교환권을 받고, 한 사람만 창구에 다녀와 결과를 같이 쓰면 문제가 없다.</p>
<script>
(function () {
  var root = document.getElementById('ygd-refresh-rotation-race');
  if (!root) { return; }
  var els = root.querySelectorAll('.ygd-el');
  var pkt = document.getElementById('ygd-refresh-rotation-race-pkt');
  var elN = root.querySelector('[data-role="n"]');
  var elT = root.querySelector('[data-role="t"]');
  var elD = root.querySelector('[data-role="d"]');
  var btnPlay = root.querySelector('[data-act="play"]');
  var btnNext = root.querySelector('[data-act="next"]');
  var btnReset = root.querySelector('[data-act="reset"]');
  var tabs = root.querySelectorAll('[data-mode-btn]');
  var LAST = 5;
  var INTERVAL = 2600;
  var mode = 'none';
  var step = -1;
  var timer = null;
  var raf = 0;
  var IDLE = {
    none: ['준비', '직렬화 없음', '만료된 Access Token을 동시에 발견한 두 요청이 각자 갱신을 시도한다. 재생을 누르면 같은 RT1이 두 번 쓰일 때 무슨 일이 생기는지 순서대로 보여 준다.'],
    serial: ['준비', '직렬화 적용', '갱신은 한 요청만 시작하고 나머지는 진행 중인 같은 Promise를 기다린다. 재생을 누르면 이 흐름이 순서대로 진행된다.']
  };
  var COMMON0 = ['두 요청이 만료를 동시에 발견한다', '두 API 호출이 거의 동시에 Access Token이 만료된 것을 발견한다. 둘 다 같은 Refresh Token, 즉 RT1을 들고 있다.'];
  var STEPS = {
    none: [
      COMMON0,
      ['요청 A가 RT1로 갱신을 요청한다', '요청 A가 RT1을 인가 서버로 보낸다. 이 클라이언트에는 갱신을 직렬화하는 장치가 없다.'],
      ['요청 B도 같은 RT1로 갱신을 요청한다', '요청 B는 갱신이 이미 진행 중인지 모른 채 똑같이 RT1을 보낸다. 같은 Refresh Token이 두 번 사용되는 상황이다.'],
      ['서버가 먼저 도착한 A를 처리한다', '회전이 켜져 있으므로 서버는 RT1을 폐기하고 RT2를 발급한다.'],
      ['요청 A는 성공한다', '요청 A는 응답으로 새 Access Token과 RT2를 받아 갱신에 성공한다.'],
      ['요청 B는 거부된다', '요청 B가 보낸 RT1은 이미 회전된 옛 Refresh Token이라 서버가 거부한다. 동시에 갱신을 시도한 두 요청 중 하나가 실패하는 것이 모바일 앱에서 가끔 보이는 갱신 실패의 흔한 원인이다.']
    ],
    serial: [
      COMMON0,
      ['요청 A가 갱신을 시작한다', '진행 중인 갱신이 없으므로 요청 A가 갱신을 시작한다. 그 Promise를 refreshing에 저장하고 RT1을 인가 서버로 보낸다.'],
      ['요청 B는 같은 Promise를 기다린다', '요청 B는 진행 중인 갱신이 있는 것을 보고 새로 시작하지 않는다. refreshing의 Promise를 그대로 돌려받아 기다리며, 서버로는 아무것도 보내지 않는다.'],
      ['서버가 RT1을 회전한다', '서버에는 갱신 요청이 한 번만 도착한다. RT1은 폐기되고 RT2가 발급된다.'],
      ['요청 A는 성공한다', '요청 A는 응답으로 새 Access Token과 RT2를 받아 갱신에 성공한다.'],
      ['요청 B도 같은 결과로 성공한다', 'Promise가 완료되면 기다리던 요청 B도 같은 결과를 받는다. 갱신은 한 번만 일어났고 두 요청이 모두 성공한다.']
    ]
  };
  function reduced() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function visible(g) {
    var m = g.getAttribute('data-mode');
    return !m || m === mode;
  }
  function hidePacket() {
    if (raf) { cancelAnimationFrame(raf); raf = 0; }
    pkt.style.display = 'none';
  }
  function runPacket() {
    hidePacket();
    if (reduced() || step < 1) { return; }
    var paths = root.querySelectorAll('path.ygd-flow');
    var p = null;
    var i, g;
    for (i = 0; i !== paths.length; i++) {
      g = paths[i].parentNode;
      if (parseInt(g.getAttribute('data-step'), 10) === step) {
        if (visible(g)) { p = paths[i]; break; }
      }
    }
    if (!p) { return; }
    var len = p.getTotalLength();
    var start = null;
    pkt.style.fill = window.getComputedStyle(p).stroke;
    pkt.style.display = '';
    function frame(t) {
      if (start === null) { start = t; }
      var k = Math.min(1, (t - start) / 700);
      var pt = p.getPointAtLength(len * k);
      pkt.setAttribute('cx', pt.x);
      pkt.setAttribute('cy', pt.y);
      if (k === 1) { hidePacket(); } else { raf = requestAnimationFrame(frame); }
    }
    raf = requestAnimationFrame(frame);
  }
  function playLabel() {
    if (timer) { return '일시정지'; }
    if (step === LAST) { return '다시 재생'; }
    if (step >= 0) { return '이어서 재생'; }
    return '재생';
  }
  function render() {
    root.setAttribute('data-mode', mode);
    var i, s, a, tx;
    for (i = 0; i !== els.length; i++) {
      s = parseInt(els[i].getAttribute('data-step'), 10);
      els[i].classList.toggle('ygd-on', step >= s);
      els[i].classList.toggle('ygd-cur', step === s);
    }
    if (step === -1) {
      tx = IDLE[mode];
      elN.textContent = tx[0];
      elT.textContent = tx[1];
      elD.textContent = tx[2];
    } else {
      a = STEPS[mode][step];
      elN.textContent = '단계 ' + (step + 1) + ' / ' + (LAST + 1);
      elT.textContent = a[0];
      elD.textContent = a[1];
    }
    for (i = 0; i !== tabs.length; i++) {
      tabs[i].setAttribute('aria-pressed', tabs[i].getAttribute('data-mode-btn') === mode ? 'true' : 'false');
    }
    btnPlay.textContent = playLabel();
    btnNext.disabled = step === LAST;
  }
  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
  }
  function go(n) {
    step = n;
    if (step === LAST) { stop(); }
    render();
    runPacket();
  }
  function play() {
    if (timer) { stop(); render(); return; }
    if (step === LAST) { step = -1; }
    timer = setInterval(function () {
      if (step >= LAST) { stop(); render(); return; }
      go(step + 1);
    }, INTERVAL);
    go(step + 1);
  }
  btnPlay.addEventListener('click', play);
  btnNext.addEventListener('click', function () {
    stop();
    if (step !== LAST) { go(step + 1); }
  });
  btnReset.addEventListener('click', function () {
    stop();
    hidePacket();
    step = -1;
    render();
  });
  Array.prototype.forEach.call(tabs, function (b) {
    b.addEventListener('click', function () {
      stop();
      hidePacket();
      mode = b.getAttribute('data-mode-btn');
      step = -1;
      render();
    });
  });
  render();
})();
</script>
</div>

### 시계 차이로 토큰이 거부된다

서버 시계가 5초 빠르면 막 발급된 토큰의 `iat`가 미래로 보인다. 그러면 `nbf` 검증에서 거부된다. NTP 동기화는 기본이고, 라이브러리 leeway 설정도 30~60초 정도 둬라.

### Discovery 호출이 부팅 시 실패한다

위에서 언급한 대로, Spring Security가 `issuer-uri`로 Discovery를 호출하는데 인가 서버가 다운이거나 네트워크 문제로 실패하면 클라이언트 부팅도 실패한다. 운영에서 인가 서버 장애가 곧 모든 클라이언트 장애로 번진다. 

방어 방법은 두 가지다. 하나는 Discovery 결과를 빌드 타임에 가져와 정적으로 설정하는 것. 다른 하나는 lazy 초기화로 첫 요청까지 미루는 것. Spring Boot에서는 `OAuth2AuthorizationServerMetadata`를 직접 빈으로 등록할 수도 있다.

### 토큰 크기가 너무 커진다

JWT 토큰에 권한 정보를 다 넣으면 헤더 사이즈가 8KB를 넘기도 한다. nginx 기본 헤더 버퍼는 8KB라 그대로 터진다. 권한이 많은 사용자(예: 관리자)에서 발견되는 패턴이다.

해결은 두 가지. 토큰에는 사용자 ID와 최소한의 권한만 넣고, 상세 권한은 캐시(Redis 등)에서 조회하는 방식. 또는 nginx 헤더 버퍼를 늘리는 방식. 전자가 정석이다.

## 기존 문서와의 관계

이 문서는 `Auth_Strategy_Deep_Dive.md`가 다룬 보안 트레이드오프 위에서 실제 구현 디테일을 채운다. 두 문서를 합치면 다음 흐름이 된다.

1. `Authentication_Strategy.md`: Session/JWT/OAuth2의 기본 동작
2. `Auth_Strategy_Deep_Dive.md`: 토큰 저장 위치, Refresh 회전, CSRF/XSS, OIDC 등장 배경
3. `O_Auth2_OIDC_Flows.md` (이 문서): Flow 종류별 구현, ID Token 검증, Discovery/JWKS, 인가 서버 직접 구축

OAuth2/OIDC를 처음부터 끝까지 한 호흡으로 가려면 1 → 2 → 3 순으로 읽으면 된다. 마이크로서비스 간 인증 시나리오는 `MSA_Auth.md`, 권한 모델은 `RBAC_ABAC.md`에서 이어진다.

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
