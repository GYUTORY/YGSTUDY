---
title: ALB Lambda 타겟 그룹 심화
tags: [aws, cloud, terraform]
updated: 2026-07-18
---

# ALB Lambda 타겟 그룹 심화

ALB 타겟 그룹 타입은 네 가지다. EC2, ECS IP, IP 주소, 그리고 Lambda. Lambda를 타겟으로 쓰면 서버 없이 HTTP 요청을 받을 수 있다. API Gateway 없이 ALB만으로 Lambda를 붙이는 방식이라 비용 구조가 다르고, 제약도 다르다.

실제로 운영하다 보면 응답 포맷 하나 틀려서 ALB가 502를 뱉거나, Cold Start 때문에 헬스체크가 실패해서 타겟이 unhealthy로 빠지는 일이 생긴다. 이 문서는 그 함정들을 정리한다.

## Lambda 응답 포맷

ALB가 Lambda에서 응답을 받으면 특정 JSON 구조를 기대한다. 이 구조를 지키지 않으면 ALB는 그냥 502를 돌려준다. Lambda 자체에서 에러가 난 게 아닌데 502가 뜨면 응답 포맷부터 확인해야 한다.

필수 필드는 세 개다.

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"message\": \"ok\"}"
}
```

`statusCode`는 정수여야 한다. 문자열 `"200"` 이면 ALB가 파싱에 실패한다. `body`는 항상 문자열이다. 객체를 그대로 넣으면 안 된다. `headers`는 빈 객체라도 있어야 하는 케이스가 있어서 빠뜨리지 않는 게 안전하다.

base64 인코딩 응답이 필요하면 `isBase64Encoded` 필드를 추가한다.

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "image/png"
  },
  "isBase64Encoded": true,
  "body": "iVBORw0KGgo..."
}
```

이미지나 바이너리 파일을 직접 반환할 때 쓴다. 단, 1MB 제한에 base64 인코딩 오버헤드까지 붙으면 원본이 약 750KB 수준에서 제한에 걸린다.

### ALB가 Lambda로 보내는 이벤트 구조

Lambda 입장에서는 HTTP 요청이 이런 구조로 들어온다.

```json
{
  "requestContext": {
    "elb": {
      "targetGroupArn": "arn:aws:elasticloadbalancing:..."
    }
  },
  "httpMethod": "GET",
  "path": "/api/users",
  "queryStringParameters": {
    "page": "1"
  },
  "headers": {
    "host": "example.com",
    "x-forwarded-for": "1.2.3.4"
  },
  "body": null,
  "isBase64Encoded": false
}
```

API Gateway의 event 구조와 비슷하지만 다르다. `requestContext` 안에 `elb` 키가 있고, `pathParameters`나 `stageVariables` 같은 필드는 없다. API Gateway용 Lambda를 그대로 ALB에 붙이면 `requestContext.apiId` 같은 걸 참조하는 코드에서 런타임 에러가 날 수 있다.

## Multi-Value Headers

기본 상태에서 ALB는 쿼리스트링과 헤더를 단일 값으로 Lambda에 전달한다. 같은 키가 여러 번 오면 마지막 값만 남는다.

```
GET /search?tag=aws&tag=lambda&tag=alb
```

기본 모드 이벤트:

```json
{
  "queryStringParameters": {
    "tag": "alb"
  }
}
```

마지막 `alb`만 살아있다. 앞의 `aws`, `lambda`는 사라진다.

Multi-Value Headers를 활성화하면 달라진다.

```json
{
  "multiValueQueryStringParameters": {
    "tag": ["aws", "lambda", "alb"]
  }
}
```

배열로 온전히 들어온다. 타겟 그룹 속성 `lambda.multi_value_headers.enabled`를 `true`로 설정하면 된다.

활성화하면 Lambda 응답도 `multiValueHeaders`를 써야 한다. `headers`와 `multiValueHeaders`를 동시에 쓰면 `multiValueHeaders`가 우선한다.

```json
{
  "statusCode": 200,
  "multiValueHeaders": {
    "Set-Cookie": ["session=abc; HttpOnly", "tracking=xyz; SameSite=Strict"],
    "Content-Type": ["application/json"]
  },
  "body": "{}"
}
```

쿠키 여러 개를 설정할 때 단일 `headers`로는 안 된다. `Set-Cookie`를 두 번 보내야 하는데, `headers` 모드는 마지막 것만 남기기 때문이다. 인증 쿠키 + 추적 쿠키를 동시에 심어야 하는 경우 multi-value headers 활성화가 필수다.

## 1MB 페이로드 제한

ALB가 Lambda를 호출할 때 요청 본문과 응답 본문 모두 1MB를 넘으면 안 된다. 정확히는 요청 최대 1MB, 응답 최대 1MB다.

1MB를 초과하는 요청이 들어오면 ALB 레벨에서 413을 반환한다. Lambda까지 도달하지 않는다. 응답이 1MB를 초과하면 ALB가 502를 반환한다.

파일 업로드나 대용량 응답이 필요한 경우 두 가지 방법으로 우회한다.

### Presigned URL 패턴

Lambda는 S3 Presigned URL만 생성해서 반환하고, 클라이언트가 직접 S3에 업로드하거나 다운로드하게 한다. Lambda를 통과하는 페이로드 크기 자체가 작아진다.

```python
import boto3

def handler(event, context):
    s3 = boto3.client('s3')
    
    # 업로드용 presigned URL 생성
    url = s3.generate_presigned_url(
        'put_object',
        Params={'Bucket': 'my-bucket', 'Key': 'uploads/file.zip'},
        ExpiresIn=300
    )
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'upload_url': url})
    }
```

클라이언트는 이 URL로 직접 S3에 PUT 요청을 보낸다. ALB와 Lambda는 URL 생성 요청/응답만 처리해서 페이로드가 수십 바이트 수준이다.

### CloudFront + S3 패턴

응답이 대용량 정적 파일인 경우, Lambda는 리다이렉트(302)나 처리된 결과의 S3 위치를 반환하고 CloudFront가 S3에서 직접 서빙하게 한다.

엑셀 리포트 생성처럼 Lambda가 파일을 만들어야 하는 경우, Lambda가 S3에 저장하고 Presigned URL을 반환하는 패턴을 쓴다. 동기적으로 파일을 스트리밍하는 건 ALB Lambda 타겟으로는 불가능하다.

## ALB가 Lambda를 호출하는 방식

ALB는 Lambda를 동기 방식(`InvocationType: RequestResponse`)으로 직접 호출한다. API Gateway처럼 Lambda 앞에 다른 서비스가 있는 게 아니라 ALB 자체가 Lambda API를 호출하는 주체다.

Lambda에 리소스 기반 정책이 없으면 ALB가 호출할 수 없다. Terraform이나 콘솔에서 타겟 그룹에 Lambda를 등록하면 자동으로 권한이 추가되지 않는 경우가 있어서, 아래 Permission을 명시적으로 붙여야 한다.

```bash
aws lambda add-permission \
  --function-name my-function \
  --statement-id alb-invoke \
  --action lambda:InvokeFunction \
  --principal elasticloadbalancing.amazonaws.com \
  --source-arn arn:aws:elasticloadbalancing:ap-northeast-2:123456789:targetgroup/my-tg/abc123
```

`source-arn`에 타겟 그룹 ARN을 지정하면 해당 타겟 그룹만 호출할 수 있다. 없으면 계정 내 모든 ALB가 호출할 수 있어서 너무 넓다.

ALB Lambda 타겟은 Lambda 별칭(Alias)이나 버전을 지정할 수 없다. 함수 이름 또는 ARN만 가능하다. 블루/그린 배포를 별칭으로 하는 경우 이 방식은 맞지 않는다.

## Cold Start와 헬스체크

ALB 타겟 그룹은 헬스체크를 주기적으로 보낸다. Lambda가 타겟이면 헬스체크도 실제 Lambda 호출이다. Cold Start가 발생하면 헬스체크 응답이 늦어진다.

헬스체크 기본 설정:

- HealthCheckIntervalSeconds: 30초
- HealthCheckTimeoutSeconds: 5초
- HealthyThresholdCount: 5회
- UnhealthyThresholdCount: 2회

Cold Start 시 Lambda 초기화가 5초를 초과하면 헬스체크가 타임아웃으로 실패한다. 연속 2회 실패하면 타겟이 unhealthy로 표시된다. unhealthy 상태에서는 실제 요청도 이 Lambda로 라우팅되지 않는다.

Lambda Provisioned Concurrency를 사용하면 Cold Start가 없어서 이 문제가 사라진다. 하지만 비용이 발생한다.

Provisioned Concurrency 없이 운영하는 경우, 헬스체크 타임아웃을 늘려서 완화할 수 있다.

```hcl
resource "aws_lb_target_group" "lambda" {
  name        = "my-lambda-tg"
  target_type = "lambda"

  health_check {
    enabled             = true
    path                = "/health"
    interval            = 35
    timeout             = 30
    healthy_threshold   = 2
    unhealthy_threshold = 5
    matcher             = "200"
  }
}
```

타임아웃을 30초까지 늘리면 Cold Start 여유가 생긴다. 단 `interval`은 `timeout`보다 반드시 커야 한다.

헬스체크 경로를 별도로 두는 게 실용적이다. `/health` 엔드포인트는 최대한 가볍게 만들어야 한다. DB 연결 확인, 외부 API 호출 같은 것을 헬스체크에 넣으면 Cold Start에 의존성 초기화까지 더해져서 타임아웃이 더 빈번해진다.

```python
def handler(event, context):
    path = event.get('path', '')
    
    if path == '/health':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': '{"status":"ok"}'
        }
    
    # 실제 로직
    return handle_request(event)
```

## ALB vs API Gateway 선택 기준

둘 다 Lambda를 HTTP로 노출할 수 있는데 선택 기준이 명확하다.

**ALB를 선택하는 경우**

ALB는 시간당 과금이다. 고정 트래픽이 있으면 API Gateway보다 싸다. VPC 내부에서만 접근하는 내부 서비스라면 ALB + internal 설정으로 충분하다. 기존 ALB가 있고 Lambda를 타겟 중 하나로 추가하는 경우 비용 추가가 거의 없다.

인증이 필요하면 ALB Cognito 통합이나 OIDC를 쓰면 된다. API Gateway Authorization보다 설정이 단순한 케이스가 많다.

**API Gateway를 선택하는 경우**

요청 건수가 적고 불규칙한 경우 API Gateway가 유리하다. 건당 과금이라 idle 시간 비용이 없다.

WebSocket이 필요하면 API Gateway WebSocket API밖에 없다. Lambda 응답 스트리밍(`ResponseStream`)도 API Gateway 쪽이 먼저 지원됐다.

IAM 기반 요청 서명(Sigv4), API 키 관리, 사용량 계획(Usage Plan), 요청/응답 매핑 템플릿이 필요하면 API Gateway를 써야 한다. ALB는 이런 기능이 없다.

Lambda 별칭 기반 트래픽 분산(Canary)도 API Gateway 쪽이 낫다. ALB는 가중치 기반 타겟 그룹으로 카나리를 구현할 수 있지만 Lambda ARN이 별칭을 지원하지 않아서 함수를 두 개 만들어야 한다.

## Terraform 설정 예제

```hcl
# Lambda 함수
resource "aws_lambda_function" "api" {
  function_name = "my-api"
  runtime       = "python3.12"
  handler       = "main.handler"
  role          = aws_iam_role.lambda.arn
  filename      = "function.zip"

  timeout = 29  # ALB 기본 idle timeout 60초보다 짧게
}

# ALB Lambda 권한
resource "aws_lambda_permission" "alb" {
  statement_id  = "AllowALBInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "elasticloadbalancing.amazonaws.com"
  source_arn    = aws_lb_target_group.lambda.arn
}

# 타겟 그룹
resource "aws_lb_target_group" "lambda" {
  name        = "my-lambda-tg"
  target_type = "lambda"

  health_check {
    enabled             = true
    path                = "/health"
    interval            = 35
    timeout             = 30
    healthy_threshold   = 2
    unhealthy_threshold = 5
    matcher             = "200"
  }
}

# Lambda를 타겟으로 등록
resource "aws_lb_target_group_attachment" "lambda" {
  target_group_arn = aws_lb_target_group.lambda.arn
  target_id        = aws_lambda_function.api.arn
  depends_on       = [aws_lambda_permission.alb]
}

# Multi-Value Headers 활성화
resource "aws_lb_target_group" "lambda_multi" {
  name        = "my-lambda-mv-tg"
  target_type = "lambda"

  lambda_multi_value_headers_enabled = true

  health_check {
    enabled             = true
    path                = "/health"
    interval            = 35
    timeout             = 30
    healthy_threshold   = 2
    unhealthy_threshold = 5
    matcher             = "200"
  }
}

# 리스너 규칙
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.lambda.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}
```

`depends_on = [aws_lambda_permission.alb]`가 중요하다. 권한이 붙기 전에 타겟을 등록하면 등록은 되는데 실제 호출 시 AccessDeniedException이 발생한다. Terraform이 타겟 등록과 권한 추가를 병렬로 처리하면 race condition이 생길 수 있어서 명시적으로 의존성을 걸어야 한다.

Lambda 함수 `timeout`을 29초로 설정한 건 ALB idle timeout(기본 60초)보다 짧게 해서 ALB에서 먼저 끊기는 상황을 막기 위해서다. Lambda가 먼저 종료되면 Lambda가 에러 응답을 반환할 수 있지만, ALB가 먼저 연결을 끊으면 클라이언트는 갑작스러운 연결 종료를 받는다. ALB idle timeout을 줄이거나 Lambda timeout을 ALB timeout보다 짧게 맞춰야 한다.
