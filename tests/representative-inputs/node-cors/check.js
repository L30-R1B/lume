const assert=require("node:assert/strict"); const {allowOrigin}=require("./app");
assert.equal(allowOrigin("https://a.example",["https://a.example"]),"https://a.example"); assert.equal(allowOrigin("https://a.example.evil",["https://a.example"]),null); assert.equal(allowOrigin("https://x",[]),null);
