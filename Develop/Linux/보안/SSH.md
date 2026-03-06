---
title: SSH & 원격 접속 가이드
tags: [linux, ssh, remote-access, key-authentication, port-forwarding, scp, rsync, tunneling]
updated: 2026-03-01
---

# SSH & 원격 접속

## 개요

SSH(Secure Shell)는 네트워크를 통해 **원격 서버에 안전하게 접속**하는 프로토콜이다. 암호화된 통신으로 비밀번호, 명령어, 파일 전송 등 모든 데이터를 보호한다. 포트 22번을 사용한다.

```
로컬 머신                           원격 서버
┌──────────┐     암호화된 터널       ┌──────────┐
│ SSH 클라  │ ◀══════════════════▶ │ SSH 서버  │
│ 이언트    │     (포트 22)          │ (sshd)   │
└──────────┘                       └──────────┘
```

## 핵심

### 1. SSH 키 인증

비밀번호 대신 **공개키/개인키 쌍**으로 인증한다. 더 안전하고 자동화에 필수.

```bash
# 키 생성 (ED25519 권장, RSA보다 안전하고 빠름)
ssh-keygen -t ed25519 -C "user@example.com"

# RSA를 써야 하는 경우 (레거시 서버)
ssh-keygen -t rsa -b 4096 -C "user@example.com"

# 결과:
#   ~/.ssh/id_ed25519       ← 개인키 (절대 공유 금지!)
#   ~/.ssh/id_ed25519.pub   ← 공개키 (서버에 등록)
```

```bash
# 공개키를 서버에 등록
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server

# 수동으로 등록 (ssh-copy-id 사용 불가 시)
cat ~/.ssh/id_ed25519.pub | ssh user@server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# 키 인증으로 접속 (비밀번호 불필요)
ssh user@server
```

#### 인증 과정

```
1. 클라이언트 → 서버: "공개키로 인증하겠습니다"
2. 서버: authorized_keys에 공개키 있는지 확인
3. 서버 → 클라이언트: 랜덤 챌린지 전송
4. 클라이언트: 개인키로 챌린지 서명
5. 클라이언트 → 서버: 서명 전송
6. 서버: 공개키로 서명 검증 → 인증 완료
```

### 2. SSH 접속

```bash
# 기본 접속
ssh user@192.168.1.100

# 포트 변경
ssh -p 2222 user@server

# 특정 키 파일 사용
ssh -i ~/.ssh/myserver_key user@server

# 명령어 실행 후 즉시 종료
ssh user@server "df -h && free -m"

# 여러 서버에 명령 실행
for server in web1 web2 web3; do
    echo "=== $server ==="
    ssh user@$server "uptime"
done
```

### 3. SSH Config (~/.ssh/config)

서버별 접속 설정을 파일로 관리한다. 긴 명령어를 짧은 별칭으로 대체.

```
# ~/.ssh/config

# 개발 서버
Host dev
    HostName 192.168.1.100
    User deploy
    Port 2222
    IdentityFile ~/.ssh/dev_key

# 프로덕션 서버
Host prod
    HostName 10.0.1.50
    User admin
    IdentityFile ~/.ssh/prod_key
    ProxyJump bastion          # 배스천 서버 경유

# 배스천 (점프) 서버
Host bastion
    HostName bastion.example.com
    User ec2-user
    IdentityFile ~/.ssh/bastion_key

# AWS EC2 공통 설정
Host aws-*
    User ec2-user
    IdentityFile ~/.ssh/aws_key
    StrictHostKeyChecking no    # 개발 환경에서만

# 모든 호스트 공통 설정
Host *
    ServerAliveInterval 60      # 60초마다 keepalive
    ServerAliveCountMax 3       # 3회 실패 시 연결 종료
    AddKeysToAgent yes          # ssh-agent에 키 자동 추가
```

```bash
# 설정 후 간단하게 접속
ssh dev          # ssh -p 2222 -i ~/.ssh/dev_key deploy@192.168.1.100 와 동일
ssh prod         # bastion 경유하여 자동 접속
```

### 4. 파일 전송

#### SCP (Secure Copy)

```bash
# 로컬 → 서버
scp file.txt user@server:/home/user/

# 서버 → 로컬
scp user@server:/var/log/app.log ./

# 디렉토리 전송 (-r)
scp -r ./dist/ user@server:/var/www/html/

# 서버 → 서버
scp user@server1:/data/backup.tar user@server2:/backup/
```

#### Rsync (효율적 동기화)

변경된 파일만 전송하므로 SCP보다 **빠르고 효율적**이다.

```bash
# 기본 동기화
rsync -avz ./dist/ user@server:/var/www/html/

# 옵션 설명
# -a: 아카이브 (권한, 소유자, 시간 보존)
# -v: 상세 출력
# -z: 압축 전송
# --delete: 원본에 없는 파일은 대상에서 삭제
# --exclude: 특정 패턴 제외

# 배포 예시 (삭제 포함, node_modules 제외)
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude '.git' \
  ./dist/ user@server:/var/www/html/

# 드라이런 (실제 전송 없이 확인)
rsync -avzn --delete ./dist/ user@server:/var/www/html/
```

| 도구 | 전송 방식 | 속도 | 적합한 경우 |
|------|---------|------|-----------|
| **scp** | 전체 복사 | 느림 | 단일 파일, 간단한 전송 |
| **rsync** | 차분 전송 | 빠름 | 반복 동기화, 대용량 |

### 5. 포트 포워딩 (SSH 터널링)

SSH 연결을 통해 **다른 포트의 트래픽을 안전하게 전달**한다.

#### 로컬 포트 포워딩 (Local → Remote)

```bash
# 로컬 8080 → 서버의 localhost:3000으로 포워딩
ssh -L 8080:localhost:3000 user@server

# 사용: 브라우저에서 http://localhost:8080 접속
# → 서버의 3000번 포트로 전달됨
```

```
로컬 머신                  SSH 터널            원격 서버
┌──────────┐          ┌──────────┐        ┌──────────┐
│ 브라우저  │──8080──▶│  SSH     │──────▶│ :3000    │
│          │          │  터널    │        │ (앱 서버) │
└──────────┘          └──────────┘        └──────────┘
```

#### 원격 포트 포워딩 (Remote → Local)

```bash
# 서버의 9090 포트 → 로컬의 3000으로 포워딩
ssh -R 9090:localhost:3000 user@server

# 용도: 로컬 개발 서버를 외부에서 접근
```

#### 실전 예시

```bash
# 1. 서버 DB에 로컬에서 접속 (DB 포트가 외부에 닫혀 있을 때)
ssh -L 5433:localhost:5432 user@server
# → psql -h localhost -p 5433 testdb

# 2. 프라이빗 서브넷 서버에 접속 (배스천 경유)
ssh -L 3307:private-db.internal:3306 user@bastion
# → mysql -h 127.0.0.1 -P 3307

# 3. 백그라운드 터널 (-f -N)
ssh -f -N -L 5433:localhost:5432 user@server
# -f: 백그라운드, -N: 명령 실행 안 함 (터널만)
```

### 6. SSH Agent

개인키 비밀번호를 매번 입력하지 않도록 **메모리에 키를 캐시**한다.

```bash
# ssh-agent 시작
eval "$(ssh-agent -s)"

# 키 추가
ssh-add ~/.ssh/id_ed25519

# 등록된 키 확인
ssh-add -l

# Agent Forwarding (서버에서 다른 서버로 키 전달)
ssh -A user@bastion
# bastion에서 다시 ssh user@internal-server 가능 (로컬 키 사용)
```

### 7. 주요 설정 정리

| 설정 | 설명 | 기본값 |
|------|------|--------|
| `Port` | SSH 포트 | 22 |
| `PasswordAuthentication` | 비밀번호 인증 | yes |
| `PubkeyAuthentication` | 키 인증 | yes |
| `PermitRootLogin` | root 로그인 허용 | prohibit-password |
| `MaxAuthTries` | 인증 시도 횟수 | 6 |
| `ClientAliveInterval` | keepalive 간격 | 0 (비활성) |
| `AllowUsers` | 접속 허용 사용자 | 전체 |

## 참고

- [OpenSSH 공식 문서](https://www.openssh.com/manual.html)
- [Linux 보안 하드닝](Security_Hardening.md) — SSH 보안 설정 포함
- [네트워크 관리](../네트워크/네트워크_관리.md) — 네트워크 기본
