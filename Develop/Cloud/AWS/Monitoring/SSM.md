---
title: AWS Systems Manager SSM
tags: [aws, monitoring-and-management, ssm]
updated: 2025-12-07
---

# AWS Systems Manager (SSM)

## 개요

SSM은 AWS 리소스를 중앙에서 관리하는 서비스다. 클라우드와 온프레미스 환경의 서버, 애플리케이션, 리소스를 통합 관리한다.

**주요 기능:**
- 중앙집중식 관리: 하나의 콘솔에서 모든 인프라 관리
- 보안 강화: SSH 없이 IAM 기반 접속
- 자동화: 패치 관리, 설정 변경, 모니터링 자동화

**사용하는 경우:**
- 수십, 수백 대의 서버 관리
- SSH 포트를 열지 않고 서버 접속
- 패치 관리 자동화
- 설정값 중앙 관리

**기존 방식의 문제점:**
- 확장성 문제: 서버 수가 증가할수록 관리 복잡도 증가
- 보안 취약점: SSH 포트 오픈으로 인한 외부 공격 위험
- 일관성 부족: 수동 작업으로 인한 설정 불일치
- 감사 어려움: 개별 서버의 작업 내역 추적 어려움

SSM은 이런 문제를 해결한다.

## 핵심 구성 요소

### SSM Agent

SSM Agent는 관리 대상 서버에 설치되는 소프트웨어다. AWS SSM 서비스와 관리 대상 인스턴스 간의 통신을 담당한다.

**주요 기능:**
- AWS SSM 서비스로부터 명령 수신 및 실행
- 실행 결과와 상태 정보를 AWS로 전송
- 주기적인 하트비트를 통해 인스턴스 상태 보고
- 다양한 SSM 기능(Parameter Store, Patch Manager 등)과 연동

**동작 원리:**
SSM Agent는 인스턴스 내에서 데몬 프로세스로 실행된다. AWS SSM 서비스와 지속적으로 통신한다. 통신은 HTTPS(443 포트)를 통해 이루어지므로 별도의 방화벽 설정이나 포트 오픈이 필요 없다.

**설치:**
- Amazon Linux 2, Ubuntu: 기본 설치됨
- Windows: 기본 설치됨
- 다른 OS: 수동 설치 필요

**실무 팁:**
SSM Agent가 실행 중인지 확인하려면 `sudo systemctl status amazon-ssm-agent` 명령을 사용한다.

### Session Manager

Session Manager는 SSH나 RDP 없이도 안전하게 서버에 접속할 수 있게 해주는 기능이다.

**보안상의 장점:**
- SSH 키 관리 불필요
- Bastion Host 운영 비용 절감
- 모든 세션 활동 자동 로깅
- IAM 기반의 세밀한 접근 제어

**사용 방법:**
```bash
# AWS CLI로 세션 시작
aws ssm start-session --target i-1234567890abcdef0

# 또는 AWS 콘솔에서
# Systems Manager > Session Manager > Start session
```

**활용 시나리오:**
- 긴급 상황에서의 서버 접속
- 개발/테스트 환경의 일시적 접속
- 감사 목적의 서버 점검
- 자동화된 스크립트 실행

**실무 팁:**
SSH 포트(22)를 닫고 Session Manager만 사용하면 보안이 크게 향상된다. 모든 세션 활동이 CloudTrail에 기록된다.

### Run Command

Run Command는 여러 인스턴스에 동시에 명령을 실행할 수 있는 기능이다.

**주요 특징:**
- 수천 대의 인스턴스에 동시 명령 실행 가능
- 명령 실행 결과 실시간 모니터링
- 실행 이력 추적 및 감사
- 다양한 운영체제 지원 (Linux, Windows)

**사용 예시:**
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

**실무 활용 예시:**
- 보안 패치 일괄 적용
- 로그 파일 정리 및 아카이빙
- 애플리케이션 배포 및 업데이트
- 시스템 상태 점검 및 진단

**실무 팁:**
Run Command는 태그를 사용해 특정 인스턴스 그룹에만 명령을 실행할 수 있다. 예: `Environment=Production` 태그가 있는 인스턴스만 선택.

### Parameter Store

Parameter Store는 애플리케이션 설정값과 민감한 정보를 안전하게 저장하고 관리하는 서비스다.

**핵심 기능:**
- 계층적 파라미터 구조 지원
- KMS를 통한 자동 암호화
- 버전 관리 및 변경 이력 추적
- 다양한 데이터 타입 지원 (String, StringList, SecureString)

**파라미터 타입:**
- String: 일반 텍스트 값
- StringList: 쉼표로 구분된 값 목록
- SecureString: 암호화된 값 (KMS 사용)

**사용 예시:**
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

**보안 모델:**
- IAM 기반의 세밀한 접근 제어
- KMS 키를 통한 암호화된 파라미터 지원
- CloudTrail을 통한 모든 접근 로그 기록
- 네트워크 레벨의 접근 제한

**실무 팁:**
계층적 구조를 사용하면 관리가 쉬워진다. 예: `/myapp/dev/database/password`, `/myapp/prod/database/password`

### Patch Manager

Patch Manager는 운영체제와 애플리케이션의 패치를 자동화하는 기능이다.

**자동화 기능:**
- 운영체제별 패치 정책 설정
- 정기적인 패치 스케줄링
- 패치 전후 상태 검증
- 롤백 기능을 통한 안전한 패치 관리

**패치 정책 유형:**
- Critical: 보안 관련 중요 패치만 적용
- Important: 중요도가 높은 패치 적용
- All: 모든 사용 가능한 패치 적용
- Custom: 사용자 정의 패치 정책

**사용 예시:**
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

**실무 팁:**
프로덕션 환경은 Critical 패치만 자동 적용하고, 나머지는 수동 검토 후 적용하는 게 안전하다.

### State Manager

State Manager는 인스턴스의 상태를 원하는 대로 유지하도록 자동화하는 기능이다.

**상태 관리 원리:**
- 선언적 상태 정의 (Desired State)
- 주기적인 상태 검증 및 수정
- 드리프트 감지 및 자동 복구
- 다양한 상태 관리 도구와의 연동

**사용 예시:**
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

**활용 사례:**
- 소프트웨어 설치 및 버전 관리
- 시스템 설정의 일관성 유지
- 보안 정책의 자동 적용
- 모니터링 에이전트의 상태 관리

**실무 팁:**
State Manager는 주기적으로 상태를 검증한다. 설정이 변경되면 자동으로 원래 상태로 복구한다.

### Inventory

Inventory는 관리 대상 인스턴스의 자산 정보를 자동으로 수집하고 관리하는 기능이다.

**수집 정보:**
- 설치된 소프트웨어 및 버전
- 운영체제 정보 및 패치 상태
- 네트워크 설정 및 보안 그룹
- 하드웨어 사양 및 리소스 사용량

**사용 예시:**
```bash
# 인벤토리 정보 조회
aws ssm get-inventory \
  --instance-id "i-1234567890abcdef0"

# 특정 소프트웨어가 설치된 인스턴스 찾기
aws ssm get-inventory-schema
```

**활용 목적:**
- 자산 인벤토리 관리
- 보안 취약점 분석
- 라이선스 관리
- 규정 준수 감사

**실무 팁:**
Inventory는 주기적으로 자동 수집된다. CloudWatch와 연동해 특정 소프트웨어가 설치된 인스턴스를 찾을 수 있다.

## 아키텍처

### 전체 구조

SSM은 AWS의 마이크로서비스 아키텍처를 기반으로 구축되어 있다. 각 기능은 독립적인 서비스로 구현되어 있다.

**핵심 구성 요소:**
- SSM Service: 중앙 관리 서비스
- SSM Agent: 인스턴스별 에이전트
- IAM: 인증 및 권한 관리
- CloudTrail: 감사 로그 관리
- CloudWatch: 모니터링 및 알림

### 통신 모델

SSM Agent와 AWS SSM 서비스 간의 통신 특징:

**폴링 기반 통신:**
SSM Agent는 주기적으로 AWS SSM 서비스에 연결해 새로운 명령이나 작업이 있는지 확인한다. 방화벽 친화적인 접근 방식이다.

**HTTPS 기반 보안:**
모든 통신은 HTTPS를 통해 암호화된다.

**지역별 엔드포인트:**
각 AWS 리전별로 전용 엔드포인트를 사용해 지연 시간을 최소화한다.

**실무 팁:**
프라이빗 서브넷에서는 VPC 엔드포인트를 사용하면 NAT Gateway 비용을 절감할 수 있다.

### 권한 모델

SSM은 AWS IAM과 통합된 권한 모델을 사용한다.

**인스턴스 프로파일:**
EC2 인스턴스는 IAM 역할을 통해 SSM 서비스에 접근할 수 있는 권한을 가진다.

**필수 IAM 정책:**
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

**사용자 권한:**
SSM 콘솔이나 CLI를 사용하는 사용자는 적절한 IAM 정책을 통해 필요한 권한을 부여받는다.

**최소 권한 원칙:**
각 구성 요소는 최소한의 필요한 권한만을 가지도록 설계되어 있다.

## 실무 활용 전략

### 보안 중심의 접근

**SSH 제거 전략:**
기존의 SSH 기반 접속을 점진적으로 SSM Session Manager로 대체한다. 보안을 향상시키고 운영 복잡성을 줄인다.

**네트워크 보안 강화:**
SSH 포트를 닫고, 모든 서버 접속을 SSM을 통해서만 수행하도록 정책을 수립한다.

**감사 체계 구축:**
CloudTrail과 연동해 모든 SSM 활동을 로깅하고, 정기적인 감사 체계를 구축한다.

**실무 팁:**
보안 그룹에서 SSH 포트(22)를 제거하고, Session Manager만 사용하도록 설정한다.

### 자동화 기반 운영

**패치 관리 자동화:**
Patch Manager를 활용해 정기적인 보안 패치를 자동화하고, 패치 현황을 실시간으로 모니터링한다.

**설정 관리 자동화:**
State Manager를 통해 서버 설정의 일관성을 유지하고, 설정 드리프트를 자동으로 감지하고 수정한다.

**배포 자동화:**
Run Command를 활용해 애플리케이션 배포를 자동화하고, 배포 과정을 추적하고 모니터링한다.

### 비용 최적화

**Bastion Host 제거:**
SSM Session Manager를 사용하면 별도의 Bastion Host가 필요 없어 인프라 비용을 절감한다.

**운영 효율성 향상:**
자동화를 통해 수동 작업을 줄이고, 운영팀의 생산성을 향상시킨다.

**리소스 최적화:**
Inventory 기능을 통해 사용하지 않는 소프트웨어나 리소스를 식별하고 정리한다.

## 도입 시 고려사항

### 기술적 요구사항

**네트워크 연결:**
관리 대상 인스턴스는 AWS SSM 엔드포인트에 접근할 수 있어야 한다. VPC 엔드포인트나 NAT Gateway를 통한 인터넷 접근이 필요하다.

**IAM 권한:**
적절한 IAM 역할과 정책이 설정되어 있어야 한다. 특히 `AmazonSSMManagedInstanceCore` 정책이 필수다.

**SSM Agent:**
모든 관리 대상 인스턴스에 SSM Agent가 설치되고 실행 중이어야 한다.

**확인 방법:**
```bash
# SSM Agent 상태 확인
sudo systemctl status amazon-ssm-agent

# 인스턴스가 SSM에 등록되었는지 확인
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0"
```

### 운영상 고려사항

**점진적 도입:**
모든 서버를 한 번에 SSM으로 전환하는 대신, 단계적으로 도입해 안정성을 확보한다.

**모니터링 체계:**
SSM Agent의 상태를 지속적으로 모니터링하고, 장애 발생 시 빠른 대응 체계를 구축한다.

**백업 계획:**
SSM에 의존하는 환경에서는 대안적인 접근 방법을 준비해둔다.

### 보안 고려사항

**최소 권한 원칙:**
각 사용자와 역할에 최소한의 필요한 권한만을 부여한다.

**정기적인 감사:**
SSM 활동 로그를 정기적으로 검토하고, 비정상적인 활동을 감지한다.

**암호화 정책:**
Parameter Store의 민감한 정보는 반드시 KMS를 통한 암호화를 적용한다.

## 다른 AWS 서비스와의 통합

### CloudWatch 통합

SSM은 CloudWatch와 통합되어 있다.

**메트릭 수집:**
SSM Agent의 상태, 명령 실행 결과 등을 CloudWatch 메트릭으로 수집한다.

**알림 설정:**
SSM 관련 이벤트에 대한 CloudWatch 알림을 설정할 수 있다.

**로그 관리:**
SSM Agent 로그를 CloudWatch Logs로 전송해 중앙 집중식 로그 관리가 가능하다.

### Lambda 통합

SSM Run Command를 Lambda 함수에서 호출해 서버리스 환경에서도 인프라 자동화가 가능하다.

**이벤트 기반 자동화:**
CloudWatch Events나 다른 AWS 서비스의 이벤트에 반응해 자동으로 SSM 명령을 실행할 수 있다.

**스케줄 기반 작업:**
EventBridge를 통해 정기적인 SSM 작업을 스케줄링할 수 있다.

**예시:**
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

**배포 자동화:**
CodePipeline에서 SSM Run Command를 사용해 애플리케이션 배포를 자동화한다.

**설정 관리:**
Parameter Store를 통해 환경별 설정값을 안전하게 관리한다.

## 제한사항

### 기술적 한계

**네트워크 의존성:**
SSM은 AWS 서비스에 대한 네트워크 연결이 필수적이다. 네트워크 장애 시 관리가 어려워진다.

**에이전트 의존성:**
SSM Agent가 설치되지 않은 시스템은 관리할 수 없다.

**지연 시간:**
폴링 기반 통신으로 인해 실시간성이 요구되는 작업에는 적합하지 않을 수 있다.

### 운영상 한계

**학습 곡선:**
기존 SSH 기반 관리에 익숙한 팀에게는 새로운 도구 학습이 필요하다.

**의존성 증가:**
SSM에 대한 의존도가 높아지면, SSM 서비스 장애 시 전체 관리가 어려워질 수 있다.

### 대안 및 보완 방안

**하이브리드 접근:**
중요한 시스템은 SSM과 기존 방식 모두를 지원하도록 구성한다.

**모니터링 강화:**
SSM Agent의 상태를 지속적으로 모니터링하고, 장애 시 대안적 접근 방법을 준비한다.

**문서화:**
SSM 사용법과 트러블슈팅 가이드를 체계적으로 문서화한다.

**실무 팁:**
SSM Agent가 정상 동작하지 않으면 CloudWatch Logs에서 에러 로그를 확인한다. IAM 권한 문제일 가능성이 높다.

## 참고

- AWS Systems Manager 공식 문서: https://docs.aws.amazon.com/systems-manager/
- AWS Systems Manager Best Practices: https://aws.amazon.com/blogs/mt/best-practices-for-aws-systems-manager/
- AWS Parameter Store 활용 가이드: https://aws.amazon.com/blogs/security/how-to-use-parameter-store-secure-string-parameters/
