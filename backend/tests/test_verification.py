"""Isolated regression checks for the evaluation flows; no live DB or AI calls."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Importing app.main constructs a Supabase client. These deliberately unusable
# values keep the test process independent from local or CI credentials.
os.environ.update(
    SUPABASE_URL="https://example.supabase.co",
    SUPABASE_SECRET_KEY="test-only-placeholder",
    OPENAI_API_KEY="test-only-placeholder",
    OPENAI_MODEL="test-model",
)

from app.api.ai import read_attempt_explanation
from app.api.auth_dependencies import get_current_learner
from app.api.diagnostic import read_diagnostic_report
from app.clients.openai_client import AIProviderError
from app.repositories import ai_explanation_repository, diagnostic_repository
from app.schemas.auth import CurrentLearnerResponse
from app.schemas.diagnostic import DiagnosticItemGradingResult, DiagnosticSubmitRequest
from app.schemas.learning import WeakLearningSubmitRequest
from app.services import (
    ai_explanation_service as ai_service,
)
from app.services import (
    ai_retrieval_service,
    diagnostic_service,
    weak_learning_service,
    wrong_review_service,
)
from app.services import (
    learning_recommendation_service as recommendation_service,
)
from fastapi import HTTPException


def grading(question_id, correct="B", subtype="S1"):
    return {
        "question_id": question_id,
        "found": True,
        "subtype_id": subtype,
        "correct_choice_label": correct,
        "incorrect_choice_traps": [
            {"choice_label": label, "trap_id": f"T-{label}"} for label in "ABCD" if label != correct
        ],
    }


def attempt(identifier, subtype, correct, timestamp, trap_id=None):
    return {
        "id": identifier,
        "subtype_id": subtype,
        "subtype_name": f"Subtype {subtype}",
        "type_id": "TYPE",
        "type_name": "Grammar",
        "is_correct": correct,
        "trap_id": trap_id,
        "trap_name": "Repeated trap" if trap_id else None,
        "trap_description": None,
        "context": "diagnostic",
        "answered_at": timestamp,
    }


VALID_EXPLANATION = {
    "summary": "요약",
    "correct_reason": "정답 근거",
    "selected_choice_reason": "선택 근거",
    "trap": {"code": "T-A", "name": "함정", "explanation": "함정 설명"},
    "rule": "문법 규칙",
    "next_tip": "다음 팁",
}


class DiagnosticTests(unittest.TestCase):
    def test_grades_and_persists_owned_session_and_attempts(self):
        submission = DiagnosticSubmitRequest(
            answers=[
                {"question_id": "q1", "selected_choice": "B"},
                {"question_id": "q2", "selected_choice": "A"},
            ]
        )
        with (
            patch.object(
                diagnostic_service,
                "get_diagnostic_question_grading_data",
                return_value=[grading("q1"), grading("q2")],
            ) as questions,
            patch.object(
                diagnostic_service, "create_diagnostic_session", return_value="session-1"
            ) as session,
            patch.object(
                diagnostic_service, "create_question_attempts", return_value={"q1": 11, "q2": 12}
            ) as saved,
        ):
            result = diagnostic_service.submit_diagnostic(submission, learner_id="learner-a")

        questions.assert_called_once_with(["q1", "q2"])
        session.assert_called_once_with(
            learner_id="learner-a",
            total_questions=2,
            correct_count=1,
            accuracy=50.0,
            estimated_score=None,
        )
        self.assertEqual(saved.call_args.kwargs["learner_id"], "learner-a")
        self.assertEqual(saved.call_args.kwargs["diagnostic_session_id"], "session-1")
        self.assertEqual([item.is_correct for item in result.results], [True, False])
        self.assertEqual([item.trap_id for item in result.results], [None, "T-A"])
        self.assertEqual([item.attempt_id for item in result.results], [11, 12])

    def test_duplicate_diagnostic_question_is_rejected_before_storage(self):
        submission = DiagnosticSubmitRequest(
            answers=[
                {"question_id": "q1", "selected_choice": "A"},
                {"question_id": "q1", "selected_choice": "B"},
            ]
        )
        with patch.object(diagnostic_service, "create_diagnostic_session") as saved:
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                diagnostic_service.submit_diagnostic(submission, learner_id="learner-a")
        saved.assert_not_called()


class RepositoryBoundaryTests(unittest.TestCase):
    def test_diagnostic_repository_writes_owner_and_grading_fields(self):
        inserted = []

        class FakeTable:
            def insert(self, payload):
                inserted.append(payload)
                return self

            def execute(self):
                if len(inserted) == 1:
                    return SimpleNamespace(data=[{"id": "session-1"}])
                return SimpleNamespace(
                    data=[{"question_id": "q2", "id": 22}, {"question_id": "q1", "id": 21}]
                )

        fake = MockSupabase(FakeTable())
        with patch.object(diagnostic_repository, "supabase", fake):
            session_id = diagnostic_repository.create_diagnostic_session(
                learner_id="learner-a", total_questions=2, correct_count=1, accuracy=50.0
            )
            results = [
                DiagnosticItemGradingResult(
                    question_id="q1",
                    subtype_id="S1",
                    selected_choice="B",
                    correct_choice="B",
                    is_correct=True,
                ),
                DiagnosticItemGradingResult(
                    question_id="q2",
                    subtype_id="S1",
                    selected_choice="A",
                    correct_choice="B",
                    is_correct=False,
                    trap_id="T-A",
                ),
            ]
            ids = diagnostic_repository.create_question_attempts(
                learner_id="learner-a", diagnostic_session_id=session_id, results=results
            )

        self.assertEqual(fake.table_names, ["diagnostic_sessions", "question_attempts"])
        self.assertEqual(inserted[0]["learner_id"], "learner-a")
        self.assertEqual(inserted[0]["correct_count"], 1)
        self.assertEqual([row["learner_id"] for row in inserted[1]], ["learner-a", "learner-a"])
        self.assertEqual([row["trap_id"] for row in inserted[1]], [None, "T-A"])
        self.assertEqual(ids, {"q2": 22, "q1": 21})

    def test_ai_attempt_lookup_filters_by_attempt_and_learner(self):
        class FakeQuery:
            def __init__(self):
                self.filters = []

            def select(self, *_):
                return self

            def eq(self, key, value):
                self.filters.append((key, value))
                return self

            def limit(self, *_):
                return self

            def execute(self):
                return SimpleNamespace(data=[])

        query = FakeQuery()
        fake = MockSupabase(query)
        with patch.object(ai_explanation_repository, "supabase", fake):
            result = ai_explanation_repository.get_owned_question_attempt(7, "learner-a")
        self.assertIsNone(result)
        self.assertEqual(fake.table_names, ["question_attempts"])
        self.assertEqual(query.filters, [("id", 7), ("learner_id", "learner-a")])


class MockSupabase:
    def __init__(self, table):
        self.table_names = []
        self._table = table

    def table(self, name):
        self.table_names.append(name)
        return self._table


class RecommendationTests(unittest.TestCase):
    def test_uses_only_requested_learner_history_and_ranks_weak_subtypes(self):
        history = [
            attempt(1, "A", False, "2026-10-03", "T-A"),
            attempt(2, "A", False, "2026-10-02", "T-A"),
            attempt(3, "A", True, "2026-10-01"),
            attempt(4, "B", True, "2026-10-03"),
            attempt(5, "B", True, "2026-10-02"),
            attempt(6, "C", False, "2026-10-03", "T-A"),
            attempt(7, "D", False, "2026-10-03", "T-B"),
            attempt(8, "D", True, "2026-10-02"),
        ]
        with patch.object(
            recommendation_service, "get_learner_toeic_attempts", return_value=history
        ) as read:
            result = recommendation_service.get_learning_recommendations("learner-a")

        read.assert_called_once_with("learner-a")
        self.assertEqual([item.subtype_id for item in result.recommendations], ["A", "D"])
        self.assertEqual([item.subtype_id for item in result.strengths], ["B"])
        self.assertEqual(result.recommendations[0].top_traps[0].wrong_count, 2)
        self.assertEqual(result.summary.total_attempts, 8)


class WeakLearningTests(unittest.TestCase):
    def test_requires_two_consecutive_correct_answers_and_persists_each(self):
        session = {
            "learner_id": "learner-a",
            "mode": "weak_learning",
            "status": "in_progress",
            "subtype_id": "S1",
        }
        newest_attempts = []
        saved_results = []

        def save_attempt(**kwargs):
            result = kwargs["result"]
            saved_results.append(result)
            newest_attempts.insert(0, {"is_correct": result.is_correct})
            return len(saved_results)

        with (
            patch.object(weak_learning_service, "get_learning_session", return_value=session),
            patch.object(
                weak_learning_service,
                "get_practice_question_grading_data",
                return_value=grading("q1"),
            ),
            patch.object(
                weak_learning_service, "create_learning_attempt", side_effect=save_attempt
            ) as save,
            patch.object(
                weak_learning_service,
                "get_learning_session_attempts",
                side_effect=lambda _: newest_attempts,
            ),
            patch.object(weak_learning_service, "complete_learning_session") as complete,
        ):
            results = []
            for choice in ("B", "A", "B", "B"):
                results.append(
                    weak_learning_service.submit_weak_learning_answer(
                        WeakLearningSubmitRequest(
                            learning_session_id="session-1",
                            question_id="q1",
                            selected_choice=choice,
                        ),
                        learner_id="learner-a",
                    )
                )

        self.assertEqual([item.correct_streak for item in results], [1, 0, 1, 2])
        self.assertEqual([item.is_completed for item in results], [False, False, False, True])
        self.assertEqual([item.attempt_id for item in results], [1, 2, 3, 4])
        self.assertEqual(save.call_count, 4)
        self.assertTrue(
            all(call.kwargs["learner_id"] == "learner-a" for call in save.call_args_list)
        )
        complete.assert_called_once_with("session-1")

    def test_foreign_weak_session_is_rejected_before_grading_or_storage(self):
        session = {
            "learner_id": "learner-b",
            "mode": "weak_learning",
            "status": "in_progress",
            "subtype_id": "S1",
        }
        submission = WeakLearningSubmitRequest(
            learning_session_id="session-1", question_id="q1", selected_choice="B"
        )
        with (
            patch.object(weak_learning_service, "get_learning_session", return_value=session),
            patch.object(weak_learning_service, "get_practice_question_grading_data") as grade,
            patch.object(weak_learning_service, "create_learning_attempt") as save,
        ):
            with self.assertRaisesRegex(ValueError, "not found"):
                weak_learning_service.submit_weak_learning_answer(
                    submission, learner_id="learner-a"
                )
        grade.assert_not_called()
        save.assert_not_called()


class WrongReviewTests(unittest.TestCase):
    def test_target_set_updates_from_latest_answer_per_question(self):
        history = [
            {"question_id": "q1", "is_correct": False},
            {"question_id": "q2", "is_correct": False},
            {"question_id": "q3", "is_correct": True},
            {"question_id": "q3", "is_correct": False},
        ]
        with patch.object(
            wrong_review_service,
            "get_learner_question_attempts",
            side_effect=lambda learner: history if learner == "learner-a" else [],
        ) as read:
            self.assertEqual(
                wrong_review_service.get_unresolved_wrong_question_ids("learner-a"), ["q1", "q2"]
            )
            history.insert(0, {"question_id": "q1", "is_correct": True})
            history.insert(0, {"question_id": "q3", "is_correct": False})
            self.assertEqual(
                wrong_review_service.get_unresolved_wrong_question_ids("learner-a"), ["q3", "q2"]
            )
            self.assertEqual(
                wrong_review_service.get_unresolved_wrong_question_ids("learner-b"), []
            )
        self.assertEqual(read.call_count, 3)

    def test_foreign_review_session_does_not_expose_items(self):
        with (
            patch.object(
                wrong_review_service,
                "get_learning_session",
                return_value={"learner_id": "learner-b"},
            ),
            patch.object(wrong_review_service, "get_learning_session_question_ids") as assignments,
            patch.object(wrong_review_service, "get_public_toeic_questions_by_ids") as questions,
        ):
            with self.assertRaisesRegex(ValueError, "not found"):
                wrong_review_service.get_wrong_review_items("session-1", "learner-a")
        assignments.assert_not_called()
        questions.assert_not_called()


class AIExplanationTests(unittest.TestCase):
    def setUp(self):
        self.owned = {
            "id": 7,
            "learner_id": "learner-a",
            "question_id": "q1",
            "subtype_id": "S1",
            "selected_choice": "A",
            "is_correct": False,
            "trap_id": "T-A",
        }

    def test_generates_validates_and_saves_explanation(self):
        with (
            patch.object(
                ai_service, "get_owned_question_attempt", return_value=self.owned
            ) as owned,
            patch.object(ai_service, "get_cached_ai_explanation", return_value=None),
            patch.object(
                ai_service, "retrieve_explanation_context", return_value={"question": "q1"}
            ) as retrieve,
            patch.object(
                ai_service, "generate_explanation", return_value=json.dumps(VALID_EXPLANATION)
            ) as provider,
            patch.object(ai_service, "create_ai_explanation") as save,
        ):
            result = ai_service.get_ai_explanation(7, "learner-a")

        owned.assert_called_once_with(7, "learner-a")
        retrieve.assert_called_once_with(self.owned)
        provider.assert_called_once_with({"question": "q1"})
        self.assertEqual(save.call_args.kwargs["attempt_id"], 7)
        self.assertEqual(save.call_args.kwargs["learner_id"], "learner-a")
        self.assertEqual(save.call_args.kwargs["content"], VALID_EXPLANATION)
        self.assertFalse(result.cached)
        self.assertEqual(result.explanation.summary, "요약")

    def test_cached_explanation_skips_retrieval_and_provider(self):
        cached = {"attempt_id": 7, "model": "cached-model", "content": VALID_EXPLANATION}
        with (
            patch.object(ai_service, "get_owned_question_attempt", return_value=self.owned),
            patch.object(ai_service, "get_cached_ai_explanation", return_value=cached),
            patch.object(ai_service, "retrieve_explanation_context") as retrieve,
            patch.object(ai_service, "generate_explanation") as provider,
        ):
            result = ai_service.get_ai_explanation(7, "learner-a")
        self.assertTrue(result.cached)
        self.assertEqual(result.model, "cached-model")
        retrieve.assert_not_called()
        provider.assert_not_called()

    def test_rejects_invalid_provider_json_and_schema_without_caching(self):
        for output in ("not-json", json.dumps({**VALID_EXPLANATION, "summary": ""})):
            with self.subTest(output=output):
                with (
                    patch.object(ai_service, "get_owned_question_attempt", return_value=self.owned),
                    patch.object(ai_service, "get_cached_ai_explanation", return_value=None),
                    patch.object(ai_service, "retrieve_explanation_context", return_value={}),
                    patch.object(ai_service, "generate_explanation", return_value=output),
                    patch.object(ai_service, "create_ai_explanation") as save,
                ):
                    with self.assertRaises(AIProviderError):
                        ai_service.get_ai_explanation(7, "learner-a")
                    save.assert_not_called()

    def test_provider_failure_propagates_without_cache_write(self):
        with (
            patch.object(ai_service, "get_owned_question_attempt", return_value=self.owned),
            patch.object(ai_service, "get_cached_ai_explanation", return_value=None),
            patch.object(ai_service, "retrieve_explanation_context", return_value={}),
            patch.object(
                ai_service, "generate_explanation", side_effect=AIProviderError("unavailable")
            ),
            patch.object(ai_service, "create_ai_explanation") as save,
        ):
            with self.assertRaises(AIProviderError):
                ai_service.get_ai_explanation(7, "learner-a")
        save.assert_not_called()

    def test_foreign_attempt_is_rejected_before_cache_or_ai(self):
        with (
            patch.object(ai_service, "get_owned_question_attempt", return_value=None),
            patch.object(ai_service, "get_cached_ai_explanation") as cache,
            patch.object(ai_service, "generate_explanation") as provider,
        ):
            with self.assertRaises(ai_service.ExplanationAttemptNotFoundError):
                ai_service.get_ai_explanation(7, "learner-b")
        cache.assert_not_called()
        provider.assert_not_called()

    def test_structured_retrieval_uses_question_taxonomy_and_trap(self):
        question = {
            "id": "q1",
            "subtype_id": "S1",
            "stem": "Stem",
            "part": "5",
            "difficulty": None,
            "translation": None,
            "question_choices": [
                {"choice_label": "B", "choice_text": "right", "is_correct": True},
                {"choice_label": "A", "choice_text": "wrong", "is_correct": False},
            ],
        }
        subtype = {
            "id": "S1",
            "name": "Subtype",
            "types": {"id": "T1", "name": "Type"},
            "subtype_specs": {"answer_rule": "Rule"},
        }
        with (
            patch.object(ai_retrieval_service, "get_question_with_choices", return_value=question),
            patch.object(ai_retrieval_service, "get_subtype_with_knowledge", return_value=subtype),
            patch.object(
                ai_retrieval_service,
                "get_trap",
                return_value={"id": "T-A", "name": "Trap", "description": "Description"},
            ),
        ):
            context = ai_retrieval_service.retrieve_explanation_context(self.owned)
        self.assertEqual(context["attempt"]["correct_choice"], "B")
        self.assertEqual(context["attempt"]["selected_choice_text"], "wrong")
        self.assertEqual(context["subtype_specs"]["answer_rule"], "Rule")
        self.assertEqual(context["trap"]["code"], "T-A")


class AccessBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.learner = CurrentLearnerResponse(
            learner_id="learner-a", auth_user_id="auth-a", name="A", age=20, email="a@example.test"
        )

    def test_missing_bearer_token_returns_401(self):
        with self.assertRaises(HTTPException) as error:
            get_current_learner(None)
        self.assertEqual(error.exception.status_code, 401)

    def test_diagnostic_report_denies_other_learners_session(self):
        session_id = "123e4567-e89b-12d3-a456-426614174000"
        with (
            patch(
                "app.api.diagnostic.get_diagnostic_session_owner",
                return_value={"learner_id": "learner-b"},
            ),
            patch("app.api.diagnostic.get_diagnostic_report") as report,
        ):
            with self.assertRaises(HTTPException) as error:
                read_diagnostic_report(session_id, self.learner)
        self.assertEqual(error.exception.status_code, 404)
        report.assert_not_called()

    def test_ai_provider_error_is_reported_as_502(self):
        with patch(
            "app.api.ai.get_ai_explanation", side_effect=AIProviderError("private upstream detail")
        ) as service:
            with self.assertRaises(HTTPException) as error:
                read_attempt_explanation(7, self.learner)
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("private upstream detail", error.exception.detail)
        service.assert_called_once_with(7, "learner-a")


if __name__ == "__main__":
    unittest.main()
