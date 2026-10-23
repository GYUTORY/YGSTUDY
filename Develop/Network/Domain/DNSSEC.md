---
title: DNSSEC (DNS Security Extensions)
tags: [network, architecture, dns, security]
updated: 2026-10-23
---

# DNSSEC (DNS Security Extensions)

## 무엇을 막으려고 만든 건가

DNS는 처음 설계될 때 무결성 검증이라는 개념이 없었다. 리졸버가 권한 서버에 질의를 던지고 응답을 받으면, 그 응답이 진짜 권한 서버가 보낸 건지 확인할 방법이 없다. UDP 53번에 출발지 IP만 맞고 질의 ID(16비트)와 포트만 맞으면 그냥 받아서 캐시에 넣는다.

여기서 캐시 포이즈닝이 나온다. 공격자가 리졸버보다 먼저 가짜 응답을 보내서 캐시에 심으면, 그 도메인을 묻는 모든 사용자가 공격자가 정한 IP로 간다. 2008년 Dan Kaminsky가 발표한 공격이 이 문제를 제대로 드러냈다. 질의 ID가 16비트(65536개)뿐이라 추측 가능하고, 서브도메인을 마구 질의시켜 가짜 NS 응답을 끼워넣으면 도메인 전체를 탈취할 수 있었다.

당시 대응은 출발지 포트 랜덤화였다. 질의 ID 16비트에 포트 16비트를 더해 추측 공간을 32비트로 키운 것이다. 근본 해결은 아니다. 시간과 대역폭만 충분하면 여전히 뚫린다. DNSSEC는 여기에 암호 서명을 붙여서 "이 레코드는 진짜 권한 서버가 서명한 값"이라는 걸 리졸버가 검증하게 만든다.

한 가지 분명히 해야 할 게 있다. DNSSEC는 응답의 무결성과 출처를 보장하지, 기밀성을 보장하지 않는다. 질의 내용은 여전히 평문으로 오간다. 도청을 막고 싶으면 [DNS over HTTPS / DoT](DNS_over_HTTPS_Do_H.md)가 풀어야 할 영역이고, DNSSEC와는 푸는 문제가 다르다. 둘은 경쟁 관계가 아니라 같이 쓰는 보완 관계다.

<div class="ygd-dns-poison" id="ygd-dns-poison" data-mode="0">
<style>
.ygd-dns-poison{--ygd-bg:#f7f6f4;--ygd-box:#ffffff;--ygd-text:#2b2825;--ygd-sub:#5f5a54;--ygd-line:#3d7387;--ygd-bad:#b3261e;--ygd-badbg:#fbe9e7;--ygd-good:#1b6e3c;--ygd-goodbg:#e3f3e9;--ygd-btn:#3d7387;--ygd-btntext:#ffffff;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1em;margin-bottom:1em;padding:12px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-text);box-sizing:border-box}
body[data-md-color-scheme="slate"] .ygd-dns-poison{--ygd-bg:#26232a;--ygd-box:#322f36;--ygd-text:#f0ede9;--ygd-sub:#c4bfb8;--ygd-line:#7fb6cb;--ygd-bad:#ff8a80;--ygd-badbg:#4a2a2a;--ygd-good:#7fd69b;--ygd-goodbg:#243a2d;--ygd-btn:#7fb6cb;--ygd-btntext:#1b1a1c}
.ygd-dns-poison .ygd-tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.ygd-dns-poison .ygd-tab,.ygd-dns-poison .ygd-btn{font-size:14px;line-height:1.3;min-height:40px;padding:6px 12px;border:1px solid var(--ygd-line);border-radius:6px;background:var(--ygd-box);color:var(--ygd-text);cursor:pointer;font-family:inherit}
.ygd-dns-poison .ygd-tab[aria-pressed="true"],.ygd-dns-poison .ygd-btn.ygd-primary{background:var(--ygd-btn);color:var(--ygd-btntext)}
.ygd-dns-poison .ygd-tab:focus-visible,.ygd-dns-poison .ygd-btn:focus-visible{outline:3px solid var(--ygd-text);outline-offset:2px}
.ygd-dns-poison .ygd-svg{display:block;width:100%;height:auto}
.ygd-dns-poison .ygd-t{fill:var(--ygd-text);font-size:12px}
.ygd-dns-poison .ygd-ts{fill:var(--ygd-sub);font-size:12px}
.ygd-dns-poison .ygd-actor{fill:var(--ygd-box);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-dns-poison .ygd-life{stroke:var(--ygd-sub);stroke-width:1;stroke-dasharray:4 4}
.ygd-dns-poison .ygd-arrow{stroke:var(--ygd-line);stroke-width:2;fill:none}
.ygd-dns-poison .ygd-arrow.ygd-evil{stroke:var(--ygd-bad)}
.ygd-dns-poison .ygd-ah{fill:var(--ygd-line)}
.ygd-dns-poison .ygd-ahb{fill:var(--ygd-bad)}
.ygd-dns-poison .ygd-res{stroke-width:1.5}
.ygd-dns-poison .ygd-m0 .ygd-res{fill:var(--ygd-badbg);stroke:var(--ygd-bad)}
.ygd-dns-poison .ygd-m1 .ygd-res{fill:var(--ygd-goodbg);stroke:var(--ygd-good)}
.ygd-dns-poison[data-mode="0"] .ygd-m1{display:none}
.ygd-dns-poison[data-mode="1"] .ygd-m0{display:none}
.ygd-dns-poison .ygd-off{opacity:0.45}
.ygd-dns-poison .ygd-on{opacity:1}
.ygd-dns-poison .ygd-step{transition:opacity .4s}
.ygd-dns-poison .ygd-desc{margin-top:8px;padding:10px 12px;min-height:4.2em;font-size:14px;line-height:1.6;background:var(--ygd-box);border-left:4px solid var(--ygd-line);border-radius:4px;color:var(--ygd-text)}
.ygd-dns-poison .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ygd-dns-poison .ygd-note{margin-top:8px;font-size:14px;line-height:1.5;color:var(--ygd-sub)}
@media (prefers-reduced-motion: reduce){.ygd-dns-poison .ygd-step{transition:none}}
</style>
<div class="ygd-tabs" role="group" aria-label="DNSSEC 적용 여부 선택">
<button type="button" class="ygd-tab" data-mode="0" aria-pressed="true">DNSSEC 없음</button>
<button type="button" class="ygd-tab" data-mode="1" aria-pressed="false">DNSSEC 검증</button>
</div>
<svg class="ygd-svg" viewBox="0 0 400 240" role="img" aria-label="공격자, 리졸버, 권한 서버 사이에서 가짜 응답이 캐시에 들어가는 경우와 DNSSEC 검증으로 폐기되는 경우를 비교하는 시퀀스 다이어그램">
<defs>
<marker id="ygd-dp-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path class="ygd-ah" d="M0 0 L10 5 L0 10 z"/></marker>
<marker id="ygd-dp-ab" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path class="ygd-ahb" d="M0 0 L10 5 L0 10 z"/></marker>
</defs>
<line class="ygd-life" x1="60" y1="40" x2="60" y2="176"/>
<line class="ygd-life" x1="200" y1="40" x2="200" y2="176"/>
<line class="ygd-life" x1="340" y1="40" x2="340" y2="176"/>
<rect class="ygd-actor" x="10" y="8" width="100" height="32" rx="6"/>
<text class="ygd-t" x="60" y="29" text-anchor="middle">공격자</text>
<rect class="ygd-actor" x="150" y="8" width="100" height="32" rx="6"/>
<text class="ygd-t" x="200" y="29" text-anchor="middle">리졸버</text>
<rect class="ygd-actor" x="290" y="8" width="100" height="32" rx="6"/>
<text class="ygd-t" x="340" y="29" text-anchor="middle">권한 서버</text>
<g class="ygd-step ygd-off" data-s="1">
<line class="ygd-arrow" x1="204" y1="72" x2="334" y2="72" marker-end="url(#ygd-dp-ah)"/>
<text class="ygd-t" x="270" y="62" text-anchor="middle">1 질의 전송</text>
</g>
<g class="ygd-step ygd-off" data-s="2">
<line class="ygd-arrow ygd-evil" x1="64" y1="114" x2="194" y2="114" marker-end="url(#ygd-dp-ab)"/>
<text class="ygd-t" x="130" y="104" text-anchor="middle">2 가짜 응답</text>
</g>
<g class="ygd-step ygd-off" data-s="3">
<line class="ygd-arrow" x1="336" y1="156" x2="206" y2="156" marker-end="url(#ygd-dp-ah)"/>
<text class="ygd-t" x="270" y="146" text-anchor="middle">3 진짜 응답</text>
</g>
<g class="ygd-step ygd-off" data-s="4">
<g class="ygd-m0">
<rect class="ygd-res" x="10" y="188" width="380" height="44" rx="6"/>
<text class="ygd-t" x="200" y="215" text-anchor="middle">가짜 응답이 캐시에 저장된다</text>
</g>
<g class="ygd-m1">
<rect class="ygd-res" x="10" y="188" width="380" height="44" rx="6"/>
<text class="ygd-t" x="200" y="215" text-anchor="middle">RRSIG 검증 실패, 가짜 응답 폐기</text>
</g>
</g>
</svg>
<div class="ygd-desc" aria-live="polite"></div>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전 단계</button>
<button type="button" class="ygd-btn" data-act="next">다음 단계</button>
</div>
<div class="ygd-note">비유: 아무나 쓸 수 있는 엽서와 발신인의 인장이 찍힌 공문서의 차이다. 인장은 위조 여부를 가려 줄 뿐 내용을 가려 주지는 않는다.</div>
<script>
(function(){
var root=document.getElementById('ygd-dns-poison');
if(!root){return;}
var D=[
["DNSSEC이 없으면 리졸버는 응답이 진짜인지 확인할 방법이 없다. 재생을 눌러 질의부터 따라가 본다.",
"리졸버가 권한 서버에 질의를 보내고 응답을 기다린다. 이 대기 시간이 공격자에게는 끼어들 틈이다.",
"공격자가 리졸버보다 먼저 가짜 응답을 보낸다. 출발지 IP와 질의 ID, 포트만 맞으면 리졸버는 그대로 받아들인다.",
"진짜 응답은 가짜 응답보다 늦게 도착한다.",
"가짜 응답이 캐시에 들어간다. 그 도메인을 묻는 모든 사용자가 공격자가 정한 IP로 가게 된다."],
["DNSSEC 검증을 하는 리졸버는 응답에 붙은 서명을 확인한다. 재생을 눌러 같은 상황을 따라가 본다.",
"리졸버가 DO 비트를 세워 질의를 보낸다. 권한 서버가 RRSIG 같은 서명 레코드를 응답에 실어 줄 수 있게 하기 위해서다.",
"공격자가 가짜 응답을 먼저 보낸다. 하지만 zone의 개인키가 없으니 유효한 RRSIG를 만들 수 없다.",
"진짜 응답은 RRSIG와 함께 도착한다.",
"리졸버가 루트 신뢰 앵커부터 이어진 체인으로 서명을 검증한다. 검증에 실패한 응답은 버려진다. 다만 DNSSEC는 무결성을 보장할 뿐 질의 내용을 숨겨 주지는 않는다."]
];
var mode=0,step=0,timer=null;
var reduce=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
var desc=root.querySelector('.ygd-desc');
var els=root.querySelectorAll('[data-s]');
var tabs=root.querySelectorAll('.ygd-tab');
var playBtn=root.querySelector('[data-act="play"]');
function stop(){if(timer){clearInterval(timer);timer=null;}playBtn.textContent='재생';}
function render(){
root.setAttribute('data-mode',String(mode));
Array.prototype.forEach.call(els,function(e){
var s=parseInt(e.getAttribute('data-s'),10);
e.setAttribute('class','ygd-step '+(s<=step?'ygd-on':'ygd-off'));
});
desc.textContent=D[mode][step];
Array.prototype.forEach.call(tabs,function(t){
t.setAttribute('aria-pressed',String(parseInt(t.getAttribute('data-mode'),10)===mode));
});
}
Array.prototype.forEach.call(tabs,function(t){
t.addEventListener('click',function(){stop();mode=parseInt(t.getAttribute('data-mode'),10);step=0;render();});
});
playBtn.addEventListener('click',function(){
if(timer){stop();return;}
if(step>=4){step=0;}
if(reduce){step=4;render();return;}
step=Math.max(step,0);
step+=1;render();
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(step>=4){stop();return;}
step+=1;render();
if(step>=4){stop();}
},1800);
});
root.querySelector('[data-act="prev"]').addEventListener('click',function(){stop();if(step>0){step-=1;}render();});
root.querySelector('[data-act="next"]').addEventListener('click',function(){stop();if(step<4){step+=1;}render();});
render();
})();
</script>
</div>

## 서명은 어떻게 붙는가

DNSSEC의 출발점은 RRset이다. 같은 이름·같은 타입의 레코드 묶음을 하나로 본다. `example.com`의 A 레코드가 3개면 그 3개가 하나의 RRset이다. 서명은 개별 레코드가 아니라 RRset 단위로 건다.

### RRSIG — 서명 그 자체

RRset마다 RRSIG 레코드가 따라붙는다. RRSIG는 해당 RRset을 개인키로 서명한 결과값이다. A 레코드를 질의하면 A RRset과 그에 대한 RRSIG가 같이 온다.

```
example.com.   3600  IN  A      93.184.216.34
example.com.   3600  IN  RRSIG  A 13 2 3600 (
                                 20260701000000 20260621000000 12345
                                 example.com.
                                 oP8j...서명값... )
```

RRSIG 안에는 서명 대상 타입(A), 알고리즘 번호(13 = ECDSA P-256), 서명 만료/시작 시각, 키 태그(12345), 서명자 이름, 그리고 실제 서명 바이트가 들어간다. 만료 시각이 있다는 게 중요하다. 서명에는 유효기간이 있고, 기간이 지나면 리졸버가 검증에 실패한다. 뒤에 나올 SERVFAIL 트러블슈팅의 절반이 여기서 나온다.

### DNSKEY — 검증용 공개키

RRSIG를 검증하려면 공개키가 필요하다. 그 공개키가 DNSKEY 레코드로 zone 안에 들어 있다. 리졸버는 DNSKEY를 가져와서 RRSIG를 검증한다.

문제는 "그 DNSKEY 자체가 진짜냐"다. zone 안에 들어 있는 공개키를 그냥 믿으면, 공격자가 가짜 zone을 통째로 만들어서 가짜 DNSKEY와 가짜 RRSIG를 같이 보내면 검증이 통과한다. 그래서 키를 두 종류로 나눈다.

- KSK (Key Signing Key): DNSKEY RRset만 서명한다. zone의 신뢰 앵커 역할.
- ZSK (Zone Signing Key): 실제 데이터 RRset(A, MX, TXT 등)을 서명한다.

KSK로 DNSKEY를 서명하고, ZSK로 일반 레코드를 서명한다. 왜 나누냐면 운영 때문이다. ZSK는 자주 바꿔야 안전한데(노출 위험), ZSK를 바꿀 때마다 상위 zone에 등록된 정보를 갱신해야 하면 너무 번거롭다. 그래서 상위에는 KSK 정보만 등록하고, ZSK는 KSK 밑에서 자유롭게 교체한다.

### DS — 상위 zone이 보증하는 지문

KSK가 진짜라는 걸 누가 보증하나. 상위 zone이다. `example.com`의 KSK 해시를 `.com` zone에 DS(Delegation Signer) 레코드로 등록한다. DS는 자식 zone KSK의 해시값이다.

```
example.com.  86400  IN  DS  12345 13 2 (
                              49FD...KSK의 SHA-256 해시... )
```

이 DS 레코드는 `.com` zone에 들어 있고, `.com`의 ZSK로 서명된다. 그러면 리졸버는 `.com`을 신뢰하는 한 그 안의 DS를 믿고, DS가 가리키는 `example.com`의 KSK를 믿게 된다. 이게 신뢰가 위에서 아래로 흐르는 구조다.

## 신뢰 사슬

전체 그림은 루트에서 시작한다.

```
flowchart TD
    Root["루트 zone (.)<br/>신뢰 앵커: 루트 KSK"]
    TLD[".com zone<br/>DNSKEY (KSK/ZSK)"]
    Auth["example.com zone<br/>DNSKEY (KSK/ZSK)"]
    Data["A / MX / TXT RRset"]

    Root -->|"DS(.com)를 루트 ZSK로 서명"| TLD
    TLD -->|"DS(example.com)를 .com ZSK로 서명"| Auth
    Auth -->|"DNSKEY를 KSK로 서명"| Data
    Auth -->|"데이터를 ZSK로 서명 (RRSIG)"| Data
```

리졸버는 루트의 공개키를 미리 알고 있다. 이게 신뢰 앵커(trust anchor)다. 루트 KSK는 코드에 박혀 있거나 설정 파일로 배포된다. 리졸버 입장에서 검증의 출발점은 항상 이 루트 키다.

검증은 위에서 아래로 한 칸씩 내려온다.

1. 루트 KSK(신뢰 앵커)로 루트 DNSKEY RRset을 검증한다.
2. 검증된 루트 ZSK로 `.com`의 DS RRset을 검증한다.
3. `.com`의 DS 해시가 `.com` KSK와 일치하는지 본다 → `.com` DNSKEY 검증.
4. `.com` ZSK로 `example.com`의 DS를 검증한다.
5. `example.com`의 DS 해시가 그 zone KSK와 맞는지 본다 → `example.com` DNSKEY 검증.
6. `example.com` ZSK로 실제 A 레코드의 RRSIG를 검증한다.

한 칸이라도 끊기면 그 아래 전부가 검증 불가다. `.com`은 DS가 있는데 `example.com`에 DS가 없으면, 거기서 신뢰 사슬이 끊겨서 `example.com`은 unsigned로 취급된다. 이건 정상 동작이다. 모든 zone이 DNSSEC를 쓰는 게 아니라서, DS가 없으면 "이 zone은 서명 안 함"으로 보고 검증 없이 통과시킨다.

진짜 문제는 DS는 있는데 서명이 안 맞을 때다. "서명한다고 했는데 검증 실패" 상황이고, 이때 리졸버는 응답을 버리고 SERVFAIL을 던진다. 끊긴 게 아니라 깨진 거라서 막아버린다.

<div class="ygd-dnssec-chain" id="ygd-dnssec-chain" data-mode="0">
<style>
.ygd-dnssec-chain{--ygd-bg:#f7f6f4;--ygd-box:#ffffff;--ygd-text:#2b2825;--ygd-sub:#5f5a54;--ygd-line:#3d7387;--ygd-bad:#b3261e;--ygd-badbg:#fbe9e7;--ygd-good:#1b6e3c;--ygd-goodbg:#e3f3e9;--ygd-grey:#6b665f;--ygd-greybg:#ecebe8;--ygd-btn:#3d7387;--ygd-btntext:#ffffff;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1em;margin-bottom:1em;padding:12px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-text);box-sizing:border-box}
body[data-md-color-scheme="slate"] .ygd-dnssec-chain{--ygd-bg:#26232a;--ygd-box:#322f36;--ygd-text:#f0ede9;--ygd-sub:#c4bfb8;--ygd-line:#7fb6cb;--ygd-bad:#ff8a80;--ygd-badbg:#4a2a2a;--ygd-good:#7fd69b;--ygd-goodbg:#243a2d;--ygd-grey:#b5b0a8;--ygd-greybg:#3a373d;--ygd-btn:#7fb6cb;--ygd-btntext:#1b1a1c}
.ygd-dnssec-chain .ygd-tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.ygd-dnssec-chain .ygd-tab,.ygd-dnssec-chain .ygd-btn{font-size:14px;line-height:1.3;min-height:40px;padding:6px 12px;border:1px solid var(--ygd-line);border-radius:6px;background:var(--ygd-box);color:var(--ygd-text);cursor:pointer;font-family:inherit}
.ygd-dnssec-chain .ygd-tab[aria-pressed="true"],.ygd-dnssec-chain .ygd-btn.ygd-primary{background:var(--ygd-btn);color:var(--ygd-btntext)}
.ygd-dnssec-chain .ygd-tab:focus-visible,.ygd-dnssec-chain .ygd-btn:focus-visible{outline:3px solid var(--ygd-text);outline-offset:2px}
.ygd-dnssec-chain .ygd-svg{display:block;width:100%;height:auto}
.ygd-dnssec-chain .ygd-t{fill:var(--ygd-text);font-size:12px}
.ygd-dnssec-chain .ygd-ts{fill:var(--ygd-sub);font-size:12px}
.ygd-dnssec-chain .ygd-node{fill:var(--ygd-box);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-dnssec-chain .ygd-st-ok .ygd-node{fill:var(--ygd-goodbg);stroke:var(--ygd-good)}
.ygd-dnssec-chain .ygd-st-fail .ygd-node{fill:var(--ygd-badbg);stroke:var(--ygd-bad)}
.ygd-dnssec-chain .ygd-st-skip .ygd-node{fill:var(--ygd-greybg);stroke:var(--ygd-grey);stroke-dasharray:5 3}
.ygd-dnssec-chain .ygd-arrow{stroke:var(--ygd-line);stroke-width:2;fill:none}
.ygd-dnssec-chain .ygd-ah{fill:var(--ygd-line)}
.ygd-dnssec-chain .ygd-ann.ygd-fail .ygd-t{fill:var(--ygd-bad)}
.ygd-dnssec-chain .ygd-ann.ygd-skip .ygd-t{fill:var(--ygd-grey)}
.ygd-dnssec-chain .ygd-off{opacity:0.45}
.ygd-dnssec-chain .ygd-on{opacity:1}
.ygd-dnssec-chain .ygd-step{transition:opacity .4s}
.ygd-dnssec-chain .ygd-desc{margin-top:8px;padding:10px 12px;min-height:4.8em;font-size:14px;line-height:1.6;background:var(--ygd-box);border-left:4px solid var(--ygd-line);border-radius:4px;color:var(--ygd-text)}
.ygd-dnssec-chain .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ygd-dnssec-chain .ygd-note{margin-top:8px;font-size:14px;line-height:1.5;color:var(--ygd-sub)}
@media (prefers-reduced-motion: reduce){.ygd-dnssec-chain .ygd-step{transition:none}}
</style>
<div class="ygd-tabs" role="group" aria-label="신뢰 사슬 시나리오 선택">
<button type="button" class="ygd-tab" data-mode="0" aria-pressed="true">정상</button>
<button type="button" class="ygd-tab" data-mode="1" aria-pressed="false">DS 없음 (unsigned)</button>
<button type="button" class="ygd-tab" data-mode="2" aria-pressed="false">DS 불일치</button>
</div>
<svg class="ygd-svg" viewBox="0 0 400 334" role="img" aria-label="루트 zone에서 com zone, example.com zone, A 레코드까지 신뢰가 한 칸씩 내려가며 검증되는 6단계 신뢰 사슬 다이어그램">
<defs>
<marker id="ygd-dc-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path class="ygd-ah" d="M0 0 L10 5 L0 10 z"/></marker>
</defs>
<g class="ygd-box" data-box="0">
<rect class="ygd-node" x="10" y="10" width="150" height="44" rx="6"/>
<text class="ygd-t" x="85" y="29" text-anchor="middle">루트 zone</text>
<text class="ygd-ts" x="85" y="45" text-anchor="middle" data-sub="0">신뢰 앵커: 루트 KSK</text>
</g>
<g class="ygd-box" data-box="1">
<rect class="ygd-node" x="10" y="100" width="150" height="44" rx="6"/>
<text class="ygd-t" x="85" y="119" text-anchor="middle">.com zone</text>
<text class="ygd-ts" x="85" y="135" text-anchor="middle" data-sub="1">DNSKEY, DS</text>
</g>
<g class="ygd-box" data-box="2">
<rect class="ygd-node" x="10" y="190" width="150" height="44" rx="6"/>
<text class="ygd-t" x="85" y="209" text-anchor="middle">example.com zone</text>
<text class="ygd-ts" x="85" y="225" text-anchor="middle" data-sub="2">DNSKEY, DS</text>
</g>
<g class="ygd-box" data-box="3">
<rect class="ygd-node" x="10" y="280" width="150" height="44" rx="6"/>
<text class="ygd-t" x="85" y="299" text-anchor="middle">A RRset</text>
<text class="ygd-ts" x="85" y="315" text-anchor="middle" data-sub="3">데이터 레코드</text>
</g>
<line class="ygd-arrow" x1="85" y1="56" x2="85" y2="98" marker-end="url(#ygd-dc-ah)"/>
<line class="ygd-arrow" x1="85" y1="146" x2="85" y2="188" marker-end="url(#ygd-dc-ah)"/>
<line class="ygd-arrow" x1="85" y1="236" x2="85" y2="278" marker-end="url(#ygd-dc-ah)"/>
<g class="ygd-step ygd-ann ygd-off" data-s="1"><text class="ygd-t" x="175" y="36">1 신뢰 앵커로 루트 DNSKEY 검증</text></g>
<g class="ygd-step ygd-ann ygd-off" data-s="2"><text class="ygd-t" x="175" y="82">2 루트 ZSK로 .com DS 검증</text></g>
<g class="ygd-step ygd-ann ygd-off" data-s="3"><text class="ygd-t" x="175" y="104">3 DS 해시와 .com KSK 대조</text></g>
<g class="ygd-step ygd-ann ygd-off" data-s="4"><text class="ygd-t" x="175" y="172" data-ann="4">4 .com ZSK로 DS 검증</text></g>
<g class="ygd-step ygd-ann ygd-off" data-s="5"><text class="ygd-t" x="175" y="194" data-ann="5">5 DS 해시와 KSK 대조</text></g>
<g class="ygd-step ygd-ann ygd-off" data-s="6"><text class="ygd-t" x="175" y="262">6 ZSK로 A의 RRSIG 검증</text></g>
</svg>
<div class="ygd-desc" aria-live="polite"></div>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전 단계</button>
<button type="button" class="ygd-btn" data-act="next">다음 단계</button>
</div>
<div class="ygd-note">비유: 공증 사슬과 비슷하다. 믿고 있는 기관이 다음 기관을 보증하고, 그 기관이 다시 아래를 보증한다. 보증이 아예 없으면 확인 대상이 아닌 것으로 보고, 보증은 있는데 내용이 안 맞으면 거부한다.</div>
<script>
(function(){
var root=document.getElementById('ygd-dnssec-chain');
if(!root){return;}
var common=[
"루트 KSK는 리졸버에 미리 들어 있다. 이 신뢰 앵커로 루트 DNSKEY RRset을 검증한다.",
"검증된 루트 ZSK로 .com의 DS RRset을 검증한다.",
"DS의 해시가 .com KSK와 일치하면 .com의 DNSKEY까지 믿을 수 있다."
];
var D=[
["리졸버는 루트 신뢰 앵커에서 출발해 한 칸씩 내려가며 검증한다. 재생을 눌러 6단계를 따라가 본다.",common[0],common[1],common[2],
".com ZSK로 example.com의 DS를 검증한다.",
"example.com의 DS 해시가 그 zone의 KSK와 맞으면 example.com의 DNSKEY가 검증된다.",
"example.com ZSK로 실제 A 레코드의 RRSIG를 검증하면 응답을 믿을 수 있다. 한 칸이라도 끊기면 그 아래는 전부 검증 불가다."],
["example.com이 DNSSEC를 쓰지 않아 .com zone에 DS가 없는 경우를 본다.",common[0],common[1],common[2],
"example.com의 DS가 .com zone에 없다. 신뢰 사슬이 여기서 끊기고 unsigned로 취급되어 검증 없이 통과한다. 이건 정상 동작이다."],
["DS는 등록돼 있는데 서명이 맞지 않는 경우를 본다.",common[0],common[1],common[2],
".com ZSK로 example.com의 DS를 검증한다.",
"DS는 있는데 해시가 example.com의 KSK와 맞지 않는다. 끊긴 게 아니라 깨진 것이라 리졸버는 응답을 버리고 SERVFAIL을 던진다."]
];
var MAX=[6,4,5];
var ANN={1:{4:"4 example.com의 DS가 없음"},2:{5:"5 DS 해시와 KSK 불일치"}};
var DEF={4:"4 .com ZSK로 DS 검증",5:"5 DS 해시와 KSK 대조"};
var SUB=["신뢰 앵커: 루트 KSK","DNSKEY, DS","DNSKEY, DS","데이터 레코드"];
var mode=0,step=0,timer=null;
var reduce=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
var desc=root.querySelector('.ygd-desc');
var steps=root.querySelectorAll('.ygd-ann');
var boxes=root.querySelectorAll('.ygd-box');
var tabs=root.querySelectorAll('.ygd-tab');
var playBtn=root.querySelector('[data-act="play"]');
function status(b){
if(mode===0){var th=[1,3,5,6];return step>=th[b]?'ok':'';}
if(mode===1){if(b===0&&step>=1){return 'ok';}if(b===1&&step>=3){return 'ok';}if(b>=2&&step>=4){return 'skip';}return '';}
if(b===0&&step>=1){return 'ok';}if(b===1&&step>=3){return 'ok';}if(b===2&&step>=5){return 'fail';}return '';
}
function stop(){if(timer){clearInterval(timer);timer=null;}playBtn.textContent='재생';}
function render(){
root.setAttribute('data-mode',String(mode));
Array.prototype.forEach.call(steps,function(e){
var s=parseInt(e.getAttribute('data-s'),10);
var cls='ygd-step ygd-ann '+(s<=step?'ygd-on':'ygd-off');
if(s<=step&&mode===1&&s===4){cls+=' ygd-skip';}
if(s<=step&&mode===2&&s===5){cls+=' ygd-fail';}
e.setAttribute('class',cls);
var tx=e.querySelector('[data-ann]');
if(tx){var a=ANN[mode]&&ANN[mode][s];tx.textContent=a?a:DEF[s];}
});
Array.prototype.forEach.call(boxes,function(g){
var b=parseInt(g.getAttribute('data-box'),10);
var st=status(b);
g.setAttribute('class','ygd-box'+(st?' ygd-st-'+st:''));
var sub=g.querySelector('[data-sub]');
sub.textContent=st==='ok'?'✓ 검증됨':st==='fail'?'✕ 검증 실패':st==='skip'?'unsigned 취급':SUB[b];
});
desc.textContent=D[mode][step];
Array.prototype.forEach.call(tabs,function(t){
t.setAttribute('aria-pressed',String(parseInt(t.getAttribute('data-mode'),10)===mode));
});
}
Array.prototype.forEach.call(tabs,function(t){
t.addEventListener('click',function(){stop();mode=parseInt(t.getAttribute('data-mode'),10);step=0;render();});
});
playBtn.addEventListener('click',function(){
if(timer){stop();return;}
if(step>=MAX[mode]){step=0;}
if(reduce){step=MAX[mode];render();return;}
step+=1;render();
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(step>=MAX[mode]){stop();return;}
step+=1;render();
if(step>=MAX[mode]){stop();}
},1800);
});
root.querySelector('[data-act="prev"]').addEventListener('click',function(){stop();if(step>0){step-=1;}render();});
root.querySelector('[data-act="next"]').addEventListener('click',function(){stop();if(step<MAX[mode]){step+=1;}render();});
render();
})();
</script>
</div>

## 검증 흐름을 한 번 따라가 보기

validating 리졸버가 `example.com`의 A 레코드를 푸는 과정이다.

```
sequenceDiagram
    participant C as 리졸버 (validating)
    participant R as 루트 서버
    participant T as .com 서버
    participant A as example.com 서버

    C->>R: example.com A? (DO 비트 set)
    R-->>C: .com 위임 + DS(.com) + RRSIG
    C->>T: example.com A?
    T-->>C: example.com 위임 + DS(example.com) + RRSIG
    C->>A: example.com A?
    A-->>C: A 레코드 + RRSIG
    Note over C: 루트 앵커부터 아래로 RRSIG 체인 검증
    Note over C: 하나라도 실패하면 SERVFAIL
```

핵심은 DO 비트(DNSSEC OK)다. 리졸버가 질의에 DO 비트를 세워야 권한 서버가 RRSIG·DNSKEY 같은 서명 레코드를 응답에 같이 실어준다. DO 비트가 없으면 서명 레코드는 빠지고 일반 응답만 온다.

그리고 검증을 실제로 하느냐는 또 다른 문제다. DO 비트만 세우고 검증을 안 하는 리졸버도 있다. 검증까지 하는 리졸버를 validating resolver라고 부른다. 우리가 흔히 쓰는 8.8.8.8, 1.1.1.1은 validating이다. 사내 BIND를 운영한다면 `dnssec-validation auto`가 켜져 있는지 봐야 한다.

직접 확인하려면 `dig`에 `+dnssec`를 붙인다.

```bash
dig +dnssec example.com A

# 응답 flags에 ad(Authenticated Data)가 있으면
# 리졸버가 검증에 성공했다는 뜻이다.
# flags: qr rd ra ad; ...

# 검증 실패면 status가 SERVFAIL로 떨어진다.
dig example.com A
# ;; ->>HEADER<<- opcode: QUERY, status: SERVFAIL
```

`ad` 플래그가 검증 성공의 신호다. CD(Checking Disabled) 비트를 세우면 검증을 건너뛰고 응답을 받는데, 트러블슈팅할 때 "검증 때문에 막힌 건지 데이터 자체가 없는 건지" 가르는 데 쓴다.

```bash
# 검증을 끄고 질의 → 응답이 오면 데이터는 정상, 서명이 문제
dig +cd example.com A
```

## 키 롤오버 — 도입하고 나서 진짜 일이 시작된다

서명 자체는 도구가 다 해준다. 운영 부담은 키 교체에서 나온다. 키를 한 번 만들고 영원히 쓰면 안 되니까 주기적으로 바꿔야 하는데, DNS 캐시 특성 때문에 그냥 바꾸면 검증이 깨진다.

### ZSK 롤오버 — Pre-Publish 방식

ZSK는 상위 zone과 무관해서 비교적 간단하다. 보통 Pre-Publish 방식을 쓴다.

1. 새 ZSK를 DNSKEY에 미리 추가한다(아직 서명에는 안 씀). 두 ZSK가 같이 publish된 상태.
2. TTL이 충분히 지나서 전 세계 캐시에 새 DNSKEY가 퍼지길 기다린다.
3. 서명을 새 ZSK로 전환한다. 이때는 새 키가 이미 캐시에 있으니 검증이 안 깨진다.
4. 옛 RRSIG의 TTL이 다 지난 뒤 옛 ZSK를 DNSKEY에서 제거한다.

기다리는 시간이 핵심이다. DNSKEY TTL과 RRSIG TTL만큼 무조건 기다려야 한다. 성급하게 옛 키를 빼면 아직 옛 RRSIG를 캐시에 들고 있는 리졸버가 검증에 실패한다.

<div class="ygd-zsk-rollover" id="ygd-zsk-rollover" data-mode="0">
<style>
.ygd-zsk-rollover{--ygd-bg:#f7f6f4;--ygd-box:#ffffff;--ygd-text:#2b2825;--ygd-sub:#5f5a54;--ygd-line:#3d7387;--ygd-bad:#b3261e;--ygd-badbg:#fbe9e7;--ygd-good:#1b6e3c;--ygd-goodbg:#e3f3e9;--ygd-btn:#3d7387;--ygd-btntext:#ffffff;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1em;margin-bottom:1em;padding:12px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-text);box-sizing:border-box}
body[data-md-color-scheme="slate"] .ygd-zsk-rollover{--ygd-bg:#26232a;--ygd-box:#322f36;--ygd-text:#f0ede9;--ygd-sub:#c4bfb8;--ygd-line:#7fb6cb;--ygd-bad:#ff8a80;--ygd-badbg:#4a2a2a;--ygd-good:#7fd69b;--ygd-goodbg:#243a2d;--ygd-btn:#7fb6cb;--ygd-btntext:#1b1a1c}
.ygd-zsk-rollover .ygd-tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px}
.ygd-zsk-rollover .ygd-tab,.ygd-zsk-rollover .ygd-btn{font-size:14px;line-height:1.3;min-height:40px;padding:6px 12px;border:1px solid var(--ygd-line);border-radius:6px;background:var(--ygd-box);color:var(--ygd-text);cursor:pointer;font-family:inherit}
.ygd-zsk-rollover .ygd-tab[aria-pressed="true"],.ygd-zsk-rollover .ygd-btn.ygd-primary{background:var(--ygd-btn);color:var(--ygd-btntext)}
.ygd-zsk-rollover .ygd-tab:focus-visible,.ygd-zsk-rollover .ygd-btn:focus-visible{outline:3px solid var(--ygd-text);outline-offset:2px}
.ygd-zsk-rollover .ygd-svg{display:block;width:100%;height:auto}
.ygd-zsk-rollover .ygd-t{fill:var(--ygd-text);font-size:12px}
.ygd-zsk-rollover .ygd-ts{fill:var(--ygd-sub);font-size:12px}
.ygd-zsk-rollover .ygd-cell{fill:var(--ygd-box);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-zsk-rollover .ygd-c-ok .ygd-cell{fill:var(--ygd-goodbg);stroke:var(--ygd-good)}
.ygd-zsk-rollover .ygd-c-bad .ygd-cell{fill:var(--ygd-badbg);stroke:var(--ygd-bad)}
.ygd-zsk-rollover .ygd-cur .ygd-cell{stroke-width:3}
.ygd-zsk-rollover .ygd-hd.ygd-cur .ygd-t{font-weight:bold}
.ygd-zsk-rollover .ygd-off{opacity:0.45}
.ygd-zsk-rollover .ygd-on{opacity:1}
.ygd-zsk-rollover .ygd-fade{transition:opacity .4s}
.ygd-zsk-rollover .ygd-desc{margin-top:8px;padding:10px 12px;min-height:4.8em;font-size:14px;line-height:1.6;background:var(--ygd-box);border-left:4px solid var(--ygd-line);border-radius:4px;color:var(--ygd-text)}
.ygd-zsk-rollover .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ygd-zsk-rollover .ygd-note{margin-top:8px;font-size:14px;line-height:1.5;color:var(--ygd-sub)}
@media (prefers-reduced-motion: reduce){.ygd-zsk-rollover .ygd-fade{transition:none}}
</style>
<div class="ygd-tabs" role="group" aria-label="롤오버 진행 방식 선택">
<button type="button" class="ygd-tab" data-mode="0" aria-pressed="true">TTL만큼 기다림</button>
<button type="button" class="ygd-tab" data-mode="1" aria-pressed="false">옛 키를 서둘러 제거</button>
</div>
<svg class="ygd-svg" viewBox="0 0 400 204" role="img" aria-label="ZSK Pre-Publish 롤오버의 네 단계에서 옛 ZSK, 새 ZSK, 리졸버 캐시의 상태가 어떻게 바뀌는지 보여주는 타임라인">
<text class="ygd-t" x="4" y="76">옛 ZSK</text>
<text class="ygd-t" x="4" y="130">새 ZSK</text>
<text class="ygd-t" x="4" y="180">리졸버</text>
<text class="ygd-ts" x="4" y="196">캐시</text>
<g class="ygd-hd ygd-fade ygd-off" data-h="0"><text class="ygd-t" x="102" y="28" text-anchor="middle">1 사전 게시</text></g>
<g class="ygd-hd ygd-fade ygd-off" data-h="1"><text class="ygd-t" x="186" y="28" text-anchor="middle">2 대기</text></g>
<g class="ygd-hd ygd-fade ygd-off" data-h="2"><text class="ygd-t" x="270" y="28" text-anchor="middle">3 서명 전환</text></g>
<g class="ygd-hd ygd-fade ygd-off" data-h="3"><text class="ygd-t" x="354" y="28" text-anchor="middle">4 옛 키 제거</text></g>
</svg>
<div class="ygd-desc" aria-live="polite"></div>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전 단계</button>
<button type="button" class="ygd-btn" data-act="next">다음 단계</button>
</div>
<div class="ygd-note">비유: 새 도장을 쓰기 전에 먼저 등록해 두는 것과 같다. 모두가 새 도장을 알게 된 뒤에 쓰기 시작하고, 옛 도장이 찍힌 서류가 모두 효력을 잃은 뒤에 옛 도장을 폐기한다.</div>
<script>
(function(){
var root=document.getElementById('ygd-zsk-rollover');
if(!root){return;}
var NS='http://www.w3.org/2000/svg';
var svg=root.querySelector('.ygd-svg');
var CELLS=[
[["게시","서명 사용"],["게시","서명 사용"],["게시","서명 중단"],["제거","TTL 경과 후"]],
[["게시","서명 안 함"],["게시","캐시로 전파"],["게시","서명 사용"],["게시","서명 사용"]],
[["옛 키 캐시","새 키 없음"],["새 키도","캐시됨"],["새 키로","검증 성공"],["옛 RRSIG","TTL 경과"]]
];
var HASTY=[[null,null,null,["제거","TTL 전"]],[null,null,null,null],[null,null,null,["옛 RRSIG","검증 실패"]]];
var D=[
["ZSK를 바꾸는 과정을 네 단계로 따라간다. 핵심은 캐시가 따라올 시간을 주는 것이다.",
"새 ZSK를 DNSKEY에 미리 추가한다. 아직 서명에는 쓰지 않으므로 두 ZSK가 함께 게시된 상태가 된다.",
"DNSKEY TTL이 지날 때까지 기다려서 전 세계 캐시에 새 DNSKEY가 퍼지게 한다.",
"서명을 새 ZSK로 전환한다. 새 키가 이미 캐시에 있으니 검증이 깨지지 않는다.",
"옛 RRSIG의 TTL이 다 지난 뒤 옛 ZSK를 DNSKEY에서 제거한다. 캐시에 옛 서명이 남아 있지 않아 안전하다."],
["ZSK를 바꾸는 과정을 네 단계로 따라간다. 이번에는 마지막 단계를 서두르는 경우다.",
"새 ZSK를 DNSKEY에 미리 추가한다. 아직 서명에는 쓰지 않으므로 두 ZSK가 함께 게시된 상태가 된다.",
"DNSKEY TTL이 지날 때까지 기다려서 전 세계 캐시에 새 DNSKEY가 퍼지게 한다.",
"서명을 새 ZSK로 전환한다. 새 키가 이미 캐시에 있으니 검증이 깨지지 않는다.",
"옛 RRSIG의 TTL을 기다리지 않고 옛 ZSK를 빼면, 아직 옛 RRSIG를 캐시에 들고 있는 리졸버가 검증에 실패한다."]
];
var cells=[];
var r,c;
for(r=0;r<3;r++){
cells.push([]);
for(c=0;c<4;c++){
var g=document.createElementNS(NS,'g');
var x=62+c*84,y=40+r*54;
var rect=document.createElementNS(NS,'rect');
rect.setAttribute('class','ygd-cell');
rect.setAttribute('x',x);rect.setAttribute('y',y);rect.setAttribute('width',80);rect.setAttribute('height',48);rect.setAttribute('rx',6);
var t1=document.createElementNS(NS,'text');
t1.setAttribute('class','ygd-t');t1.setAttribute('x',x+40);t1.setAttribute('y',y+20);t1.setAttribute('text-anchor','middle');
var t2=document.createElementNS(NS,'text');
t2.setAttribute('class','ygd-ts');t2.setAttribute('x',x+40);t2.setAttribute('y',y+38);t2.setAttribute('text-anchor','middle');
g.appendChild(rect);g.appendChild(t1);g.appendChild(t2);
svg.appendChild(g);
cells[r].push({g:g,t1:t1,t2:t2});
}
}
var mode=0,step=0,timer=null;
var reduce=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
var desc=root.querySelector('.ygd-desc');
var heads=root.querySelectorAll('.ygd-hd');
var tabs=root.querySelectorAll('.ygd-tab');
var playBtn=root.querySelector('[data-act="play"]');
function stop(){if(timer){clearInterval(timer);timer=null;}playBtn.textContent='재생';}
function render(){
root.setAttribute('data-mode',String(mode));
Array.prototype.forEach.call(heads,function(h){
var i=parseInt(h.getAttribute('data-h'),10);
h.setAttribute('class','ygd-hd ygd-fade '+(i+1<=step?'ygd-on':'ygd-off')+(i+1===step?' ygd-cur':''));
});
for(var rr=0;rr<3;rr++){
for(var cc=0;cc<4;cc++){
var o=cells[rr][cc];
var txt=CELLS[rr][cc];
var bad=false;
if(mode===1&&HASTY[rr][cc]){txt=HASTY[rr][cc];bad=true;}
o.t1.textContent=txt[0];o.t2.textContent=txt[1];
var shown=cc+1<=step;
var cls='ygd-fade '+(shown?'ygd-on':'ygd-off');
if(shown&&bad){cls+=' ygd-c-bad';}
else if(shown&&rr===2){cls+=' ygd-c-ok';}
if(cc+1===step){cls+=' ygd-cur';}
o.g.setAttribute('class',cls);
}
}
desc.textContent=D[mode][step];
Array.prototype.forEach.call(tabs,function(t){
t.setAttribute('aria-pressed',String(parseInt(t.getAttribute('data-mode'),10)===mode));
});
}
Array.prototype.forEach.call(tabs,function(t){
t.addEventListener('click',function(){stop();mode=parseInt(t.getAttribute('data-mode'),10);step=0;render();});
});
playBtn.addEventListener('click',function(){
if(timer){stop();return;}
if(step>=4){step=0;}
if(reduce){step=4;render();return;}
step+=1;render();
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(step>=4){stop();return;}
step+=1;render();
if(step>=4){stop();}
},1800);
});
root.querySelector('[data-act="prev"]').addEventListener('click',function(){stop();if(step>0){step-=1;}render();});
root.querySelector('[data-act="next"]').addEventListener('click',function(){stop();if(step<4){step+=1;}render();});
render();
})();
</script>
</div>

### KSK 롤오버 — 상위 zone과 협조해야 한다

KSK는 DS가 상위 zone에 등록돼 있어서 훨씬 까다롭다. 새 KSK를 만들면 그 DS를 상위(레지스트라 → 레지스트리)에 등록하고, 옛 DS가 제거될 때까지 양쪽 키를 다 들고 있어야 한다.

여기서 자주 사고가 난다. DS 등록은 레지스트라 웹 콘솔이나 EPP로 처리되는데, 반영이 즉시가 아니고 상위 zone TTL이 또 걸린다. `.com` DS의 TTL이 86400(24시간)이면, 옛 DS를 보고 검증하는 리졸버가 하루는 남아 있다고 봐야 한다. 새 KSK로 갈아엎고 옛 KSK를 바로 지우면, 옛 DS를 캐시한 리졸버가 새 KSK를 못 믿어서 SERVFAIL이 난다.

2018년 루트 KSK 롤오버를 ICANN이 몇 년에 걸쳐 신중하게 진행한 게 이 이유다. 신뢰 앵커가 바뀌면 전 세계 모든 validating 리졸버가 영향을 받는다. 그래서 RFC 5011(자동 신뢰 앵커 갱신)으로 새 키를 미리 publish하고 한참 뒤에 전환했다.

요즘은 BIND `dnssec-policy`, Knot DNS, OpenDNSSEC, PowerDNS 같은 도구가 롤오버 타이밍을 자동으로 잡아준다. 직접 손으로 키를 돌리는 건 사고 위험이 크다. 자동화 도구를 쓰되, DS 등록만큼은 상위 zone과 연동되는 부분이라 사람이 확인해야 한다. CDS/CDNSKEY 레코드를 지원하는 레지스트리면 DS 갱신까지 자동화되지만, 아직 다 지원하지는 않는다.

## SERVFAIL 트러블슈팅

DNSSEC를 켜고 나서 가장 많이 보는 게 SERVFAIL이다. 일반 사용자 눈에는 "사이트 접속 안 됨"으로만 보인다. validating 리졸버가 검증에 실패하면 응답을 통째로 버리고 SERVFAIL을 주기 때문에, NXDOMAIN(도메인 없음)과 달리 원인이 안 보인다. 실무에서 부딪히는 패턴은 대체로 정해져 있다.

### 1. 서명 만료

가장 흔하다. RRSIG의 만료 시각이 지났는데 재서명이 안 됐다. 자동 재서명 크론이 멈췄거나, 권한 서버 시계가 틀어졌거나, 서명 도구 설정이 잘못된 경우다. RRSIG 만료는 절벽처럼 온다. 만료 1초 전까지 멀쩡하다가 만료되는 순간 전 세계가 SERVFAIL이다.

```bash
# RRSIG 만료 시각 확인 (Expiration Inception 순)
dig +dnssec example.com A | grep RRSIG
# RRSIG A 13 2 3600 20260701000000 20260621000000 ...
#                    ^만료          ^시작
```

만료 시각을 보고 지났으면 즉시 재서명한다. 서명 유효기간은 보통 2~4주로 잡고, 재서명은 만료 한참 전에 돌려서 여유를 둔다.

### 2. DS 불일치

zone에서 KSK를 바꿨는데 상위 DS를 안 바꿨거나, 반대로 DS는 새 걸로 등록했는데 zone은 옛 KSK로 서명 중인 경우다. 키 롤오버 중에 타이밍이 어긋나면 난다.

```bash
# 현재 zone의 DNSKEY와 상위 DS를 따로 떠서 비교
dig +dnssec example.com DNSKEY
dig +dnssec example.com DS   # 상위 zone이 응답

# 온라인 분석 도구가 체인 전체를 그려준다
# dnsviz.net / verisignlabs.com DNSSEC Debugger
```

DNSViz에 도메인을 넣으면 루트부터 어디서 사슬이 깨졌는지 그림으로 보여준다. DS 불일치 의심되면 손으로 해시 맞춰보는 것보다 이게 빠르다.

### 3. 시계 틀어짐

권한 서버나 리졸버의 시각이 어긋나면 아직 유효한 서명도 "만료됨" 또는 "아직 시작 안 됨"으로 본다. RRSIG는 시작·만료 시각이 둘 다 있어서 시계가 앞서가도 뒤처져도 문제가 된다. NTP가 죽은 서버가 범인인 경우가 종종 있다.

### 4. 사슬 중간 zone의 문제

내 zone은 멀쩡한데 상위(`.com`)나 그 위에 문제가 있을 수도 있다. 내가 어찌할 수 없는 영역이라, 일단 내 쪽이 정상인지부터 `+cd`로 갈라서 확인한다.

```bash
# +cd로 검증 끄고 데이터가 오는지 본다
dig +cd example.com A   # 응답 정상 → 데이터는 멀쩡, 검증 단계가 문제
dig example.com A        # SERVFAIL → 검증 실패 확정
```

`+cd`로는 응답이 오는데 검증하면 SERVFAIL이면, 데이터 문제가 아니라 서명/체인 문제로 좁혀진다. 거기서 DNSViz로 어느 칸이 깨졌는지 본다.

### 5. 알고리즘 미스매치

리졸버가 지원 안 하는 서명 알고리즘을 쓰면 검증을 못 한다. 옛날 알고리즘(RSA/SHA-1, 알고리즘 5/7)은 폐기 단계라 쓰면 안 되고, 요즘은 ECDSA P-256(13)이나 Ed25519(15)를 쓴다. 마이그레이션할 때 알고리즘을 통째로 바꾸는 것도 일종의 키 롤오버라서 같은 절차로 신중히 해야 한다.

## 도입 전에 따져볼 것

DNSSEC는 켜는 순간 운영 난이도가 한 단계 올라간다. 서명 만료, 키 롤오버, DS 동기화가 전부 새로 생기는 장애 요인이다. 잘못 켜면 DNSSEC를 안 썼으면 멀쩡했을 도메인이 SERVFAIL로 통째로 죽는다. 무결성을 얻는 대신 가용성 리스크를 떠안는 거래다.

그래서 직접 BIND로 키를 돌리기보다, DNSSEC를 관리형으로 제공하는 DNS 서비스(Route 53, Cloudflare, NS1 등)에 맡기는 쪽이 사고가 적다. 서명·재서명·롤오버를 사업자가 처리하고, 운영자는 DS만 레지스트라에 등록하면 된다. 그래도 DS 등록과 키 교체 시점은 사람이 봐야 하는 부분이 남는다.

켤 가치가 있는 곳은 분명하다. 금융, 정부, 메일 서버(DANE/TLSA로 메일 TLS 검증까지 묶을 때)처럼 응답 변조가 실제 피해로 직결되는 도메인이다. 단순 블로그나 사내 도구에 무리해서 켰다가 롤오버 사고로 더 자주 죽는 경우도 봤다. 무결성이 정말 필요한지 먼저 따지고, 필요하면 관리형으로 켜는 게 현실적인 순서다.
