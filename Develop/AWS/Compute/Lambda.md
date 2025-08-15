---
title: AWS Lambda 완벽 가이드
tags: [aws, compute, lambda, serverless, event-driven, faas]
updated: 2025-08-10
---

# AWS Lambda 완벽 가이드

## 배경

AWS Lambda는 서버를 직접 관리하지 않고도 코드를 실행할 수 있게 해주는 서버리스 컴퓨팅 서비스입니다. 이벤트 기반으로 동작하며, 특정 이벤트가 발생할 때마다 지정된 코드를 자동으로 실행합니다. 서버 관리의 부담을 줄이고, 비용 효율성을 높이며, 빠른 개발과 배포를 가능하게 합니다.

### AWS Lambda의 필요성
- **서버 관리 부담 제거**: 인프라 관리 없이 코드 실행에만 집중
- **비용 효율성**: 사용한 만큼만 비용 지불
- **자동 확장**: 트래픽에 따른 자동 스케일링
- **빠른 개발**: 복잡한 인프라 설정 없이 즉시 배포
- **이벤트 기반 아키텍처**: 마이크로서비스와 서버리스 아키텍처 구현

### 기본 개념
- **서버리스**: 서버를 직접 관리하지 않는 컴퓨팅 모델
- **FaaS**: Function as a Service, 함수 단위로 실행되는 서비스
- **이벤트 기반**: 특정 이벤트 발생 시 자동 실행
- **콜드 스타트**: 함수가 처음 실행될 때의 초기화 지연
- **워밍**: 함수를 미리 로드하여 콜드 스타트 방지

## 핵심

### 1. Lambda의 기본 개념

#### 서버리스 컴퓨팅
서버를 직접 관리하지 않고도 애플리케이션을 실행할 수 있는 방식입니다.

```javascript
// 전통적인 서버 방식
// - 서버 프로비저닝
// - 운영체제 설치
// - 런타임 환경 설정
// - 애플리케이션 배포
// - 모니터링 및 유지보수

// Lambda 서버리스 방식
// - 코드 작성
// - Lambda 함수 업로드
// - 이벤트 설정
// - 자동 실행
```

#### 이벤트 기반 실행
특정 사건(이벤트)이 발생했을 때만 코드가 실행되는 방식입니다.

```javascript
// 다양한 이벤트 소스
const eventSources = {
    s3: 'S3 파일 업로드/삭제',
    apiGateway: 'HTTP 요청',
    dynamodb: 'DynamoDB 스트림',
    sqs: 'SQS 메시지',
    sns: 'SNS 알림',
    cloudwatch: 'CloudWatch 이벤트',
    cognito: '사용자 인증',
    kinesis: '데이터 스트림'
};
```

#### 자동 확장
트래픽에 따라 자동으로 인스턴스 수를 조절하는 기능입니다.

```javascript
// 동시 실행 예시
// 1개 요청 → 1개 Lambda 인스턴스
// 100개 요청 → 100개 Lambda 인스턴스 (병렬 처리)
// 0개 요청 → 0개 Lambda 인스턴스 (비용 0)
```

### 2. Lambda의 특징

#### 핵심 특징
| 특징 | 설명 | 장점 |
|------|------|------|
| **이벤트 기반 실행** | 특정 이벤트가 발생할 때마다 자동으로 실행 | 수동 개입 불필요 |
| **자동 확장** | 동시에 수천, 수만 개의 이벤트도 병렬 처리 | 트래픽 대응 자동화 |
| **과금 방식** | 실행된 시간(밀리초)과 사용한 메모리에 따라 과금 | 사용한 만큼만 비용 |
| **서버 관리 불필요** | 인프라 관리 작업이 전혀 필요 없음 | 개발에만 집중 가능 |
| **다양한 언어 지원** | Python, Node.js, Java, Go, C#, Ruby 등 | 기존 기술 스택 활용 |

#### 지원 언어 및 런타임
```javascript
const supportedRuntimes = {
    nodejs: ['nodejs18.x', 'nodejs16.x', 'nodejs14.x'],
    python: ['python3.11', 'python3.10', 'python3.9'],
    java: ['java17', 'java11', 'java8.al2'],
    go: ['provided.al2'],
    dotnet: ['dotnet6', 'dotnetcore3.1'],
    ruby: ['ruby3.2', 'ruby2.7'],
    custom: ['provided', 'provided.al2']
};
```

### 3. Lambda의 한계

#### 주요 한계점
| 한계 | 설명 | 영향 |
|------|------|------|
| **실행 시간 제한** | 최대 15분까지만 실행 가능 | 장시간 작업 불가 |
| **콜드 스타트** | 오랫동안 미사용 후 첫 실행 시 지연 | 응답 시간 증가 |
| **로컬 디스크 제한** | /tmp 디렉토리만 사용 가능 (최대 10GB) | 대용량 파일 처리 제한 |
| **언어/라이브러리 제한** | 지원하지 않는 언어나 라이브러리 사용 불가 | 기술 스택 제약 |
| **동시 실행 제한** | 계정별 동시 실행 제한 (기본 1,000개) | 대용량 트래픽 제약 |

#### 한계 해결 방안
```javascript
// 실행 시간 제한 해결
const solutions = {
    longRunning: 'Step Functions 또는 ECS 사용',
    coldStart: 'Provisioned Concurrency 사용',
    largeFiles: 'S3와 연동하여 처리',
    customRuntime: 'Lambda Layer 또는 Container Image 사용',
    highConcurrency: '동시 실행 제한 증가 요청'
};
```

## 예시

### 1. 기본 Lambda 함수 예시

#### Node.js Lambda 함수
```javascript
// 기본 Lambda 함수 구조
exports.handler = async (event, context) => {
    console.log('이벤트 수신:', JSON.stringify(event, null, 2));
    console.log('컨텍스트:', JSON.stringify(context, null, 2));
    
    try {
        // 비즈니스 로직 처리
        const result = await processEvent(event);
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                message: '처리 완료',
                result: result,
                timestamp: new Date().toISOString()
            })
        };
    } catch (error) {
        console.error('오류 발생:', error);
        
        return {
            statusCode: 500,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                message: '처리 실패',
                error: error.message,
                timestamp: new Date().toISOString()
            })
        };
    }
};

async function processEvent(event) {
    // 실제 비즈니스 로직 구현
    const { name, data } = event;
    
    return {
        processed: true,
        input: { name, data },
        processedAt: new Date().toISOString()
    };
}
```

#### Python Lambda 함수
```python
import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """AWS Lambda 함수 핸들러"""
    print(f"이벤트 수신: {json.dumps(event)}")
    print(f"컨텍스트: {context}")
    
    try:
        # 비즈니스 로직 처리
        result = process_event(event)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': '처리 완료',
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
        }
    except Exception as error:
        print(f"오류 발생: {error}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': '처리 실패',
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            })
        }

def process_event(event):
    """이벤트 처리 로직"""
    name = event.get('name', 'Unknown')
    data = event.get('data', {})
    
    return {
        'processed': True,
        'input': {'name': name, 'data': data},
        'processedAt': datetime.now().isoformat()
    }
```

### 2. 실제 사용 사례

#### S3 파일 업로드 트리거
```javascript
const AWS = require('aws-sdk');
const sharp = require('sharp');

const s3 = new AWS.S3();

exports.handler = async (event) => {
    console.log('S3 이벤트 수신:', JSON.stringify(event, null, 2));
    
    for (const record of event.Records) {
        try {
            const bucket = record.s3.bucket.name;
            const key = record.s3.object.key;
            
            // 이미지 파일인지 확인
            if (!isImageFile(key)) {
                console.log('이미지 파일이 아님:', key);
                continue;
            }
            
            // 원본 이미지 다운로드
            const originalImage = await downloadImage(bucket, key);
            
            // 썸네일 생성
            const thumbnail = await generateThumbnail(originalImage);
            
            // 썸네일 업로드
            const thumbnailKey = generateThumbnailKey(key);
            await uploadThumbnail(bucket, thumbnailKey, thumbnail);
            
            console.log('썸네일 생성 완료:', thumbnailKey);
            
        } catch (error) {
            console.error('썸네일 생성 실패:', error);
            throw error;
        }
    }
};

function isImageFile(key) {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp'];
    return imageExtensions.some(ext => key.toLowerCase().endsWith(ext));
}

async function downloadImage(bucket, key) {
    const params = { Bucket: bucket, Key: key };
    const response = await s3.getObject(params).promise();
    return response.Body;
}

async function generateThumbnail(imageBuffer) {
    return await sharp(imageBuffer)
        .resize(200, 200, { fit: 'inside' })
        .jpeg({ quality: 80 })
        .toBuffer();
}

function generateThumbnailKey(originalKey) {
    const pathParts = originalKey.split('/');
    const filename = pathParts.pop();
    const thumbnailFilename = `thumb_${filename}`;
    return [...pathParts, 'thumbnails', thumbnailFilename].join('/');
}

async function uploadThumbnail(bucket, key, thumbnailBuffer) {
    const params = {
        Bucket: bucket,
        Key: key,
        Body: thumbnailBuffer,
        ContentType: 'image/jpeg'
    };
    await s3.putObject(params).promise();
}
```

#### API Gateway 연동
```javascript
// API Gateway와 연동하는 Lambda 함수
exports.handler = async (event) => {
    console.log('API Gateway 이벤트:', JSON.stringify(event, null, 2));
    
    const { httpMethod, path, queryStringParameters, body } = event;
    
    try {
        let result;
        
        switch (httpMethod) {
            case 'GET':
                result = await handleGet(path, queryStringParameters);
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
                throw new Error(`지원하지 않는 HTTP 메서드: ${httpMethod}`);
        }
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
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
            body: JSON.stringify({
                error: error.message,
                timestamp: new Date().toISOString()
            })
        };
    }
};

async function handleGet(path, queryParams) {
    // GET 요청 처리
    return { method: 'GET', path, queryParams };
}

async function handlePost(path, body) {
    // POST 요청 처리
    const parsedBody = body ? JSON.parse(body) : {};
    return { method: 'POST', path, body: parsedBody };
}

async function handlePut(path, body) {
    // PUT 요청 처리
    const parsedBody = body ? JSON.parse(body) : {};
    return { method: 'PUT', path, body: parsedBody };
}

async function handleDelete(path) {
    // DELETE 요청 처리
    return { method: 'DELETE', path };
}
```

### 3. 고급 패턴

#### DynamoDB 스트림 처리
```javascript
const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {
    console.log('DynamoDB 스트림 이벤트:', JSON.stringify(event, null, 2));
    
    for (const record of event.Records) {
        try {
            const { eventName, dynamodb } = record;
            
            switch (eventName) {
                case 'INSERT':
                    await handleInsert(dynamodb);
                    break;
                case 'MODIFY':
                    await handleModify(dynamodb);
                    break;
                case 'REMOVE':
                    await handleRemove(dynamodb);
                    break;
                default:
                    console.log('지원하지 않는 이벤트:', eventName);
            }
            
        } catch (error) {
            console.error('스트림 처리 오류:', error);
            throw error;
        }
    }
};

async function handleInsert(dynamodb) {
    const newImage = dynamodb.NewImage;
    console.log('새 레코드 삽입:', newImage);
    
    // 새 레코드에 대한 처리 로직
    // 예: 알림 발송, 캐시 업데이트 등
}

async function handleModify(dynamodb) {
    const oldImage = dynamodb.OldImage;
    const newImage = dynamodb.NewImage;
    console.log('레코드 수정:', { old: oldImage, new: newImage });
    
    // 수정된 레코드에 대한 처리 로직
}

async function handleRemove(dynamodb) {
    const oldImage = dynamodb.OldImage;
    console.log('레코드 삭제:', oldImage);
    
    // 삭제된 레코드에 대한 처리 로직
}
```

## 운영 팁

### 성능 최적화

#### 콜드 스타트 최소화
```javascript
// 1. 함수 크기 최소화
const optimization = {
    bundleSize: '불필요한 의존성 제거',
    layers: '공통 라이브러리를 Lambda Layer로 분리',
    treeShaking: '사용하지 않는 코드 제거'
};

// 2. Provisioned Concurrency 사용
const provisionedConcurrency = {
    benefit: '콜드 스타트 완전 제거',
    cost: '사용하지 않아도 비용 발생',
    useCase: '지연 시간이 중요한 애플리케이션'
};

// 3. 함수 워밍
exports.handler = async (event, context) => {
    // 글로벌 변수 초기화 (콜드 스타트 시에만 실행)
    if (!global.initialized) {
        global.initialized = true;
        global.dbConnection = await createDatabaseConnection();
        global.cache = new Map();
    }
    
    // 실제 비즈니스 로직
    return await processRequest(event);
};
```

#### 메모리 최적화
```javascript
// 메모리 설정 가이드
const memorySettings = {
    '128MB': '간단한 API 호출, 기본 처리',
    '256MB': 'JSON 파싱, 간단한 계산',
    '512MB': '이미지 처리, 데이터베이스 쿼리',
    '1024MB': '복잡한 계산, 대용량 데이터 처리',
    '3008MB': '최대 성능, CPU 집약적 작업'
};

// 메모리 사용량 모니터링
exports.handler = async (event, context) => {
    const startMemory = process.memoryUsage();
    
    // 비즈니스 로직 실행
    const result = await processData(event);
    
    const endMemory = process.memoryUsage();
    console.log('메모리 사용량:', {
        heapUsed: endMemory.heapUsed - startMemory.heapUsed,
        heapTotal: endMemory.heapTotal - startMemory.heapTotal
    });
    
    return result;
};
```

### 에러 처리

#### 재시도 로직
```javascript
const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {
    const maxRetries = 3;
    let retryCount = 0;
    
    while (retryCount < maxRetries) {
        try {
            return await processWithRetry(event);
        } catch (error) {
            retryCount++;
            console.error(`시도 ${retryCount} 실패:`, error);
            
            if (retryCount >= maxRetries) {
                throw error;
            }
            
            // 지수 백오프
            const delay = Math.pow(2, retryCount) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
};

async function processWithRetry(event) {
    // 실제 처리 로직
    const result = await dynamodb.put({
        TableName: 'MyTable',
        Item: event
    }).promise();
    
    return result;
}
```

#### 데드레터 큐 활용
```javascript
const AWS = require('aws-sdk');
const sqs = new AWS.SQS();

exports.handler = async (event) => {
    try {
        // 메인 처리 로직
        await processMessage(event);
        
    } catch (error) {
        console.error('처리 실패:', error);
        
        // 데드레터 큐로 메시지 전송
        await sendToDeadLetterQueue(event, error);
        
        throw error; // Lambda 재시도 트리거
    }
};

async function sendToDeadLetterQueue(message, error) {
    const params = {
        QueueUrl: process.env.DEAD_LETTER_QUEUE_URL,
        MessageBody: JSON.stringify({
            originalMessage: message,
            error: error.message,
            timestamp: new Date().toISOString()
        })
    };
    
    await sqs.sendMessage(params).promise();
}
```

## 참고

### Lambda vs 전통적 서버 비교

| 측면 | Lambda | 전통적 서버 |
|------|--------|-------------|
| **서버 관리** | AWS 관리 | 직접 관리 |
| **확장성** | 자동 확장 | 수동 확장 |
| **비용** | 사용한 만큼만 | 24/7 비용 |
| **시작 시간** | 밀리초 | 분 단위 |
| **최대 실행 시간** | 15분 | 무제한 |
| **메모리** | 최대 10GB | 무제한 |
| **디스크** | /tmp만 (10GB) | 전체 디스크 |

### Lambda 사용 권장사항

| 사용 사례 | 권장도 | 이유 |
|----------|--------|------|
| **이벤트 기반 처리** | ⭐⭐⭐⭐⭐ | Lambda의 핵심 강점 |
| **API 백엔드** | ⭐⭐⭐⭐ | 빠른 개발, 자동 확장 |
| **데이터 처리** | ⭐⭐⭐⭐ | 병렬 처리, 비용 효율 |
| **정기 작업** | ⭐⭐⭐ | CloudWatch Events 연동 |
| **장시간 작업** | ⭐⭐ | 15분 제한 |
| **대용량 파일 처리** | ⭐⭐ | 메모리/디스크 제한 |

### 결론
AWS Lambda는 서버리스 컴퓨팅의 대표적인 서비스로, 이벤트 기반 아키텍처 구현에 최적화되어 있습니다.
콜드 스타트와 실행 시간 제한을 고려하여 적절한 사용 사례를 선택하세요.
Provisioned Concurrency와 Lambda Layer를 활용하여 성능을 최적화하세요.
다양한 AWS 서비스와 연동하여 강력한 서버리스 애플리케이션을 구축할 수 있습니다.

