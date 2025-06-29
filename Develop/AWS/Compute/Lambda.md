# AWS Lambda란 무엇인가?

> 💡 **서버리스 컴퓨팅의 핵심 서비스**
> 
> AWS Lambda는 서버를 직접 관리하지 않고도 코드를 실행할 수 있게 해주는 AWS의 핵심 서비스입니다.

## 📋 목차
- [기본 개념](#lambda의-기본-개념)
- [왜 Lambda가 필요한가?](#왜-lambda가-필요한가)
- [언제 Lambda를 사용해야 하는가?](#언제-lambda를-사용해야-하는가)
- [Lambda의 한계와 주의사항](#lambda의-한계와-주의사항)
- [AWS Fargate와 Lambda의 차이](#aws-fargate와-lambda의-차이)
- [실무 활용 예시](#실무에서의-lambda-활용-예시)
- [아키텍처 설계 팁](#lambda-아키텍처-설계-팁)
- [실전 경험담](#실전-경험담-및-베스트-프랙티스)

---

## Lambda의 기본 개념

### 🔍 핵심 용어 정리

| 용어 | 설명 |
|------|------|
| **서버리스(Serverless)** | 서버를 직접 관리하지 않고도 애플리케이션을 실행할 수 있는 방식 |
| **이벤트 기반(Event-driven)** | 특정 사건(이벤트)이 발생했을 때만 코드가 실행되는 방식 |
| **프로비저닝(Provisioning)** | 서버나 인프라를 준비하고 설정하는 과정 |
| **오토스케일링(Auto Scaling)** | 트래픽에 따라 자동으로 서버 수를 조절하는 기능 |
| **워크로드(Workload)** | 시스템이 처리해야 하는 작업량이나 부하 |

### 🎯 Lambda란?

AWS Lambda는 아마존 웹 서비스(Amazon Web Services, AWS)에서 제공하는 **서버리스 컴퓨팅 서비스**입니다. 

> **서버리스**라는 용어에서 알 수 있듯이, 사용자는 서버를 직접 관리하거나 프로비저닝할 필요 없이 코드를 실행할 수 있습니다.

Lambda는 **이벤트 기반**으로 동작하며, 사용자가 정의한 이벤트(예: S3에 파일 업로드, DynamoDB에 데이터 삽입, API Gateway 호출 등)가 발생할 때마다 지정된 코드를 자동으로 실행합니다.

### 🏗️ Lambda의 동작 원리

```
📁 사용자 코드 업로드 → ⚡ AWS 인프라 관리 → 🎯 이벤트 발생 → 🚀 자동 실행
```

1. **코드 업로드**: 사용자가 비즈니스 로직 코드를 Lambda에 업로드
2. **인프라 관리**: AWS가 서버, OS, 네트워크 등을 자동으로 관리
3. **이벤트 대기**: 특정 이벤트가 발생할 때까지 대기
4. **자동 실행**: 이벤트 발생 시 코드를 자동으로 실행

### ✨ 주요 특징

| 특징 | 설명 | 장점 |
|------|------|------|
| **이벤트 기반 실행** | 특정 이벤트가 발생할 때마다 자동으로 실행 | 수동 개입 불필요 |
| **자동 확장** | 동시에 수천, 수만 개의 이벤트도 병렬 처리 | 트래픽 대응 자동화 |
| **과금 방식** | 실행된 시간(밀리초)과 사용한 메모리에 따라 과금 | 사용한 만큼만 비용 |
| **서버 관리 불필요** | 인프라 관리 작업이 전혀 필요 없음 | 개발에만 집중 가능 |
| **다양한 언어 지원** | Python, Node.js, Java, Go, C#, Ruby 등 | 기존 기술 스택 활용 |

---

## 왜 Lambda가 필요한가?

### 🆚 기존 방식 vs Lambda 방식

#### 기존 방식 (EC2, ECS 등)
```
💰 서버 구매/임대 → 🔧 서버 설정 → 📊 용량 예측 → ⚙️ 오토스케일링 설정 → 🛠️ 지속적 관리
```

#### Lambda 방식
```
📝 코드 작성 → ⬆️ 업로드 → 🎯 이벤트 설정 → ✅ 완료
```

### 🎯 Lambda가 필요한 이유

#### 1. 🏗️ 서버 관리의 부담 해소

**기존 문제점:**
- 서버 구매, 설정, 유지보수 필요
- 용량 예측의 어려움
- 오토스케일링 설정 복잡성
- 패치, 보안 업데이트 지속적 필요

**Lambda 해결책:**
- 서버 관리 완전 자동화
- 용량 걱정 불필요
- 확장성 자동 처리
- 인프라 관리 시간 절약

#### 2. 💰 비용 효율성

| 서비스 | 과금 방식 | 비용 효율성 |
|--------|-----------|-------------|
| **EC2/ECS** | 인스턴스 실행 시간 전체 | 트래픽 적을 때도 비용 발생 |
| **Lambda** | 실제 실행 시간만 (밀리초 단위) | 사용하지 않으면 비용 0원 |

> **예시**: 하루에 10분만 실행되는 작업
> - EC2: 24시간 × 비용 = 높은 비용
> - Lambda: 10분 × 비용 = 매우 낮은 비용

#### 3. ⚡ 빠른 개발 및 배포

**기존 방식:**
```
코드 작성 → 서버 준비 → 배포 설정 → 테스트 → 수정 → 재배포
```

**Lambda 방식:**
```
코드 작성 → 업로드 → 테스트 → 수정 → 재업로드
```

#### 4. 📈 자동 확장

**시나리오**: 동시에 1,000개의 이미지 업로드 요청

- **기존 방식**: 서버 부족으로 일부 요청 실패
- **Lambda 방식**: 1,000개의 인스턴스 자동 생성하여 모든 요청 처리

#### 5. 🔗 다양한 활용 사례

| 활용 분야 | 설명 | 예시 |
|-----------|------|------|
| **API 백엔드** | REST API, GraphQL API의 백엔드 | 사용자 인증, 데이터 조회 |
| **데이터 처리** | 파일 처리, 변환, 분석 | 이미지 리사이징, 로그 분석 |
| **자동화** | 인프라 관리, 배치 작업 | 백업, 알림 시스템 |
| **IoT** | IoT 디바이스 이벤트 처리 | 센서 데이터 수집, 분석 |

---

## 언제 Lambda를 사용해야 하는가?

### ✅ Lambda가 적합한 상황

#### 1. 🎯 이벤트 기반 아키텍처

**적합한 경우:**
- 파일 업로드 시 자동 처리
- 데이터베이스 변경 시 알림
- 메시지 큐 수신 시 처리
- API 호출 시 응답

**예시:**
```javascript
// S3에 이미지 업로드 → Lambda 자동 실행 → 썸네일 생성
// DynamoDB 데이터 삽입 → Lambda 자동 실행 → 이메일 발송
```

#### 2. 📊 간헐적이거나 예측 불가능한 트래픽

**특징:**
- 트래픽이 일정하지 않음
- 특정 시간에만 사용량 증가
- 예측하기 어려운 사용 패턴

**Lambda의 장점:**
- 사용하지 않을 때 비용 0원
- 트래픽 증가 시 자동 확장
- 과도한 용량 준비 불필요

#### 3. 🧪 빠른 프로토타이핑 및 실험

**개발 단계에서 유용:**
- 새로운 기능 빠른 테스트
- 아이디어 검증
- MVP(최소 기능 제품) 개발
- A/B 테스트

#### 4. 🏗️ 마이크로서비스 아키텍처

**장점:**
- 각 기능을 독립적인 함수로 분리
- 서비스별 독립적 배포/수정
- 장애 격리
- 팀별 독립적 개발

#### 5. 🛠️ 서버 관리가 불필요한 경우

**관리 부담이 없는 경우:**
- OS 패치 관리 불필요
- 보안 업데이트 자동화
- 모니터링 자동화
- 백업 자동화

### ❌ Lambda가 부적합한 상황

#### 1. ⏰ 장시간 실행 작업
- **제한**: 최대 15분 실행 시간
- **대안**: AWS Fargate, EC2 사용

#### 2. 💾 상태 유지가 필요한 작업
- **특징**: Lambda는 무상태(Stateless)
- **대안**: 세션 정보는 외부 저장소 사용

#### 3. 🔄 지속적인 연결 유지
- **특징**: WebSocket 등 장시간 연결 불가
- **대안**: API Gateway WebSocket + Lambda

---

## Lambda의 한계와 주의사항

### ⚠️ 주요 한계점

| 한계 | 설명 | 영향 |
|------|------|------|
| **실행 시간 제한** | 최대 15분까지만 실행 가능 | 장시간 작업 불가 |
| **콜드 스타트** | 오랫동안 미사용 후 첫 실행 시 지연 | 응답 시간 증가 |
| **로컬 디스크 제한** | /tmp 디렉토리만 사용 가능 (최대 10GB) | 대용량 파일 처리 제한 |
| **언어/라이브러리 제한** | 지원하지 않는 언어나 라이브러리 사용 불가 | 기술 스택 제약 |
| **동시 실행 제한** | 계정별 동시 실행 제한 (기본 1,000개) | 대용량 트래픽 제약 |

### 🔍 상세 설명

#### 1. 콜드 스타트 (Cold Start)

**정의**: Lambda 함수가 오랫동안 호출되지 않다가 다시 호출될 때 발생하는 초기화 지연

**원인:**
- 컨테이너 초기화 시간
- 런타임 환경 준비
- 코드 로딩 시간

**해결 방법:**
- 프로비저닝된 동시성 사용
- 정기적인 워밍업 호출
- 함수 크기 최소화

#### 2. 메모리 제한

**현재 제한:**
- 최소: 128MB
- 최대: 10,240MB (10GB)
- 단위: 1MB 단위로 설정

**메모리와 성능의 관계:**
- 메모리가 클수록 CPU 성능도 향상
- 비용도 메모리 크기에 비례하여 증가

---

## AWS Fargate와 Lambda의 차이

### 🔄 서버리스 컴퓨팅의 두 가지 접근 방식

| 구분 | AWS Lambda | AWS Fargate |
|------|------------|-------------|
| **실행 단위** | 함수(코드) | 컨테이너(이미지) |
| **최대 실행 시간** | 15분 | 제한 없음 |
| **사용 목적** | 이벤트 기반, 짧은 작업 | 장시간 실행, 복잡한 서비스 |
| **상태 관리** | 무상태(Stateless) | 상태 관리 가능 |
| **배포 방식** | 코드 업로드 | 컨테이너 이미지 배포 |
| **언어/환경** | 지원 언어 제한 | 모든 언어/환경 가능 |
| **비용** | 실행 시간/메모리 기준 | vCPU/메모리 기준 |
| **확장성** | 자동 확장 | ECS/EKS 오토스케일링 |

### 🎯 선택 가이드

#### Lambda 선택 시기
- ✅ 짧고 간단한 작업
- ✅ 이벤트 기반 아키텍처
- ✅ 서버 관리 불필요
- ✅ 빠른 배포와 실험
- ✅ 비용 최적화 중요

#### Fargate 선택 시기
- ✅ 장시간 실행 작업
- ✅ 복잡한 라이브러리 필요
- ✅ 컨테이너 기반 아키텍처
- ✅ 상태 유지 필요
- ✅ 커스텀 런타임 필요

---

## 실무에서의 Lambda 활용 예시

### 🖼️ 1. S3 파일 업로드 트리거

**시나리오**: 사용자가 S3 버킷에 이미지를 업로드하면 자동으로 썸네일 생성

```javascript
// Lambda 함수 예시 (Node.js)
exports.handler = async (event) => {
    const s3 = new AWS.S3();
    
    // S3 이벤트에서 파일 정보 추출
    const bucket = event.Records[0].s3.bucket.name;
    const key = event.Records[0].s3.object.key;
    
    // 이미지 다운로드
    const image = await s3.getObject({Bucket: bucket, Key: key}).promise();
    
    // 썸네일 생성 (Sharp 라이브러리 사용)
    const thumbnail = await sharp(image.Body)
        .resize(200, 200)
        .toBuffer();
    
    // 썸네일을 다른 버킷에 저장
    await s3.putObject({
        Bucket: 'thumbnail-bucket',
        Key: `thumbnails/${key}`,
        Body: thumbnail
    }).promise();
    
    return {statusCode: 200, body: 'Thumbnail created successfully'};
};
```

**장점:**
- 서버 관리 불필요
- 트래픽 증가 시 자동 확장
- 비용 효율적

### 📊 2. 실시간 데이터 처리

**시나리오**: IoT 센서 데이터를 Kinesis로 수집하고 Lambda로 실시간 분석

```javascript
// Lambda 함수 예시
exports.handler = async (event) => {
    for (const record of event.Records) {
        const data = JSON.parse(record.kinesis.data);
        
        // 온도 이상 감지
        if (data.temperature > 30) {
            await sendAlert({
                sensorId: data.sensorId,
                temperature: data.temperature,
                timestamp: data.timestamp
            });
        }
        
        // 데이터베이스에 저장
        await saveToDatabase(data);
    }
};
```

### 🌐 3. API 백엔드

**시나리오**: API Gateway + Lambda로 서버리스 REST API 구축

```javascript
// 사용자 조회 API 예시
exports.getUser = async (event) => {
    const userId = event.pathParameters.id;
    
    try {
        const user = await getUserFromDatabase(userId);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify(user)
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({error: 'Internal server error'})
        };
    }
};
```

### 🤖 4. Slack/Discord 챗봇

**시나리오**: 메신저에서 명령어 입력 시 Lambda가 정보 조회

```javascript
// Slack 봇 예시
exports.handler = async (event) => {
    const body = JSON.parse(event.body);
    const command = body.text;
    
    let response = '';
    
    switch(command) {
        case 'weather':
            response = await getWeatherInfo();
            break;
        case 'status':
            response = await getSystemStatus();
            break;
        default:
            response = '알 수 없는 명령어입니다.';
    }
    
    return {
        statusCode: 200,
        body: JSON.stringify({
            text: response
        })
    };
};
```

### ⏰ 5. 자동화 및 배치 작업

**시나리오**: CloudWatch Events로 정기적인 배치 작업 실행

```javascript
// 매일 자정에 실행되는 배치 작업
exports.handler = async (event) => {
    console.log('배치 작업 시작:', new Date().toISOString());
    
    // 1. 데이터 집계
    const aggregatedData = await aggregateDailyData();
    
    // 2. 리포트 생성
    const report = await generateReport(aggregatedData);
    
    // 3. 이메일 발송
    await sendEmail({
        to: 'admin@company.com',
        subject: '일일 리포트',
        body: report
    });
    
    console.log('배치 작업 완료');
};
```

---

## Lambda 아키텍처 설계 팁

### 🏗️ 설계 원칙

#### 1. 📦 함수는 작고 단순하게

**좋은 예:**
```javascript
// 하나의 함수, 하나의 역할
exports.processImage = async (event) => {
    // 이미지 처리만 담당
    return await resizeImage(event.imageData);
};
```

**나쁜 예:**
```javascript
// 하나의 함수가 여러 역할 담당
exports.processEverything = async (event) => {
    // 이미지 처리 + 데이터베이스 저장 + 이메일 발송
    // 너무 많은 책임을 가짐
};
```

#### 2. 🔧 환경 변수 활용

```javascript
// 환경 변수로 설정 관리
const DATABASE_URL = process.env.DATABASE_URL;
const API_KEY = process.env.API_KEY;
const ENVIRONMENT = process.env.ENVIRONMENT;

// 환경별 다른 동작
if (ENVIRONMENT === 'production') {
    // 프로덕션 로직
} else {
    // 개발 로직
}
```

#### 3. 📊 로깅과 모니터링

```javascript
// 구조화된 로깅
exports.handler = async (event) => {
    const requestId = event.requestContext.requestId;
    
    console.log('요청 시작', {
        requestId,
        timestamp: new Date().toISOString(),
        eventType: event.type
    });
    
    try {
        const result = await processRequest(event);
        
        console.log('요청 성공', {
            requestId,
            result: result
        });
        
        return result;
    } catch (error) {
        console.error('요청 실패', {
            requestId,
            error: error.message,
            stack: error.stack
        });
        
        throw error;
    }
};
```

#### 4. 🛡️ 에러 처리

```javascript
// 재시도 로직과 DLQ 활용
exports.handler = async (event) => {
    const maxRetries = 3;
    let retryCount = 0;
    
    while (retryCount < maxRetries) {
        try {
            return await processEvent(event);
        } catch (error) {
            retryCount++;
            
            if (retryCount >= maxRetries) {
                // 최대 재시도 횟수 초과 시 DLQ로 전송
                throw error;
            }
            
            // 지수 백오프로 재시도
            await new Promise(resolve => 
                setTimeout(resolve, Math.pow(2, retryCount) * 1000)
            );
        }
    }
};
```

#### 5. 🔐 보안

```javascript
// 최소 권한 원칙 적용
// IAM 정책 예시
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::my-bucket/*"
        }
    ]
}
```

#### 6. 📚 패키지 관리

```javascript
// Lambda Layer 활용
// 공통 라이브러리를 Layer로 분리
const commonUtils = require('/opt/nodejs/common-utils');
const database = require('/opt/nodejs/database');

exports.handler = async (event) => {
    // Layer의 공통 라이브러리 사용
    const result = await commonUtils.processData(event);
    await database.save(result);
};
```

#### 7. ⚡ 콜드 스타트 최소화

**최적화 방법:**
- VPC 연결 최소화
- 패키지 크기 줄이기
- 프로비저닝된 동시성 사용
- 불필요한 초기화 코드 제거

```javascript
// 전역 변수로 초기화 최소화
const s3 = new AWS.S3();
const dynamodb = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {
    // 핸들러 내부에서 매번 초기화하지 않음
    const result = await s3.getObject({...}).promise();
    await dynamodb.put({...}).promise();
};
```

#### 8. 🎛️ 동시성 제어

```javascript
// 함수별 동시성 제한 설정
// AWS CLI 예시
aws lambda put-function-concurrency \
    --function-name my-function \
    --reserved-concurrent-executions 100
```

---

## 실전 경험담 및 베스트 프랙티스

### 💼 실제 사례

#### 🖼️ 사례 1: 이미지 변환 서비스

**상황**: 스타트업의 이미지 업로드 서비스

**기존 방식 (EC2):**
- 트래픽 증가 시 서버 부족으로 장애 발생
- 24시간 서버 운영으로 높은 비용
- 수동 스케일링으로 인한 지연

**Lambda 전환 후:**
- 자동 확장으로 장애 없음
- 사용량에 비례한 비용으로 70% 절감
- 개발팀이 인프라 관리에서 해방

**핵심 학습:**
```javascript
// 이미지 처리 최적화
const sharp = require('sharp');

exports.handler = async (event) => {
    // 메모리 사용량 최적화
    const image = await sharp(event.imageBuffer)
        .resize(800, 600, {fit: 'inside'})
        .jpeg({quality: 80})
        .toBuffer();
    
    return image;
};
```

#### 📱 사례 2: 실시간 알림 시스템

**상황**: 대형 커머스 플랫폼의 알림 시스템

**구현:**
- 주문, 결제, 배송 이벤트를 SNS로 발행
- Lambda가 이벤트를 수신하여 알림 처리
- 다양한 채널(이메일, SMS, 푸시)로 발송

**성과:**
- 실시간 알림으로 고객 만족도 향상
- 장애 상황 빠른 감지 및 대응
- 운영 비용 60% 절감

#### 💰 사례 3: 비용 최적화

**상황**: 기존 EC2 배치 작업을 Lambda로 전환

**비용 비교:**
| 항목 | EC2 (월) | Lambda (월) | 절감률 |
|------|----------|-------------|--------|
| 인스턴스 비용 | $300 | $50 | 83% |
| 관리 비용 | $200 | $0 | 100% |
| **총 비용** | **$500** | **$50** | **90%** |

**핵심 인사이트:**
- 간헐적 작업에는 Lambda가 압도적으로 유리
- 관리 비용 절감 효과가 큼
- 예측 가능한 비용 구조

### 🎯 베스트 프랙티스 체크리스트

#### 설계 단계
- [ ] 함수는 단일 책임 원칙 준수
- [ ] 환경 변수로 설정 분리
- [ ] 에러 처리 및 재시도 로직 구현
- [ ] 보안 정책 최소 권한 원칙 적용

#### 개발 단계
- [ ] 구조화된 로깅 구현
- [ ] 패키지 크기 최적화
- [ ] 콜드 스타트 최소화
- [ ] 동시성 제한 설정

#### 운영 단계
- [ ] CloudWatch 모니터링 설정
- [ ] 알람 및 알림 구성
- [ ] 비용 모니터링
- [ ] 성능 최적화

### 🚀 성능 최적화 팁

#### 1. 메모리 설정 최적화
```javascript
// 메모리 크기에 따른 CPU 성능 향상
// 128MB → 1024MB: CPU 성능 8배 향상
// 비용도 8배 증가하지만, 실행 시간 단축으로 전체 비용 절감 가능
```

#### 2. 패키지 최적화
```bash
# 불필요한 파일 제거
npm prune --production

# 패키지 크기 확인
du -sh node_modules/
```

#### 3. 비동기 처리 최적화
```javascript
// 병렬 처리로 성능 향상
exports.handler = async (event) => {
    const promises = event.records.map(record => 
        processRecord(record)
    );
    
    // 모든 작업을 병렬로 실행
    const results = await Promise.all(promises);
    return results;
};
```

---

## 🔗 Lambda와 연동 가능한 AWS 서비스

### 📡 주요 연동 서비스

| 서비스 | 용도 | 연동 방식 |
|--------|------|-----------|
| **API Gateway** | REST/HTTP API 백엔드 | HTTP 요청 → Lambda 실행 |
| **S3** | 파일 업로드/삭제 트리거 | 파일 이벤트 → Lambda 실행 |
| **DynamoDB** | 테이블 변경 트리거 | 데이터 변경 → Lambda 실행 |
| **Kinesis** | 실시간 데이터 스트림 처리 | 스트림 데이터 → Lambda 실행 |
| **SQS** | 메시지 큐 처리 | 메시지 수신 → Lambda 실행 |
| **CloudWatch Events** | 스케줄링, 이벤트 기반 자동화 | 시간/이벤트 → Lambda 실행 |
| **SNS** | 알림 발송 | 메시지 발행 → Lambda 실행 |
| **Step Functions** | 복잡한 워크플로우 오케스트레이션 | 상태 기계 → Lambda 실행 |

### 🔧 연동 예시

#### API Gateway + Lambda
```javascript
// REST API 백엔드
exports.handler = async (event) => {
    const method = event.httpMethod;
    const path = event.path;
    
    switch(method) {
        case 'GET':
            return await handleGet(path, event.queryStringParameters);
        case 'POST':
            return await handlePost(path, JSON.parse(event.body));
        default:
            return {
                statusCode: 405,
                body: JSON.stringify({error: 'Method not allowed'})
            };
    }
};
```

#### S3 + Lambda
```javascript
// 파일 업로드 트리거
exports.handler = async (event) => {
    for (const record of event.Records) {
        const bucket = record.s3.bucket.name;
        const key = record.s3.object.key;
        
        console.log(`파일 업로드 감지: ${bucket}/${key}`);
        
        // 파일 처리 로직
        await processFile(bucket, key);
    }
};
```


