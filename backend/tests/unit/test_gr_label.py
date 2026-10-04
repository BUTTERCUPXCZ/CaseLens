from datetime import date

import pytest

from caselens.domain.services.gr_label import GrLabelReader

read = GrLabelReader().read


@pytest.mark.parametrize(
    "label, numbers, decided",
    [
        # every shape below was read from the real April 1987 / June 1995 / April 2009 / July 2015 lists
        ("G.R. No. 180923 April 30, 2009", ("180923",), date(2009, 4, 30)),
        ("G.R. No. L-28156 March 31, 1987", ("L-28156",), date(1987, 3, 31)),
        ("G.R. No. L-38513 March 31,1987", ("L-38513",), date(1987, 3, 31)),  # no space after the comma
        ("G.R. No. 170270 & 179411 April 2, 2009", ("170270", "179411"), date(2009, 4, 2)),
        ("G.R. Nos. 211972 & 212045 July 22, 2015", ("211972", "212045"), date(2015, 7, 22)),
        ("G.R. No. 164785 G.R. No. 165636 April 29, 2009", ("164785", "165636"), date(2009, 4, 29)),
        ("G.R. No. 148263 and 148271-72 April 21, 2009", ("148263", "148271", "148272"), date(2009, 4, 21)),
        ("G.R. Nos. 179240-41 April 1, 2009", ("179240", "179241"), date(2009, 4, 1)),
        (
            "G.R. No. 209353-54/G.R. Nos. 211733-34 July 6, 2015",
            ("209353", "209354", "211733", "211734"),
            date(2015, 7, 6),
        ),
    ],
)
def test_real_label_shapes(label, numbers, decided):
    assert read(label) == (numbers, decided)


def test_a_range_of_old_style_numbers_keeps_the_l_prefix():  # (synthetic)
    assert read("G.R. No. L-12091-92 January 5, 1960")[0] == ("L-12091", "L-12092")


def test_a_full_length_range_end_is_the_number_itself():  # (synthetic)
    assert read("G.R. Nos. 100000-100002 May 1, 2000")[0] == ("100000", "100001", "100002")


def test_an_absurd_range_is_not_expanded():  # (synthetic) 1,000 cases in one row is a typo
    assert read("G.R. No. 100000-100999 May 1, 2000")[0] == ("100000",)


def test_the_year_is_never_read_as_a_g_r_number():
    assert read("G.R. No. 155573 April 24, 2009")[0] == ("155573",)


def test_a_missing_or_impossible_date_is_none_but_numbers_survive():
    assert read("G.R. No. 155573") == (("155573",), None)
    assert read("G.R. No. 155573 February 31, 2009") == (("155573",), None)


def test_nothing_readable():
    assert read("") == ((), None)
