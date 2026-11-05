const assert=require("node:assert/strict"); const {merge_intervals}=require("./logic");
{ const args=[[[4, 5], [1, 3], [2, 4]]]; const before=JSON.stringify(args); assert.deepEqual(merge_intervals(...args),[[1, 5]]); assert.equal(JSON.stringify(args),before); }
{ const args=[[[1, 2], [4, 6]]]; const before=JSON.stringify(args); assert.deepEqual(merge_intervals(...args),[[1, 2], [4, 6]]); assert.equal(JSON.stringify(args),before); }
{ const args=[[[-3, -1], [-1, 0]]]; const before=JSON.stringify(args); assert.deepEqual(merge_intervals(...args),[[-3, 0]]); assert.equal(JSON.stringify(args),before); }
{ const args=[[]]; const before=JSON.stringify(args); assert.deepEqual(merge_intervals(...args),[]); assert.equal(JSON.stringify(args),before); }
