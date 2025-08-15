---
title: Http Http 2.0
tags: [network, 7-layer, application-layer, http, http와-http-20]
updated: 2025-08-10
---

## 배경
- 가장 큰 차이는 속도이다. 2.0은 헤더를 압축해서 보내기도 하고, 한번의 연결로 동시에 에러메시지를 주고 받을 수도 있다.








- 가장 큰 차이는 속도이다. 2.0은 헤더를 압축해서 보내기도 하고, 한번의 연결로 동시에 에러메시지를 주고 받을 수도 있다.







# Http 그리고 Http 2.0
- First created By KYG at 2023-01-02

# HTTP 2.0
- Multiplexed라는 기술을 도입하는데 1개의 세션으로 여러 개의 요청을 순서 상관없이 Stream으로 받아서 동시다발적으로 처리 및 응답

## Multiplexed Streams
- HTTP 1.0에서 TCP 세션을 맺는 것을 중복해서 수행하는 성능 이슈가 있었다.
- HTTP 1.1에서 Keep-alive를 통해서 해당 문제를 풀어냈었습니다.



## Stream Priorityzation
- HTTP 2.0은 요청을 Stream 형식으로 처리하게 됩니다.
- HTTP 2.0에서는 각 요청에 Priority(우선 순위)를 부여합니다.


> 예를 들어, 1. HTML 문서와 2. 해당 문서에서 사용할 Image를 요청한다고 가정합니다.


- Image를 먼저 응답 받아도, 렌더링할 HTML 문서가 처리가 안되면 의미가 없습니다.
- 이때, HTML 문서의 우선순위를 높여서 먼저 응답하고, Image는 이후에 응답하면 더 효율적으로 동작하게 됩니다.



## Server Push

- HTML 문서가 있고, 해당 문서에서 사용하는 CSS와 Images가 있다고 가정합시다.
- 기존(HTTP 1.1)에서는 HTML 문서를 요청한 후, 해당 문서에서 필요한 CSS와 Images를 요청했었습니다.


## Header Compression
- 기존(HTTP 1.1)에서는 이전에 보냈던 요청과 중복되는 Header도 똑같이 전송하느라 자원을 낭비했습니다.
- HTTP 2.0부터는 허프만 코딩을 사용한 HPACK 압축 방식으로 이를 개선했습니다.







