# Combined SmartMed patient-audit fixes

Prepared 11 October 2026. Based on GitHub main commit 533d502.

## Install and deploy together

1. Extract `SmartMed-combined-fixes.zip`. Copy the included folders and files into the repository root, keeping their paths. This is one complete frontend implementation: replace `frontend/index.html` together with its included assets. Do not splice in the earlier one-file language script or earlier language-only patch.
2. Review the changes, commit them and push to `main`. The existing GitHub Actions workflow runs backend regressions and smoke checks, builds/deploys all Lambda services with SAM, injects their Function URLs, and uploads the frontend to S3. **Uploading index.html alone cannot deploy the backend fixes.** Existing AWS secrets and stack configuration are still required.
3. Wait for both Actions jobs to succeed. In the CloudFront distribution serving your site, create an invalidation for `/*`, then refresh the website.
4. Repeat the 20 synthetic audit scenarios on the deployed site in English, Bahasa Melayu and Chinese. Check browser/mobile readability and ask a pharmacist to review safety warnings before relying on generated advice.

The `.patch` is an alternative for Git users, based on the commit above. Run `git apply --check SmartMed-combined-fixes.patch` before applying; resolve conflicts if your checkout has newer edits. Do not apply both the ZIP replacements and the patch.

## What changed

- Server-side checks reject negative values and explicit taking amounts with missing units before calling the model. Medicine Card prompts also prohibit unit inference and replace “No issues found” with a limited label-copy statement.
- Precautions verify names from original patient/label text rather than generated Medicine Card prose. Missing strengths/uncertain names remain subject to clarification; this is deliberately conservative and is not a complete medicine parser.
- Targeted, source-linked warfarin/aspirin/ibuprofen and amoxicillin/reported-penicillin-allergy checks appear before generated advice. These checks are NOT a full interaction database or clinician approval. Pharmacist review remains necessary.
- Summary instructions request three short next actions, checks and label details, with plain-language explanations of abbreviations.
- Photo extraction prompts translate unreadable/missing values and replace a wholly unreadable six-field list with one retake/type-label action. Removing/replacing a photo clears its extraction and dependent results.
- Duplicate requests are blocked; streams have cancellation/timeout ownership; partial/failed results are not passed into later widgets. Editing medicine/allergy information clears dependent results. Errors show translated retry guidance instead of internal exception text.
- Full UI translation is preserved, including status/error messages, accessibility labels, preference storage and a notice to regenerate earlier answers after changing language.
- Labelled Markdown links render correctly, unsafe HTML stays escaped, result text is larger, nested result scrolling is removed and navigation no longer overlays long outputs.
- Return plans use a short deterministic preparation flow and official MyMediSAFE locator/FAQ links. They do not invent collection-point addresses, phone numbers or hours. Postcodes use exact matches only; known town names are retained. Negative quantities stop the plan.
- Return photos are currently treated as unconfirmed; the planner does not identify medicine from the image. The patient can type the label or bring packaging to a pharmacist.

## Tests completed

- 14 offline backend regression tests, including subcases across three languages: missing-unit rejection without a model call, valid units, negative quantities, prose-name contamination, bilingual label text, priority alerts, exact-only postcodes, no invented centres, unreadable-photo handling, localized backend errors, all five Flask routes/CORS/body guards, and matching packaged validation modules.
- Frontend DOM checks: complete static translation coverage; language storage; preserved inputs; translated failures; duplicate Run/Send prevention; obsolete stream cancellation; stale label/photo invalidation; labelled links and escaped unsafe HTML.
- Python compilation and Git whitespace checks.

Run backend tests after installing the existing backend requirements: `python scripts/patient_regression.py`.
Run frontend tests with Node 20+: `npm install` then `npm test`.
The backend test is now a deployment workflow gate. Frontend tests are supplied for local/CI execution.

**These tests mock Bedrock and identity retrieval.** No live AWS model generations or deployment were performed for this package. They verify application behavior and prompt wiring, not complete medical accuracy. Actual patient comprehension, mobile/assistive-technology testing and the live 20-case rerun remain validation work after deployment.

## Directory limitation

The repository does not have an authorised, maintained collection-centre data feed. The official locator is the working path provided in this update. In-app verified listings with address/phone/hours/accepted items and a last-checked date require that data integration; this package does not pretend to have it.

## Sources checked

- NHS warfarin: https://www.nhs.uk/medicines/warfarin/
- NHS amoxicillin suitability: https://www.nhs.uk/medicines/amoxicillin/who-can-and-cannot-take-amoxicillin/
- MyMediSAFE locator: https://www.mymedisafe.org.my/index.html
- MyMediSAFE policies: https://www.mymedisafe.org.my/faq.html
