import csv
import json

import pytest

from datecut.cli import main
from datecut.simulate import simulate


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    root = tmp_path_factory.mktemp("cli")
    results, meta = simulate(n_items=300, n_systems=5, drop=1.2, drift=0.8, seed=11)
    for name, rows in (("results.csv", results), ("meta.csv", meta)):
        with open(root / name, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    (root / "cutoffs.csv").write_text("system,cutoff\nsys-0,2024-01-01\nsys-1,2023-10-01\n")
    base = ["--results", str(root / "results.csv"), "--meta", str(root / "meta.csv")]
    return root, base


def run(capsys, argv):
    code = main(argv)
    return code, capsys.readouterr()


def test_gap_markdown_lists_every_system(files, capsys):
    _, base = files
    code, out = run(capsys, ["gap", *base, "--cutoff", "2024-01-01"])
    assert code == 0
    lines = out.out.strip().splitlines()
    assert lines[0].startswith("| system | cutoff | n before | n after")
    assert len(lines) == 2 + 5


def test_gap_json_and_cutoff_table(files, capsys):
    root, base = files
    code, out = run(
        capsys, ["gap", *base, "--cutoffs", str(root / "cutoffs.csv"), "--format", "json"]
    )
    assert code == 0
    payload = json.loads(out.out)
    assert [(r["system"], r["cutoff"]) for r in payload] == [
        ("sys-0", "2024-01-01"), ("sys-1", "2023-10-01"),
    ]
    assert payload[0]["gap"] < 0 and payload[0]["p_bh"] is not None


def test_gap_says_when_a_side_is_short(files, capsys):
    _, base = files
    code, out = run(capsys, ["gap", *base, "--cutoff", "2024-12-15", "--system", "sys-0"])
    assert code == 0
    assert "not reported" in out.out and "too few items" in out.out


def test_power_command(files, capsys):
    _, base = files
    code, out = run(capsys, ["power", *base, "--cutoff", "2024-01-01", "--system", "sys-2"])
    assert code == 0 and "smallest drop at 80 % power" in out.out


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--cutoff", "2024-01-01", "--system", "nobody"],
        ["--cutoff", "soon"],
    ],
)
def test_errors_exit_with_2(files, capsys, extra):
    _, base = files
    code, out = run(capsys, ["gap", *base, *extra])
    assert code == 2 and out.err.startswith("datecut:")


def test_cutoff_and_cutoffs_together_is_an_error(files, capsys):
    root, base = files
    argv = ["gap", *base, "--cutoff", "2024-01-01", "--cutoffs", str(root / "cutoffs.csv")]
    code, out = run(capsys, argv)
    assert code == 2


def test_missing_file(capsys):
    argv = ["gap", "--results", "nope.csv", "--meta", "nope.csv", "--cutoff", "2024-01-01"]
    code, out = run(capsys, argv)
    assert code == 2
