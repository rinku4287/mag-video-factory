"""
Hindi Script & Slide Data Generator for My Admission Guru.
Produces:
  - long_scenes  (5-6 scenes for 16:9 YouTube Horizontal Video, ~50-80s)
  - short_scenes (4 punchy scenes for 9:16 YouTube Shorts / IG Reels / FB Reels, ~30-45s)
  - metadata     (Hindi + English SEO title, description, tags, hashtags)

Uses Google Gemini API if GEMINI_API_KEY is set, otherwise uses a clean zero-cost Hindi template.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

import requests


TYPE_META = {
    "form": {
        "badge_hi": "नई भर्ती 2026 • LIVE UPDATE",
        "badge_short": "🚨 नई भर्ती जारी",
        "accent": "#dc2626",
        "accent_soft": "#fee2e2",
        "hook_hi": "बड़ी सरकारी नौकरी की खबर!",
        "action_hi": "ऑनलाइन आवेदन",
    },
    "admit_card": {
        "badge_hi": "एडमिट कार्ड जारी • HALL TICKET",
        "badge_short": "🎫 एडमिट कार्ड जारी",
        "accent": "#0284c7",
        "accent_soft": "#e0f2fe",
        "hook_hi": "एडमिट कार्ड जारी हो गया है!",
        "action_hi": "एडमिट कार्ड डाउनलोड",
    },
    "answer_key": {
        "badge_hi": "ऑफिशियल आंसर की • ANSWER KEY",
        "badge_short": "🔑 आंसर की जारी",
        "accent": "#7c3aed",
        "accent_soft": "#ede9fe",
        "hook_hi": "ऑफिशियल आंसर की जारी हो गई है!",
        "action_hi": "आंसर की चेक",
    },
    "result": {
        "badge_hi": "ऑफिशियल रिजल्ट जारी • MERIT LIST",
        "badge_short": "🏆 रिजल्ट जारी",
        "accent": "#15803d",
        "accent_soft": "#dcfce7",
        "hook_hi": "ऑफिशियल रिजल्ट घोषित हो गया है!",
        "action_hi": "रिजल्ट चेक",
    },
}


def nice_date(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[: len(fmt)], fmt).strftime("%d %b %Y")
        except ValueError:
            continue
    return raw


def parse_kv_lines(text: str, limit: int = 5) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for ln in (text or "").splitlines():
        ln = ln.strip(" -•*\t")
        if not ln:
            continue
        if ":" in ln:
            k, v = ln.split(":", 1)
            out.append((k.strip()[:48], v.strip()[:90]))
        else:
            out.append(("Detail", ln[:110]))
        if len(out) >= limit:
            break
    return out


def parse_bullets(text: str, limit: int = 4) -> list[str]:
    out: list[str] = []
    for ln in (text or "").splitlines():
        ln = ln.strip(" -•*0123456789.)\t")
        if ln:
            out.append(ln[:130])
        if len(out) >= limit:
            break
    return out


def _gemini_polish_narrations(payload: dict[str, Any], scenes: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return scenes

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    prompt = (
        "You are a professional Hindi education & govt-job YouTube anchor for My Admission Guru (myadmissionguru.com).\n"
        f"Rewrite ONLY the 'narration' field of each scene below into natural, crisp, engaging spoken Hindi (Devanagari script) "
        f"suitable for a {'60-second YouTube video' if mode == 'long' else '35-second YouTube Short / Instagram Reel'}.\n"
        "Rules:\n"
        "- Keep all numbers, dates, fees, post counts, and exam names 100% accurate.\n"
        "- Use natural spoken Hindi (like 'नमस्कार दोस्तों, My Admission Guru में आपका स्वागत है').\n"
        "- Each scene narration should be 18-32 words (concise, energetic, no markdown symbols, no emojis).\n"
        "- Return STRICT JSON array of strings, same length as input scenes.\n\n"
        f"Update info: {json.dumps({k: payload.get(k) for k in ('title', 'organisation', 'type', 'vacancies', 'qualification', 'apply_end', 'exam_date')}, ensure_ascii=False)}\n"
        f"Draft narrations: {json.dumps([s['narration'] for s in scenes], ensure_ascii=False)}"
    )

    try:
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
            },
            timeout=25,
        )
        if resp.status_code == 200:
            txt = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            arr = json.loads(txt)
            if isinstance(arr, list) and len(arr) == len(scenes):
                for s, new_n in zip(scenes, arr):
                    if isinstance(new_n, str) and new_n.strip():
                        s["narration"] = re.sub(r"[*_#`]+", "", new_n).strip()
    except Exception as exc:
        print(f"[script_gen] Gemini polish skipped ({exc}); using clean template.")
    return scenes


def build_scripts(payload: dict[str, Any]) -> dict[str, Any]:
    u_type = str(payload.get("type") or "form").lower()
    meta = TYPE_META.get(u_type, TYPE_META["form"])

    title = str(payload.get("title") or "Latest Sarkari Update").strip()
    org = str(payload.get("organisation") or "Official Recruitment Board").strip()
    course = str(payload.get("course") or "").strip()
    vac = int(payload.get("vacancies") or 0)
    vac_str = f"{vac:,} पद (Posts)" if vac > 0 else "ऑफिशियल नोटिफिकेशन देखें"
    qual = str(payload.get("qualification") or "10th / 12th / Graduate (नोटिफिकेशन देखें)").strip()
    apply_start = nice_date(str(payload.get("apply_start") or ""))
    apply_end = nice_date(str(payload.get("apply_end") or ""))
    exam_date = nice_date(str(payload.get("exam_date") or ""))
    url = str(payload.get("url") or "https://myadmissionguru.com").strip()

    dates_rows = parse_kv_lines(str(payload.get("dates_text") or ""), limit=5)
    if not dates_rows:
        if apply_start:
            dates_rows.append(("आवेदन शुरू (Start Date)", apply_start))
        if apply_end:
            dates_rows.append(("अंतिम तिथि (Last Date)", apply_end))
        if exam_date:
            dates_rows.append(("परीक्षा तिथि (Exam Date)", exam_date))
        if not dates_rows:
            dates_rows.append(("अपडेट स्टेटस", "ऑफिशियल पोर्टल पर लाइव"))

    fee_rows = parse_kv_lines(str(payload.get("fees") or ""), limit=4)
    if not fee_rows:
        fee_rows = [
            ("General / OBC / EWS", "ऑफिशियल नोटिफिकेशन के अनुसार"),
            ("SC / ST / Female", "नियमानुसार छूट / Online Mode"),
        ]

    age_bullets = parse_bullets(str(payload.get("age_limit") or ""), limit=3)
    if not age_bullets:
        age_bullets = ["न्यूनतम आयु: 18 वर्ष (नियमानुसार आरक्षण में छूट)"]

    elig_bullets = parse_bullets(str(payload.get("eligibility") or ""), limit=3)
    if not elig_bullets:
        elig_bullets = [qual]

    steps_bullets = parse_bullets(str(payload.get("how_to_apply") or ""), limit=4)
    if not steps_bullets:
        steps_bullets = [
            "myadmissionguru.com पर जाएं और इस अपडेट को खोलें।",
            "Important Links में डायरेक्ट ऑफिशियल लिंक पर क्लिक करें।",
            "अपनी डिटेल्स भरें और फाइनल कन्फर्मेशन सेव करें।",
        ]

    # ---------- LONG VIDEO SCENES (16:9 Horizontal) ----------
    long_scenes: list[dict[str, Any]] = [
        {
            "id": "intro",
            "kind": "hero",
            "heading": title,
            "subheading": org,
            "highlight": vac_str if u_type == "form" else meta["badge_short"],
            "rows": [
                ("बोर्ड / संस्था", org),
                ("कुल पद / अपडेट", vac_str if u_type == "form" else meta["action_hi"]),
                ("अंतिम / परीक्षा तिथि", apply_end or exam_date or "अभी चेक करें"),
            ],
            "narration": (
                f"नमस्कार दोस्तों, My Admission Guru में आपका स्वागत है। {meta['hook_hi']} "
                f"{org} ने {title} जारी कर दिया है। "
                + (f"इसमें कुल {vac} पदों पर भर्ती निकाली गई है। " if vac > 0 and u_type == "form" else "")
                + "आइए जानते हैं पूरी जानकारी हिंदी में।"
            ),
        },
        {
            "id": "dates",
            "kind": "table",
            "heading": "महत्वपूर्ण तिथियां (Important Dates)",
            "subheading": title,
            "rows": dates_rows,
            "narration": (
                "सबसे पहले महत्वपूर्ण तिथियों की बात करते हैं। "
                + (f"ऑनलाइन आवेदन {apply_start} से शुरू हो चुके हैं। " if apply_start else "")
                + (f"आवेदन की अंतिम तिथि {apply_end} रखी गई है। " if apply_end else "")
                + (f"परीक्षा की संभावित तिथि {exam_date} है। " if exam_date else "")
                + "समय रहते अपना काम पूरा कर लें।"
            ),
        },
    ]

    if u_type == "form":
        long_scenes.append(
            {
                "id": "eligibility",
                "kind": "bullets",
                "heading": "योग्यता और आयु सीमा (Eligibility & Age)",
                "subheading": course or qual,
                "bullets": elig_bullets[:2] + age_bullets[:2],
                "narration": (
                    f"योग्यता की बात करें तो उम्मीदवार के पास {qual} होना आवश्यक है। "
                    + (f"{age_bullets[0]}। " if age_bullets else "")
                    + "आरक्षित वर्गों को सरकारी नियमानुसार आयु सीमा में छूट दी जाएगी।"
                ),
            }
        )
        long_scenes.append(
            {
                "id": "fees",
                "kind": "table",
                "heading": "आवेदन शुल्क (Application Fee)",
                "subheading": "ऑनलाइन पेमेंट: UPI / डेबिट कार्ड / नेट बैंकिंग",
                "rows": fee_rows,
                "narration": (
                    "आवेदन शुल्क की जानकारी स्क्रीन पर दी गई है। "
                    + " ".join(f"{k} के लिए {v}।" for k, v in fee_rows[:2])
                    + " फीस का भुगतान ऑनलाइन माध्यम से किया जा सकता है।"
                ),
            }
        )
    else:
        long_scenes.append(
            {
                "id": "highlights",
                "kind": "bullets",
                "heading": f"{meta['action_hi']} कैसे करें?",
                "subheading": org,
                "bullets": steps_bullets[:4],
                "narration": (
                    f"अब जानते हैं कि आप {meta['action_hi']} कैसे कर सकते हैं। "
                    "सबसे पहले myadmissionguru.com वेबसाइट पर जाएं, वहां Important Links सेक्शन में "
                    "डायरेक्ट ऑफिशियल लिंक पर क्लिक करें और अपने रजिस्ट्रेशन नंबर और जन्म तिथि से लॉगिन करें।"
                ),
            }
        )

    long_scenes.append(
        {
            "id": "cta",
            "kind": "cta",
            "heading": "डायरेक्ट लिंक और फ्री नोट्स PDF",
            "subheading": "myadmissionguru.com",
            "bullets": [
                f"डायरेक्ट {meta['action_hi']} लिंक डिस्क्रिप्शन में है",
                "फ्री सिलेबस, पुराने पेपर और रिवीजन नोट्स डाउनलोड करें",
                "रोज़ाना सरकारी नौकरी अपडेट के लिए चैनल सब्सक्राइब करें",
            ],
            "narration": (
                f"डायरेक्ट {meta['action_hi']} लिंक और फ्री स्टडी नोट्स के लिए अभी जाएं myadmissionguru.com पर, "
                "जिसका लिंक वीडियो के डिस्क्रिप्शन में दिया गया है। "
                "ऐसी ही ताज़ा सरकारी नौकरी और एडमिट कार्ड अपडेट के लिए चैनल को सब्सक्राइब और वीडियो को लाइक ज़रूर करें। धन्यवाद!"
            ),
        }
    )

    # ---------- SHORT / REEL SCENES (9:16 Portrait) ----------
    short_scenes: list[dict[str, Any]] = [
        {
            "id": "s_hook",
            "kind": "hero",
            "heading": title,
            "subheading": org,
            "highlight": vac_str if u_type == "form" else meta["badge_short"],
            "rows": [
                ("संस्था", org),
                ("अपडेट", vac_str if u_type == "form" else meta["action_hi"]),
            ],
            "narration": (
                f"{meta['hook_hi']} {org} ने {title} जारी किया है। "
                + (f"कुल {vac} पदों पर भर्ती है। " if vac > 0 and u_type == "form" else "")
            ),
        },
        {
            "id": "s_dates",
            "kind": "table",
            "heading": "ज़रूरी तारीखें",
            "subheading": "आखिरी तारीख से पहले चेक करें",
            "rows": dates_rows[:3],
            "narration": (
                (f"अंतिम तिथि {apply_end} है। " if apply_end else "")
                + (f"परीक्षा तिथि {exam_date} तय की गई है। " if exam_date else "")
                + (f"योग्यता: {qual}। " if u_type == "form" else "ऑफिशियल लिंक एक्टिव हो गया है। ")
            ),
        },
        {
            "id": "s_cta",
            "kind": "cta",
            "heading": "डायरेक्ट लिंक कहाँ मिलेगा?",
            "subheading": "myadmissionguru.com",
            "bullets": [
                "Google पर सर्च करें: myadmissionguru.com",
                f"डायरेक्ट {meta['action_hi']} लिंक + फ्री नोट्स",
                "Follow / Subscribe करें रोज़ाना अपडेट के लिए!",
            ],
            "narration": (
                f"पूरी जानकारी, डायरेक्ट {meta['action_hi']} लिंक और फ्री नोट्स के लिए अभी विजिट करें "
                "myadmissionguru.com, लिंक बायो और डिस्क्रिप्शन में है। ऐसे ही अपडेट के लिए अभी फॉलो और सब्सक्राइब करें!"
            ),
        },
    ]

    long_scenes = _gemini_polish_narrations(payload, long_scenes, "long")
    short_scenes = _gemini_polish_narrations(payload, short_scenes, "short")

    # SEO Metadata
    yt_title_long = f"{title} | Full Details in Hindi | {org}"[:98]
    yt_title_short = f"{meta['badge_short']} {title[:62]} #Shorts"[:98]

    hashtags = (
        "#SarkariNaukri #GovtJobs2026 #MyAdmissionGuru #SarkariResult #HindiUpdate"
        if u_type == "form"
        else "#AdmitCard #AnswerKey #SarkariResult #MyAdmissionGuru #ExamUpdate"
    )

    desc_lines = [
        f"🔥 {title} — Full Details in Hindi",
        "",
        f"🏛️ Organisation: {org}",
    ]
    if vac > 0:
        desc_lines.append(f"📌 Total Vacancies: {vac:,} Posts")
    if qual:
        desc_lines.append(f"🎓 Qualification: {qual}")
    if apply_end:
        desc_lines.append(f"⏳ Last Date: {apply_end}")
    if exam_date:
        desc_lines.append(f"🗓️ Exam Date: {exam_date}")
    desc_lines += [
        "",
        f"👉 Direct Link, Official Notification & Free Notes PDF:",
        url,
        "",
        "🌐 Website: https://myadmissionguru.com",
        "",
        hashtags,
    ]
    description = "\n".join(desc_lines)

    tags = [
        "My Admission Guru",
        "Sarkari Naukri",
        "Govt Jobs 2026",
        "Sarkari Result",
        org[:40],
        u_type.replace("_", " "),
        "Hindi Job Update",
    ]

    return {
        "meta": meta,
        "long_scenes": long_scenes,
        "short_scenes": short_scenes,
        "yt_title_long": yt_title_long,
        "yt_title_short": yt_title_short,
        "description": description,
        "social_caption": f"{meta['badge_short']} {title}\n\n👉 Full Details & Direct Link: {url}\n\n{hashtags}",
        "tags": [t for t in tags if t],
    }
