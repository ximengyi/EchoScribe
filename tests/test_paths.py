from pathlib import Path

from echoscribe.core.media import is_supported_media, safe_stem


def test_supported_media_extensions():
    assert is_supported_media(Path("demo.mp4"))
    assert is_supported_media(Path("demo.MP3"))
    assert not is_supported_media(Path("demo.txt"))


def test_safe_stem_keeps_chinese_and_normalizes_symbols():
    assert safe_stem(Path("中文 文件!.mp4")) == "中文_文件"

