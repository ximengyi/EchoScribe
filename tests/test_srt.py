from echoscribe.core.subtitles import Segment, format_timestamp, to_plain_txt, to_srt, to_txt


def test_format_timestamp_for_srt():
    assert format_timestamp(62.3456, sep=",") == "00:01:02,346"


def test_srt_output():
    srt = to_srt([Segment(0, 1.2, "hello"), Segment(1.2, 2.5, "world")])
    assert "1\n00:00:00,000 --> 00:00:01,200\nhello" in srt
    assert "2\n00:00:01,200 --> 00:00:02,500\nworld" in srt


def test_txt_output():
    txt = to_txt([Segment(0, 1.2, "hello")])
    assert txt == "[00:00.000 - 00:01.200] hello\n"


def test_plain_txt_output():
    txt = to_plain_txt([Segment(0, 1.2, "hello"), Segment(1.2, 2.5, "world")])
    assert txt == "hello\nworld\n"
