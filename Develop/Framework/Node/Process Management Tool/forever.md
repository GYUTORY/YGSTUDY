---
title: Node.js Forever 프로세스 관리 도구
tags: [framework, node, process-management-tool, forever, nodejs, process-manager]
updated: 2026-04-30
---

# Node.js Forever 프로세스 관리 도구

## 들어가며

forever는 Node.js 프로세스를 데몬으로 띄우고 죽으면 다시 살리는 단순한 도구다. 2010년대 초반 Nodejitsu에서 만들었고, 한때 Express 앱을 운영서버에 올릴 때 표준처럼 쓰였다. 지금 새로 시스템을 짠다면 굳이 forever를 고를 이유가 없다. 그래도 레거시 환경에서 마주칠 일이 적지 않고, "forever로 잘 돌고 있었는데 갑자기 메모리가 새요" 같은 트러블슈팅 요청은 여전히 들어온다.

이 문서는 forever를 그대로 쓰는 방법보다, 왜 지금은 권장되지 않는지와 옮겨가야 할 때 어떤 점을 챙겨야 하는지에 무게를 둔다.

## forever를 쓰면 안 되는 이유

### 유지보수 사실상 중단

GitHub 저장소(foreverjs/forever)는 2019년 이후 의미 있는 커밋이 없다. README에도 "actively maintained alternatives" 운운하며 PM2나 systemd로 가라는 안내가 붙어 있다. 의존성 트리가 오래되어 npm install 단계에서 deprecated 경고와 audit 취약점이 무더기로 뜨는데, 이걸 패치할 사람이 없다. Node.js 18 이후로는 v8 디버거 옵션 변경 같은 사소한 변화에도 forever 내부가 종종 깨진다.

```bash
$ npm install -g forever
npm warn deprecated coffee-script@1.7.1: ...
npm warn deprecated request@2.88.2: ...
# 매번 이런 경고를 보면서 운영 환경을 유지할 수는 없다
```

운영 환경에서 보안 패치가 멈춘 도구를 쓰는 건 그 자체로 위험이다. 사내 보안팀이 SCA 스캔을 돌리는 순간 forever 의존성이 빨간 불부터 띄운다.

### 클러스터 모드 부재

forever는 단일 프로세스를 띄우고 감시할 뿐이다. 멀티 코어를 활용하려면 직접 cluster 모듈로 워커를 포크해야 하는데, 그러면 forever가 마스터만 감시하고 워커가 죽어도 모른다. PM2의 `instances: 'max'` 한 줄이면 끝나는 일을 forever에서는 직접 짜야 한다. 8코어 머신에서 1코어만 쓰면서 "왜 이렇게 느리지" 하는 상황을 자주 본다.

### 무중단 배포 불가

forever restart는 그냥 SIGKILL 후 재시작이다. 새 프로세스가 listen할 때까지 수 초 동안 ECONNREFUSED가 난다. 앞단에 nginx upstream이나 ALB가 있어도 health check 실패 처리에 시간이 걸려서 503이 노출된다. PM2의 reload(graceful)나 systemd의 socket activation 같은 대안이 없다.

## forever, nohup, pm2, systemd

작은 차이라고 보일 수 있지만 운영 시 결과는 완전히 갈린다.

| 항목 | nohup | forever | PM2 | systemd |
|------|-------|---------|-----|---------|
| 자동 재시작 | 없음 | 있음 | 있음 | 있음 (Restart=) |
| 클러스터 | 없음 | 없음 | 있음 | 사용자 구성 |
| 로그 분리 | stdout 리다이렉트만 | out/err 분리 | 일자별 회전 옵션 | journald 통합 |
| 부팅 시 자동 시작 | 별도 작업 필요 | startup 스크립트 별도 | pm2 startup 명령 | 기본 |
| 무중단 배포 | 없음 | 없음 | reload 지원 | socket activation |
| OS 통합 | 단순 | 약함 | 약함 | 강함 |
| 의존성 | 셸 기본 | npm 패키지 | npm 패키지 | OS 기본 |

nohup은 정말 단순한 임시 실행에만 적합하다. 터미널 닫고 나가도 죽지 않는 정도지, 프로세스가 OOM으로 죽으면 그대로 끝이다. 그래서 forever가 등장했지만, 지금은 PM2나 systemd가 그 자리를 가져갔다.

운영 환경 추천 순서는 명확하다. 컨테이너 환경이면 PM2조차 빼고 Node 프로세스를 PID 1로 두거나 tini를 쓰는 쪽이 표준이다. 베어메탈이나 VM이라면 systemd 유닛 파일 하나가 가장 안정적이다. PM2는 기능이 많지만 Node 버전 업그레이드 시 PM2 자체 업그레이드도 챙겨야 하는 부담이 있다. forever는 이 셋 중 어느 자리에도 맞지 않는다.

## 그래도 forever를 써야 한다면

기존 시스템을 당장 옮길 수 없거나, 짧게 임시 운영하는 경우를 위한 최소한의 가이드다.

### 설치와 실행

```bash
npm install -g forever@4.0.3
forever --version

forever start -a -l forever.log -o out.log -e err.log --uid "api" server.js
forever list
forever stop api
```

`-a`는 append, 즉 로그를 덮어쓰지 않고 이어 쓰게 하는 플래그다. 이걸 빼면 재시작할 때마다 로그가 날아간다. `--uid`는 인덱스(0, 1, 2…) 대신 이름으로 프로세스를 식별하게 해주는데, 운영에서는 인덱스로 stop/restart하다가 다른 프로세스를 잘못 건드리는 사고가 흔하다. uid를 항상 붙이는 습관을 들여야 한다.

### forever.json (PM2 ecosystem.json과 헷갈리지 말 것)

`ecosystem.json`이라는 이름은 PM2 규약이다. forever는 자체 JSON 포맷을 쓴다. 둘이 비슷해 보여서 옮길 때 그대로 복사했다가 안 먹는 경우가 있다.

```json
{
  "uid": "api",
  "append": true,
  "watch": false,
  "script": "server.js",
  "sourceDir": "/srv/api",
  "args": ["--harmony"],
  "logFile": "/var/log/api/forever.log",
  "outFile": "/var/log/api/out.log",
  "errFile": "/var/log/api/err.log",
  "killTree": true,
  "minUptime": 5000,
  "spinSleepTime": 2000,
  "env": {
    "NODE_ENV": "production",
    "PORT": "3000"
  }
}
```

여기서 가장 중요한 두 키가 `minUptime`과 `spinSleepTime`이다. 이 둘이 자동 재시작 무한 루프를 막아준다.

## 자동 재시작 무한 루프 방지

forever 운영하면서 가장 흔하게 겪는 사고가 무한 재시작 루프다. 시작 직후 예외가 나서 즉시 죽으면, forever는 곧바로 다시 띄우고, 또 죽고, 또 띄우고… 1초에 수십 번 재시작이 반복되면서 CPU가 100%로 튀고 로그 파티션이 가득 찬다. 새벽에 디스크 풀 알람을 받고 들어가서 보면 forever 로그만 50GB 쌓여 있는 식이다.

기본값으로는 이 보호장치가 약하기 때문에 반드시 명시해야 한다.

```bash
forever start \
  --minUptime 5000 \
  --spinSleepTime 2000 \
  --max 5 \
  --uid api server.js
```

- `minUptime`: 이 시간(ms) 안에 죽으면 "정상적인 실행이 아니다"로 간주한다. 5초 미만에 죽었다면 부팅 자체에 실패했다는 뜻이다.
- `spinSleepTime`: minUptime 안에 죽었을 때 재시작 전 대기 시간(ms). 2초씩 기다리게 하면 최소한 디스크가 가득 차지는 않는다.
- `--max N`: minUptime 미달 재시작이 N번 누적되면 forever 자체가 종료한다. 무한 루프 차단.

`--max` 옵션을 빼고 운영하다가 사고를 한 번 본 다음부터는 무조건 넣는다. forever가 죽으면 외부에서 알림이 오게 (예: monit, systemd watchdog, 또는 별도 헬스체크) 같이 두는 편이 안전하다.

### 시작 직후 크래시의 대표 원인

다섯 번 중 네 번은 환경변수다. forever가 보는 환경과 셸 환경이 다르다. 특히 sudo로 띄울 때 PATH나 NODE_ENV가 빠져 있어서 require 단계부터 터진다. systemd라면 `EnvironmentFile=`로 명시할 텐데, forever에서는 forever.json의 `env`에 직접 박거나 셸 스크립트로 export해서 넣어야 한다.

## 로그 회전

forever는 자체 로그 회전이 없다. 한 파일이 무한히 커진다. 운영 며칠만 지나면 로그 파일이 GB 단위로 부풀고, vi로 열다가 서버가 멈춘다.

OS의 logrotate에 맡기는 게 표준 답이다. forever는 SIGHUP을 받아도 파일 핸들을 다시 열지 않으므로, copytruncate를 써야 한다.

```
# /etc/logrotate.d/forever-api
/var/log/api/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    size 100M
}
```

`copytruncate`는 원본 파일을 복사한 뒤 truncate하는 방식이라 forever가 들고 있는 파일 디스크립터가 그대로 유지된다. 회전 직후 짧은 시간 동안 로그가 두 곳에 잠깐 쓰일 수 있다는 단점은 있지만, forever 환경에서는 이게 거의 유일한 선택지다. PM2였으면 `pm2-logrotate` 모듈로 SIGUSR2 기반 회전이 되는데, forever에는 그런 메커니즘이 없다.

## 메모리 임계 재시작

Node 앱은 GC가 잘 돌아가도 결국 누수가 쌓이는 일이 잦다. 특히 keep-alive 연결, 외부 API 클라이언트의 내부 캐시, 이벤트 리스너 누락이 흔한 원인이다. 메모리가 일정 수준을 넘으면 차라리 재시작하는 쪽이 안전하다.

forever에는 PM2의 `max_memory_restart` 같은 내장 옵션이 없다. 직접 감시 로직을 붙여야 한다.

```javascript
const MAX_RSS_MB = 1024;
const CHECK_INTERVAL_MS = 60_000;

setInterval(() => {
  const rssMb = process.memoryUsage().rss / 1024 / 1024;
  if (rssMb > MAX_RSS_MB) {
    console.warn(`rss=${rssMb.toFixed(0)}MB exceeded, exiting for restart`);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(1), 10_000).unref();
  }
}, CHECK_INTERVAL_MS);
```

핵심은 `server.close()`로 진행 중인 요청을 마무리하고 `process.exit(0)`으로 끊는 것이다. forever는 정상 종료(exit code 0)도 재시작 대상으로 본다. 다만 worker 큐에 무거운 작업이 걸려 있으면 close가 매달릴 수 있어 10초 타임아웃을 강제 종료로 둔다.

`--max-old-space-size`는 GC가 더 자주 돌도록 V8 힙 상한을 정하는 옵션이지, forever가 알아서 재시작해주는 옵션이 아니다. 둘을 헷갈리는 사람이 많다.

```bash
forever start --killSignal SIGTERM \
  -c "node --max-old-space-size=1024" server.js
```

`--killSignal SIGTERM`도 중요하다. 기본값이 SIGKILL이라 graceful shutdown 코드를 짜둬도 동작하지 않는다.

## 환경별 프로파일링

개발에서는 watch 옵션을 켜고, 운영에서는 절대 끄는 게 정석이다.

```bash
# dev
forever start --watch --watchDirectory ./src --watchIgnore "*.log" server.js

# prod
forever start --uid api --append \
  --minUptime 5000 --spinSleepTime 2000 --max 10 \
  -l /var/log/api/forever.log -o /var/log/api/out.log -e /var/log/api/err.log \
  server.js
```

watch가 켜진 상태로 운영에 올라간 사례를 한두 번 본 게 아니다. 빌드 산출물이나 로그 파일 변경에 반응해서 무한히 재시작한다. 옵션을 환경별로 분리하고, 배포 스크립트가 forever 인자를 명시적으로 만들도록 해야 한다.

NODE_ENV는 forever 옵션이 아니라 환경변수로 들어가야 한다. `--env production` 같은 플래그가 forever에는 없다. 있어도 무시된다.

```bash
NODE_ENV=production forever start --uid api server.js
```

## 트러블슈팅 사례

### list에는 보이는데 실제로는 죽어 있는 경우

`forever list`가 STOPPED를 보여주지 않고 RUNNING으로 표시되는데, ps로 보면 PID가 없다. forever의 상태 파일(`~/.forever/sock` 또는 `/tmp/forever`)이 깨졌을 때다. `forever stopall` 후 `~/.forever`를 비우고 다시 띄워야 한다. 같은 호스트에서 여러 사용자가 forever를 돌리면 sock 충돌이 일어나기도 한다.

### child_process.spawn 사용 시 좀비 누적

앱 안에서 `child_process.spawn`으로 외부 바이너리를 호출하는데, 부모가 재시작될 때 자식이 정리되지 않아 좀비가 누적되는 경우가 있다. forever.json에 `"killTree": true`를 켜야 한다. 기본값으로 두면 forever는 직속 자식만 죽인다.

### 로그가 갑자기 끊기는 경우

logrotate가 copytruncate 없이 동작하거나, 누군가 수동으로 mv 후 새 파일을 만든 경우다. forever는 mv된 파일에 계속 쓰다가, 그 파일이 삭제되면 그 이후 로그를 어디에도 남기지 않는다. 재시작하기 전까지는 stdout이 사라진 상태로 운영된다. 이 상황은 디스크가 안 늘어나서 모니터링에서도 잡히지 않는다. 회전 정책을 처음에 잘 잡아야 한다.

### 로컬에서는 잘 도는데 서버에서 즉시 종료

거의 항상 NODE_ENV, PORT, 그리고 uid/euid 권한 문제다. forever를 root로 띄우고 앱이 1024 미만 포트를 listen하면 잘 도는데, 일반 사용자로 바꾸는 순간 EACCES가 난다. authbind나 setcap이 필요하다. systemd라면 `AmbientCapabilities=CAP_NET_BIND_SERVICE` 한 줄로 끝나는 일이다. 이런 자잘한 차이가 쌓이면서 결국 systemd로 옮기게 된다.

## systemd로 옮기는 최소 예시

forever를 걷어내고 systemd로 옮기는 게 운영 측면에서 가장 깔끔하다. 단순한 유닛 파일 하나면 forever가 하던 일의 90%가 끝난다.

```ini
# /etc/systemd/system/api.service
[Unit]
Description=API server
After=network.target

[Service]
Type=simple
User=app
WorkingDirectory=/srv/api
EnvironmentFile=/etc/api.env
ExecStart=/usr/bin/node --max-old-space-size=1024 server.js
Restart=on-failure
RestartSec=2
StartLimitIntervalSec=60
StartLimitBurst=5
MemoryMax=1500M
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

`StartLimitIntervalSec`/`StartLimitBurst`가 forever의 `minUptime`/`max` 역할을 한다. `MemoryMax`는 cgroup 한계라 단순한 임계 재시작과는 다르지만, OOM kill로 자연스럽게 재시작이 된다. 로그는 journald가 자동으로 회전한다. forever에서 구현하려면 코드와 설정을 한참 짜야 하는 것들이 systemd 유닛 십수 줄로 정리된다.

## 정리

forever는 2010년대 표준이었지만 지금은 그 자리에 있을 이유가 사라졌다. 새 프로젝트면 systemd, 컨테이너면 PID 1 패턴, 굳이 Node 생태계 도구가 필요하면 PM2를 고른다. 기존 시스템에 forever가 박혀 있다면 minUptime/spinSleepTime/max 세 옵션으로 무한 루프부터 막고, logrotate copytruncate로 디스크부터 지키고, 메모리 임계 재시작은 앱 코드에 직접 심어야 한다. 그러고 나면 다음 분기에 옮겨갈 계획을 세우는 편이 운영 부담을 줄인다.
