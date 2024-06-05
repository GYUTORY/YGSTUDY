
# 개요
- 기존에 웹 사이트를 HTTP로 운영하고 있다가, 사용자의 정보같은 민감한 정보를 사용하게 될 경우에는 SSL 인증서를 사용한 보안처리를 해야합니다.
- 웹서버에 SSL 인증서를 사용해 웹사이트를 HTTPS로 열 수 있게끔 Nginx 프록시 서버에 SSL 인증서를 적용하는 방법을 확인해보겠습니다.

<div align="center">
    <img src="../../../etc/image/WebServer/NginX/ssl.png" alt="Nginx - SSL" width="50%">
</div>

---

## Nginx.conf

```shell
server {
    listen 80;
    server_name www.ygstudy.com ygstudy.com;

    # 리다이렉트 설정
    # return 301: HTTP 상태 코드 301을 반환합니다.
    # 301 상태 코드는 "Moved Permanently"를 의미하며, 클라이언트(예: 웹 브라우저)에게 요청한 리소스가 영구적으로 새로운 URL로 이동했음을 알립니다. 
    # 이를 통해 검색 엔진은 이 URL 변경을 인식하고 검색 색인에 반영할 수 있습니다.
    return 301 https://$host$request_uri;
}

server {
	    listen 443 ssl;
	    server_name  www.ygstudy.com ygstudy.com;
	
	    ssl_certificate      /opt/homebrew/etc/nginx/ssl/local.weezip.treefeely.com+3.pem;
	    ssl_certificate_key  /opt/homebrew/etc/nginx/ssl/local.weezip.treefeely.com+3-key.pem;
	
	    location / {
	        proxy_pass http://localhost:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
	    }
}
```
<br>
<br>

---

> 출처
> 1. https://narup.tistory.com/240
> 2. https://waterfogsw.tistory.com/43 [일단 써보기:티스토리]