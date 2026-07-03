---
title: Greedy 문제 패턴 모음 (코딩테스트/면접 빈출)
tags: [algorithm, greedy, coding-test, interview, java, priority-queue, two-pointer]
updated: 2026-05-05
---

# Greedy 문제 패턴 모음 (코딩테스트/면접 빈출)

## 들어가며

기본 개념과 증명은 [Greedy.md](Greedy.md)에서, 매트로이드와 근사 같은 이론은 [Greedy_Deep_Dive.md](Greedy_Deep_Dive.md)에서 다뤘다. 이 문서는 그 두 개에서 일부러 뺀 부분, 그러니까 실제 코딩테스트와 면접에서 반복적으로 나오는 그리디 문제 패턴을 정리한다.

5년 동안 면접관으로도 들어가 보고 후보자로도 풀어본 경험을 정리하면, 그리디 문제는 크게 10개 정도의 패턴이 돌아가면서 나온다. LeetCode Hot 100, 프로그래머스 카카오 기출, 백준 골드 구간을 보면 같은 골격에 살만 다른 문제가 계속 나온다. 그러니까 "이 문제는 어떤 패턴인가"를 빠르게 분류하는 감각이 풀이 시간을 결정한다.

각 패턴마다 그리디 기준이 왜 성립하는지 한 줄로 짚고, Java 코드를 붙이고, 내가 실제로 틀렸던 반례와 헷갈리는 형제 문제를 적는다. "이 문제 풀어봤는데 비슷한 거 못 풀겠다"의 원인은 보통 형제 문제와의 차이를 못 잡아서다.

## 1. 인터벌 스케줄링 패턴

### 1-1. 활동 선택 (Activity Selection)

가장 많은 회의를 잡으려면 **종료 시간 기준 오름차순 정렬** 후 끝나는 시간이 빠른 것부터 선택하면서 다음 회의 시작이 그 종료보다 크거나 같은지만 본다.

기준 정당화: 가장 빨리 끝나는 회의 A를 골랐을 때, A를 포함하는 최적해가 반드시 존재한다. 최적해 OPT가 A 대신 B로 시작하면, B의 종료시간 ≥ A의 종료시간이므로 OPT의 B를 A로 바꿔도 뒤따르는 회의들이 그대로 들어갈 수 있다.

```java
public int maxMeetings(int[][] meetings) {
    Arrays.sort(meetings, Comparator.comparingInt(a -> a[1]));
    int count = 0, lastEnd = Integer.MIN_VALUE;
    for (int[] m : meetings) {
        if (m[0] >= lastEnd) {
            count++;
            lastEnd = m[1];
        }
    }
    return count;
}
```

자주 빠지는 반례: 시작 시간 기준으로 정렬하면 무너진다. `[(0,30), (5,10), (15,20)]`에서 시작시간 정렬은 `(0,30)` 하나만 잡지만 종료시간 정렬은 `(5,10), (15,20)` 둘을 잡는다.

또 하나, 끝나는 시간이 같을 때 시작 시간으로 보조 정렬을 하지 않으면 같은 시간에 끝나는 짧은 회의를 놓치는 경우가 있다. 결과 개수에는 영향이 없지만, 실제 선택된 회의 목록을 반환해야 하는 변형 문제에서 답이 달라진다.

### 1-2. 인터벌 파티셔닝 (Minimum Number of Meeting Rooms)

같은 회의들을 동시에 진행할 수 있는 최소 회의실 개수를 구하는 문제다. 1-1과 골격이 똑같이 보이지만 답이 다르다. 1-1은 "한 방에서 몇 개 잡을까", 1-2는 "다 잡으려면 방이 몇 개 필요한가".

기준 정당화: 시작 시간 정렬 후 우선순위 큐로 가장 빨리 끝나는 방을 추적한다. 새 회의 시작 ≥ 큐 top 종료면 그 방을 재사용, 아니면 새 방을 만든다. 어느 시점이든 큐 크기가 그때 동시 진행 중인 회의 수다.

```java
public int minMeetingRooms(int[][] intervals) {
    if (intervals.length == 0) return 0;
    Arrays.sort(intervals, Comparator.comparingInt(a -> a[0]));
    PriorityQueue<Integer> endTimes = new PriorityQueue<>();
    endTimes.offer(intervals[0][1]);
    for (int i = 1; i < intervals.length; i++) {
        if (intervals[i][0] >= endTimes.peek()) {
            endTimes.poll();
        }
        endTimes.offer(intervals[i][1]);
    }
    return endTimes.size();
}
```

자주 빠지는 반례: `[(0,30), (5,10), (15,20)]`에서 답은 2다. `(0,30)`이 깔려 있는 동안 `(5,10)`이 들어와서 방 2개, `(15,20)`이 들어올 때 `(5,10)`이 끝났으니 그 방을 재사용해서 여전히 2다. 정답은 "동시 회의 최대 수"이고, 그게 큐 크기의 최댓값이 된다.

이벤트 정렬(시작 +1, 종료 -1) 방식으로도 풀 수 있다. 시작과 종료를 분리해서 시간순 정렬하고 누적 합의 최댓값을 답으로 잡는다. 같은 시각에 종료가 시작보다 먼저 처리돼야 하니 정렬 키에서 종료를 우선 처리해야 한다(종료 -1을 먼저, 시작 +1을 나중).

비슷한 문제 헷갈리는 케이스: Minimum Platforms(GeeksforGeeks)는 1-2와 정확히 같은 문제다. 도착/출발 배열이 분리돼 있는 형태일 뿐, 인터벌 파티셔닝이 본질이다. 그런데 LeetCode "Non-overlapping Intervals"는 1-1과 같은 종료시간 정렬 패턴이고 답이 "전체 - 활동 선택 결과"가 된다. 이름과 형태가 살짝 달라도 결국 같은 두 패턴 안에 들어간다.

## 2. Gas Station (주유소 순회)

원형으로 늘어선 주유소를 한 바퀴 돌 때, 어디서 출발하면 한 번도 빈 탱크가 되지 않을지 찾는다. 총 주유량 ≥ 총 소비량이면 답이 반드시 존재한다는 게 출발점이다.

기준 정당화: `tank = gas[i] - cost[i]`를 누적할 때 음수가 되는 순간 그 구간 안의 어떤 i에서 출발해도 실패한다. 누적합이 음수가 된 시점의 다음 인덱스에서 다시 시작하면 된다. 전체 합이 ≥ 0이라는 조건 아래서, 마지막으로 리셋된 시작점이 정답이다.

```java
public int canCompleteCircuit(int[] gas, int[] cost) {
    int total = 0, tank = 0, start = 0;
    for (int i = 0; i < gas.length; i++) {
        int diff = gas[i] - cost[i];
        total += diff;
        tank += diff;
        if (tank < 0) {
            start = i + 1;
            tank = 0;
        }
    }
    return total >= 0 ? start : -1;
}
```

자주 빠지는 반례: 모든 구간에서 `gas[i] >= cost[i]`인 경우 0번이 답이지만, 처음부터 `gas[0] < cost[0]`이라도 뒤가 충분히 좋으면 출발점이 뒤로 밀린다. 전체 합 검증 없이 단순히 "첫 양의 누적 시작점"을 답으로 내면 틀린다. `gas=[2,3,4], cost=[3,4,3]`은 총합 9-10 = -1이라 답이 없는데, 단순히 음수 리셋만 보면 인덱스 2를 답으로 내놓는 실수를 한다.

비슷한 문제 헷갈리는 케이스: 백준의 "주유소"(13305번)는 원형이 아니라 직선이고, 각 도시에서 기름값이 다른 상황이다. 이건 "지금까지 본 가장 싼 가격으로 다음 구간을 채운다"는 다른 패턴이다. 같이 묶어 외워두면 면접에서 변형이 나와도 빠르게 분류된다.

## 3. Jump Game I, II

### 3-1. Jump Game I (도달 가능성)

각 위치의 최대 점프 거리가 주어질 때 마지막 칸에 도달 가능한지 본다.

기준 정당화: 지금까지 도달 가능한 최대 인덱스 `reach`를 추적하면서, 현재 위치 i가 `reach`보다 크면 거기 못 간다. 그게 아니라면 `reach = max(reach, i + nums[i])`로 갱신한다. 마지막 인덱스까지 `reach`가 따라가면 도달 가능.

```java
public boolean canJump(int[] nums) {
    int reach = 0;
    for (int i = 0; i < nums.length; i++) {
        if (i > reach) return false;
        reach = Math.max(reach, i + nums[i]);
        if (reach >= nums.length - 1) return true;
    }
    return true;
}
```

자주 빠지는 반례: `[3,2,1,0,4]`에서 인덱스 3에 도달은 하지만 거기서 점프 0이라 4번을 못 간다. `reach`가 i를 못 따라잡는 순간이 정확히 그 시점이다.

### 3-2. Jump Game II (최소 점프 횟수)

마지막 칸까지 가는 최소 점프 횟수다. 여기서 BFS로 풀 수도 있지만 그리디가 O(n)이라 더 빠르다.

기준 정당화: 현재 점프로 갈 수 있는 범위 `currentEnd`를 정해놓고, 그 범위 안에서 다음에 갈 수 있는 가장 먼 곳 `farthest`를 추적한다. i가 `currentEnd`에 도달하면 점프 횟수를 1 늘리고 `currentEnd = farthest`로 갱신한다. 이게 BFS의 레벨 단위 확장과 똑같다.

```java
public int jump(int[] nums) {
    int jumps = 0, currentEnd = 0, farthest = 0;
    for (int i = 0; i < nums.length - 1; i++) {
        farthest = Math.max(farthest, i + nums[i]);
        if (i == currentEnd) {
            jumps++;
            currentEnd = farthest;
        }
    }
    return jumps;
}
```

자주 빠지는 반례: 루프 종료 조건이 `i < nums.length - 1`이라는 점이 중요하다. 마지막 인덱스에 도달했는데 거기서 또 점프 횟수를 한 번 더 세면 1이 추가로 붙는다. `[2,3,1,1,4]`에서 답은 2(0→1→4)인데, `i < nums.length`로 돌리면 3이 나온다.

비슷한 문제 헷갈리는 케이스: Jump Game III, IV는 그래프 BFS가 답이지 그리디가 아니다. 점프 거리가 양방향이거나 동일 값 인덱스로 워프하는 식의 변형이 들어오는 순간 그리디 가정이 깨진다. 패턴 분류할 때 "점프 방향이 단방향이고, 각 위치의 거리가 고정되어 있나"를 먼저 본다.

## 4. Candy Distribution (사탕 분배)

`ratings`가 주어지고, 각 아이는 최소 1개 이상의 사탕을 받아야 하며 평점이 옆 아이보다 높으면 사탕도 더 많아야 한다. 총 사탕 최소.

기준 정당화: 한 번에 양쪽 조건을 만족시키기 어려우니까, **왼쪽→오른쪽으로 한 번 훑고, 오른쪽→왼쪽으로 한 번 더 훑어서 둘의 max**를 취한다. 왼쪽 패스는 "왼쪽 이웃보다 평점이 높으면 +1", 오른쪽 패스는 "오른쪽 이웃보다 평점이 높으면 +1". 두 결과의 max가 양쪽 조건을 모두 만족하는 최소값이 된다.

```java
public int candy(int[] ratings) {
    int n = ratings.length;
    int[] candies = new int[n];
    Arrays.fill(candies, 1);
    for (int i = 1; i < n; i++) {
        if (ratings[i] > ratings[i - 1]) candies[i] = candies[i - 1] + 1;
    }
    for (int i = n - 2; i >= 0; i--) {
        if (ratings[i] > ratings[i + 1]) candies[i] = Math.max(candies[i], candies[i + 1] + 1);
    }
    int sum = 0;
    for (int c : candies) sum += c;
    return sum;
}
```

자주 빠지는 반례: 한 방향만 보는 함정에 잘 빠진다. `[1,3,2,2,1]`에서 왼쪽 패스만 하면 `[1,2,1,1,1]`인데, 실제론 마지막 세 개가 `2,2,1`이 되어야 한다(인덱스 2가 인덱스 3과 평점 같으니 각자 1씩, 인덱스 3은 인덱스 4보다 평점 높으니 +1, 즉 `[1,2,2,2,1]`이 답이고 합 8). 양방향을 다 봐야 잡힌다.

또 하나는 평점이 같은 경우다. "더 높은 평점에는 더 많은 사탕"이지 "다른 평점에는 다른 사탕"이 아니다. 평점이 같으면 사탕 수는 무관하므로, 둘 다 1을 줘도 된다. 이걸 놓치고 같은 평점도 다르게 주려고 하면 답이 부풀어 오른다.

O(1) 공간으로도 풀 수 있는 슬로프(slope) 카운팅 풀이가 있는데, 면접에서는 두 패스 풀이를 먼저 보여주고 추가 질문이 들어오면 슬로프로 넘어가는 게 안전하다.

## 5. Task Scheduler (쿨다운 큐)

같은 종류 작업 사이에 n초 쿨다운이 있을 때 모든 작업을 끝내는 최소 시간이다. 우선순위 큐와 그리디의 결합 패턴 중 가장 자주 나온다.

기준 정당화: 매 시점마다 **남은 횟수가 가장 많은 작업을 먼저 처리**하면 쿨다운으로 인한 idle을 최소화한다. 가장 많이 남은 게 늦게 처리되면 마지막에 그것만 남아서 강제 idle이 생긴다.

```java
public int leastInterval(char[] tasks, int n) {
    int[] freq = new int[26];
    for (char t : tasks) freq[t - 'A']++;
    PriorityQueue<Integer> pq = new PriorityQueue<>(Collections.reverseOrder());
    for (int f : freq) if (f > 0) pq.offer(f);

    int time = 0;
    while (!pq.isEmpty()) {
        List<Integer> temp = new ArrayList<>();
        for (int i = 0; i <= n; i++) {
            if (!pq.isEmpty()) {
                int f = pq.poll();
                if (f > 1) temp.add(f - 1);
            }
            time++;
            if (pq.isEmpty() && temp.isEmpty()) break;
        }
        for (int f : temp) pq.offer(f);
    }
    return time;
}
```

수식 풀이도 있다. `(maxFreq - 1) * (n + 1) + (가장 많은 빈도를 가진 작업 종류 수)`와 `tasks.length` 중 큰 값이 답이다. 면접에서 시간이 부족하면 수식 풀이로 가고, 시간이 있으면 큐 시뮬레이션을 보여주면서 "왜 수식이 성립하는가"를 설명하는 흐름이 좋다.

자주 빠지는 반례: 큐 시뮬레이션을 짜면서 idle 처리를 놓치기 쉽다. 슬롯이 비어 있는데 큐도 비어 있으면 그게 진짜 마지막이고, 시뮬레이션을 더 돌리면 안 된다. 위 코드의 `if (pq.isEmpty() && temp.isEmpty()) break;`가 그 처리다. 빼먹으면 마지막 사이클에서 쿨다운만큼 idle이 추가로 카운트된다.

비슷한 문제 헷갈리는 케이스: LeetCode "Reorganize String"이 같은 패턴이다. 같은 문자가 인접하지 않게 재배열하라는 문제인데, 빈도수 큰 것부터 한 칸씩 띄워가며 배치하는 게 그리디 핵심이다. Task Scheduler에서 idle을 다른 작업으로 채우는 것과 같은 발상이다.

## 6. 우선순위 큐 + 그리디 결합

### 6-1. Reorganize String

```java
public String reorganizeString(String s) {
    int[] count = new int[26];
    for (char c : s.toCharArray()) count[c - 'a']++;
    PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> b[1] - a[1]);
    for (int i = 0; i < 26; i++) {
        if (count[i] > 0) pq.offer(new int[]{i, count[i]});
    }
    StringBuilder sb = new StringBuilder();
    int[] prev = null;
    while (!pq.isEmpty()) {
        int[] cur = pq.poll();
        sb.append((char) ('a' + cur[0]));
        cur[1]--;
        if (prev != null && prev[1] > 0) pq.offer(prev);
        prev = cur;
    }
    return sb.length() == s.length() ? sb.toString() : "";
}
```

기준 정당화: 가장 많은 문자를 먼저 쓰고, 직전에 쓴 문자는 한 박자 쉬게 만든다(`prev`로 한 사이클 보류). 최대 빈도 문자가 `(n+1)/2`를 넘으면 어떤 배치로도 인접 회피가 불가능하니 빈 문자열 반환.

자주 빠지는 반례: `"aaab"`는 답이 없다(`a`가 3개, 길이 4의 절반인 2를 넘음). 이걸 검증 안 하면 무한 루프나 잘못된 결과가 나온다. 코드에서 `sb.length() == s.length()` 체크가 그 안전장치다.

### 6-2. K번째 큰 합 (Find K Pairs with Smallest Sums)

두 정렬 배열 `nums1`, `nums2`에서 합이 가장 작은 k 쌍을 찾는다.

기준 정당화: 최소 힙에 `(0,0)`부터 시작해서 매번 꺼낸 `(i,j)`에서 `(i+1,j)`와 `(i,j+1)`을 추가하는 식으로 BFS처럼 확장한다. 단, 같은 `(i,j)`가 중복 들어가지 않도록 visited 처리가 필요하다.

```java
public List<List<Integer>> kSmallestPairs(int[] nums1, int[] nums2, int k) {
    PriorityQueue<int[]> pq = new PriorityQueue<>((a, b) -> 
        (nums1[a[0]] + nums2[a[1]]) - (nums1[b[0]] + nums2[b[1]]));
    Set<Long> visited = new HashSet<>();
    List<List<Integer>> result = new ArrayList<>();
    pq.offer(new int[]{0, 0});
    visited.add(0L);
    while (k-- > 0 && !pq.isEmpty()) {
        int[] cur = pq.poll();
        int i = cur[0], j = cur[1];
        result.add(Arrays.asList(nums1[i], nums2[j]));
        if (i + 1 < nums1.length && visited.add((long)(i + 1) * nums2.length + j)) {
            pq.offer(new int[]{i + 1, j});
        }
        if (j + 1 < nums2.length && visited.add((long) i * nums2.length + j + 1)) {
            pq.offer(new int[]{i, j + 1});
        }
    }
    return result;
}
```

자주 빠지는 반례: visited 처리를 안 하면 같은 쌍이 두 번 큐에 들어가서 결과에 중복이 생긴다. visited 키를 `i*N+j`로 만들 때 N이 큰 경우 int 오버플로 조심. long 캐스팅이 필요하다.

## 7. 두 포인터 + 그리디

### 7-1. Container With Most Water

높이 배열에서 두 막대 사이에 담을 수 있는 물의 최대량.

기준 정당화: 양 끝에서 시작해서 **더 짧은 쪽 포인터를 안쪽으로 옮긴다**. 더 긴 쪽을 옮기면 가로 길이는 줄고, 높이는 어차피 더 짧은 쪽에 막혀 있으니 면적이 무조건 줄어든다. 짧은 쪽을 옮기면 높이가 늘어날 가능성이 있다.

```java
public int maxArea(int[] height) {
    int left = 0, right = height.length - 1, max = 0;
    while (left < right) {
        int area = Math.min(height[left], height[right]) * (right - left);
        max = Math.max(max, area);
        if (height[left] < height[right]) left++;
        else right--;
    }
    return max;
}
```

자주 빠지는 반례: 두 막대 높이가 같을 때 어느 쪽을 옮겨도 결과에 영향 없다. 양쪽 다 옮기면(`left++; right--;`) 한 칸씩 둘 다 움직이지만 답은 같다.

비슷한 문제 헷갈리는 케이스: Trapping Rain Water는 같은 두 포인터 패턴이지만 그리디 기준이 다르다. "더 낮은 쪽의 max를 추적하면서 그것보다 낮은 칸은 max에서 자기 높이 뺀 만큼 채운다"가 핵심이라, 단순히 짧은 쪽을 옮기는 패턴이 아니다. 둘을 같은 패턴으로 묶지 않도록 주의한다.

### 7-2. Boats to Save People

각 사람의 몸무게가 주어지고, 배 한 척에 최대 두 명 + 무게 제한 limit, 모두 태우는 최소 배 수.

기준 정당화: 정렬 후 양 끝 두 포인터. **가장 무거운 사람과 가장 가벼운 사람을 짝짓되 limit를 넘으면 무거운 사람만 혼자**. 가벼운 사람을 두 명 모아서 한 배에 태우는 것보다, 가벼운 사람을 무거운 사람과 짝지어주는 게 항상 낫거나 같다(교환 논증).

```java
public int numRescueBoats(int[] people, int limit) {
    Arrays.sort(people);
    int left = 0, right = people.length - 1, boats = 0;
    while (left <= right) {
        if (people[left] + people[right] <= limit) left++;
        right--;
        boats++;
    }
    return boats;
}
```

자주 빠지는 반례: `left == right`인 경우(혼자 남은 사람) 처리. 위 코드는 `left <= right` 조건으로 한 명 남았을 때도 boats++가 되어 정확하다. `left < right`로 잘못 쓰면 마지막 한 명이 누락된다.

## 8. 주식 매매 시리즈

### 8-1. Best Time to Buy and Sell Stock (1회 거래)

기준 정당화: 지금까지 본 최저가를 기억하면서 매일 "오늘 팔면 얼마 남나"를 비교한다.

```java
public int maxProfit(int[] prices) {
    int minPrice = Integer.MAX_VALUE, profit = 0;
    for (int p : prices) {
        minPrice = Math.min(minPrice, p);
        profit = Math.max(profit, p - minPrice);
    }
    return profit;
}
```

### 8-2. Best Time to Buy and Sell Stock II (다회 거래)

기준 정당화: 가격이 오르는 모든 인접 구간을 합치는 게 최적이다. `prices[i] > prices[i-1]`인 모든 i에서 `prices[i] - prices[i-1]`을 더한다. 이건 "산-골짜기" 패턴을 한 번에 잡는 트릭으로, 어느 구간을 묶어 거래해도 결과는 같다.

```java
public int maxProfit(int[] prices) {
    int profit = 0;
    for (int i = 1; i < prices.length; i++) {
        if (prices[i] > prices[i - 1]) profit += prices[i] - prices[i - 1];
    }
    return profit;
}
```

자주 빠지는 반례: "한 번에 한 주만, 다음 매수 전에 매도해야 한다"는 제약을 잊고 모든 양의 차이를 더하면 같은 결과인데 그게 우연이 아니다. `[1,2,3,4]`를 1→4 한 번에 거래해도 3이고, 1→2→3→4로 잘게 나눠도 1+1+1=3이다. 이걸 이해하지 못하고 DP로 풀려고 하면 시간이 날아간다.

### 8-3. Best Time to Buy and Sell Stock with Cooldown

이건 DP 문제다. 그리디로 풀리지 않는다. 매도 후 다음 날 매수 금지가 들어가면 "지금 팔까 말까"가 미래의 매수 가능성에 영향을 주기 때문에 그리디 가정이 깨진다. 8-1, 8-2와 형제처럼 보이지만 패턴이 완전히 다르다.

```java
public int maxProfit(int[] prices) {
    int hold = -prices[0], sold = 0, rest = 0;
    for (int i = 1; i < prices.length; i++) {
        int prevSold = sold;
        sold = hold + prices[i];
        hold = Math.max(hold, rest - prices[i]);
        rest = Math.max(rest, prevSold);
    }
    return Math.max(sold, rest);
}
```

비슷한 문제 헷갈리는 케이스: "수수료 있는 다회 거래"(LeetCode 714)도 DP로 가야 한다. 수수료가 들어가는 순간 산-골짜기 트릭이 안 통한다. `hold = max(hold, rest - prices[i])`, `rest = max(rest, hold + prices[i] - fee)` 형태의 상태 전이를 짜야 한다. 면접에서 8-2를 풀고 나면 8-3이나 수수료 변형이 자주 따라붙는데, 여기서 그리디로 밀어붙이면 막힌다.

## 9. 문자열 그리디

### 9-1. Remove K Digits

n자리 숫자에서 k개를 빼서 가장 작은 수를 만든다.

기준 정당화: 스택을 쓴다. 들어오는 숫자가 스택 top보다 작으면, k가 남아 있는 한 top을 빼낸다. 큰 숫자가 앞에 있으면 자릿수가 큰 자리에서 큰 값이 차지하니까 무조건 손해다. 단조 증가 스택을 만들어가면서 k를 소진하는 게 핵심.

```java
public String removeKdigits(String num, int k) {
    Deque<Character> stack = new ArrayDeque<>();
    for (char c : num.toCharArray()) {
        while (!stack.isEmpty() && k > 0 && stack.peek() > c) {
            stack.pop();
            k--;
        }
        stack.push(c);
    }
    while (k-- > 0 && !stack.isEmpty()) stack.pop();
    StringBuilder sb = new StringBuilder();
    while (!stack.isEmpty()) sb.append(stack.pollLast());
    while (sb.length() > 1 && sb.charAt(0) == '0') sb.deleteCharAt(0);
    return sb.length() == 0 ? "0" : sb.toString();
}
```

자주 빠지는 반례: k가 다 안 쓰인 채 단조 증가 상태로 끝나는 경우(`"12345", k=2`). 이때는 뒤에서 k개를 더 잘라야 한다. 앞에 0이 붙는 경우(`"10200", k=1` → `"0200"`)도 leading zero 제거 처리가 필요하다. 모두 빼버리면 빈 문자열이 되니 `"0"` 반환도 잊지 말 것.

### 9-2. Largest Number

정수 배열을 이어 붙여 만들 수 있는 가장 큰 수.

기준 정당화: 두 문자열 a, b를 비교할 때 `a+b vs b+a`로 정렬한다. `[3, 30]`에서 30+3 = "303"보다 3+30 = "330"이 크니까 3이 앞에 와야 한다. 단순 사전순 정렬이나 숫자 크기 정렬은 틀린다.

```java
public String largestNumber(int[] nums) {
    String[] strs = new String[nums.length];
    for (int i = 0; i < nums.length; i++) strs[i] = String.valueOf(nums[i]);
    Arrays.sort(strs, (a, b) -> (b + a).compareTo(a + b));
    if (strs[0].equals("0")) return "0";
    StringBuilder sb = new StringBuilder();
    for (String s : strs) sb.append(s);
    return sb.toString();
}
```

자주 빠지는 반례: 모든 입력이 0인 경우(`[0,0,0]`)는 결과가 `"000"`이 되면 안 되고 `"0"`이어야 한다. 정렬 후 첫 원소가 `"0"`이면 전부 0이라는 뜻이므로 `"0"` 한 자리만 반환.

비교 함수의 정당성을 면접에서 물어보면 교환 논증으로 답한다. "임의의 두 수 a, b를 인접하게 놓고 순서를 바꿨을 때 어느 쪽이 큰지 보면, 그게 정렬 기준이고 그 기준이 transitive하다"가 핵심이다. transitive 증명은 문자열 비교의 사전순 성질에서 나온다.

## 10. 정리: 문제를 만났을 때 분류 순서

면접/시험에서 그리디 문제처럼 보이는 게 나오면 내가 거치는 순서다.

먼저 인터벌이 있는지 본다. 시작/종료 시간 또는 구간 형태면 1번 패턴(활동 선택, 인터벌 파티셔닝)을 의심한다. 정렬 키가 시작인지 종료인지가 패턴을 가른다.

다음으로 배열을 한 번 훑으면서 누적 상태로 풀리는지 본다. Gas Station, Jump Game, 주식 매매 1회는 단일 패스 + 누적 변수로 끝나는 패턴이다.

빈도수가 중요한 문제(같은 작업 쿨다운, 문자 재배열)는 우선순위 큐 + 그리디 결합을 의심한다. 5번, 6번 패턴이다.

양 끝에서 좁혀가며 최적을 찾는 형태는 두 포인터 + 그리디. 7번 패턴이다. 다만 Trapping Rain Water처럼 비슷해 보이지만 다른 패턴도 있으니 "짧은 쪽을 옮기는 게 왜 정당한가"를 머릿속에서 한 번 굴려본다.

마지막으로 단조 스택이 어울리는지 본다. "k개 제거", "큰 자리부터 작게/크게"라는 키워드가 보이면 9-1 패턴이다.

이 분류가 안 되면 그리디가 아닐 가능성이 높다. 그러면 DP나 백트래킹으로 갈아타야 하는데, 가장 흔한 함정이 "그리디로 잘 될 것 같은데?"라는 직관에 매달려서 30분을 날리는 경우다. 처음 5분 안에 반례가 안 떠오르면 그때부터는 [Greedy.md](Greedy.md)에서 다룬 교환 논증을 머릿속으로 한 번 돌려보고, 막히면 DP로 넘어간다.

## 마치며

여기 정리한 10개 패턴이 코딩테스트 그리디 문제의 80% 이상을 커버한다. 나머지 20%는 매트로이드나 근사 영역으로 들어가는데 그건 [Greedy_Deep_Dive.md](Greedy_Deep_Dive.md) 쪽 내용이고, 코딩테스트보다는 알고리즘 대회나 시스템 설계 면접에서 더 자주 나온다.

패턴을 외우는 것보다 "왜 이 기준이 정답인지" 한 줄 설명을 같이 외우는 게 더 오래 간다. 면접에서 코드만 짜고 끝나는 일은 거의 없고, "왜 이 정렬 키죠?", "다른 기준이면 안 되나요?"가 반드시 따라온다. 그때 교환 논증 한 줄로 답할 수 있으면 통과 확률이 크게 올라간다.
