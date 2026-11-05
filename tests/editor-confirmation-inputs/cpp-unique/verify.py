import subprocess
for argv in [["cmake","-S",".","-B","build"],["cmake","--build","build"],["ctest","--test-dir","build","--output-on-failure"]]:
 subprocess.run(argv,check=True)
