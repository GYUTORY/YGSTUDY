---
title: Linux 보안 하드닝
tags: [linux, security, hardening, firewall, ssh, audit, selinux, fail2ban, ssh-ca, 2fa, port-knocking]
updated: 2026-04-10
---

# Linux 보안 하드닝

## 개요

서버 보안 하드닝(Hardening)은 공격 표면을 줄이고 시스템을 강화하는 과정이다. 기본 설치 상태의 Linux는 보안에 취약하므로, **프로덕션 배포 전 반드시 하드닝**을 수행해야 한다.

### 보안 하드닝 우선순위

```
[필수]  SSH 보안 → 방화벽 → 업데이트 자동화 → 불필요한 서비스 제거
[권장]  Fail2Ban → 감사 로그 → 파일 무결성 → SELinux/AppArmor
[선택]  포트 노킹 → 2FA → AIDE/Tripwire
```

## 핵심

### 1. SSH 보안 강화

#### 1-1. sshd_config 기본 설정

```bash
# /etc/ssh/sshd_config 수정

# 비밀번호 인증 비활성화 (키 인증만 허용)
PasswordAuthentication no
ChallengeResponseAuthentication no

# Root 직접 로그인 차단
PermitRootLogin no

# 기본 포트 변경 (스캔봇 회피)
Port 2222

# 접속 허용 사용자 제한
AllowUsers deploy admin

# 빈 비밀번호 차단
PermitEmptyPasswords no

# 인증 시도 횟수 제한
MaxAuthTries 3

# 로그인 시간 제한
LoginGraceTime 30

# X11 포워딩 비활성화 (불필요 시)
X11Forwarding no

# 프로토콜 2만 사용 (1은 취약)
Protocol 2
```

```bash
# 설정 적용
sudo systemctl restart sshd

# 설정 테스트 (새 터미널에서 접속 확인 후 기존 세션 종료)
ssh -p 2222 deploy@server
```

#### 1-2. SSH CA 인증서 기반 인증

일반적인 공개키 인증은 서버의 `authorized_keys`에 각 사용자의 공개키를 등록해야 한다. 서버가 수십 대로 늘어나면 키 배포가 고통이다. SSH CA는 **인증 기관(CA)이 서명한 인증서**를 사용하여 이 문제를 해결한다.

```
┌──────────────────────────────────────────────────────┐
│                    SSH CA 인증 흐름                    │
│                                                      │
│  [CA 서버]                                            │
│    │  ca_key (비밀키)                                  │
│    │  ca_key.pub (공개키)                              │
│    │                                                  │
│    ├──서명──→ [사용자 인증서]                            │
│    │          user_key-cert.pub                       │
│    │          (유효기간, 허용 principal 포함)             │
│    │                                                  │
│    └──배포──→ [서버]                                    │
│               TrustedUserCAKeys /etc/ssh/ca_key.pub   │
│               (CA 공개키만 등록하면 끝)                   │
│                                                      │
│  접속 시:                                              │
│  사용자 ──인증서 제시──→ 서버                             │
│  서버: CA 공개키로 인증서 서명 검증                        │
│        → 유효기간 확인 → principal 확인 → 접속 허용       │
└──────────────────────────────────────────────────────┘
```

**CA 키 생성 및 사용자 인증서 발급**

```bash
# 1. CA 키 생성 (CA 서버에서 1회 수행)
ssh-keygen -t ed25519 -f /etc/ssh/ca_key -C "SSH CA Key"

# 2. 사용자 공개키에 서명하여 인증서 발급
#    -s: CA 비밀키
#    -I: 인증서 식별자 (로그에 남는다)
#    -n: 허용 principal (서버에서 이 사용자로만 접속 가능)
#    -V: 유효기간 (+52w = 52주)
ssh-keygen -s /etc/ssh/ca_key \
  -I "deploy-user-2026" \
  -n deploy \
  -V +52w \
  /home/user/.ssh/id_ed25519.pub

# 결과: /home/user/.ssh/id_ed25519-cert.pub 파일 생성
```

**서버 설정**

```bash
# CA 공개키를 서버에 배포
scp /etc/ssh/ca_key.pub target-server:/etc/ssh/ca_key.pub

# /etc/ssh/sshd_config에 추가
TrustedUserCAKeys /etc/ssh/ca_key.pub

# authorized_keys 없이도 CA가 서명한 인증서로 접속 가능
sudo systemctl restart sshd
```

**인증서 정보 확인**

```bash
# 발급한 인증서 내용 확인
ssh-keygen -L -f /home/user/.ssh/id_ed25519-cert.pub

# 출력 예시:
# Type: ssh-ed25519-cert-v01@openssh.com user certificate
# Public key: ED25519-CERT SHA256:xxxx
# Signing CA: ED25519 SHA256:yyyy
# Key ID: "deploy-user-2026"
# Serial: 0
# Valid: from 2026-04-10 to 2027-04-09
# Principals:
#         deploy
# Critical Options: (none)
# Extensions:
#         permit-pty
```

실무에서 주의할 점:

- CA 비밀키가 유출되면 모든 서버가 뚫린다. CA 키는 오프라인 장비에 보관하거나, HashiCorp Vault 같은 시크릿 관리 도구에서 관리한다.
- 인증서 유효기간을 짧게 설정하면 보안은 강화되지만, 인증서 재발급 자동화가 필요하다. 팀 규모에 따라 적절한 유효기간을 정해야 한다.
- `AuthorizedPrincipalsFile`을 설정하면 특정 서버에서 허용하는 principal을 제한할 수 있다. 운영 서버와 개발 서버를 분리할 때 유용하다.

```bash
# /etc/ssh/sshd_config
AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u

# /etc/ssh/auth_principals/deploy 파일 내용
# deploy principal만 허용
deploy
```

#### 1-3. 2FA 설정 (Google Authenticator + SSH PAM)

SSH에 TOTP(Time-based One-Time Password) 기반 2FA를 추가하면, 키가 유출되더라도 OTP 없이는 접속할 수 없다.

```
┌───────────────────────────────────────────────┐
│              SSH 2FA 인증 흐름                  │
│                                               │
│  사용자                          서버           │
│    │                              │            │
│    │──(1) SSH 키 인증──────────→  │            │
│    │                    sshd가 키 검증          │
│    │                              │            │
│    │←─(2) OTP 요청────────────── │            │
│    │              PAM이 TOTP 요청              │
│    │                              │            │
│    │──(3) 6자리 코드 입력────────→│            │
│    │            Google Authenticator 검증      │
│    │                              │            │
│    │←─(4) 접속 허용──────────────│            │
└───────────────────────────────────────────────┘
```

**설치 및 설정**

```bash
# 1. Google Authenticator PAM 모듈 설치
sudo apt install libpam-google-authenticator    # Ubuntu/Debian
sudo dnf install google-authenticator           # RHEL/CentOS

# 2. 각 사용자가 자기 계정에서 초기화 실행
google-authenticator

# 대화형 설정에서 아래와 같이 응답한다:
# - Do you want authentication tokens to be time-based? → y
# - QR 코드 출력 → Google Authenticator 앱으로 스캔
# - Your new secret key: XXXXXXXXXXXXXXXXXXXX
# - Do you want me to update your ~/.google_authenticator file? → y
# - Do you want to disallow multiple uses of the same token? → y
# - Do you want to increase the time skew window? → n
# - Do you want to enable rate-limiting? → y
```

**PAM 설정**

```bash
# /etc/pam.d/sshd 수정
# 파일 맨 아래에 추가
auth required pam_google_authenticator.so nullok

# nullok: 아직 google-authenticator를 실행하지 않은 사용자도
#         접속 가능. 전체 적용 완료 후 nullok를 제거한다.
```

**sshd_config 설정**

```bash
# /etc/ssh/sshd_config
ChallengeResponseAuthentication yes
AuthenticationMethods publickey,keyboard-interactive

# 키 인증 + OTP를 모두 통과해야 접속 가능
# 쉼표(,)는 AND 조건, 공백은 OR 조건

# 설정 적용
sudo systemctl restart sshd
```

주의할 점:

- `nullok` 옵션을 제거하기 전에 **모든 사용자가 google-authenticator를 실행했는지 확인**해야 한다. 안 그러면 2FA 설정 안 한 사용자가 잠긴다.
- 비상 코드(emergency scratch codes)를 반드시 안전한 곳에 보관한다. 폰을 분실하면 이 코드로만 접속할 수 있다.
- 서버 시간이 NTP와 동기화되어 있어야 한다. TOTP는 시간 기반이라 서버 시간이 틀리면 코드 검증이 실패한다.

```bash
# NTP 동기화 확인
timedatectl status
# System clock synchronized: yes 확인

# NTP 설정이 안 되어 있다면
sudo timedatectl set-ntp true
```

#### 1-4. 포트 노킹 (Port Knocking)

SSH 포트를 평소에는 닫아두고, 특정 포트에 순서대로 접속 시도를 하면 SSH 포트를 열어주는 방식이다. 포트 스캔에서 SSH 포트가 아예 보이지 않으므로 공격 대상에서 빠진다.

```
┌──────────────────────────────────────────────────┐
│              포트 노킹 동작 방식                    │
│                                                  │
│  초기 상태: SSH 포트(2222) 닫힘                     │
│                                                  │
│  사용자 → 7000번 포트 노크 (SYN)                    │
│         → 8000번 포트 노크 (SYN)                   │
│         → 9000번 포트 노크 (SYN)                   │
│                                                  │
│  knockd: 순서 일치 확인                             │
│         → iptables로 SSH 포트 열기 (30초간)         │
│                                                  │
│  사용자 → SSH 2222번 접속                           │
│         → 30초 후 SSH 포트 다시 닫힘                 │
└──────────────────────────────────────────────────┘
```

**knockd 설치 및 설정**

```bash
# 설치
sudo apt install knockd    # Ubuntu/Debian
sudo dnf install knock      # RHEL (EPEL 필요)

# /etc/knockd.conf 설정
[options]
    UseSyslog
    Interface = eth0

[openSSH]
    sequence    = 7000,8000,9000
    seq_timeout = 5
    command     = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 2222 -j ACCEPT
    tcpflags    = syn

[closeSSH]
    sequence    = 9000,8000,7000
    seq_timeout = 5
    command     = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 2222 -j ACCEPT
    tcpflags    = syn
```

```bash
# knockd 활성화
# /etc/default/knockd (Ubuntu)
START_KNOCKD=1
KNOCKD_OPTS="-i eth0"

sudo systemctl enable --now knockd
```

**클라이언트에서 노킹**

```bash
# knock 명령어 사용
knock server-ip 7000 8000 9000 && ssh -p 2222 deploy@server-ip

# knock이 없는 환경에서는 nmap으로 대체
for port in 7000 8000 9000; do
    nmap -Pn --max-retries 0 -p $port server-ip
done
ssh -p 2222 deploy@server-ip

# 접속 종료 후 포트 닫기
knock server-ip 9000 8000 7000
```

실무에서의 포트 노킹:

- **자동 닫힘 설정을 반드시 추가한다.** 접속 후 수동으로 닫는 건 잊기 쉽다. knockd.conf에 타이머를 넣거나 iptables의 `recent` 모듈을 사용한다.
- 포트 노킹만으로 보안을 보장할 수는 없다. 네트워크를 모니터링하는 공격자가 노킹 순서를 알아낼 수 있다. 반드시 SSH 키 인증과 함께 사용한다.
- 자동화 도구(Ansible, CI/CD)에서 포트 노킹을 거치는 건 번거롭다. 관리 서버에서는 방화벽 화이트리스트로 대체하는 경우가 많다.

```bash
# 자동 닫힘 설정 예시 (knockd.conf)
[openSSH]
    sequence    = 7000,8000,9000
    seq_timeout = 5
    command     = /sbin/iptables -I INPUT -s %IP% -p tcp --dport 2222 -j ACCEPT
    tcpflags    = syn
    cmd_timeout = 30
    stop_command = /sbin/iptables -D INPUT -s %IP% -p tcp --dport 2222 -j ACCEPT
```

### 2. SSH 접속 감사 로그 분석

SSH 관련 로그를 주기적으로 확인하는 것은 침입 시도를 조기에 발견하는 기본 방법이다.

#### 로그 위치

```bash
# 배포판별 SSH 로그 위치
# Ubuntu/Debian: /var/log/auth.log
# RHEL/CentOS:   /var/log/secure
# systemd 기반:  journalctl -u sshd
```

#### auth.log / secure 파일 분석

```bash
# 로그인 실패 내역 확인
grep "Failed password" /var/log/auth.log | tail -20

# 출력 예시:
# Apr 10 14:23:11 web01 sshd[12345]: Failed password for invalid user admin from 203.0.113.50 port 45678 ssh2

# 존재하지 않는 사용자로 시도한 접속
grep "Invalid user" /var/log/auth.log | awk '{print $8}' | sort | uniq -c | sort -rn | head

# 출력 예시:
#  142 admin
#   87 root
#   43 test
#   21 oracle

# 특정 IP에서 몇 번 시도했는지
grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head

# 성공한 로그인 확인
grep "Accepted" /var/log/auth.log | tail -20
```

#### journalctl 기반 분석

systemd 환경에서는 journalctl이 더 편하다.

```bash
# SSH 서비스 로그 보기
journalctl -u sshd --since "1 hour ago"

# 오늘 로그인 실패만
journalctl -u sshd --since today | grep "Failed"

# 실시간 모니터링
journalctl -u sshd -f

# 특정 기간의 인증 로그
journalctl -u sshd --since "2026-04-01" --until "2026-04-10"

# JSON 형식으로 출력 (스크립트 처리용)
journalctl -u sshd -o json --since today | jq '{time: .__REALTIME_TIMESTAMP, msg: .MESSAGE}'
```

#### 로그 분석 스크립트 예시

```bash
#!/bin/bash
# ssh_audit.sh - SSH 접속 로그 일일 리포트

LOG="/var/log/auth.log"
DATE=$(date +"%b %e")

echo "=== SSH 접속 리포트 (${DATE}) ==="
echo ""

echo "--- 로그인 실패 TOP 10 IP ---"
grep "$DATE" "$LOG" | grep "Failed password" | \
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10

echo ""
echo "--- 로그인 성공 ---"
grep "$DATE" "$LOG" | grep "Accepted" | \
    awk '{print $1,$2,$3, "user:",$9, "from:",$11}'

echo ""
echo "--- 차단된 IP (Fail2Ban) ---"
grep "$DATE" "$LOG" | grep "Ban " | awk '{print $NF}' | sort -u
```

```bash
# cron으로 매일 실행
# crontab -e
0 9 * * * /opt/scripts/ssh_audit.sh | mail -s "SSH Daily Report" admin@example.com
```

### 3. 방화벽 설정

#### UFW (Ubuntu/Debian)

```bash
# 기본 정책: 들어오는 트래픽 차단, 나가는 트래픽 허용
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 필요한 포트만 허용
sudo ufw allow 2222/tcp        # SSH (변경한 포트)
sudo ufw allow 80/tcp          # HTTP
sudo ufw allow 443/tcp         # HTTPS

# 특정 IP만 허용
sudo ufw allow from 10.0.0.0/24 to any port 5432  # 내부망에서만 PostgreSQL

# 활성화
sudo ufw enable
sudo ufw status verbose
```

#### firewalld (RHEL/CentOS)

```bash
# 기본 존 확인
sudo firewall-cmd --get-default-zone

# 서비스 허용
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# 포트 허용
sudo firewall-cmd --permanent --add-port=2222/tcp

# 특정 IP 허용 (리치 룰)
sudo firewall-cmd --permanent --add-rich-rule='
  rule family="ipv4"
  source address="10.0.0.0/24"
  port protocol="tcp" port="5432"
  accept'

# 적용
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

### 4. 자동 보안 업데이트

```bash
# Ubuntu: unattended-upgrades
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 설정: /etc/apt/apt.conf.d/50unattended-upgrades
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "admin@example.com";

# RHEL/CentOS: dnf-automatic
sudo dnf install dnf-automatic
sudo systemctl enable --now dnf-automatic-install.timer
```

### 5. Fail2Ban (브루트포스 차단)

반복적인 로그인 실패를 감지하여 **IP를 자동 차단**한다.

```bash
# 설치
sudo apt install fail2ban    # Ubuntu
sudo dnf install fail2ban    # RHEL

# 설정: /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600          # 차단 시간 (1시간)
findtime = 600          # 감시 기간 (10분)
maxretry = 3            # 최대 실패 횟수
banaction = ufw          # UFW 연동

[sshd]
enabled = true
port = 2222             # SSH 포트
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
```

```bash
# 시작 및 확인
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd

# 차단된 IP 확인
sudo fail2ban-client status sshd

# IP 차단 해제
sudo fail2ban-client set sshd unbanip 192.168.1.100
```

### 6. 불필요한 서비스 제거

```bash
# 실행 중인 서비스 확인
systemctl list-units --type=service --state=running

# 불필요한 서비스 비활성화
sudo systemctl disable --now cups        # 프린터 (서버에 불필요)
sudo systemctl disable --now avahi-daemon # mDNS (서버에 불필요)
sudo systemctl disable --now bluetooth   # 블루투스

# 열린 포트 확인
ss -tulnp

# 사용하지 않는 패키지 제거
sudo apt autoremove    # Ubuntu
sudo dnf autoremove    # RHEL
```

### 7. 사용자 보안

```bash
# 비밀번호 정책 설정 (/etc/login.defs)
PASS_MAX_DAYS   90      # 비밀번호 최대 사용 기간
PASS_MIN_DAYS   1       # 비밀번호 최소 사용 기간
PASS_MIN_LEN    12      # 최소 비밀번호 길이
PASS_WARN_AGE   7       # 만료 경고 일수

# sudo 권한 관리
sudo visudo
# 특정 명령만 허용
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart myapp

# 로그인 불필요 계정 셸 제거
sudo usermod -s /usr/sbin/nologin nginx
sudo usermod -s /usr/sbin/nologin mysql

# 비활성 계정 잠금
sudo usermod -L inactive_user
```

### 8. 파일 시스템 보안

```bash
# 중요 파일 권한 확인
ls -la /etc/passwd      # -rw-r--r-- (644)
ls -la /etc/shadow      # -rw------- (600)
ls -la /etc/ssh/        # 키 파일은 600

# SUID/SGID 파일 찾기 (권한 상승 가능한 파일)
find / -perm /4000 -type f 2>/dev/null    # SUID
find / -perm /2000 -type f 2>/dev/null    # SGID

# 불필요한 SUID 제거
sudo chmod u-s /usr/bin/unnecessary_binary

# /tmp 보안 (noexec, nosuid)
# /etc/fstab에 추가
tmpfs /tmp tmpfs defaults,noexec,nosuid,nodev 0 0
```

### 9. 감사 로그 (Audit)

```bash
# auditd 설치 및 시작
sudo apt install auditd    # Ubuntu
sudo systemctl enable --now auditd

# 감사 규칙 추가 (/etc/audit/rules.d/audit.rules)
# 파일 변경 감시
-w /etc/passwd -p wa -k user_changes
-w /etc/shadow -p wa -k password_changes
-w /etc/sudoers -p wa -k sudo_changes
-w /etc/ssh/sshd_config -p wa -k ssh_changes

# 명령 실행 감사
-a always,exit -F arch=b64 -S execve -k command_execution

# 로그 검색
ausearch -k user_changes           # 키워드로 검색
ausearch -ts today -i              # 오늘 로그
aureport --auth                    # 인증 보고서
aureport --login --summary         # 로그인 요약
```

### 10. 커널 보안 파라미터

```bash
# /etc/sysctl.d/99-security.conf

# IP 스푸핑 방지
net.ipv4.conf.all.rp_filter = 1

# ICMP 리다이렉트 비활성화
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0

# SYN Flood 방어
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# IP 포워딩 비활성화 (라우터가 아닌 경우)
net.ipv4.ip_forward = 0

# 코어 덤프 비활성화
fs.suid_dumpable = 0

# 적용
sudo sysctl -p /etc/sysctl.d/99-security.conf
```

## 운영 팁

### SSH 보안 조합 비교

서버 환경에 따라 적절한 조합이 다르다. 아래는 일반적인 상황별 권장 구성이다.

| 환경 | 기본 설정 | CA 인증서 | 2FA | 포트 노킹 | 비고 |
|------|----------|----------|-----|----------|------|
| 개인 프로젝트 서버 | O | - | - | - | sshd_config + Fail2Ban이면 충분 |
| 소규모 팀 (5명 이하) | O | - | O | - | 2FA 추가로 키 유출 대비 |
| 중규모 팀 (5~50명) | O | O | O | - | CA로 키 배포 자동화 |
| 보안 민감 서버 | O | O | O | O | 금융, 의료 등 규제 대상 |

### 하드닝 적용 후 확인 사항

하드닝 설정을 적용한 뒤에는 반드시 아래 항목을 확인한다. 설정 실수로 접속이 불가능해지면 물리 콘솔이나 클라우드 콘솔을 통해서만 복구할 수 있다.

- 새 터미널에서 SSH 접속 테스트 (기존 세션 유지한 상태에서)
- 비밀번호 인증이 실제로 차단되는지 확인
- Fail2Ban이 정상 동작하는지 로그 확인
- 방화벽 규칙이 의도대로 적용되었는지 `ss -tulnp`로 확인
- 2FA 설정한 경우 비상 코드 보관 여부 확인

## 참고

- [CIS Benchmarks for Linux](https://www.cisecurity.org/benchmark/distribution_independent_linux)
- [SSH & 원격 접속](SSH.md) — SSH 상세 설명
- [네트워크 관리](../네트워크/네트워크_관리.md) — 네트워크 기본
- [시스템 모니터링](../시스템_관리/시스템_모니터링.md) — 모니터링 도구
