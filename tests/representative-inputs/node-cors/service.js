exports.allowOrigin=(origin,allowed)=>allowed.some(x=>origin.includes(x))?origin:null;
