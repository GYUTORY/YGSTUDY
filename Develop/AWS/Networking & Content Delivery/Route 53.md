# AWS Route 53

## ✨ AWS Route 53이란?
AWS Route 53은 **Amazon Web Services(AWS)에서 제공하는 확장 가능하고 신뢰할 수 있는 도메인 이름 시스템(DNS) 웹 서비스**입니다.   
웹 애플리케이션의 트래픽을 관리하고, 도메인 이름을 등록하며, 상태 확인을 수행하는 기능을 제공합니다.

### 🎯 Route 53의 이름 유래
Route 53이라는 이름은 DNS 서버가 사용하는 포트 번호인 53번에서 유래했습니다. 이는 DNS 프로토콜이 TCP/UDP 포트 53을 사용하기 때문입니다.

### 💡 Route 53의 주요 특징
- **고가용성**: AWS의 글로벌 인프라를 활용하여 100% 가용성 보장
- **확장성**: 초당 수백만 건의 DNS 쿼리 처리 가능
- **보안**: AWS IAM과 통합된 보안 기능 제공
- **비용 효율성**: 사용한 만큼만 지불하는 과금 방식

---

## 👉🏻 주요 기능 상세 설명

### 1️⃣ **DNS 서비스**
#### DNS 작동 방식
1. 사용자가 도메인 이름을 브라우저에 입력
2. 로컬 DNS 서버가 Route 53에 쿼리
3. Route 53이 해당 도메인의 IP 주소 반환
4. 브라우저가 해당 IP 주소로 연결

#### DNS 레코드 타입 상세 설명
| 레코드 타입 | 설명 | 사용 사례 |
|------------|------|-----------|
| **A 레코드** | IPv4 주소 매핑 | 웹사이트 호스팅 |
| **AAAA 레코드** | IPv6 주소 매핑 | IPv6 지원 웹사이트 |
| **CNAME 레코드** | 도메인 별칭 | 서브도메인 설정 |
| **MX 레코드** | 메일 서버 지정 | 이메일 서비스 구성 |
| **TXT 레코드** | 도메인 검증 | SPF, DKIM 설정 |
| **NS 레코드** | 네임서버 지정 | DNS 위임 설정 |
| **SOA 레코드** | 영역 권한 정보 | DNS 영역 관리 |

### 2️⃣ **도메인 등록**
#### 도메인 등록 프로세스
1. 도메인 이름 검색 및 가용성 확인
2. 도메인 등록 기간 선택 (1-10년)
3. 개인정보 보호 서비스 선택
4. 결제 및 등록 완료

#### 도메인 등록 시 고려사항
- **TLD(Top Level Domain) 선택**: .com, .net, .org 등
- **도메인 가격**: TLD별로 다른 가격 정책
- **자동 갱신**: 도메인 만료 방지를 위한 설정
- **이전 보호**: 도메인 도용 방지 설정

### 3️⃣ **트래픽 관리**
#### 라우팅 정책 상세 설명

1. **단순(Simple) 라우팅**
   - 단일 리소스에 대한 기본 라우팅
   - 사용 사례: 단일 서버 웹사이트

2. **가중치(Weighted) 라우팅**
   - 트래픽 분배 비율 설정
   - 사용 사례: A/B 테스트, 점진적 배포

3. **지리적(Geolocation) 라우팅**
   - 사용자 위치 기반 라우팅
   - 사용 사례: 지역별 콘텐츠 제공

4. **지연 시간(Latency-based) 라우팅**
   - 최저 지연 시간 기준 라우팅
   - 사용 사례: 글로벌 서비스 최적화

5. **Failover 라우팅**
   - 장애 발생 시 대체 리소스로 전환
   - 사용 사례: 고가용성 구성

6. **다중값(Multivalue) 라우팅**
   - 여러 리소스에 대한 랜덤 분배
   - 사용 사례: 로드 밸런싱

### 4️⃣ **상태 확인 및 헬스 체크**
#### 헬스 체크 유형
1. **HTTP/HTTPS 체크**
   - 웹 서버 상태 모니터링
   - 상태 코드 확인 (200 OK 등)

2. **TCP 체크**
   - 포트 연결성 확인
   - 데이터베이스 서버 모니터링

3. **CALCULATED 체크**
   - 여러 엔드포인트 종합 평가
   - 복합적인 상태 확인

#### 헬스 체크 설정 옵션
- **인터벌**: 10초, 30초
- **타임아웃**: 5초, 10초
- **연속 실패 임계값**: 3회
- **연속 성공 임계값**: 3회

---

## 🛠️ 실전 Route 53 설정 가이드

### 1️⃣ Route 53에서 도메인 등록하기
#### 상세 단계
1. AWS 콘솔 로그인
2. Route 53 서비스 선택
3. Domains > Register Domain 클릭
4. 도메인 이름 입력 및 검색
5. TLD 선택 및 가격 확인
6. 등록 기간 선택
7. 연락처 정보 입력
8. 개인정보 보호 서비스 선택
9. 결제 정보 입력
10. 등록 확인 및 완료

### 2️⃣ 호스팅 영역(Hosted Zone) 설정
#### 호스팅 영역 유형
1. **Public Hosted Zone**
   - 공개적으로 접근 가능한 도메인
   - 인터넷에서 조회 가능

2. **Private Hosted Zone**
   - VPC 내부에서만 사용
   - 내부 DNS 관리

#### 호스팅 영역 생성 프로세스
1. Route 53 콘솔 접속
2. Hosted Zones 선택
3. Create Hosted Zone 클릭
4. 도메인 이름 입력
5. 호스팅 영역 유형 선택
6. VPC 선택 (Private Hosted Zone의 경우)
7. 생성 확인

### 3️⃣ DNS 레코드 설정
#### A 레코드 설정 예시
```hcl
resource "aws_route53_record" "www" {
  zone_id = aws_route53_zone.example.zone_id
  name    = "www.example.com"
  type    = "A"
  ttl     = 300
  records = ["192.0.2.1"]
}
```

#### CNAME 레코드 설정 예시
```hcl
resource "aws_route53_record" "blog" {
  zone_id = aws_route53_zone.example.zone_id
  name    = "blog.example.com"
  type    = "CNAME"
  ttl     = 300
  records = ["example.com"]
}
```

#### MX 레코드 설정 예시
```hcl
resource "aws_route53_record" "mx" {
  zone_id = aws_route53_zone.example.zone_id
  name    = "example.com"
  type    = "MX"
  ttl     = 300
  records = [
    "10 mail1.example.com",
    "20 mail2.example.com"
  ]
}
```

---

## 🎯 고급 Route 53 사용 사례

### 1️⃣ 다중 리전 배포
#### 구성 방법
1. 각 리전에 애플리케이션 배포
2. 지연 시간 기반 라우팅 설정
3. 헬스 체크 구성
4. 장애 조치 설정

### 2️⃣ 도메인 위임
#### 위임 프로세스
1. 부모 도메인 NS 레코드 확인
2. 자식 도메인 NS 레코드 설정
3. 위임 확인

### 3️⃣ SSL 인증서 관리
#### ACM과 통합
1. AWS Certificate Manager에서 인증서 요청
2. DNS 검증 방식 선택
3. Route 53에 검증 레코드 자동 생성

---

## 💰 Route 53 비용 구조

### 1️⃣ 도메인 등록 비용
- .com: $12.00/년
- .net: $12.00/년
- .org: $15.00/년

### 2️⃣ 호스팅 영역 비용
- Public Hosted Zone: $0.50/월
- Private Hosted Zone: $0.50/월

### 3️⃣ 쿼리 비용
- 표준 쿼리: $0.40/백만 쿼리
- 지연 시간 기반 라우팅: $0.60/백만 쿼리
- 지리적 라우팅: $0.70/백만 쿼리

---

## 🔍 Route 53 모니터링 및 로깅

### 1️⃣ CloudWatch 통합
- DNS 쿼리 모니터링
- 헬스 체크 상태 추적
- 알림 설정

### 2️⃣ CloudTrail 통합
- API 호출 로깅
- 변경 이력 추적
- 보안 감사

---

## 🚀 Route 53 모범 사례

### 1️⃣ 보안 모범 사례
- IAM 정책 최소 권한 원칙 적용
- DNSSEC 활성화
- 도메인 자동 갱신 설정

### 2️⃣ 성능 모범 사례
- TTL 값 최적화
- 캐시 활용
- 지연 시간 기반 라우팅 활용

### 3️⃣ 가용성 모범 사례
- 다중 리전 배포
- 장애 조치 구성
- 정기적인 헬스 체크

---

## 📚 참고 자료
- [AWS Route 53 공식 문서](https://docs.aws.amazon.com/Route53/)
- [Route 53 개발자 가이드](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/)
- [Route 53 API 참조](https://docs.aws.amazon.com/Route53/latest/APIReference/)

