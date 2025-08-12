---
title: AWS EC2 인스턴스 유형
tags: [aws, compute, ec2, instance-types, cloud-computing]
updated: 2024-12-19
---

# AWS EC2 인스턴스 유형

## 배경

AWS EC2(Elastic Compute Cloud)는 클라우드에서 가상 서버를 제공하는 핵심 서비스입니다. 다양한 워크로드와 요구사항에 맞춰 최적화된 인스턴스 유형을 제공하여, 사용자는 애플리케이션의 특성에 맞는 적절한 컴퓨팅 리소스를 선택할 수 있습니다.

### EC2 인스턴스의 필요성
- **확장성**: 필요에 따라 리소스를 동적으로 조정
- **비용 효율성**: 사용한 만큼만 비용 지불
- **다양성**: 워크로드에 최적화된 다양한 인스턴스 유형
- **관리 편의성**: AWS가 하드웨어 관리 담당

## 핵심

### 인스턴스 유형 분류

AWS EC2 인스턴스는 크게 5가지 카테고리로 분류됩니다:

| **인스턴스 유형** | **특징** | **대표적인 용도** |
|------------------|---------|----------------|
| 범용 (General Purpose) | CPU, 메모리, 네트워크 성능 균형 | 웹 서버, 애플리케이션 서버 |
| 컴퓨팅 최적화 (Compute Optimized) | 고성능 CPU 제공 | 고성능 연산 작업, 게임 서버 |
| 메모리 최적화 (Memory Optimized) | 높은 RAM 제공 | 대용량 인메모리 데이터베이스 |
| 스토리지 최적화 (Storage Optimized) | 고속 디스크 I/O 제공 | 빅데이터, 로그 분석 |
| 가속 컴퓨팅 (Accelerated Computing) | GPU 또는 FPGA 제공 | AI, 머신러닝, 그래픽 렌더링 |

### 1. 범용 (General Purpose) 인스턴스

범용 인스턴스는 CPU, 메모리, 네트워크 성능이 균형 있게 제공되는 유형입니다.

#### 주요 시리즈
- **T 시리즈 (T3, T3a, T2)**: 버스트 가능한 성능, 비용 효율적
- **M 시리즈 (M6g, M5, M4)**: 다양한 애플리케이션에 적합한 범용 인스턴스

#### 사용 사례
- 웹 서버 및 애플리케이션 서버
- 개발 및 테스트 환경
- 소규모 데이터베이스
- 마이크로서비스

### 2. 컴퓨팅 최적화 (Compute Optimized) 인스턴스

고성능 CPU를 제공하여 컴퓨팅 성능이 중요한 애플리케이션에 적합합니다.

#### 주요 시리즈
- **C 시리즈 (C6g, C5, C4)**: 고성능 연산 작업에 최적화

#### 사용 사례
- 고성능 웹 서버
- 게임 서버
- 배치 처리 작업
- 과학 계산

### 3. 메모리 최적화 (Memory Optimized) 인스턴스

RAM이 많아 대규모 데이터 처리 및 캐싱 작업에 최적화된 인스턴스입니다.

#### 주요 시리즈
- **R 시리즈 (R6g, R5, R4)**: 인메모리 데이터베이스에 적합
- **X 시리즈 (X1, X2)**: 고성능 SAP, 인메모리 애플리케이션에 적합

#### 사용 사례
- Redis, Memcached 등 인메모리 데이터베이스
- SAP HANA
- 대용량 데이터 분석
- 실시간 빅데이터 처리

### 4. 스토리지 최적화 (Storage Optimized) 인스턴스

고속 디스크 I/O 성능을 제공하여 빅데이터 및 로그 분석에 적합합니다.

#### 주요 시리즈
- **I 시리즈 (I3, I4)**: NVMe SSD를 통한 빠른 데이터 접근
- **D 시리즈 (D2)**: 대용량 데이터 저장 및 분석에 최적

#### 사용 사례
- 빅데이터 워크로드
- 로그 분석
- 데이터 웨어하우스
- 고성능 데이터베이스

### 5. 가속 컴퓨팅 (Accelerated Computing) 인스턴스

GPU 또는 FPGA를 사용하여 머신러닝, AI, 그래픽 처리 등에 최적화된 인스턴스입니다.

#### 주요 시리즈
- **P 시리즈 (P4, P3)**: GPU를 활용한 머신러닝 및 딥러닝 모델 학습
- **G 시리즈 (G5, G4)**: 그래픽 렌더링 및 동영상 처리에 최적

#### 사용 사례
- 딥러닝 모델 학습
- 그래픽 렌더링
- 동영상 인코딩
- 과학적 시뮬레이션

## 예시

### 인스턴스 선택 예시

#### AWS SDK를 사용한 인스턴스 생성
```javascript
const AWS = require('aws-sdk');

// AWS EC2 클라이언트 생성
const ec2 = new AWS.EC2({
    region: 'ap-northeast-2',
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
});

// 웹 서버용 범용 인스턴스 생성 (T3.micro)
async function createWebServer() {
    const params = {
        ImageId: 'ami-12345678',
        InstanceType: 't3.micro',  // 범용 인스턴스
        MinCount: 1,
        MaxCount: 1,
        KeyName: 'my-key-pair',
        SecurityGroupIds: ['sg-12345678'],
        TagSpecifications: [{
            ResourceType: 'instance',
            Tags: [{
                Key: 'Name',
                Value: 'WebServer'
            }]
        }]
    };

    try {
        const result = await ec2.runInstances(params).promise();
        console.log('웹 서버 인스턴스 생성 완료:', result.Instances[0].InstanceId);
        return result.Instances[0];
    } catch (error) {
        console.error('인스턴스 생성 실패:', error);
        throw error;
    }
}

// 고성능 연산용 컴퓨팅 최적화 인스턴스 생성 (C5.large)
async function createComputeInstance() {
    const params = {
        ImageId: 'ami-12345678',
        InstanceType: 'c5.large',  // 컴퓨팅 최적화 인스턴스
        MinCount: 1,
        MaxCount: 1,
        KeyName: 'my-key-pair',
        SecurityGroupIds: ['sg-12345678'],
        TagSpecifications: [{
            ResourceType: 'instance',
            Tags: [{
                Key: 'Name',
                Value: 'ComputeServer'
            }]
        }]
    };

    try {
        const result = await ec2.runInstances(params).promise();
        console.log('컴퓨팅 인스턴스 생성 완료:', result.Instances[0].InstanceId);
        return result.Instances[0];
    } catch (error) {
        console.error('인스턴스 생성 실패:', error);
        throw error;
    }
}

// 인메모리 데이터베이스용 메모리 최적화 인스턴스 생성 (R5.large)
async function createMemoryInstance() {
    const params = {
        ImageId: 'ami-12345678',
        InstanceType: 'r5.large',  // 메모리 최적화 인스턴스
        MinCount: 1,
        MaxCount: 1,
        KeyName: 'my-key-pair',
        SecurityGroupIds: ['sg-12345678'],
        TagSpecifications: [{
            ResourceType: 'instance',
            Tags: [{
                Key: 'Name',
                Value: 'DatabaseServer'
            }]
        }]
    };

    try {
        const result = await ec2.runInstances(params).promise();
        console.log('메모리 최적화 인스턴스 생성 완료:', result.Instances[0].InstanceId);
        return result.Instances[0];
    } catch (error) {
        console.error('인스턴스 생성 실패:', error);
        throw error;
    }
}
```

#### 인스턴스 유형별 비용 계산
```javascript
// 인스턴스 유형별 비용 정보
const instanceCosts = {
    't3.micro': {
        vCPU: 2,
        memory: '1GB',
        hourlyCost: 0.0104,
        monthlyCost: 0.0104 * 24 * 30,
        useCase: '개발/테스트'
    },
    'c5.large': {
        vCPU: 2,
        memory: '4GB',
        hourlyCost: 0.085,
        monthlyCost: 0.085 * 24 * 30,
        useCase: '고성능 연산'
    },
    'r5.large': {
        vCPU: 2,
        memory: '16GB',
        hourlyCost: 0.126,
        monthlyCost: 0.126 * 24 * 30,
        useCase: '메모리 집약적'
    },
    'i3.large': {
        vCPU: 2,
        memory: '15GB',
        hourlyCost: 0.156,
        monthlyCost: 0.156 * 24 * 30,
        useCase: '스토리지 최적화'
    },
    'g4dn.xlarge': {
        vCPU: 4,
        memory: '16GB',
        hourlyCost: 0.526,
        monthlyCost: 0.526 * 24 * 30,
        useCase: 'GPU 컴퓨팅'
    }
};

// 비용 계산 함수
function calculateCost(instanceType, hours = 1) {
    const instance = instanceCosts[instanceType];
    if (!instance) {
        throw new Error(`알 수 없는 인스턴스 유형: ${instanceType}`);
    }
    
    return {
        instanceType,
        hourlyCost: instance.hourlyCost,
        totalCost: instance.hourlyCost * hours,
        monthlyCost: instance.monthlyCost,
        specs: {
            vCPU: instance.vCPU,
            memory: instance.memory
        },
        useCase: instance.useCase
    };
}

// 사용 예시
console.log(calculateCost('t3.micro', 24));  // 24시간 사용 비용
console.log(calculateCost('c5.large', 168)); // 1주일 사용 비용
```

#### 워크로드별 인스턴스 추천 시스템
```javascript
class InstanceRecommender {
    constructor() {
        this.workloadTypes = {
            webServer: {
                recommended: ['t3.micro', 't3.small', 'm5.large'],
                criteria: ['CPU', 'Memory', 'Network'],
                description: '웹 서버 및 애플리케이션 서버'
            },
            database: {
                recommended: ['r5.large', 'r5.xlarge', 'r6g.large'],
                criteria: ['Memory', 'Storage', 'Network'],
                description: '데이터베이스 서버'
            },
            compute: {
                recommended: ['c5.large', 'c5.xlarge', 'c6g.large'],
                criteria: ['CPU', 'Network'],
                description: '고성능 컴퓨팅 작업'
            },
            storage: {
                recommended: ['i3.large', 'i3.xlarge', 'd2.xlarge'],
                criteria: ['Storage', 'I/O'],
                description: '대용량 스토리지 및 분석'
            },
            gpu: {
                recommended: ['g4dn.xlarge', 'p3.2xlarge', 'p4d.24xlarge'],
                criteria: ['GPU', 'Memory'],
                description: '머신러닝 및 그래픽 처리'
            }
        };
    }
    
    recommendInstance(workloadType, budget = null) {
        const workload = this.workloadTypes[workloadType];
        if (!workload) {
            throw new Error(`지원하지 않는 워크로드 유형: ${workloadType}`);
        }
        
        let recommendations = workload.recommended;
        
        // 예산 제약이 있는 경우 필터링
        if (budget) {
            recommendations = recommendations.filter(instanceType => {
                const cost = instanceCosts[instanceType];
                return cost && cost.monthlyCost <= budget;
            });
        }
        
        return {
            workloadType,
            description: workload.description,
            criteria: workload.criteria,
            recommendations: recommendations.map(instanceType => ({
                instanceType,
                ...instanceCosts[instanceType]
            }))
        };
    }
    
    compareInstances(instanceTypes) {
        return instanceTypes.map(instanceType => ({
            instanceType,
            ...instanceCosts[instanceType]
        }));
    }
}

// 사용 예시
const recommender = new InstanceRecommender();

console.log(recommender.recommendInstance('webServer'));
console.log(recommender.recommendInstance('database', 100)); // 월 100달러 이하
console.log(recommender.compareInstances(['t3.micro', 'c5.large', 'r5.large']));
```

## 운영 팁

### 인스턴스 선택 가이드라인

#### 워크로드별 선택 기준
```javascript
const workloadGuidelines = {
    cpuIntensive: {
        recommendation: 'C 시리즈 선택',
        examples: ['c5.large', 'c5.xlarge', 'c6g.large'],
        useCases: ['배치 처리', '게임 서버', '과학 계산']
    },
    memoryIntensive: {
        recommendation: 'R 시리즈 선택',
        examples: ['r5.large', 'r5.xlarge', 'r6g.large'],
        useCases: ['Redis', 'SAP HANA', '대용량 데이터 분석']
    },
    storageIntensive: {
        recommendation: 'I 시리즈 선택',
        examples: ['i3.large', 'i3.xlarge', 'i4.large'],
        useCases: ['빅데이터', '로그 분석', '데이터 웨어하우스']
    },
    gpuRequired: {
        recommendation: 'P, G 시리즈 선택',
        examples: ['g4dn.xlarge', 'p3.2xlarge', 'p4d.24xlarge'],
        useCases: ['머신러닝', '그래픽 렌더링', 'AI 모델 학습']
    },
    generalPurpose: {
        recommendation: 'T, M 시리즈 선택',
        examples: ['t3.micro', 'm5.large', 'm6g.large'],
        useCases: ['웹 서버', '애플리케이션 서버', '개발 환경']
    }
};
```

### 비용 최적화

#### Reserved Instances 관리
```javascript
class ReservedInstanceManager {
    constructor() {
        this.reservedInstances = new Map();
    }
    
    // Reserved Instance 구매
    purchaseReservedInstance(instanceType, term = 1, paymentOption = 'all') {
        const baseCost = instanceCosts[instanceType].monthlyCost;
        let discount = 0;
        
        switch (term) {
            case 1:
                discount = paymentOption === 'all' ? 0.40 : 0.30;
                break;
            case 3:
                discount = paymentOption === 'all' ? 0.60 : 0.50;
                break;
            default:
                discount = 0.30;
        }
        
        const reservedCost = baseCost * (1 - discount);
        
        this.reservedInstances.set(instanceType, {
            term,
            paymentOption,
            originalCost: baseCost,
            reservedCost,
            savings: baseCost - reservedCost,
            savingsPercentage: discount * 100
        });
        
        return this.reservedInstances.get(instanceType);
    }
    
    // 비용 절약 계산
    calculateSavings(instanceType, usageHours = 730) { // 730시간 = 1개월
        const onDemandCost = instanceCosts[instanceType].hourlyCost * usageHours;
        const reserved = this.reservedInstances.get(instanceType);
        
        if (!reserved) {
            return { onDemandCost, reservedCost: onDemandCost, savings: 0 };
        }
        
        const reservedCost = reserved.reservedCost;
        const savings = onDemandCost - reservedCost;
        
        return {
            onDemandCost,
            reservedCost,
            savings,
            savingsPercentage: (savings / onDemandCost) * 100
        };
    }
}

// 사용 예시
const riManager = new ReservedInstanceManager();
riManager.purchaseReservedInstance('c5.large', 1, 'all');
console.log(riManager.calculateSavings('c5.large'));
```

#### Spot Instances 활용
```javascript
class SpotInstanceManager {
    constructor() {
        this.spotPrices = new Map();
    }
    
    // Spot Instance 요청
    async requestSpotInstance(instanceType, maxPrice = null) {
        const onDemandPrice = instanceCosts[instanceType].hourlyCost;
        const spotPrice = maxPrice || (onDemandPrice * 0.7); // 기본 30% 할인
        
        return {
            instanceType,
            onDemandPrice,
            spotPrice,
            savings: onDemandPrice - spotPrice,
            savingsPercentage: ((onDemandPrice - spotPrice) / onDemandPrice) * 100,
            risk: 'Spot Instance는 가용성에 따라 중단될 수 있습니다.'
        };
    }
    
    // Spot Instance 모니터링
    monitorSpotInstance(instanceId) {
        return {
            instanceId,
            status: 'running',
            currentPrice: 0.05,
            maxPrice: 0.08,
            uptime: '2 hours',
            risk: 'low'
        };
    }
}
```

### 성능 모니터링

#### CloudWatch 메트릭 수집
```javascript
const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch();

class InstanceMonitor {
    constructor(instanceId) {
        this.instanceId = instanceId;
    }
    
    // CPU 사용률 모니터링
    async getCPUUtilization(duration = 3600) {
        const params = {
            MetricDataQueries: [{
                Id: 'cpu',
                MetricStat: {
                    Metric: {
                        Namespace: 'AWS/EC2',
                        MetricName: 'CPUUtilization',
                        Dimensions: [{
                            Name: 'InstanceId',
                            Value: this.instanceId
                        }]
                    },
                    Period: 300,
                    Stat: 'Average'
                }
            }],
            StartTime: new Date(Date.now() - duration * 1000),
            EndTime: new Date()
        };
        
        try {
            const result = await cloudwatch.getMetricData(params).promise();
            return result.MetricDataResults[0];
        } catch (error) {
            console.error('CPU 사용률 조회 실패:', error);
            throw error;
        }
    }
    
    // 메모리 사용률 모니터링
    async getMemoryUtilization() {
        // CloudWatch Agent가 설치되어 있어야 함
        const params = {
            MetricDataQueries: [{
                Id: 'memory',
                MetricStat: {
                    Metric: {
                        Namespace: 'System/Linux',
                        MetricName: 'MemoryUtilization',
                        Dimensions: [{
                            Name: 'InstanceId',
                            Value: this.instanceId
                        }]
                    },
                    Period: 300,
                    Stat: 'Average'
                }
            }],
            StartTime: new Date(Date.now() - 3600 * 1000),
            EndTime: new Date()
        };
        
        try {
            const result = await cloudwatch.getMetricData(params).promise();
            return result.MetricDataResults[0];
        } catch (error) {
            console.error('메모리 사용률 조회 실패:', error);
            throw error;
        }
    }
    
    // 인스턴스 성능 분석
    async analyzePerformance() {
        const cpuData = await this.getCPUUtilization();
        const memoryData = await this.getMemoryUtilization();
        
        const avgCPU = cpuData.Values.reduce((sum, val) => sum + val, 0) / cpuData.Values.length;
        const avgMemory = memoryData.Values.reduce((sum, val) => sum + val, 0) / memoryData.Values.length;
        
        return {
            instanceId: this.instanceId,
            averageCPU: avgCPU,
            averageMemory: avgMemory,
            recommendation: this.getRecommendation(avgCPU, avgMemory)
        };
    }
    
    getRecommendation(cpu, memory) {
        if (cpu > 80) {
            return 'CPU 사용률이 높습니다. 더 큰 인스턴스로 업그레이드를 고려하세요.';
        } else if (memory > 80) {
            return '메모리 사용률이 높습니다. 메모리 최적화 인스턴스로 변경을 고려하세요.';
        } else if (cpu < 20 && memory < 20) {
            return '리소스 사용률이 낮습니다. 더 작은 인스턴스로 다운사이징을 고려하세요.';
        } else {
            return '현재 인스턴스 크기가 적절합니다.';
        }
    }
}

// 사용 예시
const monitor = new InstanceMonitor('i-1234567890abcdef0');
monitor.analyzePerformance().then(result => {
    console.log('성능 분석 결과:', result);
});
```

### 보안 고려사항

#### 보안 그룹 설정
```javascript
class SecurityGroupManager {
    constructor() {
        this.ec2 = new AWS.EC2();
    }
    
    // 웹 서버용 보안 그룹 생성
    async createWebServerSecurityGroup() {
        const params = {
            GroupName: 'WebServerSG',
            Description: '웹 서버용 보안 그룹',
            VpcId: 'vpc-12345678',
            IpPermissions: [
                {
                    IpProtocol: 'tcp',
                    FromPort: 80,
                    ToPort: 80,
                    IpRanges: [{ CidrIp: '0.0.0.0/0' }]
                },
                {
                    IpProtocol: 'tcp',
                    FromPort: 443,
                    ToPort: 443,
                    IpRanges: [{ CidrIp: '0.0.0.0/0' }]
                },
                {
                    IpProtocol: 'tcp',
                    FromPort: 22,
                    ToPort: 22,
                    IpRanges: [{ CidrIp: '10.0.0.0/16' }] // SSH는 내부 네트워크에서만
                }
            ]
        };
        
        try {
            const result = await this.ec2.createSecurityGroup(params).promise();
            console.log('보안 그룹 생성 완료:', result.GroupId);
            return result.GroupId;
        } catch (error) {
            console.error('보안 그룹 생성 실패:', error);
            throw error;
        }
    }
    
    // 데이터베이스용 보안 그룹 생성
    async createDatabaseSecurityGroup() {
        const params = {
            GroupName: 'DatabaseSG',
            Description: '데이터베이스용 보안 그룹',
            VpcId: 'vpc-12345678',
            IpPermissions: [
                {
                    IpProtocol: 'tcp',
                    FromPort: 3306, // MySQL
                    ToPort: 3306,
                    IpRanges: [{ CidrIp: '10.0.0.0/16' }] // 내부 네트워크에서만
                },
                {
                    IpProtocol: 'tcp',
                    FromPort: 5432, // PostgreSQL
                    ToPort: 5432,
                    IpRanges: [{ CidrIp: '10.0.0.0/16' }]
                }
            ]
        };
        
        try {
            const result = await this.ec2.createSecurityGroup(params).promise();
            console.log('데이터베이스 보안 그룹 생성 완료:', result.GroupId);
            return result.GroupId;
        } catch (error) {
            console.error('보안 그룹 생성 실패:', error);
            throw error;
        }
    }
}
```

## 참고

### 인스턴스 유형별 상세 사양

#### 최신 인스턴스 유형 비교
```javascript
const detailedSpecs = {
    't3.micro': {
        vCPU: 2,
        memory: '1GB',
        network: 'Up to 5 Gbps',
        storage: 'EBS only',
        architecture: 'x86_64',
        generation: '3rd'
    },
    'c5.large': {
        vCPU: 2,
        memory: '4GB',
        network: 'Up to 10 Gbps',
        storage: 'EBS only',
        architecture: 'x86_64',
        generation: '5th'
    },
    'r5.large': {
        vCPU: 2,
        memory: '16GB',
        network: 'Up to 10 Gbps',
        storage: 'EBS only',
        architecture: 'x86_64',
        generation: '5th'
    },
    'g4dn.xlarge': {
        vCPU: 4,
        memory: '16GB',
        network: 'Up to 25 Gbps',
        storage: '1x 125 NVMe SSD',
        architecture: 'x86_64',
        generation: '4th',
        gpu: '1x NVIDIA T4'
    }
};
```

### 결론
AWS EC2 인스턴스 유형은 다양한 워크로드에 최적화된 선택지를 제공합니다.
애플리케이션의 특성과 요구사항을 정확히 분석하여 적절한 인스턴스 유형을 선택하는 것이 중요합니다.
비용 최적화를 위해 Reserved Instances와 Spot Instances를 적절히 활용하고,
CloudWatch를 통한 지속적인 모니터링으로 성능을 최적화할 수 있습니다.
보안 설정과 함께 안정적이고 효율적인 클라우드 인프라를 구축할 수 있습니다.










