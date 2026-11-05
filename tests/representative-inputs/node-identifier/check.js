const assert=require("node:assert/strict"); const {parseId}=require("./app");
assert.equal(parseId("42"),42); for (const s of ["0","01","-1","1x"," 1","","9007199254740992"]) assert.equal(parseId(s),null); assert.equal(parseId("9007199254740991"),9007199254740991);
