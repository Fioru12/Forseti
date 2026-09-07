from core.nis2_scope import estimate_nis2_applicability, NOT_LISTED


def test_sector_not_listed_is_probably_out_of_scope():
    result = estimate_nis2_applicability(NOT_LISTED, employees=20, turnover_millions=3.0)
    assert result["likely_in_scope"] is False
    assert result["entity_type"] is None
    assert "disclaimer" in result and result["disclaimer"]


def test_annex_i_sector_medium_size_is_likely_in_scope_as_essential():
    result = estimate_nis2_applicability("energia", employees=80, turnover_millions=15.0)
    assert result["likely_in_scope"] is True
    assert result["entity_type"] == "essenziale"
    assert result["size_class"] == "media"


def test_annex_ii_sector_large_size_is_likely_in_scope_as_important():
    result = estimate_nis2_applicability("alimentare", employees=300, turnover_millions=60.0)
    assert result["likely_in_scope"] is True
    assert result["entity_type"] == "importante"
    assert result["size_class"] == "grande"


def test_annex_sector_but_micro_size_is_uncertain_not_a_flat_no():
    result = estimate_nis2_applicability("manifatturiero", employees=4, turnover_millions=0.5)
    assert result["likely_in_scope"] is None
    assert result["entity_type"] == "importante"
    assert result["size_class"] == "micro"
    assert "eccezioni" in result["reasoning"]


def test_annex_sector_small_size_is_uncertain():
    result = estimate_nis2_applicability("sanita", employees=30, turnover_millions=5.0)
    assert result["likely_in_scope"] is None
    assert result["size_class"] == "piccola"


def test_size_thresholds_use_employees_or_turnover():
    # 5 employees but very high turnover should still classify as "grande".
    result = estimate_nis2_applicability("bancario", employees=5, turnover_millions=100.0)
    assert result["size_class"] == "grande"
    assert result["likely_in_scope"] is True


def test_unknown_sector_string_falls_back_to_not_listed_behavior():
    result = estimate_nis2_applicability("settore_inesistente_a_caso", employees=500, turnover_millions=200.0)
    assert result["likely_in_scope"] is False
