"""The same real captions the screen's tests use: the Word files and the screen must name a case alike."""
import pytest

from caselens.domain.services.case_names import division_name, justice_name, short_case_name, surname_only

MARCOS = (
    "FERDINAND E. MARCOS, IMELDA R. MARCOS, FERDINAND R. MARCOS, JR., IRENE M. ARANETA, PACIFICO E. MARCOS and PHILIPPINE CONSTITUTION ASSOCIATION "
    "(PHILCONSA), represented by its President, CONRADO F. ESTRELLA, petitioners, vs. HONORABLE RAUL MANGLAPUS, CATALINO MACARAIG, SEDFREY ORDOÑEZ, "
    "MIRIAM DEFENSOR SANTIAGO, respondents."
)
BANDA = "ATTY. SYLVIA BANDA, CONSORICIA O. PENSON, RADITO V. PADRIGANO, JEAN R. DE MESA, Petitioners, vs. EDUARDO R. ERMITA, in his capacity as Executive Secretary, The National Treasurer, Respondents."


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (MARCOS, "Ferdinand E. Marcos et al. v. Honorable Raul Manglapus et al."),
        (BANDA, "Atty. Sylvia Banda et al. v. Eduardo R. Ermita et al."),
        ("ALPHA CORP, Petitioner, vs. BETA INC., Respondent.", "Alpha Corp v. Beta Inc."),
        ("PNB, Petitioner, vs. COMELEC, Respondent.", "PNB v. COMELEC"),
        ("Ople v. Torres", "Ople v. Torres"),
        ("ERNESTO MARCELO, JR. and LAURO LLAMES, Petitioners, vs. RAFAEL R. VILLORDON, Respondent.", "Ernesto Marcelo, Jr. et al. v. Rafael R. Villordon"),
        ("ACME, INC., Petitioner, vs. BETA CORP., Respondent.", "Acme, Inc. v. Beta Corp."),
        ("AQUILINO PIMENTEL III; ERNESTO OFRACIO; JANICE LIRZA MELGAR; PHILIPPINE MEDICAL ASSOCIATION, PETITIONERS,", "Aquilino Pimentel III et al."),
        (None, "Untitled case"),
    ],
)
def test_a_caption_becomes_a_readable_name(title, expected):
    assert short_case_name(title) == expected


def test_the_form_lawyers_cite():
    assert surname_only(short_case_name(MARCOS)) == "Marcos v. Manglapus"
    assert surname_only("Alicia D. Tagaro v. Ester A. Garcia et al.") == "Tagaro v. Garcia"
    assert surname_only("Ople v. Torres") == "Ople v. Torres"
    # an organisation keeps its name; only a person is cut down to a surname
    assert surname_only("Review Center Association of the Philippines v. Executive Secretary Eduardo Ermita et al.") == "Review Center Association of the Philippines v. Ermita"
    assert surname_only("Rosario S. Panuncio v. People of the Philippines") == "Panuncio v. People of the Philippines"
    assert surname_only("LPBS Commercial, Inc. v. Hon. Venancio J. Amila et al.") == "LPBS Commercial, Inc. v. Amila"


def test_justices_and_divisions():
    assert justice_name("CORTES, J.:".rstrip(":")) == "Cortes, J."
    assert justice_name("VELASCO, JR.") == "Velasco, Jr."
    assert division_name("EN BANC") == "En Banc" and division_name("SECOND DIVISION") == "Second Division"
