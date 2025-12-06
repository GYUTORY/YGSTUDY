---
title: AWS CloudWatch
tags: [aws, monitoring-and-management, cloudwatch]
updated: 2025-12-07
---

# AWS CloudWatch

## 개요

CloudWatch는 AWS 리소스와 애플리케이션을 모니터링하는 서비스다.

**주요 기능:**
- 데이터 수집: EC2, RDS, Lambda 등 AWS 리소스의 메트릭과 로그 자동 수집
- 데이터 분석: 수집된 데이터를 분석해 트렌드와 패턴 파악
- 시각화: 대시보드를 통해 메트릭 표시
- 자동화: 특정 조건에 따라 자동 대응 (알람, 스케일링 등)

**사용하는 경우:**
- 리소스 상태 모니터링
- 애플리케이션 성능 추적
- 문제 발생 전 감지
- 자동 스케일링
- 비용 최적화

**실무 팁:**
수십, 수백 개의 리소스를 수동으로 확인하는 것은 불가능하다. CloudWatch로 실시간 모니터링하고 문제 발생 전에 대응한다.

## 아키텍처

CloudWatch는 AWS 인프라와 애플리케이션 모니터링을 위한 통합 아키텍처를 제공한다.

```mermaid
graph TB
    subgraph "AWS 리소스"
        EC2[EC2 인스턴스]
        RDS[RDS 데이터베이스]
        LB[로드 밸런서]
        LAMBDA[Lambda 함수]
        APP[애플리케이션]
    end
    
    subgraph "CloudWatch 핵심 구성요소"
        METRIC[메트릭 Metrics]
        LOG[로그 Logs]
        ALARM[알람 Alarms]
        DASH[D시보드 Dashboard]
        EVENT[이벤트 Events]
    end
    
    subgraph "분석 및 시각화"
        INSIGHT[Insights]
        ANOMALY[이상 탐지]
        MAP[서비스 맵]
    end
    
    subgraph "자동화 및 대응"
        SNS[SNS 알림]
        ASG[Auto Scaling]
        LAMBDA_ACTION[Lambda 액션]
    end
    
    EC2 --> METRIC
    RDS --> METRIC
    LB --> METRIC
    LAMBDA --> METRIC
    APP --> METRIC
    
    EC2 --> LOG
    APP --> LOG
    LAMBDA --> LOG
    
    METRIC --> ALARM
    LOG --> ALARM
    
    METRIC --> DASH
    LOG --> DASH
    ALARM --> DASH
    
    METRIC --> INSIGHT
    LOG --> INSIGHT
    
    METRIC --> ANOMALY
    
    ALARM --> SNS
    ALARM --> ASG
    ALARM --> LAMBDA_ACTION
    
    EVENT --> LAMBDA_ACTION
    
    INSIGHT --> MAP
    
    style METRIC fill:#4fc3f7
    style LOG fill:#66bb6a
    style ALARM fill:#ff9800
    style DASH fill:#9c27b0
    style EVENT fill:#ef5350,color:#fff
```

### 데이터 흐름

CloudWatch는 데이터 수집부터 자동 대응까지의 전체 흐름을 관리한다.

```mermaid
sequenceDiagram
    participant APP as 애플리케이션/리소스
    participant CW as CloudWatch
    participant ALARM as 알람
    participant DASH as 대시보드
    participant ACTION as 자동화 액션
    
    Note over APP: 데이터 생성
    APP->>CW: 메트릭 수집
    APP->>CW: 로그 전송
    
    Note over CW: 데이터 처리
    CW->>CW: 메트릭 집계
    CW->>CW: 로그 인덱싱
    
    Note over CW,ALARM: 알람 평가
    CW->>ALARM: 메트릭/로그 평가
    ALARM->>ALARM: 임계값 체크
    
    alt 임계값 초과
        ALARM->>ACTION: 알람 트리거
        ACTION->>ACTION: 자동 대응 실행
        ACTION->>APP: 스케일링/복구
    end
    
    Note over CW,DASH: 시각화
    CW->>DASH: 메트릭/로그 표시
    DASH->>DASH: 실시간 모니터링
```

### 구성 요소 간 상호작용

메트릭, 로그, 알람은 서로 연관되어 작동한다.

**메트릭 → 알람:**
- 메트릭이 수집되면 알람이 주기적으로 평가한다
- 임계값을 초과하면 알람 상태가 변경되고 액션이 트리거된다
- 여러 메트릭을 조합해 복합 알람을 생성할 수 있다

**로그 → 알람:**
- 로그 패턴을 기반으로 메트릭 필터를 생성한다
- 메트릭 필터가 특정 패턴을 감지하면 알람이 트리거된다
- 예: 에러 로그가 1분에 10개 이상 발생하면 알람 발생

**대시보드 통합:**
- 메트릭, 로그, 알람 상태를 하나의 대시보드에 통합해 표시한다
- 실시간 모니터링과 히스토리 분석을 동시에 제공한다

## 핵심 구성 요소

### 메트릭 (Metrics)

메트릭은 시간에 따른 데이터 포인트의 집합이다. 시스템의 건강 상태를 수치로 표현한다.

**메트릭 구조:**
- 네임스페이스: 메트릭이 속한 카테고리 (예: AWS/EC2, AWS/RDS)
- 메트릭 이름: 측정 지표 (예: CPUUtilization, NetworkIn)
- 차원: 메트릭을 구분하는 키-값 쌍 (예: InstanceId, DatabaseName)
- 타임스탬프: 데이터 수집 시간
- 값: 실제 측정 수치

**기본 메트릭:**
AWS 서비스가 자동으로 제공하는 메트릭이다. EC2의 CPU 사용률, RDS의 연결 수 등이 있다.

**사용자 정의 메트릭:**
애플리케이션의 비즈니스 로직에 특화된 메트릭을 생성할 수 있다.

**예시:**
- 웹 애플리케이션의 응답 시간
- 데이터베이스 쿼리 성능
- 특정 기능의 사용 빈도
- 주문 처리 시간
- 결제 성공률

**실무 팁:**
사용자 정의 메트릭은 비용이 발생한다. 중요한 메트릭만 선별해 수집한다.

### 로그 (Logs)

CloudWatch Logs는 애플리케이션과 시스템의 로그 데이터를 중앙에서 수집, 저장, 분석한다.

**로그 구조:**
- 로그 그룹: 관련된 로그 스트림들을 논리적으로 그룹화한 단위
- 로그 스트림: 실제 로그 이벤트들이 순차적으로 기록되는 단위

**예시:**
```
로그 그룹: /aws/lambda/my-function
  └── 로그 스트림: 2025/12/06/[$LATEST]abc123
  └── 로그 스트림: 2025/12/06/[$LATEST]def456
```

**로그 보존 정책:**
로그 데이터는 무한정 저장되지 않는다. 비용 최적화를 위해 보존 기간을 설정한다.

**보존 기간 설정:**
- 중요하지 않은 로그: 7일
- 일반 로그: 30일
- 중요한 로그: 90일 이상 또는 S3로 아카이브

**실무 팁:**
중요한 로그는 S3나 Glacier로 아카이브해 장기 보관한다. CloudWatch Logs는 비용이 높으니 보존 기간을 적절히 설정해야 한다.

### 알람 (Alarms)

알람은 메트릭이나 로그 패턴을 기반으로 특정 조건이 충족될 때 자동으로 트리거된다.

**알람 평가 방식:**
- 임계값 기반: 특정 수치를 초과하거나 미달할 때
- 이상 탐지: 기계 학습을 통한 정상 패턴에서의 벗어남 감지
- 로그 패턴: 특정 로그 패턴이나 에러 메시지 감지

**알람 상태:**
- OK: 정상 상태
- ALARM: 임계값을 초과한 상태
- INSUFFICIENT_DATA: 데이터가 부족한 상태

**알람 액션:**
- SNS 알림 발송
- Auto Scaling 트리거
- Lambda 함수 실행
- EC2 인스턴스 재시작

**실무 팁:**
알람이 너무 많으면 알람 피로도가 발생한다. 조치 가능한 알람만 설정하고, 의미 있는 임계값을 사용해야 한다.

### 대시보드 (Dashboard)

대시보드는 여러 메트릭과 로그를 하나의 화면에 시각적으로 표시한다.

**대시보드 활용:**
- 운영 대시보드: 실시간 시스템 상태 모니터링
- 비즈니스 대시보드: 비즈니스 지표 추적
- 보안 대시보드: 보안 관련 이벤트 모니터링

**위젯 종류:**
- 메트릭 그래프
- 로그 인사이트
- 숫자 표시
- 알람 상태

**실무 팁:**
역할별로 다른 대시보드를 만든다. 개발자는 애플리케이션 메트릭, 운영자는 인프라 메트릭에 집중한다.

### 이벤트 (Events)

CloudWatch Events(현재 Amazon EventBridge로 통합)는 AWS 서비스 이벤트를 실시간으로 감지하고 자동화된 워크플로우를 실행한다.

**이벤트 소스:**
- AWS 서비스 이벤트 (EC2 인스턴스 시작/중지, S3 객체 생성 등)
- 사용자 정의 애플리케이션 이벤트
- 스케줄 기반 이벤트 (Cron 표현식)

**사용 예시:**
- EC2 인스턴스가 시작되면 Lambda 함수 실행
- S3에 파일이 업로드되면 처리 워크플로우 시작
- 매일 정해진 시간에 백업 작업 실행

## 데이터 수집 및 처리

CloudWatch는 다양한 소스로부터 데이터를 수집하고 처리한다.

```mermaid
flowchart TD
    START([데이터 소스]) --> COLLECT{데이터 수집}
    
    COLLECT -->|시스템 메트릭| METRIC[메트릭 수집]
    COLLECT -->|애플리케이션 로그| LOG[로그 수집]
    COLLECT -->|사용자 정의| CUSTOM[커스텀 메트릭]
    
    METRIC --> STORE1[메트릭 저장소]
    LOG --> STORE2[로그 저장소]
    CUSTOM --> STORE1
    
    STORE1 --> PROCESS1{메트릭 처리}
    STORE2 --> PROCESS2{로그 처리}
    
    PROCESS1 -->|집계| AGG[통계 집계<br/>평균/합계/최대/최소]
    PROCESS2 -->|파싱| PARSE[로그 파싱<br/>필드 추출]
    
    AGG --> EVAL1[알람 평가]
    PARSE --> EVAL2[메트릭 필터 평가]
    
    EVAL1 -->|임계값 초과| TRIGGER[알람 트리거]
    EVAL2 -->|패턴 매칭| TRIGGER
    
    TRIGGER --> ACTION{자동화 액션}
    ACTION -->|스케일링| SCALE[Auto Scaling]
    ACTION -->|알림| NOTIFY[SNS 알림]
    ACTION -->|실행| LAMBDA[Lambda 함수]
    
    STORE1 --> VISUAL[대시보드 시각화]
    STORE2 --> VISUAL
    AGG --> VISUAL
    
    VISUAL --> END([모니터링 완료])
    
    style METRIC fill:#4fc3f7
    style LOG fill:#66bb6a
    style TRIGGER fill:#ff9800
    style ACTION fill:#ef5350,color:#fff
    style VISUAL fill:#9c27b0
```

### 데이터 수집

**자동 수집:**
- AWS 서비스(EC2, RDS, Lambda 등)는 자동으로 메트릭을 CloudWatch에 전송한다
- 별도 설정 없이 기본 메트릭을 즉시 사용할 수 있다
- 5분 간격으로 기본 메트릭이 수집된다
- 상세 모니터링을 활성화하면 1분 간격으로 수집된다

**애플리케이션 통합:**
- CloudWatch Agent를 설치해 커스텀 메트릭과 로그를 수집한다
- AWS SDK를 통해 애플리케이션에서 직접 메트릭을 전송한다
- 구조화된 로그 형식(JSON)을 사용하면 더 효율적인 분석이 가능하다

**수집 주기 최적화:**
- 비용과 성능의 균형을 고려해 적절한 수집 주기를 설정한다
- 중요한 메트릭은 1분 간격, 일반 메트릭은 5분 간격으로 수집한다
- 배치 전송을 통해 API 호출 비용을 최적화한다

**실무 팁:**
상세 모니터링은 비용이 발생한다. 필요한 인스턴스만 활성화한다.

## 실제 운영 시나리오

### 웹 애플리케이션 모니터링

전자상거래 웹사이트를 운영하는 경우, 시스템 레벨과 애플리케이션 레벨의 모니터링을 모두 고려해야 한다.

**모니터링해야 할 메트릭:**

**시스템 메트릭:**
- EC2 인스턴스의 CPU, 메모리, 디스크 사용률
- 로드 밸런서의 응답 시간과 에러율
- 데이터베이스의 연결 수와 쿼리 성능

**애플리케이션 메트릭:**
- 페이지 로딩 시간
- 주문 처리 시간
- 결제 성공률
- 동시 사용자 수

**로그 분석:**
- 웹 서버 액세스 로그에서 느린 요청 패턴 분석
- 애플리케이션 로그에서 에러 패턴 추적
- 보안 로그에서 의심스러운 활동 감지

**알람 설계:**

**Critical 알람:**
- 서비스 중단, 데이터 손실 위험
- 즉시 대응 필요
- 예: CPU 사용률 95% 초과, 에러율 10% 초과

**Warning 알람:**
- 성능 저하, 리소스 부족
- 모니터링 강화
- 예: CPU 사용률 80% 초과, 응답 시간 2초 초과

**Info 알람:**
- 트렌드 변화, 비정상 패턴
- 분석 필요
- 예: 트래픽 급증, 비정상적인 사용 패턴

**대시보드 구성:**
- 실시간 운영 대시보드: 현재 상태를 한눈에 파악
- 성능 분석 대시보드: 트렌드 분석 및 병목 지점 식별
- 비즈니스 대시보드: 사용자 활동, 비즈니스 지표 추적

**자동화 대응:**
- 알람 발생 시 자동 스케일링 트리거
- 에러율 증가 시 자동 롤백 또는 트래픽 제한
- 리소스 부족 시 알림 및 자동 확장

### 마이크로서비스 아키텍처 모니터링

마이크로서비스 환경에서는 각 서비스의 독립적인 모니터링과 전체 시스템의 통합 모니터링이 모두 필요하다.

**서비스별 모니터링:**
- 각 마이크로서비스는 독립적인 네임스페이스를 사용해 메트릭을 분리한다
- 서비스 간 통신 지연 시간을 측정해 병목 지점을 식별한다
- 의존성 서비스의 상태를 모니터링해 장애 전파를 방지한다

**분산 추적 통합:**
- CloudWatch와 X-Ray를 통합해 요청의 전체 경로를 추적한다
- 서비스 간 호출 체인을 시각화해 의존성을 파악한다
- 느린 요청의 정확한 위치를 식별해 성능을 개선한다

**장애 대응:**
- Circuit Breaker 패턴을 구현해 장애 서비스로의 요청을 차단한다
- Fallback 메커니즘을 설정해 서비스 장애 시 대체 동작을 수행한다
- 장애 복구 후 자동으로 정상 상태로 복귀하는 메커니즘을 구축한다

**실무 팁:**
각 서비스마다 별도의 로그 그룹과 메트릭 네임스페이스를 사용하면 관리가 쉬워진다.

### 비용 최적화 모니터링

CloudWatch를 통해 리소스 사용 패턴을 분석해 비용을 최적화한다.

**리소스 사용률 분석:**
- 사용률이 낮은 EC2 인스턴스 식별
- 스토리지 사용 패턴 분석
- 네트워크 트래픽 패턴 파악

**자동 스케일링 연동:**
- CPU 사용률에 따른 자동 인스턴스 추가/제거
- 트래픽 패턴에 따른 로드 밸런서 설정 조정

**CloudWatch 비용 최적화:**

CloudWatch 자체의 비용도 최적화해야 한다. 불필요한 메트릭 수집과 로그 보관은 비용을 증가시킨다.

**메트릭 최적화:**
- 비즈니스에 중요한 메트릭만 선별해 수집
- 사용하지 않는 커스텀 메트릭은 정기적으로 정리
- 메트릭 해상도를 적절히 조정 (1분 vs 5분)

**로그 최적화:**
- 로그 보존 기간을 비즈니스 요구사항에 맞게 설정
- 중요한 로그는 S3로 아카이브하고, 일반 로그는 짧은 보존 기간 설정
- 로그 필터링을 통해 불필요한 로그 수집 방지

**알람 최적화:**
- 중복되는 알람을 통합해 알람 피로도를 방지한다
- 알람 평가 주기를 적절히 설정해 비용을 절감한다
- 알람 상태 변경 시에만 알림을 발송하도록 설정한다

**실무 팁:**
CloudWatch Logs는 비용이 높다. 보존 기간을 짧게 설정하고, 중요한 로그는 S3로 아카이브한다.

## 고급 기능

### 이상 탐지 (Anomaly Detection)

기계 학습 알고리즘을 사용해 메트릭의 정상 패턴을 학습하고, 이에서 벗어나는 이상 상황을 자동으로 감지한다.

**활용 사례:**
- 고정된 임계값으로는 감지하기 어려운 점진적인 성능 저하
- 예상치 못한 트래픽 증가
- 비정상적인 리소스 사용 패턴

**장점:**
- 정상 패턴을 자동으로 학습해 수동 임계값 설정 불필요
- 조기 이상 상황 감지 가능

**실무 팁:**
이상 탐지는 추가 비용이 발생한다. 중요한 메트릭에만 적용한다.

### 인사이트 (Insights)

CloudWatch Insights는 로그 데이터를 쿼리하고 분석하는 도구다.

**주요 기능:**
- SQL과 유사한 쿼리 언어 사용
- 대용량 로그 데이터에서 특정 패턴 검색
- 통계 계산 및 집계

**활용 사례:**
- 에러 로그 패턴 분석
- 사용자 행동 추적
- 보안 이벤트 검색

**쿼리 예시:**
```
fields @timestamp, @message, level
| filter level = "error"
| stats count() by bin(5m)
```

### 합성 모니터링 (Synthetic Monitoring)

실제 사용자 시나리오를 시뮬레이션해 애플리케이션의 가용성과 성능을 지속적으로 테스트한다.

**동작 방식:**
- 웹사이트의 특정 페이지에 주기적으로 접속
- 응답 시간과 가용성을 측정
- 사용자 경험을 시뮬레이션

**활용 사례:**
- 엔드포인트 가용성 모니터링
- 사용자 관점의 성능 측정
- 지리적으로 분산된 모니터링

### 서비스 맵 (Service Map)

분산 애플리케이션의 서비스 간 의존성을 시각적으로 표시한다.

**주요 기능:**
- 전체 시스템 아키텍처 시각화
- 장애의 전파 경로 파악
- 서비스 간 의존성 이해

**활용 사례:**
- 마이크로서비스 아키텍처 이해
- 장애 영향 범위 분석
- 시스템 아키텍처 문서화

## 운영 고려사항

### 메트릭 설계

**의미 있는 메트릭 선택:**
- 비즈니스에 중요한 지표에 집중
- 너무 많은 메트릭으로 인한 노이즈 방지
- 적절한 집계 기간 설정 (1분, 5분, 15분 등)

**메트릭 네이밍 규칙:**
- 일관된 네이밍 컨벤션 사용
- 메트릭의 목적과 의미를 명확히 표현
- 차원을 활용한 세분화

**실무 팁:**
- 애플리케이션별로 네임스페이스를 구분해 메트릭 관리
- 비즈니스 메트릭과 인프라 메트릭을 분리
- 커스텀 메트릭은 비용을 고려해 선별적으로 수집

### 알람 설정

**적절한 임계값 설정:**
- 과거 데이터 분석을 통한 기준선 설정
- 계절성과 트렌드를 고려한 동적 임계값
- 이상 탐지 기능 활용

**알람 피로도 방지:**
- 조치 가능한 알람만 설정
- 의미 있는 임계값 사용
- 관련 알람 그룹화
- 유지보수 중 알람 억제
- 단계별 알람 레벨 (Warning, Critical)
- 알람 상태 변경 시에만 알림 발송

**실무 팁:**
알람이 너무 많으면 무시하게 된다. Critical 알람만 설정하고, Warning은 선택적으로 설정한다.

### 로그 관리

**로그 구조화:**
- JSON 형태의 구조화된 로그 사용
- 일관된 로그 포맷 적용
- 적절한 로그 레벨 사용

**로그 보존 정책:**
- 비즈니스 요구사항에 따른 보존 기간 설정
- 중요한 로그의 장기 보관 계획
- 비용과 가치의 균형 고려

**실무 팁:**
CloudWatch Logs는 비용이 높다. 보존 기간을 짧게 설정하고, 중요한 로그는 S3로 아카이브한다.

### 대시보드 설계

**사용자별 맞춤 대시보드:**
- 개발자: 애플리케이션 성능 메트릭
- 운영자: 인프라 리소스 사용률
- 경영진: 비즈니스 지표

**실무 팁:**
역할별로 다른 대시보드를 만든다. 한 화면에 모든 정보를 넣지 말고, 필요한 정보만 표시한다.

## 다른 AWS 서비스와의 통합

### AWS Lambda 통합

CloudWatch는 Lambda 함수의 실행 로그와 메트릭을 자동으로 수집한다.

**모니터링 항목:**
- 함수 실행 시간
- 에러율
- 동시 실행 수
- 타임아웃 발생 횟수

**알람 설정:**
```javascript
// Lambda 함수 에러율 알람
{
  "MetricName": "Errors",
  "Namespace": "AWS/Lambda",
  "Statistic": "Sum",
  "Threshold": 10,
  "Period": 300
}
```

### Auto Scaling 통합

CloudWatch 메트릭을 기반으로 Auto Scaling 그룹의 인스턴스 수를 자동으로 조정한다.

**스케일링 조건:**
- CPU 사용률
- 네트워크 트래픽
- 사용자 정의 메트릭

**예시:**
```javascript
// CPU 사용률 70% 초과 시 인스턴스 추가
{
  "MetricName": "CPUUtilization",
  "Threshold": 70,
  "ScalingAdjustment": 1
}
```

### SNS, SQS 통합

알람이 발생했을 때 SNS를 통해 이메일, SMS, 모바일 푸시 알림을 발송하거나, SQS 큐에 메시지를 전송해 비동기 처리를 수행한다.

**사용 예시:**
- Critical 알람: SNS로 즉시 알림
- Warning 알람: SQS 큐에 메시지 전송 후 배치 처리

## 비용 최적화

### 메트릭 최적화

- 필요한 메트릭만 수집
- 적절한 메트릭 해상도 설정 (1분 vs 5분)
- 사용하지 않는 사용자 정의 메트릭 정리

### 로그 최적화

- 로그 보존 기간 최적화
- 불필요한 로그 수집 중단
- 로그 압축 및 아카이빙 활용

### 알람 최적화

- 중복되는 알람 통합
- 불필요한 알람 삭제
- 알람 평가 주기 최적화

**실무 팁:**
CloudWatch Logs는 비용이 높다. 보존 기간을 짧게 설정하고, 중요한 로그는 S3로 아카이브한다.

---

## 메트릭 vs 로그

효과적인 모니터링을 위해서는 메트릭과 로그의 특성을 이해하고 적절히 활용해야 한다.

```mermaid
graph LR
    subgraph "메트릭 Metrics"
        M1[수치 데이터]
        M2[집계 가능]
        M3[시계열 분석]
        M4[알람 트리거]
    end
    
    subgraph "로그 Logs"
        L1[상세 이벤트]
        L2[디버깅 정보]
        L3[패턴 분석]
        L4[감사 추적]
    end
    
    M1 --> USE1[성능 모니터링]
    M2 --> USE1
    M3 --> USE1
    M4 --> USE1
    
    L1 --> USE2[문제 진단]
    L2 --> USE2
    L3 --> USE2
    L4 --> USE2
    
    style M1 fill:#4fc3f7
    style L1 fill:#66bb6a
    style USE1 fill:#ff9800
    style USE2 fill:#9c27b0
```

**메트릭을 사용하는 경우:**
- 시스템의 전반적인 상태를 빠르게 파악할 때
- 시간에 따른 트렌드를 분석할 때
- 자동화된 스케일링이나 알람이 필요할 때
- 대량의 데이터를 효율적으로 처리해야 할 때

**로그를 사용하는 경우:**
- 특정 문제의 원인을 상세히 추적할 때
- 사용자 행동이나 비즈니스 이벤트를 분석할 때
- 보안 감사나 규정 준수를 위해 기록이 필요할 때
- 디버깅이나 문제 해결을 위해 상세 정보가 필요할 때

**실무 팁:**
메트릭은 "무엇이 문제인가"를 알려주고, 로그는 "왜 문제가 발생했는가"를 알려준다.

### 알람 설계

효과적인 알람을 설계하기 위해서는 단계별 접근이 필요하다.

```mermaid
flowchart TD
    START([알람 설계 시작]) --> DEFINE[1. 알람 목적 정의]
    DEFINE --> METRIC[2. 메트릭 선택]
    METRIC --> BASELINE[3. 기준선 설정]
    BASELINE --> THRESHOLD[4. 임계값 설정]
    THRESHOLD --> ACTION[5. 액션 정의]
    ACTION --> TEST[6. 테스트 및 조정]
    TEST --> DEPLOY[7. 배포 및 모니터링]
    DEPLOY --> REVIEW[8. 정기적 검토]
    REVIEW -->|조정 필요| BASELINE
    REVIEW -->|유지| END([완료])
    
    style DEFINE fill:#4fc3f7
    style THRESHOLD fill:#ff9800
    style ACTION fill:#ef5350,color:#fff
    style REVIEW fill:#66bb6a
```

**알람 설계 확인 사항:**
1. 목적 명확화: 이 알람이 해결하려는 문제는 무엇인가?
2. 메트릭 선택: 가장 정확하게 문제를 나타내는 메트릭은 무엇인가?
3. 기준선 설정: 정상 상태에서의 메트릭 값은 어떻게 되는가?
4. 임계값 설정: 어떤 값에서 알람을 트리거할 것인가?
5. 액션 정의: 알람 발생 시 어떤 조치를 취할 것인가?
6. 테스트: 알람이 올바르게 작동하는지 확인했는가?
7. 문서화: 알람의 목적과 대응 방법을 문서화했는가?

**실무 팁:**
과거 데이터를 분석해 정상 범위를 파악한 뒤, 그 범위를 벗어날 때 알람을 설정한다.

### 대시보드 설계

효과적인 대시보드는 사용자의 역할과 목적에 맞게 설계되어야 한다.

**개발자 대시보드:**
- 애플리케이션 성능 메트릭에 집중
- 에러율과 응답 시간을 실시간으로 모니터링
- 배포 후 성능 변화를 추적

**운영자 대시보드:**
- 인프라 리소스 사용률에 집중
- 시스템 가용성과 상태를 한눈에 파악
- 알람 상태와 최근 이벤트를 표시

**경영진 대시보드:**
- 비즈니스 지표에 집중
- 사용자 활동과 수익 지표를 추적
- 서비스 품질 지표를 요약

**실무 팁:**
한 화면에 모든 정보를 넣지 말고, 역할별로 필요한 정보만 표시한다.

## 실전 활용 예제

### Node.js 애플리케이션 통합 모니터링

Express.js 기반 API 서버의 성능, 에러, 비즈니스 메트릭을 CloudWatch로 통합 모니터링한다.

```mermaid
graph TD
    APP[Node.js 애플리케이션] --> MIDDLEWARE[메트릭 미들웨어]
    MIDDLEWARE --> BATCH[메트릭 배치 수집]
    BATCH --> CW[CloudWatch API]
    CW --> METRIC_STORE[메트릭 저장소]
    
    METRIC_STORE --> ALARM[알람 평가]
    METRIC_STORE --> DASH[대시보드 표시]
    
    ALARM -->|임계값 초과| ACTION[자동화 액션]
    ACTION --> SCALE[Auto Scaling]
    ACTION --> NOTIFY[SNS 알림]
    
    style APP fill:#4fc3f7
    style BATCH fill:#66bb6a
    style ALARM fill:#ff9800
    style ACTION fill:#ef5350,color:#fff
```

**핵심 구현:**
- 메트릭을 배치로 수집해 API 호출 비용을 최적화한다
- 비동기 방식으로 메트릭을 전송해 애플리케이션 성능에 영향을 최소화한다
- 차원(Dimensions)을 활용해 메트릭을 세분화해 분석한다

**구현 예시:**

```javascript
// cloudwatch-metrics.js
const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch({ region: 'ap-northeast-2' });

class CloudWatchMetrics {
  constructor(namespace = 'MyApp/API') {
    this.namespace = namespace;
    this.metrics = [];
  }

  // 메트릭 배치 수집 (비용 최적화)
  putMetric(name, value, unit = 'Count', dimensions = {}) {
    this.metrics.push({
      MetricName: name,
      Value: value,
      Unit: unit,
      Dimensions: Object.entries(dimensions).map(([Name, Value]) => ({
        Name,
        Value: String(Value)
      }))
    });

    // 20개씩 배치 전송 (CloudWatch 제한)
    if (this.metrics.length >= 20) {
      this.flush();
    }
  }

  async flush() {
    if (this.metrics.length === 0) return;

    const params = {
      Namespace: this.namespace,
      MetricData: this.metrics
    };

    try {
      await cloudwatch.putMetricData(params).promise();
      this.metrics = [];
    } catch (error) {
      console.error('CloudWatch putMetricData error:', error);
    }
  }

  // HTTP 요청 메트릭
  recordRequest(method, route, statusCode, duration) {
    this.putMetric('RequestCount', 1, 'Count', {
      Method: method,
      Route: route,
      StatusCode: statusCode
    });

    this.putMetric('RequestDuration', duration, 'Milliseconds', {
      Method: method,
      Route: route
    });

    if (statusCode >= 500) {
      this.putMetric('ErrorCount', 1, 'Count', {
        Method: method,
        Route: route,
        StatusCode: statusCode
      });
    }
  }

  // 비즈니스 메트릭
  recordBusinessMetric(metricName, value, userId = null) {
    const dimensions = {};
    if (userId) {
      dimensions.UserId = userId;
    }
    this.putMetric(metricName, value, 'Count', dimensions);
  }
}

// Express 미들웨어
const metrics = new CloudWatchMetrics();

app.use((req, res, next) => {
  const startTime = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - startTime;
    metrics.recordRequest(
      req.method,
      req.route?.path || req.path,
      res.statusCode,
      duration
    );
  });
  
  next();
});

// 주기적 플러시 (1분마다)
setInterval(() => {
  metrics.flush();
}, 60000);
```

**대시보드 구성:**
대시보드는 다음 위젯으로 구성해 API의 전반적인 상태를 모니터링한다:

```mermaid
graph TB
    DASH[API 모니터링 대시보드] --> W1[요청 수 추이]
    DASH --> W2[응답 시간 분포]
    DASH --> W3[에러율 추이]
    DASH --> W4[엔드포인트별 성능]
    DASH --> W5[비즈니스 메트릭]
    
    W1 --> METRIC1[RequestCount]
    W2 --> METRIC2[RequestDuration P95/P99]
    W3 --> METRIC3[ErrorCount/RequestCount]
    W4 --> METRIC4[Route별 메트릭]
    W5 --> METRIC5[주문/결제 메트릭]
    
    style DASH fill:#9c27b0
    style W1 fill:#4fc3f7
    style W2 fill:#66bb6a
    style W3 fill:#ff9800
```

**대시보드 JSON 설정:**

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["MyApp/API", "RequestCount", { "stat": "Sum", "period": 60 }],
          [".", "ErrorCount", { "stat": "Sum", "period": 60 }]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "ap-northeast-2",
        "title": "API 요청 및 에러"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["MyApp/API", "RequestDuration", { "stat": "p95", "period": 60 }],
          [".", ".", { "stat": "p99", "period": 60 }]
        ],
        "period": 300,
        "stat": "Average",
        "region": "ap-northeast-2",
        "title": "응답 시간 (P95, P99)"
      }
    }
  ]
}
```

### CloudWatch Logs Insights 활용

애플리케이션 로그에서 에러 패턴 및 성능 이슈를 실시간으로 분석한다.

```mermaid
flowchart LR
    LOG[애플리케이션 로그] --> STORE[CloudWatch Logs]
    STORE --> QUERY[Logs Insights 쿼리]
    QUERY --> FILTER[필터링 및 집계]
    FILTER --> RESULT[분석 결과]
    RESULT --> METRIC[메트릭 생성]
    RESULT --> ALARM[알람 트리거]
    RESULT --> DASH[대시보드 표시]
    
    style LOG fill:#4fc3f7
    style QUERY fill:#66bb6a
    style METRIC fill:#ff9800
    style ALARM fill:#ef5350,color:#fff
```

**분석 방법:**
- 구조화된 로그 형식(JSON)을 사용해 필드별 분석이 용이하도록 한다
- 자주 사용하는 쿼리를 저장해 빠르게 재사용한다
- 메트릭 필터를 활용해 로그 패턴을 실시간으로 모니터링한다

**주요 쿼리 패턴:**

```javascript
// CloudWatch Logs Insights 쿼리 예제

// 1. 최근 1시간 에러 로그 분석
fields @timestamp, @message, level, error
| filter level = "error"
| sort @timestamp desc
| limit 100

// 2. API 엔드포인트별 응답 시간 분석
fields @timestamp, @message, method, route, duration
| filter ispresent(duration)
| stats avg(duration) as avgDuration, 
        max(duration) as maxDuration,
        count() as requestCount
  by route
| sort avgDuration desc

// 3. 에러율 추이 분석
fields @timestamp, @message, statusCode
| filter statusCode >= 500
| stats count() as errorCount by bin(5m)
| sort @timestamp asc

// 4. 느린 쿼리 감지
fields @timestamp, @message, query, duration
| filter duration > 1000
| sort duration desc
| limit 50
```

**자동화된 인사이트:**

```javascript
// AWS SDK를 사용한 Logs Insights 쿼리 실행
const cloudwatchLogs = new AWS.CloudWatchLogs();

async function analyzeLogs(logGroupName, query) {
  const params = {
    logGroupName,
    startTime: Date.now() - 3600000, // 1시간 전
    endTime: Date.now(),
    queryString: query
  };

  const result = await cloudwatchLogs.startQuery(params).promise();
  
  // 쿼리 완료 대기
  let queryResult;
  do {
    await new Promise(resolve => setTimeout(resolve, 1000));
    queryResult = await cloudwatchLogs.getQueryResults({
      queryId: result.queryId
    }).promise();
  } while (queryResult.status === 'Running');

  return queryResult.results;
}

// 주기적 분석 및 알림
setInterval(async () => {
  const errorCount = await analyzeLogs(
    '/aws/lambda/my-function',
    'fields @message | filter level = "error" | stats count()'
  );
  
  if (errorCount[0]?.value > 10) {
    // SNS를 통한 알림
    await sns.publish({
      TopicArn: 'arn:aws:sns:...',
      Message: `에러 발생: ${errorCount[0].value}건`
    }).promise();
  }
}, 300000); // 5분마다
```

### CloudWatch Alarms와 Lambda를 통한 자동 복구

CPU 사용률이 높을 때 자동으로 인스턴스를 스케일링한다.

```mermaid
sequenceDiagram
    participant METRIC as CloudWatch 메트릭
    participant ALARM as CloudWatch 알람
    participant SNS as SNS 토픽
    participant LAMBDA as Lambda 함수
    participant ASG as Auto Scaling
    participant EC2 as EC2 인스턴스
    
    Note over METRIC: CPU 사용률 모니터링
    METRIC->>ALARM: 메트릭 값 평가
    ALARM->>ALARM: 임계값 초과 확인
    
    alt CPU > 80%
        ALARM->>SNS: 알람 트리거
        SNS->>LAMBDA: 이벤트 전달
        LAMBDA->>ASG: 스케일 아웃 요청
        ASG->>EC2: 새 인스턴스 시작
        EC2-->>ASG: 인스턴스 준비 완료
        ASG-->>LAMBDA: 스케일링 완료
        LAMBDA-->>SNS: 복구 완료 알림
    end
```

**자동화:**
- 알람이 트리거되면 SNS를 통해 Lambda 함수를 호출한다
- Lambda 함수는 상황에 따라 적절한 복구 액션을 수행한다
- 복구 완료 후 결과를 로깅하고 필요시 추가 알림을 발송한다

**CloudFormation 템플릿:**

```yaml
# CloudFormation 템플릿
Resources:
  HighCPUAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: HighCPUUsage
      MetricName: CPUUtilization
      Namespace: AWS/EC2
      Statistic: Average
      Period: 300
      EvaluationPeriods: 2
      Threshold: 80
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AutoScalingPolicy
      Dimensions:
        - Name: InstanceId
          Value: !Ref EC2Instance

  AutoScalingPolicy:
    Type: AWS::AutoScaling::ScalingPolicy
    Properties:
      AdjustmentType: ChangeInCapacity
      AutoScalingGroupName: !Ref AutoScalingGroup
      Cooldown: 300
      ScalingAdjustment: 1

  AutoRecoveryFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: AutoRecovery
      Runtime: nodejs18.x
      Handler: index.handler
      Code:
        ZipFile: |
          const AWS = require('aws-sdk');
          const ec2 = new AWS.EC2();
          
          exports.handler = async (event) => {
            const instanceId = event.detail.instance-id;
            
            // 인스턴스 상태 확인
            const instances = await ec2.describeInstances({
              InstanceIds: [instanceId]
            }).promise();
            
            const state = instances.Reservations[0].Instances[0].State.Name;
            
            if (state === 'running') {
              // 자동 복구: 인스턴스 재시작
              await ec2.rebootInstances({
                InstanceIds: [instanceId]
              }).promise();
              
              console.log(`인스턴스 ${instanceId} 재시작 완료`);
            }
          };
```

### 비용 최적화를 위한 메트릭 필터링

CloudWatch 비용을 최적화하기 위한 주요 방법:

```mermaid
graph TD
    START([비용 최적화]) --> STRATEGY1[메트릭 최적화]
    START --> STRATEGY2[로그 최적화]
    START --> STRATEGY3[알람 최적화]
    
    STRATEGY1 --> M1[필요한 메트릭만 수집]
    STRATEGY1 --> M2[해상도 조정]
    STRATEGY1 --> M3[배치 전송]
    
    STRATEGY2 --> L1[보존 기간 설정]
    STRATEGY2 --> L2[아카이빙 활용]
    STRATEGY2 --> L3[필터링 적용]
    
    STRATEGY3 --> A1[알람 통합]
    STRATEGY3 --> A2[평가 주기 조정]
    STRATEGY3 --> A3[상태 변경 알림]
    
    M1 --> SAVE[비용 절감]
    M2 --> SAVE
    M3 --> SAVE
    L1 --> SAVE
    L2 --> SAVE
    L3 --> SAVE
    A1 --> SAVE
    A2 --> SAVE
    A3 --> SAVE
    
    style START fill:#4fc3f7
    style SAVE fill:#66bb6a
```

**핵심 최적화 기법:**
- 샘플링: 모든 요청이 아닌 일정 비율만 메트릭으로 수집
- 집계: 로컬에서 메트릭을 집계한 후 CloudWatch로 전송
- 배치 전송: 여러 메트릭을 한 번에 전송해 API 호출 비용 절감

**실무 팁:**
CloudWatch는 메트릭 수집과 로그 보관에 비용이 발생한다. 필요한 것만 수집하고, 보존 기간을 적절히 설정한다.

**구현 예시:**

```javascript
// 비용 효율적인 메트릭 수집 전략
class OptimizedCloudWatchMetrics {
  constructor() {
    this.sampleRate = 0.1; // 10% 샘플링
    this.metricCache = new Map();
    this.flushInterval = 60000; // 1분
  }

  // 샘플링을 통한 비용 절감
  shouldRecord() {
    return Math.random() < this.sampleRate;
  }

  // 집계된 메트릭 전송
  recordAggregatedMetric(name, value, dimensions) {
    const key = `${name}_${JSON.stringify(dimensions)}`;
    
    if (!this.metricCache.has(key)) {
      this.metricCache.set(key, {
        name,
        dimensions,
        values: [],
        count: 0
      });
    }

    const metric = this.metricCache.get(key);
    metric.values.push(value);
    metric.count++;

    // 1분마다 평균값으로 전송
    if (this.metricCache.size >= 20 || Date.now() - this.lastFlush > this.flushInterval) {
      this.flushAggregated();
    }
  }

  async flushAggregated() {
    const metricData = [];
    
    for (const [key, metric] of this.metricCache.entries()) {
      const avgValue = metric.values.reduce((a, b) => a + b, 0) / metric.values.length;
      
      metricData.push({
        MetricName: metric.name,
        Value: avgValue,
        Unit: 'Count',
        Dimensions: Object.entries(metric.dimensions).map(([Name, Value]) => ({
          Name,
          Value: String(Value)
        })),
        StatisticValues: {
          SampleCount: metric.count,
          Sum: metric.values.reduce((a, b) => a + b, 0),
          Minimum: Math.min(...metric.values),
          Maximum: Math.max(...metric.values)
        }
      });
    }

    if (metricData.length > 0) {
      await cloudwatch.putMetricData({
        Namespace: 'MyApp/Optimized',
        MetricData: metricData
      }).promise();
    }

    this.metricCache.clear();
    this.lastFlush = Date.now();
  }
}
```

## 참고

- AWS CloudWatch 공식 문서: https://docs.aws.amazon.com/cloudwatch/
- AWS Well-Architected Framework: https://aws.amazon.com/architecture/well-architected/
- CloudWatch 모범 사례: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_bestpractices.html