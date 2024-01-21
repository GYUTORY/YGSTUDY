// 문자열을 Base64로 인코딩
var originalString = "Hello, World!";
var encodedString = btoa(originalString);

console.log("Original String: " + originalString);
console.log("Encoded String: " + encodedString);

// Base64를 디코딩
var decodedString = atob(encodedString);ㅁ
console.log("Decoded String: " + decodedString);
