# One-page DOCX report

Read this file only when `qa.yaml` enables reports or the user requests a Word report. `qa-testing` owns orchestration, source integrity, QA gates, and private delivery. Delegate DOCX authoring and inspection mechanics to `documents:documents`; do not add a general-purpose document layout engine to this skill.

## Source and output contract

- Generate only DOCX. Do not convert or deliver PDF.
- Project from the already classified and validated `test-result.json` plus its hashed evidence. The report must repeat `result.verdict`; it cannot derive, soften, or replace the canonical verdict.
- Preserve every file under `evidence/`. If an image needs a red frame or an equally obvious focus marker, create a derived copy under `report-assets/`, record its source evidence ID and SHA-256, and use only the derived copy in the report.
- Default to one Letter-size portrait page for a non-engineering reader. Prefer omission of engineering detail over shrinking content into unreadable text.
- Name the document `Mantis <zero-padded-issue-id> 測試報告.docx`, using the project's established issue-number width when known.

## Reader-facing content

Use a black Word `Title` style with no underline, border, or decorative line. Include only what helps a general user understand the outcome quickly:

- issue title `Mantis <zero-padded-issue-id> 測試報告`;
- problem summary and test question;
- prominent `Pass`, `Fail`, or `Pending` result;
- concise actual result;
- before/after or expected/actual images with captions;
- environment, primary safe test-data identifier, recommendation, and date.

When comparing two stages, use a left/right layout if it stays readable on one page. Every screenshot with a specific verification target must visibly mark that target. For the observed underwriting pattern, frame the three first-stage passed records on the left and the completed underwriting record area on the right. Treat that example as a focus rule, not as a universal record count or domain layout.

Keep detailed environment, safe account label, acceptance focus, test data, step results, verdict, and recommendation in the private Mantis note. Do not duplicate the full procedure in Word.

## Mandatory pre-upload QA

Use the document skill's current create/edit, render verification, and accessibility workflows. A report is `ready` only after all of these pass on the final bytes:

1. Render the DOCX to page PNGs without requesting a delivered PDF.
2. Inspect every rendered page at 100% and confirm one-page Letter portrait output, readable type, clean tables, captions, and no clipping or overlap.
3. Confirm the title is black Word `Title` style and no blue or other line remains below it.
4. Confirm every required validation focus is visibly marked in the report image, including the red-frame comparison when applicable.
5. Run the accessibility audit. Give both report images meaningful alt text and mark actual table header rows; rerender after any fix and inspect again.
6. Confirm the DOCX verdict and explanatory text match the validated JSON, then hash the final DOCX and derived assets.

Do not upload a draft. A failed gate records `report.status=retryable_error`, preserves the canonical verdict and evidence, and creates a `report-only` checkpoint.

## Private attachment delivery

The preferred first delivery is one detailed private note with the final report attached through `operations:mantis add-note <issue-id> --text <prepared-note> --private --file <final-docx>`. Upload only after all QA gates pass.

Record the returned Mantis note ID, attachment ID, server-stored filename, requested filename, revision, and any delivery error. The server may suffix a repeated filename; the stored filename is authoritative and must not be inferred from the local path.

If the user requests a revision after a successful upload, create and QA a new report revision. Add a new short private note with the revised attachment and the sentence `請以本回話附件為準`; record the superseded attachment ID. Do not overwrite, delete, or pretend to replace the old Mantis attachment.

An uncertain or failed upload resumes only report delivery with the original finalized verdict, run ID, report bytes, and hashes. It never reruns SIT or creates test data.
