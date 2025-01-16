
# Node.js와 npm, package.json, package-lock.json에 대한 이해

Node.js는 JavaScript로 서버 측 애플리케이션을 개발할 수 있는 런타임 환경입니다. npm(Node Package Manager)은 Node.js의 기본 패키지 매니저로, 패키지 설치, 관리, 버전 제어 등을 담당합니다.

## 1. package.json

`package.json`은 프로젝트의 메타데이터를 포함하는 JSON 파일로, 다음과 같은 역할을 합니다:

- 프로젝트 이름, 버전, 설명 등의 정보 제공
- 프로젝트에 필요한 의존성 정의
- 스크립트 명령어 정의 (예: `npm start`, `npm test` 등)

### package.json 구조 예시

```json
{
  "name": "example-project",
  "version": "1.0.0",
  "description": "An example Node.js project",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "nodemon": "^3.0.0"
  },
  "author": "Your Name",
  "license": "ISC"
}
```

### 주요 필드 설명
- `name`: 프로젝트 이름
- `version`: 프로젝트 버전
- `dependencies`: 애플리케이션 실행 시 필요한 패키지
- `devDependencies`: 개발 시에만 필요한 패키지
- `scripts`: npm 명령어 정의

---

## 2. package-lock.json

`package-lock.json`은 `npm install` 실행 시 자동으로 생성되는 파일로, 다음과 같은 역할을 합니다:

- 의존성 트리의 정확한 버전을 잠금 처리하여 일관성 보장
- 의존성 설치 속도 향상
- 협업 시 정확한 환경 재현 가능

### package-lock.json 예시

```json
{
  "name": "example-project",
  "version": "1.0.0",
  "lockfileVersion": 2,
  "requires": true,
  "dependencies": {
    "express": {
      "version": "4.18.2",
      "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
      "integrity": "sha512-...",
      "requires": {
        "body-parser": "1.20.0",
        "cookie-parser": "1.4.6"
      }
    }
  }
}
```

### 주요 필드 설명
- `version`: 설치된 패키지의 정확한 버전
- `resolved`: 패키지가 다운로드된 URL
- `integrity`: 패키지 무결성 검증을 위한 해시 값

---

## 3. package.json과 package-lock.json의 차이점

| 항목              | package.json                     | package-lock.json            |
|-------------------|----------------------------------|-----------------------------|
| 생성 시점         | 개발자가 직접 작성 또는 수정     | `npm install` 시 자동 생성 |
| 역할              | 프로젝트 메타데이터 및 의존성 정의 | 정확한 의존성 버전 잠금     |
| 포함 정보         | 의존성 버전 범위                 | 의존성의 정확한 버전 및 경로 |

---

## 4. npm 명령어

- `npm init`: `package.json` 생성
- `npm install [패키지명]`: 패키지 설치 및 `dependencies`에 추가
- `npm install [패키지명] --save-dev`: 패키지 설치 및 `devDependencies`에 추가
- `npm install`: `package.json`에 정의된 모든 패키지 설치

---

## 5. 예제 프로젝트 생성

### 1) 프로젝트 초기화

```bash
mkdir example-project
cd example-project
npm init -y
```

### 2) 패키지 설치

```bash
npm install express
npm install --save-dev nodemon
```

### 3) `index.js` 파일 생성

```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('Hello, World!');
});

app.listen(3000, () => {
  console.log('Server is running on http://localhost:3000');
});
```

### 4) `package.json`에 스크립트 추가

```json
"scripts": {
  "start": "node index.js",
  "dev": "nodemon index.js"
}
```

### 5) 서버 실행

```bash
npm run start
# 또는 개발 중에는
npm run dev
```

---

## 6. 요약

- `package.json`은 프로젝트의 정보를 정의하고 의존성을 관리합니다.
- `package-lock.json`은 의존성의 정확한 버전을 잠금 처리합니다.
- npm 명령어를 활용하여 패키지 설치, 프로젝트 초기화, 스크립트 실행 등을 수행할 수 있습니다.
