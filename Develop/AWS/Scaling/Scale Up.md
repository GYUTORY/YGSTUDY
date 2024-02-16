


## 스케일업에 대해서 알아보자,
- 먼저 대부분의 IT 회사에서, 규모가 커진다면 스케일업과 스케일아웃에 대해 고려해 볼 순간이 올 것이다.
  2xlarge의 사이즈로도 감당이 안된다면, 이럴 때에는 스케일아웃에 대해서도 알아볼 필요할 것이고
- 이를 공부한 후, AWS에서의 Auto Scaling에 대해 알아보도록 하자.

## 스케일업

![스케일업.png](..%2F..%2F..%2Fetc%2Fimage%2FAWS%2FScaling%2F%EC%8A%A4%EC%BC%80%EC%9D%BC%EC%97%85.png)

### 스케일업이란?
- 스케일 업(Scale-up)은 기존의 서버를 보다 높은 사양으로 업그레이드하는 것을 말한다.
- 성능이나 용량 증강을 목적으로 하나의 서버에 디스크를 추가하거나 CPU나 메모리를 업그레이드시키는 것이다.
- AWS에서 EC2 인스턴스 사양을 micro > small 또는 small > medium 등으로 높이는 것이다.


```
출처 
https://tecoble.techcourse.co.kr/post/2021-10-12-scale-up-scale-out/
```