import hashlib
import json
import os
import subprocess
from pathlib import Path

base = Path(__file__).resolve().parents[1]
root = base / "tests/framework-fixtures/android"
sdk = Path.home() / ".local/share/codex-economy/android-sdk"
gradle = Path.home() / ".local/share/codex-economy/gradle/gradle-9.2.1/bin/gradle"
source = root / "app/src/main/kotlin/sample/economy/MainActivity.kt"
resource = root / "app/src/main/res/values/strings.xml"
original = source.read_text()
original_resource = resource.read_text()
try:
    source.write_text(original.replace("value * 2", "value + value"))
    resource.write_text(original_resource.replace("Economy validation", "Economy updated"))
    process = subprocess.run(
        [str(gradle), "--no-daemon", "--max-workers=1", "assembleDebug", "testDebugUnitTest"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        env={**os.environ, "ANDROID_HOME": str(sdk)},
    )
    (base / "evidence/android-build-after.log").write_text(process.stdout + "\n" + process.stderr)
    if process.returncode:
        raise RuntimeError("Android build/check failed: see log")
    apk = root / "app/build/outputs/apk/debug/app-debug.apk"
    inspected = subprocess.run(
        [str(sdk / "build-tools/36.0.0/aapt2"), "dump", "resources", str(apk)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert "Economy updated" in inspected.stdout
    (base / "evidence/android-resource-dump.log").write_text(inspected.stdout)
    report = {
        "passed": True,
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "apk_bytes": apk.stat().st_size,
        "compile_sdk": 36,
        "agp": "9.0.1",
        "gradle": "9.2.1",
        "source_change": "equivalent Kotlin implementation",
        "resource_change_verified_in_apk": True,
        "unit_tests": [p.name for p in (root / "app/build/test-results/testDebugUnitTest").glob("TEST-*.xml")],
        "device_instrumentation": False,
    }
    (base / "evidence/android-validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
finally:
    source.write_text(original)
    resource.write_text(original_resource)
