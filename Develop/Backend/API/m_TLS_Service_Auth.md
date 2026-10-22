---
title: "서비스 간 API 인증 — mTLS"
tags: [api, encryption, security, kubernetes]
updated: 2026-10-22
---

# 서비스 간 API 인증 — mTLS

## mTLS가 뭔가

TLS는 클라이언트가 서버의 인증서를 검증하는 단방향 인증이다. mTLS(mutual TLS)는 여기에 서버가 클라이언트의 인증서도 검증하는 과정이 추가된다. 양쪽 다 인증서를 제시하고, 양쪽 다 상대방을 검증한다.

일반적인 HTTPS 통신에서는 브라우저가 서버 인증서만 확인한다. 서버는 클라이언트가 누구인지 모른다. mTLS에서는 서버가 클라이언트에게도 인증서를 요구한다. 클라이언트가 유효한 인증서를 제시하지 못하면 연결 자체가 성립되지 않는다.

핸드셰이크 과정을 정리하면 이렇다:

1. 클라이언트가 서버에 연결 요청
2. 서버가 자신의 인증서를 클라이언트에 전달
3. 클라이언트가 서버 인증서를 CA로 검증
4. **서버가 클라이언트에게 인증서를 요청** (여기가 일반 TLS와 다른 부분)
5. 클라이언트가 자신의 인증서를 서버에 전달
6. 서버가 클라이언트 인증서를 CA로 검증
7. 양쪽 모두 검증 완료 후 암호화 통신 시작

<div class="ygd-mtls-auth" id="ygd-mtls-auth">
<style>
.ygd-mtls-auth{--ygd-bg:#FAF8F6;--ygd-panel:#FFFFFF;--ygd-border:#D9D3CC;--ygd-text:#2B2724;--ygd-muted:#6B655F;--ygd-a:#1F5FA8;--ygd-a-bg:#E4EEFA;--ygd-b:#B4530A;--ygd-b-bg:#FBEBDD;--ygd-ok:#2E7D4F;--ygd-life:#A39C94;--ygd-btn-bg:#FFFFFF;--ygd-btn-text:#2B2724;--ygd-btn-on-bg:#2B2724;--ygd-btn-on-text:#FAF8F6;--ygd-focus:#1F5FA8;--ygd-badge-text:#FFFFFF;font-family:inherit;font-size:15px;line-height:1.5;color:var(--ygd-text);background:var(--ygd-bg);border:1px solid var(--ygd-border);border-radius:12px;padding:14px;margin:1.2em auto;box-sizing:border-box;max-width:760px}
body[data-md-color-scheme="slate"] .ygd-mtls-auth{--ygd-bg:#262326;--ygd-panel:#2F2B2E;--ygd-border:#4A4448;--ygd-text:#F0EDE9;--ygd-muted:#A8A29B;--ygd-a:#7DB4F0;--ygd-a-bg:#1F3550;--ygd-b:#F0A867;--ygd-b-bg:#4A3220;--ygd-ok:#6FCB93;--ygd-life:#7A736C;--ygd-btn-bg:#332F32;--ygd-btn-text:#F0EDE9;--ygd-btn-on-bg:#F0EDE9;--ygd-btn-on-text:#262326;--ygd-focus:#7DB4F0;--ygd-badge-text:#14202E}
.ygd-mtls-auth .ygd-title{font-weight:700;font-size:16px;margin-bottom:8px}
.ygd-mtls-auth .ygd-toggle{display:flex;flex-wrap:wrap;gap:8px}
.ygd-mtls-auth .ygd-btn{flex:1 1 140px;font:inherit;font-size:14px;min-height:40px;padding:6px 12px;border-radius:8px;border:1.5px solid var(--ygd-border);background:var(--ygd-btn-bg);color:var(--ygd-btn-text);cursor:pointer;box-sizing:border-box}
.ygd-mtls-auth .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-mtls-auth .ygd-btn[aria-pressed="true"],.ygd-mtls-auth .ygd-primary{background:var(--ygd-btn-on-bg);color:var(--ygd-btn-on-text);border-color:var(--ygd-btn-on-bg)}
.ygd-mtls-auth .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-mtls-auth .ygd-modenote{font-size:14px;color:var(--ygd-muted);margin:8px 0 6px}
.ygd-mtls-auth .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-mtls-auth .ygd-actor{stroke-width:2}
.ygd-mtls-auth .ygd-actor-a{fill:var(--ygd-a-bg);stroke:var(--ygd-a)}
.ygd-mtls-auth .ygd-actor-b{fill:var(--ygd-b-bg);stroke:var(--ygd-b)}
.ygd-mtls-auth[data-ygd-verify="a"] .ygd-actor-a,.ygd-mtls-auth[data-ygd-verify="b"] .ygd-actor-b{stroke-width:4}
.ygd-mtls-auth[data-ygd-verify="a"] .ygd-actor-b,.ygd-mtls-auth[data-ygd-verify="b"] .ygd-actor-a{stroke-dasharray:5 3}
.ygd-mtls-auth .ygd-atext{fill:var(--ygd-text);font-size:12px;font-weight:700;text-anchor:middle}
.ygd-mtls-auth .ygd-asub{fill:var(--ygd-muted);font-size:10.5px;text-anchor:middle}
.ygd-mtls-auth .ygd-life{stroke:var(--ygd-life);stroke-width:1.5;stroke-dasharray:3 4}
.ygd-mtls-auth .ygd-step{opacity:.35}
.ygd-mtls-auth .ygd-step.ygd-done{opacity:.8}
.ygd-mtls-auth .ygd-step.ygd-on{opacity:1}
.ygd-mtls-auth .ygd-step.ygd-skip{opacity:.3}
.ygd-mtls-auth .ygd-line{stroke-width:2.5;fill:none}
.ygd-mtls-auth .ygd-dash{stroke-dasharray:6 4;stroke-width:3}
.ygd-mtls-auth .ygd-ln-a{stroke:var(--ygd-a)}
.ygd-mtls-auth .ygd-ln-b{stroke:var(--ygd-b)}
.ygd-mtls-auth .ygd-ln-ok{stroke:var(--ygd-ok);stroke-width:3.5}
.ygd-mtls-auth .ygd-fill-a{fill:var(--ygd-a)}
.ygd-mtls-auth .ygd-fill-b{fill:var(--ygd-b)}
.ygd-mtls-auth .ygd-fill-ok{fill:var(--ygd-ok)}
.ygd-mtls-auth .ygd-tick{fill:var(--ygd-badge-text);font-size:13px;font-weight:700;text-anchor:middle}
.ygd-mtls-auth .ygd-lbl{fill:var(--ygd-text);font-size:12px;text-anchor:middle}
.ygd-mtls-auth .ygd-sub{fill:var(--ygd-muted);font-size:10.5px;text-anchor:middle}
.ygd-mtls-auth .ygd-skip-note{fill:var(--ygd-muted);font-size:10.5px;text-anchor:middle;display:none}
.ygd-mtls-auth .ygd-only-tls{display:none}
.ygd-mtls-auth.ygd-is-tls .ygd-only-tls{display:inline}
.ygd-mtls-auth.ygd-is-tls .ygd-only-mtls{display:none}
.ygd-mtls-auth.ygd-is-tls .ygd-skip-note{display:inline}
.ygd-mtls-auth.ygd-is-tls .ygd-hide-tls{display:none}
.ygd-mtls-auth .ygd-legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--ygd-muted);margin:6px 0 10px}
.ygd-mtls-auth .ygd-sw{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:4px;border:3px solid var(--ygd-life);box-sizing:border-box}
.ygd-mtls-auth .ygd-sw-a{border-color:var(--ygd-a);background:var(--ygd-a-bg)}
.ygd-mtls-auth .ygd-sw-b{border-color:var(--ygd-b);background:var(--ygd-b-bg)}
.ygd-mtls-auth .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px}
.ygd-mtls-auth .ygd-ctrl .ygd-btn{flex:1 1 70px}
.ygd-mtls-auth .ygd-panel{border:1px solid var(--ygd-border);border-left:6px solid var(--ygd-muted);background:var(--ygd-panel);border-radius:8px;padding:10px 12px;margin-top:10px;box-sizing:border-box}
.ygd-mtls-auth .ygd-panel[data-who="a"]{border-left-color:var(--ygd-a)}
.ygd-mtls-auth .ygd-panel[data-who="b"]{border-left-color:var(--ygd-b)}
.ygd-mtls-auth .ygd-panel[data-who="ok"]{border-left-color:var(--ygd-ok)}
.ygd-mtls-auth .ygd-count{font-size:13px;color:var(--ygd-muted)}
.ygd-mtls-auth .ygd-who{font-size:14px;font-weight:700;margin-top:2px}
.ygd-mtls-auth .ygd-stitle{font-size:15px;font-weight:700;margin-top:6px}
.ygd-mtls-auth .ygd-desc{font-size:14px;margin-top:2px;overflow-wrap:anywhere}
.ygd-mtls-auth .ygd-analogy{font-size:13px;color:var(--ygd-muted);margin-top:10px;overflow-wrap:anywhere}
@media (prefers-reduced-motion:no-preference){
.ygd-mtls-auth .ygd-step{transition:opacity .3s}
.ygd-mtls-auth .ygd-step.ygd-on .ygd-draw{animation:ygd-draw .7s ease forwards}
.ygd-mtls-auth .ygd-step.ygd-on .ygd-head,.ygd-mtls-auth .ygd-step.ygd-on .ygd-lbl{animation:ygd-fade .3s .55s both}
.ygd-mtls-auth .ygd-step.ygd-on .ygd-dash,.ygd-mtls-auth .ygd-step.ygd-on .ygd-badge{animation:ygd-fade .5s both}
}
@keyframes ygd-draw{from{stroke-dasharray:1;stroke-dashoffset:1}to{stroke-dasharray:1;stroke-dashoffset:0}}
@keyframes ygd-fade{from{opacity:0}to{opacity:1}}
</style>
<div class="ygd-title">일반 TLS와 mTLS 핸드셰이크 비교</div>
<div class="ygd-toggle" role="group" aria-label="인증 방식 선택">
<button type="button" class="ygd-btn ygd-mode" data-mode="mtls" aria-pressed="true">mTLS (양쪽 모두 인증)</button>
<button type="button" class="ygd-btn ygd-mode" data-mode="tls" aria-pressed="false">일반 TLS (서버만 인증)</button>
</div>
<div class="ygd-modenote" data-role="modenote"></div>
<svg class="ygd-svg" viewBox="0 0 360 380" role="img" aria-label="서비스 A와 서비스 B가 인증서를 주고받으며 서로를 검증하는 mTLS 핸드셰이크 시퀀스 다이어그램. 접속 시도, 서버 인증서 제시, 서버 인증서 검증, 클라이언트 인증서 요구, 클라이언트 인증서 제시, 클라이언트 인증서 검증, 암호화 통신 시작의 일곱 단계로 이루어진다.">
<line class="ygd-life" x1="60" y1="46" x2="60" y2="372"/>
<line class="ygd-life" x1="300" y1="46" x2="300" y2="372"/>
<rect class="ygd-actor ygd-actor-a" x="8" y="6" width="104" height="40" rx="8"/>
<text class="ygd-atext" x="60" y="23">서비스 A</text>
<text class="ygd-asub" x="60" y="38">클라이언트</text>
<rect class="ygd-actor ygd-actor-b" x="248" y="6" width="104" height="40" rx="8"/>
<text class="ygd-atext" x="300" y="23">서비스 B</text>
<text class="ygd-asub" x="300" y="38">서버</text>
<g class="ygd-step" data-i="1">
<line class="ygd-line ygd-ln-a ygd-draw" x1="66" y1="76" x2="288" y2="76" pathLength="1"/>
<polygon class="ygd-head ygd-fill-a" points="296,76 287,71.5 287,80.5"/>
<text class="ygd-lbl" x="180" y="66">① 접속 시도 (A → B)</text>
</g>
<g class="ygd-step" data-i="2">
<line class="ygd-line ygd-ln-b ygd-draw" x1="294" y1="122" x2="72" y2="122" pathLength="1"/>
<polygon class="ygd-head ygd-fill-b" points="64,122 73,117.5 73,126.5"/>
<text class="ygd-lbl" x="180" y="112">② B가 서버 인증서 제시</text>
</g>
<g class="ygd-step" data-i="3">
<circle class="ygd-badge ygd-fill-a" cx="60" cy="168" r="10"/>
<text class="ygd-tick" x="60" y="172.5">✓</text>
<line class="ygd-line ygd-ln-a ygd-dash" x1="74" y1="168" x2="288" y2="168"/>
<circle class="ygd-head ygd-fill-a" cx="296" cy="168" r="5"/>
<text class="ygd-lbl" x="180" y="158">③ A가 B 인증서 검증</text>
<text class="ygd-sub" x="180" y="184">CA로 서버 인증서 확인</text>
</g>
<g class="ygd-step" data-i="4">
<line class="ygd-line ygd-ln-b ygd-draw" x1="294" y1="214" x2="72" y2="214" pathLength="1"/>
<polygon class="ygd-head ygd-fill-b" points="64,214 73,209.5 73,218.5"/>
<text class="ygd-lbl" x="180" y="204">④ B가 클라이언트 인증서 요구</text>
<text class="ygd-skip-note" x="180" y="230">일반 TLS에는 없는 단계</text>
</g>
<g class="ygd-step" data-i="5">
<line class="ygd-line ygd-ln-a ygd-draw" x1="66" y1="260" x2="288" y2="260" pathLength="1"/>
<polygon class="ygd-head ygd-fill-a" points="296,260 287,255.5 287,264.5"/>
<text class="ygd-lbl" x="180" y="250">⑤ A가 클라이언트 인증서 제시</text>
<text class="ygd-skip-note" x="180" y="276">일반 TLS에는 없는 단계</text>
</g>
<g class="ygd-step" data-i="6">
<circle class="ygd-badge ygd-fill-b" cx="300" cy="306" r="10"/>
<text class="ygd-tick" x="300" y="310.5">✓</text>
<line class="ygd-line ygd-ln-b ygd-dash" x1="286" y1="306" x2="72" y2="306"/>
<circle class="ygd-head ygd-fill-b" cx="64" cy="306" r="5"/>
<text class="ygd-lbl" x="180" y="296">⑥ B가 A 인증서 검증</text>
<text class="ygd-sub ygd-hide-tls" x="180" y="322">CA로 클라이언트 인증서 확인</text>
<text class="ygd-skip-note" x="180" y="322">일반 TLS에는 없는 단계</text>
</g>
<g class="ygd-step" data-i="7">
<line class="ygd-line ygd-ln-ok" x1="78" y1="352" x2="282" y2="352"/>
<polygon class="ygd-head ygd-fill-ok" points="66,352 78,346 78,358"/>
<polygon class="ygd-head ygd-fill-ok" points="294,352 282,346 282,358"/>
<text class="ygd-lbl" x="180" y="342"><tspan class="ygd-only-mtls">⑦ 양방향 신뢰 · 암호화 통신 시작</tspan><tspan class="ygd-only-tls">⑦ 서버만 인증 · 암호화 통신 시작</tspan></text>
</g>
</svg>
<div class="ygd-legend">
<span><span class="ygd-sw ygd-sw-a"></span>파랑: 서비스 A의 동작</span>
<span><span class="ygd-sw ygd-sw-b"></span>주황: 서비스 B의 동작</span>
<span>실선 화살표: 메시지 전송</span>
<span>점선 + 원 끝 + 체크: 검증 (원이 가리키는 쪽이 검증 대상)</span>
</div>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전</button>
<button type="button" class="ygd-btn" data-act="next">다음</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
<div class="ygd-panel" data-who="n" role="status" aria-live="polite">
<div class="ygd-count" data-role="count"></div>
<div class="ygd-who" data-role="who"></div>
<div class="ygd-stitle" data-role="title"></div>
<div class="ygd-desc" data-role="desc"></div>
</div>
<div class="ygd-analogy">비유: 사무실 건물 출입에 가깝다. 일반 TLS는 방문자가 건물의 신원만 확인하고 들어가는 것이고, mTLS는 건물 쪽도 방문자의 출입증을 확인해야 문이 열리는 것이다. 어디까지나 비유이며, 실제 검증은 CA가 서명한 인증서를 기준으로 이루어진다.</div>
<script>
(function () {
  var root = document.getElementById('ygd-mtls-auth');
  if (!root) return;
  var groups = root.querySelectorAll('.ygd-step');
  var modeBtns = root.querySelectorAll('.ygd-mode');
  var playBtn = root.querySelector('[data-act="play"]');
  var prevBtn = root.querySelector('[data-act="prev"]');
  var nextBtn = root.querySelector('[data-act="next"]');
  var resetBtn = root.querySelector('[data-act="reset"]');
  var panel = root.querySelector('.ygd-panel');
  var elCount = root.querySelector('[data-role="count"]');
  var elWho = root.querySelector('[data-role="who"]');
  var elTitle = root.querySelector('[data-role="title"]');
  var elDesc = root.querySelector('[data-role="desc"]');
  var elNote = root.querySelector('[data-role="modenote"]');
  var NOTES = {
    mtls: 'mTLS: 클라이언트가 서버 인증서를 검증하고, 서버도 클라이언트 인증서를 검증한다. 양쪽 모두 인증서를 제시한다.',
    tls: '일반 TLS: 클라이언트가 서버 인증서만 검증한다. 서버는 클라이언트가 누구인지 모른다.'
  };
  var T = [
    null,
    { c: 'a', title: '① A → B 접속 시도', who: '전송: A → B · 아직 어느 쪽도 검증하지 않은 상태',
      d: '서비스 A(클라이언트)가 서비스 B(서버)에 연결을 요청한다. 이 시점에는 어느 쪽도 상대를 검증하지 않았다.' },
    { c: 'b', title: '② B가 서버 인증서 제시', who: '전송: B → A · B의 서버 인증서',
      d: 'B가 자신의 서버 인증서를 A에게 전달한다. 여기까지는 일반 TLS와 mTLS가 같다.' },
    { c: 'a', title: '③ A가 B 인증서 검증', who: '검증 주체: A → 검증 대상: B의 서버 인증서', v: 'a',
      d: 'A가 B의 인증서를 CA로 검증한다. 클라이언트가 서버를 확인하는 단방향 인증이 바로 이 단계다.',
      dTls: 'A가 B의 인증서를 CA로 검증한다. 클라이언트가 서버를 확인하는 단방향 인증이 바로 이 단계이고, 일반 TLS는 여기서 인증을 마친다.' },
    { c: 'b', title: '④ B가 클라이언트 인증서 요구', who: '요청: B → A · 클라이언트 인증서를 내놓으라는 요구',
      d: 'B가 A에게 클라이언트 인증서를 요구한다. 일반 TLS와 달라지는 지점이다. Node.js의 requestCert: true, Nginx의 ssl_verify_client on 설정이 이 요구에 해당한다.' },
    { c: 'a', title: '⑤ A가 클라이언트 인증서 제시', who: '전송: A → B · A의 클라이언트 인증서',
      d: 'A가 자신의 클라이언트 인증서를 B에게 전달한다. 유효한 인증서를 제시하지 못하면 연결 자체가 성립되지 않는다.' },
    { c: 'b', title: '⑥ B가 A 인증서 검증', who: '검증 주체: B → 검증 대상: A의 클라이언트 인증서', v: 'b',
      d: 'B가 A의 인증서를 CA로 검증한다. 서버가 클라이언트를 확인하는 이 단계가 mTLS에서 추가되는 부분이다. Node.js에서는 rejectUnauthorized: true일 때 유효하지 않은 인증서를 거부한다.' },
    { c: 'ok', title: '⑦ 양방향 신뢰 성립 → 암호화 통신 시작', who: 'A ↔ B · 서로 검증 완료',
      d: '양쪽 모두 상대를 검증했다. 이제 암호화 통신이 시작되고, B는 A의 인증서로 요청을 보낸 서비스를 식별할 수 있다.',
      tTls: '⑦ 서버 인증만으로 암호화 통신 시작', wTls: 'A만 B를 검증함 · B는 A를 검증하지 않음',
      dTls: '클라이언트가 서버만 확인한 상태로 암호화 통신이 시작된다. B는 A가 누구인지 알지 못하므로, 서비스 아이덴티티가 필요하면 JWT 같은 별도 수단이 있어야 한다.' }
  ];
  var mode = 'mtls';
  var cur = 0;
  var timer = null;
  function seq() { return mode === 'tls' ? [1, 2, 3, 7] : [1, 2, 3, 4, 5, 6, 7]; }
  function isLast() { var s = seq(); return cur === s[s.length - 1]; }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function step(dir) {
    var s = seq();
    var idx = s.indexOf(cur);
    if (dir > 0) {
      if (cur === 0) cur = s[0];
      else if (idx < s.length - 1) cur = s[idx + 1];
    } else {
      if (idx > 0) cur = s[idx - 1];
      else cur = 0;
    }
  }
  function render() {
    var tls = mode === 'tls';
    root.classList.toggle('ygd-is-tls', tls);
    elNote.textContent = NOTES[mode];
    Array.prototype.forEach.call(modeBtns, function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-mode') === mode ? 'true' : 'false');
    });
    Array.prototype.forEach.call(groups, function (g) {
      var i = Number(g.getAttribute('data-i'));
      g.classList.remove('ygd-on', 'ygd-done', 'ygd-skip');
      if (tls && i >= 4 && i <= 6) g.classList.add('ygd-skip');
      else if (i === cur) g.classList.add('ygd-on');
      else if (i < cur) g.classList.add('ygd-done');
    });
    var s = seq();
    var d = T[cur];
    root.setAttribute('data-ygd-verify', d && d.v ? d.v : '');
    if (!d) {
      elCount.textContent = (tls ? '일반 TLS 흐름' : 'mTLS 흐름') + ' · 준비';
      panel.setAttribute('data-who', 'n');
      elWho.textContent = '파랑은 서비스 A, 주황은 서비스 B의 동작이다.';
      elTitle.textContent = '재생을 눌러 시작';
      elDesc.textContent = '재생을 누르면 핸드셰이크가 단계별로 진행된다. 이전, 다음 버튼으로 한 단계씩 넘겨 볼 수도 있다.';
    } else {
      elCount.textContent = (tls ? '일반 TLS 흐름' : 'mTLS 흐름') + ' · 단계 ' + (s.indexOf(cur) + 1) + ' / ' + s.length;
      panel.setAttribute('data-who', d.c);
      elWho.textContent = tls && d.wTls ? d.wTls : d.who;
      elTitle.textContent = tls && d.tTls ? d.tTls : d.title;
      elDesc.textContent = tls && d.dTls ? d.dTls : d.d;
    }
    prevBtn.disabled = cur === 0;
    nextBtn.disabled = isLast();
    playBtn.textContent = timer ? '일시정지' : (isLast() ? '다시 재생' : '재생');
  }
  function tick() {
    if (!document.body.contains(root)) { stop(); return; }
    step(1);
    if (isLast()) stop();
    render();
  }
  function play() {
    if (timer) { stop(); render(); return; }
    if (cur === 0 || isLast()) { cur = 0; step(1); }
    if (!isLast()) timer = setInterval(tick, 2800);
    render();
  }
  playBtn.addEventListener('click', play);
  prevBtn.addEventListener('click', function () { stop(); step(-1); render(); });
  nextBtn.addEventListener('click', function () { stop(); step(1); render(); });
  resetBtn.addEventListener('click', function () { stop(); cur = 0; render(); });
  Array.prototype.forEach.call(modeBtns, function (b) {
    b.addEventListener('click', function () {
      stop();
      mode = b.getAttribute('data-mode');
      cur = 0;
      render();
    });
  });
  render();
})();
</script>
</div>

## 내부 API에 JWT 대신 mTLS를 쓰는 경우

마이크로서비스 환경에서 서비스 간 인증을 JWT로 하는 곳이 많다. 잘 동작하지만, 몇 가지 상황에서는 mTLS가 더 맞다.

### JWT의 한계

JWT는 애플리케이션 레이어(L7) 인증이다. 토큰을 HTTP 헤더에 넣어서 보내고, 받는 쪽에서 서명을 검증한다. 문제는:

- **토큰 탈취 가능성**: 네트워크 구간에서 토큰이 노출되면 만료 전까지 재사용할 수 있다. TLS 위에서 보내더라도, 로그에 찍히거나 중간 프록시에서 복호화되는 경우가 있다.
- **각 서비스마다 검증 로직 필요**: 토큰 파싱, 서명 검증, 클레임 확인 코드를 서비스마다 넣어야 한다. 라이브러리가 있어도 설정 실수가 생긴다.
- **토큰 갱신 관리**: 서비스가 수십 개면 토큰 발급/갱신 로직이 복잡해진다. 특히 서비스 간 호출 체인이 길어지면 토큰 전파 방식을 정해야 한다.

### mTLS가 맞는 경우

- **서비스 아이덴티티만 확인하면 될 때**: "이 요청이 order-service에서 온 건가?"만 확인하면 되는 경우. 사용자 정보나 권한 같은 클레임이 필요 없다.
- **네트워크 레벨에서 차단해야 할 때**: 인증서가 없으면 TCP 연결 자체가 안 된다. 애플리케이션 코드에 도달하기 전에 차단된다.
- **서비스 메시를 쓰는 환경**: Istio, Linkerd 같은 서비스 메시는 사이드카 프록시가 mTLS를 자동으로 처리한다. 애플리케이션 코드를 수정할 필요가 없다.

반대로 mTLS만으로 부족한 경우도 있다. 사용자별 권한이 필요하거나, 서비스 간 세분화된 접근 제어가 필요하면 mTLS + JWT를 같이 쓴다. mTLS로 서비스 아이덴티티를 확인하고, JWT로 사용자 컨텍스트를 전달하는 구조다.

## Zero-Trust 통신과 서비스 메시

### Zero-Trust의 핵심

Zero-Trust는 "네트워크 위치를 신뢰하지 않는다"는 원칙이다. 같은 VPC 안에 있어도, 같은 쿠버네티스 클러스터 안에 있어도, 모든 통신을 검증한다.

예전에는 방화벽 안쪽은 안전하다고 봤다. 그래서 내부 서비스 간 통신은 평문 HTTP로 하는 곳이 많았다. 문제는 공격자가 내부 네트워크에 한번 들어오면 lateral movement가 자유롭다는 것이다. 내부 통신에 인증이 없으니까.

mTLS는 Zero-Trust를 구현하는 기본 수단이다. 모든 서비스 간 통신에 상호 인증을 적용하면, 내부 네트워크에 침입하더라도 유효한 인증서 없이는 다른 서비스와 통신할 수 없다.

### 서비스 메시에서의 mTLS

Istio를 예로 들면, 각 Pod에 Envoy 사이드카 프록시가 붙는다. 서비스 간 통신은 실제로 Envoy-to-Envoy 통신이다. Envoy가 mTLS를 알아서 처리하기 때문에 애플리케이션은 평문 HTTP로 통신하면 된다.

```yaml
# Istio PeerAuthentication — 네임스페이스 전체에 mTLS 강제
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
```

`STRICT` 모드로 설정하면 해당 네임스페이스의 모든 서비스가 mTLS 없이는 통신할 수 없다. `PERMISSIVE` 모드도 있는데, 이건 mTLS와 평문 HTTP를 동시에 허용한다. 마이그레이션 과정에서만 쓰고, 운영에서는 반드시 `STRICT`로 전환해야 한다.

Istio는 내부적으로 SPIFFE(Secure Production Identity Framework For Everyone) 표준을 사용해서 서비스 아이덴티티를 관리한다. 각 서비스에 `spiffe://cluster.local/ns/production/sa/order-service` 같은 형태의 ID가 부여되고, 이걸 기반으로 AuthorizationPolicy를 작성한다:

```yaml
# 특정 서비스만 접근 허용
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: payment-service-policy
  namespace: production
spec:
  selector:
    matchLabels:
      app: payment-service
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/production/sa/order-service"]
    to:
    - operation:
        methods: ["POST"]
        paths: ["/api/v1/payments"]
```

이렇게 하면 payment-service는 order-service의 POST 요청만 받는다. 다른 서비스가 payment-service에 접근하려 하면 403이 반환된다.

<div class="ygd-mesh-path" id="ygd-mesh-path">
<style>
.ygd-mesh-path{--ygd-bg:#FAF8F6;--ygd-panel:#FFFFFF;--ygd-border:#D9D3CC;--ygd-text:#2B2724;--ygd-muted:#6B655F;--ygd-a:#1F5FA8;--ygd-a-bg:#E4EEFA;--ygd-b:#B4530A;--ygd-b-bg:#FBEBDD;--ygd-ok:#2E7D4F;--ygd-bad:#B3261E;--ygd-warn:#B4530A;--ygd-life:#A39C94;--ygd-plain:#6B655F;--ygd-btn-bg:#FFFFFF;--ygd-btn-text:#2B2724;--ygd-btn-on-bg:#2B2724;--ygd-btn-on-text:#FAF8F6;--ygd-focus:#1F5FA8;--ygd-badge-text:#FFFFFF;font-family:inherit;font-size:15px;line-height:1.5;color:var(--ygd-text);background:var(--ygd-bg);border:1px solid var(--ygd-border);border-radius:12px;padding:14px;margin:1.2em auto;box-sizing:border-box;max-width:760px}
body[data-md-color-scheme="slate"] .ygd-mesh-path{--ygd-bg:#262326;--ygd-panel:#2F2B2E;--ygd-border:#4A4448;--ygd-text:#F0EDE9;--ygd-muted:#A8A29B;--ygd-a:#7DB4F0;--ygd-a-bg:#1F3550;--ygd-b:#F0A867;--ygd-b-bg:#4A3220;--ygd-ok:#6FCB93;--ygd-bad:#F2877F;--ygd-warn:#F0A867;--ygd-life:#7A736C;--ygd-plain:#A8A29B;--ygd-btn-bg:#332F32;--ygd-btn-text:#F0EDE9;--ygd-btn-on-bg:#F0EDE9;--ygd-btn-on-text:#262326;--ygd-focus:#7DB4F0;--ygd-badge-text:#14202E}
.ygd-mesh-path .ygd-title{font-weight:700;font-size:16px;margin-bottom:8px}
.ygd-mesh-path .ygd-toggle{display:flex;flex-wrap:wrap;gap:8px}
.ygd-mesh-path .ygd-btn{flex:1 1 140px;font:inherit;font-size:14px;min-height:40px;padding:6px 12px;border-radius:8px;border:1.5px solid var(--ygd-border);background:var(--ygd-btn-bg);color:var(--ygd-btn-text);cursor:pointer;box-sizing:border-box}
.ygd-mesh-path .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-mesh-path .ygd-btn[aria-pressed="true"],.ygd-mesh-path .ygd-primary{background:var(--ygd-btn-on-bg);color:var(--ygd-btn-on-text);border-color:var(--ygd-btn-on-bg)}
.ygd-mesh-path .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-mesh-path .ygd-modenote{font-size:14px;color:var(--ygd-muted);margin:8px 0 6px;overflow-wrap:anywhere}
.ygd-mesh-path .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-mesh-path .ygd-pod{fill:none;stroke:var(--ygd-life);stroke-width:1.5;stroke-dasharray:4 4}
.ygd-mesh-path .ygd-node-app{fill:var(--ygd-a-bg);stroke:var(--ygd-a);stroke-width:2}
.ygd-mesh-path .ygd-node-env{fill:var(--ygd-b-bg);stroke:var(--ygd-b);stroke-width:2}
.ygd-mesh-path .ygd-node-env.ygd-hl{stroke-width:4}
.ygd-mesh-path.ygd-plain .ygd-envl{opacity:.35;stroke-dasharray:4 3}
.ygd-mesh-path .ygd-ptitle{fill:var(--ygd-muted);font-size:10.5px;text-anchor:middle}
.ygd-mesh-path .ygd-ntext{fill:var(--ygd-text);font-size:11.5px;font-weight:700;text-anchor:middle}
.ygd-mesh-path .ygd-nsub{fill:var(--ygd-muted);font-size:10px;text-anchor:middle}
.ygd-mesh-path .ygd-seg{opacity:.3}
.ygd-mesh-path .ygd-seg.ygd-done{opacity:.85}
.ygd-mesh-path .ygd-seg.ygd-on{opacity:1}
.ygd-mesh-path .ygd-seg.ygd-none{opacity:.12}
.ygd-mesh-path.ygd-plain .ygd-seg-s1{display:none}
.ygd-mesh-path .ygd-line{stroke-width:2.5;fill:none}
.ygd-mesh-path .ygd-ln-plain{stroke:var(--ygd-plain)}
.ygd-mesh-path .ygd-ln-mtls{stroke:var(--ygd-ok);stroke-width:3.5}
.ygd-mesh-path.ygd-plain .ygd-ln-mtls{stroke:var(--ygd-warn);stroke-dasharray:6 4;stroke-width:3}
.ygd-mesh-path .ygd-fill-plain{fill:var(--ygd-plain)}
.ygd-mesh-path .ygd-fill-mtls{fill:var(--ygd-ok)}
.ygd-mesh-path.ygd-plain .ygd-fill-mtls{fill:var(--ygd-warn)}
.ygd-mesh-path .ygd-lbl{fill:var(--ygd-text);font-size:10.5px}
.ygd-mesh-path .ygd-lbl-c{text-anchor:middle}
.ygd-mesh-path .ygd-badge{display:none}
.ygd-mesh-path .ygd-badge.ygd-bd-ok{display:inline;fill:var(--ygd-ok)}
.ygd-mesh-path .ygd-badge.ygd-bd-bad{display:inline;fill:var(--ygd-bad)}
.ygd-mesh-path .ygd-badge.ygd-bd-warn{display:inline;fill:var(--ygd-warn)}
.ygd-mesh-path .ygd-tick{display:none;fill:var(--ygd-badge-text);font-size:13px;font-weight:700;text-anchor:middle}
.ygd-mesh-path .ygd-tick.ygd-on{display:inline}
.ygd-mesh-path .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ygd-mesh-path .ygd-ctrl .ygd-btn{flex:1 1 70px}
.ygd-mesh-path .ygd-panel{border:1px solid var(--ygd-border);border-left:6px solid var(--ygd-muted);background:var(--ygd-panel);border-radius:8px;padding:10px 12px;margin-top:10px;box-sizing:border-box}
.ygd-mesh-path .ygd-panel[data-who="ok"]{border-left-color:var(--ygd-ok)}
.ygd-mesh-path .ygd-panel[data-who="bad"]{border-left-color:var(--ygd-bad)}
.ygd-mesh-path .ygd-panel[data-who="warn"]{border-left-color:var(--ygd-warn)}
.ygd-mesh-path .ygd-count{font-size:13px;color:var(--ygd-muted)}
.ygd-mesh-path .ygd-stitle{font-size:15px;font-weight:700;margin-top:4px}
.ygd-mesh-path .ygd-desc{font-size:14px;margin-top:2px;overflow-wrap:anywhere}
.ygd-mesh-path .ygd-analogy{font-size:13px;color:var(--ygd-muted);margin-top:10px;overflow-wrap:anywhere}
@media (prefers-reduced-motion:no-preference){
.ygd-mesh-path .ygd-seg{transition:opacity .3s}
.ygd-mesh-path .ygd-seg.ygd-on .ygd-line{animation:ygd-mesh-draw .7s ease forwards}
}
@keyframes ygd-mesh-draw{from{stroke-dasharray:1;stroke-dashoffset:1}to{stroke-dasharray:1;stroke-dashoffset:0}}
</style>
<div class="ygd-title">서비스 메시에서 요청이 지나는 경로</div>
<div class="ygd-toggle" role="group" aria-label="시나리오 선택">
<button type="button" class="ygd-btn ygd-tab" data-sc="ok" aria-pressed="true">허용된 서비스</button>
<button type="button" class="ygd-btn ygd-tab" data-sc="deny" aria-pressed="false">허용 안 된 서비스</button>
<button type="button" class="ygd-btn ygd-tab" data-sc="strict" aria-pressed="false">평문 요청 · STRICT</button>
<button type="button" class="ygd-btn ygd-tab" data-sc="perm" aria-pressed="false">평문 요청 · PERMISSIVE</button>
</div>
<div class="ygd-modenote" data-role="note"></div>
<svg class="ygd-svg" viewBox="0 0 360 226" role="img" aria-label="서비스 메시 요청 경로 다이어그램. 호출하는 쪽 앱이 평문 HTTP로 자기 Envoy 사이드카에 요청하고, 두 Envoy가 mTLS로 통신하며, 받는 쪽 Envoy가 정책을 판정한 뒤 payment-service 앱에 평문 HTTP로 전달한다.">
<rect class="ygd-pod" x="8" y="18" width="140" height="196" rx="10"/>
<rect class="ygd-pod" x="212" y="18" width="140" height="196" rx="10"/>
<text class="ygd-ptitle" x="78" y="34" data-role="podl">Pod: order-service</text>
<text class="ygd-ptitle" x="282" y="34">Pod: payment-service</text>
<rect class="ygd-node-app" x="28" y="48" width="100" height="42" rx="8"/>
<text class="ygd-ntext" x="78" y="66" data-role="appl">order-service</text>
<text class="ygd-nsub" x="78" y="81">애플리케이션</text>
<rect class="ygd-node-env ygd-envl" x="28" y="148" width="100" height="42" rx="8"/>
<text class="ygd-ntext" x="78" y="166" data-role="envl">Envoy</text>
<text class="ygd-nsub" x="78" y="181" data-role="envlsub">사이드카 프록시</text>
<rect class="ygd-node-app" x="232" y="48" width="100" height="42" rx="8"/>
<text class="ygd-ntext" x="282" y="66">payment-service</text>
<text class="ygd-nsub" x="282" y="81">애플리케이션</text>
<rect class="ygd-node-env" data-role="envb" x="232" y="148" width="100" height="42" rx="8"/>
<text class="ygd-ntext" x="282" y="166">Envoy</text>
<text class="ygd-nsub" x="282" y="181">사이드카 프록시</text>
<g class="ygd-seg ygd-seg-s1" data-seg="s1">
<line class="ygd-line ygd-ln-plain" x1="78" y1="92" x2="78" y2="138" pathLength="1"/>
<polygon class="ygd-fill-plain" points="78,146 73.5,137 82.5,137"/>
<text class="ygd-lbl" x="86" y="122">평문 HTTP</text>
</g>
<g class="ygd-seg" data-seg="s2">
<line class="ygd-line ygd-ln-mtls" x1="130" y1="170" x2="222" y2="170" pathLength="1"/>
<polygon class="ygd-fill-mtls" points="230,170 221,165.5 221,174.5"/>
<text class="ygd-lbl ygd-lbl-c" x="180" y="162" data-role="lbl2">mTLS</text>
</g>
<g class="ygd-seg" data-seg="s4">
<line class="ygd-line ygd-ln-plain" x1="282" y1="146" x2="282" y2="100" pathLength="1"/>
<polygon class="ygd-fill-plain" points="282,92 277.5,101 286.5,101"/>
<text class="ygd-lbl" x="290" y="122">평문 HTTP</text>
</g>
<circle class="ygd-badge" data-role="badge" cx="332" cy="148" r="11"/>
<text class="ygd-tick" data-role="tick" x="332" y="153"></text>
<text class="ygd-nsub" x="180" y="223">파선 테두리 = Pod 경계</text>
</svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전</button>
<button type="button" class="ygd-btn" data-act="next">다음</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
<div class="ygd-panel" data-who="n" role="status" aria-live="polite">
<div class="ygd-count" data-role="count"></div>
<div class="ygd-stitle" data-role="title"></div>
<div class="ygd-desc" data-role="desc"></div>
</div>
<div class="ygd-analogy">비유: 건물 로비의 보안 데스크에 가깝다. 사무실 직원(앱)은 평소처럼 일하고, 출입증 확인은 양쪽 로비 데스크(Envoy)가 맡는다. 어디까지나 비유이며, 실제 허용 여부는 인증서에서 얻은 서비스 ID와 AuthorizationPolicy로 판정한다.</div>
<script>
(function () {
  var root = document.getElementById('ygd-mesh-path');
  if (!root) return;
  var tabs = root.querySelectorAll('.ygd-tab');
  var segs = root.querySelectorAll('.ygd-seg');
  var playBtn = root.querySelector('[data-act="play"]');
  var prevBtn = root.querySelector('[data-act="prev"]');
  var nextBtn = root.querySelector('[data-act="next"]');
  var resetBtn = root.querySelector('[data-act="reset"]');
  var panel = root.querySelector('.ygd-panel');
  var elCount = root.querySelector('[data-role="count"]');
  var elTitle = root.querySelector('[data-role="title"]');
  var elDesc = root.querySelector('[data-role="desc"]');
  var elNote = root.querySelector('[data-role="note"]');
  var elPodL = root.querySelector('[data-role="podl"]');
  var elAppL = root.querySelector('[data-role="appl"]');
  var elEnvL = root.querySelector('[data-role="envl"]');
  var elEnvLSub = root.querySelector('[data-role="envlsub"]');
  var elLbl2 = root.querySelector('[data-role="lbl2"]');
  var elEnvB = root.querySelector('[data-role="envb"]');
  var badge = root.querySelector('[data-role="badge"]');
  var tick = root.querySelector('[data-role="tick"]');
  var GLYPH = { ok: '✓', bad: '✕', warn: '!' };
  var SC = {
    ok: {
      note: 'order-service가 payment-service의 POST /api/v1/payments를 호출한다. AuthorizationPolicy의 principals에 order-service가 들어 있는 정상 경로다.',
      podL: 'Pod: order-service', appL: 'order-service', envL: 'Envoy', envLSub: '사이드카 프록시', plain: false,
      steps: [
        { seg: 's1', who: 'ok', title: '① 앱은 평문 HTTP로 요청한다',
          d: '애플리케이션은 mTLS를 직접 다루지 않고 평문 HTTP로 요청한다. 같은 Pod의 Envoy 사이드카가 이 요청을 받아 간다.' },
        { seg: 's2', who: 'ok', title: '② Envoy끼리 mTLS로 통신한다',
          d: '서비스 간 통신은 실제로 Envoy-to-Envoy 통신이다. 양쪽 Envoy가 서로의 인증서를 검증하고, 받는 쪽은 인증서로 호출자의 서비스 ID를 알게 된다.' },
        { seg: 'eb', badge: 'ok', who: 'ok', title: '③ AuthorizationPolicy를 통과한다',
          d: '호출자 ID가 cluster.local/ns/production/sa/order-service이고 요청이 POST /api/v1/payments라서 정책의 principals, methods, paths 조건에 맞는다.' },
        { seg: 's4', who: 'ok', title: '④ payment-service 앱으로 전달된다',
          d: 'Envoy가 요청을 평문 HTTP로 앱에 넘긴다. 앱 코드는 인증서 처리를 하지 않아도 된다.' }
      ]
    },
    deny: {
      note: '정책의 principals에 없는 다른 서비스가 payment-service를 호출한다. 문서의 설명대로 403이 반환된다.',
      podL: 'Pod: 다른 서비스', appL: '다른 서비스', envL: 'Envoy', envLSub: '사이드카 프록시', plain: false,
      steps: [
        { seg: 's1', who: 'n', title: '① 앱은 평문 HTTP로 요청한다',
          d: '호출하는 쪽 앱이 평문 HTTP로 요청하고, 같은 Pod의 Envoy가 이를 받아 간다.' },
        { seg: 's2', who: 'n', title: '② Envoy끼리 mTLS로 통신한다',
          d: 'mTLS로 호출자가 어떤 서비스인지는 식별된다. 다만 식별되는 것과 접근이 허용되는 것은 별개다.' },
        { seg: 'eb', badge: 'bad', who: 'bad', title: '③ 정책에 없는 호출자라 403',
          d: '호출자 ID가 AuthorizationPolicy의 principals에 없다. 요청은 payment-service 앱에 닿지 못하고 403이 반환된다.' }
      ]
    },
    strict: {
      note: 'mTLS를 쓰지 않는 클라이언트가 payment-service에 평문 HTTP로 직접 접근한다. 네임스페이스는 mode: STRICT 상태다.',
      podL: 'mTLS 없는 호출자', appL: '클라이언트', envL: '사이드카 없음', envLSub: '', plain: true,
      steps: [
        { seg: 's2', who: 'warn', title: '① 평문 HTTP 요청이 도착한다',
          d: '호출자는 인증서 없이 평문 HTTP로 payment-service 쪽에 접근한다.' },
        { seg: 'eb', badge: 'bad', who: 'bad', title: '② STRICT 모드에서 거부된다',
          d: 'STRICT 모드에서는 해당 네임스페이스의 모든 서비스가 mTLS 없이는 통신할 수 없다. 평문 요청은 앱에 도달하지 못한다.' }
      ]
    },
    perm: {
      note: '같은 평문 요청이지만 네임스페이스가 mode: PERMISSIVE 상태다. 마이그레이션 과정에서만 쓰는 모드다.',
      podL: 'mTLS 없는 호출자', appL: '클라이언트', envL: '사이드카 없음', envLSub: '', plain: true,
      steps: [
        { seg: 's2', who: 'warn', title: '① 평문 HTTP 요청이 도착한다',
          d: '호출자는 인증서 없이 평문 HTTP로 payment-service 쪽에 접근한다.' },
        { seg: 'eb', badge: 'warn', who: 'warn', title: '② PERMISSIVE 모드에서는 수용된다',
          d: 'PERMISSIVE 모드는 mTLS와 평문 HTTP를 동시에 허용한다. 그래서 평문 요청도 걸러지지 않는다.' },
        { seg: 's4', who: 'warn', title: '③ 호출자 인증 없이 앱까지 전달된다',
          d: '평문 요청이라 호출자를 인증서로 확인할 수 없는 채로 앱까지 전달된다. 운영에서는 반드시 STRICT로 전환해야 하는 이유다.' }
      ]
    }
  };
  var key = 'ok';
  var cur = 0;
  var timer = null;
  function sc() { return SC[key]; }
  function isLast() { return cur === sc().steps.length; }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function render() {
    var s = sc();
    root.classList.toggle('ygd-plain', s.plain);
    elNote.textContent = s.note;
    elPodL.textContent = s.podL;
    elAppL.textContent = s.appL;
    elEnvL.textContent = s.envL;
    elEnvLSub.textContent = s.envLSub;
    elLbl2.textContent = s.plain ? '평문 HTTP' : 'mTLS';
    Array.prototype.forEach.call(tabs, function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-sc') === key ? 'true' : 'false');
    });
    Array.prototype.forEach.call(segs, function (g) {
      var id = g.getAttribute('data-seg');
      var at = -1, i;
      for (i = 0; i < s.steps.length; i++) { if (s.steps[i].seg === id) { at = i + 1; break; } }
      g.classList.remove('ygd-on', 'ygd-done', 'ygd-none');
      if (at < 0) g.classList.add('ygd-none');
      else if (at === cur) g.classList.add('ygd-on');
      else if (at < cur) g.classList.add('ygd-done');
    });
    elEnvB.classList.toggle('ygd-hl', cur > 0 && s.steps[cur - 1].seg === 'eb');
    var bd = null, j;
    for (j = 0; j < cur; j++) { if (s.steps[j].badge) bd = s.steps[j].badge; }
    badge.setAttribute('class', 'ygd-badge' + (bd ? ' ygd-bd-' + bd : ''));
    tick.setAttribute('class', 'ygd-tick' + (bd ? ' ygd-on' : ''));
    tick.textContent = bd ? GLYPH[bd] : '';
    if (cur === 0) {
      elCount.textContent = '준비';
      panel.setAttribute('data-who', 'n');
      elTitle.textContent = '재생을 눌러 시작';
      elDesc.textContent = '재생을 누르면 요청이 지나가는 경로가 단계별로 진행된다. 위에서 시나리오를 바꿔 결과를 비교할 수 있다.';
    } else {
      var d = s.steps[cur - 1];
      elCount.textContent = '단계 ' + cur + ' / ' + s.steps.length;
      panel.setAttribute('data-who', d.who);
      elTitle.textContent = d.title;
      elDesc.textContent = d.d;
    }
    prevBtn.disabled = cur === 0;
    nextBtn.disabled = isLast();
    playBtn.textContent = timer ? '일시정지' : (isLast() ? '다시 재생' : '재생');
  }
  function tick2() {
    if (!document.body.contains(root)) { stop(); return; }
    if (!isLast()) cur++;
    if (isLast()) stop();
    render();
  }
  function play() {
    if (timer) { stop(); render(); return; }
    if (cur === 0 || isLast()) { cur = 1; }
    if (!isLast()) timer = setInterval(tick2, 2800);
    render();
  }
  playBtn.addEventListener('click', play);
  prevBtn.addEventListener('click', function () { stop(); if (cur > 0) cur--; render(); });
  nextBtn.addEventListener('click', function () { stop(); if (!isLast()) cur++; render(); });
  resetBtn.addEventListener('click', function () { stop(); cur = 0; render(); });
  Array.prototype.forEach.call(tabs, function (b) {
    b.addEventListener('click', function () { stop(); key = b.getAttribute('data-sc'); cur = 0; render(); });
  });
  render();
})();
</script>
</div>

## 인증서 구조와 CA 운영

### 인증서 체인

mTLS를 운영하려면 인증서 체인을 이해해야 한다:

- **Root CA**: 최상위 인증 기관. 자체 서명 인증서를 가진다. 오프라인으로 보관하는 게 원칙이다.
- **Intermediate CA**: Root CA가 서명한 중간 CA. 실제 서비스 인증서 발급에 사용한다.
- **Leaf Certificate**: 각 서비스에 발급되는 인증서. Intermediate CA가 서명한다.

Root CA의 개인키가 유출되면 전체 PKI가 무너진다. 그래서 Root CA는 HSM(Hardware Security Module)에 보관하고, 네트워크에 연결하지 않는다. 일상적인 인증서 발급은 Intermediate CA가 담당한다.

### 인증서에 들어가는 정보

서비스용 인증서에는 최소한 이 정보가 들어간다:

- **CN(Common Name)**: 서비스 식별 이름. 예: `order-service.production.svc.cluster.local`
- **SAN(Subject Alternative Name)**: DNS 이름이나 IP 주소. CN보다 SAN을 우선 검증하는 게 표준이다.
- **유효 기간**: 짧을수록 안전하다. 서비스 인증서는 보통 24시간~90일.
- **Key Usage**: `Digital Signature`, `Key Encipherment` 등. 인증서의 용도를 제한한다.

```bash
# 인증서 내용 확인
openssl x509 -in service.crt -text -noout

# 인증서 체인 검증
openssl verify -CAfile ca-chain.crt service.crt

# mTLS 연결 테스트
openssl s_client -connect payment-service:443 \
  -cert client.crt \
  -key client.key \
  -CAfile ca.crt
```

## 인증서 갱신 자동화

인증서 만료는 운영 사고의 단골 원인이다. 수동 갱신은 반드시 실수가 생긴다. 자동화는 선택이 아니다.

### cert-manager (쿠버네티스 환경)

쿠버네티스에서는 cert-manager가 표준이다. 인증서 발급, 갱신, 시크릿 저장을 자동으로 처리한다.

```yaml
# Issuer 정의 — 내부 CA 사용
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: internal-ca-issuer
spec:
  ca:
    secretName: internal-ca-keypair

---
# 서비스별 인증서 요청
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: order-service-cert
  namespace: production
spec:
  secretName: order-service-tls
  duration: 720h        # 30일
  renewBefore: 168h     # 만료 7일 전에 갱신
  issuerRef:
    name: internal-ca-issuer
    kind: ClusterIssuer
  commonName: order-service.production.svc.cluster.local
  dnsNames:
  - order-service.production.svc.cluster.local
  - order-service.production.svc
  - order-service
  privateKey:
    algorithm: ECDSA
    size: 256
```

`renewBefore` 설정이 핵심이다. 만료 7일 전에 갱신을 시작하면, 갱신에 실패하더라도 대응할 시간이 있다. 인증서 만료까지 갱신 재시도를 반복한다.

### Vault PKI (비쿠버네티스 환경)

HashiCorp Vault의 PKI 시크릿 엔진을 사용하면 온프레미스 환경에서도 자동화가 가능하다.

```bash
# PKI 엔진 활성화
vault secrets enable pki
vault secrets tune -max-lease-ttl=87600h pki

# Root CA 생성
vault write pki/root/generate/internal \
  common_name="Internal Root CA" \
  ttl=87600h

# Intermediate CA 설정
vault secrets enable -path=pki_int pki
vault write pki_int/intermediate/generate/internal \
  common_name="Internal Intermediate CA"

# Role 생성 — 서비스별 인증서 발급 정책
vault write pki_int/roles/service-cert \
  allowed_domains="production.svc.cluster.local" \
  allow_subdomains=true \
  max_ttl=720h

# 인증서 발급
vault write pki_int/issue/service-cert \
  common_name="order-service.production.svc.cluster.local" \
  ttl=720h
```

Vault Agent를 서비스와 함께 실행하면 인증서 만료 전 자동 갱신이 가능하다. Agent가 Vault에서 새 인증서를 받아오고, 파일을 교체한 뒤 서비스에 reload 시그널을 보낸다.

### 만료 모니터링

자동화를 했어도 모니터링은 반드시 해야 한다. 자동화가 실패할 수 있기 때문이다.

```bash
# 인증서 만료일 확인
openssl x509 -in service.crt -enddate -noout

# 만료까지 남은 일수 계산
expiry=$(openssl x509 -in service.crt -enddate -noout | cut -d= -f2)
expiry_epoch=$(date -d "$expiry" +%s)
now_epoch=$(date +%s)
days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
echo "Days until expiry: $days_left"
```

Prometheus를 쓴다면 `x509_cert_not_after` 메트릭으로 인증서 만료를 추적하고, 7일 이내면 알림을 보내는 규칙을 설정한다.

<div class="ygd-cert-renew" id="ygd-cert-renew">
<style>
.ygd-cert-renew{--ygd-bg:#FAF8F6;--ygd-panel:#FFFFFF;--ygd-border:#D9D3CC;--ygd-text:#2B2724;--ygd-muted:#6B655F;--ygd-ok:#2E7D4F;--ygd-ok-bg:#DDF0E4;--ygd-warn:#B4530A;--ygd-warn-bg:#FBEBDD;--ygd-bad:#B3261E;--ygd-bad-bg:#F8DEDB;--ygd-mark:#1F5FA8;--ygd-btn-bg:#FFFFFF;--ygd-btn-text:#2B2724;--ygd-btn-on-bg:#2B2724;--ygd-btn-on-text:#FAF8F6;--ygd-focus:#1F5FA8;font-family:inherit;font-size:15px;line-height:1.5;color:var(--ygd-text);background:var(--ygd-bg);border:1px solid var(--ygd-border);border-radius:12px;padding:14px;margin:1.2em auto;box-sizing:border-box;max-width:760px}
body[data-md-color-scheme="slate"] .ygd-cert-renew{--ygd-bg:#262326;--ygd-panel:#2F2B2E;--ygd-border:#4A4448;--ygd-text:#F0EDE9;--ygd-muted:#A8A29B;--ygd-ok:#6FCB93;--ygd-ok-bg:#1F3A2B;--ygd-warn:#F0A867;--ygd-warn-bg:#4A3220;--ygd-bad:#F2877F;--ygd-bad-bg:#4F2623;--ygd-mark:#7DB4F0;--ygd-btn-bg:#332F32;--ygd-btn-text:#F0EDE9;--ygd-btn-on-bg:#F0EDE9;--ygd-btn-on-text:#262326;--ygd-focus:#7DB4F0}
.ygd-cert-renew .ygd-title{font-weight:700;font-size:16px;margin-bottom:8px}
.ygd-cert-renew .ygd-toggle{display:flex;flex-wrap:wrap;gap:8px}
.ygd-cert-renew .ygd-btn{flex:1 1 140px;font:inherit;font-size:14px;min-height:40px;padding:6px 12px;border-radius:8px;border:1.5px solid var(--ygd-border);background:var(--ygd-btn-bg);color:var(--ygd-btn-text);cursor:pointer;box-sizing:border-box}
.ygd-cert-renew .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-cert-renew .ygd-btn[aria-pressed="true"],.ygd-cert-renew .ygd-primary{background:var(--ygd-btn-on-bg);color:var(--ygd-btn-on-text);border-color:var(--ygd-btn-on-bg)}
.ygd-cert-renew .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-cert-renew .ygd-modenote{font-size:14px;color:var(--ygd-muted);margin:8px 0 6px;overflow-wrap:anywhere}
.ygd-cert-renew .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-cert-renew .ygd-seg-ok{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok);stroke-width:1.5}
.ygd-cert-renew .ygd-seg-warn{fill:var(--ygd-warn-bg);stroke:var(--ygd-warn);stroke-width:1.5}
.ygd-cert-renew.ygd-expired .ygd-seg-warn{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad)}
.ygd-cert-renew .ygd-newbar{display:none;fill:var(--ygd-ok-bg);stroke:var(--ygd-ok);stroke-width:1.5}
.ygd-cert-renew .ygd-newtxt{display:none}
.ygd-cert-renew.ygd-has-new .ygd-newbar,.ygd-cert-renew.ygd-has-new .ygd-newtxt{display:inline}
.ygd-cert-renew .ygd-t{fill:var(--ygd-text);font-size:10.5px}
.ygd-cert-renew .ygd-t-m{text-anchor:middle}
.ygd-cert-renew .ygd-t-e{text-anchor:end}
.ygd-cert-renew .ygd-t-mut{fill:var(--ygd-muted)}
.ygd-cert-renew .ygd-axis{stroke:var(--ygd-muted);stroke-width:1.5}
.ygd-cert-renew .ygd-mark{fill:var(--ygd-mark)}
.ygd-cert-renew .ygd-markline{stroke:var(--ygd-mark);stroke-width:2;stroke-dasharray:3 3}
.ygd-cert-renew .ygd-bell{fill:none;stroke:var(--ygd-muted);stroke-width:1.5}
.ygd-cert-renew .ygd-bell.ygd-lit{fill:var(--ygd-bad);stroke:var(--ygd-bad)}
.ygd-cert-renew .ygd-bells{display:none}
.ygd-cert-renew.ygd-is-fail .ygd-bells{display:inline}
.ygd-cert-renew .ygd-xmark{display:none;stroke:var(--ygd-bad);stroke-width:3;stroke-linecap:round}
.ygd-cert-renew.ygd-expired .ygd-xmark{display:inline}
.ygd-cert-renew .ygd-down{display:none;fill:var(--ygd-bad);font-size:11px;font-weight:700;text-anchor:middle}
.ygd-cert-renew.ygd-expired .ygd-down{display:inline}
.ygd-cert-renew .ygd-legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--ygd-muted);margin:6px 0 10px}
.ygd-cert-renew .ygd-sw{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:4px;box-sizing:border-box;border:2px solid}
.ygd-cert-renew .ygd-sw-ok{background:var(--ygd-ok-bg);border-color:var(--ygd-ok)}
.ygd-cert-renew .ygd-sw-warn{background:var(--ygd-warn-bg);border-color:var(--ygd-warn)}
.ygd-cert-renew .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px}
.ygd-cert-renew .ygd-ctrl .ygd-btn{flex:1 1 70px}
.ygd-cert-renew .ygd-panel{border:1px solid var(--ygd-border);border-left:6px solid var(--ygd-muted);background:var(--ygd-panel);border-radius:8px;padding:10px 12px;margin-top:10px;box-sizing:border-box}
.ygd-cert-renew .ygd-panel[data-who="ok"]{border-left-color:var(--ygd-ok)}
.ygd-cert-renew .ygd-panel[data-who="warn"]{border-left-color:var(--ygd-warn)}
.ygd-cert-renew .ygd-panel[data-who="bad"]{border-left-color:var(--ygd-bad)}
.ygd-cert-renew .ygd-count{font-size:13px;color:var(--ygd-muted)}
.ygd-cert-renew .ygd-stitle{font-size:15px;font-weight:700;margin-top:4px}
.ygd-cert-renew .ygd-desc{font-size:14px;margin-top:2px;overflow-wrap:anywhere}
.ygd-cert-renew .ygd-analogy{font-size:13px;color:var(--ygd-muted);margin-top:10px;overflow-wrap:anywhere}
@media (prefers-reduced-motion:no-preference){
.ygd-cert-renew .ygd-marker{transition:transform .6s ease}
}
</style>
<div class="ygd-title">인증서 수명과 자동 갱신 타임라인</div>
<div class="ygd-toggle" role="group" aria-label="갱신 결과 선택">
<button type="button" class="ygd-btn ygd-tab" data-sc="ok" aria-pressed="true">갱신 성공</button>
<button type="button" class="ygd-btn ygd-tab" data-sc="fail" aria-pressed="false">갱신 계속 실패</button>
</div>
<div class="ygd-modenote" data-role="note"></div>
<svg class="ygd-svg" viewBox="0 0 360 190" role="img" aria-label="인증서 수명 타임라인. 0일에 30일짜리 인증서가 발급되고, 23일째부터 만료 7일 전 갱신 구간이 시작된다. 갱신에 성공하면 새 인증서가 이어지고, 계속 실패하면 30일째 만료되어 통신이 중단된다.">
<rect class="ygd-seg-ok" x="20" y="70" width="245" height="24"/>
<rect class="ygd-seg-warn" x="265" y="70" width="75" height="24"/>
<text class="ygd-t ygd-t-m" x="142" y="86">유효 · 정상 사용</text>
<text class="ygd-t ygd-t-m" x="302" y="86">갱신 구간</text>
<line class="ygd-axis" x1="20" y1="98" x2="20" y2="104"/>
<line class="ygd-axis" x1="265" y1="98" x2="265" y2="104"/>
<line class="ygd-axis" x1="340" y1="98" x2="340" y2="104"/>
<text class="ygd-t ygd-t-mut" x="20" y="116">0일 발급</text>
<text class="ygd-t ygd-t-mut ygd-t-m" x="258" y="116">23일</text>
<text class="ygd-t ygd-t-mut ygd-t-e" x="344" y="116">30일 만료</text>
<g class="ygd-bells">
<circle class="ygd-bell" data-k="1" cx="265" cy="52" r="5"/>
<circle class="ygd-bell" data-k="2" cx="308" cy="52" r="5"/>
<circle class="ygd-bell" data-k="3" cx="329" cy="52" r="5"/>
<text class="ygd-t ygd-t-mut" x="20" y="56">알림 ○ 7일 · 3일 · 1일 전</text>
</g>
<g class="ygd-marker" data-role="marker" style="transform:translateX(0px)">
<line class="ygd-markline" x1="20" y1="30" x2="20" y2="70"/>
<polygon class="ygd-mark" points="20,34 14,22 26,22"/>
</g>
<rect class="ygd-newbar" x="265" y="136" width="87" height="24" rx="2"/>
<text class="ygd-t ygd-t-m ygd-newtxt" x="308" y="152">새 인증서</text>
<g class="ygd-xmark"><line x1="334" y1="64" x2="346" y2="100"/><line x1="346" y1="64" x2="334" y2="100"/></g>
<text class="ygd-down" x="180" y="152">서비스 간 통신 중단</text>
</svg>
<div class="ygd-legend">
<span><span class="ygd-sw ygd-sw-ok"></span>인증서 유효 기간</span>
<span><span class="ygd-sw ygd-sw-warn"></span>renewBefore 7일 구간</span>
<span>파란 표시: 현재 시점</span>
</div>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="prev">이전</button>
<button type="button" class="ygd-btn" data-act="next">다음</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
<div class="ygd-panel" data-who="n" role="status" aria-live="polite">
<div class="ygd-count" data-role="count"></div>
<div class="ygd-stitle" data-role="title"></div>
<div class="ygd-desc" data-role="desc"></div>
</div>
<div class="ygd-analogy">비유: 여권 유효 기간에 가깝다. 만료 직전에 갱신하면 여행 중에 막히고, 여유를 두고 갱신하면 문제가 생겨도 고칠 시간이 남는다. 어디까지나 비유이며, 여기서의 날짜는 문서의 duration 720h, renewBefore 168h 설정을 기준으로 한 예시다.</div>
<script>
(function () {
  var root = document.getElementById('ygd-cert-renew');
  if (!root) return;
  var tabs = root.querySelectorAll('.ygd-tab');
  var bells = root.querySelectorAll('.ygd-bell');
  var playBtn = root.querySelector('[data-act="play"]');
  var prevBtn = root.querySelector('[data-act="prev"]');
  var nextBtn = root.querySelector('[data-act="next"]');
  var resetBtn = root.querySelector('[data-act="reset"]');
  var panel = root.querySelector('.ygd-panel');
  var elCount = root.querySelector('[data-role="count"]');
  var elTitle = root.querySelector('[data-role="title"]');
  var elDesc = root.querySelector('[data-role="desc"]');
  var elNote = root.querySelector('[data-role="note"]');
  var marker = root.querySelector('[data-role="marker"]');
  function xOf(day) { return day * 320 / 30; }
  var START = { day: 0, who: 'n', title: '① 인증서 발급', alerts: 0,
    d: 'Certificate 리소스의 duration이 720h(30일)이므로 30일짜리 인증서가 발급되어 시크릿에 저장된다.' };
  var SC = {
    ok: {
      note: 'cert-manager가 renewBefore 시점에 갱신에 성공하는 경우다. 서비스가 새 인증서를 쓰기까지의 과정을 본다.',
      steps: [
        START,
        { day: 23, who: 'warn', title: '② 만료 7일 전 — 갱신 시작', alerts: 0,
          d: 'renewBefore가 168h(7일)이라 만료 7일 전인 23일째부터 cert-manager가 갱신을 시작한다.' },
        { day: 23, who: 'ok', title: '③ 새 인증서가 시크릿에 저장된다', alerts: 0, nu: true,
          d: 'cert-manager가 새 인증서를 발급해 order-service-tls 시크릿을 갱신한다. 기존 인증서는 아직 7일이 남아 있어 서두를 필요가 없다.' },
        { day: 23, who: 'ok', title: '④ 서비스가 새 인증서를 쓰게 한다', alerts: 0, nu: true,
          d: '문서의 NestJS 예제처럼 시작할 때 파일을 한 번만 읽는 코드라면, 파일이 바뀌어도 반영되지 않는다. 서비스를 재시작하거나 파일을 주기적으로 다시 읽도록 처리해야 한다.' }
      ]
    },
    fail: {
      note: '갱신이 계속 실패하는 경우다. 자동화를 했어도 모니터링이 필요한 이유를 본다. 알림은 만료 7일 전, 3일 전, 1일 전에 보내도록 한 설정을 가정한다.',
      steps: [
        START,
        { day: 23, who: 'warn', title: '② 갱신이 실패한다 — 7일 전 알림', alerts: 1,
          d: '갱신을 시작했지만 실패한다. 아직 7일이 남아 있어 갱신에 실패하더라도 대응할 시간이 있다.' },
        { day: 27, who: 'warn', title: '③ 재시도 중 — 3일 전 알림', alerts: 2,
          d: '인증서가 만료될 때까지 갱신 재시도는 반복된다. 그래도 원인이 해결되지 않으면 3일 전 알림이 이어진다.' },
        { day: 29, who: 'bad', title: '④ 만료 1일 전 — 마지막 알림', alerts: 3,
          d: '마지막 알림이다. 자동화가 실패할 수 있기 때문에 모니터링과 알림은 자동화와 별개로 반드시 필요하다.' },
        { day: 30, who: 'bad', title: '⑤ 만료 — 서비스 간 통신이 끊긴다', alerts: 3, expired: true,
          d: '인증서가 만료되면 서비스 간 통신이 전부 끊긴다. 새벽에 만료되면 아침에 출근했을 때 장애 상태인 걸 발견하게 된다.' }
      ]
    }
  };
  var key = 'ok';
  var cur = 0;
  var timer = null;
  function steps() { return SC[key].steps; }
  function isLast() { return cur === steps().length; }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }
  function render() {
    var s = steps();
    elNote.textContent = SC[key].note;
    root.classList.toggle('ygd-is-fail', key === 'fail');
    Array.prototype.forEach.call(tabs, function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-sc') === key ? 'true' : 'false');
    });
    var d = cur > 0 ? s[cur - 1] : null;
    var day = d ? d.day : 0;
    var alerts = d ? d.alerts : 0;
    var hasNew = false, i;
    for (i = 0; i < cur; i++) { if (s[i].nu) hasNew = true; }
    marker.style.transform = 'translateX(' + xOf(day) + 'px)';
    root.classList.toggle('ygd-has-new', hasNew);
    root.classList.toggle('ygd-expired', !!(d && d.expired));
    Array.prototype.forEach.call(bells, function (b) {
      b.classList.toggle('ygd-lit', Number(b.getAttribute('data-k')) <= alerts);
    });
    if (!d) {
      elCount.textContent = '준비';
      panel.setAttribute('data-who', 'n');
      elTitle.textContent = '재생을 눌러 시작';
      elDesc.textContent = '재생을 누르면 시간이 흐르며 인증서 상태가 바뀐다. 위에서 갱신 성공과 실패를 바꿔 비교할 수 있다.';
    } else {
      elCount.textContent = '단계 ' + cur + ' / ' + s.length + ' · ' + day + '일째';
      panel.setAttribute('data-who', d.who);
      elTitle.textContent = d.title;
      elDesc.textContent = d.d;
    }
    prevBtn.disabled = cur === 0;
    nextBtn.disabled = isLast();
    playBtn.textContent = timer ? '일시정지' : (isLast() ? '다시 재생' : '재생');
  }
  function tick() {
    if (!document.body.contains(root)) { stop(); return; }
    if (!isLast()) cur++;
    if (isLast()) stop();
    render();
  }
  function play() {
    if (timer) { stop(); render(); return; }
    if (cur === 0 || isLast()) { cur = 1; }
    if (!isLast()) timer = setInterval(tick, 2800);
    render();
  }
  playBtn.addEventListener('click', play);
  prevBtn.addEventListener('click', function () { stop(); if (cur > 0) cur--; render(); });
  nextBtn.addEventListener('click', function () { stop(); if (!isLast()) cur++; render(); });
  resetBtn.addEventListener('click', function () { stop(); cur = 0; render(); });
  Array.prototype.forEach.call(tabs, function (b) {
    b.addEventListener('click', function () { stop(); key = b.getAttribute('data-sc'); cur = 0; render(); });
  });
  render();
})();
</script>
</div>

## Node.js / NestJS mTLS 설정

### 서버 측 설정

Node.js의 `https` 모듈로 mTLS를 활성화한다.

```typescript
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import * as https from 'https';
import * as fs from 'fs';

async function bootstrap(): Promise<void> {
  const httpsOptions: https.ServerOptions = {
    key: fs.readFileSync(process.env.SSL_KEY_PATH ?? 'certs/service.key'),
    cert: fs.readFileSync(process.env.SSL_CERT_PATH ?? 'certs/service.crt'),
    ca: fs.readFileSync(process.env.SSL_CA_PATH ?? 'certs/ca.crt'),
    // mTLS 핵심 설정
    requestCert: true,    // 클라이언트에게 인증서 요청
    rejectUnauthorized: true,  // 유효하지 않은 인증서 거부 (need에 해당)
    // rejectUnauthorized: false → want에 해당 (운영 환경에서는 true 사용)
    minVersion: 'TLSv1.3',
  };

  const app = await NestFactory.create(AppModule, { httpsOptions });
  await app.listen(8443);
}
bootstrap();
```

`rejectUnauthorized: true`가 mTLS를 강제한다. `false`로 설정하면 인증서가 없어도 연결이 허용되므로 운영 환경에서는 반드시 `true`를 써야 한다.

인증서 파일 준비:

- **service.key**: 서비스 자신의 개인키
- **service.crt**: 서비스 자신의 인증서
- **ca.crt**: 클라이언트 인증서를 검증할 CA 인증서

```bash
# 서비스 인증서 + 개인키 생성
openssl ecparam -name prime256v1 -genkey -noout -out service.key
openssl req -new -key service.key -out service.csr \
  -subj "/CN=order-service.production.svc.cluster.local"
openssl x509 -req -in service.csr \
  -CA intermediate-ca.crt -CAkey intermediate-ca.key \
  -CAcreateserial -out service.crt -days 30 -sha256
```

### 클라이언트 측 설정

다른 서비스를 호출할 때도 클라이언트 인증서를 제시해야 한다.

```typescript
// mtls-http.service.ts
import { Injectable } from '@nestjs/common';
import * as https from 'https';
import * as fs from 'fs';
import axios, { AxiosInstance } from 'axios';

@Injectable()
export class MtlsHttpService {
  private readonly client: AxiosInstance;

  constructor() {
    const agent = new https.Agent({
      key: fs.readFileSync(process.env.SSL_KEY_PATH ?? 'certs/service.key'),
      cert: fs.readFileSync(process.env.SSL_CERT_PATH ?? 'certs/service.crt'),
      ca: fs.readFileSync(process.env.SSL_CA_PATH ?? 'certs/ca.crt'),
      rejectUnauthorized: true,
    });

    this.client = axios.create({ httpsAgent: agent });
  }

  async get<T>(url: string): Promise<T> {
    const response = await this.client.get<T>(url);
    return response.data;
  }

  async post<T>(url: string, data: unknown): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }
}
```

환경 변수로 인증서 경로를 관리하고, cert-manager나 Vault Agent가 파일을 갱신하면 서비스를 재시작하거나 파일을 주기적으로 다시 읽도록 처리한다.

## Nginx mTLS 설정

Nginx를 리버스 프록시로 쓰는 경우, Nginx에서 mTLS를 처리하고 백엔드에는 평문으로 전달하는 구조가 일반적이다.

```nginx
server {
    listen 443 ssl;
    server_name api.internal.example.com;

    # 서버 인증서
    ssl_certificate     /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    # mTLS 설정
    ssl_client_certificate /etc/nginx/ssl/ca.crt;    # 클라이언트 인증서를 검증할 CA
    ssl_verify_client on;                             # 클라이언트 인증서 검증 활성화
    ssl_verify_depth 2;                               # 인증서 체인 검증 깊이

    # TLS 프로토콜/암호화 설정
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    # 클라이언트 인증서 정보를 백엔드에 전달
    location / {
        proxy_pass http://backend:8080;
        proxy_set_header X-SSL-Client-DN $ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;
        proxy_set_header X-SSL-Client-Serial $ssl_client_serial;
    }
}
```

주의할 점:

- `ssl_verify_depth`는 인증서 체인의 깊이다. Root CA → Intermediate CA → Leaf Certificate 구조면 2로 설정한다.
- `ssl_client_certificate`에는 클라이언트 인증서를 발급한 CA의 인증서를 넣는다. 클라이언트 인증서 자체가 아니다. 여러 CA를 신뢰해야 하면 인증서를 하나의 파일에 이어 붙인다.
- `$ssl_client_s_dn`으로 클라이언트의 DN(Distinguished Name)을 백엔드에 전달한다. 백엔드에서 이 값으로 서비스를 식별할 수 있다.

### CRL/OCSP 설정

인증서가 유출되면 폐기(revoke)해야 한다. Nginx에서 CRL(Certificate Revocation List)을 설정하는 방법:

```nginx
# CRL 파일 지정
ssl_crl /etc/nginx/ssl/crl.pem;
```

CRL 파일은 주기적으로 업데이트해야 한다. 파일이 오래되면 새로 폐기된 인증서를 차단하지 못한다. cron으로 CA에서 최신 CRL을 가져오는 스크립트를 돌리는 방식이 일반적이다.

## 운영에서 겪는 문제들

### 인증서 만료 사고

가장 흔한 사고다. 인증서가 만료되면 서비스 간 통신이 전부 끊어진다. 새벽에 만료되면 아침에 출근했을 때 장애 상태인 걸 발견하게 된다.

대응:

- 인증서 유효 기간을 짧게 설정하고 자동 갱신을 붙인다. 유효 기간이 짧으면 갱신 주기가 빨라지고, 자동화가 정상 동작하는지 빠르게 확인된다.
- 만료 7일 전, 3일 전, 1일 전에 알림을 보낸다.

### 인증서 체인 불일치

서버 인증서는 있는데 중간 CA 인증서를 빠뜨리는 경우가 있다. 서버 쪽에서 테스트하면 잘 되는데(로컬에 CA 인증서가 설치되어 있으니까), 다른 서비스에서 연결하면 `unable to verify the first certificate` 에러가 난다.

```bash
# 인증서 체인이 올바른지 확인
openssl s_client -connect service:443 -showcerts
```

출력에서 인증서 체인이 Root CA까지 이어지는지 확인한다. 중간에 빠진 인증서가 있으면 서버 인증서 파일에 중간 CA 인증서를 추가해야 한다.

### 시간 동기화 문제

인증서 검증에는 시간이 중요하다. 서버 시간이 틀어져 있으면 유효한 인증서도 만료되었다고 판단하거나, 아직 유효하지 않다고 판단할 수 있다. NTP 동기화가 되어 있는지 확인해야 한다.

### 키 알고리즘 선택

RSA 2048은 아직 안전하지만, 새로 구축한다면 ECDSA P-256을 쓰는 게 낫다. 키 크기가 작아서 핸드셰이크가 빠르고, 같은 보안 수준에서 성능이 좋다.

```bash
# ECDSA 키 생성
openssl ecparam -name prime256v1 -genkey -noout -out service.key

# CSR 생성
openssl req -new -key service.key -out service.csr \
  -subj "/CN=order-service.production.svc.cluster.local"

# 인증서 발급 (CA의 키로 서명)
openssl x509 -req -in service.csr \
  -CA intermediate-ca.crt -CAkey intermediate-ca.key \
  -CAcreateserial \
  -out service.crt \
  -days 30 \
  -sha256 \
  -extfile <(printf "subjectAltName=DNS:order-service.production.svc.cluster.local")
```

### mTLS 디버깅

mTLS 관련 문제가 생기면 OpenSSL로 직접 연결해보는 게 가장 빠르다.

```bash
# 상세 핸드셰이크 로그 확인
openssl s_client -connect service:443 \
  -cert client.crt \
  -key client.key \
  -CAfile ca.crt \
  -state -debug

# 서버가 요구하는 CA 목록 확인
openssl s_client -connect service:443 2>&1 | grep -A5 "Acceptable client certificate CA names"
```

서버가 요구하는 CA 목록에 클라이언트 인증서를 발급한 CA가 포함되어 있는지 확인한다. 여기에 없으면 클라이언트가 아무리 인증서를 보내도 거부된다.
