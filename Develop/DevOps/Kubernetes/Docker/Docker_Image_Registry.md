---
title: Docker 이미지 레지스트리
tags:
  - docker
  - devops
  - backend
  - ci-cd
updated: 2026-09-28
---

# Docker 이미지 레지스트리

레지스트리는 이미지를 저장·배포하는 서버다. Docker Hub가 공식 퍼블릭 레지스트리고, ECR·GCR·Harbor·Nexus 같은 프라이빗 레지스트리를 별도로 운영하기도 한다.

## 이미지 이름 분해하기

`docker pull`에 넣는 이름은 사실 네 조각으로 나뉜다.

```
registry/namespace/name:tag
```

| 조각 | 설명 | 예시 |
|---|---|---|
| registry | 레지스트리 호스트:포트 | `docker.io`, `123456789.dkr.ecr.ap-northeast-2.amazonaws.com` |
| namespace | Docker Hub에서는 계정명 | `library`, `myteam` |
| name | 이미지 이름 | `nginx`, `api-server` |
| tag | 버전 식별자 | `1.25.3`, `main-abc1234` |

`nginx:1.25.3`을 pull하면 실제로는 `docker.io/library/nginx:1.25.3`이다. Docker CLI가 앞 두 조각을 기본값으로 채운다.

ECR 이미지는 형태가 다르다. namespace 개념이 없고 레지스트리 호스트에 AWS 계정 ID가 들어간다.

```
123456789.dkr.ecr.ap-northeast-2.amazonaws.com/api-server:1.2.0
```

`docker tag`로 이미지에 다른 이름을 붙일 때 이 구조를 모르면 실수가 잦다. push 대상 레지스트리 주소를 이미지 이름 앞에 붙여야 한다는 걸 놓치는 경우가 많다.

## Docker Hub push/pull

로그인부터 한다.

```bash
docker login
# Username: myaccount
# Password:
```

자격증명은 `~/.docker/config.json`에 base64로 저장된다. macOS·Windows에서는 OS의 Keychain/Credential Manager가 대신 처리한다.

이미지를 빌드하고 push하는 순서:

```bash
# 빌드할 때 바로 레지스트리 이름까지 붙여서 태그한다
docker build -t myaccount/api-server:1.0.0 .

# push
docker push myaccount/api-server:1.0.0

# 다른 머신에서 pull
docker pull myaccount/api-server:1.0.0
```

이미 빌드된 이미지에 이름을 추가하려면 `docker tag`를 쓴다.

```bash
docker tag api-server:local myaccount/api-server:1.0.0
docker push myaccount/api-server:1.0.0
```

`docker tag`는 이미지를 복사하지 않는다. 동일한 이미지 레이어에 이름표만 하나 더 붙이는 동작이라 디스크 공간은 늘지 않는다.

## 태그 컨벤션

태그 제약이 거의 없어서(`/`와 일부 특수문자 제외) 팀마다 관행이 다르다. 실무에서 자주 보이는 세 가지 패턴이다.

**시맨틱 버저닝**

릴리스 주기가 명확할 때 쓴다. `major.minor.patch` 형태로 붙이고, minor·major 태그는 항상 최신 patch를 가리키도록 덮어쓰는 팀이 많다.

```bash
docker tag api-server:1.2.3 myrepo/api-server:1.2.3
docker tag api-server:1.2.3 myrepo/api-server:1.2   # 덮어씀
docker tag api-server:1.2.3 myrepo/api-server:1      # 덮어씀
```

minor·major 태그는 편하지만 mutable이라 재현성이 없다.

**커밋 해시 기반**

CI/CD에서 가장 많이 쓰는 방식이다. 어느 커밋으로 빌드했는지 태그만 보고 바로 추적이 된다. GitHub Actions 기준:

```yaml
- name: Build and push
  run: |
    SHORT_SHA="${GITHUB_SHA::8}"
    IMAGE_TAG="${GITHUB_REF_NAME}-${SHORT_SHA}"
    docker build -t myrepo/api-server:${IMAGE_TAG} .
    docker push myrepo/api-server:${IMAGE_TAG}
```

`${{ github.sha }}`가 40자라 태그가 길어져서 앞 8자만 쓰는 경우가 많다. 충돌 확률은 무시해도 되는 수준이다.

**환경 기반**

```
api-server:staging
api-server:production
```

staging 검증 후 production 태그를 덮어쓰는 방식이다. 현재 production에 뭐가 올라가 있는지 명확하지만, 변경 이력 추적은 어렵다.

## latest 태그 함정

`latest`는 특별한 기능이 없다. `docker pull nginx`처럼 태그 없이 pull하면 레지스트리가 `latest` 태그를 찾는 것뿐이다. 그 외엔 그냥 문자열 "latest"다.

문제는 `latest`가 mutable하다는 점이다. push할 때마다 덮어써진다.

```bash
# 1차 배포: v1.0이 latest
docker push myrepo/api-server:latest

# 다음날 2차 배포: v1.1이 latest로 덮어써짐
docker push myrepo/api-server:latest
```

서버 두 대 중 한 대만 재시작했을 때, 한 대는 v1.0, 다른 한 대는 v1.1이 뜨는 상황이 생긴다. 더 자주 겪는 문제는 `latest`로만 배포하다가 이전 버전으로 롤백할 방법이 없어지는 거다. 이전 `latest`는 이미 덮어써졌으니까.

배포 manifest에 쓰는 태그는 immutable이어야 한다.

```yaml
# bad
image: myrepo/api-server:latest

# good
image: myrepo/api-server:1.2.3
image: myrepo/api-server:main-a3f1b2c
```

`latest`를 아예 쓰지 않는 팀도 있고, 커밋 해시 태그와 병행하는 팀도 있다. 어느 쪽이든 배포에는 immutable 태그를 쓴다.

## digest 고정이 필요한 이유

태그는 mutable이다. `nginx:1.25.3`이라도 레지스트리에 같은 태그로 다른 이미지를 push하면 내용이 바뀐다. Docker Hub 공식 이미지는 거의 그런 일이 없지만, 서드파티 이미지나 자체 프라이빗 레지스트리는 다르다.

완전한 재현성이 필요하면 digest를 쓴다. digest는 이미지 manifest의 SHA256이라 내용이 바뀌면 반드시 달라진다.

```bash
# 이미지의 digest 확인
docker inspect --format='{{index .RepoDigests 0}}' nginx:1.25.3
# nginx@sha256:abc123def456...

# digest로 pull
docker pull nginx@sha256:abc123def456...
```

Kubernetes manifest에도 쓸 수 있다.

```yaml
image: nginx@sha256:abc123def456...
```

관리가 불편한 건 감수해야 한다. digest는 플랫폼(amd64/arm64)마다 다르고, 보안 패치로 이미지가 업데이트되면 digest도 바뀐다. 의존성 업데이트를 수동으로 추적해야 한다.

실제로 digest 고정을 쓰는 곳은 보안 요구사항이 엄격한 금융·공공 환경, supply chain 공격 방지가 중요한 CI 빌더 이미지 정도다. 일반 서비스 배포에 강제하면 운영 부담이 크다.

## 프라이빗 레지스트리 인증 흐름

Docker CLI가 레지스트리에 접근하는 흐름이다.

```
1. docker pull registry.example.com/myapp:1.0.0
2. CLI → registry에 HTTP 요청
3. registry → 401 Unauthorized + WWW-Authenticate 헤더 반환
4. CLI → 헤더에 명시된 auth 서버에 토큰 요청 (자격증명 포함)
5. auth 서버 → JWT 발급
6. CLI → 토큰을 Authorization 헤더에 넣고 레이어 pull
```

`docker login registry.example.com`을 미리 실행해두면 자격증명이 `~/.docker/config.json`에 저장되고, 이후 pull/push 시 4단계에서 이걸 꺼내 쓴다.

Harbor 같은 self-hosted 레지스트리는 이 표준 흐름을 그대로 구현한다. `docker login harbor.mycompany.com`으로 로그인한다.

Kubernetes에서 프라이빗 레지스트리 이미지를 pull하려면 imagePullSecret이 필요하다.

```bash
kubectl create secret docker-registry regcred \
  --docker-server=registry.example.com \
  --docker-username=myuser \
  --docker-password=mypassword
```

```yaml
spec:
  imagePullSecrets:
    - name: regcred
  containers:
    - name: app
      image: registry.example.com/myapp:1.0.0
```

ECR·GCR처럼 단기 토큰을 사용하는 레지스트리는 토큰 만료가 문제다. ECR 토큰은 12시간이라 갱신하지 않으면 그 이후 pull이 실패한다. 장기 운영 클러스터에서는 토큰 갱신 자동화가 필요하다.

## ECR 로그인

ECR은 AWS IAM으로 인증한다. `docker login`에 쓸 토큰을 AWS CLI로 가져와야 한다.

```bash
aws ecr get-login-password --region ap-northeast-2 \
  | docker login --username AWS --password-stdin \
    123456789.dkr.ecr.ap-northeast-2.amazonaws.com
```

`get-login-password`는 12시간짜리 토큰을 stdout으로 출력한다. `--username AWS`는 ECR에서 요구하는 고정값이다.

이후 push 순서:

```bash
# 로컬 이미지에 ECR 태그 붙이기
docker tag myapp:1.0.0 \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:1.0.0

# push
docker push \
  123456789.dkr.ecr.ap-northeast-2.amazonaws.com/myapp:1.0.0
```

ECR 리포지토리는 push 전에 미리 만들어야 한다. Docker Hub와 달리 없는 리포지토리에 push하면 에러가 난다.

```bash
aws ecr create-repository \
  --repository-name myapp \
  --region ap-northeast-2
```

CI/CD에서 ECR을 쓸 때 주의할 점 두 가지가 있다.

GitHub Actions라면 `aws-actions/configure-aws-credentials`와 `aws-actions/amazon-ecr-login` 액션을 쓰는 게 낫다. 직접 `aws ecr get-login-password`를 스크립트에 넣으면 토큰이 로그에 노출될 수 있다.

lifecycle policy를 설정하지 않으면 이미지가 무한정 쌓인다. CI 빌드마다 push하면 몇 달 후 수천 개가 된다.

```bash
# 30일 이상 된 이미지 삭제하는 lifecycle policy
aws ecr put-lifecycle-policy \
  --repository-name myapp \
  --lifecycle-policy-text '{
    "rules": [{
      "rulePriority": 1,
      "selection": {
        "tagStatus": "any",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 30
      },
      "action": {"type": "expire"}
    }]
  }'
```
