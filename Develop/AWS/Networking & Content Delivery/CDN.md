---
title: AWS CDN CloudFront
tags: [aws, networking-and-content-delivery, cdn]
updated: 2025-08-10
---
# 🌐 AWS CDN (CloudFront) 완벽 가이드

## 배경
- [CDN이란 무엇인가?](#cdn이란-무엇인가)
- [CloudFront의 핵심 개념](#cloudfront의-핵심-개념)
- [실제 설정 과정](#실제-설정-과정)
- [JavaScript로 CDN 활용하기](#javascript로-cdn-활용하기)
- [성능 최적화](#성능-최적화)
- [비용과 보안](#비용과-보안)

---


#### 1. 오리진(Origin)
콘텐츠의 원본이 저장된 서버
```javascript
// 오리진 예시
const origins = {
  s3Bucket: "my-website-bucket.s3.amazonaws.com",
  ec2Instance: "ec2-123-456-789.compute-1.amazonaws.com",
  loadBalancer: "my-alb-123456789.ap-northeast-2.elb.amazonaws.com"
};
```

#### 2. 엣지 로케이션(Edge Location)
사용자와 가까운 지역에 위치한 CDN 서버
```javascript
// 전 세계 엣지 로케이션 예시
const edgeLocations = {
  asia: ["Seoul", "Tokyo", "Singapore", "Mumbai"],
  europe: ["London", "Frankfurt", "Paris", "Stockholm"],
  americas: ["New York", "Los Angeles", "São Paulo", "Toronto"]
};
```

#### 3. 배포(Distribution)
CloudFront에서 생성하는 콘텐츠 제공 단위
```javascript
// 배포 설정 예시
const distributionConfig = {
  id: "E123456789ABCD",
  domainName: "d1234.cloudfront.net",
  status: "Deployed",
  origins: ["my-website-bucket.s3.amazonaws.com"],
  cacheBehaviors: {
    "/*": {
      ttl: 86400, // 24시간
      compress: true
    }
  }
};
```

#### 4. 캐싱 정책(Cache Policy)
콘텐츠가 얼마나 오래 캐시될지 결정하는 규칙
```javascript
// 캐싱 정책 예시
const cachePolicy = {
  name: "CustomCachePolicy",
  ttl: {
    min: 0,        // 최소 캐시 시간
    default: 3600, // 기본 캐시 시간 (1시간)
    max: 86400     // 최대 캐시 시간 (24시간)
  },
  headers: ["Accept", "Accept-Language"],
  cookies: ["session-id"],
  queryStrings: ["utm_source", "utm_medium"]
};
```

---


### 1단계: S3 버킷 준비

#### S3 버킷 생성 및 설정
```javascript
// AWS SDK를 사용한 S3 버킷 생성 예시
const AWS = require('aws-sdk');
const s3 = new AWS.S3();

const createS3Bucket = async () => {
  const params = {
    Bucket: 'my-website-bucket',
    ACL: 'public-read',
    WebsiteConfiguration: {
      IndexDocument: { Suffix: 'index.html' },
      ErrorDocument: { Key: 'error.html' }
    }
  };
  
  try {
    await s3.createBucket(params).promise();
    console.log('S3 버킷이 성공적으로 생성되었습니다.');
  } catch (error) {
    console.error('S3 버킷 생성 실패:', error);
  }
};
```

#### 정적 웹사이트 파일 업로드
```javascript
// 정적 파일 업로드 예시
const uploadStaticFiles = async () => {
  const files = [
    { key: 'index.html', body: '<html><body>Hello World!</body></html>' },
    { key: 'styles.css', body: 'body { font-family: Arial; }' },
    { key: 'script.js', body: 'console.log("Hello from CDN!");' }
  ];
  
  for (const file of files) {
    const params = {
      Bucket: 'my-website-bucket',
      Key: file.key,
      Body: file.body,
      ContentType: getContentType(file.key)
    };
    
    await s3.putObject(params).promise();
    console.log(`${file.key} 업로드 완료`);
  }
};

const getContentType = (filename) => {
  const ext = filename.split('.').pop();
  const types = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'png': 'image/png',
    'jpg': 'image/jpeg'
  };
  return types[ext] || 'application/octet-stream';
};
```

### 2단계: CloudFront 배포 생성

#### CloudFront 배포 설정
```javascript
// CloudFront 배포 생성 예시
const cloudfront = new AWS.CloudFront();

const createCloudFrontDistribution = async () => {
  const params = {
    DistributionConfig: {
      CallerReference: Date.now().toString(),
      Origins: {
        Quantity: 1,
        Items: [{
          Id: 'S3-my-website-bucket',
          DomainName: 'my-website-bucket.s3.amazonaws.com',
          S3OriginConfig: {
            OriginAccessIdentity: ''
          }
        }]
      },
      DefaultCacheBehavior: {
        TargetOriginId: 'S3-my-website-bucket',
        ViewerProtocolPolicy: 'redirect-to-https',
        TrustedSigners: {
          Enabled: false,
          Quantity: 0
        },
        ForwardedValues: {
          QueryString: false,
          Cookies: { Forward: 'none' }
        },
        MinTTL: 0,
        DefaultTTL: 86400,
        MaxTTL: 31536000
      },
      Enabled: true,
      Comment: 'My website CDN distribution'
    }
  };
  
  try {
    const result = await cloudfront.createDistribution(params).promise();
    console.log('CloudFront 배포 생성 완료:', result.Distribution.DomainName);
    return result.Distribution;
  } catch (error) {
    console.error('CloudFront 배포 생성 실패:', error);
  }
};
```

### 3단계: 사용자 정의 도메인 연결

#### Route 53을 통한 도메인 연결
```javascript
// Route 53 레코드 생성 예시
const route53 = new AWS.Route53();

const createAliasRecord = async (domainName, distributionDomain) => {
  const params = {
    HostedZoneId: 'Z1234567890ABC', // 호스팅 존 ID
    ChangeBatch: {
      Changes: [{
        Action: 'CREATE',
        ResourceRecordSet: {
          Name: domainName,
          Type: 'A',
          AliasTarget: {
            DNSName: distributionDomain,
            HostedZoneId: 'Z2FDTNDATAQYW2', // CloudFront 호스팅 존 ID
            EvaluateTargetHealth: false
          }
        }
      }]
    }
  };
  
  try {
    await route53.changeResourceRecordSets(params).promise();
    console.log(`${domainName} 도메인이 CloudFront에 연결되었습니다.`);
  } catch (error) {
    console.error('도메인 연결 실패:', error);
  }
};
```

---

```javascript
// 정적 파일 업로드 예시
const uploadStaticFiles = async () => {
  const files = [
    { key: 'index.html', body: '<html><body>Hello World!</body></html>' },
    { key: 'styles.css', body: 'body { font-family: Arial; }' },
    { key: 'script.js', body: 'console.log("Hello from CDN!");' }
  ];
  
  for (const file of files) {
    const params = {
      Bucket: 'my-website-bucket',
      Key: file.key,
      Body: file.body,
      ContentType: getContentType(file.key)
    };
    
    await s3.putObject(params).promise();
    console.log(`${file.key} 업로드 완료`);
  }
};

const getContentType = (filename) => {
  const ext = filename.split('.').pop();
  const types = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'png': 'image/png',
    'jpg': 'image/jpeg'
  };
  return types[ext] || 'application/octet-stream';
};
```

```javascript
// CloudFront 캐시 무효화 자동화
class CloudFrontInvalidator {
  constructor(distributionId) {
    this.distributionId = distributionId;
    this.cloudfront = new AWS.CloudFront();
  }
  
  // 특정 경로 캐시 무효화
  async invalidatePaths(paths) {
    const params = {
      DistributionId: this.distributionId,
      InvalidationBatch: {
        CallerReference: `invalidation-${Date.now()}`,
        Paths: {
          Quantity: paths.length,
          Items: paths
        }
      }
    };
    
    try {
      const result = await this.cloudfront.createInvalidation(params).promise();
      console.log('캐시 무효화 요청 완료:', result.Invalidation.Id);
      return result.Invalidation;
    } catch (error) {
      console.error('캐시 무효화 실패:', error);
      throw error;
    }
  }
  
  // 전체 캐시 무효화
  async invalidateAll() {
    return this.invalidatePaths(['/*']);
  }
  
  // 특정 파일 타입만 무효화
  async invalidateByType(fileType) {
    const paths = [`/*.${fileType}`];
    return this.invalidatePaths(paths);
  }
}

// 사용 예시
const invalidator = new CloudFrontInvalidator('E123456789ABCD');

// 배포 후 캐시 무효화
const deployAndInvalidate = async () => {
  try {
    // S3에 파일 업로드
    await uploadStaticFiles();
    
    // CSS와 JS 파일만 캐시 무효화
    await invalidator.invalidateByType('css');
    await invalidator.invalidateByType('js');
    
    console.log('배포 및 캐시 무효화 완료');
  } catch (error) {
    console.error('배포 실패:', error);
  }
};
```

---


### 압축 및 최적화 설정
```javascript
// CloudFront 압축 설정
const compressionConfig = {
  Compress: true,
  CompressibleContentTypes: [
    'text/html',
    'text/css',
    'application/javascript',
    'application/json',
    'text/xml',
    'application/xml',
    'application/xml+rss',
    'text/javascript'
  ]
};

// 캐시 최적화 설정
const cacheOptimization = {
  // 정적 자산 (이미지, CSS, JS)
  staticAssets: {
    TTL: 31536000, // 1년
    Headers: ['Accept-Encoding'],
    Compress: true
  },
  
  // HTML 페이지
  htmlPages: {
    TTL: 3600, // 1시간
    Headers: ['Accept-Language'],
    Compress: true
  },
  
  // API 응답
  apiResponses: {
    TTL: 300, // 5분
    Headers: ['Authorization'],
    Compress: true
  }
};
```

### 성능 모니터링
```javascript
// CDN 성능 모니터링
class CDNPerformanceMonitor {
  constructor() {
    this.metrics = {
      loadTimes: [],
      errorRates: [],
      cacheHits: 0,
      cacheMisses: 0
    };
  }
  
  // 리소스 로딩 시간 측정
  measureLoadTime(url) {
    const startTime = performance.now();
    
    return fetch(url)
      .then(response => {
        const loadTime = performance.now() - startTime;
        this.metrics.loadTimes.push(loadTime);
        
        // 캐시 히트 여부 확인
        if (response.headers.get('x-cache') === 'Hit from cloudfront') {
          this.metrics.cacheHits++;
        } else {
          this.metrics.cacheMisses++;
        }
        
        return response;
      })
      .catch(error => {
        this.metrics.errorRates.push({
          url,
          error: error.message,
          timestamp: Date.now()
        });
        throw error;
      });
  }
  
  // 성능 통계 출력
  getPerformanceStats() {
    const avgLoadTime = this.metrics.loadTimes.reduce((a, b) => a + b, 0) / this.metrics.loadTimes.length;
    const cacheHitRate = this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses);
    
    return {
      averageLoadTime: avgLoadTime.toFixed(2) + 'ms',
      cacheHitRate: (cacheHitRate * 100).toFixed(2) + '%',
      totalRequests: this.metrics.loadTimes.length,
      errorCount: this.metrics.errorRates.length
    };
  }
}

// 사용 예시
const monitor = new CDNPerformanceMonitor();

// 여러 리소스 로딩 시간 측정
const urls = [
  'https://d1234.cloudfront.net/css/style.css',
  'https://d1234.cloudfront.net/js/app.js',
  'https://d1234.cloudfront.net/images/logo.png'
];

Promise.all(urls.map(url => monitor.measureLoadTime(url)))
  .then(() => {
    console.log('성능 통계:', monitor.getPerformanceStats());
  })
  .catch(error => console.error('모니터링 오류:', error));
```

---

```javascript
// CloudFront 압축 설정
const compressionConfig = {
  Compress: true,
  CompressibleContentTypes: [
    'text/html',
    'text/css',
    'application/javascript',
    'application/json',
    'text/xml',
    'application/xml',
    'application/xml+rss',
    'text/javascript'
  ]
};

// 캐시 최적화 설정
const cacheOptimization = {
  // 정적 자산 (이미지, CSS, JS)
  staticAssets: {
    TTL: 31536000, // 1년
    Headers: ['Accept-Encoding'],
    Compress: true
  },
  
  // HTML 페이지
  htmlPages: {
    TTL: 3600, // 1시간
    Headers: ['Accept-Language'],
    Compress: true
  },
  
  // API 응답
  apiResponses: {
    TTL: 300, // 5분
    Headers: ['Authorization'],
    Compress: true
  }
};
```

```javascript
// CDN 성능 모니터링
class CDNPerformanceMonitor {
  constructor() {
    this.metrics = {
      loadTimes: [],
      errorRates: [],
      cacheHits: 0,
      cacheMisses: 0
    };
  }
  
  // 리소스 로딩 시간 측정
  measureLoadTime(url) {
    const startTime = performance.now();
    
    return fetch(url)
      .then(response => {
        const loadTime = performance.now() - startTime;
        this.metrics.loadTimes.push(loadTime);
        
        // 캐시 히트 여부 확인
        if (response.headers.get('x-cache') === 'Hit from cloudfront') {
          this.metrics.cacheHits++;
        } else {
          this.metrics.cacheMisses++;
        }
        
        return response;
      })
      .catch(error => {
        this.metrics.errorRates.push({
          url,
          error: error.message,
          timestamp: Date.now()
        });
        throw error;
      });
  }
  
  // 성능 통계 출력
  getPerformanceStats() {
    const avgLoadTime = this.metrics.loadTimes.reduce((a, b) => a + b, 0) / this.metrics.loadTimes.length;
    const cacheHitRate = this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses);
    
    return {
      averageLoadTime: avgLoadTime.toFixed(2) + 'ms',
      cacheHitRate: (cacheHitRate * 100).toFixed(2) + '%',
      totalRequests: this.metrics.loadTimes.length,
      errorCount: this.metrics.errorRates.length
    };
  }
}

// 사용 예시
const monitor = new CDNPerformanceMonitor();

// 여러 리소스 로딩 시간 측정
const urls = [
  'https://d1234.cloudfront.net/css/style.css',
  'https://d1234.cloudfront.net/js/app.js',
  'https://d1234.cloudfront.net/images/logo.png'
];

Promise.all(urls.map(url => monitor.measureLoadTime(url)))
  .then(() => {
    console.log('성능 통계:', monitor.getPerformanceStats());
  })
  .catch(error => console.error('모니터링 오류:', error));
```

---


### 비용 최적화 전략
```javascript
// CDN 비용 계산기
class CDNCostCalculator {
  constructor() {
    this.pricing = {
      dataTransfer: {
        'us-east-1': 0.085, // USD per GB
        'eu-west-1': 0.085,
        'ap-northeast-1': 0.120
      },
      requests: {
        'us-east-1': 0.0075, // USD per 10,000 requests
        'eu-west-1': 0.0075,
        'ap-northeast-1': 0.0090
      },
      invalidation: 0.005 // USD per path
    };
  }
  
  // 월간 비용 계산
  calculateMonthlyCost(usage) {
    const dataTransferCost = usage.dataTransferGB * this.pricing.dataTransfer['ap-northeast-1'];
    const requestCost = (usage.requests / 10000) * this.pricing.requests['ap-northeast-1'];
    const invalidationCost = usage.invalidations * this.pricing.invalidation;
    
    return {
      dataTransfer: dataTransferCost,
      requests: requestCost,
      invalidations: invalidationCost,
      total: dataTransferCost + requestCost + invalidationCost
    };
  }
  
  // 비용 최적화 권장사항
  getOptimizationTips(usage) {
    const tips = [];
    
    if (usage.invalidations > 1000) {
      tips.push('캐시 무효화 횟수를 줄이세요. 전체 무효화 대신 특정 경로만 무효화하세요.');
    }
    
    if (usage.dataTransferGB > 1000) {
      tips.push('이미지 압축을 활성화하고 WebP 형식을 사용하세요.');
    }
    
    return tips;
  }
}

// 사용 예시
const calculator = new CDNCostCalculator();
const monthlyUsage = {
  dataTransferGB: 500,
  requests: 1000000,
  invalidations: 50
};

const costs = calculator.calculateMonthlyCost(monthlyUsage);
console.log('월간 CDN 비용:', costs);
console.log('최적화 팁:', calculator.getOptimizationTips(monthlyUsage));
```

### 보안 설정
```javascript
// CloudFront 보안 설정
const securityConfig = {
  // HTTPS 강제 적용
  viewerProtocolPolicy: 'redirect-to-https',
  
  // WAF 규칙
  wafRules: {
    rateLimit: {
      rate: 2000, // 초당 요청 수 제한
      burst: 5000
    },
    geoRestriction: {
      allowList: ['KR', 'US', 'JP'], // 허용 국가
      blockList: []
    }
  },
  
  // 헤더 보안
  securityHeaders: {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
  }
};

// 보안 헤더 적용 함수
const applySecurityHeaders = (response) => {
  Object.entries(securityConfig.securityHeaders).forEach(([header, value]) => {
    response.headers.set(header, value);
  });
  return response;
};
```

---

```javascript
// CDN 비용 계산기
class CDNCostCalculator {
  constructor() {
    this.pricing = {
      dataTransfer: {
        'us-east-1': 0.085, // USD per GB
        'eu-west-1': 0.085,
        'ap-northeast-1': 0.120
      },
      requests: {
        'us-east-1': 0.0075, // USD per 10,000 requests
        'eu-west-1': 0.0075,
        'ap-northeast-1': 0.0090
      },
      invalidation: 0.005 // USD per path
    };
  }
  
  // 월간 비용 계산
  calculateMonthlyCost(usage) {
    const dataTransferCost = usage.dataTransferGB * this.pricing.dataTransfer['ap-northeast-1'];
    const requestCost = (usage.requests / 10000) * this.pricing.requests['ap-northeast-1'];
    const invalidationCost = usage.invalidations * this.pricing.invalidation;
    
    return {
      dataTransfer: dataTransferCost,
      requests: requestCost,
      invalidations: invalidationCost,
      total: dataTransferCost + requestCost + invalidationCost
    };
  }
  
  // 비용 최적화 권장사항
  getOptimizationTips(usage) {
    const tips = [];
    
    if (usage.invalidations > 1000) {
      tips.push('캐시 무효화 횟수를 줄이세요. 전체 무효화 대신 특정 경로만 무효화하세요.');
    }
    
    if (usage.dataTransferGB > 1000) {
      tips.push('이미지 압축을 활성화하고 WebP 형식을 사용하세요.');
    }
    
    return tips;
  }
}

// 사용 예시
const calculator = new CDNCostCalculator();
const monthlyUsage = {
  dataTransferGB: 500,
  requests: 1000000,
  invalidations: 50
};

const costs = calculator.calculateMonthlyCost(monthlyUsage);
console.log('월간 CDN 비용:', costs);
console.log('최적화 팁:', calculator.getOptimizationTips(monthlyUsage));
```

```javascript
// CloudFront 보안 설정
const securityConfig = {
  // HTTPS 강제 적용
  viewerProtocolPolicy: 'redirect-to-https',
  
  // WAF 규칙
  wafRules: {
    rateLimit: {
      rate: 2000, // 초당 요청 수 제한
      burst: 5000
    },
    geoRestriction: {
      allowList: ['KR', 'US', 'JP'], // 허용 국가
      blockList: []
    }
  },
  
  // 헤더 보안
  securityHeaders: {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
  }
};

// 보안 헤더 적용 함수
const applySecurityHeaders = (response) => {
  Object.entries(securityConfig.securityHeaders).forEach(([header, value]) => {
    response.headers.set(header, value);
  });
  return response;
};
```

---


AWS CloudFront는 전 세계 사용자에게 빠르고 안전한 콘텐츠 전송을 제공하는 강력한 CDN 서비스입니다. 

### 핵심 포인트
- **캐싱**: 자주 요청되는 콘텐츠를 엣지 서버에 저장하여 로딩 속도 향상
- **지리적 분산**: 전 세계 여러 지역에 서버를 배치하여 지연 시간 최소화
- **보안**: HTTPS, WAF, 지리적 제한 등 다양한 보안 기능 제공
- **비용 효율성**: 사용량 기반 과금으로 비용 최적화 가능

### 다음 단계
1. S3 버킷에 정적 웹사이트 파일 업로드
2. CloudFront 배포 생성 및 S3 연결
3. 사용자 정의 도메인 설정 (Route 53)
4. 캐싱 정책 및 보안 설정 최적화
5. 성능 모니터링 및 비용 관리

이 가이드를 따라하면 빠르고 안전한 CDN 구축이 가능합니다!

- **캐싱**: 자주 요청되는 콘텐츠를 엣지 서버에 저장하여 로딩 속도 향상
- **지리적 분산**: 전 세계 여러 지역에 서버를 배치하여 지연 시간 최소화
- **보안**: HTTPS, WAF, 지리적 제한 등 다양한 보안 기능 제공
- **비용 효율성**: 사용량 기반 과금으로 비용 최적화 가능

1. S3 버킷에 정적 웹사이트 파일 업로드
2. CloudFront 배포 생성 및 S3 연결
3. 사용자 정의 도메인 설정 (Route 53)
4. 캐싱 정책 및 보안 설정 최적화
5. 성능 모니터링 및 비용 관리

이 가이드를 따라하면 빠르고 안전한 CDN 구축이 가능합니다!






---

```javascript
// 정적 파일 업로드 예시
const uploadStaticFiles = async () => {
  const files = [
    { key: 'index.html', body: '<html><body>Hello World!</body></html>' },
    { key: 'styles.css', body: 'body { font-family: Arial; }' },
    { key: 'script.js', body: 'console.log("Hello from CDN!");' }
  ];
  
  for (const file of files) {
    const params = {
      Bucket: 'my-website-bucket',
      Key: file.key,
      Body: file.body,
      ContentType: getContentType(file.key)
    };
    
    await s3.putObject(params).promise();
    console.log(`${file.key} 업로드 완료`);
  }
};

const getContentType = (filename) => {
  const ext = filename.split('.').pop();
  const types = {
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'png': 'image/png',
    'jpg': 'image/jpeg'
  };
  return types[ext] || 'application/octet-stream';
};
```

```javascript
// CloudFront 압축 설정
const compressionConfig = {
  Compress: true,
  CompressibleContentTypes: [
    'text/html',
    'text/css',
    'application/javascript',
    'application/json',
    'text/xml',
    'application/xml',
    'application/xml+rss',
    'text/javascript'
  ]
};

// 캐시 최적화 설정
const cacheOptimization = {
  // 정적 자산 (이미지, CSS, JS)
  staticAssets: {
    TTL: 31536000, // 1년
    Headers: ['Accept-Encoding'],
    Compress: true
  },
  
  // HTML 페이지
  htmlPages: {
    TTL: 3600, // 1시간
    Headers: ['Accept-Language'],
    Compress: true
  },
  
  // API 응답
  apiResponses: {
    TTL: 300, // 5분
    Headers: ['Authorization'],
    Compress: true
  }
};
```

```javascript
// CDN 성능 모니터링
class CDNPerformanceMonitor {
  constructor() {
    this.metrics = {
      loadTimes: [],
      errorRates: [],
      cacheHits: 0,
      cacheMisses: 0
    };
  }
  
  // 리소스 로딩 시간 측정
  measureLoadTime(url) {
    const startTime = performance.now();
    
    return fetch(url)
      .then(response => {
        const loadTime = performance.now() - startTime;
        this.metrics.loadTimes.push(loadTime);
        
        // 캐시 히트 여부 확인
        if (response.headers.get('x-cache') === 'Hit from cloudfront') {
          this.metrics.cacheHits++;
        } else {
          this.metrics.cacheMisses++;
        }
        
        return response;
      })
      .catch(error => {
        this.metrics.errorRates.push({
          url,
          error: error.message,
          timestamp: Date.now()
        });
        throw error;
      });
  }
  
  // 성능 통계 출력
  getPerformanceStats() {
    const avgLoadTime = this.metrics.loadTimes.reduce((a, b) => a + b, 0) / this.metrics.loadTimes.length;
    const cacheHitRate = this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses);
    
    return {
      averageLoadTime: avgLoadTime.toFixed(2) + 'ms',
      cacheHitRate: (cacheHitRate * 100).toFixed(2) + '%',
      totalRequests: this.metrics.loadTimes.length,
      errorCount: this.metrics.errorRates.length
    };
  }
}

// 사용 예시
const monitor = new CDNPerformanceMonitor();

// 여러 리소스 로딩 시간 측정
const urls = [
  'https://d1234.cloudfront.net/css/style.css',
  'https://d1234.cloudfront.net/js/app.js',
  'https://d1234.cloudfront.net/images/logo.png'
];

Promise.all(urls.map(url => monitor.measureLoadTime(url)))
  .then(() => {
    console.log('성능 통계:', monitor.getPerformanceStats());
  })
  .catch(error => console.error('모니터링 오류:', error));
```

---

```javascript
// CloudFront 압축 설정
const compressionConfig = {
  Compress: true,
  CompressibleContentTypes: [
    'text/html',
    'text/css',
    'application/javascript',
    'application/json',
    'text/xml',
    'application/xml',
    'application/xml+rss',
    'text/javascript'
  ]
};

// 캐시 최적화 설정
const cacheOptimization = {
  // 정적 자산 (이미지, CSS, JS)
  staticAssets: {
    TTL: 31536000, // 1년
    Headers: ['Accept-Encoding'],
    Compress: true
  },
  
  // HTML 페이지
  htmlPages: {
    TTL: 3600, // 1시간
    Headers: ['Accept-Language'],
    Compress: true
  },
  
  // API 응답
  apiResponses: {
    TTL: 300, // 5분
    Headers: ['Authorization'],
    Compress: true
  }
};
```

```javascript
// CDN 성능 모니터링
class CDNPerformanceMonitor {
  constructor() {
    this.metrics = {
      loadTimes: [],
      errorRates: [],
      cacheHits: 0,
      cacheMisses: 0
    };
  }
  
  // 리소스 로딩 시간 측정
  measureLoadTime(url) {
    const startTime = performance.now();
    
    return fetch(url)
      .then(response => {
        const loadTime = performance.now() - startTime;
        this.metrics.loadTimes.push(loadTime);
        
        // 캐시 히트 여부 확인
        if (response.headers.get('x-cache') === 'Hit from cloudfront') {
          this.metrics.cacheHits++;
        } else {
          this.metrics.cacheMisses++;
        }
        
        return response;
      })
      .catch(error => {
        this.metrics.errorRates.push({
          url,
          error: error.message,
          timestamp: Date.now()
        });
        throw error;
      });
  }
  
  // 성능 통계 출력
  getPerformanceStats() {
    const avgLoadTime = this.metrics.loadTimes.reduce((a, b) => a + b, 0) / this.metrics.loadTimes.length;
    const cacheHitRate = this.metrics.cacheHits / (this.metrics.cacheHits + this.metrics.cacheMisses);
    
    return {
      averageLoadTime: avgLoadTime.toFixed(2) + 'ms',
      cacheHitRate: (cacheHitRate * 100).toFixed(2) + '%',
      totalRequests: this.metrics.loadTimes.length,
      errorCount: this.metrics.errorRates.length
    };
  }
}

// 사용 예시
const monitor = new CDNPerformanceMonitor();

// 여러 리소스 로딩 시간 측정
const urls = [
  'https://d1234.cloudfront.net/css/style.css',
  'https://d1234.cloudfront.net/js/app.js',
  'https://d1234.cloudfront.net/images/logo.png'
];

Promise.all(urls.map(url => monitor.measureLoadTime(url)))
  .then(() => {
    console.log('성능 통계:', monitor.getPerformanceStats());
  })
  .catch(error => console.error('모니터링 오류:', error));
```

---


```javascript
// CDN 비용 계산기
class CDNCostCalculator {
  constructor() {
    this.pricing = {
      dataTransfer: {
        'us-east-1': 0.085, // USD per GB
        'eu-west-1': 0.085,
        'ap-northeast-1': 0.120
      },
      requests: {
        'us-east-1': 0.0075, // USD per 10,000 requests
        'eu-west-1': 0.0075,
        'ap-northeast-1': 0.0090
      },
      invalidation: 0.005 // USD per path
    };
  }
  
  // 월간 비용 계산
  calculateMonthlyCost(usage) {
    const dataTransferCost = usage.dataTransferGB * this.pricing.dataTransfer['ap-northeast-1'];
    const requestCost = (usage.requests / 10000) * this.pricing.requests['ap-northeast-1'];
    const invalidationCost = usage.invalidations * this.pricing.invalidation;
    
    return {
      dataTransfer: dataTransferCost,
      requests: requestCost,
      invalidations: invalidationCost,
      total: dataTransferCost + requestCost + invalidationCost
    };
  }
  
  // 비용 최적화 권장사항
  getOptimizationTips(usage) {
    const tips = [];
    
    if (usage.invalidations > 1000) {
      tips.push('캐시 무효화 횟수를 줄이세요. 전체 무효화 대신 특정 경로만 무효화하세요.');
    }
    
    if (usage.dataTransferGB > 1000) {
      tips.push('이미지 압축을 활성화하고 WebP 형식을 사용하세요.');
    }
    
    return tips;
  }
}

// 사용 예시
const calculator = new CDNCostCalculator();
const monthlyUsage = {
  dataTransferGB: 500,
  requests: 1000000,
  invalidations: 50
};

const costs = calculator.calculateMonthlyCost(monthlyUsage);
console.log('월간 CDN 비용:', costs);
console.log('최적화 팁:', calculator.getOptimizationTips(monthlyUsage));
```

```javascript
// CloudFront 보안 설정
const securityConfig = {
  // HTTPS 강제 적용
  viewerProtocolPolicy: 'redirect-to-https',
  
  // WAF 규칙
  wafRules: {
    rateLimit: {
      rate: 2000, // 초당 요청 수 제한
      burst: 5000
    },
    geoRestriction: {
      allowList: ['KR', 'US', 'JP'], // 허용 국가
      blockList: []
    }
  },
  
  // 헤더 보안
  securityHeaders: {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
  }
};

// 보안 헤더 적용 함수
const applySecurityHeaders = (response) => {
  Object.entries(securityConfig.securityHeaders).forEach(([header, value]) => {
    response.headers.set(header, value);
  });
  return response;
};
```

---

```javascript
// CDN 비용 계산기
class CDNCostCalculator {
  constructor() {
    this.pricing = {
      dataTransfer: {
        'us-east-1': 0.085, // USD per GB
        'eu-west-1': 0.085,
        'ap-northeast-1': 0.120
      },
      requests: {
        'us-east-1': 0.0075, // USD per 10,000 requests
        'eu-west-1': 0.0075,
        'ap-northeast-1': 0.0090
      },
      invalidation: 0.005 // USD per path
    };
  }
  
  // 월간 비용 계산
  calculateMonthlyCost(usage) {
    const dataTransferCost = usage.dataTransferGB * this.pricing.dataTransfer['ap-northeast-1'];
    const requestCost = (usage.requests / 10000) * this.pricing.requests['ap-northeast-1'];
    const invalidationCost = usage.invalidations * this.pricing.invalidation;
    
    return {
      dataTransfer: dataTransferCost,
      requests: requestCost,
      invalidations: invalidationCost,
      total: dataTransferCost + requestCost + invalidationCost
    };
  }
  
  // 비용 최적화 권장사항
  getOptimizationTips(usage) {
    const tips = [];
    
    if (usage.invalidations > 1000) {
      tips.push('캐시 무효화 횟수를 줄이세요. 전체 무효화 대신 특정 경로만 무효화하세요.');
    }
    
    if (usage.dataTransferGB > 1000) {
      tips.push('이미지 압축을 활성화하고 WebP 형식을 사용하세요.');
    }
    
    return tips;
  }
}

// 사용 예시
const calculator = new CDNCostCalculator();
const monthlyUsage = {
  dataTransferGB: 500,
  requests: 1000000,
  invalidations: 50
};

const costs = calculator.calculateMonthlyCost(monthlyUsage);
console.log('월간 CDN 비용:', costs);
console.log('최적화 팁:', calculator.getOptimizationTips(monthlyUsage));
```

```javascript
// CloudFront 보안 설정
const securityConfig = {
  // HTTPS 강제 적용
  viewerProtocolPolicy: 'redirect-to-https',
  
  // WAF 규칙
  wafRules: {
    rateLimit: {
      rate: 2000, // 초당 요청 수 제한
      burst: 5000
    },
    geoRestriction: {
      allowList: ['KR', 'US', 'JP'], // 허용 국가
      blockList: []
    }
  },
  
  // 헤더 보안
  securityHeaders: {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
  }
};

// 보안 헤더 적용 함수
const applySecurityHeaders = (response) => {
  Object.entries(securityConfig.securityHeaders).forEach(([header, value]) => {
    response.headers.set(header, value);
  });
  return response;
};
```

---


AWS CloudFront는 전 세계 사용자에게 빠르고 안전한 콘텐츠 전송을 제공하는 강력한 CDN 서비스입니다. 

- **캐싱**: 자주 요청되는 콘텐츠를 엣지 서버에 저장하여 로딩 속도 향상
- **지리적 분산**: 전 세계 여러 지역에 서버를 배치하여 지연 시간 최소화
- **보안**: HTTPS, WAF, 지리적 제한 등 다양한 보안 기능 제공
- **비용 효율성**: 사용량 기반 과금으로 비용 최적화 가능

1. S3 버킷에 정적 웹사이트 파일 업로드
2. CloudFront 배포 생성 및 S3 연결
3. 사용자 정의 도메인 설정 (Route 53)
4. 캐싱 정책 및 보안 설정 최적화
5. 성능 모니터링 및 비용 관리

이 가이드를 따라하면 빠르고 안전한 CDN 구축이 가능합니다!

- **캐싱**: 자주 요청되는 콘텐츠를 엣지 서버에 저장하여 로딩 속도 향상
- **지리적 분산**: 전 세계 여러 지역에 서버를 배치하여 지연 시간 최소화
- **보안**: HTTPS, WAF, 지리적 제한 등 다양한 보안 기능 제공
- **비용 효율성**: 사용량 기반 과금으로 비용 최적화 가능

1. S3 버킷에 정적 웹사이트 파일 업로드
2. CloudFront 배포 생성 및 S3 연결
3. 사용자 정의 도메인 설정 (Route 53)
4. 캐싱 정책 및 보안 설정 최적화
5. 성능 모니터링 및 비용 관리

이 가이드를 따라하면 빠르고 안전한 CDN 구축이 가능합니다!






---





## CDN이란 무엇인가? 🤔

### CDN의 정의
**CDN(Content Delivery Network)**은 웹 콘텐츠를 전 세계 여러 지역에 분산 저장하여 사용자에게 빠르게 전달하는 네트워크 시스템입니다.

### CDN이 필요한 이유
```javascript
// CDN 없이 웹사이트를 로드하는 경우
const loadWebsiteWithoutCDN = () => {
  // 사용자가 한국에서 미국 서버의 이미지를 요청
  const imageUrl = "https://us-server.com/images/photo.jpg";
  // 네트워크 지연: 200-300ms
  return fetch(imageUrl); // 느린 로딩
};

// CDN을 사용하는 경우
const loadWebsiteWithCDN = () => {
  // 사용자가 한국에서 한국 CDN 서버의 이미지를 요청
  const imageUrl = "https://cdn.example.com/images/photo.jpg";
  // 네트워크 지연: 20-50ms
  return fetch(imageUrl); // 빠른 로딩
};
```

### CDN의 작동 원리
1. **캐싱**: 자주 요청되는 콘텐츠를 엣지 서버에 저장
2. **지리적 분산**: 전 세계 여러 지역에 서버 배치
3. **지능적 라우팅**: 사용자와 가장 가까운 서버로 요청 전달

---

## CloudFront의 핵심 개념 🧠

## JavaScript로 CDN 활용하기 💻

### CDN 리소스 로딩 최적화
```javascript
// CDN을 활용한 리소스 로딩
class CDNResourceLoader {
  constructor(cdnDomain) {
    this.cdnDomain = cdnDomain;
    this.cache = new Map();
  }
  
  // 이미지 최적화 로딩
  loadImage(path, options = {}) {
    const url = `${this.cdnDomain}/${path}`;
    
    return new Promise((resolve, reject) => {
      const img = new Image();
      
      if (options.lazy) {
        // 지연 로딩 구현
        const observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              img.src = url;
              observer.unobserve(entry.target);
            }
          });
        });
        observer.observe(img);
      } else {
        img.src = url;
      }
      
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`이미지 로딩 실패: ${url}`));
    });
  }
  
  // JavaScript 모듈 로딩
  loadScript(path, options = {}) {
    const url = `${this.cdnDomain}/${path}`;
    
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = url;
      script.async = options.async !== false;
      script.defer = options.defer || false;
      
      script.onload = () => resolve(script);
      script.onerror = () => reject(new Error(`스크립트 로딩 실패: ${url}`));
      
      document.head.appendChild(script);
    });
  }
  
  // CSS 스타일시트 로딩
  loadStylesheet(path) {
    const url = `${this.cdnDomain}/${path}`;
    
    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      
      link.onload = () => resolve(link);
      link.onerror = () => reject(new Error(`스타일시트 로딩 실패: ${url}`));
      
      document.head.appendChild(link);
    });
  }
}

// 사용 예시
const cdnLoader = new CDNResourceLoader('https://d1234.cloudfront.net');

// 이미지 지연 로딩
cdnLoader.loadImage('images/hero.jpg', { lazy: true })
  .then(img => document.body.appendChild(img))
  .catch(error => console.error(error));

// 스크립트 로딩
cdnLoader.loadScript('js/app.js', { async: true })
  .then(() => console.log('앱 스크립트 로딩 완료'))
  .catch(error => console.error(error));
```

