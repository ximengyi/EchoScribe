from echoscribe.core.text import should_simplify_language, to_simplified_chinese


def test_to_simplified_chinese_fallback_common_words():
    text = "這個軟體會錄製電腦聲音，並輸出轉錄文件。"

    assert to_simplified_chinese(text) == "这个软件会录制电脑声音，并输出转录文件。"


def test_should_simplify_language_only_chinese():
    assert should_simplify_language("zh")
    assert should_simplify_language("yue")
    assert not should_simplify_language("en")
    assert not should_simplify_language(None)
