// JavaScript String slice()

let text = "Apple, Banana, Kiwi";
let part = text.slice(7, 13);

console.log(part);


let text2 = "Apple, Banana, Kiwi";
let part2 = text2.slice(7);

console.log(part2);

// If a parameter is negative, the position is counted from the end of the string:

let text3 = "Apple, Banana, Kiwi";
let part3 = text3.slice(-12);

console.log(part3)

// substring() is similar to slice().
// The difference is that start and end values less than 0 are treated as 0 in substring().

// Example
let str = "Apple, Banana, Kiwi";
let part4 = str.substring(7, 13);
console.log(part4);


let str2 = "Apple, Banana, Kiwi";
let part5 = str2.substr(7, 6);
console.log(part5, 'part5');

let str3 = "Apple, Banana, Kiwi";
let part6 = str3.substr(-4);
console.log(part6, 'part6');