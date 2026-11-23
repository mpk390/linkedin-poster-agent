"""One AI-written poster per India calendar day, optionally queued to LinkedIn through Buffer."""
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
POSTS = ROOT / "posts"
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TOPICS = [
    "practical digital marketing lessons", "AI tools for everyday work",
    "marketing analytics", "electric vehicle customer education",
    "creative storytelling for brands", "automotive customer experience",
    "lead generation best practices"
]

def required(name):
    result = os.getenv(name, "").strip()
    if not result:
        raise RuntimeError(f"Missing {name}. Add it in GitHub Actions Secrets/Variables.")
    return result

def make_content(day):
    topic = TOPICS[day.toordinal() % len(TOPICS)]
    prompt = f"""Create one useful, original professional LinkedIn educational post about {topic}.
Date: {day.isoformat()}. Audience: Indian marketing and automotive professionals.
No invented statistics, quotes, personal experience, current news or unverifiable claims.
Return ONLY a valid JSON object with:
"headline" (4-9 words),
"subhead" (8-18 words),
"caption" (100-180 words: engaging but truthful opening, 2-3 concrete lessons and a discussion question),
"hashtags" (3-5 hashtags starting with #).
Keep the image and caption on the same topic; write in English and avoid generic motivational slogans."""
    model = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
    response = requests.post(
        GEMINI_API.format(model=quote(model, safe="")),
        headers={"x-goog-api-key": required("GEMINI_API_KEY")},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8}},
        timeout=60,
    )
    response.raise_for_status()
    candidates = response.json().get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no content. Check model, quota and safety settings.")
    result = json.loads("".join(p.get("text", "") for p in candidates[0]["content"]["parts"]))
    if not all(k in result for k in ("headline", "subhead", "caption", "hashtags")):
        raise ValueError("Incomplete generated JSON")
    if not isinstance(result["hashtags"], list):
        raise ValueError("hashtags must be an array")
    return result

def font(size, bold=False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p, size)

def wrap(draw, text, width, face):
    lines, line = [], ""
    for word in re.sub(r"\\s+", " ", str(text).strip()).split():
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def poster(content, destination, day):
    im = Image.new("RGB", (1200, 1200), (247, 248, 252))
    d = ImageDraw.Draw(im)
    navy, blue, grey = (18, 34, 58), (35, 94, 190), (92, 107, 125)
    d.rectangle((0, 0, 1200, 20), fill=blue)
    d.rounded_rectangle((84, 100, 372, 162), radius=24, fill=(229, 237, 251))
    d.text((109, 115), "IDEA OF THE DAY", font=font(24, True), fill=blue)
    headline = str(content["headline"]).strip()
    for size in range(88, 46, -4):
        face = font(size, True)
        title_lines = wrap(d, headline, 1020, face)
        if len(title_lines) <= 5:
            break
    y = 270
    for line in title_lines[:5]:
        d.text((86, y), line, font=face, fill=navy)
        y += size + 27
    y += 25
    if y < 960:
        d.rounded_rectangle((86, y, 170, y + 9), radius=4, fill=blue)
    y += 55
    subface = font(35)
    for line in wrap(d, content["subhead"], 1005, subface)[:max(0, (1010-y)//52)]:
        d.text((86, y), line, font=subface, fill=grey)
        y += 52
    d.line((86, 1050, 1114, 1050), fill=(213, 221, 233), width=2)
    d.text((86, 1080), (os.getenv("POSTER_BRAND") or "INSIGHTS / DAILY")[:36],
           font=font(27, True), fill=navy)
    d.text((910, 1080), day.strftime("%d %b %Y"), font=font(24), fill=grey)
    destination.parent.mkdir(parents=True, exist_ok=True)
    im.save(destination, format="PNG", optimize=True)

def commit(files, message):
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], cwd=ROOT, check=True)
    subprocess.run(["git", "config", "user.email",
                    "41898282+github-actions[bot]@users.noreply.github.com"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", *[str(p.relative_to(ROOT)) for p in files]], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT, check=True)

def queue(caption, image_url):
    text = json.dumps(caption, ensure_ascii=False)
    channel = json.dumps(required("BUFFER_CHANNEL_ID"))
    url = json.dumps(image_url)
    mutation = f"""mutation CreatePost {{
      createPost(input: {{
        text: {text}
        channelId: {channel}
        schedulingType: automatic
        mode: addToQueue
        assets: [{{ image: {{ url: {url} }} }}]
      }}) {{
        ... on PostActionSuccess {{ post {{ id dueAt }} }}
        ... on MutationError {{ message }}
      }}
    }}"""
    r = requests.post("https://api.buffer.com",
                      headers={"Authorization": "Bearer " + required("BUFFER_API_KEY"),
                               "Content-Type": "application/json"},
                      json={"query": mutation}, timeout=45)
    r.raise_for_status()
    payload = r.json()
    if payload.get("errors"):
        raise RuntimeError(f"Buffer errors: {payload['errors']}")
    result = payload.get("data", {}).get("createPost") or {}
    if not (result.get("post") or {}).get("id"):
        raise RuntimeError(f"Buffer rejected post: {result}")
    return result["post"]

def main():
    day = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5, minutes=30)).date()
    img = POSTS / f"{day.isoformat()}.png"
    receipt = POSTS / f"{day.isoformat()}.json"
    if receipt.exists():
        item = json.loads(receipt.read_text(encoding="utf-8"))
        if item.get("buffer_post_id"):
            print("Already queued today. Skipping duplicate.")
            return
        raise RuntimeError("Existing unfinished daily record; inspect Buffer before retrying.")
    content = make_content(day)
    poster(content, img, day)
    caption = str(content["caption"]).strip() + "\\n\\n" + " ".join(content["hashtags"])
    record = {"date": day.isoformat(), "content": content, "status": "generated"}
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    if os.getenv("ENABLE_PUBLISH", "false").lower() != "true":
        print("DRY RUN: no image uploaded or post queued.")
        print("Caption preview:\\n" + caption)
        print("Image generated at:", img)
        return
    repo = required("GITHUB_REPOSITORY")
    public_url = f"https://raw.githubusercontent.com/{repo}/main/posts/{day.isoformat()}.png"
    commit([img, receipt], f"content: poster {day.isoformat()}")
    for _ in range(8):
        try:
            r = requests.get(public_url, timeout=20)
            if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image/"):
                break
        except requests.RequestException:
            pass
        time.sleep(8)
    else:
        raise RuntimeError("Poster not publicly available yet. Verify GitHub access before retrying.")
    created = queue(caption, public_url)
    record.update({"status": "queued", "buffer_post_id": created["id"],
                   "due_at": created.get("dueAt"), "image_url": public_url})
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    commit([receipt], f"receipt: Buffer post {day.isoformat()}")
    print("Queued Buffer post", created["id"], "for", created.get("dueAt"))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)
