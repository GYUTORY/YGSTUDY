- First Created by KYG. on 2023-01-01


# Redis 기초 설명
1. String, Hash, List, Set, Bitmap, HyperLogLog와 같은 데이터 타입 때문에 데이터 구조 서버라고도 불린다.
2. Redis는 기본적으로 메모리에 저장하기 때문에 읽기와 쓰기 명령이 매우 빠르다.
3. Redis는 디스크에도 데이터를 저장할 수 있다.


# 방법
1. Snapshot - 저장된 데이터를 바이너리 스냅샷으로 설정
2. Journaling - 시간에 걸쳐 실행된 모든 커맨드를 순서대로 저장해 사람이 읽을 수 있는 파일로 생성

# Part 1(Strings)
1. set을 이용하여 key, value형식으로 저장이 가능
2. get { key } 형식으로 key에 해당하는 value을 가져 올 수 있음.
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_jBFnH3/스크린샷 2023-01-01 오후 3.10.07.png)

3. expire을 이용하여 해당 키의 만료시간을 설정할 수 있음.(10초)
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_QnpTi1/스크린샷 2023-01-01 오후 3.12.02.png)

4. ttl을 이용하여 해당 키의 만료시간을 알아 낼 수 있음(7초남음)
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_deUhHv/스크린샷 2023-01-01 오후 3.13.21.png)
> -는 만료되고 지난 시간(s)을 의미

5. 만료된 key값 호출
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_aCmPYo/스크린샷 2023-01-01 오후 3.14.07.png)


6. Key값 조회
6.1 Key값 조회를 위한 키값 세팅
- set incheon yeonsu
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_5Ost6O/스크린샷 2023-01-01 오후 3.15.20.png)

6.2 모든 key값 조회하기
> $keys * 
>![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_iCAkFu/스크린샷 2023-01-01 오후 3.16.23.png)

6.3 SQL Like문과 같이 i가 포함된 key를 조회
> $keys *i* 
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_AZGk22/스크린샷 2023-01-01 오후 3.17.33.png)


# Part2(list)

1. list에 data 삽입
> $lpush number_lists 3
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_jaba5G/스크린샷 2023-01-01 오후 3.18.59.png)

2. lrange명령어를 통해 값 조회가능 lrange {keyname} start stop -1은 제일 마지막 원소이다.
> $lrange number_lists 0 -1
> ![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_p5YbNq/스크린샷 2023-01-01 오후 3.23.01.png)



# Part3(Set)
- set은 List와 비슷하나 중복값은 허용이 안됨.
- del keyname 을 통해서 해당 키를 지울수도 있음.

1. 데이터 삽입
> $sadd number_sets 1
![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_vG7VW4/스크린샷 2023-01-01 오후 3.25.01.png)

2. 조회
> $smembers number_sets
![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_NAmuGA/스크린샷 2023-01-01 오후 3.26.28.png)





참고 자료
- https://dleunji.tistory.com/41?category=999005