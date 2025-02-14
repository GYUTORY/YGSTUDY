# Docker Blue-Green 배포

## 🎯 Blue-Green 배포란?
Blue-Green 배포는 무중단 배포 전략 중 하나로, **현재 운영 중인 환경(Blue)과 신규 배포 환경(Green)을 분리하여 운영**하는 방식입니다. 이를 통해 **배포 시 장애를 최소화**하고 **빠른 롤백이 가능**하도록 합니다.

---

## 🛠 Blue-Green 배포의 핵심 개념
### 1. **Blue (현재 운영 중인 환경)**
현재 서비스가 실행 중인 상태를 의미합니다. 사용자는 이 환경을 통해 애플리케이션을 이용합니다.

### 2. **Green (신규 배포 환경)**
새로운 버전의 애플리케이션을 배포할 환경입니다. 이 환경이 준비되면 트래픽을 Blue에서 Green으로 전환합니다.

### 3. **트래픽 스위칭**
Green 환경이 정상적으로 작동하는지 확인한 후, **로드 밸런서(LB)를 통해 트래픽을 Blue에서 Green으로 변경**합니다.

### 4. **롤백 (Rollback)**
만약 Green 환경에서 문제가 발생하면, 트래픽을 다시 Blue로 돌려 빠르게 원상 복구할 수 있습니다.

---

## 🏗 Docker 기반 Blue-Green 배포 예제

이제 **Docker와 Nginx를 활용한 Blue-Green 배포 예제**를 살펴보겠습니다.

### 📌 기본 개념
- **Blue 컨테이너**: 기존 운영 중인 서비스 (`blue-app`)
- **Green 컨테이너**: 새롭게 배포할 서비스 (`green-app`)
- **Nginx Reverse Proxy**를 사용해 트래픽을 Blue 또는 Green으로 전환

### 📂 프로젝트 구조
```plaintext
blue-green-deploy/
│── nginx/
│   ├── default.conf  # Nginx 설정 파일
│── blue/
│   ├── Dockerfile
│   ├── app.py
│── green/
│   ├── Dockerfile
│   ├── app.py
│── docker-compose.yml
```

---

## 📝 `app.py` 작성 (Blue & Green 동일)
먼저 Blue와 Green 환경에서 실행할 **간단한 Flask 애플리케이션**을 작성합니다.

```python
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, this is the BLUE version!"  # Green에서는 "GREEN version!"으로 변경

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```
> 💡 **포인트**: Blue 환경에서는 `"Hello, this is the BLUE version!"`을 반환하고,  
> Green 환경에서는 `"Hello, this is the GREEN version!"`으로 변경합니다.

---

## 📦 `Dockerfile` 작성 (Blue & Green 동일)

```dockerfile
# 베이스 이미지 설정
FROM python:3.9

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# 애플리케이션 복사
COPY . .

# Flask 실행
CMD ["python", "app.py"]
```
> 💡 `requirements.txt`에는 `Flask` 패키지를 포함해야 합니다.

---

## 📑 `nginx/default.conf` 설정

```nginx
server {
    listen 80;

    location / {
        proxy_pass http://blue:5000;  # 기본적으로 blue 컨테이너로 트래픽 전달
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
> 🚀 **트래픽 스위칭 시** `proxy_pass`를 `green:5000`으로 변경하면 Green 환경으로 전환됩니다.

---

## 📜 `docker-compose.yml` 설정

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:latest
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "80:80"
    depends_on:
      - blue

  blue:
    build:
      context: ./blue
    container_name: blue
    ports:
      - "5001:5000"

  green:
    build:
      context: ./green
    container_name: green
    ports:
      - "5002:5000"
```
> 🎯 처음에는 Blue 컨테이너가 트래픽을 받지만, 설정 변경 후 Green으로 전환 가능!

---

## 🔄 배포 및 트래픽 전환

### 1️⃣ Blue 컨테이너 실행
```bash
docker-compose up -d
```
- `http://localhost/`로 접속하면 `"Hello, this is the BLUE version!"`이 출력됨

### 2️⃣ Green 컨테이너로 전환
- `nginx/default.conf` 파일에서 `proxy_pass`를 `green:5000`으로 변경
- Nginx 재시작
```bash
docker-compose restart nginx
```
- 이제 `http://localhost/` 접속 시 `"Hello, this is the GREEN version!"`이 출력됨

### 3️⃣ 문제가 발생하면 롤백!
- 다시 `proxy_pass`를 `blue:5000`으로 변경 후 Nginx 재시작

---

## ✅ Blue-Green 배포의 장점
- **무중단 배포** 가능
- **빠른 롤백**으로 안정성 확보
- **배포 테스트**를 실제 트래픽 없이 수행 가능

---

## ❗️ Blue-Green 배포 시 고려할 점
- 데이터베이스 변경 시 **마이그레이션 전략** 필요
- 운영 비용 증가 가능 (두 개의 환경을 유지해야 함)
- 트래픽 전환 과정에서 **세션 관리 문제** 발생 가능
