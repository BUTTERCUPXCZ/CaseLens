from pathlib import Path

import pytest

from caselens.infrastructure.lawphil.html_decoding import decode_html

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_the_real_lawphil_page_keeps_its_curly_apostrophes():
    """GR 180046 declares windows-1252 only in a <meta> tag. Decoded as UTF-8 it lost 81
    characters to U+FFFD, including the apostrophe in "Center's President"."""
    html = decode_html((FIXTURES / "gr_180046_2009.html").read_bytes(), "text/html")

    assert "�" not in html
    assert "Inress Review Center’s President" in html


def test_a_charset_in_the_http_header_wins():
    assert decode_html("café".encode("utf-8"), "text/html; charset=utf-8") == "café"
    assert decode_html("café".encode("cp1252"), 'text/html; charset="windows-1252"') == "café"


def test_the_meta_tag_is_used_when_the_header_says_nothing():
    page = b'<html><head><meta http-equiv="content-type" content="text/html; charset=windows-1252"></head>OSG\x92s'
    assert decode_html(page, "text/html").endswith("OSG’s")


def test_a_plain_utf8_page_needs_no_declaration():
    assert decode_html("Ang Tibay v. CIR — “plenary”".encode("utf-8")) == "Ang Tibay v. CIR — “plenary”"


def test_iso_8859_1_is_read_as_windows_1252_like_browsers_do():
    assert decode_html(b"it\x92s", "text/html; charset=iso-8859-1") == "it’s"


def test_an_unknown_charset_name_is_ignored_not_fatal():
    assert decode_html(b"plain text", "text/html; charset=no-such-charset") == "plain text"


def test_undecodable_bytes_are_replaced_instead_of_crashing():
    # 0x81 is undefined in Windows-1252 and invalid as UTF-8: the last resort must still return text.
    assert decode_html(b"before\x81after") == "before�after"


@pytest.mark.parametrize("declared", ["utf-8", "UTF-8"])
def test_declared_utf8_that_is_actually_cp1252_falls_back_cleanly(declared):
    assert decode_html(b"it\x92s", f"text/html; charset={declared}") == "it’s"
