---
title: AWS CodeCommit
tags: [aws, codecommit, git, repository, version-control, scm]
updated: 2026-01-18
---

# AWS CodeCommit

## 개요

CodeCommit은 Git 저장소 서비스다. GitHub, GitLab, Bitbucket과 비슷하다. AWS 계정 내에서 프라이빗 저장소를 호스팅한다. IAM으로 접근을 제어한다. CodePipeline, CodeBuild와 완벽하게 통합된다.

### 왜 필요한가

대부분 팀은 GitHub나 GitLab을 사용한다. CodeCommit을 굳이 사용할 이유가 있나?

**CodeCommit을 선택하는 경우:**

**1. AWS 종속 환경**
모든 인프라가 AWS다. 외부 서비스를 추가하고 싶지 않다.

**2. IAM 기반 권한**
GitHub Organizations보다 세밀한 권한 제어가 필요하다.

**3. 감사 추적**
CloudTrail로 모든 Git 작업을 추적한다. 금융, 의료 등 규제 산업.

**4. 비용**
저장소 개수 제한 없음. 사용자 5명까지 무료.

**하지만 대부분은 GitHub/GitLab을 사용한다:**
- UI가 좋다
- Pull Request 리뷰 기능이 강력하다
- 커뮤니티가 크다
- CI/CD 도구가 풍부하다 (GitHub Actions, GitLab CI)

**CodeCommit의 한계:**
- UI가 기본적
- Pull Request 기능 제한적
- Code Review 불편
- Issue Tracker 없음

## GitHub vs CodeCommit

| 항목 | GitHub | CodeCommit |
|------|--------|------------|
| 가격 | Public 무료, Private $4/월 | 5 users 무료, 추가 $1/월 |
| 저장소 제한 | 무제한 | 무제한 |
| UI | 우수 | 기본적 |
| Pull Request | 강력 | 제한적 |
| Code Review | 좋음 | 불편 |
| CI/CD | Actions, 다양한 통합 | CodePipeline, CodeBuild |
| 권한 관리 | Organizations | IAM |
| 감사 | GitHub Audit Log | CloudTrail |
| 커뮤니티 | 매우 큼 | 작음 |

**추천:**
- **일반 프로젝트**: GitHub/GitLab
- **AWS 올인, 규제 산업**: CodeCommit

## 저장소 생성

### 콘솔

1. CodeCommit 콘솔
2. "Create repository"
3. 이름: my-app
4. 설명: My Application Repository
5. 태그 추가 (선택)
6. 생성

### CLI

```bash
aws codecommit create-repository \
  --repository-name my-app \
  --repository-description "My Application Repository"
```

### Clone

**HTTPS:**
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

**SSH:**
```bash
git clone ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

## 인증 설정

### HTTPS (Git Credentials)

**IAM 사용자 생성:**
1. IAM 콘솔
2. Users → Create user
3. 이름: git-user
4. Access type: Programmatic access (선택 해제)
5. Attach policy: AWSCodeCommitPowerUser
6. 생성

**Git Credentials 생성:**
1. IAM 사용자 선택
2. "Security credentials" 탭
3. "HTTPS Git credentials for AWS CodeCommit"
4. "Generate credentials"
5. Username과 Password 저장

**Clone:**
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
Username: git-user-at-123456789012
Password: <generated-password>
```

### SSH

**SSH 키 생성:**
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

**Public Key 업로드:**
1. IAM 사용자 선택
2. "Security credentials" 탭
3. "SSH keys for AWS CodeCommit"
4. "Upload SSH public key"
5. `~/.ssh/id_rsa.pub` 내용 붙여넣기
6. SSH Key ID 저장 (APKA...)

**SSH Config 설정:**
```bash
vi ~/.ssh/config
```

```
Host git-codecommit.*.amazonaws.com
  User APKAEXAMPLEKEYID
  IdentityFile ~/.ssh/id_rsa
```

**Clone:**
```bash
git clone ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

### AWS CLI Credential Helper (권장)

**설정:**
```bash
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
```

**Clone:**
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

AWS CLI의 자격 증명을 자동으로 사용한다. 가장 편하다.

## 기본 Git 작업

CodeCommit은 표준 Git이다. 일반 Git 명령을 사용한다.

**Clone:**
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
cd my-app
```

**Commit:**
```bash
echo "# My App" > README.md
git add README.md
git commit -m "Add README"
```

**Push:**
```bash
git push origin main
```

**Branch:**
```bash
git checkout -b feature/new-feature
git push origin feature/new-feature
```

## Pull Request

### 생성

**콘솔:**
1. CodeCommit 콘솔
2. Repositories → my-app
3. "Pull requests" 탭
4. "Create pull request"
5. Source: feature/new-feature
6. Destination: main
7. 제목과 설명 작성
8. 생성

**CLI:**
```bash
aws codecommit create-pull-request \
  --title "Add new feature" \
  --description "This PR adds a new feature" \
  --targets repositoryName=my-app,sourceReference=feature/new-feature,destinationReference=main
```

### 코드 리뷰

**댓글 작성:**
1. Pull Request 선택
2. "Changes" 탭
3. 줄 번호 클릭
4. 댓글 작성

**승인:**
1. Pull Request 선택
2. "Approve" 클릭

### 병합

**콘솔:**
1. Pull Request 선택
2. "Merge" 클릭
3. 병합 전략 선택:
   - Fast forward
   - Squash
   - Three-way

**CLI:**
```bash
aws codecommit merge-pull-request-by-fast-forward \
  --pull-request-id 1 \
  --repository-name my-app
```

## 승인 규칙

Pull Request 병합 전에 승인을 요구한다.

**규칙 생성:**
```bash
aws codecommit create-pull-request-approval-rule \
  --pull-request-id 1 \
  --approval-rule-name "Require 2 approvals" \
  --approval-rule-content '{
    "Version": "2018-11-08",
    "DestinationReferences": ["refs/heads/main"],
    "Statements": [{
      "Type": "Approvers",
      "NumberOfApprovalsNeeded": 2,
      "ApprovalPoolMembers": [
        "arn:aws:iam::123456789012:user/senior-dev-1",
        "arn:aws:iam::123456789012:user/senior-dev-2"
      ]
    }]
  }'
```

**동작:**
- main 브랜치로 병합하려면 2명 승인 필요
- senior-dev-1 또는 senior-dev-2만 승인 가능

## Triggers

Git 이벤트 발생 시 알림을 보낸다.

### SNS 트리거

**생성:**
1. CodeCommit 콘솔
2. Repositories → my-app
3. "Settings" → "Triggers"
4. "Create trigger"
5. 이름: notify-on-push
6. Events: Push to existing branch
7. Branch: main
8. SNS topic: code-commit-notifications
9. 생성

**동작:**
main 브랜치에 push 시 SNS 알림.

### Lambda 트리거

**생성:**
```bash
aws codecommit put-repository-triggers \
  --repository-name my-app \
  --triggers '[
    {
      "name": "run-tests",
      "destinationArn": "arn:aws:lambda:us-west-2:123456789012:function:run-tests",
      "events": ["all"]
    }
  ]'
```

**Lambda 함수:**
```python
import json

def lambda_handler(event, context):
    for record in event['Records']:
        region = record['awsRegion']
        repo_name = record['eventSourceARN'].split(':')[-1]
        references = record['codecommit']['references']
        
        for ref in references:
            commit = ref['commit']
            branch = ref['ref'].split('/')[-1]
            
            print(f"Push to {repo_name}/{branch}: {commit}")
            
            # 테스트 실행, Slack 알림 등
```

## Notifications

EventBridge를 통해 알림을 보낸다.

**EventBridge Rule:**
```json
{
  "source": ["aws.codecommit"],
  "detail-type": ["CodeCommit Repository State Change"],
  "detail": {
    "event": ["referenceCreated", "referenceUpdated"],
    "referenceType": ["branch"],
    "referenceName": ["main"]
  }
}
```

**Slack 통합:**
```python
import urllib.request
import json

def lambda_handler(event, context):
    detail = event['detail']
    repo = detail['repositoryName']
    branch = detail['referenceName']
    commit = detail['commitId']
    
    message = {
        "text": f"📝 Push to {repo}/{branch}\nCommit: {commit[:7]}"
    }
    
    req = urllib.request.Request(
        "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        data=json.dumps(message).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    urllib.request.urlopen(req)
```

## 브랜치 보호

특정 브랜치를 보호한다.

**IAM 정책:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": [
        "codecommit:GitPush",
        "codecommit:DeleteBranch",
        "codecommit:PutFile",
        "codecommit:MergeBranchesByFastForward"
      ],
      "Resource": "arn:aws:codecommit:us-west-2:123456789012:my-app",
      "Condition": {
        "StringEqualsIfExists": {
          "codecommit:References": [
            "refs/heads/main",
            "refs/heads/production"
          ]
        }
      }
    }
  ]
}
```

**동작:**
- main, production 브랜치에 직접 push 불가
- Pull Request를 통해서만 병합 가능

## 모니터링

### CloudTrail

모든 CodeCommit API 호출을 기록한다.

**이벤트:**
- CreateRepository
- DeleteRepository
- CreateBranch
- DeleteBranch
- GitPush
- MergePullRequestByFastForward

**쿼리 (CloudTrail Lake):**
```sql
SELECT
  eventTime,
  userIdentity.principalId,
  eventName,
  requestParameters.repositoryName,
  requestParameters.branchName
FROM events
WHERE eventSource = 'codecommit.amazonaws.com'
  AND eventName = 'GitPush'
  AND eventTime > '2026-01-01'
```

누가, 언제, 어떤 작업을 했는지 추적한다.

## 마이그레이션

### GitHub → CodeCommit

**1. GitHub 저장소 Clone (Mirror):**
```bash
git clone --mirror https://github.com/my-org/my-app.git
cd my-app.git
```

**2. CodeCommit 저장소 생성:**
```bash
aws codecommit create-repository --repository-name my-app
```

**3. Push:**
```bash
git push https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app --all
git push https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app --tags
```

**4. 검증:**
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
cd my-app
git log --oneline
```

### CodeCommit → GitHub

반대로도 동일하게 진행한다.

```bash
git clone --mirror https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
cd my-app.git
git push https://github.com/my-org/my-app.git --all
git push https://github.com/my-org/my-app.git --tags
```

## 비용

### 무료 티어

**매월:**
- Active users: 5명
- 스토리지: 50 GB
- Git requests: 10,000개

**Active user:**
매월 한 번이라도 Git 작업을 한 AWS 사용자.

### 유료

**Active users:**
$1.00 per additional active user per month

**스토리지:**
$0.06 per GB-month (50 GB 초과)

**Git requests:**
$0.001 per request (10,000 초과)

### 예시

**팀 구성:**
- 개발자 10명
- 저장소 크기: 2 GB
- 월 Git requests: 50,000개

**비용:**
- Active users: (10 - 5) × $1 = $5
- 스토리지: 2 GB < 50 GB → 무료
- Git requests: (50,000 - 10,000) × $0.001 = $40
- 합계: $45/월

**GitHub Teams ($4/user):**
10 × $4 = $40/월

비슷한 수준.

## 실무 팁

### CodeCommit을 사용하는 경우

**1. AWS 완전 종속:**
모든 인프라가 AWS다. 외부 의존성을 최소화하고 싶다.

**2. 규제 산업:**
금융, 의료 등. 모든 작업 추적이 필요하다 (CloudTrail).

**3. 세밀한 권한 제어:**
IAM Policy로 브랜치별, 작업별 권한을 세밀하게 제어한다.

### GitHub를 사용하는 경우

**1. 협업 중심:**
Pull Request 리뷰, Issue Tracker, Project Board 필요.

**2. 오픈소스:**
Public 저장소, 커뮤니티 기여.

**3. 풍부한 통합:**
GitHub Actions, 다양한 CI/CD 도구.

### 혼합 사용

**소스는 GitHub, 배포는 CodePipeline:**
- GitHub에서 개발
- CodePipeline이 GitHub 감지
- CodeBuild로 빌드
- CodeDeploy로 배포

**장점:**
- GitHub의 강력한 협업 기능
- AWS 서비스와 원활한 통합

## 참고

- CodeCommit 개발자 가이드: https://docs.aws.amazon.com/codecommit/
- CodeCommit 요금: https://aws.amazon.com/codecommit/pricing/
- IAM Policies: https://docs.aws.amazon.com/codecommit/latest/userguide/auth-and-access-control.html
- GitHub vs CodeCommit: https://aws.amazon.com/blogs/devops/

