"""Pure-logic tests for etl.clean_dataframe — no credentials or network needed."""

import pandas as pd

from skills.etl import clean_dataframe


def test_drops_fully_empty_rows():
    df = pd.DataFrame({"Nome ": ["Rossi", "  ", None], " Città": ["Napoli", "", None]})
    cleaned, report = clean_dataframe(df)
    assert len(cleaned) == 1
    assert report["empty_rows_removed"] == 2


def test_strips_whitespace_from_text_columns():
    df = pd.DataFrame({"nome": [" Rossi ", "Bianchi"]})
    cleaned, report = clean_dataframe(df)
    assert list(cleaned["nome"]) == ["Rossi", "Bianchi"]
    assert report["cells_stripped"] == 1


def test_standardises_column_names():
    df = pd.DataFrame({"Nome Cliente ": ["Rossi"], " Città": ["Napoli"]})
    cleaned, report = clean_dataframe(df)
    assert list(cleaned.columns) == ["nome_cliente", "città"]
    assert len(report["columns_renamed"]) == 2


def test_resolves_column_name_collisions():
    df = pd.DataFrame([[1, 2]], columns=["Col A", "Col-A"])
    cleaned, _ = clean_dataframe(df)
    assert list(cleaned.columns) == ["col_a", "col_a_1"]
