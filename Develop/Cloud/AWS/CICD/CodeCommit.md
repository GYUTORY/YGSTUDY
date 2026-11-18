---
title: AWS CodeCommit
tags: [aws, git, cloud]
updated: 2026-11-18
---

# AWS CodeCommit

## 개요

CodeCommit은 Git 저장소 서비스다. GitHub, GitLab, Bitbucket과 비슷하다. AWS 계정 내에서 프라이빗 저장소를 호스팅한다. IAM으로 접근을 제어한다. CodePipeline, CodeBuild와 연동된다.

### 왜 필요한가

대부분 팀은 GitHub나 GitLab을 사용한다. CodeCommit을 굳이 사용할 이유가 있나?

CodeCommit을 선택하는 이유는 네 가지다.

모든 인프라가 AWS여서 외부 서비스를 추가하고 싶지 않은 경우다.

IAM 기반 권한이 필요한 경우다. GitHub Organizations보다 세밀한 권한 제어가 필요할 때 해당한다.

감사 추적이 필요한 경우다. CloudTrail로 모든 Git 작업을 추적한다. 금융, 의료 등 규제 산업이 여기에 든다.

비용 때문인 경우다. 저장소 개수 제한이 없고 사용자 5명까지 무료다.

하지만 대부분은 GitHub/GitLab을 사용한다. 이유는 네 가지다.
- UI가 좋다
- Pull Request 리뷰 기능이 낫다
- 커뮤니티가 크다
- CI/CD 도구가 풍부하다 (GitHub Actions, GitLab CI)

CodeCommit은 한계도 뚜렷하다.
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

프로젝트 성격에 따라 고른다.
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

HTTPS로 clone한다.
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

SSH로 clone한다.
```bash
git clone ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

## 인증 설정

### HTTPS (Git Credentials)

IAM 사용자를 만든다.
1. IAM 콘솔
2. Users → Create user
3. 이름: git-user
4. Access type: Programmatic access (선택 해제)
5. Attach policy: AWSCodeCommitPowerUser
6. 생성

만든 사용자에서 Git Credentials를 생성한다.
1. IAM 사용자 선택
2. "Security credentials" 탭
3. "HTTPS Git credentials for AWS CodeCommit"
4. "Generate credentials"
5. Username과 Password 저장

생성한 자격 증명으로 clone한다.
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
Username: git-user-at-123456789012
Password: <generated-password>
```

### SSH

SSH 키를 생성한다.
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

Public Key를 IAM 사용자에 업로드한다.
1. IAM 사용자 선택
2. "Security credentials" 탭
3. "SSH keys for AWS CodeCommit"
4. "Upload SSH public key"
5. `~/.ssh/id_rsa.pub` 내용 붙여넣기
6. SSH Key ID 저장 (APKA...)

SSH Config를 설정한다.
```bash
vi ~/.ssh/config
```

```
Host git-codecommit.*.amazonaws.com
  User APKAEXAMPLEKEYID
  IdentityFile ~/.ssh/id_rsa
```

키 등록 후 clone한다.
```bash
git clone ssh://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

### AWS CLI Credential Helper (권장)

credential helper를 설정한다.
```bash
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
```

설정 후에는 별도 입력 없이 clone한다.
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
```

AWS CLI의 자격 증명을 자동으로 사용한다. 가장 편하다.

## 기본 Git 작업

CodeCommit은 표준 Git이다. 일반 Git 명령을 사용한다.

저장소를 clone한다.
```bash
git clone https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app
cd my-app
```

파일을 커밋한다.
```bash
echo "# My App" > README.md
git add README.md
git commit -m "Add README"
```

main에 push한다.
```bash
git push origin main
```

브랜치를 만들어 push한다.
```bash
git checkout -b feature/new-feature
git push origin feature/new-feature
```

## Pull Request

### 생성

콘솔에서는 이 순서로 만든다.
1. CodeCommit 콘솔
2. Repositories → my-app
3. "Pull requests" 탭
4. "Create pull request"
5. Source: feature/new-feature
6. Destination: main
7. 제목과 설명 작성
8. 생성

CLI로도 만들 수 있다.
```bash
aws codecommit create-pull-request \
  --title "Add new feature" \
  --description "This PR adds a new feature" \
  --targets repositoryName=my-app,sourceReference=feature/new-feature,destinationReference=main
```

### 코드 리뷰

댓글은 이 순서로 작성한다.
1. Pull Request 선택
2. "Changes" 탭
3. 줄 번호 클릭
4. 댓글 작성

승인은 이 순서로 한다.
1. Pull Request 선택
2. "Approve" 클릭

### 병합

콘솔에서 병합한다.
1. Pull Request 선택
2. "Merge" 클릭
3. 병합 전략 선택:
   - Fast forward
   - Squash
   - Three-way

CLI로는 fast forward 병합을 실행한다.
```bash
aws codecommit merge-pull-request-by-fast-forward \
  --pull-request-id 1 \
  --repository-name my-app
```

## 승인 규칙

Pull Request 병합 전에 승인을 요구한다.

승인 규칙은 CLI로 만든다.
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

이 규칙을 걸면 두 가지가 적용된다.
- main 브랜치로 병합하려면 2명 승인 필요
- senior-dev-1 또는 senior-dev-2만 승인 가능

## Triggers

Git 이벤트 발생 시 알림을 보낸다.

### SNS 트리거

콘솔에서 트리거를 만든다.
1. CodeCommit 콘솔
2. Repositories → my-app
3. "Settings" → "Triggers"
4. "Create trigger"
5. 이름: notify-on-push
6. Events: Push to existing branch
7. Branch: main
8. SNS topic: code-commit-notifications
9. 생성

main 브랜치에 push 시 SNS 알림.

### Lambda 트리거

CLI로 트리거를 만든다.
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

Lambda 함수는 push된 저장소, 브랜치, 커밋을 읽는다.
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

EventBridge로 알림을 보낸다.

EventBridge 규칙은 main 브랜치의 참조 생성·갱신 이벤트를 잡는다.
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

Slack 알림은 Lambda에서 웹훅을 호출해 보낸다.
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

IAM 정책으로 막는다.
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

정책을 붙이면 두 가지가 달라진다.
- main, production 브랜치에 직접 push 불가
- Pull Request로만 병합 가능

## 모니터링

### CloudTrail

모든 CodeCommit API 호출을 기록한다.

기록되는 이벤트 중 주요한 것들이다.
- CreateRepository
- DeleteRepository
- CreateBranch
- DeleteBranch
- GitPush
- MergePullRequestByFastForward

CloudTrail Lake에서는 SQL로 조회한다.
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

먼저 GitHub 저장소를 mirror로 clone한다.
```bash
git clone --mirror https://github.com/my-org/my-app.git
cd my-app.git
```

CodeCommit 저장소를 만든다.
```bash
aws codecommit create-repository --repository-name my-app
```

모든 브랜치와 태그를 push한다.
```bash
git push https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app --all
git push https://git-codecommit.us-west-2.amazonaws.com/v1/repos/my-app --tags
```

clone해서 이력을 확인한다.
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

무료 티어는 매월 아래 한도까지 제공된다.
- Active users: 5명
- 스토리지: 50 GB
- Git requests: 10,000개

Active user는 매월 한 번이라도 Git 작업을 한 AWS 사용자다.

### 유료

Active users는 추가 사용자당 월 $1.00다.

스토리지는 50 GB 초과분에 GB-월당 $0.06이다.

Git requests는 10,000개 초과분에 요청당 $0.001이다.

### 예시

예시로 아래 팀을 가정한다.
- 개발자 10명
- 저장소 크기: 2 GB
- 월 Git requests: 50,000개

월 비용은 이렇게 계산된다.
- Active users: (10 - 5) × $1 = $5
- 스토리지: 2 GB < 50 GB → 무료
- Git requests: (50,000 - 10,000) × $0.001 = $40
- 합계: $45/월

GitHub Teams($4/user)는 10 × $4 = $40/월이다.

비슷한 수준.

## 실무 팁

### CodeCommit을 사용하는 경우

모든 인프라가 AWS여서 외부 의존성을 최소화하고 싶을 때 쓴다.

금융, 의료 등 규제 산업에서 모든 작업을 CloudTrail로 추적해야 할 때 쓴다.

IAM Policy로 브랜치별, 작업별 권한을 세밀하게 제어해야 할 때 쓴다.

### GitHub를 사용하는 경우

Pull Request 리뷰, Issue Tracker, Project Board가 필요한 협업 중심 팀은 GitHub를 쓴다.

Public 저장소로 커뮤니티 기여를 받는 오픈소스는 GitHub를 쓴다.

GitHub Actions 같은 CI/CD 도구와 연동해야 하면 GitHub를 쓴다.

### 혼합 사용

소스는 GitHub에 두고 배포는 CodePipeline으로 하는 구성도 있다.
- GitHub에서 개발
- CodePipeline이 GitHub 감지
- CodeBuild로 빌드
- CodeDeploy로 배포

이 구성의 장점은 두 가지다.
- GitHub의 협업 기능
- AWS 서비스와의 연동

## 참고

- CodeCommit 개발자 가이드: https://docs.aws.amazon.com/codecommit/
- CodeCommit 요금: https://aws.amazon.com/codecommit/pricing/
- IAM Policies: https://docs.aws.amazon.com/codecommit/latest/userguide/auth-and-access-control.html
- GitHub vs CodeCommit: https://aws.amazon.com/blogs/devops/

