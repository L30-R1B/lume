import subprocess

for cmd in [
    ["cmake", "-S", ".", "-B", "build"],
    ["cmake", "--build", "build"],
    ["ctest", "--test-dir", "build", "--output-on-failure"],
]:
    subprocess.run(cmd, check=True)
