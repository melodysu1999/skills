"""Regression tests for the qa-testing artifact scripts."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def result_fixture(run_id: str, evidence_hash: str) -> dict:
    return {
        "schema_version": 1,
        "run": {
            "id": run_id,
            "started_at": "2026-09-04T14:30:00+08:00",
            "completed_at": "2026-09-04T14:40:00+08:00",
            "status": "completed",
        },
        "issue": {
            "id": "37259",
            "url": "https://mantis.example.test/view.php?id=37259",
            "project_id": "123",
            "summary": "列印內容驗證",
            "status": "待驗測",
            "updated_at": "2026-09-04T13:00:00+08:00",
            "fetched_at": "2026-09-04T14:30:01+08:00",
            "acceptance_summary": "產生文件並確認內容顯示正確。",
        },
        "project": {
            "name": "範例專案",
            "environment": "SIT",
            "source_review": "unavailable_optional",
        },
        "resume": {"mode": "fresh", "prior_run_id": None, "reason": "沒有相容的既有 checkpoint。"},
        "test_plan": {
            "objective": "驗證 SIT 產生的測試文件內容。",
            "preconditions": ["已進入正確 SIT"],
            "steps": [{"id": "step-01", "action": "建立安全測試資料並產生文件"}],
            "regression_checks": ["文件可開啟"],
            "prohibited_actions": ["正式外部送件"],
        },
        "execution": {
            "last_completed_step": "step-01",
            "next_safe_step": "無；驗測完成。",
            "test_data_refs": [{"type": "safe_quote", "value": "TEST-37259"}],
            "steps": [
                {
                    "id": "step-01",
                    "action": "建立安全測試資料並產生文件",
                    "expected": "文件可開啟且內容正確",
                    "actual": "文件可開啟且內容正確",
                    "status": "passed",
                    "evidence_ids": ["ev-01"],
                }
            ],
        },
        "evidence": [
            {
                "id": "ev-01",
                "step_id": "step-01",
                "type": "screenshot",
                "path": "evidence/step-01.txt",
                "sha256": evidence_hash,
                "captured_at": "2026-09-04T14:39:00+08:00",
                "description": "SIT 文件結果畫面",
            }
        ],
        "result": {
            "verdict": "Pass",
            "summary": "所有驗收條件符合。",
            "blockers": [],
            "release_conditions": [],
            "next_step": "可進行後續複測。",
        },
        "mantis_note": {
            "status": "pending",
            "private": True,
            "note_id": None,
            "prepared_note_path": "mantis-note.txt",
            "content_sha256": None,
            "error": None,
        },
        "security": {"secrets_redacted": True},
    }


class QaTestingScriptsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(__file__).resolve().parent / f".tmp-{uuid.uuid4().hex}"
        self.run_id = "qa-37259-20260904T143000+0800"
        self.issue_dir = self.temp / "docs" / "testing" / "37259"
        self.run_dir = self.issue_dir / self.run_id
        evidence = self.run_dir / "evidence" / "step-01.txt"
        evidence.parent.mkdir(parents=True)
        evidence.write_text("fixture evidence\n", encoding="utf-8")
        self.result_path = self.run_dir / "test-result.json"
        self.result = result_fixture(self.run_id, hashlib.sha256(evidence.read_bytes()).hexdigest())
        write_json(self.result_path, self.result)
        rendered = self.run_script("render_mantis_note.py", self.result_path, "--output", self.run_dir / "mantis-note.txt")
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.note_manifest = json.loads(rendered.stdout)
        self.result["mantis_note"]["content_sha256"] = self.note_manifest["sha256"]
        write_json(self.result_path, self.result)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def run_script(self, name: str, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPTS / name), *(str(arg) for arg in args)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def write_result(self, value: dict) -> None:
        write_json(self.result_path, value)

    def delivery_checkpoint(self) -> dict:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "updated_at": "2026-09-04T14:41:00+08:00",
            "phase": "delivering",
            "status": "delivery_pending",
            "issue": {"id": "37259", "project_id": "123", "updated_at": "2026-09-04T13:00:00+08:00"},
            "project": {"name": "範例專案", "environment": "SIT"},
            "continuation": {
                "mode": "delivery-only",
                "prior_run_id": self.run_id,
                "result_finalized": True,
                "last_completed_step": "step-01",
                "next_safe_step": "確認非公開 Mantis 留言是否已存在。",
            },
            "test_data_refs": self.result["execution"]["test_data_refs"],
            "evidence_refs": ["evidence/step-01.txt"],
            "result_path": "test-result.json",
            "prepared_note": {
                "path": "mantis-note.txt",
                "sha256": self.note_manifest["sha256"],
                "status": "pending",
            },
            "security": {"secrets_redacted": True},
        }

    def assert_invalid_result(self, value: dict, message: str) -> None:
        self.write_result(value)
        completed = self.run_script("validate_result.py", self.result_path)
        self.assertEqual(completed.returncode, 1)
        self.assertIn(message, completed.stderr)

    def test_validate_result_accepts_valid_result(self) -> None:
        completed = self.run_script("validate_result.py", self.result_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("VALID:", completed.stdout)

    def test_validate_result_rejects_invalid_status_and_verdict_pair(self) -> None:
        invalid = copy.deepcopy(self.result)
        invalid["run"]["status"] = "retryable_error"
        invalid["result"]["verdict"] = "Fail"
        self.assert_invalid_result(invalid, "invalid terminal combination")

    def test_validate_result_rejects_secret_like_data(self) -> None:
        invalid = copy.deepcopy(self.result)
        invalid["execution"]["test_data_refs"].append({"token": "must-not-be-stored"})
        self.assert_invalid_result(invalid, "secret-like field")

    def test_validate_result_rejects_evidence_path_traversal(self) -> None:
        invalid = copy.deepcopy(self.result)
        invalid["evidence"][0]["path"] = "../outside.txt"
        self.assert_invalid_result(invalid, "escapes run directory")

    def test_validate_result_rejects_evidence_hash_mismatch(self) -> None:
        invalid = copy.deepcopy(self.result)
        invalid["evidence"][0]["sha256"] = "0" * 64
        self.assert_invalid_result(invalid, "evidence hash mismatch")

    def test_render_mantis_note_is_human_readable_and_omits_local_paths(self) -> None:
        note = (self.run_dir / "mantis-note.txt").read_text(encoding="utf-8")
        self.assertIn("【QA SIT 驗測結果】", note)
        self.assertIn("Mantis：#37259", note)
        self.assertIn("結果：Pass", note)
        self.assertIn(f"執行識別：{self.run_id}", note)
        self.assertNotIn("evidence/step-01.txt", note)
        self.assertEqual(self.note_manifest["sha256"], hashlib.sha256(note.encode("utf-8")).hexdigest())

    def test_render_mantis_note_rejects_public_note(self) -> None:
        public = copy.deepcopy(self.result)
        public["mantis_note"]["private"] = False
        self.write_result(public)
        completed = self.run_script("render_mantis_note.py", self.result_path)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("mantis_note.private must be true", completed.stderr)

    def test_update_latest_writes_result_pointer_and_hash(self) -> None:
        completed = self.run_script("update_latest.py", self.result_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        latest = json.loads((self.issue_dir / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual(latest["run_id"], self.run_id)
        self.assertEqual(latest["result_path"], f"{self.run_id}/test-result.json")
        self.assertEqual(latest["sha256"], hashlib.sha256(self.result_path.read_bytes()).hexdigest())

    def test_update_latest_rejects_run_directory_identity_mismatch(self) -> None:
        invalid = copy.deepcopy(self.result)
        invalid["run"]["id"] = "different-run"
        self.write_result(invalid)
        completed = self.run_script("update_latest.py", self.result_path)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("run.id must match", completed.stderr)

    def test_validate_checkpoint_accepts_unfinished_run(self) -> None:
        running_id = "qa-37259-20260904T150000+0800"
        running_dir = self.issue_dir / running_id
        checkpoint_path = running_dir / "checkpoint.json"
        checkpoint = {
            "schema_version": 1,
            "run_id": running_id,
            "updated_at": "2026-09-04T15:01:00+08:00",
            "phase": "planned",
            "status": "running",
            "issue": {"id": "37259", "project_id": "123", "updated_at": "2026-09-04T13:00:00+08:00"},
            "project": {"name": "範例專案", "environment": "SIT"},
            "continuation": {
                "mode": "fresh",
                "prior_run_id": None,
                "result_finalized": False,
                "last_completed_step": None,
                "next_safe_step": "開始第一個安全測試步驟。",
            },
            "test_data_refs": [],
            "evidence_refs": [],
            "result_path": None,
            "prepared_note": {"path": None, "sha256": None, "status": "not_prepared"},
            "security": {"secrets_redacted": True},
        }
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_validate_checkpoint_accepts_delivery_only_resume(self) -> None:
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, self.delivery_checkpoint())
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_validate_checkpoint_rejects_delivery_only_without_final_result(self) -> None:
        checkpoint = self.delivery_checkpoint()
        checkpoint["continuation"]["result_finalized"] = False
        checkpoint["result_path"] = None
        checkpoint["prepared_note"] = {"path": None, "sha256": None, "status": "not_prepared"}
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("delivery-only requires", completed.stderr)

    def test_validate_checkpoint_rejects_project_identity_mismatch(self) -> None:
        checkpoint = self.delivery_checkpoint()
        checkpoint["project"]["name"] = "錯誤專案"
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("project identity differ", completed.stderr)

    def test_validate_checkpoint_rejects_prepared_note_hash_mismatch(self) -> None:
        checkpoint = self.delivery_checkpoint()
        checkpoint["prepared_note"]["sha256"] = "0" * 64
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("prepared note identity differ", completed.stderr)


if __name__ == "__main__":
    unittest.main()
