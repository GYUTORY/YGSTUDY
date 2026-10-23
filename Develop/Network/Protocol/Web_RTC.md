---
title: WebRTC 심화
tags: [network]
updated: 2026-10-23
---

# WebRTC 심화

## 개요

WebRTC는 브라우저나 앱 사이에서 서버를 거치지 않고 직접 미디어와 데이터를 주고받는 기술이다. 화상 통화, 화면 공유, 저지연 게임 데이터 동기화 같은 곳에 쓴다. WebSocket과 헷갈리는 사람이 많은데, WebSocket은 클라이언트-서버 연결이고 WebRTC는 클라이언트-클라이언트(P2P) 연결이다. 다만 P2P 연결을 맺기까지의 과정이 WebSocket보다 훨씬 복잡하다. 두 단말이 서로의 주소를 모르고, 대부분 NAT 뒤에 있어서 공인 IP로 바로 연결되지 않기 때문이다.

WebRTC를 처음 붙일 때 "코드는 다 짰는데 로컬에서는 되고 운영에서는 연결이 안 된다"는 상황을 거의 다 겪는다. 이 문서는 그 연결 과정이 내부에서 어떻게 돌아가는지, 그리고 안 될 때 어디를 봐야 하는지를 중심으로 정리한다.

```
WebSocket:
  Client ──────▶ Server ◀────── Client
  (모든 트래픽이 서버를 경유)

WebRTC:
  Client ◀══════ 직접 연결(P2P) ══════▶ Client
       │                              │
       └──── 시그널링 서버 (연결 수립용) ────┘
  (연결만 서버 도움으로 맺고, 미디어/데이터는 직접)
```

P2P 개념 자체는 [P2P 문서](../P2P.md)에서 다루고, 여기서는 WebRTC가 실제로 그 연결을 어떻게 뚫는지를 본다.

## 전체 연결 흐름

연결이 맺히기까지 크게 세 단계를 거친다.

1. 시그널링: 두 단말이 서로의 정보(SDP, ICE 후보)를 교환한다. 이 교환 통로는 WebRTC가 제공하지 않는다. 직접 만들어야 한다.
2. ICE: 양쪽이 가능한 연결 경로 후보를 모으고, 그중 실제로 통하는 경로를 찾는다.
3. 연결: 찾은 경로로 DTLS 핸드셰이크를 하고 미디어/데이터를 흘린다.

```
A 단말                  시그널링 서버                  B 단말
  │                          │                          │
  │── Offer(SDP) ───────────▶│── Offer 전달 ───────────▶│
  │                          │                          │
  │◀─────────── Answer(SDP) ─│◀──────────── Answer ─────│
  │                          │                          │
  │── ICE 후보 ─────────────▶│── 후보 전달 ────────────▶│
  │◀──────────────── ICE 후보│◀──────────────── ICE 후보│
  │                          │                          │
  │◀════ 연결 점검(STUN 바인딩) ════▶ (서버 안 거침)      │
  │◀═══════ DTLS 핸드셰이크 ═══════▶                      │
  │◀═════ 미디어 / DataChannel ════▶                      │
```

핵심은 시그널링 서버는 연결을 맺을 때까지만 쓰이고, 일단 P2P가 뚫리면 미디어와 데이터는 서버를 거치지 않는다는 점이다. 그래서 서버 대역폭이 사용자 수에 비례해서 폭증하지 않는다. 단 뒤에서 설명할 TURN 릴레이로 떨어지면 이 전제가 깨진다.

<div class="ygd-webrtc-flow" id="ygd-webrtc-flow">
<style>
.ygd-webrtc-flow{--ygd-fg:#2B2724;--ygd-muted:#5F5A54;--ygd-line:#B8B1A8;--ygd-sig:#3D7387;--ygd-p2p:#A24E12;--ygd-bg:#FDFBFA;--ygd-panel:#F3EFEA;--ygd-btn:#3D7387;--ygd-btnfg:#FFFFFF;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1.5em;margin-bottom:1.5em;color:var(--ygd-fg);box-sizing:border-box}
body[data-md-color-scheme="slate"] .ygd-webrtc-flow{--ygd-fg:#F0EDE9;--ygd-muted:#B5AEA5;--ygd-line:#6B655E;--ygd-sig:#7FB9CF;--ygd-p2p:#F0A868;--ygd-bg:#1F1C1E;--ygd-panel:#2B2729;--ygd-btn:#7FB9CF;--ygd-btnfg:#1F1C1E}
.ygd-webrtc-flow *{box-sizing:border-box}
.ygd-webrtc-flow .ygd-note{font-size:14px;line-height:1.6;color:var(--ygd-muted);margin:0 0 10px 0}
.ygd-webrtc-flow .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-webrtc-flow .ygd-life{stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:4 4}
.ygd-webrtc-flow .ygd-box{fill:var(--ygd-panel);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-webrtc-flow .ygd-boxt{fill:var(--ygd-fg);font-size:13px;font-weight:600}
.ygd-webrtc-flow .ygd-row{opacity:.5;transition:opacity .3s}
.ygd-webrtc-flow .ygd-row.ygd-done{opacity:.8}
.ygd-webrtc-flow .ygd-row.ygd-on{opacity:1}
.ygd-webrtc-flow .ygd-ln{stroke-width:2;fill:none}
.ygd-webrtc-flow .ygd-on .ygd-ln{stroke-width:3;stroke-dasharray:var(--ygd-len);animation:ygd-webrtc-flow-draw .5s ease-out both}
.ygd-webrtc-flow .ygd-on .ygd-hd{animation:ygd-webrtc-flow-fade .3s both}
.ygd-webrtc-flow .ygd-sig .ygd-ln{stroke:var(--ygd-sig)}
.ygd-webrtc-flow .ygd-sig .ygd-hd,.ygd-webrtc-flow .ygd-sig .ygd-num{fill:var(--ygd-sig)}
.ygd-webrtc-flow .ygd-p2p .ygd-ln{stroke:var(--ygd-p2p)}
.ygd-webrtc-flow .ygd-p2p .ygd-hd,.ygd-webrtc-flow .ygd-p2p .ygd-num{fill:var(--ygd-p2p)}
.ygd-webrtc-flow .ygd-numt{fill:var(--ygd-bg);font-size:11px;font-weight:700}
.ygd-webrtc-flow .ygd-lb{fill:var(--ygd-fg);font-size:13px;stroke:var(--ygd-bg);stroke-width:4px;paint-order:stroke}
.ygd-webrtc-flow .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.ygd-webrtc-flow .ygd-btn{font:inherit;font-size:14px;line-height:1.2;padding:9px 16px;min-height:40px;border:0;border-radius:6px;background:var(--ygd-btn);color:var(--ygd-btnfg);cursor:pointer}
.ygd-webrtc-flow .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-webrtc-flow .ygd-btn:focus-visible{outline:3px solid var(--ygd-p2p);outline-offset:2px}
.ygd-webrtc-flow .ygd-cnt{font-size:14px;color:var(--ygd-muted)}
.ygd-webrtc-flow .ygd-panel{background:var(--ygd-panel);border-radius:8px;padding:12px 14px;border-left:4px solid var(--ygd-sig)}
.ygd-webrtc-flow .ygd-panel.ygd-p2p{border-left-color:var(--ygd-p2p)}
.ygd-webrtc-flow .ygd-ptitle{font-size:15px;font-weight:700;margin:0 0 4px 0}
.ygd-webrtc-flow .ygd-ptext{font-size:14px;line-height:1.65;margin:0}
@keyframes ygd-webrtc-flow-draw{from{stroke-dashoffset:var(--ygd-len)}to{stroke-dashoffset:0}}
@keyframes ygd-webrtc-flow-fade{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){.ygd-webrtc-flow .ygd-ln,.ygd-webrtc-flow .ygd-hd{animation:none !important}.ygd-webrtc-flow .ygd-row{transition:none}}
</style>
<p class="ygd-note">비유: 시그널링 서버는 두 사람에게 서로의 연락처를 건네주는 소개자다. 연락처만 전달하고 이후 통화에는 끼지 않는다. 단 TURN 릴레이로 떨어지면 이 비유는 맞지 않는다.</p>
<svg class="ygd-svg" viewBox="0 0 480 320" role="img" aria-label="WebRTC 연결 흐름 다이어그램. A 단말과 B 단말이 시그널링 서버를 통해 Offer, Answer, ICE 후보를 교환한 뒤, 서버를 거치지 않고 연결 점검, DTLS 핸드셰이크, 미디어 전송을 직접 수행한다."></svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-prev">이전</button>
<button type="button" class="ygd-btn ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-next">다음</button>
<span class="ygd-cnt" aria-hidden="true"></span>
</div>
<div class="ygd-panel" aria-live="polite">
<p class="ygd-ptitle"></p>
<p class="ygd-ptext"></p>
</div>
<script>
(function(){
var root=document.getElementById('ygd-webrtc-flow');
if(!root)return;
var NS='http://www.w3.org/2000/svg';
var svg=root.querySelector('.ygd-svg');
var A=70,S=240,B=410;
function el(n,a,p,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!==undefined)e.textContent=t;if(p)p.appendChild(e);return e;}
var steps=[
{ph:'sig',t:'1단계 시그널링: Offer 전달',x:'A가 createOffer로 만든 SDP(코덱, 미디어, 암호화 조건)를 시그널링 서버로 보낸다. 서버는 내용을 해석하지 않고 B에게 그대로 전달한다.',s:[[A,S,'Offer(SDP)'],[S,B,'Offer 전달']]},
{ph:'sig',t:'2단계 시그널링: Answer 회신',x:'B는 setRemoteDescription 뒤 createAnswer로 응답을 만들어 같은 경로로 돌려보낸다. 양쪽이 쓸 코덱이 여기서 정해지며, 겹치는 코덱이 없으면 연결이 맺혀도 영상이 나오지 않는다.',s:[[B,S,'Answer(SDP)'],[S,A,'Answer 전달']]},
{ph:'sig',t:'3단계 시그널링: ICE 후보 교환',x:'host, srflx, relay 후보가 발견되는 대로 Trickle ICE로 바로 상대에게 보낸다. 후보가 Answer보다 먼저 도착하면 addIceCandidate가 에러를 내므로 큐에 모아 둔다.',s:[[A,S,'ICE 후보',1],[S,B,'ICE 후보',1]]},
{ph:'p2p',t:'4단계 ICE: 연결 점검',x:'교환한 후보로 쌍을 만들어 host, srflx, relay 우선순위로 STUN 바인딩 요청을 주고받는다. 이 구간부터는 시그널링 서버를 거치지 않으며, 통하는 쌍 중 우선순위가 가장 높은 것으로 연결된다.',s:[[A,B,'연결 점검 · 서버 미경유',1]]},
{ph:'p2p',t:'5단계 연결: DTLS 핸드셰이크',x:'선택된 경로 위에서 DTLS 핸드셰이크를 한다. 이후 DataChannel은 SCTP over DTLS로 전송된다.',s:[[A,B,'DTLS 핸드셰이크',1]]},
{ph:'p2p',t:'6단계 연결: 미디어와 DataChannel',x:'미디어는 RTP/SRTP over UDP로, 데이터는 DataChannel로 서버 없이 직접 흐른다. 다만 TURN relay 후보가 선택됐다면 이 트래픽이 전부 TURN 서버를 거친다.',s:[[A,B,'미디어 / DataChannel',1]]}
];
[[A,'A 단말'],[S,'시그널링 서버'],[B,'B 단말']].forEach(function(h){
el('line',{x1:h[0],y1:42,x2:h[0],y2:318,'class':'ygd-life'},svg);
el('rect',{x:h[0]-60,y:8,width:120,height:34,rx:6,'class':'ygd-box'},svg);
el('text',{x:h[0],y:30,'class':'ygd-boxt','text-anchor':'middle'},svg,h[1]);
});
steps.forEach(function(st,i){
var y=80+i*45;
var g=el('g',{'class':'ygd-row ygd-'+st.ph},svg);
el('circle',{cx:24,cy:y,r:10,'class':'ygd-num'},g);
el('text',{x:24,y:y+4,'class':'ygd-numt','text-anchor':'middle'},g,String(i+1));
st.s.forEach(function(sg,si){
var x1=sg[0],x2=sg[1],d=x2>x1?1:-1;
var ln=el('line',{x1:x1,y1:y,x2:x2,y2:y,'class':'ygd-ln'},g);
ln.style.setProperty('--ygd-len',String(Math.abs(x2-x1)));
ln.style.animationDelay=(si*0.5)+'s';
function head(x,dir){
var p=el('polygon',{points:x+','+y+' '+(x-dir*9)+','+(y-4.5)+' '+(x-dir*9)+','+(y+4.5),'class':'ygd-hd'},g);
p.style.animationDelay=(si*0.5+0.35)+'s';
}
head(x2,d);
if(sg[3])head(x1,-d);
el('text',{x:(x1+x2)/2,y:y-9,'class':'ygd-lb','text-anchor':'middle'},g,sg[2]);
});
st.g=g;
});
var prev=root.querySelector('.ygd-prev'),next=root.querySelector('.ygd-next'),playBtn=root.querySelector('.ygd-play');
var cnt=root.querySelector('.ygd-cnt'),panel=root.querySelector('.ygd-panel');
var ptitle=root.querySelector('.ygd-ptitle'),ptext=root.querySelector('.ygd-ptext');
var cur=0,timer=null;
function show(i){
cur=i;
steps.forEach(function(st,k){
st.g.setAttribute('class','ygd-row ygd-'+st.ph+(k===i?' ygd-on':(k<i?' ygd-done':'')));
});
ptitle.textContent=steps[i].t;
ptext.textContent=steps[i].x;
panel.setAttribute('class','ygd-panel ygd-'+steps[i].ph);
cnt.textContent=(i+1)+' / '+steps.length;
prev.disabled=i===0;
next.disabled=i===steps.length-1;
}
function stop(){
if(timer){clearInterval(timer);timer=null;}
playBtn.textContent='재생';
}
function play(){
if(cur>=steps.length-1)show(0);
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(cur>=steps.length-1){stop();return;}
show(cur+1);
},2800);
}
playBtn.addEventListener('click',function(){if(timer)stop();else play();});
prev.addEventListener('click',function(){stop();if(cur>0)show(cur-1);});
next.addEventListener('click',function(){stop();if(cur<steps.length-1)show(cur+1);});
show(0);
})();
</script>
</div>

## 시그널링 서버

WebRTC 명세에는 시그널링 프로토콜이 없다. 일부러 비워뒀다. 두 단말이 SDP와 ICE 후보를 교환할 통로만 있으면 되고, 그 통로를 WebSocket으로 만들든 HTTP 폴링으로 만들든 상관없다. 보통 WebSocket으로 만든다. 양방향이고 지연이 낮아서 후보 교환에 잘 맞는다.

시그널링 서버가 하는 일은 단순하다. A가 보낸 메시지를 B에게, B가 보낸 메시지를 A에게 전달한다. 메시지 내용을 해석할 필요도 없다. 그냥 상대에게 던져주면 된다.

```javascript
// 시그널링 서버 (Node.js + ws) — 룸 단위 릴레이만 한다
const rooms = new Map(); // roomId -> Set<WebSocket>

wss.on('connection', (ws) => {
  let roomId = null;

  ws.on('message', (raw) => {
    const msg = JSON.parse(raw);

    if (msg.type === 'join') {
      roomId = msg.roomId;
      if (!rooms.has(roomId)) rooms.set(roomId, new Set());
      rooms.get(roomId).add(ws);
      return;
    }

    // offer / answer / candidate 는 같은 방의 다른 사람에게 그대로 전달
    const peers = rooms.get(roomId);
    if (!peers) return;
    for (const peer of peers) {
      if (peer !== ws && peer.readyState === peer.OPEN) {
        peer.send(raw);
      }
    }
  });

  ws.on('close', () => {
    if (roomId && rooms.has(roomId)) {
      rooms.get(roomId).delete(ws);
    }
  });
});
```

여기서 자주 빠뜨리는 게 연결 종료 처리다. close 이벤트에서 룸 set을 비워주지 않으면 끊긴 소켓에 계속 send를 시도하고, 룸 인원 카운트도 틀어진다. 운영하다 보면 "방을 나갔는데 상대 화면에 아직 내가 보인다"는 류의 버그가 여기서 나온다.

시그널링 서버는 연결만 맺어주면 역할이 끝나지만, 실무에서는 보통 연결 유지 동안 켜둔다. 통화 중에 한쪽 네트워크가 바뀌면(와이파이→LTE) ICE 재협상이 일어나고, 새 후보를 다시 교환해야 하기 때문이다.

## SDP 교환

SDP(Session Description Protocol)는 "내가 어떤 코덱을 쓸 수 있고, 어떤 미디어를 보낼 거고, 암호화 키는 뭐고" 같은 연결 조건을 텍스트로 적은 문서다. A가 만든 걸 Offer, B가 그에 답해서 만든 걸 Answer라고 부른다. 이 둘을 교환하면 양쪽이 공통으로 쓸 코덱과 파라미터가 정해진다.

```javascript
// A 단말 (발신)
const pc = new RTCPeerConnection({ iceServers });

const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
stream.getTracks().forEach(track => pc.addTrack(track, stream));

const offer = await pc.createOffer();
await pc.setLocalDescription(offer);
signaling.send({ type: 'offer', sdp: offer.sdp });

// B 단말 (수신)
pc.ondatachannel = ... ;
signaling.on('offer', async (msg) => {
  await pc.setRemoteDescription({ type: 'offer', sdp: msg.sdp });
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  signaling.send({ type: 'answer', sdp: answer.sdp });
});

// 다시 A 단말
signaling.on('answer', async (msg) => {
  await pc.setRemoteDescription({ type: 'answer', sdp: msg.sdp });
});
```

SDP 본문은 이렇게 생겼다. 직접 파싱할 일은 거의 없지만 디버깅할 때 한 번씩 읽게 된다.

```
v=0
o=- 4611731400430051336 2 IN IP4 127.0.0.1
s=-
t=0 0
m=video 9 UDP/TLS/RTP/SAVPF 96 97
a=rtpmap:96 VP8/90000
a=rtpmap:97 H264/90000
a=candidate:1 1 udp 2122260223 192.168.0.10 54321 typ host
a=candidate:2 1 udp 1686052607 203.0.113.5 54321 typ srflx ...
```

`m=` 줄이 미디어 종류, `a=rtpmap` 이 코덱 협상 후보다. A가 VP8과 H264를 둘 다 제시했는데 B가 VP8만 지원하면 결과적으로 VP8로 합의된다. 여기서 양쪽이 겹치는 코덱이 하나도 없으면 연결은 맺혀도 영상이 안 나온다. 모바일에서 H264만 되는 단말과 데스크톱 브라우저를 붙일 때 가끔 이 문제가 난다.

순서도 중요하다. `setRemoteDescription`을 하기 전에 도착한 ICE 후보를 `addIceCandidate`로 넣으면 에러가 난다. 시그널링이 빨라서 후보가 Answer보다 먼저 도착하는 경우가 있어서, remoteDescription이 세팅되기 전 후보는 큐에 모아뒀다가 나중에 넣는 처리를 해두는 게 안전하다.

## ICE 후보 수집

ICE(Interactive Connectivity Establishment)는 "이 두 단말이 실제로 통할 수 있는 경로"를 찾는 절차다. 단말 하나가 가질 수 있는 주소는 한 개가 아니다. 사설 IP도 있고, NAT를 거친 공인 IP도 있고, 릴레이 서버 주소도 있다. 이 가능한 주소들을 후보(candidate)라고 부르고, 양쪽이 후보를 다 모아서 서로 교환한 뒤 짝을 지어가며 통하는 조합을 찾는다.

후보는 세 종류다.

| 종류 | 표기 | 의미 | 통하는 경우 |
|------|------|------|-----------|
| host | typ host | 단말의 로컬 주소 (사설 IP 포함) | 같은 LAN |
| server reflexive | typ srflx | STUN으로 알아낸 NAT 바깥 공인 주소 | 일반적인 NAT 환경 |
| relay | typ relay | TURN 서버가 대신 받아주는 주소 | NAT 통과 실패 시 |

```
후보 수집 과정:

  단말 A ── "내 공인 주소가 뭐야?" ──▶ STUN 서버
        ◀── "너는 203.0.113.5:54321 로 보여" ──

  → A는 자기 사설 주소(host)와 STUN이 알려준 공인 주소(srflx)를
    둘 다 후보로 등록하고, 시그널링으로 B에게 보낸다.
```

### STUN의 역할

NAT 뒤에 있는 단말은 자기 공인 IP를 모른다. 자기가 아는 건 사설 IP(예: 192.168.0.10)뿐이다. STUN 서버는 "너 지금 나한테 어떤 주소로 보이는지" 알려주는 역할만 한다. 단말이 STUN 서버에 패킷을 하나 보내면, STUN 서버는 그 패킷의 출발지 주소(즉 NAT를 거친 공인 주소)를 그대로 응답에 담아 돌려준다. 단말은 이걸로 자기 공인 주소를 알게 되고 srflx 후보로 등록한다.

STUN 서버는 가볍다. 주소만 알려주고 끝이라 트래픽을 중계하지 않는다. 구글이 공개로 운영하는 `stun.l.google.com:19302`를 테스트용으로 많이 쓴다. 다만 운영에서는 자체 STUN/TURN을 띄우는 게 맞다. 공개 STUN은 가용성 보장이 없다.

```javascript
const iceServers = [
  { urls: 'stun:stun.l.google.com:19302' },
  {
    urls: 'turn:turn.example.com:3478',
    username: 'webrtc',
    credential: 'secret',
  },
];
```

### Trickle ICE

후보를 다 모은 다음에 한꺼번에 보내면 느리다. STUN 응답을 기다리는 동안 연결이 지연된다. 그래서 후보가 하나 발견될 때마다 즉시 보내는 방식을 쓴다. 이걸 Trickle ICE라고 한다.

```javascript
pc.onicecandidate = (event) => {
  if (event.candidate) {
    // 후보 하나 발견 → 바로 시그널링으로 전송
    signaling.send({ type: 'candidate', candidate: event.candidate });
  } else {
    // event.candidate 가 null 이면 후보 수집 완료
    console.log('ICE 후보 수집 끝');
  }
};

signaling.on('candidate', async (msg) => {
  try {
    await pc.addIceCandidate(msg.candidate);
  } catch (e) {
    // remoteDescription 세팅 전이면 여기서 터진다 → 큐잉 필요
    console.error('candidate 추가 실패', e);
  }
});
```

host 후보는 STUN을 안 거치니 즉시 나오고, srflx는 STUN 왕복 후에, relay는 TURN 할당 후에 나온다. 그래서 후보가 시간차를 두고 도착한다. 로그를 보면 host가 먼저 깔리고 srflx, relay가 순서대로 붙는 게 보인다.

## NAT 통과와 TURN 릴레이

NAT 종류에 따라 STUN만으로 뚫리는 경우와 안 뚫리는 경우가 갈린다. 여기서 WebRTC 트러블슈팅의 절반이 나온다.

NAT는 동작 방식에 따라 분류되는데, 실무에서 문제 되는 건 Symmetric NAT다. Symmetric NAT는 목적지마다 다른 외부 포트를 할당한다. 즉 A가 STUN 서버에 보낼 때 쓴 공인 포트와, B에게 직접 보낼 때 쓰는 공인 포트가 다르다. STUN으로 알아낸 주소(srflx)가 B에게 보낼 때는 무효가 되는 것이다. 양쪽이 다 Symmetric NAT면 srflx 후보로는 절대 연결이 안 된다.

```
일반 NAT (Cone):
  A → STUN  : 공인주소 = 203.0.113.5:54321
  A → B     : 공인주소 = 203.0.113.5:54321  (같음 → srflx 통함)

Symmetric NAT:
  A → STUN  : 공인주소 = 203.0.113.5:54321
  A → B     : 공인주소 = 203.0.113.5:60000  (다름 → srflx 무효)
  → 직접 연결 불가, TURN 릴레이로 떨어짐
```

이때 쓰는 게 TURN(Traversal Using Relays around NAT)이다. TURN 서버는 양쪽 단말의 트래픽을 대신 받아서 상대에게 넘겨준다. 직접 연결이 아니라 서버를 한 번 거치는 중계다. 직접 연결이 안 되는 환경에서도 통신이 되게 해주는 마지막 수단이다.

```
직접 연결 실패 시 TURN 릴레이:

  A ──▶ TURN 서버 ──▶ B
  A ◀── TURN 서버 ◀── B

  미디어/데이터가 전부 TURN을 경유한다.
  → P2P의 장점(서버 부하 안 늘어남)이 사라진다.
```

TURN으로 떨어지면 그 통화의 모든 트래픽이 TURN 서버 대역폭을 먹는다. 화상 통화 한 건이 수 Mbps인데 이게 전부 서버를 지난다. 그래서 TURN 서버는 STUN과 달리 트래픽 비용이 크고, 공개 무료 TURN이 거의 없는 이유도 이거다. 운영에서는 coturn을 직접 띄우거나 Twilio 같은 유료 TURN을 쓴다.

```bash
# coturn 최소 설정 (/etc/turnserver.conf)
listening-port=3478
tls-listening-port=5349
fingerprint
lt-cred-mech
user=webrtc:secret
realm=turn.example.com
# 방화벽 환경 대응 — 뒤에서 설명
listening-ip=0.0.0.0
external-ip=203.0.113.50
```

전체 통화 중 TURN으로 떨어지는 비율은 환경에 따라 다르다. 일반 가정용 인터넷끼리는 대부분 직접 연결이 되지만, 기업 네트워크나 모바일 캐리어 NAT가 끼면 비율이 확 올라간다. 운영 모니터링에서 "TURN relay 비율"을 지표로 잡아두면, 갑자기 이 비율이 튈 때 네트워크 쪽 문제를 빨리 잡을 수 있다.

<div class="ygd-nat-types" id="ygd-nat-types">
<style>
.ygd-nat-types{--ygd-fg:#2B2724;--ygd-muted:#5F5A54;--ygd-line:#B8B1A8;--ygd-sig:#3D7387;--ygd-p2p:#A24E12;--ygd-bad:#B3261E;--ygd-turn:#6B4E9B;--ygd-bg:#FDFBFA;--ygd-panel:#F3EFEA;--ygd-btn:#3D7387;--ygd-btnfg:#FFFFFF;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1.5em;margin-bottom:1.5em;color:var(--ygd-fg);box-sizing:border-box}
body[data-md-color-scheme="slate"] .ygd-nat-types{--ygd-fg:#F0EDE9;--ygd-muted:#B5AEA5;--ygd-line:#6B655E;--ygd-sig:#7FB9CF;--ygd-p2p:#F0A868;--ygd-bad:#FF9A94;--ygd-turn:#C4A8F0;--ygd-bg:#1F1C1E;--ygd-panel:#2B2729;--ygd-btn:#7FB9CF;--ygd-btnfg:#1F1C1E}
.ygd-nat-types *{box-sizing:border-box}
.ygd-nat-types .ygd-note{font-size:14px;line-height:1.6;color:var(--ygd-muted);margin:0 0 10px 0}
.ygd-nat-types .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-nat-types .ygd-wire{stroke:var(--ygd-line);stroke-width:2}
.ygd-nat-types .ygd-box{fill:var(--ygd-panel);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-nat-types .ygd-boxt{fill:var(--ygd-fg);font-size:13px;font-weight:600}
.ygd-nat-types .ygd-grp{opacity:.5;transition:opacity .3s}
.ygd-nat-types .ygd-grp.ygd-done{opacity:.8}
.ygd-nat-types .ygd-grp.ygd-on{opacity:1}
.ygd-nat-types .ygd-hide{display:none}
.ygd-nat-types .ygd-ln{fill:none;stroke-width:2}
.ygd-nat-types .ygd-on .ygd-ln{stroke-width:3;stroke-dasharray:var(--ygd-len);animation:ygd-nat-types-draw .5s ease-out both}
.ygd-nat-types .ygd-on .ygd-hd{animation:ygd-nat-types-fade .3s both}
.ygd-nat-types .ygd-stun .ygd-ln{stroke:var(--ygd-sig)}
.ygd-nat-types .ygd-stun .ygd-hd{fill:var(--ygd-sig)}
.ygd-nat-types .ygd-direct .ygd-ln{stroke:var(--ygd-p2p)}
.ygd-nat-types .ygd-direct .ygd-hd{fill:var(--ygd-p2p)}
.ygd-nat-types .ygd-turn .ygd-ln{stroke:var(--ygd-turn)}
.ygd-nat-types .ygd-turn .ygd-hd{fill:var(--ygd-turn)}
.ygd-nat-types .ygd-bad .ygd-ln{stroke:var(--ygd-bad);stroke-dasharray:6 4;animation:none}
.ygd-nat-types .ygd-bad .ygd-hd{fill:var(--ygd-bad)}
.ygd-nat-types .ygd-bad .ygd-lbbad{fill:var(--ygd-bad)}
.ygd-nat-types .ygd-lb{fill:var(--ygd-fg);font-size:12px;stroke:var(--ygd-bg);stroke-width:4px;paint-order:stroke}
.ygd-nat-types .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.ygd-nat-types .ygd-btn{font:inherit;font-size:14px;line-height:1.2;padding:9px 14px;min-height:40px;border:2px solid var(--ygd-btn);border-radius:6px;background:transparent;color:var(--ygd-fg);cursor:pointer}
.ygd-nat-types .ygd-btn.ygd-act{background:var(--ygd-btn);color:var(--ygd-btnfg)}
.ygd-nat-types .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-nat-types .ygd-btn:focus-visible{outline:3px solid var(--ygd-p2p);outline-offset:2px}
.ygd-nat-types .ygd-cnt{font-size:14px;color:var(--ygd-muted)}
.ygd-nat-types .ygd-panel{background:var(--ygd-panel);border-radius:8px;padding:12px 14px;border-left:4px solid var(--ygd-sig)}
.ygd-nat-types .ygd-ptitle{font-size:15px;font-weight:700;margin:0 0 4px 0}
.ygd-nat-types .ygd-ptext{font-size:14px;line-height:1.65;margin:0}
@keyframes ygd-nat-types-draw{from{stroke-dashoffset:var(--ygd-len)}to{stroke-dashoffset:0}}
@keyframes ygd-nat-types-fade{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){.ygd-nat-types .ygd-ln,.ygd-nat-types .ygd-hd{animation:none !important}.ygd-nat-types .ygd-grp{transition:none}}
</style>
<p class="ygd-note">비유: NAT는 건물 안내 데스크와 비슷하다. 밖에서는 대표번호만 보이는데, Cone 방식은 어느 상대와 통화하든 같은 내선을 쓰고, Symmetric 방식은 상대마다 다른 내선을 배정한다. 아래 버튼으로 두 경우를 바꿔 본다.</p>
<div class="ygd-ctrl" role="group" aria-label="NAT 종류 선택">
<button type="button" class="ygd-btn ygd-act ygd-sc-cone" aria-pressed="true">일반 NAT (Cone)</button>
<button type="button" class="ygd-btn ygd-sc-sym" aria-pressed="false">Symmetric NAT</button>
</div>
<svg class="ygd-svg" viewBox="0 0 480 302" role="img" aria-label="NAT 종류별 연결 경로 다이어그램. A 단말은 NAT 뒤에서 STUN 서버로 공인 주소를 확인한 뒤 B 단말로 직접 보낸다. Cone NAT에서는 같은 공인 포트라 직접 연결되고, Symmetric NAT에서는 포트가 달라져 TURN 서버를 거치는 릴레이로 떨어진다."></svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-prev">이전</button>
<button type="button" class="ygd-btn ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-next">다음</button>
<span class="ygd-cnt" aria-hidden="true"></span>
</div>
<div class="ygd-panel" aria-live="polite">
<p class="ygd-ptitle"></p>
<p class="ygd-ptext"></p>
</div>
<script>
(function(){
var root=document.getElementById('ygd-nat-types');
if(!root)return;
var NS='http://www.w3.org/2000/svg';
var svg=root.querySelector('.ygd-svg');
function el(n,a,p,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!==undefined)e.textContent=t;if(p)p.appendChild(e);return e;}
function box(x,y,w,h,s){el('rect',{x:x,y:y,width:w,height:h,rx:6,'class':'ygd-box'},svg);el('text',{x:x+w/2,y:y+h/2+4,'class':'ygd-boxt','text-anchor':'middle'},svg,s);}
el('line',{x1:100,y1:145,x2:140,y2:145,'class':'ygd-wire'},svg);
box(10,125,90,40,'A 단말');
box(140,125,90,40,'NAT');
box(370,125,100,40,'B 단말');
box(370,20,100,40,'STUN 서버');
var G={};
['stun','direct','turn'].forEach(function(k){G[k]=el('g',{'class':'ygd-grp ygd-'+k},svg);});
function ln(g,d,len,delay){var p=el('path',{d:d,'class':'ygd-ln'},g);p.style.setProperty('--ygd-len',String(len));p.style.animationDelay=delay+'s';}
function hd(g,pts,delay){var p=el('polygon',{points:pts,'class':'ygd-hd'},g);p.style.animationDelay=delay+'s';}
function lb(g,x,y,s,c){return el('text',{x:x,y:y,'class':'ygd-lb'+(c?' '+c:''),'text-anchor':'middle'},g,s);}
ln(G.stun,'M185 125 L185 40 L370 40',270,0);
hd(G.stun,'370,40 361,35.5 361,44.5',0.35);
ln(G.stun,'M370 58 L201 58 L201 125',236,0.5);
hd(G.stun,'201,125 196.5,116 205.5,116',0.85);
lb(G.stun,277,31,'STUN 요청');
lb(G.stun,285,78,'응답: 203.0.113.5:54321');
ln(G.direct,'M230 145 L370 145',140,0);
hd(G.direct,'370,145 361,140.5 361,149.5',0.35);
lb(G.direct,300,134,'A→B 직접 시도');
var d2=lb(G.direct,300,161,'');
var d3=lb(G.direct,300,184,'','ygd-lbbad');
el('rect',{x:250,y:235,width:100,height:40,rx:6,'class':'ygd-box'},G.turn);
el('text',{x:300,y:259,'class':'ygd-boxt','text-anchor':'middle'},G.turn,'TURN 서버');
ln(G.turn,'M185 165 L185 255 L250 255',155,0);
hd(G.turn,'250,255 241,250.5 241,259.5',0.35);
ln(G.turn,'M350 255 L420 255 L420 165',160,0.5);
hd(G.turn,'420,165 415.5,174 424.5,174',0.85);
lb(G.turn,300,295,'전부 TURN 경유');
var SC={
cone:[
{on:'stun',t:'일반 NAT: STUN으로 공인 주소 확인',x:'A가 STUN 서버에 패킷을 보내면 서버는 출발지 주소를 응답에 담아 돌려준다. A는 203.0.113.5:54321을 srflx 후보로 등록하고 시그널링으로 B에게 보낸다.'},
{on:'direct',t:'B에게 보낼 때도 같은 공인 포트',x:'A가 B에게 보낼 때 쓰는 공인 주소도 203.0.113.5:54321로 같다. STUN으로 알아낸 srflx 후보가 B에게도 유효해서 직접 연결이 된다.'}
],
sym:[
{on:'stun',t:'Symmetric NAT: STUN으로 공인 주소 확인',x:'여기까지는 일반 NAT와 같다. STUN 서버는 A가 STUN으로 보낼 때의 공인 주소 203.0.113.5:54321을 알려준다.'},
{on:'direct',t:'B에게 보낼 때는 다른 공인 포트',x:'Symmetric NAT는 목적지마다 다른 외부 포트를 할당한다. A가 B에게 보내면 203.0.113.5:60000이 되어, STUN으로 알아낸 srflx 후보가 무효가 된다.'},
{on:'turn',t:'TURN 릴레이로 전환',x:'직접 연결이 안 되면 TURN 서버가 양쪽 트래픽을 대신 받아 넘겨준다. 통신은 되지만 모든 트래픽이 TURN 대역폭을 먹어 P2P의 장점이 사라진다. 양쪽이 다 Symmetric NAT면 srflx 후보로는 절대 연결되지 않는다.'}
]};
var bCone=root.querySelector('.ygd-sc-cone'),bSym=root.querySelector('.ygd-sc-sym');
var prev=root.querySelector('.ygd-prev'),next=root.querySelector('.ygd-next'),playBtn=root.querySelector('.ygd-play');
var cnt=root.querySelector('.ygd-cnt'),ptitle=root.querySelector('.ygd-ptitle'),ptext=root.querySelector('.ygd-ptext');
var sc='cone',cur=0,timer=null;
function show(i){
cur=i;
var steps=SC[sc];
['stun','direct','turn'].forEach(function(k){
var idx=-1;
steps.forEach(function(s,n){if(s.on===k&&idx<0)idx=n;});
var c='ygd-grp ygd-'+k;
if(idx<0)c+=' ygd-hide';
else if(idx===i)c+=' ygd-on';
else if(idx<i)c+=' ygd-done';
if(k==='direct'&&sc==='sym'&&i>=1)c+=' ygd-bad';
G[k].setAttribute('class',c);
});
d2.textContent='공인 포트 :'+(sc==='cone'?'54321':'60000');
d3.textContent=sc==='cone'?'STUN과 같은 포트 → 유효':'STUN과 다른 포트 → 무효';
ptitle.textContent=steps[i].t;
ptext.textContent=steps[i].x;
cnt.textContent=(i+1)+' / '+steps.length;
prev.disabled=i===0;
next.disabled=i===steps.length-1;
}
function stop(){if(timer){clearInterval(timer);timer=null;}playBtn.textContent='재생';}
function play(){
if(cur>=SC[sc].length-1)show(0);
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(cur>=SC[sc].length-1){stop();return;}
show(cur+1);
},2800);
}
function pick(s){
stop();sc=s;
bCone.classList.toggle('ygd-act',s==='cone');
bSym.classList.toggle('ygd-act',s==='sym');
bCone.setAttribute('aria-pressed',String(s==='cone'));
bSym.setAttribute('aria-pressed',String(s==='sym'));
show(0);
}
bCone.addEventListener('click',function(){pick('cone');});
bSym.addEventListener('click',function(){pick('sym');});
playBtn.addEventListener('click',function(){if(timer)stop();else play();});
prev.addEventListener('click',function(){stop();if(cur>0)show(cur-1);});
next.addEventListener('click',function(){stop();if(cur<SC[sc].length-1)show(cur+1);});
show(0);
})();
</script>
</div>

### ICE 후보 짝짓기

후보를 다 교환하면 ICE는 가능한 모든 조합을 만들어서 우선순위 순으로 연결을 시도한다. 우선순위는 host > srflx > relay 순이다. 직접 연결이 가장 좋고, 릴레이가 가장 비싸니까 마지막이다.

```
후보 쌍 점검 (Connectivity Check):

  (A host, B host)   → 같은 LAN이면 성공, 아니면 실패
  (A srflx, B srflx) → 일반 NAT면 성공
  (A relay, B *)     → 위가 다 실패하면 여기로
```

각 쌍에 대해 STUN 바인딩 요청을 주고받아서 실제로 통하는지 확인한다. 통하는 쌍 중 우선순위가 가장 높은 걸로 연결이 맺힌다. 이 과정이 `iceConnectionState`로 노출된다.

```javascript
pc.oniceconnectionstatechange = () => {
  console.log('ICE 상태:', pc.iceConnectionState);
  // checking → connected → completed  (정상)
  // checking → failed                 (모든 후보 쌍 실패)
  // connected → disconnected          (일시적 끊김, 복구될 수 있음)
};
```

`failed`가 뜨면 통하는 후보 쌍이 하나도 없다는 뜻이다. 십중팔구 TURN 설정이 없거나 잘못됐다. `disconnected`는 다르다. 네트워크가 잠깐 끊긴 거라 곧 `connected`로 돌아오는 경우가 많아서, 바로 연결을 끊지 말고 몇 초 기다려보는 게 낫다.

## DataChannel과 미디어 채널

WebRTC로 보낼 수 있는 건 두 가지다. 카메라/마이크 같은 미디어 트랙과, 임의의 데이터를 보내는 DataChannel이다. 둘은 전송 방식이 다르다.

| 구분 | 미디어 채널 | DataChannel |
|------|-----------|-------------|
| 전송 | RTP/SRTP over UDP | SCTP over DTLS |
| 신뢰성 | 비신뢰 (손실 허용) | 신뢰/비신뢰 선택 가능 |
| 순서 보장 | 없음 | 선택 가능 |
| 용도 | 영상, 음성 | 채팅, 파일, 게임 상태, 시그널 |

미디어는 실시간성이 신뢰성보다 중요하다. 영상 프레임 하나 손실됐다고 재전송 기다리면 화면이 멈춘다. 그래서 미디어는 UDP 위에서 손실을 허용하고 그냥 다음 프레임으로 넘어간다.

DataChannel은 TCP처럼 신뢰성 있게 보낼 수도 있고, UDP처럼 손실을 허용하게 설정할 수도 있다. 게임에서 위치 동기화처럼 "최신 값만 중요하고 옛날 패킷은 버려도 되는" 데이터는 비신뢰/비순서로 설정하는 게 낫다.

```javascript
// 신뢰성 있는 채널 (기본) — 채팅, 파일 전송
const chatChannel = pc.createDataChannel('chat');

// 비신뢰 채널 — 게임 위치 동기화 같은 거
const gameChannel = pc.createDataChannel('game', {
  ordered: false,        // 순서 보장 안 함
  maxRetransmits: 0,     // 재전송 안 함 (손실 허용)
});

chatChannel.onopen = () => chatChannel.send('연결됨');
chatChannel.onmessage = (e) => console.log('받음:', e.data);

// 수신 쪽
pc.ondatachannel = (event) => {
  const channel = event.channel;
  channel.onmessage = (e) => console.log(channel.label, e.data);
};
```

DataChannel만 쓰는 경우도 많다. 미디어 없이 P2P 데이터만 주고받는 멀티플레이 게임이나, 서버 부하 없이 파일을 직접 전송하는 경우다. 이때도 NAT 통과 과정은 미디어와 똑같다. STUN/TURN/ICE를 거쳐야 채널이 열린다. DataChannel은 서버 안 거치니 공짜라고 생각하기 쉬운데, TURN으로 떨어지면 데이터도 릴레이를 타서 똑같이 서버 대역폭을 먹는다.

한 가지 주의할 점은 DataChannel의 메시지 크기 제한이다. 큰 파일을 한 번에 send하면 버퍼가 넘쳐서 채널이 끊긴다. 보통 16KB 정도로 잘라서 보내고, `bufferedAmount`를 보면서 흐름을 조절해야 한다.

```javascript
const CHUNK = 16 * 1024;
const THRESHOLD = 1 * 1024 * 1024; // 1MB 넘으면 잠깐 멈춤

async function sendFile(channel, buffer) {
  for (let offset = 0; offset < buffer.byteLength; offset += CHUNK) {
    // 버퍼가 차면 비워질 때까지 대기
    while (channel.bufferedAmount > THRESHOLD) {
      await new Promise(r => setTimeout(r, 50));
    }
    channel.send(buffer.slice(offset, offset + CHUNK));
  }
}
```

## 방화벽 환경 트러블슈팅

로컬에서는 잘 되던 WebRTC가 회사 망이나 특정 고객사 환경에서 연결이 안 되는 일이 흔하다. 원인은 대부분 방화벽이 UDP를 막거나 특정 포트를 차단하는 데 있다. 순서대로 확인할 항목을 정리한다.

### UDP 차단

WebRTC 미디어는 기본적으로 UDP를 쓴다. 그런데 기업 방화벽은 보안상 UDP를 통째로 막아둔 곳이 많다. 이러면 STUN도 안 되고(STUN도 UDP), 미디어도 못 흐른다. 이때는 TURN을 TCP로, 더 나아가 TLS(443 포트)로 돌리는 설정이 필요하다.

```javascript
const iceServers = [
  { urls: 'stun:turn.example.com:3478' },
  // UDP TURN
  { urls: 'turn:turn.example.com:3478', username: 'u', credential: 'p' },
  // TCP TURN — UDP 막힌 환경
  { urls: 'turn:turn.example.com:3478?transport=tcp', username: 'u', credential: 'p' },
  // TLS TURN — 443 으로 위장, 거의 모든 방화벽 통과
  { urls: 'turns:turn.example.com:443?transport=tcp', username: 'u', credential: 'p' },
];
```

`turns:` (s가 붙은 것)는 TLS 위의 TURN이다. 443 포트로 돌리면 HTTPS 트래픽과 구분이 안 돼서 웬만한 방화벽은 통과시킨다. 연결이 도저히 안 되는 빡빡한 환경에서 마지막 카드로 쓴다. 단 모든 트래픽이 TURN을 경유하므로 가장 느리고 서버 부하가 크다.

<div class="ygd-fw-turn" id="ygd-fw-turn">
<style>
.ygd-fw-turn{--ygd-fg:#2B2724;--ygd-muted:#5F5A54;--ygd-line:#B8B1A8;--ygd-sig:#3D7387;--ygd-p2p:#A24E12;--ygd-bad:#B3261E;--ygd-ok:#1E7A46;--ygd-bg:#FDFBFA;--ygd-panel:#F3EFEA;--ygd-btn:#3D7387;--ygd-btnfg:#FFFFFF;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1.5em;margin-bottom:1.5em;color:var(--ygd-fg);box-sizing:border-box}
body[data-md-color-scheme="slate"] .ygd-fw-turn{--ygd-fg:#F0EDE9;--ygd-muted:#B5AEA5;--ygd-line:#6B655E;--ygd-sig:#7FB9CF;--ygd-p2p:#F0A868;--ygd-bad:#FF9A94;--ygd-ok:#7FD6A0;--ygd-bg:#1F1C1E;--ygd-panel:#2B2729;--ygd-btn:#7FB9CF;--ygd-btnfg:#1F1C1E}
.ygd-fw-turn *{box-sizing:border-box}
.ygd-fw-turn .ygd-note{font-size:14px;line-height:1.6;color:var(--ygd-muted);margin:0 0 10px 0}
.ygd-fw-turn .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-fw-turn .ygd-box{fill:var(--ygd-panel);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-fw-turn .ygd-wall{fill:var(--ygd-panel);stroke:var(--ygd-bad);stroke-width:1.5}
.ygd-fw-turn .ygd-boxt{fill:var(--ygd-fg);font-size:13px;font-weight:600}
.ygd-fw-turn .ygd-lane{opacity:.5;transition:opacity .3s}
.ygd-fw-turn .ygd-lane.ygd-done{opacity:.8}
.ygd-fw-turn .ygd-lane.ygd-on{opacity:1}
.ygd-fw-turn .ygd-ln{fill:none;stroke:var(--ygd-sig);stroke-width:2}
.ygd-fw-turn .ygd-hd{fill:var(--ygd-sig)}
.ygd-fw-turn .ygd-on .ygd-ln{stroke-width:3;stroke-dasharray:var(--ygd-len);animation:ygd-fw-turn-draw .5s ease-out both}
.ygd-fw-turn .ygd-on .ygd-hd,.ygd-fw-turn .ygd-on .ygd-mk{animation:ygd-fw-turn-fade .3s .45s both}
.ygd-fw-turn .ygd-blk .ygd-r{stroke:var(--ygd-bad);stroke-dasharray:6 4;animation:none}
.ygd-fw-turn .ygd-blk .ygd-hd{fill:var(--ygd-bad)}
.ygd-fw-turn .ygd-mk{font-size:15px;font-weight:700;stroke:var(--ygd-panel);stroke-width:3px;paint-order:stroke}
.ygd-fw-turn .ygd-mk-ok{fill:var(--ygd-ok)}
.ygd-fw-turn .ygd-mk-no{fill:var(--ygd-bad)}
.ygd-fw-turn .ygd-lb{fill:var(--ygd-fg);font-size:12px;stroke:var(--ygd-bg);stroke-width:4px;paint-order:stroke}
.ygd-fw-turn .ygd-wl{fill:var(--ygd-bad);font-size:12px;font-weight:600}
.ygd-fw-turn .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.ygd-fw-turn .ygd-btn{font:inherit;font-size:14px;line-height:1.2;padding:9px 14px;min-height:40px;border:2px solid var(--ygd-btn);border-radius:6px;background:transparent;color:var(--ygd-fg);cursor:pointer}
.ygd-fw-turn .ygd-btn.ygd-act{background:var(--ygd-btn);color:var(--ygd-btnfg)}
.ygd-fw-turn .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-fw-turn .ygd-btn:focus-visible{outline:3px solid var(--ygd-p2p);outline-offset:2px}
.ygd-fw-turn .ygd-cnt{font-size:14px;color:var(--ygd-muted)}
.ygd-fw-turn .ygd-panel{background:var(--ygd-panel);border-radius:8px;padding:12px 14px;border-left:4px solid var(--ygd-sig)}
.ygd-fw-turn .ygd-panel.ygd-blk{border-left-color:var(--ygd-bad)}
.ygd-fw-turn .ygd-panel.ygd-pass{border-left-color:var(--ygd-ok)}
.ygd-fw-turn .ygd-ptitle{font-size:15px;font-weight:700;margin:0 0 4px 0}
.ygd-fw-turn .ygd-ptext{font-size:14px;line-height:1.65;margin:0}
@keyframes ygd-fw-turn-draw{from{stroke-dashoffset:var(--ygd-len)}to{stroke-dashoffset:0}}
@keyframes ygd-fw-turn-fade{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){.ygd-fw-turn .ygd-ln,.ygd-fw-turn .ygd-hd,.ygd-fw-turn .ygd-mk{animation:none !important}.ygd-fw-turn .ygd-lane{transition:none}}
</style>
<p class="ygd-note">비유: 출입구가 여러 개인 건물에서 보안 검색대가 일부 출입구만 막고, 일반 방문객이 쓰는 정문(443)은 열어 두는 것과 비슷하다. 방화벽 정책을 고른 뒤 세 가지 TURN 후보가 어떻게 되는지 본다.</p>
<div class="ygd-ctrl" role="group" aria-label="방화벽 정책 선택">
<button type="button" class="ygd-btn ygd-act ygd-sc-a" aria-pressed="true">UDP만 차단</button>
<button type="button" class="ygd-btn ygd-sc-b" aria-pressed="false">UDP와 3478 차단</button>
</div>
<svg class="ygd-svg" viewBox="0 0 480 262" role="img" aria-label="방화벽 환경별 TURN 후보 통과 여부 다이어그램. 단말에서 TURN 서버로 가는 UDP 3478, TCP 3478, TLS 443 세 경로가 방화벽 정책에 따라 막히거나 통과한다."></svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-prev">이전</button>
<button type="button" class="ygd-btn ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-next">다음</button>
<span class="ygd-cnt" aria-hidden="true"></span>
</div>
<div class="ygd-panel" aria-live="polite">
<p class="ygd-ptitle"></p>
<p class="ygd-ptext"></p>
</div>
<script>
(function(){
var root=document.getElementById('ygd-fw-turn');
if(!root)return;
var NS='http://www.w3.org/2000/svg';
var svg=root.querySelector('.ygd-svg');
function el(n,a,p,t){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(t!==undefined)e.textContent=t;if(p)p.appendChild(e);return e;}
el('rect',{x:10,y:50,width:70,height:200,rx:6,'class':'ygd-box'},svg);
el('text',{x:45,y:154,'class':'ygd-boxt','text-anchor':'middle'},svg,'A 단말');
el('rect',{x:370,y:50,width:100,height:200,rx:6,'class':'ygd-box'},svg);
el('text',{x:420,y:154,'class':'ygd-boxt','text-anchor':'middle'},svg,'TURN 서버');
el('rect',{x:190,y:50,width:20,height:200,rx:4,'class':'ygd-wall'},svg);
el('text',{x:200,y:36,'class':'ygd-wl','text-anchor':'middle'},svg,'방화벽');
var LANES=[
{y:90,l:'UDP · 3478',r:'turn: (UDP)'},
{y:150,l:'TCP · 3478',r:'turn: ?transport=tcp'},
{y:210,l:'TLS · 443',r:'turns: ?transport=tcp'}
];
LANES.forEach(function(ln){
var g=el('g',{'class':'ygd-lane'},svg);
var a=el('path',{d:'M80 '+ln.y+' L190 '+ln.y,'class':'ygd-ln ygd-l'},g);
a.style.setProperty('--ygd-len','110');
el('polygon',{points:'190,'+ln.y+' 181,'+(ln.y-4.5)+' 181,'+(ln.y+4.5),'class':'ygd-hd'},g);
var b=el('path',{d:'M210 '+ln.y+' L370 '+ln.y,'class':'ygd-ln ygd-r'},g);
b.style.setProperty('--ygd-len','160');
b.style.animationDelay='0.4s';
el('polygon',{points:'370,'+ln.y+' 361,'+(ln.y-4.5)+' 361,'+(ln.y+4.5),'class':'ygd-hd'},g);
el('text',{x:135,y:ln.y-9,'class':'ygd-lb','text-anchor':'middle'},g,ln.l);
el('text',{x:290,y:ln.y-9,'class':'ygd-lb','text-anchor':'middle'},g,ln.r);
ln.mk=el('text',{x:200,y:ln.y+5,'class':'ygd-mk','text-anchor':'middle'},g,'');
ln.g=g;
});
var SC={
a:[
{ok:0,t:'UDP TURN (3478): 차단',x:'UDP를 통째로 막은 방화벽에서는 STUN도 UDP라 동작하지 않고, 미디어도 UDP라 흐르지 못한다. 이 후보는 통과하지 못한다.'},
{ok:1,t:'TCP TURN (3478): 통과',x:'TURN을 TCP로 돌리면 UDP만 막은 방화벽은 지나간다. 이 경로로 TURN 릴레이가 성립한다.'},
{ok:1,t:'TLS TURN (443): 통과',x:'turns:는 TLS 위의 TURN이라 443 포트에서 HTTPS 트래픽과 구분되지 않는다. 다만 모든 트래픽이 TURN을 경유하므로 가장 느리고 서버 부하가 크다.'}
],
b:[
{ok:0,t:'UDP TURN (3478): 차단',x:'UDP가 막혀 있으므로 이 후보는 통과하지 못한다. STUN 바인딩도 UDP라 같이 막힌다.'},
{ok:0,t:'TCP TURN (3478): 차단',x:'방화벽이 3478 포트까지 막았다면 TCP로 바꿔도 소용없다. 특정 고객사에서만 연결이 안 되는 경우가 이런 모양이다.'},
{ok:1,t:'TLS TURN (443): 통과',x:'turns:443으로 바꿔서 연결이 되면 방화벽이 원인이라는 게 확정된다. 빡빡한 환경의 마지막 카드지만 모든 트래픽이 TURN을 경유한다.'}
]};
var bA=root.querySelector('.ygd-sc-a'),bB=root.querySelector('.ygd-sc-b');
var prev=root.querySelector('.ygd-prev'),next=root.querySelector('.ygd-next'),playBtn=root.querySelector('.ygd-play');
var cnt=root.querySelector('.ygd-cnt'),panel=root.querySelector('.ygd-panel');
var ptitle=root.querySelector('.ygd-ptitle'),ptext=root.querySelector('.ygd-ptext');
var sc='a',cur=0,timer=null;
function show(i){
cur=i;
var steps=SC[sc];
LANES.forEach(function(ln,k){
var c='ygd-lane';
if(k===i)c+=' ygd-on';else if(k<i)c+=' ygd-done';
if(k<=i&&!steps[k].ok)c+=' ygd-blk';
ln.g.setAttribute('class',c);
ln.mk.setAttribute('class','ygd-mk '+(steps[k].ok?'ygd-mk-ok':'ygd-mk-no'));
ln.mk.textContent=k<=i?(steps[k].ok?'\u2713':'\u2715'):'';
});
ptitle.textContent=steps[i].t;
ptext.textContent=steps[i].x;
panel.setAttribute('class','ygd-panel '+(steps[i].ok?'ygd-pass':'ygd-blk'));
cnt.textContent=(i+1)+' / '+steps.length;
prev.disabled=i===0;
next.disabled=i===steps.length-1;
}
function stop(){if(timer){clearInterval(timer);timer=null;}playBtn.textContent='재생';}
function play(){
if(cur>=2)show(0);
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(cur>=2){stop();return;}
show(cur+1);
},2800);
}
function pick(s){
stop();sc=s;
bA.classList.toggle('ygd-act',s==='a');
bB.classList.toggle('ygd-act',s==='b');
bA.setAttribute('aria-pressed',String(s==='a'));
bB.setAttribute('aria-pressed',String(s==='b'));
show(0);
}
bA.addEventListener('click',function(){pick('a');});
bB.addEventListener('click',function(){pick('b');});
playBtn.addEventListener('click',function(){if(timer)stop();else play();});
prev.addEventListener('click',function(){stop();if(cur>0)show(cur-1);});
next.addEventListener('click',function(){stop();if(cur<2)show(cur+1);});
show(0);
})();
</script>
</div>

### 어디서 막히는지 확인하는 법

연결이 안 될 때 추측하지 말고 실제 후보 상태를 봐야 한다. 크롬이면 `chrome://webrtc-internals`를 열면 ICE 후보와 연결 시도 과정이 전부 나온다. 코드에서는 `getStats()`로 확인한다.

```javascript
// 어떤 후보 쌍으로 연결됐는지 확인
const stats = await pc.getStats();
stats.forEach(report => {
  if (report.type === 'candidate-pair' && report.state === 'succeeded') {
    console.log('연결된 쌍:', report.localCandidateId, report.remoteCandidateId);
  }
  if (report.type === 'local-candidate') {
    console.log('로컬 후보:', report.candidateType, report.protocol, report.address);
  }
});
```

여기서 봐야 할 건 성공한 candidate-pair의 후보 타입이다.

- 양쪽 다 host면: 같은 LAN. 정상.
- srflx면: NAT 통과 성공. 정상.
- relay면: 직접 연결 실패해서 TURN 릴레이 중. 동작은 하지만 느리고 비싸다. 이게 의도보다 자주 나오면 NAT/방화벽을 점검해야 한다.
- candidate-pair가 아예 succeeded 없이 failed면: 통하는 경로가 없다. TURN이 없거나 TURN도 막힌 것.

### 자주 겪는 증상과 원인

운영하면서 반복적으로 만난 패턴들이다.

연결은 되는데 영상이 안 나온다. ICE는 connected인데 화면이 검다. 코덱 협상 실패이거나 미디어 트랙이 SDP에 안 실린 경우다. SDP의 `m=video` 줄과 양쪽 코덱 교집합을 확인한다.

로컬에서는 되고 운영에서만 안 된다. 로컬은 같은 LAN이라 host 후보로 바로 붙는다. 운영은 서로 다른 NAT 뒤라 STUN/TURN이 필요한데 TURN 설정이 빠진 경우가 대부분이다. 로컬 테스트로는 NAT 통과를 검증할 수 없다는 걸 기억해야 한다.

특정 고객사에서만 안 된다. 그 망의 방화벽이 UDP나 3478 포트를 막은 것이다. `turns:443` 으로 떨어뜨려서 되는지 본다. 되면 방화벽이 원인이라는 게 확정된다.

가끔 끊겼다가 다시 붙는다. `disconnected` → `connected` 반복. 모바일에서 네트워크가 흔들리거나 와이파이/LTE 전환 시 ICE 재협상이 일어나는 정상 동작에 가깝다. `iceRestart` 옵션으로 후보를 다시 모아 재연결하는 처리를 넣어두면 사용자가 끊김을 덜 느낀다.

```javascript
// 연결이 실패하면 ICE 재시작으로 후보 재수집
pc.oniceconnectionstatechange = async () => {
  if (pc.iceConnectionState === 'failed') {
    const offer = await pc.createOffer({ iceRestart: true });
    await pc.setLocalDescription(offer);
    signaling.send({ type: 'offer', sdp: offer.sdp });
  }
};
```

## 다대다 연결의 한계

여기까지는 1:1 연결을 전제로 했다. 그런데 화상 회의처럼 여러 명이 붙으면 P2P 풀메시는 금방 한계에 부딪힌다. N명이 서로 다 연결하면 각 단말이 N-1개의 연결을 유지하고 자기 영상을 N-1번 인코딩해서 보내야 한다. 4~5명만 넘어가도 클라이언트 CPU와 업로드 대역폭이 못 버틴다.

```
풀메시 (P2P 다대다):
  4명이면 각자 3개 연결 → 총 6개 연결, 각자 3번 송신
  10명이면 각자 9개 연결 → 클라이언트 폭발

SFU (미디어 서버):
  각 단말은 서버와 1개 연결만
  서버가 받아서 다른 사람들에게 분배
```

그래서 인원이 많아지면 SFU(Selective Forwarding Unit)나 MCU 같은 미디어 서버를 둔다. 각 단말은 서버와만 연결하고, 서버가 영상을 받아서 다른 참가자에게 뿌린다. 이러면 순수 P2P는 아니지만 클라이언트 부담이 사라진다. mediasoup, Janus, LiveKit 같은 게 이 SFU 구현이다. 소규모는 P2P로 충분하지만, 회의 규모가 커지면 SFU 도입을 검토하게 된다.

## 정리

WebRTC 연결이 안 될 때 볼 곳은 거의 정해져 있다. 시그널링이 SDP와 후보를 제대로 전달하는지, ICE 후보가 양쪽에서 수집되는지, TURN 설정이 있는지, 방화벽이 UDP를 막지는 않는지. `chrome://webrtc-internals`와 `getStats()`로 어느 후보 쌍에서 막히는지 확인하면 원인의 대부분이 잡힌다. 로컬에서 된다고 운영에서 되는 게 아니라는 것, TURN 없이는 NAT 통과가 보장되지 않는다는 것, 이 두 개만 기억해도 초기 삽질을 크게 줄인다.
