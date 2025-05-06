# URL과 URI 

<div align="center">
    <img src="../../etc/image/Network_image/URL.png" alt="URL" width="50%">
</div>

## URL(Uniform Resource Locator)
- URL은 웹 상에서 자원(리소스)의 위치를 지정하는 주소 체계이다.
- 브라우저의 주소창에 입력한 URL은 서버가 제공되는 환경에 존재하는 파일의 위치를 나타낸다.
- CLI 환경에서 폴더와 파일의 위치를 찾아 이동하듯이, 슬래시(/)를 이용해 서버의 폴더에 진입하거나 파일을 요청할 수 있다.
- URL은 웹에서 특정 리소스에 접근하기 위한 경로를 제공하며, 이는 인터넷에서 정보를 찾고 접근하는 데 필수적인 요소이다.

## URL 구성요소 
1. **Scheme (프로토콜)**
   - 통신 방식을 결정하는 부분으로, 자원에 접근하기 위해 사용할 프로토콜을 지정한다.
   - 주요 프로토콜:
     - `http`: 일반적인 웹 페이지 접근
     - `https`: 보안이 강화된 웹 페이지 접근
     - `ftp`: 파일 전송
     - `mailto`: 이메일 주소
     - `file`: 로컬 파일 시스템
   - 예: `https://`, `http://`, `ftp://`

2. **Host (호스트)**
   - 웹 서버의 위치를 지정하는 부분
   - 도메인 이름이나 IP 주소를 사용
   - 예: `www.example.com`, `192.168.1.1`
   - 서브도메인을 포함할 수 있음 (예: `blog.example.com`)

3. **Port (포트)**
   - 서버 내에서 실행 중인 특정 서비스를 식별하는 번호
   - 기본값: HTTP(80), HTTPS(443)
   - 예: `:8080`, `:3000`

4. **Path (경로)**
   - 서버 내에서 자원의 위치를 지정
   - 디렉토리 구조를 반영
   - 예: `/images/logo.png`, `/api/users`

5. **Query (쿼리)**
   - 서버에 전달할 추가 정보
   - `?`로 시작하며, `key=value` 형태로 구성
   - 여러 쿼리는 `&`로 구분
   - 예: `?id=123&name=john`

6. **Fragment (프래그먼트)**
   - 문서 내 특정 부분을 가리키는 식별자
   - `#`으로 시작
   - 주로 HTML 문서의 특정 섹션으로 이동할 때 사용
   - 예: `#section1`, `#main-content`

## URI(Uniform Resource Identifier)
- URI는 인터넷 상의 자원을 식별하는 문자열이다.
- URL은 URI의 하위 개념으로, 자원의 위치를 지정하는 방식이다.
- URI는 자원을 식별하는 더 넓은 개념으로, URL과 URN(Uniform Resource Name)을 포함한다.

### URI의 주요 특징
1. **식별성**
   - 각 자원을 고유하게 식별할 수 있어야 함
   - 동일한 자원은 항상 동일한 URI로 식별되어야 함

2. **구성 요소**
   - Scheme: 프로토콜
   - Authority: 사용자 정보, 호스트, 포트
   - Path: 자원의 경로
   - Query: 추가 정보
   - Fragment: 문서 내 특정 부분

### URI 예시
```
https://www.example.com:8080/path/to/resource?param1=value1&param2=value2#section1
```
- Scheme: `https`
- Host: `www.example.com`
- Port: `8080`
- Path: `/path/to/resource`
- Query: `param1=value1&param2=value2`
- Fragment: `section1`

### URL과 URI의 차이점
1. **범위**
   - URI는 자원을 식별하는 모든 문자열을 포함
   - URL은 URI의 하위 집합으로, 자원의 위치를 지정하는 방식

2. **목적**
   - URI: 자원을 식별
   - URL: 자원의 위치를 지정

3. **사용 예시**
   - URI: `urn:isbn:0451450523` (책의 ISBN 번호)
   - URL: `https://www.example.com/book/0451450523`

### 실제 사용 사례
1. **웹 페이지 접근**
   ```
   https://www.example.com/index.html
   ```

2. **API 엔드포인트**
   ```
   https://api.example.com/users/123?fields=name,email
   ```

3. **이미지 리소스**
   ```
   https://cdn.example.com/images/logo.png
   ```

4. **동적 페이지**
   ```
   https://www.example.com/search?q=keyword&page=2
   ```

5. **문서 내 특정 섹션**
   ```
   https://www.example.com/document#chapter-3
   ```
