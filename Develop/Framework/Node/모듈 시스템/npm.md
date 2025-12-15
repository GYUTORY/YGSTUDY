---
title: npm, package.json, package-lock.json
tags: [framework, node, 모듈-시스템, npm, nodejs]
updated: 2025-12-15
---

# npm, package.json, package-lock.json

## npm (Node Package Manager) 이해하기

npm은 Node.js 생태계의 핵심 도구로, JavaScript 패키지와 의존성을 관리하는 표준 도구입니다. 2009년 Node.js와 함께 출시된 이후, 전 세계에서 가장 큰 소프트웨어 레지스트리로 성장했습니다.

### npm의 핵심 역할

npm은 단순한 패키지 설치 도구를 넘어서 다음과 같은 역할을 수행합니다:

1. **패키지 레지스트리**: 전 세계 개발자들이 공유하는 오픈소스 패키지 저장소
2. **의존성 관리**: 프로젝트의 모든 의존성을 자동으로 추적하고 관리
3. **버전 관리**: 시맨틱 버저닝을 통한 체계적인 버전 관리
4. **스크립트 실행**: 프로젝트 빌드, 테스트, 배포 등의 작업 자동화
5. **보안 관리**: 패키지 취약점 검사 및 보안 업데이트

### npm 설치 및 버전 확인

Node.js를 설치하면 npm이 자동으로 함께 설치됩니다:

```bash
# npm 버전 확인
npm -v

# Node.js 버전 확인 (npm과 함께 설치됨)
node -v
```

### npm 기본 명령어

```bash
# 패키지 설치
npm install <패키지명>

# 전역 설치
npm install -g <패키지명>

# 개발 의존성으로 설치
npm install --save-dev <패키지명>

# 패키지 제거
npm uninstall <패키지명>

# 패키지 업데이트
npm update <패키지명>

# 모든 패키지 업데이트
npm update
```

## package.json - 프로젝트의 핵심 설정 파일

package.json은 Node.js 프로젝트의 핵심 설정 파일로, 프로젝트의 메타데이터와 의존성 정보를 담고 있습니다. 이 파일 하나로 프로젝트의 모든 정보를 파악할 수 있으며, 다른 개발자나 CI/CD 시스템이 프로젝트를 이해하고 실행할 수 있게 해줍니다.

### package.json의 주요 목적

1. **프로젝트 식별**: 프로젝트 이름, 버전, 설명 등 기본 정보
2. **의존성 관리**: 프로젝트가 필요로 하는 패키지들의 목록과 버전
3. **스크립트 정의**: 빌드, 테스트, 배포 등의 자동화된 작업
4. **메타데이터 제공**: 라이선스, 작성자, 저장소 정보 등

### package.json 생성하기

새로운 프로젝트를 시작할 때 package.json을 생성하는 방법:

```bash
# 대화형으로 package.json 생성
npm init

# 기본값으로 package.json 생성 (모든 질문에 엔터)
npm init -y

# 특정 값으로 package.json 생성
npm init --yes
```

### package.json 구조 분석

```json
{
  "name": "my-awesome-project",
  "version": "1.0.0",
  "description": "Node.js 프로젝트 예제",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js",
    "test": "jest",
    "build": "webpack --mode production"
  },
  "keywords": ["nodejs", "express", "api"],
  "author": "Your Name <your.email@example.com>",
  "license": "MIT",
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "nodemon": "^2.0.15",
    "jest": "^29.0.0"
  },
  "engines": {
    "node": ">=14.0.0",
    "npm": ">=6.0.0"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/username/my-awesome-project.git"
  }
}
```

### package.json 주요 필드 설명

| 필드 | 설명 | 필수 여부 |
|------|------|-----------|
| `name` | 패키지 이름 (npm 레지스트리에서 고유해야 함) | 필수 |
| `version` | 시맨틱 버저닝 형식의 버전 (예: 1.0.0) | 필수 |
| `description` | 패키지에 대한 간단한 설명 | 권장 |
| `main` | 패키지의 진입점이 되는 파일 | 권장 |
| `scripts` | npm run으로 실행할 수 있는 스크립트들 | 선택 |
| `dependencies` | 프로덕션 환경에서 필요한 패키지들 | 선택 |
| `devDependencies` | 개발 환경에서만 필요한 패키지들 | 선택 |
| `keywords` | npm 검색에 도움이 되는 키워드들 | 선택 |
| `author` | 패키지 작성자 정보 | 권장 |
| `license` | 라이선스 정보 | 권장 |
| `engines` | 지원하는 Node.js, npm 버전 | 선택 |
| `repository` | 소스 코드 저장소 정보 | 권장 |

### 의존성 관리 심화

#### dependencies vs devDependencies

```json
{
  "dependencies": {
    "express": "^4.18.2",
    "mongoose": "^7.0.0"
  },
  "devDependencies": {
    "nodemon": "^2.0.15",
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }
}
```

- **dependencies**: 프로덕션 환경에서 실제로 필요한 패키지들
- **devDependencies**: 개발 중에만 필요한 패키지들 (테스트 도구, 빌드 도구 등)

#### 버전 범위 지정자 이해하기

```json
{
  "dependencies": {
    "express": "^4.18.2",    // 4.18.2 이상 5.0.0 미만
    "lodash": "~4.17.21",    // 4.17.21 이상 4.18.0 미만
    "moment": "2.29.4",      // 정확히 2.29.4 버전만
    "axios": "*",            // 최신 버전
    "react": ">=16.8.0"      // 16.8.0 이상
  }
}
```

### npm 스크립트 활용하기

package.json의 scripts 섹션을 통해 복잡한 작업들을 간단한 명령어로 실행할 수 있습니다:

```json
{
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "build": "webpack --mode production",
    "build:dev": "webpack --mode development",
    "lint": "eslint src/",
    "lint:fix": "eslint src/ --fix",
    "clean": "rimraf dist/",
    "prebuild": "npm run clean",
    "postbuild": "echo 'Build completed!'"
  }
}
```

스크립트 실행:
```bash
npm run dev          # 개발 서버 시작
npm run test         # 테스트 실행
npm run build        # 프로덕션 빌드
npm run lint:fix     # 린트 오류 자동 수정
```

### npm 명령어 완전 가이드

#### 패키지 설치 관련
```bash
# package.json의 모든 의존성 설치
npm install

# 특정 패키지 설치 (dependencies에 추가)
npm install express

# 개발 의존성으로 설치
npm install --save-dev nodemon

# 전역 설치
npm install -g typescript

# 특정 버전 설치
npm install express@4.18.2

# 최신 버전 설치
npm install express@latest
```

#### 패키지 관리 관련
```bash
# 패키지 제거
npm uninstall express

# 개발 의존성 제거
npm uninstall --save-dev nodemon

# 전역 패키지 제거
npm uninstall -g typescript

# 패키지 업데이트
npm update express

# 모든 패키지 업데이트
npm update

# 오래된 패키지 확인
npm outdated
```

#### 유틸리티 명령어
```bash
# npm 캐시 정리
npm cache clean --force

# 설치된 패키지 목록 확인
npm list

# 전역 패키지 목록 확인
npm list -g --depth=0

# 패키지 정보 확인
npm info express

# 패키지 검색
npm search express
```










## package-lock.json - 정확한 의존성 버전 관리

package-lock.json은 npm이 자동으로 생성하는 파일로, 프로젝트에 설치된 모든 패키지의 정확한 버전과 의존성 트리를 기록합니다. 이 파일은 개발 환경 간의 일관성을 보장하고, "내 컴퓨터에서는 되는데..." 문제를 해결하는 핵심 도구입니다.

### package-lock.json이 중요한 이유

1. **정확한 버전 고정**: package.json의 `^4.18.2` 같은 범위 지정자 대신 정확한 버전을 기록
2. **의존성 트리 보존**: 모든 하위 의존성까지 포함한 완전한 의존성 트리 저장
3. **빠른 설치**: 이미 해결된 의존성 정보를 바탕으로 빠른 설치 가능
4. **보안**: 패키지의 무결성 해시값을 포함하여 보안 강화

### package-lock.json 구조 이해

```json
{
  "name": "my-project",
  "version": "1.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "my-project",
      "version": "1.0.0",
      "dependencies": {
        "express": "^4.18.2"
      }
    },
    "node_modules/express": {
      "version": "4.18.2",
      "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
      "integrity": "sha512-5/PsL6iGPdfQ/lKM1UuielYgv3BUoJfz1aUwU9vHZ+J7gyvwdQXFEBIEIaxeGf0GIcreATNyBExtalisDbuMqQ==",
      "dependencies": {
        "accepts": "~1.3.8",
        "array-flatten": "1.1.1",
        "body-parser": "1.20.1"
      }
    },
    "node_modules/accepts": {
      "version": "1.3.8",
      "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.8.tgz",
      "integrity": "sha512-PYAthTa2m2VKxuvSD3DPC/Gy+U+sOA1LAu8/4bEfDQtlaqfCLSpa0qfZgdQpJovNA6E5p6feH+LhsvzXC0K2Bw==",
      "dependencies": {
        "mime-types": "~2.1.34",
        "negotiator": "0.6.3"
      }
    }
  }
}
```

### package-lock.json 주요 필드 설명

| 필드 | 설명 |
|------|------|
| `lockfileVersion` | package-lock.json 파일 형식 버전 |
| `requires` | package.json의 의존성이 필요한지 여부 |
| `packages` | 모든 패키지의 상세 정보 |
| `version` | 정확한 패키지 버전 |
| `resolved` | 패키지 다운로드 URL |
| `integrity` | 패키지 무결성 해시값 |
| `dependencies` | 해당 패키지의 의존성들 |

### package-lock.json 관리 방법

```bash
# package-lock.json 자동 생성/업데이트
npm install

# package-lock.json만 업데이트 (패키지 설치 없이)
npm install --package-lock-only

# package-lock.json 삭제 후 재생성
rm package-lock.json
npm install

# 특정 패키지 업데이트 시 lock 파일도 함께 업데이트
npm update express
```

## package.json vs package-lock.json 완전 비교

| 구분 | package.json | package-lock.json |
|------|-------------|------------------|
| **목적** | 프로젝트 메타데이터 및 의존성 선언 | 정확한 의존성 버전 및 트리 기록 |
| **버전 지정** | 범위 지정 가능 (`^4.18.2`, `~4.18.2`) | 정확한 버전만 기록 (`4.18.2`) |
| **수정 가능성** | 개발자가 직접 수정 | npm이 자동 생성/관리 |
| **Git 관리** | 반드시 커밋 필요 | 반드시 커밋 필요 |
| **CI/CD 중요도** | 필수 | 필수 (더 중요) |
| **파일 크기** | 작음 | 큼 (의존성 트리 포함) |
| **가독성** | 높음 | 낮음 (자동 생성) |

### 실제 개발 워크플로우에서의 역할

1. **개발자 A가 새 패키지 설치**:
   ```bash
   npm install lodash
   ```
   - package.json에 `"lodash": "^4.17.21"` 추가
   - package-lock.json에 정확한 버전과 의존성 트리 기록

2. **개발자 B가 프로젝트 클론 후 설치**:
   ```bash
   git clone <repository>
   npm install
   ```
   - package-lock.json 덕분에 개발자 A와 동일한 버전 설치

3. **CI/CD 환경에서 배포**:
   - package-lock.json으로 모든 환경에서 동일한 패키지 버전 보장

### 주의사항 및 모범 사례

#### 해야 할 것
- package-lock.json을 Git에 커밋하기
- 팀원들과 package-lock.json 공유하기
- CI/CD에서 package-lock.json 사용하기

#### 하지 말아야 할 것
- package-lock.json을 .gitignore에 추가하기
- package-lock.json을 수동으로 편집하기
- package-lock.json 없이 프로덕션 배포하기

## 참고 자료

- [npm 공식 문서](https://docs.npmjs.com/)
- [package.json 가이드](https://docs.npmjs.com/cli/v8/configuring-npm/package-json)
- [package-lock.json 설명](https://docs.npmjs.com/cli/v8/configuring-npm/package-lock-json)
- [시맨틱 버저닝](https://semver.org/)
- [Node.js 모듈 시스템](https://nodejs.org/api/modules.html)

