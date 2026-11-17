---
title: AWS Systems Manager SSM
tags: [aws, cloud]
updated: 2026-11-17
---

# AWS Systems Manager (SSM)

## 개요

SSM은 AWS 리소스를 중앙에서 관리하는 서비스다. 클라우드와 온프레미스 환경의 서버, 애플리케이션, 리소스를 통합 관리한다.

주요 기능은 세 가지다.

- 중앙집중식 관리: 하나의 콘솔에서 모든 인프라 관리
- 보안 강화: SSH 없이 IAM 기반 접속
- 자동화: 패치 관리, 설정 변경, 모니터링 자동화

이런 경우에 SSM을 쓴다.

- 수십, 수백 대의 서버 관리
- SSH 포트를 열지 않고 서버 접속
- 패치 관리 자동화
- 설정값 중앙 관리

기존 방식에는 네 가지 문제가 있다.

- 확장성 문제: 서버 수가 증가할수록 관리 복잡도 증가
- 보안 취약점: SSH 포트 오픈으로 인한 외부 공격 위험
- 일관성 부족: 수동 작업으로 인한 설정 불일치
- 감사 어려움: 개별 서버의 작업 내역 추적 어려움

SSM은 이런 문제를 해결한다.

## 핵심 구성 요소

### SSM Agent

SSM Agent는 관리 대상 서버에 설치되는 소프트웨어다. AWS SSM 서비스와 관리 대상 인스턴스 간의 통신을 담당한다.

Agent가 하는 일은 네 가지다.

- AWS SSM 서비스로부터 명령 수신 및 실행
- 실행 결과와 상태 정보를 AWS로 전송
- 주기적인 하트비트로 인스턴스 상태 보고
- SSM 기능(Parameter Store, Patch Manager 등)과 연동

SSM Agent는 인스턴스 내에서 데몬 프로세스로 실행된다. AWS SSM 서비스와 지속적으로 통신한다. 통신은 HTTPS(443 포트)로 이루어지므로 별도의 방화벽 설정이나 포트 오픈이 필요 없다.

설치 여부는 OS마다 다르다.

- Amazon Linux 2, Ubuntu: 기본 설치됨
- Windows: 기본 설치됨
- 다른 OS: 수동 설치 필요

Agent가 실행 중인지는 `sudo systemctl status amazon-ssm-agent` 명령으로 확인한다.

### Session Manager

Session Manager는 SSH나 RDP 없이도 안전하게 서버에 접속할 수 있게 해주는 기능이다.

보안 면에서 얻는 것은 네 가지다.

- SSH 키 관리 불필요
- Bastion Host 운영 비용 절감
- 모든 세션 활동 자동 로깅
- IAM 기반의 세밀한 접근 제어

세션은 CLI나 콘솔에서 시작한다.

```bash
# AWS CLI로 세션 시작
aws ssm start-session --target i-1234567890abcdef0

# 또는 AWS 콘솔에서
# Systems Manager > Session Manager > Start session
```

주로 쓰는 상황은 이렇다.

- 긴급 상황에서의 서버 접속
- 개발/테스트 환경의 일시적 접속
- 감사 목적의 서버 점검
- 자동화된 스크립트 실행

SSH 포트(22)를 닫고 Session Manager만 쓰면 외부에서 들어올 입구가 사라진다. 세션 활동은 모두 CloudTrail에 기록된다.

### Run Command

Run Command는 여러 인스턴스에 동시에 명령을 실행할 수 있는 기능이다.

특징은 네 가지다.

- 수천 대의 인스턴스에 동시 명령 실행 가능
- 명령 실행 결과 실시간 모니터링
- 실행 이력 추적 및 감사
- Linux, Windows 지원

아래 코드는 여러 인스턴스에 명령을 보내고 실행 상태를 확인하는 예다.

```bash
# 여러 인스턴스에 동시 명령 실행
aws ssm send-command \
  --instance-ids "i-1234567890abcdef0" "i-0987654321fedcba0" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["sudo yum update -y"]'

# 명령 실행 상태 확인
aws ssm list-command-invocations \
  --command-id "command-id-here"
```

자주 하는 작업은 이렇다.

- 보안 패치 일괄 적용
- 로그 파일 정리 및 아카이빙
- 애플리케이션 배포 및 업데이트
- 시스템 상태 점검 및 진단

태그로 명령 대상을 특정 인스턴스 그룹에만 좁힐 수 있다. 예: `Environment=Production` 태그가 있는 인스턴스만 선택.

### Parameter Store

Parameter Store는 애플리케이션 설정값과 민감한 정보를 안전하게 저장하고 관리하는 서비스다.

핵심 기능은 네 가지다.

- 계층적 파라미터 구조 지원
- KMS로 자동 암호화
- 버전 관리 및 변경 이력 추적
- 데이터 타입 지원 (String, StringList, SecureString)

파라미터 타입은 세 가지다.

- String: 일반 텍스트 값
- StringList: 쉼표로 구분된 값 목록
- SecureString: 암호화된 값 (KMS 사용)

아래 코드는 파라미터를 저장하고 조회하는 예다.

```bash
# 파라미터 저장
aws ssm put-parameter \
  --name "/myapp/database/password" \
  --value "secret123" \
  --type "SecureString" \
  --key-id "alias/aws/ssm"

# 파라미터 조회
aws ssm get-parameter \
  --name "/myapp/database/password" \
  --with-decryption
```

접근 제어는 네 가지로 이루어진다.

- IAM 기반의 세밀한 접근 제어
- KMS 키로 암호화된 파라미터 지원
- CloudTrail에 모든 접근 로그 기록
- 네트워크 레벨의 접근 제한

파라미터 이름에 환경을 경로로 넣으면 환경별로 나눠 관리하기 쉽다. 예: `/myapp/dev/database/password`, `/myapp/prod/database/password`

### Patch Manager

Patch Manager는 운영체제와 애플리케이션의 패치를 자동화하는 기능이다.

자동화되는 항목은 네 가지다.

- 운영체제별 패치 정책 설정
- 정기적인 패치 스케줄링
- 패치 전후 상태 검증
- 롤백 기능으로 패치를 되돌릴 수 있음

패치 정책 유형은 네 가지다.

- Critical: 보안 관련 중요 패치만 적용
- Important: 중요도가 높은 패치 적용
- All: 모든 사용 가능한 패치 적용
- Custom: 사용자 정의 패치 정책

아래 코드는 패치 정책을 만들고 패치 그룹에 연결하는 예다.

```bash
# 패치 정책 생성
aws ssm create-patch-baseline \
  --name "Production-Patch-Baseline" \
  --description "Production environment patch policy" \
  --approval-rules 'PatchRules=[{PatchFilterGroup={PatchFilters=[{Key=PATCH_SET,Values=[OS]}]},ComplianceLevel=CRITICAL}]'

# 패치 그룹에 정책 연결
aws ssm register-patch-baseline-for-patch-group \
  --baseline-id "pb-1234567890abcdef0" \
  --patch-group "Production"
```

프로덕션 환경은 Critical 패치만 자동 적용하고, 나머지는 수동 검토 후 적용하는 게 안전하다.

### State Manager

State Manager는 인스턴스의 상태를 원하는 대로 유지하도록 자동화하는 기능이다.

상태 관리는 네 가지 원리로 동작한다.

- 선언적 상태 정의 (Desired State)
- 주기적인 상태 검증 및 수정
- 드리프트 감지 및 자동 복구
- 다른 상태 관리 도구와 연동

아래 코드는 CloudWatch Agent 패키지를 설치하는 association을 만들고 실행 결과를 확인하는 예다.

```bash
# 상태 관리 문서 생성
aws ssm create-association \
  --name "AWS-ConfigureAWSPackage" \
  --targets "Key=instanceids,Values=i-1234567890abcdef0" \
  --parameters 'action=Install,name=AmazonCloudWatchAgent'

# 상태 확인
aws ssm describe-association-executions \
  --association-id "association-id-here"
```

활용하는 사례는 이렇다.

- 소프트웨어 설치 및 버전 관리
- 시스템 설정의 일관성 유지
- 보안 정책의 자동 적용
- 모니터링 에이전트의 상태 관리

State Manager는 주기적으로 상태를 검증한다. 설정이 변경되면 자동으로 원래 상태로 복구한다.

### Inventory

Inventory는 관리 대상 인스턴스의 자산 정보를 자동으로 수집하고 관리하는 기능이다.

수집하는 정보는 네 가지다.

- 설치된 소프트웨어 및 버전
- 운영체제 정보 및 패치 상태
- 네트워크 설정 및 보안 그룹
- 하드웨어 사양 및 리소스 사용량

아래 코드는 인벤토리를 조회하는 예다.

```bash
# 인벤토리 정보 조회
aws ssm get-inventory \
  --instance-id "i-1234567890abcdef0"

# 특정 소프트웨어가 설치된 인스턴스 찾기
aws ssm get-inventory-schema
```

활용 목적은 이렇다.

- 자산 인벤토리 관리
- 보안 취약점 분석
- 라이선스 관리
- 규정 준수 감사

Inventory는 주기적으로 자동 수집된다. CloudWatch와 연동해 특정 소프트웨어가 설치된 인스턴스를 찾을 수 있다.

## 아키텍처

### 전체 구조

SSM은 AWS의 마이크로서비스 아키텍처로 구축되어 있다. 각 기능은 독립적인 서비스로 구현되어 있다.

구성 요소는 다섯 가지다.

- SSM Service: 중앙 관리 서비스
- SSM Agent: 인스턴스별 에이전트
- IAM: 인증 및 권한 관리
- CloudTrail: 감사 로그 관리
- CloudWatch: 모니터링 및 알림

### 통신 모델

SSM Agent와 AWS SSM 서비스 간 통신의 특징은 세 가지다.

통신은 폴링 방식이다. SSM Agent는 주기적으로 AWS SSM 서비스에 연결해 새로운 명령이나 작업이 있는지 확인한다. 방화벽 친화적인 접근 방식이다.

모든 통신은 HTTPS로 암호화된다.

각 AWS 리전별로 전용 엔드포인트를 사용해 지연 시간을 최소화한다.

프라이빗 서브넷에서는 VPC 엔드포인트를 쓰면 NAT Gateway 비용을 줄인다.

### 권한 모델

SSM은 AWS IAM과 통합된 권한 모델을 사용한다.

EC2 인스턴스는 인스턴스 프로파일에 붙인 IAM 역할로 SSM 서비스에 접근할 권한을 얻는다.

인스턴스 역할에 필요한 IAM 정책 JSON은 이렇다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:UpdateInstanceInformation",
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    }
  ]
}
```

SSM 콘솔이나 CLI를 쓰는 사용자는 IAM 정책으로 필요한 권한을 부여받는다.

각 구성 요소는 필요한 권한만 갖도록 설계되어 있다.

## 실무 활용 전략

### 보안 중심의 접근

SSH 접속을 점진적으로 SSM Session Manager로 대체한다. 보안이 올라가고 운영 복잡성이 줄어든다.

보안 그룹에서 SSH 포트(22)를 제거하고 모든 서버 접속을 SSM으로만 하도록 정책을 세운다.

CloudTrail과 연동해 SSM 활동을 모두 로깅하고 정기 감사 체계를 만든다.

### 자동화 기반 운영

Patch Manager로 보안 패치를 정기적으로 자동화하고 패치 현황을 실시간으로 모니터링한다.

State Manager로 서버 설정의 일관성을 유지하고 설정 드리프트를 자동으로 감지해 수정한다.

Run Command로 애플리케이션 배포를 자동화하고 배포 과정을 추적·모니터링한다.

### 비용 최적화

Session Manager를 쓰면 Bastion Host를 따로 운영하지 않아도 돼 인프라 비용이 준다.

자동화로 수동 작업을 줄이면 운영팀 생산성이 올라간다.

Inventory로 사용하지 않는 소프트웨어나 리소스를 찾아 정리한다.

## 도입 시 고려사항

### 기술적 요구사항

관리 대상 인스턴스는 AWS SSM 엔드포인트에 접근할 수 있어야 한다. VPC 엔드포인트나 NAT Gateway를 거친 인터넷 접근이 필요하다.

IAM 역할과 정책이 설정되어 있어야 한다. 특히 `AmazonSSMManagedInstanceCore` 정책이 필수다.

모든 관리 대상 인스턴스에 SSM Agent가 설치되고 실행 중이어야 한다.

Agent 상태와 SSM 등록 여부는 아래 명령으로 확인한다.

```bash
# SSM Agent 상태 확인
sudo systemctl status amazon-ssm-agent

# 인스턴스가 SSM에 등록되었는지 확인
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0"
```

### 운영상 고려사항

모든 서버를 한 번에 SSM으로 전환하지 말고 단계적으로 도입해 안정성을 확보한다.

SSM Agent 상태를 지속적으로 모니터링하고, 장애가 나면 빠르게 대응할 체계를 만든다.

SSM에 의존하는 환경에서는 대체 접속 방법을 준비해둔다.

### 보안 고려사항

각 사용자와 역할에 필요한 권한만 부여한다.

SSM 활동 로그를 정기적으로 검토하고 비정상 활동을 감지한다.

Parameter Store의 민감한 정보는 반드시 KMS로 암호화한다.

## 다른 AWS 서비스와의 통합

### CloudWatch 통합

SSM은 CloudWatch와 통합되어 있다.

SSM Agent의 상태, 명령 실행 결과 등을 CloudWatch 메트릭으로 수집한다.

SSM 관련 이벤트는 CloudWatch 알림으로 받을 수 있다.

SSM Agent 로그를 CloudWatch Logs로 전송해 중앙 집중식 로그 관리가 가능하다.

### Lambda 통합

SSM Run Command를 Lambda 함수에서 호출해 서버리스 환경에서도 인프라 자동화가 가능하다.

CloudWatch Events나 다른 AWS 서비스의 이벤트에 반응해 자동으로 SSM 명령을 실행할 수 있다.

EventBridge로 정기적인 SSM 작업을 스케줄링할 수 있다.

아래 코드는 Lambda 함수에서 SSM 명령을 실행하는 예다.

```javascript
// Lambda 함수에서 SSM 명령 실행
const ssm = new AWS.SSM();

const params = {
  InstanceIds: ['i-1234567890abcdef0'],
  DocumentName: 'AWS-RunShellScript',
  Parameters: {
    commands: ['sudo systemctl restart myapp']
  }
};

await ssm.sendCommand(params).promise();
```

### CodePipeline 통합

CI/CD 파이프라인에서 SSM을 활용할 수 있다.

CodePipeline에서 SSM Run Command를 사용해 애플리케이션 배포를 자동화한다.

Parameter Store로 환경별 설정값을 안전하게 관리한다.

## 제한사항

### 기술적 한계

SSM은 AWS 서비스에 대한 네트워크 연결이 필수적이다. 네트워크 장애 시 관리가 어려워진다.

SSM Agent가 설치되지 않은 시스템은 관리할 수 없다.

폴링 기반 통신이라 실시간성이 필요한 작업에는 맞지 않을 수 있다.

### 운영상 한계

기존 SSH 기반 관리에 익숙한 팀에게는 새로운 도구 학습이 필요하다.

SSM 의존도가 높아지면 SSM 서비스 장애 때 전체 관리가 어려워질 수 있다.

### 대안 및 보완 방안

중요한 시스템은 SSM과 기존 방식 모두를 지원하도록 구성한다.

SSM Agent 상태를 지속적으로 모니터링하고, 장애 시 쓸 대체 접속 방법을 준비한다.

SSM 사용법과 트러블슈팅 방법을 문서로 정리한다.

SSM Agent가 정상 동작하지 않으면 CloudWatch Logs에서 에러 로그를 확인한다. IAM 권한 문제일 가능성이 높다.

## 참고

- AWS Systems Manager 공식 문서: https://docs.aws.amazon.com/systems-manager/
- AWS Systems Manager Best Practices: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-best-practices.html
- AWS Parameter Store 활용 가이드: https://docs.aws.amazon.com/systems-manager/latest/userguide/secure-string-parameter-kms-encryption.html
