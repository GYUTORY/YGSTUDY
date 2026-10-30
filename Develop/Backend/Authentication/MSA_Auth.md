---
title: 마이크로서비스 환경의 인증/인가
tags: [backend, auth, microservices, api]
updated: 2026-10-30
---

# 마이크로서비스 환경의 인증/인가

## 단일 서비스와 뭐가 다른가

단일 서비스에서는 로그인 → 세션/JWT 발급 → 매 요청 검증, 이게 끝이다. 서비스가 하나니까 인증 정보가 밖으로 나갈 일이 없다.

MSA에서는 문제가 복잡해진다.

```
Client → API Gateway → Order Service → Payment Service → Inventory Service
                           │                  │
                      이 사용자가 누군지     여기서도 알아야 함
                      어디까지 할 수 있는지   여기서도 확인해야 함
```

사용자 요청 하나가 내부 서비스 여러 개를 거치는데, 각 서비스가 "이 요청이 누구 거고, 뭘 할 수 있는지" 알아야 한다. 인증 정보를 서비스 간에 어떻게 전파할 것인지가 핵심이다.

## API Gateway에서의 토큰 검증

모든 외부 요청은 API Gateway를 통과한다. 토큰 검증을 각 서비스에서 개별로 하면 중복 로직이 생기고, 인증 서버에 부하가 몰린다. Gateway에서 한 번 검증하고, 내부 서비스에는 검증된 사용자 정보를 전달하는 구조가 일반적이다.

```
Client ──Bearer Token──▶ API Gateway ──내부 헤더──▶ 각 서비스
                            │
                      1. JWT 서명 검증
                      2. 만료 확인
                      3. 사용자 정보 추출
                      4. 내부 헤더에 담아 전달
```

<div class="ygd-gateway-token-verification-flow" id="ygd-gateway-token-verification-flow">
<style>
.ygd-gateway-token-verification-flow{max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:12px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-fg);--ygd-bg:#FAF8F6;--ygd-fg:#2B2825;--ygd-muted:#5F5A54;--ygd-line:#8A847C;--ygd-box:#FFFFFF;--ygd-on:#2F6B80;--ygd-on-bg:#DDEEF4;--ygd-ok:#2F7D4F;--ygd-ok-bg:#E4F3EA;--ygd-bad:#B3261E;--ygd-bad-bg:#FBE9E7;}
body[data-md-color-scheme="slate"] .ygd-gateway-token-verification-flow{--ygd-bg:#1F1C1E;--ygd-fg:#F0EDE9;--ygd-muted:#B5AFA7;--ygd-line:#8F897F;--ygd-box:#2A2729;--ygd-on:#7FC0D6;--ygd-on-bg:#223A44;--ygd-ok:#6FCF97;--ygd-ok-bg:#1F3A2B;--ygd-bad:#FF8A80;--ygd-bad-bg:#432220;}
.ygd-gateway-token-verification-flow *{box-sizing:border-box;}
.ygd-gateway-token-verification-flow .ygd-svg{display:block;width:100%;height:auto;max-width:100%;}
.ygd-gateway-token-verification-flow .ygd-r{fill:var(--ygd-box);stroke:var(--ygd-line);stroke-width:1.5;transition:fill .3s,stroke .3s;}
.ygd-gateway-token-verification-flow .ygd-tx{fill:var(--ygd-fg);font-size:12px;text-anchor:middle;}
.ygd-gateway-token-verification-flow .ygd-tx-s{fill:var(--ygd-fg);font-size:11px;text-anchor:middle;}
.ygd-gateway-token-verification-flow .ygd-tx-xs{fill:var(--ygd-fg);font-size:10px;text-anchor:middle;}
.ygd-gateway-token-verification-flow .ygd-xmark{fill:var(--ygd-bad);font-size:16px;font-weight:700;text-anchor:middle;}
.ygd-gateway-token-verification-flow .ygd-ln{stroke:var(--ygd-line);stroke-width:2;fill:none;transition:stroke .3s;}
.ygd-gateway-token-verification-flow .ygd-thin{stroke:var(--ygd-line);stroke-width:1;fill:none;}
.ygd-gateway-token-verification-flow .ygd-ln.ygd-on{stroke:var(--ygd-on);}
.ygd-gateway-token-verification-flow .ygd-ln.ygd-ok{stroke:var(--ygd-ok);}
.ygd-gateway-token-verification-flow .ygd-ln.ygd-bad{stroke:var(--ygd-bad);}
.ygd-gateway-token-verification-flow g.ygd-on .ygd-r{stroke:var(--ygd-on);fill:var(--ygd-on-bg);stroke-width:2.5;}
.ygd-gateway-token-verification-flow g.ygd-ok .ygd-r{stroke:var(--ygd-ok);fill:var(--ygd-ok-bg);stroke-width:2;}
.ygd-gateway-token-verification-flow g.ygd-bad .ygd-r{stroke:var(--ygd-bad);fill:var(--ygd-bad-bg);stroke-width:2.5;}
.ygd-gateway-token-verification-flow .ygd-dim{opacity:.5;}
.ygd-gateway-token-verification-flow .ygd-hid{visibility:hidden;}
.ygd-gateway-token-verification-flow .ygd-flow{stroke-dasharray:6 4;animation:ygd-gateway-token-verification-flow-dash .8s linear infinite;}
@keyframes ygd-gateway-token-verification-flow-dash{to{stroke-dashoffset:-10;}}
.ygd-gateway-token-verification-flow .ygd-mn{fill:var(--ygd-line);}
.ygd-gateway-token-verification-flow .ygd-mo{fill:var(--ygd-on);}
.ygd-gateway-token-verification-flow .ygd-mk{fill:var(--ygd-ok);}
.ygd-gateway-token-verification-flow .ygd-mb{fill:var(--ygd-bad);}
.ygd-gateway-token-verification-flow .ygd-pbox{fill:var(--ygd-box);stroke:var(--ygd-line);stroke-width:1;}
.ygd-gateway-token-verification-flow .ygd-pt{fill:var(--ygd-muted);font-size:11px;font-weight:700;}
.ygd-gateway-token-verification-flow .ygd-pl{fill:var(--ygd-fg);font-size:11px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
.ygd-gateway-token-verification-flow .ygd-ctl{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 8px;}
.ygd-gateway-token-verification-flow .ygd-btn{font:inherit;font-size:14px;min-height:40px;padding:6px 16px;border:1px solid var(--ygd-line);border-radius:6px;background:var(--ygd-box);color:var(--ygd-fg);cursor:pointer;}
.ygd-gateway-token-verification-flow .ygd-btn-main{border-color:var(--ygd-on);background:var(--ygd-on-bg);font-weight:700;}
.ygd-gateway-token-verification-flow .ygd-btn:disabled{opacity:.5;cursor:default;}
.ygd-gateway-token-verification-flow .ygd-btn:focus-visible{outline:3px solid var(--ygd-on);outline-offset:2px;}
.ygd-gateway-token-verification-flow .ygd-step{margin:0 0 4px;font-size:15px;font-weight:700;color:var(--ygd-fg);}
.ygd-gateway-token-verification-flow .ygd-desc{margin:0 0 8px;font-size:15px;line-height:1.6;color:var(--ygd-fg);min-height:4.8em;}
.ygd-gateway-token-verification-flow .ygd-note{margin:0;padding-top:8px;border-top:1px solid var(--ygd-line);font-size:14px;line-height:1.6;color:var(--ygd-muted);}
@media (prefers-reduced-motion:reduce){.ygd-gateway-token-verification-flow *{transition:none !important;animation:none !important;}}
</style>
<svg class="ygd-svg" viewBox="0 0 360 292" role="img" aria-label="Client가 Bearer 토큰으로 요청하면 API Gateway가 서명 검증, 만료 확인, 사용자 정보 추출을 거쳐 Authorization 헤더를 지우고 X-User 헤더를 붙여 Order 서비스로 전달한다. 검증에 실패하면 Gateway가 401로 끊고, Gateway를 우회한 직접 요청은 네트워크 차단으로 막힌다.">
<defs>
<marker id="ygd-gateway-token-verification-flow-m-n" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path class="ygd-mn" d="M0,0 L8,4 L0,8 Z"/></marker>
<marker id="ygd-gateway-token-verification-flow-m-o" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path class="ygd-mo" d="M0,0 L8,4 L0,8 Z"/></marker>
<marker id="ygd-gateway-token-verification-flow-m-k" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path class="ygd-mk" d="M0,0 L8,4 L0,8 Z"/></marker>
<marker id="ygd-gateway-token-verification-flow-m-b" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path class="ygd-mb" d="M0,0 L8,4 L0,8 Z"/></marker>
</defs>
<line class="ygd-thin" x1="180" y1="64" x2="180" y2="84"/>
<line class="ygd-ln" data-k="a1" x1="92" y1="42" x2="136" y2="42" marker-end="url(#ygd-gateway-token-verification-flow-m-n)"/>
<line class="ygd-ln" data-k="a2" x1="222" y1="42" x2="266" y2="42" marker-end="url(#ygd-gateway-token-verification-flow-m-n)"/>
<line class="ygd-ln" data-k="a401" x1="118" y1="95" x2="94" y2="95" marker-end="url(#ygd-gateway-token-verification-flow-m-n)"/>
<line class="ygd-ln" data-k="aatk" x1="310" y1="148" x2="310" y2="112" marker-end="url(#ygd-gateway-token-verification-flow-m-n)"/>
<line class="ygd-ln" data-k="adash" x1="310" y1="94" x2="310" y2="66" stroke-dasharray="3 4"/>
<g data-k="client"><rect class="ygd-r" x="8" y="20" width="84" height="44" rx="6"/><text class="ygd-tx" x="50" y="46">Client</text></g>
<g data-k="gw"><rect class="ygd-r" x="138" y="20" width="84" height="44" rx="6"/><text class="ygd-tx" x="180" y="38">API</text><text class="ygd-tx" x="180" y="54">Gateway</text></g>
<g data-k="order"><rect class="ygd-r" x="268" y="20" width="84" height="44" rx="6"/><text class="ygd-tx" x="310" y="38">Order</text><text class="ygd-tx" x="310" y="54">서비스</text></g>
<g data-k="b401"><rect class="ygd-r" x="8" y="84" width="84" height="22" rx="4"/><text class="ygd-tx-s" x="50" y="99">401 응답</text></g>
<g data-k="c1"><rect class="ygd-r" x="118" y="84" width="124" height="22" rx="4"/><text class="ygd-tx-s" x="180" y="99">1. 서명 검증</text></g>
<g data-k="c2"><rect class="ygd-r" x="118" y="112" width="124" height="22" rx="4"/><text class="ygd-tx-s" x="180" y="127">2. 만료 확인</text></g>
<g data-k="c3"><rect class="ygd-r" x="118" y="140" width="124" height="22" rx="4"/><text class="ygd-tx-s" x="180" y="155">3. 사용자 정보 추출</text></g>
<g data-k="c4"><rect class="ygd-r" x="118" y="168" width="124" height="22" rx="4"/><text class="ygd-tx-s" x="180" y="183">4. 헤더 교체 후 전달</text></g>
<g data-k="bar"><rect class="ygd-r" x="268" y="96" width="84" height="14" rx="3"/><text class="ygd-tx-xs" x="310" y="106.5">네트워크 차단</text></g>
<text class="ygd-xmark" data-k="x" x="310" y="86">✕</text>
<g data-k="atk"><rect class="ygd-r" x="268" y="150" width="84" height="40" rx="6"/><text class="ygd-tx-s" x="310" y="167">공격자</text><text class="ygd-tx-s" x="310" y="183">(직접 호출)</text></g>
<rect class="ygd-pbox" x="8" y="198" width="344" height="92" rx="6"/>
<text class="ygd-pt" data-k="pt" x="18" y="214"></text>
<text class="ygd-pl" data-k="p0" x="18" y="232"></text>
<text class="ygd-pl" data-k="p1" x="18" y="248"></text>
<text class="ygd-pl" data-k="p2" x="18" y="264"></text>
<text class="ygd-pl" data-k="p3" x="18" y="280"></text>
</svg>
<div class="ygd-ctl">
<button type="button" class="ygd-btn ygd-btn-main" data-k="play">재생</button>
<button type="button" class="ygd-btn" data-k="next">다음 단계</button>
<button type="button" class="ygd-btn" data-k="reset">처음으로</button>
</div>
<p class="ygd-step" data-k="step" aria-live="polite"></p>
<p class="ygd-desc" data-k="desc" aria-live="polite"></p>
<p class="ygd-note">비유: 건물 안내데스크가 방문증을 확인한 뒤 내부 출입 전용 카드로 바꿔 주는 것과 비슷하다. 다만 X-User 헤더 자체에는 위조를 막는 장치가 없으므로, 데스크를 거치지 않는 뒷문은 네트워크 수준에서 닫아 두어야 한다.</p>
<script>
(function(){
var root=document.getElementById('ygd-gateway-token-verification-flow');
if(!root){return;}
var P='ygd-gateway-token-verification-flow-m-';
function q(k){return root.querySelector('[data-k="'+k+'"]');}
var keys=['client','gw','order','atk','c1','c2','c3','c4','a1','a2','a401','b401','aatk','bar','adash','x'];
var arrows=['a1','a2','a401','aatk'];
var el={};
keys.forEach(function(k){el[k]=q(k);});
var pt=q('pt'),pl=[q('p0'),q('p1'),q('p2'),q('p3')];
var playBtn=q('play'),nextBtn=q('next'),resetBtn=q('reset'),stepEl=q('step'),descEl=q('desc');
var steps=[
{t:'준비',d:'재생을 누르면 Client의 요청이 Gateway를 거쳐 Order 서비스에 닿기까지를 한 단계씩 보여 준다. 마지막에는 검증 실패와 Gateway 우회 공격도 다룬다.',on:[],ok:[],bad:[],p:['요청 헤더',['재생 또는 다음 단계를 눌러 시작한다']]},
{t:'정상 경로 · Bearer 토큰으로 요청',d:'Client가 Authorization 헤더에 Bearer 토큰을 실어 요청한다. 모든 외부 요청은 API Gateway를 먼저 통과한다.',on:['client','a1'],ok:[],bad:[],p:['Client → Gateway',['GET /orders','Authorization: Bearer <JWT>']]},
{t:'정상 경로 · 1. 서명 검증',d:'Gateway가 Bearer 뒤의 토큰을 꺼내 JWT 서명을 검증한다. 검증을 각 서비스가 따로 하지 않고 여기서 한 번만 한다.',on:['gw','c1'],ok:['client','a1'],bad:[],p:['Gateway 내부',['Bearer 뒤의 토큰 문자열을 꺼낸다','JWT 서명을 검증한다']]},
{t:'정상 경로 · 2. 만료 확인',d:'서명이 맞더라도 토큰이 만료됐다면 통과하지 못한다. 서명과 만료 확인이 모두 끝나야 다음 단계로 넘어간다.',on:['gw','c2'],ok:['client','a1','c1'],bad:[],p:['Gateway 내부',['토큰이 만료됐는지 확인한다','만료됐다면 여기서 멈춘다']]},
{t:'정상 경로 · 3. 사용자 정보 추출',d:'검증을 통과한 토큰에서 sub, roles, email을 꺼낸다. 이 값이 내부 서비스에 넘길 사용자 정보가 된다.',on:['gw','c3'],ok:['client','a1','c1','c2'],bad:[],p:['Gateway 내부',['검증된 토큰에서 꺼낸 값','sub, roles, email']]},
{t:'정상 경로 · 4. 헤더 교체',d:'Gateway는 원본 Authorization 헤더를 지우고 X-User-Id, X-User-Roles, X-User-Email을 붙인다. 내부 서비스가 외부 토큰을 직접 파싱하지 않게 하려는 것이다.',on:['gw','c4'],ok:['client','a1','c1','c2','c3'],bad:[],p:['Gateway가 만든 내부 헤더',['X-User-Id: <sub>','X-User-Roles: <roles를 쉼표로 연결>','X-User-Email: <email>','Authorization: (제거됨)']]},
{t:'정상 경로 · Order 서비스로 전달',d:'Order 서비스는 Gateway가 넣어 준 X-User-* 헤더만 신뢰한다. X-User-Id로 사용자를 식별하고 roles에는 ROLE_ 접두어를 붙여 권한으로 쓴다.',on:['a2','order'],ok:['client','a1','gw','c1','c2','c3','c4'],bad:[],p:['Order 서비스 수신',['X-User-Id로 사용자를 식별한다','X-User-Roles를 ROLE_ 권한으로 바꾼다','Authorization은 보지 않는다']]},
{t:'실패 분기 · 401로 끊김',d:'Bearer 헤더가 없거나 검증 중 예외가 나면 Gateway가 401로 응답하고 끝낸다. 서명이 틀렸거나 만료된 토큰도 여기에 해당하며, Order 서비스까지는 요청이 가지 않는다.',on:['gw'],ok:['client','a1'],bad:['c1','c2','a401','b401'],p:['검증 실패 → Gateway에서 종료',['Bearer 헤더 없음 또는 검증 예외','Gateway가 401을 돌려주고 끝낸다','Order 서비스에는 요청이 도달하지 않는다']]},
{t:'우회 공격 · 네트워크에서 차단',d:'Gateway를 거치지 않고 X-User-Id: admin을 직접 보내면 관리자 행세가 가능해진다. 그래서 내부 서비스는 내부 네트워크에서만 접근되게 막아야 하고, Kubernetes는 NetworkPolicy, AWS는 Security Group으로 잡는다.',on:['atk','aatk'],ok:['order'],bad:['bar','adash','x'],p:['공격자 → Order (Gateway 우회)',['X-User-Id: admin','내부 네트워크 밖에서 온 직접 요청은','NetworkPolicy / Security Group이 차단한다']]}
];
var last=steps.length-1,idx=0,timer=null,DELAY=3400;
function render(i){
var s=steps[i];
keys.forEach(function(k){
var e=el[k],st='';
e.classList.remove('ygd-on','ygd-ok','ygd-bad','ygd-dim');
if(s.on.indexOf(k)>=0){st='on';}else if(s.ok.indexOf(k)>=0){st='ok';}else if(s.bad.indexOf(k)>=0){st='bad';}
if(st){e.classList.add('ygd-'+st);}else if(i>0){e.classList.add('ygd-dim');}
if(arrows.indexOf(k)>=0){
var m=st==='on'?'o':st==='ok'?'k':st==='bad'?'b':'n';
e.setAttribute('marker-end','url(#'+P+m+')');
if(st==='on'){e.classList.add('ygd-flow');}else{e.classList.remove('ygd-flow');}
}
});
if(i===last){el.x.classList.remove('ygd-hid');}else{el.x.classList.add('ygd-hid');}
pt.textContent=s.p[0];
for(var n=0;n<4;n++){pl[n].textContent=s.p[1][n]||'';}
stepEl.textContent=(i===0?'단계 0 / ':'단계 '+i+' / ')+last+' · '+s.t;
descEl.textContent=s.d;
nextBtn.disabled=(i>=last);
playBtn.textContent=timer?'일시정지':(i>=last?'다시 재생':'재생');
}
function stop(){
if(timer){clearTimeout(timer);timer=null;}
}
function tick(){
timer=null;
if(idx<last){
idx++;
if(idx<last){timer=setTimeout(tick,DELAY);}
}
render(idx);
}
playBtn.addEventListener('click',function(){
if(timer){stop();render(idx);return;}
if(idx>=last){idx=0;}
idx++;
timer=setTimeout(tick,DELAY);
render(idx);
});
nextBtn.addEventListener('click',function(){
stop();
if(idx<last){idx++;}
render(idx);
});
resetBtn.addEventListener('click',function(){
stop();
idx=0;
render(idx);
});
render(0);
})();
</script>
</div>

### NestJS API Gateway 구현

```typescript
import { Injectable, NestMiddleware, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class AuthGatewayMiddleware implements NestMiddleware {
  constructor(private readonly jwtService: JwtService) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const authHeader = req.headers['authorization'];

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).end();
      return;
    }

    const token = authHeader.substring(7);

    try {
      const jwt = await this.jwtService.verifyAsync<{
        sub: string;
        roles: string[];
        email: string;
      }>(token);

      // 검증된 사용자 정보를 내부 헤더로 전달
      req.headers['x-user-id'] = jwt.sub;
      req.headers['x-user-roles'] = jwt.roles.join(',');
      req.headers['x-user-email'] = jwt.email;
      // 원본 Authorization 헤더는 제거
      delete req.headers['authorization'];

      next();
    } catch {
      res.status(401).end();
    }
  }
}
```

원본 `Authorization` 헤더를 제거하는 이유: 내부 서비스가 외부 토큰을 직접 파싱하기 시작하면, Gateway의 검증 로직과 각 서비스의 검증 로직이 따로 놀게 된다. 내부 서비스는 Gateway가 넣어준 `X-User-*` 헤더만 신뢰하도록 통일해야 한다.

### 내부 서비스에서 사용자 정보 수신

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class InternalAuthMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    const userId = req.headers['x-user-id'] as string | undefined;
    const roles = req.headers['x-user-roles'] as string | undefined;

    if (userId) {
      const authorities = (roles ?? '')
        .split(',')
        .filter((r) => r.trim() !== '')
        .map((r) => 'ROLE_' + r);

      // 요청 컨텍스트에 사용자 정보 저장
      (req as Request & { internalUser: { userId: string; roles: string[] } }).internalUser = {
        userId,
        roles: authorities,
      };
    }

    next();
  }
}
```

```typescript
// 컨트롤러에서 사용
import { Controller, Get, Req } from '@nestjs/common';
import { Request } from 'express';

@Controller('orders')
export class OrderController {
  constructor(private readonly orderService: OrderService) {}

  @Get()
  getMyOrders(@Req() req: Request & { internalUser: { userId: string } }): Promise<Order[]> {
    return this.orderService.findByUserId(req.internalUser.userId);
  }
}
```

여기서 중요한 문제가 하나 있다. `X-User-Id` 헤더를 외부에서 직접 보내면? Gateway를 거치지 않고 내부 서비스에 직접 접근하는 경우, 누구든 `X-User-Id: admin`을 넣어서 관리자 행세를 할 수 있다. 내부 서비스는 반드시 내부 네트워크에서만 접근 가능하도록 네트워크 레벨에서 차단해야 한다. Kubernetes라면 NetworkPolicy, AWS라면 Security Group으로 잡는다.

## Service-to-Service 인증

사용자 요청 전파와는 별개로, 서비스끼리 직접 호출하는 경우가 있다. 배치 처리, 이벤트 처리, 헬스 체크 같은 상황이다. 이때는 사용자 토큰이 없으니 서비스 자체를 인증해야 한다.

<div class="ygd-service-to-service-auth-compare" id="ygd-service-to-service-auth-compare">
<style>
.ygd-service-to-service-auth-compare{--ygd-bg:#FFFFFF;--ygd-surface:#F5F3F0;--ygd-border:#CFC9C0;--ygd-text:#2B2825;--ygd-muted:#5F5A54;--ygd-a1:#2F6477;--ygd-a2:#8F4B00;--ygd-ac:var(--ygd-a1);--ygd-on:#FFFFFF;--ygd-line:#6B655E;--ygd-soft:#EAF1F4;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:12px;border:1px solid var(--ygd-border);border-radius:10px;background:var(--ygd-bg);color:var(--ygd-text);font-size:15px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-service-to-service-auth-compare{--ygd-bg:#262325;--ygd-surface:#302C2F;--ygd-border:#5A5558;--ygd-text:#F0EDE9;--ygd-muted:#B8B2AA;--ygd-a1:#7FC0D6;--ygd-a2:#F0B35E;--ygd-on:#1F1C1E;--ygd-line:#A39D95;--ygd-soft:#2A3A41}
.ygd-service-to-service-auth-compare .ygd-title{font-size:16px;font-weight:700;margin:0 0 10px}
.ygd-service-to-service-auth-compare .ygd-tabs{display:flex;gap:6px;margin-bottom:12px}
.ygd-service-to-service-auth-compare .ygd-tab,.ygd-service-to-service-auth-compare .ygd-btn{box-sizing:border-box;font-family:inherit;font-size:14px;line-height:1.3;min-height:44px;padding:8px 14px;border:1px solid var(--ygd-border);border-radius:8px;background:var(--ygd-surface);color:var(--ygd-text);cursor:pointer}
.ygd-service-to-service-auth-compare .ygd-tab{flex:1 1 0;font-size:15px;font-weight:700}
.ygd-service-to-service-auth-compare .ygd-tab.ygd-on{background:var(--ygd-a1);border-color:var(--ygd-a1);color:var(--ygd-on)}
.ygd-service-to-service-auth-compare .ygd-tab:focus-visible,.ygd-service-to-service-auth-compare .ygd-btn:focus-visible{outline:3px solid var(--ygd-a2);outline-offset:2px}
.ygd-service-to-service-auth-compare .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-service-to-service-auth-compare .ygd-panel[hidden]{display:none}
.ygd-service-to-service-auth-compare .ygd-p-jwt{--ygd-ac:var(--ygd-a2)}
.ygd-service-to-service-auth-compare .ygd-svg{display:block;width:100%;max-width:520px;height:auto;margin:0 auto}
.ygd-service-to-service-auth-compare .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.ygd-service-to-service-auth-compare .ygd-step{padding:10px 12px;border-left:4px solid var(--ygd-ac);background:var(--ygd-soft);border-radius:6px;font-size:15px;line-height:1.6}
.ygd-service-to-service-auth-compare .ygd-sn{font-size:14px;font-weight:700;color:var(--ygd-muted);margin-bottom:2px}
.ygd-service-to-service-auth-compare .ygd-sd{color:var(--ygd-text)}
.ygd-service-to-service-auth-compare .ygd-facts{margin-top:10px;display:flex;flex-direction:column;gap:8px}
.ygd-service-to-service-auth-compare .ygd-fact{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;font-size:14px;line-height:1.6}
.ygd-service-to-service-auth-compare .ygd-fl{flex:0 0 auto;font-weight:700;padding:0 8px;border:1px solid var(--ygd-ac);border-radius:6px;color:var(--ygd-ac)}
.ygd-service-to-service-auth-compare .ygd-ft{flex:1 1 220px;min-width:0}
.ygd-service-to-service-auth-compare .ygd-note{margin-top:12px;font-size:14px;line-height:1.6;color:var(--ygd-muted)}
.ygd-service-to-service-auth-compare .ygd-s{opacity:.5;transition:opacity .3s}
.ygd-service-to-service-auth-compare .ygd-s.ygd-done,.ygd-service-to-service-auth-compare .ygd-s.ygd-now{opacity:1}
.ygd-service-to-service-auth-compare .ygd-ln{fill:none;stroke:var(--ygd-line);stroke-width:1.6;marker-end:url(#ygd-service-to-service-auth-compare-mk)}
.ygd-service-to-service-auth-compare .ygd-now .ygd-ln{stroke:var(--ygd-ac);stroke-width:2.4;stroke-dasharray:6 4;animation:ygd-service-to-service-auth-compare-flow .8s linear infinite;marker-end:url(#ygd-service-to-service-auth-compare-mkh)}
@keyframes ygd-service-to-service-auth-compare-flow{to{stroke-dashoffset:-20}}
.ygd-service-to-service-auth-compare .ygd-mk{fill:var(--ygd-line)}
.ygd-service-to-service-auth-compare .ygd-mkh{fill:var(--ygd-ac)}
.ygd-service-to-service-auth-compare .ygd-box{fill:var(--ygd-surface);stroke:var(--ygd-border);stroke-width:1.2}
.ygd-service-to-service-auth-compare .ygd-pod{fill:none;stroke:var(--ygd-border);stroke-width:1.2;stroke-dasharray:4 3}
.ygd-service-to-service-auth-compare .ygd-life{stroke:var(--ygd-border);stroke-width:1.2;stroke-dasharray:3 3}
.ygd-service-to-service-auth-compare .ygd-card{fill:var(--ygd-surface);stroke:var(--ygd-border);stroke-width:1.2}
.ygd-service-to-service-auth-compare .ygd-now .ygd-card{stroke:var(--ygd-ac);stroke-width:2}
.ygd-service-to-service-auth-compare .ygd-tx{fill:var(--ygd-text);font-family:inherit}
.ygd-service-to-service-auth-compare .ygd-tm{fill:var(--ygd-muted)}
.ygd-service-to-service-auth-compare .ygd-b{font-weight:700}
.ygd-service-to-service-auth-compare .ygd-mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.ygd-service-to-service-auth-compare .ygd-now .ygd-tx{fill:var(--ygd-ac);font-weight:700}
.ygd-service-to-service-auth-compare .ygd-bd{fill:var(--ygd-muted)}
.ygd-service-to-service-auth-compare .ygd-done .ygd-bd,.ygd-service-to-service-auth-compare .ygd-now .ygd-bd{fill:var(--ygd-ac)}
.ygd-service-to-service-auth-compare .ygd-s .ygd-bdt{fill:var(--ygd-on);font-weight:700}
@media (prefers-reduced-motion:reduce){.ygd-service-to-service-auth-compare .ygd-s{transition:none}.ygd-service-to-service-auth-compare .ygd-now .ygd-ln{animation:none;stroke-dasharray:none}}
</style>
<div class="ygd-title">Service-to-Service 인증: mTLS와 Internal JWT</div>
<div class="ygd-tabs" role="tablist" aria-label="서비스 간 인증 방식 선택">
<button type="button" class="ygd-tab ygd-on" role="tab" data-key="mtls" id="ygd-service-to-service-auth-compare-tab-mtls" aria-controls="ygd-service-to-service-auth-compare-panel-mtls" aria-selected="true" tabindex="0">mTLS</button>
<button type="button" class="ygd-tab" role="tab" data-key="jwt" id="ygd-service-to-service-auth-compare-tab-jwt" aria-controls="ygd-service-to-service-auth-compare-panel-jwt" aria-selected="false" tabindex="-1">Internal JWT</button>
</div>
<div class="ygd-panel ygd-p-mtls" role="tabpanel" data-key="mtls" id="ygd-service-to-service-auth-compare-panel-mtls" aria-labelledby="ygd-service-to-service-auth-compare-tab-mtls">
<svg class="ygd-svg" viewBox="0 0 320 334" role="img" aria-label="mTLS 핸드셰이크 다이어그램. Order 앱이 자기 Pod의 사이드카로 요청을 보내면, 두 사이드카가 TLS 연결을 열고 서버 인증서와 클라이언트 인증서를 서로 제시해 검증한 뒤 암호화된 연결로 요청을 Payment 앱에 전달한다.">
<defs>
<marker id="ygd-service-to-service-auth-compare-mk" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-service-to-service-auth-compare-mkh" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mkh" d="M0 0L10 5L0 10z"/></marker>
</defs>
<rect class="ygd-pod" x="2" y="4" width="100" height="104" rx="8"/>
<rect class="ygd-pod" x="218" y="4" width="100" height="104" rx="8"/>
<text class="ygd-tx ygd-tm" x="52" y="18" text-anchor="middle" font-size="10.5">Order Pod</text>
<text class="ygd-tx ygd-tm" x="268" y="18" text-anchor="middle" font-size="10.5">Payment Pod</text>
<rect class="ygd-box" x="10" y="28" width="84" height="24" rx="5"/>
<text class="ygd-tx" x="52" y="44" text-anchor="middle" font-size="11">Order 앱</text>
<rect class="ygd-box" x="10" y="76" width="84" height="24" rx="5"/>
<text class="ygd-tx" x="52" y="92" text-anchor="middle" font-size="11">사이드카</text>
<rect class="ygd-box" x="226" y="28" width="84" height="24" rx="5"/>
<text class="ygd-tx" x="268" y="44" text-anchor="middle" font-size="11">Payment 앱</text>
<rect class="ygd-box" x="226" y="76" width="84" height="24" rx="5"/>
<text class="ygd-tx" x="268" y="92" text-anchor="middle" font-size="11">사이드카</text>
<line class="ygd-life" x1="52" y1="100" x2="52" y2="328"/>
<line class="ygd-life" x1="268" y1="100" x2="268" y2="328"/>
<g class="ygd-s" data-s="1">
<line class="ygd-ln" x1="52" y1="54" x2="52" y2="74"/>
<circle class="ygd-bd" cx="74" cy="64" r="8"/>
<text class="ygd-tx ygd-bdt" x="74" y="67.5" text-anchor="middle" font-size="10">1</text>
</g>
<g class="ygd-s" data-s="2">
<circle class="ygd-bd" cx="16" cy="140" r="8"/>
<text class="ygd-tx ygd-bdt" x="16" y="143.5" text-anchor="middle" font-size="10">2</text>
<text class="ygd-tx" x="160" y="132" text-anchor="middle" font-size="11.5">TLS 연결 시작</text>
<line class="ygd-ln" x1="56" y1="140" x2="264" y2="140"/>
</g>
<g class="ygd-s" data-s="3">
<circle class="ygd-bd" cx="16" cy="196" r="8"/>
<text class="ygd-tx ygd-bdt" x="16" y="199.5" text-anchor="middle" font-size="10">3</text>
<text class="ygd-tx" x="160" y="188" text-anchor="middle" font-size="11.5">서버 인증서 제시</text>
<line class="ygd-ln" x1="264" y1="196" x2="56" y2="196"/>
<text class="ygd-tx ygd-tm" x="60" y="216" font-size="11">Order 사이드카가 검증</text>
</g>
<g class="ygd-s" data-s="4">
<circle class="ygd-bd" cx="16" cy="252" r="8"/>
<text class="ygd-tx ygd-bdt" x="16" y="255.5" text-anchor="middle" font-size="10">4</text>
<text class="ygd-tx" x="160" y="244" text-anchor="middle" font-size="11.5">클라이언트 인증서 제시</text>
<line class="ygd-ln" x1="56" y1="252" x2="264" y2="252"/>
<text class="ygd-tx ygd-tm" x="264" y="272" text-anchor="end" font-size="11">Payment 사이드카가 검증</text>
</g>
<g class="ygd-s" data-s="5">
<circle class="ygd-bd" cx="16" cy="308" r="8"/>
<text class="ygd-tx ygd-bdt" x="16" y="311.5" text-anchor="middle" font-size="10">5</text>
<text class="ygd-tx" x="160" y="300" text-anchor="middle" font-size="11.5">암호화된 연결로 요청 전달</text>
<line class="ygd-ln" x1="56" y1="308" x2="264" y2="308"/>
<text class="ygd-tx ygd-tm" x="160" y="326" text-anchor="middle" font-size="11">STRICT: mTLS가 아닌 평문은 거부</text>
</g>
<g class="ygd-s" data-s="5">
<line class="ygd-ln" x1="268" y1="74" x2="268" y2="54"/>
</g>
</svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-play" aria-pressed="false">재생</button>
<button type="button" class="ygd-btn ygd-next">다음 단계</button>
<button type="button" class="ygd-btn ygd-reset">처음으로</button>
</div>
<div class="ygd-step" aria-live="polite"><div class="ygd-sn"></div><div class="ygd-sd"></div></div>
<div class="ygd-facts">
<div class="ygd-fact"><span class="ygd-fl">관리 부담</span><span class="ygd-ft">메시가 있으면 사이드카가 발급·갱신·검증을 맡는다. 직접 구현하면 만료·갱신·배포를 직접 해야 하고 서비스가 늘수록 관리 포인트가 폭발한다.</span></div>
<div class="ygd-fact"><span class="ygd-fl">키 유출 시</span><span class="ygd-ft">인증서는 Pod(서비스)별로 발급되므로, 유출된 개인키로는 해당 서비스의 신원으로 행세할 수 있다.</span></div>
</div>
</div>
<div class="ygd-panel ygd-p-jwt" role="tabpanel" data-key="jwt" id="ygd-service-to-service-auth-compare-panel-jwt" aria-labelledby="ygd-service-to-service-auth-compare-tab-jwt" hidden>
<svg class="ygd-svg" viewBox="0 0 320 300" role="img" aria-label="Internal JWT 흐름 다이어그램. 호출하는 Order 서비스가 type이 service이고 permissions가 담긴 5분짜리 서비스 토큰을 발급해 X-Service-Auth 헤더로 보내면, 수신 측 Payment 서비스가 type 클레임과 permissions를 차례로 검사하고 통과하면 요청을 처리한다.">
<defs>
<marker id="ygd-service-to-service-auth-compare-mk2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-service-to-service-auth-compare-mkh2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mkh" d="M0 0L10 5L0 10z"/></marker>
</defs>
<rect class="ygd-box" x="2" y="4" width="100" height="40" rx="6"/>
<text class="ygd-tx ygd-b" x="52" y="21" text-anchor="middle" font-size="11.5">Order 서비스</text>
<text class="ygd-tx ygd-tm" x="52" y="37" text-anchor="middle" font-size="10.5">호출 측</text>
<rect class="ygd-box" x="218" y="4" width="100" height="40" rx="6"/>
<text class="ygd-tx ygd-b" x="268" y="21" text-anchor="middle" font-size="11.5">Payment 서비스</text>
<text class="ygd-tx ygd-tm" x="268" y="37" text-anchor="middle" font-size="10.5">수신 측</text>
<line class="ygd-life" x1="52" y1="44" x2="52" y2="56"/>
<line class="ygd-life" x1="268" y1="44" x2="268" y2="56"/>
<line class="ygd-life" x1="52" y1="142" x2="52" y2="196"/>
<line class="ygd-life" x1="268" y1="142" x2="268" y2="196"/>
<g class="ygd-s" data-s="1">
<rect class="ygd-card" x="8" y="56" width="304" height="86" rx="8"/>
<circle class="ygd-bd" cx="22" cy="74" r="8"/>
<text class="ygd-tx ygd-bdt" x="22" y="77.5" text-anchor="middle" font-size="10">1</text>
<text class="ygd-tx" x="38" y="78" font-size="11.5">서비스 토큰 발급 · Order 서비스가 직접 서명</text>
<text class="ygd-tx ygd-tm ygd-mono" x="18" y="96" font-size="10.5">sub: order-service   type: service</text>
<text class="ygd-tx ygd-tm ygd-mono" x="18" y="112" font-size="10.5">permissions: order:read, payment:process</text>
<text class="ygd-tx ygd-tm" x="18" y="128" font-size="10.5">만료 300초(5분) · 서비스 서명 키로 서명</text>
</g>
<g class="ygd-s" data-s="2">
<circle class="ygd-bd" cx="16" cy="176" r="8"/>
<text class="ygd-tx ygd-bdt" x="16" y="179.5" text-anchor="middle" font-size="10">2</text>
<text class="ygd-tx" x="160" y="168" text-anchor="middle" font-size="11.5">X-Service-Auth: Bearer 토큰</text>
<line class="ygd-ln" x1="56" y1="176" x2="264" y2="176"/>
</g>
<rect class="ygd-card" x="8" y="196" width="304" height="98" rx="8"/>
<text class="ygd-tx ygd-b" x="18" y="214" font-size="11.5">Payment 서비스가 수신 후 검사</text>
<g class="ygd-s" data-s="3">
<circle class="ygd-bd" cx="22" cy="232" r="8"/>
<text class="ygd-tx ygd-bdt" x="22" y="235.5" text-anchor="middle" font-size="10">3</text>
<text class="ygd-tx" x="38" y="236" font-size="11.5">type 클레임이 service인가</text>
</g>
<g class="ygd-s" data-s="4">
<circle class="ygd-bd" cx="22" cy="256" r="8"/>
<text class="ygd-tx ygd-bdt" x="22" y="259.5" text-anchor="middle" font-size="10">4</text>
<text class="ygd-tx" x="38" y="260" font-size="11.5">permissions에 호출 API 권한이 있는가</text>
</g>
<g class="ygd-s" data-s="5">
<circle class="ygd-bd" cx="22" cy="280" r="8"/>
<text class="ygd-tx ygd-bdt" x="22" y="283.5" text-anchor="middle" font-size="10">5</text>
<text class="ygd-tx" x="38" y="284" font-size="11.5">둘 다 통과하면 요청 처리</text>
</g>
</svg>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-play" aria-pressed="false">재생</button>
<button type="button" class="ygd-btn ygd-next">다음 단계</button>
<button type="button" class="ygd-btn ygd-reset">처음으로</button>
</div>
<div class="ygd-step" aria-live="polite"><div class="ygd-sn"></div><div class="ygd-sd"></div></div>
<div class="ygd-facts">
<div class="ygd-fact"><span class="ygd-fl">관리 부담</span><span class="ygd-ft">mTLS보다 구현이 간단하다. 대신 서비스가 서명 키를 보관하고 토큰을 직접 발급해야 한다.</span></div>
<div class="ygd-fact"><span class="ygd-fl">키 유출 시</span><span class="ygd-ft">서명 키가 유출되면 서비스 토큰을 위조할 수 있다. 사용자 JWT와 같은 키를 쓰면 사용자 토큰까지 위조되므로 키를 분리해야 한다.</span></div>
</div>
</div>
<div class="ygd-note">비유: 보안 구역 출입에 견주면, mTLS는 양쪽이 서로 신분증을 보여 주고 확인하는 것이고, Internal JWT는 권한이 적힌 5분짜리 출입증을 건네고 문 앞에서 확인하는 것이다. 비유일 뿐, 실제 동작은 위 단계를 따른다.</div>
<style>
.ygd-service-to-service-auth-compare .ygd-p-jwt .ygd-ln{marker-end:url(#ygd-service-to-service-auth-compare-mk2)}
.ygd-service-to-service-auth-compare .ygd-p-jwt .ygd-now .ygd-ln{marker-end:url(#ygd-service-to-service-auth-compare-mkh2)}
</style>
<script>
(function(){
var root=document.getElementById('ygd-service-to-service-auth-compare');
if(!root){return;}
var DELAY=2600;
var DATA={
mtls:{n:5,text:[
'재생을 누르면 Order 서비스가 Payment 서비스를 호출하는 과정을 사이드카 기준으로 보여 준다. 애플리케이션 코드에는 인증서 처리가 들어가지 않는다.',
'Order 앱은 요청만 보낸다. 인증서 발급, 갱신, 검증은 Pod에 붙은 사이드카 프록시가 맡는다.',
'Order 쪽 사이드카가 Payment 쪽 사이드카와 TLS 연결을 시작한다. 여기까지는 일반 TLS와 같다.',
'Payment 사이드카가 서버 인증서를 보내고 Order 사이드카가 이를 검증한다. 일반 TLS에서도 하는 단방향 검증이다.',
'mTLS의 차이는 여기다. Order 사이드카가 클라이언트 인증서를 보내고 Payment 사이드카가 검증해 양방향 인증이 완성된다.',
'양쪽 검증이 끝나면 요청이 암호화된 연결을 지나 Payment 앱으로 전달된다. STRICT 모드에서는 mTLS가 아닌 평문 연결을 거부한다.'
]},
jwt:{n:5,text:[
'재생을 누르면 Order 서비스가 서비스 토큰을 만들어 Payment 서비스를 호출하는 흐름을 보여 준다.',
'호출하는 Order 서비스가 서비스 토큰을 직접 발급한다. type은 service, permissions에는 허용 권한을 담고 만료는 5분(300초)이다.',
'토큰은 X-Service-Auth 헤더에 Bearer 형식으로 실려 간다. 수신 측은 이 헤더로 호출한 서비스의 신원을 확인한다.',
'수신 측 Payment 서비스는 먼저 type 클레임이 service인지 확인한다. 이 값이 아니면 서비스 토큰으로 보지 않는다.',
'다음으로 permissions에 이번에 호출한 API의 권한이 들어 있는지 검사한다. 서비스 신원이 맞아도 권한이 없으면 통과하지 못한다.',
'두 검사를 모두 통과하면 요청을 처리한다. 예시 코드는 요청마다 토큰을 새로 발급한다.'
]}
};
var panels={};
var tabs=Array.prototype.slice.call(root.querySelectorAll('.ygd-tab'));
Array.prototype.forEach.call(root.querySelectorAll('.ygd-panel'),function(el){
var key=el.getAttribute('data-key');
var d=DATA[key];
var groups=el.querySelectorAll('.ygd-s');
var playBtn=el.querySelector('.ygd-play');
var nextBtn=el.querySelector('.ygd-next');
var resetBtn=el.querySelector('.ygd-reset');
var sn=el.querySelector('.ygd-sn');
var sd=el.querySelector('.ygd-sd');
var step=0;
var timer=null;
function render(){
Array.prototype.forEach.call(groups,function(g){
var s=parseInt(g.getAttribute('data-s'),10);
g.classList.toggle('ygd-done',step>s);
g.classList.toggle('ygd-now',step===s);
});
sn.textContent=step===0?'시작 전':'단계 '+step+' / '+d.n;
sd.textContent=d.text[step];
nextBtn.disabled=step>=d.n;
}
function stop(){
if(timer){clearInterval(timer);timer=null;}
playBtn.textContent=step>=d.n?'다시 재생':'재생';
playBtn.setAttribute('aria-pressed','false');
}
function advance(){
if(step>=d.n){stop();return;}
step+=1;
render();
if(step>=d.n){stop();}
}
playBtn.addEventListener('click',function(){
if(timer){stop();return;}
if(step>=d.n){step=0;render();}
playBtn.textContent='일시정지';
playBtn.setAttribute('aria-pressed','true');
advance();
if(step<d.n){timer=setInterval(advance,DELAY);}
});
nextBtn.addEventListener('click',function(){
stop();
advance();
playBtn.textContent=step>=d.n?'다시 재생':'재생';
});
resetBtn.addEventListener('click',function(){
step=0;
stop();
render();
});
panels[key]={el:el,reset:function(){step=0;stop();render();}};
render();
});
function select(key,focus){
tabs.forEach(function(t){
var on=t.getAttribute('data-key')===key;
t.classList.toggle('ygd-on',on);
t.setAttribute('aria-selected',on?'true':'false');
t.setAttribute('tabindex',on?'0':'-1');
if(on&&focus){t.focus();}
});
Object.keys(panels).forEach(function(k){
var p=panels[k];
if(k===key){p.el.removeAttribute('hidden');}
else{p.el.setAttribute('hidden','');p.reset();}
});
}
tabs.forEach(function(t,i){
t.addEventListener('click',function(){select(t.getAttribute('data-key'),false);});
t.addEventListener('keydown',function(e){
var n=tabs.length;
var to=-1;
if(e.key==='ArrowRight'){to=(i+1)%n;}
else if(e.key==='ArrowLeft'){to=(i+n-1)%n;}
else if(e.key==='Home'){to=0;}
else if(e.key==='End'){to=n-1;}
if(to>-1){e.preventDefault();select(tabs[to].getAttribute('data-key'),true);}
});
});
})();
</script>
</div>

### mTLS (Mutual TLS)

일반 HTTPS에서는 클라이언트가 서버 인증서를 검증한다. mTLS는 서버도 클라이언트 인증서를 검증한다. 양방향 인증이다.

```
일반 TLS:
Client ────────▶ Server
         서버 인증서 검증

mTLS:
Client ◀───────▶ Server
  서버 인증서 검증    클라이언트 인증서 검증
```

Kubernetes에서는 Istio 같은 서비스 메시가 mTLS를 자동으로 처리한다. 각 Pod에 사이드카 프록시가 붙어서 인증서 발급, 갱신, 검증을 알아서 한다. 애플리케이션 코드를 건드릴 필요가 없다.

```yaml
# Istio PeerAuthentication - 네임스페이스 전체에 mTLS 적용
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: my-namespace
spec:
  mtls:
    mode: STRICT  # mTLS만 허용, 평문 거부
```

서비스 메시 없이 직접 구현하면 인증서 관리가 고역이다. 인증서 만료, 갱신, 배포를 직접 해야 하고, 서비스가 늘어날수록 관리 포인트가 폭발한다.

### Internal JWT

서비스 간 호출에 별도의 JWT를 발급하는 방식이다. mTLS보다 구현이 간단하고, 토큰에 서비스 정보와 권한을 담을 수 있다.

```typescript
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class ServiceTokenProvider {
  constructor(
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {}

  // 서비스 자체 인증용 토큰 발급
  issueServiceToken(sourceService: string): string {
    return this.jwtService.sign(
      {
        sub: sourceService,
        type: 'service',
        permissions: ['order:read', 'payment:process'],
      },
      {
        secret: this.configService.get<string>('AUTH_SERVICE_SIGNING_KEY'),
        expiresIn: 300, // 5분
      },
    );
  }
}
```

```typescript
// 다른 서비스 호출 시 토큰 첨부 (HttpService 인터셉터)
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ServiceTokenProvider } from './service-token.provider';

@Injectable()
export class PaymentServiceClient {
  constructor(
    private readonly httpService: HttpService,
    private readonly tokenProvider: ServiceTokenProvider,
  ) {
    this.httpService.axiosRef.interceptors.request.use((config) => {
      const token = this.tokenProvider.issueServiceToken('order-service');
      config.headers['X-Service-Auth'] = `Bearer ${token}`;
      return config;
    });
  }
}
```

수신 측에서는 `type` 클레임이 `service`인지 확인하고, `permissions`에 해당 API 호출 권한이 있는지 검사한다. 사용자 JWT와 서비스 JWT를 같은 키로 서명하면 안 된다. 서비스 토큰 키가 유출되면 사용자 토큰도 위조할 수 있게 된다.

## 토큰 릴레이와 권한 축소 문제

사용자가 주문을 하면 Order Service가 Payment Service를 호출하는데, 이때 사용자 토큰을 그대로 전달하는 걸 토큰 릴레이라 한다.

```
Client (Admin 권한)
  │
  ▼
Order Service ──사용자 토큰 그대로 전달──▶ Payment Service
                                            │
                                     이 토큰에 Admin 권한이 있네?
                                     Payment의 Admin API도 호출 가능?
```

문제가 보이는가. 사용자가 Order Service에 대해 Admin 권한을 갖고 있으면, 그 토큰이 Payment Service에 전달됐을 때 Payment의 Admin API까지 접근할 수 있다. 의도하지 않은 권한 확대다.

<div class="ygd-token-relay-vs-downscoping" id="ygd-token-relay-vs-downscoping">
<style>
.ygd-token-relay-vs-downscoping{--ygd-bg:#FDFBFA;--ygd-fg:#2B2725;--ygd-muted:#736E68;--ygd-line:#B9B2AA;--ygd-arrow:#6B655F;--ygd-node-bg:#FFFFFF;--ygd-chip-bg:#F3F0EC;--ygd-accent:#3D7387;--ygd-on-accent:#FFFFFF;--ygd-danger:#B3261E;--ygd-danger-bg:#FBE9E7;--ygd-ok:#1F7A45;--ygd-ok-bg:#E6F4EA;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:12px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:14px;line-height:1.5;overflow:hidden}
body[data-md-color-scheme="slate"] .ygd-token-relay-vs-downscoping{--ygd-bg:#1F1C1E;--ygd-fg:#F0EDE9;--ygd-muted:#9A948C;--ygd-line:#5A5459;--ygd-arrow:#B5AEA6;--ygd-node-bg:#2A2628;--ygd-chip-bg:#2F2B2D;--ygd-accent:#8CC4D8;--ygd-on-accent:#1F1C1E;--ygd-danger:#FF8A80;--ygd-danger-bg:#3A2020;--ygd-ok:#7FD6A0;--ygd-ok-bg:#1E3326}
.ygd-token-relay-vs-downscoping .ygd-bar{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px 0}
.ygd-token-relay-vs-downscoping .ygd-btn{box-sizing:border-box;min-height:40px;padding:8px 14px;border:1px solid var(--ygd-line);border-radius:6px;background:var(--ygd-chip-bg);color:var(--ygd-fg);font:inherit;font-size:14px;cursor:pointer}
.ygd-token-relay-vs-downscoping .ygd-mode{flex:1 1 140px}
.ygd-token-relay-vs-downscoping .ygd-mode[aria-pressed="true"]{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-on-accent);font-weight:700}
.ygd-token-relay-vs-downscoping .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-token-relay-vs-downscoping .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-token-relay-vs-downscoping .ygd-svg{display:block;width:100%;max-width:520px;height:auto;margin:0 auto}
.ygd-token-relay-vs-downscoping .ygd-s{opacity:.45;transition:opacity .3s}
.ygd-token-relay-vs-downscoping .ygd-s.ygd-on{opacity:1}
.ygd-token-relay-vs-downscoping .ygd-box{fill:var(--ygd-node-bg);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-token-relay-vs-downscoping .ygd-line{stroke:var(--ygd-arrow);stroke-width:2;fill:none}
.ygd-token-relay-vs-downscoping .ygd-arrowhead{fill:var(--ygd-arrow)}
.ygd-token-relay-vs-downscoping .ygd-t{fill:var(--ygd-fg);font-size:13.5px;font-weight:700}
.ygd-token-relay-vs-downscoping .ygd-sub{fill:var(--ygd-muted);font-size:11.5px}
.ygd-token-relay-vs-downscoping .ygd-chip-r{fill:var(--ygd-chip-bg);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-token-relay-vs-downscoping .ygd-ct{fill:var(--ygd-fg);font-size:11.5px}
.ygd-token-relay-vs-downscoping .ygd-ct0{font-weight:700}
.ygd-token-relay-vs-downscoping .ygd-k-a .ygd-chip-r{stroke:var(--ygd-danger)}
.ygd-token-relay-vs-downscoping .ygd-k-a .ygd-ct0{fill:var(--ygd-danger)}
.ygd-token-relay-vs-downscoping .ygd-k-s .ygd-chip-r{stroke:var(--ygd-accent)}
.ygd-token-relay-vs-downscoping .ygd-k-s .ygd-ct0{fill:var(--ygd-accent)}
.ygd-token-relay-vs-downscoping .ygd-cur .ygd-line{stroke:var(--ygd-accent);stroke-width:3}
.ygd-token-relay-vs-downscoping .ygd-cur .ygd-box{stroke:var(--ygd-accent);stroke-width:2.5}
.ygd-token-relay-vs-downscoping .ygd-bad .ygd-box{fill:var(--ygd-danger-bg);stroke:var(--ygd-danger)}
.ygd-token-relay-vs-downscoping .ygd-bad .ygd-t,.ygd-token-relay-vs-downscoping .ygd-bad .ygd-sub{fill:var(--ygd-danger)}
.ygd-token-relay-vs-downscoping .ygd-good .ygd-box{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok)}
.ygd-token-relay-vs-downscoping .ygd-good .ygd-t,.ygd-token-relay-vs-downscoping .ygd-good .ygd-sub{fill:var(--ygd-ok)}
.ygd-token-relay-vs-downscoping .ygd-pkt{stroke:var(--ygd-bg);stroke-width:1.5}
.ygd-token-relay-vs-downscoping .ygd-pkt.ygd-k-a{fill:var(--ygd-danger)}
.ygd-token-relay-vs-downscoping .ygd-pkt.ygd-k-s{fill:var(--ygd-accent)}
.ygd-token-relay-vs-downscoping .ygd-x{opacity:0;transition:opacity .3s .8s}
.ygd-token-relay-vs-downscoping .ygd-x.ygd-show{opacity:1}
.ygd-token-relay-vs-downscoping .ygd-xc{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok);stroke-width:2}
.ygd-token-relay-vs-downscoping .ygd-xp{stroke:var(--ygd-ok);stroke-width:2.5;fill:none;stroke-linecap:round}
.ygd-token-relay-vs-downscoping .ygd-panel{margin-top:10px;padding:10px 12px;min-height:8.5em;box-sizing:border-box;background:var(--ygd-chip-bg);border-left:4px solid var(--ygd-accent);border-radius:6px}
.ygd-token-relay-vs-downscoping .ygd-step-title{font-size:14px;font-weight:700;color:var(--ygd-accent);margin:0 0 4px 0}
.ygd-token-relay-vs-downscoping .ygd-desc{font-size:15px;line-height:1.6;margin:0;color:var(--ygd-fg)}
.ygd-token-relay-vs-downscoping .ygd-note{margin-top:10px;font-size:14px;line-height:1.6;color:var(--ygd-muted)}
@media (prefers-reduced-motion: reduce){
.ygd-token-relay-vs-downscoping .ygd-s,.ygd-token-relay-vs-downscoping .ygd-x{transition:none}
.ygd-token-relay-vs-downscoping .ygd-pkt{display:none}
}
</style>
<div class="ygd-bar" role="group" aria-label="방식 전환">
<button type="button" class="ygd-btn ygd-mode" data-mode="relay" aria-pressed="true">토큰 그대로 릴레이</button>
<button type="button" class="ygd-btn ygd-mode" data-mode="down" aria-pressed="false">다운스코핑 적용</button>
</div>
<div class="ygd-bar" role="group" aria-label="재생 제어">
<button type="button" class="ygd-btn ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-next">다음 단계</button>
<button type="button" class="ygd-btn ygd-reset">처음으로</button>
</div>
<svg class="ygd-svg" viewBox="0 0 362 400" role="img" aria-label="">
<defs><marker id="ygd-token-relay-vs-downscoping-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-arrowhead" d="M0 0L10 5L0 10z"/></marker></defs>
<g class="ygd-s" data-step="0"><line class="ygd-line" x1="85" y1="52" x2="85" y2="108" marker-end="url(#ygd-token-relay-vs-downscoping-arrow)"/><g class="ygd-chip"><rect class="ygd-chip-r" x="172" y="54" width="180" height="52" rx="6"/><text class="ygd-ct ygd-ct0" x="180" y="0"></text><text class="ygd-ct" x="180" y="0"></text><text class="ygd-ct" x="180" y="0"></text></g></g>
<g class="ygd-s" data-step="1"><line class="ygd-line" x1="85" y1="152" x2="85" y2="208" marker-end="url(#ygd-token-relay-vs-downscoping-arrow)"/><g class="ygd-chip"><rect class="ygd-chip-r" x="172" y="154" width="180" height="52" rx="6"/><text class="ygd-ct ygd-ct0" x="180" y="0"></text><text class="ygd-ct" x="180" y="0"></text><text class="ygd-ct" x="180" y="0"></text></g></g>
<g class="ygd-s" data-step="2"><line class="ygd-line" x1="85" y1="252" x2="85" y2="308" marker-end="url(#ygd-token-relay-vs-downscoping-arrow)"/><g class="ygd-chip"><rect class="ygd-chip-r" x="172" y="254" width="180" height="52" rx="6"/><text class="ygd-ct ygd-ct0" x="180" y="0"></text><text class="ygd-ct" x="180" y="0"></text><text class="ygd-ct" x="180" y="0"></text></g></g>
<g class="ygd-s" data-step="3"><line class="ygd-line" x1="160" y1="330" x2="232" y2="330" marker-end="url(#ygd-token-relay-vs-downscoping-arrow)"/></g>
<g class="ygd-s" data-step="0"><rect class="ygd-box" x="10" y="8" width="150" height="44" rx="8"/><text class="ygd-t" x="85" y="27" text-anchor="middle">Client</text><text class="ygd-sub" x="85" y="43" text-anchor="middle">Admin 권한 보유</text></g>
<g class="ygd-s" data-step="0"><rect class="ygd-box" x="10" y="108" width="150" height="44" rx="8"/><text class="ygd-t" x="85" y="127" text-anchor="middle">API Gateway</text><text class="ygd-sub ygd-gw" x="85" y="143" text-anchor="middle"></text></g>
<g class="ygd-s" data-step="1"><rect class="ygd-box" x="10" y="208" width="150" height="44" rx="8"/><text class="ygd-t" x="85" y="227" text-anchor="middle">Order Service</text><text class="ygd-sub" x="85" y="243" text-anchor="middle">order-service</text></g>
<g class="ygd-s" data-step="2"><rect class="ygd-box" x="10" y="308" width="150" height="44" rx="8"/><text class="ygd-t" x="85" y="327" text-anchor="middle">Payment Service</text><text class="ygd-sub" x="85" y="343" text-anchor="middle">payment-service</text></g>
<g class="ygd-s ygd-admin" data-step="3"><rect class="ygd-box" x="232" y="308" width="120" height="44" rx="8"/><text class="ygd-t" x="292" y="327" text-anchor="middle">Admin API</text><text class="ygd-sub ygd-admin-sub" x="292" y="343" text-anchor="middle">Payment 내부</text></g>
<g class="ygd-s ygd-banner" data-step="3"><rect class="ygd-box" x="10" y="364" width="342" height="28" rx="6"/><text class="ygd-t ygd-banner-t" x="181" y="383" text-anchor="middle" style="font-size:12px"></text></g>
<circle class="ygd-pkt ygd-k-a" cx="0" cy="0" r="6"/>
<g class="ygd-x"><circle class="ygd-xc" cx="196" cy="330" r="10"/><path class="ygd-xp" d="M191 325L201 335M201 325L191 335"/></g>
</svg>
<div class="ygd-panel" aria-live="polite"><div class="ygd-step-title"></div><div class="ygd-desc"></div></div>
<div class="ygd-note">비유: 마스터키를 다른 층 직원에게 그대로 넘기느냐, 그 층만 열리고 곧 만료되는 임시 카드키로 바꿔 주느냐의 차이다. 실제로는 Gateway가 스코프를 줄인 새 JWT를 발급해 교체하는 것이다.</div>
<script>
(function(){
var root=document.getElementById('ygd-token-relay-vs-downscoping');
if(!root){return;}
function q(s){return root.querySelector(s);}
function qa(s){return root.querySelectorAll(s);}
function each(list,fn){Array.prototype.forEach.call(list,fn);}
var TITLES=['Admin 토큰으로 요청','Gateway 통과','Order가 Payment 호출','Payment Admin API 접근'];
var PATHS=[{x1:85,y1:52,x2:85,y2:108},{x1:85,y1:152,x2:85,y2:208},{x1:85,y1:252,x2:85,y2:308},{x1:160,y1:330,x2:232,y2:330}];
var BLOCK_X=196;
var START_DESC='Admin 권한을 가진 사용자가 토큰을 들고 Gateway로 요청을 보낸다. 여기까지는 두 방식이 같다.';
var MODES={
relay:{
gw:'검증 후 그대로 전달',
label:'Client에서 API Gateway, Order Service, Payment Service로 Admin 토큰이 그대로 전달되어 Payment Admin API가 열리는 다이어그램',
chips:[
{k:'a',t:['Admin 토큰','Admin 권한 포함']},
{k:'a',t:['Admin 토큰 (그대로)','스코프 변경 없음']},
{k:'a',t:['Admin 토큰 (그대로)','Admin 권한 포함']}
],
desc:[
START_DESC,
'Gateway는 토큰을 검증한 뒤 스코프를 건드리지 않고 Order Service로 그대로 넘긴다.',
'Order Service가 받은 사용자 토큰을 Payment Service 호출에 그대로 붙인다. 이것이 토큰 릴레이다.',
'같은 토큰으로 Payment의 Admin API를 부르면 토큰에 Admin 권한이 있어 열린다. 의도하지 않은 권한 확대다.'
],
banner:'Admin API 열림: 의도하지 않은 권한 확대',
state:'ygd-bad',
adminSub:'접근 허용'
},
down:{
gw:'스코프 축소·30초 교체',
label:'Client에서 API Gateway, Order Service, Payment Service로 이어지며 Gateway가 서비스별 허용 스코프만 남긴 30초 토큰으로 교체해 Payment Admin API 요청이 거부되는 다이어그램',
chips:[
{k:'a',t:['Admin 토큰','Admin 권한 포함']},
{k:'s',t:['Order 전용 토큰 · 30초','order:read, order:write,','user:read']},
{k:'s',t:['Payment 전용 토큰 · 30초','payment:process,','user:read']}
],
desc:[
START_DESC,
'Gateway가 원본 스코프 중 order-service 허용 목록에 있는 것만 남기고, 만료 30초짜리 새 토큰으로 교체해 전달한다.',
'Payment로 가는 요청도 payment-service 허용 스코프만 남긴 30초 토큰으로 교체된다. Admin 권한은 이미 없다.',
'같은 요청이 Payment의 Admin API에 도달해도 토큰에 Admin 권한이 없어 거부된다. 토큰도 30초 뒤 만료된다.'
],
banner:'Admin API 거부: 토큰에 Admin 권한 없음',
state:'ygd-good',
adminSub:'접근 거부'
}
};
var mode='relay';
var step=0;
var timer=null;
var svg=q('.ygd-svg');
var pkt=q('.ygd-pkt');
var playBtn=q('.ygd-play');
var nextBtn=q('.ygd-next');
function placePacket(animate){
var p=PATHS[step];
var tx=p.x2;
if(mode==='down'&&step===3){tx=BLOCK_X;}
var admin=(mode==='relay'||step===0);
pkt.setAttribute('class','ygd-pkt '+(admin?'ygd-k-a':'ygd-k-s'));
if(animate){
pkt.style.transition='none';
pkt.style.transform='translate('+p.x1+'px,'+p.y1+'px)';
void pkt.getBoundingClientRect();
pkt.style.transition='transform .9s ease-in-out';
}else{
pkt.style.transition='none';
}
pkt.style.transform='translate('+tx+'px,'+p.y2+'px)';
}
function render(animate){
var m=MODES[mode];
each(qa('.ygd-mode'),function(b){
b.setAttribute('aria-pressed',b.getAttribute('data-mode')===mode?'true':'false');
});
svg.setAttribute('aria-label',m.label);
q('.ygd-gw').textContent=m.gw;
var chipEls=qa('.ygd-chip');
for(var i=0;i!==3;i++){
var c=m.chips[i];
var g=chipEls[i];
g.setAttribute('class','ygd-chip ygd-k-'+c.k);
var top=54+100*i;
var texts=g.querySelectorAll('.ygd-ct');
var start=top+(52-c.t.length*14)/2+11;
for(var j=0;j!==3;j++){
if(c.t[j]){
texts[j].textContent=c.t[j];
texts[j].setAttribute('y',String(start+j*14));
}else{
texts[j].textContent='';
}
}
}
each(qa('.ygd-s'),function(el){
var ds=parseInt(el.getAttribute('data-step'),10);
var cls=el.getAttribute('class').replace(/\s*ygd-(on|cur|bad|good)\b/g,'');
if(step>=ds){cls+=' ygd-on';}
if(step===ds){cls+=' ygd-cur';}
if(step>=3&&(el.getAttribute('data-step')==='3')&&(cls.indexOf('ygd-admin')!==-1||cls.indexOf('ygd-banner')!==-1)){cls+=' '+m.state;}
el.setAttribute('class',cls);
});
q('.ygd-admin-sub').textContent=step>=3?m.adminSub:'Payment 내부';
q('.ygd-banner-t').textContent=step>=3?m.banner:'결과: 마지막 단계에서 확인';
var xEl=q('.ygd-x');
xEl.setAttribute('class',(mode==='down'&&step>=3)?'ygd-x ygd-show':'ygd-x');
q('.ygd-step-title').textContent=(step+1)+' / 4 · '+TITLES[step];
q('.ygd-desc').textContent=m.desc[step];
nextBtn.disabled=(step>=3);
placePacket(animate);
}
function stop(){
if(timer!==null){clearInterval(timer);timer=null;}
playBtn.textContent='재생';
}
function tick(){
if(!root.isConnected){stop();return;}
if(step>=3){stop();return;}
step=step+1;
render(true);
if(step>=3){stop();}
}
playBtn.addEventListener('click',function(){
if(timer!==null){stop();return;}
if(step>=3){step=0;render(false);}else{tick();}
if(step<3){
playBtn.textContent='일시정지';
timer=setInterval(tick,2400);
}
});
nextBtn.addEventListener('click',function(){
stop();
if(step<3){step=step+1;render(true);}
});
q('.ygd-reset').addEventListener('click',function(){
stop();
step=0;
render(false);
});
each(qa('.ygd-mode'),function(b){
b.addEventListener('click',function(){
mode=b.getAttribute('data-mode');
render(false);
});
});
render(false);
})();
</script>
</div>

### 해결: 토큰 다운스코핑

Gateway에서 내부 서비스로 요청을 전달할 때, 해당 서비스에 필요한 최소 권한만 담은 토큰으로 교체한다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request, Response, NextFunction } from 'express';

// 서비스별 허용 권한 매핑
const SERVICE_SCOPES: Record<string, Set<string>> = {
  'order-service': new Set(['order:read', 'order:write', 'user:read']),
  'payment-service': new Set(['payment:process', 'user:read']),
  'inventory-service': new Set(['inventory:read']),
};

@Injectable()
export class TokenDownScopingMiddleware implements NestMiddleware {
  constructor(private readonly jwtService: JwtService) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const targetService = this.resolveTargetService(req);
    const allowedScopes = SERVICE_SCOPES[targetService] ?? new Set<string>();

    const auth = (req as Request & { auth?: { userId: string; scopes: string[] } }).auth;
    if (!auth) {
      next();
      return;
    }

    // 원본 토큰의 권한 중 대상 서비스에 허용된 것만 남김
    const originalScopes: string[] = auth.scopes;
    const downScoped = originalScopes.filter((s) => allowedScopes.has(s));

    // 축소된 권한으로 새 토큰 발급
    const scopedToken = this.jwtService.sign(
      {
        sub: auth.userId,
        scopes: downScoped,
        original_scopes: originalScopes, // 디버깅용
      },
      { expiresIn: 30 }, // 짧은 수명
    );

    req.headers['x-scoped-token'] = scopedToken;
    next();
  }

  private resolveTargetService(req: Request): string {
    // URL 경로에서 대상 서비스 이름 추출 (구현에 따라 다를 수 있음)
    return req.headers['x-target-service'] as string ?? '';
  }
}
```

`original_scopes`를 넣는 건 디버깅 용도다. 운영에서 "이 사용자가 원래 어떤 권한이었는데 축소됐는지" 로그로 확인할 때 쓴다. 민감한 환경이면 빼도 된다.

## Gateway와 서비스의 인가 책임 분리

인가(Authorization)를 어디서 처리할지가 MSA에서 가장 논쟁이 많은 부분이다.

### Gateway에서 처리하면 좋은 것

- URL 패턴 기반 접근 제어: `/admin/**`은 ADMIN 역할만 허용
- Rate Limiting: 사용자/API Key별 요청 제한
- IP 화이트리스트/블랙리스트
- 인증 실패 시 일괄 처리 (401, 403)

```yaml
# Spring Cloud Gateway route 설정
spring:
  cloud:
    gateway:
      routes:
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
          filters:
            - name: Auth
            - name: RoleCheck
              args:
                required-role: USER
        - id: admin-service
          uri: lb://admin-service
          predicates:
            - Path=/admin/**
          filters:
            - name: Auth
            - name: RoleCheck
              args:
                required-role: ADMIN
```

### 각 서비스에서 처리해야 하는 것

- 비즈니스 로직에 의존하는 권한 검사: "본인의 주문만 취소 가능", "같은 팀 멤버만 조회 가능"
- 데이터 레벨 접근 제어: 특정 리소스의 소유자인지 확인
- 도메인 규칙에 따른 상태 기반 접근 제어: "배송 시작된 주문은 수정 불가"

```typescript
import { Injectable, NotFoundException, ForbiddenException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Order, OrderStatus } from './order.entity';

@Injectable()
export class OrderService {
  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
  ) {}

  // Gateway가 ROLE_USER는 확인했지만,
  // "이 주문이 이 사용자의 것인지"는 서비스가 확인해야 한다
  async cancelOrder(orderId: string, userId: string): Promise<Order> {
    const order = await this.orderRepository.findOne({ where: { id: orderId } });
    if (!order) {
      throw new NotFoundException('주문을 찾을 수 없음');
    }

    // 본인 주문인지 확인
    if (order.userId !== userId) {
      throw new ForbiddenException('본인의 주문만 취소할 수 있음');
    }

    // 상태 기반 접근 제어
    if (order.status === OrderStatus.SHIPPED) {
      throw new Error('배송이 시작된 주문은 취소할 수 없음');
    }

    order.cancel();
    return this.orderRepository.save(order);
  }
}
```

원칙을 정리하면: **Gateway는 "누가 어떤 종류의 API에 접근할 수 있는지"를 처리하고, 서비스는 "이 사용자가 이 특정 리소스에 대해 이 작업을 할 수 있는지"를 처리한다.**

Gateway에 비즈니스 로직을 넣기 시작하면 Gateway가 모든 서비스의 도메인을 알아야 하는 상황이 된다. 서비스 하나 바뀔 때마다 Gateway도 수정해야 하고, Gateway가 단일 장애점(SPOF)이 될 위험도 커진다.

## NestJS API Gateway + JWT 조합

전체 구조를 코드로 정리한다.

### Gateway 모듈 설정

```typescript
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AuthGatewayMiddleware } from './auth-gateway.middleware';

@Module({
  imports: [
    ConfigModule.forRoot(),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => ({
        secret: configService.get<string>('JWT_SECRET'),
      }),
      inject: [ConfigService],
    }),
  ],
})
export class GatewayModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer
      .apply(AuthGatewayMiddleware)
      .exclude('/api/auth/(.*)', '/health')
      .forRoutes('*');
  }
}
```

### Gateway 글로벌 미들웨어 - 사용자 정보 전파

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request, Response, NextFunction } from 'express';
import { randomUUID } from 'crypto';

@Injectable()
export class UserContextRelayMiddleware implements NestMiddleware {
  constructor(private readonly jwtService: JwtService) {}

  async use(req: Request, res: Response, next: NextFunction): Promise<void> {
    const authHeader = req.headers['authorization'];

    if (authHeader?.startsWith('Bearer ')) {
      const token = authHeader.substring(7);
      try {
        const jwt = await this.jwtService.verifyAsync<{
          sub: string;
          email: string;
          roles: string[];
        }>(token);

        // 외부에서 주입한 내부 헤더 제거 (보안)
        delete req.headers['x-user-id'];
        delete req.headers['x-user-email'];
        delete req.headers['x-user-roles'];

        // 검증된 사용자 정보 설정
        req.headers['x-user-id'] = jwt.sub;
        req.headers['x-user-email'] = jwt.email;
        req.headers['x-user-roles'] = jwt.roles.join(',');
        req.headers['x-request-id'] = randomUUID().substring(0, 8);
      } catch {
        // 인증 실패 시 헤더 제거만 수행
        delete req.headers['x-user-id'];
        delete req.headers['x-user-email'];
        delete req.headers['x-user-roles'];
      }
    }

    next();
  }
}
```

`X-Request-Id`를 여기서 생성하는 이유: 사용자 요청 하나가 내부 서비스 여러 개를 거치는데, 같은 Request ID를 전파하면 분산 로그 추적이 가능하다. 문제 발생 시 이 ID로 관련 로그를 한 번에 검색할 수 있다.

헤더를 먼저 `remove`하고 다시 `header`로 설정하는 순서가 맞나 싶을 수 있다. `mutate().header()`는 추가(add)이고, `headers(h -> h.remove())`가 삭제다. 외부에서 `X-User-Id`를 주입해서 내부 서비스를 속이는 공격을 막으려면, 기존 값을 지우고 Gateway가 검증한 값으로 덮어써야 한다.

### 내부 서비스 Security 설정

```typescript
import { Module, NestModule, MiddlewareConsumer } from '@nestjs/common';
import { InternalAuthMiddleware } from './internal-auth.middleware';

// Gateway가 아닌 내부 서비스용
// JWT 검증은 Gateway가 했으므로 여기서는 하지 않음
@Module({})
export class InternalServiceModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer
      .apply(InternalAuthMiddleware)
      .forRoutes('*');
  }
}
```

### 서비스 간 호출 시 사용자 컨텍스트 전파

Order Service가 Payment Service를 호출할 때, 원래 사용자 정보를 같이 전달해야 한다. Axios(HttpService)를 쓰는 경우:

```typescript
import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ServiceTokenProvider } from './service-token.provider';
import { Request } from 'express';

@Injectable()
export class PaymentServiceClient {
  constructor(
    private readonly httpService: HttpService,
    private readonly serviceTokenProvider: ServiceTokenProvider,
  ) {}

  async chargePayment(
    amount: number,
    req: Request & { internalUser?: { userId: string; roles: string[] } },
  ): Promise<unknown> {
    const userId = req.internalUser?.userId ?? '';
    const roles = req.internalUser?.roles.join(',') ?? '';
    const serviceToken = this.serviceTokenProvider.issueServiceToken('order-service');

    return this.httpService.axiosRef.post(
      'http://payment-service/charge',
      { amount },
      {
        headers: {
          // 사용자 컨텍스트 전파
          'X-User-Id': userId,
          'X-User-Roles': roles,
          // 서비스 인증 토큰 추가
          'X-Service-Auth': `Bearer ${serviceToken}`,
        },
      },
    );
  }
}
```

수신 서비스에서는 `X-Service-Auth`로 호출한 서비스의 신원을 확인하고, `X-User-Id`로 원래 사용자가 누구인지 파악한다. 두 가지 인증이 동시에 필요하다.

<div class="ygd-user-context-propagation-flow" id="ygd-user-context-propagation-flow">
<style>
.ygd-user-context-propagation-flow{--ygd-surface:#F7F5F2;--ygd-node:#FFFFFF;--ygd-border:#C9C3BB;--ygd-text:#2B2724;--ygd-muted:#5E5851;--ygd-accent:#2F6A80;--ygd-on-accent:#FFFFFF;--ygd-warn:#8A5200;--ygd-err:#B3261E;--ygd-edge:#8C867E;--ygd-focus:#1F5FBF;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;border:1px solid var(--ygd-border);border-radius:10px;background:var(--ygd-surface);color:var(--ygd-text);padding:14px;font-size:15px;line-height:1.55;}
body[data-md-color-scheme="slate"] .ygd-user-context-propagation-flow{--ygd-surface:#2B282B;--ygd-node:#343036;--ygd-border:#5B555C;--ygd-text:#F0EDE9;--ygd-muted:#BDB7AF;--ygd-accent:#82C3D8;--ygd-on-accent:#0F2630;--ygd-warn:#F0B861;--ygd-err:#FF9A92;--ygd-edge:#8F898F;--ygd-focus:#8DB8FF;}
.ygd-user-context-propagation-flow *{box-sizing:border-box;}
.ygd-user-context-propagation-flow .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px;}
.ygd-user-context-propagation-flow .ygd-btn{font-family:inherit;font-size:14px;line-height:1.2;min-height:40px;padding:6px 14px;border-radius:8px;border:1px solid var(--ygd-border);background:var(--ygd-node);color:var(--ygd-text);cursor:pointer;margin:0;}
.ygd-user-context-propagation-flow .ygd-btn:hover{border-color:var(--ygd-accent);}
.ygd-user-context-propagation-flow .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px;}
.ygd-user-context-propagation-flow .ygd-btn:disabled{opacity:.5;cursor:default;}
.ygd-user-context-propagation-flow .ygd-btn-main{background:var(--ygd-accent);color:var(--ygd-on-accent);border-color:var(--ygd-accent);font-weight:600;}
.ygd-user-context-propagation-flow .ygd-body{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start;}
.ygd-user-context-propagation-flow .ygd-figure{flex:1 1 300px;min-width:0;max-width:420px;margin:0 auto;}
.ygd-user-context-propagation-flow .ygd-svg{display:block;width:100%;height:auto;}
.ygd-user-context-propagation-flow .ygd-panel{flex:1 1 300px;min-width:0;}
.ygd-user-context-propagation-flow .ygd-step{font-size:14px;color:var(--ygd-muted);}
.ygd-user-context-propagation-flow .ygd-title{font-size:16px;font-weight:700;margin:2px 0 4px;}
.ygd-user-context-propagation-flow .ygd-desc{font-size:15px;margin:0 0 10px;min-height:7.4em;}
.ygd-user-context-propagation-flow .ygd-wire{font-size:14px;color:var(--ygd-muted);margin:0 0 6px;}
.ygd-user-context-propagation-flow .ygd-off{display:none;}
.ygd-user-context-propagation-flow .ygd-hdr{display:grid;gap:6px;margin:0 0 6px;}
.ygd-user-context-propagation-flow .ygd-row{display:grid;grid-template-columns:minmax(0,10.5em) minmax(0,1fr) auto;column-gap:8px;align-items:center;border:1px solid var(--ygd-border);border-left-width:4px;border-radius:6px;padding:5px 8px;background:var(--ygd-node);}
.ygd-user-context-propagation-flow .ygd-row.ygd-chg{border-left-color:var(--ygd-accent);}
.ygd-user-context-propagation-flow .ygd-row.ygd-r-swap{border-left-color:var(--ygd-warn);}
.ygd-user-context-propagation-flow .ygd-row.ygd-r-err{border-left-color:var(--ygd-err);}
.ygd-user-context-propagation-flow .ygd-rn{grid-row:1;grid-column:1;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:14px;font-weight:600;overflow-wrap:anywhere;}
.ygd-user-context-propagation-flow .ygd-val{grid-row:1;grid-column:2;font-size:14px;overflow-wrap:anywhere;}
.ygd-user-context-propagation-flow .ygd-pill{grid-row:1;grid-column:3;font-size:14px;line-height:1.3;padding:0 8px;border-radius:999px;border:1px solid currentColor;white-space:nowrap;}
.ygd-user-context-propagation-flow .ygd-k-new,.ygd-user-context-propagation-flow .ygd-k-add,.ygd-user-context-propagation-flow .ygd-k-inc{color:var(--ygd-accent);}
.ygd-user-context-propagation-flow .ygd-k-swap{color:var(--ygd-warn);}
.ygd-user-context-propagation-flow .ygd-k-keep,.ygd-user-context-propagation-flow .ygd-k-none{color:var(--ygd-muted);}
.ygd-user-context-propagation-flow .ygd-k-err{color:var(--ygd-err);font-weight:700;}
@media (max-width:520px){.ygd-user-context-propagation-flow .ygd-rn{grid-column:1;}.ygd-user-context-propagation-flow .ygd-pill{grid-column:2;}.ygd-user-context-propagation-flow .ygd-val{grid-row:2;grid-column:1 / -1;}}
.ygd-user-context-propagation-flow .ygd-note{font-size:14px;color:var(--ygd-muted);margin:0;}
.ygd-user-context-propagation-flow .ygd-log{border:1px solid var(--ygd-border);border-radius:6px;background:var(--ygd-node);padding:8px 10px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:14px;}
.ygd-user-context-propagation-flow .ygd-logline{margin:0 0 6px;overflow-wrap:anywhere;}
.ygd-user-context-propagation-flow .ygd-logline:last-child{margin-bottom:0;}
.ygd-user-context-propagation-flow .ygd-rid{background:var(--ygd-accent);color:var(--ygd-on-accent);border-radius:4px;padding:0 3px;}
.ygd-user-context-propagation-flow .ygd-analogy{font-size:14px;margin:12px 0 0;padding-top:10px;border-top:1px solid var(--ygd-border);}
.ygd-user-context-propagation-flow .ygd-node{opacity:.65;transition:opacity .25s;}
.ygd-user-context-propagation-flow .ygd-node.ygd-act{opacity:1;}
.ygd-user-context-propagation-flow .ygd-node-box{fill:var(--ygd-node);stroke:var(--ygd-border);stroke-width:1.5;}
.ygd-user-context-propagation-flow .ygd-node.ygd-act .ygd-node-box{stroke:var(--ygd-accent);stroke-width:2.5;}
.ygd-user-context-propagation-flow .ygd-node.ygd-bad .ygd-node-box{stroke:var(--ygd-err);}
.ygd-user-context-propagation-flow .ygd-nm{fill:var(--ygd-text);font-size:12px;font-weight:600;}
.ygd-user-context-propagation-flow .ygd-sb{fill:var(--ygd-muted);font-size:11px;}
.ygd-user-context-propagation-flow .ygd-edge{opacity:.75;transition:opacity .25s;}
.ygd-user-context-propagation-flow .ygd-edge.ygd-act{opacity:1;}
.ygd-user-context-propagation-flow .ygd-edge line,.ygd-user-context-propagation-flow .ygd-edge path{stroke:var(--ygd-edge);stroke-width:2;fill:none;}
.ygd-user-context-propagation-flow .ygd-edge polygon{fill:var(--ygd-edge);}
.ygd-user-context-propagation-flow .ygd-edge text{fill:var(--ygd-muted);font-size:11px;}
.ygd-user-context-propagation-flow .ygd-edge.ygd-act line,.ygd-user-context-propagation-flow .ygd-edge.ygd-act path{stroke:var(--ygd-accent);}
.ygd-user-context-propagation-flow .ygd-edge.ygd-act polygon{fill:var(--ygd-accent);}
.ygd-user-context-propagation-flow .ygd-edge.ygd-act text{fill:var(--ygd-text);}
.ygd-user-context-propagation-flow .ygd-loop path{stroke-dasharray:5 4;}
.ygd-user-context-propagation-flow .ygd-bdg{opacity:0;transition:opacity .25s;}
.ygd-user-context-propagation-flow .ygd-bdg.ygd-on{opacity:1;}
.ygd-user-context-propagation-flow .ygd-bdg rect{fill:var(--ygd-node);stroke:var(--ygd-accent);stroke-width:1.5;}
.ygd-user-context-propagation-flow .ygd-bdg text{fill:var(--ygd-text);font-size:11px;}
.ygd-user-context-propagation-flow .ygd-hopb rect{stroke:var(--ygd-warn);}
.ygd-user-context-propagation-flow .ygd-bdg.ygd-glow rect{fill:var(--ygd-accent);}
.ygd-user-context-propagation-flow .ygd-bdg.ygd-glow text{fill:var(--ygd-on-accent);}
.ygd-user-context-propagation-flow .ygd-bdg.ygd-berr rect{stroke:var(--ygd-err);stroke-width:2;}
.ygd-user-context-propagation-flow .ygd-bdg.ygd-berr text{fill:var(--ygd-err);font-weight:700;}
.ygd-user-context-propagation-flow .ygd-pkt{transition:transform .28s linear;}
.ygd-user-context-propagation-flow .ygd-pkt circle{fill:var(--ygd-accent);stroke:var(--ygd-surface);stroke-width:2;}
.ygd-user-context-propagation-flow .ygd-pkt.ygd-bad circle{fill:var(--ygd-err);}
@media (prefers-reduced-motion:reduce){.ygd-user-context-propagation-flow .ygd-pkt,.ygd-user-context-propagation-flow .ygd-node,.ygd-user-context-propagation-flow .ygd-edge,.ygd-user-context-propagation-flow .ygd-bdg{transition:none;}}
</style>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-btn-main" data-ygd="play" aria-label="재생 또는 일시정지">재생</button>
<button type="button" class="ygd-btn" data-ygd="prev" aria-label="이전 단계">이전</button>
<button type="button" class="ygd-btn" data-ygd="next" aria-label="다음 단계">다음</button>
<button type="button" class="ygd-btn" data-ygd="reset" aria-label="처음으로 되돌리기">처음으로</button>
</div>
<div class="ygd-body">
<div class="ygd-figure">
<svg class="ygd-svg" viewBox="0 0 340 372" role="img" aria-label="Client에서 Gateway, Order Service, Payment Service, Inventory Service로 이어지는 요청 경로. 각 구간에서 X-User-Id, X-User-Roles, X-Request-Id, X-Service-Auth, X-Hop-Count 헤더가 붙거나 바뀌는 모습과, Inventory에서 Order로 되돌아가는 순환 호출이 Hop Count 5에서 508로 끊기는 분기를 보여준다.">
<g class="ygd-edge" data-e="0"><line x1="72" y1="52" x2="72" y2="78"/><polygon points="68,78 76,78 72,86"/><text x="84" y="73">Authorization: Bearer JWT</text></g>
<g class="ygd-edge" data-e="1"><line x1="72" y1="130" x2="72" y2="156"/><polygon points="68,156 76,156 72,164"/><text x="84" y="151">X-User-Id, Roles, Request-Id</text></g>
<g class="ygd-edge" data-e="2"><line x1="72" y1="208" x2="72" y2="234"/><polygon points="68,234 76,234 72,242"/><text x="84" y="229">+ X-Service-Auth, X-Hop-Count</text></g>
<g class="ygd-edge" data-e="3"><line x1="72" y1="286" x2="72" y2="312"/><polygon points="68,312 76,312 72,320"/><text x="84" y="307">X-Service-Auth 교체, Hop +1</text></g>
<g class="ygd-edge ygd-loop" data-e="loop"><path d="M60 342 H30 V186 H52"/><polygon points="52,182 52,190 60,186"/><text x="17" y="264" text-anchor="middle" transform="rotate(-90 17 264)">순환 호출</text></g>
<g class="ygd-node" data-n="0"><rect class="ygd-node-box" x="60" y="8" width="156" height="44" rx="8"/><text class="ygd-nm" x="84" y="27">Client</text><text class="ygd-sb" x="84" y="43">사용자 요청</text></g>
<g class="ygd-node" data-n="1"><rect class="ygd-node-box" x="60" y="86" width="156" height="44" rx="8"/><text class="ygd-nm" x="84" y="105">Gateway</text><text class="ygd-sb" x="84" y="121">JWT 검증</text></g>
<g class="ygd-node" data-n="2"><rect class="ygd-node-box" x="60" y="164" width="156" height="44" rx="8"/><text class="ygd-nm" x="84" y="183">Order Service</text><text class="ygd-sb" x="84" y="199">주문</text></g>
<g class="ygd-node" data-n="3"><rect class="ygd-node-box" x="60" y="242" width="156" height="44" rx="8"/><text class="ygd-nm" x="84" y="261">Payment Service</text><text class="ygd-sb" x="84" y="277">결제</text></g>
<g class="ygd-node" data-n="4"><rect class="ygd-node-box" x="60" y="320" width="156" height="44" rx="8"/><text class="ygd-nm" x="84" y="339">Inventory Service</text><text class="ygd-sb" x="84" y="355">재고</text></g>
<g class="ygd-bdg ygd-idb" data-n="1"><rect x="226" y="109" width="104" height="17" rx="8.5"/><text x="278" y="121.5" text-anchor="middle">ID a1b2c3d4</text></g>
<g class="ygd-bdg ygd-hopb" data-n="2"><rect x="226" y="168" width="104" height="17" rx="8.5"/><text x="278" y="180.5" text-anchor="middle"></text></g>
<g class="ygd-bdg ygd-idb" data-n="2"><rect x="226" y="187" width="104" height="17" rx="8.5"/><text x="278" y="199.5" text-anchor="middle">ID a1b2c3d4</text></g>
<g class="ygd-bdg ygd-hopb" data-n="3"><rect x="226" y="246" width="104" height="17" rx="8.5"/><text x="278" y="258.5" text-anchor="middle"></text></g>
<g class="ygd-bdg ygd-idb" data-n="3"><rect x="226" y="265" width="104" height="17" rx="8.5"/><text x="278" y="277.5" text-anchor="middle">ID a1b2c3d4</text></g>
<g class="ygd-bdg ygd-hopb" data-n="4"><rect x="226" y="324" width="104" height="17" rx="8.5"/><text x="278" y="336.5" text-anchor="middle"></text></g>
<g class="ygd-bdg ygd-idb" data-n="4"><rect x="226" y="343" width="104" height="17" rx="8.5"/><text x="278" y="355.5" text-anchor="middle">ID a1b2c3d4</text></g>
<g class="ygd-pkt" data-ygd="pkt"><circle r="6" cx="0" cy="0"/></g>
</svg>
</div>
<div class="ygd-panel">
<div aria-live="polite">
<div class="ygd-step" data-ygd="step"></div>
<div class="ygd-title" data-ygd="title"></div>
<p class="ygd-desc" data-ygd="desc"></p>
</div>
<div data-ygd="hdrbox">
<p class="ygd-wire" data-ygd="wire"></p>
<div class="ygd-hdr" data-ygd="rows"></div>
<p class="ygd-note">X-Hop-Count의 화살표는 수신한 값 → 미들웨어가 올린 값이다.</p>
</div>
<div class="ygd-log ygd-off" data-ygd="logbox">
<div class="ygd-logline">14:23:01 <span class="ygd-rid">[a1b2c3d4]</span> [user-123] [order-service] 주문 생성 요청</div>
<div class="ygd-logline">14:23:01 <span class="ygd-rid">[a1b2c3d4]</span> [user-123] [payment-service] 결제 처리 시작</div>
<div class="ygd-logline">14:23:02 <span class="ygd-rid">[a1b2c3d4]</span> [user-123] [inventory-service] 재고 차감</div>
</div>
</div>
</div>
<p class="ygd-analogy">비유: Gateway는 신분증(JWT)을 확인하고 방문증(내부 헤더)을 발급하는 안내 데스크이고, 방문증은 부서(서비스)를 옮겨 다녀도 그대로 따라간다. 다만 방문증과 달리 이 헤더는 서명되지 않은 평문이라, 내부 서비스는 네트워크 수준에서 Gateway 외의 직접 접근을 막아야 한다.</p>
<script>
(function () {
  var root = document.getElementById("ygd-user-context-propagation-flow");
  if (!root) { return; }
  function q(s) { return root.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(root.querySelectorAll(s)); }
  function reduced() { return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches); }
  var KIND = { "new": "신규", keep: "유지", add: "추가", swap: "교체", inc: "+1", none: "없음", err: "508" };
  var NAMES = ["X-User-Id", "X-User-Roles", "X-Request-Id", "X-Service-Auth", "X-Hop-Count"];
  function r(v, k) { return { v: v, k: k }; }
  function keep3() { return [r("user-123", "keep"), r("USER", "keep"), r("a1b2c3d4", "keep")]; }
  var steps = [
    { t: "Client가 Gateway로 요청을 보낸다", wire: "Client → Gateway (Authorization: Bearer JWT만 전송)",
      d: "Client는 Access Token(JWT)을 Authorization 헤더에 담아 보낸다. 내부용 헤더 5개는 아직 하나도 없고, 외부에서 X-User-Id 같은 값을 임의로 넣어 보내도 Gateway가 다음 단계에서 지운다.",
      rows: [r("—", "none"), r("—", "none"), r("—", "none"), r("—", "none"), r("—", "none")],
      nodes: [0, 1], edge: 0, from: [72, 52], pkt: [[72, 86]] },
    { t: "Gateway가 헤더를 새로 쓴다", wire: "Gateway 내부 처리 후",
      d: "JWT 서명을 검증한 뒤, 외부에서 들어온 x-user-id와 x-user-roles를 먼저 삭제하고 검증된 값으로 다시 설정한다. X-Request-Id는 이 지점에서 처음 생성한다.",
      rows: [r("user-123", "new"), r("USER", "new"), r("a1b2c3d4", "new"), r("—", "none"), r("—", "none")],
      nodes: [1], edge: -1, pkt: [[72, 130]], ids: [1] },
    { t: "Order Service가 사용자 컨텍스트를 받는다", wire: "Gateway → Order Service",
      d: "Order는 Gateway가 넣어 준 X-User-Id와 X-User-Roles로 사용자를 파악한다. HopCountMiddleware는 X-Hop-Count가 없으면 0으로 보고 1로 올린다.",
      rows: keep3().concat([r("—", "none"), r("없음 → 1", "inc")]),
      nodes: [2], edge: 1, pkt: [[72, 164]], ids: [2], hop: { 2: "Hop 0 → 1" } },
    { t: "Order가 Payment를 호출한다", wire: "Order Service → Payment Service",
      d: "호출 코드가 X-User-Id와 X-User-Roles를 그대로 옮기고, order-service 신원의 서비스 토큰을 X-Service-Auth에 추가한다. Payment는 서비스 토큰으로 호출자를, X-User-Id로 원래 사용자를 확인한다. Hop은 받은 1이 5 미만이라 통과하고 2로 올라간다.",
      rows: keep3().concat([r("Bearer (order-service 토큰)", "add"), r("1 → 2", "inc")]),
      nodes: [3], edge: 2, pkt: [[72, 242]], ids: [3], hop: { 3: "Hop 1 → 2" } },
    { t: "Payment가 Inventory를 호출한다", wire: "Payment Service → Inventory Service",
      d: "호출하는 서비스가 바뀌었으므로 X-Service-Auth는 payment-service 신원의 토큰으로 교체된다. 사용자 컨텍스트와 X-Request-Id는 처음 값 그대로 따라가고, Hop은 2에서 3이 된다.",
      rows: keep3().concat([r("Bearer (payment-service 토큰)", "swap"), r("2 → 3", "inc")]),
      nodes: [4], edge: 3, pkt: [[72, 320]], ids: [4], hop: { 4: "Hop 2 → 3" } },
    { t: "같은 requestId로 로그가 이어진다", wire: "각 서비스의 로그", log: true,
      d: "각 서비스의 LogContextMiddleware가 requestId와 userId를 로그에 심는다. a1b2c3d4로 검색하면 세 서비스를 거친 흐름을 한 번에 추적할 수 있다.",
      rows: [], nodes: [1, 2, 3, 4], edge: -1, pkt: [[72, 320]], glow: true },
    { t: "분기: Inventory가 Order를 다시 호출한다", wire: "Inventory Service → Order Service",
      d: "A → B → C → A 같은 순환 호출이 생기면 사용자 컨텍스트를 단 채 계속 돈다. 호출할 때마다 X-Hop-Count가 올라가므로, 이번에는 Order가 3을 받아 4로 올린다.",
      rows: keep3().concat([r("Bearer (inventory-service 토큰)", "swap"), r("3 → 4", "inc")]),
      nodes: [2], edge: "loop", pkt: [[72, 342], [30, 342], [30, 186], [60, 186]], hop: { 2: "Hop 3 → 4" } },
    { t: "순환이 한 바퀴 더 돈다", wire: "Order Service → Payment Service",
      d: "Payment는 받은 값 4가 5 미만이라 통과시키고 5로 올린다. 이 요청은 다음 호출에서 한계에 닿는다.",
      rows: keep3().concat([r("Bearer (order-service 토큰)", "swap"), r("4 → 5", "inc")]),
      nodes: [3], edge: 2, pkt: [[72, 186], [72, 242]], hop: { 3: "Hop 4 → 5" } },
    { t: "Hop Count가 5에 닿아 508로 끊긴다", wire: "Payment Service → Inventory Service",
      d: "Inventory는 받은 값 5가 MAX_HOPS(5) 이상이라 next를 호출하지 않고 508과 서비스 호출 깊이 초과를 응답한다. 순환 호출은 설계 문제이고, 이 헤더는 방어용 안전장치일 뿐이다.",
      rows: keep3().concat([r("Bearer (payment-service 토큰)", "swap"), r("5 → 거부", "err")]),
      nodes: [4], edge: 3, bad: 4, pkt: [[72, 320]], hop: { 4: "Hop 5 → 508" } }
  ];
  var last = steps.length - 1, idx = 0, playing = false, tm = null, mv = [];
  var pkt = q('[data-ygd="pkt"]');
  var nodeEls = qa(".ygd-node"), edgeEls = qa(".ygd-edge");
  var rowsBox = q('[data-ygd="rows"]'), rowEls = [];
  NAMES.forEach(function (n) {
    var row = document.createElement("div"); row.className = "ygd-row";
    var a = document.createElement("span"); a.className = "ygd-rn"; a.textContent = n;
    var b = document.createElement("span"); b.className = "ygd-val";
    var c = document.createElement("span"); c.className = "ygd-pill";
    row.appendChild(a); row.appendChild(b); row.appendChild(c); rowsBox.appendChild(row);
    rowEls.push({ row: row, val: b, pill: c });
  });
  var playBtn = q('[data-ygd="play"]'), prevBtn = q('[data-ygd="prev"]'), nextBtn = q('[data-ygd="next"]');
  function place(p) { pkt.style.transform = "translate(" + p[0] + "px," + p[1] + "px)"; }
  function move(s, animate) {
    while (mv.length) { clearTimeout(mv.pop()); }
    var pts = s.pkt, k = 0;
    if (!animate || reduced()) { place(pts[pts.length - 1]); return; }
    if (s.from) {
      pkt.style.transition = "none"; place(s.from); void pkt.getBoundingClientRect(); pkt.style.transition = "";
    }
    (function go() {
      place(pts[k]); k++;
      if (k < pts.length) { mv.push(setTimeout(go, 300)); }
    })();
  }
  function label() {
    playBtn.textContent = playing ? "일시정지" : (idx === last ? "다시 재생" : (idx === 0 ? "재생" : "이어서 재생"));
  }
  function show(i, animate) {
    idx = i;
    var s = steps[i], bad = (s.bad === undefined ? -1 : s.bad), ids = {}, hops = {}, j;
    nodeEls.forEach(function (el, k) {
      el.classList.toggle("ygd-act", s.nodes.indexOf(k) !== -1);
      el.classList.toggle("ygd-bad", bad === k);
    });
    edgeEls.forEach(function (el) { el.classList.toggle("ygd-act", String(s.edge) === el.getAttribute("data-e")); });
    for (j = 0; j <= i; j++) {
      (steps[j].ids || []).forEach(function (n) { ids[n] = true; });
      if (steps[j].hop) { Object.keys(steps[j].hop).forEach(function (n) { hops[n] = steps[j].hop[n]; }); }
    }
    qa(".ygd-idb").forEach(function (el) {
      el.classList.toggle("ygd-on", !!ids[el.getAttribute("data-n")]);
      el.classList.toggle("ygd-glow", !!s.glow);
    });
    qa(".ygd-hopb").forEach(function (el) {
      var n = el.getAttribute("data-n");
      el.classList.toggle("ygd-on", !!hops[n]);
      el.classList.toggle("ygd-berr", bad === Number(n));
      el.querySelector("text").textContent = hops[n] || "";
    });
    pkt.classList.toggle("ygd-bad", bad !== -1);
    move(s, animate);
    q('[data-ygd="step"]').textContent = "단계 " + (i + 1) + " / " + steps.length;
    q('[data-ygd="title"]').textContent = s.t;
    q('[data-ygd="desc"]').textContent = s.d;
    q('[data-ygd="wire"]').textContent = "구간: " + s.wire;
    q('[data-ygd="hdrbox"]').classList.toggle("ygd-off", !!s.log);
    q('[data-ygd="logbox"]').classList.toggle("ygd-off", !s.log);
    s.rows.forEach(function (rw, k) {
      var e = rowEls[k], changed = rw.k !== "keep" && rw.k !== "none";
      e.val.textContent = rw.v;
      e.pill.textContent = KIND[rw.k];
      e.pill.className = "ygd-pill ygd-k-" + rw.k;
      e.row.className = "ygd-row" + (changed ? " ygd-chg" : "") + (rw.k === "swap" ? " ygd-r-swap" : "") + (rw.k === "err" ? " ygd-r-err" : "");
    });
    prevBtn.disabled = (i === 0);
    nextBtn.disabled = (i === last);
    label();
  }
  function pause() { playing = false; clearTimeout(tm); label(); }
  function schedule() {
    clearTimeout(tm);
    tm = setTimeout(function () {
      show(idx + 1, true);
      if (idx === last) { pause(); } else { schedule(); }
    }, 3800);
  }
  playBtn.addEventListener("click", function () {
    if (playing) { pause(); return; }
    if (idx === last) { show(0, true); } else if (idx === 0) { show(0, true); }
    playing = true; label(); schedule();
  });
  prevBtn.addEventListener("click", function () { pause(); if (idx > 0) { show(idx - 1, false); } });
  nextBtn.addEventListener("click", function () { pause(); if (idx < last) { show(idx + 1, true); } });
  q('[data-ygd="reset"]').addEventListener("click", function () { pause(); show(0, false); });
  show(0, false);
})();
</script>
</div>

## 실무에서 자주 겪는 문제

### 토큰 만료 타이밍

서비스 A가 서비스 B를 호출하는 시점에 토큰이 만료되는 경우가 있다. Access Token 유효시간이 15분인데, Gateway에서 검증한 시점과 내부 서비스에서 사용하는 시점 사이에 1-2초 차이가 나면서 만료되는 거다.

내부 전파용 토큰은 Gateway가 발급하고 수명을 짧게(30초~1분) 잡되, 외부 토큰 만료와는 독립적으로 관리한다.

### Gateway 장애 시 인증 불가

Gateway가 죽으면 모든 인증이 멈춘다. Gateway는 최소 2개 이상의 인스턴스를 띄우고, 로드밸런서 뒤에 두어야 한다. Gateway의 토큰 검증은 가능하면 인증 서버 호출 없이 로컬에서 처리한다(JWT 서명 검증). JWKS(공개키 세트)를 캐시해두면 인증 서버가 잠깐 죽어도 기존 키로 검증이 가능하다.

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: https://auth.example.com/.well-known/jwks.json
          # JWK 캐시 설정 - NimbusJwtDecoder가 기본적으로 캐시하지만
          # 캐시 기간을 직접 제어하려면 커스텀 JwtDecoder를 빈으로 등록
```

### 서비스 간 순환 호출과 토큰 전파

A → B → C → A 같은 순환 호출이 발생하면, 토큰 전파가 무한 루프에 빠질 수 있다. 순환 호출 자체가 설계 문제이지만, 방어 차원에서 `X-Hop-Count` 같은 헤더를 두고 일정 횟수 이상이면 요청을 거부하는 방법이 있다.

```typescript
import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class HopCountMiddleware implements NestMiddleware {
  private static readonly MAX_HOPS = 5;

  use(req: Request, res: Response, next: NextFunction): void {
    const hopHeader = req.headers['x-hop-count'] as string | undefined;
    const hopCount = hopHeader != null ? parseInt(hopHeader, 10) : 0;

    if (hopCount >= HopCountMiddleware.MAX_HOPS) {
      res.status(508).json({ message: '서비스 호출 깊이 초과' });
      return;
    }

    // 다음 서비스 호출 시 hop count 증가
    req.headers['x-hop-count'] = String(hopCount + 1);
    next();
  }
}
```

### 로그에 사용자 컨텍스트 남기기

분산 환경에서 문제 추적 시 "어떤 사용자의 요청이 어떤 서비스를 거쳤는지" 로그로 남겨야 한다. MDC(Mapped Diagnostic Context)를 쓴다.

```typescript
import { Injectable, NestMiddleware, Logger } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LogContextMiddleware implements NestMiddleware {
  private readonly logger = new Logger('order-service');

  use(req: Request, res: Response, next: NextFunction): void {
    const userId = req.headers['x-user-id'] as string | undefined;
    const requestId = req.headers['x-request-id'] as string | undefined;

    // NestJS Logger에 컨텍스트를 심어서 요청 추적
    (req as Request & { logContext: Record<string, string | undefined> }).logContext = {
      userId,
      requestId,
      service: 'order-service',
    };

    // 예: Logger.log(`[${requestId}] [${userId}] [order-service] 요청 처리`);
    this.logger.log(`[${requestId}] [${userId}] [order-service] ${req.method} ${req.path}`);
    next();
  }
}
```

```typescript
// winston 또는 pino 사용 시 로그 포맷 예시
// {timestamp} [{requestId}] [{userId}] [{service}] {message}
// 14:23:01 [a1b2c3d4] [user-123] [order-service] 주문 생성 요청
```

이렇게 하면 로그가 이렇게 찍힌다:

```
14:23:01 [a1b2c3d4] [user-123] [order-service] 주문 생성 요청
14:23:01 [a1b2c3d4] [user-123] [payment-service] 결제 처리 시작
14:23:02 [a1b2c3d4] [user-123] [inventory-service] 재고 차감
```

같은 `requestId`로 전체 흐름을 추적할 수 있다.

## 참고

- [인증/인가 방식 비교](Authentication_Strategy.md) — 단일 서비스 기준 인증 방식
- [RBAC/ABAC](RBAC_ABAC.md) — 역할/속성 기반 접근 제어
- [API 인증/인가 실무 패턴](../API/API_Security_Patterns.md)

---
이 문서는 [인증과 토큰 허브](../../_hub/인증과_토큰.md)의 일부입니다.
