from pathlib import Path

from echoscribe.config import output_session_dir
from echoscribe.core.media import is_supported_media, safe_stem


def test_supported_media_extensions():
    assert is_supported_media(Path("demo.mp4"))
    assert is_supported_media(Path("demo.MP3"))
    assert not is_supported_media(Path("demo.txt"))


def test_safe_stem_keeps_chinese_and_normalizes_symbols():
    assert safe_stem(Path("中文 文件!.mp4")) == "中文_文件"


def test_output_session_dir_uses_timestamp_and_label(tmp_path):
    path = output_session_dir("my audio", root=tmp_path)

    assert path.parent == tmp_path
    assert path.exists()
    assert path.name.endswith("-my_audio")
    assert len(path.name.split("-")) >= 4
