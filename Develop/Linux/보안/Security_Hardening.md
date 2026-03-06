---
title: Linux 보안 하드닝 가이드
tags: [linux, security, hardening, firewall, ssh, audit, selinux, fail2ban]
updated: 2026-03-01
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

### 2. 방화벽 설정

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

### 3. 자동 보안 업데이트

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

### 4. Fail2Ban (브루트포스 차단)

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

### 5. 불필요한 서비스 제거

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

### 6. 사용자 보안

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

### 7. 파일 시스템 보안

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

### 8. 감사 로그 (Audit)

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

### 9. 커널 보안 파라미터

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

### 보안 하드닝 체크리스트

| 항목 | 설명 | 필수 |
|------|------|------|
| SSH 키 인증만 허용 | 비밀번호 인증 비활성화 | ✅ |
| SSH Root 로그인 차단 | `PermitRootLogin no` | ✅ |
| 방화벽 활성화 | 필요한 포트만 허용 | ✅ |
| 보안 업데이트 자동화 | unattended-upgrades / dnf-automatic | ✅ |
| Fail2Ban 설치 | 브루트포스 자동 차단 | ✅ |
| 불필요한 서비스 제거 | 공격 표면 최소화 | ✅ |
| 감사 로그 활성화 | auditd 설정 | ⭐ |
| 커널 보안 파라미터 | sysctl 튜닝 | ⭐ |
| SUID/SGID 점검 | 불필요한 권한 상승 제거 | ⭐ |

## 참고

- [CIS Benchmarks for Linux](https://www.cisecurity.org/benchmark/distribution_independent_linux)
- [SSH & 원격 접속](SSH.md) — SSH 상세 가이드
- [네트워크 관리](../네트워크/네트워크_관리.md) — 네트워크 기본
- [시스템 모니터링](../시스템_관리/시스템_모니터링.md) — 모니터링 도구
