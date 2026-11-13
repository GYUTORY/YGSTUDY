---
title: mTLS - 상호 TLS 인증과 서비스 간 신뢰
tags: [network, security, encryption, proxy]
updated: 2026-11-14
---

# mTLS - 상호 TLS 인증과 서비스 간 신뢰

일반 HTTPS는 서버만 인증서를 보여준다. 클라이언트는 "이 서버가 진짜 example.com이 맞나"를 검증하지만, 서버 입장에서 "지금 접속한 클라이언트가 누구인가"는 TLS 계층에서 알 수 없다. 그건 보통 그 위 애플리케이션 계층에서 토큰이나 세션으로 처리한다.

mTLS(mutual TLS)는 이 검증을 양방향으로 만든다. 서버도 인증서를 내고, 클라이언트도 인증서를 낸다. 핸드셰이크가 끝나는 순간 서로가 서로의 신원을 인증서로 증명한 상태가 된다. 처음엔 "그냥 API 키 쓰면 되지 왜 인증서까지"라고 생각했는데, 서비스 수가 수십 개로 늘고 내부 트래픽도 평문으로 두면 안 되는 상황이 되니까 mTLS 말고는 답이 없었다. 토큰은 탈취되면 끝이지만, 사설키는 디스크 밖으로 나가지 않게 운영할 수 있다.

이 문서는 mTLS의 핸드셰이크 흐름, 서비스 메시와 제로트러스트에서 mTLS를 어떻게 쓰는지, SPIFFE라는 신원 체계, 그리고 운영하면서 가장 자주 깨지는 인증서 만료·SAN 불일치 문제를 다룬다. 단방향 TLS 핸드셰이크 자체나 ACME 자동 갱신은 [TLS와 HTTPS](TLS_HTTPS.md) 문서에 정리해 두었으니 그쪽을 먼저 보는 게 좋다.

## 단방향 TLS와 무엇이 다른가

핵심 차이는 핸드셰이크 중간에 서버가 클라이언트 인증서를 요구하느냐다. TLS 1.2 기준으로 서버가 `CertificateRequest` 메시지를 보내면 그때부터 양방향이 된다. 클라이언트는 자기 인증서를 보내고, 그 인증서로 핸드셰이크 해시에 서명한 `CertificateVerify`까지 보낸다. 서버는 이 서명을 검증해서 "클라이언트가 정말 그 사설키를 들고 있다"는 걸 확인한다.

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: ClientHello
    S-->>C: ServerHello
    S-->>C: Certificate (서버 인증서 체인)
    S-->>C: CertificateRequest (클라이언트 인증서 요구)
    S-->>C: ServerHelloDone

    C->>S: Certificate (클라이언트 인증서 체인)
    C->>S: ClientKeyExchange
    C->>S: CertificateVerify (사설키로 서명)
    C->>S: ChangeCipherSpec / Finished

    S-->>C: ChangeCipherSpec / Finished
    C->>S: Application Data
```

여기서 `CertificateRequest`와 `CertificateVerify` 두 메시지가 단방향 TLS에는 없는 부분이다. 나머지는 동일하다. TLS 1.3에서는 메시지 순서가 좀 다르고 `CertificateRequest`가 암호화된 구간에서 오가지만, "서버가 요구하면 클라이언트가 인증서와 서명을 낸다"는 본질은 같다.

서버가 클라이언트 인증서를 검증할 때 보는 건 두 가지다. 첫째, 클라이언트 인증서가 서버가 신뢰하는 CA로 서명됐는가(체인 검증). 둘째, 그 인증서에 박힌 신원(CN 또는 SAN)이 허용된 대상인가. 첫 번째는 TLS 라이브러리가 자동으로 해주지만, 두 번째는 애플리케이션이나 프록시 설정에서 별도로 걸어줘야 하는 경우가 많다. 이걸 빼먹으면 "우리 CA가 발급한 인증서면 누구든 통과"가 되어서 mTLS를 하는 의미가 절반으로 준다.

## CA 체인과 신뢰 구조

mTLS에서 양쪽이 인증서를 검증하려면 공통의 신뢰 기준이 있어야 한다. 그게 CA(Certificate Authority)다. 외부 공개 서비스는 Let's Encrypt 같은 공인 CA를 쓰지만, 내부 서비스 간 mTLS는 거의 사설 CA(internal CA)를 직접 운영한다. 공인 CA는 클라이언트 인증서를 수백 개씩 발급해 주지도 않고, 내부 서비스 이름으로 인증서를 받을 수도 없기 때문이다.

사설 CA 구조는 보통 루트 CA 하나에 중간 CA를 두고, 실제 서비스 인증서는 중간 CA로 발급한다. 루트 CA의 사설키는 평소에 오프라인으로 격리하고 중간 CA만 온라인에 두는 식이다. 루트가 털리면 전체 신뢰가 무너지지만 중간 CA는 폐기하고 재발급하면 되니까 위험을 분리하는 구조다.

체인 검증은 잎(서비스 인증서)에서 시작해서 루트까지 거슬러 올라간다.

```
서비스 인증서 (leaf)
  └─ 발급자: 중간 CA
       └─ 발급자: 루트 CA  ← 양쪽이 미리 신뢰 목록에 가지고 있어야 함
```

여기서 자주 터지는 게 중간 CA 인증서 누락이다. 서버가 leaf 인증서만 보내고 중간 CA를 빼먹으면, 클라이언트는 leaf의 발급자를 찾지 못해 체인을 못 잇는다. 브라우저는 AIA(Authority Information Access) 필드를 보고 중간 인증서를 알아서 받아오는 경우가 있어서 브라우저에선 되는데 curl이나 다른 서비스에선 깨지는 일이 생긴다. 그래서 서버는 항상 leaf + 중간 CA를 묶은 풀체인(fullchain)을 내보내야 한다.

검증해 보려면 openssl로 직접 체인을 확인하는 게 빠르다.

```bash
# 서버가 실제로 내보내는 인증서 체인 확인
openssl s_client -connect api.internal:443 -showcerts </dev/null 2>/dev/null

# 클라이언트 인증서를 들고 mTLS 연결 시도
openssl s_client -connect api.internal:443 \
  -cert client.crt -key client.key \
  -CAfile ca-chain.crt </dev/null

# 인증서 하나를 CA 체인으로 검증
openssl verify -CAfile ca-chain.crt client.crt
```

`openssl verify`가 `OK`를 내면 체인이 정상이다. `unable to get local issuer certificate`가 나오면 중간 CA가 빠진 것이고, `certificate has expired`면 만료다.

<div class="ygd-chain-verification-fullchain-vs-leaf-only" id="ygd-chain-verification-fullchain-vs-leaf-only">
<style>
.ygd-chain-verification-fullchain-vs-leaf-only{--ygd-surface:#F7F5F3;--ygd-box:#FFFFFF;--ygd-line:#8C867F;--ygd-border:#D6D1CB;--ygd-text:#2B2724;--ygd-muted:#5F5A54;--ygd-accent:#2F6B80;--ygd-accent-bg:#E6F0F4;--ygd-ok:#17653A;--ygd-ok-bg:#E5F4EA;--ygd-bad:#B3261E;--ygd-bad-bg:#FBE9E7;--ygd-warn:#8A5A00;--ygd-warn-bg:#FFF3DC;--ygd-on-bg:#2F6B80;--ygd-on-fg:#FFFFFF;max-width:760px;margin-left:auto;margin-right:auto;margin-top:16px;margin-bottom:16px;padding:12px;box-sizing:border-box;background:var(--ygd-surface);border:1px solid var(--ygd-border);border-radius:10px;color:var(--ygd-text);}
body[data-md-color-scheme="slate"] .ygd-chain-verification-fullchain-vs-leaf-only{--ygd-surface:#2A2628;--ygd-box:#332F31;--ygd-line:#9A948C;--ygd-border:#5A544F;--ygd-text:#F0EDE9;--ygd-muted:#B3ADA5;--ygd-accent:#7FC1D8;--ygd-accent-bg:#1F3A45;--ygd-ok:#6FCF97;--ygd-ok-bg:#1F3A2A;--ygd-bad:#FF8A80;--ygd-bad-bg:#4A2724;--ygd-warn:#E3B04B;--ygd-warn-bg:#3F3217;--ygd-on-bg:#7FC1D8;--ygd-on-fg:#10262E;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-bar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-grp{display:flex;flex-wrap:wrap;gap:8px;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-btn{box-sizing:border-box;min-height:40px;padding:6px 12px;font-size:14px;line-height:1.3;font-family:inherit;color:var(--ygd-text);background:var(--ygd-box);border:1px solid var(--ygd-border);border-radius:8px;cursor:pointer;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-btn:hover{border-color:var(--ygd-accent);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-btn[aria-pressed="true"]{background:var(--ygd-on-bg);color:var(--ygd-on-fg);border-color:var(--ygd-on-bg);font-weight:700;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-btn:disabled{opacity:0.5;cursor:default;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-svg{display:block;width:100%;max-width:440px;height:auto;margin:0 auto;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-cap{font-size:12px;fill:var(--ygd-muted);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-rect{fill:var(--ygd-box);stroke:var(--ygd-border);stroke-width:1.5;transition:fill 0.3s,stroke 0.3s;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-title{font-size:14px;font-weight:700;fill:var(--ygd-text);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-sub{font-size:12px;fill:var(--ygd-muted);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-tag{font-size:12px;font-weight:600;fill:var(--ygd-muted);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-verdict{font-size:13px;font-weight:700;fill:var(--ygd-muted);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-active .ygd-rect{fill:var(--ygd-accent-bg);stroke:var(--ygd-accent);stroke-width:3;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-ok .ygd-rect{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok);stroke-width:2.5;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-bad .ygd-rect{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad);stroke-width:2.5;stroke-dasharray:6 4;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-miss .ygd-rect{fill:var(--ygd-surface);stroke:var(--ygd-line);stroke-width:2;stroke-dasharray:6 4;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-fetch .ygd-rect{fill:var(--ygd-warn-bg);stroke:var(--ygd-warn);stroke-width:2.5;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-active .ygd-tag,.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-active .ygd-verdict{fill:var(--ygd-accent);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-ok .ygd-tag,.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-ok .ygd-verdict{fill:var(--ygd-ok);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-bad .ygd-tag,.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-bad .ygd-verdict{fill:var(--ygd-bad);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-st-fetch .ygd-tag{fill:var(--ygd-warn);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-aline{fill:none;stroke:var(--ygd-line);stroke-width:2;transition:stroke 0.3s;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-albl{font-size:12px;fill:var(--ygd-muted);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-active .ygd-aline{stroke:var(--ygd-accent);stroke-width:3;stroke-dasharray:6 4;animation:ygd-chain-verification-fullchain-vs-leaf-only-dash 0.8s linear infinite;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-active .ygd-albl{fill:var(--ygd-accent);font-weight:700;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-ok .ygd-aline{stroke:var(--ygd-ok);stroke-width:3;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-ok .ygd-albl{fill:var(--ygd-ok);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-bad .ygd-aline{stroke:var(--ygd-bad);stroke-width:3;stroke-dasharray:4 5;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-bad .ygd-albl{fill:var(--ygd-bad);font-weight:700;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-x{display:none;stroke:var(--ygd-bad);stroke-width:3.5;stroke-linecap:round;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-bad .ygd-x{display:inline;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-mk0{fill:var(--ygd-line);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-mk1{fill:var(--ygd-accent);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-mk2{fill:var(--ygd-ok);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-panel{box-sizing:border-box;margin-top:10px;padding:12px 14px;min-height:8em;background:var(--ygd-box);border:1px solid var(--ygd-border);border-radius:8px;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-step{margin:0 0 4px 0;font-size:14px;color:var(--ygd-muted);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ptitle{margin:0 0 6px 0;font-size:16px;font-weight:700;line-height:1.4;color:var(--ygd-text);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ptext{margin:0;font-size:15px;line-height:1.6;color:var(--ygd-text);}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-note{margin:10px 0 0 0;font-size:14px;line-height:1.6;color:var(--ygd-muted);}
@keyframes ygd-chain-verification-fullchain-vs-leaf-only-dash{to{stroke-dashoffset:-10;}}
@media (prefers-reduced-motion: reduce){
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-rect,.ygd-chain-verification-fullchain-vs-leaf-only .ygd-aline{transition:none;}
.ygd-chain-verification-fullchain-vs-leaf-only .ygd-ar-active .ygd-aline{animation:none;}
}
</style>
<div class="ygd-bar">
<div class="ygd-grp" role="group" aria-label="서버가 보내는 인증서 선택">
<button type="button" class="ygd-btn" data-mode="full" aria-pressed="true">풀체인을 보낸 경우</button>
<button type="button" class="ygd-btn" data-mode="leaf" aria-pressed="false">leaf만 보낸 경우</button>
</div>
<div class="ygd-grp" role="group" aria-label="재생 제어">
<button type="button" class="ygd-btn" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="next">다음 단계</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
</div>
<svg class="ygd-svg" viewBox="0 0 340 416" role="img" aria-label="인증서 체인 검증 다이어그램" focusable="false">
<defs>
<marker id="ygd-chain-verification-fullchain-vs-leaf-only-ah0" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path class="ygd-mk0" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="ygd-chain-verification-fullchain-vs-leaf-only-ah1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path class="ygd-mk1" d="M0,0 L10,5 L0,10 z"/></marker>
<marker id="ygd-chain-verification-fullchain-vs-leaf-only-ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" orient="auto"><path class="ygd-mk2" d="M0,0 L10,5 L0,10 z"/></marker>
</defs>
<text class="ygd-cap" x="10" y="16">검증 방향: leaf에서 위로, 루트 CA까지</text>
<g class="ygd-box ygd-st-idle" data-k="root">
<rect class="ygd-rect" x="10" y="28" width="320" height="56" rx="8"/>
<text class="ygd-title" x="24" y="52">루트 CA</text>
<text class="ygd-tag" x="316" y="52" text-anchor="end">신뢰 목록</text>
<text class="ygd-sub" x="24" y="72">검증하는 쪽 신뢰 목록에 미리 있음</text>
</g>
<g class="ygd-arrow ygd-ar-idle" data-k="a2">
<line class="ygd-aline" x1="34" y1="132" x2="34" y2="88"/>
<text class="ygd-albl" x="52" y="112">발급자 = 루트 CA</text>
</g>
<g class="ygd-box ygd-st-idle" data-k="mid">
<rect class="ygd-rect" x="10" y="132" width="320" height="56" rx="8"/>
<text class="ygd-title" x="24" y="156">중간 CA</text>
<text class="ygd-tag" x="316" y="156" text-anchor="end">서버가 보냄</text>
<text class="ygd-sub" x="24" y="176">발급자: 루트 CA</text>
</g>
<g class="ygd-arrow ygd-ar-idle" data-k="a1">
<line class="ygd-aline" x1="34" y1="236" x2="34" y2="190"/>
<g class="ygd-x"><line x1="28" y1="206" x2="40" y2="218"/><line x1="40" y1="206" x2="28" y2="218"/></g>
<text class="ygd-albl" x="52" y="216">발급자 = 중간 CA</text>
</g>
<g class="ygd-box ygd-st-idle" data-k="leaf">
<rect class="ygd-rect" x="10" y="236" width="320" height="56" rx="8"/>
<text class="ygd-title" x="24" y="260">leaf (서비스 인증서)</text>
<text class="ygd-tag" x="316" y="260" text-anchor="end">서버가 보냄</text>
<text class="ygd-sub" x="24" y="280">발급자: 중간 CA</text>
</g>
<g class="ygd-box ygd-st-idle" data-k="rb">
<rect class="ygd-rect" x="10" y="312" width="320" height="44" rx="8"/>
<text class="ygd-title" x="24" y="331">브라우저</text>
<text class="ygd-verdict" x="316" y="331" text-anchor="end">대기</text>
<text class="ygd-sub" x="24" y="349"> </text>
</g>
<g class="ygd-box ygd-st-idle" data-k="rc">
<rect class="ygd-rect" x="10" y="364" width="320" height="44" rx="8"/>
<text class="ygd-title" x="24" y="383">curl</text>
<text class="ygd-verdict" x="316" y="383" text-anchor="end">대기</text>
<text class="ygd-sub" x="24" y="401"> </text>
</g>
</svg>
<div class="ygd-panel" aria-live="polite">
<p class="ygd-step"></p>
<p class="ygd-ptitle"></p>
<p class="ygd-ptext"></p>
</div>
<p class="ygd-note">비유: 낯선 사람이 소개장(leaf)을 내밀면, 소개한 사람(중간 CA)이 누구인지 알아야 믿을 수 있고, 그 사람은 내가 이미 아는 사람(루트 CA)이 보증해야 한다. 중간 소개인의 서류가 빠지면 확인이 끊긴다. 비유일 뿐이고, 실제 검증은 인증서의 서명과 발급자 필드로 이뤄진다.</p>
<script>
(function(){
var root=document.getElementById('ygd-chain-verification-fullchain-vs-leaf-only');
if(!root){return;}
var PFX='ygd-chain-verification-fullchain-vs-leaf-only';
var ERR='unable to get local issuer certificate';
var AIA_NOTE='AIA로 중간 CA를 받아와 체인 완성';
var svg=root.querySelector('.ygd-svg');
var g={};
['root','mid','leaf','rb','rc'].forEach(function(k){g[k]=root.querySelector('.ygd-box[data-k="'+k+'"]');});
g.a1=root.querySelector('.ygd-arrow[data-k="a1"]');
g.a2=root.querySelector('.ygd-arrow[data-k="a2"]');
var elStep=root.querySelector('.ygd-step');
var elTitle=root.querySelector('.ygd-ptitle');
var elText=root.querySelector('.ygd-ptext');
var playBtn=root.querySelector('[data-act="play"]');
var nextBtn=root.querySelector('[data-act="next"]');
var modeBtns=root.querySelectorAll('[data-mode]');
var STEPS={
full:[
{t:'서버가 풀체인을 보낸다',d:'서버가 leaf와 중간 CA를 묶은 풀체인을 내보낸다. 루트 CA는 검증하는 쪽의 신뢰 목록에 미리 들어 있다.',leaf:'',mid:'',root:'',a1:'',a2:'',rb:'p',rc:'p'},
{t:'1단계: leaf의 발급자 확인',d:'leaf의 발급자는 중간 CA다. 서버가 보낸 체인 안에 중간 CA가 있어서 바로 이어 붙일 수 있다.',leaf:'active',mid:'',root:'',a1:'active',a2:'',rb:'p',rc:'p'},
{t:'2단계: 중간 CA의 발급자 확인',d:'중간 CA의 발급자는 루트 CA다. 루트는 신뢰 목록에 있으므로 여기서 신뢰 기준점에 닿는다.',leaf:'ok',mid:'active',root:'',a1:'ok',a2:'active',rb:'p',rc:'p'},
{t:'3단계: 체인 완성',d:'leaf에서 루트까지 끊김 없이 이어졌다. 브라우저든 curl이든 결과가 같고, openssl verify도 OK를 낸다.',leaf:'ok',mid:'ok',root:'ok',a1:'ok',a2:'ok',rb:'ok',rc:'ok'}
],
leaf:[
{t:'서버가 leaf만 보낸다',d:'서버가 leaf 인증서 하나만 내보냈다. 중간 CA는 체인에 없고, 루트 CA만 검증하는 쪽의 신뢰 목록에 들어 있다.',leaf:'',mid:'miss',root:'',a1:'',a2:'',rb:'p',rc:'p'},
{t:'1단계: leaf의 발급자를 찾는다',d:'leaf의 발급자는 중간 CA다. 서명을 확인하려면 그 중간 CA 인증서가 손에 있어야 한다.',leaf:'active',mid:'miss',root:'',a1:'active',a2:'',rb:'p',rc:'p'},
{t:'2단계: 중간 CA에서 끊긴다',d:'발급자인 중간 CA를 찾지 못해 루트까지 올라가지 못한다. openssl verify는 '+ERR+' 를 낸다.',leaf:'active',mid:'bad',root:'',a1:'bad',a2:'',a1l:'발급자인 중간 CA를 못 찾음',rb:'p',rc:'p'},
{t:'3단계: 브라우저는 AIA로 받아온다',d:'브라우저는 leaf의 AIA(Authority Information Access) 필드를 보고 중간 인증서를 받아와 체인을 잇는 경우가 있다. 그래서 브라우저에서는 열린다.',leaf:'ok',mid:'fetch',root:'ok',a1:'ok',a2:'ok',mt:'AIA로 받아옴',ms:'발급자: 루트 CA',rb:'ok',rc:'p'},
{t:'4단계: curl은 같은 서버에서 실패',d:'curl이나 다른 서비스는 중간 인증서를 받아오지 못해 같은 서버에서 깨지는 일이 생긴다. 서버가 leaf와 중간 CA를 묶은 풀체인을 내보내야 한다.',leaf:'active',mid:'bad',root:'',a1:'bad',a2:'',a1l:'발급자인 중간 CA를 못 찾음',rb:'ok',rc:'bad'}
]
};
var mode='full';
var idx=0;
var timer=null;
function setCls(el,base,st){el.setAttribute('class',base+' '+(base==='ygd-arrow'?'ygd-ar-':'ygd-st-')+(st||'idle'));}
function setText(el,sel,txt){el.querySelector(sel).textContent=txt;}
function rowInfo(st){
if(st==='ok'){return {v:'통과',d:(mode==='full'?'풀체인으로 루트까지 연결됨':AIA_NOTE)};}
if(st==='bad'){return {v:'실패',d:ERR};}
return {v:'대기',d:' '};
}
function setArrow(el,st,label,defLabel){
setCls(el,'ygd-arrow',st);
var line=el.querySelector('.ygd-aline');
var n={'active':'1','ok':'2','bad':''}[st];
if(n===undefined){n='0';}
if(n===''){line.removeAttribute('marker-end');}
else{line.setAttribute('marker-end','url(#'+PFX+'-ah'+n+')');}
setText(el,'.ygd-albl',label||defLabel);
}
function render(){
var list=STEPS[mode];
var s=list[idx];
var last=list.length-1;
setCls(g.leaf,'ygd-box',s.leaf);
setCls(g.mid,'ygd-box',s.mid);
setCls(g.root,'ygd-box',s.root==='ok'?'ok':s.root);
setArrow(g.a1,s.a1,s.a1l,'발급자 = 중간 CA');
setArrow(g.a2,s.a2,'','발급자 = 루트 CA');
setText(g.mid,'.ygd-tag',s.mt||(mode==='full'?'서버가 보냄':'체인에 없음'));
setText(g.mid,'.ygd-sub',s.ms||(mode==='full'?'발급자: 루트 CA':'발급자 확인에 필요하지만 보내지 않음'));
var rows=[['rb',s.rb],['rc',s.rc]];
rows.forEach(function(r){
var info=rowInfo(r[1]);
setCls(g[r[0]],'ygd-box',r[1]==='p'?'idle':r[1]);
setText(g[r[0]],'.ygd-verdict',info.v);
setText(g[r[0]],'.ygd-sub',info.d);
});
elStep.textContent='단계 '+(idx+1)+' / '+(last+1)+' · '+(mode==='full'?'풀체인을 보낸 경우':'leaf만 보낸 경우');
elTitle.textContent=s.t;
elText.textContent=s.d;
svg.setAttribute('aria-label','인증서 체인 검증 다이어그램. '+(mode==='full'?'풀체인을 보낸 경우. ':'leaf만 보낸 경우. ')+s.t+'. '+s.d);
nextBtn.disabled=(idx>=last);
playBtn.textContent=timer?'일시정지':(idx>=last?'다시 재생':'재생');
}
function stop(){
if(timer){clearTimeout(timer);timer=null;}
}
function tick(){
timer=setTimeout(function(){
timer=null;
var last=STEPS[mode].length-1;
if(idx<last){idx=idx+1;}
if(idx<last){tick();}
render();
},3000);
}
function play(){
if(timer){stop();render();return;}
if(idx>=STEPS[mode].length-1){idx=0;}
tick();
render();
}
playBtn.addEventListener('click',play);
nextBtn.addEventListener('click',function(){
stop();
if(idx<STEPS[mode].length-1){idx=idx+1;}
render();
});
root.querySelector('[data-act="reset"]').addEventListener('click',function(){
stop();
idx=0;
render();
});
Array.prototype.forEach.call(modeBtns,function(b){
b.addEventListener('click',function(){
stop();
mode=b.getAttribute('data-mode');
idx=0;
Array.prototype.forEach.call(modeBtns,function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});
render();
});
});
render();
})();
</script>
</div>

## 클라이언트 인증서 발급과 로테이션

서버 인증서는 만료 관리만 잘하면 되지만, 클라이언트 인증서는 발급 대상이 서비스/워크로드 단위로 늘어나기 때문에 운영 부담이 다르다. 서비스가 50개면 클라이언트 인증서도 50종이고, 오토스케일로 인스턴스가 뜨고 죽을 때마다 인증서가 필요하다. 이걸 손으로 발급하는 건 불가능하다.

처음엔 인증서 유효기간을 1년쯤 길게 잡고 싶은 유혹이 있는데, 길게 잡으면 그만큼 탈취됐을 때 노출 시간이 길어진다. 그래서 요즘은 오히려 유효기간을 짧게(몇 시간~며칠) 가져가고 자동으로 재발급하는 쪽으로 간다. 짧게 가면 폐기 목록(CRL/OCSP)을 관리할 필요도 줄어든다. 어차피 곧 만료되니까.

로테이션에서 제일 중요한 건 무중단이다. 인증서를 교체하는 순간 기존 연결이 끊기거나 새 연결이 거부되면 안 된다. 핵심은 겹침 구간을 두는 것이다.

- 새 인증서를 발급할 때 기존 인증서가 만료되기 한참 전에 미리 발급한다.
- 서버의 CA 신뢰 목록에는 구 CA와 신 CA를 동시에 올려둔다(CA를 교체하는 경우).
- 클라이언트가 새 인증서로 갈아탄 뒤에야 구 인증서를 폐기한다.

CA 자체를 교체(rotation)할 때 이 겹침을 안 두면 대형 장애가 난다. 신 CA로 발급한 클라이언트가 접속했는데 서버가 아직 구 CA만 신뢰하고 있으면 전부 거부된다. 그래서 CA 교체는 "신 CA를 신뢰 목록에 추가 → 모든 워크로드를 신 CA 인증서로 전환 → 구 CA 제거" 순서를 반드시 지킨다. 중간 단계에서 둘 다 신뢰하는 구간이 있어야 한다.

파일 기반으로 인증서를 마운트해 쓰는 서비스라면, 인증서 파일이 교체됐을 때 프로세스가 다시 읽도록 해야 한다. Nginx는 reload 신호를 줘야 새 인증서를 읽고, Envoy는 SDS(Secret Discovery Service)로 받으면 재시작 없이 갱신된다. 파일만 바꿔놓고 reload를 안 해서 만료된 인증서를 계속 쓰다가 터지는 사고가 흔하다.

<div class="ygd-ca-rotation-overlap-timeline" id="ygd-ca-rotation-overlap-timeline">
<style>
.ygd-ca-rotation-overlap-timeline{--ygd-fg:#2b2826;--ygd-muted:#5f5a55;--ygd-surface:#faf8f6;--ygd-border:#b9b1a8;--ygd-ok:#1b7a3d;--ygd-ok-bg:#e1f2e6;--ygd-bad:#b3261e;--ygd-bad-bg:#fbe3e0;--ygd-accent:#2f6f86;--ygd-on-accent:#ffffff;--ygd-chip:#edf3f5;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1.2em;margin-bottom:1.2em;padding:14px;box-sizing:border-box;background:var(--ygd-surface);color:var(--ygd-fg);border:1px solid var(--ygd-border);border-radius:10px;font-size:14px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-ca-rotation-overlap-timeline{--ygd-fg:#ece8e4;--ygd-muted:#b3ada5;--ygd-surface:#2a2629;--ygd-border:#6b645d;--ygd-ok:#6fd697;--ygd-ok-bg:#1f3a2a;--ygd-bad:#ff8a80;--ygd-bad-bg:#4a2523;--ygd-accent:#7cc0d6;--ygd-on-accent:#10202a;--ygd-chip:#323a3e}
.ygd-ca-rotation-overlap-timeline *{box-sizing:border-box}
.ygd-ca-rotation-overlap-timeline .ygd-modes,.ygd-ca-rotation-overlap-timeline .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px 0}
.ygd-ca-rotation-overlap-timeline .ygd-ctrl{margin:12px 0 0 0}
.ygd-ca-rotation-overlap-timeline .ygd-btn{min-height:40px;padding:6px 14px;font-size:14px;font-family:inherit;color:var(--ygd-fg);background:transparent;border:1.5px solid var(--ygd-border);border-radius:8px;cursor:pointer}
.ygd-ca-rotation-overlap-timeline .ygd-btn:hover{border-color:var(--ygd-accent)}
.ygd-ca-rotation-overlap-timeline .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-ca-rotation-overlap-timeline .ygd-btn[aria-pressed="true"],.ygd-ca-rotation-overlap-timeline .ygd-play{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-on-accent);font-weight:700}
.ygd-ca-rotation-overlap-timeline .ygd-btn[aria-pressed="true"].ygd-mode-bad{background:var(--ygd-bad);border-color:var(--ygd-bad)}
.ygd-ca-rotation-overlap-timeline .ygd-btn:disabled{opacity:0.45;cursor:default}
.ygd-ca-rotation-overlap-timeline .ygd-svg{display:block;width:100%;max-width:520px;height:auto;margin:0 auto}
.ygd-ca-rotation-overlap-timeline .ygd-t{fill:var(--ygd-fg);font-size:12px;font-family:inherit}
.ygd-ca-rotation-overlap-timeline .ygd-tb{font-weight:700}
.ygd-ca-rotation-overlap-timeline .ygd-tm{fill:var(--ygd-muted)}
.ygd-ca-rotation-overlap-timeline .ygd-tok{fill:var(--ygd-ok)}
.ygd-ca-rotation-overlap-timeline .ygd-tbad{fill:var(--ygd-bad)}
.ygd-ca-rotation-overlap-timeline .ygd-tacc{fill:var(--ygd-accent)}
.ygd-ca-rotation-overlap-timeline .ygd-ton{fill:var(--ygd-on-accent)}
.ygd-ca-rotation-overlap-timeline .ygd-box{fill:var(--ygd-chip);stroke:var(--ygd-border);stroke-width:1.5}
.ygd-ca-rotation-overlap-timeline .ygd-on{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok)}
.ygd-ca-rotation-overlap-timeline .ygd-bad{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad)}
.ygd-ca-rotation-overlap-timeline .ygd-off{fill:none;stroke-dasharray:4 3}
.ygd-ca-rotation-overlap-timeline .ygd-band{fill:var(--ygd-chip);stroke:var(--ygd-accent);stroke-width:1.5;stroke-dasharray:5 3}
.ygd-ca-rotation-overlap-timeline .ygd-panel{margin-top:12px;padding:10px 12px;background:var(--ygd-chip);border-left:5px solid var(--ygd-accent);border-radius:6px}
.ygd-ca-rotation-overlap-timeline .ygd-panel.ygd-fail{border-left-color:var(--ygd-bad)}
.ygd-ca-rotation-overlap-timeline .ygd-count{margin:0;font-size:14px;color:var(--ygd-muted)}
.ygd-ca-rotation-overlap-timeline .ygd-step-title{margin:2px 0 4px 0;font-size:16px;font-weight:700;color:var(--ygd-fg)}
.ygd-ca-rotation-overlap-timeline .ygd-step-desc{margin:0;font-size:14px;color:var(--ygd-fg)}
.ygd-ca-rotation-overlap-timeline .ygd-analogy{margin:12px 0 0 0;font-size:14px;color:var(--ygd-muted)}
</style>
<div class="ygd-modes" role="group" aria-label="시나리오 선택">
  <button type="button" class="ygd-btn ygd-mode ygd-mode-ok" aria-pressed="true">정상 순서 (겹침 구간 있음)</button>
  <button type="button" class="ygd-btn ygd-mode ygd-mode-bad" aria-pressed="false">장애 시나리오 (바로 전환)</button>
</div>
<svg class="ygd-svg" viewBox="0 0 340 254" role="img" aria-label="CA 교체 시 서버 신뢰 목록과 클라이언트 접속 결과를 단계별로 보여주는 타임라인">
  <g class="ygd-layer"></g>
</svg>
<div class="ygd-panel" aria-live="polite">
  <p class="ygd-count"></p>
  <p class="ygd-step-title"></p>
  <p class="ygd-step-desc"></p>
</div>
<div class="ygd-ctrl">
  <button type="button" class="ygd-btn ygd-play">재생</button>
  <button type="button" class="ygd-btn ygd-prev">이전 단계</button>
  <button type="button" class="ygd-btn ygd-next">다음 단계</button>
</div>
<p class="ygd-analogy">비유: 출입 게이트가 옛 발급처의 사원증만 인정하는 상태에서, 새 발급처의 사원증도 먼저 인정하도록 게이트를 바꾼 뒤 사원증을 교체하고, 마지막에 옛 발급처 인정을 끝내는 순서와 같다. 게이트 설정을 먼저 바꾸지 않으면 새 사원증은 전부 막힌다.</p>
<script>
(function(){
  var root=document.getElementById('ygd-ca-rotation-overlap-timeline');
  if(!root){return;}
  var NS='http://www.w3.org/2000/svg';
  var layer=root.querySelector('.ygd-layer');
  var svg=root.querySelector('.ygd-svg');
  var panel=root.querySelector('.ygd-panel');
  var elCount=root.querySelector('.ygd-count');
  var elTitle=root.querySelector('.ygd-step-title');
  var elDesc=root.querySelector('.ygd-step-desc');
  var btnPlay=root.querySelector('.ygd-play');
  var btnPrev=root.querySelector('.ygd-prev');
  var btnNext=root.querySelector('.ygd-next');
  var btnOk=root.querySelector('.ygd-mode-ok');
  var btnBad=root.querySelector('.ygd-mode-bad');
  function el(name,attrs,text,parent){
    var e=document.createElementNS(NS,name);
    for(var k in attrs){e.setAttribute(k,attrs[k]);}
    if(text!==null&&text!==undefined){e.textContent=text;}
    if(parent){parent.appendChild(e);}
    return e;
  }
  var MODES={
    ok:{name:'정상 순서',steps:[
      {label:'구 CA만',title:'구 CA만 신뢰',old:['on','신뢰함'],neu:['off','미등록'],a:['ok'],b:['idle','미발급'],
       desc:'서버 신뢰 목록에는 구 CA만 있다. 모든 클라이언트가 구 CA가 발급한 인증서를 쓰므로 접속이 정상이다. 신 CA 인증서는 아직 쓰이지 않는다.'},
      {label:'신 CA 추가',title:'신 CA를 신뢰 목록에 추가',old:['on','신뢰함'],neu:['on','신뢰함'],a:['ok'],b:['ok'],
       desc:'서버가 구 CA와 신 CA를 동시에 신뢰하는 겹침 구간이 시작된다. 구 CA 인증서와 신 CA 인증서 모두 접속에 성공한다. 클라이언트는 아직 바꾸지 않았다.'},
      {label:'인증서 전환',title:'워크로드를 신 CA 인증서로 전환',old:['on','신뢰함'],neu:['on','신뢰함'],a:['ok'],b:['ok'],
       desc:'워크로드를 신 CA 인증서로 하나씩 전환한다. 서버가 양쪽을 신뢰하므로 구 인증서를 쓰는 워크로드와 신 인증서를 쓰는 워크로드가 섞여 있어도 둘 다 성공한다.'},
      {label:'구 CA 제거',title:'구 CA 제거',old:['off','제거됨'],neu:['on','신뢰함'],a:['idle','전환 완료'],b:['ok'],
       desc:'모든 워크로드가 신 CA 인증서로 바뀐 것을 확인한 뒤에야 구 CA를 신뢰 목록에서 제거한다. 구 CA 인증서가 남은 클라이언트가 있다면 이 시점부터 거부되므로 제거는 맨 마지막에 한다.'}
    ]},
    bad:{name:'장애 시나리오',steps:[
      {label:'구 CA만',title:'구 CA만 신뢰',old:['on','신뢰함'],neu:['off','미등록'],a:['ok'],b:['idle','미발급'],
       desc:'여기까지는 정상 순서와 같다. 서버는 구 CA만 신뢰하고 클라이언트는 구 CA 인증서로 접속한다. 다음 단계에서 신 CA 추가를 건너뛴다.'},
      {label:'바로 전환',title:'신 CA 추가 없이 바로 전환',old:['on','신뢰함'],neu:['off','미등록'],a:['idle','전환 완료'],b:['deny'],fail:true,
       desc:'서버는 아직 구 CA만 신뢰하는데 워크로드가 신 CA 인증서로 접속한다. 서버가 신 CA를 신뢰하지 않으므로 신 CA 클라이언트가 전부 거부된다. 겹침 구간이 없는 전환이 대형 장애로 이어진다.'}
    ]}
  };
  var mode='ok';
  var idx=0;
  var playing=false;
  var timer=null;
  var raf=null;
  function reduced(){
    return !!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function clearAnim(){
    if(raf){cancelAnimationFrame(raf);raf=null;}
  }
  function chip(y,name,spec){
    var cls='ygd-box '+(spec[0]==='on'?'ygd-on':'ygd-off');
    if(spec[0]==='off'&&spec[2]){cls='ygd-box ygd-bad ygd-off';}
    el('rect',{x:200,y:y,width:124,height:40,rx:6,'class':cls},null,layer);
    el('text',{x:262,y:y+16,'text-anchor':'middle','class':'ygd-t ygd-tb'},name,layer);
    el('text',{x:262,y:y+32,'text-anchor':'middle','class':'ygd-t '+(spec[0]==='on'?'ygd-tok':'ygd-tm')},spec[1],layer);
  }
  function client(y,name,cert,spec,packets,labels){
    var kind=spec[0];
    var cy=y+20;
    var g=el('g',{},null,layer);
    if(kind==='idle'){g.setAttribute('opacity','0.7');}
    el('rect',{x:6,y:y,width:116,height:40,rx:6,'class':'ygd-box'+(kind==='idle'?' ygd-off':'')},null,g);
    el('text',{x:64,y:y+16,'text-anchor':'middle','class':'ygd-t ygd-tb'},name,g);
    el('text',{x:64,y:y+32,'text-anchor':'middle','class':'ygd-t'},cert,g);
    if(kind==='idle'){
      el('line',{x1:126,y1:cy,x2:186,y2:cy,stroke:'var(--ygd-border)','stroke-width':2,'stroke-dasharray':'4 3'},null,g);
      el('text',{x:156,y:cy-8,'text-anchor':'middle','class':'ygd-t ygd-tm'},spec[1],g);
      return;
    }
    var color=kind==='ok'?'var(--ygd-ok)':'var(--ygd-bad)';
    el('line',{x1:122,y1:cy,x2:184,y2:cy,stroke:color,'stroke-width':2,'stroke-dasharray':kind==='deny'?'5 3':'0'},null,g);
    el('polygon',{points:'190,'+cy+' 182,'+(cy-4)+' 182,'+(cy+4),fill:color},null,g);
    var lab=el('text',{x:156,y:cy-8,'text-anchor':'middle','class':'ygd-t ygd-tb '+(kind==='ok'?'ygd-tok':'ygd-tbad')},kind==='ok'?'✓ 성공':'✗ 거부',g);
    labels.push(lab);
    packets.push(el('circle',{cx:126,cy:cy,r:4,fill:color},null,g));
  }
  function render(){
    clearAnim();
    while(layer.firstChild){layer.removeChild(layer.firstChild);}
    var m=MODES[mode];
    var s=m.steps[idx];
    var n=m.steps.length;
    var packets=[];
    var labels=[];
    el('text',{x:64,y:30,'text-anchor':'middle','class':'ygd-t ygd-tb'},'클라이언트',layer);
    el('rect',{x:190,y:8,width:144,height:142,rx:8,'class':'ygd-box'+(s.fail?' ygd-bad':'')},null,layer);
    el('text',{x:262,y:30,'text-anchor':'middle','class':'ygd-t ygd-tb'},'서버 신뢰 목록',layer);
    chip(42,'구 CA',s.old);
    chip(94,'신 CA',s.neu.concat(s.fail?[true]:[]));
    client(42,'클라이언트 A','구 CA 인증서',s.a,packets,labels);
    client(94,'클라이언트 B','신 CA 인증서',s.b,packets,labels);
    var span=n===2?150:83.33;
    var x0=170-span*(n-1)/2;
    var cy=206;
    function nx(i){return x0+i*span;}
    if(mode==='ok'){
      var bx=nx(1)-38;
      var bw=nx(2)-nx(1)+76;
      el('rect',{x:bx,y:184,width:bw,height:66,rx:10,'class':'ygd-band',opacity:(idx>=1&&idx<=2)?'1':'0.6'},null,layer);
      el('text',{x:(nx(1)+nx(2))/2,y:172,'text-anchor':'middle','class':'ygd-t ygd-tb ygd-tacc'},'겹침 구간: 구·신 CA 모두 신뢰',layer);
    }else{
      el('text',{x:170,y:172,'text-anchor':'middle','class':'ygd-t ygd-tb ygd-tbad'},'겹침 구간 없음',layer);
    }
    el('line',{x1:nx(0),y1:cy,x2:nx(n-1),y2:cy,stroke:'var(--ygd-border)','stroke-width':3},null,layer);
    if(idx>0){
      el('line',{x1:nx(0),y1:cy,x2:nx(idx),y2:cy,stroke:s.fail?'var(--ygd-bad)':'var(--ygd-accent)','stroke-width':3},null,layer);
    }
    for(var i=0;i<n;i++){
      var active=i===idx;
      var done=i<idx;
      var stepFail=!!m.steps[i].fail;
      var fillC=active?(stepFail?'var(--ygd-bad)':'var(--ygd-accent)'):(done?'var(--ygd-chip)':'var(--ygd-surface)');
      var strokeC=active?(stepFail?'var(--ygd-bad)':'var(--ygd-accent)'):(done?'var(--ygd-accent)':'var(--ygd-border)');
      el('circle',{cx:nx(i),cy:cy,r:12,fill:fillC,stroke:strokeC,'stroke-width':2},null,layer);
      el('text',{x:nx(i),y:cy+4,'text-anchor':'middle','class':'ygd-t ygd-tb '+(active?'ygd-ton':(done?'ygd-tacc':'ygd-tm'))},String(i+1),layer);
      el('text',{x:nx(i),y:240,'text-anchor':'middle','class':'ygd-t '+(active?'ygd-tb':'ygd-tm')},m.steps[i].label,layer);
    }
    elCount.textContent='단계 '+(idx+1)+' / '+n+' · '+m.name;
    elTitle.textContent=s.title;
    elDesc.textContent=s.desc;
    if(s.fail){panel.classList.add('ygd-fail');}else{panel.classList.remove('ygd-fail');}
    function res(spec){
      if(spec[0]==='ok'){return '성공';}
      if(spec[0]==='deny'){return '거부';}
      return spec[1];
    }
    svg.setAttribute('aria-label','CA 교체 타임라인 '+(idx+1)+'단계, '+s.title+'. 서버 신뢰 목록: 구 CA '+s.old[1]+', 신 CA '+s.neu[1]+'. 구 CA 인증서 클라이언트 A: '+res(s.a)+'. 신 CA 인증서 클라이언트 B: '+res(s.b)+'.');
    btnPrev.disabled=idx===0;
    btnNext.disabled=idx===n-1;
    btnPlay.textContent=playing?'일시정지':(idx===n-1?'다시 재생':'재생');
    if(reduced()||packets.length===0){return;}
    for(var j=0;j<labels.length;j++){labels[j].setAttribute('opacity','0');}
    var start=null;
    function frame(t){
      if(start===null){start=t;}
      var p=Math.min(1,(t-start)/700);
      for(var k=0;k<packets.length;k++){packets[k].setAttribute('cx',String(126+p*54));}
      if(p<1){raf=requestAnimationFrame(frame);}
      else{
        raf=null;
        for(var q=0;q<packets.length;q++){packets[q].setAttribute('opacity','0');}
        for(var r=0;r<labels.length;r++){labels[r].setAttribute('opacity','1');}
      }
    }
    raf=requestAnimationFrame(frame);
  }
  function stop(){
    playing=false;
    if(timer){clearTimeout(timer);timer=null;}
    btnPlay.textContent=idx===MODES[mode].steps.length-1?'다시 재생':'재생';
  }
  function schedule(){
    timer=setTimeout(function(){
      var last=MODES[mode].steps.length-1;
      if(idx<last){
        idx++;
        render();
        if(idx<last){schedule();}else{stop();}
      }else{stop();}
    },3200);
  }
  btnPlay.addEventListener('click',function(){
    if(playing){stop();return;}
    if(idx===MODES[mode].steps.length-1){idx=0;}
    playing=true;
    render();
    schedule();
  });
  btnPrev.addEventListener('click',function(){
    stop();
    if(idx>0){idx--;}
    render();
  });
  btnNext.addEventListener('click',function(){
    stop();
    if(idx<MODES[mode].steps.length-1){idx++;}
    render();
  });
  function setMode(m){
    stop();
    mode=m;
    idx=0;
    btnOk.setAttribute('aria-pressed',m==='ok'?'true':'false');
    btnBad.setAttribute('aria-pressed',m==='bad'?'true':'false');
    render();
  }
  btnOk.addEventListener('click',function(){setMode('ok');});
  btnBad.addEventListener('click',function(){setMode('bad');});
  render();
})();
</script>
</div>

## SPIFFE와 SVID

서비스가 많아지면 "이 인증서가 어느 서비스 것인가"를 사람이 정한 CN 문자열로 관리하는 게 한계에 부딪힌다. SPIFFE(Secure Production Identity Framework For Everyone)는 이 신원을 표준화한 규격이다.

SPIFFE의 핵심은 SPIFFE ID라는 신원 식별자다. URI 형태로 생긴다.

```
spiffe://example.org/ns/payment/sa/checkout-service
```

이 ID가 워크로드의 신원이다. 도메인(trust domain) `example.org` 아래에 네임스페이스 `payment`, 서비스 계정 `checkout-service`라는 식으로 계층 구조를 표현한다. 이 SPIFFE ID를 X.509 인증서의 SAN(URI 타입)에 박은 게 SVID(SPIFFE Verifiable Identity Document)다. 즉 SVID는 그냥 "SPIFFE ID가 SAN에 들어간 X.509 인증서"다.

```
X.509 SVID
  Subject Alternative Name:
    URI: spiffe://example.org/ns/payment/sa/checkout-service
```

이렇게 하면 서버가 클라이언트 인증서를 검증할 때 SAN의 URI를 보고 "아, 이건 payment 네임스페이스의 checkout 서비스구나"를 명확히 안다. CN에 호스트명을 적던 방식보다 신원이 분명하고, 권한 정책도 이 SPIFFE ID 기준으로 짤 수 있다.

SPIFFE를 구현한 대표적인 게 SPIRE다. SPIRE는 워크로드를 증명(attestation)해서 SVID를 자동 발급하고, 짧은 주기로 로테이션까지 처리한다. 워크로드는 사설키를 직접 들고 다닐 필요 없이 SPIRE 에이전트한테서 SVID를 받아 쓴다. 서비스 메시 중에는 내부적으로 이 SPIFFE 신원 체계를 그대로 쓰는 것들이 있다.

## 서비스 메시에서의 mTLS

내부 서비스가 수십 개일 때 각 서비스 코드에 mTLS 핸드셰이크와 인증서 로딩을 직접 넣는 건 현실적이지 않다. 서비스 메시는 이걸 사이드카 프록시로 빼낸다. 애플리케이션은 평문으로 통신한다고 생각하고, 옆에 붙은 프록시(Envoy 등)가 나가고 들어오는 트래픽을 가로채서 mTLS로 감싼다.

```mermaid
flowchart LR
    A[서비스 A] -->|평문| PA[사이드카 프록시 A]
    PA -->|mTLS| PB[사이드카 프록시 B]
    PB -->|평문| B[서비스 B]
```

서비스 코드는 mTLS를 전혀 몰라도 된다. 프록시 사이 구간만 암호화·상호인증된다. 애플리케이션과 사이드카는 같은 파드/호스트 안 localhost로 붙으니까 그 구간은 외부에 노출되지 않는다.

Istio는 이걸 기본으로 제공한다. PeerAuthentication 정책으로 mTLS 모드를 정한다.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: payment
spec:
  mtls:
    mode: STRICT
```

`STRICT`는 mTLS가 아닌 평문 연결을 전부 거부한다. `PERMISSIVE`는 평문과 mTLS를 둘 다 받는데, 이건 마이그레이션 중에만 쓰는 모드다. 기존 서비스를 메시에 점진적으로 넣을 때 일단 PERMISSIVE로 평문도 받다가, 전부 들어온 걸 확인하고 STRICT로 조인다. 처음부터 STRICT로 켜면 아직 사이드카가 안 붙은 서비스가 통신을 못 해서 장애가 난다.

Istio는 인증서 발급·로테이션을 istiod(컨트롤 플레인)가 자동으로 처리한다. 각 워크로드의 SPIFFE ID는 서비스 계정 기준으로 자동 생성된다. 그래서 운영자가 인증서를 직접 만들 일이 거의 없다. 권한 정책(AuthorizationPolicy)도 이 SPIFFE ID(principal)로 "payment 네임스페이스의 checkout만 order 서비스를 호출 가능" 같은 규칙을 건다.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: order-allow-checkout
  namespace: order
spec:
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/payment/sa/checkout-service"]
```

Linkerd도 비슷하게 동작하는데, mTLS가 기본으로 켜져 있고 설정이 더 단순한 편이다. Linkerd는 메시 안에 들어온 TCP 트래픽을 자동으로 mTLS로 감싸고, 인증서 로테이션(기본 24시간 주기)도 알아서 한다. Istio가 설정 표면이 넓고 세밀한 제어가 되는 대신 복잡하다면, Linkerd는 "켜면 그냥 된다"는 쪽이다. 다만 Linkerd는 트러스트 앵커(루트 CA)를 직접 갈아끼울 때 수동 단계가 있어서, CA 만료 전에 미리 교체하는 작업을 까먹으면 메시 전체가 죽는 사고가 난다. 트러스트 앵커 만료일은 캘린더에 박아두는 게 안전하다.

<div class="ygd-mesh-peerauth-permissive-vs-strict" id="ygd-mesh-peerauth-permissive-vs-strict">
<style>
.ygd-mesh-peerauth-permissive-vs-strict{--ygd-fg:#2b2826;--ygd-muted:#5c5650;--ygd-bg:#fbf9f7;--ygd-card:#ffffff;--ygd-pod:#f3efeb;--ygd-line:#cdc6be;--ygd-idle:#8c857d;--ygd-ok:#17713f;--ygd-plain:#9a5800;--ygd-bad:#b3261e;--ygd-accent:#3D7387;--ygd-onaccent:#ffffff;--ygd-tint:#e3eef2;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1.2em;margin-bottom:1.2em;box-sizing:border-box;padding:14px;border:1px solid var(--ygd-line);border-radius:10px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:15px;line-height:1.6;overflow:hidden}
body[data-md-color-scheme="slate"] .ygd-mesh-peerauth-permissive-vs-strict{--ygd-fg:#f0ede9;--ygd-muted:#b8b2aa;--ygd-bg:#262224;--ygd-card:#322d30;--ygd-pod:#2b2729;--ygd-line:#51494d;--ygd-idle:#8d867f;--ygd-ok:#5fd18e;--ygd-plain:#f2b45c;--ygd-bad:#ff8077;--ygd-accent:#7fb8cd;--ygd-onaccent:#10161a;--ygd-tint:#2f4650}
.ygd-mesh-peerauth-permissive-vs-strict *{box-sizing:border-box}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-ctrl{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 6px 0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-grp{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-glabel{font-size:14px;font-weight:600;color:var(--ygd-muted)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-btn{font-family:inherit;font-size:15px;line-height:1.2;min-height:44px;padding:6px 12px;margin:0;border-radius:8px;border:2px solid var(--ygd-line);background:var(--ygd-card);color:var(--ygd-fg);cursor:pointer}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-btn[aria-pressed="true"]{background:var(--ygd-tint);border-color:var(--ygd-accent);font-weight:700}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-play{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-onaccent);font-weight:700;min-width:96px}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-svg{display:block;width:100%;max-width:480px;height:auto;margin:8px auto 4px auto}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-t{fill:var(--ygd-fg);font-size:12.5px;font-family:inherit}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-tm{fill:var(--ygd-muted);font-size:12px;font-family:inherit}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-tp{fill:var(--ygd-muted);font-size:12px;font-weight:700;font-family:inherit}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-pod{fill:var(--ygd-pod);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-node{fill:var(--ygd-card);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-hot-ok{stroke:var(--ygd-ok);stroke-width:3}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-hot-plain{stroke:var(--ygd-plain);stroke-width:3}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-hot-bad{stroke:var(--ygd-bad);stroke-width:3}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-dim{opacity:.55}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-seg{fill:none;stroke-width:3}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-k-idle{stroke:var(--ygd-idle);stroke-width:2;stroke-dasharray:2 5}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-k-ok{stroke:var(--ygd-ok)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-k-plain{stroke:var(--ygd-plain);stroke-dasharray:7 5}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-k-bad{stroke:var(--ygd-bad)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-mk-idle{fill:var(--ygd-idle)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-mk-ok{fill:var(--ygd-ok)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-mk-plain{fill:var(--ygd-plain)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-mk-bad{fill:var(--ygd-bad)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-lbl{font-size:12.5px;font-weight:700;font-family:inherit;fill:var(--ygd-muted)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-lbl-ok{fill:var(--ygd-ok)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-lbl-plain{fill:var(--ygd-plain)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-lbl-bad{fill:var(--ygd-bad)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-pkt{stroke:var(--ygd-card);stroke-width:2}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-pk-ok{fill:var(--ygd-ok)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-pk-plain{fill:var(--ygd-plain)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-xc{fill:var(--ygd-bad)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-xl{stroke:#ffffff;stroke-width:2.5;stroke-linecap:round}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-hide{display:none}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-legend{display:flex;flex-wrap:wrap;gap:6px 16px;justify-content:center;font-size:14px;color:var(--ygd-muted);margin:0 0 10px 0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-sw{display:inline-block;width:28px;height:0;border-top:3px solid;vertical-align:middle;margin-right:6px}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-sw-ok{border-color:var(--ygd-ok)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-sw-plain{border-color:var(--ygd-plain);border-top-style:dashed}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-sw-bad{border-color:var(--ygd-bad);border-top-style:double;border-top-width:6px}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-panel{border:1px solid var(--ygd-line);border-left:5px solid var(--ygd-accent);border-radius:8px;background:var(--ygd-card);padding:10px 12px;margin:0 0 12px 0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-step{font-size:14px;font-weight:700;color:var(--ygd-accent);margin:0 0 2px 0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-desc{font-size:15px;line-height:1.6;margin:0;min-height:5.2em;color:var(--ygd-fg)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-table{width:100%;table-layout:fixed;border-collapse:collapse;margin:0 0 12px 0;font-size:14px;display:table;overflow:visible}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-table caption{caption-side:top;text-align:left;font-size:14px;font-weight:700;color:var(--ygd-muted);padding:0 0 4px 0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-table th,.ygd-mesh-peerauth-permissive-vs-strict .ygd-table td{border:1px solid var(--ygd-line);padding:6px;text-align:left;vertical-align:middle;font-size:14px;line-height:1.45;overflow-wrap:anywhere;color:var(--ygd-fg);background:var(--ygd-card);min-width:0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-table thead th{background:var(--ygd-pod);font-weight:700}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-table .ygd-c1{width:30%}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-table td.ygd-cur{background:var(--ygd-tint);outline:3px solid var(--ygd-accent);outline-offset:-3px;font-weight:700}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-mig{border-top:1px dashed var(--ygd-line);padding-top:10px}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-mig-t{font-size:15px;font-weight:700;margin:0 0 4px 0}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-ol{margin:0 0 8px 0;padding-left:1.5em;font-size:14.5px;line-height:1.6;list-style:decimal}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-ol li{margin:0 0 3px 0;padding:0;color:var(--ygd-fg)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-warn{font-size:14.5px;line-height:1.6;margin:0 0 8px 0;color:var(--ygd-fg)}
.ygd-mesh-peerauth-permissive-vs-strict .ygd-analogy{font-size:14px;line-height:1.6;margin:0;color:var(--ygd-muted)}
@media (min-width:520px){.ygd-mesh-peerauth-permissive-vs-strict .ygd-desc{min-height:3.4em}}
@media (max-width:480px){.ygd-mesh-peerauth-permissive-vs-strict .ygd-desc{min-height:9.6em}}
@media (prefers-reduced-motion:reduce){.ygd-mesh-peerauth-permissive-vs-strict *{transition:none !important;animation:none !important}}
</style>
<div class="ygd-ctrl">
<div class="ygd-grp" role="group" aria-label="PeerAuthentication mTLS 모드 선택"><span class="ygd-glabel">모드</span><button class="ygd-btn" type="button" data-mode="PERMISSIVE" aria-pressed="true">PERMISSIVE</button><button class="ygd-btn" type="button" data-mode="STRICT" aria-pressed="false">STRICT</button></div>
<div class="ygd-grp" role="group" aria-label="호출하는 서비스 선택"><span class="ygd-glabel">호출자</span><button class="ygd-btn" type="button" data-caller="A" aria-pressed="false">사이드카 있는 A</button><button class="ygd-btn" type="button" data-caller="C" aria-pressed="true">사이드카 없는 C</button></div>
<button class="ygd-btn ygd-play" type="button">재생</button>
</div>
<svg class="ygd-svg" viewBox="0 0 360 436" role="img" aria-label="서비스 A 또는 C가 서비스 B의 사이드카 프록시를 거쳐 호출하는 경로 다이어그램" focusable="false">
<defs>
<marker id="ygd-mesh-peerauth-permissive-vs-strict-arrow-idle" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" orient="auto"><path class="ygd-mk-idle" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-mesh-peerauth-permissive-vs-strict-arrow-ok" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" orient="auto"><path class="ygd-mk-ok" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-mesh-peerauth-permissive-vs-strict-arrow-plain" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" orient="auto"><path class="ygd-mk-plain" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-mesh-peerauth-permissive-vs-strict-arrow-bad" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" orient="auto"><path class="ygd-mk-bad" d="M0 0L10 5L0 10z"/></marker>
</defs>
<rect class="ygd-pod" x="8" y="250" width="344" height="178" rx="10"/>
<text class="ygd-tp" x="206" y="269" text-anchor="middle">서비스 B 파드 (사이드카 있음)</text>
<rect class="ygd-node" data-n="nPB" x="40" y="282" width="300" height="34" rx="6"/>
<text class="ygd-t" x="190" y="303" text-anchor="middle">사이드카 프록시 B</text>
<rect class="ygd-node" data-n="nB" x="110" y="372" width="160" height="34" rx="6"/>
<text class="ygd-t" x="190" y="393" text-anchor="middle">서비스 B (앱)</text>
<line class="ygd-seg ygd-k-idle" data-s="sB" x1="190" y1="316" x2="190" y2="372"/>
<text class="ygd-lbl" data-l="sB" x="198" y="349"></text>
<g class="ygd-own" data-o="A">
<rect class="ygd-pod" x="8" y="8" width="170" height="160" rx="10"/>
<text class="ygd-tp" x="18" y="26">사이드카 있는 파드</text>
<rect class="ygd-node" data-n="nAppA" x="22" y="38" width="142" height="32" rx="6"/>
<text class="ygd-t" x="93" y="58" text-anchor="middle">서비스 A (앱)</text>
<rect class="ygd-node" data-n="nPA" x="22" y="110" width="142" height="32" rx="6"/>
<text class="ygd-t" x="93" y="130" text-anchor="middle">사이드카 프록시 A</text>
<line class="ygd-seg ygd-k-idle" data-s="sAapp" x1="93" y1="70" x2="93" y2="110"/>
<line class="ygd-seg ygd-k-idle" data-s="sAnet" x1="93" y1="142" x2="93" y2="282"/>
<text class="ygd-lbl" data-l="sAapp" x="101" y="94"></text>
<text class="ygd-lbl" data-l="sAnet" x="101" y="214"></text>
</g>
<g class="ygd-own" data-o="C">
<rect class="ygd-pod" x="190" y="8" width="162" height="160" rx="10"/>
<text class="ygd-tp" x="200" y="26">사이드카 없는 파드</text>
<rect class="ygd-node" data-n="nAppC" x="202" y="38" width="138" height="32" rx="6"/>
<text class="ygd-t" x="271" y="58" text-anchor="middle">서비스 C (앱)</text>
<text class="ygd-tm" x="208" y="122">사이드카 없음</text>
<text class="ygd-tm" x="208" y="140">평문 그대로 전송</text>
<line class="ygd-seg ygd-k-idle" data-s="sCnet" x1="320" y1="70" x2="320" y2="282"/>
<text class="ygd-lbl" data-l="sCnet" x="312" y="214" text-anchor="end"></text>
</g>
<g class="ygd-xmark ygd-hide" transform="translate(320 282)"><circle class="ygd-xc" r="11"/><path class="ygd-xl" d="M-5 -5L5 5M5 -5L-5 5"/></g>
<circle class="ygd-pkt ygd-hide" r="6" cx="0" cy="0"/>
</svg>
<div class="ygd-legend"><span><span class="ygd-sw ygd-sw-ok"></span>mTLS</span><span><span class="ygd-sw ygd-sw-plain"></span>평문</span><span><span class="ygd-sw ygd-sw-bad"></span>거부 (X 표시)</span></div>
<div class="ygd-panel" aria-live="polite"><p class="ygd-step" data-r="step"></p><p class="ygd-desc" data-r="desc"></p></div>
<table class="ygd-table"><caption>호출자와 모드별 결과 (현재 선택 강조)</caption><thead><tr><th class="ygd-c1" scope="col">호출자</th><th scope="col">PERMISSIVE</th><th scope="col">STRICT</th></tr></thead><tbody>
<tr><th scope="row">사이드카 있음 (A)</th><td data-c="A" data-m="PERMISSIVE">통과 · 프록시 구간 mTLS</td><td data-c="A" data-m="STRICT">통과 · 프록시 구간 mTLS</td></tr>
<tr><th scope="row">사이드카 없음 (C)</th><td data-c="C" data-m="PERMISSIVE">통과 · 평문</td><td data-c="C" data-m="STRICT">거부</td></tr>
</tbody></table>
<div class="ygd-mig">
<p class="ygd-mig-t">마이그레이션 순서</p>
<ol class="ygd-ol"><li>PERMISSIVE로 시작한다. 평문과 mTLS를 둘 다 받으므로 사이드카가 없는 서비스의 기존 호출이 계속 통과한다.</li><li>서비스를 메시에 점진적으로 넣어 사이드카를 붙인다.</li><li>전부 들어온 것을 확인한 뒤 STRICT로 조인다.</li></ol>
<p class="ygd-warn">처음부터 STRICT로 켜면 아직 사이드카가 안 붙은 서비스가 통신을 못 해서 장애가 난다. 위에서 STRICT와 사이드카 없는 호출자를 고르면 그 장면이 나온다.</p>
<p class="ygd-analogy"><strong>비유</strong> 사옥 로비의 출입 게이트(사이드카 B)로 보면, PERMISSIVE는 사원증이 아직 다 배포되지 않은 기간에 사원증 없는 방문자도 들여보내는 상태이고 STRICT는 사원증(인증서) 없이는 돌려보내는 상태다. 사원증이 모두에게 가기 전에 게이트부터 잠그면 안 되는 이유와 같다. 다만 실제 판단 기준은 사원증 유무가 아니라 연결이 mTLS인지 여부다.</p>
</div>
<script>
(function(){
var root=document.getElementById('ygd-mesh-peerauth-permissive-vs-strict');
if(!root){return;}
function $(s){return root.querySelector(s);}
function $$(s){return Array.prototype.slice.call(root.querySelectorAll(s));}
var MK='ygd-mesh-peerauth-permissive-vs-strict-arrow-';
var svg=$('.ygd-svg'),pkt=$('.ygd-pkt'),xmark=$('.ygd-xmark'),titleEl=$('[data-r="step"]'),descEl=$('[data-r="desc"]'),playBtn=$('.ygd-play');
var segs={};
['sAapp','sAnet','sCnet','sB'].forEach(function(id){
var el=$('[data-s="'+id+'"]');
segs[id]={el:el,lbl:$('[data-l="'+id+'"]'),x1:+el.getAttribute('x1'),y1:+el.getAttribute('y1'),x2:+el.getAttribute('x2'),y2:+el.getAttribute('y2')};
});
var nodes=$$('[data-n]');
var owners=$$('[data-o]');
var state={mode:'PERMISSIVE',caller:'C',idx:-1};
var timer=null,raf=null;
var STEP_MS=4800,MOVE_MS=1200;
var mq=window.matchMedia?window.matchMedia('(prefers-reduced-motion: reduce)'):null;
function reduced(){return mq?mq.matches:false;}
var BASE_LABEL='서비스 A 또는 C가 서비스 B의 사이드카 프록시를 거쳐 호출하는 경로 다이어그램.';
function build(caller,mode){
if(caller==='A'){
return [
{seg:'sAapp',kind:'plain',label:'평문',hot:[['nAppA','plain'],['nPA','plain']],title:'단계 1/3 · 앱은 평문으로 호출',desc:'서비스 A는 mTLS를 모른 채 평문으로 요청을 보낸다. 같은 파드 안 localhost로 사이드카 A에 붙으므로 이 구간은 외부에 노출되지 않는다.'},
{seg:'sAnet',kind:'ok',label:'mTLS',hot:[['nPA','ok'],['nPB','ok']],title:'단계 2/3 · 사이드카 A가 mTLS로 감쌈',desc:'사이드카 A가 요청을 가로채 mTLS로 감싸 사이드카 B로 보낸다. 프록시 사이 구간만 암호화되고 서로 인증된다.'},
{seg:'sB',kind:'plain',label:'평문 (localhost)',hot:[['nPB','ok'],['nB','ok']],title:'단계 3/3 · 사이드카 B가 풀어서 전달',desc:'사이드카 B가 mTLS를 풀고 평문으로 서비스 B에 넘긴다. 이 요청은 mTLS 연결이라 모드와 관계없이 통과한다.'},
{seg:null,hot:[['nB','ok']],title:'결과 · 통과 (프록시 구간 mTLS)',desc:'사이드카가 붙은 서비스끼리는 PERMISSIVE와 STRICT 모두 같은 경로로 mTLS를 거쳐 통과한다. 모드 차이는 사이드카 없는 호출자에서 갈린다.'}
];
}
var send={seg:'sCnet',kind:'plain',label:'평문',hot:[['nAppC','plain']],title:'단계 1/2 · 평문 그대로 전송',desc:'서비스 C는 사이드카가 없어 평문을 그대로 보낸다. mTLS로 감싸 주는 프록시가 없기 때문이다.'};
if(mode==='PERMISSIVE'){
return [send,
{seg:'sB',kind:'plain',label:'평문 (localhost)',hot:[['nPB','plain'],['nB','plain']],title:'단계 2/2 · 사이드카 B가 평문도 수락',desc:'PERMISSIVE는 평문과 mTLS를 둘 다 받는다. 사이드카 B는 평문 요청을 그대로 서비스 B에 넘긴다.'},
{seg:null,hot:[['nB','plain']],title:'결과 · 통과 (평문)',desc:'호출은 성공하지만 이 구간은 mTLS가 아니다. 그래서 PERMISSIVE는 마이그레이션 중에만 쓰는 모드다.'}
];
}
return [send,
{seg:null,block:true,hot:[['nPB','bad']],title:'단계 2/2 · 사이드카 B가 거부',desc:'STRICT는 mTLS가 아닌 평문 연결을 전부 거부한다. 요청은 서비스 B에 닿지 못한다.'},
{seg:null,block:true,hot:[['nPB','bad']],title:'결과 · 거부',desc:'아직 사이드카를 못 붙인 서비스는 통신하지 못한다. 처음부터 STRICT로 켜면 이런 서비스에서 장애가 난다.'}
];
}
function cur(){return build(state.caller,state.mode);}
function hidePkt(){pkt.setAttribute('class','ygd-pkt ygd-hide');}
function stop(){
if(timer){clearTimeout(timer);timer=null;}
if(raf){cancelAnimationFrame(raf);raf=null;}
}
function render(i){
var steps=cur(),st=steps[i],kinds={},labels={},blocked=false,j,s;
for(j=0;i>=j;j++){
s=steps[j];
if(s.seg){kinds[s.seg]=s.kind;labels[s.seg]=s.label;}
if(s.block){blocked=true;}
}
Object.keys(segs).forEach(function(id){
var k=kinds[id]||'idle',g=segs[id];
g.el.setAttribute('class','ygd-seg ygd-k-'+k);
g.el.setAttribute('marker-end','url(#'+MK+k+')');
g.lbl.textContent=kinds[id]?labels[id]:'';
g.lbl.setAttribute('class','ygd-lbl ygd-lbl-'+k);
});
if(blocked){
segs.sCnet.lbl.textContent='평문 · 거부';
segs.sCnet.lbl.setAttribute('class','ygd-lbl ygd-lbl-bad');
}
xmark.setAttribute('class','ygd-xmark'+(blocked?'':' ygd-hide'));
nodes.forEach(function(n){n.setAttribute('class','ygd-node');});
st.hot.forEach(function(h){
var n=$('[data-n="'+h[0]+'"]');
if(n){n.setAttribute('class','ygd-node ygd-hot-'+h[1]);}
});
owners.forEach(function(g){
g.setAttribute('class','ygd-own'+(g.getAttribute('data-o')===state.caller?'':' ygd-dim'));
});
titleEl.textContent=st.title;
descEl.textContent=st.desc;
$$('td[data-c]').forEach(function(td){
var on=td.getAttribute('data-c')===state.caller;
if(on){on=td.getAttribute('data-m')===state.mode;}
td.setAttribute('class',on?'ygd-cur':'');
if(on){td.setAttribute('aria-current','true');}else{td.removeAttribute('aria-current');}
});
svg.setAttribute('aria-label',BASE_LABEL+' 현재 선택: '+(state.caller==='A'?'사이드카 있는 서비스 A':'사이드카 없는 서비스 C')+', '+state.mode+' 모드. '+steps[steps.length-1].title+'.');
}
function movePacket(st){
var g=segs[st.seg],t0=null;
if(reduced()){hidePkt();return;}
pkt.setAttribute('class','ygd-pkt ygd-pk-'+st.kind);
pkt.setAttribute('cx',g.x1);
pkt.setAttribute('cy',g.y1);
function frame(ts){
if(t0===null){t0=ts;}
var p=Math.min(1,(ts-t0)/MOVE_MS);
var e=p*(2-p);
pkt.setAttribute('cx',g.x1+(g.x2-g.x1)*e);
pkt.setAttribute('cy',g.y1+(g.y2-g.y1)*e);
if(p!==1){raf=requestAnimationFrame(frame);}else{raf=null;}
}
raf=requestAnimationFrame(frame);
}
function updateBtn(){
var last=cur().length-1,label;
if(reduced()){
label=(state.idx===-1||state.idx===last)?'단계별로 보기':'다음 단계';
}else if(state.idx===-1){
label='재생';
}else if(state.idx===last){
label='다시 재생';
}else{
label='처음부터 다시';
}
playBtn.textContent=label;
}
function showStep(i){
var steps=cur(),st=steps[i],last=steps.length-1;
stop();
state.idx=i;
render(i);
if(st.seg){movePacket(st);}else{hidePkt();}
if(!reduced()){
if(i!==last){
timer=setTimeout(function(){showStep(i+1);},STEP_MS);
}
}
updateBtn();
}
function reset(){
stop();
state.idx=-1;
render(cur().length-1);
hidePkt();
updateBtn();
}
playBtn.addEventListener('click',function(){
var last=cur().length-1;
if(reduced()){
if(state.idx===-1||state.idx===last){showStep(0);}else{showStep(state.idx+1);}
}else{
showStep(0);
}
});
$$('[data-mode]').forEach(function(b){
b.addEventListener('click',function(){
state.mode=b.getAttribute('data-mode');
$$('[data-mode]').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});
reset();
});
});
$$('[data-caller]').forEach(function(b){
b.addEventListener('click',function(){
state.caller=b.getAttribute('data-caller');
$$('[data-caller]').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});
reset();
});
});
if(mq){
if(mq.addEventListener){mq.addEventListener('change',function(){reset();});}
}
reset();
})();
</script>
</div>

## 제로트러스트에서의 위치

제로트러스트는 "내부망이니까 믿는다"를 버리는 모델이다. 네트워크 경계 안에 있다는 사실만으로는 아무것도 신뢰하지 않고, 모든 요청을 그 요청자의 신원으로 검증한다. 전통적인 모델은 방화벽 안쪽을 신뢰 구역으로 봤지만, 한 번 내부로 침투당하면 측면 이동(lateral movement)을 막을 수 없다는 게 문제였다.

mTLS는 제로트러스트에서 서비스 간(workload-to-workload) 인증을 담당한다. 사람의 인증은 OIDC 토큰 같은 걸로 하지만, 서비스끼리는 사람이 없으니까 인증서가 신원이 된다. 모든 서비스 호출이 양방향 인증서 검증을 거치면, 침투한 공격자가 다른 서비스로 옮겨가려 해도 유효한 클라이언트 인증서가 없으면 막힌다. 평문 트래픽 자체를 거부하므로 내부망 스니핑도 무력화된다.

여기서 mTLS는 신원 증명(authentication)까지만 한다. "이 서비스가 누구다"는 확인하지만, "이 서비스가 저 API를 호출할 권한이 있나"는 인가(authorization) 정책의 몫이다. 그래서 mTLS만 켜고 인가 정책을 안 짜면, 메시 안의 모든 서비스가 서로를 자유롭게 호출할 수 있는 상태가 된다. 신원은 분명한데 권한 통제가 없는 셈이다. SPIFFE ID나 인증서 신원을 기준으로 최소 권한 정책을 같이 걸어야 제로트러스트가 완성된다.

## Nginx 설정 예제

Nginx로 mTLS를 거는 건 지시어 몇 개면 된다. 클라이언트 인증서를 검증할 CA를 지정하고, 검증을 강제하면 된다.

```nginx
server {
    listen 443 ssl;
    server_name api.internal;

    # 서버 인증서 (단방향 TLS와 동일)
    ssl_certificate     /etc/nginx/certs/server-fullchain.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    # 클라이언트 인증서를 검증할 CA 체인
    ssl_client_certificate /etc/nginx/certs/client-ca-chain.crt;

    # on: 반드시 유효한 클라이언트 인증서 요구
    # optional: 있으면 검증, 없어도 통과 (애플리케이션에서 분기)
    ssl_verify_client on;

    # 체인 깊이 (중간 CA가 있으면 2 이상으로)
    ssl_verify_depth 2;

    location / {
        # 검증 결과와 클라이언트 신원을 백엔드로 전달
        proxy_set_header X-Client-Verify  $ssl_client_verify;
        proxy_set_header X-Client-Subject $ssl_client_s_dn;
        proxy_pass http://backend;
    }
}
```

`ssl_verify_client on`이면 유효한 클라이언트 인증서 없이는 핸드셰이크가 거부된다. `$ssl_client_verify`는 검증 결과(`SUCCESS`, `FAILED`, `NONE`)를 담고, `$ssl_client_s_dn`은 클라이언트 인증서의 Subject DN을 담는다. 이걸 헤더로 백엔드에 넘기면 애플리케이션이 "어느 클라이언트가 들어왔는지"를 알 수 있다.

주의할 점이 있다. `ssl_verify_client on`은 CA 체인이 맞는지까지만 본다. 즉 그 CA로 발급된 인증서면 누구든 통과한다. 특정 클라이언트만 허용하려면 `$ssl_client_s_dn`이나 SAN을 보고 추가로 걸러야 한다. `optional`로 두고 애플리케이션에서 신원별로 분기하거나, Nginx map 지시어로 허용 목록을 만드는 식이다.

```nginx
# 허용된 클라이언트 DN만 통과
map $ssl_client_s_dn $allowed {
    default                              0;
    "CN=checkout,O=payment"             1;
    "CN=order,O=fulfillment"            1;
}

server {
    # ...
    location / {
        if ($allowed = 0) { return 403; }
        proxy_pass http://backend;
    }
}
```

## Envoy 설정 예제

Envoy는 서비스 메시에서 쓰지만 단독으로도 mTLS를 건다. 리스너의 transport_socket에 양방향 검증을 설정한다.

```yaml
transport_socket:
  name: envoy.transport_sockets.tls
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
    require_client_certificate: true
    common_tls_context:
      tls_certificates:
        - certificate_chain: { filename: "/certs/server-fullchain.crt" }
          private_key:       { filename: "/certs/server.key" }
      validation_context:
        trusted_ca: { filename: "/certs/client-ca-chain.crt" }
        # SAN으로 허용 클라이언트 신원 제한
        match_typed_subject_alt_names:
          - san_type: URI
            matcher:
              prefix: "spiffe://example.org/ns/payment/"
```

`require_client_certificate: true`가 mTLS를 켜는 부분이고, `trusted_ca`로 클라이언트 인증서를 검증할 CA를 준다. `match_typed_subject_alt_names`가 Nginx에 없던 강점인데, SAN의 URI(SPIFFE ID)를 prefix로 매칭해서 "payment 네임스페이스 워크로드만 허용" 같은 신원 제한을 TLS 계층에서 바로 건다. 애플리케이션까지 안 가고 프록시가 거른다.

운영 환경에서는 인증서를 파일로 박지 않고 SDS로 받는다. 그래야 인증서가 로테이션될 때 Envoy 재시작 없이 갱신된다. 파일 기반은 로테이션마다 reload가 필요해서, 짧은 주기 로테이션과 안 맞는다.

## 트러블슈팅

mTLS에서 핸드셰이크가 깨지는 원인은 거의 정해져 있다. 증상별로 정리한다.

### 인증서 만료

가장 흔하다. `certificate has expired` 또는 `certificate is not yet valid`가 로그에 찍힌다. 후자는 인증서 시작 시각이 미래인 경우인데, 보통 서버 간 시계가 안 맞아서(NTP 미동기화) 생긴다. 인증서는 유효 기간(notBefore ~ notAfter)을 절대 시각으로 박기 때문에, 검증하는 쪽 시계가 틀어지면 멀쩡한 인증서도 거부된다.

```bash
# 인증서 유효기간 확인
openssl x509 -in client.crt -noout -dates

# 남은 일수만 빠르게 보기
openssl x509 -in client.crt -noout -enddate
```

짧은 주기 로테이션을 쓰는데 갱신 파이프라인이 멈추면, 며칠 안에 전 서비스가 동시에 만료되는 사고로 번진다. 만료 임박 인증서를 모니터링으로 사전에 알람 거는 게 필수다.

### CN/SAN 불일치

서버 인증서 검증에서 나는 문제다. 클라이언트가 `api.internal`로 접속했는데 서버 인증서의 SAN에 `api.internal`이 없으면 거부된다. 에러는 보통 이렇게 찍힌다.

```
x509: certificate is valid for api-internal, not api.internal
```

요즘 라이브러리(Go 1.15+, 최신 브라우저)는 CN을 아예 안 보고 SAN만 본다. 그래서 인증서에 CN만 넣고 SAN을 빼면, openssl로는 통과해도 실제 서비스에서는 깨진다. "예전엔 됐는데 라이브러리 업데이트하니까 안 된다"는 거의 이 케이스다. 인증서 발급할 때 SAN을 반드시 채워야 한다.

```bash
# 인증서에 박힌 SAN 확인
openssl x509 -in server.crt -noout -ext subjectAltName
```

mTLS에서는 반대 방향도 같다. 서버가 클라이언트 인증서의 SAN(SPIFFE ID 등)으로 신원을 거는데, 클라이언트 인증서 SAN이 정책과 안 맞으면 서버가 핸드셰이크를 끊는다. 이때 클라이언트는 "연결이 그냥 리셋됐다"고만 보이고 이유를 모를 수 있으니, 서버 쪽 로그를 봐야 원인이 나온다.

### 클라이언트 인증서를 안 보냄

서버는 `require_client_certificate`로 인증서를 요구하는데 클라이언트가 안 보내면, 서버가 핸드셰이크를 끊는다. 클라이언트 쪽에선 `tls: certificate required` 또는 그냥 연결 종료로 보인다. curl이면 `--cert`, `--key` 옵션을 빠뜨린 경우다.

```bash
# 클라이언트 인증서를 들고 호출
curl https://api.internal/health \
  --cert client.crt --key client.key \
  --cacert ca-chain.crt
```

`--cacert`까지 줘야 서버 인증서를 검증할 수 있다. 사설 CA라서 시스템 신뢰 저장소에 없기 때문이다. 이걸 빼면 `unable to verify the first certificate`가 난다.

### 체인 검증 실패

`unable to get local issuer certificate`는 중간 CA가 빠진 것이다. 앞서 말한 풀체인 문제다. 서버가 leaf만 보내거나, 검증하는 쪽 `trusted_ca`/`ssl_client_certificate`에 중간 CA가 없으면 난다. 한쪽 끝(leaf)에서 루트까지 연결이 끊기지 않게 체인을 다 갖춰야 한다.

체인을 확인하려면 `openssl s_client`의 출력에서 인증서가 몇 개 오는지 본다. leaf 하나만 오면 중간 CA가 빠진 것이다.

```bash
openssl s_client -connect api.internal:443 -showcerts </dev/null 2>/dev/null \
  | grep -c "BEGIN CERTIFICATE"
```

### 암호 스위트/프로토콜 불일치

`no shared cipher`나 `handshake failure`가 나면 클라이언트와 서버가 합의할 수 있는 암호 스위트나 TLS 버전이 없는 경우다. 한쪽이 TLS 1.3만 받게 설정됐는데 다른 쪽이 1.2까지만 지원하면 난다. 보안 강화한다고 서버 쪽 허용 버전을 좁혔다가 구형 클라이언트를 끊어먹는 일이 있다. 어느 버전·스위트로 연결되는지 확인하려면 다음으로 본다.

```bash
openssl s_client -connect api.internal:443 \
  -cert client.crt -key client.key </dev/null 2>/dev/null \
  | grep -E "Protocol|Cipher"
```

핸드셰이크 문제는 양쪽 로그를 같이 봐야 한다. 클라이언트 로그만 보면 "연결이 끊겼다"는 것밖에 안 나오고, 진짜 거부 이유는 서버 쪽에 찍히는 경우가 대부분이다. mTLS 디버깅의 절반은 "어느 쪽이 끊었는가"를 먼저 가리는 일이다.
