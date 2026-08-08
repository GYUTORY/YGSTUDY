---
title: 배스천 호스트 - private subnet 접근과 감사 구성
tags: [network, linux, security]
updated: 2026-07-25
---

# 배스천 호스트 - private subnet 접근과 감사 구성

배스천 호스트를 처음 구성한 건 AWS에서 RDS를 private subnet에만 두기로 결정하면서였다. public subnet에 묶어두는 건 찜찜하니까 DB는 무조건 private, 그런데 로컬 DBeaver에서 바로 붙고 싶다. 그때 처음 배스천을 세우고 SSH 터널을 뚫었다.

몇 년 지나면서 팀이 커지고, 배스천 호스트에 누가 언제 들어갔는지 기록도 없고, IAM 계정은 있는데 OS 계정 관리가 따로 노는 문제가 생겼다. 결국 AWS Systems Manager Session Manager로 넘어갔고, 배스천 자체를 없앴다.

배스천 호스트를 언제 쓰고 언제 버리는지, 실제 운영하면서 겪은 것들을 정리했다.

## 배스천 호스트가 하는 일

배스천 호스트(Bastion Host)는 외부 네트워크에서 private 네트워크로 들어가는 유일한 진입점 역할을 한다. 군사 용어에서 왔는데, 요새 안으로 들어가는 성문 하나와 비슷한 개념이다.

private subnet에 있는 서버들은 인터넷에서 직접 접근이 안 된다. 라우팅 테이블에 인터넷 게이트웨이 경로가 없거나, 보안 그룹/NACL에서 아예 차단한다. 이 서버들을 관리하려면 같은 VPC 안이나 VPN으로 연결된 네트워크에서 들어가야 한다.

배스천은 public subnet에 올려서 22번 포트를 외부에 노출하고, 이 배스천을 거쳐서 private 서버로 들어가는 구조다.

```
인터넷 → [배스천 호스트 - public subnet] → [private 서버들 - private subnet]
                22 포트만 열림                    22 포트 내부에서만
```

배스천의 보안 그룹은 22번에 대해 사무실 IP, VPN 출구 IP, 개발자 집 IP 등 신뢰할 수 있는 대역만 허용한다. `0.0.0.0/0`으로 22번 열어두는 건 배스천이 아니라 그냥 공개된 SSH 서버다.

## 점프 서버 구성

점프 서버(Jump Server)는 배스천 호스트를 통해 내부 서버로 SSH하는 방식이다. 두 가지 방법이 있다.

### ProxyJump 방식

`~/.ssh/config`에 설정해두면 매번 옵션을 안 써도 된다.

```ssh-config
Host bastion
  HostName 52.xx.xx.xx
  User ec2-user
  IdentityFile ~/.ssh/bastion-key.pem

Host db-server
  HostName 10.0.2.15
  User ec2-user
  IdentityFile ~/.ssh/private-key.pem
  ProxyJump bastion

Host app-server-*
  HostName 10.0.3.%n
  User ubuntu
  IdentityFile ~/.ssh/private-key.pem
  ProxyJump bastion
```

`ssh db-server` 한 번으로 배스천 경유가 자동으로 처리된다. `ProxyJump`는 OpenSSH 7.3부터 지원된다.

이전에는 `ProxyCommand`를 썼다.

```ssh-config
Host db-server
  HostName 10.0.2.15
  User ec2-user
  ProxyCommand ssh -W %h:%p bastion
```

`ProxyJump`가 더 간결하니 구버전 서버가 아니면 `ProxyJump`를 쓴다.

### 키 전달 주의사항

배스천 호스트에 개인키를 복사하면 안 된다. 배스천이 털리면 private 서버 키까지 노출된다. SSH 에이전트 포워딩(`-A`)을 쓰면 배스천에 키를 두지 않아도 된다.

```bash
ssh -A ec2-user@bastion
# 그 다음 배스천에서
ssh ec2-user@10.0.2.15
```

에이전트 포워딩은 배스천 서버의 루트 권한을 가진 누군가가 에이전트 소켓을 재사용할 수 있다는 위험이 있다. 에이전트 포워딩을 쓰려면 배스천 서버 자체가 완전히 신뢰 가능해야 한다. `ProxyJump`는 이 문제가 없다. 클라이언트에서 내부 서버까지 직접 연결을 만들기 때문에 배스천 서버에 에이전트 소켓이 남지 않는다.

## SSH 터널링으로 private subnet 접근

private subnet의 DB나 내부 서비스에 로컬에서 직접 붙으려면 포트 포워딩을 쓴다.

### 로컬 포워딩

```bash
# 로컬 15432 → 배스천 → private RDS (10.0.2.50:5432)
ssh -L 15432:10.0.2.50:5432 -N ec2-user@bastion

# DBeaver나 psql에서 localhost:15432로 접속
psql -h localhost -p 15432 -U dbuser mydb
```

`-N`은 원격 명령 실행 없이 포워딩만 유지한다. `-f`까지 붙이면 백그라운드로 돌아간다.

```bash
# 백그라운드 실행
ssh -fN -L 15432:10.0.2.50:5432 ec2-user@bastion

# 세션 종료
ps aux | grep ssh
kill <pid>
```

혼자 쓰는 단발성 접속엔 이게 제일 편하다. 다만 세션이 끊어지면 재연결을 수동으로 해야 한다. 장시간 유지해야 하면 `autossh`나 `systemd` 유닛을 쓴다.

```ini
# /etc/systemd/system/ssh-tunnel-rds.service
[Unit]
Description=SSH tunnel to private RDS
After=network.target

[Service]
User=deploy
ExecStart=/usr/bin/ssh -NT \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -L 15432:10.0.2.50:5432 \
  ec2-user@bastion
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### SOCKS 프록시로 내부망 접근

내부 서비스 여러 개에 붙어야 할 때 `-L`을 서비스마다 잡는 건 번거롭다. `-D`로 SOCKS5 프록시를 띄우면 내부 IP 전체를 라우팅할 수 있다.

```bash
ssh -D 1080 -N ec2-user@bastion
```

브라우저나 curl을 SOCKS5 프록시로 설정하면 내부 서비스에 직접 붙는다.

```bash
curl --socks5 localhost:1080 http://10.0.3.10:8080/admin
```

브라우저에서는 FoxyProxy 같은 확장으로 내부 IP 대역만 SOCKS 프록시를 경유하게 설정한다.

## AWS Session Manager와 배스천 호스트 비교

배스천 호스트를 몇 년 운영하면서 점점 불편해진 것들이 있었다.

OS 수준 계정 관리가 IAM과 별개였다. 신규 입사자에게 배스천 접근 주려면 IAM 계정 만들고, SSH 키 생성하고, 배스천 서버에 공개키 등록하는 걸 따로 했다. 퇴사자 처리도 IAM 비활성화와 별개로 배스천 `authorized_keys`에서 키를 지워야 했다. 한 번은 퇴사한 개발자 키가 한 달 넘게 살아 있었다.

또 배스천 서버 자체를 관리해야 했다. OS 패치, 키 관리, 로그 수집 설정. 트래픽이 거의 없는 서버인데 거기에 시간을 쓰는 게 낭비였다.

AWS Systems Manager Session Manager(SSM Session Manager)는 이 문제들을 IAM 하나로 해결한다.

### Session Manager의 동작 방식

SSM Agent가 인스턴스에서 실행되고, 이 에이전트가 AWS Systems Manager 엔드포인트로 아웃바운드 HTTPS 연결을 유지한다. 사용자는 이 채널로 세션을 연다. 인바운드 22번 포트가 전혀 필요 없다.

```
사용자 → AWS Systems Manager 엔드포인트 → SSM Agent (인스턴스)
```

인스턴스 보안 그룹에서 22번 포트 인바운드 규칙을 완전히 제거한다. 인터넷이나 사내망에서 직접 접근할 방법 자체가 사라진다.

접근 권한은 IAM 정책으로만 관리한다. 퇴사자 IAM 계정을 비활성화하는 것만으로 Session Manager 접근이 차단된다. 키 파일을 따로 회수할 필요가 없다.

### SSM Agent 설치와 IAM 역할 설정

Amazon Linux 2, Amazon Linux 2023, Ubuntu 20.04 이후 버전에는 SSM Agent가 기본 설치된다. 직접 설치해야 하는 경우:

```bash
# Ubuntu/Debian
sudo snap install amazon-ssm-agent --classic
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

인스턴스에 IAM 역할을 붙여야 한다. 최소 권한으로 쓰려면 `AmazonSSMManagedInstanceCore` 정책이 필요하다. 이 정책에 포함된 권한이다.

- `ssm:UpdateInstanceInformation` - 인스턴스 상태 보고
- `ssmmessages:*` - 세션 채널 메시지 처리
- `ec2messages:*` - Run Command 처리
- `s3:GetEncryptionConfiguration` - S3 암호화 확인

VPC에 인터넷 게이트웨이가 없는 완전한 private 환경이면 SSM, SSMMMessages, EC2Messages에 대한 VPC 엔드포인트가 필요하다.

```
com.amazonaws.ap-northeast-2.ssm
com.amazonaws.ap-northeast-2.ssmmessages
com.amazonaws.ap-northeast-2.ec2messages
```

### 세션 시작

```bash
# AWS CLI로 세션 시작
aws ssm start-session --target i-0123456789abcdef0

# 특정 리전
aws ssm start-session --target i-0123456789abcdef0 --region ap-northeast-2
```

브라우저에서는 EC2 콘솔 → 인스턴스 선택 → Connect → Session Manager 탭으로 들어간다.

### SSM으로 포트 포워딩

Session Manager는 SSH 포트 포워딩도 대체한다.

```bash
# 로컬 15432 → private RDS (10.0.2.50:5432)
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["10.0.2.50"],"portNumber":["5432"],"localPortNumber":["15432"]}'
```

`~/.ssh/config`에 배스천 없이 ProxyCommand로 쓸 수도 있다.

```ssh-config
Host i-* mi-*
  ProxyCommand sh -c "aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters 'portNumber=%p'"
```

이 설정으로 `ssh ec2-user@i-0123456789abcdef0` 형태로 쓴다. SSH 키 인증은 그대로 쓰되, 전송 채널이 SSM Session Manager를 타는 구조다. 22번 포트가 열려 있을 필요가 없다.

### 배스천 호스트가 여전히 필요한 경우

Session Manager가 만능은 아니다. AWS 밖의 서버, 온프레미스 서버는 SSM Agent를 붙이더라도 AWS managed instance로 등록하는 설정이 별도로 필요하다. 여러 클라우드나 IDC가 섞인 환경에서는 배스천 호스트가 더 단순하다.

또 SSH 자체 기능(SCP, SFTP, 포트포워딩)을 이미 스크립트화해서 쓰고 있다면 Session Manager로 전환할 때 그 부분을 전부 다시 짜야 한다. 팀에 SSH에 익숙하지 않은 사람이 있을 때 Session Manager 콘솔이 더 접근하기 쉬운 면도 있다.

## 접근 이력 로깅과 감사 구성

배스천 호스트든 Session Manager든, 누가 언제 어떤 서버에 들어갔는지는 기록이 있어야 한다. 감사 요청이 올 때 로그가 없으면 할 말이 없다.

### 배스천 호스트 로깅

sshd 자체 로그는 `authlog`나 `secure`에 기록된다.

```
/var/log/auth.log  (Ubuntu/Debian)
/var/log/secure    (RHEL/CentOS/Amazon Linux)
```

기본 로그에는 접속 시각, 소스 IP, 사용자명, 키 핑거프린트가 찍힌다.

```
Jul 25 10:23:15 bastion sshd[12345]: Accepted publickey for ec2-user from 121.xx.xx.xx port 54321 ssh2: RSA SHA256:xxxx
```

이것만으로는 배스천에서 어디로 ProxyJump했는지, 세션에서 뭘 했는지는 알 수 없다. 더 상세한 감사가 필요하면 `auditd`나 세션 로깅 도구를 쓴다.

터미널 세션 내용 자체를 기록하려면 `script` 명령이나 `tlog` 같은 도구를 사용한다.

```bash
# sshd_config에 ForceCommand로 tlog 강제 적용
# /etc/ssh/sshd_config
ForceCommand /usr/bin/tlog-rec-session
```

`tlog`는 터미널 입출력을 JSON으로 기록하고 나중에 재생할 수 있다. 설치와 설정은 별도 작업이 필요하지만, 보안 감사가 엄격한 환경에서는 이 수준의 로그가 요구된다.

로그를 배스천 서버 로컬에만 두면 서버가 교체되거나 날아가면 사라진다. CloudWatch Logs나 S3로 중앙화해야 한다.

```json
{
  "/var/log/secure": {
    "file_path": "/var/log/secure",
    "log_group_name": "/bastion/secure",
    "log_stream_name": "{instance_id}"
  }
}
```

CloudWatch Logs Agent나 CloudWatch Agent를 배스천에 설치하고 위 설정을 적용한다.

### Session Manager 로깅

Session Manager는 로깅 설정이 한 곳에서 된다. Systems Manager 콘솔 → Session Manager → Preferences에서 설정한다.

S3에 세션 출력 저장:

```json
{
  "s3BucketName": "company-ssm-session-logs",
  "s3KeyPrefix": "sessions/",
  "s3EncryptionEnabled": true
}
```

CloudWatch Logs로도 보낼 수 있다.

```json
{
  "cloudWatchLogGroupName": "/ssm/session-manager",
  "cloudWatchEncryptionEnabled": true,
  "cloudWatchStreamingEnabled": true
}
```

세션 중 실행한 명령과 출력이 S3나 CloudWatch Logs에 남는다. Session Manager 이전에 배스천을 쓸 때는 이 수준의 로깅을 구성하려면 별도 도구가 필요했는데, Session Manager는 설정 몇 줄로 된다.

### CloudTrail로 접근 감사

Session Manager의 세션 시작/종료는 AWS CloudTrail에 API 호출로 기록된다.

```json
{
  "eventName": "StartSession",
  "userIdentity": {
    "type": "IAMUser",
    "userName": "dev-user",
    "arn": "arn:aws:iam::123456789012:user/dev-user"
  },
  "requestParameters": {
    "target": "i-0123456789abcdef0"
  },
  "eventTime": "2026-07-25T10:23:15Z",
  "sourceIPAddress": "121.xx.xx.xx"
}
```

누가, 어느 IP에서, 어떤 인스턴스에, 언제 들어갔는지 쿼리가 된다. Athena로 CloudTrail 로그를 분석하거나, CloudWatch Logs Insights로 실시간 모니터링한다.

```sql
-- Athena로 특정 인스턴스 접근 이력 조회
SELECT eventtime, useridentity.username, sourceipaddress
FROM cloudtrail_logs
WHERE eventsource = 'ssm.amazonaws.com'
  AND eventname = 'StartSession'
  AND requestparameters LIKE '%i-0123456789abcdef0%'
ORDER BY eventtime DESC
```

Session Manager 접근 권한을 IAM으로 세밀하게 제어할 수도 있다. 특정 인스턴스에만 접근을 허용하거나, 특정 태그가 달린 인스턴스에만 접근하게 하는 식이다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ssm:StartSession",
      "Resource": [
        "arn:aws:ssm:*:*:document/AWS-StartSSHSession",
        "arn:aws:ec2:*:*:instance/*"
      ],
      "Condition": {
        "StringEquals": {
          "ssm:resourceTag/Environment": "production"
        }
      }
    }
  ]
}
```

이 정책은 `Environment: production` 태그가 붙은 인스턴스에만 Session Manager 접근을 허용한다.

## 실무에서 자주 겪는 문제

배스천을 통한 SSH 포트포워딩이 갑자기 끊기는 경우, 대부분 idle timeout 때문이다. 방화벽이나 AWS NAT Gateway가 일정 시간 트래픽 없는 연결을 끊는다.

`ServerAliveInterval`을 설정해서 keepalive를 보내면 해결된다.

```ssh-config
Host bastion
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

인스턴스가 교체되면 host key가 바뀌어서 `REMOTE HOST IDENTIFICATION HAS CHANGED` 오류가 난다. 배스천 IP가 같아도 인스턴스가 다르면 키가 다르다. 오토스케일링이나 스팟 인스턴스 사용 시 자주 발생한다.

```bash
ssh-keygen -R bastion.example.com
```

배스천을 완전히 없애고 Session Manager만 쓰게 되면 이 문제 자체가 없어진다.

Session Manager 포트포워딩 세션이 끊겼는데 로컬 포트가 해제되지 않는 경우가 있다. 프로세스가 CLOSE_WAIT 상태로 남은 것인데, 해당 aws ssm 프로세스를 직접 종료해야 한다.

```bash
lsof -ti :15432 | xargs kill -9
```
