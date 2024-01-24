
# NFS(Network File System)
- 네트워크를 통해 파일 시스템을 공유하는 프로토콜입니다. 
- NFS는 1984년에 썬 마이크로시스템즈에서 개발되었으며, 현재 널리 사용되고 있습니다.
- 한 개의 서버에 NFS로 여러대의 웹서버로 연결할수 있어 여러클라이언트에서 한 서버의 정보를 공유할 수 있다.
  ![nfs.png](..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2Fnfs.png)

## 장점
- 편리성: 네트워크를 통해 파일을 공유하기 쉽습니다.
- 효율성: 네트워크 대역폭을 효율적으로 사용합니다.
- 보안성: 다양한 보안 기능을 제공합니다.

## NFS의 용도
- 파일 공유: 파일을 다른 컴퓨터와 공유할 수 있습니다.
- 백업: 파일을 다른 컴퓨터에 백업할 수 있습니다.
- 클라우드 스토리지: 클라우드 스토리지를 사용할 수 있습니다.


## NFS의 구성
- NFS는 클라이언트와 서버로 구성됩니다.
- 클라이언트는 서버의 파일 시스템을 마운트하여 사용합니다. 서버는 클라이언트의 요청에 응답하여 파일을 제공합니다.

## NFS는 다음과 같은 RPC 함수를 사용합니다.
- mount(): 클라이언트가 서버의 파일 시스템을 마운트합니다.
- open(): 클라이언트가 서버의 파일을 엽니다.
- read(): 클라이언트가 서버의 파일에서 데이터를 읽습니다.
- write(): 클라이언트가 서버의 파일에 데이터를 씁니다.
- close(): 클라이언트가 서버의 파일을 닫습니다.

## NFS의 보안
- NFS는 다음과 같은 보안 기능을 제공합니다.


# NFS 서버(192.168.0.1) 구축 순서

1. NFS서버 패키지 설치
```[root@kkyung ~]# yum install portmap nfs-utils* libgssapi```


2. NFS exports 설정
- 마운트를 허가할 디렉토리 및 호스트 목록 설정

### NFS 서버의 특정 IP호스트 접속 허용 설정
```
[root@kkyung /]# vi /etc/exports /home   192.168.0.1(rw,sync)
```

3. 방화벽 해제
```
[root@kkyung /]# service iptables stop
```

4. NFS실행
```
[root@kkyung /]# /etc/init.d/rpcbind start[root@kkyung /]# /etc/init.d/portmap start
[root@kkyung /]# /etc/init.d/rpcidmapd start
[root@kkyung /]# /etc/init.d/nfs start
```   
