### HTTP(Hyper Text Transfer Protocol)란?
- 웹에서 데이터를 주고받을 수 있는 프로토콜이다.
- 80번 포트를 사용하며, 클라이언트-서버 모델을 따른다.
- TCP/IP를 기반으로 동작하며, 상태가 없는(Stateless) 프로토콜이다.
- 텍스트 기반의 프로토콜로, 데이터를 암호화하지 않고 전송한다.

### HTTPS(Hyper Text Transfer Protocol Secure)란?
- HyperText Transfer Protocol over Secure Socket Layer, HTTP over TLS, HTTP over SSL, HTTP Secure 등으로 불리는 HTTPS는 HTTP에 데이터 암호화가 추가된 프로토콜이다.
- HTTPS는 HTTP와 다르게 443번 포트를 사용하며, 네트워크 상에서 중간에 제3자가 정보를 볼 수 없도록 암호화를 지원하고 있다.
- SSL/TLS 프로토콜을 통해 데이터를 암호화하여 전송한다.

![https_secure.png](..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FHttp%2Fhttps_secure.png)

---

### HTTP와 HTTPS의 주요 차이점
1. **보안성**
   - HTTP: 데이터가 암호화되지 않은 평문으로 전송되어 보안에 취약
   - HTTPS: SSL/TLS를 통해 데이터를 암호화하여 전송하여 보안성 강화

2. **포트**
   - HTTP: 80번 포트 사용
   - HTTPS: 443번 포트 사용

3. **인증서**
   - HTTP: 인증서 불필요
   - HTTPS: SSL 인증서 필요 (CA에서 발급)

4. **연산 속도**
   - HTTP: 암호화 과정이 없어 상대적으로 빠름
   - HTTPS: 암호화/복호화 과정으로 인해 상대적으로 느림

---

### 암호화 방식
- 공개키 암호화 방식과 공개키의 느리다는 단점을 보완한 대칭키 암호화 방식을 함께 사용한다. 
- 공개키 방식으로 대칭키를 전달하고, 서로 공유된 대칭키를 가지고 통신하게 된다.

#### [ 대칭키 암호화와 비대칭키 암호화]

##### 대칭키 암호화
- 클라이언트와 서버가 동일한 키를 사용해 암호화/복호화를 진행함
- 키가 노출되면 매우 위험하지만 연산 속도가 빠름
- AES, DES, 3DES 등이 대표적인 대칭키 암호화 알고리즘
- 키 교환 문제가 있음 (키를 안전하게 전달하기 어려움)

##### 비대칭키 암호화
- 1개의 쌍으로 구성된 공개키와 개인키를 암호화/복호화 하는데 사용함
- 공개키로 암호화하면 개인키로만 복호화 가능
- 개인키로 암호화하면 공개키로만 복호화 가능
- 키가 노출되어도 비교적 안전하지만 연산 속도가 느림
- RSA가 대표적인 비대칭키 암호화 알고리즘

---

### HTTPS 통신 과정
1. **SSL/TLS 핸드셰이크**
   - 클라이언트가 서버에 연결을 시도
   - 서버는 자신의 인증서를 클라이언트에 전송
   - 클라이언트는 인증서의 유효성을 검증

2. **키 교환**
   - 클라이언트는 대칭키를 생성하여 서버의 공개키로 암호화하여 전송
   - 서버는 개인키로 복호화하여 대칭키를 획득

3. **데이터 통신**
   - 양측은 공유된 대칭키를 사용하여 데이터를 암호화/복호화하며 통신

---

#### 개인적인 생각으로는, 해당 https의 개념보다 [TLS HandShake](TLS%20HandShake.md)를 더 연구해보자.

---

```
출처
1. https://velog.io/@bclef25/http%EC%99%80-https%EC%9D%98-%EC%B0%A8%EC%9D%B4
2. https://stackoverflow.com/questions/188266/how-are-ssl-certificates-verified#:~:text=Your%20web%20browser%20downloads%20the,key%20of%20the%20web%20server.&text=It%20uses%20this%20public%20key,address%20of%20the%20web%20server
3. https://jeong-pro.tistory.com/89
4. https://tiptopsecurity.com/how-does-https-work-rsa-encryption-explained/
5. https://mangkyu.tistory.com/98 [MangKyu's Diary:티스토리]
```
