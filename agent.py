import subprocess
import json
import os
from openai import OpenAI

TOOLS = [
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

def call_model(client, model: str, messages: list, tools: list) -> dict:
    print("call_model messages:", messages)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    )
    result = response.choices[0].message.model_dump(exclude_none=True)
    result.setdefault("content", None)
    print("call_model result:", result)
    return result

def execute_tool(name: str, arguments_json: str) -> str:
    print("execute_tool name:", name)
    print("execute_tool arguments:", arguments_json)

    try:
        arguments = json.loads(arguments_json)

        if name == "read_file":
            result = read_file(**arguments)
        elif name == "write_file":
            result = write_file(**arguments)
        elif name == "run_command":
            result = run_command(**arguments)
        else:
            raise ValueError(f"unknown tool: {name}")

        output = {"ok": True, "result": result}
    except Exception as error:
        output = {"ok": False, "error": str(error)}

    print("execute_tool result:", output)
    return json.dumps(output, ensure_ascii=False)

def run_agent(client, model: str, task: str, max_steps: int = 8) -> str:
    messages = [{"role": "user", "content": task}]
    print("run_agent task:", repr(task))

    for step in range(max_steps):
        print("run_agent step:", step + 1)
        reply = call_model(client, model, messages, TOOLS)
        tool_calls = reply.get("tool_calls")

        if not tool_calls:
            print("run_agent final:", repr(reply.get("content")))
            return reply.get("content") or ""

        messages.append(reply)

        for tool_call in tool_calls:
            function = tool_call["function"]
            result = execute_tool(
                function["name"],
                function["arguments"],
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
    task = input("Task: ").strip()
    if not task:
        raise ValueError("task cannot be empty")

    api_key = os.environ["ZAI_API_KEY"]
    client = OpenAI(
        api_key=api_key,
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )

    result = run_agent(client, "glm-4.7-flash", task)
    print("agent result:", result)
    return result


if __name__ == "__main__":
    main()