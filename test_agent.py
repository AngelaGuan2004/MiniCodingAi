from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import json
import os
import builtins
import agent

from agent import (
    list_files, read_file, write_file, run_command, call_model,
    TOOLS, execute_tool, run_agent, main, read_task
)


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
    assert len(TOOLS) == 4

    functions = {tool["function"]["name"]: tool["function"]
                 for tool in TOOLS}
    print("tool names:", list(functions))

    assert set(functions) == {
        "list_files", "read_file", "write_file", "run_command"
    }

    assert functions["list_files"]["parameters"]["required"] == []
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


def test_run_agent_tool_loop():
    path = Path("tmp_agent_loop.txt")
    path.write_text("loop data", encoding="utf-8")
    replies = iter([
        {"role": "assistant", "content": None, "tool_calls": [{
            "id": "call_1", "type": "function",
            "function": {"name": "read_file",
                         "arguments": '{"path":"tmp_agent_loop.txt"}'}
        }]},
        {"role": "assistant", "content": "任务完成"},
    ])
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        data = next(replies)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(
                model_dump=lambda exclude_none=True, d=data: d)
        )])

    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)))

    result = run_agent(client, "demo-model", "读取测试文件")
    print("agent result:", result)
    print("second request messages:", requests[1]["messages"])

    assert result == "任务完成"
    assert requests[1]["messages"][-1]["role"] == "tool"
    assert "loop data" in requests[1]["messages"][-1]["content"]
    path.unlink()


def test_run_agent_max_steps():
    msg = SimpleNamespace(model_dump=lambda exclude_none=True: {
        "role": "assistant", "content": None, "tool_calls": [{
            "id": "1", "type": "function",
            "function": {"name": "unknown", "arguments": "{}"}
        }]
    })
    client, _ = fake_client(msg)
    try:
        run_agent(client, "demo-model", "无限任务", max_steps=1)
        assert False, "max steps should raise RuntimeError"
    except RuntimeError:
        print("agent correctly stopped at max steps")

def test_main_normal():
    calls = {}
    old_key = os.environ.get("ZAI_API_KEY")
    old_input = builtins.input
    old_openai = agent.OpenAI
    old_run_agent = agent.run_agent

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls["client"] = kwargs

    def fake_run_agent(
        client,
        model,
        task,
        workspace=".",
    ):
        calls["model"] = model
        calls["task"] = task
        return "完成"

    try:
        os.environ["ZAI_API_KEY"] = "fake-key"
        lines = iter(["修复测试代码", ""])
        builtins.input = lambda prompt="": next(lines)
        agent.OpenAI = FakeOpenAI
        agent.run_agent = fake_run_agent

        result = main()
    finally:
        builtins.input = old_input
        agent.OpenAI = old_openai
        agent.run_agent = old_run_agent
        if old_key is None:
            os.environ.pop("ZAI_API_KEY", None)
        else:
            os.environ["ZAI_API_KEY"] = old_key

    assert result == "完成"
    assert calls["model"] == "glm-4.7-flash"
    assert calls["task"] == "修复测试代码"
    assert calls["client"]["api_key"] == "fake-key"


def test_main_empty_task():
    old_input = builtins.input
    lines = iter([""])
    builtins.input = lambda prompt="": next(lines)
    try:
        try:
            main()
            assert False, "empty task should raise ValueError"
        except ValueError:
            print("empty task correctly rejected")
    finally:
        builtins.input = old_input


def test_main_missing_key():
    old_key = os.environ.pop("ZAI_API_KEY", None)
    old_input = builtins.input
    lines = iter(["读取文件", ""])
    builtins.input = lambda prompt="": next(lines)

    try:
        try:
            main()
            assert False, "missing API key should raise KeyError"
        except KeyError:
            print("missing API key correctly rejected")
    finally:
        builtins.input = old_input
        if old_key is not None:
            os.environ["ZAI_API_KEY"] = old_key



def test_read_task_multiline():
    lines = iter(["第一行", "第二行", ""])
    result = agent.read_task(lambda prompt="": next(lines))
    assert result == "第一行\n第二行"


def test_read_task_empty():
    lines = iter([""])
    try:
        agent.read_task(lambda prompt="": next(lines))
        assert False
    except ValueError:
        pass
    
def test_list_files():
    root = Path("tmp_list_files")
    (root / "pkg").mkdir(parents=True)
    (root / "node_modules").mkdir()
    (root / "a.py").write_text("", encoding="utf-8")
    (root / "pkg" / "b.py").write_text("", encoding="utf-8")
    (root / "node_modules" / "ignored.js").write_text("", encoding="utf-8")

    result = list_files(str(root))

    assert result == [
        "tmp_list_files/a.py",
        "tmp_list_files/pkg/b.py",
    ]

    (root / "a.py").unlink()
    (root / "pkg" / "b.py").unlink()
    (root / "node_modules" / "ignored.js").unlink()
    (root / "pkg").rmdir()
    (root / "node_modules").rmdir()
    root.rmdir()


def test_execute_tool_list_files():
    root = Path("tmp_execute_list")
    root.mkdir()
    (root / "demo.py").write_text("", encoding="utf-8")

    result = json.loads(
        execute_tool("list_files", '{"path":"tmp_execute_list"}')
    )

    assert result["ok"] is True
    assert result["result"] == ["tmp_execute_list/demo.py"]

    (root / "demo.py").unlink()
    root.rmdir()

def test_workspace_blocks_escape():
    root = Path("tmp_workspace")
    root.mkdir()

    try:
        try:
            read_file("../agent.py", workspace=str(root))
            assert False, "workspace escape should fail"
        except ValueError:
            pass
    finally:
        root.rmdir()


def test_run_command_workspace():
    root = Path("tmp_command_workspace")
    root.mkdir()

    try:
        cmd = (
            f'"{sys.executable}" '
            '-c "import os; print(os.getcwd())"'
        )
        result = run_command(cmd, workspace=str(root))

        assert Path(result["stdout"].strip()).resolve() == root.resolve()
    finally:
        root.rmdir()


def test_list_files_workspace_relative():
    root = Path("tmp_list_workspace")
    root.mkdir()
    (root / "demo.py").write_text("", encoding="utf-8")

    try:
        assert list_files(".", workspace=str(root)) == ["demo.py"]
    finally:
        (root / "demo.py").unlink()
        root.rmdir()


def test_main_model_override():
    calls = {}
    old_key = os.environ.get("ZAI_API_KEY")
    old_model = os.environ.get("ZAI_MODEL")
    old_input = builtins.input
    old_openai = agent.OpenAI
    old_run_agent = agent.run_agent

    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass

    def fake_run_agent(
        client,
        model,
        task,
        workspace=".",
    ):
        calls["model"] = model
        return "完成"

    try:
        os.environ["ZAI_API_KEY"] = "fake-key"
        os.environ["ZAI_MODEL"] = "glm-4.7"
        lines = iter(["修复代码", ""])
        builtins.input = lambda prompt="": next(lines)
        agent.OpenAI = FakeOpenAI
        agent.run_agent = fake_run_agent
        main()
    finally:
        builtins.input = old_input
        agent.OpenAI = old_openai
        agent.run_agent = old_run_agent

        if old_key is None:
            os.environ.pop("ZAI_API_KEY", None)
        else:
            os.environ["ZAI_API_KEY"] = old_key

        if old_model is None:
            os.environ.pop("ZAI_MODEL", None)
        else:
            os.environ["ZAI_MODEL"] = old_model

    assert calls["model"] == "glm-4.7"

TESTS = [
    value for name, value in list(globals().items())
    if name.startswith("test_") and callable(value)
]

for test in TESTS:
    test()

print(f"all {len(TESTS)} tests passed")