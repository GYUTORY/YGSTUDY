
### HTTPS(Hyper Text Transfer Protocol Secure)란?
- HyperText Transfer Protocol over Secure Socket Layer, HTTP over TLS, HTTP over SSL, HTTP Secure 등으로 불리는 HTTPS는 HTTP에 데이터 암호화가 추가된 프로토콜이다.
- HTTPS는 HTTP와 다르게 443번 포트를 사용하며, 네트워크 상에서 중간에 제3자가 정보를 볼 수 없도록 암호화를 지원하고 있다.

![https_secure.png](..%2F..%2F..%2F..%2F..%2Fetc%2Fimage%2FNetwork_image%2F7Layer%2FHttp%2Fhttps_secure.png)

---

### 암호화 방식
- 공개키 암호화 방식과 공개키의 느리다는 단점을 보완한 대칭키 암호화 방식을 함께 사용한다. 
- 공개키 방식으로 대칭키를 전달하고, 서로 공유된 대칭키를 가지고 통신하게 된다.

--- 

#### [ 대칭키 암호화와 비대칭키 암호화]
- HTTPS는 대칭키 암호화 방식과 비대칭키 암호화 방식을 모두 사용하고 있다. 각각의 암호화 방식은 다음과 같다.

#### 대칭키 암호화
- 클라이언트와 서버가 동일한 키를 사용해 암호화/복호화를 진행함
- 키가 노출되면 매우 위험하지만 연산 속도가 빠름

#### 비대칭키 암호화
- 1개의 쌍으로 구성된 공개키와 개인키를 암호화/복호화 하는데 사용함
- 키가 노출되어도 비교적 안전하지만 연산 속도가 느림

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
