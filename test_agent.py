from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import json
from agent import read_file, write_file, run_command, call_model, TOOLS, execute_tool


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



def fake_client(message=None, error=None):
    calls = {}

    def create(**kwargs):
        calls.update(kwargs)
        if error:
            raise error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)]
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )
    )
    return client, calls


def test_call_model_text():
    msg = SimpleNamespace(
        model_dump=lambda exclude_none=True:
        {"role": "assistant", "content": "done"}
    )
    client, calls = fake_client(msg)
    messages = [{"role": "user", "content": "hello"}]

    result = call_model(client, "demo-model", messages, [])

    print("text model result:", result)
    assert result == {"role": "assistant", "content": "done"}
    assert calls["model"] == "demo-model"
    assert calls["messages"] == messages
    assert calls["tools"] == []


def test_call_model_tool_call():
    expected = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": "1", "type": "function"}],
    }
    msg = SimpleNamespace(
        model_dump=lambda exclude_none=True: expected
    )
    client, _ = fake_client(msg)

    result = call_model(client, "demo-model", [], [])

    print("tool model result:", result)
    assert result == expected


def test_call_model_error():
    client, _ = fake_client(error=RuntimeError("API failed"))
    try:
        call_model(client, "demo-model", [], [])
        assert False, "API error should propagate"
    except RuntimeError:
        print("model API error correctly propagated")


def test_tools_schema():
    assert len(TOOLS) == 3

    functions = {tool["function"]["name"]: tool["function"]
                 for tool in TOOLS}
    print("tool names:", list(functions))

    assert set(functions) == {
        "read_file", "write_file", "run_command"
    }

    assert functions["read_file"]["parameters"]["required"] == ["path"]
    assert functions["write_file"]["parameters"]["required"] == [
        "path", "content"
    ]
    assert functions["run_command"]["parameters"]["required"] == ["command"]

    for function in functions.values():
        assert function["parameters"]["type"] == "object"
        assert "description" in function



def test_execute_tool_read():
    path = Path("tmp_execute.txt")
    path.write_text("agent data", encoding="utf-8")

    result = json.loads(
        execute_tool("read_file", '{"path":"tmp_execute.txt"}')
    )
    print("execute read result:", result)

    assert result == {"ok": True, "result": "agent data"}
    path.unlink()


def test_execute_tool_write():
    result = json.loads(
        execute_tool(
            "write_file",
            '{"path":"tmp_execute_write.txt","content":"hello"}',
        )
    )
    print("execute write result:", result)

    assert result == {"ok": True, "result": None}
    assert Path("tmp_execute_write.txt").read_text(
        encoding="utf-8"
    ) == "hello"
    Path("tmp_execute_write.txt").unlink()


def test_execute_tool_unknown():
    result = json.loads(execute_tool("unknown", "{}"))
    print("unknown tool result:", result)

    assert result["ok"] is False
    assert "unknown" in result["error"]


def test_execute_tool_bad_arguments():
    result = json.loads(execute_tool("read_file", "{bad json"))
    print("bad arguments result:", result)

    assert result["ok"] is False

test_execute_tool_read()
test_execute_tool_write()
test_execute_tool_unknown()
test_execute_tool_bad_arguments()
print("all execute_tool tests passed")