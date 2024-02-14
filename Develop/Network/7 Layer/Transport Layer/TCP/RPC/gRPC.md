
# gRPC

---

# 내용
1. gRPC는 구글이 오픈소스로 공개한 원격 프로시저 호출을 위한 바이너리 프로토콜이다. 
2. 성능과 간편함으로 인기를 얻은 REST의 대안이다. 
3. gRPC는 [Http 2.0](..%2F..%2F..%2FApplication%20Layer%2FHttp%2FHttp%EC%99%80%20Http%202.0.md)에 대한 전이중(full duplex) 연결을 제공한다.
![gRPC.svg](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC.svg)


--- 

# gRPC 특징 

## 성능
- 네트워크 요청으로 보내기 위해 Protobuf를 직렬화(Serialization) 및 역직렬화(Deserialization)하는 작업은 JSON 형태의 직렬화/역직렬화 보다 빠르다.
- 또한 gRPC의 네트워크 속도가 HTTP POST/GET 속도보다 빠르다. 특히 POST 요청 시 많은 차이를 보인다.

## REST API 지원
- Protobuf로 정의된 API는 envoyproxy나 grpc-gateway 같은 gateway 를 통해 REST API로 제공 가능하다. 
- gRPC로 정의된 API를 OpenAPI 프로토콜로 변환하여 REST API를 사용하는 클라이언트에도 API-우선 방식을 적용할 수 있다.

--- 

## gRPC와 REST의 차이점 및 특징

![gRPC & Rest.png](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FgRPC%20%26%20Rest.png)


1. gRPC는 HTTP2를 사용한다. (REST는 HTTP1.1)
2. gRPC는 protocol buffer data format을 사용한다. REST는 주로 JSON을 사용한다.
3. gRPC를 활용하면 server-side streaming, client-side streamin, bidirect-streaming과 같은 HTTP/2가 가진 feature를 활용할 수 있다.
4. 내부적으로는 Netty(소켓통신)을 사용하고 있다.
5. 이미 배포한 서비스를 중단할 필요 없이 데이터 구조를 바꿀 수 있다.

---

## 프로토콜 버퍼가 무엇일까?
- 프로토콜 버퍼(Protocol Buffers)는 구글에서 개발한 바이너리 직렬화 데이터 형식입니다.
- 이는 다양한 프로그래밍 언어에서 구조화된 데이터를 직렬화하고, 효율적으로 전송하고 저장하기 위한 목적으로 사용됩니다.

![Protocol Buffer.png](..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FgRPC%2FProtocol%20Buffer.png)
```
위 그림은 json과 Protocol buffer를 사용한 직렬화의 용량 차이이다.
json: 82byte
protocol buffer: 33 byte
```

### 2. 프로토콜 버퍼의 장점
1) 통신이 빠릅니다.
- 같은 데이터를 보내더라도 데이터의 크기가 작아 같은 시간에 더 많은 데이터를 보낼 수 있고, 더 빠르게 보내질 수 있습니다.
2) 파싱을 할 필요가 없습니다.
- json 포맷을 사용하게 되면 받은 데이터를 다시 객체로 파싱해서 사용하는데, protobuf를 사용하면 byte를 받아서 그 byte 그대로 메모리에 써버리고 객체 레퍼런스가 가리키는 형태로 사용하기 때문에 별도의 파싱이 필요가 없어집니다.

### 3. 프로토콜 버퍼의 단점
1) 인간이 읽기가 어렵습니다.
- json 포맷은 사람이 읽기 편한 형태로 되어 있는데, .proto 파일이 없으면 의미를 알 수 없을 정도로 protobuf로 쓴 데이터는 사람이 읽기가 어렵습니다. 
- 즉, .proto 파일이 반드시 있어야지 protobuf로 쓰여진 데이터를 읽을 수가 있다는 단점이 있습니다.
- 따라서 외부 API 통신에는 보통 사용되지 않고(각 클라이언트마다 .proto 파일이 있어야 합니다), 내부 서비스(Microservice 등)
2. proto문법을 배워야 합니다.
.proto파일은 json과 같이 key, value 쌍으로 단순하게 되어 있지 않고, 작성 방법에 따른 문법을 배워야하기 때문에 난이도가 있습니다.
---

