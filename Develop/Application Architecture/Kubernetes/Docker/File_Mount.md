# 🐳 Docker 파일 마운트 완벽 가이드

## 📋 목차
- [개념 이해](#개념-이해)
- [마운트 방식](#마운트-방식)
- [실제 사용법](#실제-사용법)
- [주의사항](#주의사항)

---

## 🎯 개념 이해

### 파일 마운트란?
컴퓨터에서 **"마운트"**는 외부 저장장치(USB, 하드디스크 등)를 컴퓨터에 연결해서 사용할 수 있게 하는 것을 말합니다.

Docker에서 **파일 마운트**는 비슷한 개념으로, **호스트 컴퓨터의 파일이나 폴더를 Docker 컨테이너 안에서 사용할 수 있게 연결**하는 것입니다.

### 왜 파일 마운트가 필요한가?
- **데이터 보존**: 컨테이너를 삭제해도 중요한 데이터는 남아있음
- **개발 효율성**: 코드 수정 시 컨테이너를 다시 빌드할 필요 없음
- **리소스 공유**: 여러 컨테이너가 같은 데이터를 공유 가능

---

## 🔧 마운트 방식

Docker에서는 두 가지 주요 마운트 방식을 제공합니다:

### 1️⃣ 바인드 마운트 (Bind Mount)
**호스트의 특정 경로를 컨테이너에 직접 연결**

#### 특징
- ✅ **직접 연결**: 호스트의 실제 폴더/파일을 그대로 사용
- ✅ **실시간 반영**: 컨테이너에서 수정하면 호스트에도 즉시 반영
- ⚠️ **주의**: 호스트 경로가 없으면 오류 발생

#### 기본 문법
```bash
docker run -v 호스트경로:컨테이너경로 이미지명
```

#### 실제 예시
```bash
# 현재 폴더를 컨테이너의 /app에 연결
docker run -it -v $(pwd):/app ubuntu

# 특정 폴더 연결
docker run -it -v /home/user/project:/workspace node:16
```

### 2️⃣ 볼륨 마운트 (Volume Mount)
**Docker가 관리하는 전용 저장공간 사용**

#### 특징
- ✅ **자동 관리**: Docker가 저장공간을 자동으로 관리
- ✅ **안전성**: 호스트 시스템과 격리되어 보안상 안전
- ✅ **백업 용이**: Docker 명령어로 쉽게 백업 가능

#### 기본 문법
```bash
# 1단계: 볼륨 생성
docker volume create 볼륨이름

# 2단계: 컨테이너에 마운트
docker run -v 볼륨이름:컨테이너경로 이미지명
```

#### 실제 예시
```bash
# 데이터베이스용 볼륨 생성
docker volume create mysql-data

# MySQL 컨테이너에 볼륨 마운트
docker run -d --name mysql \
  -v mysql-data:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=password \
  mysql:8.0
```

---

## 💡 실제 사용법

### 개발 환경에서 사용하기

#### 웹 개발 시나리오
```bash
# 1. 프로젝트 폴더로 이동
cd /home/user/web-project

# 2. 현재 폴더를 컨테이너에 마운트
docker run -it --name dev-server \
  -v $(pwd):/app \
  -p 3000:3000 \
  node:16 bash

# 3. 컨테이너 내부에서 개발 작업
cd /app
npm install
npm start
```

#### 데이터베이스 데이터 보존
```bash
# 1. 데이터용 볼륨 생성
docker volume create postgres-data

# 2. PostgreSQL 컨테이너 실행
docker run -d --name postgres \
  -v postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:13

# 3. 컨테이너 삭제 후에도 데이터는 볼륨에 보존됨
docker rm postgres
```

### 볼륨 관리 명령어

```bash
# 볼륨 목록 확인
docker volume ls

# 볼륨 상세 정보 확인
docker volume inspect 볼륨이름

# 사용하지 않는 볼륨 삭제
docker volume prune

# 특정 볼륨 삭제
docker volume rm 볼륨이름
```

---

## ⚠️ 주의사항

### 바인드 마운트 주의점
1. **경로 존재 확인**: 마운트할 호스트 경로가 반드시 존재해야 함
2. **권한 문제**: 호스트와 컨테이너의 파일 권한이 다를 수 있음
3. **보안 위험**: 호스트의 민감한 파일이 노출될 수 있음

### 볼륨 마운트 주의점
1. **용량 관리**: 볼륨이 계속 쌓이면 디스크 공간 부족 가능
2. **백업 필요**: 중요한 데이터는 정기적으로 백업 필요

### 성능 고려사항
- **바인드 마운트**: 대용량 파일 처리 시 성능 저하 가능
- **볼륨 마운트**: 일반적으로 더 나은 성능 제공

---

## 🔍 고급 설정

### 읽기 전용 마운트
```bash
# 컨테이너에서 수정 불가능하게 설정
docker run -v /host/path:/container/path:ro 이미지명
```

### 여러 볼륨 동시 마운트
```bash
docker run -v volume1:/app/data \
  -v volume2:/app/logs \
  -v /host/config:/app/config \
  이미지명
```

---

## 📚 용어 정리

| 용어 | 설명 |
|------|------|
| **호스트** | Docker가 실행되는 실제 컴퓨터 |
| **컨테이너** | Docker로 생성된 격리된 실행 환경 |
| **마운트** | 외부 저장공간을 시스템에 연결하는 것 |
| **볼륨** | Docker가 관리하는 전용 저장공간 |
| **바인드** | 호스트의 실제 경로를 직접 연결하는 방식 |

---

## 🎯 언제 어떤 방식을 사용할까?

### 바인드 마운트 사용 시기
- 개발 중인 코드를 실시간으로 테스트할 때
- 호스트의 설정 파일을 컨테이너에서 사용할 때
- 로그 파일을 호스트에서 직접 확인하고 싶을 때

### 볼륨 마운트 사용 시기
- 데이터베이스 데이터를 영구 보존하고 싶을 때
- 여러 컨테이너가 같은 데이터를 공유할 때
- 보안이 중요한 데이터를 다룰 때

---

## 📖 추가 학습 자료
- [Docker 공식 문서 - Volumes](https://docs.docker.com/storage/volumes/)
- [Docker 공식 문서 - Bind mounts](https://docs.docker.com/storage/bind-mounts/)
