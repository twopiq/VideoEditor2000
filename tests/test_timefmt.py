import pytest

from videoeditor.core.timefmt import format_size, format_time, parse_time


def test_format_time():
    assert format_time(0) == "00:00.000"
    assert format_time(12.3456) == "00:12.346"
    assert format_time(3723.5) == "1:02:03.500"
    assert format_time(59.9999) == "01:00.000"
    assert format_time(83, millis=False) == "01:23"


@pytest.mark.parametrize(
    "text,value",
    [("83.5", 83.5), ("83,5", 83.5), ("1:23.5", 83.5), ("01:02:03", 3723), (" 0:05 ", 5)],
)
def test_parse_time(text, value):
    assert parse_time(text) == pytest.approx(value)


@pytest.mark.parametrize("text", ["", "abc", "1:60", "1::2", "1:2:3:4", "-5"])
def test_parse_time_invalid(text):
    with pytest.raises(ValueError):
        parse_time(text)


def test_roundtrip():
    for t in (0, 1.25, 61.5, 3599.999, 7322.042):
        assert parse_time(format_time(t)) == pytest.approx(t, abs=1e-3)


def test_format_size():
    assert format_size(512) == "512 B"
    assert format_size(1536) == "1.5 KB"
    assert format_size(5 * 1024**3) == "5.0 GB"
