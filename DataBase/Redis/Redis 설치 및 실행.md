- First Created by KYG. on 2023-01-05

# Redis 실습

# Mac Redis 설치하기 
- brew install redis (Mac Redis 설치)

![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_6PJcOs/스크린샷 2023-01-01 오후 2.46.59.png)


# Redis server 실행하기
> $redis-server

![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_Sv31Hu/스크린샷 2023-01-01 오후 2.48.26.png)

- redis-server 실행 후 정상실행 확인하기


# Redis Client 접속
> $redis-cli 

![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_tvL6Gn/스크린샷 2023-01-01 오후 2.49.35.png)

- Not connected 라면 레디스 접속에 실패한 것이다.


# Redis 백그라운드 실행하기
> $brew services start redis
![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_4oS9Xq/스크린샷 2023-01-01 오후 2.51.14.png)

> redis-cli

- redis-cli가 정상적으로 연결이되었다면, ping을 날리고, pong 응답이 돌아오는지 확인한다.

# Redis 백그라운드 중지하기
> $brew services stop redis
![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_F4c7hs/스크린샷 2023-01-01 오후 2.53.29.png)

- redis가 정상적으로 중지되었다면, 다시 클라이언트에 접속해서 Redis 접속상태를 확인한다.

# Redis 서비스 재시작
> $brew services restart redis
![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_HG8hhf/스크린샷 2023-01-01 오후 2.55.24.png)

- redis가 정상적으로 중지되었다면, 다시 클라이언트에 접속해서 Redis 접속상태를 확인한다.


