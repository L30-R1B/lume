"""Create isolated multi-file service fixtures, distinct pilot and reserved task manifests."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[1]
fixtures = base / "tests/representative-inputs"
# Each entry contains only the defective source and independent acceptance assertions.
PY_CASES = [
    (
        "expiry",
        "is_expired",
        "Treat a credential as expired when now is at or after expires_at.",
        "def is_expired(now, expires_at):\n    return now > expires_at\n",
        "assert is_expired(10,10) and is_expired(11,10) and not is_expired(9,10)",
    ),
    (
        "discount",
        "discounted_cents",
        "Apply an integer percent discount to cents using floor division only after multiplication.",
        "def discounted_cents(cents, percent):\n    return cents // 100 * (100 - percent)\n",
        "assert discounted_cents(199,10)==179 and discounted_cents(0,30)==0 and discounted_cents(500,100)==0 and discounted_cents(17,0)==17",
    ),
    (
        "bearer",
        "bearer",
        "Extract a nonempty token only from the exact case-sensitive prefix Bearer followed by one space; otherwise return None.",
        'def bearer(header):\n    return header.split(" ")[-1] if header else None\n',
        'assert bearer("Bearer abc")=="abc" and bearer("Bearer ") is None and bearer("Basic abc") is None and bearer("") is None and bearer("bearer abc") is None',
    ),
    (
        "filename",
        "safe_name",
        "Accept a nonempty filename only if it is neither . nor .. and contains neither slash nor backslash.",
        "def safe_name(name):\n    return bool(name)\n",
        'assert safe_name("report.csv") and not safe_name("") and not safe_name(".") and not safe_name("..") and not safe_name("a/b") and not safe_name("a\\\\b")',
    ),
    (
        "pagination",
        "offset",
        "Return zero-based pagination offset for a one-based page and size 1 through 100; raise ValueError for any other page or size.",
        "def offset(page,size):\n    return page*size\n",
        "assert offset(1,10)==0 and offset(4,20)==60\nfor page,size in ((0,10),(1,0),(1,101)):\n    try: offset(page,size)\n    except ValueError: pass\n    else: raise AssertionError((page,size))",
    ),
]
JS_CASES = [
    (
        "cors",
        "allowOrigin",
        "Return the supplied origin only if it exactly equals an entry in the allowlist, otherwise null.",
        "exports.allowOrigin=(origin,allowed)=>allowed.some(x=>origin.includes(x))?origin:null;\n",
        'assert.equal(allowOrigin("https://a.example",["https://a.example"]),"https://a.example"); assert.equal(allowOrigin("https://a.example.evil",["https://a.example"]),null); assert.equal(allowOrigin("https://x",[]),null);',
    ),
    (
        "utf8length",
        "bodyBytes",
        "Return the UTF-8 byte length of a string as transmitted over HTTP.",
        "exports.bodyBytes=s=>s.length;\n",
        'assert.equal(bodyBytes("abc"),3); assert.equal(bodyBytes("€"),3); assert.equal(bodyBytes("a😀"),5); assert.equal(bodyBytes(""),0);',
    ),
    (
        "retryheader",
        "retrySeconds",
        "Convert milliseconds to a nonnegative Retry-After number of whole seconds, rounding upward.",
        "exports.retrySeconds=ms=>Math.floor(ms/1000);\n",
        "assert.equal(retrySeconds(0),0); assert.equal(retrySeconds(1),1); assert.equal(retrySeconds(1000),1); assert.equal(retrySeconds(1001),2); assert.equal(retrySeconds(-1),0);",
    ),
    (
        "identifier",
        "parseId",
        "Parse only a canonical positive decimal integer string without leading zero and within JavaScript safe integer range; otherwise return null.",
        "exports.parseId=s=>parseInt(s,10)||null;\n",
        'assert.equal(parseId("42"),42); for (const s of ["0","01","-1","1x"," 1","","9007199254740992"]) assert.equal(parseId(s),null); assert.equal(parseId("9007199254740991"),9007199254740991);',
    ),
    (
        "tax",
        "taxCents",
        "Return tax in cents rounded to nearest integer from integer cents and basis points (10000 basis points is 100%).",
        "exports.taxCents=(cents,basisPoints)=>Math.round(cents*basisPoints/100);\n",
        "assert.equal(taxCents(1000,825),83); assert.equal(taxCents(100,500),5); assert.equal(taxCents(1,0),0); assert.equal(taxCents(200,10000),200);",
    ),
]
CPP_CASES = [
    (
        "trim",
        "trim",
        "Trim leading and trailing ASCII spaces, tabs, carriage returns and line feeds; preserve interior bytes.",
        'inline std::string trim(std::string s){auto a=s.find_first_not_of(" "); if(a==std::string::npos)return ""; return s.substr(a,s.find_last_not_of(" ")-a+1);}\n',
        'assert(trim(" \\tvalue\\r\\n")=="value"); assert(trim("  ")==""); assert(trim("a b")=="a b");',
    ),
    (
        "port",
        "parsePort",
        "Parse a nonempty ASCII decimal port from 1 to 65535 inclusive; return -1 for malformed or out-of-range input, including overflow.",
        "inline int parsePort(const std::string& s){return s.empty()?-1:std::atoi(s.c_str());}\n",
        'assert(parsePort("1")==1); assert(parsePort("65535")==65535); for(auto s:{"", "0", "65536", "1x", "-1", " 1", "99999999999999999999999999"}) assert(parsePort(s)==-1);',
    ),
    (
        "overlap",
        "overlap",
        "Return whether two nonempty half-open integer intervals [a,b) and [c,d) overlap; empty or reversed intervals never overlap.",
        "inline bool overlap(int a,int b,int c,int d){return a<=d && c<=b;}\n",
        "assert(overlap(1,4,3,5)); assert(!overlap(1,3,3,4)); assert(!overlap(2,2,1,4)); assert(!overlap(4,1,0,5));",
    ),
    (
        "kib",
        "kib",
        "Round unsigned byte counts up to whole kibibytes without overflowing for the maximum unsigned long long.",
        "inline unsigned long long kib(unsigned long long n){return n/1024;}\n",
        "assert(kib(0)==0); assert(kib(1)==1); assert(kib(1024)==1); assert(kib(1025)==2); assert(kib(ULLONG_MAX)==ULLONG_MAX/1024+1);",
    ),
    (
        "csvfield",
        "csvField",
        "Encode one CSV field by surrounding it with double quotes and doubling each embedded double quote; preserve all other bytes.",
        'inline std::string csvField(const std::string& s){return "\\""+s+"\\"";}\n',
        'assert(csvField("")=="\\"\\""); assert(csvField("a,b")=="\\"a,b\\""); assert(csvField("a\\"b")=="\\"a\\"\\"b\\"");',
    ),
]


def create():
    if fixtures.exists():
        raise SystemExit("Fixture directory already exists; preserve previous frozen data")
    tasks = {"pilot": [], "confirmation": []}
    for family, cases in [("python", PY_CASES), ("node", JS_CASES), ("cpp", CPP_CASES)]:
        for index, (name, symbol, objective, defective, checks) in enumerate(cases):
            root = fixtures / (family + "-" + name)
            root.mkdir(parents=True)
            (root / "README.md").write_text(
                "Local service component. The app layer delegates policy decisions to service; verify with the supplied check. No network is required.\n"
            )
            (root / "config.json").write_text(json.dumps({"service": "fixture", "network": False, "version": 1}) + "\n")
            if family == "python":
                target = "service.py"
                (root / target).write_text(defective)
                (root / "app.py").write_text("from service import " + symbol + "\n")
                (root / "check.py").write_text("from app import " + symbol + "\n" + checks + "\n")
                verify = ["python3", "check.py"]
            elif family == "node":
                target = "service.js"
                (root / target).write_text(defective)
                (root / "app.js").write_text('module.exports=require("./service");\n')
                (root / "check.js").write_text(
                    'const assert=require("node:assert/strict"); const {'
                    + symbol
                    + '}=require("./app");\n'
                    + checks
                    + "\n"
                )
                verify = ["node", "check.js"]
            else:
                target = "service.hpp"
                headers = "#pragma once\n#include <string>\n#include <cstdlib>\n#include <climits>\n"
                (root / target).write_text(headers + defective)
                (root / "app.hpp").write_text('#pragma once\n#include "service.hpp"\n')
                (root / "check.cpp").write_text('#include <cassert>\n#include "app.hpp"\nint main(){' + checks + "}\n")
                (root / "check.py").write_text(
                    'import pathlib,subprocess\np=pathlib.Path("build");p.mkdir(exist_ok=True)\nsubprocess.run(["c++","-std=c++17","-Wall","-Wextra","-o",str(p/"check"),"check.cpp"],check=True)\nsubprocess.run([str(p/"check")],check=True)\n'
                )
                verify = ["python3", "check.py"]
            failed = subprocess.run(verify, cwd=root, capture_output=True, check=False, timeout=30)
            if failed.returncode == 0:
                raise ValueError("Fixture defect did not fail independent acceptance: " + str(root))
            task = {
                "id": family + "-" + name,
                "family": family,
                "root": str(root),
                "objective": "In " + target + ", fix " + symbol + ". " + objective + " Only change " + target + ".",
                "acceptance": "All existing checks pass; no test or unrelated source changes.",
                "target": target,
                "protected": [str(p.relative_to(root)) for p in root.iterdir() if p.name != target and p.is_file()],
                "verify": verify,
            }
            tasks["pilot" if index == 0 else "confirmation"].append(task)
    (base / "evidence/representative-tasks.json").write_text(json.dumps(tasks, indent=2))
    make_manifest("pilot", tasks["pilot"])


def make_manifest(phase, tasks):
    from codex_economy.benchmark import config_fingerprint

    manifest_path = base / ("evidence/representative-" + phase + "-manifest.json")
    if manifest_path.exists():
        raise SystemExit("Manifest already exists; do not overwrite an experiment")
    files = [p for task in tasks for p in Path(task["root"]).iterdir() if p.is_file()]
    files.extend(p for p in (base / "src/codex_economy").iterdir() if p.suffix in (".py", ".cjs"))
    manifest = {
        "version": 4,
        "phase": "distinct-multifile-" + phase,
        "seed": 20261110 if phase == "pilot" else 20261111,
        "model": "gpt-6.1-sol",
        "effort": "high",
        "arms": ["A", "E"],
        "comparison_arm": "E",
        "repetitions": 1 if phase == "pilot" else 3,
        "timeout": 180,
        "context_bytes": 6000,
        "output": str(base / ("evidence/representative-" + phase)),
        "tasks": tasks,
        "codex_binary": shutil.which("codex"),
        "reference_config_hash": hashlib.sha256((Path.home() / ".codex/config.toml").read_bytes()).hexdigest(),
        "reference_config_semantic_hash": config_fingerprint(
            Path.home() / ".codex/config.toml", base / ("evidence/representative-" + phase) / "workspaces"
        ),
        "fixture_hashes": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {
                "phase": phase,
                "tasks": len(tasks),
                "jobs": len(tasks) * manifest["repetitions"] * len(manifest["arms"]),
                "manifest": str(manifest_path),
            }
        )
    )


if len(sys.argv) == 1:
    create()
elif sys.argv[1:] == ["--confirmation"]:
    make_manifest("confirmation", json.loads((base / "evidence/representative-tasks.json").read_text())["confirmation"])
elif sys.argv[1:] == ["--pilot"]:
    make_manifest("pilot", json.loads((base / "evidence/representative-tasks.json").read_text())["pilot"])
else:
    raise SystemExit("Use without arguments to create; --pilot or --confirmation freezes a manifest")
