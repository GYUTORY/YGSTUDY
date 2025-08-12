---
title: AWS Lambda
tags: [aws, compute, lambda, serverless, event-driven]
updated: 2024-12-19
---

# AWS Lambda

## 배경

AWS Lambda는 서버를 직접 관리하지 않고도 코드를 실행할 수 있게 해주는 서버리스 컴퓨팅 서비스입니다. 이벤트 기반으로 동작하며, 특정 이벤트가 발생할 때마다 지정된 코드를 자동으로 실행합니다. 서버 관리의 부담을 줄이고, 비용 효율성을 높이며, 빠른 개발과 배포를 가능하게 합니다.

## 핵심

### Lambda의 기본 개념

#### 서버리스 컴퓨팅
- 서버를 직접 관리하지 않고도 애플리케이션을 실행할 수 있는 방식
- 인프라 관리의 복잡성을 제거하고 개발에만 집중 가능

#### 이벤트 기반 실행
- 특정 사건(이벤트)이 발생했을 때만 코드가 실행되는 방식
- S3 파일 업로드, API Gateway 호출, DynamoDB 변경 등 다양한 이벤트 지원

#### 자동 확장
- 트래픽에 따라 자동으로 인스턴스 수를 조절하는 기능
- 동시에 수천, 수만 개의 이벤트도 병렬 처리 가능

### Lambda의 특징

| 특징 | 설명 | 장점 |
|------|------|------|
| **이벤트 기반 실행** | 특정 이벤트가 발생할 때마다 자동으로 실행 | 수동 개입 불필요 |
| **자동 확장** | 동시에 수천, 수만 개의 이벤트도 병렬 처리 | 트래픽 대응 자동화 |
| **과금 방식** | 실행된 시간(밀리초)과 사용한 메모리에 따라 과금 | 사용한 만큼만 비용 |
| **서버 관리 불필요** | 인프라 관리 작업이 전혀 필요 없음 | 개발에만 집중 가능 |
| **다양한 언어 지원** | Python, Node.js, Java, Go, C#, Ruby 등 | 기존 기술 스택 활용 |

### Lambda의 한계

| 한계 | 설명 | 영향 |
|------|------|------|
| **실행 시간 제한** | 최대 15분까지만 실행 가능 | 장시간 작업 불가 |
| **콜드 스타트** | 오랫동안 미사용 후 첫 실행 시 지연 | 응답 시간 증가 |
| **로컬 디스크 제한** | /tmp 디렉토리만 사용 가능 (최대 10GB) | 대용량 파일 처리 제한 |
| **언어/라이브러리 제한** | 지원하지 않는 언어나 라이브러리 사용 불가 | 기술 스택 제약 |
| **동시 실행 제한** | 계정별 동시 실행 제한 (기본 1,000개) | 대용량 트래픽 제약 |

## 예시

### 기본 Lambda 함수 예시

```javascript
// Node.js Lambda 함수 예시
exports.handler = async (event) => {
    console.log('이벤트 수신:', JSON.stringify(event, null, 2));
    
    try {
        // 비즈니스 로직 처리
        const result = await processEvent(event);
        
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: '처리 완료',
                result: result
            })
        };
    } catch (error) {
        console.error('오류 발생:', error);
        
        return {
            statusCode: 500,
            body: JSON.stringify({
                message: '처리 실패',
                error: error.message
            })
        };
    }
};

async function processEvent(event) {
    // 실제 비즈니스 로직 구현
    return { processed: true, timestamp: new Date().toISOString() };
}
```

### S3 파일 업로드 트리거 예시

```javascript
// S3 파일 업로드 시 썸네일 생성
const AWS = require('aws-sdk');
const sharp = require('sharp');

const s3 = new AWS.S3();

exports.handler = async (event) => {
    for (const record of event.Records) {
        const bucket = record.s3.bucket.name;
        const key = record.s3.object.key;
        
        console.log(`파일 업로드 감지: ${bucket}/${key}`);
        
        try {
            // 원본 이미지 다운로드
            const image = await s3.getObject({Bucket: bucket, Key: key}).promise();
            
            // 썸네일 생성
            const thumbnail = await sharp(image.Body)
                .resize(200, 200, {fit: 'inside'})
                .jpeg({quality: 80})
                .toBuffer();
            
            // 썸네일을 다른 버킷에 저장
            await s3.putObject({
                Bucket: 'thumbnail-bucket',
                Key: `thumbnails/${key}`,
                Body: thumbnail,
                ContentType: 'image/jpeg'
            }).promise();
            
            console.log(`썸네일 생성 완료: thumbnails/${key}`);
        } catch (error) {
            console.error(`썸네일 생성 실패: ${error.message}`);
            throw error;
        }
    }
};
```

### API Gateway 연동 예시

```javascript
// REST API 백엔드
exports.handler = async (event) => {
    const method = event.httpMethod;
    const path = event.path;
    const body = event.body ? JSON.parse(event.body) : {};
    
    console.log(`${method} ${path} 요청 처리`);
    
    try {
        let result;
        
        switch(method) {
            case 'GET':
                result = await handleGet(path, event.queryStringParameters);
                break;
            case 'POST':
                result = await handlePost(path, body);
                break;
            case 'PUT':
                result = await handlePut(path, body);
                break;
            case 'DELETE':
                result = await handleDelete(path);
                break;
            default:
                return {
                    statusCode: 405,
                    headers: {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    body: JSON.stringify({error: 'Method not allowed'})
                };
        }
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify(result)
        };
    } catch (error) {
        console.error('API 처리 오류:', error);
        
        return {
            statusCode: 500,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({error: 'Internal server error'})
        };
    }
};

async function handleGet(path, queryParams) {
    // GET 요청 처리 로직
    return { message: 'GET 요청 처리됨', path, queryParams };
}

async function handlePost(path, body) {
    // POST 요청 처리 로직
    return { message: 'POST 요청 처리됨', path, body };
}

async function handlePut(path, body) {
    // PUT 요청 처리 로직
    return { message: 'PUT 요청 처리됨', path, body };
}

async function handleDelete(path) {
    // DELETE 요청 처리 로직
    return { message: 'DELETE 요청 처리됨', path };
}
```

## 운영 팁

### 1. 함수 설계 원칙

#### 단일 책임 원칙
- 하나의 함수는 하나의 역할만 담당
- 함수 크기를 작게 유지하여 유지보수성 향상

```javascript
// 좋은 예: 단일 책임
exports.processImage = async (event) => {
    return await resizeImage(event.imageData);
};

// 나쁜 예: 여러 책임
exports.processEverything = async (event) => {
    // 이미지 처리 + 데이터베이스 저장 + 이메일 발송
    // 너무 많은 책임을 가짐
};
```

#### 환경 변수 활용
- 설정값을 환경 변수로 관리
- 환경별 다른 동작 구현

```javascript
const DATABASE_URL = process.env.DATABASE_URL;
const API_KEY = process.env.API_KEY;
const ENVIRONMENT = process.env.ENVIRONMENT;

if (ENVIRONMENT === 'production') {
    // 프로덕션 로직
} else {
    // 개발 로직
}
```

### 2. 에러 처리 및 로깅

#### 구조화된 로깅
```javascript
exports.handler = async (event) => {
    const requestId = event.requestContext?.requestId || 'unknown';
    
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

#### 재시도 로직
```javascript
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

### 3. 성능 최적화

#### 콜드 스타트 최소화
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

#### 패키지 크기 최적화
```bash
# 불필요한 개발 의존성 제거
npm prune --production

# 패키지 크기 확인
du -sh node_modules/
```

#### 병렬 처리
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

### 4. 보안

#### 최소 권한 원칙
```json
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

#### 환경 변수 암호화
```javascript
// AWS KMS를 사용한 환경 변수 암호화
const AWS = require('aws-sdk');
const kms = new AWS.KMS();

async function decryptValue(encryptedValue) {
    const result = await kms.decrypt({
        CiphertextBlob: Buffer.from(encryptedValue, 'base64')
    }).promise();
    
    return result.Plaintext.toString('utf-8');
}
```

### 5. 모니터링 및 알림

#### CloudWatch 메트릭
- Invocations: 함수 호출 횟수
- Duration: 실행 시간
- Errors: 오류 발생 횟수
- Throttles: 제한 초과 횟수

#### 알림 설정
```javascript
// CloudWatch 알람 설정 예시
const cloudwatch = new AWS.CloudWatch();

await cloudwatch.putMetricAlarm({
    AlarmName: 'LambdaErrorRate',
    MetricName: 'Errors',
    Namespace: 'AWS/Lambda',
    Statistic: 'Sum',
    Period: 300,
    EvaluationPeriods: 2,
    Threshold: 5,
    ComparisonOperator: 'GreaterThanThreshold'
}).promise();
```

## 참고

### Lambda와 연동 가능한 AWS 서비스

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

### 실무 활용 사례

#### 1. 이미지 변환 서비스
- S3에 이미지 업로드 시 자동으로 썸네일 생성
- 다양한 크기와 포맷으로 변환
- CDN 연동으로 빠른 이미지 서빙

#### 2. 실시간 알림 시스템
- 주문, 결제, 배송 이벤트를 SNS로 발행
- Lambda가 이벤트를 수신하여 알림 처리
- 다양한 채널(이메일, SMS, 푸시)로 발송

#### 3. 데이터 처리 파이프라인
- IoT 센서 데이터를 Kinesis로 수집
- Lambda로 실시간 데이터 분석 및 필터링
- 결과를 DynamoDB에 저장

#### 4. 서버리스 API
- API Gateway + Lambda로 REST API 구축
- 인증, 권한 관리, 데이터 검증
- 마이크로서비스 아키텍처 구현

### 관련 링크

- [AWS Lambda 공식 문서](https://docs.aws.amazon.com/lambda/)
- [AWS Lambda 가격](https://aws.amazon.com/lambda/pricing/)
- [AWS Lambda 모범 사례](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [AWS Well-Architected Framework - 서버리스](https://aws.amazon.com/architecture/well-architected/)

