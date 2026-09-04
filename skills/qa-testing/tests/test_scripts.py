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

    def report_quality(self, passed: bool) -> dict:
        return {
            "page_count": 1 if passed else None,
            "page_size": "Letter",
            "orientation": "portrait",
            "max_pages": 1,
            "render_reviewed": passed,
            "title_style_checked": passed,
            "focus_annotations_checked": passed,
            "accessibility_audit_passed": passed,
        }

    def unrequested_report(self) -> dict:
        return {
            "requested": False,
            "status": "not_requested",
            "format": None,
            "path": None,
            "sha256": None,
            "assets": [],
            "quality": self.report_quality(False),
            "delivery": {
                "status": "not_requested",
                "note_id": None,
                "attachment_id": None,
                "requested_filename": None,
                "stored_filename": None,
                "revision": 0,
                "supersedes_attachment_id": None,
                "error": None,
            },
            "error": None,
        }

    def retryable_report(self) -> dict:
        report = self.unrequested_report()
        report.update({"requested": True, "status": "retryable_error", "format": "docx", "error": "render failed"})
        report["delivery"].update(
            {
                "status": "not_ready",
                "requested_filename": "Mantis 037259 測試報告.docx",
                "revision": 1,
            }
        )
        return report

    def ready_report(self, *, delivered: bool = False, revision: int = 1) -> dict:
        report_file = self.run_dir / "Mantis 037259 測試報告.docx"
        report_file.write_bytes(b"fixture docx bytes")
        report_asset = self.run_dir / "report-assets" / "underwriting-focus.png"
        report_asset.parent.mkdir(parents=True, exist_ok=True)
        report_asset.write_bytes(b"annotated screenshot fixture")
        delivery_status = "posted" if delivered else "pending"
        stored_filename = "Mantis 037259 測試報告-2.docx" if revision > 1 else "Mantis 037259 測試報告.docx"
        return {
            "requested": True,
            "status": "delivered" if delivered else "ready",
            "format": "docx",
            "path": report_file.name,
            "sha256": hashlib.sha256(report_file.read_bytes()).hexdigest(),
            "assets": [
                {
                    "id": "report-asset-01",
                    "source_evidence_id": "ev-01",
                    "type": "annotated_screenshot",
                    "path": "report-assets/underwriting-focus.png",
                    "sha256": hashlib.sha256(report_asset.read_bytes()).hexdigest(),
                    "description": "以紅框標示核保紀錄區",
                    "annotation": "red_frame",
                }
            ],
            "quality": self.report_quality(True),
            "delivery": {
                "status": delivery_status,
                "note_id": "98123" if delivered else None,
                "attachment_id": "45678" if delivered else None,
                "requested_filename": "Mantis 037259 測試報告.docx",
                "stored_filename": stored_filename if delivered else None,
                "revision": revision,
                "supersedes_attachment_id": "44567" if delivered and revision > 1 else None,
                "error": None,
            },
            "error": None,
        }

    def write_version_two_result(self, report: dict) -> dict:
        value = copy.deepcopy(self.result)
        value["schema_version"] = 2
        value["execution"]["actor"] = {"role": "核保人員", "account_label": "SIT 核保測試帳號"}
        value["report"] = report
        write_json(self.result_path, value)
        rendered = self.run_script("render_mantis_note.py", self.result_path, "--output", self.run_dir / "mantis-note.txt")
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        self.note_manifest = json.loads(rendered.stdout)
        value["mantis_note"]["content_sha256"] = self.note_manifest["sha256"]
        write_json(self.result_path, value)
        self.result = value
        return value

    def version_two_checkpoint(self, value: dict, *, mode: str, phase: str, status: str) -> dict:
        report = value["report"]
        delivery = report["delivery"]
        return {
            "schema_version": 2,
            "run_id": self.run_id,
            "updated_at": "2026-09-04T14:41:00+08:00",
            "phase": phase,
            "status": status,
            "issue": {"id": "37259", "project_id": "123", "updated_at": "2026-09-04T13:00:00+08:00"},
            "project": {"name": "範例專案", "environment": "SIT"},
            "continuation": {
                "mode": mode,
                "prior_run_id": self.run_id,
                "result_finalized": True,
                "last_completed_step": "step-01",
                "next_safe_step": "只續跑報告下游工作，不重新執行 SIT。",
            },
            "test_data_refs": value["execution"]["test_data_refs"],
            "evidence_refs": ["evidence/step-01.txt"],
            "result_path": "test-result.json",
            "prepared_note": {
                "path": value["mantis_note"]["prepared_note_path"],
                "sha256": value["mantis_note"]["content_sha256"],
                "status": value["mantis_note"]["status"],
            },
            "report": {
                "requested": report["requested"],
                "status": report["status"],
                "path": report["path"],
                "sha256": report["sha256"],
                "delivery_status": delivery["status"],
                "attachment_id": delivery["attachment_id"],
                "stored_filename": delivery["stored_filename"],
                "revision": delivery["revision"],
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

    def test_version_two_result_accepts_unrequested_report_and_detailed_note(self) -> None:
        self.write_version_two_result(self.unrequested_report())
        completed = self.run_script("validate_result.py", self.result_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        note = (self.run_dir / "mantis-note.txt").read_text(encoding="utf-8")
        self.assertIn("帳號／角色：SIT 核保測試帳號", note)
        self.assertIn("驗收重點：產生文件並確認內容顯示正確。", note)
        self.assertIn("主要測試資料：", note)
        self.assertIn("預期：文件可開啟且內容正確", note)
        self.assertIn("實際：文件可開啟且內容正確", note)

    def test_validate_result_accepts_ready_report_with_red_frame_asset(self) -> None:
        self.write_version_two_result(self.ready_report())
        evidence_hash_before = hashlib.sha256((self.run_dir / "evidence" / "step-01.txt").read_bytes()).hexdigest()
        completed = self.run_script("validate_result.py", self.result_path)
        evidence_hash_after = hashlib.sha256((self.run_dir / "evidence" / "step-01.txt").read_bytes()).hexdigest()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(evidence_hash_before, evidence_hash_after)

    def test_validate_result_rejects_ready_report_before_all_qa_gates_pass(self) -> None:
        report = self.ready_report()
        report["quality"]["focus_annotations_checked"] = False
        value = self.write_version_two_result(report)
        self.assert_invalid_result(value, "ready report requires every pre-upload QA gate")

    def test_validate_result_rejects_annotated_asset_without_visible_focus_marker(self) -> None:
        report = self.ready_report()
        report["assets"][0]["annotation"] = "none"
        value = self.write_version_two_result(report)
        self.assert_invalid_result(value, "annotated report screenshot requires a visible focus marker")

    def test_validate_result_rejects_report_asset_that_reuses_evidence_path(self) -> None:
        report = self.ready_report()
        report["assets"][0]["path"] = "evidence/step-01.txt"
        report["assets"][0]["sha256"] = self.result["evidence"][0]["sha256"]
        value = self.write_version_two_result(report)
        self.assert_invalid_result(value, "report asset must stay under report-assets")

    def test_report_failure_preserves_completed_pass_verdict(self) -> None:
        value = self.write_version_two_result(self.retryable_report())
        completed = self.run_script("validate_result.py", self.result_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(value["run"]["status"], "completed")
        self.assertEqual(value["result"]["verdict"], "Pass")

    def test_report_upload_failure_preserves_verdict_for_delivery_only_retry(self) -> None:
        report = self.ready_report()
        report["delivery"]["status"] = "retryable_error"
        report["delivery"]["error"] = "Mantis upload timeout"
        value = self.write_version_two_result(report)
        completed = self.run_script("validate_result.py", self.result_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(value["run"]["status"], "completed")
        self.assertEqual(value["result"]["verdict"], "Pass")

        checkpoint = self.version_two_checkpoint(value, mode="delivery-only", phase="delivering", status="delivery_pending")
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        resumed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)

    def test_delivered_revision_records_attachment_identity_and_server_filename(self) -> None:
        value = self.write_version_two_result(self.ready_report(delivered=True, revision=2))
        completed = self.run_script("validate_result.py", self.result_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        delivery = value["report"]["delivery"]
        self.assertEqual(delivery["attachment_id"], "45678")
        self.assertEqual(delivery["stored_filename"], "Mantis 037259 測試報告-2.docx")
        self.assertEqual(delivery["supersedes_attachment_id"], "44567")

    def test_delivered_report_rejects_missing_attachment_id(self) -> None:
        report = self.ready_report(delivered=True)
        report["delivery"]["attachment_id"] = None
        value = self.write_version_two_result(report)
        self.assert_invalid_result(value, "report.delivery.attachment_id must be a non-empty string")

    def test_report_only_checkpoint_requires_finalized_result_and_skips_sit(self) -> None:
        value = self.write_version_two_result(self.retryable_report())
        checkpoint = self.version_two_checkpoint(value, mode="report-only", phase="reporting", status="report_pending")
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(checkpoint["continuation"]["result_finalized"])
        self.assertIn("不重新執行 SIT", checkpoint["continuation"]["next_safe_step"])

    def test_report_only_checkpoint_rejects_unfinalized_result(self) -> None:
        value = self.write_version_two_result(self.retryable_report())
        checkpoint = self.version_two_checkpoint(value, mode="report-only", phase="reporting", status="report_pending")
        checkpoint["continuation"]["result_finalized"] = False
        checkpoint["result_path"] = None
        checkpoint["prepared_note"] = {"path": None, "sha256": None, "status": "not_prepared"}
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("report-only requires continuation.result_finalized=true", completed.stderr)

    def test_delivery_only_checkpoint_accepts_ready_report_when_note_is_already_posted(self) -> None:
        report = self.ready_report()
        value = self.write_version_two_result(report)
        value["mantis_note"]["status"] = "posted"
        value["mantis_note"]["note_id"] = "98122"
        write_json(self.result_path, value)
        checkpoint = self.version_two_checkpoint(value, mode="delivery-only", phase="delivering", status="delivery_pending")
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_checkpoint_rejects_report_attachment_identity_mismatch(self) -> None:
        value = self.write_version_two_result(self.ready_report(delivered=True))
        checkpoint = self.version_two_checkpoint(value, mode="fresh", phase="delivering", status="completed")
        checkpoint["report"]["stored_filename"] = "guessed-local-name.docx"
        checkpoint_path = self.run_dir / "checkpoint.json"
        write_json(checkpoint_path, checkpoint)
        completed = self.run_script("validate_checkpoint.py", checkpoint_path)
        self.assertEqual(completed.returncode, 1)
        self.assertIn("checkpoint and result report identity differ", completed.stderr)


if __name__ == "__main__":
    unittest.main()
