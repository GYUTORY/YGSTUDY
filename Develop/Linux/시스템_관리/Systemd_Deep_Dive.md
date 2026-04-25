---
title: Linux 시스템 서비스 관리 (systemd) 심화 가이드
tags: [linux, systemd, systemctl, cgroup, journald, service, unit]
updated: 2026-04-25
---

# Linux 시스템 서비스 관리 (systemd) 심화 가이드

## 들어가며

기본 `systemctl start/stop/enable` 명령만 알아도 일상적인 운영은 가능하지만, 운영 환경에서 사고가 터지는 순간은 거의 항상 unit 파일의 디테일에서 나온다. 재시작이 무한 루프로 들어가서 부팅이 안 되거나, `systemctl stop`을 했는데 프로세스가 안 죽거나, 패키지 업데이트가 커스텀 설정을 덮어쓰거나, journal이 디스크를 가득 채우거나 하는 일이 그렇다.

이 문서는 5년간 운영 환경에서 systemd를 다루며 겪었던 함정과 패턴을 정리한 글이다. `systemctl status nginx` 정도는 익숙한 독자를 가정한다.

## Type= 의 진짜 의미

unit 파일의 `Type=` 옵션은 systemd가 "프로세스가 시작됐다"라고 판단하는 시점을 결정한다. 이 판단을 잘못하면 의존하는 후속 서비스가 너무 일찍 시작되거나, 반대로 영영 시작 안 됐다고 판단해서 타임아웃이 나기도 한다.

| Type | systemd가 ready로 판단하는 시점 | 적합한 케이스 |
|------|--------------------------------|--------------|
| `simple` | `ExecStart`로 fork된 프로세스가 실행 시작된 직후 | 기본값. 일반적인 foreground 데몬 |
| `forking` | 부모가 종료되고 자식이 살아있을 때 | 전통적인 Unix 데몬 (자체 fork) |
| `notify` | 자식이 `sd_notify(READY=1)` 보냈을 때 | 시작 시간이 긴 앱 (DB, JVM 등) |
| `dbus` | D-Bus에 `BusName=`이 등록됐을 때 | D-Bus 서비스 |
| `idle` | 다른 작업이 끝날 때까지 시작 지연 | TTY 메시지가 다른 부팅 로그와 섞이지 않게 |
| `oneshot` | `ExecStart`가 종료되면 성공 (그 후 inactive) | 마이그레이션, 초기화 스크립트 |

### simple의 함정

`Type=simple`은 fork만 되면 ready로 본다. 즉 앱이 포트 바인딩에 1초가 걸리는데 의존 서비스가 곧바로 그 포트로 접속하면 connection refused가 난다. 가장 흔한 사고 패턴이다.

```ini
# 의존성이 있다면 Type=notify를 쓰는 게 맞다
[Service]
Type=notify
NotifyAccess=main
ExecStart=/usr/bin/myapp
```

### sd_notify로 정확하게 ready 알리기

`Type=notify`를 쓰면 앱이 `sd_notify` 프로토콜로 systemd에 상태를 보고해야 한다. systemd가 `NOTIFY_SOCKET` 환경변수에 유닉스 소켓 경로를 넣어주고, 앱은 거기에 메시지를 쓴다.

Python 예제:

```python
import socket
import os

def sd_notify(state: str) -> None:
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr.startswith("@"):
        addr = "\0" + addr[1:]  # abstract namespace
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.connect(addr)
        s.sendall(state.encode())

# 앱 초기화가 끝나면
sd_notify("READY=1\nSTATUS=Listening on :8080")

# 종료 시작 시
sd_notify("STOPPING=1")

# Watchdog 갱신
sd_notify("WATCHDOG=1")
```

Node.js는 `sd-notify` 패키지, Java는 `systemd-java-notify` 등 언어별 라이브러리가 있지만 위처럼 직접 소켓에 쓰는 게 가장 단순하다.

## ExecStart의 prefix 기호

`ExecStart=`, `ExecStartPre=` 등에 명령어를 적을 때 앞에 붙는 기호를 모르면 unit 파일을 읽을 때 헷갈린다.

```ini
ExecStartPre=-/usr/bin/mkdir -p /var/run/myapp
ExecStartPre=+/usr/bin/chown myapp:myapp /var/run/myapp
ExecStart=@/usr/bin/myapp myapp-renamed --config /etc/myapp.conf
ExecStartPost=!/usr/bin/post-init.sh
```

| 기호 | 의미 |
|------|------|
| `-` | 실패해도 무시 (exit code 0이 아니어도 다음 단계 진행) |
| `@` | argv[0]을 다음 단어로 덮어쓴다. ps에서 다른 이름으로 보이게 할 때 |
| `+` | User= 설정을 무시하고 root로 실행 |
| `!` | User=, Group= 설정만 적용하고 SystemCallFilter, NoNewPrivileges 같은 격리는 건너뜀 |
| `!!` | `!`와 동일하되 ambient capability를 지원하지 않는 시스템에서만 효과 |

`-` 는 실무에서 자주 쓴다. 디렉토리가 이미 있어도 `mkdir`이 실패해서 서비스가 안 뜨는 일을 막아준다. `+`는 mount나 네트워크 설정처럼 일부 작업만 root 권한이 필요할 때 유용하다.

## ExecStartPre/Post와 ExecStopPost

`ExecStart` 앞뒤에 추가 스크립트를 끼워 넣을 수 있다. 흐름을 정리하면 이렇다.

```
ExecStartPre  → ExecStart  → (running)  → ExecStop  → ExecStopPost
                              ↑
                       ExecStartPost (병렬)
```

```ini
[Service]
Type=simple
ExecStartPre=-/usr/bin/mkdir -p /var/log/myapp
ExecStartPre=/usr/bin/chmod 755 /var/log/myapp
ExecStart=/usr/bin/myapp
ExecStartPost=/usr/bin/curl -X POST http://localhost:9090/notify-up
ExecStop=/usr/bin/myapp --graceful-stop
ExecStopPost=/usr/bin/curl -X POST http://localhost:9090/notify-down
```

주의할 점은 `ExecStartPost`는 메인 프로세스 시작 직후에 병렬로 실행된다는 것이다. `Type=simple`이면 메인 프로세스가 정말 ready인지 확인 안 하고 곧바로 실행되므로, 헬스체크 같은 건 sleep을 넣거나 `Type=notify`로 바꿔야 한다.

`ExecStopPost`는 정상 종료뿐 아니라 비정상 종료 후에도 실행되므로 cleanup 용도로 좋다. 단, 시스템 셧다운 중에는 제한 시간이 짧으니 무거운 작업을 넣으면 안 된다.

## Restart 정책과 재시작 루프 방지

운영에서 가장 많이 사고 나는 부분이 재시작 정책이다. `Restart=always`만 적어두면 앱이 시작 직후 죽는 버그가 있을 때 1초 간격으로 무한히 재시작되고, journal이 폭발한다.

### Restart 옵션 비교

| 값 | 동작 |
|----|------|
| `no` | 재시작 안 함 (기본값) |
| `on-success` | exit code 0으로 끝났을 때만 |
| `on-failure` | 0이 아닌 exit, 시그널, 타임아웃 시 |
| `on-abnormal` | 시그널, 타임아웃 (정상/비정상 exit code는 제외) |
| `on-watchdog` | watchdog 타임아웃 시 |
| `on-abort` | SIGABRT 등으로 죽었을 때 |
| `always` | 어떤 이유로 끝나도 재시작 |

대부분의 운영 서비스는 `on-failure`가 정답이다. `always`는 `systemctl stop`이 normal exit으로 처리되긴 하지만, 앱이 의도적으로 exit 0을 호출하는 경우 (예: graceful drain 후 종료) 까지 재시작하기 때문에 의도와 다를 수 있다.

### 재시작 루프 방지

```ini
[Service]
Restart=on-failure
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s

[Unit]
StartLimitBurst=5
StartLimitIntervalSec=60s
```

`StartLimitIntervalSec=60s` 동안 `StartLimitBurst=5`번 재시작 시도가 실패하면 systemd는 더 이상 재시작하지 않고 unit을 `failed` 상태로 둔다. 알림 시스템이 이걸 잡으면 진짜 사람이 봐야 할 상황을 놓치지 않는다.

함정 하나: 옛날 systemd 버전(<v230)에서는 `StartLimitBurst`가 `[Service]` 섹션에 있었지만, 최신 버전은 `[Unit]` 섹션에 있다. 호환성을 위해 두 곳에 다 적어두는 unit 파일을 종종 본다.

`RestartSec`은 너무 짧으면 무한 루프, 너무 길면 사용자가 다운타임을 길게 느낀다. 5~10초가 무난하다.

## drop-in으로 패키지 unit 안전하게 덮어쓰기

`/usr/lib/systemd/system/nginx.service`를 직접 수정하면 패키지 업데이트할 때 덮어쓰여진다. 정답은 drop-in 디렉토리.

```bash
# 권장 방법
sudo systemctl edit nginx
# → /etc/systemd/system/nginx.service.d/override.conf 생성/편집
```

`systemctl edit`은 빈 파일을 열어주는데, 기존 unit 전체가 아니라 덮어쓸 부분만 적으면 된다.

```ini
# /etc/systemd/system/nginx.service.d/override.conf
[Service]
LimitNOFILE=65535
Environment="NGINX_WORKER_PROCESSES=8"
```

기존 값을 완전히 비우고 새로 쓰고 싶으면 빈 값을 한 번 넣어줘야 한다. 이건 `Exec*=`나 `Environment=` 같은 누적되는 항목에 해당한다.

```ini
[Service]
ExecStart=
ExecStart=/usr/sbin/nginx -g "daemon off; pid /run/nginx.pid;"
```

`ExecStart=` 한 줄로 비우지 않으면 `ExecStart`가 두 개가 되어버린다 (`Type=oneshot`이 아니면 unit이 안 뜬다).

drop-in 적용 후에는 반드시:

```bash
sudo systemctl daemon-reload
sudo systemctl restart nginx
```

`systemctl cat nginx`로 최종 병합된 unit을 확인할 수 있다. 이게 진짜 적용된 설정이다.

## 보안 강화 옵션

리눅스 컨테이너 없이도 systemd 옵션만으로 상당한 격리를 걸 수 있다. 운영 환경 unit 파일에는 최소한 다음 정도는 들어가야 한다.

```ini
[Service]
# 파일시스템
ProtectSystem=strict          # /usr, /boot, /etc 읽기전용 (full은 /etc 제외)
ProtectHome=true              # /home, /root, /run/user 접근 차단
PrivateTmp=true               # /tmp, /var/tmp 격리
ReadWritePaths=/var/log/myapp /var/lib/myapp

# 디바이스/커널
PrivateDevices=true           # /dev에 최소한만
ProtectKernelTunables=true    # /proc/sys, /sys 읽기전용
ProtectKernelModules=true
ProtectControlGroups=true

# 권한
NoNewPrivileges=true          # setuid 바이너리 무력화
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
RestrictSUIDSGID=true

# 시스템콜
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
SystemCallArchitectures=native

# 네트워크
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
```

### ProtectSystem과 ReadWritePaths

`ProtectSystem=strict`은 거의 전체 파일시스템을 읽기전용으로 만든다. 앱이 로그를 쓰거나 데이터 파일을 만들어야 한다면 `ReadWritePaths=`로 예외를 명시해야 한다. 빠뜨리면 앱이 EROFS로 죽는다.

```ini
ProtectSystem=strict
ReadWritePaths=/var/log/myapp /var/lib/myapp /var/cache/myapp
```

### CAP_NET_BIND_SERVICE

1024 미만 포트를 바인드하려면 root거나 `CAP_NET_BIND_SERVICE`가 있어야 한다. 일반 유저로 80번 포트를 쓰려면:

```ini
[Service]
User=myapp
Group=myapp
AmbientCapabilities=CAP_NET_BIND_SERVICE
```

`CapabilityBoundingSet`은 프로세스가 가질 수 있는 capability의 상한이고, `AmbientCapabilities`는 실제로 부여되는 것이다. 둘 다 필요하다.

### SystemCallFilter

seccomp 필터를 unit 단위로 걸 수 있다. `@system-service`는 일반 서비스에 필요한 시스템콜 묶음이고, `~@privileged`는 그중에서 권한 관련 콜을 빼라는 뜻이다.

```ini
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources @debug
```

너무 빡빡하게 걸면 앱이 SIGSYS로 죽는다. `journalctl -u myapp` 에 `seccomp` 관련 로그가 보이면 필터를 풀거나 범위를 조정해야 한다.

### 보안 점수 확인

```bash
systemd-analyze security myapp.service
```

각 옵션별 위험도와 점수가 나온다. 0점에 가까울수록 격리가 잘 되어있다. 처음 보면 9점대가 나오는 unit이 흔하다.

## Resource Control과 cgroup v2

systemd는 cgroup v2 (또는 hybrid) 위에서 동작한다. unit 파일 옵션이 곧 cgroup 설정으로 들어간다.

```ini
[Service]
# 메모리
MemoryMax=2G                  # 하드 리밋. 넘으면 OOM kill
MemoryHigh=1500M              # 소프트 리밋. 넘으면 throttle
MemorySwapMax=0               # 스왑 사용 금지

# CPU
CPUQuota=200%                 # CPU 2개 분량
CPUWeight=100                 # 1~10000, 기본 100

# I/O
IOWeight=100                  # 1~10000, 기본 100
IOReadBandwidthMax=/dev/sda 50M

# Task
TasksMax=4096                 # fork bomb 방지
```

### MemoryMax vs MemoryHigh

`MemoryMax`는 절대 한계다. 넘기 직전까지 reclaim하다 안 되면 OOM이다. `MemoryHigh`는 부드러운 한계로, 넘으면 process가 throttle 상태로 들어가고 reclaim이 일어난다. 둘 다 거는 게 맞다.

JVM처럼 자체적으로 메모리를 관리하는 앱은 `MemoryHigh`만 두고 `MemoryMax`는 넉넉히 잡는 편이 안전하다. JVM이 GC 중에 일시적으로 메모리를 많이 쓰는 패턴이 있어서다.

### 모니터링

```bash
systemd-cgtop                              # top 처럼 cgroup별 사용량
systemctl status myapp                     # 메모리, 태스크 수 표시
systemd-cgls                               # cgroup 트리 구조
cat /sys/fs/cgroup/system.slice/myapp.service/memory.current
```

`systemd-cgtop`은 운영 중 메모리 누수를 빠르게 확인할 때 유용하다.

## Slice 구조

systemd는 모든 unit을 slice 트리에 배치한다. 기본 slice는 셋이다.

```
-.slice
├── system.slice/      # 시스템 데몬 (대부분의 .service)
├── user.slice/        # 로그인 사용자
│   └── user-1000.slice/
└── machine.slice/     # nspawn, VM
```

slice 단위로 리소스 한계를 걸 수 있다. 예를 들어 사용자 전체에 메모리 상한을 걸려면:

```bash
sudo systemctl edit user.slice
```

```ini
[Slice]
MemoryMax=4G
CPUQuota=400%
```

커스텀 slice도 만들 수 있다. 여러 서비스를 묶어서 공통 한계를 걸 때 유용하다.

```ini
# /etc/systemd/system/myapp.slice
[Slice]
MemoryMax=8G
CPUQuota=400%

# myapp-api.service
[Service]
Slice=myapp.slice
```

## Socket activation

inetd 스타일의 lazy start를 systemd로 구현할 수 있다. `.socket` unit이 포트를 listen하고 있다가 연결이 들어오면 `.service`를 시작한다.

```ini
# /etc/systemd/system/myapp.socket
[Unit]
Description=MyApp Socket

[Socket]
ListenStream=8080
Accept=no

[Install]
WantedBy=sockets.target
```

```ini
# /etc/systemd/system/myapp.service
[Unit]
Requires=myapp.socket

[Service]
ExecStart=/usr/bin/myapp
StandardInput=socket
```

`Accept=no`는 accept된 연결이 아니라 listen 소켓 자체를 앱에 넘긴다. 앱이 자체적으로 accept 루프를 돌리는 형태다. 보통 이게 맞다.

`Accept=yes`는 연결마다 새 인스턴스를 만든다 (`myapp@1.service`, `myapp@2.service`...). 옛날 inetd 스타일이고, 연결당 fork 비용 때문에 거의 안 쓴다.

장점은 부팅 시간 단축과 zero-downtime 재시작이다. 서비스 재시작 중에도 소켓은 계속 listen하고 있어서 connection refused가 안 난다 (커널 큐에 쌓인다).

## Path unit

파일이나 디렉토리 변화를 감지해서 서비스를 트리거할 수 있다.

```ini
# /etc/systemd/system/upload-watch.path
[Path]
PathChanged=/var/spool/uploads
Unit=upload-process.service

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/upload-process.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/process-uploads
```

inotify 기반이라 가볍다. cron으로 1분마다 폴링하던 스크립트를 path unit으로 바꾸면 즉시성과 효율이 둘 다 올라간다.

`PathExists=`, `PathExistsGlob=`, `PathChanged=`, `PathModified=`, `DirectoryNotEmpty=` 옵션이 있다. `PathChanged`는 파일이 닫힐 때 (write 완료 시점), `PathModified`는 매 write마다 트리거되므로 의도에 맞게 골라야 한다.

## Template unit과 인스턴스 변수

unit 이름에 `@`가 들어가면 템플릿이다. 같은 unit을 파라미터만 바꿔서 여러 인스턴스로 띄울 수 있다.

```ini
# /etc/systemd/system/worker@.service
[Unit]
Description=Worker for queue %i

[Service]
ExecStart=/usr/bin/worker --queue=%i --instance=%I
WorkingDirectory=/var/lib/worker/%i
```

```bash
sudo systemctl start worker@email.service
sudo systemctl start worker@sms.service
sudo systemctl start worker@push.service
```

자주 쓰는 specifier:

| 코드 | 의미 |
|------|------|
| `%i` | 인스턴스 이름 (escape된 형태) |
| `%I` | 인스턴스 이름 (unescape) |
| `%n` | 전체 unit 이름 (worker@email.service) |
| `%N` | 전체 unit 이름 unescape |
| `%p` | unit 이름의 prefix (worker) |
| `%h` | 사용자 홈 디렉토리 |
| `%H` | 호스트명 |
| `%U` | 사용자 UID |
| `%u` | 사용자 이름 |

`%h`와 `%H`를 헷갈려서 사고가 나는 경우가 있다. 소문자 `%h`는 home, 대문자 `%H`는 hostname이다.

`%i`와 `%I`의 차이는 `worker@my-queue.service` 같이 특수문자가 들어갈 때 드러난다. `%i`는 `\x2d` 같이 escape된 형태로 나오고, `%I`는 디코드된 원본이다. 파일 경로에 쓸 때는 `%I`가 보통 맞다.

## Watchdog

앱이 hang 상태로 빠질 때 systemd가 강제로 재시작하게 만든다.

```ini
[Service]
Type=notify
WatchdogSec=30s
Restart=on-watchdog
NotifyAccess=main
ExecStart=/usr/bin/myapp
```

앱은 30초마다 `WATCHDOG=1`을 보내야 한다. 못 보내면 systemd가 SIGTERM으로 죽이고 재시작한다.

```python
import os, time, threading

def watchdog_loop():
    interval = int(os.environ.get("WATCHDOG_USEC", "30000000")) // 2 // 1_000_000
    while True:
        sd_notify("WATCHDOG=1")
        time.sleep(interval)

threading.Thread(target=watchdog_loop, daemon=True).start()
```

`WATCHDOG_USEC` 환경변수에 마이크로초 단위로 타임아웃이 들어온다. 보통 그 절반 주기로 ping을 보내는 게 안전하다.

watchdog의 핵심은 단순 ping이 아니라 "앱이 진짜 일하고 있는지" 확인하는 거다. 메인 이벤트 루프 안에서 ping을 보내면, 데드락이나 무한루프에 빠졌을 때 자연스럽게 ping이 멈춘다. 별도 스레드에서 ping을 돌리면 메인이 죽어도 ping이 가는 의미 없는 패턴이 된다.

## systemd-run으로 임시 unit 실행

매번 unit 파일을 만들지 않고 일회성으로 명령을 systemd 관리하에 돌릴 수 있다.

```bash
# 임시 서비스로 백그라운드 실행
systemd-run --unit=mybackup --slice=backup.slice \
    --property=MemoryMax=1G \
    /usr/local/bin/backup.sh

# 결과 확인
systemctl status mybackup
journalctl -u mybackup -f

# 임시 타이머 (5분 뒤 한 번만 실행)
systemd-run --on-active=5m /usr/local/bin/cleanup.sh

# cron 스타일 매시간
systemd-run --on-calendar=hourly /usr/local/bin/sync.sh
```

특히 메모리/CPU 한계 걸어서 무거운 작업 돌릴 때 유용하다. `nice`나 `cgexec`보다 깔끔하다.

```bash
# DB 백업을 메모리 2G, CPU 50%로 제한
systemd-run --scope -p MemoryMax=2G -p CPUQuota=50% \
    pg_dump mydb > backup.sql
```

`--scope`는 새 프로세스를 만들지 않고 현재 셸을 cgroup에 넣는다. 결과를 곧바로 stdout으로 받을 때 쓴다.

## journalctl 고급 사용

`journalctl -u myapp` 정도는 누구나 쓰지만, 운영 환경에선 더 정밀한 필터가 필요하다.

```bash
# 특정 PID
journalctl _PID=12345

# 특정 unit (-u 옵션과 동일하지만 정확)
journalctl _SYSTEMD_UNIT=myapp.service

# UID
journalctl _UID=1000

# 시간 범위
journalctl --since "2026-04-25 09:00" --until "2026-04-25 10:00"
journalctl --since "1 hour ago"

# 우선순위 (emerg=0, err=3, warning=4, info=6, debug=7)
journalctl -p err -u myapp

# 정규식 grep
journalctl -u myapp --grep "timeout|connection refused"

# JSON 출력 (파싱하기 좋음)
journalctl -u myapp -o json
journalctl -u myapp -o json-pretty

# 부팅 단위로
journalctl -b           # 현재 부팅
journalctl -b -1        # 직전 부팅
journalctl --list-boots
```

### 디스크 관리

journal이 디스크를 가득 채워서 시스템이 멈추는 사고가 의외로 많다.

```bash
# 현재 사용량
journalctl --disk-usage

# 크기로 정리 (1GB만 남기고 삭제)
sudo journalctl --vacuum-size=1G

# 시간으로 정리 (7일 이전 삭제)
sudo journalctl --vacuum-time=7d

# 파일 개수로 정리
sudo journalctl --vacuum-files=10
```

자동 정리는 `/etc/systemd/journald.conf`:

```ini
[Journal]
Storage=persistent          # /var/log/journal에 저장
SystemMaxUse=2G             # 디스크 최대 2G
SystemKeepFree=4G           # 디스크 4G는 항상 free로 유지
SystemMaxFileSize=128M      # 개별 journal 파일 최대 크기
MaxRetentionSec=1month      # 최대 보관 기간
ForwardToSyslog=no
```

설정 변경 후:

```bash
sudo systemctl restart systemd-journald
```

### Persistent journal

기본은 `/run/log/journal`(tmpfs)에 저장돼서 재부팅하면 사라진다. 영구 저장하려면:

```bash
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

또는 `journald.conf`에 `Storage=persistent`. 운영 서버는 거의 항상 persistent로 둔다.

## systemd-analyze로 부팅 분석

부팅이 느려졌을 때.

```bash
# 전체 부팅 시간
systemd-analyze

# unit별 시간 (오래 걸린 순)
systemd-analyze blame

# 의존성 critical path
systemd-analyze critical-chain
systemd-analyze critical-chain myapp.service

# SVG 차트 생성
systemd-analyze plot > boot.svg

# unit 파일 검증
systemd-analyze verify /etc/systemd/system/myapp.service
```

`blame`은 시작이 오래 걸린 unit을 보여주지만, 의존성 때문에 대기한 시간도 포함된다. 진짜 병목은 `critical-chain`으로 봐야 한다.

```bash
$ systemd-analyze critical-chain
multi-user.target @8.342s
└─myapp.service @3.821s +4.521s
  └─postgresql.service @1.234s +2.587s
    └─network-online.target @1.230s
```

`+4.521s`가 그 unit이 실제로 시작에 쓴 시간이다.

## 시크릿 관리

DB 비밀번호 같은 걸 unit 파일에 직접 쓰면 `systemctl cat`으로 누구나 본다. 분리해야 한다.

### EnvironmentFile

```ini
[Service]
EnvironmentFile=/etc/myapp/secret.env
ExecStart=/usr/bin/myapp
```

```bash
# /etc/myapp/secret.env
DB_PASSWORD=s3cr3t
API_KEY=abc123
```

```bash
sudo chown root:root /etc/myapp/secret.env
sudo chmod 600 /etc/myapp/secret.env
```

권한이 600/root여야 일반 사용자가 못 읽는다. 600이 아니면 `cat /etc/myapp/secret.env`로 그냥 보인다.

### LoadCredential (systemd 247+)

더 안전한 방법은 `LoadCredential=`이다. 자격증명을 환경변수가 아니라 메모리 매핑된 임시 파일로 전달한다.

```ini
[Service]
LoadCredential=db_password:/etc/myapp/db_password
ExecStart=/usr/bin/myapp
```

앱은 `$CREDENTIALS_DIRECTORY/db_password` 경로에서 읽는다. 환경변수와 달리 `/proc/<pid>/environ`에 안 노출된다.

```python
import os
cred_dir = os.environ["CREDENTIALS_DIRECTORY"]
with open(f"{cred_dir}/db_password") as f:
    password = f.read().strip()
```

`SetCredentialEncrypted=`로 암호화된 자격증명도 가능하다 (TPM 활용).

## 트러블슈팅

### SIGTERM을 받고도 안 죽는 프로세스

`systemctl stop`을 해도 한참 hang 되다가 강제 종료되는 케이스. 원인은 보통:

1. 앱이 SIGTERM 핸들러가 없어서 무시
2. 앱이 graceful shutdown 중인데 너무 오래 걸림
3. 자식 프로세스가 살아있어서 cgroup이 비지 않음

```ini
[Service]
KillMode=mixed              # main에 SIGTERM, 나머지는 SIGKILL
KillSignal=SIGTERM
TimeoutStopSec=30s           # 30초 내 안 죽으면 SIGKILL
SendSIGKILL=yes              # SIGKILL 보낼지 여부 (기본 yes)
SendSIGHUP=no                # SIGTERM 후 SIGHUP도 보낼지
```

### KillMode 선택

| 값 | 동작 |
|----|------|
| `control-group` | 전체 cgroup에 SIGTERM (기본값) |
| `mixed` | main에 SIGTERM, 자식들은 SIGKILL |
| `process` | main에만 SIGTERM, 자식은 그대로 |
| `none` | 시그널 안 보냄 (위험) |

`control-group`이 기본이고 보통 맞다. nginx 같이 master가 worker를 직접 graceful shutdown 시키는 앱은 `mixed`나 `process`를 써야 master가 깔끔하게 처리할 시간을 준다.

### graceful shutdown 패턴

```python
import signal, sys, time

shutdown = False

def handle_sigterm(signum, frame):
    global shutdown
    shutdown = True
    sd_notify("STOPPING=1\nSTATUS=Draining connections")

signal.signal(signal.SIGTERM, handle_sigterm)

while not shutdown:
    process_one_request()
    
# 큐 드레인
drain_pending(timeout=20)
sys.exit(0)
```

`TimeoutStopSec=30s`로 두면 30초 안에 끝내야 한다. 앱이 더 필요하면 unit에서 늘려준다.

### 자주 놓치는 함정

#### After= ≠ Requires=

`After=`는 시작 순서만 정한다. 의존하는 unit이 실패해도 내 unit은 시작된다.

```ini
[Unit]
After=postgresql.service
Requires=postgresql.service       # 함께 시작/중지
# 또는
Wants=postgresql.service          # 함께 시작 시도, 실패해도 진행
```

`Requires`만 있고 `After`가 없으면 둘이 동시에 시작돼서 race가 난다. 보통은 둘 다 적어야 한다.

| 옵션 | 시작 순서 | 의존 unit이 실패하면 |
|------|----------|--------------------|
| `After=` | 보장 | 무시 |
| `Wants=` | 보장 안 함 | 무시 |
| `Requires=` | 보장 안 함 | 내 unit도 멈춤 |
| `BindsTo=` | 보장 안 함 | 내 unit도 멈춤 (더 강함) |
| `Requisite=` | 보장 안 함 | 즉시 fail (시작 시도조차 안 함) |

전형적인 패턴은 `After=postgresql.service`와 `Requires=postgresql.service`를 함께 쓰는 것.

#### daemon-reload vs daemon-reexec

unit 파일을 바꿨을 때:

```bash
sudo systemctl daemon-reload
```

systemd 자체를 업그레이드했을 때:

```bash
sudo systemctl daemon-reexec
```

`daemon-reload`는 unit 파일만 다시 읽는다. systemd 바이너리가 바뀌어도 새 코드가 적용 안 된다. `daemon-reexec`는 systemd 자체를 PID 1 그대로 두면서 재시작하므로 패키지 업그레이드 후에 한 번 돌려주는 게 좋다.

#### enable과 start의 차이

```bash
sudo systemctl enable myapp     # 부팅 시 자동 시작 설정 (지금은 안 시작)
sudo systemctl start myapp      # 지금 시작 (부팅 시는 자동 아님)
sudo systemctl enable --now myapp   # 둘 다
```

`enable`만 하고 `start` 안 한 채 재부팅 안 하면 서비스가 안 도는 상태다. `--now`를 같이 쓰는 습관을 들이는 게 좋다.

## 실제 운영 unit 템플릿

### Node.js 앱

```ini
# /etc/systemd/system/api-server.service
[Unit]
Description=API Server
After=network-online.target postgresql.service
Wants=network-online.target
Requires=postgresql.service

[Service]
Type=notify
NotifyAccess=main
WatchdogSec=30s

User=apiserver
Group=apiserver
WorkingDirectory=/opt/api-server

Environment=NODE_ENV=production
Environment=PORT=8080
EnvironmentFile=/etc/api-server/secret.env

ExecStartPre=-/usr/bin/mkdir -p /var/log/api-server
ExecStart=/usr/bin/node /opt/api-server/dist/index.js
ExecReload=/bin/kill -HUP $MAINPID

KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30s

Restart=on-failure
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60s

# 리소스
MemoryMax=2G
MemoryHigh=1500M
CPUQuota=200%
TasksMax=4096
LimitNOFILE=65535

# 보안
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictSUIDSGID=true
ReadWritePaths=/var/log/api-server /var/lib/api-server
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources

[Install]
WantedBy=multi-user.target
```

Node.js 코드:

```javascript
const sdNotify = require("sd-notify");

const server = app.listen(process.env.PORT, () => {
    sdNotify.ready();
    sdNotify.startWatchdogMode(15000);
});

let shuttingDown = false;
process.on("SIGTERM", () => {
    if (shuttingDown) return;
    shuttingDown = true;
    sdNotify.stopping();
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 25000).unref();
});
```

### Java/Spring Boot 앱

```ini
# /etc/systemd/system/order-service.service
[Unit]
Description=Order Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=javaapp
Group=javaapp
WorkingDirectory=/opt/order-service

Environment="JAVA_OPTS=-Xms2g -Xmx2g -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
Environment="SPRING_PROFILES_ACTIVE=production"
EnvironmentFile=/etc/order-service/secret.env

ExecStart=/usr/bin/java $JAVA_OPTS -jar /opt/order-service/app.jar

# JVM은 SIGTERM 잘 받지만, shutdown hook이 끝날 때까지 기다려야 함
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=60s

Restart=on-failure
RestartSec=10s
StartLimitBurst=3
StartLimitIntervalSec=120s

# JVM은 자체 메모리 관리. MemoryMax는 -Xmx보다 충분히 크게
MemoryMax=4G
TasksMax=8192
LimitNOFILE=65535

NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/var/log/order-service /var/lib/order-service

[Install]
WantedBy=multi-user.target
```

Spring Boot의 graceful shutdown:

```yaml
# application.yml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

`TimeoutStopSec`은 `timeout-per-shutdown-phase`보다 여유있게 잡는다. 그렇지 않으면 graceful shutdown이 끝나기 전에 SIGKILL이 날아간다.

## 마무리

systemd는 단순한 init 시스템이 아니다. cgroup, namespace, capability, seccomp 같은 커널 기능을 unit 파일 한 줄씩으로 노출하는 격리 도구이자 리소스 관리 도구다. 운영 환경에서 만나는 거의 모든 안정성 문제는 unit 파일을 충분히 빡빡하게 안 짠 데서 온다.

처음 unit 파일을 만들 때 `Type=simple`, `Restart=always`만 적고 끝내지 말고, 위에 정리한 템플릿을 출발점으로 삼아서 보안 옵션과 리소스 한계, watchdog까지 같이 설정하는 습관을 들이면 새벽에 깨는 일이 확연히 줄어든다.
