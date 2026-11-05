const assert=require("node:assert/strict"); const {retrySeconds}=require("./app");
assert.equal(retrySeconds(0),0); assert.equal(retrySeconds(1),1); assert.equal(retrySeconds(1000),1); assert.equal(retrySeconds(1001),2); assert.equal(retrySeconds(-1),0);
