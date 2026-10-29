---
title: ALB → ECS → S3 요청 흐름 (DNS부터 S3 업로드까지)
tags: [aws, vpc, network, cloud]
updated: 2026-10-29
---

# ALB → ECS → S3 요청 흐름 (DNS부터 S3 업로드까지)

브라우저에서 `https://api.example.com/upload`로 파일을 던지면 그 패킷이 ECS 컨테이너에 닿고, 컨테이너가 S3에 putObject를 호출하기까지 어떤 일이 벌어지는지 6단계로 끊어서 본다. 단계마다 실제 운영하면서 밟았던 지뢰를 끼워 넣어 두었다.

전체 흐름은 이렇다.

```
  사용자 브라우저
        |
        |  (1) Route 53 조회 → api.example.com → ALB DNS 이름 → 다중 A 레코드
        |
        v
    인터넷
        |
        |  (2) TCP/443 패킷이 ALB Public IP로
        |
        v
   [Internet Gateway]
        |
        |  (3) Public Subnet의 ENI(ALB)로 라우팅
        |
        v
   [ALB — 퍼블릭 서브넷, AZ-a / AZ-c]
        |
        |  (4) 리스너 규칙 평가 → 매칭 target group 선택
        |
        v
   [ECS Task ENI — 프라이빗 서브넷, awsvpc 모드]
        |
        |  (5) 컨테이너가 요청 처리 → multipart upload 시작
        |
        v
   [S3 — putObject 아웃바운드]
        (6) NAT Gateway 경로 또는 S3 Gateway Endpoint 경로 중 하나
```

이 그림은 정상적인 경로다. 실무에서 패킷이 막히면 (1)~(6) 중 어느 단계인지 좁히는 게 디버깅의 절반이다.

---

## STEP 1. DNS 조회 — `api.example.com`에서 ALB IP를 얻기까지

### Route 53 hosted zone에서 일어나는 일

브라우저가 `api.example.com`을 입력받으면 로컬 리졸버 → ISP DNS → 권한 있는 네임서버 순으로 거슬러 올라간다. 도메인이 Route 53 hosted zone에 등록되어 있다면 권한 네임서버는 AWS의 `ns-XXX.awsdns-XX.com` 같은 4개 NS다. 등록자(레지스트라)의 NS 설정이 Route 53 NS를 가리키지 않으면 hosted zone에 아무리 레코드를 박아도 의미가 없다. 외주에서 받은 도메인을 Route 53에 옮길 때 NS 변경을 빠뜨려서 반나절 헤매는 사례가 흔하다.

ALB를 가리키는 레코드는 보통 alias 레코드로 잡는다.

```hcl
resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.example.com"
  type    = "A"

  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}
```

alias는 Route 53이 ALB의 DNS 이름(`internal-api-1234.ap-northeast-2.elb.amazonaws.com`)을 조회 시점에 A 레코드 묶음으로 풀어준다. CNAME과 다르게 zone apex(`example.com` 같은 루트 도메인)에도 쓸 수 있고, 추가 조회 한 단계가 사라져 응답이 빠르다.

### ALB DNS는 왜 IP가 여러 개인가

ALB의 DNS 이름을 dig으로 찍어 보면 A 레코드가 보통 AZ 수만큼 나온다.

```bash
$ dig +short internal-api-1234.ap-northeast-2.elb.amazonaws.com
10.0.11.42
10.0.12.118
```

ALB는 각 가용 영역마다 자체 ENI를 하나씩 들고 있다. 클라이언트는 그중 하나의 IP로 TCP 연결을 맺는다. 어느 IP에 연결되든 같은 리스너 규칙이 평가되니까 동작은 동일하다.

여기서 자주 밟는 지뢰가 TTL이다. ALB의 DNS TTL은 60초다. 스케일링이나 AZ 장애로 ALB가 새 ENI를 띄우면 60초 안에 클라이언트 캐시가 갈린다. 그런데 일부 SDK나 JVM 기본값은 TTL을 무시하고 무한 캐시한다(JVM의 `networkaddress.cache.ttl`이 기본 -1이라 영원히 캐싱). ALB IP가 바뀐 뒤에도 옛 IP로 계속 때리다가 `connection refused`나 타임아웃이 난다. JVM 기반 클라이언트는 반드시 TTL을 30~60초로 명시해야 한다.

```bash
# JVM 옵션
-Dsun.net.inetaddr.ttl=60
-Dsun.net.inetaddr.negative.ttl=10
```

<div class="ygd-alb-dns-ttl-cache-timeline" id="ygd-alb-dns-ttl-cache-timeline">
<style>
.ygd-alb-dns-ttl-cache-timeline{--ygd-bg:rgb(251,250,248);--ygd-text:rgb(38,35,32);--ygd-muted:rgb(95,90,84);--ygd-line:rgb(120,114,106);--ygd-old-bg:rgb(234,230,225);--ygd-old-bd:rgb(125,118,110);--ygd-ok-bg:rgb(214,236,223);--ygd-ok-bd:rgb(38,120,72);--ygd-ok:rgb(28,110,62);--ygd-bad-bg:rgb(248,219,215);--ygd-bad-bd:rgb(176,52,40);--ygd-bad:rgb(168,45,34);--ygd-accent:rgb(61,115,135);--ygd-panel:rgb(243,240,236);--ygd-btn-text:rgb(255,255,255);--ygd-focus:rgb(61,115,135);max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:12px;border:1px solid var(--ygd-line);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-text);overflow:hidden}
body[data-md-color-scheme="slate"] .ygd-alb-dns-ttl-cache-timeline{--ygd-bg:rgb(31,28,30);--ygd-text:rgb(240,237,233);--ygd-muted:rgb(180,174,166);--ygd-line:rgb(150,144,136);--ygd-old-bg:rgb(58,54,56);--ygd-old-bd:rgb(150,144,136);--ygd-ok-bg:rgb(30,66,46);--ygd-ok-bd:rgb(110,200,145);--ygd-ok:rgb(125,212,160);--ygd-bad-bg:rgb(84,38,36);--ygd-bad-bd:rgb(255,140,130);--ygd-bad:rgb(255,150,140);--ygd-accent:rgb(130,190,210);--ygd-panel:rgb(45,41,43);--ygd-btn-text:rgb(20,20,20);--ygd-focus:rgb(255,200,100)}
.ygd-alb-dns-ttl-cache-timeline .ygd-svg{display:block;width:100%;height:auto}
.ygd-alb-dns-ttl-cache-timeline .ygd-t{fill:var(--ygd-text);font-size:12px;font-family:inherit}
.ygd-alb-dns-ttl-cache-timeline .ygd-t-lane{font-size:13px;font-weight:700}
.ygd-alb-dns-ttl-cache-timeline .ygd-t-m{fill:var(--ygd-muted)}
.ygd-alb-dns-ttl-cache-timeline .ygd-t-bad{fill:var(--ygd-bad)}
.ygd-alb-dns-ttl-cache-timeline .ygd-t-ok{fill:var(--ygd-ok)}
.ygd-alb-dns-ttl-cache-timeline .ygd-axis{stroke:var(--ygd-line);stroke-width:1.5;fill:none}
.ygd-alb-dns-ttl-cache-timeline .ygd-arrow-head{fill:var(--ygd-line)}
.ygd-alb-dns-ttl-cache-timeline .ygd-dot{fill:var(--ygd-accent);stroke:var(--ygd-bg);stroke-width:1.5}
.ygd-alb-dns-ttl-cache-timeline .ygd-head{fill:var(--ygd-accent);transition:transform .5s ease}
.ygd-alb-dns-ttl-cache-timeline .ygd-el{opacity:.45;transition:opacity .4s ease}
.ygd-alb-dns-ttl-cache-timeline .ygd-el.ygd-on{opacity:1}
.ygd-alb-dns-ttl-cache-timeline .ygd-seg{fill:var(--ygd-old-bg);stroke:var(--ygd-old-bd);stroke-width:1.5;transition:fill .4s ease,stroke .4s ease}
.ygd-alb-dns-ttl-cache-timeline .ygd-seg-ok{fill:var(--ygd-ok-bg);stroke:var(--ygd-ok-bd)}
.ygd-alb-dns-ttl-cache-timeline .ygd-alt .ygd-seg{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad-bd)}
.ygd-alb-dns-ttl-cache-timeline .ygd-g{fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.ygd-alb-dns-ttl-cache-timeline .ygd-g-ok{stroke:var(--ygd-ok)}
.ygd-alb-dns-ttl-cache-timeline .ygd-g-bad{stroke:var(--ygd-bad)}
.ygd-alb-dns-ttl-cache-timeline .ygd-panel{margin-top:10px;padding:10px 12px;border-radius:6px;background:var(--ygd-panel);min-height:96px;box-sizing:border-box}
.ygd-alb-dns-ttl-cache-timeline .ygd-step-title{font-size:15px;font-weight:700;color:var(--ygd-text);margin:0 0 4px 0;line-height:1.4}
.ygd-alb-dns-ttl-cache-timeline .ygd-step-text{font-size:15px;color:var(--ygd-text);margin:0;line-height:1.6}
.ygd-alb-dns-ttl-cache-timeline .ygd-controls{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.ygd-alb-dns-ttl-cache-timeline .ygd-btn{font-family:inherit;font-size:15px;line-height:1.2;min-height:40px;padding:8px 16px;border:1px solid var(--ygd-accent);border-radius:6px;background:transparent;color:var(--ygd-accent);cursor:pointer}
.ygd-alb-dns-ttl-cache-timeline .ygd-btn-primary{background:var(--ygd-accent);color:var(--ygd-btn-text);font-weight:700}
.ygd-alb-dns-ttl-cache-timeline .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-alb-dns-ttl-cache-timeline .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-alb-dns-ttl-cache-timeline .ygd-note{margin:10px 0 0 0;font-size:14px;line-height:1.6;color:var(--ygd-muted)}
@media (prefers-reduced-motion:reduce){.ygd-alb-dns-ttl-cache-timeline .ygd-head,.ygd-alb-dns-ttl-cache-timeline .ygd-el,.ygd-alb-dns-ttl-cache-timeline .ygd-seg{transition:none}}
</style>
<svg class="ygd-svg" viewBox="0 0 360 290" role="img" aria-label="ALB IP 변경 이후 두 클라이언트의 DNS 캐시 타임라인. TTL 60초를 지키는 클라이언트는 60초 안에 새 IP로 갈아타고, JVM 기본값 networkaddress.cache.ttl=-1로 무한 캐시하는 클라이언트는 옛 IP로 계속 요청해 connection refused 또는 타임아웃이 난다.">
<defs>
<marker id="ygd-alb-dns-ttl-cache-timeline-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-arrow-head" d="M0 0 L10 5 L0 10 Z"/></marker>
</defs>
<line class="ygd-axis" x1="20" y1="34" x2="344" y2="34" marker-end="url(#ygd-alb-dns-ttl-cache-timeline-arrow)"/>
<text class="ygd-t ygd-t-m" x="346" y="18" text-anchor="end">시간</text>
<g class="ygd-el" data-s="1"><circle class="ygd-dot" cx="110" cy="34" r="4"/><text class="ygd-t" x="110" y="18" text-anchor="middle">ALB IP 변경</text></g>
<g class="ygd-el" data-s="2"><circle class="ygd-dot" cx="250" cy="34" r="4"/><text class="ygd-t" x="250" y="18" text-anchor="middle">TTL 60초</text></g>
<g class="ygd-head" style="transform:translate(60px,0)"><path d="M0 42 L-6 51 L6 51 Z"/></g>
<text class="ygd-t ygd-t-lane" x="20" y="70">TTL 60초를 지키는 클라이언트</text>
<g class="ygd-el" data-s="0"><rect class="ygd-seg" x="20" y="78" width="90" height="30" rx="4"/><text class="ygd-t" x="65" y="97" text-anchor="middle">옛 IP</text></g>
<g class="ygd-el" data-s="1"><rect class="ygd-seg" x="110" y="78" width="140" height="30" rx="4"/><text class="ygd-t" x="180" y="97" text-anchor="middle">옛 IP 캐시</text></g>
<g class="ygd-el" data-s="2"><rect class="ygd-seg ygd-seg-ok" x="250" y="78" width="90" height="30" rx="4"/><text class="ygd-t" x="295" y="97" text-anchor="middle">새 IP</text></g>
<g class="ygd-el" data-s="0"><path class="ygd-g ygd-g-ok" d="M-5 0 L-1.5 4 L5 -5" transform="translate(50,126)"/><path class="ygd-g ygd-g-ok" d="M-5 0 L-1.5 4 L5 -5" transform="translate(85,126)"/></g>
<g class="ygd-el" data-s="2"><path class="ygd-g ygd-g-ok" d="M-5 0 L-1.5 4 L5 -5" transform="translate(290,126)"/><path class="ygd-g ygd-g-ok" d="M-5 0 L-1.5 4 L5 -5" transform="translate(325,126)"/><text class="ygd-t ygd-t-ok" x="20" y="150">캐시 만료 후 재조회 → 새 IP로 정상 요청</text></g>
<text class="ygd-t ygd-t-lane" x="20" y="184">JVM 기본값 (networkaddress.cache.ttl=-1)</text>
<g class="ygd-el" data-s="0"><rect class="ygd-seg" x="20" y="192" width="90" height="30" rx="4"/><text class="ygd-t" x="65" y="211" text-anchor="middle">옛 IP</text></g>
<g class="ygd-el" data-s="1" data-alt="3"><rect class="ygd-seg" x="110" y="192" width="230" height="30" rx="4"/><text class="ygd-t" x="225" y="211" text-anchor="middle">옛 IP 캐시 유지 (만료 없음)</text></g>
<g class="ygd-el" data-s="0"><path class="ygd-g ygd-g-ok" d="M-5 0 L-1.5 4 L5 -5" transform="translate(50,240)"/><path class="ygd-g ygd-g-ok" d="M-5 0 L-1.5 4 L5 -5" transform="translate(85,240)"/></g>
<g class="ygd-el" data-s="3"><path class="ygd-g ygd-g-bad" d="M-4 -4 L4 4 M4 -4 L-4 4" transform="translate(140,240)"/><path class="ygd-g ygd-g-bad" d="M-4 -4 L4 4 M4 -4 L-4 4" transform="translate(175,240)"/><path class="ygd-g ygd-g-bad" d="M-4 -4 L4 4 M4 -4 L-4 4" transform="translate(215,240)"/><path class="ygd-g ygd-g-bad" d="M-4 -4 L4 4 M4 -4 L-4 4" transform="translate(290,240)"/><path class="ygd-g ygd-g-bad" d="M-4 -4 L4 4 M4 -4 L-4 4" transform="translate(325,240)"/><text class="ygd-t ygd-t-bad" x="20" y="264">옛 IP로 계속 요청</text><text class="ygd-t ygd-t-bad" x="20" y="282">connection refused 또는 타임아웃</text></g>
</svg>
<div class="ygd-panel" aria-live="polite"><div class="ygd-step-title"></div><div class="ygd-step-text"></div></div>
<div class="ygd-controls" role="group" aria-label="타임라인 재생 컨트롤"><button type="button" class="ygd-btn ygd-btn-primary" data-ygd="play">재생</button><button type="button" class="ygd-btn" data-ygd="prev">이전</button><button type="button" class="ygd-btn" data-ygd="next">다음</button></div>
<div class="ygd-note">비유: 이사한 친구의 주소를 수첩에 적어 두는 것과 비슷하다. 수첩을 주기적으로 다시 확인하면 새 집으로 가지만, 한 번 적은 주소를 영원히 믿으면 빈집 앞에서 계속 초인종을 누르게 된다.</div>
<script>
(function () {
  var root = document.getElementById('ygd-alb-dns-ttl-cache-timeline');
  if (!root) { return; }
  var els = root.querySelectorAll('[data-s]');
  var head = root.querySelector('.ygd-head');
  var titleEl = root.querySelector('.ygd-step-title');
  var textEl = root.querySelector('.ygd-step-text');
  var playBtn = root.querySelector('[data-ygd="play"]');
  var prevBtn = root.querySelector('[data-ygd="prev"]');
  var nextBtn = root.querySelector('[data-ygd="next"]');
  var xs = [60, 110, 250, 295, 325];
  var steps = [
    { t: '정상 상태', d: 'IP가 바뀌기 전에는 두 클라이언트 모두 DNS로 받아 둔 옛 IP(예: 10.0.11.42)로 연결하고, 요청이 정상적으로 처리된다.' },
    { t: 'ALB가 새 ENI를 띄워 IP가 바뀜', d: '스케일링이나 AZ 장애로 ALB가 새 ENI를 띄우면 ALB의 IP가 바뀐다. 두 클라이언트는 아직 캐시에 옛 IP를 들고 있다.' },
    { t: 'TTL을 지키는 클라이언트는 새 IP로 전환', d: 'ALB의 DNS TTL은 60초다. TTL을 지키는 클라이언트는 캐시가 만료되면 다시 조회하므로 60초 안에 새 IP로 갈아탄다.' },
    { t: '무한 캐시 클라이언트는 옛 IP로 계속 요청', d: 'JVM 기본값 networkaddress.cache.ttl=-1은 영원히 캐싱한다. 이 클라이언트는 옛 IP로 계속 요청하다 connection refused나 타임아웃을 만난다.' },
    { t: '처방: TTL을 명시한다', d: 'JVM 기반 클라이언트는 TTL을 30~60초로 명시해야 한다. 예를 들어 JVM 옵션 -Dsun.net.inetaddr.ttl=60 을 준다.' }
  ];
  var last = steps.length - 1;
  var cur = 0;
  var timer = null;
  function render() {
    Array.prototype.forEach.call(els, function (el) {
      var s = parseInt(el.getAttribute('data-s'), 10);
      el.classList.toggle('ygd-on', cur >= s);
      var alt = el.getAttribute('data-alt');
      if (alt !== null) { el.classList.toggle('ygd-alt', cur >= parseInt(alt, 10)); }
    });
    head.style.transform = 'translate(' + xs[cur] + 'px,0)';
    titleEl.textContent = (cur + 1) + ' / ' + steps.length + ' · ' + steps[cur].t;
    textEl.textContent = steps[cur].d;
    prevBtn.disabled = (cur === 0);
    nextBtn.disabled = (cur === last);
  }
  function stop() {
    if (timer !== null) { clearInterval(timer); timer = null; }
    playBtn.textContent = (cur === last) ? '다시 재생' : '재생';
  }
  function play() {
    if (cur === last) { cur = 0; render(); }
    playBtn.textContent = '일시정지';
    timer = setInterval(function () {
      if (cur >= last) { stop(); return; }
      cur += 1;
      render();
      if (cur >= last) { stop(); }
    }, 2800);
  }
  playBtn.addEventListener('click', function () {
    if (timer !== null) { stop(); } else { play(); }
  });
  prevBtn.addEventListener('click', function () {
    if (timer !== null) { stop(); }
    if (cur > 0) { cur -= 1; render(); }
    playBtn.textContent = '재생';
  });
  nextBtn.addEventListener('click', function () {
    if (timer !== null) { stop(); }
    if (cur < last) { cur += 1; render(); }
    playBtn.textContent = (cur === last) ? '다시 재생' : '재생';
  });
  render();
})();
</script>
</div>

### 클라이언트 입장에서 본 응답 흐름

```
브라우저 ─┐
          │ api.example.com A?
          v
   로컬 리졸버 (OS)
          │ 캐시 miss
          v
     ISP DNS
          │ 권한 네임서버 위임 추적
          v
   Route 53 NS
          │ alias 풀이 → ALB의 A 레코드 세트
          v
   10.0.11.42, 10.0.12.118 반환
```

DNS 응답이 돌아오면 브라우저는 그중 하나의 IP로 TCP SYN을 보낸다. ALB가 public-facing이라면 이 IP는 퍼블릭 IP다. 인터넷 라우팅이 시작된다.

---

## STEP 2. 인터넷 → Internet Gateway

### IGW가 하는 일

Internet Gateway는 흔히 "VPC를 인터넷에 연결하는 장치"라고 설명되지만 실제로는 두 가지를 한다.

1. VPC로 들어오는 패킷을 받아 라우팅 테이블을 따라 서브넷으로 전달
2. 퍼블릭 IP를 가진 ENI에 대해 1:1 NAT를 수행 — 외부에서 들어오는 패킷의 destination을 ENI의 프라이빗 IP로 바꾸고, 나가는 패킷의 source를 퍼블릭 IP로 바꾼다

ALB의 Public-facing 모드는 각 ENI가 EIP나 AWS가 할당한 퍼블릭 IP를 가진다. 외부에서 보면 ALB의 IP는 퍼블릭이지만 ENI 자체는 서브넷의 프라이빗 IP(`10.0.11.42`)를 들고 있다. IGW가 둘을 매핑한다.

### 라우팅 테이블의 0.0.0.0/0

퍼블릭 서브넷이 "퍼블릭"인 이유는 라우팅 테이블에 IGW가 박혀 있어서다.

```hcl
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}
```

서브넷 자체에 "public"이라는 속성이 있는 게 아니라, 그 서브넷이 연결된 라우팅 테이블에 IGW로 향하는 0.0.0.0/0이 있으면 퍼블릭이 된다. 똑같은 CIDR 블록을 잡아 놓고 라우팅만 NAT GW로 바꾸면 프라이빗 서브넷이 된다.

### 자주 밟는 지뢰: 인바운드는 IGW가 받지만 응답이 못 나가는 경우

새로 만든 ALB가 외부에서 안 닿을 때 점검 순서는 이렇다.

1. ALB가 "internet-facing"으로 만들어졌는지 (internal과 헷갈리는 경우가 많다)
2. ALB가 속한 서브넷의 라우팅 테이블에 `0.0.0.0/0 → igw-xxxx`가 있는지
3. ALB ENI의 시큐리티 그룹 인바운드에 443/80이 열려 있는지
4. 서브넷의 NACL 인바운드/아웃바운드가 ephemeral port(1024-65535)까지 열려 있는지

NACL은 stateless라 응답 트래픽도 별도 규칙이 필요하다. NACL 인바운드만 443 열고 아웃바운드 ephemeral을 막아 두면 인바운드 SYN은 들어오는데 ALB가 SYN-ACK을 못 보내서 TCP 핸드셰이크가 안 끝난다. 패킷 캡처를 떠 보면 SYN만 잡히고 응답이 없다.

---

## STEP 3. IGW → 퍼블릭 서브넷 (ALB가 사는 곳)

### ALB는 ENI 모음일 뿐이다

ALB는 추상적인 리소스라기보다 가용 영역마다 하나씩 띄워진 ENI들의 묶음에 가깝다. ALB를 만들 때 "subnets"에 최소 2개 AZ의 서브넷을 지정해야 하는 이유가 이거다. 각 서브넷마다 ENI가 하나 생기고, IGW는 그 ENI로 패킷을 전달한다.

```hcl
resource "aws_lb" "api" {
  name               = "api-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [
    aws_subnet.public_a.id,
    aws_subnet.public_c.id,
  ]
}
```

여기서 `internal = false`면 internet-facing ALB가 만들어진다. `true`면 ENI에 퍼블릭 IP가 안 붙는다.

### 시큐리티 그룹: ALB 입구

ALB 자체에 붙은 SG는 외부에서 ALB로 들어오는 트래픽을 통제한다.

```hcl
resource "aws_security_group" "alb" {
  name   = "api-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

ALB SG의 아웃바운드는 ECS Task SG로 가는 트래픽을 허용해야 한다. 기본값(`0.0.0.0/0` 전체 허용)이면 문제 없지만 보안 강화를 위해 아웃바운드를 좁혀 둔 환경에서는 누락되기 쉽다.

### NACL이 한 번 더 본다

패킷은 ALB ENI에 닿기 전에 서브넷의 NACL을 통과한다. SG는 stateful, NACL은 stateless. SG가 ENI 단위라면 NACL은 서브넷 단위다.

평가 순서는 패킷이 들어올 때 기준으로 이렇다.

```
인터넷에서 들어오는 패킷
    │
    v
[서브넷 NACL 인바운드 규칙]   ← stateless, 번호 순서대로 첫 매칭 적용
    │
    v
[ALB ENI의 SG 인바운드 규칙]  ← stateful, 한 번 허용되면 응답도 자동 허용
    │
    v
   ALB
    │  (응답 SYN-ACK)
    v
[ALB ENI SG 아웃바운드]       ← SG는 응답을 자동 허용
    │
    v
[서브넷 NACL 아웃바운드]      ← stateless라 응답도 별도 허용 필요
    │
    v
인터넷
```

NACL은 기본값이 all allow다. 직접 좁혀 둔 적이 없으면 신경 쓸 일이 적은데, 보안팀이 컴플라이언스 요구로 좁혀 놓은 환경에서 트러블슈팅이 어려워진다.

---

## STEP 4. ALB가 리스너 규칙을 평가한다

### 리스너와 규칙

ALB는 포트별로 리스너를 만든다. HTTPS면 443, HTTP면 80. 리스너 안에는 규칙(rule)이 우선순위 순서대로 정렬되어 있다. 평가는 number 작은 것부터, 첫 매칭에서 멈춘다.

```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.api.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener_rule" "upload" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.upload.arn
  }

  condition {
    path_pattern {
      values = ["/upload", "/upload/*"]
    }
  }

  condition {
    host_header {
      values = ["api.example.com"]
    }
  }
}

resource "aws_lb_listener_rule" "admin" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 50

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.admin.arn
  }

  condition {
    http_header {
      http_header_name = "X-Admin-Token"
      values           = ["*"]
    }
  }
}
```

위 설정에서 `/upload` 경로 요청이 오면 priority 50의 admin 규칙은 헤더 미스매치라 패스, priority 100의 upload 규칙이 매칭되어 upload target group으로 forward된다. 어느 규칙에도 안 걸리면 default action으로 떨어진다.

<div class="ygd-alb-listener-rule-evaluation" id="ygd-alb-listener-rule-evaluation">
<style>
.ygd-alb-listener-rule-evaluation{--ygd-bg:#FAF8F6;--ygd-card:#FFFFFF;--ygd-border:#D9D3CC;--ygd-text:#2B2724;--ygd-muted:#6B655F;--ygd-line:#8C857D;--ygd-accent:#2F6B80;--ygd-onaccent:#FFFFFF;--ygd-pass:#1E7A46;--ygd-fail:#B3261E;--ygd-dflt:#8A5A00;max-width:760px;margin:1.2em auto;box-sizing:border-box;padding:12px;border:1px solid var(--ygd-border);border-radius:12px;background:var(--ygd-bg);color:var(--ygd-text);font-size:15px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-alb-listener-rule-evaluation{--ygd-bg:#1F1C1E;--ygd-card:#2A2628;--ygd-border:#4A4448;--ygd-text:#F0EDE9;--ygd-muted:#A8A29A;--ygd-line:#8C857D;--ygd-accent:#7FB8CC;--ygd-onaccent:#1F1C1E;--ygd-pass:#6FCF97;--ygd-fail:#FF8A80;--ygd-dflt:#E8B04A}
.ygd-alb-listener-rule-evaluation .ygd-cap{margin:0 0 6px;font-size:14px;color:var(--ygd-muted)}
.ygd-alb-listener-rule-evaluation .ygd-analogy{margin:0 0 10px;font-size:14px;color:var(--ygd-text)}
.ygd-alb-listener-rule-evaluation .ygd-row{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}
.ygd-alb-listener-rule-evaluation .ygd-btn{box-sizing:border-box;min-height:40px;padding:6px 14px;border:1px solid var(--ygd-border);border-radius:8px;background:var(--ygd-card);color:var(--ygd-text);font:inherit;font-size:14px;line-height:1.3;cursor:pointer}
.ygd-alb-listener-rule-evaluation .ygd-btn[aria-pressed="true"],.ygd-alb-listener-rule-evaluation .ygd-primary{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-onaccent);font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-btn:disabled{opacity:.45;cursor:default}
.ygd-alb-listener-rule-evaluation .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-alb-listener-rule-evaluation .ygd-svg{display:block;width:100%;max-width:440px;height:auto;margin:0 auto 10px}
.ygd-alb-listener-rule-evaluation .ygd-t{font-size:12.5px;fill:var(--ygd-text)}
.ygd-alb-listener-rule-evaluation .ygd-h{font-size:13px;font-weight:700;fill:var(--ygd-text)}
.ygd-alb-listener-rule-evaluation .ygd-sub{font-size:12px;fill:var(--ygd-muted)}
.ygd-alb-listener-rule-evaluation .ygd-end{text-anchor:end}
.ygd-alb-listener-rule-evaluation .ygd-mid{text-anchor:middle}
.ygd-alb-listener-rule-evaluation .ygd-rect{fill:var(--ygd-card);stroke:var(--ygd-border);stroke-width:1.5}
.ygd-alb-listener-rule-evaluation .ygd-box,.ygd-alb-listener-rule-evaluation .ygd-pill{opacity:.65;transition:opacity .35s}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-pass,.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-fail,.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-reach,.ygd-alb-listener-rule-evaluation .ygd-pill.ygd-is-on{opacity:1}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-skip{opacity:.45}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-pass .ygd-rect,.ygd-alb-listener-rule-evaluation .ygd-pill.ygd-is-on .ygd-rect{stroke:var(--ygd-pass);stroke-width:2.5}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-fail .ygd-rect{stroke:var(--ygd-fail);stroke-width:2.5}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-reach .ygd-rect,.ygd-alb-listener-rule-evaluation .ygd-pill.ygd-is-on.ygd-is-dflt .ygd-rect{stroke:var(--ygd-dflt);stroke-width:2.5}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-pass .ygd-tag{fill:var(--ygd-pass);font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-fail .ygd-tag{fill:var(--ygd-fail);font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-box.ygd-is-reach .ygd-tag{fill:var(--ygd-dflt);font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-tag,.ygd-alb-listener-rule-evaluation .ygd-bd{font-size:12px;fill:var(--ygd-muted)}
.ygd-alb-listener-rule-evaluation .ygd-cond.ygd-is-pass .ygd-bd{fill:var(--ygd-pass);font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-cond.ygd-is-fail .ygd-bd{fill:var(--ygd-fail);font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-arr{color:var(--ygd-line);opacity:.55;transition:opacity .35s}
.ygd-alb-listener-rule-evaluation .ygd-arr line{stroke:currentColor;stroke-width:2}
.ygd-alb-listener-rule-evaluation .ygd-arr polygon{fill:currentColor}
.ygd-alb-listener-rule-evaluation .ygd-arr.ygd-m-next{color:var(--ygd-accent);opacity:1}
.ygd-alb-listener-rule-evaluation .ygd-arr.ygd-m-ok{color:var(--ygd-pass);opacity:1}
.ygd-alb-listener-rule-evaluation .ygd-arr.ygd-m-def{color:var(--ygd-dflt);opacity:1}
.ygd-alb-listener-rule-evaluation .ygd-arr.ygd-m-stop line{stroke-dasharray:4 4}
.ygd-alb-listener-rule-evaluation .ygd-gl{font-size:12px;font-weight:700}
.ygd-alb-listener-rule-evaluation .ygd-gl-next{fill:var(--ygd-accent)}
.ygd-alb-listener-rule-evaluation .ygd-gl-stop{fill:var(--ygd-pass)}
.ygd-alb-listener-rule-evaluation .ygd-gl-def{fill:var(--ygd-dflt)}
.ygd-alb-listener-rule-evaluation .ygd-pk{fill:var(--ygd-accent);stroke:var(--ygd-card);stroke-width:2;transition:transform .6s ease}
.ygd-alb-listener-rule-evaluation .ygd-panel{box-sizing:border-box;min-height:122px;padding:10px 12px;margin:0 0 10px;border:1px solid var(--ygd-border);border-radius:8px;background:var(--ygd-card)}
.ygd-alb-listener-rule-evaluation .ygd-step{margin:0;font-size:14px;color:var(--ygd-muted)}
.ygd-alb-listener-rule-evaluation .ygd-stitle{margin:2px 0 4px;font-size:16px;font-weight:700;color:var(--ygd-text)}
.ygd-alb-listener-rule-evaluation .ygd-desc{margin:0;font-size:15px;color:var(--ygd-text)}
@media (prefers-reduced-motion: reduce){.ygd-alb-listener-rule-evaluation *{transition:none !important;animation:none !important}}
</style>
<p class="ygd-cap">HTTPS 443 리스너 · 규칙은 priority 오름차순으로 평가 · 규칙 안의 조건은 AND</p>
<p class="ygd-analogy">비유: 접수 창구 직원이 기준표를 번호 순서대로 대 보고, 처음 맞는 기준의 담당 부서로 서류를 넘긴다. 어떤 기준에도 안 맞으면 기본 담당 부서로 보낸다.</p>
<div class="ygd-row" role="group" aria-label="요청 종류 선택">
<button type="button" class="ygd-btn" data-sc="upload" aria-pressed="true">/upload 요청</button>
<button type="button" class="ygd-btn" data-sc="admin" aria-pressed="false">관리자 헤더 요청</button>
<button type="button" class="ygd-btn" data-sc="none" aria-pressed="false">매칭 없는 요청</button>
</div>
<svg class="ygd-svg" data-ygd="svg" viewBox="0 0 360 406" role="img" aria-label="ALB 리스너 규칙 평가 다이어그램" focusable="false">
<g data-ygd="req"><rect class="ygd-rect" x="12" y="8" width="336" height="92" rx="8"/><text class="ygd-h" x="24" y="28">수신 요청</text><text class="ygd-t" data-ygd="rq1" x="24" y="50"></text><text class="ygd-t" data-ygd="rq2" x="24" y="68"></text><text class="ygd-t" data-ygd="rq3" x="24" y="86"></text></g>
<g class="ygd-arr ygd-m-next" data-ygd="a0"><line x1="131" y1="100" x2="131" y2="126"/><polygon points="131,134 125,125 137,125"/></g>
<g class="ygd-arr" data-ygd="a1"><line x1="131" y1="194" x2="131" y2="220"/><polygon points="131,228 125,219 137,219"/></g>
<g class="ygd-arr" data-ygd="a2"><line x1="131" y1="310" x2="131" y2="336"/><polygon points="131,344 125,335 137,335"/></g>
<text class="ygd-gl" data-ygd="g1" x="143" y="215"></text>
<text class="ygd-gl" data-ygd="g2" x="143" y="331"></text>
<g class="ygd-box ygd-is-idle" data-ygd="r50"><rect class="ygd-rect" x="12" y="134" width="238" height="60" rx="8"/><text class="ygd-h" x="24" y="156">priority 50 · admin</text><text class="ygd-tag ygd-end" data-ygd="r50-tag" x="238" y="156">대기</text><g class="ygd-cond ygd-is-idle" data-ygd="h50"><text class="ygd-t" x="24" y="180">header X-Admin-Token = *</text><text class="ygd-bd ygd-end" data-ygd="h50-b" x="238" y="180">—</text></g></g>
<g class="ygd-box ygd-is-idle" data-ygd="r100"><rect class="ygd-rect" x="12" y="228" width="238" height="82" rx="8"/><text class="ygd-h" x="24" y="250">priority 100 · upload</text><text class="ygd-tag ygd-end" data-ygd="r100-tag" x="238" y="250">대기</text><g class="ygd-cond ygd-is-idle" data-ygd="host"><text class="ygd-t" x="24" y="274">host = api.example.com</text><text class="ygd-bd ygd-end" data-ygd="host-b" x="238" y="274">—</text></g><g class="ygd-cond ygd-is-idle" data-ygd="path"><text class="ygd-t" x="24" y="296">path = /upload, /upload/*</text><text class="ygd-bd ygd-end" data-ygd="path-b" x="238" y="296">—</text></g></g>
<g class="ygd-box ygd-is-idle" data-ygd="def"><rect class="ygd-rect" x="12" y="344" width="238" height="54" rx="8"/><text class="ygd-h" x="24" y="366">default action</text><text class="ygd-tag ygd-end" data-ygd="def-tag" x="238" y="366">대기</text><text class="ygd-sub" x="24" y="386">어느 규칙에도 안 걸린 요청</text></g>
<g class="ygd-arr" data-ygd="pa-admin"><line x1="250" y1="164" x2="257" y2="164"/><polygon points="266,164 257,158 257,170"/></g>
<g class="ygd-arr" data-ygd="pa-upload"><line x1="250" y1="269" x2="257" y2="269"/><polygon points="266,269 257,263 257,275"/></g>
<g class="ygd-arr" data-ygd="pa-api"><line x1="250" y1="371" x2="257" y2="371"/><polygon points="266,371 257,365 257,377"/></g>
<g class="ygd-pill" data-ygd="pill-admin"><rect class="ygd-rect" x="266" y="142" width="86" height="44" rx="8"/><text class="ygd-h ygd-mid" x="309" y="161">admin</text><text class="ygd-sub ygd-mid" x="309" y="177">target group</text></g>
<g class="ygd-pill" data-ygd="pill-upload"><rect class="ygd-rect" x="266" y="247" width="86" height="44" rx="8"/><text class="ygd-h ygd-mid" x="309" y="266">upload</text><text class="ygd-sub ygd-mid" x="309" y="282">target group</text></g>
<g class="ygd-pill" data-ygd="pill-api"><rect class="ygd-rect" x="266" y="349" width="86" height="44" rx="8"/><text class="ygd-h ygd-mid" x="309" y="368">api</text><text class="ygd-sub ygd-mid" x="309" y="384">target group</text></g>
<circle class="ygd-pk" data-ygd="pk" cx="0" cy="0" r="6" style="transform:translate(12px,54px)"/>
</svg>
<div class="ygd-panel" aria-live="polite"><p class="ygd-step" data-ygd="stepno"></p><p class="ygd-stitle" data-ygd="stitle"></p><p class="ygd-desc" data-ygd="sdesc"></p></div>
<div class="ygd-row">
<button type="button" class="ygd-btn ygd-primary" data-ygd="play">재생</button>
<button type="button" class="ygd-btn" data-ygd="prev">이전 단계</button>
<button type="button" class="ygd-btn" data-ygd="next">다음 단계</button>
</div>
<script>
(function(){
var root=document.getElementById('ygd-alb-listener-rule-evaluation');
if(!root){return;}
function q(k){return root.querySelector('[data-ygd="'+k+'"]');}
var I='idle',P='pass',F='fail',K='skip',R='reach';
var REQ=[12,54],C50=[12,164],C100=[12,269],CDEF=[12,371],PAD=[266,164],PUP=[266,269],PAPI=[266,371];
var STOP='첫 매칭 · 여기서 멈춤';
var SC={
upload:{req:['Host: api.example.com','Path: /upload','X-Admin-Token: (없음)'],steps:[
{t:'요청 도착',d:'리스너가 /upload 요청을 받았다. 규칙은 priority 숫자가 작은 것부터 차례로 평가한다.',pk:REQ},
{t:'priority 50 · admin 평가',d:'이 규칙의 조건은 X-Admin-Token 헤더 하나뿐인데 요청에 헤더가 없어 불일치다. 다음 규칙으로 넘어간다.',r50:F,h50:F,pk:C50,a1:'next',g1:'불일치 → 다음 규칙'},
{t:'priority 100 · upload 평가',d:'host와 path 조건을 AND로 평가한다. 둘 다 맞으므로 이 규칙이 일치한다.',r50:F,h50:F,r100:P,host:P,path:P,pk:C100,a1:'next',g1:'불일치 → 다음 규칙'},
{t:'첫 매칭에서 멈춤',d:'일치한 규칙의 action이 실행되어 upload target group으로 forward된다. 이미 멈췄으므로 default action은 평가하지 않는다.',r50:F,h50:F,r100:P,host:P,path:P,def:K,out:'upload',pk:PUP,a1:'next',g1:'불일치 → 다음 규칙',a2:'stop',g2:STOP}
]},
admin:{req:['Host: api.example.com','Path: /users','X-Admin-Token: abc123'],steps:[
{t:'요청 도착',d:'관리자 헤더가 붙은 요청이 도착했다. 가장 작은 priority 50 규칙부터 평가한다.',pk:REQ},
{t:'priority 50 · admin 평가',d:'admin 규칙의 조건은 헤더 하나뿐이고, 요청에 X-Admin-Token이 있어 일치한다. 첫 매칭이다.',r50:P,h50:P,pk:C50,a1:'stop',g1:STOP},
{t:'첫 매칭에서 멈춤',d:'priority 100 규칙과 default action은 평가하지 않고 admin target group으로 forward된다. /upload 요청에 같은 헤더가 붙어도 priority 50이 먼저라 admin으로 간다.',r50:P,h50:P,r100:K,host:K,path:K,def:K,out:'admin',pk:PAD,a1:'stop',g1:STOP}
]},
none:{req:['Host: api.example.com','Path: /users','X-Admin-Token: (없음)'],steps:[
{t:'요청 도착',d:'어느 규칙에도 해당하지 않는 /users 요청이 도착했다. 규칙을 priority 순으로 대 보고, 끝까지 안 걸리면 어떻게 되는지 본다.',pk:REQ},
{t:'priority 50 · admin 평가',d:'X-Admin-Token 헤더가 없어 불일치다. 다음 규칙으로 넘어간다.',r50:F,h50:F,pk:C50,a1:'next',g1:'불일치 → 다음 규칙'},
{t:'priority 100 · upload 평가',d:'host는 맞지만 path가 /upload, /upload/* 가 아니다. 조건은 AND라 하나만 틀려도 규칙 전체가 불일치다.',r50:F,h50:F,r100:F,host:P,path:F,pk:C100,a1:'next',g1:'불일치 → 다음 규칙',a2:'def',g2:'모두 불일치 → default'},
{t:'default action으로 떨어짐',d:'남은 규칙이 없다. 어느 규칙에도 안 걸린 요청은 default action으로 가서 api target group으로 forward된다.',r50:F,h50:F,r100:F,host:P,path:F,def:R,out:'api',pk:PAPI,a1:'next',g1:'불일치 → 다음 규칙',a2:'def',g2:'모두 불일치 → default'}
]}
};
var TAG={idle:'대기',pass:'매칭',fail:'불일치',skip:'평가 안 함',reach:'도착'};
var BADGE={idle:'—',pass:'일치',fail:'불일치',skip:'—'};
var CLS=['idle','pass','fail','skip','reach'];
var scen='upload',cur=0,timer=null,playing=false;
var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
var btnPlay=q('play'),btnPrev=q('prev'),btnNext=q('next');
function setS(el,s){CLS.forEach(function(c){el.classList.remove('ygd-is-'+c);});el.classList.add('ygd-is-'+s);}
function setArrow(el,mode){el.setAttribute('class','ygd-arr ygd-m-'+mode);}
function setLabel(el,text,mode){el.textContent=text||'';el.setAttribute('class','ygd-gl ygd-gl-'+(mode==='stop'?'stop':(mode==='def'?'def':'next')));}
function last(){return SC[scen].steps.length-1;}
function playLabel(){btnPlay.textContent=playing?'일시정지':(cur>=last()&&cur>0?'다시 재생':'재생');}
function render(){
var sc=SC[scen],st=sc.steps[cur],i;
for(i=0;i<3;i++){q('rq'+(i+1)).textContent=sc.req[i];}
['r50','r100','def'].forEach(function(k){var s=st[k]||I;setS(q(k),s);q(k+'-tag').textContent=TAG[s];});
['h50','host','path'].forEach(function(k){var s=st[k]||I;setS(q(k),s);q(k+'-b').textContent=BADGE[s];});
['admin','upload','api'].forEach(function(n){
var on=st.out===n;
q('pill-'+n).setAttribute('class','ygd-pill'+(on?' ygd-is-on':'')+(on&&n==='api'?' ygd-is-dflt':''));
setArrow(q('pa-'+n),on?(n==='api'?'def':'ok'):'off');
});
setArrow(q('a1'),st.a1||'off');
setArrow(q('a2'),st.a2||'off');
setLabel(q('g1'),st.g1,st.a1);
setLabel(q('g2'),st.g2,st.a2);
q('pk').style.transform='translate('+st.pk[0]+'px,'+st.pk[1]+'px)';
q('stepno').textContent='단계 '+(cur+1)+' / '+sc.steps.length;
q('stitle').textContent=st.t;
q('sdesc').textContent=st.d;
btnPrev.disabled=cur===0;
btnNext.disabled=cur>=last();
q('svg').setAttribute('aria-label','ALB 리스너 규칙 평가 다이어그램. 단계 '+(cur+1)+' / '+sc.steps.length+'. '+st.t+'. '+st.d);
playLabel();
}
function stopPlay(){clearTimeout(timer);timer=null;playing=false;}
function tick(){
if(!playing){return;}
if(cur<last()){cur++;render();}
if(cur<last()){timer=setTimeout(tick,reduce?2600:2200);}else{stopPlay();playLabel();}
}
btnPlay.addEventListener('click',function(){
if(playing){stopPlay();playLabel();return;}
if(cur>=last()){cur=0;render();}
playing=true;playLabel();
timer=setTimeout(tick,reduce?1800:1500);
});
btnPrev.addEventListener('click',function(){stopPlay();if(cur>0){cur--;}render();});
btnNext.addEventListener('click',function(){stopPlay();if(cur<last()){cur++;}render();});
var tabs=root.querySelectorAll('[data-sc]');
Array.prototype.forEach.call(tabs,function(b){
b.addEventListener('click',function(){
stopPlay();
scen=b.getAttribute('data-sc');
cur=0;
Array.prototype.forEach.call(tabs,function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});
render();
});
});
render();
})();
</script>
</div>

### 평가 가능한 조건 종류

ALB가 매칭할 수 있는 건 host header, path pattern, HTTP header, HTTP method, query string, source IP다. 같은 규칙 내의 조건은 AND, values 배열은 OR로 묶인다. 정규식은 못 쓰고 와일드카드(`*`, `?`)만 가능하다는 점이 가끔 발목을 잡는다. 복잡한 라우팅은 ALB 단에서 풀려 하지 말고 애플리케이션 내부에서 처리하는 게 낫다.

### 우선순위 충돌

priority가 같은 규칙은 만들 수 없다. 다만 path는 같은데 host만 다른 규칙이 우선순위가 비슷한 경우 의도와 다르게 매칭되는 경우가 있다. 운영 중에 새 규칙을 끼워 넣을 때 우선순위를 10단위로 띄워 두면 사이에 끼워 넣기 쉽다(50, 100, 150...).

### Sticky session

업로드처럼 상태를 가진 요청이 같은 컨테이너에 가야 하면 target group에 stickiness를 켠다.

```hcl
resource "aws_lb_target_group" "upload" {
  name        = "upload-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"  # awsvpc 모드 ECS는 ip 타입

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 3600
    enabled         = true
  }
}
```

stickiness가 켜져 있으면 ALB가 `AWSALB` 쿠키를 심어서 같은 컨테이너로 라우팅한다. 단, 컨테이너가 죽거나 deregister되면 쿠키와 무관하게 다른 컨테이너로 간다. 멱등하지 않은 multipart upload는 클라이언트가 처음부터 다시 보내야 한다. 이 케이스를 무시하고 sticky만 믿었다가 ECS 롤링 배포 중 업로드가 깨지는 일이 생긴다.

### Target group 헬스체크

ALB는 30초마다(설정 가능) target group의 모든 타겟에 헬스체크를 날린다. 위 설정이면 `/health`에 200을 두 번 연속 받아야 healthy로 본다. unhealthy로 떨어지면 라우팅에서 제외된다.

운영하면서 가장 자주 보는 헬스체크 사고는 다음 셋이다.

첫째, 헬스체크 경로가 DB나 외부 서비스에 의존한다. DB가 잠깐 느려지면 헬스체크가 타임아웃 나고, ALB가 모든 컨테이너를 unhealthy로 만들고, 결국 503이 떨어진다. `/health`는 의존성 없이 200만 뱉어야 한다. 의존성까지 보는 deep check는 `/health/ready` 같은 별도 엔드포인트로 분리하고 운영 알람용으로만 쓴다.

둘째, 헬스체크 SG 누락. ALB SG가 ECS Task SG의 헬스체크 포트로 outbound가 안 되거나, ECS Task SG가 ALB SG로부터 inbound를 안 받으면 헬스체크가 다 실패한다.

셋째, healthy_threshold가 너무 높다. 2회면 60초만에 healthy로 올라오는데, 5회로 잡으면 첫 배포 후 2분 30초간 모든 트래픽이 default action으로 떨어진다. 새 컨테이너가 띄워졌는데 503이 나면 우선 healthy_threshold부터 확인한다.

---

<div class="ygd-target-group-health-check-timeline" id="ygd-target-group-health-check-timeline">
<style>
.ygd-target-group-health-check-timeline{--ygd-bg:#FDFBFA;--ygd-text:#2B2623;--ygd-sub:#5F5A55;--ygd-border:#CFC9C2;--ygd-ok:#1E7A46;--ygd-ok-bg:#CFEBDA;--ygd-bad:#B3261E;--ygd-bad-bg:#F6D5D1;--ygd-warn:#8A5A00;--ygd-warn-bg:#F7E3B5;--ygd-mute-bg:#DEDAD5;--ygd-on:#FFFFFF;--ygd-accent:#3D7387;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:12px;border:1px solid var(--ygd-border);border-radius:8px;background:var(--ygd-bg);color:var(--ygd-text);font-size:14px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-target-group-health-check-timeline{--ygd-bg:#1F1C1E;--ygd-text:#F0EDE9;--ygd-sub:#B8B2AA;--ygd-border:#5A545A;--ygd-ok:#5CCB93;--ygd-ok-bg:#1F4A35;--ygd-bad:#FF8A80;--ygd-bad-bg:#5A2522;--ygd-warn:#F2C14E;--ygd-warn-bg:#4D3B12;--ygd-mute-bg:#3F3A3D;--ygd-on:#14110F;--ygd-accent:#7FB6CB}
.ygd-target-group-health-check-timeline *{box-sizing:border-box}
.ygd-target-group-health-check-timeline .ygd-head{font-size:15px;font-weight:700;margin:0 0 8px}
.ygd-target-group-health-check-timeline .ygd-svg{display:block;width:100%;max-width:100%;height:auto}
.ygd-target-group-health-check-timeline .ygd-svg text{font-family:inherit;fill:var(--ygd-text);font-size:11px}
.ygd-target-group-health-check-timeline .ygd-lt{font-size:12px;font-weight:700}
.ygd-target-group-health-check-timeline .ygd-lr{font-size:11px;fill:var(--ygd-sub);text-anchor:end}
.ygd-target-group-health-check-timeline .ygd-ls{fill:var(--ygd-sub)}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-ls,.ygd-target-group-health-check-timeline .ygd-svg .ygd-lr{fill:var(--ygd-sub)}
.ygd-target-group-health-check-timeline .ygd-c-ok{fill:var(--ygd-ok-bg)}
.ygd-target-group-health-check-timeline .ygd-c-bad{fill:var(--ygd-bad-bg)}
.ygd-target-group-health-check-timeline .ygd-c-warn{fill:var(--ygd-warn-bg)}
.ygd-target-group-health-check-timeline .ygd-c-mute{fill:var(--ygd-mute-bg)}
.ygd-target-group-health-check-timeline .ygd-ghost{opacity:.35}
.ygd-target-group-health-check-timeline .ygd-fill{transform:scaleX(0);transform-box:fill-box;transform-origin:0 50%;transition:transform .45s ease}
.ygd-target-group-health-check-timeline .ygd-hatch-l{stroke:var(--ygd-bad);stroke-width:2;opacity:.3}
.ygd-target-group-health-check-timeline .ygd-outline{fill:none;stroke:var(--ygd-border);stroke-width:1}
.ygd-target-group-health-check-timeline .ygd-div{stroke:var(--ygd-border);stroke-width:1}
.ygd-target-group-health-check-timeline .ygd-tl{stroke:var(--ygd-border);stroke-width:1;fill:none}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-tick{fill:var(--ygd-sub);text-anchor:middle}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-tick.ygd-on{fill:var(--ygd-text);font-weight:700}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-st{text-anchor:middle;font-weight:600;opacity:.6;transition:opacity .3s}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-st.ygd-act{opacity:1}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-halo{paint-order:stroke;stroke:var(--ygd-bad-bg);stroke-width:4px;stroke-linejoin:round}
.ygd-target-group-health-check-timeline .ygd-dot circle{fill:var(--ygd-bg);stroke:var(--ygd-sub);stroke-width:1.5;opacity:.7;transition:fill .3s,opacity .3s}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-dot text{text-anchor:middle;fill:var(--ygd-sub);font-weight:700}
.ygd-target-group-health-check-timeline .ygd-dot.ygd-d-ok circle{fill:var(--ygd-ok);stroke:var(--ygd-ok);opacity:1}
.ygd-target-group-health-check-timeline .ygd-dot.ygd-d-bad circle{fill:var(--ygd-bad);stroke:var(--ygd-bad);opacity:1}
.ygd-target-group-health-check-timeline .ygd-svg .ygd-dot.ygd-d-ok text,.ygd-target-group-health-check-timeline .ygd-svg .ygd-dot.ygd-d-bad text{fill:var(--ygd-on)}
.ygd-target-group-health-check-timeline .ygd-dot.ygd-cur circle{stroke:var(--ygd-text);stroke-width:3}
.ygd-target-group-health-check-timeline .ygd-controls{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.ygd-target-group-health-check-timeline .ygd-btn{appearance:none;font:inherit;font-size:15px;min-height:44px;padding:0 16px;border:1px solid var(--ygd-border);border-radius:6px;background:var(--ygd-bg);color:var(--ygd-text);cursor:pointer}
.ygd-target-group-health-check-timeline .ygd-btn.ygd-primary{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-on);font-weight:700}
.ygd-target-group-health-check-timeline .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-target-group-health-check-timeline .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-target-group-health-check-timeline .ygd-panel{border:1px solid var(--ygd-border);border-left:4px solid var(--ygd-accent);border-radius:6px;padding:10px 12px;min-height:9em;font-size:15px}
.ygd-target-group-health-check-timeline .ygd-ptitle{font-weight:700;margin:0 0 4px;font-size:15px}
.ygd-target-group-health-check-timeline .ygd-ptext{margin:0;font-size:15px}
.ygd-target-group-health-check-timeline .ygd-legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:10px 0 0;padding:0;list-style:none;font-size:14px}
.ygd-target-group-health-check-timeline .ygd-legend li{margin:0;padding:0}
.ygd-target-group-health-check-timeline .ygd-sw{display:inline-block;width:14px;height:14px;border:1px solid var(--ygd-border);border-radius:3px;vertical-align:-2px;margin-right:6px}
.ygd-target-group-health-check-timeline .ygd-sw-ok{background:var(--ygd-ok-bg)}
.ygd-target-group-health-check-timeline .ygd-sw-warn{background:var(--ygd-warn-bg)}
.ygd-target-group-health-check-timeline .ygd-sw-mute{background:var(--ygd-mute-bg)}
.ygd-target-group-health-check-timeline .ygd-sw-bad{background:repeating-linear-gradient(45deg,var(--ygd-bad-bg) 0,var(--ygd-bad-bg) 3px,var(--ygd-bad) 3px,var(--ygd-bad) 4px)}
.ygd-target-group-health-check-timeline .ygd-note{margin:10px 0 0;font-size:14px;color:var(--ygd-sub)}
@media (prefers-reduced-motion:reduce){.ygd-target-group-health-check-timeline *{transition:none !important;animation:none !important}}
</style>
<p class="ygd-head">헬스체크 결과가 쌓이며 상태가 바뀌는 과정</p>
<svg class="ygd-svg" viewBox="0 0 360 342" role="img" aria-label="Target group 헬스체크 타임라인. healthy_threshold 2는 60초에 healthy가 되고, healthy_threshold 5는 150초까지 default action으로 떨어져 503이 납니다. unhealthy_threshold 3은 연속 실패 3회째인 90초에 라우팅에서 제외됩니다.">
<defs>
<pattern id="ygd-target-group-health-check-timeline-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line class="ygd-hatch-l" x1="0" y1="0" x2="0" y2="8"/></pattern>
</defs>
<g>
<text class="ygd-lt" x="8" y="22">healthy_threshold = 2</text>
<text class="ygd-lr" x="352" y="22">60초 후 healthy</text>
<text class="ygd-ls" x="8" y="38">0초 = 컨테이너 등록 · 연속 성공 2회 필요</text>
<rect class="ygd-ghost ygd-c-warn" x="24" y="72" width="104" height="24"/>
<rect class="ygd-ghost ygd-c-ok" x="128" y="72" width="208" height="24"/>
<rect class="ygd-fill ygd-c-warn" data-a="0" data-b="60" x="24" y="72" width="104" height="24"/>
<rect class="ygd-fill ygd-c-ok" data-a="60" data-b="180" x="128" y="72" width="208" height="24"/>
<line class="ygd-div" x1="128" y1="72" x2="128" y2="96"/>
<rect class="ygd-outline" x="24" y="72" width="312" height="24"/>
<text class="ygd-st" data-a="0" x="76" y="88">healthy 대기</text>
<text class="ygd-st" data-a="60" x="232" y="88">healthy · 트래픽 수신</text>
<path class="ygd-tl" d="M24 96v5M76 96v5M128 96v5M180 96v5M232 96v5M284 96v5M336 96v5"/>
<text class="ygd-tick" data-t="0" x="24" y="114">0초</text>
<text class="ygd-tick" data-t="30" x="76" y="114">30</text>
<text class="ygd-tick" data-t="60" x="128" y="114">60</text>
<text class="ygd-tick" data-t="90" x="180" y="114">90</text>
<text class="ygd-tick" data-t="120" x="232" y="114">120</text>
<text class="ygd-tick" data-t="150" x="284" y="114">150</text>
<text class="ygd-tick" data-t="180" x="334" y="114">180초</text>
<g class="ygd-dot" data-t="30" data-k="ok"><circle cx="76" cy="58" r="9"/><text x="76" y="62">1</text></g>
<g class="ygd-dot" data-t="60" data-k="ok"><circle cx="128" cy="58" r="9"/><text x="128" y="62">2</text></g>
<g class="ygd-dot" data-t="90" data-k="ok"><circle cx="180" cy="58" r="9"/><text x="180" y="62">✓</text></g>
<g class="ygd-dot" data-t="120" data-k="ok"><circle cx="232" cy="58" r="9"/><text x="232" y="62">✓</text></g>
<g class="ygd-dot" data-t="150" data-k="ok"><circle cx="284" cy="58" r="9"/><text x="284" y="62">✓</text></g>
<g class="ygd-dot" data-t="180" data-k="ok"><circle cx="334" cy="58" r="9"/><text x="334" y="62">✓</text></g>
</g>
<g>
<text class="ygd-lt" x="8" y="134">healthy_threshold = 5</text>
<text class="ygd-lr" x="352" y="134">150초 후 healthy</text>
<text class="ygd-ls" x="8" y="150">0초 = 컨테이너 등록 · 연속 성공 5회 필요</text>
<rect class="ygd-ghost ygd-c-bad" x="24" y="184" width="260" height="24"/>
<rect class="ygd-ghost ygd-c-ok" x="284" y="184" width="52" height="24"/>
<rect class="ygd-fill ygd-c-bad" data-a="0" data-b="150" x="24" y="184" width="260" height="24"/>
<rect class="ygd-fill" data-a="0" data-b="150" x="24" y="184" width="260" height="24" fill="url(#ygd-target-group-health-check-timeline-hatch)"/>
<rect class="ygd-fill ygd-c-ok" data-a="150" data-b="180" x="284" y="184" width="52" height="24"/>
<line class="ygd-div" x1="284" y1="184" x2="284" y2="208"/>
<rect class="ygd-outline" x="24" y="184" width="312" height="24"/>
<text class="ygd-st ygd-halo" data-a="0" x="154" y="200">default action → 503 · 2분 30초</text>
<text class="ygd-st" data-a="150" x="310" y="200">healthy</text>
<path class="ygd-tl" d="M24 208v5M76 208v5M128 208v5M180 208v5M232 208v5M284 208v5M336 208v5"/>
<text class="ygd-tick" data-t="0" x="24" y="226">0초</text>
<text class="ygd-tick" data-t="30" x="76" y="226">30</text>
<text class="ygd-tick" data-t="60" x="128" y="226">60</text>
<text class="ygd-tick" data-t="90" x="180" y="226">90</text>
<text class="ygd-tick" data-t="120" x="232" y="226">120</text>
<text class="ygd-tick" data-t="150" x="284" y="226">150</text>
<text class="ygd-tick" data-t="180" x="334" y="226">180초</text>
<g class="ygd-dot" data-t="30" data-k="ok"><circle cx="76" cy="170" r="9"/><text x="76" y="174">1</text></g>
<g class="ygd-dot" data-t="60" data-k="ok"><circle cx="128" cy="170" r="9"/><text x="128" y="174">2</text></g>
<g class="ygd-dot" data-t="90" data-k="ok"><circle cx="180" cy="170" r="9"/><text x="180" y="174">3</text></g>
<g class="ygd-dot" data-t="120" data-k="ok"><circle cx="232" cy="170" r="9"/><text x="232" y="174">4</text></g>
<g class="ygd-dot" data-t="150" data-k="ok"><circle cx="284" cy="170" r="9"/><text x="284" y="174">5</text></g>
<g class="ygd-dot" data-t="180" data-k="ok"><circle cx="334" cy="170" r="9"/><text x="334" y="174">✓</text></g>
</g>
<g>
<text class="ygd-lt" x="8" y="246">unhealthy_threshold = 3</text>
<text class="ygd-lr" x="352" y="246">90초 후 라우팅 제외</text>
<text class="ygd-ls" x="8" y="262">0초 = healthy 타겟의 첫 실패 · 연속 실패 3회</text>
<rect class="ygd-ghost ygd-c-warn" x="24" y="296" width="156" height="24"/>
<rect class="ygd-ghost ygd-c-mute" x="180" y="296" width="156" height="24"/>
<rect class="ygd-fill ygd-c-warn" data-a="0" data-b="90" x="24" y="296" width="156" height="24"/>
<rect class="ygd-fill ygd-c-mute" data-a="90" data-b="180" x="180" y="296" width="156" height="24"/>
<line class="ygd-div" x1="180" y1="296" x2="180" y2="320"/>
<rect class="ygd-outline" x="24" y="296" width="312" height="24"/>
<text class="ygd-st" data-a="0" x="102" y="312">실패 누적 · 라우팅 유지</text>
<text class="ygd-st" data-a="90" x="258" y="312">라우팅 제외</text>
<path class="ygd-tl" d="M24 320v5M76 320v5M128 320v5M180 320v5M232 320v5M284 320v5M336 320v5"/>
<text class="ygd-tick" data-t="0" x="24" y="338">0초</text>
<text class="ygd-tick" data-t="30" x="76" y="338">30</text>
<text class="ygd-tick" data-t="60" x="128" y="338">60</text>
<text class="ygd-tick" data-t="90" x="180" y="338">90</text>
<text class="ygd-tick" data-t="120" x="232" y="338">120</text>
<text class="ygd-tick" data-t="150" x="284" y="338">150</text>
<text class="ygd-tick" data-t="180" x="334" y="338">180초</text>
<g class="ygd-dot" data-t="30" data-k="bad"><circle cx="76" cy="282" r="9"/><text x="76" y="286">1</text></g>
<g class="ygd-dot" data-t="60" data-k="bad"><circle cx="128" cy="282" r="9"/><text x="128" y="286">2</text></g>
<g class="ygd-dot" data-t="90" data-k="bad"><circle cx="180" cy="282" r="9"/><text x="180" y="286">3</text></g>
</g>
</svg>
<ul class="ygd-legend">
<li><span class="ygd-sw ygd-sw-warn"></span>healthy 전환 대기</li>
<li><span class="ygd-sw ygd-sw-bad"></span>default action으로 떨어져 503</li>
<li><span class="ygd-sw ygd-sw-ok"></span>healthy · 라우팅 대상</li>
<li><span class="ygd-sw ygd-sw-mute"></span>라우팅 제외</li>
</ul>
<div class="ygd-controls">
<button type="button" class="ygd-btn ygd-primary" data-ygd="play">재생</button>
<button type="button" class="ygd-btn" data-ygd="next">다음 단계</button>
<button type="button" class="ygd-btn" data-ygd="reset">처음으로</button>
</div>
<div class="ygd-panel" aria-live="polite">
<p class="ygd-ptitle" data-ygd="title"></p>
<p class="ygd-ptext" data-ygd="text"></p>
</div>
<p class="ygd-note">비유: 신입이 현장에 투입되려면 점검을 연속으로 N번 통과해야 하는 수습 기간과 비슷하다. 실제 동작의 기준은 위 설정값(간격 30초, 임계값)이다.</p>
<script>
(function(){
var root=document.getElementById('ygd-target-group-health-check-timeline');
if(!root)return;
var STEPS=[
{t:0,h:'0초 · 컨테이너 등록 직후',x:'헬스체크는 30초 간격(설정 가능)으로 /health에 200을 기대한다. 위 두 줄은 새 컨테이너가 healthy가 되는 과정이고, 아래 줄은 healthy였던 타겟이 제외되는 과정이다.'},
{t:30,h:'30초 · 첫 헬스체크',x:'위 두 줄은 200을 받아 연속 성공 1회째다. 아래 줄은 반대로 실패 1회째이고, 아직 라우팅 대상이다.'},
{t:60,h:'60초 · 임계값 2는 여기서 healthy',x:'임계값 2는 연속 2회 성공으로 60초 만에 healthy가 되어 트래픽을 받기 시작한다. 임계값 5는 아직 2/5라 healthy가 아니다.'},
{t:90,h:'90초 · 라우팅에서 제외되는 시점',x:'아래 줄은 실패가 3회 쌓여 unhealthy_threshold에 도달했고, 이 타겟은 라우팅에서 제외된다. 임계값 5는 3/5이며 모든 트래픽이 default action으로 떨어진다.'},
{t:120,h:'120초 · 503 구간 지속',x:'임계값 5는 4/5다. 새 컨테이너가 떠 있는데도 healthy 타겟이 없어 default action으로 떨어지는 상태가 이어진다.'},
{t:150,h:'150초 · 임계값 5는 여기서 healthy',x:'연속 5회 성공으로 healthy가 된다. 첫 배포 후 2분 30초간 이어진 503 구간이 여기서 끝난다.'},
{t:180,h:'180초 · 비교 정리',x:'이후에는 두 줄 모두 정상 라우팅이다. 임계값을 2에서 5로 올리면 healthy까지의 대기가 60초에서 150초로 늘어난다. 새 컨테이너인데 503이 나면 healthy_threshold부터 확인한다.'}
];
var N=STEPS.length;
var fills=root.querySelectorAll('.ygd-fill');
var sts=root.querySelectorAll('.ygd-st');
var dots=root.querySelectorAll('.ygd-dot');
var ticks=root.querySelectorAll('.ygd-tick');
var bPlay=root.querySelector('[data-ygd="play"]');
var bNext=root.querySelector('[data-ygd="next"]');
var bReset=root.querySelector('[data-ygd="reset"]');
var pTitle=root.querySelector('[data-ygd="title"]');
var pText=root.querySelector('[data-ygd="text"]');
var step=0,timer=null;
function clamp(v){return v<0?0:(v>1?1:v);}
function render(){
var T=STEPS[step].t,i;
for(i=0;i<fills.length;i++){
var a=+fills[i].getAttribute('data-a'),b=+fills[i].getAttribute('data-b');
fills[i].style.transform='scaleX('+clamp((T-a)/(b-a))+')';
}
for(i=0;i<sts.length;i++){
var sa=+sts[i].getAttribute('data-a');
sts[i].classList.toggle('ygd-act',T>0&&T>=sa);
}
for(i=0;i<dots.length;i++){
var dt=+dots[i].getAttribute('data-t'),k=dots[i].getAttribute('data-k');
dots[i].classList.toggle('ygd-d-ok',dt<=T&&k==='ok');
dots[i].classList.toggle('ygd-d-bad',dt<=T&&k==='bad');
dots[i].classList.toggle('ygd-cur',dt===T);
}
for(i=0;i<ticks.length;i++){
ticks[i].classList.toggle('ygd-on',+ticks[i].getAttribute('data-t')===T);
}
pTitle.textContent='단계 '+(step+1)+' / '+N+' · '+STEPS[step].h;
pText.textContent=STEPS[step].x;
bNext.disabled=step>=N-1;
bPlay.textContent=timer?'일시정지':(step>=N-1?'다시 재생':'재생');
}
function stop(){if(timer){clearInterval(timer);timer=null;}}
function tick(){
if(step<N-1){step++;render();}
if(step>=N-1){stop();render();}
}
bPlay.addEventListener('click',function(){
if(timer){stop();render();return;}
if(step>=N-1){step=0;}
render();
timer=setInterval(tick,1800);
bPlay.textContent='일시정지';
});
bNext.addEventListener('click',function(){stop();if(step<N-1)step++;render();});
bReset.addEventListener('click',function(){stop();step=0;render();});
render();
})();
</script>
</div>

## STEP 5. ALB → 프라이빗 서브넷 (ECS Task ENI)

### awsvpc 네트워크 모드

ECS Fargate와 EC2 launch type 중 awsvpc 모드를 쓰면 task마다 자체 ENI가 생긴다. 이 ENI는 프라이빗 서브넷 안에 위치하며 고유한 프라이빗 IP를 가진다. 컨테이너는 host의 IP를 공유하지 않고 자기 IP로 통신한다.

bridge 모드라면 task가 EC2 host의 ENI를 공유하면서 동적 포트 매핑을 쓰지만, awsvpc는 task = ENI라서 컨테이너 → S3 같은 아웃바운드도 host와 무관하게 task ENI로 나간다. ECS Fargate는 사실상 awsvpc 모드만 지원한다.

```json
{
  "family": "upload-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/upload-task-role",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "123456789012.dkr.ecr.ap-northeast-2.amazonaws.com/upload:1.2.3",
      "portMappings": [
        { "containerPort": 8080, "protocol": "tcp" }
      ],
      "essential": true
    }
  ]
}
```

`executionRoleArn`은 ECS agent가 ECR pull, CloudWatch Logs 쓰기에 쓰는 role이고, `taskRoleArn`은 컨테이너 프로세스가 AWS API를 호출할 때 쓰는 role이다. S3 putObject 권한은 taskRole에 붙는다. 이 둘을 혼동하면 컨테이너는 떠 있는데 S3 호출이 403으로 떨어진다.

### SG 체인 — ALB → ECS Task

ALB에서 ECS task로 트래픽이 가려면 두 SG가 짝을 이뤄야 한다.

```hcl
resource "aws_security_group" "ecs_task" {
  name   = "upload-task-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # ALB SG에서만 인바운드 허용
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

ingress의 `security_groups`로 ALB SG를 지정하면 ALB ENI에서 오는 트래픽만 허용된다. CIDR로 잡으면 같은 서브넷의 다른 자원도 접근 가능해진다. SG 간 참조가 보안상 더 좁다.

### ALB → Task 패킷 경로

ALB ENI는 퍼블릭 서브넷, Task ENI는 프라이빗 서브넷에 있다. 같은 VPC라서 IGW나 NAT GW를 거치지 않고 VPC 내부 라우팅으로 직접 간다. 패킷 흐름은 이렇다.

```
ALB ENI (10.0.11.42, public subnet)
    │
    │  ALB가 application 레이어에서 새 TCP 연결을 만든다 (HTTP/1.1 keepalive)
    │  source IP: ALB ENI의 프라이빗 IP
    │  destination IP: target group에 등록된 task ENI IP
    v
[ALB SG egress] → [NACL public outbound] → [VPC 라우팅] → [NACL private inbound]
    │
    v
[ECS Task SG ingress: 8080]
    │
    v
ECS Task ENI (10.0.21.55, private subnet) → 컨테이너 8080
```

여기서 중요한 건 source IP다. ALB는 클라이언트의 진짜 IP를 그대로 넘기지 않는다. 컨테이너 입장에서 보이는 source IP는 ALB ENI의 프라이빗 IP다. 클라이언트의 실제 IP는 `X-Forwarded-For` 헤더에 들어 있다.

```python
# Flask 예시
from flask import request

@app.route("/upload", methods=["POST"])
def upload():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    # client_ip가 콤마로 여러 개 들어올 수 있음 (proxy chain)
    real_ip = client_ip.split(",")[0].strip()
    ...
```

`X-Forwarded-For`는 신뢰할 수 있는 proxy를 거쳤을 때만 쓴다. ALB 앞에 CloudFront가 있고, 그 앞에 또 다른 LB가 있으면 헤더가 chain으로 쌓인다. 가장 왼쪽이 실제 클라이언트지만, 클라이언트가 임의로 헤더를 위조할 수 있으므로 신뢰 경계를 정확히 잡아야 한다.

### NACL/SG 평가 순서 정리

ALB → Task 한 방향 패킷의 평가 순서다.

```
[ALB ENI에서 패킷 송출]
    │
    v
[ALB SG egress 평가]            ← 허용되어야 나갈 수 있음
    │
    v
[퍼블릭 서브넷 NACL outbound]   ← stateless, 별도 평가
    │
    v
   VPC 내부 라우팅 (라우팅 테이블 local 엔트리)
    │
    v
[프라이빗 서브넷 NACL inbound]  ← stateless
    │
    v
[Task SG ingress 평가]           ← 8080 허용 여부
    │
    v
[Task ENI 수신]
```

응답 패킷(Task → ALB)은 반대 방향으로 같은 게이트를 다시 거친다. SG는 stateful이라 연결을 기억하지만 NACL은 stateless라 양방향 모두 명시적 허용이 필요하다.

---

## STEP 6. ECS가 S3에 파일 업로드

### 두 가지 경로 — NAT Gateway vs S3 Gateway Endpoint

프라이빗 서브넷의 ECS task가 `s3.ap-northeast-2.amazonaws.com`을 호출하려면 트래픽이 VPC 밖으로 나가야 한다. 두 가지 방법이 있다.

**경로 A: NAT Gateway**

```
Task ENI (private subnet)
    │
    │  destination: s3.ap-northeast-2.amazonaws.com (퍼블릭 IP)
    │  라우팅 테이블: 0.0.0.0/0 → nat-gw-xxxx
    v
NAT Gateway (퍼블릭 서브넷)
    │
    │  source IP를 NAT GW의 EIP로 NAT
    v
IGW
    │
    v
인터넷
    │
    v
S3 퍼블릭 엔드포인트
```

**경로 B: S3 Gateway VPC Endpoint**

```
Task ENI (private subnet)
    │
    │  destination: s3.ap-northeast-2.amazonaws.com
    │  라우팅 테이블: pl-XXXX (S3 prefix list) → vpce-xxxx
    v
S3 Gateway Endpoint (VPC 내부)
    │
    v
S3 (인터넷 거치지 않음)
```

차이는 셋이다.

첫째, 비용. NAT GW는 데이터 처리량당 0.045 USD/GB(서울 기준)를 받는다. S3에 1TB 올리면 NAT GW 처리비만 45 USD가 추가로 나온다. Gateway Endpoint는 무료다.

둘째, 보안 경계. NAT 경로는 인터넷을 거친다(TLS는 끝까지 유지되지만 경로상 퍼블릭). Gateway Endpoint는 AWS 내부망에만 머문다.

셋째, 라우팅 방식. Gateway Endpoint는 ENI를 만들지 않고 라우팅 테이블에 prefix list를 박는 방식이다. 그래서 `vpc_endpoint_type = "Gateway"`로 만들어진 건 S3와 DynamoDB뿐이다. 나머지는 모두 Interface Endpoint(ENI 기반, PrivateLink).

```hcl
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-northeast-2.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:PutObject", "s3:GetObject"]
      Resource = [
        "arn:aws:s3:::upload-bucket",
        "arn:aws:s3:::upload-bucket/*"
      ]
    }]
  })
}
```

`route_table_ids`에 등록한 라우팅 테이블에 S3 prefix list 라우트가 자동으로 박힌다. 이 라우팅 테이블에 연결된 서브넷의 트래픽 중 S3로 가는 것만 Endpoint를 타고, 나머지는 기존 0.0.0.0/0(NAT GW) 라우트를 탄다.

<div class="ygd-nat-vs-s3-gateway-endpoint" id="ygd-nat-vs-s3-gateway-endpoint" data-tab="a">
<style>
.ygd-nat-vs-s3-gateway-endpoint{--ygd-bg:#FDFBFA;--ygd-card:#FFFFFF;--ygd-text:#2B2623;--ygd-muted:#5E5852;--ygd-line:#D9D3CC;--ygd-accent:#0E7490;--ygd-accent-soft:rgba(14,116,144,0.15);--ygd-on-accent:#FFFFFF;--ygd-route:#4338CA;--ygd-cost:#9A4406;--ygd-sec:#047857;--ygd-tag-bg:#F4F1ED;--ygd-focus:#1D4ED8;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;font-size:15px;line-height:1.55;color:var(--ygd-text);background:var(--ygd-bg);border:1px solid var(--ygd-line);border-radius:12px;padding:16px;overflow-wrap:anywhere}
body[data-md-color-scheme="slate"] .ygd-nat-vs-s3-gateway-endpoint{--ygd-bg:#1F1C1E;--ygd-card:#2A2629;--ygd-text:#F0EDE9;--ygd-muted:#B5AEA6;--ygd-line:#4A4448;--ygd-accent:#67E8F9;--ygd-accent-soft:rgba(103,232,249,0.18);--ygd-on-accent:#0B1F24;--ygd-route:#A5B4FC;--ygd-cost:#FCD34D;--ygd-sec:#6EE7B7;--ygd-tag-bg:#332E31;--ygd-focus:#93C5FD}
.ygd-nat-vs-s3-gateway-endpoint *{box-sizing:border-box}
.ygd-nat-vs-s3-gateway-endpoint .ygd-head{font-size:16px;font-weight:700;margin:0 0 12px;color:var(--ygd-text)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tabs{display:flex;gap:8px;margin:0 0 10px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tab{flex:1 1 0;min-width:0;min-height:44px;font:inherit;font-size:14px;font-weight:600;line-height:1.35;margin:0;padding:8px 10px;border:1.5px solid var(--ygd-line);border-radius:8px;background:var(--ygd-card);color:var(--ygd-text);cursor:pointer}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tab[aria-selected="true"]{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-on-accent)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-ctrl{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-btn{min-height:40px;font:inherit;font-size:14px;font-weight:600;margin:0;padding:8px 14px;border:1.5px solid var(--ygd-line);border-radius:8px;background:var(--ygd-card);color:var(--ygd-text);cursor:pointer}
.ygd-nat-vs-s3-gateway-endpoint .ygd-btn-p{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-on-accent)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-btn[disabled]{opacity:0.5;cursor:not-allowed}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tab:focus-visible,.ygd-nat-vs-s3-gateway-endpoint .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-stage{position:relative;padding:4px 0 4px 40px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-spine{position:absolute;left:0;top:0;width:36px;pointer-events:none;overflow:visible}
.ygd-nat-vs-s3-gateway-endpoint .ygd-spine .ygd-base{stroke:var(--ygd-line);stroke-width:3}
.ygd-nat-vs-s3-gateway-endpoint .ygd-spine .ygd-prog{stroke:var(--ygd-accent);stroke-width:3}
.ygd-nat-vs-s3-gateway-endpoint .ygd-spine .ygd-dot{fill:var(--ygd-card);stroke:var(--ygd-line);stroke-width:2.5}
.ygd-nat-vs-s3-gateway-endpoint .ygd-spine .ygd-dot-on{fill:var(--ygd-accent);stroke:var(--ygd-accent)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-spine .ygd-pkt{fill:var(--ygd-accent);stroke:var(--ygd-card);stroke-width:3}
.ygd-nat-vs-s3-gateway-endpoint .ygd-list{display:block}
.ygd-nat-vs-s3-gateway-endpoint .ygd-hop{display:grid;grid-template-columns:minmax(0,220px) minmax(0,1fr);gap:8px 14px;align-items:start;padding:8px 0;transition:opacity 0.3s}
.ygd-nat-vs-s3-gateway-endpoint .ygd-hop.ygd-pending{opacity:0.55}
.ygd-nat-vs-s3-gateway-endpoint .ygd-node{display:block;padding:8px 12px;border:1.5px solid var(--ygd-line);border-radius:10px;background:var(--ygd-card);transition:border-color 0.3s,box-shadow 0.3s}
.ygd-nat-vs-s3-gateway-endpoint .ygd-hop.ygd-active .ygd-node{border-color:var(--ygd-accent);box-shadow:0 0 0 3px var(--ygd-accent-soft)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-node-name{display:block;font-size:15px;font-weight:700;color:var(--ygd-text)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-node-sub{display:block;font-size:14px;color:var(--ygd-muted)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tags{display:flex;flex-direction:column;gap:6px;min-width:0}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag{display:block;font-size:14px;line-height:1.45;padding:6px 10px;border-radius:6px;background:var(--ygd-tag-bg);border-left:4px solid var(--ygd-muted);color:var(--ygd-text)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag-k{font-weight:700;margin-right:6px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag[data-k="route"]{border-left-color:var(--ygd-route)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag[data-k="route"] .ygd-tag-k{color:var(--ygd-route)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag[data-k="cost"]{border-left-color:var(--ygd-cost)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag[data-k="cost"] .ygd-tag-k{color:var(--ygd-cost)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag[data-k="sec"]{border-left-color:var(--ygd-sec)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-tag[data-k="sec"] .ygd-tag-k{color:var(--ygd-sec)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-panel{margin:14px 0 10px;padding:12px 14px;min-height:7.2em;border:1.5px solid var(--ygd-accent);border-radius:10px;background:var(--ygd-card)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-panel-t{font-size:14px;font-weight:700;color:var(--ygd-accent);margin:0 0 4px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-panel-b{font-size:15px;color:var(--ygd-text)}
.ygd-nat-vs-s3-gateway-endpoint .ygd-analogy{font-size:14px;color:var(--ygd-muted);margin:0}
@media (max-width:600px){
.ygd-nat-vs-s3-gateway-endpoint{padding:12px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-stage{padding-left:36px}
.ygd-nat-vs-s3-gateway-endpoint .ygd-hop{grid-template-columns:minmax(0,1fr)}
}
@media (prefers-reduced-motion:reduce){
.ygd-nat-vs-s3-gateway-endpoint,.ygd-nat-vs-s3-gateway-endpoint *{transition:none !important}
}
</style>
<div class="ygd-head">Task ENI에서 S3까지, 패킷이 거치는 홉</div>
<div class="ygd-tabs" role="tablist" aria-label="경로 선택">
<button type="button" class="ygd-tab" role="tab" id="ygd-nat-vs-s3-gateway-endpoint-tab-a" aria-selected="true" aria-controls="ygd-nat-vs-s3-gateway-endpoint-stage" data-k="a">경로 A · NAT Gateway</button>
<button type="button" class="ygd-tab" role="tab" id="ygd-nat-vs-s3-gateway-endpoint-tab-b" aria-selected="false" aria-controls="ygd-nat-vs-s3-gateway-endpoint-stage" tabindex="-1" data-k="b">경로 B · S3 Gateway Endpoint</button>
</div>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-btn-p" data-act="play">재생</button>
<button type="button" class="ygd-btn" data-act="next">다음 단계</button>
<button type="button" class="ygd-btn" data-act="reset">처음으로</button>
</div>
<div class="ygd-stage" id="ygd-nat-vs-s3-gateway-endpoint-stage" role="tabpanel" aria-labelledby="ygd-nat-vs-s3-gateway-endpoint-tab-a">
<svg class="ygd-spine" role="img" aria-label="Task ENI에서 S3까지 패킷이 지나는 경로" focusable="false" width="36" height="200" viewBox="0 0 36 200">
<line class="ygd-base" x1="18" x2="18" y1="0" y2="0"></line>
<line class="ygd-prog" x1="18" x2="18" y1="0" y2="0"></line>
<g class="ygd-dots"></g>
<circle class="ygd-pkt" cx="18" cy="0" r="9"></circle>
</svg>
<div class="ygd-list" role="list"></div>
</div>
<div class="ygd-panel" aria-live="polite">
<div class="ygd-panel-t"></div>
<div class="ygd-panel-b"></div>
</div>
<p class="ygd-analogy">비유: 경로 A는 건물 정문을 나가 공용 도로를 거쳐 창고에 가는 길이고, 경로 B는 건물에서 창고로 바로 이어진 전용 통로다. 비유일 뿐이므로 실제 차이는 위의 홉과 태그를 기준으로 본다.</p>
<script>
(function () {
var root = document.getElementById("ygd-nat-vs-s3-gateway-endpoint");
if (!root) { return; }
var KIND = { route: "라우팅", cost: "비용", sec: "보안 경계" };
var DATA = {
a: {
label: "경로 A: NAT Gateway를 거쳐 인터넷으로 나가는 경로",
hops: [
{ name: "Task ENI", sub: "프라이빗 서브넷",
tags: [["route", "목적지는 s3.ap-northeast-2.amazonaws.com, 즉 S3의 퍼블릭 IP"]],
desc: "프라이빗 서브넷의 Task ENI가 s3.ap-northeast-2.amazonaws.com 으로 패킷을 보낸다. 목적지가 퍼블릭 IP라서 트래픽이 VPC 밖으로 나가야 한다." },
{ name: "라우팅 테이블", sub: "0.0.0.0/0 → nat-gw-xxxx",
tags: [["route", "기본 라우트(0.0.0.0/0)가 NAT Gateway를 가리킨다"]],
desc: "라우팅 테이블의 0.0.0.0/0 → nat-gw-xxxx 라우트에 매치되어 패킷이 NAT Gateway로 향한다." },
{ name: "NAT Gateway", sub: "퍼블릭 서브넷",
tags: [["route", "source IP를 NAT GW의 EIP로 NAT한다"], ["cost", "데이터 처리량당 0.045 USD/GB (서울 기준). S3에 1TB를 올리면 NAT GW 처리비만 45 USD가 추가된다"]],
desc: "퍼블릭 서브넷의 NAT Gateway가 source IP를 NAT GW의 EIP로 바꿔 내보낸다. 이 구간을 지나는 데이터량마다 처리비가 붙는다." },
{ name: "IGW", sub: "인터넷 게이트웨이",
tags: [["sec", "IGW를 거쳐 VPC 밖으로 나간다"]],
desc: "패킷이 IGW를 지나 VPC 밖으로 나간다. 이 경로에는 IGW가 반드시 들어간다." },
{ name: "인터넷", sub: "퍼블릭 경로",
tags: [["sec", "TLS는 끝까지 유지되지만 경로상으로는 퍼블릭이다"]],
desc: "TLS는 끝까지 유지되지만, 패킷은 경로상 퍼블릭 인터넷을 지난다. 보안 경계가 AWS 내부망에 머물지 않는다." },
{ name: "S3 퍼블릭 엔드포인트", sub: "s3.ap-northeast-2.amazonaws.com",
tags: [["cost", "업로드한 데이터량만큼 NAT GW 처리비가 따라붙는다"]],
desc: "패킷이 S3 퍼블릭 엔드포인트에 도착한다. 업로드한 데이터량만큼 NAT GW 처리비가 함께 발생한다." }
]
},
b: {
label: "경로 B: S3 Gateway Endpoint로 VPC 내부에서 S3에 닿는 경로",
hops: [
{ name: "Task ENI", sub: "프라이빗 서브넷",
tags: [["route", "목적지는 경로 A와 같은 s3.ap-northeast-2.amazonaws.com"]],
desc: "프라이빗 서브넷의 Task ENI가 s3.ap-northeast-2.amazonaws.com 으로 패킷을 보낸다. 목적지 주소는 경로 A와 같다." },
{ name: "라우팅 테이블", sub: "pl-XXXX (S3 prefix list) → vpce-xxxx",
tags: [["route", "라우팅 테이블에 S3 prefix list 라우트를 박는 방식이다"], ["route", "S3로 가는 트래픽만 Endpoint를 타고, 나머지는 기존 0.0.0.0/0(NAT GW) 라우트를 탄다"]],
desc: "pl-XXXX(S3 prefix list) → vpce-xxxx 라우트에 매치되어 패킷이 Endpoint로 향한다. 이 테이블에서 S3 외의 트래픽은 기존 0.0.0.0/0 라우트를 그대로 탄다." },
{ name: "S3 Gateway Endpoint", sub: "VPC 내부",
tags: [["cost", "무료"], ["route", "ENI를 만들지 않는다. Gateway 타입은 S3와 DynamoDB뿐이고, 나머지는 Interface Endpoint(ENI 기반, PrivateLink)다"], ["sec", "IGW·NAT GW 없이 AWS 내부망에만 머문다"]],
desc: "S3 Gateway Endpoint는 VPC 내부에 있고 ENI를 만들지 않는다. 이 경로에는 NAT GW도 IGW도 끼지 않고, Endpoint 자체의 비용은 없다." },
{ name: "S3", sub: "인터넷을 거치지 않음",
tags: [["sec", "인터넷을 거치지 않고 도착한다"]],
desc: "패킷이 인터넷을 거치지 않고 S3에 도착한다. 경로 A와 달리 NAT GW 처리비가 붙지 않는다." }
]
}
};
var tabs = root.querySelectorAll(".ygd-tab");
var stage = root.querySelector(".ygd-stage");
var list = root.querySelector(".ygd-list");
var svg = root.querySelector(".ygd-spine");
var base = root.querySelector(".ygd-base");
var prog = root.querySelector(".ygd-prog");
var dotsG = root.querySelector(".ygd-dots");
var pkt = root.querySelector(".ygd-pkt");
var panelT = root.querySelector(".ygd-panel-t");
var panelB = root.querySelector(".ygd-panel-b");
var btnPlay = root.querySelector('[data-act="play"]');
var btnNext = root.querySelector('[data-act="next"]');
var btnReset = root.querySelector('[data-act="reset"]');
var NS = "http://www.w3.org/2000/svg";
var tab = "a", step = -1, playing = false, timer = null, raf = null;
var ys = [], curY = 0, rows = [];
var reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
function hops() { return DATA[tab].hops; }
function last() { return hops().length - 1; }
function el(tag, cls, text) {
var e = document.createElement(tag);
if (cls) { e.className = cls; }
if (text) { e.textContent = text; }
return e;
}
function buildRows() {
list.textContent = "";
rows = [];
hops().forEach(function (h) {
var row = el("div", "ygd-hop");
row.setAttribute("role", "listitem");
var node = el("div", "ygd-node");
node.appendChild(el("span", "ygd-node-name", h.name));
node.appendChild(el("span", "ygd-node-sub", h.sub));
var tags = el("div", "ygd-tags");
h.tags.forEach(function (t) {
var tg = el("div", "ygd-tag");
tg.setAttribute("data-k", t[0]);
tg.appendChild(el("span", "ygd-tag-k", KIND[t[0]]));
tg.appendChild(document.createTextNode(t[1]));
tags.appendChild(tg);
});
row.appendChild(node);
row.appendChild(tags);
list.appendChild(row);
rows.push(row);
});
}
function draw() {
if (!ys.length) { return; }
pkt.setAttribute("cy", curY);
prog.setAttribute("y1", ys[0]);
prog.setAttribute("y2", curY);
}
function target() { return ys.length ? ys[Math.max(step, 0)] : 0; }
function moveTo(y) {
if (raf) { cancelAnimationFrame(raf); raf = null; }
if (!reduce || reduce.matches) { curY = y; draw(); return; }
var from = curY, t0 = null;
function f(t) {
if (t0 === null) { t0 = t; }
var p = Math.min(1, (t - t0) / 600);
var e = 0.5 > p ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
curY = from + (y - from) * e;
draw();
if (1 > p) { raf = requestAnimationFrame(f); } else { raf = null; }
}
raf = requestAnimationFrame(f);
}
function layout() {
var sr = stage.getBoundingClientRect();
ys = rows.map(function (r) {
var nr = r.querySelector(".ygd-node").getBoundingClientRect();
return nr.top - sr.top + nr.height / 2;
});
svg.setAttribute("height", sr.height);
svg.setAttribute("viewBox", "0 0 36 " + sr.height);
base.setAttribute("y1", ys[0]);
base.setAttribute("y2", ys[ys.length - 1]);
dotsG.textContent = "";
ys.forEach(function (y) {
var c = document.createElementNS(NS, "circle");
c.setAttribute("class", "ygd-dot");
c.setAttribute("cx", 18);
c.setAttribute("cy", y);
c.setAttribute("r", 6);
dotsG.appendChild(c);
});
markDots();
if (raf) { cancelAnimationFrame(raf); raf = null; }
curY = target();
draw();
}
function markDots() {
var cs = dotsG.childNodes;
for (var i = 0; cs.length > i; i++) {
cs[i].setAttribute("class", step >= i ? "ygd-dot ygd-dot-on" : "ygd-dot");
}
}
function updateButtons() {
btnPlay.textContent = playing ? "일시정지" : (step >= last() ? "다시 재생" : "재생");
btnNext.disabled = step >= last();
}
function render() {
rows.forEach(function (r, i) {
var cls = "ygd-hop";
if (step >= 0) {
if (i === step) { cls += " ygd-active"; }
else if (i > step) { cls += " ygd-pending"; }
}
r.className = cls;
});
if (0 > step) {
panelT.textContent = "준비 · " + DATA[tab].label;
panelB.textContent = "재생을 누르면 Task ENI에서 S3까지 " + hops().length + "개 홉을 차례로 따라간다. 홉 옆의 태그에 라우팅 방식, 비용, 보안 경계 차이가 붙어 있다.";
} else {
var h = hops()[step];
panelT.textContent = "단계 " + (step + 1) + " / " + hops().length + " · " + h.name;
panelB.textContent = h.desc;
}
markDots();
updateButtons();
moveTo(target());
}
function go(s) { step = s; render(); }
function stop() {
playing = false;
if (timer) { clearTimeout(timer); timer = null; }
updateButtons();
}
function play() {
if (playing) { stop(); return; }
if (step >= last()) { step = -1; }
playing = true;
function loop() {
if (!playing) { return; }
go(step + 1);
if (step >= last()) { stop(); return; }
timer = setTimeout(loop, 2600);
}
loop();
}
function setTab(k) {
stop();
tab = k;
root.setAttribute("data-tab", k);
for (var i = 0; tabs.length > i; i++) {
var on = tabs[i].getAttribute("data-k") === k;
tabs[i].setAttribute("aria-selected", on ? "true" : "false");
tabs[i].setAttribute("tabindex", on ? "0" : "-1");
if (on) { stage.setAttribute("aria-labelledby", tabs[i].id); }
}
svg.setAttribute("aria-label", DATA[k].label);
step = -1;
buildRows();
layout();
render();
}
for (var i = 0; tabs.length > i; i++) {
(function (t) {
t.addEventListener("click", function () { setTab(t.getAttribute("data-k")); });
t.addEventListener("keydown", function (ev) {
var k = ev.key, to = null;
if (k === "ArrowRight" || k === "ArrowLeft") { to = tab === "a" ? "b" : "a"; }
else if (k === "Home") { to = "a"; }
else if (k === "End") { to = "b"; }
if (to) {
ev.preventDefault();
setTab(to);
root.querySelector('.ygd-tab[data-k="' + to + '"]').focus();
}
});
})(tabs[i]);
}
btnPlay.addEventListener("click", play);
btnNext.addEventListener("click", function () {
stop();
if (last() > step) { go(step + 1); }
});
btnReset.addEventListener("click", function () { stop(); go(-1); });
if (window.ResizeObserver) {
new ResizeObserver(function () { layout(); }).observe(stage);
} else {
window.addEventListener("resize", layout);
}
setTab("a");
})();
</script>
</div>

### VPC Endpoint policy의 함정

위 정책에서 `Resource`를 `*`로 두면 모든 S3 버킷에 접근 가능해진다. 보안팀이 데이터 유출 방지를 위해 좁혀 두는 게 흔하다. 그런데 여기서 빠지기 쉬운 함정이 있다.

ECR이 컨테이너 이미지를 저장하는 S3 버킷도 있다. ECS Fargate가 이미지를 pull할 때 내부적으로 S3에 접근한다. Endpoint policy에 사용자 버킷만 적어 두면 ECR pull이 실패하면서 task가 안 뜬다. CloudWatch Logs도 마찬가지로 내부적으로 S3 버킷을 쓴다.

ECR/Logs 관련 버킷까지 허용해야 한다.

```hcl
policy = jsonencode({
  Version = "2012-10-17"
  Statement = [
    {
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:PutObject", "s3:GetObject"]
      Resource = [
        "arn:aws:s3:::upload-bucket",
        "arn:aws:s3:::upload-bucket/*"
      ]
    },
    {
      # ECR 이미지 레이어 저장소
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject"]
      Resource = [
        "arn:aws:s3:::prod-ap-northeast-2-starport-layer-bucket/*"
      ]
    }
  ]
})
```

이 prod-ap-northeast-2-starport-layer-bucket은 AWS가 관리하는 ECR의 내부 버킷이다. 리전마다 이름이 다르다.

### IAM 권한 — Task Role의 putObject

컨테이너가 S3에 PutObject를 호출하려면 Task Role에 권한이 있어야 한다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:AbortMultipartUpload",
        "s3:ListBucketMultipartUploads",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "arn:aws:s3:::upload-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::upload-bucket"
    }
  ]
}
```

PutObject만 있고 multipart 관련 액션이 없으면 큰 파일 업로드가 중간에 실패한다. AWS SDK는 5MB 이상 파일을 자동으로 multipart로 쪼개 올리는데, `CreateMultipartUpload`, `UploadPart`, `CompleteMultipartUpload`는 `s3:PutObject` 권한으로 커버되지만, 중간 실패 시 정리하는 `AbortMultipartUpload`는 별도 권한이다. 이게 없으면 실패한 업로드 잔재가 버킷에 쌓여 비용으로 돌아온다.

`Resource`도 자주 틀린다. `arn:aws:s3:::upload-bucket`은 버킷 자체에 대한 리소스고(`ListBucket`용), `arn:aws:s3:::upload-bucket/*`이 객체에 대한 리소스다(`PutObject`용). 둘을 헷갈리면 403이 떨어진다.

### Multipart upload — 컨테이너 안에서 일어나는 일

5MB 이상의 파일을 받았을 때 SDK가 multipart upload를 어떻게 진행하는지 보면 이렇다.

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    config=Config(
        retries={"max_attempts": 3, "mode": "adaptive"},
        max_pool_connections=20,
    ),
)

# 자동 multipart — managed upload
s3.upload_file(
    Filename="/tmp/large.bin",
    Bucket="upload-bucket",
    Key="uploads/2026/05/large.bin",
    Config=boto3.s3.transfer.TransferConfig(
        multipart_threshold=8 * 1024 * 1024,   # 8MB 넘으면 multipart
        multipart_chunksize=8 * 1024 * 1024,
        max_concurrency=10,
    ),
)
```

SDK 내부에서 일어나는 일을 다이어그램으로 보면:

```mermaid
sequenceDiagram
    participant App as ECS 컨테이너
    participant SDK as boto3
    participant S3 as S3 API

    App->>SDK: upload_file(large.bin)
    SDK->>S3: CreateMultipartUpload
    S3-->>SDK: UploadId=abc123

    par 병렬 업로드
        SDK->>S3: UploadPart #1 (UploadId=abc123, PartNumber=1)
        S3-->>SDK: ETag-1
    and
        SDK->>S3: UploadPart #2 (UploadId=abc123, PartNumber=2)
        S3-->>SDK: ETag-2
    and
        SDK->>S3: UploadPart #3 (UploadId=abc123, PartNumber=3)
        S3-->>SDK: ETag-3
    end

    SDK->>S3: CompleteMultipartUpload(parts=[ETag-1,2,3])
    S3-->>SDK: 200 OK
    SDK-->>App: 업로드 완료
```

여기서 알아 둘 점이 몇 가지 있다.

`UploadPart` 호출 하나하나가 별도의 TCP 연결이다(SDK는 connection pool로 재사용한다). 각각이 NAT GW나 S3 Endpoint를 거친다. 컨테이너의 SG egress가 일시적으로 다수의 outbound connection을 처리해야 한다는 뜻이다.

업로드 도중 컨테이너가 죽으면 진행 중이던 multipart는 버킷에 "incomplete multipart upload"로 남는다. S3 Lifecycle 정책으로 7일 후 자동 삭제하도록 걸어 두는 게 안전하다.

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "upload" {
  bucket = aws_s3_bucket.upload.id

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
```

### S3로 향하는 패킷의 평가 순서

`PutObject` 한 번의 outbound 패킷 흐름은 이렇다(Gateway Endpoint 경로 기준).

```
컨테이너 프로세스
    │
    │  boto3 → HTTPS 연결 시도
    v
Task ENI (프라이빗 IP, 프라이빗 서브넷)
    │
    │  destination: s3.ap-northeast-2.amazonaws.com → DNS 조회
    │
    │  Endpoint 활성 상태라면 DNS가 VPC 내부 IP를 반환
    │
    v
[Task SG egress 평가]                    ← 443 허용 필요
    │
    v
[프라이빗 서브넷 NACL outbound]          ← stateless
    │
    v
[라우팅 테이블 평가]                      ← pl-XXXX → vpce-xxxx
    │
    v
S3 Gateway Endpoint
    │
    v
[Endpoint Policy 평가]                    ← 버킷 ARN 매칭 확인
    │
    v
[S3 Bucket Policy 평가]                   ← Principal/Action/Resource 확인
    │
    v
[IAM Task Role 권한 평가]                 ← s3:PutObject 권한 확인
    │
    v
S3 PutObject 실행
```

응답이 오면 stateful SG는 자동 허용하지만, NACL은 outbound 응답을 위해 ephemeral port(1024-65535) inbound 허용이 필요하다.

---

## 자주 마주치는 트러블슈팅 사례

### 사례 1: ALB로는 닿는데 컨테이너에서 502가 떨어진다

증상: 브라우저에서 요청하면 502 Bad Gateway. ALB CloudWatch 메트릭에서 `HTTPCode_ELB_502_Count`가 올라간다.

원인 후보:
1. ECS task가 healthy로 잡혀 있지만 실제로는 8080을 안 열고 있음 (헬스체크 경로와 실제 포트가 다른 경우)
2. 컨테이너가 응답을 보내는데 ALB가 keepalive 끊김을 처리 못 함 (컨테이너의 idle timeout이 ALB의 idle timeout(기본 60초)보다 짧으면 발생)
3. 컨테이너가 응답을 보내기 전에 OOM으로 죽음

확인 순서:
```bash
# 컨테이너에서 직접 healthcheck 호출
aws ecs execute-command --cluster prod --task <task-id> --container app \
  --interactive --command "/bin/sh"

# 컨테이너 내부에서
curl -v http://localhost:8080/health
```

컨테이너 안에서 200이 안 떨어지면 애플리케이션 문제다. 200이 떨어지는데 ALB가 502를 내면 keepalive timeout이 의심된다. 애플리케이션의 idle timeout을 ALB(60초)보다 길게(예: 75초) 잡는 게 정석이다.

### 사례 2: 새 환경에서 S3 putObject가 403

증상: 컨테이너 로그에 `An error occurred (AccessDenied) when calling the PutObject operation`.

확인 순서:
1. Task Role의 정책 — `aws iam list-attached-role-policies --role-name upload-task-role`
2. 정책 내용에서 `Resource`의 ARN이 실제 버킷과 일치하는지 (`upload-bucket-prod` vs `upload-bucket-dev` 같은 오타)
3. 버킷 정책에 deny가 있는지 — `aws s3api get-bucket-policy --bucket upload-bucket`
4. S3 Gateway Endpoint policy가 좁혀져 있어 차단되는지
5. SSE-KMS 암호화 버킷이면 `kms:GenerateDataKey` 권한도 필요

403이 떨어지면 어디서 막혔는지 메시지로는 거의 알 수 없다. CloudTrail에서 PutObject 이벤트를 찾으면 정확한 deny 원인이 나온다.

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --max-results 10
```

### 사례 3: 프라이빗 서브넷에서 인터넷이 안 됨

증상: 컨테이너가 외부 API(예: Stripe, 외부 OAuth)에 못 닿는다. S3는 잘 됨.

원인: S3는 Gateway Endpoint로 빠지는데 NAT GW가 없거나 라우팅 테이블에 0.0.0.0/0이 없는 경우다. Endpoint가 잘 동작해서 S3는 되니까 "네트워크가 되는 줄" 착각한다.

확인:
```bash
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=subnet-xxxx" \
  --query 'RouteTables[].Routes'
```

여기서 `0.0.0.0/0`에 대한 라우팅이 NAT GW를 가리키지 않으면 인터넷이 안 된다. `pl-xxxx → vpce-xxxx`만 있고 `0.0.0.0/0`이 없으면 S3 외에는 다 막힌다.

### 사례 4: ALB Listener Rule 매칭이 의도와 다름

증상: `/api/admin`은 admin target group으로 보내려 했는데 default action으로 떨어진다.

원인: path_pattern에서 `/api/admin`만 적고 `/api/admin/*`을 안 적었다. ALB는 정확히 매칭이라 `/api/admin/users` 같은 하위 경로가 안 잡힌다.

```hcl
condition {
  path_pattern {
    values = ["/api/admin", "/api/admin/*"]  # 둘 다 필요
  }
}
```

### 사례 5: VPC Endpoint가 동작하지 않는다

증상: Gateway Endpoint를 만들었는데 컨테이너에서 S3 호출이 여전히 NAT GW를 탄다(VPC Flow Logs에서 확인).

원인 후보:
1. Endpoint의 `route_table_ids`에 컨테이너 서브넷이 연결된 라우팅 테이블이 빠져 있음
2. Endpoint policy가 너무 좁아 deny되고 SDK가 IAM은 통과한 줄 알고 NAT로 fallback하는 게 아니라 그냥 403 (이 경우는 별도 사고)
3. S3 SDK가 다른 리전 엔드포인트를 호출하는 경우 (`us-east-1` 리전의 버킷을 서울 리전 Endpoint로 가려 하면 안 됨)

확인:
```bash
aws ec2 describe-vpc-endpoints --vpc-endpoint-ids vpce-xxxx \
  --query 'VpcEndpoints[].[RouteTableIds,State,PolicyDocument]'
```

route_table_ids가 비어 있거나 의도한 라우팅 테이블이 빠져 있으면 prefix list 라우트가 안 박힌다.

---

## 전체 평가 순서 한눈에 보기

요청 한 번이 들어와 응답이 나가기까지 평가되는 게이트를 다 적으면 이렇다.

**인바운드 (클라이언트 → 컨테이너):**

```
[1] DNS — Route 53 hosted zone alias → ALB A 레코드
[2] IGW — VPC route 0.0.0.0/0 → igw-xxxx
[3] Public Subnet NACL inbound — 443/80, ephemeral
[4] ALB SG inbound — 443/80
[5] ALB Listener — TLS termination + 인증서 매칭
[6] ALB Listener Rule — priority 순 평가
[7] Target Group — healthy target 선택 (stickiness 적용)
[8] ALB SG egress
[9] Public Subnet NACL outbound
[10] VPC 내부 라우팅 (local)
[11] Private Subnet NACL inbound
[12] Task SG inbound — 8080 from ALB SG
[13] 컨테이너 처리
```

**아웃바운드 (컨테이너 → S3):**

```
[14] Task SG egress — 443 to anywhere or S3 prefix list
[15] Private Subnet NACL outbound
[16] 라우팅 테이블 — pl-XXXX → vpce-xxxx (Endpoint 경로) 또는 0.0.0.0/0 → nat-xxxx
[17] (NAT 경로일 때) NAT GW EIP로 source NAT
[18] (NAT 경로일 때) IGW 통과
[19] S3 Endpoint Policy 평가
[20] S3 Bucket Policy 평가
[21] Task IAM Role 권한 평가
[22] S3 PutObject 실행
```

응답은 SG가 stateful이라 자동 허용되지만, NACL은 stateless라 모든 게이트의 반대 방향도 명시적으로 열려 있어야 한다. 패킷이 막혔을 때 위 22단계 중 어디서 막혔는지 좁히는 게 디버깅이다. 보통 5분 안에 막힌 단계를 찾고, 나머지 시간은 정확한 원인 파악과 수정에 쓴다.

---

## 참고할 운영 팁

VPC Flow Logs는 매번 켜 두는 게 좋다. 패킷이 막혔을 때 어느 ENI에서 ACCEPT/REJECT가 떨어졌는지가 로그에 남아 디버깅 시간을 크게 줄인다.

```hcl
resource "aws_flow_log" "vpc" {
  log_destination      = aws_cloudwatch_log_group.flow.arn
  log_destination_type = "cloud-watch-logs"
  traffic_type         = "ALL"
  vpc_id               = aws_vpc.main.id
  iam_role_arn         = aws_iam_role.flow_log.arn
}
```

ALB Access Log는 S3에 적재한다. 클라이언트 IP, 요청 시각, 응답 코드, target group 처리 시간이 다 들어 있어 ALB 단의 문제와 컨테이너 단의 문제를 가를 때 가장 빠른 근거가 된다. Athena로 쿼리하면 5분 안에 502가 어느 target에서 났는지 찾는다.

ECS Service의 deployment_circuit_breaker도 켜 둔다. 헬스체크에 실패하는 새 task가 계속 뜨다 죽는 무한 루프를 막아 준다.

```hcl
resource "aws_ecs_service" "upload" {
  # ...
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
```

이 전체 흐름은 처음 설계할 때보다 운영하면서 더 자주 마주친다. 새 환경을 만들 때마다 22단계 게이트 중 한두 개가 빠지고, 빠진 게이트가 어디인지 찾는 데 한 시간씩 쓴다. 패턴이 머리에 박히면 SG 누락인지 라우팅인지 IAM인지 증상만 보고 30초 안에 좁혀진다.
