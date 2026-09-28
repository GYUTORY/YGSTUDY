---
title: TCP 패킷 구조 — Wireshark 실측 기준
tags: [network, tcp]
updated: 2026-09-28
---

# TCP 패킷 구조 — Wireshark 실측 기준

TCP 헤더는 최소 20바이트다. 옵션이 없을 때 딱 20바이트이고, SYN 패킷처럼 MSS·Window Scale·SACK·Timestamp 옵션이 붙으면 40바이트까지 늘어난다. 이 문서는 각 필드를 Wireshark 캡처 실측값 기준으로 설명하고, 3-way handshake 과정에서 hex 레벨로 무슨 일이 일어나는지 따라간다.

## 헤더 바이트 레이아웃

```
바이트 오프셋
 0  1    2  3
[src port][dst port]           포트 번호 (각 16비트)
 4  5  6  7
[   sequence number   ]        시퀀스 번호 (32비트)
 8  9 10 11
[  acknowledgment number  ]    확인 번호 (32비트)
12  13   14 15
[DO|Fl][   window   ]          Data Offset + Flags | 윈도우 크기
16  17   18 19
[checksum][   urg   ]          체크섬 | 긴급 포인터
20 ...
[   options (0~40B)   ]        가변 길이 옵션
```

옵션이 없는 순수한 ACK 패킷은 12번 바이트의 Data Offset 필드가 `0x50`으로 찍힌다. `5 × 4 = 20바이트` 헤더다.

## 각 필드: 실측값 기준

### 포트 번호 (오프셋 0~3)

Wireshark에서 `tcp.srcport == 52846` 필터를 치면 임시 포트(ephemeral port) 구간인 32768~60999 사이의 값이 나온다. 이게 리눅스 커널 기본 범위다. macOS·Windows는 49152~65535를 쓴다.

`curl https://example.com` 직후 캡처한 SYN 패킷:

```
CE 6E   →   0xCE6E = 52846   (클라이언트 임시 포트)
01 BB   →   0x01BB = 443     (HTTPS 서버 포트)
```

같은 호스트에서 탭을 여러 개 열면 각 탭이 다른 임시 포트를 쓴다. TCP 연결은 `(src IP, src port, dst IP, dst port)` 4-튜플로 식별하기 때문에 포트가 겹치면 커널이 구분하지 못한다.

### Sequence Number (오프셋 4~7)

```
3B 9A C9 FF   →   0x3B9AC9FF = 1,000,111,615
```

ISN(Initial Sequence Number)은 예측 불가 난수여야 한다. RFC 6528이 이를 강제한다. 옛날 구현에서 ISN이 예측 가능했을 때 TCP 세션 하이재킹 공격이 가능했다.

Wireshark는 기본 설정에서 ISN을 0으로 표시하고 상대적 오프셋을 보여준다. `Edit → Preferences → Protocols → TCP → Relative Sequence Numbers` 옵션을 끄면 실제 값이 보인다. 두 세션의 시퀀스 번호가 겹치는 문제를 추적할 때는 이 옵션을 꺼야 혼동이 없다.

### Acknowledgment Number (오프셋 8~11)

```
00 00 00 00   →   0                (SYN 패킷: 아직 서버 ISN 모름)
3B 9A CA 00   →   1,000,111,616    (SYN-ACK 이후: 클라이언트 ISN + 1)
```

ACK 번호는 "다음에 받기를 기대하는 바이트 번호"다. 상대방이 Seq=1000을 보내고 10바이트 데이터를 실었으면 내 ACK에는 1010이 들어간다.

ACK 플래그가 0인 패킷에서 ACK 번호 필드는 의미가 없다. 보통 0이지만 뭔가 들어가 있어도 무시된다.

### Data Offset + Flags (오프셋 12~13)

`A0 02` 두 바이트를 한 바이트씩 분리해서 본다.

`0xA0`:
- 상위 4비트 = `0xA` = 10 → 헤더 크기 = 10 × 4 = **40바이트** (옵션 포함)
- 하위 4비트 = Reserved + NS 플래그, 정상 패킷에서는 0

`0x02`:
- 비트 배치 (MSB → LSB): URG, ACK, PSH, RST, SYN, FIN
- `0x02` = `0b0000 0010` → SYN 비트만 1

자주 보이는 플래그 조합:

| 값 | 플래그 | 상황 |
|---|---|---|
| `0x02` | SYN | 연결 요청 |
| `0x12` | SYN+ACK | 연결 응답 |
| `0x10` | ACK | 데이터 확인 |
| `0x18` | PSH+ACK | 애플리케이션 데이터 전송 |
| `0x04` | RST | 연결 강제 종료 |
| `0x11` | FIN+ACK | 정상 종료 요청 |

RST 패킷이 보이는 상황은 크게 두 가지다. 하나는 닫힌 포트로 SYN을 보냈을 때 커널이 RST로 응답하는 경우고, 다른 하나는 방화벽이나 로드밸런서가 idle 연결을 중간에 끊을 때다. 애플리케이션 레벨에서는 `Connection reset by peer` 에러로 나타난다.

### Window Size (오프셋 14~15)

```
FF FF   →   65535 바이트   (SYN 패킷)
04 00   →   1,024          (SYN-ACK, Window Scale 옵션과 함께 봐야 함)
```

주의할 점이 있다. Window Scale 옵션이 협상되면 이 필드의 값에 스케일 팩터를 곱해야 실제 윈도우 크기가 나온다. SYN 패킷의 옵션 섹션에 `03 03 08`이 있으면 Window Scale = 8이다. 이 경우 SYN-ACK의 `04 00 = 1024`는 실제로 `1024 × 2^8 = 262,144바이트`다. Wireshark는 계산된 값을 `Calculated window size: 262144` 형태로 따로 표시한다.

고속 네트워크에서 Window Size가 0으로 떨어지면 수신 측 버퍼가 가득 찬 것이다. 이때 송신 측은 Zero Window Probe를 주기적으로 보내서 버퍼가 비워지기를 기다린다. `tcp.window_size_value == 0` 필터로 잡을 수 있다.

### Checksum (오프셋 16~17)

```
5E 7A   →   0x5E7A   [correct]
```

현대 NIC 대부분은 checksum offload를 지원한다. 커널이 패킷을 만들 때 체크섬 필드를 `0x0000`으로 두면 NIC가 전송 직전에 계산해서 채워 넣는다. Wireshark에서 loopback 인터페이스로 캡처하거나 NIC 직전이 아닌 드라이버 레벨에서 캡처하면 `[incorrect, should be XX]` 경고가 뜬다. 진짜 오류가 아니라 offload 때문이다. `ethtool -K eth0 tx-checksum-ip-generic off`로 offload를 끄거나 외부 인터페이스에서 캡처하면 정상값이 보인다.

### Urgent Pointer (오프셋 18~19)

```
00 00   →   0   (URG 플래그 없을 때는 항상 0)
```

URG 플래그와 세트로 쓰인다. 현대 애플리케이션에서 Telnet을 제외하면 거의 보이지 않는다. 보안 스캐너 중에 URG 비트를 이상하게 조합해서 IDS를 우회하려는 시도가 있는데, 정상 트래픽에서 URG+RST 조합이나 URG 없이 Urgent Pointer 값이 있는 패킷은 의심할 만하다.

## TCP 옵션

옵션은 Kind(1B) + Length(1B) + Value(가변)로 구성된다. Kind만 있는 단일 바이트 옵션도 있다.

```
Kind 0x00   →   End of Options List (EOL)
Kind 0x01   →   No-Operation (NOP, 패딩용)
Kind 0x02   →   MSS: Maximum Segment Size
Kind 0x03   →   Window Scale
Kind 0x04   →   SACK Permitted
Kind 0x05   →   SACK
Kind 0x08   →   Timestamps
```

SYN 패킷의 옵션 섹션을 실제 hex로 보면:

```
02 04 05 B4                            # MSS = 0x05B4 = 1460
04 02                                  # SACK Permitted
08 0A 12 34 56 78 00 00 00 00          # Timestamp (TSval=0x12345678, TSecr=0)
01                                     # NOP (패딩)
03 03 08                               # Window Scale = 8
```

MSS 1460은 이더넷 MTU 1500에서 IP 헤더 20바이트, TCP 헤더 20바이트를 뺀 값이다. 옵션이 없을 때 기준이라 SYN 패킷처럼 TCP 헤더가 40바이트면 페이로드는 1440바이트까지만 들어간다.

PMTUD(Path MTU Discovery)가 정상 작동하면 경로상 가장 좁은 MTU에 맞춰 MSS가 조정된다. 방화벽이 ICMP Type 3 Code 4(Fragmentation Needed)를 차단하면 이 협상이 안 되고 패킷이 조용히 드롭된다. 연결은 되는데 특정 크기 이상 데이터 전송이 막히는 증상이 나타나면 PMTUD 블랙홀을 먼저 의심한다.

## 3-way Handshake: hex dump 단계별

`curl -v https://93.184.216.34:443` 연결 시 Wireshark로 캡처한 패킷을 기준으로 한다. IP 헤더는 제외하고 TCP 헤더만 본다.

### 1단계: SYN (클라이언트 → 서버)

```
오프셋  hex                                 필드 해석
 0- 3  CE 6E 01 BB                         src:52846  dst:443
 4- 7  3B 9A C9 FF                         Seq = 1,000,111,615  (ISN, 매번 다름)
 8-11  00 00 00 00                         Ack = 0  (아직 서버 ISN 모름)
12-13  A0 02                               DO=10(40B)  Flags=0x02 (SYN)
14-15  FF FF                               Win = 65535  (WS 협상 전 원시값)
16-17  5E 7A                               Checksum
18-19  00 00                               Urg = 0
--- 옵션 (20바이트) ---
20-23  02 04 05 B4                         MSS = 1460
24-25  04 02                               SACK Permitted
26-35  08 0A 12 34 56 78 00 00 00 00       Timestamp (TSval/TSecr)
36     01                                  NOP
37-39  03 03 08                            Window Scale = 8
```

SYN 패킷에는 데이터 페이로드가 없다. 헤더 40바이트만 나간다.

### 2단계: SYN-ACK (서버 → 클라이언트)

```
오프셋  hex                                 필드 해석
 0- 3  01 BB CE 6E                         src:443  dst:52846
 4- 7  7A 1B 2C 3D                         Seq = 2,048,442,429  (서버 ISN)
 8-11  3B 9A CA 00                         Ack = 1,000,111,616  (클라이언트 ISN + 1)
12-13  A0 12                               DO=10(40B)  Flags=0x12 (SYN+ACK)
14-15  04 00                               Win = 1,024  (실제 = 1024 × 2^8 = 262,144)
16-17  E3 91                               Checksum
18-19  00 00                               Urg = 0
--- 옵션 (20바이트) ---
20-23  02 04 05 B4                         MSS = 1460
24-25  04 02                               SACK Permitted
26-35  08 0A AB CD EF 01 12 34 56 78       Timestamp
36     01                                  NOP
37-39  03 03 08                            Window Scale = 8
```

ACK 번호를 보면 클라이언트 ISN `3B 9A C9 FF`에 1을 더한 `3B 9A CA 00`이 들어 있다. SYN 자체가 1바이트를 소모한 것으로 처리된다. 데이터가 없어도 SYN·FIN 각각 시퀀스 공간 1을 쓴다.

### 3단계: ACK (클라이언트 → 서버)

```
오프셋  hex                 필드 해석
 0- 3  CE 6E 01 BB         src:52846  dst:443
 4- 7  3B 9A CA 00         Seq = 1,000,111,616  (SYN의 ISN + 1)
 8-11  7A 1B 2C 3E         Ack = 2,048,442,430  (서버 ISN + 1)
12-13  50 10               DO=5(20B)  Flags=0x10 (ACK only)  ← 옵션 없음
14-15  08 00               Win = 2,048  (실제 = 2048 × 2^8 = 524,288)
16-17  F1 23               Checksum
18-19  00 00               Urg = 0
(옵션 없음. 총 20바이트)
```

3단계에서 Data Offset이 `0xA0`에서 `0x50`으로 바뀐다. SYN·SYN-ACK는 40바이트 헤더인데 이후 일반 ACK 패킷은 20바이트로 돌아간다. 연결이 완전히 수립된 뒤의 패킷들은 대부분 Timestamp 옵션만 붙는 32바이트 헤더를 쓴다.

### 세 패킷의 필드 변화 요약

| 필드 | SYN | SYN-ACK | ACK |
|---|---|---|---|
| Src Port | 52846 | 443 | 52846 |
| Dst Port | 443 | 52846 | 443 |
| Seq | ISN_c (랜덤) | ISN_s (랜덤) | ISN_c + 1 |
| Ack | 0 | ISN_c + 1 | ISN_s + 1 |
| Flags | 0x02 (SYN) | 0x12 (SYN+ACK) | 0x10 (ACK) |
| Header size | 40B | 40B | 20B |
| Options | MSS+WS+SACK+TS | MSS+WS+SACK+TS | 없음 |

## Wireshark 디버깅에서 실제로 쓰는 방법

**연결이 맺어지지 않을 때**: SYN 다음에 SYN-ACK가 오는지, RST가 오는지 확인한다. RST가 오면 포트가 닫혀 있거나 방화벽이 RST로 응답하는 것이다. 아무 응답도 없이 SYN 재전송만 반복된다면 방화벽이 패킷을 드롭하는 것이다. 두 경우가 애플리케이션에서는 비슷하게 보이지만 Wireshark로 보면 바로 구분된다.

**연결은 됐는데 데이터 전송이 막힐 때**: `tcp.window_size_value == 0` 필터로 Zero Window 패킷을 찾는다. 수신 측 버퍼가 가득 찬 상태고, 애플리케이션이 소켓 버퍼를 제때 비우지 못하는 경우다. Zero Window Probe가 주기적으로 나가고 있으면 수신 측이 살아 있는 것이고, Probe에 대한 응답도 없으면 연결이 실질적으로 죽은 것이다.

**재전송이 많을 때**: `tcp.analysis.retransmission` 필터. 재전송 간격으로 RTO(Retransmission Timeout) 추정값이 나온다. 첫 재전송이 1초 후면 RTO ≈ 1s, 그 다음이 2초 후면 지수 백오프다. 수십 ms 안에 재전송이 보이면 Fast Retransmit(3 dup ACK)이다.

**응답이 이상하게 느릴 때**: Wireshark 컬럼 설정에서 `tcp.analysis.ack_rtt`를 추가하면 데이터 패킷과 그 ACK 사이의 시간이 찍힌다. 서버 처리 시간인지 네트워크 지연인지 구분하려면 클라이언트 쪽과 서버 쪽 모두에서 동시에 캡처해서 타임스탬프를 비교한다.
