
# JWT 

<div style="text-align: center;">
<img src="../../../etc/image/AUTH/JWT.png" alt="이미지" width="75%">
</div>

1. 헤더 : 헤더에는 토큰의 종류와 SIGNATRUE 생성을 위해서 어떤 알고리즘을 사용했는지가 명시되어 있다.
2. PAYLOAD : 페이로드에는 내가 로그인한 유저임을 증명할 수 있는 기본적인 정보들을 넣는다. 차후에 틀라이언트가 다시 토큰을 보내면 해독해서 DB내의 유저 정보와 비교한다.
3. SIGNATURE : Signature는 토큰을 인코딩하거나 유효성 검증을 할 때 사용하는 고유한 암호화 코드이다. 서명은 위에서 만든 헤더와 페이로드의 값을 각각 BASE64로 인코딩하고, 인코딩한 값을 내가 설정한 비밀키를 이용해 헤더에서 정의한 알고리즘(여기서는 HS256)으로 해싱을 하고, 이 값을 다시 BASE64로 인코딩하여 생성한다. 혹시라도 토큰이 제 3자에 의해 탈취되어서 페이로드의 내용이 변경된다면 토큰의 값이 크게 변경된다.


HEADER(ALGOFITEM & TOKEN TYPE)
{
    “alg” : “HS256”,
    “typ” : “JWT”
}

PAYLOAD(DATA)
{
    “userId” : “test”,
    “userPwd” : “1111”
}

VERIFY SIGNATURE

HAMCSHA256{
    base64UrlEncode(header) + “.” +
    base64UrlEncode(payload) ,
    your-256-bit-secret
)

## 장점
- JWT를 이용하면 따로 서버의 메모리에 저장 공간을 확보 할 필요가 없다.
- 서버가 토큰을 한번 클라이언트에게 보내주면 클라이언트는 토큰을 보관하고 있다가(가장 쉬운 방법은 localstorage에 저장하는 것이다) 요청을 보낼 대마다 헤더에 토큰을 실어보내면 된다.
- 쿠키를 사용할 수 없는(쿠키는 웹브라우저에서 사용할 수 있는 기능이다!) 모바일 어플리케이션에는 JWT를 사용한 인증방식이 최적이다.

## 단점
- JWT는 HTTP를 통해 전송하기 때문에 페이로드의 크기가 클수록 데이터 전송에 있어서 비용이 커진다.
- JWT는 유효기간을 따로 정하지 않는 이상 소멸되지 않기 때문에 장기간 방치시 해킹의 위험이 커진다.
- JWT를 localstorage에 보관한다면 XSS공격에 취약해진다.
- (XSS는 외부의 해커가 우리의 프로그램에 특정 javascript 코드를 심어서 local storage에 접근하는 공격이다.)
- 보통 httpOnly가 설정돼서 브라우저만 접근 가능한 쿠키에 토큰을 실어보내서 XSS 공격을 막는다.