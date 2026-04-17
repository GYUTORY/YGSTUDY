---
title: Amazon Bedrock
tags: [AWS, AI, Bedrock, LLM, GenAI]
updated: 2026-04-17
---

# Amazon Bedrock

## 개요

Amazon Bedrock은 여러 회사의 Foundation Model을 하나의 API로 호출할 수 있게 해주는 AWS의 관리형 서비스다. Anthropic Claude, Meta Llama, Amazon Titan, Mistral, Cohere, AI21, Stability AI 같은 모델들을 인프라 구축 없이 바로 쓸 수 있다.

OpenAI API를 써봤다면 개념은 비슷하다. 다만 Bedrock은 AWS 생태계 안에서 동작하니까 IAM으로 권한을 관리하고, VPC endpoint로 private하게 호출할 수 있고, CloudWatch로 로깅이 자동으로 붙는다. 엔터프라이즈 환경에서 OpenAI를 직접 붙이기 어려운 경우(데이터가 외부로 나가는 게 금지된 경우) Bedrock이 대안이 되는 일이 많다.

실무에서 Bedrock을 쓸 때 자주 걸리는 포인트 몇 가지가 있다. 모델 접근 권한을 콘솔에서 별도로 활성화해야 하고, 리전별로 쓸 수 있는 모델이 다르고, On-demand는 throttling이 생각보다 빡세게 걸린다. 이런 것들을 모르고 들어가면 프로덕션에서 당황하는 경우가 많다.

## 모델 접근 권한 활성화

처음 Bedrock을 쓸 때 가장 많이 당황하는 부분이다. IAM 권한이 있어도 모델 자체에 대한 접근이 활성화되어 있지 않으면 `AccessDeniedException`이 난다.

콘솔에서 Bedrock → Model access로 들어가서 쓰고 싶은 모델별로 "Request model access"를 눌러야 한다. Claude 같은 Anthropic 모델은 use case를 적어서 제출해야 하고, 보통 몇 분 안에 승인된다. Meta Llama도 use case 폼이 있다. Amazon Titan은 바로 활성화된다.

이게 리전별로 따로 설정된다는 점이 중요하다. us-east-1에서 활성화했다고 us-west-2에서도 되는 게 아니다. 멀티 리전으로 운영한다면 각 리전에서 따로 신청해야 한다.

## InvokeModel API

가장 기본적인 호출 방법이다. 모델별로 요청/응답 포맷이 다르기 때문에 모델을 바꿀 때마다 코드를 수정해야 한다.

```python
import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "파이썬 데코레이터 간단히 설명해줘"}
    ]
}

response = client.invoke_model(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    body=json.dumps(body),
    contentType="application/json",
)

result = json.loads(response["body"].read())
print(result["content"][0]["text"])
```

Claude는 Anthropic 포맷을 따르고, Llama는 Meta 포맷, Titan은 Amazon 포맷을 따른다. 그래서 `body` 구조가 완전히 달라진다. 이게 불편해서 Converse API가 나왔다.

## Converse API

모델에 상관없이 동일한 포맷으로 호출할 수 있는 API다. 2024년 중반에 추가됐고 실무에서 새로 짠다면 이걸 쓰는 게 맞다.

```python
response = client.converse(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[
        {"role": "user", "content": [{"text": "파이썬 데코레이터 간단히 설명해줘"}]}
    ],
    inferenceConfig={
        "maxTokens": 1024,
        "temperature": 0.7,
    },
)

print(response["output"]["message"]["content"][0]["text"])
```

모델 ID만 바꾸면 Llama로 전환할 수 있다. `inferenceConfig`로 `maxTokens`, `temperature`, `topP`, `stopSequences`를 넘긴다. 모델별 특수 파라미터(Claude의 `top_k` 같은 것)는 `additionalModelRequestFields`로 따로 넘겨야 한다.

단점이 하나 있다. Converse API가 나온 지 얼마 안 돼서 모든 모델이 지원하는 게 아니다. 새로 출시된 모델은 Converse를 바로 지원하지만, 옛날 모델은 InvokeModel만 되는 경우가 있다. 그리고 일부 모델은 시스템 프롬프트 포맷이 미묘하게 다르게 변환되니까 migration할 때는 실제 응답을 비교해봐야 한다.

## 스트리밍 응답

ChatGPT처럼 토큰이 한 글자씩 나오는 UX를 만들려면 스트리밍이 필수다. Bedrock은 `InvokeModelWithResponseStream`과 `ConverseStream`을 제공한다.

```python
response = client.converse_stream(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[
        {"role": "user", "content": [{"text": "긴 글을 써줘"}]}
    ],
    inferenceConfig={"maxTokens": 2048},
)

for event in response["stream"]:
    if "contentBlockDelta" in event:
        delta = event["contentBlockDelta"]["delta"]
        if "text" in delta:
            print(delta["text"], end="", flush=True)
    elif "messageStop" in event:
        print()
    elif "metadata" in event:
        usage = event["metadata"]["usage"]
        print(f"\ninput: {usage['inputTokens']}, output: {usage['outputTokens']}")
```

이벤트 종류가 몇 가지 있다. `messageStart`, `contentBlockStart`, `contentBlockDelta`, `contentBlockStop`, `messageStop`, `metadata`. 실무에서 자주 놓치는 게 `metadata` 이벤트인데, 여기에 토큰 사용량이 들어있다. 비용 계산하려면 이걸 받아야 한다.

스트리밍에서 주의할 점은 중간에 네트워크가 끊기거나 throttling이 걸리면 에러 이벤트가 스트림 안에서 날아온다는 것이다. 클라이언트 쪽에서 이벤트를 파싱할 때 예외 이벤트도 처리해야 한다. 스트리밍 시작된 뒤에는 응답이 끝날 때까지 토큰 사용량이 계속 차감되니까, 중간에 중단할 방법이 없다는 것도 기억해야 한다.

## Guardrails

모델이 폭력/성적/혐오 콘텐츠를 생성하거나, 특정 주제(주식 추천, 의료 상담 같은 것)를 다루지 않도록 제한하는 기능이다. PII 감지와 마스킹, 사용자 정의 거부어도 된다.

```python
response = client.converse(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[{"role": "user", "content": [{"text": user_input}]}],
    guardrailConfig={
        "guardrailIdentifier": "abc123xyz",
        "guardrailVersion": "1",
        "trace": "enabled",
    },
)

if response["stopReason"] == "guardrail_intervened":
    # guardrail이 차단한 경우
    pass
```

실무에서 Guardrails를 쓸 때 맞닥뜨리는 문제가 있다. 한국어 탐지 정확도가 영어보다 확실히 떨어진다. 영어 기반으로 학습된 필터가 한국어 맥락을 잘 이해 못 해서 false positive가 많이 나온다. 금융이나 의료 도메인에서는 Guardrails만 믿지 말고 애플리케이션 레이어에서 별도 검증을 넣어야 한다.

또 Guardrails 호출이 모델 호출과 별도로 과금된다. 프롬프트 토큰과 응답 토큰 양쪽에 대해 guardrail 처리 비용이 붙으니까 비용 산정할 때 빼먹으면 안 된다.

## Knowledge Base (RAG)

Bedrock이 제공하는 관리형 RAG 서비스다. S3에 문서를 올리면 자동으로 청킹하고 임베딩을 만들어서 벡터 DB에 저장해준다. 벡터 DB는 OpenSearch Serverless, Aurora PostgreSQL(pgvector), Pinecone, Redis Enterprise 중 고를 수 있다.

```python
agent_client = boto3.client("bedrock-agent-runtime")

response = agent_client.retrieve_and_generate(
    input={"text": "우리 회사 휴가 정책이 어떻게 되나요?"},
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "knowledgeBaseId": "KB12345ABC",
            "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        },
    },
)

print(response["output"]["text"])
for citation in response["citations"]:
    for ref in citation["retrievedReferences"]:
        print(ref["location"])
```

장점은 빠르게 PoC 만들기 좋다는 것이다. S3에 PDF/DOCX/TXT 올리고 knowledge base 만들면 몇 시간 안에 RAG 챗봇이 돌아간다. 인용(citation)도 자동으로 붙는다.

단점은 커스터마이징이 제한적이다는 것이다. 청킹 전략은 fixed-size, hierarchical, semantic 정도만 고를 수 있고 세밀하게 제어하기 어렵다. 한국어 임베딩 품질도 별로다. Titan Embeddings는 영어 기준으로 만들어져서 한국어 검색 정확도가 아쉬운 편이다. Cohere multilingual이 나아서 실무에서는 이걸 많이 쓴다. 정말 품질이 중요한 서비스라면 LangChain이나 LlamaIndex로 직접 파이프라인을 짜는 게 맞다.

OpenSearch Serverless를 고르면 유의할 점이 있다. 최소 OCU(OpenSearch Compute Unit) 비용이 꽤 나간다. 개발 환경에서 24시간 돌려놓으면 월 $700 넘게 나올 수 있으니 개발용은 Aurora PostgreSQL pgvector로 하는 게 낫다.

## Agents for Bedrock

LLM이 도구를 호출해서 복잡한 작업을 수행하는 Agent 기능이다. OpenAI Function Calling이나 Assistants API와 비슷한 개념인데, Lambda 함수를 action group으로 연결하는 구조다.

실무에서 Agent를 써보면 생각보다 다루기 어렵다. 플로우가 블랙박스라서 왜 이런 응답이 나왔는지 추적하려면 trace를 켜고 꼼꼼히 봐야 한다. 프롬프트 템플릿이 내부적으로 관리되는데 이게 모델 버전에 따라 바뀌면서 동작이 달라지는 경우가 있다. Claude 3와 Claude 3.5에서 같은 agent 설정이 다르게 작동하는 걸 본 적이 있다.

단순한 tool calling이 필요하다면 Converse API의 `toolConfig`를 쓰는 게 낫다. 훨씬 투명하고 제어하기 쉽다. Agent는 정말 복잡한 멀티스텝 플로우가 필요하고 AWS 네이티브 서비스 연동(Lambda, Knowledge Base)을 많이 써야 할 때 검토한다.

```python
response = client.converse(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=messages,
    toolConfig={
        "tools": [
            {
                "toolSpec": {
                    "name": "get_weather",
                    "description": "특정 도시의 현재 날씨를 조회한다",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"}
                            },
                            "required": ["city"],
                        }
                    },
                }
            }
        ]
    },
)

if response["stopReason"] == "tool_use":
    for block in response["output"]["message"]["content"]:
        if "toolUse" in block:
            tool_name = block["toolUse"]["name"]
            tool_input = block["toolUse"]["input"]
            # 여기서 실제 도구 실행
```

## 요금 모델

두 가지 모드가 있다.

**On-demand**는 요청한 만큼만 과금되는 방식이다. 입력 토큰, 출력 토큰별로 단가가 다르고 모델별로 가격이 크게 차이난다. Claude 3.5 Sonnet은 입력 1M 토큰당 $3, 출력 1M 토큰당 $15 수준이다. Haiku는 10배 가까이 싸다. Titan Text Lite는 더 싸다.

실무에서 자주 놓치는 게 캐시된 프롬프트(prompt caching)의 가격 차이다. Claude는 prompt caching을 지원하는데, 캐시 쓰기는 기본 요금의 1.25배, 캐시 읽기는 0.1배다. 긴 시스템 프롬프트를 반복해서 쓰는 경우 비용을 10배 가까이 줄일 수 있다.

**Provisioned Throughput**은 시간당 고정 비용으로 throughput을 예약하는 방식이다. 모델 유닛(Model Unit) 단위로 사다. 단가는 싸지 않은데, 장점은 throttling이 없고 latency가 안정적이라는 것이다. 프로덕션에서 꾸준한 부하가 예측되는 경우 아니면 On-demand가 유리하다. 보통 초당 수십 요청 이상이 지속적으로 들어오는 상황에서 검토한다.

Provisioned Throughput은 1개월, 6개월 commitment가 있고 1개월은 지금 풀려있는 모델이 제한적이다. 미리 확인하지 않고 commit 걸었다가 해지 못 해서 돈 날리는 경우가 있다.

## IAM 권한 설정

최소 권한으로 깔끔하게 묶기가 까다로운 편이다. 기본 패턴은 이렇다.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:Converse",
                "bedrock:ConverseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-*",
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-*"
            ]
        }
    ]
}
```

모델 ARN을 와일드카드로 지정할 수 있지만, 너무 넓게 열면 비싼 모델을 실수로 호출했을 때 비용이 폭발한다. 프로덕션 IAM은 쓸 모델만 명시적으로 허용하는 게 안전하다.

Guardrails나 Knowledge Base를 쓰면 별도 권한이 필요하다. `bedrock:ApplyGuardrail`, `bedrock:Retrieve`, `bedrock:RetrieveAndGenerate` 등을 추가해야 한다. Agent는 `bedrock:InvokeAgent`가 따로 있다.

VPC endpoint도 많이 쓴다. 온프레미스나 private subnet에서 인터넷으로 나가지 않고 Bedrock을 호출하려면 `com.amazonaws.<region>.bedrock-runtime` interface endpoint를 만든다. 이걸 안 만들고 private subnet에서 호출하면 NAT gateway를 통해서 나가게 돼서 트래픽 비용이 뜬금없이 나온다.

## 리전별 모델 가용성

리전마다 쓸 수 있는 모델이 다르다. us-east-1(버지니아)와 us-west-2(오레곤)가 가장 많은 모델을 지원한다. 새 모델은 보통 이 두 리전에 먼저 풀린다.

서울 리전(ap-northeast-2)은 지원 모델이 제한적이다. Claude 3 Haiku, Claude 3.5 Sonnet은 2024년 후반부터 지원됐지만, 최신 모델이 바로 들어오지는 않는다. 법적으로 데이터가 한국 리전에 머물러야 하는 서비스라면 모델 선택지가 좁아진다.

이 문제를 해결하려고 **Cross-Region Inference Profile**이라는 기능이 나왔다. 여러 리전을 묶어서 하나의 profile ID로 호출하면, Bedrock이 알아서 가용한 리전으로 라우팅한다. 예를 들어 `us.anthropic.claude-3-5-sonnet-20241022-v2:0` 같은 prefix(`us.`, `eu.`, `apac.`)가 붙은 모델 ID를 쓴다. Throttling 회피에도 도움이 되고, 단일 리전 대비 더 많은 capacity를 쓸 수 있다.

다만 cross-region inference는 요청이 어느 리전으로 갔는지 확정적이지 않다. 데이터 주권 요구사항이 빡빡한 프로젝트에서는 쓰면 안 된다. 응답 메타데이터에서 실제 처리된 리전을 확인할 수 있으니까 로깅해두는 게 좋다.

## ThrottlingException과 재시도

On-demand를 쓰면 ThrottlingException을 피하기가 어렵다. AWS가 공식적으로 공개하지 않는 계정별 per-model 쿼터가 있는데, 신규 계정은 꽤 낮게 책정되어 있다. Claude 3.5 Sonnet의 경우 신규 계정에서 분당 20요청, 분당 40만 토큰 수준에서 시작하는 경우가 많다.

```python
import time
import random
from botocore.exceptions import ClientError

def invoke_with_retry(client, model_id, messages, max_retries=5):
    for attempt in range(max_retries):
        try:
            return client.converse(
                modelId=model_id,
                messages=messages,
                inferenceConfig={"maxTokens": 1024},
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ThrottlingException":
                if attempt == max_retries - 1:
                    raise
                # exponential backoff + jitter
                wait = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
            elif code == "ModelTimeoutException":
                # 이건 재시도해도 같은 결과일 가능성이 높음
                raise
            else:
                raise
```

boto3가 기본적으로 standard retry mode를 쓰는데, 이건 재시도 횟수가 3회로 제한적이다. `Config(retries={"max_attempts": 10, "mode": "adaptive"})`로 adaptive 모드를 켜면 throttling 비율에 따라 client-side rate limiting이 자동으로 걸린다. 실무에서는 이게 수동 재시도보다 낫다.

```python
from botocore.config import Config

config = Config(
    retries={"max_attempts": 10, "mode": "adaptive"},
    read_timeout=300,
)
client = boto3.client("bedrock-runtime", config=config, region_name="us-east-1")
```

Throttling이 지속적으로 난다면 몇 가지 선택지가 있다.

첫째, AWS Support에 quota increase를 요청한다. 처리 시간은 보통 며칠 걸리고, 비즈니스 justification이 있어야 허가된다. 최근 써본 경험으로는 Claude 최신 모델 쿼터 증설은 상당히 까다로운 편이다.

둘째, Cross-region inference profile로 바꾼다. 여러 리전의 capacity를 합쳐 쓰니까 단일 리전 쿼터보다 여유가 있다.

셋째, Provisioned Throughput으로 전환한다. 비용이 크게 뛰지만 throttling 자체가 없어진다.

넷째, 작은 모델로 트래픽을 분산한다. 모든 요청을 Claude 3.5 Sonnet으로 보내지 말고, 쉬운 질문은 Haiku로 돌리는 라우팅을 짜면 쿼터 부담이 확 줄어든다.

## 로깅과 관측성

Bedrock은 CloudWatch 메트릭을 자동으로 기록한다. `Invocations`, `InvocationLatency`, `InvocationThrottles`, `InputTokenCount`, `OutputTokenCount`가 기본 메트릭이다. 모델별로 dimension이 붙는다.

CloudTrail에는 API 호출 자체만 기록되고 프롬프트/응답 내용은 들어가지 않는다. 내용까지 저장하려면 **Model Invocation Logging**을 따로 켜야 한다. 이건 S3나 CloudWatch Logs로 프롬프트 전문과 응답 전문을 내보내준다. 디버깅이나 감사에 필수인데 기본적으로 꺼져있어서 놓치는 경우가 많다.

```
Bedrock Console → Settings → Model invocation logging → Enable
```

로깅이 켜지면 프롬프트 내용이 S3에 저장되니까 PII 관리에 신경 써야 한다. 암호화와 접근 권한을 빡빡하게 걸고, 필요 없는 로그는 S3 lifecycle로 주기적으로 삭제하는 게 안전하다.

## 정리

Bedrock을 실무에 도입할 때 순서는 보통 이렇게 간다. 콘솔에서 모델 access 신청 → IAM 정책 작성 → Converse API로 기본 호출 구현 → CloudWatch 메트릭 대시보드 구성 → Model Invocation Logging 활성화 → throttling 대비해서 adaptive retry와 cross-region inference 검토 → 트래픽이 커지면 Provisioned Throughput 고려.

OpenAI에 익숙한 팀이라면 처음엔 Bedrock의 추가 복잡도(리전 관리, IAM, 모델 access 승인 같은 것)가 번거롭게 느껴질 수 있다. 대신 AWS 안에서 VPC private 호출, IAM 기반 권한, CloudWatch 통합 관측, 데이터 주권 보장 같은 것들이 쉽게 되니까 엔터프라이즈 요구사항이 있는 조직에서는 결국 이쪽으로 가게 되는 경우가 많다.
