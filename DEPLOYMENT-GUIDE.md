# SmartMed Cycle — approved update and deployment

Prepared 12 October 2026 against repository main commit `c46077a8338208792e823f1d7d071946092e1536`.
Repository: https://github.com/Keith1405/my-partyrock-app
Live website: https://d250i0gcy6fvmo.cloudfront.net/

## What this update does

- Uses the public NPRA QUEST3+ pharmaceutical catalogue for Malaysian product names and MAL registration numbers. Brand-only text is accepted. Multiple matching strengths/forms are shown for clarification; the app does not guess an ingredient. Exact product matches retrieve active ingredients and a source link.
- Keeps a restricted RxNorm fallback for explicitly matched generic ingredient names. It never substitutes a US brand for an unconfirmed Malaysian brand.
- Includes the approved shorter descriptions and placeholders, with 20px main patient text and 18px supporting text/buttons. Preserves the original layout, colours, logo, hero and floating navigation. Navigation and hero heading sizes stay original. English, Bahasa Melayu and Chinese wording is included. Existing deployment configuration is unchanged.
- Shows three nearby listed collection centres with names, addresses, phone numbers where supplied, approximate distances, Google Maps links and Directions links. Uses 1,302 validated location records from the MyMediSAFE public directory and 2,818 GeoNames postal coordinate rows, downloaded on 12 October 2026.
- Includes the pending reply-quality improvements: the precautions reply focuses on what to do and what needs checking, uses the original label even if a Medicine Card has not been generated, and avoids repeating the card.

## Deploy using GitHub Desktop (recommended)

1. Download `SmartMed-approved-update.zip` and extract it. The extracted directory contains `backend`, `frontend` and `scripts` and this guide.
2. In GitHub Desktop, open or clone `Keith1405/my-partyrock-app`. Select main and click Fetch origin / Pull origin to obtain the latest version. Save any work you already have before applying this update.
3. Copy the extracted `backend`, `frontend` and `scripts` folders into the repository folder. Merge the folders and replace the matching files. Keep their paths unchanged. Uploading only index.html will NOT install the brand lookup or location backend.
4. Review Changes in GitHub Desktop. The included `CHANGED-FILES.json` lists the expected files. Your floating-navigation code and the newest rx_abbreviations.json should not be changed. If main has changed after the baseline commit above, merge those newer edits before committing.
5. Commit with summary `Add Malaysian product lookup and nearby medicine return points`, then click Push origin. If you use a separate branch, merge it into main when ready.
6. Open https://github.com/Keith1405/my-partyrock-app/actions and select the new **Deploy SmartMed Cycle** run. Wait for both **smoke** and **deploy** to turn green. This existing workflow deploys the Python services with AWS SAM and uploads the frontend to S3.
7. Open the live website and press Ctrl+F5. If CloudFront still serves an old page, in AWS CloudFront select distribution `d250i0gcy6fvmo.cloudfront.net`, choose Invalidations → Create invalidation, and enter `/*`.

The existing workflow needs the repository's existing secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `SAM_DEPLOY_BUCKET`. No new secret, paid maps API or backend package dependency is introduced. Do not paste AWS keys into code. The services need outbound HTTPS access to NPRA; a lookup outage results in an unverified name, not a fabricated match.

## Alternative: upload using the GitHub website

Open each matching folder in the repository and use **Add file → Upload files** to replace/add the files listed in CHANGED-FILES.json at that exact path. Include the new JSON data and directory.py in backend/my_return_plan. Commit the code as one branch update where possible, then merge to main to trigger deployment. The folder layout must stay the same; do not upload the ZIP itself as the application.

## Checks after deployment

1. Enter `Panadol` without a strength. The result should ask which product matches the pack and show real product variants; it must not guess a dose.
2. Enter `NORVASC TABLET 5MG`, then separately `MAL19970269ARZ`. Both should resolve to the same NPRA product and ingredient. No taking schedule should be invented.
3. Enter a misspelling, incomplete label, or blurred photograph. The app should request clearer details and leave the identity unconfirmed.
4. Switch English → Bahasa Melayu → 中文. Check that the approved shorter descriptions translate and the larger text is readable; generate fresh results to test each response language.
5. Return plan: enter `50480 Kuala Lumpur`, `Petaling Jaya`, or `80200`. Check the centre names and open Map / Directions.
6. Enter `Klang 00000` or `50480 Johor Bahru`. The app should ask for a corrected location rather than invent a nearby centre.
7. Use a Sabah or Sarawak postcode. A broad town may need a postcode if its coordinate records span a large area.
8. Compare a medicine card with precautions: the second reply should focus on actions and questions, not reproduce all label fields. Verify the floating navigation still follows scrolling, including on a phone.

## Coverage and data maintenance

“Every Malaysian brand” cannot be guaranteed: coverage depends on NPRA's pharmaceutical records, the entered name and service availability. This is a public website adapter, not a documented NPRA API. Changed markup or an access challenge fails safely and may require adapter maintenance. Results are identity evidence, not proof that a dose is appropriate or that medicines are safe together. Lookup results are briefly cached (30 minutes for matches, 60 seconds for unsuccessful lookups). At most four label queries are checked per request; longer medicine lists need a pharmacist's full review.

The return list is a snapshot of listed collection points, not confirmation that a centre is open or accepts a particular item today. Distances are straight-line estimates from a town/postcode centre, not GPS or travel distances. Patients should call before travelling. Some town/postcode searches lack usable coordinates and will request a clearer location. The app's added value is showing nearby listed centres and direct links within the medicine workflow; the directory source remains MyMediSAFE.

Refresh the bundled data periodically from the repository root:

```powershell
python scripts/refresh_return_directory.py
python scripts/brand_location_regression.py
```

Review the changed records, commit and push to deploy the refreshed directory. The refresher refuses unexpectedly small/changed data instead of replacing the snapshot with an empty directory.

Sources and attribution:
- NPRA QUEST3+: https://quest3plus.bpfk.gov.my/pmo2/index.php
- MyMediSAFE collection directory: https://www.mymedisafe.org.my/index.html
- GeoNames postal coordinates: https://download.geonames.org/export/zip/ — Creative Commons Attribution 4.0; GeoNames attribution is displayed in return results. Coordinates are estimated by the source.

## Scope verification

This is the final approved package. It combines backend identity/location/reply fixes with exactly the three frontend files used in the reviewed preview. No infrastructure or deployment-workflow file is included. Use this ZIP instead of either earlier update ZIP.

The archive contains complete replacement versions of each changed file, not the entire repository. Merge its folders into your existing project; retain files not included in the archive. CHANGED-FILES.json lists every supplied code/data file and its hash.

## Validation performed

- 16 existing patient input/safety regressions passed (model and reference retrieval mocked).
- 14 new identity/directory regressions passed: ambiguous brands, exact match, missing ingredients, unavailable/changed sources, external detail rejection, postcode/town conflicts and actual minimum-distance ranking.
- Frontend DOM tests passed for EN/MS/ZH switching, request language, input preservation, safe links, stale-result handling and recoverable errors. These are not a full visual browser inspection.
- All five backend services passed local startup, CORS, streaming-route and payload-limit checks.
- Live NPRA queries passed for Panadol (ambiguous), NORVASC TABLET 5MG and its MAL number (verified).
- Live Bedrock-generated clinical replies were not tested here because this workspace has no AWS/Bedrock credentials. Test the actual deployed replies before patient use.

## Roll back

Revert this update's commit in GitHub Desktop and push the revert. The same workflow redeploys the previous version. If the browser remains stale, invalidate CloudFront `/*` and reload.
