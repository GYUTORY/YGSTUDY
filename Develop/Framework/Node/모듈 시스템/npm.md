

# 🚀 npm, package.json, package-lock.json 개념 및 설명

## 1️⃣ npm이란?
**npm (Node Package Manager)** 는 Node.js에서 패키지를 관리하는 도구입니다.  
Node.js 애플리케이션에서 필요한 라이브러리 및 의존성을 쉽게 설치하고 관리할 수 있습니다.

> **👉🏻 npm은 Node.js와 함께 설치되며, 전 세계 개발자들이 공유하는 패키지 레지스트리입니다.**

### ✅ npm 주요 기능
- **패키지 설치** (`npm install <패키지명>`)
- **패키지 업데이트** (`npm update <패키지명>`)
- **패키지 제거** (`npm uninstall <패키지명>`)
- **패키지 버전 관리** (`package.json`, `package-lock.json` 활용)
- **스크립트 실행** (`npm run <스크립트명>`)

### ✨ npm 버전 확인
```bash
npm -v
```

> **👉🏻 위 명령어를 실행하면 설치된 npm 버전을 확인할 수 있습니다.**

---

## 2️⃣ package.json이란?

### ✅ package.json 개념
- 프로젝트의 **설정 및 의존성(Dependencies)을 관리**하는 파일
- 프로젝트에 대한 **메타데이터** (이름, 버전, 설명 등) 포함
- 설치한 패키지 목록과 버전이 기록됨

### ✨ package.json 생성
```bash
npm init
```

> **👉🏻 위 명령어를 실행하면 package.json 파일이 생성되며, 프로젝트 정보를 입력할 수 있습니다.**

### ✅ package.json 예제
```json
{
  "name": "my-project",
  "version": "1.0.0",
  "description": "Node.js 프로젝트 예제",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "nodemon": "^2.0.15"
  }
}
```

> **👉🏻 package.json에는 프로젝트 정보와 패키지 의존성이 기록됩니다.**

#### **🎯 주요 속성**
| 속성 | 설명 |
|------|------|
| `name` | 프로젝트 이름 |
| `version` | 프로젝트 버전 |
| `description` | 프로젝트 설명 |
| `main` | 엔트리 파일 (기본값: `index.js`) |
| `scripts` | 실행 가능한 npm 명령어 정의 |
| `dependencies` | 실제 운영 환경에서 필요한 패키지 목록 |
| `devDependencies` | 개발 환경에서만 필요한 패키지 목록 |

---

## 3️⃣ package-lock.json이란?

### ✅ package-lock.json 개념
- 프로젝트에 설치된 패키지의 **정확한 버전을 기록하는 파일**
- `package.json`이 의존성의 "범위"를 저장한다면, `package-lock.json`은 **정확한 버전**을 저장
- **CI/CD 환경에서 동일한 패키지 버전이 설치되도록 보장**

### ✨ package-lock.json 예제
```json
{
  "name": "my-project",
  "lockfileVersion": 2,
  "requires": true,
  "packages": {
    "node_modules/express": {
      "version": "4.18.2",
      "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
      "integrity": "sha512-xyz",
      "dependencies": {
        "accepts": "^1.3.8",
        "body-parser": "^1.19.0"
      }
    }
  }
}
```

> **👉🏻 package-lock.json은 정확한 패키지 버전을 기록하여 일관된 환경을 유지합니다.**

---

## 4️⃣ npm 명령어 정리

### ✅ 패키지 설치 관련
| 명령어 | 설명 |
|--------|------|
| `npm install` | `package.json`에 정의된 모든 패키지 설치 |
| `npm install <패키지명>` | 특정 패키지 설치 |
| `npm install <패키지명>@<버전>` | 특정 버전의 패키지 설치 |
| `npm install <패키지명> --save-dev` | 개발 의존성 패키지 설치 (`devDependencies`에 추가) |

### ✅ 패키지 제거 관련
| 명령어 | 설명 |
|--------|------|
| `npm uninstall <패키지명>` | 특정 패키지 제거 |

### ✅ 패키지 업데이트
| 명령어 | 설명 |
|--------|------|
| `npm update` | 모든 패키지를 최신 버전으로 업데이트 |
| `npm update <패키지명>` | 특정 패키지를 최신 버전으로 업데이트 |

### ✅ 캐시 및 정리
| 명령어 | 설명 |
|--------|------|
| `npm cache clean --force` | npm 캐시 정리 |

---

## 5️⃣ package.json vs package-lock.json 차이점

| 비교 항목 | package.json | package-lock.json |
|-----------|-------------|------------------|
| **역할** | 프로젝트 정보 및 의존성 관리 | 설치된 패키지의 정확한 버전 기록 |
| **패키지 버전** | `^` 또는 `~`를 포함한 범위 지정 가능 | 특정 버전만 저장 |
| **개발자가 직접 수정 가능?** | ✅ 가능 | ❌ 자동 생성됨 |
| **CI/CD 환경에서 필요?** | 필요 없음 | ✅ 필수 (일관된 패키지 설치 보장) |

> **👉🏻 package.json은 "의존성 선언", package-lock.json은 "정확한 버전 기록"이 목적입니다.**
