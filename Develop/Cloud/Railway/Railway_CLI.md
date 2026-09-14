---
title: Railway CLI 실무 사용법
tags: [cloud, devops, ci-cd, backend]
updated: 2026-09-14
---

# Railway CLI 실무 사용법

Railway 대시보드에서 할 수 있는 거의 모든 작업을 CLI로 처리할 수 있다. 로그 확인, 환경변수 주입, 배포 트리거까지. 대시보드를 열지 않고 터미널에서 끝내는 작업이 훨씬 빠를 때가 많다.

## 설치와 로그인

```bash
# npm
npm install -g @railway/cli

# brew (macOS)
brew install railway
```

설치 후 로그인은 두 가지 방식이다.

```bash
railway login
```

브라우저가 열리면서 OAuth 인증을 처리한다. 로컬 개발 환경에서 쓰는 방식이다. 인증 토큰은 `~/.railway/config.json`에 저장된다.

CI 환경처럼 브라우저가 없는 경우는 `RAILWAY_TOKEN`을 환경변수로 넘기면 `railway login` 없이 동작한다. 이건 뒤에서 따로 다룬다.

현재 어떤 계정으로 로그인됐는지 확인할 때:

```bash
railway whoami
```

출력 예:

```
Logged in as user@example.com (Workspace: my-workspace)
```

여러 Railway 계정을 쓰는 경우 — 회사 계정과 개인 계정을 번갈아 쓰다 보면 현재 어느 계정인지 모르고 커맨드를 날리는 경우가 생긴다. 배포 전에 `railway whoami`로 계정을 확인하는 게 낫다.

로그아웃:

```bash
railway logout
```

`~/.railway/config.json`에서 토큰이 삭제된다. 다른 계정으로 전환할 때 `railway logout` → `railway login` 순서로 한다.

## 프로젝트 탐색

로그인된 계정에 속한 프로젝트 전체를 보려면:

```bash
railway list
```

출력 예:

```
 Projects
 ─────────────────────────────────
 my-api-service          (3 services)
 data-pipeline           (2 services)
 staging-env             (4 services)
```

현재 디렉토리가 연결된 프로젝트가 뭔지 모를 때, 또는 처음 합류한 팀 계정에서 어떤 프로젝트들이 있는지 파악할 때 쓴다.

현재 프로젝트를 브라우저에서 바로 열려면:

```bash
railway open
```

Railway 대시보드의 현재 프로젝트 페이지가 브라우저에서 열린다. 로그 보다가 대시보드로 넘어가야 할 때, 팀원에게 링크를 보내야 할 때 바로 쓸 수 있다.

## 프로젝트 연결

Railway CLI는 현재 디렉토리가 어떤 프로젝트·서비스·환경에 연결됐는지를 기준으로 동작한다.

```bash
# 새 프로젝트 생성 또는 기존 프로젝트 연결
railway init

# 이미 Railway에 올라간 프로젝트를 로컬 레포에 연결
railway link
```

`railway init`은 대화형 프롬프트로 프로젝트를 선택하거나 새로 만든다. 이 과정에서 `.railway` 디렉토리 또는 `railway.json` 파일이 생긴다. 이 파일에 projectId와 environmentId가 박혀 있어서 이후 커맨드들이 어느 프로젝트를 대상으로 할지 알 수 있다.

`railway link`는 이미 존재하는 프로젝트에 현재 레포를 연결할 때 쓴다. 프로젝트를 선택하면 서비스, 환경까지 지정할 수 있다.

현재 연결 상태를 확인하는 방법:

```bash
railway status
```

출력에 Project, Environment, Service가 뜨면 연결된 것이다. 아무것도 안 뜨면 `railway link`부터 해야 한다.

## 배포

```bash
railway up
```

현재 디렉토리를 Railway에 올린다. GitHub 연동 없이 직접 소스를 밀어 올리는 방식이다. `.gitignore`에 지정된 파일은 제외된다.

`railway up`은 GitHub 자동 배포와 별개로 작동한다. 로컬에서 빠르게 테스트하거나 GitHub에 올리기 전에 Railway 환경을 먼저 확인해야 할 때 쓴다. 단, 이렇게 올린 배포는 GitHub 레포와 연결되지 않아서 롤백 기록에 남지 않는다.

배포할 서비스를 명시하려면:

```bash
railway up --service api-server
```

프로젝트에 서비스가 여러 개면 `--service` 없이 `railway up`을 치면 어느 서비스에 올릴지 물어본다. CI에서 쓸 때는 반드시 `--service`를 명시해야 한다. 대화형 프롬프트가 뜨면 파이프라인이 멈추기 때문이다.

## 로그 확인

```bash
railway logs
```

현재 연결된 서비스의 로그를 실시간으로 스트리밍한다. 기본은 최신 배포의 로그다.

```bash
# 이전 배포 로그
railway logs --deployment <deploymentId>

# 빌드 로그만
railway logs --build

# 특정 서비스 로그
railway logs --service worker
```

`railway logs`는 대시보드 로그보다 검색하기 편하다. 터미널에서 `grep`으로 필터링할 수 있어서 에러 패턴을 찾을 때 더 빠르다.

```bash
railway logs --service api-server | grep "ERROR"
```

## 컨테이너 직접 접속

배포된 컨테이너 안으로 직접 들어갈 때 쓴다.

```bash
railway shell
```

현재 연결된 서비스의 컨테이너에 대화형 셸이 붙는다. 컨테이너 안에서 실행되기 때문에 Railway에 등록된 환경변수가 전부 주입된 상태다.

어느 서비스에 접속할지 명시하려면:

```bash
railway shell --service api-server
```

주로 이런 경우에 쓴다:

- 배포 후 예상치 못한 동작이 나올 때 컨테이너 안 파일 시스템이나 프로세스 상태를 직접 확인
- 마이그레이션이나 일회성 스크립트를 대화형으로 돌려야 할 때
- 컨테이너 안 특정 바이너리나 설정 파일 위치 확인

한 가지 제약이 있다. Railway 컨테이너는 기본적으로 `bash`가 없는 경우가 많다. alpine 기반 이미지면 `sh`만 있고, 일부 distroless 이미지는 셸 자체가 없다. 접속이 안 된다면 Dockerfile을 확인해야 한다.

`railway shell`로 들어가서 작업한 내용은 컨테이너가 재시작되면 전부 사라진다. 파일을 직접 수정하는 건 디버깅용으로만 써야 한다. 실제 변경은 소스 코드에 반영해서 재배포하는 게 맞다.

## 로컬에서 Railway 환경변수 주입

Railway에 등록된 환경변수를 로컬 프로세스에 주입해서 실행하는 게 `railway run`이다.

```bash
railway run node src/index.js
railway run npm run dev
railway run python manage.py runserver
```

로컬 `.env`와 Railway 환경변수를 따로 관리하지 않아도 된다. Railway 대시보드에 넣어 둔 `DATABASE_URL`, `REDIS_URL` 같은 값들이 그대로 주입된 상태로 프로세스가 뜬다.

실제로 어떤 환경변수가 주입되는지 보려면:

```bash
railway variables
```

`railway run`은 특히 서드파티 서비스 연결 테스트할 때 유용하다. 로컬에 DB를 띄우지 않아도 Railway에 올라간 PostgreSQL에 연결된 채로 마이그레이션을 돌릴 수 있다.

```bash
railway run --service database npx prisma migrate deploy
```

### 프로덕션 환경에 실수로 날리는 경우

`railway run`으로 주입된 환경변수는 현재 연결된 환경(production 또는 staging)을 기준으로 가져온다. 프로덕션 DB에 연결된 채로 테스트 스크립트를 돌리는 사고가 생긴다. 특히 환경 전환을 자주 하는 경우, `railway environment production`을 치고 작업하다가 `railway run`을 습관적으로 날리면 위험하다.

환경을 명시하는 방법:

```bash
# 세션 전체를 staging으로 전환
railway environment staging
railway run npm test

# 한 커맨드에만 적용
railway run --environment staging npm test
```

이 정도로는 실수를 막기 어렵다. 습관적으로 엔터를 누르면 `--environment`를 빠뜨리는 경우가 생긴다.

프로덕션에서 `railway run`이 실행될 때 확인을 강제하는 셸 함수를 `~/.zshrc` 또는 `~/.bashrc`에 넣는 방법이 있다.

```bash
# ~/.zshrc 또는 ~/.bashrc에 추가
rrun() {
  local current_env
  current_env=$(railway status 2>/dev/null | grep -i "environment" | awk '{print $NF}')

  if [[ "$current_env" == "production" ]]; then
    echo "[WARNING] 현재 환경: production"
    echo "실행할 커맨드: railway run $*"
    printf "계속 진행하시겠습니까? (yes/N): "
    read -r confirm
    if [[ "$confirm" != "yes" ]]; then
      echo "취소됨"
      return 1
    fi
  fi

  railway run "$@"
}
```

`railway run` 대신 `rrun`을 쓰면 된다. 환경이 production일 때만 확인 프롬프트가 뜨고, staging에서는 그냥 넘어간다. "yes"를 풀로 타이핑해야 통과하도록 했다. "y"만으로 넘어가게 하면 엔터를 잘못 누르는 경우를 못 막는다.

팀 전체에 강제하려면 환경별 토큰을 분리하는 게 더 확실하다. Railway 대시보드 → Project Settings → Tokens에서 production 전용 토큰과 staging 전용 토큰을 따로 발급한다. 개발자 로컬에는 staging 토큰만 배포하면, production에서 `railway run`을 날리려면 토큰을 바꿔야 한다는 마찰이 생긴다.

```bash
# staging 토큰만 로컬에 설정
export RAILWAY_TOKEN="staging-token-here"
railway run npm test  # staging DB에 연결됨

# production에 접근하려면 명시적으로 토큰을 바꿔야 함
RAILWAY_TOKEN="prod-token-here" railway run --environment production <커맨드>
```

이 패턴은 실수를 구조적으로 막는다. 셸 함수는 우회할 수 있지만 토큰 교체는 명시적인 행동이다.

## 서비스별 배포 타겟 지정

프로젝트에 서비스가 여러 개인 경우, CLI 커맨드는 항상 현재 연결된 서비스를 기준으로 동작한다. 서비스를 전환하는 방법은 두 가지다.

**세션 전환 방식**

```bash
railway service
```

대화형 프롬프트로 서비스를 선택하면 이후 커맨드가 그 서비스를 기준으로 동작한다.

**커맨드마다 명시 방식**

```bash
railway logs --service api-server
railway up --service worker
railway variables --service database
```

`--service` 플래그를 지원하는 커맨드라면 세션 전환 없이 바로 지정할 수 있다. 스크립트로 자동화할 때는 이 방식이 안전하다. 세션 상태에 의존하면 다른 사람이 같은 터미널 세션에서 `railway service`를 실행했을 때 의도치 않은 서비스에 명령이 날아갈 수 있다.

환경 변수를 서비스별로 다르게 관리할 때:

```bash
# api-server 서비스의 환경변수 목록
railway variables --service api-server

# 변수 추가
railway variables --set "LOG_LEVEL=debug" --service api-server

# 변수 삭제
railway variables --delete "OLD_KEY" --service api-server
```

## CI/CD에서 비대화형 배포

GitHub Actions나 GitLab CI에서 Railway CLI를 쓸 때는 `RAILWAY_TOKEN`으로 인증한다.

Railway 대시보드 → Project Settings → Tokens에서 토큰을 발급받는다. 토큰은 프로젝트 범위로 발급되고, 환경별로 발급할 수도 있다.

발급한 토큰을 CI 시크릿에 등록하고 환경변수로 넘기면 `railway login` 없이 동작한다.

```yaml
# GitHub Actions 예시
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service api-server --detach
```

`--detach` 플래그는 배포를 트리거하고 완료를 기다리지 않는다. 기본 동작은 배포 완료까지 CLI가 블로킹된다. 배포가 5~10분 걸리는 경우 CI 타임아웃에 걸릴 수 있어서 `--detach`를 쓰는 경우가 있다. 단, 배포 실패를 CI에서 감지하지 못하는 트레이드오프가 생긴다.

배포 성공 여부를 CI에서 확인하려면 블로킹 모드를 쓰고 타임아웃을 넉넉히 잡는다.

```yaml
- name: Deploy
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
  timeout-minutes: 15
  run: railway up --service api-server
```

멀티 서비스 배포는 순서가 중요할 때가 있다. DB 마이그레이션이 끝난 다음에 API 서버를 배포해야 하는 경우:

```yaml
- name: Run migrations
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
  run: railway run --service database npx prisma migrate deploy

- name: Deploy API
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
  run: railway up --service api-server
```

환경별로 토큰을 나눠 쓰면 스테이징 배포와 프로덕션 배포를 실수로 섞는 경우를 막을 수 있다.

```yaml
# staging 브랜치는 RAILWAY_TOKEN_STAGING, main은 RAILWAY_TOKEN_PROD
- name: Deploy
  env:
    RAILWAY_TOKEN: ${{ github.ref == 'refs/heads/main' && secrets.RAILWAY_TOKEN_PROD || secrets.RAILWAY_TOKEN_STAGING }}
  run: railway up --service api-server
```
