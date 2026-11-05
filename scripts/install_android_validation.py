"""Install pinned public Android tooling under the product's isolated prefix."""

import hashlib
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

root = Path.home() / ".local/share/codex-economy/android-sdk"
root.mkdir(parents=True, exist_ok=True)
archive = root / "commandline-tools.zip"
url = "https://dl.google.com/android/repository/commandlinetools-linux-16111833_latest.zip"
if not archive.exists():
    urllib.request.urlretrieve(url, archive)
assert hashlib.sha1(archive.read_bytes()).hexdigest() == "e025545c62a8e64c7559119566a569fb1dec5f60"
with zipfile.ZipFile(archive) as z:
    for entry in z.infolist():
        if not (root / entry.filename).resolve().is_relative_to(root):
            raise ValueError("Invalid tool archive")
    z.extractall(root)
for file in (root / "cmdline-tools/bin").iterdir():
    file.chmod(0o755)
manager = root / "cmdline-tools/bin/sdkmanager"
# Local installation was authorized for the requested Android validation. No account or purchase.
licenses = subprocess.run(
    [str(manager), "--sdk_root=" + str(root), "--licenses"],
    input="y\n" * 100,
    capture_output=True,
    text=True,
    timeout=180,
    check=False,
)
Path("evidence/android-licenses.log").write_text(licenses.stdout + "\n" + licenses.stderr)
installed = subprocess.run(
    [str(manager), "--sdk_root=" + str(root), "platforms;android-36", "build-tools;36.0.0", "platform-tools"],
    input="y\n" * 50,
    capture_output=True,
    text=True,
    timeout=300,
    check=False,
)
Path("evidence/android-sdk-install.log").write_text(installed.stdout + "\n" + installed.stderr)
if installed.returncode:
    raise RuntimeError("Android SDK install failed; see log")
print(json.dumps({"sdk": str(root), "platform": 36, "build_tools": "36.0.0", "code": installed.returncode}))
