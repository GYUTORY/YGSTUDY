---
title: TCP 프로토콜 동작 메커니즘
tags: [network, tcp, observability]
updated: 2026-06-03
---

# TCP 프로토콜 동작 메커니즘

## TCP 연결 수립: 3-Way Handshake

TCP는 데이터를 보내기 전에 반드시 연결을 수립한다. 이 과정이 3-Way Handshake다.

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: SYN (seq=100)
    Note right of C: 1단계: 연결 요청
    S->>C: SYN+ACK (seq=300, ack=101)
    Note left of S: 2단계: 요청 수락 + 자기 시퀀스 전달
    C->>S: ACK (ack=301)
    Note right of C: 3단계: 확인 응답

    Note over C,S: 연결 수립 완료
```

각 단계에서 일어나는 일을 구체적으로 보면:

**1단계 - SYN**: 클라이언트가 ISN(Initial Sequence Number)을 생성한다. ISN은 랜덤 값이다. 예전에는 시간 기반으로 증가하는 값을 썼는데, TCP sequence prediction attack 때문에 랜덤으로 바뀌었다.

**2단계 - SYN+ACK**: 서버도 자기 ISN을 생성하고, 클라이언트의 SYN에 대한 ACK를 보낸다. ACK 번호는 클라이언트의 seq + 1이다. SYN 자체가 시퀀스 번호 1개를 소비하기 때문이다.

**3단계 - ACK**: 클라이언트가 서버의 SYN에 대한 ACK를 보낸다. 이 패킷부터 데이터를 실어 보낼 수 있다.

### SYN Backlog와 SYN Flood 공격

서버가 SYN을 받으면 SYN 큐(반연결 큐)에 저장한다. ACK가 돌아와서 연결이 완료되면 Accept 큐(완전연결 큐)로 옮긴다.

```mermaid
flowchart LR
    A[SYN 수신] --> B["SYN 큐<br/>(반연결 큐)"]
    B --> C[ACK 수신]
    C --> D["Accept 큐<br/>(완전연결 큐)"]
    D --> E["accept() 호출"]
```

SYN Flood 공격은 SYN만 대량으로 보내고 ACK를 보내지 않아 SYN 큐를 가득 채우는 방식이다. 리눅스에서의 대응:

```bash
# SYN 큐 크기 확인
cat /proc/sys/net/ipv4/tcp_max_syn_backlog

# SYN Cookie 활성화 - SYN 큐를 사용하지 않고 쿠키로 검증
sysctl net.ipv4.tcp_syncookies=1

# Accept 큐 크기 - listen() 호출 시 backlog 파라미터로 결정
cat /proc/sys/net/core/somaxconn
```

실무에서 `listen(fd, backlog)`의 backlog 값을 너무 작게 잡으면 트래픽이 몰릴 때 연결이 거부된다. Nginx 기본값은 511이고, 고트래픽 서비스에서는 `somaxconn`과 함께 늘려야 한다.


## TCP 연결 종료: 4-Way Termination

연결 종료는 양쪽 모두 데이터 전송이 끝났음을 확인해야 하기 때문에 4단계가 필요하다.

```mermaid
sequenceDiagram
    participant C as Client (Active Close)
    participant S as Server (Passive Close)

    C->>S: FIN (seq=500)
    Note right of C: 1단계: 종료 요청<br/>Client → FIN_WAIT_1

    S->>C: ACK (ack=501)
    Note left of S: 2단계: FIN 수신 확인<br/>Client → FIN_WAIT_2<br/>Server → CLOSE_WAIT

    Note over S: 서버가 남은 데이터 전송

    S->>C: FIN (seq=700)
    Note left of S: 3단계: 서버도 종료 요청<br/>Server → LAST_ACK

    C->>S: ACK (ack=701)
    Note right of C: 4단계: 확인 응답<br/>Client → TIME_WAIT<br/>Server → CLOSED

    Note over C: 2MSL 대기 후 CLOSED
```

2단계와 3단계 사이에 서버가 아직 보낼 데이터가 있으면 계속 보낼 수 있다. 그래서 3-way가 아니라 4-way다. 실제로는 서버에 보낼 데이터가 없으면 2단계와 3단계가 합쳐져서 FIN+ACK가 한 패킷으로 가는 경우도 있다.


## TCP 상태 전이

TCP 연결은 여러 상태를 거친다. 서버 운영 시 자주 보게 되는 상태를 중심으로 정리한다.

```mermaid
stateDiagram-v2
    [*] --> CLOSED

    CLOSED --> LISTEN : passive open
    CLOSED --> SYN_SENT : active open<br/>SYN 전송

    LISTEN --> SYN_RCVD : SYN 수신<br/>SYN+ACK 전송
    SYN_SENT --> SYN_RCVD : SYN 수신<br/>SYN+ACK 전송
    SYN_SENT --> ESTABLISHED : SYN+ACK 수신<br/>ACK 전송

    SYN_RCVD --> ESTABLISHED : ACK 수신

    ESTABLISHED --> FIN_WAIT_1 : close()<br/>FIN 전송
    ESTABLISHED --> CLOSE_WAIT : FIN 수신<br/>ACK 전송

    FIN_WAIT_1 --> FIN_WAIT_2 : ACK 수신
    FIN_WAIT_1 --> CLOSING : FIN 수신<br/>ACK 전송

    FIN_WAIT_2 --> TIME_WAIT : FIN 수신<br/>ACK 전송

    CLOSING --> TIME_WAIT : ACK 수신

    TIME_WAIT --> CLOSED : 2MSL 타이머 만료

    CLOSE_WAIT --> LAST_ACK : close()<br/>FIN 전송
    LAST_ACK --> CLOSED : ACK 수신
```

CLOSING 상태는 양쪽이 동시에 FIN을 보내는 경우(simultaneous close)에 나타난다. 실무에서 자주 보이지는 않지만, `ss` 출력에서 간혹 관찰된다.

### 실무에서 문제가 되는 상태들

**CLOSE_WAIT 누적**: 서버 프로세스에 CLOSE_WAIT이 쌓이면 서버 쪽 코드에서 `close()`를 호출하지 않고 있다는 뜻이다. 상대방이 FIN을 보냈는데 우리 쪽이 소켓을 닫지 않는 상황이다. 커넥션 풀에서 죽은 연결을 반환하지 않거나, 예외 처리에서 소켓 close를 빠뜨린 경우에 생긴다.

```bash
# CLOSE_WAIT 상태 연결 확인
ss -tnp state close-wait

# 특정 포트의 CLOSE_WAIT 개수
ss -tn state close-wait | grep :8080 | wc -l
```

CLOSE_WAIT은 커널이 자동으로 정리하지 않는다. 프로세스가 직접 close()를 호출해야 한다. 프로세스가 죽어야 정리되므로, CLOSE_WAIT이 계속 쌓이면 코드를 고쳐야 한다.

**TIME_WAIT 누적**: Active Close를 한 쪽에서 발생한다. HTTP 서버가 먼저 연결을 끊으면 서버에 TIME_WAIT이 쌓이고, 클라이언트가 먼저 끊으면 클라이언트에 쌓인다.

TIME_WAIT은 원래 2MSL(Maximum Segment Lifetime) 동안 유지하도록 정의돼 있다. 다만 리눅스는 MSL 을 재서 곱하지 않고 지속시간 자체를 `TCP_TIMEWAIT_LEN` 60초로 커널에 박아 뒀다. 그래서 실제로는 60초다.

TIME_WAIT이 존재하는 이유:
1. 마지막 ACK가 유실됐을 때 재전송된 FIN을 처리하기 위해
2. 이전 연결의 지연된 패킷이 새 연결에 영향을 주지 않도록 격리하기 위해

```bash
# TIME_WAIT 상태 개수 확인
ss -tn state time-wait | wc -l

# TIME_WAIT 재사용 허용 (클라이언트 측에서 유용)
sysctl net.ipv4.tcp_tw_reuse=1
```

`tcp_tw_reuse`는 TIME_WAIT 상태의 소켓을 새 연결에 재사용하되, 타임스탬프를 비교해서 안전한 경우에만 재사용한다. 서버 간 통신이 많은 경우(예: API 서버에서 DB나 Redis로 연결할 때) 유용하다.

`tcp_tw_recycle`은 커널 4.12에서 삭제되었다. NAT 환경에서 같은 IP 뒤의 다른 클라이언트 패킷을 드롭하는 문제가 있었다.


## 혼잡 제어

네트워크에 패킷이 너무 많으면 라우터가 패킷을 버리기 시작한다. TCP 혼잡 제어는 이 문제를 보내는 쪽에서 조절하는 메커니즘이다.

### 기본 개념: cwnd와 ssthresh

- **cwnd (Congestion Window)**: 한 번에 보낼 수 있는 패킷 수. ACK를 받지 않은 상태로 네트워크에 내보낼 수 있는 양이다.
- **ssthresh (Slow Start Threshold)**: Slow Start에서 Congestion Avoidance로 전환하는 기준점.

실제로 보낼 수 있는 양은 `min(cwnd, rwnd)`다. rwnd는 수신 측의 Window Size.

### Slow Start

연결 초기에 cwnd를 빠르게 늘린다. cwnd가 1에서 시작해서 ACK를 받을 때마다 1씩 증가한다. RTT당 cwnd가 2배씩 늘어나는 셈이다.

```mermaid
xychart-beta
    title "Slow Start: RTT별 cwnd 변화"
    x-axis "RTT" [1, 2, 3, 4, 5, 6, 7]
    y-axis "cwnd (segments)" 0 --> 70
    line [1, 2, 4, 8, 16, 32, 64]
```

| RTT | cwnd | 동작 |
|-----|------|------|
| 1 | 1 | 1 세그먼트 전송, ACK 1개 수신 |
| 2 | 2 | 2 세그먼트 전송, ACK 2개 수신 |
| 3 | 4 | 4 세그먼트 전송, ACK 4개 수신 |
| 4 | 8 | 8 세그먼트 전송, ACK 8개 수신 |
| ... | ... | cwnd가 ssthresh에 도달하면 Congestion Avoidance로 전환 |

리눅스의 초기 cwnd(initcwnd)는 10이다. `ip route` 명령어로 확인하고 변경할 수 있다.

```bash
# 현재 initcwnd 확인
ip route show | grep initcwnd

# initcwnd 변경
ip route change default via 10.0.0.1 initcwnd 20
```

### Congestion Avoidance

cwnd가 ssthresh에 도달하면 증가 속도를 줄인다. RTT당 cwnd가 1씩 선형으로 증가한다.

패킷 손실이 감지되면:
- **타임아웃**: cwnd를 1로 초기화, ssthresh = cwnd/2. Slow Start부터 다시 시작.
- **중복 ACK 3개 (Fast Retransmit)**: ssthresh = cwnd/2, cwnd = ssthresh + 3. Congestion Avoidance부터 시작. 타임아웃보다 덜 심각한 상황으로 판단하기 때문이다.

아래 그래프는 타임아웃과 Fast Retransmit 발생 시 cwnd 변화를 보여준다.

```mermaid
xychart-beta
    title "혼잡 제어: cwnd 변화 흐름 (Slow Start → Congestion Avoidance → 손실 대응)"
    x-axis "RTT" [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    y-axis "cwnd (segments)" 0 --> 40
    line "cwnd" [1, 2, 4, 8, 16, 17, 18, 19, 20, 21, 22, 23, 24, 1, 2, 4, 8, 12, 13, 14, 15]
```

- RTT 0~4: Slow Start (지수 증가, ssthresh=16)
- RTT 4~12: Congestion Avoidance (선형 증가)
- RTT 13: 타임아웃 발생 → cwnd=1로 초기화, ssthresh=12
- RTT 13~17: Slow Start (ssthresh=12까지)
- RTT 17~: Congestion Avoidance 재진입

<div class="ygd-tcp-loss-response-cwnd" id="ygd-tcp-loss-response-cwnd">
<style>
.ygd-tcp-loss-response-cwnd{--ygd-bg:#ffffff;--ygd-panel:#f6f4f2;--ygd-text:#1f1c1e;--ygd-muted:#736E68;--ygd-border:#d9d5d0;--ygd-grid:#e4e0dc;--ygd-timeout:#B4411F;--ygd-fast:#1B6A8A;--ygd-ss:#6B4FA0;--ygd-band-ss:#F6DFB4;--ygd-band-ca:#C7E2EC;--ygd-sel-bg:#3D7387;--ygd-sel-text:#ffffff;--ygd-focus:#1B6A8A;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;background:var(--ygd-bg);color:var(--ygd-text);border:1px solid var(--ygd-border);border-radius:10px;padding:14px;margin-top:1em;margin-bottom:1em;font-size:14px;line-height:1.55}
body[data-md-color-scheme="slate"] .ygd-tcp-loss-response-cwnd{--ygd-bg:#262326;--ygd-panel:#302c2f;--ygd-text:#F0EDE9;--ygd-muted:#A8A29A;--ygd-border:#4a4548;--ygd-grid:#3d393c;--ygd-timeout:#FF8A65;--ygd-fast:#6BC4E2;--ygd-ss:#B9A3F0;--ygd-band-ss:#6B5017;--ygd-band-ca:#1F5368;--ygd-sel-bg:#6BC4E2;--ygd-sel-text:#1F1C1E;--ygd-focus:#6BC4E2}
.ygd-tcp-loss-response-cwnd *{box-sizing:border-box}
.ygd-tcp-loss-response-cwnd .ygd-title{font-size:16px;font-weight:700;margin:0 0 4px 0}
.ygd-tcp-loss-response-cwnd .ygd-lead{font-size:14px;color:var(--ygd-muted);margin:0 0 10px 0}
.ygd-tcp-loss-response-cwnd .ygd-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.ygd-tcp-loss-response-cwnd .ygd-group{display:flex;flex-wrap:wrap;gap:6px}
.ygd-tcp-loss-response-cwnd .ygd-spacer{flex:1 1 8px}
.ygd-tcp-loss-response-cwnd .ygd-btn{font:inherit;font-size:14px;font-weight:600;min-height:40px;padding:6px 14px;border-radius:8px;border:1px solid var(--ygd-border);background:var(--ygd-panel);color:var(--ygd-text);cursor:pointer;margin:0}
.ygd-tcp-loss-response-cwnd .ygd-btn[aria-pressed="true"]{background:var(--ygd-sel-bg);color:var(--ygd-sel-text);border-color:var(--ygd-sel-bg)}
.ygd-tcp-loss-response-cwnd .ygd-btn:hover{border-color:var(--ygd-muted)}
.ygd-tcp-loss-response-cwnd .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-tcp-loss-response-cwnd .ygd-legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:14px;color:var(--ygd-muted);margin:0 0 6px 0}
.ygd-tcp-loss-response-cwnd .ygd-lg{display:inline-flex;align-items:center;gap:6px}
.ygd-tcp-loss-response-cwnd .ygd-sw{display:inline-block;width:14px;height:10px;border-radius:2px;border:1px solid var(--ygd-border)}
.ygd-tcp-loss-response-cwnd .ygd-sw-ss{background:var(--ygd-band-ss)}
.ygd-tcp-loss-response-cwnd .ygd-sw-ca{background:var(--ygd-band-ca)}
.ygd-tcp-loss-response-cwnd .ygd-svg{display:block;width:100%;max-width:560px;height:auto;margin:0 auto}
.ygd-tcp-loss-response-cwnd .ygd-tx{fill:var(--ygd-muted);font-size:11px}
.ygd-tcp-loss-response-cwnd .ygd-tx-strong{fill:var(--ygd-text);font-size:11px;font-weight:700}
.ygd-tcp-loss-response-cwnd .ygd-grid{stroke:var(--ygd-grid);stroke-width:1}
.ygd-tcp-loss-response-cwnd .ygd-axis{stroke:var(--ygd-muted);stroke-width:1}
.ygd-tcp-loss-response-cwnd .ygd-band-ss{fill:var(--ygd-band-ss)}
.ygd-tcp-loss-response-cwnd .ygd-band-ca{fill:var(--ygd-band-ca)}
.ygd-tcp-loss-response-cwnd .ygd-band-tx{fill:var(--ygd-text);font-size:10px;font-weight:700}
.ygd-tcp-loss-response-cwnd .ygd-lossline{stroke:var(--ygd-muted);stroke-width:1;stroke-dasharray:2 3}
.ygd-tcp-loss-response-cwnd .ygd-ssline{fill:none;stroke:var(--ygd-ss);stroke-width:2;stroke-dasharray:6 3}
.ygd-tcp-loss-response-cwnd .ygd-sstx{fill:var(--ygd-ss);font-size:11px;font-weight:700}
.ygd-tcp-loss-response-cwnd .ygd-ghost{fill:none;stroke:var(--ygd-muted);stroke-width:2;stroke-dasharray:3 4}
.ygd-tcp-loss-response-cwnd .ygd-ln-timeout{fill:none;stroke:var(--ygd-timeout);stroke-width:2.5;stroke-linejoin:round}
.ygd-tcp-loss-response-cwnd .ygd-ln-fast{fill:none;stroke:var(--ygd-fast);stroke-width:2.5;stroke-linejoin:round}
.ygd-tcp-loss-response-cwnd .ygd-dot-timeout{fill:var(--ygd-timeout)}
.ygd-tcp-loss-response-cwnd .ygd-dot-fast{fill:var(--ygd-fast)}
.ygd-tcp-loss-response-cwnd .ygd-head-timeout{fill:var(--ygd-timeout);stroke:var(--ygd-bg);stroke-width:2}
.ygd-tcp-loss-response-cwnd .ygd-head-fast{fill:var(--ygd-fast);stroke:var(--ygd-bg);stroke-width:2}
.ygd-tcp-loss-response-cwnd .ygd-end-timeout{fill:var(--ygd-timeout);font-size:11px;font-weight:700}
.ygd-tcp-loss-response-cwnd .ygd-end-fast{fill:var(--ygd-fast);font-size:11px;font-weight:700}
.ygd-tcp-loss-response-cwnd .ygd-end-dim{fill:var(--ygd-muted);font-size:11px}
.ygd-tcp-loss-response-cwnd .ygd-panel{background:var(--ygd-panel);border:1px solid var(--ygd-border);border-radius:8px;padding:10px 12px;margin-top:8px;min-height:9.5em}
.ygd-tcp-loss-response-cwnd .ygd-step-t{font-size:14px;font-weight:700;margin:0 0 4px 0}
.ygd-tcp-loss-response-cwnd .ygd-step-d{font-size:14px;margin:0 0 6px 0}
.ygd-tcp-loss-response-cwnd .ygd-readout{font-size:14px;color:var(--ygd-muted);font-variant-numeric:tabular-nums;margin:0}
.ygd-tcp-loss-response-cwnd .ygd-cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}
.ygd-tcp-loss-response-cwnd .ygd-card{border:2px solid var(--ygd-border);border-radius:8px;padding:8px 10px;background:var(--ygd-bg);min-width:0}
.ygd-tcp-loss-response-cwnd .ygd-card.ygd-on{border-color:var(--ygd-text)}
.ygd-tcp-loss-response-cwnd .ygd-card-h{font-size:14px;font-weight:700;margin:0 0 4px 0}
.ygd-tcp-loss-response-cwnd .ygd-card-timeout .ygd-card-h{color:var(--ygd-timeout)}
.ygd-tcp-loss-response-cwnd .ygd-card-fast .ygd-card-h{color:var(--ygd-fast)}
.ygd-tcp-loss-response-cwnd .ygd-row{display:block;font-size:14px;margin:0 0 4px 0;overflow-wrap:anywhere}
.ygd-tcp-loss-response-cwnd .ygd-k{display:block;color:var(--ygd-muted);font-size:14px}
.ygd-tcp-loss-response-cwnd .ygd-v{display:block;font-weight:600}
.ygd-tcp-loss-response-cwnd .ygd-note{font-size:14px;color:var(--ygd-muted);margin:10px 0 0 0}
@media (max-width:420px){.ygd-tcp-loss-response-cwnd{padding:10px}.ygd-tcp-loss-response-cwnd .ygd-card{padding:6px 8px}}
@media (prefers-reduced-motion:reduce){.ygd-tcp-loss-response-cwnd *{transition:none !important;animation:none !important}}
</style>
<div class="ygd-title">손실 대응 비교: 타임아웃 vs 중복 ACK 3개</div>
<div class="ygd-lead">같은 지점(cwnd 24, ssthresh 16)에서 손실이 감지돼도 감지 방식에 따라 cwnd와 ssthresh가 다시 시작하는 위치가 달라진다.</div>
<div class="ygd-controls">
<div class="ygd-group" role="group" aria-label="손실 시나리오 선택">
<button type="button" class="ygd-btn ygd-sc-btn" data-sc="timeout" aria-pressed="true">타임아웃</button>
<button type="button" class="ygd-btn ygd-sc-btn" data-sc="fast" aria-pressed="false">중복 ACK 3개</button>
</div>
<span class="ygd-spacer"></span>
<div class="ygd-group">
<button type="button" class="ygd-btn ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-reset">초기화</button>
</div>
</div>
<div class="ygd-legend">
<span class="ygd-lg"><span class="ygd-sw ygd-sw-ss"></span>SS: Slow Start</span>
<span class="ygd-lg"><span class="ygd-sw ygd-sw-ca"></span>CA: Congestion Avoidance</span>
<span class="ygd-lg">보라 점선: ssthresh</span>
<span class="ygd-lg">회색 점선: 비교용 다른 시나리오</span>
</div>
<svg class="ygd-svg" viewBox="0 0 360 264" role="img" aria-label="TCP 혼잡 제어 cwnd 곡선" preserveAspectRatio="xMidYMid meet">
<g class="ygd-g-static"></g>
<g class="ygd-g-dyn"></g>
</svg>
<div class="ygd-panel">
<div class="ygd-step-t" aria-live="polite"></div>
<div class="ygd-step-d" aria-live="polite"></div>
<div class="ygd-readout"></div>
</div>
<div class="ygd-cards">
<div class="ygd-card ygd-card-timeout" data-sc="timeout">
<div class="ygd-card-h">타임아웃</div>
<div class="ygd-row"><span class="ygd-k">감지</span><span class="ygd-v">타임아웃 발생</span></div>
<div class="ygd-row"><span class="ygd-k">ssthresh</span><span class="ygd-v">24 / 2 = 12</span></div>
<div class="ygd-row"><span class="ygd-k">cwnd</span><span class="ygd-v">1로 초기화</span></div>
<div class="ygd-row"><span class="ygd-k">재시작</span><span class="ygd-v">Slow Start부터</span></div>
</div>
<div class="ygd-card ygd-card-fast" data-sc="fast">
<div class="ygd-card-h">중복 ACK 3개</div>
<div class="ygd-row"><span class="ygd-k">감지</span><span class="ygd-v">같은 ACK가 3번 중복</span></div>
<div class="ygd-row"><span class="ygd-k">ssthresh</span><span class="ygd-v">24 / 2 = 12</span></div>
<div class="ygd-row"><span class="ygd-k">cwnd</span><span class="ygd-v">12 + 3 = 15</span></div>
<div class="ygd-row"><span class="ygd-k">재시작</span><span class="ygd-v">Congestion Avoidance부터</span></div>
</div>
</div>
<div class="ygd-note">비유: 도로가 막혔을 때 타임아웃은 완전히 멈췄다가 다시 가속하는 상황, 중복 ACK 3개는 뒤따르는 차들이 계속 도착하는 걸 보고 속도만 줄여 계속 가는 상황에 가깝다. 비유일 뿐이고 실제 조정은 위 규칙을 따른다.</div>
<div class="ygd-note">손실 시점 cwnd 24는 본문 그래프와 같은 가정이다. 중복 ACK 쪽 이후 곡선은 본문 규칙(cwnd = ssthresh + 3, Congestion Avoidance에서 RTT당 +1)으로 이어 그렸고, 중복 ACK를 받는 동안의 세부 조정은 그리지 않았다.</div>
<script>
(function(){
var root=document.getElementById('ygd-tcp-loss-response-cwnd');
if(!root){return;}
var NS='http://www.w3.org/2000/svg';
var L=34,T=42,B=228,PW=268,PH=186,YMAX=26,XMAX=20;
function px(t){return L+t*PW/XMAX;}
function py(v){return B-v*PH/YMAX;}
var PRE=[1,2,4,8,16,17,18,19,20,21,22,23,24];
var STEP_SS={end:4,title:'1단계 · Slow Start (RTT 0~4)',text:'cwnd가 1에서 시작해 RTT마다 2배씩 늘어난다. cwnd가 ssthresh 16에 도달하면 이 단계가 끝난다.'};
var STEP_CA={end:12,title:'2단계 · Congestion Avoidance (RTT 4~12)',text:'ssthresh에 도달했으므로 증가 속도를 줄여 RTT당 1씩 선형으로 늘린다. RTT 12에서 cwnd는 24다.'};
var SC={
timeout:{name:'타임아웃',endLabel:'타임아웃',post:[1,2,4,8,12,13,14,15],bands:[[12.5,17,'ss'],[17,20,'ca']],
label:'TCP 혼잡 제어 cwnd 곡선, 타임아웃 시나리오. RTT 0~4 Slow Start, RTT 4~12 Congestion Avoidance로 cwnd 24까지 늘다가 RTT 13에 타임아웃으로 cwnd가 1이 되고 ssthresh는 12가 된다. Slow Start로 RTT 17에 ssthresh에 닿은 뒤 선형으로 증가한다.',
steps:[STEP_SS,STEP_CA,
{end:13,title:'3단계 · 타임아웃 (RTT 13)',text:'손실을 타임아웃으로 감지했다. ssthresh는 24/2 = 12로 줄고, cwnd는 1로 초기화된다.'},
{end:17,title:'4단계 · Slow Start 재시작 (RTT 13~17)',text:'cwnd가 1, 2, 4, 8로 늘어나 RTT 17에서 ssthresh 12에 닿는다. 정상 구간을 처음부터 다시 쌓는 셈이다.'},
{end:20,title:'5단계 · Congestion Avoidance 재진입 (RTT 17~)',text:'ssthresh에 도달했으므로 다시 RTT당 1씩 선형으로 늘린다. RTT 20의 cwnd는 15다.'}]},
fast:{name:'중복 ACK 3개',endLabel:'중복 ACK',post:[15,16,17,18,19,20,21,22],bands:[[12.5,20,'ca']],
label:'TCP 혼잡 제어 cwnd 곡선, 중복 ACK 3개 시나리오. RTT 0~4 Slow Start, RTT 4~12 Congestion Avoidance로 cwnd 24까지 늘다가 RTT 13에 cwnd가 15로 줄고 ssthresh는 12가 된다. Slow Start 없이 Congestion Avoidance로 바로 선형 증가한다.',
steps:[STEP_SS,STEP_CA,
{end:13,title:'3단계 · 중복 ACK 3개 (RTT 13)',text:'같은 ACK가 3번 중복되어 타임아웃을 기다리지 않고 바로 재전송한다. ssthresh는 24/2 = 12, cwnd는 12+3 = 15가 된다.'},
{end:20,title:'4단계 · Congestion Avoidance 계속 (RTT 13~)',text:'타임아웃보다 덜 심각한 상황으로 판단하므로 Slow Start를 거치지 않고 cwnd 15에서 RTT당 1씩 늘린다. RTT 20의 cwnd는 22다.'}]}
};
var state={sc:'timeout',t:20,idle:true,playing:false};
var timer=null;
function q(sel){return root.querySelector(sel);}
function qa(sel){return root.querySelectorAll(sel);}
function s(tag,attrs,parent){var e=document.createElementNS(NS,tag);for(var k in attrs){e.setAttribute(k,attrs[k]);}if(parent){parent.appendChild(e);}return e;}
function txt(str,attrs,parent){var e=s('text',attrs,parent);e.textContent=str;return e;}
function reduced(){return window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;}
function series(sc){return PRE.concat(sc.post);}
var svg=q('.ygd-svg');
var gs=q('.ygd-g-static');
var gd=q('.ygd-g-dyn');
(function(){
var yv=[0,10,20];
for(var i=0;i<yv.length;i++){
s('line',{x1:L,x2:L+PW,y1:py(yv[i]),y2:py(yv[i]),'class':yv[i]===0?'ygd-axis':'ygd-grid'},gs);
txt(String(yv[i]),{x:L-6,y:py(yv[i])+4,'text-anchor':'end','class':'ygd-tx'},gs);
}
s('line',{x1:L,x2:L,y1:T,y2:B,'class':'ygd-axis'},gs);
var xv=[0,4,8,12,16,20];
for(var j=0;j<xv.length;j++){
s('line',{x1:px(xv[j]),x2:px(xv[j]),y1:B,y2:B+4,'class':'ygd-axis'},gs);
txt(String(xv[j]),{x:px(xv[j]),y:B+16,'text-anchor':'middle','class':'ygd-tx'},gs);
}
txt('RTT',{x:L+PW/2,y:B+32,'text-anchor':'middle','class':'ygd-tx'},gs);
txt('cwnd (세그먼트)',{x:11,y:(T+B)/2,'text-anchor':'middle',transform:'rotate(-90 11 '+((T+B)/2)+')','class':'ygd-tx'},gs);
})();
function render(){
var sc=SC[state.sc];
var oth=SC[state.sc==='timeout'?'fast':'timeout'];
var otherKey=state.sc==='timeout'?'fast':'timeout';
var t=state.t;
var ser=series(sc);
var oser=series(oth);
gd.textContent='';
var bands=[[0,4,'ss'],[4,12.5,'ca']].concat(sc.bands);
for(var i=0;i<bands.length;i++){
var a=bands[i][0],b=Math.min(bands[i][1],t);
if(t>a){
var w=px(b)-px(a);
s('rect',{x:px(a),y:20,width:w,height:14,rx:2,'class':'ygd-band-'+bands[i][2]},gd);
if(w>=24){txt(bands[i][2]==='ss'?'SS':'CA',{x:px(a)+w/2,y:30.5,'text-anchor':'middle','class':'ygd-band-tx'},gd);}
}
}
if(t>=13){
s('line',{x1:px(12.5),x2:px(12.5),y1:T,y2:B,'class':'ygd-lossline'},gd);
txt('손실 감지',{x:px(12.5),y:12,'text-anchor':'middle','class':'ygd-tx-strong'},gd);
}
var d='';
if(t>0){d+='M'+px(0)+' '+py(16)+'H'+px(Math.min(t,12.5));}
if(t>=13){d+='M'+px(12.5)+' '+py(16)+'V'+py(12)+'H'+px(t);}
if(d){s('path',{d:d,'class':'ygd-ssline'},gd);}
if(t>=5){txt('ssthresh = 16',{x:px(12),y:py(16)+13,'text-anchor':'end','class':'ygd-sstx'},gd);}
if(t>=13){
txt('ssthresh',{x:px(20)+6,y:py(12)+4,'class':'ygd-sstx'},gd);
txt('= 12',{x:px(20)+6,y:py(12)+17,'class':'ygd-sstx'},gd);
}
if(t>12){
var gp='';
for(var k=12;k<=t;k++){gp+=(k===12?'M':'L')+px(k)+' '+py(oser[k]);}
s('path',{d:gp,'class':'ygd-ghost'},gd);
}
var pts='';
for(var m=0;m<=t;m++){pts+=(m===0?'M':'L')+px(m)+' '+py(ser[m]);}
if(t>0){s('path',{d:pts,'class':'ygd-ln-'+state.sc},gd);}
for(var n=0;n<=t;n++){s('circle',{cx:px(n),cy:py(ser[n]),r:2.5,'class':'ygd-dot-'+state.sc},gd);}
if(!state.idle){s('circle',{cx:px(t),cy:py(ser[t]),r:5.5,'class':'ygd-head-'+state.sc},gd);}
if(t>=20){
txt(sc.endLabel,{x:px(20)+6,y:py(ser[20])+4,'class':'ygd-end-'+state.sc},gd);
txt(oth.endLabel,{x:px(20)+6,y:py(oser[20])+4,'class':'ygd-end-dim'},gd);
}
svg.setAttribute('aria-label',sc.label);
panel();
}
function panel(){
var sc=SC[state.sc];
var tt=q('.ygd-step-t'),dd=q('.ygd-step-d'),ro=q('.ygd-readout');
var cards=qa('.ygd-card');
for(var c=0;c<cards.length;c++){
if(cards[c].getAttribute('data-sc')===state.sc){cards[c].classList.add('ygd-on');}else{cards[c].classList.remove('ygd-on');}
}
if(state.idle){
var tt0=sc.name+' 시나리오 전체 곡선';
var dd0=state.sc==='timeout'?'타임아웃이면 cwnd가 1로 떨어져 Slow Start부터 다시 오른다. 재생을 누르면 RTT 0부터 단계별로 진행한다.':'중복 ACK 3개면 cwnd가 ssthresh+3으로 줄고 Slow Start 없이 선형 증가한다. 재생을 누르면 RTT 0부터 단계별로 진행한다.';
if(tt.textContent!==tt0){tt.textContent=tt0;}
if(dd.textContent!==dd0){dd.textContent=dd0;}
ro.textContent='전체 보기 · 손실 시점 cwnd 24';
return;
}
var steps=sc.steps,idx=steps.length-1;
for(var i=0;i<steps.length;i++){if(state.t<=steps[i].end){idx=i;break;}}
if(tt.textContent!==steps[idx].title){tt.textContent=steps[idx].title;}
if(dd.textContent!==steps[idx].text){dd.textContent=steps[idx].text;}
ro.textContent='RTT '+state.t+' · cwnd '+series(sc)[state.t]+' · ssthresh '+(state.t>=13?12:16);
}
var playBtn=q('.ygd-play');
function setPlaying(p){
state.playing=p;
playBtn.textContent=p?'일시정지':'재생';
}
function stop(){
if(timer){clearTimeout(timer);timer=null;}
setPlaying(false);
}
function tick(){
timer=null;
var sc=SC[state.sc];
var nt=state.t+1;
if(reduced()){
nt=20;
for(var i=0;i<sc.steps.length;i++){if(sc.steps[i].end>state.t){nt=sc.steps[i].end;break;}}
}
state.t=Math.min(nt,20);
render();
if(state.t>=20){stop();return;}
timer=setTimeout(tick,reduced()?1800:450);
}
function play(){
if(state.idle||state.t>=20){state.t=0;}
state.idle=false;
setPlaying(true);
render();
timer=setTimeout(tick,reduced()?1800:450);
}
playBtn.addEventListener('click',function(){
if(state.playing){stop();}else{play();}
});
q('.ygd-reset').addEventListener('click',function(){
stop();
state.t=20;
state.idle=true;
render();
});
var scBtns=qa('.ygd-sc-btn');
for(var i=0;i<scBtns.length;i++){
scBtns[i].addEventListener('click',function(){
state.sc=this.getAttribute('data-sc');
for(var j=0;j<scBtns.length;j++){scBtns[j].setAttribute('aria-pressed',scBtns[j]===this?'true':'false');}
render();
});
}
render();
})();
</script>
</div>

### Fast Retransmit과 Fast Recovery

수신 측이 순서가 맞지 않는 패킷을 받으면 마지막으로 정상 수신한 ACK를 다시 보낸다. 같은 ACK가 3번 중복되면 해당 패킷이 유실된 것으로 판단하고 타임아웃을 기다리지 않고 바로 재전송한다.

```mermaid
sequenceDiagram
    participant Sn as Sender
    participant Rc as Receiver

    Sn->>Rc: seq=1
    Rc->>Sn: ACK=2 (정상 수신)

    Sn-xRc: seq=2 (유실)

    Sn->>Rc: seq=3
    Rc->>Sn: ACK=2 (중복 1 - 순서 안 맞음)

    Sn->>Rc: seq=4
    Rc->>Sn: ACK=2 (중복 2)

    Sn->>Rc: seq=5
    Rc->>Sn: ACK=2 (중복 3)

    Note over Sn: 중복 ACK 3개 도착 → Fast Retransmit

    Sn->>Rc: seq=2 (재전송)
    Rc->>Sn: ACK=6 (버퍼에 3,4,5 있으므로)
```

### TCP Cubic

리눅스 기본 혼잡 제어 알고리즘이다. 패킷 손실이 발생하기 직전의 cwnd를 기억해두고, 손실 후 그 값에 빠르게 복귀한 다음 천천히 탐색한다. 3차 함수(cubic function) 형태로 cwnd를 조절한다.

```mermaid
xychart-beta
    title "TCP Cubic: cwnd 변화 (3차 함수 곡선)"
    x-axis "시간 (RTT)" [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    y-axis "cwnd" 0 --> 50
    line [40, 15, 10, 8, 10, 15, 25, 35, 39, 40, 41, 41, 42]
```

손실이 발생하면 cwnd가 급격히 떨어진 뒤, W_max(손실 직전 값) 근처까지 빠르게 복귀하고 그 이후로는 천천히 증가한다. 이 곡선이 3차 함수(cubic) 형태다.

RTT에 독립적이라서 장거리 고대역 네트워크(Long Fat Network)에서 성능이 좋다.

### BBR (Bottleneck Bandwidth and RTT)

Google이 만든 혼잡 제어 알고리즘이다. 패킷 손실이 아니라 실제 대역폭과 RTT를 측정해서 보내는 양을 결정한다.

기존 알고리즘(Reno, Cubic)은 패킷 손실을 혼잡의 신호로 본다. 문제는 라우터 버퍼가 큰 현대 네트워크에서 버퍼가 가득 차야 손실이 발생하므로, 이미 지연(latency)이 크게 늘어난 뒤에야 반응한다는 것이다. BBR은 지연이 늘어나기 시작하는 시점을 찾아서 그 지점에서 보내는 양을 조절한다.

```bash
# 현재 혼잡 제어 알고리즘 확인
sysctl net.ipv4.tcp_congestion_control

# BBR 사용
sysctl net.ipv4.tcp_congestion_control=bbr

# 사용 가능한 알고리즘 목록
sysctl net.ipv4.tcp_available_congestion_control
```

BBR은 패킷 손실률이 높은 환경(모바일 네트워크, 해외 구간)에서 Cubic보다 처리량이 좋다. 다만 BBR끼리 경쟁할 때 공정성 문제가 있고, BBRv2에서 개선 중이다.


## 흐름 제어: Sliding Window

흐름 제어는 수신 측이 처리할 수 있는 속도에 맞춰 보내는 양을 조절하는 메커니즘이다. 혼잡 제어가 네트워크 상태를 보는 것이라면, 흐름 제어는 상대방의 처리 능력을 보는 것이다.

### Window Size

TCP 헤더의 Window Size 필드는 수신 측이 "앞으로 이만큼 더 받을 수 있다"고 알려주는 값이다. 16비트이므로 최대 65,535 바이트인데, Window Scale 옵션을 사용하면 최대 1GB까지 늘릴 수 있다. Window Scale은 3-Way Handshake 때 협상한다.

### Sliding Window 동작

```mermaid
flowchart LR
    subgraph 전송완료["전송 완료 (ACK 수신)"]
        s1["1"] --- s2["2"] --- s3["3"] --- s4["4"]
    end
    subgraph 윈도우["전송 가능 (Window)"]
        s5["5"] --- s6["6"] --- s7["7"] --- s8["8"] --- s9["9"] --- s10["10"]
    end
    subgraph 대기["전송 불가 (Window 밖)"]
        s11["11"] --- s12["12"] --- s13["13"] --- s14["14"]
    end
    전송완료 ~~~ 윈도우 ~~~ 대기

    style 전송완료 fill:#d1fae5,stroke:#10b981
    style 윈도우 fill:#dbeafe,stroke:#3b82f6
    style 대기 fill:#fee2e2,stroke:#ef4444
```

Window 크기는 `min(cwnd, rwnd)`로 결정된다. ACK가 돌아오면 윈도우 왼쪽 경계가 오른쪽으로 이동(슬라이딩)하면서 새로운 세그먼트를 전송할 수 있게 된다.

ACK가 돌아오면 윈도우가 오른쪽으로 슬라이딩한다. 수신 측이 Window Size를 줄이면 윈도우가 줄어들고, 0이 되면 전송을 멈춘다.

### Zero Window와 Window Probe

수신 측 버퍼가 가득 차면 Window Size가 0이 된다. 송신 측은 전송을 멈추고, 주기적으로 Window Probe(1바이트짜리 패킷)를 보내서 윈도우가 열렸는지 확인한다.

애플리케이션이 소켓에서 데이터를 읽는 속도가 느리면 Zero Window가 발생한다. `ss` 명령어에서 Recv-Q가 계속 높으면 애플리케이션의 처리 속도를 의심해야 한다.

```bash
# 소켓 버퍼 상태 확인
ss -tnpi
# Recv-Q: 수신 버퍼에 쌓여 있는 데이터 (아직 read() 안 한 양)
# Send-Q: 송신 버퍼에 쌓여 있는 데이터 (아직 ACK 못 받은 양)
```

<div class="ygd-tcp-zero-window-probe" id="ygd-tcp-zero-window-probe">
<style>
.ygd-tcp-zero-window-probe{--ygd-bg:#fbfaf9;--ygd-card:#ffffff;--ygd-fg:#2b2a28;--ygd-mu:#5f5a54;--ygd-bd:#d8d3cd;--ygd-acked-bg:#d1fae5;--ygd-acked-bd:#047857;--ygd-acked-fg:#064e3b;--ygd-sent-bg:#fde68a;--ygd-sent-bd:#b45309;--ygd-sent-fg:#78350f;--ygd-open-bg:#dbeafe;--ygd-open-bd:#1d4ed8;--ygd-open-fg:#1e3a8a;--ygd-out-bg:#f1efec;--ygd-out-bd:#8a847c;--ygd-out-fg:#5f5a54;--ygd-bad-bg:#fee2e2;--ygd-bad-bd:#b91c1c;--ygd-bad-fg:#7f1d1d;--ygd-acc:#3D7387;--ygd-acc-fg:#ffffff;--ygd-focus:#1d4ed8;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:14px;border:1px solid var(--ygd-bd);border-radius:10px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:15px;line-height:1.55}
body[data-md-color-scheme="slate"] .ygd-tcp-zero-window-probe{--ygd-bg:#2a2628;--ygd-card:#352f32;--ygd-fg:#f0ede9;--ygd-mu:#b5afa7;--ygd-bd:#4f494b;--ygd-acked-bg:#064e3b;--ygd-acked-bd:#34d399;--ygd-acked-fg:#d1fae5;--ygd-sent-bg:#78350f;--ygd-sent-bd:#fbbf24;--ygd-sent-fg:#fef3c7;--ygd-open-bg:#1e3a8a;--ygd-open-bd:#93c5fd;--ygd-open-fg:#dbeafe;--ygd-out-bg:#3a3537;--ygd-out-bd:#9a948c;--ygd-out-fg:#cfc9c1;--ygd-bad-bg:#7f1d1d;--ygd-bad-bd:#fca5a5;--ygd-bad-fg:#fee2e2;--ygd-acc:#8ec3d6;--ygd-acc-fg:#1a1a1a;--ygd-focus:#93c5fd}
.ygd-tcp-zero-window-probe *{box-sizing:border-box}
.ygd-tcp-zero-window-probe .ygd-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 10px}
.ygd-tcp-zero-window-probe .ygd-btn{font:inherit;font-size:15px;line-height:1.2;min-height:44px;margin:0;padding:0 14px;border-radius:8px;border:1px solid var(--ygd-bd);background:var(--ygd-card);color:var(--ygd-fg);cursor:pointer}
.ygd-tcp-zero-window-probe .ygd-btn.ygd-primary{background:var(--ygd-acc);color:var(--ygd-acc-fg);border-color:var(--ygd-acc);font-weight:700;min-width:104px}
.ygd-tcp-zero-window-probe .ygd-btn:focus-visible,.ygd-tcp-zero-window-probe .ygd-chip:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-tcp-zero-window-probe .ygd-btn:disabled{opacity:.45;cursor:not-allowed}
.ygd-tcp-zero-window-probe .ygd-prog{margin-left:auto;font-size:14px;color:var(--ygd-mu)}
.ygd-tcp-zero-window-probe .ygd-svg{display:block;width:100%;height:auto;max-width:100%;background:var(--ygd-card);border:1px solid var(--ygd-bd);border-radius:8px}
.ygd-tcp-zero-window-probe .ygd-svg text{fill:var(--ygd-fg);font-family:inherit}
.ygd-tcp-zero-window-probe .ygd-hd{font-size:12px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-cell rect{stroke-width:1.5;transition:fill .35s,stroke .35s}
.ygd-tcp-zero-window-probe .ygd-cell text{font-size:11px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-s-acked rect{fill:var(--ygd-acked-bg);stroke:var(--ygd-acked-bd)}
.ygd-tcp-zero-window-probe .ygd-s-acked text{fill:var(--ygd-acked-fg)}
.ygd-tcp-zero-window-probe .ygd-s-sent rect{fill:var(--ygd-sent-bg);stroke:var(--ygd-sent-bd)}
.ygd-tcp-zero-window-probe .ygd-s-sent text{fill:var(--ygd-sent-fg)}
.ygd-tcp-zero-window-probe .ygd-s-open rect{fill:var(--ygd-open-bg);stroke:var(--ygd-open-bd)}
.ygd-tcp-zero-window-probe .ygd-s-open text{fill:var(--ygd-open-fg)}
.ygd-tcp-zero-window-probe .ygd-s-out rect{fill:var(--ygd-out-bg);stroke:var(--ygd-out-bd);stroke-dasharray:3 2}
.ygd-tcp-zero-window-probe .ygd-s-out text{fill:var(--ygd-out-fg)}
.ygd-tcp-zero-window-probe .ygd-winr{fill:none;stroke:var(--ygd-open-bd);stroke-width:2}
.ygd-tcp-zero-window-probe .ygd-bar{fill:var(--ygd-bad-bd)}
.ygd-tcp-zero-window-probe .ygd-off{opacity:0}
.ygd-tcp-zero-window-probe .ygd-wl{font-size:12px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-svg .ygd-wl.ygd-zero{fill:var(--ygd-bad-bd)}
.ygd-tcp-zero-window-probe .ygd-lane{stroke:var(--ygd-out-bd);stroke-width:1.5;stroke-dasharray:4 4;opacity:.7}
.ygd-tcp-zero-window-probe .ygd-pk{transition:opacity .3s}
.ygd-tcp-zero-window-probe .ygd-pk rect{stroke-width:1.5}
.ygd-tcp-zero-window-probe .ygd-pk text{font-size:12px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-k-data rect{fill:var(--ygd-open-bg);stroke:var(--ygd-open-bd)}
.ygd-tcp-zero-window-probe .ygd-k-data text{fill:var(--ygd-open-fg)}
.ygd-tcp-zero-window-probe .ygd-k-ack rect{fill:var(--ygd-acked-bg);stroke:var(--ygd-acked-bd)}
.ygd-tcp-zero-window-probe .ygd-k-ack text{fill:var(--ygd-acked-fg)}
.ygd-tcp-zero-window-probe .ygd-k-zero rect{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad-bd)}
.ygd-tcp-zero-window-probe .ygd-k-zero text{fill:var(--ygd-bad-fg)}
.ygd-tcp-zero-window-probe .ygd-k-probe rect{fill:var(--ygd-sent-bg);stroke:var(--ygd-sent-bd)}
.ygd-tcp-zero-window-probe .ygd-k-probe text{fill:var(--ygd-sent-fg)}
.ygd-tcp-zero-window-probe .ygd-slot rect{stroke-width:1.5;transition:fill .35s,stroke .35s}
.ygd-tcp-zero-window-probe .ygd-slot text{font-size:13px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-slot.ygd-e rect{fill:var(--ygd-out-bg);stroke:var(--ygd-out-bd);stroke-dasharray:3 2}
.ygd-tcp-zero-window-probe .ygd-slot.ygd-e text{fill:var(--ygd-out-fg);font-weight:400;font-size:12px}
.ygd-tcp-zero-window-probe .ygd-slot.ygd-f rect{fill:var(--ygd-sent-bg);stroke:var(--ygd-sent-bd)}
.ygd-tcp-zero-window-probe .ygd-slot.ygd-f text{fill:var(--ygd-sent-fg)}
.ygd-tcp-zero-window-probe .ygd-slot.ygd-x rect{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad-bd)}
.ygd-tcp-zero-window-probe .ygd-slot.ygd-x text{fill:var(--ygd-bad-fg)}
.ygd-tcp-zero-window-probe .ygd-app rect{fill:var(--ygd-out-bg);stroke:var(--ygd-out-bd);stroke-width:1.5}
.ygd-tcp-zero-window-probe .ygd-app text{font-size:13px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-app.ygd-ok rect{fill:var(--ygd-acked-bg);stroke:var(--ygd-acked-bd)}
.ygd-tcp-zero-window-probe .ygd-app.ygd-ok text{fill:var(--ygd-acked-fg)}
.ygd-tcp-zero-window-probe .ygd-app.ygd-stuck rect{fill:var(--ygd-bad-bg);stroke:var(--ygd-bad-bd)}
.ygd-tcp-zero-window-probe .ygd-app.ygd-stuck text{fill:var(--ygd-bad-fg)}
.ygd-tcp-zero-window-probe .ygd-ar{color:var(--ygd-out-bd)}
.ygd-tcp-zero-window-probe .ygd-ar line{stroke:currentColor;stroke-width:2}
.ygd-tcp-zero-window-probe .ygd-ar polygon{fill:currentColor}
.ygd-tcp-zero-window-probe .ygd-ar.ygd-ar-on{color:var(--ygd-acked-bd)}
.ygd-tcp-zero-window-probe .ygd-ar.ygd-ar-block{color:var(--ygd-bad-bd)}
.ygd-tcp-zero-window-probe .ygd-ar.ygd-ar-block line{stroke-dasharray:3 3}
.ygd-tcp-zero-window-probe .ygd-ar.ygd-ar-block polygon{opacity:0}
.ygd-tcp-zero-window-probe .ygd-arl{font-size:12px}
.ygd-tcp-zero-window-probe .ygd-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:10px 0}
.ygd-tcp-zero-window-probe .ygd-stat{min-width:0;padding:8px 10px;border:1px solid var(--ygd-bd);border-radius:8px;background:var(--ygd-card)}
.ygd-tcp-zero-window-probe .ygd-stat[data-tone="bad"]{border-color:var(--ygd-bad-bd);background:var(--ygd-bad-bg)}
.ygd-tcp-zero-window-probe .ygd-sl{font-size:14px;font-weight:700}
.ygd-tcp-zero-window-probe .ygd-sv{font-size:20px;font-weight:700;line-height:1.3}
.ygd-tcp-zero-window-probe .ygd-stat[data-tone="bad"] .ygd-sv,.ygd-tcp-zero-window-probe .ygd-stat[data-tone="bad"] .ygd-sl{color:var(--ygd-bad-fg)}
.ygd-tcp-zero-window-probe .ygd-ss{font-size:14px;color:var(--ygd-mu);line-height:1.35}
.ygd-tcp-zero-window-probe .ygd-stat[data-tone="bad"] .ygd-ss{color:var(--ygd-bad-fg)}
.ygd-tcp-zero-window-probe .ygd-panel{padding:10px 12px;border:1px solid var(--ygd-bd);border-left:4px solid var(--ygd-acc);border-radius:8px;background:var(--ygd-card);min-height:120px}
.ygd-tcp-zero-window-probe .ygd-pt{font-size:16px;font-weight:700;margin:0 0 4px}
.ygd-tcp-zero-window-probe .ygd-pd{font-size:15px;margin:0;line-height:1.6}
.ygd-tcp-zero-window-probe .ygd-steps{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.ygd-tcp-zero-window-probe .ygd-chip{font:inherit;font-size:14px;font-weight:700;width:38px;height:38px;margin:0;padding:0;border-radius:50%;border:1px solid var(--ygd-bd);background:var(--ygd-card);color:var(--ygd-mu);cursor:pointer}
.ygd-tcp-zero-window-probe .ygd-chip.ygd-past{border-color:var(--ygd-acc);color:var(--ygd-fg)}
.ygd-tcp-zero-window-probe .ygd-chip.ygd-now{background:var(--ygd-acc);border-color:var(--ygd-acc);color:var(--ygd-acc-fg)}
.ygd-tcp-zero-window-probe .ygd-legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin:0 0 8px;font-size:14px;color:var(--ygd-mu)}
.ygd-tcp-zero-window-probe .ygd-lg{display:inline-flex;align-items:center;gap:6px}
.ygd-tcp-zero-window-probe .ygd-sw{display:inline-block;width:16px;height:16px;border-radius:3px;border:1.5px solid}
.ygd-tcp-zero-window-probe .ygd-sw.ygd-s-acked{background:var(--ygd-acked-bg);border-color:var(--ygd-acked-bd)}
.ygd-tcp-zero-window-probe .ygd-sw.ygd-s-sent{background:var(--ygd-sent-bg);border-color:var(--ygd-sent-bd)}
.ygd-tcp-zero-window-probe .ygd-sw.ygd-s-open{background:var(--ygd-open-bg);border-color:var(--ygd-open-bd)}
.ygd-tcp-zero-window-probe .ygd-sw.ygd-s-out{background:var(--ygd-out-bg);border-color:var(--ygd-out-bd);border-style:dashed}
.ygd-tcp-zero-window-probe .ygd-note{margin:0;font-size:14px;color:var(--ygd-mu);line-height:1.6}
@media (prefers-reduced-motion:reduce){.ygd-tcp-zero-window-probe *{transition:none !important;animation:none !important}}
</style>
<div class="ygd-ctrl">
<button type="button" class="ygd-btn ygd-primary" data-ygd="play">▶ 재생</button>
<button type="button" class="ygd-btn" data-ygd="prev">이전</button>
<button type="button" class="ygd-btn" data-ygd="next">다음</button>
<button type="button" class="ygd-btn" data-ygd="reset">처음으로</button>
<span class="ygd-prog" data-ygd="prog"></span>
</div>
<svg class="ygd-svg" viewBox="0 0 360 304" role="img" aria-label="TCP Zero Window와 Window Probe 흐름 다이어그램" data-ygd="svg">
<text class="ygd-hd" x="24" y="16">송신 측 · 보낼 세그먼트 번호</text>
<g data-ygd="cells"></g>
<rect class="ygd-winr" data-ygd="winr" x="23" y="30" width="106" height="36" rx="4"></rect>
<rect class="ygd-bar ygd-off" data-ygd="bar" x="230" y="30" width="4" height="36" rx="1"></rect>
<text class="ygd-wl" data-ygd="wl" x="76" y="84" text-anchor="middle">Window = 4</text>
<line class="ygd-lane" x1="180" y1="98" x2="180" y2="186"></line>
<g class="ygd-pk ygd-k-data ygd-off" data-ygd="pk" transform="translate(105,98)">
<rect x="0" y="0" width="150" height="22" rx="11"></rect>
<text data-ygd="pkt" x="75" y="15" text-anchor="middle"></text>
</g>
<text class="ygd-hd" x="24" y="204">수신 측 · 수신 버퍼 (빈 칸 수 = Window)</text>
<g data-ygd="slots"></g>
<g class="ygd-ar" data-ygd="ar">
<line x1="180" y1="246" x2="180" y2="262"></line>
<polygon points="174,260 186,260 180,268"></polygon>
</g>
<text class="ygd-arl" data-ygd="arl" x="196" y="262"></text>
<g class="ygd-app" data-ygd="app">
<rect x="24" y="270" width="312" height="30" rx="6"></rect>
<text data-ygd="appt" x="180" y="290" text-anchor="middle"></text>
</g>
</svg>
<div class="ygd-stats">
<div class="ygd-stat" data-ygd="st-sq"><div class="ygd-sl">Send-Q</div><div class="ygd-sv"></div><div class="ygd-ss">ACK 못 받은 양</div></div>
<div class="ygd-stat" data-ygd="st-rq"><div class="ygd-sl">Recv-Q</div><div class="ygd-sv"></div><div class="ygd-ss">read() 안 한 양</div></div>
<div class="ygd-stat" data-ygd="st-win"><div class="ygd-sl">Window</div><div class="ygd-sv"></div><div class="ygd-ss">수신 측이 알린 값</div></div>
</div>
<div class="ygd-panel" aria-live="polite"><p class="ygd-pt" data-ygd="pt"></p><p class="ygd-pd" data-ygd="pd"></p></div>
<div class="ygd-steps" role="group" aria-label="단계 선택" data-ygd="steps"></div>
<div class="ygd-legend">
<span class="ygd-lg"><span class="ygd-sw ygd-s-acked"></span>ACK 받음</span>
<span class="ygd-lg"><span class="ygd-sw ygd-s-sent"></span>전송함, ACK 대기</span>
<span class="ygd-lg"><span class="ygd-sw ygd-s-open"></span>윈도우 안, 전송 가능</span>
<span class="ygd-lg"><span class="ygd-sw ygd-s-out"></span>윈도우 밖, 전송 불가</span>
</div>
<p class="ygd-note">비유: 수신 버퍼는 창고이고 read()는 창고에서 물건을 꺼내 가는 일이다. 창고가 가득 차면 수신 측이 지금은 못 받는다고 알리고, 송신 측은 짐을 내리지 않은 채 자리가 났는지만 가끔 확인한다. 실제 TCP에서 이 확인용 패킷(Window Probe)은 1바이트짜리다.</p>
<script>
(function(){
var root=document.getElementById('ygd-tcp-zero-window-probe');
if(!root)return;
var NS='http://www.w3.org/2000/svg';
var mq=window.matchMedia?window.matchMedia('(prefers-reduced-motion: reduce)'):{matches:false};
function Q(k){return root.querySelector('[data-ygd="'+k+'"]');}
function el(n,a){var e=document.createElementNS(NS,n);for(var k in a){e.setAttribute(k,a[k]);}return e;}
var S=[
{t:"시작: 윈도우가 열려 있다",d:"수신 측이 Window=4를 알려 둔 상태다. 송신 측은 ACK를 기다리지 않고도 윈도우 안의 1~4번까지 보낼 수 있다. 번호는 설명용 세그먼트 번호이고, ACK n은 n번부터 받을 차례라는 뜻이다.",a:0,f:0,ws:1,wl:4,pk:null,buf:[],app:["대기 중",""],ar:["idle","read()"],sq:"0개",rq:"0개",win:"4"},
{t:"윈도우 안의 데이터를 전송",d:"송신 측이 1~4번을 보냈다. ACK를 못 받은 데이터가 Send-Q에 잡히고, 윈도우를 다 썼으므로 ACK가 올 때까지 더 보내지 못한다.",a:0,f:4,ws:1,wl:4,pk:{k:"data",x:"▼ DATA 1~4",dir:"down"},buf:[],app:["대기 중",""],ar:["idle","read()"],sq:"4개",rq:"0개",win:"4"},
{t:"ACK가 오면 윈도우가 슬라이딩",d:"수신 앱이 read()로 1~4번을 읽어 수신 버퍼가 비었고, ACK 5와 Window=4가 돌아왔다. 윈도우 왼쪽 경계가 5번으로 슬라이딩해 5~8번을 보낼 수 있게 된다.",a:4,f:4,ws:5,wl:4,pk:{k:"ack",x:"▲ ACK 5 · Win=4",dir:"up"},buf:[],app:["1~4를 read()로 읽음","ok"],ar:["on","read()"],sq:"0개",rq:"0개",win:"4"},
{t:"5~8번 전송",d:"송신 측이 5~8번을 보낸다. 지금까지는 ACK가 올 때마다 윈도우가 오른쪽으로 밀리는 정상 흐름이다.",a:4,f:8,ws:5,wl:4,pk:{k:"data",x:"▼ DATA 5~8",dir:"down"},buf:[],app:["다음 데이터 대기",""],ar:["idle","read()"],sq:"4개",rq:"0개",win:"4"},
{t:"버퍼가 차서 Window = 0",d:"이번에는 수신 앱이 read()를 못 불러 5~8번이 수신 버퍼에 그대로 쌓였다(Recv-Q 4개). 수신 측은 ACK 9와 함께 Window=0을 알려 윈도우가 닫힌다.",a:8,f:8,ws:9,wl:0,wz:"Window = 0 · 전송 중단",pk:{k:"zero",x:"▲ ACK 9 · Win=0",dir:"up"},buf:[5,6,7,8],app:["read() 못 부름 (처리 지연)","stuck"],ar:["block","read() 안 됨"],sq:"0개",rq:"4개",win:"0"},
{t:"송신 측 정지, Window Probe 전송",d:"송신 측은 9번 이후 전송을 멈춘다. 대신 윈도우가 열렸는지 확인하려고 1바이트짜리 Window Probe를 보낸다.",a:8,f:8,ws:9,wl:0,wz:"Window = 0 · Probe만 전송",pk:{k:"probe",x:"▼ Probe 1바이트",dir:"down"},buf:[5,6,7,8],app:["read() 못 부름 (처리 지연)","stuck"],ar:["block","read() 안 됨"],sq:"0개",rq:"4개",win:"0"},
{t:"Probe 응답: 아직 0",d:"수신 버퍼가 아직 차 있어서 응답에 Window=0이 그대로 담겨 온다. 송신 측은 계속 멈춘 채 Probe를 주기적으로 다시 보낸다.",a:8,f:8,ws:9,wl:0,wz:"Window = 0 · Probe만 전송",pk:{k:"zero",x:"▲ ACK 9 · Win=0",dir:"up"},buf:[5,6,7,8],app:["read() 못 부름 (처리 지연)","stuck"],ar:["block","read() 안 됨"],sq:"0개",rq:"4개",win:"0"},
{t:"수신 앱이 read()를 다시 부른다",d:"수신 앱이 read()를 다시 불러 5~8번을 읽자 Recv-Q가 0이 됐다. 하지만 송신 측은 아직 Window=0으로 알고 있어서 이 순간에는 여전히 멈춰 있다.",a:8,f:8,ws:9,wl:0,wz:"Window = 0 · Probe만 전송",pk:null,buf:[],app:["5~8을 read()로 읽음","ok"],ar:["on","read()"],sq:"0개",rq:"0개",win:"0"},
{t:"윈도우가 다시 열림",d:"다음 Probe에 대한 응답(수신 측이 보내는 Window Update일 수도 있다)에 Window=4가 담겨 온다. 송신 측 윈도우가 9~12번으로 다시 열린다.",a:8,f:8,ws:9,wl:4,pk:{k:"ack",x:"▲ ACK 9 · Win=4",dir:"up"},buf:[],app:["대기 중",""],ar:["idle","read()"],sq:"0개",rq:"0개",win:"4"},
{t:"전송 재개",d:"송신 측이 9~12번을 보내고 Send-Q가 다시 올라간다. ss로 봤을 때 Recv-Q가 계속 높다면 수신 앱의 처리 속도를 의심해야 한다.",a:8,f:12,ws:9,wl:4,pk:{k:"data",x:"▼ DATA 9~12",dir:"down"},buf:[],app:["다음 데이터 대기",""],ar:["idle","read()"],sq:"4개",rq:"0개",win:"4"}
];
var N=S.length,CW=26,X0=24,Y_TOP=98,Y_BOT=158;
var cells=[],slots=[],i;
var gc=Q('cells'),gs=Q('slots');
for(i=1;i<=12;i++){
var g=el('g',{'class':'ygd-cell ygd-s-out'});
var r=el('rect',{x:X0+1+(i-1)*CW,y:34,width:24,height:28,rx:3});
var t=el('text',{x:X0+13+(i-1)*CW,y:52,'text-anchor':'middle'});
t.textContent=String(i);
g.appendChild(r);g.appendChild(t);gc.appendChild(g);cells.push(g);
}
for(i=0;i<4;i++){
var sg=el('g',{'class':'ygd-slot ygd-e'});
var sr=el('rect',{x:42+i*70,y:212,width:66,height:32,rx:4});
var st=el('text',{x:75+i*70,y:233,'text-anchor':'middle'});
sg.appendChild(sr);sg.appendChild(st);gs.appendChild(sg);slots.push({g:sg,t:st});
}
var winR=Q('winr'),bar=Q('bar'),wl=Q('wl'),pk=Q('pk'),pkt=Q('pkt');
var ar=Q('ar'),arl=Q('arl'),app=Q('app'),appt=Q('appt');
var cur={wx:X0,ww:104,lx:76,py:Y_TOP};
function draw(){
winR.setAttribute('x',cur.wx-1);
winR.setAttribute('width',Math.max(cur.ww+2,0));
winR.classList.toggle('ygd-off',cur.ww<1);
bar.setAttribute('x',cur.wx-2);
bar.classList.toggle('ygd-off',cur.ww>=1);
wl.setAttribute('x',cur.lx);
pk.setAttribute('transform','translate(105,'+cur.py+')');
}
var raf={};
function cancelAll(){for(var k in raf){if(raf[k]){cancelAnimationFrame(raf[k]);raf[k]=0;}}}
function tween(name,to,ms,done){
if(raf[name]){cancelAnimationFrame(raf[name]);raf[name]=0;}
var from={},k;
for(k in to){from[k]=cur[k];}
if(ms<=0){for(k in to){cur[k]=to[k];}draw();if(done)done();return;}
var t0=null;
function f(now){
if(t0===null)t0=now;
var p=Math.min(1,(now-t0)/ms);
var e=p<0.5?2*p*p:1-Math.pow(-2*p+2,2)/2;
for(k in to){cur[k]=from[k]+(to[k]-from[k])*e;}
draw();
if(p<1){raf[name]=requestAnimationFrame(f);}else{raf[name]=0;if(done)done();}
}
raf[name]=requestAnimationFrame(f);
}
function setStat(key,val,bad){
var e=Q(key);
e.querySelector('.ygd-sv').textContent=val;
if(bad){e.setAttribute('data-tone','bad');}else{e.removeAttribute('data-tone');}
}
function applyS(s,ms){
var n,st;
for(n=1;n<=12;n++){
if(n<=s.a){st='acked';}
else if(n<=s.f){st='sent';}
else if(n>=s.ws&&n<s.ws+s.wl){st='open';}
else{st='out';}
cells[n-1].setAttribute('class','ygd-cell ygd-s-'+st);
}
var label=s.wl>0?'Window = '+s.wl:s.wz;
wl.textContent=label;
wl.setAttribute('class','ygd-wl'+(s.wl>0?'':' ygd-zero'));
var wx=X0+(s.ws-1)*CW,ww=s.wl*CW;
var center=s.wl>0?wx+ww/2:wx;
var half=label.length*4.4;
var lx=Math.max(X0+half,Math.min(336-half,center));
setStat('st-sq',s.sq,false);
setStat('st-win',s.win,s.win==='0');
tween('win',{wx:wx,ww:ww,lx:lx},ms);
}
function applyR(s){
var n,b;
for(n=0;n<4;n++){
b=s.buf[n];
if(b){
slots[n].t.textContent=String(b);
slots[n].g.setAttribute('class','ygd-slot '+(s.buf.length>=4?'ygd-x':'ygd-f'));
}else{
slots[n].t.textContent='빈 칸';
slots[n].g.setAttribute('class','ygd-slot ygd-e');
}
}
appt.textContent=s.app[0];
app.setAttribute('class','ygd-app'+(s.app[1]?' ygd-'+s.app[1]:''));
ar.setAttribute('class','ygd-ar'+(s.ar[0]==='idle'?'':' ygd-ar-'+s.ar[0]));
arl.textContent=s.ar[1];
setStat('st-rq',s.rq,s.buf.length>=4);
}
var chipsBox=Q('steps'),chips=[];
var idx=0,token=0,playing=false,timer=0;
var btnPlay=root.querySelector('[data-ygd="play"]');
var btnPrev=root.querySelector('[data-ygd="prev"]');
var btnNext=root.querySelector('[data-ygd="next"]');
var btnReset=root.querySelector('[data-ygd="reset"]');
for(i=0;i<N;i++){
(function(n){
var c=document.createElement('button');
c.type='button';
c.className='ygd-chip';
c.textContent=String(n+1);
c.setAttribute('aria-label',(n+1)+'단계: '+S[n].t);
c.addEventListener('click',function(){pause();go(n,false);});
chipsBox.appendChild(c);chips.push(c);
})(i);
}
function updateBtn(){
if(playing){btnPlay.textContent='⏸ 일시정지';}
else if(idx>=N-1){btnPlay.textContent='↻ 다시 재생';}
else{btnPlay.textContent='▶ 재생';}
btnPrev.disabled=idx<=0;
btnNext.disabled=idx>=N-1;
}
function chrome(){
var s=S[idx],n;
Q('pt').textContent=(idx+1)+'. '+s.t;
Q('pd').textContent=s.d;
Q('prog').textContent='단계 '+(idx+1)+' / '+N;
for(n=0;n<N;n++){
chips[n].className='ygd-chip'+(n<idx?' ygd-past':'')+(n===idx?' ygd-now':'');
if(n===idx){chips[n].setAttribute('aria-current','step');}else{chips[n].removeAttribute('aria-current');}
}
Q('svg').setAttribute('aria-label','TCP Zero Window와 Window Probe 흐름 다이어그램. 단계 '+(idx+1)+': '+s.t+'. Send-Q '+s.sq+', Recv-Q '+s.rq+', Window '+s.win+'.');
updateBtn();
}
function go(n,anim){
cancelAll();
token++;
var my=token;
idx=n;
var s=S[n];
var useAnim=anim&&!mq.matches;
chrome();
if(!s.pk){
pk.classList.add('ygd-off');
applyR(s);
applyS(s,useAnim?500:0);
return;
}
pk.setAttribute('class','ygd-pk ygd-k-'+s.pk.k);
pkt.textContent=s.pk.x;
var up=s.pk.dir==='up';
var y0=up?Y_BOT:Y_TOP,y1=up?Y_TOP:Y_BOT;
cur.py=y0;
draw();
if(!useAnim){
cur.py=y1;draw();
applyR(s);applyS(s,0);
return;
}
if(up){
applyR(s);
tween('pkt',{py:y1},800,function(){if(my===token)applyS(s,500);});
}else{
applyS(s,500);
tween('pkt',{py:y1},800,function(){if(my===token)applyR(s);});
}
}
function pause(){
playing=false;
if(timer){clearTimeout(timer);timer=0;}
updateBtn();
}
function schedule(){
timer=setTimeout(function(){
timer=0;
if(!playing)return;
go(idx+1,true);
if(idx>=N-1){pause();}else{schedule();}
},4500);
}
btnPlay.addEventListener('click',function(){
if(playing){pause();return;}
if(idx>=N-1){go(0,false);}
playing=true;
updateBtn();
schedule();
});
btnPrev.addEventListener('click',function(){pause();if(idx>0)go(idx-1,false);});
btnNext.addEventListener('click',function(){pause();if(idx<N-1)go(idx+1,true);});
btnReset.addEventListener('click',function(){pause();go(0,false);});
go(0,false);
})();
</script>
</div>


## Nagle 알고리즘과 TCP_NODELAY

Nagle 알고리즘은 작은 패킷을 모아서 보내는 방식이다. 1바이트짜리 데이터를 보낼 때마다 40바이트 헤더(IP 20 + TCP 20)가 붙으니까, 작은 패킷을 모아서 한 번에 보내면 네트워크 효율이 좋아진다.

동작 방식:
- 보낼 데이터가 MSS(Maximum Segment Size) 이상이면 바로 전송
- 아직 ACK를 받지 못한 데이터가 없으면 바로 전송
- ACK를 기다리는 중이면, 데이터를 버퍼에 모아뒀다가 ACK가 오면 한꺼번에 전송

=== "Nagle ON (기본값)"

    ```mermaid
    sequenceDiagram
        participant App as Application
        participant TCP as TCP Stack
        participant Net as Network

        App->>TCP: write("H")
        TCP->>Net: "H" 전송 (미확인 데이터 없음)
        App->>TCP: write("e")
        Note right of TCP: 버퍼에 보관 (ACK 대기 중)
        App->>TCP: write("l")
        App->>TCP: write("l")
        Net->>TCP: ACK 도착
        TCP->>Net: "ell" 한 번에 전송
    ```

=== "Nagle OFF (TCP_NODELAY)"

    ```mermaid
    sequenceDiagram
        participant App as Application
        participant TCP as TCP Stack
        participant Net as Network

        App->>TCP: write("H")
        TCP->>Net: "H" 전송
        App->>TCP: write("e")
        TCP->>Net: "e" 전송
        App->>TCP: write("l")
        TCP->>Net: "l" 전송
        App->>TCP: write("l")
        TCP->>Net: "l" 전송
    ```

### Nagle + Delayed ACK 조합 문제

Delayed ACK는 ACK를 바로 보내지 않고 최대 200ms까지 기다렸다가 보내는 기능이다. 보낼 데이터가 있으면 데이터와 ACK를 같이 보내서 패킷 수를 줄인다.

Nagle과 Delayed ACK가 동시에 켜져 있으면 서로 기다리는 상황이 생긴다:
1. 클라이언트: 작은 데이터를 보냄, 나머지는 ACK 올 때까지 대기 (Nagle)
2. 서버: ACK를 200ms 뒤에 보내려고 대기 (Delayed ACK)
3. 결과: 200ms 지연 발생

HTTP 서버, 게임 서버, 실시간 통신 서버에서는 `TCP_NODELAY`를 켜는 게 일반적이다.

```java
// Java
socket.setTcpNoDelay(true);
```

```go
// Go - net.TCPConn
conn.SetNoDelay(true)
```

```python
# Python
import socket
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
```

<div class="ygd-nagle-delayed-ack-stall" id="ygd-nagle-delayed-ack-stall">
<style>
.ygd-nagle-delayed-ack-stall{--ygd-bg:#fdfbfa;--ygd-fg:#2b2927;--ygd-muted:#5f5a54;--ygd-bd:#cfc9c1;--ygd-box:#f1eee9;--ygd-line:#7d776f;--ygd-accent:#1f6b86;--ygd-accent-soft:#dcecf2;--ygd-onaccent:#ffffff;--ygd-warn:#a9470f;--ygd-warnbg:#fbeadd;--ygd-ok:#1a7344;--ygd-okbg:#dff2e8;max-width:760px;margin-left:auto;margin-right:auto;box-sizing:border-box;padding:14px;border:1px solid var(--ygd-bd);border-radius:10px;background:var(--ygd-bg);color:var(--ygd-fg);font-size:14px;line-height:1.6}
body[data-md-color-scheme="slate"] .ygd-nagle-delayed-ack-stall{--ygd-bg:#1f1c1e;--ygd-fg:#f0ede9;--ygd-muted:#b3ada5;--ygd-bd:#4d4749;--ygd-box:#2c282b;--ygd-line:#9a948c;--ygd-accent:#7cc4de;--ygd-accent-soft:#25414d;--ygd-onaccent:#10202a;--ygd-warn:#f4a870;--ygd-warnbg:#4a3123;--ygd-ok:#6fcf9b;--ygd-okbg:#1f3d2e}
.ygd-nagle-delayed-ack-stall *{box-sizing:border-box}
.ygd-nagle-delayed-ack-stall .ygd-title{font-size:16px;font-weight:700;margin:0 0 6px}
.ygd-nagle-delayed-ack-stall .ygd-note{font-size:14px;color:var(--ygd-muted);margin:0 0 12px}
.ygd-nagle-delayed-ack-stall .ygd-bar{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}
.ygd-nagle-delayed-ack-stall .ygd-grp{display:flex;flex-wrap:wrap;gap:8px}
.ygd-nagle-delayed-ack-stall .ygd-btn{font-family:inherit;font-size:14px;line-height:1.2;min-height:40px;padding:0 14px;border:1px solid var(--ygd-bd);border-radius:8px;background:var(--ygd-box);color:var(--ygd-fg);cursor:pointer}
.ygd-nagle-delayed-ack-stall .ygd-btn:hover{border-color:var(--ygd-accent)}
.ygd-nagle-delayed-ack-stall .ygd-btn:focus-visible{outline:3px solid var(--ygd-accent);outline-offset:2px}
.ygd-nagle-delayed-ack-stall .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-nagle-delayed-ack-stall .ygd-btn.ygd-primary{background:var(--ygd-accent);border-color:var(--ygd-accent);color:var(--ygd-onaccent);font-weight:700}
.ygd-nagle-delayed-ack-stall .ygd-btn[aria-pressed="true"]{border-color:var(--ygd-accent);background:var(--ygd-accent-soft);font-weight:700}
.ygd-nagle-delayed-ack-stall .ygd-svg{display:block;width:100%;max-width:520px;height:auto;margin:0 auto}
.ygd-nagle-delayed-ack-stall .ygd-svg[hidden]{display:none}
.ygd-nagle-delayed-ack-stall .ygd-t{font-size:12px;fill:var(--ygd-fg)}
.ygd-nagle-delayed-ack-stall .ygd-tb{font-size:12px;font-weight:700;fill:var(--ygd-fg)}
.ygd-nagle-delayed-ack-stall .ygd-th{font-size:13px;font-weight:700;fill:var(--ygd-fg)}
.ygd-nagle-delayed-ack-stall .ygd-tw{font-size:12px;font-weight:700;fill:var(--ygd-warn)}
.ygd-nagle-delayed-ack-stall .ygd-to{font-size:12px;font-weight:700;fill:var(--ygd-ok)}
.ygd-nagle-delayed-ack-stall .ygd-ta{font-size:12px;fill:var(--ygd-accent);font-weight:700}
.ygd-nagle-delayed-ack-stall .ygd-box{fill:var(--ygd-box);stroke:var(--ygd-bd);stroke-width:1.5}
.ygd-nagle-delayed-ack-stall .ygd-boxw{fill:var(--ygd-warnbg);stroke:var(--ygd-warn);stroke-width:1.5}
.ygd-nagle-delayed-ack-stall .ygd-boxo{fill:var(--ygd-okbg);stroke:var(--ygd-ok);stroke-width:1.5}
.ygd-nagle-delayed-ack-stall .ygd-life{stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:4 4}
.ygd-nagle-delayed-ack-stall .ygd-ln-data{stroke:var(--ygd-accent);stroke-width:2;fill:none}
.ygd-nagle-delayed-ack-stall .ygd-ln-ack{stroke:var(--ygd-ok);stroke-width:2;fill:none}
.ygd-nagle-delayed-ack-stall .ygd-cur .ygd-ln-data,.ygd-nagle-delayed-ack-stall .ygd-cur .ygd-ln-ack{stroke-width:3.5}
.ygd-nagle-delayed-ack-stall .ygd-mk-data{fill:var(--ygd-accent)}
.ygd-nagle-delayed-ack-stall .ygd-mk-ack{fill:var(--ygd-ok)}
.ygd-nagle-delayed-ack-stall .ygd-dot-data{fill:var(--ygd-accent);opacity:0}
.ygd-nagle-delayed-ack-stall .ygd-dot-ack{fill:var(--ygd-ok);opacity:0}
.ygd-nagle-delayed-ack-stall .ygd-track{fill:var(--ygd-box);stroke:var(--ygd-bd);stroke-width:1.5}
.ygd-nagle-delayed-ack-stall .ygd-tfill{fill:var(--ygd-warn)}
.ygd-nagle-delayed-ack-stall .ygd-el{opacity:.45;transition:opacity .35s}
.ygd-nagle-delayed-ack-stall .ygd-el.ygd-on{opacity:1}
.ygd-nagle-delayed-ack-stall .ygd-panel{margin:10px 0 0;padding:10px 12px;border:1px solid var(--ygd-bd);border-left:4px solid var(--ygd-accent);border-radius:8px;background:var(--ygd-box)}
.ygd-nagle-delayed-ack-stall .ygd-badge{font-size:14px;font-weight:700;color:var(--ygd-accent);margin:0 0 2px}
.ygd-nagle-delayed-ack-stall .ygd-desc{font-size:15px;line-height:1.65;min-height:3.3em}
.ygd-nagle-delayed-ack-stall .ygd-cards{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0}
.ygd-nagle-delayed-ack-stall .ygd-card{flex:1 1 220px;min-width:0;padding:8px 10px;border:1px solid var(--ygd-bd);border-radius:8px;font-size:14px;line-height:1.5;color:var(--ygd-muted)}
.ygd-nagle-delayed-ack-stall .ygd-card.ygd-act{border-color:var(--ygd-accent);background:var(--ygd-accent-soft);color:var(--ygd-fg)}
@media (prefers-reduced-motion:reduce){.ygd-nagle-delayed-ack-stall .ygd-el{transition:none}}
</style>
<div class="ygd-title">Nagle + Delayed ACK: 서로 기다리다 생기는 200ms 정지</div>
<div class="ygd-note">비유: 문 앞에서 두 사람이 서로 먼저 가라고 양보하는 상황이다. 다만 TCP에서는 Delayed ACK 타이머가 끝나면 서버가 스스로 움직이므로 영원히 막히지는 않고, 최대 200ms 뒤에 풀린다.</div>
<div class="ygd-bar">
<div class="ygd-grp" role="group" aria-label="모드 선택">
<button type="button" class="ygd-btn" data-ygd="m-on" aria-pressed="true">Nagle ON (기본값)</button>
<button type="button" class="ygd-btn" data-ygd="m-off" aria-pressed="false">TCP_NODELAY</button>
</div>
<div class="ygd-grp">
<button type="button" class="ygd-btn ygd-primary" data-ygd="play">재생</button>
<button type="button" class="ygd-btn" data-ygd="next">다음 단계</button>
<button type="button" class="ygd-btn" data-ygd="reset">처음으로</button>
</div>
</div>
<svg class="ygd-svg ygd-svg-on" viewBox="0 0 420 392" role="img" aria-label="Nagle이 켜진 클라이언트와 Delayed ACK를 쓰는 서버의 시퀀스. 클라이언트는 A를 보낸 뒤 B를 ACK가 올 때까지 보류하고, 서버는 ACK를 최대 200ms 미뤄 서로 기다린다. 타이머가 만료되어 ACK가 도착한 뒤에야 B가 전송된다.">
<defs>
<marker id="ygd-nagle-delayed-ack-stall-ah-data" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-data" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-nagle-delayed-ack-stall-ah-ack" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-ack" d="M0 0L10 5L0 10z"/></marker>
</defs>
<rect class="ygd-box" x="20" y="6" width="100" height="28" rx="6"/>
<text class="ygd-th" x="70" y="25" text-anchor="middle">클라이언트</text>
<rect class="ygd-box" x="300" y="6" width="100" height="28" rx="6"/>
<text class="ygd-th" x="350" y="25" text-anchor="middle">서버</text>
<line class="ygd-life" x1="70" y1="34" x2="70" y2="388"/>
<line class="ygd-life" x1="350" y1="34" x2="350" y2="388"/>
<g class="ygd-el" data-s="1"><line class="ygd-ln-data" x1="70" y1="60" x2="344" y2="76" marker-end="url(#ygd-nagle-delayed-ack-stall-ah-data)"/><text class="ygd-ta" x="210" y="52" text-anchor="middle">A 즉시 전송 (미확인 데이터 없음)</text></g>
<g class="ygd-el" data-s="2"><rect class="ygd-boxw" x="80" y="90" width="220" height="40" rx="6"/><text class="ygd-tw" x="90" y="107">B 보류 (Nagle)</text><text class="ygd-t" x="90" y="123">A의 ACK가 올 때까지 대기</text></g>
<g class="ygd-el" data-s="3"><rect class="ygd-boxw" x="130" y="144" width="210" height="40" rx="6"/><text class="ygd-tw" x="140" y="161">A 수신 · ACK 보류 (Delayed ACK)</text><text class="ygd-t" x="140" y="177">보낼 데이터 없음 → 타이머 시작</text></g>
<g class="ygd-el" data-s="4"><text class="ygd-t" data-ygd="ttext" x="80" y="204">대기 타이머 · 0ms / 최대 200ms</text><rect class="ygd-track" x="80" y="210" width="260" height="12" rx="6"/><rect class="ygd-tfill" data-ygd="tfill" x="80" y="210" width="0" height="12" rx="6"/><text class="ygd-tw" x="210" y="244" text-anchor="middle">클라이언트 ↔ 서버: 서로 상대를 기다림</text></g>
<g class="ygd-el" data-s="5"><line class="ygd-ln-ack" x1="350" y1="280" x2="76" y2="296" marker-end="url(#ygd-nagle-delayed-ack-stall-ah-ack)"/><text class="ygd-to" x="210" y="272" text-anchor="middle">ACK 단독 전송 (타이머 만료)</text></g>
<g class="ygd-el" data-s="6"><line class="ygd-ln-data" x1="70" y1="326" x2="344" y2="342" marker-end="url(#ygd-nagle-delayed-ack-stall-ah-data)"/><text class="ygd-ta" x="210" y="318" text-anchor="middle">B 전송 (ACK 도착 → 보류 해제)</text></g>
<g class="ygd-el" data-s="7"><rect class="ygd-boxw" x="110" y="356" width="230" height="28" rx="6"/><text class="ygd-tw" x="120" y="374">B 수신 → 요청 완성, 처리 시작</text></g>
<circle class="ygd-dot-data ygd-dot" data-s="1" data-x1="70" data-y1="60" data-x2="344" data-y2="76" cx="70" cy="60" r="5"/>
<circle class="ygd-dot-ack ygd-dot" data-s="5" data-x1="350" data-y1="280" data-x2="76" data-y2="296" cx="350" cy="280" r="5"/>
<circle class="ygd-dot-data ygd-dot" data-s="6" data-x1="70" data-y1="326" data-x2="344" data-y2="342" cx="70" cy="326" r="5"/>
</svg>
<svg class="ygd-svg ygd-svg-off" viewBox="0 0 420 300" hidden role="img" aria-label="TCP_NODELAY를 켠 클라이언트의 시퀀스. A와 B가 모두 보류 없이 즉시 전송되고, 서버는 요청을 완성해 ACK를 실은 응답을 보낸다. 서로를 막는 대기 구간이 없다.">
<defs>
<marker id="ygd-nagle-delayed-ack-stall-ah-data2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-data" d="M0 0L10 5L0 10z"/></marker>
<marker id="ygd-nagle-delayed-ack-stall-ah-ack2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="ygd-mk-ack" d="M0 0L10 5L0 10z"/></marker>
</defs>
<rect class="ygd-box" x="20" y="6" width="100" height="28" rx="6"/>
<text class="ygd-th" x="70" y="25" text-anchor="middle">클라이언트</text>
<rect class="ygd-box" x="300" y="6" width="100" height="28" rx="6"/>
<text class="ygd-th" x="350" y="25" text-anchor="middle">서버</text>
<line class="ygd-life" x1="70" y1="34" x2="70" y2="296"/>
<line class="ygd-life" x1="350" y1="34" x2="350" y2="296"/>
<g class="ygd-el" data-s="1"><line class="ygd-ln-data" x1="70" y1="60" x2="344" y2="76" marker-end="url(#ygd-nagle-delayed-ack-stall-ah-data2)"/><text class="ygd-ta" x="210" y="52" text-anchor="middle">A 즉시 전송</text></g>
<g class="ygd-el" data-s="2"><line class="ygd-ln-data" x1="70" y1="104" x2="344" y2="120" marker-end="url(#ygd-nagle-delayed-ack-stall-ah-data2)"/><text class="ygd-ta" x="210" y="96" text-anchor="middle">B도 즉시 전송 (보류 없음)</text></g>
<g class="ygd-el" data-s="3"><rect class="ygd-boxo" x="110" y="140" width="230" height="40" rx="6"/><text class="ygd-to" x="120" y="157">A, B 수신 → 요청 완성</text><text class="ygd-t" x="120" y="173">ACK 타이머를 기다리지 않고 처리</text></g>
<g class="ygd-el" data-s="4"><line class="ygd-ln-ack" x1="350" y1="212" x2="76" y2="228" marker-end="url(#ygd-nagle-delayed-ack-stall-ah-ack2)"/><text class="ygd-to" x="210" y="204" text-anchor="middle">응답 (ACK를 함께 실어 보냄)</text></g>
<g class="ygd-el" data-s="5"><rect class="ygd-boxo" x="80" y="246" width="250" height="40" rx="6"/><text class="ygd-to" x="90" y="263">200ms 정지 구간 없음</text><text class="ygd-t" x="90" y="279">서로를 막는 대기가 없음</text></g>
<circle class="ygd-dot-data ygd-dot" data-s="1" data-x1="70" data-y1="60" data-x2="344" data-y2="76" cx="70" cy="60" r="5"/>
<circle class="ygd-dot-data ygd-dot" data-s="2" data-x1="70" data-y1="104" data-x2="344" data-y2="120" cx="70" cy="104" r="5"/>
<circle class="ygd-dot-ack ygd-dot" data-s="4" data-x1="350" data-y1="212" data-x2="76" data-y2="228" cx="350" cy="212" r="5"/>
</svg>
<div class="ygd-panel" aria-live="polite"><div class="ygd-badge" data-ygd="badge"></div><div class="ygd-desc" data-ygd="desc"></div></div>
<div class="ygd-cards">
<div class="ygd-card" data-ygd="c-on">Nagle ON + Delayed ACK: 클라이언트는 ACK를, 서버는 타이머를 기다려 최대 200ms 정지한다.</div>
<div class="ygd-card" data-ygd="c-off">TCP_NODELAY: 작은 데이터도 바로 나가므로 이 정지 구간이 생기지 않는다.</div>
</div>
<script>
(function(){
var root=document.getElementById('ygd-nagle-delayed-ack-stall');
if(!root){return;}
var q=function(s){return root.querySelector(s);};
var qa=function(s){return Array.prototype.slice.call(root.querySelectorAll(s));};
var T={
on:[
"클라이언트가 작은 write를 연달아 두 번(A, B) 하고, 서버는 요청이 다 오기 전에는 응답할 데이터가 없다. 재생을 누르면 Nagle이 켜진 기본 상태의 흐름을 단계별로 보여준다.",
"미확인 데이터가 없으므로 Nagle은 A를 기다리지 않고 바로 내보낸다.",
"A의 ACK가 아직 오지 않았다. B는 작은 데이터라서 Nagle이 버퍼에 붙잡아 두고, ACK가 오면 보내려고 기다린다.",
"서버는 A를 받았지만 요청이 덜 와서 ACK에 실어 보낼 데이터가 없다. Delayed ACK가 ACK를 최대 200ms까지 미룬다.",
"클라이언트는 ACK를 기다리고 서버는 타이머를 기다린다. 서로 상대가 먼저 움직이길 기다리는 이 구간이 200ms 정지다.",
"Delayed ACK 타이머가 만료되자 서버가 ACK를 단독으로 보낸다.",
"ACK를 받은 클라이언트가 보류해 둔 B를 내보낸다. 정지는 타이머가 풀어줄 때까지 이어졌다.",
"서버는 B를 받고서야 요청이 완성되어 처리를 시작한다. 데이터는 작은데 응답만 최대 200ms 늦어졌다."
],
off:[
"TCP_NODELAY를 켜면 Nagle이 꺼진다. 같은 작은 write 두 번이 어떻게 달라지는지 본다.",
"A는 Nagle ON일 때와 똑같이 즉시 전송된다.",
"Nagle이 없으므로 B도 A의 ACK를 기다리지 않고 바로 나간다.",
"서버는 A와 B로 요청을 완성하고 곧바로 처리한다. ACK 타이머가 끝나기를 기다릴 이유가 없다.",
"응답이 ACK를 함께 실어 간다. 클라이언트는 ACK를 기다리며 멈추지 않는다.",
"Nagle 대기도 Delayed ACK 대기도 서로를 막지 않으므로 200ms 정지 구간이 생기지 않는다."
]
};
var MAX={on:7,off:5};
var mode='on',step=0,playing=false,tm=null,dotTok=0,tmTok=0;
var btnPlay=q('[data-ygd="play"]'),btnNext=q('[data-ygd="next"]'),btnReset=q('[data-ygd="reset"]');
var btnOn=q('[data-ygd="m-on"]'),btnOff=q('[data-ygd="m-off"]');
var badge=q('[data-ygd="badge"]'),desc=q('[data-ygd="desc"]');
var cOn=q('[data-ygd="c-on"]'),cOff=q('[data-ygd="c-off"]');
var tfill=q('[data-ygd="tfill"]'),ttext=q('[data-ygd="ttext"]');
function reduce(){return !!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);}
function runDots(){
var my=++dotTok;
var dots=qa('.ygd-svg-'+mode+' .ygd-dot');
dots.forEach(function(d){d.style.opacity=0;});
if(step===0||reduce()){return;}
var d=dots.filter(function(x){return +x.getAttribute('data-s')===step;})[0];
if(!d){return;}
var x1=+d.getAttribute('data-x1'),y1=+d.getAttribute('data-y1'),x2=+d.getAttribute('data-x2'),y2=+d.getAttribute('data-y2');
var t0=null;
function f(ts){
if(my!==dotTok){return;}
if(t0===null){t0=ts;}
var p=Math.min(1,(ts-t0)/900);
d.setAttribute('cx',x1+(x2-x1)*p);
d.setAttribute('cy',y1+(y2-y1)*p);
d.style.opacity=1;
if(p<1){requestAnimationFrame(f);}else{d.style.opacity=0;}
}
requestAnimationFrame(f);
}
function setTimer(w,t){tfill.setAttribute('width',w);ttext.textContent=t;}
function runTimer(){
var my=++tmTok,W=260;
if(step<4){setTimer(0,"대기 타이머 · 0ms / 최대 200ms");return;}
if(step>=5){setTimer(W,"타이머 만료 (최대 200ms)");return;}
if(reduce()){setTimer(W,"서로 대기 중 · 최대 200ms");return;}
var t0=null;
function f(ts){
if(my!==tmTok){return;}
if(t0===null){t0=ts;}
var p=Math.min(1,(ts-t0)/2200);
setTimer(W*p,"서로 대기 중 · "+Math.round(p*200)+"ms / 최대 200ms");
if(p<1){requestAnimationFrame(f);}
}
requestAnimationFrame(f);
}
function render(){
var on=mode==='on';
q('.ygd-svg-on').hidden=!on;
q('.ygd-svg-off').hidden=on;
qa('.ygd-svg-'+mode+' .ygd-el').forEach(function(g){
var s=+g.getAttribute('data-s');
g.classList.toggle('ygd-on',s<=step);
g.classList.toggle('ygd-cur',s===step);
});
btnOn.setAttribute('aria-pressed',on?'true':'false');
btnOff.setAttribute('aria-pressed',on?'false':'true');
cOn.classList.toggle('ygd-act',on);
cOff.classList.toggle('ygd-act',!on);
badge.textContent=step===0?'준비':'단계 '+step+' / '+MAX[mode];
desc.textContent=T[mode][step];
btnPlay.textContent=playing?'일시정지':(step>=MAX[mode]?'다시 재생':(step>0?'이어서 재생':'재생'));
btnNext.disabled=step>=MAX[mode];
if(on){runTimer();}
runDots();
}
function stop(){playing=false;if(tm){clearTimeout(tm);tm=null;}}
function delay(){return (mode==='on'&&step===4)?4600:3400;}
function tick(){
if(!playing){return;}
if(step>=MAX[mode]){stop();render();return;}
step++;
render();
if(step>=MAX[mode]){stop();render();return;}
tm=setTimeout(tick,delay());
}
btnPlay.addEventListener('click',function(){
if(playing){stop();render();return;}
if(step>=MAX[mode]){step=0;}
playing=true;
tm=setTimeout(tick,step===0?200:600);
render();
});
btnNext.addEventListener('click',function(){
stop();
if(step<MAX[mode]){step++;}
render();
});
btnReset.addEventListener('click',function(){stop();step=0;render();});
function setMode(m){if(m===mode){return;}stop();mode=m;step=0;render();}
btnOn.addEventListener('click',function(){setMode('on');});
btnOff.addEventListener('click',function(){setMode('off');});
render();
})();
</script>
</div>


## TCP Keepalive

TCP 연결이 수립된 후 데이터가 오가지 않으면, 양쪽 모두 상대방이 살아있는지 알 수 없다. Keepalive는 주기적으로 빈 패킷을 보내서 연결이 유효한지 확인한다.

```bash
# 리눅스 기본값 확인
sysctl net.ipv4.tcp_keepalive_time     # 7200초 (2시간) - 첫 probe까지 대기 시간
sysctl net.ipv4.tcp_keepalive_intvl    # 75초 - probe 간격
sysctl net.ipv4.tcp_keepalive_probes   # 9회 - 최대 probe 횟수

# 기본값대로면: 2시간 동안 데이터가 없으면 probe 시작
# 75초 간격으로 9번 시도 → 응답 없으면 연결 끊김
# 총 2시간 + 75*9 = 약 2시간 11분 후에 연결 정리
```

기본값 2시간은 대부분의 실무 환경에서 너무 길다. 로드밸런서(AWS ALB 기본 idle timeout: 60초)나 방화벽이 먼저 연결을 끊어버리기 때문에, keepalive가 동작하기도 전에 중간 장비가 연결을 정리하는 경우가 많다.

애플리케이션 레벨에서 설정하는 게 일반적이다:

```java
// Spring Boot - HikariCP DB 커넥션 풀
spring.datasource.hikari.keepalive-time=30000  // 30초마다 검증
spring.datasource.hikari.connection-timeout=3000
```

```go
// Go - DB 커넥션 풀
db.SetConnMaxIdleTime(5 * time.Minute)
```


## Backlog 큐

서버 소켓의 `listen()` 호출 시 지정하는 backlog은 Accept 큐의 크기다.

```mermaid
flowchart LR
    A[클라이언트] -->|SYN| B["SYN 큐 (반연결)<br/>tcp_max_syn_backlog"]
    B -->|ACK| C["Accept 큐 (완전연결)<br/>min(backlog, somaxconn)"]
    C --> D["accept()"]
```

Accept 큐가 가득 차면:
- `tcp_abort_on_overflow = 0` (기본값): 서버가 SYN+ACK를 재전송하며 클라이언트를 대기시킴
- `tcp_abort_on_overflow = 1`: 서버가 RST를 보내서 즉시 연결 거부

```bash
# Accept 큐 오버플로우 확인
nstat -az TcpExtListenOverflows
nstat -az TcpExtListenDrops

# 프로세스별 Accept 큐 상태 확인
ss -tlnp
# State    Recv-Q  Send-Q  Local Address
# LISTEN   0       128     0.0.0.0:8080
#          ^       ^
#          |       +-- Accept 큐 최대 크기
#          +---------- Accept 큐에 대기 중인 연결 수
```

Java 서버에서 backlog 설정:

```java
// Tomcat
server.tomcat.accept-count=100  // Accept 큐 크기

// Netty
ServerBootstrap b = new ServerBootstrap();
b.option(ChannelOption.SO_BACKLOG, 1024);
```

<div class="ygd-tcp-backlog-overflow" id="ygd-tcp-backlog-overflow">
<style>
.ygd-tcp-backlog-overflow{--ygd-panel:#F7F5F2;--ygd-fg:#2B2825;--ygd-mut:#5F5A55;--ygd-line:#8C857D;--ygd-box:#FFFFFF;--ygd-fill:#DCE9EF;--ygd-blue:#2F6F8F;--ygd-green:#2E7D4F;--ygd-red:#B3261E;--ygd-redsoft:#F6DAD7;--ygd-tkfg:#FFFFFF;--ygd-sel:#2F6F8F;--ygd-selfg:#FFFFFF;--ygd-focus:#C2570C;--ygd-border:#D8D3CC;max-width:760px;margin-left:auto;margin-right:auto;margin-top:1em;margin-bottom:1em;padding:14px;background:var(--ygd-panel);color:var(--ygd-fg);border:1px solid var(--ygd-border);border-radius:10px;font-size:14px;line-height:1.55;box-sizing:border-box;overflow:hidden}
body[data-md-color-scheme="slate"] .ygd-tcp-backlog-overflow{--ygd-panel:#2A2628;--ygd-fg:#F0EDE9;--ygd-mut:#B8B1A8;--ygd-line:#8C857D;--ygd-box:#1F1C1E;--ygd-fill:#34505E;--ygd-blue:#7FB4CC;--ygd-green:#7BC79A;--ygd-red:#F28B82;--ygd-redsoft:#4A2A28;--ygd-tkfg:#10202A;--ygd-sel:#7FB4CC;--ygd-selfg:#10202A;--ygd-focus:#FFB067;--ygd-border:#4A4548}
.ygd-tcp-backlog-overflow *{box-sizing:border-box}
.ygd-tcp-backlog-overflow .ygd-ttl{font-weight:700;font-size:15px;margin-bottom:10px}
.ygd-tcp-backlog-overflow .ygd-modes{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.ygd-tcp-backlog-overflow .ygd-btn{font:inherit;font-size:14px;color:var(--ygd-fg);background:var(--ygd-box);border:1px solid var(--ygd-line);border-radius:6px;padding:8px 14px;min-height:40px;cursor:pointer;overflow-wrap:anywhere;margin:0}
.ygd-tcp-backlog-overflow .ygd-btn:hover{border-color:var(--ygd-blue)}
.ygd-tcp-backlog-overflow .ygd-btn:focus-visible{outline:3px solid var(--ygd-focus);outline-offset:2px}
.ygd-tcp-backlog-overflow .ygd-btn:disabled{opacity:.5;cursor:default}
.ygd-tcp-backlog-overflow .ygd-mode{flex:1 1 150px}
.ygd-tcp-backlog-overflow .ygd-mode[aria-pressed="true"]{background:var(--ygd-sel);color:var(--ygd-selfg);border-color:var(--ygd-sel);font-weight:700}
.ygd-tcp-backlog-overflow .ygd-svg{display:block;width:100%;height:auto;max-width:100%;background:var(--ygd-box);border:1px solid var(--ygd-border);border-radius:8px}
.ygd-tcp-backlog-overflow .ygd-t{fill:var(--ygd-fg);font-size:11.5px;font-family:inherit}
.ygd-tcp-backlog-overflow .ygd-tm{fill:var(--ygd-mut);font-size:10.5px;font-family:inherit}
.ygd-tcp-backlog-overflow .ygd-th{fill:var(--ygd-fg);font-size:13px;font-weight:700;font-family:inherit}
.ygd-tcp-backlog-overflow .ygd-box{fill:var(--ygd-box);stroke:var(--ygd-line);stroke-width:1.5}
.ygd-tcp-backlog-overflow .ygd-full{stroke:var(--ygd-red);stroke-width:2.5}
.ygd-tcp-backlog-overflow .ygd-slot rect{fill:none;stroke:var(--ygd-line);stroke-width:1;stroke-dasharray:3 3;opacity:.7}
.ygd-tcp-backlog-overflow .ygd-slot text{opacity:0}
.ygd-tcp-backlog-overflow .ygd-slot.ygd-on rect{fill:var(--ygd-fill);stroke:var(--ygd-blue);stroke-dasharray:none;opacity:1;stroke-width:1.5}
.ygd-tcp-backlog-overflow .ygd-slot.ygd-on text{opacity:1}
.ygd-tcp-backlog-overflow .ygd-slot.ygd-warn.ygd-on rect{fill:var(--ygd-redsoft);stroke:var(--ygd-red)}
.ygd-tcp-backlog-overflow .ygd-lane{stroke:var(--ygd-line);stroke-width:1.5;stroke-dasharray:4 4;opacity:.7}
.ygd-tcp-backlog-overflow .ygd-dot{fill:var(--ygd-line)}
.ygd-tcp-backlog-overflow .ygd-tk rect{stroke:none}
.ygd-tcp-backlog-overflow .ygd-tk text{fill:var(--ygd-tkfg);font-size:11px;font-weight:700;font-family:inherit}
.ygd-tcp-backlog-overflow .ygd-tb rect{fill:var(--ygd-blue)}
.ygd-tcp-backlog-overflow .ygd-tg rect{fill:var(--ygd-green)}
.ygd-tcp-backlog-overflow .ygd-tr rect{fill:var(--ygd-red)}
.ygd-tcp-backlog-overflow .ygd-rt rect{stroke:var(--ygd-fg);stroke-width:1.5;stroke-dasharray:3 2}
.ygd-tcp-backlog-overflow .ygd-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px}
.ygd-tcp-backlog-overflow .ygd-card{background:var(--ygd-box);border:1px solid var(--ygd-border);border-radius:8px;padding:8px 10px;min-width:0}
.ygd-tcp-backlog-overflow .ygd-lbl{font-size:14px;color:var(--ygd-mut);overflow-wrap:anywhere}
.ygd-tcp-backlog-overflow .ygd-val{font-size:22px;font-weight:700;line-height:1.3;display:inline-block}
.ygd-tcp-backlog-overflow .ygd-val.ygd-pulse{animation:ygd-tcp-backlog-overflow-pop .6s ease-out}
.ygd-tcp-backlog-overflow .ygd-bar{display:flex;gap:4px;margin:6px 0 4px}
.ygd-tcp-backlog-overflow .ygd-seg{flex:1;height:10px;border-radius:3px;background:var(--ygd-border)}
.ygd-tcp-backlog-overflow .ygd-seg.ygd-on{background:var(--ygd-red)}
.ygd-tcp-backlog-overflow .ygd-cap{margin-top:10px;background:var(--ygd-box);border:1px solid var(--ygd-border);border-left:4px solid var(--ygd-blue);border-radius:8px;padding:10px 12px;min-height:7.5em}
.ygd-tcp-backlog-overflow .ygd-capt{font-weight:700;font-size:15px;margin-bottom:4px}
.ygd-tcp-backlog-overflow .ygd-capd{font-size:14px}
.ygd-tcp-backlog-overflow .ygd-ctl{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.ygd-tcp-backlog-overflow .ygd-ctl .ygd-btn{flex:1 1 100px}
.ygd-tcp-backlog-overflow .ygd-note{margin-top:10px;font-size:14px;color:var(--ygd-mut)}
@keyframes ygd-tcp-backlog-overflow-pop{0%{transform:scale(1);color:var(--ygd-red)}40%{transform:scale(1.35);color:var(--ygd-red)}100%{transform:scale(1)}}
@media (prefers-reduced-motion:reduce){.ygd-tcp-backlog-overflow .ygd-val.ygd-pulse{animation:none}.ygd-tcp-backlog-overflow *{transition:none}}
</style>
<div class="ygd-ttl">Accept 큐가 가득 찼을 때: tcp_abort_on_overflow 비교</div>
<div class="ygd-modes" role="group" aria-label="tcp_abort_on_overflow 설정 선택">
<button type="button" class="ygd-btn ygd-mode" data-m="0" aria-pressed="true">tcp_abort_on_overflow = 0 (기본값)</button>
<button type="button" class="ygd-btn ygd-mode" data-m="1" aria-pressed="false">tcp_abort_on_overflow = 1</button>
</div>
<svg class="ygd-svg" viewBox="0 0 400 276" role="img" aria-label="클라이언트, SYN 큐, Accept 큐의 점유 상태와 그 사이를 오가는 패킷을 보여주는 다이어그램. Accept 큐는 가득 차 있다.">
<text class="ygd-th" x="50" y="20" text-anchor="middle">클라이언트</text>
<text class="ygd-tm" x="50" y="36" text-anchor="middle">새 연결 시도</text>
<text class="ygd-th" x="190" y="20" text-anchor="middle">SYN 큐</text>
<text class="ygd-tm" x="190" y="36" text-anchor="middle">반연결</text>
<text class="ygd-th" x="335" y="20" text-anchor="middle">Accept 큐</text>
<text class="ygd-tm" x="335" y="36" text-anchor="middle">완전연결</text>
<rect class="ygd-box" x="10" y="46" width="80" height="186" rx="8"/>
<rect class="ygd-box" x="130" y="46" width="120" height="186" rx="8"/>
<rect class="ygd-box ygd-full" x="280" y="46" width="110" height="186" rx="8"/>
<text class="ygd-t ygd-cs1" x="50" y="136" text-anchor="middle" font-weight="700"></text>
<text class="ygd-t ygd-cs2" x="50" y="154" text-anchor="middle"></text>
<g class="ygd-slot ygd-synslot"><rect x="140" y="58" width="100" height="28" rx="5"/><text class="ygd-t" x="190" y="76" text-anchor="middle">새 연결</text></g>
<g class="ygd-slot"><rect x="140" y="94" width="100" height="28" rx="5"/></g>
<g class="ygd-slot"><rect x="140" y="130" width="100" height="28" rx="5"/></g>
<g class="ygd-slot"><rect x="140" y="166" width="100" height="28" rx="5"/></g>
<text class="ygd-t ygd-synocc" x="190" y="212" text-anchor="middle">점유 0</text>
<g class="ygd-slot ygd-warn ygd-on"><rect x="290" y="58" width="90" height="28" rx="5"/><text class="ygd-t" x="335" y="76" text-anchor="middle">연결 1</text></g>
<g class="ygd-slot ygd-warn ygd-on"><rect x="290" y="94" width="90" height="28" rx="5"/><text class="ygd-t" x="335" y="112" text-anchor="middle">연결 2</text></g>
<g class="ygd-slot ygd-warn ygd-on"><rect x="290" y="130" width="90" height="28" rx="5"/><text class="ygd-t" x="335" y="148" text-anchor="middle">연결 3</text></g>
<g class="ygd-slot ygd-warn ygd-on"><rect x="290" y="166" width="90" height="28" rx="5"/><text class="ygd-t" x="335" y="184" text-anchor="middle">연결 4</text></g>
<text class="ygd-t" x="335" y="210" text-anchor="middle">Recv-Q 4</text>
<text class="ygd-t" x="335" y="225" text-anchor="middle">Send-Q 4</text>
<line class="ygd-lane" x1="50" y1="258" x2="335" y2="258"/>
<circle class="ygd-dot" cx="50" cy="258" r="3"/>
<circle class="ygd-dot" cx="190" cy="258" r="3"/>
<circle class="ygd-dot" cx="335" cy="258" r="3"/>
<g class="ygd-tk ygd-tb" style="display:none"><rect x="-33" y="-9" width="66" height="18" rx="9"/><text x="0" y="4" text-anchor="middle"></text></g>
</svg>
<div class="ygd-stats">
<div class="ygd-card"><div class="ygd-lbl">ListenOverflows 카운터</div><div class="ygd-val ygd-ov">0</div></div>
<div class="ygd-card"><div class="ygd-lbl">SYN 큐 점유</div><div class="ygd-val ygd-sy">0</div></div>
<div class="ygd-card"><div class="ygd-lbl">Accept 큐 점유</div><div class="ygd-val">4 / 4</div></div>
<div class="ygd-card"><div class="ygd-lbl">클라이언트 대기 누적</div><div class="ygd-bar" aria-hidden="true"><span class="ygd-seg"></span><span class="ygd-seg"></span><span class="ygd-seg"></span><span class="ygd-seg"></span></div><div class="ygd-lbl ygd-dl">아직 대기 없음</div></div>
</div>
<div class="ygd-cap" aria-live="polite"><div class="ygd-capt"></div><div class="ygd-capd"></div></div>
<div class="ygd-ctl">
<button type="button" class="ygd-btn ygd-play">재생</button>
<button type="button" class="ygd-btn ygd-next">다음 단계</button>
<button type="button" class="ygd-btn ygd-reset">처음으로</button>
</div>
<div class="ygd-note">비유: 만석인 식당 입구다. 0은 직원이 손님을 문 앞에 세워 둔 채 자리가 나길 기다리게 하는 것이고, 1은 바로 돌려보내는 것이다. 다만 실제 서버는 사람이 아니라 타이머로 SYN+ACK를 재전송한다.</div>
<script>
(function(){
var root=document.getElementById('ygd-tcp-backlog-overflow');
if(!root)return;
var q=function(s){return root.querySelector(s)};
var qa=function(s){return root.querySelectorAll(s)};
var tkG=q('.ygd-tk'),tkR=tkG.querySelector('rect'),tkT=tkG.querySelector('text');
var synSlot=q('.ygd-synslot'),synOcc=q('.ygd-synocc'),cs1=q('.ygd-cs1'),cs2=q('.ygd-cs2');
var ovEl=q('.ygd-ov'),syEl=q('.ygd-sy'),dl=q('.ygd-dl'),segs=qa('.ygd-seg');
var capT=q('.ygd-capt'),capD=q('.ygd-capd');
var playB=q('.ygd-play'),nextB=q('.ygd-next'),resetB=q('.ygd-reset');
var C=50,S=190,B=300;
var TB='ygd-tk ygd-tb',TG='ygd-tk ygd-tg',TGR='ygd-tk ygd-tg ygd-rt',TR='ygd-tk ygd-tr';
var H=[
['초기 상태: Accept 큐가 가득 참','Accept 큐가 이미 가득 찼다. ss로 보면 Recv-Q가 Send-Q와 같은 상태다. 이때 새 클라이언트가 접속을 시도한다.',0,0,0,'대기','(시도 전)',null],
['SYN 도착: SYN 큐에 적재','클라이언트의 SYN이 SYN 큐(반연결)에 들어간다. 이 큐에는 자리가 있어 여기서는 막히지 않는다.',1,0,0,'SYN','전송',['SYN',TB,C,S]],
['서버가 SYN+ACK로 응답','서버가 SYN+ACK를 보낸다. 핸드셰이크는 여기까지 정상적으로 진행된다.',1,0,0,'SYN+ACK','수신',['SYN+ACK',TG,S,C]],
['클라이언트의 ACK 도착','클라이언트가 ACK를 보낸다. 서버는 이 연결을 SYN 큐에서 Accept 큐로 옮기려 한다.',1,0,0,'ACK','전송',['ACK',TB,C,S]]
];
var M=[
H.concat([
['ACK를 버림: ListenOverflows 증가','Accept 큐가 가득 차서 연결을 옮기지 못하고 ListenOverflows가 1 오른다. abort_on_overflow가 0이면 RST를 보내지 않고 연결을 SYN 큐에 둔 채 넘어간다.',1,1,0,'응답','대기',['ACK 버림',TR,S,B]],
['SYN+ACK 재전송: 클라이언트 대기','서버가 SYN+ACK를 다시 보낸다. 클라이언트는 연결이 열리길 기다리며 붙잡혀 있고 대기 시간이 쌓이기 시작한다.',1,1,1,'SYN+ACK','재수신',['SYN+ACK',TGR,S,C]],
['ACK 재응답, 또 버려짐','클라이언트가 ACK로 다시 응답하지만 Accept 큐는 여전히 가득이다. ListenOverflows가 2로 오른다.',1,2,1,'ACK','재응답',['ACK 버림',TR,C,B]],
['SYN+ACK 재전송 반복','같은 과정이 되풀이된다. 클라이언트의 대기 시간은 계속 쌓이고 SYN 큐 점유는 1로 유지된다.',1,2,2,'SYN+ACK','재수신',['SYN+ACK',TGR,S,C]],
['ACK 또 버려짐','ListenOverflows가 3까지 오른다. 큐에 자리가 날 때까지 이 흐름이 이어진다.',1,3,2,'ACK','재응답',['ACK 버림',TR,C,B]],
['정리: 붙잡아 두고 지연이 쌓임','서버는 RST 없이 재전송만 계속한다. 클라이언트는 거부당하지 않는 대신 연결이 열릴지 모른 채 기다리며 지연이 누적된다.',1,3,3,'SYN+ACK','재수신',['SYN+ACK',TGR,S,C]]
]),
H.concat([
['ACK를 버림: ListenOverflows 증가','Accept 큐가 가득 차서 연결을 옮기지 못하고 ListenOverflows가 1 오른다. abort_on_overflow가 1이면 서버는 이 연결을 그냥 두지 않고 정리한다.',1,1,0,'응답','대기',['ACK 버림',TR,S,B]],
['RST 전송: SYN 큐 항목 제거','서버가 RST를 보내고 SYN 큐의 항목을 지운다. SYN 큐 점유가 0으로 돌아온다.',0,1,0,'RST','수신',['RST',TR,S,C]],
['정리: 즉시 거부, 대기 없음','클라이언트는 재전송을 기다리지 않고 즉시 거부당한다(connection reset). 지연은 쌓이지 않지만 실패가 바로 오류로 드러난다. ListenOverflows는 올랐고 Accept 큐는 여전히 가득이다.',0,1,0,'연결','거부됨',['RST',TR,C,C]]
])
];
var mode=0,idx=0,playing=false,timer=null,raf=null,lastOv=0;
function reduced(){return window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches}
function setX(x){tkG.setAttribute('transform','translate('+x+',258)')}
function moveTk(tk){
if(raf){cancelAnimationFrame(raf);raf=null}
if(!tk){tkG.style.display='none';return}
tkG.style.display='';
tkG.setAttribute('class',tk[1]);
tkT.textContent=tk[0];
var x0=tk[2],x1=tk[3];
if(reduced()||x0===x1){setX(x1);return}
var t0=null,dur=700;
setX(x0);
function f(ts){
if(t0===null)t0=ts;
var p=Math.min(1,(ts-t0)/dur);
var e=p<0.5?2*p*p:1-Math.pow(-2*p+2,2)/2;
setX(x0+(x1-x0)*e);
if(p<1){raf=requestAnimationFrame(f)}else{raf=null}
}
raf=requestAnimationFrame(f);
}
function render(){
var steps=M[mode],s=steps[idx],n=steps.length;
capT.textContent=(idx+1)+' / '+n+' · '+s[0];
capD.textContent=s[1];
synSlot.setAttribute('class','ygd-slot ygd-synslot'+(s[2]?' ygd-on':''));
synOcc.textContent='점유 '+s[2];
syEl.textContent=s[2];
ovEl.textContent=s[3];
if(s[3]!==lastOv&&s[3]>0){
ovEl.classList.remove('ygd-pulse');
void ovEl.offsetWidth;
ovEl.classList.add('ygd-pulse');
}
lastOv=s[3];
for(var i=0;i<segs.length;i++){segs[i].setAttribute('class','ygd-seg'+(i<s[4]?' ygd-on':''))}
if(mode===0){dl.textContent=s[4]?('SYN+ACK 재전송 '+s[4]+'회째 대기'):'아직 대기 없음'}
else{dl.textContent=idx>=5?'대기 없음: 즉시 거부':'아직 대기 없음'}
cs1.textContent=s[5];
cs2.textContent=s[6];
moveTk(s[7]);
nextB.disabled=idx>=n-1;
}
function updPlay(){
playB.textContent=playing?'일시정지':(idx>=M[mode].length-1?'다시 재생':'재생');
}
function stopPlay(){
playing=false;
clearTimeout(timer);timer=null;
updPlay();
}
function tick(){
if(!playing)return;
if(idx<M[mode].length-1){
idx++;render();
if(idx<M[mode].length-1){timer=setTimeout(tick,3000)}else{stopPlay()}
}else{stopPlay()}
}
playB.addEventListener('click',function(){
if(playing){stopPlay();return}
if(idx>=M[mode].length-1){idx=0;render()}
playing=true;updPlay();
timer=setTimeout(tick,700);
});
nextB.addEventListener('click',function(){
stopPlay();
if(idx<M[mode].length-1){idx++;render()}
updPlay();
});
resetB.addEventListener('click',function(){
stopPlay();idx=0;render();updPlay();
});
var mb=qa('.ygd-mode');
for(var i=0;i<mb.length;i++){
mb[i].addEventListener('click',function(){
stopPlay();
mode=parseInt(this.getAttribute('data-m'),10);
for(var j=0;j<mb.length;j++){mb[j].setAttribute('aria-pressed',mb[j]===this?'true':'false')}
idx=0;lastOv=0;render();updPlay();
});
}
render();updPlay();
})();
</script>
</div>


## 주요 소켓 옵션

소켓 옵션은 잘못 쓰면 운영 장애로 이어지는 항목이 많다. 기본값을 그대로 쓰면 큰 문제가 없지만, 성능 튜닝이나 특수한 상황에서 손대다가 사고가 나는 경우가 종종 있다.

### SO_REUSEADDR

서버 프로세스를 재시작할 때 "Address already in use" 에러를 피하기 위한 옵션이다. 원인은 이전 프로세스가 사용하던 소켓이 TIME_WAIT 상태로 남아 있어서 같은 포트에 다시 바인딩할 수 없기 때문이다.

```c
int yes = 1;
setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
bind(sockfd, ...);
```

```java
// Java - 바인딩 전에 호출해야 함
ServerSocket server = new ServerSocket();
server.setReuseAddress(true);
server.bind(new InetSocketAddress(8080));
```

```go
// Go - net.ListenConfig (Go 1.11+)
lc := net.ListenConfig{
    Control: func(network, address string, c syscall.RawConn) error {
        return c.Control(func(fd uintptr) {
            syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET, syscall.SO_REUSEADDR, 1)
        })
    },
}
ln, _ := lc.Listen(context.Background(), "tcp", ":8080")
```

리눅스에서 SO_REUSEADDR은 TIME_WAIT 상태 소켓 위에 새 바인딩을 허용한다. 같은 IP:Port 조합을 두 프로세스가 동시에 LISTEN하지는 못한다.

흔한 오해: SO_REUSEADDR이 켜져 있으면 살아있는 LISTEN 소켓을 빼앗을 수 있다고 생각하는데, 그렇지 않다. 같은 포트로 LISTEN 중인 프로세스가 살아있으면 새 프로세스의 bind는 실패한다.

`SO_REUSEADDR`을 켰는데도 바인딩이 안 된다면 다음을 의심한다:
1. 이전 프로세스가 아직 살아있고 LISTEN 중 (`ss -tlnp`로 확인)
2. 클라이언트 측에서 같은 4-tuple로 ESTABLISHED 상태 잔존 (`ss -tnp`로 확인)
3. systemd가 소켓을 잡고 있는 경우 (socket activation)

### SO_REUSEPORT

리눅스 3.9에서 추가된 옵션이다. 같은 IP:Port를 여러 프로세스가 동시에 LISTEN할 수 있게 해주고, 커널이 들어오는 연결을 4-tuple 해시로 각 프로세스에 분배한다.

```c
int yes = 1;
setsockopt(sockfd, SOL_SOCKET, SO_REUSEPORT, &yes, sizeof(yes));
```

```nginx
# Nginx
listen 80 reuseport;
```

멀티프로세스 서버에서 worker 간 부하 분산에 쓴다. 기존에는 1개 프로세스가 accept하고 worker로 넘기거나, 모든 worker가 같은 listen socket에서 accept를 경쟁(thundering herd)했는데, SO_REUSEPORT는 각 프로세스가 독립된 accept 큐를 갖는다.

주의할 점: 한 프로세스가 갑자기 죽으면 그 프로세스의 accept 큐에 쌓여 있던 연결도 같이 사라진다. graceful shutdown을 구현하지 않으면 재시작 시점에 연결이 끊긴 클라이언트가 발생한다.

### SO_LINGER

`close()` 호출 시 송신 버퍼의 처리 방식을 결정한다.

```c
struct linger {
    int l_onoff;   // 0이면 비활성, 1이면 활성
    int l_linger;  // 대기 시간(초)
};

struct linger lin = { .l_onoff = 1, .l_linger = 0 };
setsockopt(sockfd, SOL_SOCKET, SO_LINGER, &lin, sizeof(lin));
```

세 가지 동작:

| 설정 | 동작 |
|------|------|
| `l_onoff=0` (기본값) | close() 즉시 리턴. 커널이 백그라운드에서 송신 버퍼를 비우고 FIN으로 정상 종료 |
| `l_onoff=1, l_linger>0` | 송신 버퍼가 비거나 타임아웃까지 close() 블록 |
| `l_onoff=1, l_linger=0` | 송신 버퍼를 버리고 RST 전송. 정상 종료 없이 즉시 끊김 |

`l_linger=0`은 TIME_WAIT을 만들지 않으려고 쓰는 경우가 있는데 위험하다. 상대방은 RST를 받고 비정상 종료로 인식한다. HTTP 응답을 다 보내기 전에 끊기는 경우도 있어서 운영 서버에서는 거의 쓸 일이 없다.

쓸 만한 상황은 부하 테스트 도구처럼 짧은 연결을 빠르게 만들었다 끊는 경우 정도다. 일반 백엔드 서버에서는 손대지 않는 게 안전하다.

### SO_KEEPALIVE

소켓 단위로 TCP keepalive를 켜는 옵션이다. 기본값이 OFF라서 명시적으로 켜야 동작한다.

```java
socket.setKeepAlive(true);
```

```go
conn.SetKeepAlive(true)
conn.SetKeepAlivePeriod(30 * time.Second)  // 소켓별 주기 설정
```

`SO_KEEPALIVE`만 켜면 주기는 시스템 기본값(`tcp_keepalive_time`)을 따른다. 리눅스 기본값 2시간이 너무 길어서, Go의 `SetKeepAlivePeriod`나 Java NIO의 `TCP_KEEPIDLE` 옵션으로 소켓별 주기를 줄이는 게 일반적이다.

### TCP_NODELAY

Nagle 알고리즘을 끄는 옵션이다. 앞서 Nagle 섹션에서 다뤘다. HTTP 서버, 게임 서버, RPC 서버처럼 작은 메시지를 자주 주고받는 경우에 켠다.

### 옵션 적용 시점 주의

소켓 옵션은 적용 시점이 중요하다.

- `SO_REUSEADDR`, `SO_REUSEPORT`: `bind()` **이전**에 설정해야 한다
- `SO_KEEPALIVE`, `TCP_NODELAY`: `connect()` 또는 `accept()` 이후에도 설정 가능
- `SO_LINGER`: `close()` **이전**에 설정해야 한다

서버 코드를 짤 때 ServerSocket을 만든 후 bind 호출 전에 옵션을 설정하는 흐름을 잘 지켜야 한다. Java의 `ServerSocket` 생성자에서 포트를 지정하면 내부적으로 bind까지 끝나버려서 setReuseAddress가 효과 없는 경우가 있다.

```java
// 잘못된 예 - 생성자에서 이미 bind됨
ServerSocket server = new ServerSocket(8080);
server.setReuseAddress(true);  // 효과 없음

// 올바른 예 - bind 전에 설정
ServerSocket server = new ServerSocket();
server.setReuseAddress(true);
server.bind(new InetSocketAddress(8080));
```


## 실무 트러블슈팅

### tcpdump로 TCP 상태 확인

```bash
# 특정 호스트와의 TCP 통신 캡처
tcpdump -i eth0 host 10.0.1.5 -nn

# 3-way handshake만 보기 (SYN 패킷 필터)
tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0' -nn

# FIN, RST 패킷 보기 (연결 종료 문제 분석)
tcpdump -i eth0 'tcp[tcpflags] & (tcp-fin|tcp-rst) != 0' -nn

# 특정 포트의 통신을 pcap 파일로 저장 (Wireshark에서 분석)
tcpdump -i eth0 port 8080 -w /tmp/capture.pcap -c 10000

# 재전송 패킷 확인 (같은 seq 번호가 반복되면 재전송)
tcpdump -i eth0 port 8080 -nn -S  # -S: 절대 시퀀스 번호 표시
```

### ss와 netstat로 TCP 상태 분석

`ss`는 `netstat`을 대체하는 명령어다. netstat은 `/proc/net/tcp`를 파싱하지만 ss는 netlink 소켓을 직접 쓰기 때문에 연결이 수만 개 수준이 되면 체감 속도 차이가 크다. 최신 배포판은 net-tools 패키지(`netstat`이 들어있는) 자체가 기본 설치되지 않는 경우가 많아 ss를 익혀두는 쪽이 안전하다.

자주 쓰는 명령어 대응:

| 목적 | netstat | ss |
|------|---------|-----|
| 전체 TCP 연결 | `netstat -an` | `ss -tan` |
| LISTEN 포트와 프로세스 | `netstat -tlnp` | `ss -tlnp` |
| 상태별 통계 요약 | `netstat -s` | `ss -s` |
| ESTABLISHED만 | `netstat -an \| grep EST` | `ss -tn state established` |
| TIME_WAIT만 | `netstat -an \| grep TIME_WAIT` | `ss -tn state time-wait` |
| 라우팅 테이블 | `netstat -rn` | `ip route` |

netstat을 써야 하는 환경(오래된 컨테이너 이미지, 일부 임베디드 장비)에서도 동일한 정보를 뽑을 수 있도록 양쪽 명령어를 같이 알아두는 게 좋다.

```bash
# 상태별 TCP 연결 수 요약
ss -s

# 모든 TCP 연결을 상태별로 확인
ss -tan

# 특정 상태의 연결만 필터
ss -tn state established
ss -tn state time-wait
ss -tn state close-wait

# 특정 포트에 연결된 소켓과 프로세스 확인
ss -tnp dst :3306

# 소켓의 타이머 정보 확인 (keepalive, 재전송 타이머 등)
ss -tno state established

# 내부 TCP 정보 (cwnd, rtt, 재전송 횟수 등)
ss -ti state established
# 출력 예: cubic wscale:7,7 rto:204 rtt:1.5/0.5 cwnd:10 send 78.1Mbps
```

### 자주 겪는 문제와 확인 방법

**연결이 느리게 맺어지는 경우**:
```bash
# SYN 재전송 횟수 확인 - 서버까지 도달 못하면 SYN 재전송이 발생
sysctl net.ipv4.tcp_syn_retries      # 클라이언트 SYN 재전송 횟수
sysctl net.ipv4.tcp_synack_retries   # 서버 SYN+ACK 재전송 횟수

# 방화벽이 SYN을 드롭하면 타임아웃까지 기다려야 하므로 느려짐
# tcp_syn_retries=6이면 최대 약 127초까지 기다림
```

**연결은 되는데 응답이 느린 경우**:
```bash
# 재전송 통계 확인
nstat -az | grep -i retrans
# TcpRetransSegs: 재전송된 세그먼트 수
# TcpExtTCPSlowStartRetrans: Slow Start 중 재전송

# RTT 확인
ss -ti dst 10.0.1.5
# rtt:1.5/0.5 → 평균 1.5ms, 편차 0.5ms
```

**RST로 연결이 끊기는 경우**:
```bash
# RST 패킷 원인 분석
tcpdump -i eth0 'tcp[tcpflags] & tcp-rst != 0' -nn -v

# 흔한 원인:
# 1. 서버 프로세스가 죽음 → 해당 포트에 listen하는 프로세스 없음
# 2. Accept 큐 오버플로우 (tcp_abort_on_overflow=1)
# 3. 방화벽/로드밸런서가 idle 연결을 정리
# 4. 애플리케이션이 SO_LINGER로 즉시 종료 설정
```

**소켓 고갈 문제**:
```bash
# 사용 가능한 로컬 포트 범위
sysctl net.ipv4.ip_local_port_range
# 기본값: 32768 ~ 60999 → 약 28,000개

# TIME_WAIT이 많으면 로컬 포트가 부족해질 수 있음
# 같은 목적지(IP:Port)로의 연결에서 로컬 포트가 고갈
ss -tn state time-wait dst 10.0.1.5:3306 | wc -l

# 포트 범위 확장
sysctl net.ipv4.ip_local_port_range="1024 65535"

# 커넥션 풀을 사용해서 TCP 연결을 재사용하는 게 근본적인 해결책
```
