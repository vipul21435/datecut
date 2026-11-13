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


def test_strata_command(files, capsys):
    _, base = files
    argv = ["strata", *base, "--cutoff", "2024-01-01", "--strata", "source", "--system", "sys-0"]
    code, out = run(capsys, argv)
    assert code == 0
    assert "MH odds ratio" in out.out and "| source-0 |" in out.out
    code, out = run(capsys, ["strata", *base, "--cutoff", "2024-01-01"])
    assert code == 2 and "--strata" in out.err


def test_did_command_json_is_seeded(files, capsys):
    _, base = files
    argv = ["did", *base, "--cutoff", "2024-01-01", "--boot", "200", "--format", "json"]
    _, first = run(capsys, argv)
    _, second = run(capsys, argv)
    assert first.out == second.out
    payload = json.loads(first.out)
    assert len(payload) == 5 and payload[0]["did"] < 0
    clustered = ["did", *base, "--cutoff", "2024-01-01", "--boot", "200", "--cluster"]
    code, out = run(capsys, clustered)
    assert code == 2
    code, out = run(capsys, [*clustered, "--strata", "source"])
    assert code == 0 and "strata of `source`" in out.out


def test_adjust_and_summary_commands(files, capsys):
    _, base = files
    code, out = run(capsys, ["adjust", *base, "--cutoff", "2024-01-01", "--robust"])
    assert code == 0 and "after coefficient (log-odds)" in out.out
    code, out = run(capsys, ["summary", *base, "--cutoff", "2024-01-01", "--boot", "200"])
    assert code == 0 and "removed %" in out.out
    assert len(out.out.strip().splitlines()) == 2 + 2 + 5
    code, out = run(
        capsys, ["summary", *base, "--cutoff", "2024-12-20", "--boot", "50", "--format", "json"]
    )
    assert code == 0
    assert json.loads(out.out)[0]["gap"]["reported"] is False
    code, out = run(capsys, ["summary", *base, "--cutoff", "2024-12-20", "--boot", "50"])
    assert "Not reported" in out.out


def test_scan_command(files, capsys):
    _, base = files
    argv = ["scan", *base, "--system", "sys-0", "--perm", "100", "--max-points", "10"]
    code, out = run(capsys, argv)
    assert code == 0
    assert "permutation band" in out.out and "candidate date" in out.out
    every = ["scan", *base, "--perm", "50", "--max-points", "5", "--format", "json"]
    code, out = run(capsys, every)
    assert code == 0 and len(json.loads(out.out)) == 5
    code, out = run(capsys, [*argv, "--within-strata"])
    assert code == 2
    one_sided = [*argv, "--within-strata", "--strata", "source", "--alternative", "drop"]
    code, out = run(capsys, one_sided)
    assert code == 0 and "most negative z" in out.out


def test_trend_command(files, capsys):
    _, base = files
    code, out = run(capsys, ["trend", *base, "--system", "sys-0", "--by", "quarter"])
    assert code == 0 and out.out.startswith("### sys-0")
    code, out = run(capsys, ["trend", *base, "--window", "150", "--format", "json"])
    assert code == 0 and len(json.loads(out.out)) == 5


def test_markdown_cells_escape_pipes():
    from datecut import report

    text = report.table(["largest |z|", "name"], [[1.5, "a|b"]])
    lines = text.splitlines()
    assert lines[0] == "| largest \\|z\\| | name |"
    assert lines[2] == "| 1.5 | a\\|b |"
    assert report.pval(None) == "n/a" and report.num(float("nan")) == "n/a"
    assert report.pct(None) == "n/a" and report.interval(None, 1.0) == "n/a"
    assert report.to_json({"x": float("inf"), "d": [1.5]}).count("null") == 1


def test_degenerate_options_are_reported_not_crashed(files, capsys):
    root, base = files
    code, out = run(capsys, ["scan", *base, "--system", "sys-0", "--perm", "0"])
    assert code == 2 and "n_perm" in out.err
    code, out = run(capsys, ["did", *base, "--cutoff", "2024-01-01", "--boot", "0"])
    assert code == 2 and "n_boot" in out.err
    code, out = run(capsys, ["gap", *base, "--cutoff", "2024-01-01", "--conf", "1.5"])
    assert code == 2 and "conf" in out.err
    for command in ("gap", "adjust", "did", "summary", "power"):
        argv = [command, *base, "--cutoff", "2030-01-01", "--min-side", "0", "--system", "sys-0"]
        code, out = run(capsys, argv)
        assert code == 0
    (root / "broken.json").write_text("{not json")
    argv = ["gap", "--results", str(root / "broken.json"), "--meta", str(root / "meta.csv")]
    code, out = run(capsys, [*argv, "--cutoff", "2024-01-01"])
    assert code == 2 and out.err.startswith("datecut:")
    (root / "empty.csv").write_text("")
    argv = ["gap", "--results", str(root / "empty.csv"), "--meta", str(root / "meta.csv")]
    code, out = run(capsys, [*argv, "--cutoff", "2024-01-01"])
    assert code == 2


def test_a_single_system_has_no_pool(files, capsys, tmp_path):
    root, _ = files
    lines = (root / "results.csv").read_text().splitlines()
    only = [lines[0]] + [line for line in lines[1:] if ",sys-0," in line]
    (tmp_path / "one.csv").write_text("\n".join(only) + "\n")
    base = ["--results", str(tmp_path / "one.csv"), "--meta", str(root / "meta.csv")]
    for command in ("adjust", "did", "summary"):
        code, out = run(capsys, [command, *base, "--cutoff", "2024-01-01"])
        assert code == 0 and "Not reported" in out.out
        assert "no item was answered by any other system" in out.out
    code, out = run(capsys, ["scan", *base, "--perm", "10"])
    assert code == 0 and "no item was answered by any other system" in out.out
    code, out = run(capsys, ["gap", *base, "--cutoff", "2024-01-01"])
    assert code == 0 and "not reported" not in out.out
    code, out = run(capsys, ["trend", *base, "--by", "year"])
    assert code == 0 and "n/a" in out.out
