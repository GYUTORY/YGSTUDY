---
title: MSA 서비스 체인 멱등성
tags: [microservices, architecture]
updated: 2026-10-23
---

# MSA 서비스 체인 멱등성

단일 서비스에서 멱등성을 구현하는 건 어렵지 않다. DB에 멱등성 키 테이블 하나 만들고, 요청이 들어올 때마다 키를 확인하면 된다. 문제는 서비스가 체인으로 엮이는 순간부터 시작된다.

주문 서비스 → 재고 서비스 → 결제 서비스 → 배송 서비스 순으로 호출이 이어질 때, 어느 지점에서 타임아웃이 발생하거나 네트워크 오류가 나면 재시도가 들어온다. 이때 각 서비스가 독립적으로 멱등성을 처리하지 않으면 중복 결제가 발생하거나, 재고가 두 번 차감되거나, 배송이 두 번 생성된다.

## 멱등성 키 전파 방식

서비스 체인에서 멱등성 키를 어떻게 전달할지는 두 가지 방식이 있다.

### 상위 키 재사용

클라이언트가 생성한 멱등성 키를 체인 전체에서 그대로 사용하는 방식이다.

```
Client → 주문서비스(key=abc123) → 결제서비스(key=abc123) → 포인트서비스(key=abc123)
```

단순하다는 게 장점이다. 어느 서비스에서 문제가 생겨도 재시도 시 동일한 키로 멱등성 검사를 통과한다.

단점은 키가 여러 서비스 컨텍스트에 걸쳐 쓰이면서 충돌 가능성이 생긴다는 점이다. 포인트 서비스와 쿠폰 서비스가 같은 키 `abc123`을 받으면, 각 서비스 DB에서 키를 분리해서 관리해야 한다. 키 자체에 서비스 prefix를 붙이는 방법으로 해결한다.

```java
// 멱등성 키 저장 시 서비스 범위를 키에 포함
String idempotencyKey = "payment:" + upstreamKey;  // payment:abc123
String idempotencyKey = "point:" + upstreamKey;     // point:abc123
```

### 파생 키 생성

각 서비스가 상위 키에서 하위 키를 파생시키는 방식이다.

```
Client(key=abc123) → 주문서비스 → 결제서비스(derived=payment:abc123) → 포인트서비스(derived=point:abc123)
```

HMAC이나 단순 해시로 파생 키를 생성한다.

```java
String deriveKey(String parentKey, String serviceScope) {
    return HmacUtils.hmacSha256Hex(serviceScope, parentKey);
}

// 주문 서비스에서 결제 서비스 호출 시
String paymentKey = deriveKey(incomingKey, "payment-service");
httpClient.post("/payment")
    .header("Idempotency-Key", paymentKey)
    .execute();
```

파생 키의 핵심은 동일한 입력이 항상 동일한 출력을 만든다는 것이다. 재시도가 들어오면 상위 서비스가 같은 입력으로 같은 파생 키를 생성하고, 하위 서비스는 이미 처리한 키라는 걸 인식한다.

### 방식 선택 기준

두 서비스가 완전히 다른 팀이 관리하고 키 네임스페이스 충돌이 없다면 상위 키 재사용이 더 간단하다. 체인이 깊거나 외부 시스템을 호출할 때는 파생 키를 만드는 편이 낫다.

현실적으로는 두 방식을 섞어 쓰는 경우가 많다. 같은 도메인 내 서비스끼리는 키를 그대로 전파하고, 외부 결제 게이트웨이나 타 팀 서비스를 호출할 때는 파생 키를 만들어서 보낸다.

<div class="ygd-key-propagation" id="ygd-key-propagation">
<style>
.ygd-key-propagation{max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;border:1px solid var(--ygd-border);border-radius:8px;padding:12px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:14px;line-height:1.6;--ygd-bg:rgb(250,248,246);--ygd-fg:rgb(40,36,33);--ygd-muted:rgb(104,98,92);--ygd-border:rgb(205,199,192);--ygd-box:rgb(255,255,255);--ygd-accent:rgb(36,102,128);--ygd-accent2:rgb(124,58,166);--ygd-on-accent:rgb(255,255,255)}
body[data-md-color-scheme="slate"] .ygd-key-propagation{--ygd-bg:rgb(31,28,30);--ygd-fg:rgb(240,237,233);--ygd-muted:rgb(170,164,156);--ygd-border:rgb(86,80,84);--ygd-box:rgb(44,40,43);--ygd-accent:rgb(120,190,215);--ygd-accent2:rgb(206,160,240);--ygd-on-accent:rgb(20,20,20)}
.ygd-key-propagation *{box-sizing:border-box}
.ygd-key-propagation .ygd-title{font-weight:700;font-size:15px;margin:0 0 8px}
.ygd-key-propagation .ygd-bar{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.ygd-key-propagation .ygd-btn{font-family:inherit;font-size:14px;line-height:1.3;padding:6px 12px;min-height:36px;border:1px solid var(--ygd-border);border-radius:6px;background:var(--ygd-box);color:var(--ygd-fg);cursor:pointer;margin:0}
.ygd-key-propagation .ygd-btn[aria-selected="true"]{background:var(--ygd-accent);color:var(--ygd-on-accent);border-color:var(--ygd-accent)}
.ygd-key-propagation .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-key-propagation .ygd-play{margin-left:auto;font-weight:700}
.ygd-key-propagation .ygd-svg{display:block;width:100%;max-width:400px;height:auto;margin:0 auto}
.ygd-key-propagation .ygd-box{fill:var(--ygd-box);stroke:var(--ygd-border);stroke-width:1.5}
.ygd-key-propagation .ygd-nt{fill:var(--ygd-fg);font-size:13px;font-weight:700;font-family:inherit}
.ygd-key-propagation .ygd-t1{fill:var(--ygd-accent);font-size:12.5px;font-weight:700;font-family:inherit}
.ygd-key-propagation .ygd-t2{fill:var(--ygd-accent2);font-size:12.5px;font-weight:700;font-family:inherit}
.ygd-key-propagation .ygd-sub{fill:var(--ygd-muted);font-size:12px;font-family:inherit}
.ygd-key-propagation .ygd-line{fill:none;stroke-width:2.5}
.ygd-key-propagation .ygd-l1{stroke:var(--ygd-accent)}
.ygd-key-propagation .ygd-l2{stroke:var(--ygd-accent2)}
.ygd-key-propagation .ygd-ah1{fill:var(--ygd-accent)}
.ygd-key-propagation .ygd-ah2{fill:var(--ygd-accent2)}
.ygd-key-propagation .ygd-panel{margin-top:10px;padding:10px 12px;border-left:4px solid var(--ygd-accent);background:var(--ygd-box);border-radius:4px;font-size:14px;line-height:1.65}
.ygd-key-propagation .ygd-note{margin-top:8px;font-size:14px;color:var(--ygd-muted);line-height:1.6}
@media (prefers-reduced-motion:no-preference){.ygd-key-propagation .ygd-fade{animation:ygd-kp-fade .45s ease}}
@keyframes ygd-kp-fade{from{opacity:0}to{opacity:1}}
</style>
<div class="ygd-title">멱등성 키가 체인을 따라 전달되는 방식</div>
<div class="ygd-bar">
<div class="ygd-bar" role="tablist" aria-label="키 전파 방식 선택" style="margin-bottom:0">
<button type="button" class="ygd-btn ygd-tab" role="tab" aria-selected="true">상위 키 재사용</button>
<button type="button" class="ygd-btn ygd-tab" role="tab" aria-selected="false">파생 키 생성</button>
<button type="button" class="ygd-btn ygd-tab" role="tab" aria-selected="false">두 방식 혼합</button>
</div>
<button type="button" class="ygd-btn ygd-play" aria-pressed="false">재생</button>
</div>
<svg class="ygd-svg" viewBox="0 0 360 324" role="img" aria-label="서비스 체인에서 멱등성 키가 전달되는 경로"></svg>
<div class="ygd-panel" aria-live="polite"></div>
<div class="ygd-note">비유: 상위 키 재사용은 모든 창구에 같은 접수번호를 내미는 것, 파생 키는 접수번호에 창구 코드를 섞어 창구별 번호를 새로 만드는 것에 가깝다. 비유일 뿐이고 실제 구현은 서비스 prefix 또는 HMAC이다.</div>
<script>
(function(){
var root=document.getElementById('ygd-key-propagation');
if(!root){return;}
var svg=root.querySelector('.ygd-svg');
var panel=root.querySelector('.ygd-panel');
var tabs=Array.prototype.slice.call(root.querySelectorAll('.ygd-tab'));
var play=root.querySelector('.ygd-play');
var data=[
{aria:'상위 키 재사용: 클라이언트가 만든 키 abc123이 주문, 결제, 포인트 서비스까지 그대로 전달된다',
nodes:['Client','주문 서비스','결제 서비스','포인트 서비스'],
arrows:[
{k:1,a:'key = abc123',b:'클라이언트가 생성'},
{k:1,a:'key = abc123 (그대로 전달)',b:'결제 쪽 저장 키: payment:abc123'},
{k:1,a:'key = abc123 (그대로 전달)',b:'포인트 쪽 저장 키: point:abc123'}],
desc:'클라이언트가 만든 키 abc123을 체인 전체에 그대로 넘긴다. 단순하고, 어느 구간에서 재시도가 와도 같은 키로 멱등성 검사를 통과한다. 다만 여러 서비스가 같은 키를 받으므로 서비스 prefix를 붙여 저장해야 충돌하지 않는다.'},
{aria:'파생 키 생성: 각 서비스가 상위 키에서 서비스 범위별 하위 키를 만들어 다음 서비스에 전달한다',
nodes:['Client','주문 서비스','결제 서비스','포인트 서비스'],
arrows:[
{k:1,a:'key = abc123',b:'클라이언트가 생성'},
{k:2,a:'파생 키 (결제 범위)',b:'HMAC(상위 키, payment-service)'},
{k:2,a:'파생 키 (포인트 범위)',b:'같은 입력이면 항상 같은 값'}],
desc:'각 서비스가 상위 키와 서비스 범위로 하위 키를 HMAC이나 해시로 만들어 넘긴다. 같은 입력은 항상 같은 출력이라 재시도 때도 같은 파생 키가 만들어지고, 하위 서비스는 이미 처리한 키임을 알아본다. 체인이 깊거나 외부 시스템을 호출할 때 알맞다.'},
{aria:'혼합: 같은 도메인 안에서는 키를 그대로 전파하고 외부 결제 게이트웨이를 호출할 때만 파생 키를 만든다',
nodes:['Client','주문 서비스','포인트 서비스','외부 결제 게이트웨이'],
arrows:[
{k:1,a:'key = abc123',b:'클라이언트가 생성'},
{k:1,a:'key = abc123 (그대로)',b:'같은 도메인 안에서는 그대로 전파'},
{k:2,a:'파생 키',b:'외부 호출에는 파생 키를 만들어 보냄'}],
desc:'현실에서는 두 방식을 섞는 경우가 많다. 같은 도메인 안의 서비스끼리는 키를 그대로 전파하고, 외부 결제 게이트웨이나 타 팀 서비스를 호출할 때만 파생 키를 만들어 보낸다.'}
];
var NX=10,NW=140,NH=34,GAP=56,TOP=10,AX=80;
var cur=0,timer=null;
function build(d){
var s='<defs>'
+'<marker id="ygd-kp-ah1" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-ah1" d="M0 0L10 5L0 10z"/></marker>'
+'<marker id="ygd-kp-ah2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-ah2" d="M0 0L10 5L0 10z"/></marker>'
+'</defs><g class="ygd-fade">';
var i,y;
for(i=0;i<d.arrows.length;i++){
var ar=d.arrows[i];
y=TOP+i*(NH+GAP)+NH;
var mid=y+GAP/2;
s+='<line class="ygd-line ygd-l'+ar.k+'" x1="'+AX+'" y1="'+(y+2)+'" x2="'+AX+'" y2="'+(y+GAP-2)+'" marker-end="url(#ygd-kp-ah'+ar.k+')"/>';
s+='<text class="ygd-t'+ar.k+'" x="'+(AX+16)+'" y="'+(mid-2)+'">'+ar.a+'</text>';
s+='<text class="ygd-sub" x="'+(AX+16)+'" y="'+(mid+14)+'">'+ar.b+'</text>';
}
for(i=0;i<d.nodes.length;i++){
y=TOP+i*(NH+GAP);
s+='<rect class="ygd-box" x="'+NX+'" y="'+y+'" width="'+NW+'" height="'+NH+'" rx="6"/>';
s+='<text class="ygd-nt" x="'+(NX+NW/2)+'" y="'+(y+NH/2+4.5)+'" text-anchor="middle">'+d.nodes[i]+'</text>';
}
return s+'</g>';
}
function show(i){
cur=i;
tabs.forEach(function(t,j){t.setAttribute('aria-selected',j===i?'true':'false');t.setAttribute('tabindex',j===i?'0':'-1');});
svg.innerHTML=build(data[i]);
svg.setAttribute('aria-label',data[i].aria);
panel.textContent=data[i].desc;
}
function stop(){
if(timer){clearInterval(timer);timer=null;}
play.textContent='재생';
play.setAttribute('aria-pressed','false');
}
function start(){
show(0);
play.textContent='정지';
play.setAttribute('aria-pressed','true');
timer=setInterval(function(){
if(cur>=data.length-1){stop();return;}
show(cur+1);
},3500);
}
tabs.forEach(function(t,j){
t.addEventListener('click',function(){stop();show(j);});
t.addEventListener('keydown',function(e){
var n=-1;
if(e.key==='ArrowRight'){n=(j+1)%tabs.length;}
else if(e.key==='ArrowLeft'){n=(j+tabs.length-1)%tabs.length;}
if(n>=0){e.preventDefault();stop();show(n);tabs[n].focus();}
});
});
play.addEventListener('click',function(){if(timer){stop();}else{start();}});
show(0);
})();
</script>
</div>

## Saga 단계별 멱등 처리

Saga 패턴에서 각 단계는 독립적으로 멱등성을 보장해야 한다. 오케스트레이터가 실패한 단계를 재시도할 때 이미 성공한 단계를 다시 실행하는 경우가 생기기 때문이다.

### 상태 기반 멱등성 테이블

각 Saga 단계를 별도의 멱등성 레코드로 관리한다.

```sql
CREATE TABLE saga_idempotency (
    saga_id         VARCHAR(64)  NOT NULL,
    step_name       VARCHAR(64)  NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    status          VARCHAR(16)  NOT NULL,  -- PROCESSING, COMPLETED, FAILED
    response        TEXT,
    created_at      TIMESTAMP    NOT NULL,
    completed_at    TIMESTAMP,
    PRIMARY KEY (saga_id, step_name)
);
```

단계 실행 전에 `(saga_id, step_name)` 쌍으로 레코드를 확인한다. `COMPLETED`면 저장된 응답을 그대로 반환한다. `PROCESSING`이면 실행 중이라는 응답을 돌려주거나 잠시 대기한다.

```java
SagaIdempotency record = sagaIdempotencyRepo.findBySagaIdAndStep(sagaId, "payment");

if (record != null && record.getStatus().equals("COMPLETED")) {
    return deserialize(record.getResponse());
}

// 실제 처리
Result result = paymentService.process(command);

// 결과 저장
sagaIdempotencyRepo.save(sagaId, "payment", "COMPLETED", serialize(result));
return result;
```

`PROCESSING` 상태를 두는 이유는 같은 단계가 동시에 실행되는 경우를 막기 위해서다. 멱등성 레코드 삽입 시 `INSERT ... ON CONFLICT DO NOTHING`을 쓰고, 삽입 실패 시 기존 레코드 상태를 확인하는 방식으로 처리한다.

<div class="ygd-saga-idempotency" id="ygd-saga-idempotency">
<style>
.ygd-saga-idempotency{max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;border:1px solid var(--ygd-border);border-radius:8px;padding:12px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:14px;line-height:1.6;--ygd-bg:rgb(250,248,246);--ygd-fg:rgb(40,36,33);--ygd-muted:rgb(104,98,92);--ygd-border:rgb(205,199,192);--ygd-box:rgb(255,255,255);--ygd-accent:rgb(36,102,128);--ygd-ok:rgb(26,110,62);--ygd-warn:rgb(150,86,6);--ygd-on-accent:rgb(255,255,255)}
body[data-md-color-scheme="slate"] .ygd-saga-idempotency{--ygd-bg:rgb(31,28,30);--ygd-fg:rgb(240,237,233);--ygd-muted:rgb(170,164,156);--ygd-border:rgb(86,80,84);--ygd-box:rgb(44,40,43);--ygd-accent:rgb(120,190,215);--ygd-ok:rgb(120,205,150);--ygd-warn:rgb(240,180,95);--ygd-on-accent:rgb(20,20,20)}
.ygd-saga-idempotency *{box-sizing:border-box}
.ygd-saga-idempotency .ygd-title{font-weight:700;font-size:15px;margin:0 0 8px}
.ygd-saga-idempotency .ygd-bar{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;align-items:center}
.ygd-saga-idempotency .ygd-btn{font-family:inherit;font-size:14px;line-height:1.3;padding:6px 12px;min-height:36px;border:1px solid var(--ygd-border);border-radius:6px;background:var(--ygd-box);color:var(--ygd-fg);cursor:pointer;margin:0}
.ygd-saga-idempotency .ygd-btn[aria-pressed="true"]{background:var(--ygd-accent);color:var(--ygd-on-accent);border-color:var(--ygd-accent)}
.ygd-saga-idempotency .ygd-btn:disabled{opacity:.5;cursor:not-allowed}
.ygd-saga-idempotency .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-saga-idempotency .ygd-play{font-weight:700}
.ygd-saga-idempotency .ygd-status{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
.ygd-saga-idempotency .ygd-badge{display:inline-block;padding:2px 10px;border-radius:12px;border:2px solid var(--ygd-border);font-weight:700;font-size:14px;color:var(--ygd-fg)}
.ygd-saga-idempotency .ygd-st-processing{border-color:var(--ygd-warn);color:var(--ygd-warn)}
.ygd-saga-idempotency .ygd-st-completed{border-color:var(--ygd-ok);color:var(--ygd-ok)}
.ygd-saga-idempotency .ygd-svg{display:block;width:100%;max-width:420px;height:auto;margin:0 auto}
.ygd-saga-idempotency .ygd-actor{fill:var(--ygd-box);stroke:var(--ygd-border);stroke-width:1.5}
.ygd-saga-idempotency .ygd-an{fill:var(--ygd-fg);font-size:12px;font-weight:700;font-family:inherit}
.ygd-saga-idempotency .ygd-life{stroke:var(--ygd-border);stroke-width:1.5;stroke-dasharray:4 4}
.ygd-saga-idempotency .ygd-line{fill:none;stroke:var(--ygd-muted);stroke-width:2}
.ygd-saga-idempotency .ygd-dash{stroke-dasharray:6 4}
.ygd-saga-idempotency .ygd-lbl{fill:var(--ygd-fg);font-size:11.5px;font-family:inherit}
.ygd-saga-idempotency .ygd-ah{fill:var(--ygd-muted)}
.ygd-saga-idempotency .ygd-todo{opacity:.5}
.ygd-saga-idempotency .ygd-done .ygd-line{stroke:var(--ygd-accent)}
.ygd-saga-idempotency .ygd-done .ygd-ah{fill:var(--ygd-accent)}
.ygd-saga-idempotency .ygd-now .ygd-line{stroke:var(--ygd-accent);stroke-width:3.5}
.ygd-saga-idempotency .ygd-now .ygd-ah{fill:var(--ygd-accent)}
.ygd-saga-idempotency .ygd-now .ygd-lbl{font-weight:700}
.ygd-saga-idempotency .ygd-panel{margin-top:10px;padding:10px 12px;border-left:4px solid var(--ygd-accent);background:var(--ygd-box);border-radius:4px;font-size:14px;line-height:1.65;min-height:5.2em}
.ygd-saga-idempotency .ygd-counter{color:var(--ygd-muted);font-size:14px}
.ygd-saga-idempotency .ygd-note{margin-top:8px;font-size:14px;color:var(--ygd-muted);line-height:1.6}
@media (prefers-reduced-motion:no-preference){.ygd-saga-idempotency .ygd-now{animation:ygd-sg-pop .45s ease}}
@keyframes ygd-sg-pop{from{opacity:.2}to{opacity:1}}
</style>
<div class="ygd-title">같은 Saga 단계가 다시 들어왔을 때 멱등성 레코드가 하는 일</div>
<div class="ygd-bar" role="group" aria-label="재시도가 도착하는 시점 선택">
<button type="button" class="ygd-btn ygd-sc" aria-pressed="true">재시도가 완료 후 도착</button>
<button type="button" class="ygd-btn ygd-sc" aria-pressed="false">재시도가 처리 중 도착</button>
</div>
<div class="ygd-bar">
<button type="button" class="ygd-btn ygd-prev">이전</button>
<button type="button" class="ygd-btn ygd-play" aria-pressed="false">재생</button>
<button type="button" class="ygd-btn ygd-next">다음</button>
<button type="button" class="ygd-btn ygd-reset">처음으로</button>
<span class="ygd-counter"></span>
</div>
<svg class="ygd-svg" viewBox="0 0 360 308" role="img" aria-label="오케스트레이터, 결제 서비스, 멱등성 테이블 사이에서 Saga 결제 단계 요청과 재시도가 처리되는 순서"></svg>
<div class="ygd-status"><span>멱등성 레코드 (saga_id, payment) 상태:</span><span class="ygd-badge"></span></div>
<div class="ygd-panel" aria-live="polite"></div>
<div class="ygd-note">비유: 식당 주문서에 먼저 도장을 찍어 두는 것과 비슷하다. 같은 주문이 또 들어오면 도장을 보고 새로 조리하지 않는다. 비유일 뿐이고 실제로는 (saga_id, step_name) 레코드와 INSERT 충돌로 판단한다.</div>
<script>
(function(){
var root=document.getElementById('ygd-saga-idempotency');
if(!root){return;}
var svg=root.querySelector('.ygd-svg');
var panel=root.querySelector('.ygd-panel');
var badge=root.querySelector('.ygd-badge');
var counter=root.querySelector('.ygd-counter');
var scBtns=Array.prototype.slice.call(root.querySelectorAll('.ygd-sc'));
var prev=root.querySelector('.ygd-prev');
var next=root.querySelector('.ygd-next');
var play=root.querySelector('.ygd-play');
var reset=root.querySelector('.ygd-reset');
var actors=['오케스트레이터','결제 서비스','멱등성 테이블'];
var CX=[60,180,300];
var STLABEL={none:'레코드 없음',PROCESSING:'PROCESSING',COMPLETED:'COMPLETED'};
var scen=[
[
{f:0,t:1,l:'결제 단계 요청',s:'none',d:'오케스트레이터가 Saga의 결제 단계를 요청한다. 결제 서비스는 실행 전에 saga_id와 step_name 쌍으로 멱등성 레코드를 확인한다.'},
{f:1,t:2,l:'INSERT 시도',s:'PROCESSING',d:'레코드가 없어 삽입에 성공하고 상태는 PROCESSING이 된다. 같은 단계가 동시에 실행되는 것을 막는 표시다.'},
{f:1,t:2,l:'COMPLETED 저장',s:'COMPLETED',d:'결제 서비스가 실제 결제를 처리하고 결과를 응답과 함께 COMPLETED로 저장한다.'},
{f:0,t:1,l:'재시도 요청',s:'COMPLETED',d:'응답이 오케스트레이터에 닿지 못하는 등의 이유로 같은 단계를 다시 요청한다. 이미 성공한 단계가 다시 실행될 수 있는 상황이다.'},
{f:1,t:2,l:'조회: COMPLETED',s:'COMPLETED',d:'같은 saga_id와 step_name 레코드가 이미 있고 상태가 COMPLETED임을 확인한다.'},
{f:1,t:0,l:'저장된 응답 반환',dash:true,s:'COMPLETED',d:'결제를 다시 실행하지 않고 저장해 둔 응답을 그대로 돌려준다. 재시도가 와도 결제는 한 번만 일어난다.'}
],
[
{f:0,t:1,l:'결제 단계 요청',s:'none',d:'오케스트레이터가 Saga의 결제 단계를 요청한다. 결제 서비스는 실행 전에 멱등성 레코드를 확인한다.'},
{f:1,t:2,l:'INSERT 시도',s:'PROCESSING',d:'레코드가 없어 삽입에 성공하고 상태는 PROCESSING이 된다. 결제 처리는 아직 끝나지 않았다.'},
{f:0,t:1,l:'같은 단계 재시도',s:'PROCESSING',d:'처리가 끝나기 전에 같은 단계 요청이 다시 도착한다. 타임아웃 등으로 오케스트레이터가 먼저 재시도하는 경우다.'},
{f:1,t:2,l:'INSERT 충돌',s:'PROCESSING',d:'INSERT가 충돌해서 기존 레코드의 상태를 확인한다. 상태는 PROCESSING이다.'},
{f:1,t:0,l:'실행 중 응답',dash:true,s:'PROCESSING',d:'이미 실행 중이라는 응답을 돌려주거나 잠시 대기한다. 두 번째 실행은 시작되지 않는다.'},
{f:1,t:2,l:'COMPLETED 저장',s:'COMPLETED',d:'먼저 들어온 요청이 처리를 마치면 COMPLETED로 저장된다. 이후 재시도는 왼쪽 시나리오처럼 저장된 응답을 받는다.'}
]
];
var sc=0,step=0,timer=null;
var Y0=82,DY=44;
function build(){
var steps=scen[sc];
var s='<defs><marker id="ygd-sg-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-ah" d="M0 0L10 5L0 10z"/></marker></defs>';
var i;
for(i=0;i<3;i++){
s+='<line class="ygd-life" x1="'+CX[i]+'" y1="42" x2="'+CX[i]+'" y2="304"/>';
s+='<rect class="ygd-actor" x="'+(CX[i]-54)+'" y="6" width="108" height="34" rx="6"/>';
s+='<text class="ygd-an" x="'+CX[i]+'" y="27" text-anchor="middle">'+actors[i]+'</text>';
}
for(i=0;i<steps.length;i++){
var st=steps[i];
var y=Y0+i*DY;
var dir=CX[st.t]>CX[st.f]?1:-1;
var x1=CX[st.f]+dir*4,x2=CX[st.t]-dir*4;
s+=i<step?'<g class="ygd-done">':(i===step?'<g class="ygd-now">':'<g class="ygd-todo">');
s+='<line class="ygd-line'+(st.dash?' ygd-dash':'')+'" x1="'+x1+'" y1="'+y+'" x2="'+x2+'" y2="'+y+'" marker-end="url(#ygd-sg-ah)"/>';
s+='<text class="ygd-lbl" x="'+((CX[st.f]+CX[st.t])/2)+'" y="'+(y-9)+'" text-anchor="middle">'+st.l+'</text>';
s+='</g>';
}
return s;
}
function render(){
var steps=scen[sc];
var st=steps[step];
svg.innerHTML=build();
panel.textContent=st.d;
badge.textContent=STLABEL[st.s];
badge.className='ygd-badge'+(st.s==='PROCESSING'?' ygd-st-processing':(st.s==='COMPLETED'?' ygd-st-completed':''));
counter.textContent='단계 '+(step+1)+' / '+steps.length;
prev.disabled=step===0;
next.disabled=step===steps.length-1;
scBtns.forEach(function(b,j){b.setAttribute('aria-pressed',j===sc?'true':'false');});
}
function stop(){
if(timer){clearInterval(timer);timer=null;}
play.textContent='재생';
play.setAttribute('aria-pressed','false');
}
function start(){
if(step>=scen[sc].length-1){step=0;render();}
play.textContent='정지';
play.setAttribute('aria-pressed','true');
timer=setInterval(function(){
if(step>=scen[sc].length-1){stop();return;}
step++;render();
},2600);
}
scBtns.forEach(function(b,j){b.addEventListener('click',function(){stop();sc=j;step=0;render();});});
prev.addEventListener('click',function(){stop();if(step>0){step--;render();}});
next.addEventListener('click',function(){stop();if(step<scen[sc].length-1){step++;render();}});
reset.addEventListener('click',function(){stop();step=0;render();});
play.addEventListener('click',function(){if(timer){stop();}else{start();}});
render();
})();
</script>
</div>

### 이벤트 기반 Saga에서의 멱등성

코레오그래피 방식에서는 이벤트 소비 자체를 멱등으로 만들어야 한다.

```java
@KafkaListener(topics = "order-created")
public void handleOrderCreated(OrderCreatedEvent event) {
    String messageId = event.getMessageId();

    if (processedMessageRepo.exists(messageId)) {
        log.info("Duplicate message, skipping: {}", messageId);
        return;
    }

    reserveInventory(event);

    // TTL 설정 필수 — 메시지 큐의 최대 재전달 기간보다 길게
    processedMessageRepo.save(messageId, Duration.ofDays(7));
}
```

`processedMessageRepo`에는 Redis를 쓰는 경우가 많다. TTL이 너무 짧으면 재시도 시 멱등성 보장이 깨지므로 메시지 큐의 최대 재전달 기간을 기준으로 충분히 여유 있게 설정한다.

## 보상 트랜잭션 멱등성

보상 트랜잭션은 일반 트랜잭션보다 멱등성이 더 중요하다. 이미 롤백된 작업을 한 번 더 롤백하면 데이터가 망가진다.

### 보상 트랜잭션이 처리해야 하는 두 가지 경우

원래 트랜잭션이 성공했고 이를 되돌리는 경우가 있다. 이미 차감된 재고를 원복하거나, 이미 승인된 결제를 취소한다. 반면 원래 트랜잭션이 실패했거나 아예 실행되지 않아서 보상 자체가 무의미한 경우도 있다. 이걸 `No-Op 보상`이라고 부른다. 원래 작업이 없었으니 보상할 것도 없다.

```java
public CompensationResult compensatePayment(String sagaId, String orderId) {
    Optional<PaymentRecord> payment = paymentRepo.findBySagaId(sagaId);

    if (payment.isEmpty()) {
        // 결제 자체가 실행된 적 없음 - No-Op
        return CompensationResult.NO_OP;
    }

    if (payment.get().getStatus() == REFUNDED) {
        // 이미 환불 완료 - 멱등 처리
        return CompensationResult.ALREADY_COMPENSATED;
    }

    refund(payment.get());
    return CompensationResult.SUCCESS;
}
```

### 보상 멱등성 키

보상 트랜잭션도 별도의 멱등성 키를 가져야 한다. 원본 트랜잭션 키와 구분하기 위해 접두사를 붙인다.

```java
String compensationKey = "compensate:" + originalSagaId + ":" + stepName;
```

보상 트랜잭션 실행 전에 이 키를 확인하고, 이미 실행됐으면 캐싱된 결과를 반환한다.

### 외부 시스템 보상

외부 결제 게이트웨이 같은 서비스의 보상이 멱등하지 않을 수 있다. 이때는 보상 실행 결과를 로컬 DB에 저장하고, 이후 재시도 시 외부 API를 호출하지 않고 로컬 결과를 반환한다.

```java
String compensationKey = "pg:refund:" + paymentId;

Optional<RefundResult> cachedResult = idempotencyStore.get(compensationKey);
if (cachedResult.isPresent()) {
    return cachedResult.get();
}

RefundResult result = paymentGateway.refund(paymentId, amount);

// TTL은 충분히 길게
idempotencyStore.save(compensationKey, result, Duration.ofDays(30));
return result;
```

## 클라이언트 SDK 재시도 키 영속화

모바일 앱이나 웹 클라이언트에서 요청을 보낼 때 네트워크가 끊기거나 앱이 종료되면 재시도 시 새로운 멱등성 키를 생성하는 실수를 저지른다. 그러면 서버가 중복 요청을 막지 못한다.

### 로컬 저장소 기반 영속화

요청을 보내기 전에 멱등성 키를 로컬 저장소에 저장하고, 성공 응답을 받은 후에 삭제한다.

```kotlin
class IdempotentApiClient(private val prefs: SharedPreferences) {

    fun placeOrder(orderRequest: OrderRequest): OrderResponse {
        val operationKey = "place_order:${orderRequest.cartId}"

        // 기존 키 조회 또는 새 키 생성
        val idempotencyKey = prefs.getString(operationKey, null)
            ?: UUID.randomUUID().toString().also {
                prefs.edit().putString(operationKey, it).apply()
            }

        return try {
            val response = api.placeOrder(orderRequest, idempotencyKey)
            prefs.edit().remove(operationKey).apply()
            response
        } catch (e: NetworkException) {
            // 네트워크 오류 - 키 유지, 재시도 시 같은 키 사용
            throw e
        } catch (e: HttpException) {
            if (e.code() in 400..499) {
                // 클라이언트 오류 - 요청이 잘못됐으니 키 삭제
                prefs.edit().remove(operationKey).apply()
            }
            throw e
        }
    }
}
```

### 멱등성 키 생명주기

멱등성 키를 언제 삭제할지가 핵심이다.

2xx 응답이 왔을 때는 키를 삭제한다. 다음에 같은 작업을 하면 새로운 요청으로 처리해야 한다. 4xx 응답이 왔을 때도 키를 삭제하고 수정된 요청으로 재시도해야 한다. 같은 키로 재시도하면 서버가 캐싱된 4xx를 그대로 반환해버린다. 5xx나 네트워크 오류의 경우는 키를 유지하고 동일 키로 재시도한다. 서버가 요청을 처리했는지 알 수 없기 때문이다.

```kotlin
fun handleResponse(response: Response, operationKey: String) {
    when {
        response.isSuccessful    -> deleteKey(operationKey)
        response.code in 400..499 -> deleteKey(operationKey)
        // 5xx, 타임아웃 - 키 유지
    }
}
```

<div class="ygd-key-lifecycle" id="ygd-key-lifecycle">
<style>
.ygd-key-lifecycle{max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;border:1px solid var(--ygd-border);border-radius:8px;padding:12px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:14px;line-height:1.6;--ygd-bg:rgb(250,248,246);--ygd-fg:rgb(40,36,33);--ygd-muted:rgb(104,98,92);--ygd-border:rgb(205,199,192);--ygd-box:rgb(255,255,255);--ygd-accent:rgb(36,102,128);--ygd-ok:rgb(26,110,62);--ygd-bad:rgb(176,40,40);--ygd-warn:rgb(150,86,6);--ygd-on-accent:rgb(255,255,255)}
body[data-md-color-scheme="slate"] .ygd-key-lifecycle{--ygd-bg:rgb(31,28,30);--ygd-fg:rgb(240,237,233);--ygd-muted:rgb(170,164,156);--ygd-border:rgb(86,80,84);--ygd-box:rgb(44,40,43);--ygd-accent:rgb(120,190,215);--ygd-ok:rgb(120,205,150);--ygd-bad:rgb(245,130,130);--ygd-warn:rgb(240,180,95);--ygd-on-accent:rgb(20,20,20)}
.ygd-key-lifecycle *{box-sizing:border-box}
.ygd-key-lifecycle .ygd-title{font-weight:700;font-size:15px;margin:0 0 8px}
.ygd-key-lifecycle .ygd-bar{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;align-items:center}
.ygd-key-lifecycle .ygd-btn{font-family:inherit;font-size:14px;line-height:1.3;padding:6px 12px;min-height:36px;border:1px solid var(--ygd-border);border-radius:6px;background:var(--ygd-box);color:var(--ygd-fg);cursor:pointer;margin:0}
.ygd-key-lifecycle .ygd-btn[aria-pressed="true"]{background:var(--ygd-accent);color:var(--ygd-on-accent);border-color:var(--ygd-accent)}
.ygd-key-lifecycle .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-key-lifecycle .ygd-play{font-weight:700}
.ygd-key-lifecycle .ygd-status{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
.ygd-key-lifecycle .ygd-badge{display:inline-block;padding:2px 10px;border-radius:12px;border:2px solid var(--ygd-border);font-weight:700;font-size:14px;color:var(--ygd-fg)}
.ygd-key-lifecycle .ygd-st-has{border-color:var(--ygd-accent);color:var(--ygd-accent)}
.ygd-key-lifecycle .ygd-st-gone{border-color:var(--ygd-muted);color:var(--ygd-muted)}
.ygd-key-lifecycle .ygd-svg{display:block;width:100%;max-width:420px;height:auto;margin:0 auto}
.ygd-key-lifecycle .ygd-conn{stroke:var(--ygd-border);stroke-width:3}
.ygd-key-lifecycle .ygd-dot{fill:var(--ygd-box);stroke:var(--ygd-accent);stroke-width:2.5}
.ygd-key-lifecycle .ygd-dot-ok{stroke:var(--ygd-ok)}
.ygd-key-lifecycle .ygd-dot-bad{stroke:var(--ygd-bad)}
.ygd-key-lifecycle .ygd-dot-warn{stroke:var(--ygd-warn)}
.ygd-key-lifecycle .ygd-num{fill:var(--ygd-fg);font-size:12px;font-weight:700;font-family:inherit}
.ygd-key-lifecycle .ygd-h{fill:var(--ygd-fg);font-size:13px;font-weight:700;font-family:inherit}
.ygd-key-lifecycle .ygd-sub{fill:var(--ygd-muted);font-size:12px;font-family:inherit}
.ygd-key-lifecycle .ygd-todo{opacity:.45}
.ygd-key-lifecycle .ygd-now .ygd-h{fill:var(--ygd-accent)}
.ygd-key-lifecycle .ygd-panel{margin-top:10px;padding:10px 12px;border-left:4px solid var(--ygd-accent);background:var(--ygd-box);border-radius:4px;font-size:14px;line-height:1.65;min-height:5.2em}
.ygd-key-lifecycle .ygd-note{margin-top:8px;font-size:14px;color:var(--ygd-muted);line-height:1.6}
@media (prefers-reduced-motion:no-preference){.ygd-key-lifecycle .ygd-now{animation:ygd-kl-pop .45s ease}}
@keyframes ygd-kl-pop{from{opacity:.2}to{opacity:1}}
</style>
<div class="ygd-title">응답 종류에 따라 클라이언트의 멱등성 키가 어떻게 되는가</div>
<div class="ygd-bar" role="group" aria-label="응답 종류 선택">
<button type="button" class="ygd-btn ygd-sc" aria-pressed="true">2xx 성공</button>
<button type="button" class="ygd-btn ygd-sc" aria-pressed="false">4xx 클라이언트 오류</button>
<button type="button" class="ygd-btn ygd-sc" aria-pressed="false">5xx 또는 네트워크 오류</button>
<button type="button" class="ygd-btn ygd-play" aria-pressed="false">재생</button>
</div>
<svg class="ygd-svg" viewBox="0 0 360 288" role="img" aria-label="요청 전 키 저장부터 응답 종류별 키 삭제 또는 유지, 다음 동작까지의 시간 순서"></svg>
<div class="ygd-status"><span>로컬 저장소의 키:</span><span class="ygd-badge"></span></div>
<div class="ygd-panel" aria-live="polite"></div>
<div class="ygd-note">비유: 택배 송장번호를 보관해 두는 것과 비슷하다. 배송 결과를 모르면 같은 송장번호로 조회하고, 끝났거나 접수가 반려되면 번호를 버리고 새로 받는다. 비유일 뿐이고 기준은 위에 적은 응답 코드 규칙이다.</div>
<script>
(function(){
var root=document.getElementById('ygd-key-lifecycle');
if(!root){return;}
var svg=root.querySelector('.ygd-svg');
var panel=root.querySelector('.ygd-panel');
var badge=root.querySelector('.ygd-badge');
var scBtns=Array.prototype.slice.call(root.querySelectorAll('.ygd-sc'));
var play=root.querySelector('.ygd-play');
var common=[
{h:'요청 직전',s:'키를 로컬 저장소에 먼저 저장',k:true,d:'요청을 보내기 전에 멱등성 키를 로컬 저장소에 저장한다. 앱이 중간에 종료돼도 같은 작업의 재시도가 같은 키를 쓸 수 있다.'},
{h:'요청 전송',s:'저장된 키와 함께 서버로 전송',k:true,d:'멱등성 키와 함께 요청이 서버로 간다. 이 시점에는 서버가 요청을 처리했는지 아직 알 수 없다.'}
];
var scen=[
{cls:'ok',rest:[
{h:'2xx 성공 응답',s:'서버가 요청을 처리했다',k:true,d:'서버가 2xx로 응답했다.'},
{h:'키 삭제',s:'저장소에서 키를 지운다',k:false,d:'성공했으므로 저장소에서 키를 삭제한다.'},
{h:'다음 작업은 새 키',s:'같은 작업을 또 하면 새 요청',k:false,d:'다음에 같은 작업을 하면 새로운 요청으로 처리해야 하므로 새 키를 만든다.'}]},
{cls:'bad',rest:[
{h:'4xx 클라이언트 오류',s:'요청 자체에 문제가 있다',k:true,d:'4xx 응답이 왔다. 요청 내용에 문제가 있다는 뜻이다.'},
{h:'키 삭제',s:'저장소에서 키를 지운다',k:false,d:'4xx일 때도 키를 삭제한다.'},
{h:'수정한 요청 + 새 키',s:'같은 키면 캐싱된 4xx가 반환됨',k:false,d:'수정된 요청으로 새 키를 써서 재시도한다. 같은 키로 재시도하면 서버가 캐싱해 둔 4xx를 그대로 반환해 버린다.'}]},
{cls:'warn',rest:[
{h:'5xx 또는 네트워크 오류',s:'처리 여부를 알 수 없다',k:true,d:'5xx를 받았거나 타임아웃, 네트워크 오류가 났다. 서버가 요청을 처리했는지 알 수 없다.'},
{h:'키 유지',s:'저장소에 키를 그대로 둔다',k:true,d:'처리 여부를 모르기 때문에 키를 지우지 않고 유지한다.'},
{h:'같은 키로 재시도',s:'서버가 이미 처리했을 수 있음',k:true,d:'재시도할 때 저장해 둔 같은 키를 쓴다. 서버가 이미 처리했다면 멱등성 검사가 중복 실행을 막는다.'}]}
];
var sc=0,step=4,timer=null;
function nodes(){return common.concat(scen[sc].rest);}
function build(){
var ns=nodes();
var s='';
var i,cy;
for(i=0;i<ns.length-1;i++){
s+='<line class="ygd-conn" x1="24" y1="'+(24+i*60+12)+'" x2="24" y2="'+(24+(i+1)*60-12)+'"/>';
}
for(i=0;i<ns.length;i++){
cy=24+i*60;
var dc=i>=2?' ygd-dot-'+scen[sc].cls:'';
s+=i<step?'<g class="ygd-done">':(i===step?'<g class="ygd-now">':'<g class="ygd-todo">');
s+='<circle class="ygd-dot'+dc+'" cx="24" cy="'+cy+'" r="12"/>';
s+='<text class="ygd-num" x="24" y="'+(cy+4.5)+'" text-anchor="middle">'+(i+1)+'</text>';
s+='<text class="ygd-h" x="48" y="'+(cy-2)+'">'+ns[i].h+'</text>';
s+='<text class="ygd-sub" x="48" y="'+(cy+15)+'">'+ns[i].s+'</text>';
s+='</g>';
}
return s;
}
function render(){
var ns=nodes();
svg.innerHTML=build();
panel.textContent=ns[step].d;
var has=ns[step].k;
badge.textContent=has?'있음':'삭제됨';
badge.className='ygd-badge '+(has?'ygd-st-has':'ygd-st-gone');
scBtns.forEach(function(b,j){b.setAttribute('aria-pressed',j===sc?'true':'false');});
}
function stop(){
if(timer){clearInterval(timer);timer=null;}
play.textContent='재생';
play.setAttribute('aria-pressed','false');
}
function start(){
step=0;render();
play.textContent='정지';
play.setAttribute('aria-pressed','true');
timer=setInterval(function(){
if(step>=4){stop();return;}
step++;render();
},2600);
}
scBtns.forEach(function(b,j){b.addEventListener('click',function(){stop();sc=j;step=4;render();});});
play.addEventListener('click',function(){if(timer){stop();}else{start();}});
render();
})();
</script>
</div>

### 앱 재시작 후 미완료 요청 처리

앱이 재시작되면 이전에 실행 중이던 요청의 상태를 알 수 없다. 로컬 저장소에 키가 남아있으면 해당 요청이 완료되지 않았다고 보고 재시도한다.

```kotlin
class PendingRequestRecovery(private val prefs: SharedPreferences) {

    fun recoverOnAppStart() {
        val pendingKeys = prefs.all.filter { it.key.startsWith("place_order:") }

        pendingKeys.forEach { (operationKey, idempotencyKey) ->
            val result = queryRequestStatus(idempotencyKey as String)

            when (result) {
                is Success    -> prefs.edit().remove(operationKey).apply()
                is NotFound   -> retryRequest(operationKey, idempotencyKey)
                is InProgress -> scheduleRetry(operationKey, idempotencyKey)
            }
        }
    }
}
```

일부 서버는 멱등성 키로 요청 상태를 조회하는 별도 API를 제공한다. 이 API가 없으면 재시도 자체가 멱등 처리를 하므로 단순히 재요청해도 된다.

### 네트워크 변경 대응

Wi-Fi에서 LTE로 전환되거나 VPN이 끊길 때 진행 중인 요청이 실패한다. 재시도 큐에 멱등성 키와 함께 요청을 넣고, 네트워크가 복구되면 자동으로 재시도하는 방식으로 처리한다.

```kotlin
class RetryQueue(private val db: LocalDatabase) {

    fun enqueue(request: PendingRequest) {
        db.insert(PendingRequestEntity(
            idempotencyKey = request.idempotencyKey,
            requestBody    = serialize(request),
            retryCount     = 0,
            nextRetryAt    = Instant.now()
        ))
    }

    fun processQueue() {
        db.getPendingRequests(before = Instant.now()).forEach { entity ->
            try {
                execute(deserialize(entity.requestBody), entity.idempotencyKey)
                db.delete(entity)
            } catch (e: Exception) {
                db.updateRetry(entity, nextRetryAt = exponentialBackoff(entity.retryCount))
            }
        }
    }
}
```

로컬 DB에 요청을 저장하면 앱이 강제 종료되거나 기기가 꺼져도 미완료 요청이 유실되지 않는다. 재시도 횟수와 다음 재시도 시간을 함께 저장해서 지수 백오프를 구현한다.

## 주의사항

**멱등성 키 TTL**: 서버에서 멱등성 키를 영구 보존하면 안 된다. 주문의 경우 최소 24시간에서 7일 정도가 일반적이다. TTL이 너무 짧으면 재시도 시 멱등성 보장이 깨진다.

**분산 환경에서의 키 저장소**: 여러 서버 인스턴스가 멱등성 키를 공유해야 한다. 로컬 캐시만 쓰면 다른 인스턴스로 요청이 라우팅될 때 중복 처리가 발생한다. Redis나 DB를 공유 저장소로 써야 한다.

**응답 캐싱 크기**: 서버가 멱등성 키에 매핑된 응답을 캐싱할 때, 응답 크기가 크면 저장 비용이 늘어난다. 응답을 압축하거나 응답의 핵심 식별자만 저장하는 방법을 고려한다.

**Saga 오케스트레이터 장애**: 오케스트레이터 자체가 죽으면 Saga 상태를 복구해야 한다. Saga 상태와 멱등성 키를 같은 DB 트랜잭션에 저장하면 일관성을 유지할 수 있다.
