import json
from pathlib import Path
base=Path(__file__).resolve().parents[1]
fixtures=base/'tests/benchmark-fixtures'
tasks=[]
for family in ('python','node','cpp'):
    for i,(name,bug,expression,cases) in enumerate([
        ('clamp','return x;','return x < lo ? lo : (x > hi ? hi : x);',[(2,0,5,2),(-1,0,5,0),(8,0,5,5)]),
        ('span','return hi + lo;','return hi - lo;',[(2,7,5),(-3,4,7),(0,0,0)]),
        ('parity','return x % 2 == 1;','return x % 2 == 0;',[(2,True),(3,False),(-2,True)]),
        ('square','return x + x;','return x * x;',[(3,9),(-3,9),(0,0)])]):
        root=fixtures/(family+'-'+name);root.mkdir(parents=True,exist_ok=True)
        nargs=3 if name=='clamp' else 2 if name=='span' else 1
        args=['x','lo','hi'] if name=='clamp' else ['lo','hi'] if name=='span' else ['x']
        if family=='python':
            target='logic.py';protected=['check.py'];verify=['python3','check.py']
            body={'clamp':'return x','span':'return hi + lo','parity':'return x % 2 == 1','square':'return x + x'}[name]
            (root/target).write_text(f'def {name}({", ".join(args)}):\n    {body}\n')
            (root/'check.py').write_text(f'from logic import {name}\n'+''.join(f'assert {name}({", ".join(repr(a) for a in row[:-1])}) == {row[-1]!r}\n' for row in cases))
        elif family=='node':
            target='logic.js';protected=['check.js'];verify=['node','check.js']
            (root/target).write_text(f'exports.{name} = function({", ".join(args)}) {{ {bug} }};\n')
            (root/'check.js').write_text(f'const assert = require("node:assert/strict");\nconst {{{name}}} = require("./logic");\n'+''.join(f'assert.equal({name}({", ".join(str(a) for a in row[:-1])}), {json.dumps(row[-1])});\n' for row in cases))
        else:
            target='logic.hpp';protected=['check.cpp','CMakeLists.txt'];verify=['python3','verify.py'];protected+=['verify.py']
            (root/target).write_text(f'#pragma once\ninline int {name}({", ".join("int "+a for a in args)}) {{ {bug} }}\n')
            (root/'check.cpp').write_text('#include <cassert>\n#include "logic.hpp"\nint main() {\n'+''.join(f'assert({name}({", ".join(str(a) for a in row[:-1])}) == {int(row[-1])});\n' for row in cases)+'}\n')
            (root/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.16)\nproject(check CXX)\nenable_testing()\nadd_executable(check check.cpp)\nadd_test(NAME logic COMMAND check)\n')
            (root/'verify.py').write_text('import subprocess\nfor cmd in [["cmake","-S",".","-B","build"],["cmake","--build","build"],["ctest","--test-dir","build","--output-on-failure"]]:\n subprocess.run(cmd,check=True)\n')
        for j in range(12):
            (root/f'notes-{j}.md').write_text(f'# Module {j}\nUnrelated inventory administration documentation.\n'*20)
        tasks.append({'id':family+'-'+name,'family':family,'root':str(root),'objective':f'Fix {name} in {target}. It must '+{'clamp':'restrict x to the inclusive interval lo to hi.','span':'compute hi minus lo.','parity':'return whether x is even.','square':'compute x squared.'}[name],'acceptance':'All existing checks pass; tests unchanged; only the target implementation may change.','verify':verify,'protected':protected,'target':target})
manifest={'version':1,'phase':'confirmation-representative-small-tasks','seed':20261104,'model':'gpt-6.1-sol','effort':'high','arms':['A','B','C'],'repetitions':3,'timeout':180,'context_bytes':6000,'output':str(base/'evidence/benchmark'),'tasks':tasks}
(base/'evidence/benchmark-manifest.json').write_text(json.dumps(manifest,indent=2))
