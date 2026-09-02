import subprocess
import json
import os
from pathlib import Path
import difflib
from openai import OpenAI

SYSTEM_PROMPT = (
    "你是本地 Coding Agent。所有文件路径和命令都以当前 workspace 为根目录。"
    "只探索和修改当前任务相关的文件，不要修改测试来规避问题。"
    "修改后运行与任务直接相关的测试或验证。"
    "一旦相关验证成功，立即结束并总结，不要继续运行无关脚本。"
    "如果现有相关测试已经通过且没有可复现失败，不要自行发明新的需求、"
    "边界条件或 bug；直接说明当前无法复现并结束。"
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "递归列出目录中的项目文件，用于探索代码仓库结构",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要探索的目录，默认当前目录",
                        "default": ".",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取UTF-8文本文件的完整内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将UTF-8文本内容写入文件并覆盖原内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "写入内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "在本地Shell中执行命令",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell命令"}
                },
                "required": ["command"],
            },
        },
    },
]

# print("TOOLS:", [tool["function"]["name"] for tool in TOOLS])
def resolve_path(workspace: str, path: str) -> Path:
    root = Path(workspace).resolve()
    target = (root / path).resolve()

    if target != root and root not in target.parents:
        raise ValueError(f"path outside workspace: {path}")

    return target

def list_files(path: str = ".", workspace: str = ".") -> list[str]:
    print("list_files path:", repr(path))
    root = resolve_path(workspace, path)

    if not root.is_dir():
        raise FileNotFoundError(path)

    workspace_root = Path(workspace).resolve()
    ignored = {
        ".git", "__pycache__", ".venv", "venv", "env",
        "node_modules", "build", "dist",
    }
    files = []

    for current, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in ignored]
        for name in names:
            file_path = Path(current) / name
            files.append(
                file_path.relative_to(workspace_root).as_posix()
            )

    return sorted(files)


def read_file(path: str, workspace: str = ".") -> str:
    print("read_file path:", repr(path))
    target = resolve_path(workspace, path)

    with open(target, "r", encoding="utf-8") as f:
        return f.read()

def write_file(
    path: str,
    content: str,
    workspace: str = ".",
) -> None:
    print("write_file path:", repr(path))
    target = resolve_path(workspace, path)

    with open(target, "w", encoding="utf-8") as f:
        f.write(content)


def run_command(
    command: str,
    timeout: float = 10,
    workspace: str = ".",
) -> dict:
    print("run_command command:", repr(command))
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=Path(workspace).resolve(),
    )
    output = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    # print("run_command result:", output)
    print("returncode:", result.returncode)
    if result.stdout:
        print("stdout:", repr(result.stdout))
    if result.stderr:
        print("stderr:", repr(result.stderr))
    return output

def read_task(input_fn=None) -> str:
    if input_fn is None:
        input_fn = input

    print("请输入（回车2次以运行）：")
    lines = []

    while True:
        line = input_fn()
        if line == "":
            break
        lines.append(line)

    task = "\n".join(lines).strip()
    if not task:
        raise ValueError("task cannot be empty")

    return task


def call_model(client, model: str, messages: list, tools: list) -> dict:
    # print("call_model messages:", messages)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    )
    result = response.choices[0].message.model_dump(exclude_none=True)
    result.setdefault("content", None)
    # print("call_model result:", result)
    return result

def execute_tool(
    name: str,
    arguments_json: str,
    workspace: str = ".",
    on_event=None,
) -> str:
    print("execute_tool name:", name)

    try:
        arguments = json.loads(arguments_json)

        if on_event:
            detail = arguments.get(
                "path", arguments.get("command", "")
            )
            on_event({
                "type": "tool_start",
                "tool": name,
                "detail": detail,
            })

        if name == "list_files":
            result = list_files(
                arguments.get("path", "."),
                workspace,
            )
        elif name == "read_file":
            result = read_file(arguments["path"], workspace)
        elif name == "write_file":
            path = arguments["path"]
            target = resolve_path(workspace, path)
            old = (
                target.read_text(encoding="utf-8")
                if target.exists() else ""
            )
            content = arguments["content"]
            result = write_file(path, content, workspace)

            if on_event:
                diff = "".join(difflib.unified_diff(
                    old.splitlines(True),
                    content.splitlines(True),
                    fromfile=path,
                    tofile=path,
                ))
                on_event({
                    "type": "file_changed",
                    "path": path,
                    "diff": diff,
                })
        elif name == "run_command":
            result = run_command(
                arguments["command"],
                workspace=workspace,
            )
            if on_event:
                on_event({
                    "type": "command_result",
                    "command": arguments["command"],
                    **result,
                })
        else:
            raise ValueError(f"unknown tool: {name}")

        output = {"ok": True, "result": result}
    except Exception as error:
        output = {"ok": False, "error": str(error)}

    return json.dumps(output, ensure_ascii=False)

def run_agent(
    client,
    model: str,
    task: str,
    max_steps: int = 15,
    workspace: str = ".",
    on_event=None,
) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    # print("run_agent task:", repr(task))
    print("agent started")

    if on_event:
        on_event({
            "type": "agent_start",
            "task": task,
            "workspace": workspace,
        })

    for step in range(max_steps):
        print("run_agent step:", step + 1)
        if on_event:
            on_event({
                "type": "step",
                "step": step + 1,
            })
        reply = call_model(client, model, messages, TOOLS)
        tool_calls = reply.get("tool_calls")

        if tool_calls:
            print(
                "tools:",
                [call["function"]["name"] for call in tool_calls],
            )
        if not tool_calls:
            result = reply.get("content") or ""

            if on_event:
                on_event({
                    "type": "agent_done",
                    "result": result,
                })

            return result

        messages.append(reply)

        for tool_call in tool_calls:
            function = tool_call["function"]
            result = execute_tool(
                function["name"],
                function["arguments"],
                workspace,
                on_event,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

    raise RuntimeError(
        f"agent exceeded maximum steps: {max_steps}"
    )

def main() -> str:
    task = read_task()
    if not task:
        raise ValueError("task cannot be empty")

    api_key = os.environ["ZAI_API_KEY"]
    model = os.getenv("ZAI_MODEL", "glm-4.7-flash")
    client = OpenAI(
        api_key=api_key,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )
    workspace = os.getenv("AGENT_WORKSPACE", ".")
    print("workspace:", str(Path(workspace).resolve()))

    # result = run_agent(client, "glm-4.7-flash", task)
    result = run_agent(
        client,
        model,
        task,
        workspace=workspace,
    )
    print("\nResult:")
    print(result)
    return result


if __name__ == "__main__":
    main()