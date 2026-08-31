from pathlib import Path
from agent import read_file


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


test_read_normal_file()
test_read_empty_file()
test_missing_file_raises()
print("all read_file tests passed")