from pathlib import Path
import subprocess
import sys

from agent import read_file, write_file, run_command


def test_read_normal_file():
    path = Path("tmp_read_test.txt")
    path.write_text("hello agent\n第二行", encoding="utf-8")

    result = read_file(str(path))
    print("normal result:", repr(result))

    assert result == "hello agent\n第二行"
    path.unlink()


def test_read_empty_file():
    path = Path("tmp_empty_test.txt")
    path.write_text("", encoding="utf-8")

    result = read_file(str(path))
    print("empty result:", repr(result))

    assert result == ""
    path.unlink()


def test_missing_file_raises():
    try:
        read_file("definitely_missing_file.txt")
        assert False, "missing file should raise FileNotFoundError"
    except FileNotFoundError:
        print("missing file correctly raised FileNotFoundError")



def test_write_normal_file():
    path = Path("tmp_write_test.txt")
    write_file(str(path), "hello\n你好")
    print("written content:", repr(path.read_text(encoding="utf-8")))

    assert path.read_text(encoding="utf-8") == "hello\n你好"
    path.unlink()


def test_write_empty_file():
    path = Path("tmp_write_empty.txt")
    write_file(str(path), "")
    print("empty file size:", path.stat().st_size)

    assert path.read_text(encoding="utf-8") == ""
    path.unlink()


def test_write_missing_parent_raises():
    try:
        write_file("tmp_missing_dir/file.txt", "data")
        assert False, "missing parent should raise FileNotFoundError"
    except FileNotFoundError:
        print("missing parent correctly raised FileNotFoundError")



def test_run_command_success():
    cmd = f'"{sys.executable}" -c "print(123)"'
    result = run_command(cmd)
    print("success result:", result)

    assert result["returncode"] == 0
    assert result["stdout"].strip() == "123"
    assert result["stderr"] == ""


def test_run_command_failure():
    cmd = f'"{sys.executable}" -c "import sys; sys.stderr.write(\'bad\'); sys.exit(2)"'
    result = run_command(cmd)
    print("failure result:", result)

    assert result["returncode"] == 2
    assert result["stderr"] == "bad"


def test_run_command_timeout():
    cmd = f'"{sys.executable}" -c "import time; time.sleep(2)"'

    try:
        run_command(cmd, timeout=0.1)
        assert False, "timeout should raise TimeoutExpired"
    except subprocess.TimeoutExpired:
        print("command correctly timed out")


test_run_command_success()
test_run_command_failure()
test_run_command_timeout()
print("all run_command tests passed")