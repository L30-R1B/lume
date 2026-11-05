const assert=require("node:assert/strict"); const {parse_port}=require("./logic");
{ const args=["1"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),1); assert.equal(JSON.stringify(args),before); }
{ const args=["65535"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),65535); assert.equal(JSON.stringify(args),before); }
{ const args=["8080"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),8080); assert.equal(JSON.stringify(args),before); }
{ const args=["0"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=["65536"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=["-1"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=["1x"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=[""]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=[" 80"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=["\uff11\uff12"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=["\u0661\u0662"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
{ const args=["99999999999999999999999999"]; const before=JSON.stringify(args); assert.deepEqual(parse_port(...args),null); assert.equal(JSON.stringify(args),before); }
