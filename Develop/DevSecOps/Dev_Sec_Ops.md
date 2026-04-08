---
title: DevSecOps
tags: [devsecops, security, cicd, sast, dast, sca, supply-chain]
updated: 2026-04-08
---

# DevSecOps

DevSecOps는 CI/CD 파이프라인에 보안 검사를 자동화해서 넣는 것이다. 코드가 머지되기 전에 취약점을 잡고, 컨테이너 이미지나 의존성에 알려진 CVE가 있으면 빌드를 멈추는 구조를 만든다. 보안팀이 배포 후에 수동 점검하던 방식에서, 개발자가 PR 단계에서 보안 이슈를 직접 확인하고 수정하는 방식으로 바꾸는 것이 핵심이다.

실무에서 DevSecOps를 도입하면 처음에는 false positive가 쏟아지고, 파이프라인이 느려지고, 개발자들이 보안 스캔 결과를 무시하기 시작한다. 이 문서는 그런 상황을 겪으면서 실제로 어떻게 세팅하고 운영했는지를 다룬다.

---

## SAST — 정적 분석

SAST(Static Application Security Testing)는 소스 코드를 실행하지 않고 분석하는 방식이다. SQL Injection, XSS, 하드코딩된 시크릿 같은 패턴을 코드 레벨에서 잡는다.

### SonarQube

SonarQube는 코드 품질과 보안 취약점을 같이 잡는 도구다. Community Edition은 무료인데, 브랜치 분석이 안 되서 PR 단위 스캔을 하려면 Developer Edition 이상이 필요하다. 이게 꽤 비싸서 소규모 팀은 SonarCloud(SaaS)를 쓰는 경우가 많다.

**GitHub Actions 연동:**

```yaml
# .github/workflows/sonar.yml
name: SonarQube Analysis
on:
  pull_request:
    branches: [main, develop]

jobs:
  sonar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 전체 히스토리가 있어야 blame 정보를 분석한다
      
      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v3
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
        with:
          args: >
            -Dsonar.projectKey=my-project
            -Dsonar.sources=src/
            -Dsonar.exclusions=**/test/**,**/node_modules/**
            -Dsonar.qualitygate.wait=true
```

`sonar.qualitygate.wait=true`를 넣으면 Quality Gate 결과가 나올 때까지 기다리고, 통과 못 하면 파이프라인이 실패한다. 이걸 안 넣으면 스캔만 돌리고 결과는 무시하는 구조가 되는데, 그러면 아무도 안 본다.

**sonar-project.properties 설정:**

```properties
sonar.projectKey=my-project
sonar.sources=src/main
sonar.tests=src/test
sonar.java.binaries=build/classes
sonar.coverage.jacoco.xmlReportPaths=build/reports/jacoco/test/jacocoTestReport.xml
sonar.issue.ignore.multicriteria=e1
sonar.issue.ignore.multicriteria.e1.ruleKey=java:S1135
sonar.issue.ignore.multicriteria.e1.resourceKey=**/*
```

`sonar.issue.ignore.multicriteria`는 특정 룰을 무시할 때 쓴다. 예를 들어 `java:S1135`는 TODO 코멘트 관련 룰인데, 이걸 Critical로 잡으면 PR마다 터지니까 프로젝트 특성에 맞게 조정해야 한다.

### Semgrep

Semgrep은 패턴 기반 정적 분석 도구다. SonarQube보다 가볍고, 커스텀 룰을 YAML로 쉽게 만들 수 있다. OSS 프로젝트에서 많이 쓴다.

```yaml
# .github/workflows/semgrep.yml
name: Semgrep
on:
  pull_request: {}

jobs:
  semgrep:
    runs-on: ubuntu-latest
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v4
      - run: semgrep ci
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}
```

`semgrep ci`를 쓰면 Semgrep Cloud Platform과 연동되어 PR에 코멘트를 달아준다. 토큰 없이 로컬에서만 돌리려면:

```bash
# 기본 보안 룰셋으로 스캔
semgrep --config=p/security-audit src/

# 특정 언어만
semgrep --config=p/java src/

# 커스텀 룰 적용
semgrep --config=.semgrep/ src/
```

**커스텀 룰 작성:**

```yaml
# .semgrep/custom-rules.yml
rules:
  - id: no-system-exit
    patterns:
      - pattern: System.exit(...)
    message: System.exit()은 프로덕션 코드에서 쓰지 않는다. 예외를 던져라.
    languages: [java]
    severity: ERROR

  - id: no-raw-sql-string
    patterns:
      - pattern: |
          String $QUERY = "..." + $VAR + "...";
      - metavariable-regex:
          metavariable: $QUERY
          regex: (?i).*(select|insert|update|delete).*
    message: SQL 문자열을 직접 조합하고 있다. PreparedStatement를 써라.
    languages: [java]
    severity: ERROR
```

Semgrep의 장점은 이런 커스텀 룰을 프로젝트에 맞게 빠르게 만들 수 있다는 것이다. SonarQube에서 커스텀 룰을 만들려면 Java 플러그인을 개발해야 하는데, Semgrep은 YAML 파일 하나면 된다.

---

## DAST — 동적 분석

DAST(Dynamic Application Security Testing)는 실행 중인 애플리케이션에 실제 요청을 보내서 취약점을 찾는다. SAST가 코드를 보는 거라면, DAST는 외부에서 공격자처럼 접근하는 방식이다.

### OWASP ZAP

ZAP(Zed Attack Proxy)은 가장 많이 쓰이는 오픈소스 DAST 도구다. CI에서 돌릴 때는 Docker 이미지를 쓴다.

**GitHub Actions에서 Baseline Scan:**

```yaml
name: DAST
on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types: [completed]

jobs:
  zap-scan:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: 'https://staging.example.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j'
          allow_issue_writing: false
```

Baseline Scan은 passive scan만 수행한다. 페이지를 크롤링하면서 응답 헤더, 쿠키 설정, 정보 노출 같은 것을 확인하는데, 서버에 부하를 거의 주지 않는다. Full Scan은 active scan까지 하는데, SQL Injection 같은 공격 패턴을 실제로 보내기 때문에 스테이징 환경에서만 돌려야 한다.

**룰 커스터마이징 (.zap/rules.tsv):**

```tsv
10010	IGNORE	(Cookie No HttpOnly Flag)
10011	IGNORE	(Cookie Without Secure Flag)
10015	WARN	(Incomplete or No Cache-control Header Set)
10021	FAIL	(X-Content-Type-Options Header Missing)
10038	FAIL	(Content Security Policy Header Not Set)
90033	FAIL	(Loosely Scoped Cookie)
```

각 룰에 IGNORE, WARN, FAIL을 지정할 수 있다. 처음에 돌리면 수십 개 경고가 뜨는데, 한꺼번에 다 잡으려고 하면 안 된다. FAIL로 잡을 항목을 3~5개만 정하고, 나머지는 WARN으로 돌리면서 점진적으로 줄여나가야 한다.

**Full Scan은 이렇게 따로 돌린다:**

```yaml
      - name: ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.10.0
        with:
          target: 'https://staging.example.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j -T 60'  # 타임아웃 60분
```

Full Scan은 30분~1시간 넘게 걸리는 경우가 있다. PR마다 돌리면 파이프라인이 막히니까, 보통 야간 스케줄이나 릴리스 전에만 실행한다.

---

## SCA — 의존성 취약점 스캔

SCA(Software Composition Analysis)는 프로젝트가 사용하는 오픈소스 라이브러리에 알려진 취약점(CVE)이 있는지 검사한다. Log4Shell(CVE-2021-44228) 같은 사태가 터지면 SCA가 있냐 없냐에 따라 대응 속도가 완전히 달라진다.

### Trivy

Trivy는 Aqua Security에서 만든 도구로, 컨테이너 이미지, 파일시스템, Git 리포지토리를 스캔한다. 설치가 간단하고 속도가 빠르다.

```yaml
# .github/workflows/trivy.yml
name: Trivy Scan
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  trivy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy (파일시스템)
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'           # 발견되면 빌드 실패
          ignore-unfixed: true     # 패치가 없는 취약점은 무시
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

`ignore-unfixed: true`는 중요하다. 아직 패치 버전이 나오지 않은 취약점까지 잡으면 개발자가 할 수 있는 게 없는데 빌드만 계속 실패하게 된다.

**컨테이너 이미지 스캔:**

```yaml
      - name: Build Image
        run: docker build -t my-app:${{ github.sha }} .
      
      - name: Trivy Image Scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: 'my-app:${{ github.sha }}'
          severity: 'CRITICAL'
          exit-code: '1'
```

이미지 스캔은 베이스 이미지(alpine, debian 등)에 포함된 OS 패키지 취약점까지 잡아준다. `alpine` 기반 이미지를 쓰면 취약점이 적고 이미지 크기도 작다.

### Snyk

Snyk은 의존성 취약점 검사에 특화된 SaaS 도구다. 무료 플랜에서 매월 200회 테스트가 가능하고, PR에 자동으로 수정 제안을 달아준다.

```yaml
      - name: Snyk Test
        uses: snyk/actions/node@master  # 언어별로 다름: /maven, /gradle, /python 등
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
```

Snyk의 편한 점은 취약점을 발견하면 어떤 버전으로 올려야 하는지 알려주고, 자동으로 Fix PR까지 만들어준다는 것이다. 단, 무료 플랜은 private repo에서 제한이 있으니 팀 규모에 따라 Trivy와 병행하는 경우가 많다.

**.snyk 파일로 예외 처리:**

```yaml
# .snyk
version: v1.5.0
ignore:
  SNYK-JS-LODASH-590103:
    - '*':
        reason: 'lodash.merge만 쓰고 있고, 해당 취약점이 발생하는 경로로 사용하지 않음'
        expires: '2026-07-01T00:00:00.000Z'
```

예외 처리할 때 `expires`를 반드시 넣어라. 기한 없이 무시하면 나중에 아무도 재검토하지 않는다.

---

## Secret Scanning

코드에 AWS 키, DB 비밀번호, API 토큰 같은 시크릿이 들어가는 사고는 생각보다 자주 발생한다. git history에 한 번 들어가면 rebase를 하거나 BFG로 지우지 않는 한 계속 남아 있다.

### gitleaks

gitleaks는 git 커밋 히스토리까지 스캔하는 시크릿 탐지 도구다.

```yaml
# .github/workflows/gitleaks.yml
name: Gitleaks
on:
  pull_request: {}
  push:
    branches: [main]

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

`fetch-depth: 0`이 필수다. 기본값인 1(shallow clone)로 하면 최신 커밋만 보기 때문에 과거에 넣었다가 삭제한 시크릿을 못 잡는다.

**커스텀 설정 (.gitleaks.toml):**

```toml
[allowlist]
  paths = [
    '''test/fixtures/.*''',
    '''docs/examples/.*'''
  ]

[[rules]]
  id = "custom-internal-token"
  description = "Internal API Token"
  regex = '''(?i)internal[_-]?api[_-]?(?:key|token)\s*[=:]\s*['"]?([a-zA-Z0-9]{32,})'''
  tags = ["key", "internal"]

[[rules]]
  id = "slack-webhook"
  description = "Slack Webhook URL"
  regex = '''https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+'''
  tags = ["key", "slack"]
```

테스트 코드에 있는 더미 토큰(test-token-12345 같은)을 false positive로 잡는 경우가 많다. `allowlist.paths`로 테스트 디렉토리를 제외하거나, 더미 값 패턴을 allowlist에 추가해야 한다.

### trufflehog

trufflehog는 entropy 분석과 실제 검증(verification)을 지원한다. AWS 키를 찾으면 실제로 유효한 키인지 API 호출로 확인하는 기능이 있다.

```yaml
      - name: TruffleHog Scan
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified --results=verified,unknown
```

`--only-verified`를 쓰면 실제로 유효한 시크릿만 보고한다. false positive를 크게 줄일 수 있는데, 외부 API 호출이 필요하니까 네트워크 환경에 따라 스캔 시간이 길어질 수 있다.

### pre-commit hook으로 커밋 전 차단

시크릿은 커밋되기 전에 잡는 게 가장 좋다. git history에 들어가면 처리가 복잡해진다.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

```bash
pip install pre-commit
pre-commit install
```

팀원 전체가 pre-commit hook을 설치해야 하는데, 이걸 강제하기 어렵다. 그래서 CI에서도 반드시 스캔을 돌려야 한다. pre-commit은 1차 방어선, CI는 2차 방어선이다.

---

## 보안 게이트 설정

보안 스캔을 돌리는 것만으로는 부족하다. 스캔 결과에 따라 빌드를 통과시킬지 차단할지 기준이 있어야 한다.

### 임계값 설정 기준

실무에서 처음 도입할 때 권장하는 단계별 기준:

**1단계 — 도입 초기 (1~2주):**

```yaml
# 모니터링만, 빌드 차단하지 않음
exit-code: '0'
severity: 'CRITICAL,HIGH,MEDIUM'
```

처음에는 빌드를 안 막고 어떤 이슈가 얼마나 나오는지 파악한다. 이 단계를 건너뛰고 바로 차단을 걸면 개발이 멈춘다.

**2단계 — 기준 수립 (2~4주):**

```yaml
# Critical만 빌드 차단
exit-code: '1'
severity: 'CRITICAL'
```

**3단계 — 안정화 후:**

```yaml
# Critical + High 빌드 차단
exit-code: '1'
severity: 'CRITICAL,HIGH'
```

Medium까지 빌드를 막는 팀은 거의 못 봤다. Medium 이슈는 알림만 보내고 스프린트 백로그에 넣어서 점진적으로 처리하는 게 현실적이다.

### GitHub Actions에서 통합 보안 게이트

여러 보안 스캔 결과를 종합해서 최종 판단하는 Job을 만들 수 있다:

```yaml
jobs:
  sast:
    # ... Semgrep 스캔
  sca:
    # ... Trivy 스캔
  secret:
    # ... gitleaks 스캔

  security-gate:
    needs: [sast, sca, secret]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Check Security Results
        run: |
          if [ "${{ needs.sast.result }}" == "failure" ] || \
             [ "${{ needs.sca.result }}" == "failure" ] || \
             [ "${{ needs.secret.result }}" == "failure" ]; then
            echo "::error::보안 스캔 실패. PR을 머지할 수 없습니다."
            exit 1
          fi
```

Branch Protection Rule에서 이 `security-gate` Job을 Required Status Check로 지정하면, 보안 스캔을 통과하지 않으면 머지 자체가 불가능해진다.

### GitLab CI 기반 보안 파이프라인

GitLab은 보안 스캔 기능을 CI 템플릿으로 제공한다:

```yaml
# .gitlab-ci.yml
include:
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Dependency-Scanning.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml
  - template: Security/Container-Scanning.gitlab-ci.yml

stages:
  - build
  - test
  - security
  - deploy

sast:
  stage: security
  variables:
    SAST_EXCLUDED_PATHS: "test/,docs/"

dependency_scanning:
  stage: security
  variables:
    DS_EXCLUDED_ANALYZERS: "bundler-audit"

container_scanning:
  stage: security
  variables:
    CS_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    CS_SEVERITY_THRESHOLD: "CRITICAL"
```

GitLab Ultimate에서는 Security Dashboard에서 취약점을 한눈에 볼 수 있고, Merge Request에 보안 리포트가 자동으로 표시된다. 하지만 Ultimate 가격이 상당하기 때문에, 무료 플랜에서는 위에서 설명한 오픈소스 도구들을 조합해서 쓰는 게 낫다.

---

## 취약점 발견 시 대응 흐름

스캔에서 취약점이 발견됐을 때 실제로 어떻게 처리하는지가 중요하다. 도구를 셋업하는 것보다 이 프로세스가 잘 돌아가는지가 더 중요하다.

### Critical 취약점 대응

1. **스캔에서 Critical 발견** — CI가 실패하고, Slack 알림이 간다.
2. **담당자 지정** — 해당 코드를 마지막으로 수정한 사람이 1차 담당. git blame으로 확인한다.
3. **영향도 확인** — 해당 취약점이 실제 서비스에서 exploit 가능한지 확인한다. CVSS 점수가 높아도 우리 환경에서는 해당되지 않는 경우가 있다.
4. **수정 또는 완화** — 라이브러리 업그레이드, 코드 수정, 또는 WAF 룰 추가로 임시 차단.
5. **검증** — 수정 후 스캔을 다시 돌려서 해결 확인.

```bash
# 예: Trivy에서 Critical CVE 발견 시
trivy fs --severity CRITICAL --vuln-type library .

# 어떤 의존성이 문제인지 확인
trivy fs --severity CRITICAL --format json . | jq '.Results[].Vulnerabilities[] | {PkgName, InstalledVersion, FixedVersion, VulnerabilityID}'
```

### High 취약점 대응

High는 즉시 수정이 아니라 SLA 기반으로 처리한다. 보통 팀마다 다르지만:

- Critical: 24시간 이내 수정
- High: 1주일 이내 수정
- Medium: 다음 스프린트에 포함
- Low: 백로그에 기록

이 SLA를 정해두지 않으면 High 취약점이 수십 개 쌓여도 아무도 처리하지 않는 상황이 된다.

---

## Supply Chain Security

의존성을 통한 공격(Supply Chain Attack)이 늘고 있다. 2024년 xz-utils 백도어 사건처럼, 신뢰하던 라이브러리 자체가 공격 벡터가 되는 경우가 있다.

### SBOM 생성

SBOM(Software Bill of Materials)은 소프트웨어에 포함된 모든 구성 요소 목록이다. 취약점이 발견됐을 때 어떤 서비스가 영향을 받는지 빠르게 파악하려면 SBOM이 있어야 한다.

```yaml
# Trivy로 SBOM 생성
- name: Generate SBOM
  run: |
    trivy fs --format cyclonedx --output sbom.json .

# Syft로 SBOM 생성 (더 상세한 결과)
- name: Generate SBOM with Syft
  uses: anchore/sbom-action@v0
  with:
    format: spdx-json
    output-file: sbom.spdx.json
    image: my-app:${{ github.sha }}
```

SBOM 포맷은 CycloneDX와 SPDX 두 가지가 주로 쓰인다. 둘 다 업계 표준이고 대부분의 도구에서 지원한다.

### 컨테이너 이미지 서명 (Cosign)

빌드한 이미지가 변조되지 않았는지 검증하려면 서명이 필요하다. Sigstore의 Cosign을 쓰면 keyless 서명이 가능하다.

```yaml
# 이미지 빌드 → 서명 → 레지스트리 푸시
- name: Sign Image
  run: |
    # keyless signing (GitHub OIDC 사용)
    cosign sign --yes \
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}

# 배포 시 서명 검증
- name: Verify Image
  run: |
    cosign verify \
      --certificate-identity-regexp="https://github.com/${{ github.repository }}/*" \
      --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ env.DIGEST }}
```

GitHub Actions에서 빌드하면 OIDC 토큰을 자동으로 발급받아서 keyless signing이 된다. 별도의 키 관리가 필요 없어서 운영 부담이 적다.

---

## False Positive 처리

DevSecOps에서 가장 귀찮은 문제가 false positive다. 처리하지 않으면 개발자들이 보안 스캔 결과 자체를 무시하게 된다.

### false positive가 많이 나오는 패턴

**1. 테스트 코드의 더미 시크릿**

```java
// 이런 코드를 gitleaks가 잡는다
private static final String TEST_API_KEY = "sk-test-1234567890abcdef";
```

해결: `.gitleaks.toml`에서 테스트 경로를 제외하거나, 더미 값에 `test`, `dummy`, `fake` 같은 접두어를 붙이는 규칙을 정한다.

**2. 내부 URL이 외부 노출로 오탐**

DAST에서 내부 전용 엔드포인트를 external에서 접근 가능한 것으로 잡는 경우가 있다. ZAP rules.tsv에서 해당 룰을 IGNORE로 돌리거나, 스캔 대상 URL을 정확하게 지정해야 한다.

**3. 의존성의 간접 취약점**

`A → B → C` 형태로 의존하는데, C에 취약점이 있지만 B가 C의 취약한 함수를 호출하지 않는 경우. Snyk은 이런 "reachability" 분석을 지원하지만 완벽하지 않다.

### false positive 관리 원칙

- 무시할 때는 반드시 사유와 만료일을 적는다.
- 분기마다 무시 목록을 검토한다. 만료일이 지난 항목은 다시 확인한다.
- 무시 설정은 코드 리뷰 대상이다. `.snyk`, `.gitleaks.toml`, `rules.tsv` 파일 변경은 보안 담당자가 approve해야 한다.

---

## 파이프라인 병목 문제 해결

보안 스캔을 다 넣으면 파이프라인이 10분이던 게 30분으로 늘어나는 경우가 있다. 개발자 입장에서 PR 올리고 30분 기다리는 건 생산성에 직접적인 타격이다.

### 병렬 실행

가장 기본적인 방법. 보안 스캔들은 서로 의존성이 없으니 전부 병렬로 돌린다.

```yaml
jobs:
  test:
    # ... 테스트
  sast:
    # ... SAST (Semgrep) — 테스트와 동시에 실행
  sca:
    # ... SCA (Trivy) — 테스트와 동시에 실행
  secret-scan:
    # ... gitleaks — 테스트와 동시에 실행
  
  # 이미지 빌드 후에만 실행해야 하는 것
  image-scan:
    needs: [build]
    # ... 이미지 스캔
```

### diff 기반 스캔

전체 코드를 매번 스캔하는 대신, 변경된 파일만 스캔하면 속도가 크게 줄어든다.

```yaml
      - name: Get Changed Files
        id: changed
        run: |
          echo "files=$(git diff --name-only origin/main...HEAD | tr '\n' ' ')" >> $GITHUB_OUTPUT
      
      - name: Semgrep (changed files only)
        run: semgrep --config=p/security-audit ${{ steps.changed.outputs.files }}
```

단, 주간 또는 야간에 전체 스캔을 별도로 돌려야 한다. diff 스캔만 하면 기존 코드의 취약점을 놓칠 수 있다.

### 캐시 활용

```yaml
      - name: Cache Trivy DB
        uses: actions/cache@v4
        with:
          path: ~/.cache/trivy
          key: trivy-db-${{ github.run_id }}
          restore-keys: trivy-db-
```

Trivy는 취약점 DB를 매번 다운로드하는데, 캐시하면 스캔 시작이 30초~1분 빨라진다.

### DAST는 분리

앞에서 말한 것처럼 DAST(ZAP Full Scan)는 PR 파이프라인에 넣지 않는다. 별도 스케줄로 돌린다:

```yaml
on:
  schedule:
    - cron: '0 2 * * 1-5'  # 평일 새벽 2시
```

---

## 전체 파이프라인 구성 예시

실무에서 돌리는 보안 파이프라인의 전체 모습:

```yaml
# .github/workflows/security.yml
name: Security Pipeline
on:
  pull_request:
    branches: [main, develop]

concurrency:
  group: security-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            .semgrep/

  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy FS Scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          ignore-unfixed: true

  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  image-scan:
    needs: [sast]  # SAST 통과한 코드만 이미지 빌드
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: docker build -t app:${{ github.sha }} .
      - name: Trivy Image Scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: 'app:${{ github.sha }}'
          severity: 'CRITICAL'
          exit-code: '1'

  security-gate:
    needs: [sast, sca, secret-scan, image-scan]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Evaluate Results
        run: |
          results=("${{ needs.sast.result }}" "${{ needs.sca.result }}" "${{ needs.secret-scan.result }}" "${{ needs.image-scan.result }}")
          for result in "${results[@]}"; do
            if [ "$result" == "failure" ]; then
              echo "::error::보안 게이트 실패"
              exit 1
            fi
          done
          echo "보안 게이트 통과"
```

`concurrency`로 같은 PR에서 새 커밋이 푸시되면 이전 스캔을 취소한다. 이게 없으면 커밋할 때마다 스캔이 쌓여서 runner가 부족해진다.

---

## 도입 순서

한 번에 모든 도구를 넣으려고 하면 실패한다. 다음 순서로 하나씩 추가하는 게 현실적이다:

1. **Secret Scanning** — 가장 먼저. 시크릿 유출은 즉시 피해가 발생한다. gitleaks 하나면 충분하다.
2. **SCA** — Trivy로 의존성 스캔. 설정이 간단하고 결과가 명확하다.
3. **SAST** — Semgrep부터 시작. SonarQube는 운영 부담이 있으니 팀 규모가 커진 후에 도입한다.
4. **보안 게이트** — 위 3가지가 안정화된 후 빌드 차단 조건을 건다.
5. **DAST** — 스테이징 환경이 안정적으로 운영되고 있을 때 추가한다.
6. **Supply Chain** — SBOM 생성과 이미지 서명은 컴플라이언스 요구사항이 있을 때 도입한다.

각 단계에서 2~3주 정도 운영하면서 false positive를 정리하고, 팀이 결과를 확인하는 습관이 생긴 후에 다음 단계로 넘어가야 한다.
