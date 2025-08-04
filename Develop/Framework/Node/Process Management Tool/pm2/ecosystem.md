
# PM2 Ecosystem File

> PM2의 **Ecosystem 파일**은 Node.js 애플리케이션을 관리하고 배포할 때 사용하는 **설정 파일**입니다.  
> 특히 여러 애플리케이션을 관리하거나, 클러스터 모드와 같은 고급 기능을 사용할 때 유용합니다.

---

## 📋 개요

### PM2 에코시스템 파일이란?
- **JavaScript**나 **JSON** 형식으로 작성되는 설정 파일
- `ecosystem.config.js`라는 이름의 파일 사용
- 한 번에 여러 애플리케이션을 설정하고, PM2의 다양한 옵션을 관리 가능

### 주요 기능
- ✅ 클러스터 모드 활성화
- ✅ 자동 재시작 및 메모리 관리
- ✅ 환경 변수 설정
- ✅ 여러 애플리케이션 관리
- ✅ 로그 관리 및 파일 감시

---

## ⚙️ 설정 파일 예제

### 기본 구조 (ecosystem.config.js)

```javascript
module.exports = {
  apps: [
    {
      name: "my-app",              // 애플리케이션 이름
      script: "./app.js",          // 실행할 파일 경로
      instances: "max",            // 모든 CPU 코어를 사용 (클러스터 모드)
      exec_mode: "cluster",        // 클러스터 모드 활성화
      watch: true,                 // 파일 변경 감시 및 자동 재시작
      max_memory_restart: "500M",  // 메모리 사용이 500MB를 초과할 경우 재시작
      env: {                       // 기본 환경 변수 설정
        NODE_ENV: "development"
      },
      env_production: {            // 프로덕션 환경 변수 설정
        NODE_ENV: "production"
      }
    }
  ]
};
```

### 주요 옵션 설명

| 옵션 | 설명 | 예시 |
|------|------|------|
| `name` | 애플리케이션 이름 | `"my-app"` |
| `script` | 실행할 메인 파일 경로 | `"./app.js"` |
| `instances` | 실행할 프로세스 수 | `"max"` (CPU 코어 수만큼) |
| `exec_mode` | 실행 모드 | `"fork"` 또는 `"cluster"` |
| `watch` | 파일 변경 감시 및 자동 재시작 | `true` |
| `max_memory_restart` | 메모리 사용량 초과 시 자동 재시작 | `"500M"` |
| `env` | 개발 환경의 환경 변수 | `{ NODE_ENV: "development" }` |
| `env_production` | 프로덕션 환경의 환경 변수 | `{ NODE_ENV: "production" }` |

---

## 🚀 사용법

### 기본 실행
```bash
pm2 start ecosystem.config.js
```

### 프로덕션 환경에서 실행
```bash
pm2 start ecosystem.config.js --env production
```

---

## 📊 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `pm2 list` | 애플리케이션 상태 확인 |
| `pm2 restart all` | 모든 프로세스 재시작 |
| `pm2 stop all` | 모든 애플리케이션 중지 |
| `pm2 logs` | 로그 확인 |

---

## 🎯 장점

### 1. 고급 구성 가능
- 클러스터 모드, 환경 변수, 메모리 제한 등 다양한 옵션 제공

### 2. 다중 애플리케이션 관리
- 한 파일에서 여러 애플리케이션을 관리할 수 있음

### 3. 간편한 유지보수
- 설정 파일 하나로 모든 설정을 관리 가능

### 4. 자동 장애 복구
- 메모리 제한 초과나 에러 발생 시 자동 재시작

---

## 📝 결론

PM2의 에코시스템 파일은 **대규모 Node.js 애플리케이션**을 관리하는 데 매우 유용합니다.  
특히 **고가용성**, **자동 복구**, **로드 밸런싱**을 손쉽게 구현할 수 있습니다.

---

## 🔗 참고 자료
- [PM2 공식 문서](https://pm2.keymetrics.io/)
