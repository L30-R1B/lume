const assert=require("node:assert/strict"); const {retry_delay}=require("./logic");
{ const args=[0, 2, 100]; const before=JSON.stringify(args); assert.deepEqual(retry_delay(...args),2); assert.equal(JSON.stringify(args),before); }
{ const args=[3, 2, 100]; const before=JSON.stringify(args); assert.deepEqual(retry_delay(...args),16); assert.equal(JSON.stringify(args),before); }
{ const args=[60, 10, 1000]; const before=JSON.stringify(args); assert.deepEqual(retry_delay(...args),1000); assert.equal(JSON.stringify(args),before); }
{ const args=[20, 0, 100]; const before=JSON.stringify(args); assert.deepEqual(retry_delay(...args),0); assert.equal(JSON.stringify(args),before); }
{ const args=[2, 3, 0]; const before=JSON.stringify(args); assert.deepEqual(retry_delay(...args),0); assert.equal(JSON.stringify(args),before); }
