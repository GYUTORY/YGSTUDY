---
title: 온톨로지 (Ontology)
tags: [ai, ontology, knowledge-graph, rdf, owl, sparql, semantic-web]
updated: 2026-05-07
---

# 온톨로지

## 1. 온톨로지란 무엇인가

온톨로지는 어떤 도메인에 등장하는 개념들과 그 개념들 사이의 관계를 기계가 읽을 수 있는 형태로 정의한 명세다. 데이터베이스 스키마와 비슷해 보이지만 결정적인 차이가 있다. 스키마는 "이 테이블에는 이런 컬럼이 있다"를 기술하고, 온톨로지는 "사람은 동물이다", "주문은 반드시 고객을 가진다", "두 개의 부모는 자식 한 명을 공유할 수 있다"처럼 개념 자체의 의미와 제약을 기술한다.

처음 온톨로지를 접하면 ER 다이어그램을 어렵게 풀어 쓴 거 아닌가 싶다. 실제로 작은 도메인에서는 비슷해 보이기도 한다. 차이가 드러나는 지점은 추론(inference)이다. 온톨로지는 "철수는 사람이다", "사람은 포유류다"라는 두 사실을 입력하면 "철수는 포유류다"를 자동으로 도출한다. 관계형 DB는 이런 추론을 안 한다. 조인 결과가 사실의 전부고, 명시되지 않은 건 모른다.

### 1.1 등장 배경

온톨로지는 시맨틱 웹(Semantic Web) 흐름에서 자리 잡았다. 2000년대 초 W3C가 RDF, OWL을 표준화한 이유는 단순했다. 웹 페이지의 텍스트는 사람만 이해하고 기계는 못 읽는다. URL로 연결된 데이터에 의미를 붙여 기계가 추론하게 만들자는 게 시작이었다.

당시 기대만큼 웹 전반에 퍼지진 않았다. 하지만 도메인 지식이 복잡한 분야 — 의료, 생물정보학, 금융 규제, 항공우주 — 에서는 자리를 잡았다. 최근에는 LLM과 RAG가 보급되면서 다시 주목받는다. LLM이 환각을 일으키지 않게 하려면 검증된 지식 구조가 필요하고, 그 후보로 온톨로지가 다시 거론된다.

### 1.2 스키마와 온톨로지의 차이

```
관계형 스키마:
  Customer (id PK, name, email)
  Order    (id PK, customer_id FK, amount)

온톨로지:
  Customer는 Person의 하위 개념이다
  Order는 반드시 정확히 1명의 Customer를 가진다 (cardinality)
  Customer가 가진 Order 수는 Customer.lifetime_value와 양의 상관 (관계 정의)
  VIPCustomer는 Customer 중 lifetime_value > 10000인 것 (분류 규칙)
```

스키마에서 "VIP 고객"은 애플리케이션 코드의 if 조건이거나 뷰 쿼리다. 온톨로지에서는 분류 규칙 자체가 모델의 일부다. 새 고객을 입력하면 추론기가 알아서 VIPCustomer로 분류한다.

## 2. 클래스, 속성, 관계 모델링

온톨로지의 기본 구성 요소는 세 가지다. 클래스(Class), 인스턴스(Individual), 속성(Property). 클래스는 개념의 집합, 인스턴스는 개별 객체, 속성은 인스턴스가 가진 데이터나 다른 인스턴스와의 관계를 표현한다.

### 2.1 클래스 계층

클래스는 트리 또는 DAG 형태로 계층을 이룬다. `subClassOf`로 상속 관계를 만든다.

```
Thing
├── LivingThing
│   ├── Animal
│   │   ├── Mammal
│   │   │   ├── Human
│   │   │   └── Dog
│   │   └── Bird
│   └── Plant
└── Artifact
    ├── Vehicle
    └── Building
```

여기서 주의할 점이 있다. 클래스 계층을 짤 때 "is-a" 관계만 써야 한다. "구성된다"나 "가진다"를 subClassOf로 표현하면 추론이 망가진다. 자동차는 바퀴를 가지지만 바퀴의 하위 클래스가 아니다. 이걸 헷갈리면 나중에 디버깅이 지옥이 된다.

### 2.2 속성

속성은 두 종류다.

- **DataProperty**: 인스턴스가 가진 값. 이름, 나이, 가격 같은 리터럴.
- **ObjectProperty**: 인스턴스 사이의 관계. 소유한다, 작성했다, 부모다 같은 연결.

```
:Person     a owl:Class .
:hasName    a owl:DataProperty ;
            rdfs:domain :Person ;
            rdfs:range  xsd:string .

:hasParent  a owl:ObjectProperty ;
            rdfs:domain :Person ;
            rdfs:range  :Person .
```

`domain`은 속성이 시작되는 클래스, `range`는 속성이 가리키는 클래스 또는 데이터 타입이다. 도메인과 레인지를 잘못 잡으면 추론기가 엉뚱한 결과를 낸다. 예를 들어 `:hasAuthor`의 도메인을 `:Book`으로만 잡았다가 나중에 논문 데이터를 넣으면, 추론기가 "이 논문은 책이다"라고 결론 내린다. 도메인은 좁히지 말고 공통 상위 클래스(Document)로 잡는 게 안전하다.

### 2.3 제약(Restriction)

OWL은 클래스의 멤버가 만족해야 할 제약을 표현한다. 카디널리티, 값 제한, 필수 관계 같은 것들.

```
:Order owl:equivalentClass [
    a owl:Restriction ;
    owl:onProperty :hasCustomer ;
    owl:cardinality 1
] .
```

이 제약은 "주문은 정확히 한 명의 고객을 가진다"를 의미한다. 일반 DB의 NOT NULL 제약과 비슷하지만, 추론기는 여기서 한 단계 더 간다. 만약 어떤 인스턴스에 고객이 없으면? 관계형 DB는 "유효하지 않은 데이터"라고 거부한다. 온톨로지는 OWA(Open World Assumption) 때문에 "아직 모르는 고객이 어디엔가 있을 것"이라고 가정한다. 이 차이가 실무에서 사람을 자주 헷갈리게 한다.

## 3. RDF, OWL, SPARQL

이 셋은 온톨로지를 다룰 때 거의 항상 같이 등장한다. 역할이 다르다.

### 3.1 RDF — 데이터 표현

RDF(Resource Description Framework)는 사실을 (subject, predicate, object) 트리플로 표현한다.

```turtle
@prefix : <http://example.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

:alice  foaf:name   "Alice" .
:alice  foaf:knows  :bob .
:bob    foaf:name   "Bob" .
:bob    foaf:age    30 .
```

각 줄이 하나의 트리플이다. 주어와 술어는 URI로 식별하고 목적어는 URI나 리터럴이다. URI를 쓰는 이유는 전 세계에서 유일한 식별자를 보장하기 위해서다. `:alice`는 짧게 보이지만 실제로는 `http://example.org/alice`다.

RDF는 직렬화 포맷이 여러 개다. Turtle, RDF/XML, JSON-LD, N-Triples. 사람이 읽기 편한 건 Turtle이고, 웹 API에서 자주 쓰는 건 JSON-LD다. 같은 그래프를 다른 포맷으로 표현할 뿐이라 변환은 자유롭다.

### 3.2 OWL — 의미 표현

OWL(Web Ontology Language)은 RDF 위에 의미와 제약을 얹는다. 클래스, 속성, 카디널리티, 동등성, 분리(disjoint), 함수형 속성 같은 개념을 표준화한 어휘로 제공한다.

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix : <http://example.org/> .

:Person   a owl:Class .
:Employee a owl:Class ;
          rdfs:subClassOf :Person .

:hasManager a owl:ObjectProperty ;
            rdfs:domain :Employee ;
            rdfs:range  :Employee ;
            a owl:FunctionalProperty .
```

`FunctionalProperty`는 "한 인스턴스에 대해 이 속성이 가질 수 있는 값은 최대 1개"라는 의미다. 직원의 매니저는 한 명이라는 제약을 넣은 셈이다.

OWL은 표현력에 따라 OWL Lite, OWL DL, OWL Full로 나뉜다. 보통 실무에서는 OWL DL을 쓴다. Description Logic 기반이라 추론이 결정 가능(decidable)하다. OWL Full은 표현력이 가장 크지만 추론이 끝나지 않을 수 있어 위험하다.

### 3.3 SPARQL — 질의

SPARQL은 RDF 그래프를 질의하는 SQL 같은 언어다.

```sparql
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX :     <http://example.org/>

SELECT ?name ?friendName WHERE {
    ?person foaf:name ?name .
    ?person foaf:knows ?friend .
    ?friend foaf:name ?friendName .
    FILTER(?name = "Alice")
}
```

SQL과 다른 점은 조인이 없다는 것이다. 트리플 패턴을 나열하면 변수 바인딩으로 자연스럽게 연결된다. 같은 변수가 여러 패턴에 나오면 그 자리는 같은 값이어야 한다.

추론이 켜진 SPARQL 엔드포인트에 질의하면 명시되지 않은 사실도 매칭된다. 예를 들어 트리플에 "Alice는 Employee", "Employee는 Person의 하위 클래스"만 있어도 `?p a :Person` 질의에 Alice가 잡힌다. 이게 SPARQL의 강점이자 함정이다. 결과가 갑자기 늘어나는 이유를 모르고 디버깅하다 보면 시간을 한참 잡아먹는다. 추론을 켤지 끌지는 항상 의식하고 써야 한다.

```sparql
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX :     <http://example.org/>

SELECT ?employee ?manager WHERE {
    ?employee a :Employee .
    ?employee :hasManager ?manager .
}
```

이 질의는 트리플 스토어에 따라 다르게 동작한다. 추론을 켜면 `:Employee`의 하위 클래스(`:Engineer`, `:Manager` 등) 인스턴스도 결과에 포함된다. 끄면 정확히 `:Employee`로 선언된 것만 나온다.

## 4. 온톨로지와 지식 그래프의 차이

이 둘을 같은 말로 쓰는 사람도 있고 다르다고 우기는 사람도 있다. 둘 다 그래프 구조로 사실을 표현하지만 강조점이 다르다.

| 구분 | 온톨로지 | 지식 그래프 |
|------|----------|-------------|
| 주된 관심사 | 개념과 관계의 정의(스키마) | 인스턴스와 사실의 축적(데이터) |
| 표현력 | 풍부한 제약·분류·추론 | 단순 트리플이 일반적 |
| 규모 | 수천~수만 클래스 수준 | 수억~수십억 트리플 |
| 추론 | OWL 기반 자동 추론 | 보통 안 함, 또는 제한적 |
| 대표 사례 | SNOMED CT, FOAF, Schema.org | Google KG, Wikidata, DBpedia |

거칠게 말하면 온톨로지는 "스키마"고 지식 그래프는 "스키마 + 데이터"다. 지식 그래프 위에 온톨로지가 얹히는 구조라고 봐도 된다. Wikidata는 가벼운 온톨로지(클래스, 속성 정의)와 거대한 데이터(수십억 트리플)를 같이 가지고 있다.

실무에서는 둘을 분리해서 다뤄야 한다. 스키마(온톨로지)는 자주 안 바뀌고 변경에 신중해야 한다. 데이터(지식 그래프)는 매일 들어오고 빠진다. 같은 저장소에 넣더라도 변경 정책은 분리해서 관리한다. 이걸 안 하면 스키마 변경 한 번에 데이터 수억 건이 무효화되는 사고가 난다.

## 5. AI/RAG에서의 온톨로지

LLM은 텍스트를 잘 다루지만 정확한 도메인 지식을 보장하진 못한다. 환각이 자주 발생하고, 도메인 용어를 일관되게 쓰지 못한다. 여기서 온톨로지가 보조 역할을 한다.

### 5.1 일반 RAG의 한계

벡터 검색 기반 RAG는 텍스트 유사도로 청크를 가져온다. 의미가 가까운 문서를 잘 찾지만, 구조적 추론이 약하다.

```
질문: "지난 분기 매출이 가장 큰 고객이 추천한 다른 고객들의 평균 LTV는?"

벡터 검색:
  "매출 큰 고객", "추천", "LTV" 관련 문서 청크를 가져옴
  → LLM이 청크에서 답을 추출하려 하지만, 정확한 계산은 어려움
  → 환각 발생 가능
```

이건 문서 검색이 아니라 그래프 순회 + 집계 문제다. 온톨로지로 모델링된 지식 그래프 위에서 SPARQL 쿼리를 돌리면 정확한 답이 나온다.

### 5.2 GraphRAG, KG-RAG 패턴

최근 연구와 도구들이 이 빈틈을 메우려 한다. 보통 다음 구조를 띤다.

```
사용자 질문
    │
    ▼
LLM이 질문 의도 파악 → SPARQL/Cypher 쿼리 생성
    │
    ▼
지식 그래프 질의 → 정확한 사실 집합 획득
    │
    ▼
사실 + 원본 문서 청크를 LLM 컨텍스트에 주입
    │
    ▼
최종 답변 생성
```

핵심은 "구조화된 답"과 "비구조화된 설명"을 합치는 것이다. 그래프는 정확한 숫자와 관계를 주고, 문서는 맥락과 자연어 설명을 준다. LLM은 두 입력을 조합해서 답한다.

### 5.3 온톨로지가 LLM 환각을 줄이는 지점

LLM이 자주 틀리는 영역을 정리하면 이렇다.

- 동의어와 표기 불일치: "심근경색", "MI", "myocardial infarction" 처리
- 계층 관계: "약 X는 항생제다" → "약 X는 박테리아 감염에 쓰인다" 추론
- 명시적 제약: "이 약은 임신부 금기" 같은 안전성 규칙

이 셋 모두 온톨로지로 명시할 수 있다. LLM에 시스템 프롬프트로 "온톨로지에 정의된 사실만 답변에 사용해라"고 지시하고, RAG 단계에서 그래프 질의 결과를 컨텍스트에 넣으면 환각이 눈에 띄게 줄어든다. 의료, 법률처럼 사실 정확도가 중요한 분야에서 이 조합을 쓴다.

### 5.4 LLM으로 온톨로지를 만드는 시도

거꾸로, LLM에게 텍스트를 주고 온톨로지를 생성하게 하는 시도도 활발하다. 결과는 절반의 성공이다. LLM은 클래스와 속성 후보를 빠르게 뽑지만, 일관성과 정밀성이 떨어진다. 같은 개념을 두 번 다른 이름으로 만들거나, 클래스 계층이 뒤죽박죽이 되거나, "is-a"와 "part-of"를 섞는다.

실무에서는 LLM을 첫 초안 생성에만 쓰고, 도메인 전문가가 검토·수정하는 워크플로가 안전하다. 완전 자동 생성은 아직 위험하다.

## 6. 실무에서 겪는 문제와 해결법

이론적으로는 온톨로지가 깔끔해 보이지만 실제로 운영하면 꽤 다양한 문제가 생긴다.

### 6.1 스키마 진화

온톨로지는 한번 만들면 끝이 아니다. 도메인이 바뀌면 클래스와 속성을 추가, 변경, 삭제해야 한다. 문제는 기존 데이터와의 호환성이다.

DB 마이그레이션은 ALTER TABLE이 잘 정의돼 있다. 온톨로지는 그런 표준이 약하다. 클래스를 분리하거나 두 개를 합칠 때 어떻게 트리플을 옮길지 매번 결정해야 한다.

겪은 사례를 정리하면 이렇다.

- **클래스 분리**: `:Customer`를 `:Individual`과 `:Corporate`로 나눠야 했다. 기존 인스턴스를 둘 중 어디에 분류할지 규칙을 만들고, SPARQL UPDATE로 옮겼다. 분류가 모호한 인스턴스는 따로 큐에 넣어 사람이 검토했다.
- **속성 통합**: `:hasEmail`과 `:contactEmail`이 같이 있던 걸 `:hasEmail`로 통일했다. CONSTRUCT 쿼리로 양쪽 트리플을 모아 새 트리플을 만들고, 옛 트리플을 삭제했다.
- **클래스 삭제**: 안 쓰는 클래스를 지웠더니 그 클래스를 참조하던 다른 온톨로지가 깨졌다. 외부 영향도까지 확인해야 한다.

이런 변경을 매번 SPARQL UPDATE로 손으로 짜면 실수가 잦다. 온톨로지에도 마이그레이션 도구가 필요하다. ROBOT 같은 도구가 OWL 변경을 스크립트화해 주지만, 아직 DB 마이그레이션만큼 성숙하진 않았다. 그래서 변경 이력을 git처럼 기록하고, 환경별로 동일한 변경 스크립트를 돌리는 사내 도구를 만드는 회사가 많다.

### 6.2 추론 비용

OWL 추론은 무겁다. 데이터가 늘어나면 추론 시간이 비선형으로 증가한다. 트리플 1억 개를 가진 그래프에서 OWL DL 전체 추론을 돌리면 몇 시간씩 걸리는 경우가 흔하다.

해결 방법은 표현력을 깎는 것이다. OWL DL을 다 쓸 일은 거의 없다. 실무에서는 OWL 2 RL 프로파일이 자주 선택된다. 룰 기반으로 추론을 단순화해서 대규모 데이터에서도 빠르게 동작한다. 표현력은 줄지만 SPARQL UPDATE처럼 점진적 추론이 가능해서 대규모 운영에 맞다.

또 한 가지는 추론을 항상 켜지 않는 것이다. 데이터를 적재할 때 한 번 풀 추론을 돌려 결과를 트리플 스토어에 저장하고, 질의 시에는 추론 없이 단순 패턴 매칭만 한다. 이걸 머티리얼라이제이션(materialization)이라고 한다. 변경이 자주 없으면 효과가 크다.

```
일반 추론(질의 시 추론):
  매 SPARQL 쿼리마다 추론기가 돌아감 → 느림
  데이터 변경에 즉시 반영됨

머티리얼라이제이션:
  로딩 후 한 번 풀 추론 → 결과 트리플 저장
  쿼리는 빠름
  데이터 변경 시 재계산 또는 증분 업데이트 필요
```

증분 업데이트는 어렵다. 트리플 하나를 추가했을 때 추론으로 새로 도출되는 사실이 무엇인지, 트리플 하나를 삭제했을 때 어떤 사실이 더 이상 성립 안 하는지 추적해야 한다. 이걸 잘 처리하는 트리플 스토어는 비싸다. RDFox, GraphDB, Stardog 같은 상용 제품이 잘한다. 오픈소스인 Apache Jena, Blazegraph는 가능하지만 직접 운영 부담이 있다.

### 6.3 매핑 충돌

여러 출처에서 데이터를 모아 하나의 그래프로 합칠 때 충돌이 생긴다. 같은 개념을 다른 이름으로 표현하거나, 같은 이름을 다른 의미로 쓴다.

예를 들어 회사 A의 온톨로지는 `:Customer`가 "결제를 한 번이라도 한 사람"이고, 회사 B의 온톨로지는 `:Customer`가 "계정을 만든 사람"이다. URI는 같아 보이지만 의미는 다르다. 그냥 합치면 일관성이 깨진다.

해결 방법은 두 가지가 있다.

- **owl:sameAs로 인스턴스 매핑**: 두 인스턴스가 같은 객체를 가리킨다고 명시한다. 추론기가 두 URI를 동일시한다.
- **상위 온톨로지(upper ontology) 도입**: 양쪽 위에 더 일반적인 개념(`:Buyer`, `:AccountHolder`)을 만들고 각각을 그 하위로 둔다. 의미 차이를 명시적으로 보존한다.

`owl:sameAs`는 강력하지만 위험하다. 한 번 같다고 선언하면 추론기가 모든 속성을 양쪽에 동일하게 적용한다. 실수로 다른 객체를 같다고 묶으면 트리플이 마구 잘못 생성된다. 합치기 전에 매칭 신뢰도를 측정해야 한다. 보통 임계값(예: 95% 이상)을 넘는 경우만 자동 매칭하고, 나머지는 사람이 검토한다.

또 하나의 함정은 라이선스다. 외부 온톨로지(Schema.org, FOAF, DBpedia)를 가져다 쓸 때 그쪽 라이선스에 묶인다. 사내 데이터와 합쳐 외부에 공개하려면 사전에 확인이 필요하다.

### 6.4 너무 깊은 클래스 계층

처음 모델링할 때 욕심이 생긴다. 가능한 모든 분류를 클래스로 만든다. `:Animal → :Mammal → :Carnivore → :Felidae → :Cat → :DomesticCat → :ShortHairedCat → ...` 이렇게 깊어지면 추론도 느려지고 사람도 헷갈린다.

경험상 클래스 계층은 5~6 단계를 넘기지 않는 게 좋다. 그보다 깊으면 데이터 속성으로 표현하는 게 낫다. "고양이의 종은 무엇인가?"를 클래스로 풀지 말고 `:species` 속성으로 풀어라.

## 7. Protégé로 온톨로지 만들기

Protégé는 스탠퍼드에서 만든 무료 온톨로지 편집기다. 실무에서 가장 많이 쓰이는 도구 중 하나다. GUI로 클래스, 속성, 인스턴스를 편집하고 OWL 파일로 저장한다.

### 7.1 간단한 도서관 온톨로지

도서관 도메인을 예로 들어 보자. 책, 저자, 출판사, 대출 같은 개념을 모델링한다.

설치는 [protege.stanford.edu](https://protege.stanford.edu/)에서 받는다. 데스크톱 버전과 웹 버전이 있고, 데스크톱 버전이 기능이 풍부하다.

새 프로젝트를 열고 클래스 계층을 만든다.

```
Thing
├── Document
│   ├── Book
│   ├── Magazine
│   └── Thesis
├── Person
│   ├── Author
│   └── Member
├── Organization
│   └── Publisher
└── Loan
```

`Author`와 `Member`는 둘 다 사람이지만, 한 사람이 둘 다 될 수 있다. 그래서 `Author`와 `Member`를 disjoint(분리) 선언하면 안 된다. 모델링 단계에서 자주 실수하는 부분이다. "한 사람이 동시에 둘일 수 있는가?"를 항상 자문해야 한다.

다음으로 속성을 추가한다.

```
ObjectProperty:
  hasAuthor    domain Book      range Author
  hasPublisher domain Document   range Publisher
  borrows      domain Member    range Book
  borrowedIn   domain Loan      range Book

DataProperty:
  hasTitle    domain Document   range xsd:string
  hasISBN     domain Book      range xsd:string
  publishedIn domain Document   range xsd:gYear
```

제약을 건다. 책은 ISBN이 정확히 하나여야 한다.

```
Book SubClassOf:
    hasISBN exactly 1 xsd:string
```

Protégé의 추론기 탭에서 `Pellet`이나 `HermiT`를 선택하고 실행하면, 명시되지 않은 사실이 도출된다. 인스턴스를 몇 개 넣고 추론을 돌려 보면 감이 온다.

```
Individuals:
  :book1   a :Book ;
           :hasTitle "Refactoring" ;
           :hasISBN "9780201485677" ;
           :hasAuthor :fowler .
  :fowler  a :Author ;
           :hasName "Martin Fowler" .
```

추론기가 `:fowler`를 `:Person`으로도 분류한다(상위 클래스라서). `:book1`은 `:Document`로도 분류된다.

### 7.2 SPARQL 쿼리로 검증

Protégé의 SPARQL 탭에서 직접 질의할 수 있다.

```sparql
PREFIX :    <http://example.org/library#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:<http://www.w3.org/2000/01/rdf-schema#>

SELECT ?title ?authorName WHERE {
    ?book   a :Book ;
            :hasTitle ?title ;
            :hasAuthor ?author .
    ?author :hasName ?authorName .
}
```

추론을 켰을 때와 껐을 때 결과가 다르다. 끈 상태에서는 명시적으로 `:hasName`이 선언된 저자만 나온다. 켠 상태에서는 추론으로 도출된 트리플도 매칭된다.

### 7.3 OWL 파일 출력과 운영

Protégé에서 만든 온톨로지는 `.owl` 파일로 저장된다. 실제로는 RDF/XML이나 Turtle 형식이다. 이 파일을 트리플 스토어에 로드하면 운영 환경에서 사용할 수 있다.

```bash
# Apache Jena Fuseki에 로드
curl -X POST -H "Content-Type: text/turtle" \
     --data-binary @library.ttl \
     http://localhost:3030/library/data
```

GraphDB, Stardog 같은 상용 제품도 비슷하게 REST API로 적재한다. 적재 후에는 SPARQL 엔드포인트가 열린다. 애플리케이션은 이 엔드포인트에 SPARQL 쿼리를 던져 데이터를 가져온다.

운영을 시작하면 Protégé는 점차 안 쓰게 된다. 스키마 변경이 잦지 않은 단계로 가면 git에 OWL 파일을 두고 코드 리뷰로 변경을 관리하는 게 더 안전하다. Protégé GUI에서 잘못 클릭해 의도치 않은 axiom이 들어가는 사고를 막기 위해서다. 텍스트 diff로 변경 사항을 보는 게 훨씬 명확하다.

## 8. 실제 사례 — 의료 도메인

온톨로지가 가장 깊게 쓰이는 영역 중 하나가 의료다. SNOMED CT는 35만 개 이상의 임상 개념을 가진 거대 온톨로지로, 영국 NHS, 미국 의료기관, 한국의 일부 병원 시스템에서 표준으로 쓰인다.

진료 기록에 "심근경색"이라고 쓰면 SNOMED CT 코드 `22298006`이 매핑된다. 이 코드는 "Acute myocardial infarction"의 하위 개념이고, 그 위로 "Heart disease", "Cardiovascular disorder" 같은 상위 개념과 연결된다. 환자 데이터에 코드만 넣어 두면 "심혈관 질환을 가진 모든 환자"를 SPARQL 한 줄로 찾을 수 있다. 텍스트 매칭으로는 "심근경색", "MI", "AMI" 같은 표기 차이를 다 잡기 어렵지만, 온톨로지 코드는 표기와 무관하다.

LLM 기반 의료 챗봇이 여기에 SNOMED CT를 연결하면 환각이 줄어든다. 환자가 "가슴이 아파요"라고 하면 LLM이 후보 증상을 SNOMED CT 코드로 매핑하고, 그 코드의 상위/하위 관계를 이용해 관련 검사와 진단명을 추천한다. 텍스트 유사도만 쓰는 것보다 정확하다.

문제는 비용이다. SNOMED CT 자체가 라이선스가 비싸고(국가별로 다름), 추론을 풀로 돌리면 매우 느리다. 그래서 실무에서는 필요한 부분만 추출(subset)해서 쓴다. 전체 35만 개를 다 안 쓰고, 자기 도메인(예: 심혈관)에 관련된 1만 개만 가져다 쓴다.

## 9. 정리

온톨로지는 도메인 지식을 기계가 추론할 수 있는 형태로 명세하는 기술이다. 클래스, 속성, 제약으로 의미를 표현하고, RDF로 데이터를 적재하고, OWL로 의미를 정의하고, SPARQL로 질의한다.

지식 그래프와 비슷하지만 강조점이 다르다. 지식 그래프는 데이터의 양, 온톨로지는 의미의 정확성에 무게를 둔다. 둘은 같이 쓴다.

LLM과 RAG가 보편화되면서 온톨로지가 다시 주목받는다. 환각을 줄이고 도메인 지식을 보장하는 보조 장치로 유용하다. 다만 모든 시스템에 필요한 건 아니다. 도메인이 단순하고 텍스트 검색만으로 충분하면 굳이 도입할 필요가 없다. 의료, 금융, 법률처럼 사실 정확성이 중요한 분야, 또는 여러 출처의 데이터를 통합해야 하는 분야에서 온톨로지의 가치가 커진다.

도입을 결정했다면 작게 시작해라. 처음부터 거대한 클래스 계층을 만들지 말고, 핵심 개념 20~30개로 시작해서 운영하면서 키워라. 스키마 진화 비용이 생각보다 크기 때문에, 변경 정책과 머티리얼라이제이션 전략을 운영 초기부터 같이 설계해야 한다.

## 참고 자료

- [W3C OWL 2 Web Ontology Language Primer](https://www.w3.org/TR/owl2-primer/)
- [W3C SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/)
- [Protégé](https://protege.stanford.edu/)
- [Apache Jena](https://jena.apache.org/)
- [SNOMED CT](https://www.snomed.org/)
- [Wikidata](https://www.wikidata.org/)
