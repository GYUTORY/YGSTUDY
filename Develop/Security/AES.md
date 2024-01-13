
# AES
- 표준이었던 DES를 대신하여 새로운 표준이 된 대칭 알고리즘이다.
- 전 세계의 기업과 암호학자가 AES의 후보로서 다수의 대칭 암호 알고리즘을 제안했지만!!
- 그 중에 Rijndel이라는 대칭 암호 알고리즘이 2000년에 AES로 선정

# AES가 DES를 대신한 이유
1. DES에 비해서 키 사이즈가 자유롭다.
2. 즉, 가변 길이의 블록과 가변 길이의 키 사용이 가능하다.(128bit, 192bit, 256bit)

--- 

# AES와 SHA의 차이



## SHA256
- 단방향 암호화로 복호화 하는 방법이 없어서 불가능하다.

![SHA256.png](..%2F..%2Fetc%2Fimage%2FSECURITY%2FSHA256.png)

## AES 
- 대칭키 알고리즘으로 암복호화에 같은 키를 사용한다.

> DES는 Feistel 네트워크라는 기본 구조를 사용하지만 AES에서는 SPN 이라는 구조를 사용하고 있다. 

![AES.png](..%2F..%2Fetc%2Fimage%2FSECURITY%2FAES.png) 

### spn
- Subsititution Layer과 Pernutation을 이용하여 Confusion과 Diffusion을 만족시켜주는 구조이다. 
- 이 구조의 장점은 Feistal 구조와 반대로 병렬연산이 가능하여 속도가 빠르고 단점은 복호화시 별도의 복호화 모듈을 구현해줘야 한다는 것이다.

```
출처
https://thenicesj.tistory.com/721
``` 