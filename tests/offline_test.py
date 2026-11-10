"""Behavior tests that never construct an LLM client or call a service."""

import tempfile
import unittest
from pathlib import Path

import loophole.main  # Check the complete CLI import graph without invoking it.
from loophole.models import Case, CaseStatus, CaseType, LegalCode, SessionState
from loophole.session import SessionManager
from loophole.visualize import _compute_diff_html, generate_html


def sample_state() -> SessionState:
    first = LegalCode(version=1, text="Rule A")
    second = LegalCode(version=2, text="Rule B")
    return SessionState(
        session_id="offline-test",
        domain="test domain",
        moral_principles="avoid harm",
        current_code=second,
        code_history=[first, second],
        cases=[
            Case(
                id=1,
                round=1,
                case_type=CaseType.LOOPHOLE,
                scenario="<script>alert(1)</script>",
                explanation="edge case",
                status=CaseStatus.USER_RESOLVED,
                resolution="Rule B",
                resolved_by="user",
            ),
            Case(
                id=2,
                round=1,
                case_type=CaseType.OVERREACH,
                scenario="pending",
                explanation="edge case",
            ),
        ],
    )


class OfflineTest(unittest.TestCase):
    def test_models_filter_resolved_cases_and_assign_next_id(self):
        state = sample_state()
        self.assertEqual([case.id for case in state.resolved_cases], [1])
        self.assertEqual(state.next_case_id, 3)

    def test_session_roundtrip_uses_temporary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = SessionManager(directory)
            state = sample_state()
            manager.save(state)
            loaded = manager.load(state.session_id)
            self.assertEqual(loaded.model_dump(), state.model_dump())
            self.assertEqual(manager.list_sessions()[0]["cases"], 2)

    def test_visualization_escapes_case_content_and_shows_code_change(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.html"
            self.assertEqual(generate_html(sample_state(), str(report)), str(report))
            html = report.read_text()
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("Rule B", html)
        self.assertIn("diff-add", _compute_diff_html("Rule A\n", "Rule B\n"))


if __name__ == "__main__":
    unittest.main()
