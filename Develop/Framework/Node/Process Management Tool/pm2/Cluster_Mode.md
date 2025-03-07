
# PM2 클러스터 모드 (Cluster Mode)

PM2는 Node.js 애플리케이션의 프로세스를 효율적으로 관리하고, **고가용성**과 **부하 분산**을 제공하는 **프로세스 관리자**입니다.  
특히 **클러스터 모드(Cluster Mode)**는 여러 CPU 코어를 활용하여 성능과 안정성을 극대화할 수 있도록 지원합니다.

---

## 👉🏻 PM2 클러스터 모드란?
- 클러스터 모드는 PM2의 내장 기능으로, 단일 애플리케이션을 여러 인스턴스로 실행하여 **멀티코어를 활용**하는 방식입니다.
- **로드 밸런싱**을 통해 여러 요청을 각 인스턴스에 고르게 분배합니다.
- Node.js의 **싱글 스레드** 한계를 극복하고 CPU의 모든 코어를 활용할 수 있습니다.

---

## 🎯 PM2 클러스터 모드 사용법

PM2를 사용하여 애플리케이션을 클러스터 모드로 실행하는 명령어를 소개합니다.

### 1️⃣ 애플리케이션 클러스터 모드 실행

```bash
pm2 start app.js -i max
```

- `-i max`: 사용 가능한 모든 CPU 코어를 사용하여 인스턴스를 실행합니다.
- `app.js`: 실행할 애플리케이션 파일 경로를 지정합니다.

### 2️⃣ 특정 인스턴스 개수 지정

```bash
pm2 start app.js -i 4
```

- `-i 4`: 4개의 인스턴스를 실행합니다. (CPU 코어 수와 무관)

---

## 🏗️ 클러스터 모드 설정 파일 (ecosystem.config.js)

PM2의 설정 파일을 사용하여 클러스터 모드를 구성할 수 있습니다.

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "my-cluster-app",    // 애플리케이션 이름
      script: "app.js",          // 실행할 파일
      instances: "max",          // 모든 CPU 코어를 사용
      exec_mode: "cluster",      // 클러스터 모드 활성화
      watch: true,               // 파일 변경 시 자동 재시작
      max_memory_restart: "1G"   // 메모리 초과 시 재시작
    }
  ]
}
```

### 📌 설정 파일로 실행하기
```bash
pm2 start ecosystem.config.js
```

---

## 🚀 PM2 주요 명령어

### ✅ 현재 실행 중인 애플리케이션 확인
```bash
pm2 list
```

### ✅ 실행 중인 프로세스 상세 확인
```bash
pm2 show <프로세스 ID>
```

### ✅ PM2 대시보드 실행 (모니터링 툴)
```bash
pm2 monit
```

### ✅ 애플리케이션 중지
```bash
pm2 stop all
```

### ✅ 애플리케이션 재시작
```bash
pm2 restart all
```

### ✅ 로그 확인
```bash
pm2 logs
```

---

## PM2 클러스터 모드의 장점

1. **CPU 코어 최대 활용**: 여러 코어를 활용하여 성능 극대화
2. **자동 장애 복구**: 프로세스가 중단되면 자동 재시작
3. **간편한 배포 및 관리**: `ecosystem.config.js` 파일로 쉽고 직관적인 설정 가능
4. **로드 밸런싱**: 트래픽을 여러 프로세스에 고르게 분배

---

## 📌 결론
- PM2 클러스터 모드는 **Node.js** 애플리케이션의 성능을 최대로 끌어올릴 수 있는 강력한 기능입니다.  
- 특히 **CPU 코어를 최대한 활용**하고, **자동 장애 복구**와 **부하 분산** 기능은 프로덕션 환경에서 매우 유용합니다.

---

## 📖 참고 자료
- [PM2 공식 문서](https://pm2.keymetrics.io/)
