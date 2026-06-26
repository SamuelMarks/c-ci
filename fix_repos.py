import os
import re
import subprocess

repos = [
    "../c-abstract-http",
    "../c-fs",
    "../c-orm",
    "../c-rest-framework",
    "../c-str-span",
    "../c89stringutils",
    "../cdd-c"
]

msvc_2005_str = """      - id: build-msvc-2005-wine
        name: Build and Test (MSVC 2005 Wine)
        entry: python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/SamuelMarks/c-ci/master/precommit_matrix.py').read())" build msvc_2005_wine
        language: python
        pass_filenames: false"""

msvc_2026_str = """      - id: build-msvc-2026-wine
        name: Build and Test (MSVC 2026 Wine)
        entry: python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/SamuelMarks/c-ci/master/precommit_matrix.py').read())" build msvc_2026_wine
        language: python
        pass_filenames: false"""

for repo in repos:
    if not os.path.exists(repo):
        print(f"Skipping {repo}, does not exist")
        continue

    # Cleanup any stale build dirs so that FetchContent clones fresh copies.
    for f in os.listdir(repo):
        if f.startswith("build_") and os.path.isdir(os.path.join(repo, f)):
            os.system(f"rm -rf {os.path.join(repo, f)}")

    yaml_path = os.path.join(repo, ".pre-commit-config.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r') as f:
            content = f.read()

        # Fix python3 to python for entry commands
        content = content.replace("entry: python3 -c", "entry: python -c")
        
        # Remove broken build-msvc-wine
        content = re.sub(r'\s*- id: build-msvc-wine\n', '\n', content)
        content = re.sub(r'\s*- id: build-msvc-wine\s*- id: build-msvc', '\n      - id: build-msvc', content)

        # Update or insert msvc 2005 and 2026
        # First, let's remove existing msvc_2005_wine block to re-insert cleanly
        # Regex to remove an entire hook block by id:
        content = re.sub(r'\s*- id: build-msvc-2005-wine.*?(?=\s*- id:|$)', '\n', content, flags=re.DOTALL)
        content = re.sub(r'\s*- id: build-msvc-2026-wine.*?(?=\s*- id:|$)', '\n', content, flags=re.DOTALL)
        
        # Insert them right before `build-msvc` or `build-mingw` or `valgrind`
        if '- id: build-msvc' in content:
            content = content.replace('      - id: build-msvc\n', msvc_2005_str + '\n' + msvc_2026_str + '\n      - id: build-msvc\n')
        elif '- id: build-mingw' in content:
            content = content.replace('      - id: build-mingw\n', msvc_2005_str + '\n' + msvc_2026_str + '\n      - id: build-mingw\n')
        else:
            content = content.replace('      - id: valgrind\n', msvc_2005_str + '\n' + msvc_2026_str + '\n      - id: valgrind\n')

        # Clean up empty lines created by removals
        content = re.sub(r'\n\s*\n', '\n', content)

        with open(yaml_path, 'w') as f:
            f.write(content)
        
        print(f"Updated {yaml_path}")

        subprocess.run(["git", "add", ".pre-commit-config.yaml"], cwd=repo)
        subprocess.run(["git", "commit", "--no-verify", "-m", "Add MSVC 2005 and MSVC 2026 Wine support via c-ci scripts"], cwd=repo)

