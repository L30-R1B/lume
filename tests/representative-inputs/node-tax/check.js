const assert=require("node:assert/strict"); const {taxCents}=require("./app");
assert.equal(taxCents(1000,825),83); assert.equal(taxCents(100,500),5); assert.equal(taxCents(1,0),0); assert.equal(taxCents(200,10000),200);
