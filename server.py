import os

from flask import Flask, jsonify, request
from openai import OpenAI

from agent import list_files, run_agent

app = Flask(__name__)


@app.get("/api/files")
def files():
    workspace = os.getenv("AGENT_WORKSPACE", ".")
    return jsonify(list_files(".", workspace))


@app.post("/api/run")
def run():
    data = request.get_json()
    task = data.get("task", "").strip()
    if not task:
        return jsonify({"error": "task cannot be empty"}), 400

    workspace = os.getenv("AGENT_WORKSPACE", ".")
    events = []

    client = OpenAI(
        api_key=os.environ["ZAI_API_KEY"],
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )

    result = run_agent(
        client,
        os.getenv("ZAI_MODEL", "glm-4.7-flash"),
        task,
        workspace=workspace,
        on_event=events.append,
    )

    return jsonify({
        "result": result,
        "events": events,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)