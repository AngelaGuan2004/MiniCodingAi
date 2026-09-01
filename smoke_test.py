import os
from openai import OpenAI
from agent import run_agent

client = OpenAI(
    api_key=os.environ["ZAI_API_KEY"],
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

result = run_agent(
    client,
    "glm-4.7-flash",
    "必须先使用 read_file 读取 agent.py，然后告诉我 TOOLS 中定义了几个工具，以及它们的名称。",
)

print("FINAL:", result)