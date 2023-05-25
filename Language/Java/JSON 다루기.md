
# Java에서 JSON을 다룰 때 사용하는 클래스
주로 Gson과 Jackson이다.

![](../../../../../../../../../var/folders/py/mt1_j5_j7pzb4jcv7tm58bfr0000gn/T/TemporaryItems/NSIRD_screencaptureui_8qAHwi/스크린샷 2022-12-13 오후 11.19.46.png)



- 요약 : 적은 데이터에서는 GSON이 성능 우수, 대량데이터에서는 JACKSON이 우수

# 아래 User라는 Java Object가 존재한다고 가정

public class User {

    private String name;
    private int age;
    
    public User(String name, int age) {
    	this.name = name;
        this.age = age;
    }
    
    public String getName() {
    	return name;
	}
    
    public int getAge() {
    	return age;
	}
}

ObjectMapper objectMapper = new ObjectMapper();
User user = new User("Ryan", 30);

objectMapper.writeValue(new File("user.json"), user);
// 파일 출력: user.json
{"name":"Ryan","age":30}
// 문자열 출력
String userAsString = objectMapper.writeValueAsString(user);
{"name":"Ryan","age":30}


2.2. Convert "JSON" to "Java Object"
// String to Object
String json = "{ \"name\" : \"Ryan\", \"age\" : 30 }";
User user = objectMapper.readValue(json, User.class);
// JSON File to Object
User user = objectMapper.readValue(new File("user.json"), User.class);
// JSON URL to Object
User user = objectMapper.readValue(new URL("file:user.json"), User.class);


# Convert "JSON" > "Jackson JsonNode"
String json = "{ \"name\" : \"Ryan\", \"age\" : 30 }";
JsonNode jsonNode = objectMapper.readTree(json);
String name = jsonNode.get("name").asText();// Ryan
int age = jsonNode.get("age").asInt();// 30


# "JSON Array String" > "Java List"
String jsonArr = "[{\"name\":\"Ryan\",\"age\":30},{\"name\":\"Jake\",\"age\":20}]";
List<User> users = objectMapper.readValue(jsonArr, new TypeReference<>() {});


# "JSON String" > "Java Map"
String jsonArr = "{\"name\":\"Ryan\",\"age\":30}";
Map<String, Object> user = objectMapper.readValue(jsonArr, new TypeReference<>() {
});

출처
- https://cchoimin.tistory.com/entry/JAVA-JSON-%EB%8B%A4%EB%A3%A8%EA%B8%B0-%EC%A0%95%EB%A6%AC-JACKSON-ObjectMapper
- https://interconnection.tistory.com/137