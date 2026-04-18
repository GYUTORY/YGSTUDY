---
title: Graph Traversal (그래프 탐색 - DFS/BFS)
tags: [algorithm, graph, dfs, bfs, topological-sort, cycle-detection]
updated: 2026-04-18
---

# Graph Traversal (그래프 탐색 - DFS/BFS)

## 들어가며

그래프 탐색은 알고리즘 문제에서 가장 흔하지만, 실무로 들어오면 오히려 더 자주 마주친다. 팔로우 관계, 조직도, 권한 상속, 빌드 의존성, 워크플로우 실행 순서, 마이크로서비스 호출 트레이싱. 이런 구조를 다룰 때마다 결국 DFS 아니면 BFS다. 알고리즘 공부할 때는 "노드 1번부터 시작"이라는 깔끔한 입력만 봤지만, 실무에서는 노드가 수백만 개씩 쌓인 DB에서 "이 사용자와 연결된 모든 사용자"를 뽑아야 하는 상황이 온다.

DFS/BFS 자체는 코드가 짧다. 재귀 함수 하나, 큐 하나면 끝난다. 그런데 실무에서 이걸 틀리는 이유는 대부분 구현 자체가 아니라 주변 문제에서 터진다. 그래프 표현 방식을 잘못 골라서 메모리가 터지거나, 재귀 깊이가 깊어져서 스택 오버플로가 나거나, 방문 처리 타이밍을 한 줄 잘못 써서 같은 노드를 여러 번 큐에 밀어 넣는다. 이 문서는 DFS/BFS의 기본보다는 이런 함정에 초점을 맞춘다.

## 그래프를 메모리에 올리는 두 가지 방법

그래프 알고리즘을 짜기 전에 먼저 결정해야 할 게 있다. 그래프를 어떻게 표현할 것인가. 알고리즘 책에는 인접 행렬(adjacency matrix)과 인접 리스트(adjacency list) 두 가지가 나온다. 실무에서는 거의 인접 리스트만 쓰는데, 왜 그런지 이해해 두면 나중에 "이 케이스에서는 행렬이 낫겠다"는 판단도 할 수 있다.

### 인접 행렬

N개의 노드가 있으면 N×N 크기의 2차원 배열을 만든다. `matrix[i][j]`가 1이면 i에서 j로 가는 간선이 있고, 0이면 없다. 가중치가 있으면 1 대신 가중치 값을 넣는다.

```python
# 노드 5개, 간선 (0,1), (0,2), (1,3), (2,4)
matrix = [
    [0, 1, 1, 0, 0],
    [0, 0, 0, 1, 0],
    [0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
]
```

장점은 "i에서 j로 가는 간선이 있는가?"를 O(1)에 확인할 수 있다는 점이다. 단점은 메모리다. 노드가 10만 개면 10억 개의 칸이 필요하다. 간선이 실제로 10만 개밖에 없어도 배열은 10억 칸을 그대로 차지한다. 희소 그래프(sparse graph)에서는 낭비가 심하다.

실무에서 인접 행렬을 쓸 만한 경우는 노드 수가 수백 개 이하로 작고, 간선 존재 여부를 자주 조회해야 할 때다. 예를 들어 도시 간 거리 테이블이나 플로이드-워셜 알고리즘을 돌릴 때 정도다.

### 인접 리스트

각 노드마다 연결된 노드들의 리스트를 따로 저장한다. 딕셔너리나 배열의 배열로 구현한다.

```python
# 같은 그래프를 인접 리스트로
graph = {
    0: [1, 2],
    1: [3],
    2: [4],
    3: [],
    4: [],
}
```

메모리 사용량은 O(V + E)다. 노드 수와 간선 수의 합. 간선이 10만 개면 정말 10만 개 정도만 메모리를 쓴다. 대부분의 실무 그래프는 희소하다. 사용자 한 명이 전체 사용자와 다 연결되어 있진 않다. 친구가 많아야 몇백 명 수준이다. 그래서 인접 리스트가 거의 표준이다.

단점은 "i에서 j로 가는 간선이 있는가?"를 확인하려면 i의 리스트를 순회해야 한다는 점이다. 평균적으로 O(degree) 시간이 걸린다. 이게 문제가 되는 경우는 드물다. 간선 존재 조회가 빈번하면 `set`으로 바꿔서 O(1)로 만들 수도 있다.

### 선택 기준

노드 수가 수천 개를 넘기 시작하면 인접 행렬은 메모리가 부담된다. 실무에서는 거의 무조건 인접 리스트라고 보면 된다. 단, 간선 수가 V²에 가까운 밀집 그래프(dense graph)이고 간선 조회가 성능 병목이면 행렬이 나을 수 있다. 이건 드문 경우다.

## DFS: 재귀로 짤 것인가, 스택으로 짤 것인가

DFS는 "한 방향으로 끝까지 들어갔다가, 막히면 되돌아와서 다른 방향으로 간다"는 탐색이다. 자연스럽게 재귀로 표현된다. 코드가 짧고 직관적이라서 대부분 재귀로 먼저 작성한다.

```python
def dfs_recursive(graph, node, visited):
    visited.add(node)
    # 여기서 노드 처리
    for neighbor in graph[node]:
        if neighbor not in visited:
            dfs_recursive(graph, neighbor, visited)
```

이게 문제를 일으키는 순간은 그래프가 깊을 때다. 예를 들어 노드 10만 개가 일렬로 연결된 그래프를 생각해 보자. DFS가 10만 번 재귀 호출된다. Python의 기본 재귀 한계는 1000이다. 그 전에 `RecursionError`가 터진다.

`sys.setrecursionlimit(100000)`으로 한계를 늘릴 수 있지만, 이건 근본 해결이 아니다. Python 재귀는 프레임 하나당 메모리를 많이 쓰고, 한계를 무리하게 늘리면 프로세스 자체가 스택 오버플로로 죽을 수 있다. 실무 데이터는 예상보다 깊은 경우가 많다. 특히 포크처럼 체인 형태의 데이터(예: 계정 상속 구조, Git 커밋 히스토리)에서 쉽게 터진다.

### 반복 DFS로 전환하기

재귀 DFS를 명시적 스택을 쓰는 반복 DFS로 바꾸면 재귀 한계에서 자유로워진다.

```python
def dfs_iterative(graph, start):
    visited = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        # 여기서 노드 처리
        for neighbor in graph[node]:
            if neighbor not in visited:
                stack.append(neighbor)
    return visited
```

두 버전의 탐색 순서는 다를 수 있다. 재귀 DFS는 이웃 리스트의 앞쪽부터 먼저 들어가지만, 스택 기반 반복 DFS는 나중에 넣은 것부터 꺼내기 때문에 뒤쪽 이웃부터 방문한다. 순서를 맞추려면 이웃을 역순으로 스택에 넣으면 된다. 탐색 순서가 중요한 문제(예: 위상 정렬 결과 순서)에서는 이 차이를 염두에 두어야 한다.

실무에서는 재귀 깊이가 확실히 얕다는 보장이 없으면 처음부터 반복 DFS로 짠다. 깊이가 얕을 것 같아서 재귀로 짰다가, 운영 중 데이터가 쌓이면서 어느 날 갑자기 터지는 일이 자주 있다.

## BFS와 큐 기반 구현

BFS는 시작 노드에서 가까운 노드부터 차례로 방문한다. 가중치 없는 그래프에서 최단 경로를 찾을 때 기본적으로 쓰는 방법이다. 자료구조는 큐다.

```python
from collections import deque

def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        # 여기서 노드 처리
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
```

Python에서는 반드시 `collections.deque`를 써야 한다. 리스트를 써서 `list.pop(0)`을 호출하면 O(N)이라 전체 시간 복잡도가 O(V²)로 망가진다. `deque`는 양쪽 끝 삽입/삭제가 O(1)이다. 이걸 모르고 리스트로 큐를 구현한 코드를 실무에서도 가끔 본다.

## 방문 처리 타이밍: 큐에 넣을 때냐, 꺼낼 때냐

BFS에서 의외로 자주 틀리는 부분이 이거다. "방문했다"는 표시를 언제 하느냐. 두 가지 선택이 있다.

### 큐에 넣을 때 방문 처리

```python
visited = {start}
queue = deque([start])
while queue:
    node = queue.popleft()
    for neighbor in graph[node]:
        if neighbor not in visited:
            visited.add(neighbor)      # 큐에 넣기 전에 방문 처리
            queue.append(neighbor)
```

### 큐에서 꺼낼 때 방문 처리

```python
queue = deque([start])
visited = set()
while queue:
    node = queue.popleft()
    if node in visited:
        continue
    visited.add(node)                   # 꺼낼 때 방문 처리
    for neighbor in graph[node]:
        if neighbor not in visited:
            queue.append(neighbor)
```

결과만 보면 같은 노드를 다 방문하긴 한다. 그런데 두 방식은 성능과 정확성 면에서 차이가 있다.

꺼낼 때 방문 처리를 하면 같은 노드가 여러 번 큐에 들어갈 수 있다. 예를 들어 A가 B와 C를 가리키고, B와 C가 둘 다 D를 가리키면, D는 B를 처리할 때 한 번, C를 처리할 때 한 번, 이렇게 큐에 두 번 들어간다. 노드 수가 많고 간선이 빽빽한 그래프에서는 이게 O(V+E)가 아니라 O(E²)에 가까운 동작을 하게 만든다.

반대로 큐에 넣을 때 방문 처리를 하면 각 노드는 큐에 정확히 한 번만 들어간다. 거의 모든 상황에서 이 방식이 맞다.

꺼낼 때 방문 처리가 필요한 경우도 있다. 다익스트라(Dijkstra)처럼 우선순위 큐에서 더 짧은 경로가 나중에 들어올 수 있는 경우다. 이때는 꺼낼 때 "이 노드가 이미 더 짧은 거리로 처리됐는지"를 확인해야 한다. 하지만 일반적인 BFS/DFS에서는 큐/스택에 넣을 때 방문 처리하는 게 표준이다.

실무에서 이걸 틀리면 증상이 미묘하다. 결과는 맞는데 속도가 이상하게 느리다. 작은 테스트에서는 안 드러나고, 본 데이터에서 터진다. 코드 리뷰할 때 방문 처리 타이밍부터 확인하는 습관을 들이면 이런 버그를 쉽게 잡는다.

## BFS로 최단 경로 찾기

가중치 없는 그래프에서 시작점으로부터 각 노드까지의 최단 거리를 구할 때 BFS를 쓴다. 거리 배열을 하나 더 두면 된다.

```python
from collections import deque

def shortest_paths(graph, start):
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in dist:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)
    return dist
```

BFS는 "가까운 것부터 확장"이라는 성질 덕분에, 어떤 노드에 처음 도달했을 때의 거리가 곧 최단 거리다. 한 번 거리가 정해지면 다시 업데이트할 필요가 없다. 이게 성립하는 이유는 모든 간선의 비용이 1이라는 전제 때문이다. 간선마다 비용이 다르면 BFS는 맞지 않는다. 이때는 다익스트라를 써야 한다.

경로 자체(어떤 노드를 거쳐 왔는지)가 필요하면 `parent` 딕셔너리를 하나 더 둔다. 도착 노드에서 `parent`를 역으로 따라가서 경로를 재구성한다.

```python
parent = {start: None}
# BFS 순회 중 neighbor 방문할 때
parent[neighbor] = node

# 경로 재구성
def reconstruct_path(parent, target):
    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return path[::-1]
```

## 연결 요소 찾기

무방향 그래프에서 "서로 연결된 노드들의 집합"을 연결 요소(connected component)라고 한다. 실무에서는 사용자 그룹 분리, 네트워크 파티션 분석, 이상치 군집화 등에 쓴다. 모든 노드를 한 번씩 돌면서, 아직 방문하지 않은 노드에서 DFS/BFS를 시작한다. 한 번의 탐색으로 도달한 노드들이 하나의 연결 요소다.

```python
def connected_components(graph, nodes):
    visited = set()
    components = []
    for node in nodes:
        if node not in visited:
            component = []
            stack = [node]
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                component.append(cur)
                for neighbor in graph.get(cur, []):
                    if neighbor not in visited:
                        stack.append(neighbor)
            components.append(component)
    return components
```

실무에서 이 로직을 짤 때 자주 놓치는 게 "고립된 노드" 처리다. 간선이 하나도 없는 노드도 그 자체로 하나의 연결 요소다. DB에서 간선 테이블만 읽어서 인접 리스트를 만들면 고립 노드는 아예 누락된다. 노드 목록을 별도로 읽어서 모든 노드를 순회해야 한다.

## 위상 정렬

방향 그래프에서 "A가 B보다 먼저 와야 한다"는 순서를 모두 만족하는 선형 순서를 만드는 작업이 위상 정렬(topological sort)이다. 빌드 시스템의 태스크 순서, 강의 선수과목 처리, 작업 스케줄러의 의존성 해결, 마이그레이션 실행 순서에 쓴다.

두 가지 방식이 있다. Kahn 알고리즘(BFS 기반)과 DFS 기반 위상 정렬.

### Kahn 알고리즘

진입 차수(in-degree)가 0인 노드부터 꺼낸다. 꺼낸 노드와 연결된 간선을 제거하면서 새로 진입 차수가 0이 된 노드를 큐에 넣는다. 이게 반복되면 자연스럽게 위상 순서가 나온다.

```python
from collections import deque

def topological_sort(graph, nodes):
    in_degree = {node: 0 for node in nodes}
    for node in nodes:
        for neighbor in graph.get(node, []):
            in_degree[neighbor] += 1

    queue = deque([node for node in nodes if in_degree[node] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(nodes):
        raise ValueError("Cycle detected")
    return order
```

`len(order) != len(nodes)`라는 검사가 중요하다. 그래프에 사이클이 있으면 진입 차수가 0이 되지 않는 노드가 남는다. 이 경우 위상 정렬 자체가 불가능하다. Kahn 알고리즘은 이 검사로 자연스럽게 사이클 검출까지 같이 해 준다.

실무에서 위상 정렬을 돌렸는데 순서가 비어 있거나 노드 수가 맞지 않으면 십중팔구 사이클이다. 의존성 그래프에 순환이 생기는 건 팀에서 누군가 실수로 "A가 B를 참조하고, B가 A를 참조"하도록 만들었을 때다. 이런 상황을 감지만 해도 많은 운영 사고를 막는다.

### DFS 기반

후위 순회(post-order)로 DFS를 돌면서 방문이 끝난 노드를 스택에 쌓는다. 마지막에 스택을 뒤집으면 위상 순서가 나온다. 사이클 검출은 별도로 해야 하는데, 이 부분은 다음 절에서 다룬다.

## 사이클 검출

무방향 그래프와 방향 그래프의 사이클 검출 방법이 다르다. 이걸 구분 못 해서 틀리는 경우가 많다.

### 무방향 그래프

DFS 중에 "이미 방문한 노드"를 만났을 때, 그게 내가 방금 온 부모 노드가 아니면 사이클이다. 부모 노드면 그냥 왔던 길을 되짚는 것뿐이니까 사이클이 아니다.

```python
def has_cycle_undirected(graph, nodes):
    visited = set()

    def dfs(node, parent):
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor, node):
                    return True
            elif neighbor != parent:
                return True
        return False

    for node in nodes:
        if node not in visited:
            if dfs(node, None):
                return True
    return False
```

### 방향 그래프

방향 그래프에서는 부모-자식 개념이 다르다. "현재 DFS 경로에 포함된 노드"를 다시 만나면 사이클이다. 방문 완료된 다른 경로의 노드는 사이클이 아니다. 그래서 노드 상태를 세 가지로 나눠야 한다. 미방문(WHITE), 현재 탐색 중(GRAY), 탐색 완료(BLACK).

```python
def has_cycle_directed(graph, nodes):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in nodes}

    def dfs(node):
        color[node] = GRAY
        for neighbor in graph.get(node, []):
            if color[neighbor] == GRAY:
                return True
            if color[neighbor] == WHITE and dfs(neighbor):
                return True
        color[node] = BLACK
        return False

    for node in nodes:
        if color[node] == WHITE:
            if dfs(node):
                return True
    return False
```

방향 그래프에서 단순히 `visited` 하나만 쓰면, 두 개의 경로가 같은 노드로 수렴할 때 사이클이 아닌데도 사이클로 오인한다. 3색 구분이 핵심이다.

실무 예시를 하나 들면, 마이크로서비스 호출 관계를 방향 그래프로 그리고 사이클을 찾는 일이 있다. 서비스 A가 B를 호출하고 B가 C를, C가 다시 A를 호출하면 순환 의존이다. 이런 걸 자동으로 찾아 주는 린트 툴을 만들 때 이 3색 DFS를 쓴다.

## 이분 그래프 판정

이분 그래프(bipartite graph)는 노드를 두 그룹으로 나눴을 때, 모든 간선이 서로 다른 그룹 사이에만 있는 그래프다. 같은 그룹 안의 두 노드를 잇는 간선이 하나라도 있으면 이분 그래프가 아니다.

판정 방법은 BFS나 DFS로 색칠하기다. 시작 노드를 0번 색으로 칠하고, 이웃은 반대 색인 1번으로 칠한다. 이웃의 이웃은 다시 0번. 이렇게 번갈아 칠하다가, 이미 칠해진 이웃과 내 색이 같으면 이분 그래프가 아니다.

```python
from collections import deque

def is_bipartite(graph, nodes):
    color = {}
    for start in nodes:
        if start in color:
            continue
        color[start] = 0
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in graph.get(node, []):
                if neighbor not in color:
                    color[neighbor] = 1 - color[node]
                    queue.append(neighbor)
                elif color[neighbor] == color[node]:
                    return False
    return True
```

연결 요소가 여러 개면 각각 독립적으로 판정해야 한다. 위 코드에서 `for start in nodes` 루프가 이 역할을 한다. 한 연결 요소가 이분 그래프여도 다른 요소가 아니면 전체적으로는 이분 그래프가 아니다.

실무에서 이분 그래프 판정은 매칭 문제의 전처리로 자주 쓴다. 작업-사람 할당, 광고-슬롯 매칭 같은 문제는 본질적으로 이분 그래프 위의 매칭이다. 입력이 정말 이분 그래프인지를 먼저 검증해야 이후 매칭 알고리즘이 의미를 가진다.

## 실무에서 그래프 데이터를 다룰 때

알고리즘 문제는 그래프가 이미 메모리에 있다고 가정한다. 실무는 그 반대다. 데이터는 DB, 파일, 외부 API에 흩어져 있고, 이걸 메모리에 올리는 과정에서 대부분의 문제가 생긴다.

### 그래프 크기 파악부터

DFS/BFS를 짜기 전에 노드 수와 간선 수를 먼저 확인해야 한다. 노드 100만, 간선 1000만 짜리 그래프를 인접 리스트로 만들면 메모리가 수 GB를 넘길 수 있다. Python의 딕셔너리나 리스트는 오버헤드가 커서, 알고리즘 문제에서 보던 메모리 사용량보다 훨씬 크다.

DB에서 `SELECT * FROM edges`를 그냥 하면 수천만 행이 한 번에 올라와서 OOM이 난다. 청크로 나눠 읽거나, 인접 리스트를 증분 방식으로 쌓거나, 애초에 탐색 대상을 서브그래프로 제한해야 한다.

### 시작점 제한하기

전체 그래프를 다 탐색할 필요가 거의 없다. 대부분 "사용자 A로부터 N홉 안에 연결된 노드"처럼 서브그래프만 필요하다. 깊이 제한을 두면 탐색 범위가 극적으로 줄어든다.

```python
def bfs_limited(graph, start, max_depth):
    visited = {start: 0}
    queue = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited[neighbor] = depth + 1
                queue.append((neighbor, depth + 1))
    return visited
```

특히 소셜 그래프처럼 친구의 친구의 친구로 뻗어 나가면 노드 수가 기하급수적으로 불어난다. 6단계만 넘어도 대부분의 인구를 커버한다는 "6단계 분리" 이론이 실제로 맞다. 깊이 제한 없이 돌리면 사실상 전체 그래프를 탐색하게 된다.

### 지연 로딩

인접 리스트 전체를 메모리에 올리는 대신, 탐색하면서 필요한 노드의 이웃만 DB에서 꺼내는 방식이다. 노드당 한 번의 쿼리가 발생하니까 네트워크 왕복 비용이 누적된다. 탐색할 노드 수가 제한적일 때 유효하다.

```python
def bfs_lazy(get_neighbors, start, max_depth):
    visited = {start}
    queue = deque([(start, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        neighbors = get_neighbors(node)  # DB 쿼리
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
    return visited
```

쿼리가 많아지면 N+1 문제처럼 성능이 나빠진다. 배치로 이웃을 가져오거나 캐시를 적극적으로 써야 한다. 같은 노드의 이웃을 여러 번 물어볼 가능성이 있으면 LRU 캐시를 붙이는 게 현실적이다.

### DB에 저장된 그래프를 다룰 때

관계형 DB에 그래프를 저장하면 재귀 쿼리로 탐색해야 한다. PostgreSQL의 `WITH RECURSIVE`가 대표적이다. 코드로 BFS를 짜는 것과 DB 재귀 쿼리로 푸는 것 중 어느 게 나은지는 데이터 크기와 쿼리 빈도에 달렸다.

일반적으로 수십~수백 노드 수준의 얕은 탐색은 DB 재귀 쿼리가 깔끔하고 빠르다. 네트워크 왕복이 한 번으로 끝나기 때문이다. 깊이가 깊거나 노드가 많으면 애플리케이션 메모리에 올려서 처리하는 게 빠르다. 진짜로 큰 그래프라면 Neo4j 같은 그래프 DB를 쓰거나, 주기적으로 덤프를 만들어서 오프라인 처리하는 파이프라인을 세우는 게 맞다.

### 동시성 문제

그래프가 계속 변하는 상황에서 탐색을 돌리면 스냅샷 시점이 중요하다. 탐색 중간에 간선이 추가되거나 노드가 삭제되면 결과가 불일치해진다. 트랜잭션으로 묶거나, 스냅샷 타임스탬프를 기준으로 일관된 뷰를 만든 뒤 탐색해야 한다.

라이브 서비스에서 그래프를 다룰 때 자주 마주치는 실수다. 분석 쿼리 돌리는 도중에 데이터가 바뀌면서, 어떤 노드는 보였다 안 보였다 한다. 디버깅할 때 재현이 안 돼서 더 골치 아프다.

## 정리

DFS와 BFS는 코드가 짧다. 하지만 실제 쓸 때 틀리는 지점은 코드 자체가 아니라 주변 조건들이다. 그래프 표현을 뭘로 쓸지, 재귀 깊이가 감당 가능한지, 방문 처리 타이밍을 언제로 둘지, 방향 그래프의 사이클 검출에서 3색을 썼는지. 이런 부분들이 실무에서 그래프 코드를 안정적으로 돌리느냐 마느냐를 가른다.

가장 자주 겪는 함정 세 가지만 꼽자면, 재귀 DFS로 짰다가 데이터가 깊어져서 스택 오버플로, 방문 처리를 꺼낼 때 하느라 같은 노드를 큐에 여러 번 밀어 넣어서 성능 저하, 전체 그래프를 다 올리려다 메모리 터짐이다. 이 셋만 의식하고 있어도 실무에서 DFS/BFS 관련 사고의 절반 이상은 피할 수 있다.
