import pathlib,subprocess
p=pathlib.Path("build");p.mkdir(exist_ok=True)
subprocess.run(["c++","-std=c++17","-Wall","-Wextra","-o",str(p/"check"),"check.cpp"],check=True)
subprocess.run([str(p/"check")],check=True)
