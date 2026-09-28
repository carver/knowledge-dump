from pathlib import Path

import kd_host


def test_init_adds_the_queue_page_and_links_it(tmp_path: Path) -> None:
    kd_host.init(tmp_path)
    assert "[[Queue]]" in (tmp_path / "index.md").read_text()
    assert 'index.tasks("queue")' in (tmp_path / "Queue.md").read_text()


def test_init_keeps_an_edited_queue_page(tmp_path: Path) -> None:
    (tmp_path / "Queue.md").write_text("mine\n")
    kd_host.init(tmp_path)
    assert (tmp_path / "Queue.md").read_text() == "mine\n"
