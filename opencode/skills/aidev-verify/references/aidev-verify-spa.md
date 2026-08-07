# aidev-verify-spa - SPA Verification Adapter (aidev-verify reference)

> Progressive-disclosure reference for `aidev-verify`. Load this file only when the active verification session involves a web UI, SPA, frontend route, component interaction, browser-visible state, frontend test output, or user-journey proof. The parent `aidev-verify` skill stays loaded; this reference adds the SPA-specific contract on demand.

This reference is a technology adapter for `aidev-verify`. It proves browser-visible SPA behavior and captures frontend test outputs as verification artifacts. It owns the instructions for turning SPA screenshots, videos, browser logs, and frontend test logs into `verification.md` evidence rows.

It works from requirements and live application behavior, not from a parent-supplied AC checklist. The parent verifier supplies the active framework/session inputs; this adapter decides how SPA artifacts map back to scenarios, tests, and ACs.

## Core rules

- Generate only verification artifacts: scripts, screenshots, videos, and logs.
- Use the fixed `verification_artifacts/` directory defined by `skills/aidev-verify/assets/spa_verify_template.py`. Do not add another CLI path override.
- Store generated SPA scripts under `verification_artifacts/scripts/`.
- Keep logs in `verification_artifacts/logs/` alongside screenshots and videos.
- Use Taskfile (`Taskfile.yml` or `Taskfile.yaml`) when available. Invoke its test tasks with `task <task-name>` instead of bypassing it with raw package-manager commands.
- Capture every executed frontend test command, including unit, component, integration, e2e, smoke, or coverage commands, with stdout, stderr, exit code, duration, command, and working directory.
- Redirect each frontend test command's output to the matching folder under `verification_artifacts/logs/`: `unit/`, `component/`, `integration/`, `e2e/`, `smoke/`, `coverage/`, or `other/` when the level cannot be classified.
- VCP browser evidence is independent of frontend test evidence. A passing unit, component, integration, e2e, smoke, or contract test never replaces VCP unless browser verification is technically infeasible or the environment disallows it.
- The test plan may name frontend test commands, but it cannot waive VCP. Treat phrases such as "no separate browser E2E harness required" as test-harness scope only, not as permission to skip browser-visible proof.
- If creating Playwright scripts, copy `skills/aidev-verify/assets/spa_verify_template.py` and preserve all standard CLI arguments: `--url`, `--headed`, `--slow-mo`, `--viewport`, `--no-screenshots`, `--no-video`, and `--video-dir`.
- Always open the exact URL emitted by the running service when terminal output provides one. Do not fabricate, hard-code, or guess a different URL.
- Before every click, use the template's `highlight_and_click()` helper so evidence includes before/after screenshots.
- A screenshot must show the claimed state unambiguously. Loading spinners, blank screens, wrong routes, and hidden states are failures.
- Treat recordings as one atomic final batch. After exploratory runs and script/timing corrections finish, remove prior recordings and rerun every feasible VCP script so retained videos all come from the same complete batch.
- `verification.md` must include an ordered VCP screenshot annex with embedded Markdown images. Artifact tables with screenshot paths are not enough for reviewer-facing VCP evidence.
- Do not write a separate SPA report. Return a `spa_verification_contribution` block that tells the parent verifier what to add to `verification.md`.

## Inputs

- Requirement file(s) from the active framework contract that are relevant to the current verification session.
- Test design artifact when available.
- Implementation evidence artifact when available.
- Optional application URL or running service output.
- Optional frontend repo root, generated script location, package manager, prior test output, screenshots, or logs.

The AC list is not an input. Infer AC coverage by cross-referencing requirement scenarios, test-plan rows, and acceptance criterion text.

## Artifact layout

Use this fixed artifact layout under `<framework-session-path>`. `verification_artifacts/` is the parent directory for all SPA verification artifacts, and `scripts/` is a child directory inside it:

```text
<framework-session-path>/
`-- verification_artifacts/
    |-- scripts/
    |-- screenshots/
    |-- videos/
    `-- logs/
        |-- unit/
        |-- component/
        |-- integration/
        |-- e2e/
        |-- smoke/
        |-- coverage/
        `-- other/
```

Generated SPA scripts are verification artifacts, but they are not reports. Copy them to `<framework-session-path>/verification_artifacts/scripts/`. Do not create or use `<framework-session-path>/scripts/` for SPA verification. The copied script must treat `<framework-session-path>/verification_artifacts/` as its artifact root. Screenshots, videos, and logs are written to other child directories of that same parent folder, as defined by `skills/aidev-verify/assets/spa_verify_template.py`.

Each frontend test command log filename must include the evidence ID, test level, and command slug, for example:

```text
verification_artifacts/logs/unit/EVID-SPA-TEST-1-unit-task-test-unit.log
verification_artifacts/logs/integration/EVID-SPA-TEST-2-integration-task-test-integration.log
```

## Verification script template contract

Use `skills/aidev-verify/assets/spa_verify_template.py` as a template, never as the working script.

For every browser evidence check / VCP:

1. Copy `skills/aidev-verify/assets/spa_verify_template.py` to the generated scripts directory.
2. Name the copy `verify_<scenario-slug>.py`, where `<scenario-slug>` is stable and human-readable.
3. Fill every VCP-specific `# TODO` section in that copied script.
4. Keep one copied script per VCP scenario. Do not mix unrelated scenarios or evidence checks in the same script.
5. Do not modify `skills/aidev-verify/assets/spa_verify_template.py` during verification runs.

Every copied script must preserve these CLI arguments exactly:

| Argument           | Type           | Default                          | Purpose                                                                                                                   |
| ------------------ | -------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `--url`            | `str` required | none                             | Target URL to verify                                                                                                      |
| `--headed`         | flag           | `False`                          | Run browser visibly for replay/debugging                                                                                  |
| `--slow-mo`        | `int`          | `0`                              | Slow-motion delay in ms for headed replay                                                                                 |
| `--viewport`       | `WxH` string   | `None`                           | Override the standard 1920x1080 viewport                                                                                  |
| `--no-screenshots` | flag           | `False`                          | Skip screenshot files                                                                                                     |
| `--no-video`       | flag           | `False`                          | Skip video files                                                                                                          |
| `--video-dir`      | `str`          | `verification_artifacts/videos/` | Override only the video output directory                                                                                  |
| `--browser`        | `str`          | `None`                           | Browser engine (`chromium`, `firefox`, `webkit`). Defaults to auto-detect (preferred order: chromium → firefox → webkit). |

Additional task-specific arguments may be added after these standard arguments, but must not rename, remove, repurpose, or make optional any standard argument.

Copied scripts must:

- Navigate to the target URL from scratch on every run.
- Respect `--no-screenshots`: every `page.screenshot()` call and every `highlight_and_click()` call must use `save_screenshots=not args.no_screenshots`.
- Respect `--no-video`: when enabled, do not pass `record_video_dir` to `browser.new_context()`.
- Use `highlight_and_click()` for every click.
- Never use `full_page=True`.
- Use `next_shot(slug)` for every screenshot so numbering is global and increasing.
- Write VCP results to `verification_artifacts/logs/verification_log.txt`.
- When copied to `<framework-session-path>/verification_artifacts/scripts/verify_<scenario-slug>.py`, write artifacts to `<framework-session-path>/verification_artifacts/`, never to `<framework-session-path>/scripts/` or `<framework-session-path>/verification_artifacts/scripts/verification_artifacts/`.
- Exit `0` only when every VCP in that script passes; exit `1` when any VCP fails.

## Prerequisites

Verify Playwright and at least one supported browser are available before browser execution:

```bash
source .venv/bin/activate 2>/dev/null || true
python3 -c "from playwright.async_api import async_playwright; print('playwright OK')"
```

## Workflow

### Step 1 - Resolve SPA inputs

1. Resolve where generated verification scripts will run: `<framework-session-path>/verification_artifacts/scripts/`.
2. Create `<framework-session-path>/verification_artifacts/scripts/`, `<framework-session-path>/verification_artifacts/screenshots/`, `<framework-session-path>/verification_artifacts/videos/`, and `<framework-session-path>/verification_artifacts/logs/`.
3. Read each supplied requirement file.
4. Read the supplied test design and implementation evidence artifacts when available.
5. Resolve the application URL from explicit input, active framework/session input, environment config, frontend config, package scripts, dev-server output, or a freshly started safe local dev server.
6. Confirm the URL responds before browser verification.
7. Decide VCP feasibility. VCP is feasible when a safe application URL is available or can be started locally, Playwright and at least one supported browser are available or approved for installation, required credentials/state are available, and the target environment is safe to exercise.
8. If VCP is not feasible, record `vcp_feasibility: blocked` with the exact reason and continue with safe frontend test commands. Do not treat tests as a replacement for the missing VCP.

Gate:

- [ ] The fixed `verification_artifacts/` directory is available.
- [ ] Requirement scenarios are available or standalone scenario derivation is possible.
- [ ] URL is resolved, or VCP feasibility is blocked with a specific reason.
- [ ] VCP is either feasible or represented as blocked browser evidence in the returned contribution.

### Step 2 - Capture frontend test outputs

Find SPA test commands in this order:

1. Commands named in the test plan's execution evidence.
2. Commands recorded in the code journal as verification evidence.
3. The defined repository-root Taskfile (`Taskfile.yml` or `Taskfile.yaml`) when present. Prefer tasks that clearly run SPA tests, such as `test`, `test-unit`, `test-component`, `test-integration`, `test-e2e`, `test-smoke`, or `test-coverage`; invoke them as `task <task-name>`.
4. Frontend package scripts that clearly run tests, such as `test`, `test:unit`, `test:component`, `test:integration`, `test:e2e`, `vitest`, `jest`, `playwright`, `cypress`, or Angular/Vue/Svelte test commands.

If task commands are not working, make sure to install all dependencies as the repo might not contain them locally yet.

When a Taskfile exposes an applicable test task, use `task <task-name>` as the evidence command and do not replace it with the underlying command unless the task itself is broken or missing. Integration, e2e, smoke, mutation, coverage, or service-backed commands are inferred only when the test plan names that level or the repo exposes an obviously safe local test task. Otherwise, record them as not run.

Run unit tests whenever a safe local unit test command exists, even when browser VCP verification is also possible. Run only safe local test commands. Build or lint commands are captured only when the test plan lists them as verification evidence. Write one log per command under the corresponding `verification_artifacts/logs/<test-level>/` folder with command, working directory, start/end time, duration, exit code, stdout, and stderr.

Gate:

- [ ] Each discovered safe test command was run or explicitly skipped with reason.
- [ ] Unit tests were run when a safe unit test command exists, or skipped with a clear reason.
- [ ] Every executed command has a test level, log path, exit status, and result.

### Step 3 - Explore the live page

Before writing scenario scripts, perform a quick browser exploration:

1. Launch a browser through Playwright (preferred order: chromium, firefox, webkit).
2. Navigate to the resolved URL.
3. Save `verification_artifacts/screenshots/explore_verify.png`.
4. Print URL, title, and an ARIA snapshot of the page body.
5. Inspect the screenshot with `view_image` before selecting VCP selectors.

Use exploration to identify stable selectors and the observable success state for each scenario.

Skip this step only when Step 1 marked VCP infeasible. In that case, continue to Step 4 and define the intended VCP scenarios as blocked browser evidence so the parent verifier can see exactly which user-visible proof is missing.

You can also navigate to the URL, take a screenshot, and print the ARIA snapshot:

```bash
python3 - <<'PY'
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def pick_browser(pw, preferred=None):
    candidates = [preferred] if preferred else ["chromium", "firefox", "webkit"]
    for name in candidates:
        try:
            browser_type = getattr(pw, name)
            b = await browser_type.launch()
            await b.close()
            return browser_type
        except Exception:
            continue
    return None

async def main():
    async with async_playwright() as pw:
        browser_type = await pick_browser(pw)
        if browser_type is None:
            print("ERROR: No supported browser found (tried: chromium, firefox, webkit).")
            return
        browser = await browser_type.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await page.goto("<START_URL>", wait_until="domcontentloaded")
        await asyncio.sleep(4)
        Path(SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=f"{SCREENSHOTS_DIR}/explore_verify.png")
        print("URL:", page.url)
        print("TITLE:", await page.title())
        print("ARIA:", (await page.locator("body").aria_snapshot())[:3000])
        await browser.close()

asyncio.run(main())
PY
```

Use `view_image` on `{SCREENSHOTS_DIR}/explore_verify.png` and read the ARIA output before proceeding. This tells you:

- What visible elements, headings, buttons, and states are present.
- Which selectors to target for each VCP.

### Step 4 - Define Visual Check Points

Derive one Visual Check Point (VCP) per meaningful user-facing scenario:

- Use requirement user stories, flows, "given/when/then", "the user can", route, form, or page-state language.
- Infer covered ACs by matching scenario wording and expected outcomes against AC text.
- Prefer scenario-level VCPs that cover multiple ACs when the flow naturally proves them together.
- Do not use "page loaded" as a VCP unless the requirement is specifically an initial visible state.
- Define VCPs from the requirements even when frontend tests already cover the same ACs.
- If VCP execution is infeasible, still define the intended VCPs and return each one with `result: blocked`, the expected observable state, affected ACs, and the feasibility reason.

You must always try to find as many VCPs as possible, even when the test plan already has frontend tests. This ensures that the outcome, once VCPs pass, is aligned with the requirement and followd ACs.

Don't be lazy: if the requirement has 10 ACs, don't return only 1 VCP that covers all of them. Return multiple VCPs that each cover a subset of ACs, so the parent verifier can see which ACs are proven by which scenario.

Gate:

- [ ] Each VCP has scenario id, scenario name, requirement ref, expected observable state, and inferred AC coverage.

### Step 5 - Generate and run scripts

For each VCP:

```
VCP1 [login-flow]:      "A user who is not authenticated is redirected to the login page"
                        Requirement ref: file.md §2.1
                        Covers ACs: AC-001, AC-007   ← inferred by matching scenario text against AC descriptions

VCP2 [submit-booking]:  "A user fills the booking form and sees a confirmation message"
                        Requirement ref: file.md §3.4
                        Covers ACs: AC-012, AC-013
```

- Use the scenario description from the requirement as the goal, not an AC ID.
- Infer which ACs the scenario covers by matching its description against AC text in the requirement.
- Use the exploration output from Step 3 to identify selectors needed to observe the scenario outcome.

Be eager to come up with VCP scenarios that cover multiple ACs at once, so `verification.md` stays concise and evidence-rich.

1. Copy `skills/aidev-verify/assets/spa_verify_template.py` to the generated scripts directory as `verify_<scenario-slug>.py`.
2. Fill every VCP-specific TODO section in the copied script.
3. Run with `--url <resolved-url>`.
4. Use `highlight_and_click()` for every click.
5. Respect `--no-screenshots`, `--no-video`, and `--video-dir`.
6. Use `next_shot(slug)` for every screenshot and write VCP log lines to `verification_artifacts/logs/verification_log.txt`.
7. Never use `full_page=True`.
8. Iterate selector and wait fixes until the result is clear, or mark the scenario as `fail`/`blocked`.
9. After all iterative runs are complete, generate the final recording batch:
10. Delete every existing `.webm` file directly inside the current session's exact `<framework-session-path>/verification_artifacts/videos/` directory. Do not delete the directory itself, recurse into other directories, follow files outside the session, or remove scripts, screenshots, or logs.
11. Rerun every feasible VCP script once with video recording enabled and the standard session video directory, including scenarios whose earlier run already passed. This complete rerun, not a selective rerun of changed or failed scenarios, is the final batch.

Do not skip this step.

Gate:

- [ ] Every VCP script exits `0`, `1`, or blocked with a documented reason.
- [ ] Every VCP has screenshots and a log entry.
- [ ] Every VCP has a recording.
- [ ] Every browser evidence check uses its own copied `verify_<scenario-slug>.py` script.
- [ ] The videos directory contains only the last complete batch, with one newly generated recording for every feasible VCP script.
- [ ] The new batch of videos is correctly reference in the journal.

### Step 6 - Self-verify artifacts

Use `view_image` on every scenario screenshot before reporting `pass`.

Fail the VCP if the screenshot does not visibly prove the claimed state, even when the script log says `PASS`.

Prepare reviewer-facing screenshot annex entries after visual inspection:

1. Include every screenshot that proves a VCP state, in the same order the VCPs ran.
2. Group screenshots under one entry per VCP/evidence ID.
3. Use Markdown image syntax with relative artifact paths, for example `![VCP1 - blocked row visible](verification_artifacts/screenshots/verify_block_pending_and_render-10-blocked_row_visible.png)`.
4. Add a one-sentence caption for each image explaining what the reviewer should see.
5. Include links only to videos from the final complete batch as supporting artifacts; videos do not replace embedded screenshots.

Gate:

- [ ] Screenshots visibly match each scenario's expected state.
- [ ] No failed screenshot is reported as pass.
- [ ] The returned contribution includes ordered annex entries for every passing or failing VCP screenshot.

### Step 7 - Return verification.md contribution

Do not write a separate SPA report. Return one structured contribution block that tells the parent verifier how to update `verification.md`:

```yaml
spa_verification_contribution:
  adapter: aidev-verify-spa
  result: pass | fail | blocked
  vcp_feasibility:
    status: feasible | blocked
    reason: <null or exact technical/environment blocker>
    tests_are_substitute: false
  add_to_evidence_reviewed:
    - evidence_id: EVID-SPA-1
      type: browser-journey | frontend-test
      source: <relative artifact path or command>
      result: pass | fail | blocked
      linked_tests: [TEST-1]
      linked_acs: [AC-1]
      notes: <short explanation>
  add_to_spa_verification_evidence:
    - scenario_id: <string>
      scenario_name: <string>
      requirement_ref: <string>
      covered_acs: [AC-1]
      result: pass | fail | blocked
      evidence:
        script_path: verification_artifacts/scripts/verify_<scenario-slug>.py
        screenshot_paths: [<relative path>]
        log_paths: [<relative path>]
        video_path: <relative path or null>
        blocked_reason: <null or exact technical/environment blocker>
  add_to_vcp_screenshot_annex:
    - order: 1
      evidence_id: EVID-SPA-1
      vcp_id: VCP1
      scenario_name: <string>
      covered_acs: [AC-1]
      result: pass | fail | blocked
      images:
        - path: verification_artifacts/screenshots/<file>.png
          alt: VCP1 - <observable state>
          caption: <one sentence describing the visible proof>
      supporting_video_path: <relative path or null>
  add_to_command_results:
    - evidence_id: EVID-SPA-2
      command: <command>
      log_path: <relative path>
      exit_code: <integer>
      duration_seconds: <number or null>
      test_level: unit | component | integration | e2e | smoke | coverage | other
      linked_tests: [TEST-2]
      linked_acs: [AC-2]
      result: pass | fail | blocked
  skipped_commands:
    - command: <command>
      test_level: unit | component | integration | e2e | smoke | coverage | other
      reason: <safety or availability reason>
      affected_tests: [TEST-2]
      affected_acs: [AC-2]
  ac_status_suggestions:
    - ac_id: AC-1
      suggested_status: pass | fail | accepted-risk | deferred
      evidence_ids: [EVID-SPA-1]
      rationale: <short reason>
  notes: <optional free text>
```

The block must be complete enough for `aidev-verify` to update these `verification.md` sections without understanding browser-specific details:

- `## Artifact Index`
- `## Evidence Reviewed`
- `## SPA Verification Evidence`
- `## Command Results`
- `## Acceptance Criteria Verification`
- `## Adapter Results`
- `## VCP Screenshot Annex`

When the parent verifier maps artifact paths into these sections, it renders them as filename-only links and registers each one in `## Artifact Index`.

## Hard rules

- Prefer Chrome (Chromium), but fall back to any available Playwright-supported browser (firefox, webkit). Respect an explicit `--browser` choice.
- Fresh navigation every run.
- One script per scenario.
- Preserve all standard CLI arguments from the template.
- Keep screenshot numbering global and increasing through `next_shot(slug)`.
- Store generated scripts under `verification_artifacts/scripts/`.
- Store screenshots, videos, and logs under the fixed `verification_artifacts/` tree.
- Before producing final evidence, delete prior `.webm` recordings only from the current session's exact `verification_artifacts/videos/` directory and generate a complete replacement batch by rerunning every feasible VCP script once. Never retain a partial or mixed-attempt batch.
- Store unit, component, integration, e2e, smoke, coverage, and other frontend test logs in their corresponding `verification_artifacts/logs/<test-level>/` folders.
- Add an ordered `## VCP Screenshot Annex` section to `verification.md` whenever VCP screenshots exist. It must embed the images with Markdown image syntax, not only list paths in tables.
- Video recording defaults on. When active, force `slow_mo` to `500` ms, wait 1 second after navigation, and wait 1 second before closing the context.
- Do not invent custom timeout constants or arbitrary delay variables.
- Never let test-plan scope, complex-track scope, or passing frontend tests suppress VCP browser evidence. VCP is included whenever technically feasible and environment-safe.
- Iterate failures before declaring them final, but do not hide real failures.
- If VCP verification is not possible because the prerequisites are not met, run safe SPA tests through the defined Taskfile when available, including unit tests when present, and report the missing browser evidence as blocked VCP evidence.

## Reference files

| Reference                    | Path                                                | Purpose                                                                         |
| ---------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------- |
| Verification script template | `skills/aidev-verify/assets/spa_verify_template.py` | Base Playwright browser-agnostic script with required CLI and artifact behavior |
