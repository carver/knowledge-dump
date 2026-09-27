"""A full triage run: sync the clone, triage, push, and confirm the host merged it.

If the host can't merge (you ticked a box on the Triage page while the run was
working), the run starts over from the host's newer main. The model's answers
are cached for the run, so a retry doesn't pay for them twice.
"""

from collections.abc import Callable
from typing import Any

from kd import state
from kd.gitsync import Unreachable, VaultClone
from kd.propose import Model
from kd.triage import NewPage, Report, triage

ATTEMPTS = 3

SparkSource = Callable[[set[str]], tuple[list[NewPage], list[str]]]


def _cached(model: Model) -> Model:
    answers: dict[str, dict[str, Any]] = {}

    def ask(prompt: str) -> dict[str, Any]:
        if prompt not in answers:
            answers[prompt] = model(prompt)
        return answers[prompt]

    return ask


def _message(report: Report) -> str:
    counts = [
        (len(report.applied), "applied"),
        (len(report.proposed), "proposed"),
        (len(report.imported), "imported"),
        (len(report.parked), "parked"),
        (len(report.dropped), "dropped"),
    ]
    summary = ", ".join(f"{n} {label}" for n, label in counts if n) or "refresh the Triage page"
    return f"Triage: {summary}\n\n" + "\n".join(report.lines()) + "\n"


def _read_sparks(sparks: SparkSource, done: set[str], log: Callable[[str], None]) -> list[NewPage]:
    """New Spark pages. A broken tab-squasher checkout is logged, not fatal: triage goes on without Sparks."""
    try:
        new_pages, skipped = sparks(done)
    except (ImportError, OSError, ValueError) as e:
        log(f"can't read tab-squasher's Inbox, skipping Sparks this run: {e!r}")
        return []
    for line in skipped:
        log(f"skipped tab-squasher Inbox line: {line}")
    return new_pages


def run(clone: VaultClone, model: Model | None, sparks: SparkSource, log: Callable[[str], None]) -> bool:
    """Returns False if the run gave up; the reason has been logged."""
    cached = _cached(model) if model else None
    try:
        clone.ensure()
        clone.fetch()
        for _ in range(ATTEMPTS):
            clone.reset_to_main()
            new_pages = _read_sparks(sparks, set(state.load(clone.path).imported_sparks), log)
            report = triage(clone.path, cached, new_pages)
            if not clone.commit_all(_message(report)):
                for problem in report.problems:
                    log(f"problem: {problem}")
                return True
            commit = clone.push()
            if clone.merged(commit):
                for line in report.lines():
                    log(line)
                return True
            log("host didn't merge the push (probably a concurrent edit); retrying from its main")
    except Unreachable as e:
        log(f"vault unreachable, skipping this run: {e}")
        return True
    log(f"gave up after {ATTEMPTS} attempts; the host keeps refusing the merge")
    return False
