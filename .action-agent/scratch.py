"""
run = false
name = "OP13AirDrop baseline diagnosis"
reason = "Run the repository's documented host-side checks and regression suites before making a repair."
timeout = 1800
priority = 10

[commands]
before = []
run = ["python .action-agent/scratch.py"]
after = []

[output]
mode = "both"
path = ".action-agent/output/op13airdrop-baseline.log"
artifact = true
commit = false

[execution]
cwd = "."
shell = "bash"
continue_on_error = false
reset_on = "always"
after = "always"
"""

from pathlib import Path
import subprocess
import sys

target = Path(".action-agent/tmp/OP13AirDrop_")
target.parent.mkdir(parents=True, exist_ok=True)

def run(label, command, cwd, timeout=900):
    print("\n" + "=" * 76)
    print(label)
    print("$ " + " ".join(command))
    print("=" * 76, flush=True)
    try:
        result = subprocess.run(
            command, cwd=str(cwd), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout
        )
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        print(f"\n[{label}] exit={result.returncode}", flush=True)
        return result.returncode
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        if output:
            print(output, end="" if output.endswith("\n") else "\n")
        print(f"\n[{label}] TIMEOUT after {timeout}s", flush=True)
        return 124

print("ActionAgent diagnostic task: OP13AirDrop_")
print("This is a read-only baseline. It does not modify the target repository.")
print("Runtime versions:")
for command in (["python3", "--version"], ["git", "--version"],
                ["node", "--version"], ["npm", "--version"],
                ["java", "-version"], ["javac", "-version"]):
    run("runtime: " + command[0], command, Path("."), timeout=20)

if not (target / ".git").exists():
    code = run(
        "clone target repository",
        ["git", "clone", "--depth", "1",
         "https://github.com/martian53058/OP13AirDrop_.git", str(target)],
        Path(".action-agent/tmp"), timeout=300
    )
    if code != 0:
        raise SystemExit(code)

failures = []
checks = [
    ("source namespace, Python and shell syntax, kernel hashes",
     ["python3", "tools/check.py"], target, 180),
    ("all Python host regression tests",
     ["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
     target, 900),
    ("WebUI API tests", ["node", "tests/test-api.mjs"], target, 180),
    ("WebUI refresh tests", ["node", "tests/test-webui-refresh.mjs"], target, 180),
    ("OShare JVM regression tests", ["sh", "oshare/tests/run.sh"], target, 300),
    ("WebUI dependency install", ["npm", "ci", "--no-audit", "--no-fund"], target / "webui", 900),
    ("WebUI TypeScript check", ["npm", "run", "check"], target / "webui", 300),
    ("WebUI production build", ["npm", "run", "build"], target / "webui", 300),
]

for label, command, cwd, timeout in checks:
    code = run(label, command, cwd, timeout=timeout)
    if code != 0:
        failures.append((label, code))

print("\n" + "=" * 76)
print("BASELINE SUMMARY")
print(f"Checks: {len(checks)}; failures: {len(failures)}")
for label, code in failures:
    print(f"FAILED ({code}): {label}")
if not failures:
    print("All host-side baseline checks passed.")
print("No source files in OP13AirDrop_ were modified.")
print("=" * 76, flush=True)

raise SystemExit(1 if failures else 0)
