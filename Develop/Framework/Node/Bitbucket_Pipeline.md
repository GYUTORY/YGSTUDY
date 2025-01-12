
# 🚀 Node.js Bitbucket Pipeline

---

## 1. Bitbucket Pipeline이란?
**Bitbucket Pipeline**은 Bitbucket에서 제공하는 **CI/CD (지속적 통합 및 지속적 배포)** 도구입니다.  
Git 저장소에 코드를 푸시할 때 **자동으로 빌드, 테스트, 배포**를 수행할 수 있습니다.

---

### 👉🏻 Bitbucket Pipeline의 주요 특징
- **자동화**: 코드 푸시 시 자동으로 빌드 및 배포 수행.
- **내장 CI/CD**: 별도 도구 설치 없이 Bitbucket에서 직접 사용.
- **YAML 기반 구성**: `bitbucket-pipelines.yml` 파일로 손쉽게 설정.
- **다중 언어 지원**: Node.js, Python, Java 등 다양한 프로그래밍 언어 지원.

---

## 2. Bitbucket Pipeline의 기본 구성 📦
**Bitbucket Pipeline**은 저장소의 루트 디렉터리에 위치하는 **`bitbucket-pipelines.yml`** 파일을 통해 구성됩니다.

### 📂 Node.js 프로젝트의 기본 예제
```yaml
# 사용할 Node.js 버전 Docker 이미지 지정
image: node:14  

pipelines:
  default:  # 모든 브랜치에 대해 실행
    - step:
        name: 'Install and Test'  # 단계 이름
        caches:
          - node  # npm 패키지 캐시
        script:  # 실행할 명령어들
          - npm install  # 패키지 설치
          - npm test     # 유닛 테스트 실행

  branches:  # 특정 브랜치에 대한 규칙 설정
    main:
      - step:
          name: 'Deploy to Production'  # 메인 브랜치에 배포
          script:
            - npm run build  # 프로젝트 빌드
            - scp -r ./dist user@server:/var/www/myapp  # 서버에 배포
```

---

## 3. Bitbucket Pipeline의 구성 요소 📦
### 📌 `image`
- 사용할 **Docker 이미지**를 지정합니다.
- 예: `node:14`, `python:3.9`

### 📌 `pipelines`
- **전체 파이프라인 워크플로우**를 정의하는 섹션입니다.

### 📌 `default`
- 모든 브랜치에 대해 실행되는 기본 파이프라인입니다.

### 📌 `branches`
- 특정 브랜치에 대해 실행될 규칙을 정의합니다.

### 📌 `step`
- **각 단계**를 정의하는 블록입니다.

### 📌 `script`
- 각 단계에서 실행할 **쉘 명령어**를 작성합니다.

### 📌 `caches`
- 빌드 속도를 높이기 위해 **캐시**를 설정할 수 있습니다.
- 예: `node` (npm 패키지 캐시)

---

## 4. Node.js CI/CD 예제 🛠️
### 📦 4.1 Node.js 프로젝트 자동화 (테스트 + 빌드 + 배포)
```yaml
image: node:16

pipelines:
  default:
    - step:
        name: 'Install and Run Tests'
        caches:
          - node
        script:
          - npm install
          - npm test

  branches:
    main:
      - step:
          name: 'Build and Deploy to Production'
          script:
            - npm run build
            - scp -r ./dist user@my-production-server:/var/www/myapp
```

### 📌 설명 (한 줄씩 해설)
- `image: node:16` → Node.js 16 버전의 Docker 이미지를 사용.
- `default` → 모든 브랜치에 대해 실행.
- `step` → 개별 단계를 정의.
- `caches` → `node_modules`를 캐시하여 속도 최적화.
- `script` → `npm install`로 의존성 설치, `npm test`로 테스트 실행.
- `main` → `main` 브랜치에 푸시 시 `npm run build`와 `scp`를 이용해 프로덕션 배포.

---

### ✅ 4.2 Node.js 프로젝트 + AWS S3 배포 예제
```yaml
image: node:14

pipelines:
  default:
    - step:
        name: 'Build and Deploy to S3'
        script:
          - npm install
          - npm run build
          - aws s3 sync ./dist s3://my-bucket-name --delete
          - aws cloudfront create-invalidation --distribution-id EXAMPLE_ID --paths "/*"
```

---

## 5. Bitbucket Pipeline의 보안 설정 🔒
### ✅ 보안 모범 사례
- **IAM 최소 권한 사용**: AWS 자격 증명 최소 권한 부여.
- **환경 변수 보호**: `Repository Settings → Environment Variables` 사용.
- **보안 토큰 암호화**: `secrets` 관리 사용.

---

## 6. Bitbucket Pipeline의 장단점 📊
### ✅ 장점
- **내장 CI/CD**: 추가 도구 설치 없이 사용 가능.
- **간편한 설정**: YAML 파일만으로 간단히 구성.
- **무료 플랜 제공**: 소규모 프로젝트 무료 사용 가능.

### ❗ 단점
- **고급 워크플로우 제한**: Jenkins, GitLab CI에 비해 기능 제한.
- **커스터마이징 제한**: 복잡한 파이프라인 구성 어려움.

---

## 7. Bitbucket Pipeline 사용 사례 📦
- **Node.js 프로젝트 테스트 및 배포**
- **정적 웹사이트 S3 + CloudFront 배포**
- **서버리스 Lambda 함수 자동 배포**
- **Docker 컨테이너 빌드 및 ECR 푸시**

---

## 8. Bitbucket Pipeline과 GitHub Actions 비교
| **특징**                   | **Bitbucket Pipelines**      | **GitHub Actions**      |
|:---------------------------|:----------------------------|:------------------------|
| **통합 방식**              | Bitbucket에 내장           | GitHub에 내장          |
| **사용 용이성**             | 간편함                    | 다소 복잡함            |
| **무료 플랜 제공**         | 50분/월 무료               | 2,000분/월 무료         |
| **커스터마이징**           | 제한적                    | 고급 커스터마이징 가능   |

---

## 9. 결론 ✅
- **Bitbucket Pipeline**은 **Node.js 프로젝트의 CI/CD를 간편하게 자동화**할 수 있는 강력한 도구입니다.
- **`bitbucket-pipelines.yml`** 파일 하나로 빌드, 테스트, 배포를 자동화할 수 있습니다.
- **보안 모범 사례**를 준수하고, **환경 변수 보호**를 강화해야 합니다.
