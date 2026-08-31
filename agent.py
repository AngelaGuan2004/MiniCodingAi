import subprocess

def read_file(path: str) -> str:
    print("read_file path:", repr(path))
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    print("read_file content:", repr(content))
    return content

def write_file(path: str, content: str) -> None:
    print("write_file path:", repr(path))
    print("write_file content:", repr(content))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_command(command: str, timeout: float = 10) -> dict:
    print("run_command command:", repr(command))
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    print("run_command result:", output)
    return output