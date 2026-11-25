# My Admission Guru — Auto Hindi Video Factory (Setup Guide)

Har naye **Vacancy / Admit Card / Answer Key** par:
1. `myadmissionguru.com` (Hostinger) sirf ek lightweight JSON trigger bhejta hai (**0% video rendering on Hostinger**).
2. **GitHub Actions (100% Free)** automatically:
   - Hindi script + **Neural Hindi Voiceover** (`edge-tts`: Madhur / Swara) banata hai
   - **16:9 Horizontal Video** (YouTube Long) + **9:16 Portrait Video** (YouTube Shorts, FB Reels, IG Reels) render karta hai
   - Teeno platforms par auto-publish karta hai
   - `myadmissionguru.com/api/video-callback` par callback bhej kar **relevant page par YouTube video auto-embed** kar deta hai!

---

## Step 1: `mag-v9-19.zip` Hostinger par Deploy karein
1. Hostinger File Manager → `public_html` mein `mag-v9-19.zip` upload karke **Extract** karein.
   *(Isme `storage/`, `uploads/`, `config.php` nahi hain — aapka data 100% safe rahega. `SCHEMA_V` 15→16 automatically `youtube_id` & `youtube_short_id` columns add kar dega.)*
2. Admin Panel → **Settings** kholein. Neeche naya section dikhega:
   **Auto Hindi Video Factory (GitHub Actions → YouTube, Shorts, FB & IG)**.
3. Wahan auto-generated **`Callback Secret`** copy kar lein (Step 3 mein kaam aayega).

---

## Step 2: `mag-video-factory` ko GitHub par Push karein
1. GitHub par ek **naya Private ya Public repo** banayein, e.g. `mag-video-factory`.
   *(Note: Instagram Reels upload ke liye Meta ko temporary public MP4 URL chahiye hota hai — agar Instagram auto-post use karna hai toh repo **Public** rakhein; aapki saari keys GitHub Secrets mein 100% encrypted aur hidden rahengi.)*
2. `mag-video-factory/` folder ki saari files us repo mein push kar dein:
   ```bash
   cd mag-video-factory
   git init
   git add .
   git commit -m "Initial MAG Hindi Video Factory"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/mag-video-factory.git
   git push -u origin main
   ```

---

## Step 3: GitHub Repo Secrets Add karein
GitHub Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Required? | Kahan se milega |
|---|---|---|
| `MAG_CALLBACK_SECRET` | **Yes** | `myadmissionguru.com` Admin → Settings → Video Factory → Callback Secret |
| `YT_CLIENT_ID` | **For YouTube** | Google Cloud Console → YouTube Data API v3 OAuth Client |
| `YT_CLIENT_SECRET` | **For YouTube** | Same OAuth Client |
| `YT_REFRESH_TOKEN` | **For YouTube** | Local PC par `python scripts/get_youtube_token.py client_secret.json` chala kar |
| `FB_PAGE_ID` | **For FB Reels** | Facebook Page → About → Page ID |
| `FB_PAGE_ACCESS_TOKEN` | **For FB & IG** | Meta Developers → Graph API Explorer (Long-lived Page Token with `pages_manage_posts`, `instagram_content_publish`) |
| `IG_USER_ID` | **For IG Reels** | Meta Graph API: `GET /{FB_PAGE_ID}?fields=instagram_business_account` |
| `GEMINI_API_KEY` | Optional | Free from `aistudio.google.com` (Hindi narration aur bhi natural banane ke liye) |
| `HINDI_VOICE` | Optional | Default `hi-IN-MadhurNeural` (Male) ya `hi-IN-SwaraNeural` (Female) |

---

## Step 4: `myadmissionguru.com` ko GitHub se Connect karein
1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**:
   - Repository access: **Only select repositories** → `mag-video-factory`
   - Permissions → Repository permissions → **Contents: Read and write**
2. `myadmissionguru.com` Admin → **Settings → Auto Hindi Video Factory**:
   - **Auto-generate & publish:** `On`
   - **GitHub Repository:** `YOUR_USERNAME/mag-video-factory`
   - **GitHub Personal Access Token:** *(apna PAT paste karein)*
   - **Update types:** `form,admit_card,answer_key`
   - **Save** karein!

---

## Step 5: Pehla Free Test Run (Bina Upload kiye Video Preview!)
1. GitHub Repo → **Actions** tab → **Auto Hindi Video Factory (MAG)** → **Run workflow**.
2. `dry_run` ko **`true`** rakhein aur **Run workflow** click karein.
3. ~90 seconds mein workflow complete hoga → neeche **Artifacts** mein **`rendered-hindi-videos`** zip download karke dono videos (**16:9 Horizontal** aur **9:16 Portrait**) preview kar lein!
4. Jab look & voice perfect lage, bas `myadmissionguru.com` par naya Vacancy / Admit Card / Answer Key publish hote hi sab kuch **100% auto** chalega!
