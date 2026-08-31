from pathlib import Path
from agent import read_file, write_file


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


test_write_normal_file()
test_write_empty_file()
test_write_missing_parent_raises()
print("all write_file tests passed")