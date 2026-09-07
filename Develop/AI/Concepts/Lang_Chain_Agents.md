---
title: LangChain Agent
tags: [ai, llm, python]
updated: 2026-09-07
---

# LangChain Agent

## ReAct 루프가 실제로 하는 일

ReAct(Reason + Act)는 LLM이 생각(Thought) → 행동(Action) → 관찰(Observation) 사이클을 반복하며 문제를 푸는 방식이다. AgentExecutor는 이 루프를 관리하는 실행기다.

실행 흐름은 이렇다:

1. 사용자 입력이 들어오면 프롬프트에 Tool 목록을 붙여 LLM에 전달
2. LLM이 `Action: tool_name`, `Action Input: ...`을 포함한 텍스트를 반환
3. AgentExecutor가 해당 Tool을 호출하고 결과를 `Observation: ...`으로 프롬프트에 추가
4. LLM이 최종 답변이라고 판단하면 `Final Answer: ...`를 반환하며 루프 종료

3번에서 Tool 결과가 기대와 다를 때가 문제다. LLM이 "이 정보로는 부족하다"고 판단하면 같은 Tool을 다시 호출한다. Tool 결과가 충분히 구체적이지 않으면 루프가 계속 반복된다.

## Tool 정의

Tool을 정의하는 방법은 두 가지 주류 방식이 있다.

**함수에 데코레이터를 붙이는 방법**이 가장 단순하다:

```python
from langchain.tools import tool

@tool
def get_weather(city: str) -> str:
    """도시 이름을 받아 현재 날씨를 반환한다."""
    return f"{city}의 현재 날씨: 맑음, 23도"
```

`@tool` 데코레이터는 함수의 docstring을 Tool 설명으로, 파라미터 힌트를 스키마로 사용한다. LLM은 이 설명을 보고 언제 이 Tool을 쓸지 판단하므로 docstring이 부실하면 엉뚱한 상황에서 호출된다.

**Pydantic 스키마로 입력을 정의하는 방법**은 파라미터가 여러 개거나 타입 검증이 필요할 때 쓴다:

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class SearchInput(BaseModel):
    query: str = Field(description="검색할 키워드")
    max_results: int = Field(default=5, description="반환할 최대 결과 수")

class SearchTool(BaseTool):
    name = "web_search"
    description = "웹에서 정보를 검색한다. 최신 정보나 모르는 정보를 찾을 때 사용한다."
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        return f"검색 결과: ..."

    def _arun(self, query: str, max_results: int = 5) -> str:
        raise NotImplementedError("비동기 미지원")
```

`args_schema`를 명시하면 LLM이 JSON 형태로 파라미터를 구성하고, AgentExecutor가 호출 전에 Pydantic으로 검증한다. 타입 오류는 Tool 실행 전에 잡힌다.

## AgentExecutor 설정과 max_iterations 함정

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

prompt = hub.pull("hwchase17/react")
agent = create_react_agent(llm, tools, prompt)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=10,                  # 기본값 15
    max_execution_time=60,              # 초 단위, 기본값 None
    early_stopping_method="generate",   # 또는 "force"
    handle_parsing_errors=True,
    verbose=True,
)
```

`max_iterations` 기본값이 15인데, 복잡한 작업에서 Tool 하나 호출에 LLM 왕복이 3~4번 붙으면 한도가 금방 찬다. 작업 중간에 `"Agent stopped due to iteration limit or time limit"`이 뜨면서 중간 결과만 반환된다.

반대로 제한이 너무 크면 LLM이 스스로 종료하지 못하는 루프에 빠진 상태로 비용이 쌓인다. `max_iterations`와 `max_execution_time` 둘 다 설정하는 게 안전하다. 시간 제한이 더 직관적으로 동작한다.

`early_stopping_method`를 `"force"`로 설정하면 한도 초과 시 그냥 종료하고, `"generate"`는 LLM에 최종 답변을 강제로 생성하도록 한 번 더 요청한다. 둘 다 완전한 답변을 보장하지 않는다.

`handle_parsing_errors=True`는 LLM이 잘못된 포맷으로 응답할 때 에러를 던지지 않고 LLM에 다시 요청한다. 켜두지 않으면 포맷 에러 하나에 전체 에이전트가 죽는다. 단, 재시도마다 이터레이션을 소모하므로 파싱 에러가 반복되면 `max_iterations`를 여유있게 설정해야 한다.

## OpenAI Functions 기반 에이전트

ReAct는 텍스트 파싱 방식이라 LLM이 포맷을 틀리면 실패한다. OpenAI Functions 기반은 모델이 JSON 형태로 Tool 호출을 반환해서 파싱 에러가 거의 없다.

```python
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0)
agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
```

내부적으로 Tool 정보를 OpenAI의 `functions` 파라미터로 전달하고, 모델이 `function_call` 형태로 응답한다. AgentExecutor가 `function_call.name`으로 Tool을 찾아 `function_call.arguments`를 파싱해서 호출한다.

ReAct와 비교하면 파싱 에러는 줄지만 OpenAI 모델에 종속된다. 로컬 모델이나 Anthropic을 쓰려면 ReAct 방식을 써야 한다. LangChain 0.2 이후로는 `create_openai_tools_agent`가 더 권장된다 — parallel function calling을 지원하기 때문이다.

## 커스텀 Tool 에러 반환

Tool에서 에러가 발생했을 때 처리 방식이 에이전트 전체 동작에 영향을 준다.

```python
class DatabaseQueryTool(BaseTool):
    name = "query_db"
    description = "데이터베이스에서 데이터를 조회한다."

    def _run(self, query: str) -> str:
        try:
            result = db.execute(query)
            return str(result)
        except Exception as e:
            return f"오류 발생: {str(e)}. 쿼리 형식을 확인하고 다시 시도하라."
```

에러를 문자열로 반환하면 에이전트는 그걸 `Observation`으로 받아 다음 액션을 결정한다. 에러 메시지에 "다음에 어떻게 해야 하는지" 힌트를 담으면 에이전트가 수정해서 재시도할 가능성이 높아진다.

예외를 올리면 AgentExecutor가 `ToolException`으로 처리한다. `handle_tool_error=True` 설정 시 에러 메시지를 Observation에 넣고 계속 진행한다. 에러 시 반환할 내용을 커스터마이즈하려면 문자열이나 함수를 넣는다:

```python
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    handle_tool_error=True,
    # 또는 커스텀 메시지:
    # handle_tool_error="요청이 잘못됐다. 다른 방법을 시도하라.",
)
```

## 에이전트 루프가 무한 반복되는 원인

`max_iterations` 한도 도달 전에 루프가 종료되지 않는 원인은 대부분 세 가지다.

**Tool 결과가 LLM의 기대와 다를 때.** 에이전트가 특정 형식의 데이터를 기대하는데 Tool이 다른 형식을 반환하면 LLM은 "아직 원하는 걸 못 얻었다"고 판단하고 같은 Tool을 반복 호출한다. Tool 설명과 실제 반환값의 형식을 일치시켜야 한다.

**Final Answer를 생성할 수 없는 상황.** 질문에 답할 충분한 정보가 없는데 사용 가능한 Tool로는 가져올 수 없으면 루프를 돈다. Tool 중 하나가 "충분한 정보를 가져오지 못하면 그 사실을 명시적으로 반환"하도록 만들면 에이전트가 중단 조건을 찾는다.

**프롬프트에 종료 조건이 불명확할 때.** ReAct 프롬프트는 `Final Answer:`로 끝나도록 유도하는데, 시스템 프롬프트에 다른 규칙이 충돌하면 LLM이 Final Answer를 생성하지 않는다.

시스템 프롬프트에 종료 조건을 명시하면 루프가 줄어든다:

```python
system_message = """당신은 도움이 되는 어시스턴트다.
주어진 Tool로 충분한 정보를 얻으면 Final Answer를 반환한다.
Tool 결과가 충분하지 않거나 오류가 계속 발생하면,
현재까지 얻은 정보로 최선의 답변을 Final Answer로 반환한다."""
```

## LangSmith 없이 에이전트 중간 스텝 디버깅

`verbose=True`는 stdout에 출력하지만 프로그래밍적으로 처리하기 어렵다. 중간 스텝을 실제로 다루려면 `return_intermediate_steps=True`를 쓴다.

```python
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    return_intermediate_steps=True,
    verbose=True,
)

result = executor.invoke({"input": "현재 서울 날씨를 알려줘"})

print(result["output"])

for step in result["intermediate_steps"]:
    action, observation = step
    print(f"Tool: {action.tool}")
    print(f"Input: {action.tool_input}")
    print(f"Output: {observation}")
    print("---")
```

`intermediate_steps`는 `(AgentAction, observation)` 튜플의 리스트다. `AgentAction`에는 `tool`, `tool_input`, `log`(LLM이 생성한 원문)가 들어있다.

실시간으로 보려면 `astream_events`를 쓴다:

```python
async for event in executor.astream_events(
    {"input": "서울 날씨는?"},
    version="v1"
):
    kind = event["event"]
    if kind == "on_tool_start":
        print(f"Tool 시작: {event['name']}, 입력: {event['data']['input']}")
    elif kind == "on_tool_end":
        print(f"Tool 종료: {event['name']}, 결과: {event['data']['output']}")
    elif kind == "on_chat_model_stream":
        print(event["data"]["chunk"].content, end="", flush=True)
```

가장 직접적인 방법은 `callbacks`를 사용하는 거다. LLM에 어떤 프롬프트가 들어가는지까지 볼 수 있다:

```python
from langchain.callbacks.base import BaseCallbackHandler

class DebugCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print(f"=== LLM 호출 ===")
        print(prompts[0][-500:])  # 마지막 500자만

    def on_tool_start(self, serialized, input_str, **kwargs):
        print(f"=== Tool 호출: {serialized['name']} ===")
        print(f"입력: {input_str}")

    def on_tool_end(self, output, **kwargs):
        print(f"=== Tool 결과 ===")
        print(output[:200])  # 처음 200자만

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[DebugCallback()],
)
```

루프가 예상과 다르게 동작할 때는 `on_llm_start`의 프롬프트 내용을 보는 게 핵심이다. 이전 Observation들이 어떻게 누적되는지, Tool 설명이 실제로 어떻게 전달되는지 거기서 다 보인다.
