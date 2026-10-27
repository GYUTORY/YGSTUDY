---
title: ECS Networking Modes — awsvpc / bridge / host / none 모드 상세
tags: [aws, network, cloud]
updated: 2026-10-27
---

# ECS Networking Modes

## 개요

ECS에서 네트워크 모드를 고른다는 건 단순히 "컨테이너가 어떻게 IP를 받을지"의 문제가 아니다. Task에 보안 그룹을 붙일 수 있는지, ALB 타깃 그룹을 IP 타입으로 쓸지 인스턴스 타입으로 쓸지, Service Connect/Cloud Map과 어떻게 맞물리는지, Fargate로 갈 수 있는지, VPC Endpoint 비용을 얼마나 줄일 수 있는지가 모두 이 선택 하나에서 갈린다.

네트워크 모드는 Task Definition에서 `networkMode` 필드로 지정한다. 값은 넷 중 하나다.

- `awsvpc` — Task당 ENI 하나. Fargate는 무조건 이 모드.
- `bridge` — Docker bridge 네트워크. 호스트의 ENI를 공유하고 포트 매핑으로 노출.
- `host` — 호스트 네트워크 스택을 그대로 사용. 포트 충돌 주의.
- `none` — 외부 네트워크 없음. 네트워크가 필요 없는 배치 작업용.

ENI 개수 제한과 Task 밀도 계산은 [ECS ENI 제한과 Task 한계](ECS_ENI_제한과_Task_한계.md) 문서에서 다뤘고, 여기서는 모드별 동작 원리와 실무에서 부딪히는 포트 매핑, 서비스 디스커버리, VPC Endpoint 구성에 집중한다.

```mermaid
flowchart LR
    A[Task Definition] --> B{networkMode}
    B -->|awsvpc| C[Task당 ENI 1개<br/>Fargate 강제]
    B -->|bridge| D[Docker bridge<br/>포트 매핑]
    B -->|host| E[호스트 네트워크<br/>직접 사용]
    B -->|none| F[외부 통신 차단]
    C --> G[SG 개별 적용<br/>ALB IP target]
    D --> H[SG 인스턴스 공유<br/>ALB instance target]
    E --> I[포트 충돌 위험]
    F --> J[배치/연산 작업]
```

## awsvpc 모드 — Task당 ENI 할당 구조

### 동작 원리

awsvpc 모드에서 Task가 뜨면 ECS Agent가 다음 순서를 밟는다.

1. Task 배치가 결정되면 ECS가 먼저 **ENI를 생성**한다 (이 단계에서 VPC API 호출 발생).
2. ENI가 지정된 서브넷에 할당되고, Task에 지정한 **보안 그룹이 ENI에 attach** 된다.
3. ENI가 EC2 인스턴스 또는 Fargate 호스트에 hot-attach 된다.
4. ENI 내부에 네임스페이스가 만들어지고, 컨테이너가 그 네임스페이스에서 기동한다.

이 과정은 보통 10~30초가 걸린다. Service 배포 중 Task 시작이 느리게 느껴지는 가장 큰 이유가 이 ENI 프로비저닝이다. Auto Scaling 이벤트가 터졌을 때 bridge 모드는 몇 초 내로 Task가 RUNNING 되는데, awsvpc는 `PROVISIONING` → `ACTIVATING` 상태를 길게 거친다.

### Task별 보안 그룹의 실제 효과

awsvpc 모드의 가장 큰 장점은 **보안 그룹이 Task 단위로 적용된다**는 점이다. 같은 EC2 인스턴스에 웹 서버 Task와 배치 워커 Task가 같이 떠 있어도, 각각 다른 SG를 붙일 수 있다. 웹은 ALB에서만 8080을 받고, 배치는 SQS와 RDS로만 아웃바운드가 열려 있는 식.

bridge/host 모드에서는 보안 그룹이 **인스턴스 ENI에 붙어 있어서** 같은 인스턴스에 뜬 모든 컨테이너가 같은 SG를 공유한다. 컨테이너 A만 외부 포트를 열고 컨테이너 B는 막고 싶어도, SG 레벨에서는 분리가 안 된다.

실무에서 특히 자주 걸리는 상황이 있다. 같은 Service 내에서 여러 컨테이너를 하나의 Task로 묶어 띄울 때, awsvpc 모드에서는 **컨테이너들이 같은 ENI를 공유**한다는 점이다. Task 안의 컨테이너들은 `localhost`로 서로를 부르지만, Task 외부에서는 ENI에 붙은 SG를 공유한다. Task 내부 격리는 불가능하다.

### ALB Target Type 선택

awsvpc 모드에서는 ALB Target Group의 타겟 타입을 반드시 **IP**로 설정해야 한다. `instance` 타입으로 설정하면 등록 자체는 되지만 트래픽이 엉뚱한 곳으로 간다.

```json
{
  "TargetType": "ip",
  "VpcId": "vpc-xxxx",
  "Port": 8080,
  "Protocol": "HTTP"
}
```

instance 타입은 EC2 인스턴스의 프라이머리 ENI로 트래픽을 보내는 구조라서, Task 전용 ENI를 거치지 않는다. bridge/host 모드에서만 instance 타입을 쓴다.

### 서브넷 IP 고갈 문제

awsvpc는 Task마다 IP를 하나씩 쓴다. `/24` 서브넷이 약 250개 IP인데, 배포 중에는 구버전 + 신버전 Task가 동시에 떠서 평소보다 2배의 IP를 쓴다. `minimumHealthyPercent=100, maximumPercent=200`으로 배포하면 순간적으로 Task 수가 두 배가 되는데, 여기에 EC2 인스턴스 자체 IP와 다른 리소스(RDS, ElastiCache, NAT 등)까지 합치면 생각보다 금방 바닥난다.

IP 고갈이 나면 Task가 `PENDING` 상태에서 안 넘어가고, `RESOURCE:ENI` 에러가 CloudTrail에 찍힌다. 처음부터 `/22`(약 1,000개 IP) 이상으로 서브넷을 잡거나, awsvpc용 서브넷을 따로 분리해서 구성하는 게 안전하다.

<div class="ygd-awsvpc-subnet-ip-exhaustion" id="ygd-awsvpc-subnet-ip-exhaustion">
<style>
.ygd-awsvpc-subnet-ip-exhaustion{--ygd-bg:rgb(250,248,246);--ygd-border:rgb(214,208,201);--ygd-text:rgb(38,35,32);--ygd-muted:rgb(95,90,85);--ygd-other:rgb(138,143,152);--ygd-old:rgb(74,127,176);--ygd-new:rgb(47,143,91);--ygd-pend:rgb(192,57,43);--ygd-hl:rgba(61,115,135,0.12);--ygd-accent:rgb(61,115,135);--ygd-accent-text:rgb(255,255,255);--ygd-btn-bg:rgb(255,255,255);--ygd-focus:rgb(26,84,200);max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:16px;border:1px solid var(--ygd-border);border-radius:10px;background:var(--ygd-bg);color:var(--ygd-text);font-size:15px;line-height:1.6;overflow:hidden}
body[data-md-color-scheme="slate"] .ygd-awsvpc-subnet-ip-exhaustion{--ygd-bg:rgb(38,35,40);--ygd-border:rgb(78,73,80);--ygd-text:rgb(236,232,227);--ygd-muted:rgb(181,175,168);--ygd-other:rgb(122,128,138);--ygd-old:rgb(106,163,214);--ygd-new:rgb(79,191,134);--ygd-pend:rgb(255,122,107);--ygd-hl:rgba(140,190,210,0.16);--ygd-accent:rgb(120,180,200);--ygd-accent-text:rgb(24,22,26);--ygd-btn-bg:rgb(52,48,54);--ygd-focus:rgb(130,177,255)}
.ygd-awsvpc-subnet-ip-exhaustion *{box-sizing:border-box}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-title{margin:0 0 4px;font-size:17px;font-weight:700;line-height:1.4;color:var(--ygd-text)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-note{margin:0 0 12px;font-size:14px;color:var(--ygd-muted)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-bar{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-group{display:flex;gap:0;border:1px solid var(--ygd-border);border-radius:8px;overflow:hidden}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-btn{min-height:40px;padding:6px 14px;border:0;margin:0;background:var(--ygd-btn-bg);color:var(--ygd-text);font:inherit;font-size:15px;line-height:1.3;cursor:pointer}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-ctl{border:1px solid var(--ygd-border);border-radius:8px}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-btn[aria-pressed="true"]{background:var(--ygd-accent);color:var(--ygd-accent-text);font-weight:700}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-play{background:var(--ygd-accent);color:var(--ygd-accent-text);font-weight:700}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-btn:disabled{opacity:0.45;cursor:default}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px;position:relative;z-index:1}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-svgwrap{width:100%;max-width:560px;margin:0 auto}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-svg{display:block;width:100%;height:auto;max-width:100%}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-svg text{font-size:13px;font-family:inherit;fill:var(--ygd-text)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-svg .ygd-mut{fill:var(--ygd-muted)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-svg .ygd-err{fill:var(--ygd-pend);font-weight:700}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-axis{stroke:var(--ygd-muted);stroke-width:1}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-cap{stroke:var(--ygd-pend);stroke-width:1.5;stroke-dasharray:5 4}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-hlr{fill:var(--ygd-hl)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-seg-o{fill:var(--ygd-other);stroke:var(--ygd-bg);stroke-width:1}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-seg-old{fill:var(--ygd-old);stroke:var(--ygd-bg);stroke-width:1}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-seg-new{fill:var(--ygd-new);stroke:var(--ygd-bg);stroke-width:1}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-seg-p{fill:url(#ygd-sub-hatch);stroke:var(--ygd-pend);stroke-width:1.5;stroke-dasharray:4 3}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-hatch-bg{fill:var(--ygd-bg)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-hatch-ln{stroke:var(--ygd-pend);stroke-width:2}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-colg{opacity:0.5;transition:opacity 0.3s;transform-box:fill-box;transform-origin:50% 100%}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-colg.ygd-past{opacity:0.8}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-colg.ygd-now{opacity:1}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-colg.ygd-grow{animation:ygd-sub-grow 0.6s ease-out}
@keyframes ygd-sub-grow{from{transform:scaleY(0.3);opacity:0.4}to{transform:scaleY(1);opacity:1}}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:10px 0;padding:0;font-size:14px;color:var(--ygd-muted)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-li{display:flex;align-items:center;gap:6px}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-sw{display:inline-block;width:14px;height:14px;border-radius:3px;flex:none}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-sw-o{background:var(--ygd-other)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-sw-old{background:var(--ygd-old)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-sw-new{background:var(--ygd-new)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-sw-p{border:2px dashed var(--ygd-pend);background:transparent}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-sw-cap{height:0;border-top:2px dashed var(--ygd-pend);border-radius:0}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-readout{margin:8px 0;font-size:14px;font-weight:700;color:var(--ygd-text);overflow-wrap:anywhere}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-panel{margin:0;padding:10px 12px;border-left:4px solid var(--ygd-accent);border-radius:4px;background:var(--ygd-hl);font-size:15px;line-height:1.6;color:var(--ygd-text)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-panel.ygd-bad{border-left-color:var(--ygd-pend)}
.ygd-awsvpc-subnet-ip-exhaustion .ygd-foot{margin:10px 0 0;font-size:14px;color:var(--ygd-muted)}
@media (prefers-reduced-motion:reduce){.ygd-awsvpc-subnet-ip-exhaustion .ygd-colg{transition:none}.ygd-awsvpc-subnet-ip-exhaustion .ygd-colg.ygd-grow{animation:none}}
</style>
<p class="ygd-title">롤링 배포 중 서브넷 IP 사용량 타임라인</p>
<p class="ygd-note">awsvpc는 Task마다 IP를 하나씩 쓴다. 비유하면 서브넷 IP 풀은 주차장이고 Task 한 개가 한 칸을 차지한다. 롤링 배포는 구버전이 빠지기 전에 신버전이 먼저 들어오는 방식이라 잠시 두 배의 칸이 필요하다. 다만 칸이 모자라면 줄을 서는 대신 Task가 PENDING에 남는다.</p>
<div class="ygd-bar">
<div class="ygd-group" role="group" aria-label="서브넷 크기 선택">
<button type="button" class="ygd-btn ygd-m24" aria-pressed="true">/24 서브넷</button>
<button type="button" class="ygd-btn ygd-m22" aria-pressed="false">/22 서브넷</button>
</div>
<button type="button" class="ygd-btn ygd-ctl ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-ctl ygd-prev">이전 단계</button>
<button type="button" class="ygd-btn ygd-ctl ygd-next">다음 단계</button>
</div>
<div class="ygd-svgwrap">
<svg class="ygd-svg" viewBox="0 0 420 248" role="img" aria-label="롤링 배포 중 서브넷 IP 사용량 막대 그래프">
<defs><pattern id="ygd-sub-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" class="ygd-hatch-bg"></rect><line x1="0" y1="0" x2="0" y2="6" class="ygd-hatch-ln"></line></pattern></defs>
<g class="ygd-hlg"></g>
<g class="ygd-bars"></g>
<line class="ygd-axis" x1="52" y1="220" x2="414" y2="220"></line>
<line class="ygd-cap" x1="52" y1="87" x2="414" y2="87"></line>
<text class="ygd-capt ygd-mut" x="46" y="91" text-anchor="end">250</text>
<g class="ygd-xl"></g>
</svg>
</div>
<div class="ygd-legend">
<span class="ygd-li"><span class="ygd-sw ygd-sw-o"></span>기타 리소스 IP (인스턴스, RDS, ElastiCache, NAT 등)</span>
<span class="ygd-li"><span class="ygd-sw ygd-sw-old"></span>구버전 Task</span>
<span class="ygd-li"><span class="ygd-sw ygd-sw-new"></span>신버전 Task</span>
<span class="ygd-li"><span class="ygd-sw ygd-sw-p"></span>IP가 없어 PENDING인 신버전 Task</span>
<span class="ygd-li"><span class="ygd-sw ygd-sw-cap"></span>서브넷 IP 풀 한도</span>
</div>
<p class="ygd-readout" aria-hidden="true"></p>
<p class="ygd-panel" aria-live="polite"></p>
<p class="ygd-foot">수치는 설명용 가정이다: 평상시 Task 110개, 기타 리소스 IP 50개, minimumHealthyPercent=100, maximumPercent=200. 풀 크기는 /24가 약 250개, /22가 약 1,000개다.</p>
<script>
(function(){
var root=document.getElementById('ygd-awsvpc-subnet-ip-exhaustion');
if(!root||root.getAttribute('data-ygd-init')==='1'){return;}
root.setAttribute('data-ygd-init','1');
var NS='http://www.w3.org/2000/svg';
function q(s){return root.querySelector(s);}
var svg=q('.ygd-svg'),barsG=q('.ygd-bars'),hlG=q('.ygd-hlg'),xlG=q('.ygd-xl');
var capLine=q('.ygd-cap'),capT=q('.ygd-capt');
var readout=q('.ygd-readout'),panel=q('.ygd-panel');
var bPlay=q('.ygd-play'),bPrev=q('.ygd-prev'),bNext=q('.ygd-next');
var b24=q('.ygd-m24'),b22=q('.ygd-m22');
var BASE=220,H=170,X0=52,CW=90,BW=54;
var MODES={
m24:{name:'/24',pool:250,axis:320,capLabel:'250',poolText:'약 250개',
xl:['평상시','배포 시작','풀 소진','PENDING'],
steps:[
{o:50,old:110,nw:0,p:0,t:'구버전 Task 110개가 IP를 하나씩 쓰고, 인스턴스, RDS, ElastiCache, NAT 등 기타 리소스가 50개를 쓴다. 합계 160개라 250개 풀에 90개가 남아 있다.'},
{o:50,old:110,nw:40,p:0,t:'minimumHealthyPercent=100이라 구버전은 그대로 두고, maximumPercent=200 한도까지 신버전 Task를 추가로 띄운다. 신버전 40개가 올라오면 사용량은 200개가 된다.'},
{o:50,old:110,nw:90,p:0,t:'신버전이 90개째 뜨면 160 + 90 = 250개로 풀이 가득 찬다. 그런데 신버전은 20개를 더 띄워야 한다.'},
{o:50,old:110,nw:90,p:20,bad:true,t:'91번째 신버전 Task는 ENI에 줄 IP가 없다. Task가 PENDING에서 넘어가지 못하고 RESOURCE:ENI 에러가 CloudTrail에 찍힌다. 남은 신버전 20개가 대기 중이다.'}
]},
m22:{name:'/22',pool:1000,axis:1200,capLabel:'1,000',poolText:'약 1,000개',
xl:['평상시','배포 시작','신버전 90','피크'],
steps:[
{o:50,old:110,nw:0,p:0,t:'구버전 Task 110개와 기타 리소스 50개를 합쳐 160개를 쓴다. 약 1,000개 풀에 840개가 남아 있다.'},
{o:50,old:110,nw:40,p:0,t:'구버전을 유지한 채 maximumPercent=200 한도까지 신버전 Task를 추가한다. 신버전 40개가 올라와도 사용량은 200개로, 풀의 20%다.'},
{o:50,old:110,nw:90,p:0,t:'신버전이 90개 떠도 합계 250개로 풀의 4분의 1이다. 같은 시점에 /24 서브넷은 풀이 가득 찼다.'},
{o:50,old:110,nw:110,p:0,t:'신버전 110개가 모두 떠서 순간 최대 270개를 쓴다. 약 1,000개 풀 안에서 끝나므로 PENDING이나 RESOURCE:ENI 에러 없이 배포가 진행된다.'}
]}
};
var mode='m24',step=0,timer=null,prevStep=-1;
function el(tag,attrs,parent){var e=document.createElementNS(NS,tag);for(var k in attrs){e.setAttribute(k,attrs[k]);}if(parent){parent.appendChild(e);}return e;}
function clear(n){while(n.firstChild){n.removeChild(n.firstChild);}}
function build(){
var M=MODES[mode];
clear(barsG);clear(hlG);clear(xlG);
var capY=BASE-M.pool/M.axis*H;
capLine.setAttribute('y1',capY);capLine.setAttribute('y2',capY);
capT.setAttribute('y',capY+4);capT.textContent=M.capLabel;
for(var i=0;i!==M.steps.length;i++){
var s=M.steps[i];
var cx=X0+CW*i+CW/2;
var hl=el('rect',{'class':'ygd-hlr',x:X0+CW*i+2,y:6,width:CW-4,height:BASE-6+30,rx:6,'data-i':i,visibility:'hidden'},hlG);
var g=el('g',{'class':'ygd-colg','data-i':i},barsG);
var y=BASE;
var segs=[['ygd-seg-o',s.o],['ygd-seg-old',s.old],['ygd-seg-new',s.nw],['ygd-seg-p',s.p]];
for(var j=0;j!==segs.length;j++){
var v=segs[j][1];
if(v===0){continue;}
var h=v/M.axis*H;
y-=h;
el('rect',{'class':segs[j][0],x:cx-BW/2,y:y,width:BW,height:h},g);
}
if(s.p>0){
var t1=el('text',{'class':'ygd-err',x:414,y:y-10,'text-anchor':'end'},g);
t1.textContent='RESOURCE:ENI';
}else{
var t2=el('text',{x:cx,y:y-10,'text-anchor':'middle'},g);
t2.textContent=String(s.o+s.old+s.nw);
}
var xl=el('text',{'class':'ygd-mut',x:cx,y:240,'text-anchor':'middle'},xlG);
xl.textContent=M.xl[i];
}
}
function paint(animate){
var M=MODES[mode],s=M.steps[step];
var cols=barsG.childNodes,hls=hlG.childNodes;
for(var i=0;i!==cols.length;i++){
var c=cols[i];
c.setAttribute('class','ygd-colg'+(i===step?' ygd-now':(i<step?' ygd-past':'')));
hls[i].setAttribute('visibility',i===step?'visible':'hidden');
}
if(animate&&step!==prevStep){
var cur=cols[step];
void cur.getBoundingClientRect();
cur.setAttribute('class','ygd-colg ygd-now ygd-grow');
}
var tot=s.o+s.old+s.nw;
var txt=M.name+' 서브넷 · '+(step+1)+'/4단계 · 구버전 '+s.old+' + 신버전 '+s.nw+' + 기타 '+s.o+' = '+tot+' / 풀 '+M.poolText;
if(s.p>0){txt+=' · 대기 '+s.p;}
readout.textContent=txt;
panel.textContent=M.xl[step]+': '+s.t;
panel.className='ygd-panel'+(s.bad?' ygd-bad':'');
svg.setAttribute('aria-label',M.name+' 서브넷 롤링 배포 IP 사용량 막대 그래프. '+(step+1)+'단계, '+txt);
bPrev.disabled=step===0;
bNext.disabled=step===M.steps.length-1;
prevStep=step;
}
function stop(){
if(timer!==null){clearInterval(timer);timer=null;}
bPlay.textContent=step===MODES[mode].steps.length-1?'다시 재생':'재생';
}
function tick(){
if(step>=MODES[mode].steps.length-1){stop();return;}
step++;paint(true);
if(step>=MODES[mode].steps.length-1){stop();}
}
function play(){
if(step>=MODES[mode].steps.length-1){step=0;prevStep=-1;paint(true);}
bPlay.textContent='일시정지';
timer=setInterval(tick,2600);
}
function setMode(m){
mode=m;
b24.setAttribute('aria-pressed',m==='m24'?'true':'false');
b22.setAttribute('aria-pressed',m==='m22'?'true':'false');
build();prevStep=-1;paint(true);
if(timer===null){stop();}
}
bPlay.addEventListener('click',function(){if(timer!==null){stop();}else{play();}});
bPrev.addEventListener('click',function(){stop();if(step>0){step--;paint(true);}stop();});
bNext.addEventListener('click',function(){stop();if(step<MODES[mode].steps.length-1){step++;paint(true);}stop();});
b24.addEventListener('click',function(){setMode('m24');});
b22.addEventListener('click',function(){setMode('m22');});
build();paint(false);stop();
})();
</script>
</div>

## bridge 모드 — 동적 포트 매핑과 ALB 연동

### Docker bridge 네트워크

bridge 모드는 Docker의 기본 네트워크 드라이버를 쓴다. 컨테이너는 `docker0` 브리지 인터페이스를 통해 외부와 통신하고, 호스트의 ENI는 모든 컨테이너가 공유한다. 컨테이너의 포트를 외부로 노출하려면 `hostPort`를 지정해서 포트 매핑을 해야 한다.

### 정적 포트 매핑의 한계

Task Definition에 `hostPort: 8080`을 하드코딩하면, 같은 포트를 쓰는 Task는 **하나의 인스턴스에 하나만** 올라간다. Service의 desiredCount를 인스턴스 수보다 많게 올릴 수 없다.

```json
{
  "containerDefinitions": [
    {
      "name": "api",
      "portMappings": [
        { "containerPort": 8080, "hostPort": 8080, "protocol": "tcp" }
      ]
    }
  ],
  "networkMode": "bridge"
}
```

이 설정으로 t3.medium 10대 클러스터에 띄우면, Task는 최대 10개다. 11번째 Task는 `RESOURCE:PORTS` 에러로 PENDING 상태에 빠진다.

### 동적 포트 매핑

`hostPort`를 `0`으로 두면 Docker가 32768~60999 범위에서 랜덤 포트를 할당한다. 같은 인스턴스에 동일 서비스 Task를 여러 개 띄울 수 있고, ALB가 동적 포트를 자동으로 타깃 그룹에 등록한다.

```json
{
  "containerDefinitions": [
    {
      "name": "api",
      "portMappings": [
        { "containerPort": 8080, "hostPort": 0, "protocol": "tcp" }
      ]
    }
  ],
  "networkMode": "bridge"
}
```

이때 ALB Target Group은 `instance` 타입으로 설정한다. ECS Service가 Task를 띄울 때 `{인스턴스ID, 동적할당포트}` 쌍을 Target Group에 register 하고, 죽을 때 deregister 한다.

```mermaid
sequenceDiagram
    participant Client
    participant ALB
    participant TG as Target Group (instance)
    participant Agent as ECS Agent
    participant Docker

    Agent->>Docker: Task 시작 (hostPort=0)
    Docker-->>Agent: 포트 할당: 32768
    Agent->>TG: register (i-abc123, 32768)
    Client->>ALB: HTTP 요청
    ALB->>TG: 대상 조회
    TG-->>ALB: i-abc123:32768
    ALB->>Docker: 포워딩
    Docker-->>ALB: 응답
```

bridge 모드에서 동적 포트를 쓰면 ENI 제한이 없어서 Task 밀도를 높이기 쉽다. 다만 보안 그룹이 인스턴스 단위로 적용된다는 한계는 그대로다. 인스턴스 SG에서 `32768-60999`를 ALB SG에만 열어두는 식으로 우회한다.

### bridge 모드에서 자주 겪는 트러블

- **SG가 32768-60999를 안 열어뒀을 때**: ALB Health Check가 계속 `Connection timeout` 난다. 타깃이 unhealthy 상태로 깜빡거리며 Task가 계속 교체된다.
- **Task 재시작 시 포트가 바뀌는데 Health Check가 먼저 등록 해제를 못 따라가는 경우**: 드물지만 ECS Agent가 죽어있으면 deregister가 늦어지고, ALB가 죽은 포트로 계속 요청을 보낸다. Agent 모니터링 필수.
- **Docker 0.x 브리지를 거치는 네트워크 오버헤드**: awsvpc 대비 레이턴시가 수백 마이크로초 더 든다. 대부분은 무시 가능한 수준이지만, 지연에 민감한 서비스라면 host 모드를 고려한다.

## host 모드 — 호스트 네트워크 직통

### 동작 원리

host 모드는 컨테이너가 호스트의 네트워크 네임스페이스를 **그대로 공유**한다. 컨테이너 안에서 `curl http://localhost:8080`을 하면 호스트의 8080을 호출하는 것과 같다. 포트 매핑도 없고, 브리지도 없다.

가장 빠르다. 네트워크 스택을 한 번도 안 거치기 때문에 bridge 모드보다 레이턴시가 낮고, 처리량 한계도 호스트의 물리 한계에 가깝다.

### 포트 충돌 문제

host 모드에서 `containerPort: 80`을 쓰는 Task는 인스턴스 하나에 딱 하나만 올라간다. 동적 포트 같은 개념이 없다. 두 번째 Task는 포트 바인딩 에러로 기동 실패한다.

그래서 host 모드는 다음 경우에만 쓴다.

- **데몬셋 패턴**: 인스턴스마다 정확히 하나만 떠야 하는 Task. DaemonSet 스타일로 로그 수집기, 모니터링 에이전트, Service Mesh sidecar proxy 등.
- **네트워크 성능 극단 최적화**: 초저지연 게임 서버, 실시간 스트리밍, 고빈도 트레이딩 시스템.
- **대역폭이 전부인 워크로드**: 10Gbps 이상 처리하는 프록시나 파일 전송 서버.

Service의 `schedulingStrategy`를 `DAEMON`으로 설정하면 ECS가 인스턴스마다 Task를 하나씩만 배치하도록 강제한다. host 모드와 DAEMON 조합이 일반적이다.

### 보안 측면의 주의

host 모드는 컨테이너가 호스트 네트워크에 직접 노출된다. 컨테이너에서 열린 포트는 인스턴스의 포트이기도 하다. 실수로 디버그 포트(5005 같은)를 열어두면 보안 그룹만이 최종 방어선이 된다. 프로덕션에서는 호스트 포트 범위를 최소화하고, 인스턴스 SG를 타이트하게 유지해야 한다.

## none 모드

컨테이너에 외부 네트워크를 붙이지 않는다. `lo` 인터페이스만 있다. 외부 API 호출도 안 되고 다른 Task와도 통신할 수 없다.

쓰는 경우는 한정적이다. 순수 연산만 하는 배치 작업, S3나 EFS만 건드리는 데이터 처리 Job 정도. 실무에서는 거의 볼 일이 없지만, 보안 격리가 극단적으로 필요한 워크로드에서는 고려할 만하다.

주의할 점은 `none` 모드라도 **IAM Task Role은 동작한다**. Task Role은 메타데이터 엔드포인트를 통해 credentials를 받는데, 이 엔드포인트는 로컬 링크다. 다만 실제로 S3 같은 API를 호출하려면 VPC Endpoint가 EC2 호스트에 연결되어 있어야 하고, 이건 Task가 아니라 호스트 ENI가 담당한다.

## Service Connect와 Cloud Map 서비스 디스커버리

### 문제: Task IP는 휘발성이다

ECS Task가 재시작되면 IP가 바뀐다. 서비스 간 호출에서 IP를 하드코딩하거나 매번 API로 조회하는 건 현실적이지 않다. 해결책은 두 가지다.

1. **ALB/NLB 경유** — 비용이 들고 내부 트래픽에도 로드밸런서 홉이 추가된다.
2. **Service Discovery** — Cloud Map 또는 Service Connect로 이름 기반 호출.

### AWS Cloud Map + Service Discovery

전통적인 방식이다. ECS Service가 Cloud Map에 자신의 Task들을 등록하고, DNS(Route 53 Private Hosted Zone) 또는 API로 조회한다.

```json
{
  "serviceRegistries": [
    {
      "registryArn": "arn:aws:servicediscovery:ap-northeast-2:...:service/srv-xxx",
      "containerName": "api",
      "containerPort": 8080
    }
  ]
}
```

DNS로 `api.internal` 같은 이름을 만들고, Task가 뜨면 A 레코드로 IP가 등록된다. 다른 Task에서 `curl http://api.internal:8080`으로 호출한다.

DNS 기반이라 **TTL 문제**가 있다. 기본 TTL 60초인데, Task가 죽고 새로 뜨는 사이에 클라이언트가 옛 IP를 캐싱하면 1분 동안 실패 요청이 간다. 클라이언트에서 DNS 캐시 TTL을 줄이거나, 애플리케이션 레벨에서 재시도를 넣어야 한다.

awsvpc 모드에서만 깔끔하게 동작한다. bridge 모드는 호스트 IP와 포트를 조합해야 해서 SRV 레코드를 써야 하는데, 대부분의 HTTP 클라이언트가 SRV를 지원하지 않는다.

### Service Connect

2022년에 나온 신형 방식이다. Cloud Map을 내부적으로 사용하지만, Task 사이드카로 **Envoy proxy**가 자동으로 주입되어 L7 로드밸런싱, 재시도, 타임아웃, 메트릭을 처리한다.

```mermaid
graph LR
    subgraph TaskA[Task A]
        AppA[App]
        EnvoyA[Envoy]
        AppA --> EnvoyA
    end
    subgraph TaskB[Task B]
        EnvoyB[Envoy]
        AppB[App]
        EnvoyB --> AppB
    end
    EnvoyA -->|mTLS 가능| EnvoyB
    EnvoyA -.->|메트릭| CW[CloudWatch]
    EnvoyB -.->|메트릭| CW
```

클라이언트는 `http://api:8080`처럼 단순 이름으로 호출하고, 같은 Task 안의 Envoy가 대상 Task로 부하를 분산한다. DNS TTL 문제가 사라지고, 배포 중에도 끊김 없이 트래픽이 흐른다.

```json
{
  "serviceConnectConfiguration": {
    "enabled": true,
    "namespace": "prod.local",
    "services": [
      {
        "portName": "api",
        "discoveryName": "api",
        "clientAliases": [
          { "port": 8080, "dnsName": "api" }
        ]
      }
    ]
  }
}
```

Cloud Map과 비교했을 때 Service Connect의 장점은 세 가지다.

- **L7 로드밸런싱**: DNS 기반 round-robin이 아니라 Envoy가 최소 연결 기반으로 분산.
- **메트릭 자동 수집**: Envoy가 RequestCount, HTTPCode, TargetResponseTime을 CloudWatch로 내보낸다.
- **Graceful 연결 종료**: Task 종료 시 Envoy가 in-flight 요청을 끝까지 처리하고 나간다.

단점은 Envoy 사이드카의 **리소스 오버헤드**다. Task당 CPU ~128, Memory ~64MB 정도 추가로 쓴다. 수백 개 Task를 돌리면 꽤 쌓인다.

<div class="ygd-cloudmap-dns-vs-service-connect" id="ygd-cloudmap-dns-vs-service-connect">
<style>
.ygd-cloudmap-dns-vs-service-connect{--ygd-bg:#fdfbfa;--ygd-fg:#2b2927;--ygd-muted:#5f5a54;--ygd-surface:#f4f1ed;--ygd-line:#8a847c;--ygd-border:#d9d4cd;--ygd-accent:#2f6b80;--ygd-onaccent:#ffffff;--ygd-ok:#1f7a45;--ygd-fail:#c0332b;--ygd-warn:#8f5b00;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:14px;border:1px solid var(--ygd-border);border-radius:12px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:15px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-cloudmap-dns-vs-service-connect{--ygd-bg:#1f1c1e;--ygd-fg:#ece8e3;--ygd-muted:#b3ada5;--ygd-surface:#2a2729;--ygd-line:#8f8982;--ygd-border:#4a4548;--ygd-accent:#7fc0d6;--ygd-onaccent:#11262e;--ygd-ok:#5fcf8a;--ygd-fail:#ff8a80;--ygd-warn:#f0b957}
.ygd-cloudmap-dns-vs-service-connect .ygd-modes{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.ygd-cloudmap-dns-vs-service-connect .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.ygd-cloudmap-dns-vs-service-connect .ygd-steps{display:flex;gap:6px;align-items:center;margin-left:auto}
.ygd-cloudmap-dns-vs-service-connect .ygd-btn{font:inherit;font-size:14px;line-height:1.3;min-height:36px;padding:4px 12px;border:1px solid var(--ygd-border);border-radius:8px;background:var(--ygd-surface);color:var(--ygd-fg);cursor:pointer}
.ygd-cloudmap-dns-vs-service-connect .ygd-btn:hover{border-color:var(--ygd-accent)}
.ygd-cloudmap-dns-vs-service-connect .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-cloudmap-dns-vs-service-connect .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-cloudmap-dns-vs-service-connect .ygd-mode{flex:1 1 140px}
.ygd-cloudmap-dns-vs-service-connect .ygd-btn[aria-pressed="true"]{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-onaccent);font-weight:700}
.ygd-cloudmap-dns-vs-service-connect .ygd-sdot{width:34px;min-height:34px;padding:0;border-radius:50%}
.ygd-cloudmap-dns-vs-service-connect .ygd-svg{display:block;width:100%;max-width:560px;height:auto;margin:0 auto;font-family:inherit}
.ygd-cloudmap-dns-vs-service-connect .ygd-t{fill:var(--ygd-fg);font-size:12px;font-family:inherit}
.ygd-cloudmap-dns-vs-service-connect .ygd-tb{font-weight:700}
.ygd-cloudmap-dns-vs-service-connect .ygd-tm{fill:var(--ygd-muted)}
.ygd-cloudmap-dns-vs-service-connect .ygd-tacc{fill:var(--ygd-accent)}
.ygd-cloudmap-dns-vs-service-connect .ygd-l-ok{fill:var(--ygd-ok)}
.ygd-cloudmap-dns-vs-service-connect .ygd-l-fail{fill:var(--ygd-fail)}
.ygd-cloudmap-dns-vs-service-connect .ygd-box{fill:var(--ygd-surface);stroke:var(--ygd-line);stroke-width:1.2;transition:stroke .3s}
.ygd-cloudmap-dns-vs-service-connect .ygd-zone{fill:none;stroke:var(--ygd-border);stroke-width:1.2}
.ygd-cloudmap-dns-vs-service-connect .ygd-stale{stroke:var(--ygd-warn);stroke-width:2}
.ygd-cloudmap-dns-vs-service-connect .ygd-task{transition:opacity .3s}
.ygd-cloudmap-dns-vs-service-connect .ygd-s-alive .ygd-box{stroke:var(--ygd-ok);stroke-width:2}
.ygd-cloudmap-dns-vs-service-connect .ygd-s-drain .ygd-box{stroke:var(--ygd-warn);stroke-width:2}
.ygd-cloudmap-dns-vs-service-connect .ygd-s-dead{opacity:.55}
.ygd-cloudmap-dns-vs-service-connect .ygd-s-dead .ygd-box{stroke:var(--ygd-fail);stroke-dasharray:5 4}
.ygd-cloudmap-dns-vs-service-connect .ygd-s-off{opacity:.5}
.ygd-cloudmap-dns-vs-service-connect .ygd-s-off .ygd-box{stroke-dasharray:3 4}
.ygd-cloudmap-dns-vs-service-connect .ygd-arrow{fill:none;transition:stroke .3s}
.ygd-cloudmap-dns-vs-service-connect .ygd-a-ok{stroke:var(--ygd-ok);stroke-width:2.4;marker-end:url(#ygd-cmsc-ah-ok)}
.ygd-cloudmap-dns-vs-service-connect .ygd-a-fail{stroke:var(--ygd-fail);stroke-width:2.4;stroke-dasharray:6 4;marker-end:url(#ygd-cmsc-ah-fail)}
.ygd-cloudmap-dns-vs-service-connect .ygd-a-idle{stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:2 5;opacity:.5;marker-end:url(#ygd-cmsc-ah-idle)}
.ygd-cloudmap-dns-vs-service-connect .ygd-mk-ok{fill:var(--ygd-ok)}
.ygd-cloudmap-dns-vs-service-connect .ygd-mk-fail{fill:var(--ygd-fail)}
.ygd-cloudmap-dns-vs-service-connect .ygd-mk-idle{fill:var(--ygd-line)}
.ygd-cloudmap-dns-vs-service-connect .ygd-link{fill:none;transition:stroke .3s}
.ygd-cloudmap-dns-vs-service-connect .ygd-link-on{stroke:var(--ygd-accent);stroke-width:2.2}
.ygd-cloudmap-dns-vs-service-connect .ygd-link-off{stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:2 5;opacity:.55}
.ygd-cloudmap-dns-vs-service-connect .ygd-dot{stroke:var(--ygd-bg);stroke-width:1.5}
.ygd-cloudmap-dns-vs-service-connect .ygd-d-ok{fill:var(--ygd-ok)}
.ygd-cloudmap-dns-vs-service-connect .ygd-d-fail{fill:var(--ygd-fail)}
.ygd-cloudmap-dns-vs-service-connect .ygd-panel{margin-top:10px;padding:10px 12px;border:1px solid var(--ygd-border);border-left:4px solid var(--ygd-accent);border-radius:8px;background:var(--ygd-surface);font-size:15px}
.ygd-cloudmap-dns-vs-service-connect .ygd-ptitle{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:4px;font-weight:700}
.ygd-cloudmap-dns-vs-service-connect .ygd-badge{padding:0 10px;border:1px solid currentColor;border-radius:999px;font-size:14px;font-weight:700}
.ygd-cloudmap-dns-vs-service-connect .ygd-b-ok{color:var(--ygd-ok)}
.ygd-cloudmap-dns-vs-service-connect .ygd-b-fail{color:var(--ygd-fail)}
.ygd-cloudmap-dns-vs-service-connect .ygd-b-warn{color:var(--ygd-warn)}
.ygd-cloudmap-dns-vs-service-connect .ygd-ptext{margin:0}
.ygd-cloudmap-dns-vs-service-connect .ygd-note{margin-top:10px;font-size:14px;line-height:1.6;color:var(--ygd-muted)}
@media (prefers-reduced-motion: reduce){.ygd-cloudmap-dns-vs-service-connect *{transition:none !important;animation:none !important}}
</style>
<div class="ygd-modes" role="group" aria-label="서비스 디스커버리 방식 선택">
<button type="button" class="ygd-btn ygd-mode" data-ygd-mode="dns" aria-pressed="true">Cloud Map DNS</button>
<button type="button" class="ygd-btn ygd-mode" data-ygd-mode="sc" aria-pressed="false">Service Connect</button>
</div>
<svg class="ygd-svg" data-ygd="svg" viewBox="0 0 400 352" role="img" aria-label="Task 교체 시나리오 다이어그램">
<defs>
<marker id="ygd-cmsc-ah-ok" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-ok" d="M0 0 L10 5 L0 10 z"/></marker>
<marker id="ygd-cmsc-ah-fail" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-fail" d="M0 0 L10 5 L0 10 z"/></marker>
<marker id="ygd-cmsc-ah-idle" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-idle" d="M0 0 L10 5 L0 10 z"/></marker>
</defs>
<rect class="ygd-box" x="100" y="8" width="200" height="40" rx="8"/>
<text class="ygd-t ygd-tb" x="200" y="23" text-anchor="middle">Cloud Map 레지스트리</text>
<text class="ygd-t ygd-tm" data-ygd="reg" x="200" y="40" text-anchor="middle"></text>
<path class="ygd-link ygd-link-off" data-ygd="link" d="M200 48 L200 84"/>
<text class="ygd-t ygd-tm" data-ygd="linklbl" x="212" y="70"></text>
<rect class="ygd-zone" x="10" y="84" width="380" height="96" rx="10"/>
<text class="ygd-t ygd-tm ygd-tb" x="22" y="102">클라이언트 Task</text>
<rect class="ygd-box" x="22" y="112" width="128" height="54" rx="8"/>
<text class="ygd-t ygd-tb" x="34" y="132">App</text>
<text class="ygd-t ygd-tm" data-ygd="app2" x="34" y="150"></text>
<path class="ygd-arrow ygd-a-idle" d="M150 139 L170 139" style="opacity:1;stroke-dasharray:none;stroke:var(--ygd-line)"/>
<rect class="ygd-box" data-ygd="slotbox" x="172" y="112" width="206" height="54" rx="8"/>
<text class="ygd-t ygd-tb" data-ygd="slot1" x="184" y="132"></text>
<text class="ygd-t ygd-tm" data-ygd="slot2" x="184" y="150"></text>
<path class="ygd-arrow ygd-a-idle" data-ygd="a1" d="M268 166 L102 246"/>
<path class="ygd-arrow ygd-a-idle" data-ygd="a2" d="M268 166 L298 246"/>
<text class="ygd-t ygd-tb" data-ygd="l1" x="156" y="210" text-anchor="end"></text>
<text class="ygd-t ygd-tb" data-ygd="l2" x="300" y="210"></text>
<circle class="ygd-dot ygd-d-ok" data-ygd="d1" r="5" cx="268" cy="166" opacity="0"/>
<circle class="ygd-dot ygd-d-ok" data-ygd="d2" r="5" cx="268" cy="166" opacity="0"/>
<g class="ygd-task ygd-s-alive" data-ygd="t1">
<rect class="ygd-box" x="10" y="250" width="180" height="96" rx="10"/>
<text class="ygd-t ygd-tb" x="22" y="272">Task B-1 (기존)</text>
<text class="ygd-t ygd-tm" x="22" y="291">10.0.1.5</text>
<text class="ygd-t ygd-tb" data-ygd="t1s1" x="22" y="314"></text>
<text class="ygd-t ygd-tm" data-ygd="t1s2" x="22" y="332"></text>
</g>
<g class="ygd-task ygd-s-off" data-ygd="t2">
<rect class="ygd-box" x="210" y="250" width="180" height="96" rx="10"/>
<text class="ygd-t ygd-tb" x="222" y="272">Task B-2 (신규)</text>
<text class="ygd-t ygd-tm" x="222" y="291">10.0.1.9</text>
<text class="ygd-t ygd-tb" data-ygd="t2s1" x="222" y="314"></text>
<text class="ygd-t ygd-tm" data-ygd="t2s2" x="222" y="332"></text>
</g>
</svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn" data-ygd="play">재생</button>
<button type="button" class="ygd-btn" data-ygd="next">다음 단계</button>
<button type="button" class="ygd-btn" data-ygd="reset">처음으로</button>
<div class="ygd-steps" data-ygd="steps" role="group" aria-label="단계 선택"></div>
</div>
<div class="ygd-panel" aria-live="polite">
<div class="ygd-ptitle"><span data-ygd="ptitle"></span><span class="ygd-badge" data-ygd="badge"></span></div>
<div class="ygd-ptext" data-ygd="ptext"></div>
</div>
<div class="ygd-note">비유: DNS 캐시는 전화번호를 적어 둔 수첩과 같아서, 번호가 바뀌어도 TTL이 지나야 다시 확인한다. Service Connect의 Envoy는 최신 명단을 보고 연결해 주는 안내 데스크에 가깝다. 비유일 뿐 실제 Envoy는 L7 프록시이며, 화면의 IP는 설명용 예시다.</div>
<script>
(function(){
var root=document.getElementById('ygd-cloudmap-dns-vs-service-connect');
if(!root)return;
function q(n){return root.querySelector('[data-ygd="'+n+'"]');}
var NAMES={dns:'Cloud Map DNS',sc:'Service Connect'};
var D={
dns:[
{t:'평상시',k:'ok',kb:'정상',x:'클라이언트가 api.internal 을 조회해 A 레코드의 IP(10.0.1.5)를 받고 DNS 캐시에 저장한다. 요청은 Task B-1로 정상 전달된다.',reg:'api.internal → 10.0.1.5',link:[1,'최초 조회 → 캐시 저장'],slot1:'DNS 캐시 (TTL 60초)',slot2:'api.internal → 10.0.1.5',stale:0,t1:['alive','실행 중','요청 처리 가능'],t2:['off','아직 없음',''],a1:['ok','성공 ✓'],a2:[0,'']},
{t:'B-1 종료, 캐시는 옛 IP',k:'fail',kb:'여기서 실패',x:'Task B-1이 종료되어 레코드가 사라진다. 그래도 클라이언트는 TTL(기본 60초)이 지나기 전이라 재조회하지 않고 옛 IP로 요청을 보내고, 그 요청은 실패한다.',reg:'등록된 레코드 없음',link:[0,'조회 없음 · 캐시 사용'],slot1:'DNS 캐시 · 옛 IP 보관 중',slot2:'api.internal → 10.0.1.5',stale:1,t1:['dead','종료됨','A 레코드 제거'],t2:['off','아직 없음',''],a1:['fail','실패 ✕'],a2:[0,'']},
{t:'B-2 시작, 그래도 옛 IP',k:'fail',kb:'실패 지속',x:'새 Task B-2가 떠서 새 IP(10.0.1.9)로 등록된다. 하지만 클라이언트 캐시는 아직 만료 전이라 옛 IP를 계속 쓰고, TTL이 지날 때까지 실패가 이어진다.',reg:'api.internal → 10.0.1.9',link:[0,'조회 없음 · 캐시 사용'],slot1:'DNS 캐시 · 옛 IP 보관 중',slot2:'api.internal → 10.0.1.5',stale:1,t1:['dead','종료됨','A 레코드 제거'],t2:['alive','시작됨','A 레코드 등록'],a1:['fail','실패 ✕'],a2:[0,'']},
{t:'TTL 만료, 재조회',k:'ok',kb:'복구',x:'TTL이 만료되면 클라이언트가 다시 조회해 새 IP를 받고, 요청이 B-2로 성공한다. 이 공백을 줄이려면 클라이언트의 DNS 캐시 TTL을 줄이거나 애플리케이션에서 재시도를 넣어야 한다.',reg:'api.internal → 10.0.1.9',link:[1,'TTL 만료 → 재조회'],slot1:'DNS 캐시 (재조회됨)',slot2:'api.internal → 10.0.1.9',stale:0,t1:['dead','종료됨','A 레코드 제거'],t2:['alive','실행 중','요청 처리 가능'],a1:[0,''],a2:['ok','성공 ✓']}
],
sc:[
{t:'평상시',k:'ok',kb:'정상',x:'앱은 http://api:8080 처럼 이름만 호출한다. 같은 Task 안의 Envoy가 대상 Task로 요청을 분산한다.',reg:'등록: 10.0.1.5',link:[1,'대상 목록 수신'],slot1:'Envoy 사이드카',slot2:'대상: 10.0.1.5',stale:0,t1:['alive','실행 중','요청 처리 가능'],t2:['off','아직 없음',''],a1:['ok','성공 ✓'],a2:[0,'']},
{t:'B-2 등록, 목록 갱신',k:'ok',kb:'정상',x:'새 Task B-2가 등록되면 같은 Task 안의 Envoy가 대상 목록을 갱신한다. DNS 캐시 TTL을 기다리지 않으므로 B-2도 곧바로 분산 대상이 된다.',reg:'등록: 10.0.1.5, 10.0.1.9',link:[1,'대상 목록 갱신'],slot1:'Envoy 사이드카',slot2:'대상: 10.0.1.5, 10.0.1.9',stale:0,t1:['alive','실행 중','요청 처리 가능'],t2:['alive','시작됨','등록 완료'],a1:['ok','성공 ✓'],a2:['ok','성공 ✓']},
{t:'B-1 종료 시작, 요청 마무리',k:'warn',kb:'안전하게 전환',x:'B-1이 종료되기 시작하면 대상 목록에서 빠진다. Envoy는 in-flight 요청을 끝까지 처리하고, 새 요청은 B-2로 보낸다.',reg:'등록: 10.0.1.9',link:[1,'목록에서 B-1 제외'],slot1:'Envoy 사이드카',slot2:'대상: 10.0.1.9',stale:0,t1:['drain','종료 중','in-flight 마무리 중'],t2:['alive','실행 중','요청 처리 가능'],a1:['ok','in-flight 마무리'],a2:['ok','신규 요청 ✓']},
{t:'전환 완료',k:'ok',kb:'실패 없음',x:'B-1이 완전히 종료되어도 목록에는 B-2만 남아 있어 요청이 계속 성공한다. 이 시나리오에서는 클라이언트가 실패 요청을 받는 구간이 없다.',reg:'등록: 10.0.1.9',link:[0,'목록 변화 없음'],slot1:'Envoy 사이드카',slot2:'대상: 10.0.1.9',stale:0,t1:['dead','종료됨','목록에서 이미 제외'],t2:['alive','실행 중','요청 처리 가능'],a1:[0,''],a2:['ok','성공 ✓']}
]
};
var mode='dns',step=0,timer=null,raf=0,vis=true;
var LAST=3;
var mq=window.matchMedia?window.matchMedia('(prefers-reduced-motion: reduce)'):null;
function reduced(){return !!(mq&&mq.matches);}
var svg=q('svg'),reg=q('reg'),link=q('link'),linklbl=q('linklbl'),app2=q('app2');
var slot1=q('slot1'),slot2=q('slot2'),slotbox=q('slotbox');
var tg=[q('t1'),q('t2')];
var ts1=[q('t1s1'),q('t2s1')],ts2=[q('t1s2'),q('t2s2')];
var arrows=[q('a1'),q('a2')],lbls=[q('l1'),q('l2')],dots=[q('d1'),q('d2')];
var ptitle=q('ptitle'),badge=q('badge'),ptext=q('ptext');
var playBtn=q('play'),nextBtn=q('next'),resetBtn=q('reset'),stepsBox=q('steps');
var P=[{x0:268,y0:166,x1:102,y1:246},{x0:268,y0:166,x1:298,y1:246}];
var cur=[null,null];
var stepBtns=[];
for(var i=0;i<=LAST;i++){
var b=document.createElement('button');
b.type='button';
b.className='ygd-btn ygd-sdot';
b.textContent=String(i+1);
b.setAttribute('aria-label',(i+1)+'단계로 이동');
(function(n){b.addEventListener('click',function(){stop();step=n;render();});})(i);
stepsBox.appendChild(b);
stepBtns.push(b);
}
function render(){
var s=D[mode][step];
reg.textContent=s.reg;
app2.textContent=mode==='dns'?'api.internal:8080':'api:8080';
link.setAttribute('class','ygd-link '+(s.link[0]?'ygd-link-on':'ygd-link-off'));
linklbl.textContent=s.link[1];
linklbl.setAttribute('class','ygd-t '+(s.link[0]?'ygd-tb ygd-tacc':'ygd-tm'));
slot1.textContent=s.slot1;
slot2.textContent=s.slot2;
slotbox.setAttribute('class','ygd-box'+(s.stale?' ygd-stale':''));
var ts=[s.t1,s.t2];
for(var i=0;i<2;i++){
tg[i].setAttribute('class','ygd-task ygd-s-'+ts[i][0]);
ts1[i].textContent=ts[i][1];
ts2[i].textContent=ts[i][2];
var a=i===0?s.a1:s.a2;
cur[i]=a[0]||null;
arrows[i].setAttribute('class','ygd-arrow '+(a[0]==='ok'?'ygd-a-ok':a[0]==='fail'?'ygd-a-fail':'ygd-a-idle'));
lbls[i].textContent=a[1];
lbls[i].setAttribute('class','ygd-t ygd-tb '+(a[0]==='fail'?'ygd-l-fail':'ygd-l-ok'));
dots[i].setAttribute('class','ygd-dot '+(a[0]==='fail'?'ygd-d-fail':'ygd-d-ok'));
if(reduced()||!a[0]){dots[i].setAttribute('opacity','0');}
}
ptitle.textContent=NAMES[mode]+' · 단계 '+(step+1)+'/'+(LAST+1)+' · '+s.t;
badge.textContent=s.kb;
badge.setAttribute('class','ygd-badge ygd-b-'+s.k);
ptext.textContent=s.x;
svg.setAttribute('aria-label','Task 교체 시나리오, '+NAMES[mode]+' 방식. 단계 '+(step+1)+': '+s.t+'. '+s.x);
for(var j=0;j<stepBtns.length;j++){
stepBtns[j].setAttribute('aria-pressed',j===step?'true':'false');
if(j===step){stepBtns[j].setAttribute('aria-current','step');}else{stepBtns[j].removeAttribute('aria-current');}
}
nextBtn.disabled=step>=LAST;
loop();
}
function tick(now){
raf=0;
if(!vis||document.hidden||reduced()){return;}
var p=(now%1600)/1600;
for(var i=0;i<2;i++){
if(cur[i]){
dots[i].setAttribute('cx',String(P[i].x0+(P[i].x1-P[i].x0)*p));
dots[i].setAttribute('cy',String(P[i].y0+(P[i].y1-P[i].y0)*p));
dots[i].setAttribute('opacity','1');
}
}
raf=requestAnimationFrame(tick);
}
function loop(){
if(raf||reduced()||!vis||document.hidden){return;}
if(cur[0]||cur[1]){raf=requestAnimationFrame(tick);}
}
function stop(){
if(timer){clearInterval(timer);timer=null;}
playBtn.textContent='재생';
}
function play(){
if(step>=LAST){step=0;render();}
playBtn.textContent='일시정지';
timer=setInterval(function(){
if(step<LAST){step++;render();}
if(step>=LAST){stop();}
},3400);
}
playBtn.addEventListener('click',function(){if(timer){stop();}else{play();}});
nextBtn.addEventListener('click',function(){stop();if(step<LAST){step++;render();}});
resetBtn.addEventListener('click',function(){stop();step=0;render();});
var mbs=root.querySelectorAll('[data-ygd-mode]');
for(var m=0;m<mbs.length;m++){
mbs[m].addEventListener('click',function(){
mode=this.getAttribute('data-ygd-mode');
for(var k=0;k<mbs.length;k++){
mbs[k].setAttribute('aria-pressed',mbs[k]===this?'true':'false');
}
stop();
step=0;
render();
});
}
if('IntersectionObserver' in window){
new IntersectionObserver(function(es){vis=es[0].isIntersecting;if(vis){loop();}}).observe(root);
}
document.addEventListener('visibilitychange',function(){if(!document.hidden){loop();}});
render();
})();
</script>
</div>

## Fargate가 awsvpc만 지원하는 이유

Fargate는 사용자가 관리하는 EC2 인스턴스가 없다. AWS가 내부적으로 공유 호스트(Firecracker microVM 또는 전용 호스트)에서 Task를 돌리는데, 여러 고객의 Task가 같은 물리 호스트에 섞여 있을 수 있다.

bridge/host 모드는 **호스트 네트워크를 공유**하는 모델이다. 같은 호스트에 여러 고객의 Task가 있으면 네트워크 격리가 깨진다. 호스트 ENI의 SG를 공유한다는 건 고객 A의 Task가 고객 B의 트래픽에 SG 정책을 걸 수 있다는 뜻이기도 하다. 멀티테넌트 환경에서는 불가능한 모델이다.

awsvpc는 Task마다 전용 ENI를 할당하기 때문에 네트워크 레벨에서 완전히 격리된다. Fargate가 이 모드만 지원하는 이유다.

그 외에도 Fargate는 다음과 같은 awsvpc 특성에 의존한다.

- **Task별 독립 IP**가 있어야 VPC 라우팅 테이블이 격리 가능.
- **Task별 SG**가 있어야 멀티테넌트에서 안전.
- **ENI hot-attach**가 VPC 수준에서 과금/관리 추적 가능.

Fargate에서 `networkMode: bridge`로 Task Definition을 등록하려고 하면 API 자체가 에러를 뱉는다.

## VPC Endpoint로 NAT 비용 줄이기

### 문제: NAT Gateway 데이터 처리 비용

프라이빗 서브넷에서 awsvpc Task가 ECR에서 이미지를 받거나 CloudWatch로 로그를 보낼 때, 기본 경로는 NAT Gateway를 거쳐 AWS 퍼블릭 엔드포인트로 나간다. NAT Gateway는 **처리 데이터 GB당 $0.045** (서울 리전 기준)가 붙는다.

대규모 서비스에서 이게 꽤 크다. ECR 이미지가 500MB이고 Task가 하루에 1,000번 pull 된다면 그것만으로 500GB × $0.045 = $22.5/day, 월 $675가 나간다. CloudWatch Logs 트래픽까지 합치면 수천 달러 규모가 금방 된다.

### VPC Endpoint 구성

VPC Endpoint를 만들면 VPC 내부에서 AWS 서비스로 **프라이빗 경로**가 열린다. NAT Gateway를 안 거치므로 데이터 처리 요금이 없어진다.

ECS awsvpc Task에 필요한 최소 Endpoint 목록.

```
com.amazonaws.ap-northeast-2.ecr.api         (Interface)
com.amazonaws.ap-northeast-2.ecr.dkr         (Interface)
com.amazonaws.ap-northeast-2.s3              (Gateway, ECR 레이어 저장소)
com.amazonaws.ap-northeast-2.logs            (Interface, CloudWatch Logs)
com.amazonaws.ap-northeast-2.secretsmanager  (Interface, Secrets Manager 사용 시)
com.amazonaws.ap-northeast-2.ssm             (Interface, SSM Parameter Store 사용 시)
com.amazonaws.ap-northeast-2.ecs-agent       (Interface, ECS Agent 통신)
com.amazonaws.ap-northeast-2.ecs-telemetry   (Interface, ECS 메트릭)
com.amazonaws.ap-northeast-2.ecs             (Interface, ECS API)
```

S3는 Gateway Endpoint고 나머지는 Interface Endpoint다. Interface Endpoint는 서브넷마다 ENI를 만들고 **시간당 $0.01 × ENI 수**와 **처리 데이터 GB당 $0.01**이 붙는다. AZ 3개에 9개 Endpoint면 27개 ENI × $0.01 × 730시간 = 월 $197 정도가 고정비로 나간다.

손익 분기점은 NAT을 거쳐 나가는 데이터가 월 ~2TB 이상일 때다. 소규모 서비스는 NAT만 쓰는 게 이득이고, 프로덕션 규모에서는 VPC Endpoint가 압도적으로 싸다.

### Endpoint 적용 후 주의사항

- **Security Group**: Interface Endpoint의 ENI에 붙는 SG를 만들어서, VPC CIDR에서 443 인바운드만 열어야 한다.
- **DNS 설정**: Interface Endpoint의 Private DNS를 활성화해야 SDK가 퍼블릭 URL을 알아서 프라이빗 IP로 풀어준다. 안 켜면 여전히 NAT으로 나간다.
- **S3 Gateway Endpoint 라우팅**: 프라이빗 서브넷의 라우팅 테이블에 Endpoint를 추가해야 한다. 추가 안 하면 S3 트래픽이 그대로 NAT으로 간다.
- **ECS Fargate PV 1.4.0 이상 필수**: 이전 버전은 일부 Endpoint를 인식 못 해서 NAT을 탄다. 플랫폼 버전을 `LATEST`로 두는 것보다 `1.4.0` 명시가 안전하다.

```mermaid
flowchart LR
    subgraph Private[프라이빗 서브넷]
        Task[ECS Task]
    end

    subgraph Endpoints[VPC Endpoints]
        E1[ecr.api]
        E2[ecr.dkr]
        E3[logs]
        E4[s3 Gateway]
    end

    subgraph Public[퍼블릭 서브넷]
        NAT[NAT Gateway]
    end

    Task -->|ECR 이미지 Pull| E1
    Task -->|ECR 레이어 Pull| E2
    Task -->|로그 전송| E3
    Task -->|S3 접근| E4
    Task -.->|외부 인터넷| NAT

    style E1 fill:#e6f3ff,stroke:#336699
    style E2 fill:#e6f3ff,stroke:#336699
    style E3 fill:#e6f3ff,stroke:#336699
    style E4 fill:#e6f3ff,stroke:#336699
```

AWS 내부 서비스는 Endpoint로, 외부 API 호출(예: Slack webhook, 외부 결제 API)만 NAT으로 보내는 구조로 분리한다.

## 네트워크 모드 종합 비교

| 항목 | awsvpc | bridge | host | none |
|------|--------|--------|------|------|
| Task당 IP | 전용 (ENI 1개) | 공유 (호스트 ENI) | 공유 (호스트) | 없음 |
| Task별 SG | 가능 | 인스턴스 공유 | 인스턴스 공유 | 무의미 |
| ALB Target Type | IP | instance | instance | 불가 |
| Task 시작 속도 | 느림 (ENI 할당 10~30초) | 빠름 | 빠름 | 빠름 |
| Task 밀도 | ENI 제한에 묶임 | 높음 | 포트 수 만큼 | 이론상 무제한 |
| 네트워크 레이턴시 | 보통 | 오버헤드 소폭 | 최저 | 외부 통신 불가 |
| Fargate 지원 | 지원 | 미지원 | 미지원 | 미지원 |
| Service Connect | 지원 | 제한적 | 제한적 | 미지원 |
| Cloud Map DNS | 완전 지원 | SRV 레코드 필요 | SRV 레코드 필요 | 미지원 |
| VPC Flow Logs 구분 | Task 단위 | 인스턴스 단위 | 인스턴스 단위 | 해당 없음 |
| 주 용도 | 프로덕션 기본값 | EC2 밀도 중요한 내부 서비스 | 데몬셋, 초저지연 | 격리된 배치 작업 |

## 실무 선택 기준

awsvpc를 기본값으로 두고, 특별한 이유가 있을 때만 다른 모드를 고려한다는 원칙이 지금 AWS 권장 방향이다. 실제로 부딪히는 케이스를 정리하면 이렇다.

**Fargate를 쓰려는 순간**: 고민 끝. awsvpc 외에는 선택지가 없다.

**EC2 Launch Type + 고밀도 서비스**: bridge 모드 + 동적 포트 매핑이 여전히 의미 있다. 예를 들어 마이크로서비스 20개를 m5.large 5대에 압축해서 돌리고 싶을 때, awsvpc는 ENI 제한(대당 9개)으로 45개까지 한정되는데 bridge는 수백 개까지 가능하다. 대신 Task별 SG를 포기해야 한다.

**초저지연 요구 워크로드**: host 모드 + DAEMON 스케줄링. 게임 서버, 실시간 스트리밍 쪽에서 쓴다. 그러나 요즘은 Fargate의 awsvpc 성능이 대부분의 레이턴시 요구를 커버하므로, host 모드까지 갈 일이 점점 줄어든다.

**레거시에서 마이그레이션 중**: bridge → awsvpc 전환은 Target Group 타입(instance → ip) 변경과 SG 재설계가 함께 따라붙는다. 한 번에 바꾸면 트래픽이 끊긴다. 새 Service를 awsvpc로 띄우고 가중치 라우팅으로 점진 전환하는 패턴을 쓴다.

Service Connect는 awsvpc 모드와 조합했을 때 가장 효과가 크다. bridge 모드에서도 쓸 수는 있지만 포트 매핑 때문에 설정이 복잡해지고, awsvpc에서 얻을 수 있는 mTLS, 개별 SG 같은 이점을 포기해야 한다. 새 프로젝트라면 awsvpc + Service Connect 조합으로 가는 게 장기적으로 가장 덜 꼬인다.
