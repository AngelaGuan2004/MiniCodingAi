def read_file(path: str) -> str:
    print("read_file path:", repr(path))
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    print("read_file content:", repr(content))
    return content