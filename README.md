# Daily AI LinkedIn Poster Agent

Automates **one image poster + caption each day**, with publishing targeted for **5:00 PM Asia/Kolkata** using Buffer.

## How it works
1. GitHub Actions runs at **4:15 PM IST** (time-zone-aware schedule).
2. Gemini generates educational, original LinkedIn copy.
3. Pillow renders a **1200 × 1200 PNG poster** (typographic graphic, not AI-generated photography).
4. If publishing is enabled, the action commits the PNG to this **public** GitHub repository so Buffer can access the image.
5. Buffer adds the post to the connected personal LinkedIn channel's **next available posting slot**.

**Important:** Set one daily **5:00 PM IST** slot in Buffer, and ensure the queue has no conflicting content. GitHub schedules can be delayed, and Buffer's next available slot may be tomorrow if the workflow runs late. This is a target, not an exact-time guarantee.

## Setup
1. Connect the intended personal LinkedIn account at https://buffer.com (Buffer Free).
2. In Buffer, set your LinkedIn channel posting schedule to daily at **17:00 Asia/Kolkata**.
3. Create a Buffer API key at https://publish.buffer.com/settings/api and obtain the **LinkedIn channel ID** using https://developers.buffer.com/guides/getting-started.html.
4. Obtain a Gemini API key at https://aistudio.google.com/apikey. Availability and free quota depend on account/model.
5. Under **Settings > Secrets and variables > Actions** for this repository, add:
   - Secrets: `GEMINI_API_KEY`, `BUFFER_API_KEY`
   - Variables: `BUFFER_CHANNEL_ID`, `ENABLE_PUBLISH` = `false`
   - Optional variables: `GEMINI_MODEL` (defaults to `gemini-2.5-flash`), `POSTER_BRAND`.
6. Open **Actions > Daily LinkedIn Poster > Run workflow**. Confirm a dry-run caption in the logs.
7. Set `ENABLE_PUBLISH` to `true`; manually run once to check the PNG and Buffer queue (it will create a real scheduled post).
8. Confirm Buffer's due time is 5:00 PM IST. Watch the first scheduled publication and GitHub Actions logs.

## Safety and limits
- Publishing defaults to **OFF**; no API credentials are stored in source code.
- The repo is public. Do not commit personal, secret, or confidential information.
- Duplicate prevention uses `posts/YYYY-MM-DD.json`. If Buffer succeeds but the final receipt fails, inspect Buffer before manually rerunning.
- Buffer Free queue length and API quotas apply. Gemini model free quotas can change.
- ChatGPT's GitHub connection allows conversational edits to this repository. Unattended generation is powered by the separate Gemini API, **not** a background ChatGPT session.
- This does not automatically research current news or create illustrated AI artwork.

References:
- https://developers.buffer.com/examples/create-image-post.html
- https://developers.buffer.com/guides/hosting-media.html
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
