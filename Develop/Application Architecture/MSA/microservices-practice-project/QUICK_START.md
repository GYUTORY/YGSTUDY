# 🚀 마이크로서비스 실습 프로젝트 빠른 시작 가이드

## 📋 사전 요구사항

- Docker & Docker Compose
- Node.js 18+ (개발 모드 실행 시)
- Git

## ⚡ 빠른 시작 (Docker Compose)

### 1. 프로젝트 클론 및 이동
```bash
cd /Users/kkyung/Desktop/workspace/Project/YGSTUDY/Develop/Application\ Architecture/MSA/microservices-practice-project
```

### 2. 환경 변수 설정
```bash
# 각 서비스별로 환경 변수 파일 복사
cp api-gateway/env.example api-gateway/.env
cp user-service/env.example user-service/.env
cp order-service/env.example order-service/.env
cp payment-service/env.example payment-service/.env
```

### 3. 전체 스택 실행
```bash
# 모든 서비스 및 인프라 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

### 4. 서비스 상태 확인
```bash
# API Gateway 헬스체크
curl http://localhost:3000/health

# 개별 서비스 헬스체크
curl http://localhost:3001/health  # User Service
curl http://localhost:3002/health  # Order Service
curl http://localhost:3003/health  # Payment Service
```

## 🧪 API 테스트

### 1. 사용자 등록
```bash
curl -X POST http://localhost:3000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User"
  }'
```

### 2. 사용자 로그인
```bash
curl -X POST http://localhost:3000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 3. 주문 생성 (JWT 토큰 필요)
```bash
# 위에서 받은 토큰을 사용
TOKEN="your-jwt-token-here"

curl -X POST http://localhost:3000/api/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "items": [
      {
        "productId": "product-1",
        "quantity": 2,
        "price": 29.99
      }
    ],
    "shippingAddress": {
      "street": "123 Main St",
      "city": "Seoul",
      "zipCode": "12345"
    }
  }'
```

### 4. 결제 처리
```bash
curl -X POST http://localhost:3000/api/payments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "orderId": "order-id-from-previous-step",
    "amount": 59.98,
    "paymentMethod": "credit_card",
    "cardDetails": {
      "number": "4111111111111111",
      "expiry": "12/25",
      "cvv": "123"
    }
  }'
```

## 🔧 개발 모드 실행

### 1. 의존성 설치
```bash
# 각 서비스별로 의존성 설치
cd api-gateway && npm install
cd ../user-service && npm install
cd ../order-service && npm install
cd ../payment-service && npm install
```

### 2. 인프라만 Docker로 실행
```bash
# 데이터베이스와 Redis만 실행
docker-compose up -d mongodb-user mongodb-order mongodb-payment redis
```

### 3. 서비스별 개발 서버 실행
```bash
# 각 터미널에서 개별 실행
npm run dev:gateway    # API Gateway (포트 3000)
npm run dev:user       # User Service (포트 3001)
npm run dev:order      # Order Service (포트 3002)
npm run dev:payment    # Payment Service (포트 3003)
```

## 📊 모니터링

### 1. 서비스 로그 확인
```bash
# 특정 서비스 로그
docker-compose logs -f api-gateway
docker-compose logs -f user-service
docker-compose logs -f order-service
docker-compose logs -f payment-service

# 모든 서비스 로그
docker-compose logs -f
```

### 2. 데이터베이스 접속
```bash
# MongoDB 접속 (User Service)
docker exec -it mongodb-user mongosh -u admin -p password123

# MongoDB 접속 (Order Service)
docker exec -it mongodb-order mongosh -u admin -p password123

# MongoDB 접속 (Payment Service)
docker exec -it mongodb-payment mongosh -u admin -p password123

# Redis 접속
docker exec -it redis redis-cli
```

### 3. Grafana 대시보드 (선택사항)
```bash
# Grafana 접속
open http://localhost:3001
# 사용자명: admin, 비밀번호: admin123
```

## 🛠️ 문제 해결

### 일반적인 문제들

1. **포트 충돌**
   ```bash
   # 포트 사용 확인
   lsof -i :3000
   lsof -i :3001
   lsof -i :3002
   lsof -i :3003
   ```

2. **Docker 컨테이너 재시작**
   ```bash
   # 특정 서비스 재시작
   docker-compose restart api-gateway
   
   # 전체 재시작
   docker-compose down && docker-compose up -d
   ```

3. **데이터베이스 연결 문제**
   ```bash
   # MongoDB 컨테이너 상태 확인
   docker-compose ps mongodb-user
   
   # MongoDB 로그 확인
   docker-compose logs mongodb-user
   ```

4. **Redis 연결 문제**
   ```bash
   # Redis 컨테이너 상태 확인
   docker-compose ps redis
   
   # Redis 연결 테스트
   docker exec -it redis redis-cli ping
   ```

### 로그 레벨 변경
```bash
# 환경 변수로 로그 레벨 설정
export LOG_LEVEL=debug

# 또는 .env 파일에서
echo "LOG_LEVEL=debug" >> api-gateway/.env
```

## 🔄 서비스 간 통신 테스트

### 1. gRPC 통신 테스트
```bash
# gRPC 클라이언트로 테스트 (grpcurl 설치 필요)
grpcurl -plaintext localhost:50051 user.UserService/GetUser -d '{"user_id": "user-id"}'
```

### 2. Redis Pub/Sub 테스트
```bash
# Redis CLI에서 이벤트 발행
docker exec -it redis redis-cli
> PUBLISH events:user.created '{"id": "evt_123", "type": "user.created", "data": {"userId": "user-123"}}'
```

## 📈 성능 테스트

### 1. 부하 테스트 (Apache Bench)
```bash
# API Gateway 부하 테스트
ab -n 1000 -c 10 http://localhost:3000/health

# 사용자 등록 부하 테스트
ab -n 100 -c 5 -p user-register.json -T application/json http://localhost:3000/api/users/register
```

### 2. 메모리 사용량 확인
```bash
# Docker 컨테이너 리소스 사용량
docker stats

# 특정 서비스 메모리 사용량
docker stats api-gateway user-service order-service payment-service
```

## 🧹 정리

### 1. 서비스 중지
```bash
# 모든 서비스 중지
docker-compose down

# 볼륨까지 삭제 (데이터 삭제)
docker-compose down -v
```

### 2. 로그 정리
```bash
# 로그 파일 정리
rm -rf */logs/*
rm -rf logs/*
```

## 📚 추가 학습 자료

- [마이크로서비스 운영 및 장애 대응 가이드](../마이크로서비스_운영_및_장애_대응_가이드.md)
- [멀티레포 vs 모노레포 비교](../멀티%20레포.md)
- [시스템 설계 및 아키텍처 패턴 가이드](../시스템_설계_및_아키텍처_패턴_가이드.md)

## 🆘 도움이 필요하신가요?

문제가 발생하거나 질문이 있으시면:
1. 로그를 확인해보세요
2. 헬스체크 엔드포인트를 확인해보세요
3. Docker 컨테이너 상태를 확인해보세요
4. 네트워크 연결을 확인해보세요
