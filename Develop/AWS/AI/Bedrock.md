---
title: Amazon Bedrock
tags: [AWS, AI, Bedrock, LLM, GenAI]
updated: 2026-05-03
---

# Amazon Bedrock

## 개요

Amazon Bedrock은 여러 회사의 Foundation Model을 하나의 API로 호출할 수 있게 해주는 AWS의 관리형 서비스다. Anthropic Claude, Meta Llama, Amazon Titan, Mistral, Cohere, AI21, Stability AI 같은 모델들을 인프라 구축 없이 바로 쓸 수 있다.

OpenAI API를 써봤다면 개념은 비슷하다. 다만 Bedrock은 AWS 생태계 안에서 동작하니까 IAM으로 권한을 관리하고, VPC endpoint로 private하게 호출할 수 있고, CloudWatch로 로깅이 자동으로 붙는다. 엔터프라이즈 환경에서 OpenAI를 직접 붙이기 어려운 경우(데이터가 외부로 나가는 게 금지된 경우) Bedrock이 대안이 되는 일이 많다.

실무에서 Bedrock을 쓸 때 자주 걸리는 포인트 몇 가지가 있다. 모델 접근 권한을 콘솔에서 별도로 활성화해야 하고, 리전별로 쓸 수 있는 모델이 다르고, On-demand는 throttling이 생각보다 빡세게 걸린다. 이런 것들을 모르고 들어가면 프로덕션에서 당황하는 경우가 많다.

## 사용할 수 있는 모델 종류

Bedrock에서 호출할 수 있는 Foundation Model은 크게 텍스트 생성, 멀티모달, 임베딩, 이미지 생성 네 부류로 나뉜다. 모델 ID는 `<provider>.<model_name>-<version>` 형태이고, cross-region inference profile은 앞에 `us.`, `eu.`, `apac.` 같은 prefix가 붙는다.

**Anthropic Claude 계열**이 실무에서 가장 많이 쓰인다. Claude 3.5 Sonnet(`anthropic.claude-3-5-sonnet-20241022-v2:0`)이 범용 작업에서 품질이 가장 안정적이다. 200K 컨텍스트, vision 지원, tool use 지원이 다 들어있다. Claude 3.5 Haiku는 분류, 요약, 라우팅 같은 가벼운 작업에 쓴다. Sonnet 대비 8배 정도 싸다. Claude 3 Opus는 가장 비싸고 latency도 가장 느리지만, 복잡한 추론이 필요한 곳에서 차이가 난다. 실무에서는 Sonnet과 Haiku 조합으로 거의 다 해결되는 편이다.

**Meta Llama 3 / 3.1 / 3.2 계열**은 오픈 가중치 모델이다. Llama 3.1 405B는 GPT-4급 성능을 내지만 응답이 느리고 비용도 비싸서 실시간 서비스에는 부담스럽다. Llama 3.1 70B가 가성비가 좋다. 영어 위주로 학습돼서 한국어 성능은 Claude보다 확실히 떨어진다. 한국어 서비스를 만든다면 PoC 단계에서 같은 프롬프트로 Claude와 Llama를 돌려보고 직접 품질을 비교해야 한다.

**Amazon Titan 계열**은 AWS가 직접 만든 모델이다. Titan Text Lite/Express는 가격이 매우 싸지만 품질이 Claude/Llama 대비 한 단계 아래다. 단순 분류나 키워드 추출 같은 작업이 아니면 잘 안 쓴다. Titan Embeddings G1/V2는 RAG에서 임베딩 모델로 자주 쓰이는데, 영어 기준으로 만들어져서 한국어 검색 품질은 아쉽다. Titan Image Generator는 이미지 생성용인데 Stable Diffusion 대비 활용도가 낮다.

**Cohere 계열**에서 실무적으로 중요한 건 Embed Multilingual이다. 100개 이상 언어를 지원하고 한국어 임베딩 품질이 Titan보다 확실히 낫다. 한국어 RAG를 Bedrock에서 돌린다면 임베딩은 Cohere를 쓰는 경우가 많다. Command R+는 Llama 70B와 비슷한 포지션인데 RAG에 특화된 fine-tuning이 들어가서 인용(citation) 처리가 깔끔하다.

**Mistral 계열**은 유럽발 모델이다. Mistral Large 2가 Llama 70B와 경쟁하는 위치인데, 함수 호출 정확도가 좋다는 평이 있다. 다만 한국어는 Llama와 비슷하게 약하다.

**AI21 Jamba**는 SSM(State Space Model) 기반이라 긴 컨텍스트 처리에서 메모리 효율이 좋다. 256K 컨텍스트가 필요하면서 비용이 부담스러운 경우에 검토한다.

**Stability AI**의 SDXL과 Stable Diffusion 3는 이미지 생성용이다. Bedrock에서 부르면 IAM/VPC 통합이 자동으로 되니까 자체 호스팅 부담을 덜 수 있다.

모델 선택할 때 실무 가이드는 단순하다. 일단 Claude 3.5 Sonnet으로 시작해서 동작이 검증되면 비용/지연 시간을 보고 Haiku로 다운그레이드하거나, 한국어 RAG라면 Cohere Embed Multilingual + Claude 조합으로 가는 패턴이 가장 무난하다. 새 모델이 나올 때마다 갈아타기보다는 평가 데이터셋을 만들어 두고 점수를 비교하는 게 안전하다.

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

언제 InvokeModel을 그대로 쓰는 게 나은가. 이미지 생성 모델(Stable Diffusion, Titan Image)과 임베딩 모델은 Converse 지원이 안 되거나 의미가 없어서 InvokeModel로만 호출한다. 그리고 모델 고유 파라미터를 세밀하게 튜닝해야 하는 경우(Claude의 `top_k`, Llama의 `repetition_penalty` 같은 것)에 Converse의 `additionalModelRequestFields`로 넘기는 게 어색하면 InvokeModel이 더 직관적이다. 챗봇 흐름 같은 일반 텍스트 생성 작업은 Converse, 그 외 특수 모델은 InvokeModel로 가르면 깔끔하다.

## 시스템 프롬프트와 멀티턴 대화

Converse API는 `system` 필드를 별도로 분리해놨다. OpenAI처럼 첫 메시지에 role="system"을 넣는 방식이 아니다. 이걸 모르고 messages 배열에 system role을 넣으면 ValidationException이 난다.

```python
MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"

system_prompts = [
    {"text": "너는 백엔드 시니어 엔지니어다. 코드는 Python으로 보여주고 한국어로 설명한다."}
]

def chat(messages, user_text):
    messages.append({"role": "user", "content": [{"text": user_text}]})
    response = client.converse(
        modelId=MODEL,
        system=system_prompts,
        messages=messages,
        inferenceConfig={"maxTokens": 1024, "temperature": 0.5},
    )
    assistant_msg = response["output"]["message"]
    messages.append(assistant_msg)
    return assistant_msg["content"][0]["text"]

history = []
chat(history, "asyncio.gather와 TaskGroup 차이가 뭐야?")
chat(history, "그럼 예외 처리 관점에서는?")
```

멀티턴에서 자주 놓치는 게 컨텍스트 누적이다. 매 요청마다 직전까지의 모든 메시지가 입력 토큰으로 다시 들어간다. 100턴 대화의 마지막 요청은 99턴치 전체를 한 번 더 보내는 셈이다. 비용과 latency가 같이 선형으로 올라간다. 운영에서는 일정 토큰을 넘어가면 오래된 턴을 잘라내거나 요약으로 압축하는 로직을 같이 짜야 한다. 보통 슬라이딩 윈도우(최근 N턴 유지) + 그 이전은 한 줄 요약으로 치환하는 패턴을 많이 쓴다.

role은 user와 assistant만 번갈아 나와야 한다. user 두 번 연속, assistant 두 번 연속이면 거부된다. 첫 메시지는 반드시 user여야 한다. 이 제약은 Anthropic 모델 특성인데 Converse가 모델 차이를 추상화해도 이 부분은 그대로 노출된다.

## Vision 멀티모달 호출

Claude 3 계열과 Llama 3.2 Vision은 이미지를 입력으로 받는다. 영수증 OCR, 스크린샷에서 에러 메시지 추출, 차트 해석, 디자인 시안에서 컴포넌트 추출 같은 작업에 쓴다.

```python
with open("receipt.jpg", "rb") as f:
    image_bytes = f.read()

response = client.converse(
    modelId=MODEL,
    messages=[
        {
            "role": "user",
            "content": [
                {"image": {"format": "jpeg", "source": {"bytes": image_bytes}}},
                {"text": "영수증의 품목별 가격과 총합을 JSON으로 추출해줘"},
            ],
        }
    ],
    inferenceConfig={"maxTokens": 1024},
)
```

이미지 토큰 비용이 생각보다 비싸다. Claude는 1092×1092 이상 이미지를 약 1.6K 토큰으로 환산한다. 고해상도 사진을 그대로 보내면 한 호출에 입력 토큰이 만 단위로 뛴다. 입력 전에 Pillow로 적정 해상도(보통 1024px 이내)로 리사이즈하는 게 표준이다. 너무 줄이면 글자 인식 정확도가 떨어지니까 OCR 작업이라면 768~1024px 사이가 적당하다.

S3에 있는 이미지는 `source.s3Location`으로 직접 참조할 수 있다. Lambda에서 이미지를 다운받아 base64로 보내는 것보다 빠르고 메모리도 덜 쓴다. 이 방식은 Bedrock service principal에게 해당 S3 객체에 대한 GetObject 권한이 있어야 한다.

PNG, JPEG, GIF, WebP를 지원한다. PDF 직접 입력은 Converse에서 지원되니까 단순 문서 분석은 PDF를 통째로 보내는 게 편하다. 다만 PDF는 페이지당 토큰 비용이 누적되니 50페이지 넘는 문서는 미리 필요한 페이지만 추출해서 보내는 게 낫다.

## 임베딩 모델 호출

RAG 외에 검색, 중복 탐지, 분류, 클러스터링에서도 임베딩이 따로 필요하다. 임베딩은 Converse가 지원되지 않아 InvokeModel로 호출한다.

```python
def embed_cohere(texts, input_type="search_document"):
    body = json.dumps({
        "texts": texts,
        "input_type": input_type,
    })
    response = client.invoke_model(
        modelId="cohere.embed-multilingual-v3",
        body=body,
    )
    return json.loads(response["body"].read())["embeddings"]

# 인덱싱 시
doc_vectors = embed_cohere(["문서 본문 1", "문서 본문 2"], "search_document")
# 검색 시
query_vector = embed_cohere(["사용자 질문"], "search_query")[0]
```

Cohere Embed Multilingual은 `input_type`을 구분해서 넘기는 게 핵심이다. 문서 인덱싱은 `search_document`, 검색 쿼리는 `search_query`로 다르게 줘야 검색 정확도가 정상적으로 나온다. 비대칭 임베딩 구조라서 같은 텍스트라도 input_type에 따라 임베딩 벡터가 달라진다. 이걸 모르고 둘 다 `search_document`로 인덱싱/쿼리를 하면 검색 품질이 미묘하게 떨어지는데 원인 찾기가 어렵다.

Titan Embeddings는 단순하다. `inputText` 하나만 넘기면 끝이고 input type 구분이 없다. 한 번에 텍스트 하나만 보낼 수 있어서 배치 처리가 불편하다. 한국어 품질도 Cohere만 못하다.

배치 호출은 throttling 회피의 핵심이다. Cohere는 한 번에 96개까지 묶을 수 있다. 1만 건짜리 문서를 단건씩 호출하면 분당 쿼터에 금방 걸린다. 96개씩 묶으면 호출 수가 100배 줄어든다.

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

청킹 전략별 특성도 미리 알아두는 게 좋다. Fixed-size는 토큰 수 기준으로 자르는데, 문장이 중간에서 끊기는 경우가 많아 검색 품질이 떨어질 수 있다. Hierarchical은 부모-자식 청크를 함께 저장해서 작은 청크로 검색하고 큰 청크로 컨텍스트를 보낸다. 표나 목록이 많은 기술 문서에 유리하다. Semantic chunking은 임베딩 유사도로 의미 단위 경계를 찾는데, 처리 비용이 가장 높고 한국어에서는 경계 추정이 부정확한 편이다. 처음에는 fixed-size 500토큰 + overlap 100 정도로 시작하고, 검색 품질이 부족하면 hierarchical로 옮기는 패턴이 보통이다.

OpenSearch Serverless를 고르면 유의할 점이 있다. 최소 OCU(OpenSearch Compute Unit) 비용이 꽤 나간다. 개발 환경에서 24시간 돌려놓으면 월 $700 넘게 나올 수 있으니 개발용은 Aurora PostgreSQL pgvector로 하는 게 낫다. 인덱싱과 검색에 OCU가 따로 잡히는 구조라서 트래픽이 적은 단계에서는 비용 효율이 더 떨어진다.

Knowledge Base를 동기화할 때도 함정이 있다. S3에 새 문서를 올려도 자동으로 인덱싱되지 않는다. Data source를 만들 때 `ingestion job`을 명시적으로 트리거하거나 EventBridge로 S3 이벤트를 받아서 `start_ingestion_job`을 호출해야 한다. 이걸 깜박하면 새 문서가 검색에 안 잡혀서 한참 디버깅하게 된다.

## Agents for Bedrock

LLM이 도구를 호출해서 복잡한 작업을 수행하는 Agent 기능이다. OpenAI Function Calling이나 Assistants API와 비슷한 개념인데, Lambda 함수를 action group으로 연결하는 구조다.

Agent는 다음 4가지 컴포넌트로 구성된다. Agent 본체(어떤 모델을 쓰고 어떤 instruction을 가질지), Action group(Lambda 함수와 OpenAPI 스키마 또는 함수 정의), Knowledge base(연결된 RAG 소스), Prompt template(orchestration/pre-processing/post-processing 각 단계의 프롬프트). 호출은 `bedrock-agent-runtime` 클라이언트의 `invoke_agent`로 한다. Session ID를 넘겨야 멀티턴 대화 컨텍스트가 유지되니까 클라이언트에서 세션 관리를 직접 해야 한다.

```python
agent_client = boto3.client("bedrock-agent-runtime")

response = agent_client.invoke_agent(
    agentId="AGENT123",
    agentAliasId="ALIAS456",
    sessionId="user-789-session-001",
    inputText="이번 달 EC2 비용 알려줘",
    enableTrace=True,
)

for event in response["completion"]:
    if "chunk" in event:
        print(event["chunk"]["bytes"].decode(), end="")
    if "trace" in event:
        # 어떤 도구를 어떤 입력으로 호출했는지 trace에 들어있다
        pass
```

실무에서 Agent를 써보면 생각보다 다루기 어렵다. 플로우가 블랙박스라서 왜 이런 응답이 나왔는지 추적하려면 trace를 켜고 꼼꼼히 봐야 한다. 특히 `orchestrationTrace.modelInvocationInput.text`를 보면 Bedrock이 모델에게 실제로 보낸 system prompt와 사용 가능한 도구 목록이 다 찍힌다. Tool 호출이 의도와 다르게 일어나면 거기서 원인을 찾아야 한다. 프롬프트 템플릿이 내부적으로 관리되는데 이게 모델 버전에 따라 바뀌면서 동작이 달라지는 경우가 있다. Claude 3와 Claude 3.5에서 같은 agent 설정이 다르게 작동하는 걸 본 적이 있다.

단순한 tool calling이 필요하다면 Converse API의 `toolConfig`를 쓰는 게 낫다. 훨씬 투명하고 제어하기 쉽다. Agent는 정말 복잡한 멀티스텝 플로우가 필요하고 AWS 네이티브 서비스 연동(Lambda, Knowledge Base)을 많이 써야 할 때 검토한다.

`toolUse`가 나오면 모델이 답을 만든 게 아니라 "이 도구를 이런 입력으로 불러달라"고 요청한 상태다. 우리가 도구를 직접 실행하고 결과를 다시 모델에 돌려줘야 최종 답이 나온다. 이 라운드트립을 빠뜨리고 toolUse 응답만 보고 끝내버리는 실수가 자주 보인다.

```python
tool_config = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_weather",
                "description": "특정 도시의 현재 날씨를 조회한다",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    }
                },
            }
        }
    ]
}

def run_tool(name, input_):
    if name == "get_weather":
        return {"city": input_["city"], "temp": 18, "condition": "맑음"}
    raise ValueError(f"unknown tool: {name}")

messages = [{"role": "user", "content": [{"text": "서울 날씨 알려줘"}]}]
response = client.converse(modelId=MODEL, messages=messages, toolConfig=tool_config)

while response["stopReason"] == "tool_use":
    # 어시스턴트의 toolUse 메시지를 그대로 history에 추가
    messages.append(response["output"]["message"])

    tool_results = []
    for block in response["output"]["message"]["content"]:
        if "toolUse" not in block:
            continue
        use = block["toolUse"]
        result = run_tool(use["name"], use["input"])
        tool_results.append({
            "toolResult": {
                "toolUseId": use["toolUseId"],
                "content": [{"json": result}],
            }
        })

    messages.append({"role": "user", "content": tool_results})
    response = client.converse(modelId=MODEL, messages=messages, toolConfig=tool_config)

print(response["output"]["message"]["content"][0]["text"])
```

while 루프로 도는 이유는 모델이 한 번에 여러 도구를 차례로 부를 수 있기 때문이다. 첫 번째 도구 결과를 본 뒤 두 번째 도구를 부르고, 그 결과를 본 뒤 세 번째를 부르는 식이다. `stopReason`이 `end_turn`으로 바뀔 때까지 계속 돌려야 한다. 무한 루프 방지로 최대 반복 횟수도 같이 거는 게 안전하다.

`toolUseId`는 반드시 같이 돌려줘야 한다. 한 응답에 toolUse가 여러 개 있을 때 어떤 결과가 어떤 호출에 대응하는지 모델이 매칭하는 키다. 도구 실행이 실패하면 toolResult에 `"status": "error"`와 함께 에러 메시지를 넘기면 된다. 그러면 모델이 에러를 인지하고 다른 시도를 하거나 사용자에게 사과한다.

## 요금 모델

두 가지 모드가 있다.

**On-demand**는 요청한 만큼만 과금되는 방식이다. 입력 토큰, 출력 토큰별로 단가가 다르고 모델별로 가격이 크게 차이난다. Claude 3.5 Sonnet은 입력 1M 토큰당 $3, 출력 1M 토큰당 $15 수준이다. Haiku는 10배 가까이 싸다. Titan Text Lite는 더 싸다.

실무에서 자주 놓치는 게 캐시된 프롬프트(prompt caching)의 가격 차이다. Claude는 prompt caching을 지원하는데, 캐시 쓰기는 기본 요금의 1.25배, 캐시 읽기는 0.1배다. 긴 시스템 프롬프트를 반복해서 쓰는 경우 비용을 10배 가까이 줄일 수 있다.

Converse API에서는 `cachePoint` 콘텐츠 블록으로 캐시 경계를 표시한다. 그 앞쪽 내용이 캐시된다.

```python
response = client.converse(
    modelId=MODEL,
    system=[
        {"text": LONG_SYSTEM_PROMPT},  # 회사 가이드, 도메인 지식, 응답 형식 규칙 등
        {"cachePoint": {"type": "default"}},
    ],
    messages=messages,
)

usage = response["usage"]
print(usage.get("cacheReadInputTokens"), usage.get("cacheWriteInputTokens"))
```

캐시 TTL이 5분이라 그 안에 같은 prefix로 다시 호출이 들어와야 캐시 히트가 된다. 트래픽이 산발적인 서비스에서는 5분 TTL을 못 채우고 매번 cache write만 일으키면서 오히려 비용이 늘 수 있다. 시스템 프롬프트에 최소 토큰 요건도 있다(Claude 3.5 Sonnet 기준 약 1024 토큰). 짧은 프롬프트에 cachePoint를 붙이면 그냥 무시된다. 캐시 쓰기 비용도 1.25배라서 한 번 쓰고 한 번도 안 읽으면 손해다. 적어도 2~3회 이상 재사용이 보장될 때만 켜는 게 맞다.

**Provisioned Throughput**은 시간당 고정 비용으로 throughput을 예약하는 방식이다. 모델 유닛(Model Unit) 단위로 사다. 단가는 싸지 않은데, 장점은 throttling이 없고 latency가 안정적이라는 것이다. 프로덕션에서 꾸준한 부하가 예측되는 경우 아니면 On-demand가 유리하다. 보통 초당 수십 요청 이상이 지속적으로 들어오는 상황에서 검토한다.

Provisioned Throughput은 1개월, 6개월 commitment가 있고 1개월은 지금 풀려있는 모델이 제한적이다. 미리 확인하지 않고 commit 걸었다가 해지 못 해서 돈 날리는 경우가 있다.

**Batch inference**도 알아두면 좋다. 실시간 응답이 필요 없는 대량 처리(분류, 요약, 데이터 라벨링)에 쓴다. JSONL 파일을 S3에 올리고 batch job을 만들면 결과를 다시 S3로 떨궈준다. On-demand 대비 50% 저렴한 단가로 처리되고, throttling 영향도 거의 받지 않는다. 단점은 처리 완료까지 수 시간이 걸린다는 것이고 모든 모델이 batch를 지원하는 건 아니다. 야간에 누적된 데이터를 한 번에 처리하는 작업에서 비용 절감 효과가 크다.

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

비용 폭주 방지용으로 Deny 정책을 같이 거는 패턴도 자주 쓴다. 예를 들어 개발 계정에서는 Opus 같은 비싼 모델을 명시적으로 막는다.

```json
{
    "Effect": "Deny",
    "Action": "bedrock:InvokeModel*",
    "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-opus-*",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-7-*"
    ]
}
```

Allow는 와일드카드여도 Deny가 더 강하니까 실수로 비싼 모델을 호출하는 사고를 막을 수 있다. 신규 비싼 모델이 출시될 때마다 Deny 리스트를 갱신하는 운영 프로세스가 같이 필요하다.

## 비용 모니터링과 태깅

Bedrock은 토큰 단위 과금이라 몇 줄 잘못 짠 루프 하나가 하루 만에 수백 달러를 태우는 일이 흔하다. 사고 친 다음 청구서에서 발견하면 늦으니 사전에 가드레일을 깔아둬야 한다.

CloudWatch에서 모델별로 `InputTokenCount`, `OutputTokenCount`, `Invocations` 메트릭을 받을 수 있다. 모델 ID를 dimension으로 잡고 임계치 알람을 걸어두는 게 기본이다.

```python
cw = boto3.client("cloudwatch")
cw.put_metric_alarm(
    AlarmName="bedrock-claude-sonnet-input-tokens-spike",
    MetricName="InputTokenCount",
    Namespace="AWS/Bedrock",
    Dimensions=[{"Name": "ModelId", "Value": "anthropic.claude-3-5-sonnet-20241022-v2:0"}],
    Statistic="Sum",
    Period=300,
    EvaluationPeriods=1,
    Threshold=5_000_000,  # 5분간 500만 토큰 = 약 $15 (Sonnet 기준)
    ComparisonOperator="GreaterThanThreshold",
    AlarmActions=["arn:aws:sns:us-east-1:111122223333:bedrock-alerts"],
)
```

AWS Budgets로 Bedrock 서비스 단위 예산을 잡고, 50%, 80%, 100% 도달 시 SNS 알림을 받게 설정한다. Cost Explorer에서 Bedrock 비용을 모델별로 보려면 인보이스가 모델 단위로 쪼개져 있어야 하는데, 이건 자동으로 안 되고 비용 할당 태그(cost allocation tag)를 활성화해야 한다.

태깅은 호출 코드에서 직접 못 한다. Bedrock 호출 자체에는 태그가 안 붙는다. 대신 application inference profile을 만들고 거기에 태그를 붙이면 호출 시 그 profile ID로 모델을 부르고, 비용이 태그 단위로 집계된다. 팀별/프로젝트별 비용 분리가 필요하면 이 패턴이 사실상 유일한 방법이다.

```python
bedrock = boto3.client("bedrock")
profile = bedrock.create_inference_profile(
    inferenceProfileName="team-search-claude-sonnet",
    modelSource={
        "copyFrom": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    },
    tags=[{"key": "Team", "value": "search"}, {"key": "CostCenter", "value": "CC-1234"}],
)
```

호출할 때는 `modelId`에 모델 ARN 대신 inference profile ARN을 넣는다. 비용 보고서에서 Team 태그로 필터하면 팀별 사용량이 떨어진다.

운영에서 흔한 사고 패턴 몇 가지를 미리 알아두면 좋다. 첫째, 무한 루프 — tool_use 응답이 계속 나오는데 stop 조건을 안 걸어두면 모델이 계속 도구를 부르면서 토큰을 태운다. while에 max_iterations(보통 10~15)를 같이 거는 게 표준이다. 둘째, 컨텍스트 누적 — 멀티턴 챗봇에서 history를 자르지 않으면 한 사용자 세션이 시간이 갈수록 호출당 비용이 기하급수적으로 늘어난다. 셋째, 재시도 폭주 — throttling 에러가 났을 때 백오프 없이 즉시 재시도를 돌리면 같은 요청이 수백 번 큐잉되면서 결국 다 처리돼버려 비용이 폭주한다.

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
