---
title: AWS EC2 T 시리즈 (Burstable Performance Instances)
tags: [aws, compute, ec2, t-series, burstable, cloud-computing]
updated: 2025-08-10
---

# AWS EC2 T 시리즈 (Burstable Performance Instances)

## 배경

AWS EC2 T 시리즈는 버스트 성능을 지원하는 범용 인스턴스로, 일반적인 상태에서는 적절한 성능을 유지하다가 필요할 때 순간적으로 CPU 성능을 높일 수 있는 저비용, 고효율 인스턴스입니다. 이는 간헐적으로 CPU를 사용하는 애플리케이션에 최적화된 설계로, 비용 효율성을 극대화할 수 있습니다.

### T 시리즈의 필요성
- **비용 최적화**: 지속적인 고성능이 필요하지 않은 워크로드에 적합
- **유연한 성능**: 필요에 따라 성능을 동적으로 조절 가능
- **다양한 워크로드 지원**: 웹 서버, 개발 환경, 소규모 애플리케이션에 최적

### T 시리즈의 발전 과정
- **T2**: 초기 버스트 가능 인스턴스, 기본적인 크레딧 시스템
- **T3**: 개선된 크레딧 시스템, 더 나은 성능과 비용 효율성
- **T4g**: ARM 기반으로 비용 절감, 환경 친화적

## 핵심

### T 시리즈의 특징

#### 버스트 가능한 성능 (Burstable Performance)
- 기본적으로 저전력 CPU 성능을 유지
- CPU 크레딧을 이용하여 순간적으로 성능을 높일 수 있음
- 필요할 때만 고성능을 사용하여 비용 절약

#### 비용 효율적 (Cost-Effective)
- 일정 수준 이하의 CPU 사용량에서는 매우 저렴한 비용으로 운영 가능
- 웹 서버, 개발 환경 등 간헐적으로 CPU를 사용하는 애플리케이션에 적합

#### 다양한 옵션 제공
- **T4g**: ARM 기반, 비용 절감형
- **T3, T3a**: x86 기반, 표준 성능
- **T2**: 이전 세대, 여전히 사용 가능

### CPU 크레딧 시스템

T 시리즈는 CPU 크레딧 시스템을 통해 버스트 성능을 제공합니다:

#### 크레딧 적립
- CPU를 적게 사용하면 크레딧이 쌓임
- 기본 성능 수준 이하로 사용할 때마다 크레딧 적립

#### 크레딧 소비
- CPU를 많이 사용할 때 크레딧을 소비하여 성능 증가
- 크레딧이 소진되면 기본 성능 수준으로 제한

#### T3 Unlimited 모드
- 추가 비용을 내고 크레딧 없이도 성능을 유지 가능
- 예측 불가능한 트래픽에 적합

### T 시리즈 인스턴스 유형

| 인스턴스 유형 | CPU | 메모리 (RAM) | 특징 |
|--------------|-----|-------------|-----------------|
| **T4g** | ARM 기반 | 0.5~32GB | 저비용, 고성능 |
| **T3** | x86 기반 | 0.5~32GB | 표준 성능, 대부분의 워크로드에 적합 |
| **T3a** | AMD 기반 | 0.5~32GB | T3보다 저렴, 약간 낮은 성능 |
| **T2** | x86 기반 | 0.5~32GB | 이전 세대, 여전히 사용 가능 |

## 예시

### T3.micro 인스턴스 생성 예시

```javascript
const AWS = require('aws-sdk');

// AWS EC2 클라이언트 생성
const ec2 = new AWS.EC2({
    region: 'ap-northeast-2',
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
});

// T3.micro 인스턴스 생성
async function createT3MicroInstance() {
    const params = {
        ImageId: 'ami-12345678',  // AMI ID (운영체제 이미지)
        InstanceType: 't3.micro',  // T3 인스턴스 선택
        MinCount: 1,
        MaxCount: 1,
        KeyName: 'my-key-pair',  // SSH 접속을 위한 키 페어
        SecurityGroupIds: ['sg-12345678'],  // 보안 그룹 ID
        SubnetId: 'subnet-12345678',  // 서브넷 ID
        TagSpecifications: [{
            ResourceType: 'instance',
            Tags: [{
                Key: 'Name',
                Value: 'T3-Micro-WebServer'
            }]
        }]
    };

    try {
        const result = await ec2.runInstances(params).promise();
        const instanceId = result.Instances[0].InstanceId;
        
        console.log(`새로운 T3.micro EC2 인스턴스가 생성되었습니다: ${instanceId}`);
        
        // T3 인스턴스 Unlimited 모드 활성화
        await ec2.modifyInstanceCreditSpecification({
            InstanceCreditSpecifications: [{
                InstanceId: instanceId,
                CpuCredits: 'unlimited'
            }]
        }).promise();
        
        console.log('Unlimited 모드가 활성화되었습니다.');
        
        return instanceId;
    } catch (error) {
        console.error('인스턴스 생성 오류:', error);
        throw error;
    }
}

// 사용 예시
createT3MicroInstance();
```

### CPU 크레딧 모니터링

```javascript
const AWS = require('aws-sdk');

// CloudWatch 클라이언트 생성
const cloudwatch = new AWS.CloudWatch({
    region: 'ap-northeast-2'
});

class T3InstanceMonitor {
    constructor(instanceId) {
        this.instanceId = instanceId;
        this.metrics = {
            cpuCredits: [],
            cpuUtilization: []
        };
    }

    // CPU 크레딧 사용량 모니터링
    async getCPUCredits() {
        const params = {
            Namespace: 'AWS/EC2',
            MetricName: 'CPUCreditUsage',
            Dimensions: [{
                Name: 'InstanceId',
                Value: this.instanceId
            }],
            StartTime: new Date(Date.now() - 3600000), // 1시간 전
            EndTime: new Date(),
            Period: 300, // 5분 간격
            Statistics: ['Average']
        };

        try {
            const result = await cloudwatch.getMetricStatistics(params).promise();
            return result.Datapoints;
        } catch (error) {
            console.error('CPU 크레딧 모니터링 오류:', error);
            return [];
        }
    }

    // CPU 크레딧 잔액 모니터링
    async getCPUCreditBalance() {
        const params = {
            Namespace: 'AWS/EC2',
            MetricName: 'CPUCreditBalance',
            Dimensions: [{
                Name: 'InstanceId',
                Value: this.instanceId
            }],
            StartTime: new Date(Date.now() - 3600000),
            EndTime: new Date(),
            Period: 300,
            Statistics: ['Average']
        };

        try {
            const result = await cloudwatch.getMetricStatistics(params).promise();
            return result.Datapoints;
        } catch (error) {
            console.error('CPU 크레딧 잔액 모니터링 오류:', error);
            return [];
        }
    }

    // CPU 사용률 모니터링
    async getCPUUtilization() {
        const params = {
            Namespace: 'AWS/EC2',
            MetricName: 'CPUUtilization',
            Dimensions: [{
                Name: 'InstanceId',
                Value: this.instanceId
            }],
            StartTime: new Date(Date.now() - 3600000),
            EndTime: new Date(),
            Period: 300,
            Statistics: ['Average']
        };

        try {
            const result = await cloudwatch.getMetricStatistics(params).promise();
            return result.Datapoints;
        } catch (error) {
            console.error('CPU 사용률 모니터링 오류:', error);
            return [];
        }
    }

    // 종합 모니터링 리포트
    async generateReport() {
        const [credits, balance, utilization] = await Promise.all([
            this.getCPUCredits(),
            this.getCPUCreditBalance(),
            this.getCPUUtilization()
        ]);

        console.log('=== T3 인스턴스 모니터링 리포트 ===');
        console.log(`인스턴스 ID: ${this.instanceId}`);
        console.log(`모니터링 기간: ${new Date(Date.now() - 3600000).toISOString()} ~ ${new Date().toISOString()}`);
        
        if (credits.length > 0) {
            const avgCredits = credits.reduce((sum, point) => sum + point.Average, 0) / credits.length;
            console.log(`평균 CPU 크레딧 사용량: ${avgCredits.toFixed(2)}`);
        }
        
        if (balance.length > 0) {
            const avgBalance = balance.reduce((sum, point) => sum + point.Average, 0) / balance.length;
            console.log(`평균 CPU 크레딧 잔액: ${avgBalance.toFixed(2)}`);
        }
        
        if (utilization.length > 0) {
            const avgUtilization = utilization.reduce((sum, point) => sum + point.Average, 0) / utilization.length;
            console.log(`평균 CPU 사용률: ${avgUtilization.toFixed(2)}%`);
        }
    }
}

// 사용 예시
const monitor = new T3InstanceMonitor('i-1234567890abcdef0');
monitor.generateReport();
```

### T 시리즈 워크로드 최적화

```javascript
class T3WorkloadOptimizer {
    constructor() {
        this.workloads = {
            webServer: {
                name: '웹 서버',
                recommendedType: 't3.micro',
                cpuBaseline: 10, // % 기준
                burstThreshold: 80,
                description: '간헐적인 트래픽을 처리하는 웹 서버'
            },
            development: {
                name: '개발 환경',
                recommendedType: 't3.small',
                cpuBaseline: 20,
                burstThreshold: 90,
                description: '개발 및 테스트 환경'
            },
            database: {
                name: '소규모 데이터베이스',
                recommendedType: 't3.medium',
                cpuBaseline: 30,
                burstThreshold: 85,
                description: '소규모 데이터베이스 서버'
            }
        };
    }

    // 워크로드에 따른 인스턴스 타입 추천
    recommendInstanceType(workloadType, expectedTraffic) {
        const workload = this.workloads[workloadType];
        
        if (!workload) {
            throw new Error(`알 수 없는 워크로드 타입: ${workloadType}`);
        }

        let instanceType = workload.recommendedType;
        
        // 트래픽에 따른 인스턴스 타입 조정
        if (expectedTraffic === 'high') {
            instanceType = instanceType.replace('micro', 'small')
                                     .replace('small', 'medium');
        } else if (expectedTraffic === 'very-high') {
            instanceType = instanceType.replace('micro', 'medium')
                                     .replace('small', 'medium')
                                     .replace('medium', 'large');
        }

        return {
            instanceType: instanceType,
            workload: workload,
            recommendation: `이 워크로드는 ${instanceType} 인스턴스에 적합합니다.`,
            considerations: [
                'CPU 크레딧을 모니터링하여 적절한 크레딧 잔액 유지',
                '예측 불가능한 트래픽의 경우 Unlimited 모드 고려',
                '정기적인 성능 모니터링으로 인스턴스 타입 조정'
            ]
        };
    }

    // 비용 최적화 가이드
    getCostOptimizationGuide(instanceType) {
        const guides = {
            't3.micro': {
                monthlyCost: '약 $8-12',
                optimizationTips: [
                    'CPU 크레딧 사용량을 모니터링하여 과도한 사용 방지',
                    '불필요한 프로세스 제거로 기본 CPU 사용률 낮추기',
                    '정적 콘텐츠는 CDN 활용'
                ]
            },
            't3.small': {
                monthlyCost: '약 $16-24',
                optimizationTips: [
                    '애플리케이션 최적화로 CPU 사용률 개선',
                    '캐싱 전략으로 반복 작업 최소화',
                    '로드 밸런서를 통한 트래픽 분산'
                ]
            },
            't3.medium': {
                monthlyCost: '약 $32-48',
                optimizationTips: [
                    '데이터베이스 쿼리 최적화',
                    '메모리 사용량 모니터링',
                    '스케일링 정책 수립'
                ]
            }
        };

        return guides[instanceType] || {
            monthlyCost: '가격 정보 확인 필요',
            optimizationTips: ['일반적인 T3 인스턴스 최적화 가이드 적용']
        };
    }
}

// 사용 예시
const optimizer = new T3WorkloadOptimizer();

// 웹 서버 워크로드 추천
const webServerRecommendation = optimizer.recommendInstanceType('webServer', 'medium');
console.log('웹 서버 추천:', webServerRecommendation);

// 비용 최적화 가이드
const costGuide = optimizer.getCostOptimizationGuide('t3.micro');
console.log('비용 최적화 가이드:', costGuide);
```

## 운영 팁

### 성능 최적화

#### CPU 크레딧 관리
```javascript
class CPUCreditManager {
    constructor(instanceId) {
        this.instanceId = instanceId;
        this.cloudwatch = new AWS.CloudWatch();
        this.alertThreshold = 50; // 크레딧 잔액 경고 임계값
    }

    // 크레딧 잔액 알림 설정
    async setupCreditAlert() {
        const params = {
            AlarmName: `${this.instanceId}-cpu-credit-alert`,
            ComparisonOperator: 'LessThanThreshold',
            EvaluationPeriods: 2,
            MetricName: 'CPUCreditBalance',
            Namespace: 'AWS/EC2',
            Period: 300,
            Statistic: 'Average',
            Threshold: this.alertThreshold,
            ActionsEnabled: true,
            AlarmDescription: 'CPU 크레딧 잔액이 낮을 때 알림',
            Dimensions: [{
                Name: 'InstanceId',
                Value: this.instanceId
            }]
        };

        try {
            await this.cloudwatch.putMetricAlarm(params).promise();
            console.log('CPU 크레딧 알림이 설정되었습니다.');
        } catch (error) {
            console.error('알림 설정 오류:', error);
        }
    }

    // 크레딧 사용 패턴 분석
    async analyzeCreditPattern() {
        const endTime = new Date();
        const startTime = new Date(Date.now() - 24 * 60 * 60 * 1000); // 24시간

        const params = {
            Namespace: 'AWS/EC2',
            MetricName: 'CPUCreditUsage',
            Dimensions: [{
                Name: 'InstanceId',
                Value: this.instanceId
            }],
            StartTime: startTime,
            EndTime: endTime,
            Period: 3600, // 1시간 간격
            Statistics: ['Average', 'Maximum']
        };

        try {
            const result = await this.cloudwatch.getMetricStatistics(params).promise();
            
            const analysis = {
                totalCredits: result.Datapoints.reduce((sum, point) => sum + point.Average, 0),
                maxCredits: Math.max(...result.Datapoints.map(point => point.Maximum)),
                avgCredits: result.Datapoints.reduce((sum, point) => sum + point.Average, 0) / result.Datapoints.length,
                recommendations: []
            };

            // 권장사항 생성
            if (analysis.avgCredits > 20) {
                analysis.recommendations.push('CPU 사용량이 높습니다. 인스턴스 타입 업그레이드 고려');
            }
            
            if (analysis.maxCredits > 50) {
                analysis.recommendations.push('크레딧 사용량이 급증합니다. 애플리케이션 최적화 필요');
            }

            return analysis;
        } catch (error) {
            console.error('크레딧 패턴 분석 오류:', error);
            return null;
        }
    }
}
```

### 비용 최적화

#### T3 인스턴스 비용 계산기
```javascript
class T3CostCalculator {
    constructor() {
        this.pricing = {
            't3.micro': {
                hourly: 0.0104,
                monthly: 7.488,
                vcpu: 2,
                memory: 1
            },
            't3.small': {
                hourly: 0.0208,
                monthly: 14.976,
                vcpu: 2,
                memory: 2
            },
            't3.medium': {
                hourly: 0.0416,
                monthly: 29.952,
                vcpu: 2,
                memory: 4
            },
            't3.large': {
                hourly: 0.0832,
                monthly: 59.904,
                vcpu: 2,
                memory: 8
            }
        };
    }

    // 월 비용 계산
    calculateMonthlyCost(instanceType, hoursPerDay = 24, daysPerMonth = 30) {
        const instance = this.pricing[instanceType];
        
        if (!instance) {
            throw new Error(`지원하지 않는 인스턴스 타입: ${instanceType}`);
        }

        const monthlyHours = hoursPerDay * daysPerMonth;
        const baseCost = instance.hourly * monthlyHours;
        
        return {
            instanceType: instanceType,
            monthlyHours: monthlyHours,
            baseCost: baseCost,
            estimatedCost: baseCost * 1.1, // 10% 버퍼 포함
            specifications: {
                vcpu: instance.vcpu,
                memory: instance.memory
            }
        };
    }

    // 비용 비교
    compareCosts(instanceTypes, usage = {}) {
        const comparison = instanceTypes.map(type => {
            const cost = this.calculateMonthlyCost(type, usage.hoursPerDay, usage.daysPerMonth);
            return {
                ...cost,
                costPerVcpu: cost.baseCost / this.pricing[type].vcpu,
                costPerGB: cost.baseCost / this.pricing[type].memory
            };
        });

        // 비용 효율성 순으로 정렬
        comparison.sort((a, b) => a.costPerVcpu - b.costPerVcpu);

        return comparison;
    }

    // 워크로드별 비용 추천
    getWorkloadRecommendation(workload) {
        const recommendations = {
            'low-traffic-web': {
                recommended: 't3.micro',
                reason: '낮은 트래픽 웹사이트에 적합한 최저 비용 옵션',
                estimatedCost: this.calculateMonthlyCost('t3.micro').baseCost
            },
            'development': {
                recommended: 't3.small',
                reason: '개발 환경에 적합한 균형잡힌 성능과 비용',
                estimatedCost: this.calculateMonthlyCost('t3.small').baseCost
            },
            'small-database': {
                recommended: 't3.medium',
                reason: '소규모 데이터베이스에 적합한 메모리와 성능',
                estimatedCost: this.calculateMonthlyCost('t3.medium').baseCost
            }
        };

        return recommendations[workload] || {
            recommended: 't3.small',
            reason: '일반적인 워크로드에 적합한 기본 옵션',
            estimatedCost: this.calculateMonthlyCost('t3.small').baseCost
        };
    }
}

// 사용 예시
const calculator = new T3CostCalculator();

// 월 비용 계산
const monthlyCost = calculator.calculateMonthlyCost('t3.micro');
console.log('월 비용:', monthlyCost);

// 비용 비교
const comparison = calculator.compareCosts(['t3.micro', 't3.small', 't3.medium']);
console.log('비용 비교:', comparison);

// 워크로드 추천
const recommendation = calculator.getWorkloadRecommendation('low-traffic-web');
console.log('워크로드 추천:', recommendation);
```

## 참고

### T 시리즈 vs 다른 인스턴스 타입

#### 성능 비교
```javascript
const instanceComparison = {
    'T 시리즈 (Burstable)': {
        특징: '버스트 가능한 성능, 비용 효율적',
        적합한_워크로드: ['웹 서버', '개발 환경', '소규모 애플리케이션'],
        장점: ['저비용', '유연한 성능', '간헐적 워크로드에 최적'],
        단점: ['지속적 고성능 부족', '크레딧 관리 필요']
    },
    'M 시리즈 (General Purpose)': {
        특징: '균형잡힌 성능과 비용',
        적합한_워크로드: ['애플리케이션 서버', '중간 규모 데이터베이스'],
        장점: ['안정적인 성능', '다양한 워크로드 지원'],
        단점: ['T 시리즈보다 비용 높음']
    },
    'C 시리즈 (Compute Optimized)': {
        특징: '고성능 컴퓨팅',
        적합한_워크로드: ['고성능 웹 서버', '배치 처리', '게임 서버'],
        장점: ['높은 CPU 성능', '일관된 성능'],
        단점: ['높은 비용', '메모리 제한']
    }
};
```

### T 시리즈 모니터링 도구

#### CloudWatch 대시보드 설정
```javascript
class T3Dashboard {
    constructor(instanceId) {
        this.instanceId = instanceId;
        this.cloudwatch = new AWS.CloudWatch();
    }

    // 대시보드 생성
    async createDashboard() {
        const dashboardBody = {
            widgets: [
                {
                    type: 'metric',
                    x: 0,
                    y: 0,
                    width: 12,
                    height: 6,
                    properties: {
                        metrics: [
                            ['AWS/EC2', 'CPUCreditUsage', 'InstanceId', this.instanceId],
                            ['.', 'CPUCreditBalance', '.', '.'],
                            ['.', 'CPUUtilization', '.', '.']
                        ],
                        view: 'timeSeries',
                        stacked: false,
                        region: 'ap-northeast-2',
                        title: 'T3 인스턴스 성능 메트릭'
                    }
                }
            ]
        };

        const params = {
            DashboardName: `T3-${this.instanceId}-Dashboard`,
            DashboardBody: JSON.stringify(dashboardBody)
        };

        try {
            await this.cloudwatch.putDashboard(params).promise();
            console.log('T3 인스턴스 대시보드가 생성되었습니다.');
        } catch (error) {
            console.error('대시보드 생성 오류:', error);
        }
    }
}
```

### 결론
AWS EC2 T 시리즈는 비용 효율적인 버스트 가능 인스턴스로, 간헐적인 워크로드에 최적화되어 있습니다.
CPU 크레딧 시스템을 통해 필요할 때만 고성능을 사용하여 비용을 절약할 수 있습니다.
적절한 모니터링과 크레딧 관리를 통해 안정적인 성능을 유지할 수 있습니다.
워크로드 특성에 따라 T3, T3a, T4g 중 적절한 옵션을 선택하는 것이 중요합니다.
Unlimited 모드를 활용하여 예측 불가능한 트래픽에도 대응할 수 있습니다.
