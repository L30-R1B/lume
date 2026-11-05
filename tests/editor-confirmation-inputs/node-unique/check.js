const assert=require("node:assert/strict"); const {unique}=require("./logic");
{ const args=[[3, 1, 3, 2, 1]]; const before=JSON.stringify(args); assert.deepEqual(unique(...args),[3, 1, 2]); assert.equal(JSON.stringify(args),before); }
{ const args=[[]]; const before=JSON.stringify(args); assert.deepEqual(unique(...args),[]); assert.equal(JSON.stringify(args),before); }
{ const args=[[-1, -1, 0]]; const before=JSON.stringify(args); assert.deepEqual(unique(...args),[-1, 0]); assert.equal(JSON.stringify(args),before); }
