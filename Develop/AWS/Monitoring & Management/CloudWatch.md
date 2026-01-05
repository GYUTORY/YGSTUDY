---
title: AWS CloudWatch 로그 분석 및 실시간 모니터링 전략
tags: [aws, cloudwatch, monitoring, logs, observability]
updated: 2026-01-05
---

# AWS CloudWatch Logs: 실시간 로그 분석 및 모니터링 전략

AWS CloudWatch는 로그 수집, 분석, 모니터링, 경보 설정까지 모두 지원하는 AWS의 대표적인 관측(Observability) 서비스입니다.  
본 문서는 **CloudWatch Logs의 실시간 분석과 운영 전략**을 실무 중심으로 정리합니다.

---

## 1. CloudWatch Logs란?

CloudWatch Logs는 AWS 리소스에서 발생한 로그 데이터를 실시간으로 수집하고 저장하며, 이를 기반으로 **검색**, **시각화**, **알람**, **자동 대응**까지 할 수 있게 해주는 서비스입니다.

### 지원 로그 예시:
- EC2 인스턴스 내 애플리케이션 로그 (agent 설치)
- Lambda 로그 (자동 수집)
- ECS/EKS 로그 (CloudWatch Agent 또는 FluentBit 사용)
- VPC Flow Logs, RDS 로그, API Gateway 로그 등

---

## 2. 로그 수집 아키텍처

### 일반 아키텍처 구성

```
[서비스 또는 인스턴스]
      ↓
[CloudWatch Logs Agent / Lambda 자동 수집]
      ↓
[Log Group & Log Stream (CloudWatch Logs)]
      ↓
[CloudWatch Logs Insights, Metric Filter, Alarm, Dashboard]
```

- **Log Group**: 로그의 논리적 그룹 (예: `/ecs/web`, `/lambda/my-service`)
- **Log Stream**: 실제 로그 데이터 스트림 (인스턴스 ID 또는 컨테이너 ID 단위)

---

## 3. 로그 분석 도구

### 3.1 CloudWatch Logs Insights

CloudWatch Logs Insights는 SQL 유사 문법을 이용해 대용량 로그를 빠르게 쿼리할 수 있는 분석 도구입니다.

```sql
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20
```

**주요 기능:**
- 필터링 (filter)
- 정렬 및 제한 (sort, limit)
- 그룹화 및 집계 (stats)
- 필드 추출 및 파싱 (parse)

**예시: 상태 코드별 요청 수**
```sql
fields status
| stats count(*) by status
```

**예시: IP별 오류 발생 횟수**
```sql
fields @message
| filter @message like /500/
| parse @message "IP: *," as ip
| stats count(*) by ip
```

---

### 3.2 Metric Filter

Log Group에서 특정 패턴이 발견될 때 **지표(Metric)** 로 전환하여 알람 생성에 활용할 수 있습니다.

**예시: 로그 메시지에 "ERROR" 포함 시 지표 생성**

1. Log Group 선택 → “Create metric filter”
2. 패턴 입력: `ERROR`
3. 지표 이름 지정: `AppErrorCount`
4. 알람 설정: 지표가 1 이상일 때 알림

---

## 4. 실시간 모니터링 전략

### 4.1 주요 이벤트 감지

| 감지 항목 | 로그 위치 | 감지 방식 |
|-----------|------------|------------|
| Lambda 오류 | CloudWatch Logs (자동) | Metric Filter + 알람 |
| ECS 애플리케이션 오류 | `/var/log/app.log` | CloudWatch Agent 수집 + 필터 |
| VPC 보안 위협 | VPC Flow Logs | IP/포트 기반 패턴 분석 |
| ALB 5xx 오류 | ALB 액세스 로그 | Athena/CloudWatch Logs로 분석 가능 |

---

### 4.2 로그 기반 알림 예시

| 경보 대상 | 로그 패턴 | 대응 |
|-----------|------------|------------|
| 서비스 오류 증가 | `"ERROR"` 10건 이상/1분 | SNS/Slack 알림, 자동 복구 |
| 인증 실패 감지 | `"Auth failed"` 포함 | 관리자 알림, IP 차단 |
| 과도한 요청 | `"429 Too Many Requests"` | API Gateway Throttling 재조정 |

---

### 4.3 실시간 알림 구성 (SNS 연동)

1. Metric Filter 설정 (예: `ERROR`)
2. 지표 생성: `AppErrorCount`
3. CloudWatch Alarm 생성
4. SNS Topic 연동 (Email, Slack, Lambda 등)
5. 실시간 알림 수신

---

## 5. 비용 관리 전략

CloudWatch Logs는 사용량 기반 과금입니다. 로그 수집량, 저장 기간, 쿼리 실행량에 따라 비용이 증가할 수 있습니다.

### 5.1 비용 요소

| 항목 | 과금 기준 |
|------|------------|
| 로그 수집 | GB 단위 |
| 로그 저장 | GB-월 |
| Logs Insights 쿼리 | GB 스캔량 단위 |
| Metric Filter | 지표 수에 따라 |

### 5.2 절감 전략

- 로그 레벨 최소화 (`INFO` vs `DEBUG`)
- 저장 기간 설정 (예: 30일 후 삭제)
- 오래된 로그는 S3로 Export 후 삭제
- 쿼리 최적화 (time range, filter 조건 명확히)

---

## 6. 실무 구성 예시

### 예: MSA 구조에서 로그 모니터링 구성

```
[API Gateway]      [ECS (서비스들)]      [Lambda]
     ↓                  ↓                   ↓
  Access Logs      Application Logs      CloudWatch Logs
     ↓                  ↓                   ↓
  CloudWatch Logs Group (서비스 단위)
     ↓
  Logs Insights / Metric Filter
     ↓
  CloudWatch Alarm
     ↓
  SNS (Slack, Email, Lambda 트리거 등)
```

---

## 7. Terraform 예시: 로그 그룹 + Metric Filter + Alarm

```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/my-app"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_metric_filter" "error_filter" {
  name           = "error-metric-filter"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "ERROR"
  
  metric_transformation {
    name      = "AppErrorCount"
    namespace = "MyApp"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "error_alarm" {
  alarm_name          = "app-error-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "AppErrorCount"
  namespace           = "MyApp"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

---

## 8. 결론 및 실무 팁

- CloudWatch Logs는 단순 수집이 아닌 **분석/알림/자동 대응까지 연결**해야 효과적입니다
- 실시간 장애 감지를 위해 **Logs Insights + Metric Filter + Alarm + SNS** 조합을 권장합니다
- 비용 최적화 및 저장 정책도 반드시 설정해 두어야 합니다
- ECS/EKS 환경에서는 **FluentBit, CloudWatch Agent** 활용 필수입니다
- 팀 내 로그 쿼리 공유 문화도 중요 (Logs Insights 쿼리는 URL로 공유 가능)

---

## 참고 자료

- [CloudWatch Logs Insights 공식 문서](https://docs.aws.amazon.com/cloudwatch/latest/logs/AnalyzingLogData.html)
- [CloudWatch Agent 설치 가이드](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [ECS 로그 수집 설정](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_cloudwatch_logs.html)
- [CloudWatch 비용 계산기](https://calculator.aws.amazon.com/)