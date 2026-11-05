const assert=require("node:assert/strict"); const {bodyBytes}=require("./app");
assert.equal(bodyBytes("abc"),3); assert.equal(bodyBytes("€"),3); assert.equal(bodyBytes("a😀"),5); assert.equal(bodyBytes(""),0);
