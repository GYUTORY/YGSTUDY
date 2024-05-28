
## CORS
- 웹과 협업하는 개발자라면 처음 한 번은 무조건 만나게 되는 오류가 있다. 
- 바로 클라이언트가 우리가 열심히 만든 API를 붙이려고 할 때 나타나는 Cross-Origin Resource Sharing, 즉 CORS 오류이다. 
- 우선은 이 짜증나는 CORS 오류가 왜 있는지 알아야 할 필요가 있다.

## CORS의 존재 이유
- 웹은 기본적으로 '동일 출처 정책(Same-Orgin Policy)'를 기본적인 보안 원칙으로 책정하고 있다. 
- 해당 정책은 간단히 말해 출처 A에서 생산된 리소스들에 대해서 출처 B가 상호작용 하지 못하도록 막는 것인데 이를 통해 악의적인 사이트에서 사용자의 데이터를 도용하거나 조작하는 것을 방지하기 위함이다.
- 하지만 이럴 경우 다른 출처에 대해서 리소스가 필요할 때는 요청하지 못하게 되기 때문에 이를 지키면서 추가적으로 접근할 수 있도록 허용해주는 것이 CORS인 것이다. 
- CORS 덕분에 안전하게 다른 사이트의 리소스를 가져올 수 있다고 생각하면 된다.

## CORS 처리 방법
- CORS는 우리가 진행하는 프로젝트 코드 단에서 잡을 수도 있고 최종적으로 우리가 배포할 인프라 단에서도 잡을 수 있다. 
- 배포 후 Nignx 자체에서 CORS를 잡는 방법을 소개하도록 하겠다.

---

## Nginx

```shell
location / {
    # 기타 설정... 리버스 프록시 설정 등

    # CORS 헤더 추가
    add_header 'Access-Control-Allow-Origin' 'https://example.com' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, DELETE, PATCH, PUT' always; 
    add_header 'Access-Control-Allow-Headers' 'Authorization,Content-Type' always;
    
    # OPTIONS 요청에 대한 처리
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' 'https://example.com';
        add_header 'Access-Control-Allow-Methods' 'GET, POST, DELETE, PATCH, PUT, OPTIONS';
        add_header 'Access-Control-Allow-Headers' 'Authorization,Content-Type';
        add_header 'Content-Length' '0';
        add_header 'Content-Type' 'text/plain charset=UTF-8';
        add_header 'Access-Control-Max-Age' 1728000;
        return 204;
    }
}
```


### 브라우저 대원칙 
> 회사, 작업중 무슨 수를 써도 CORS가 허용이 되지 않은 문제가 발생했다.
> 사유는, 공인IP > 사설IP로는 호출이 되지 않는다. 즉, 낮은 레벨의 통신에서는 CORS가 발생.
* 단, fireFox가 유연하게 허용해주는 부분이 있다.

