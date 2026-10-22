from uuid import uuid4

import pandas as pd
import pytest
from fastapi import HTTPException

from backend.utils import general_helper


def test_json_records_converts_missing_values_to_json_nulls():
    frame = pd.DataFrame(
        {
            "integer": pd.Series([1, pd.NA], dtype="Int64"),
            "text": ["present", None],
        }
    )

    assert general_helper.json_records(frame) == [
        {"integer": 1, "text": "present"},
        {"integer": None, "text": None},
    ]


@pytest.mark.parametrize(
    "dataset_id",
    [
        "",
        "-" * 36,
        "g" * 36,
        "{" + str(uuid4()) + "}",
        "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF",
        "../" + "a" * 33,
        None,
    ],
)
def test_safe_dataset_id_rejects_noncanonical_uuid(dataset_id):
    with pytest.raises(HTTPException) as exc_info:
        general_helper.safe_dataset_id(dataset_id)

    assert exc_info.value.status_code == 400


def test_safe_dataset_id_accepts_canonical_uuid():
    dataset_id = str(uuid4())

    assert general_helper.safe_dataset_id(dataset_id) == dataset_id


def test_dataset_path_returns_existing_dataset(tmp_path, monkeypatch):
    dataset_id = str(uuid4())
    dataset_file = tmp_path / f"{dataset_id}.csv"
    dataset_file.write_text("value\n1\n", encoding="utf-8")
    monkeypatch.setattr(general_helper, "UPLOAD_DIR", tmp_path)

    assert general_helper.dataset_path(dataset_id) == dataset_file


def test_dataset_path_rejects_missing_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(general_helper, "UPLOAD_DIR", tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        general_helper.dataset_path(str(uuid4()))

    assert exc_info.value.status_code == 404


def test_dataset_path_rejects_symlink(tmp_path, monkeypatch):
    dataset_id = str(uuid4())
    outside_file = tmp_path.parent / f"{dataset_id}.csv"
    outside_file.write_text("value\n1\n", encoding="utf-8")
    dataset_link = tmp_path / f"{dataset_id}.csv"
    try:
        dataset_link.symlink_to(outside_file)
    except OSError as exc:
        pytest.skip(f"Creating symlinks is not permitted: {exc}")

    monkeypatch.setattr(general_helper, "UPLOAD_DIR", tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        general_helper.dataset_path(dataset_id)

    assert exc_info.value.status_code == 404
