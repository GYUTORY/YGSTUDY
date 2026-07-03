---
title: SSH 키 라이프사이클 관리
tags: [ssh, key-management, security, vault, certificate-authority, devops, fido2, yubikey, ssh-agent, cloud, audit]
updated: 2026-04-29
---

# SSH 키 라이프사이클 관리

SSH 키는 생성하고 끝이 아니다. 서버가 10대, 100대로 늘어나면 누가 어떤 키로 어디에 접속하는지 추적하기 어려워진다. 퇴사자의 키가 authorized_keys에 남아있거나, 3년 전에 만든 키가 passphrase 없이 돌아다니는 상황이 실제로 발생한다. 키의 생성부터 폐기까지 전체 흐름을 관리해야 한다.

## 키 생성 정책

키를 만들 때부터 규칙이 있어야 나중에 관리가 된다.

### 알고리즘 선택

```bash
# ED25519 — 현재 권장. 키가 짧고 성능이 좋다
ssh-keygen -t ed25519 -C "deploy@mycompany 2026-04"

# RSA — FIPS 인증 환경이나 레거시 시스템에서 필요할 때
ssh-keygen -t rsa -b 4096 -C "deploy@mycompany 2026-04"

# ECDSA — 일부 하드웨어 보안 모듈(HSM)에서 ED25519를 지원하지 않을 때
ssh-keygen -t ecdsa -b 521 -C "deploy@mycompany 2026-04"
```

코멘트(-C)에 용도와 생성 시점을 넣어두면, 나중에 authorized_keys에서 어떤 키가 누구 것인지 구분할 수 있다. 코멘트 없는 키가 쌓이면 어떤 키를 삭제해도 되는지 판단이 안 된다.

### passphrase 필수화

```bash
# passphrase 없이 만들면 키 파일 유출 = 즉시 접속 가능
ssh-keygen -t ed25519 -C "deploy@mycompany 2026-04"
# 프롬프트에서 passphrase를 반드시 입력한다

# ssh-agent로 passphrase 캐싱 — 매번 입력할 필요 없다
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# macOS에서 키체인 연동
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

CI/CD 환경에서는 passphrase 없는 키를 쓸 수밖에 없는 경우가 있다. 이때는 키 파일 권한을 600으로 설정하고, 해당 키의 접근 범위를 최소한으로 제한해야 한다.

### 키 파일 네이밍

키가 여러 개면 파일명으로 구분한다.

```bash
# 용도별 키 분리
~/.ssh/id_ed25519_github        # GitHub 개인 계정
~/.ssh/id_ed25519_deploy_prod   # 프로덕션 배포
~/.ssh/id_ed25519_deploy_staging # 스테이징 배포
~/.ssh/id_ed25519_bastion       # 배스천 접속

# ~/.ssh/config에서 호스트별 키 지정
Host github.com
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes    # 이 키만 시도

Host prod-*
    IdentityFile ~/.ssh/id_ed25519_deploy_prod
    IdentitiesOnly yes
```

`IdentitiesOnly yes`가 없으면 ssh-agent에 등록된 모든 키를 순서대로 시도한다. 키가 5개 이상이면 MaxAuthTries에 걸려서 인증이 실패하는 경우가 있다.

## 하드웨어 기반 키

소프트웨어 키는 결국 디스크의 파일이다. 디스크 이미지가 유출되거나, 백업이 잘못 노출되면 키도 함께 새어나간다. 하드웨어 보안 모듈에 개인키를 가두면 파일이 유출돼도 사용 불가능하다. 5년차쯤 되면 한 번쯤 "키 파일이 어디로 흘러갔는지 모르겠다"는 상황을 겪는데, 하드웨어 키는 그런 사고의 영향 범위 자체를 좁혀준다.

### FIDO2 보안키 (YubiKey 등)

OpenSSH 8.2부터 sk-ed25519, sk-ecdsa-sha2-nistp256 키 타입이 추가됐다. 개인키는 보안키 내부 보안 칩에 저장되고, 호스트의 키 파일은 그 칩을 가리키는 핸들일 뿐이다.

```bash
# YubiKey가 꽂혀있어야 한다
ssh-keygen -t ed25519-sk -O resident -O verify-required \
    -C "kim@yubikey-2026Q2"

# resident: 키를 YubiKey 내부에 저장 (다른 PC에서 ssh-keygen -K로 복원 가능)
# verify-required: 매 인증 시 PIN 또는 지문 추가 요구
# touch-required: 매 인증 시 물리적 터치 (기본값)
```

생성된 `~/.ssh/id_ed25519_sk`는 보통 키 파일처럼 보이지만 실제 비밀은 YubiKey 안에 있다. 파일이 유출돼도 YubiKey가 없으면 무용지물이다. 키를 다른 PC로 옮기려면 YubiKey를 꽂고 `ssh-keygen -K`로 resident key를 복원한다.

verify-required의 부작용 — Git push, Ansible 작업처럼 짧은 시간에 여러 번 인증이 필요한 경우 매번 PIN을 묻는다. 배포 자동화용 키는 verify-required를 빼고 touch-required만 두는 게 현실적이다. 회사 정책상 PIN이 필요하면 `ssh-add -t 600`처럼 ssh-agent 캐시 시간을 길게 두는 방식으로 우회한다.

### Apple Secure Enclave / Touch ID

Apple Silicon 맥은 Secure Enclave 칩이 내장되어 있어서 별도 하드웨어 없이도 보안 영역에 키를 저장할 수 있다. Secretive 같은 오픈소스 도구가 이걸 SSH 에이전트 형태로 노출한다.

```bash
# Secretive 설치
brew install --cask secretive

# Secretive UI에서 키 생성 → 에이전트 소켓 경로 안내됨
# ~/.zshrc 또는 ~/.bashrc
export SSH_AUTH_SOCK="$HOME/Library/Containers/com.maxgoedjen.Secretive.SecretAgent/Data/socket.ssh"

# 공개키 등록 후 사용 — 인증 때마다 Touch ID 프롬프트
ssh user@server
```

Secretive로 만든 키는 Secure Enclave에 격리되어서 어떤 프로세스도 개인키 자체를 읽을 수 없다. 약점은 키를 다른 컴퓨터로 절대 옮길 수 없다는 점. 노트북이 망가지면 키도 사라진다. 백업이 의미 있는 키는 Secure Enclave가 아니라 일반 파일이나 비밀번호 관리자 vault에 둔다.

### TPM 기반 키 (Linux/Windows)

리눅스 워크스테이션이나 서버에는 TPM 2.0 칩이 들어있는 경우가 많다. ssh-tpm-agent를 쓰면 TPM에 키를 저장하고 사용할 수 있다.

```bash
# Ubuntu에서 설치
sudo apt install ssh-tpm-agent

# TPM에 키 생성
ssh-tpm-keygen -t ecdsa
# 생성: ~/.ssh/id_ecdsa.tpm (TPM 핸들 파일)

# 에이전트 시작
ssh-tpm-agent --listen ~/.ssh/tpm-agent.sock &
export SSH_AUTH_SOCK=~/.ssh/tpm-agent.sock

# 공개키만 일반 파일이다
cat ~/.ssh/id_ecdsa.pub
```

TPM 기반 키는 해당 머신을 떠날 수 없다. 메인보드를 교체하거나 운영체제를 재설치하면 키가 사라진다. 백업이 필요한 사용자 키보다는 일회성 워크스테이션, 짧게 살다가 사라지는 인스턴스에 적합하다.

## ssh-agent 보안

ssh-agent는 메모리에 풀린 개인키를 들고 있는 프로세스다. 하드웨어 키를 써도 결국 ssh-agent 소켓을 거치므로, 소켓 자체가 공격 표면이 된다. 공격자가 ssh-agent 소켓에 접근할 수 있으면, 키 파일이나 passphrase가 없어도 사용자의 모든 SSH 세션을 가로챌 수 있다.

### 소켓 권한과 위치

```bash
# 소켓 위치 확인
echo $SSH_AUTH_SOCK
# /tmp/ssh-XXXXXX/agent.<pid>

# 권한 — 본인만 접근 가능해야 한다
ls -la $SSH_AUTH_SOCK
# srwx------ 1 kim staff 0 ... agent.12345
```

소켓 디렉토리(`/tmp/ssh-XXXXXX`)가 700이 아니거나, 다른 사용자가 들어갈 수 있다면 같은 시스템의 다른 사용자가 ssh-agent를 가로챌 수 있다. 공유 점프 호스트, 빌드 서버처럼 여러 사용자가 같은 머신을 쓰는 환경에서 특히 위험하다.

### 키 타임아웃

ssh-add로 등록한 키는 기본적으로 ssh-agent가 죽을 때까지 메모리에 남는다. 노트북을 잠그지 않고 자리를 비웠을 때 노출 시간이 길어진다.

```bash
# 등록 시 타임아웃 지정
ssh-add -t 3600 ~/.ssh/id_ed25519
# 1시간 뒤 자동 삭제

# 등록된 키 모두 확인
ssh-add -L

# 모든 키 즉시 삭제 (출장 가기 전, 자리 비울 때)
ssh-add -D
```

회사 정책으로 강제하려면 `~/.ssh/config`에 `AddKeysToAgent yes` 대신 명시적 ssh-add를 쓰고, 셸 종료 시 ssh-agent 프로세스를 죽이는 wrapper를 둔다.

### Agent Forwarding의 위험

`ssh -A`로 agent forwarding을 켜면 원격 서버의 ssh-agent 소켓을 통해 로컬 키에 접근할 수 있다. 편하지만 점프 호스트가 침해된 경우 공격자도 같은 경로로 다른 서버에 접속할 수 있다.

```bash
# 위험한 사용
ssh -A user@bastion
# bastion이 뚫리면 공격자가 내 ssh-agent로 다른 서버에 접속

# 대신 ProxyJump 사용 — 인증은 로컬에서 처리
ssh -J bastion user@target
```

`~/.ssh/config`에 ProxyJump를 박아두면 매번 신경 쓸 필요가 없다.

```ssh-config
Host target-*
    ProxyJump bastion
    ForwardAgent no
```

agent forwarding이 꼭 필요한 경우(예: 점프 호스트에서 git push)에는 confirm 옵션을 켠다. `ssh-add -c`로 등록하면 forwarding된 키 사용 시마다 로컬에서 확인 프롬프트가 뜬다.

### 1Password / Bitwarden agent 연동

비밀번호 관리자가 SSH agent를 제공하면 키를 vault에 저장하고 마스터 인증으로 풀 수 있다. 여러 기기 간 동기화가 자연스러운 게 큰 장점이다.

```bash
# 1Password SSH agent
# 1Password 앱 > Developer > Use the SSH agent 활성화

# ~/.zshrc 또는 셸 시작 스크립트
export SSH_AUTH_SOCK="$HOME/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"

# 사용 시 1Password가 잠겨있으면 unlock 프롬프트 (Touch ID 또는 마스터 비밀번호)
ssh user@server
```

```bash
# Bitwarden (CLI 기반)
bw login
bw unlock
# 키 항목을 vault에 저장하고 ssh-add로 등록하는 wrapper 스크립트 작성
```

비밀번호 관리자 agent의 함정 — 앱이 충돌하거나 자동 잠금이 걸려있으면 SSH 인증이 막힌다. 비상 상황에 쓸 수 있는 별도 키(예: passphrase 보호된 일반 키 파일)를 다른 곳에 백업해 둔다.

## 키 배포

서버에 공개키를 등록하는 과정이다. 서버가 적으면 수동으로 하지만, 수십 대 이상이면 자동화가 필요하다.

### 수동 배포

```bash
# ssh-copy-id가 가장 간편하다
ssh-copy-id -i ~/.ssh/id_ed25519_deploy_prod.pub user@server

# authorized_keys에 옵션을 붙여서 제한할 수 있다
# 서버의 ~/.ssh/authorized_keys
command="/usr/bin/rsync --server",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA... deploy@mycompany
```

`command=` 옵션은 해당 키로 접속하면 지정된 명령만 실행되게 한다. 배포용 키가 셸 접속까지 허용할 필요는 없다. rsync만 필요하면 rsync만 허용한다.

### Ansible로 자동 배포

```yaml
# authorized_keys 관리 — Ansible playbook
- name: SSH 키 배포
  hosts: all
  tasks:
    - name: 운영팀 공개키 등록
      ansible.posix.authorized_key:
        user: deploy
        key: "{{ lookup('file', 'keys/' + item + '.pub') }}"
        state: present
      loop:
        - kim
        - lee
        - park

    - name: 퇴사자 키 제거
      ansible.posix.authorized_key:
        user: deploy
        key: "{{ lookup('file', 'keys/removed/' + item + '.pub') }}"
        state: absent
      loop:
        - choi   # 2026-03 퇴사
```

공개키 파일을 Git 저장소에 넣고 Ansible로 배포하면, 누가 어떤 서버에 접근 가능한지 Git 히스토리로 추적할 수 있다. 퇴사자 처리도 PR 하나로 끝난다.

### authorized_keys 관리 스크립트

Ansible 없이 간단하게 관리하는 경우:

```bash
#!/bin/bash
# sync_authorized_keys.sh
# 중앙 저장소에서 authorized_keys를 가져와서 동기화

KEY_REPO="https://git.internal.com/infra/ssh-keys.git"
KEY_DIR="/opt/ssh-keys"
TARGET_USER="deploy"

# 최신 키 가져오기
cd "$KEY_DIR" && git pull --ff-only

# authorized_keys 재구성
cat "$KEY_DIR/team-ops/"*.pub > /tmp/authorized_keys_new
cat "$KEY_DIR/service-accounts/"*.pub >> /tmp/authorized_keys_new

# 원자적 교체
install -m 600 -o "$TARGET_USER" /tmp/authorized_keys_new \
    "/home/$TARGET_USER/.ssh/authorized_keys"

rm /tmp/authorized_keys_new
```

cron으로 주기적으로 실행하거나, Git webhook으로 트리거한다. authorized_keys를 직접 편집하는 것보다 중앙에서 관리하는 방식이 훨씬 안전하다.

## 키 교체 (Rotation)

키를 주기적으로 교체하지 않으면, 오래된 키가 어디에 복사되어 있는지 추적이 불가능해진다.

### 교체 주기

- 개인 키: 1년마다 교체
- 서비스 계정 키: 6개월마다 교체
- 인시던트 발생 시: 즉시 교체

### 무중단 키 교체 절차

기존 키를 바로 삭제하면 접속이 끊긴다. 새 키를 먼저 배포하고, 이전 키를 나중에 제거한다.

```bash
# 1단계: 새 키 생성
ssh-keygen -t ed25519 -C "deploy@mycompany 2026-04-new" \
    -f ~/.ssh/id_ed25519_deploy_prod_new

# 2단계: 새 공개키를 모든 서버에 추가 (기존 키는 유지)
ssh-copy-id -i ~/.ssh/id_ed25519_deploy_prod_new.pub user@server

# 3단계: 새 키로 접속 테스트
ssh -i ~/.ssh/id_ed25519_deploy_prod_new user@server

# 4단계: SSH config에서 키 경로 변경
# ~/.ssh/config
# IdentityFile ~/.ssh/id_ed25519_deploy_prod_new

# 5단계: 모든 서비스가 새 키를 사용하는지 확인 후, 이전 키 제거
# 서버의 authorized_keys에서 이전 공개키 삭제
```

CI/CD 파이프라인에서 사용하는 키를 교체할 때는 5단계가 가장 위험하다. Jenkins, GitHub Actions, ArgoCD 등 여러 시스템에서 같은 키를 쓰고 있을 수 있다. 교체 전에 해당 키를 사용하는 모든 곳을 파악해야 한다.

### 교체 자동화 (Ansible)

```yaml
# rotate_ssh_keys.yml
- name: SSH 키 교체
  hosts: all
  vars:
    new_key: "{{ lookup('file', 'keys/deploy_2026Q2.pub') }}"
    old_key: "{{ lookup('file', 'keys/deploy_2026Q1.pub') }}"
  tasks:
    - name: 새 키 추가
      ansible.posix.authorized_key:
        user: deploy
        key: "{{ new_key }}"
        state: present

    - name: 접속 테스트 대기 (수동 확인 후 진행)
      pause:
        prompt: "새 키로 접속 테스트 완료? (Enter to continue)"

    - name: 이전 키 제거
      ansible.posix.authorized_key:
        user: deploy
        key: "{{ old_key }}"
        state: absent
```

## 키 폐기

키가 더 이상 필요 없으면 확실하게 제거해야 한다. "혹시 모르니까 남겨두자"는 보안 사고의 원인이 된다.

### 폐기 절차

```bash
# 1. 모든 서버의 authorized_keys에서 해당 공개키 제거
# grep으로 어디에 등록되어 있는지 먼저 확인
for server in $(cat server_list.txt); do
    ssh "$server" "grep 'user@comment' ~/.ssh/authorized_keys" 2>/dev/null && \
        echo "Found on: $server"
done

# 2. 개인키 파일 삭제
shred -vfz -n 5 ~/.ssh/id_ed25519_old
rm ~/.ssh/id_ed25519_old.pub

# 3. ssh-agent에서 제거
ssh-add -d ~/.ssh/id_ed25519_old

# 4. 키 폐기 기록 남기기
echo "$(date) - id_ed25519_old (deploy@mycompany 2025-Q3) 폐기 - 사유: 정기 교체" \
    >> /var/log/ssh-key-audit.log
```

`shred`로 파일을 덮어쓴 뒤 삭제한다. `rm`만으로는 디스크에서 데이터가 완전히 지워지지 않는다. SSD에서는 shred가 완벽하지 않지만, 일반적인 파일 복구 도구로는 복원이 어려워진다.

## 키 인벤토리 감사

서버 100대, 사용자 50명 환경에서 누가 어디에 키를 등록했는지 수동으로 파악하는 건 불가능하다. 정기 감사를 자동화하지 않으면 퇴사자 키, 출처 불명의 키, 정책에 어긋나는 알고리즘이 시간이 갈수록 쌓인다. 보안팀이 6개월에 한 번 손으로 점검하는 방식은 그 사이에 발생한 사고를 막지 못한다.

### authorized_keys 인벤토리 수집

```bash
#!/bin/bash
# audit_authorized_keys.sh
# 모든 서버의 authorized_keys를 수집해서 한 곳에 모은다

OUTPUT_DIR="/var/log/ssh-audit/$(date +%Y-%m-%d)"
mkdir -p "$OUTPUT_DIR"

while read -r server; do
    {
        echo "=== $server ==="
        # /home/*, /root 모든 사용자의 authorized_keys 확인
        ssh -o ConnectTimeout=10 "$server" \
            'sudo find /home /root -name authorized_keys -path "*/.ssh/*" \
                 -exec sh -c "echo \"--- \$1 ---\"; cat \"\$1\"" _ {} \;'
    } > "$OUTPUT_DIR/${server}.txt" 2>&1
done < server_list.txt

# 핑거프린트만 추출 (중복 제거)
for f in "$OUTPUT_DIR"/*.txt; do
    grep -E '^(ssh-|ecdsa|sk-)' "$f" | while read -r key; do
        echo "$key" | ssh-keygen -lf - 2>/dev/null
    done
done | sort -u > "$OUTPUT_DIR/all_fingerprints.txt"
```

수집한 데이터에서 매번 봐야 할 것 — 코멘트(`-C`)가 비어있는 키(출처 불명), CA를 도입했는데도 직접 등록된 일반 공개키, 같은 핑거프린트가 비정상적으로 많은 서버에 퍼져있는 경우(공유된 서비스 계정 키), RSA 1024비트나 ssh-dss 같은 약한 알고리즘. 사람 이름을 코멘트에 박아두는 정책이 자리 잡히면 인사 시스템의 퇴사자 목록과 grep으로 비교하는 게 가능해진다.

### ssh-audit으로 sshd 설정 점검

ssh-audit은 sshd가 지원하는 알고리즘과 호스트 키 상태를 점검하는 도구다. 약한 KEX, MAC, 작은 호스트 키, 취약한 OpenSSH 버전을 잡아낸다.

```bash
# 설치
pip install ssh-audit

# 단일 서버 점검 — fail/warn/info 레벨로 결과 출력
ssh-audit example.com

# 정책 파일 기반 점검
ssh-audit -P /etc/ssh-audit/policy.json example.com

# JSON 출력 — 자동화에 쓴다
ssh-audit -j example.com > result.json
```

ssh-audit이 흔히 잡는 문제 — `diffie-hellman-group1-sha1` KEX, `hmac-sha1` MAC, 1024비트 RSA 호스트 키, `ssh-rsa` 서명 알고리즘. 발견된 항목은 sshd_config의 `KexAlgorithms`, `Ciphers`, `MACs`를 화이트리스트로 운영해서 차단한다.

### 정기 감사 자동화

```bash
#!/bin/bash
# weekly_ssh_audit.sh — cron으로 매주 실행

DATE=$(date +%Y-%m-%d)
PREV=$(date -d '7 days ago' +%Y-%m-%d)
CURR_DIR="/var/log/ssh-audit/$DATE"
PREV_DIR="/var/log/ssh-audit/$PREV"

# 1. authorized_keys 인벤토리 수집
./audit_authorized_keys.sh

# 2. 서버별 ssh-audit
while read -r server; do
    ssh-audit -j "$server" > "$CURR_DIR/audit_${server}.json"
done < server_list.txt

# 3. 이전 주와 diff
diff -r "$PREV_DIR" "$CURR_DIR" > "$CURR_DIR/changes.diff"

# 4. 변경 내역 알림
if [ -s "$CURR_DIR/changes.diff" ]; then
    mail -s "SSH 키 인벤토리 변경 감지" sec-team@mycompany.com \
        < "$CURR_DIR/changes.diff"
fi
```

매주 diff를 보면 누가 임의로 authorized_keys를 수정했는지 추적할 수 있다. CMDB나 권한 관리 시스템과 대조해서 권한이 없는 사용자의 키가 등록된 경우를 잡는다. 운영 자체를 PR 기반으로 옮기면 이 차이가 0에 가까워야 한다 — 0이 아닌 변경이 나오면 누군가 절차를 우회한 것이다.

### 키 사용 추적

키가 *등록되어 있는지*만 확인하는 것으로는 부족하다. 등록은 됐는데 1년 동안 한 번도 안 쓴 키는 폐기 후보다.

```bash
# 최근 30일간 SSH 인증 성공 핑거프린트 추출
sudo grep "Accepted publickey" /var/log/auth.log* | \
    grep -oE 'SHA256:[A-Za-z0-9+/]+' | \
    sort -u > /tmp/used_keys_30d.txt

# 등록은 되어 있지만 안 쓰인 키 찾기
comm -23 <(sort /var/log/ssh-audit/$(date +%Y-%m-%d)/all_fingerprints.txt) \
         <(sort /tmp/used_keys_30d.txt) > /tmp/unused_keys.txt
```

OpenSSH의 `LogLevel VERBOSE` 설정이 켜져있어야 핑거프린트가 로그에 남는다. 기본값은 INFO라 핑거프린트가 안 찍힌다.

## SSH CA로 대규모 서버 관리

서버가 수십 대를 넘어가면 authorized_keys 파일을 개별 관리하는 방식은 한계가 있다. SSH Certificate Authority(CA)를 쓰면 CA가 서명한 인증서 하나로 모든 서버에 접속할 수 있다.

### CA 구축

```bash
# CA 키 생성 — 이 키가 유출되면 전체 인프라가 뚫린다
ssh-keygen -t ed25519 -f /secure/ssh-ca/ca_key -C "MyCompany SSH CA"

# CA 키는 오프라인 저장이 원칙
# USB 보안 토큰이나 HSM에 보관한다
```

### 사용자 인증서 발급

```bash
# 인증서 발급 — 유효기간과 접근 범위를 제한한다
ssh-keygen -s /secure/ssh-ca/ca_key \
    -I "kim-deploy-cert-2026Q2" \
    -n deploy \
    -V +4w \
    -O source-address=10.0.0.0/8 \
    ~/.ssh/id_ed25519.pub

# 발급된 인증서 확인
ssh-keygen -L -f ~/.ssh/id_ed25519-cert.pub
```

인증서 발급 시 주요 옵션:

| 옵션 | 설명 |
|------|------|
| `-I` | 인증서 식별자. 로그에 남는다 |
| `-n` | principal — 접속 가능한 사용자명 |
| `-V` | 유효기간. `+4w`는 4주, `+8h`는 8시간 |
| `-O source-address` | 접속 허용 IP 대역 |
| `-O no-port-forwarding` | 포트 포워딩 차단 |

### 서버 설정

```bash
# /etc/ssh/sshd_config
TrustedUserCAKeys /etc/ssh/ca_key.pub

# principal 매핑 — 인증서의 principal과 실제 사용자를 매핑
AuthorizedPrincipalsFile /etc/ssh/auth_principals/%u

# /etc/ssh/auth_principals/deploy 파일 내용:
# deploy
# ops-team
```

이 설정이 끝나면 authorized_keys에 개별 공개키를 등록할 필요가 없다. CA가 서명한 인증서를 가진 사용자는 principal이 매칭되는 모든 서버에 접속 가능하다.

### 인증서 폐기

인증서를 발급한 뒤에 해당 사용자가 퇴사하면 인증서를 무효화해야 한다. 유효기간이 남아있어도 즉시 차단할 수 있다.

```bash
# KRL(Key Revocation List) 생성
ssh-keygen -k -f /etc/ssh/revoked_keys -s /secure/ssh-ca/ca_key \
    ~/.ssh/compromised_user-cert.pub

# 기존 KRL에 추가
ssh-keygen -k -u -f /etc/ssh/revoked_keys -s /secure/ssh-ca/ca_key \
    ~/.ssh/another_compromised-cert.pub

# sshd_config에 KRL 적용
# RevokedKeys /etc/ssh/revoked_keys
```

KRL 파일을 모든 서버에 배포해야 한다. 이 부분을 자동화하지 않으면, 일부 서버에서 폐기된 인증서로 접속이 가능한 상태가 된다.

## GitHub/GitLab SSH 키 운영

### GitHub SSH 키 등록

```bash
# 키 생성 — GitHub 전용으로 분리한다
ssh-keygen -t ed25519 -C "kim@mycompany.com" -f ~/.ssh/id_ed25519_github

# GitHub에 등록
# Settings > SSH and GPG keys > New SSH key
cat ~/.ssh/id_ed25519_github.pub
# 출력된 공개키를 복사해서 등록

# 접속 테스트
ssh -T git@github.com
# Hi username! You've successfully authenticated...
```

```bash
# ~/.ssh/config
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

### GitHub 계정이 여러 개인 경우

회사 계정과 개인 계정을 분리해서 쓰는 경우가 흔하다.

```bash
# ~/.ssh/config
Host github.com-work
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_work
    IdentitiesOnly yes

Host github.com-personal
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_personal
    IdentitiesOnly yes
```

```bash
# clone할 때 호스트명을 바꿔서 사용
git clone git@github.com-work:company/repo.git
git clone git@github.com-personal:myname/repo.git

# 기존 저장소의 remote URL 변경
git remote set-url origin git@github.com-work:company/repo.git
```

### Deploy Key

Deploy Key는 특정 저장소에만 접근 가능한 SSH 키다. 서비스 계정의 키를 GitHub 계정에 등록하면 해당 계정이 접근 가능한 모든 저장소에 접근할 수 있다. Deploy Key는 저장소 단위로 접근을 제한한다.

```bash
# Deploy Key 전용 키 생성
ssh-keygen -t ed25519 -C "deploy-key-myrepo" -f ~/.ssh/deploy_key_myrepo

# GitHub 저장소 > Settings > Deploy keys > Add deploy key
# "Allow write access"는 배포에 push가 필요한 경우만 체크한다
```

```bash
# CI 서버의 ~/.ssh/config
Host github-myrepo
    HostName github.com
    User git
    IdentityFile ~/.ssh/deploy_key_myrepo
    IdentitiesOnly yes
```

Deploy Key는 하나의 저장소에만 등록할 수 있다. 같은 공개키를 두 저장소에 등록하려고 하면 GitHub이 거부한다. 저장소마다 별도의 키 쌍을 만들어야 한다.

### GitLab SSH 키

GitLab도 구조는 동일하다. 다만 GitLab은 키에 만료일을 설정할 수 있다.

```bash
# GitLab > Preferences > SSH Keys
# "Expiration date" 필드에 만료일 설정 가능
# 만료되면 키가 자동으로 비활성화된다
```

GitLab 관리자는 인스턴스 레벨에서 SSH 키 만료를 강제할 수 있다. 이 설정이 켜져 있으면 만료일 없는 키 등록이 거부된다. GitHub에는 이 기능이 없어서, 조직 정책으로 관리해야 한다.

## 키 유출 시 대응

키가 유출된 것을 인지하면 시간이 중요하다.

### 즉시 대응

```bash
# 1. 유출된 키의 공개키 핑거프린트 확인
ssh-keygen -lf ~/.ssh/compromised_key.pub
# SHA256:xxxx... 이 값으로 authorized_keys에서 검색한다

# 2. 모든 서버에서 해당 키 제거
# 서버 목록이 있다면:
for server in $(cat /etc/ansible/hosts | grep -v '^#'); do
    ssh "$server" "sed -i '/FINGERPRINT_OR_COMMENT/d' ~/.ssh/authorized_keys" &
done
wait

# 3. GitHub/GitLab에서 해당 키 삭제
# GitHub: Settings > SSH keys > Delete
# GitLab: Preferences > SSH Keys > Remove

# 4. SSH CA 인증서였다면 KRL에 추가
ssh-keygen -k -u -f /etc/ssh/revoked_keys \
    -s /secure/ssh-ca/ca_key compromised-cert.pub
# KRL을 모든 서버에 배포
```

### 영향 범위 파악

```bash
# 유출된 키로 접속한 기록 확인
# auth.log에서 해당 키의 핑거프린트 검색
sudo grep "SHA256:xxxx" /var/log/auth.log

# journalctl로 검색
sudo journalctl -u sshd | grep "SHA256:xxxx"

# 최근 로그인 기록
last -i | head -50

# 해당 시간대에 실행된 명령어 확인 (bash_history)
# 공격자가 히스토리를 지울 수 있으므로 auditd 로그가 더 신뢰할 수 있다
sudo ausearch -m execve -ts recent
```

### 사후 조치

1. 유출 원인 파악 — 키 파일이 Git에 커밋됐는지, 공유 드라이브에 있었는지, 노트북 분실인지
2. 새 키 생성 및 배포
3. passphrase가 없었다면 새 키에는 반드시 설정
4. 필요하면 서버의 호스트 키도 교체 (서버 자체가 침해된 경우)

Git에 개인키가 커밋된 경우, 히스토리에서 완전히 제거해야 한다.

```bash
# BFG Repo-Cleaner로 민감 파일 제거
java -jar bfg.jar --delete-files id_ed25519 repo.git
cd repo.git && git reflog expire --expire=now --all && git gc --prune=now --aggressive

# .gitignore에 키 파일 패턴 추가
echo "id_*" >> .gitignore
echo "*.pem" >> .gitignore
echo "!*.pub" >> .gitignore  # 공개키는 괜찮다
```

## HashiCorp Vault SSH Secrets Engine

Vault의 SSH Secrets Engine은 SSH 인증서를 동적으로 발급한다. CA 키를 Vault가 관리하고, 사용자가 요청하면 짧은 유효기간의 인증서를 발급해준다. 수동으로 CA를 운영하는 것보다 안전하고, 인증서 발급 이력이 Vault의 audit log에 남는다.

### Signed Certificates 방식

Vault가 CA 역할을 하면서 사용자의 공개키에 서명해서 인증서를 발급한다.

```bash
# Vault에서 SSH Secrets Engine 활성화
vault secrets enable -path=ssh-client-signer ssh

# CA 키 생성 (Vault 내부에 저장된다)
vault write ssh-client-signer/config/ca generate_signing_key=true

# CA 공개키 가져오기 — 이걸 서버에 배포한다
vault read -field=public_key ssh-client-signer/config/ca > /etc/ssh/trusted-ca.pub
```

### 역할(Role) 설정

```bash
# 인증서 발급 조건을 Role로 정의한다
vault write ssh-client-signer/roles/ops-team - <<EOF
{
  "algorithm_signer": "rsa-sha2-256",
  "allow_user_certificates": true,
  "allowed_users": "deploy,admin",
  "allowed_extensions": "permit-pty",
  "default_extensions": {
    "permit-pty": ""
  },
  "key_type": "ca",
  "default_user": "deploy",
  "ttl": "8h",
  "max_ttl": "24h"
}
EOF
```

TTL을 8시간으로 설정하면, 출근해서 인증서를 발급받고 퇴근하면 만료된다. 키를 교체하거나 폐기할 필요가 없다.

### 인증서 발급

```bash
# 사용자가 자신의 공개키로 인증서 발급 요청
vault write ssh-client-signer/sign/ops-team \
    public_key=@$HOME/.ssh/id_ed25519.pub

# 인증서를 파일로 저장
vault write -field=signed_key ssh-client-signer/sign/ops-team \
    public_key=@$HOME/.ssh/id_ed25519.pub > ~/.ssh/id_ed25519-cert.pub

# 인증서 내용 확인
ssh-keygen -L -f ~/.ssh/id_ed25519-cert.pub
```

### 서버 설정

```bash
# /etc/ssh/sshd_config
TrustedUserCAKeys /etc/ssh/trusted-ca.pub

# systemctl restart sshd
```

authorized_keys 파일을 건드릴 필요가 없다. Vault에서 인증서를 발급받은 사용자는 TrustedUserCAKeys에 등록된 CA로 서명된 인증서를 가지고 있으므로, principal이 맞으면 접속된다.

### OTP 방식

인증서 대신 일회용 비밀번호(OTP)를 발급하는 방식도 있다. 서버에 vault-ssh-helper를 설치해야 한다.

```bash
# OTP용 Secrets Engine 설정
vault secrets enable -path=ssh-otp ssh

vault write ssh-otp/roles/otp-role \
    key_type=otp \
    default_user=deploy \
    cidr_list=10.0.0.0/8

# OTP 발급
vault write ssh-otp/creds/otp-role ip=10.0.1.50
# Key    Value
# key    73b3e2... (일회용 비밀번호)

# 이 OTP로 SSH 접속
ssh deploy@10.0.1.50
# Password: 73b3e2... (한 번 쓰면 폐기된다)
```

OTP 방식은 키 파일 자체가 없어서 키 유출 위험이 없다. 다만 서버마다 vault-ssh-helper를 설치하고 PAM 설정을 변경해야 해서, 초기 구축 비용이 인증서 방식보다 높다.

### Vault SSH 운영 시 주의점

Vault 자체가 죽으면 새 인증서를 발급받을 수 없다. 기존 인증서의 TTL이 남아있으면 접속은 되지만, TTL을 짧게 설정할수록 Vault 장애의 영향이 커진다. Vault를 HA 구성으로 운영하거나, 비상용 authorized_keys를 별도로 관리해야 한다.

```bash
# 비상용 키 설정 — Vault 장애 시 사용
# /etc/ssh/sshd_config
AuthorizedKeysFile .ssh/authorized_keys

# 비상용 키는 금고(사내 비밀번호 관리자)에 보관하고
# 평소에는 사용하지 않는다
```

## 클라우드 네이티브 SSH 키 관리

클라우드 환경에서는 authorized_keys를 직접 관리하지 않는 방식이 점점 표준이 되고 있다. 클라우드 IAM과 SSH 접속을 직접 연동해서, 신원 관리와 접속 권한을 한 곳에서 본다. 인스턴스에 키를 영구히 등록하지 않아도 되고, 누가 어떤 인스턴스에 접속했는지 클라우드 감사 로그에 그대로 남는다.

### AWS EC2 Instance Connect

EC2 Instance Connect는 AWS API를 통해 임시 SSH 공개키를 인스턴스에 60초 동안 등록한다. 사용자는 IAM 권한으로 푸시 요청을 보내고, 60초 안에 SSH 접속을 시작한다. 이후 키는 인스턴스에서 자동으로 사라진다.

```bash
# 임시 키 생성
ssh-keygen -t ed25519 -f /tmp/temp_key -N ""

# 키 푸시 — IAM 권한이 필요하다
aws ec2-instance-connect send-ssh-public-key \
    --instance-id i-1234567890abcdef0 \
    --instance-os-user ec2-user \
    --availability-zone us-east-1a \
    --ssh-public-key file:///tmp/temp_key.pub

# 60초 안에 접속
ssh -i /tmp/temp_key ec2-user@<instance-public-ip>

# 퍼블릭 IP 없는 인스턴스는 Session Manager 경유
aws ssm start-session --target i-1234567890abcdef0
```

장점 — IAM 정책으로 누가 어떤 인스턴스에 접속하는지 제어한다. CloudTrail에 모든 푸시 요청이 기록된다. 인스턴스에 영구 키를 둘 필요가 없다. 단점 — `ec2-instance-connect` 패키지가 설치되어 있어야 한다(Amazon Linux 2 이후 기본 포함, Ubuntu는 별도 설치). 그리고 60초 윈도우가 끝나면 키가 사라지므로 장시간 세션은 일반 ssh-agent로 유지해야 한다.

CI/CD에서 임시 접속이 필요할 때 특히 유용하다 — 영구 키를 인스턴스에 박아두지 않아도 된다.

### GCP OS Login

OS Login은 GCP IAM 사용자를 리눅스 사용자에 자동 매핑한다. SSH 공개키를 Google 계정에 한 번 등록하면, OS Login이 활성화된 모든 인스턴스에 자동으로 푸시된다. 인스턴스마다 사용자 계정을 만들 필요도 없다.

```bash
# 프로젝트 또는 인스턴스 메타데이터에 OS Login 활성화
gcloud compute project-info add-metadata \
    --metadata enable-oslogin=TRUE

# 사용자가 자기 키 등록 (TTL 지정 가능)
gcloud compute os-login ssh-keys add \
    --key-file ~/.ssh/id_ed25519.pub \
    --ttl 8h

# IAM 역할 부여 — 일반 사용자
gcloud projects add-iam-policy-binding my-project \
    --member='user:kim@mycompany.com' \
    --role='roles/compute.osLogin'

# sudo가 필요하면 osAdminLogin
gcloud projects add-iam-policy-binding my-project \
    --member='user:kim@mycompany.com' \
    --role='roles/compute.osAdminLogin'

# gcloud로 접속 — 키 푸시와 사용자 매핑이 자동
gcloud compute ssh instance-name
```

OS Login은 sudo 권한도 IAM으로 분리한다. `osLogin`은 일반 사용자, `osAdminLogin`은 sudo 권한 보유자다. 인스턴스 안에서 `useradd`나 `visudo`를 건드릴 일이 없어진다.

2단계 인증을 강제하려면 `enable-oslogin-2fa=TRUE` 메타데이터를 추가한다. SSH 접속 시 Google Authenticator 코드를 묻는다. 운영 환경에는 거의 필수로 켜둔다.

### Azure AD SSH (Linux VM)

Azure는 Azure AD 자격 증명으로 Linux VM에 SSH 접속하는 기능을 제공한다. `AADSSHLoginForLinux` 확장 프로그램을 VM에 설치하고 RBAC으로 권한을 부여한다.

```bash
# VM에 확장 설치
az vm extension set \
    --publisher Microsoft.Azure.ActiveDirectory \
    --name AADSSHLoginForLinux \
    --resource-group my-rg \
    --vm-name my-vm

# 사용자에게 역할 부여
az role assignment create \
    --role "Virtual Machine Administrator Login" \
    --assignee kim@mycompany.com \
    --scope /subscriptions/.../resourceGroups/my-rg/providers/Microsoft.Compute/virtualMachines/my-vm

# 일반 사용자는 "Virtual Machine User Login"
# 관리자(sudo)는 "Virtual Machine Administrator Login"

# Azure CLI로 접속
az ssh vm --name my-vm --resource-group my-rg
```

`az ssh vm`은 백그라운드에서 임시 SSH 인증서를 발급받아 접속한다. 사용자가 키 파일을 따로 관리할 필요가 없고, AAD에 MFA가 켜져있으면 SSH 접속에도 MFA가 적용된다. Conditional Access 정책으로 IP 대역, 디바이스 컴플라이언스 같은 조건을 SSH에도 그대로 적용할 수 있다.

### 클라우드 네이티브의 한계

클라우드 네이티브 SSH 관리는 같은 클라우드 안의 자원에만 작동한다. 멀티 클라우드 환경이거나 온프레미스 서버가 섞여있으면 통합 관리가 안 된다. 이런 환경에서는 SSH CA(또는 Vault)를 일관된 발급자로 두고, 클라우드 네이티브 방식은 해당 클라우드 자원에만 보조적으로 쓰는 구성이 흔하다.

또 하나 — 클라우드 네이티브 방식은 클라우드 IAM API에 의존한다. 클라우드 콘솔이 다운되거나 IAM이 일시적으로 장애를 겪으면 SSH도 같이 막힌다. SRE 입장에서 비상 접속용 백도어(IP 제한된 비상 키, 별도 jump host)를 별도로 운영해두는 건 이런 의존성 때문이다.

## 참고

- [SSH 보안 기초](../Linux/보안/SSH.md) — SSH 키 인증, sshd_config, 포트 포워딩 등 기본 설정
- [HashiCorp Vault 공식 문서 — SSH Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/ssh)
- [OpenSSH Certificate 인증](https://man.openbsd.org/ssh-keygen#CERTIFICATES)
- [OpenSSH FIDO/U2F 지원](https://www.openssh.com/txt/release-8.2)
- [ssh-audit](https://github.com/jtesta/ssh-audit) — sshd 설정과 알고리즘 점검 도구
- [Secretive](https://github.com/maxgoedjen/secretive) — Apple Secure Enclave 기반 SSH agent
- [ssh-tpm-agent](https://github.com/Foxboron/ssh-tpm-agent) — TPM 기반 SSH agent
- [AWS EC2 Instance Connect](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Connect-using-EC2-Instance-Connect.html)
- [GCP OS Login](https://cloud.google.com/compute/docs/oslogin)
- [Azure AD login for Linux VMs](https://learn.microsoft.com/azure/active-directory/devices/howto-vm-sign-in-azure-ad-linux)
