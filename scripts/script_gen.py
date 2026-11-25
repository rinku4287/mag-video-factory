"""
Hindi Script & Slide Data Generator for My Admission Guru.
Produces:
  - long_scenes  (9 detailed scenes for 16:9 YouTube Horizontal Video -> 3:15 to 3:45 minutes)
  - short_scenes (3 punchy scenes for 9:16 YouTube Shorts / IG Reels / FB Reels -> 35 to 50 seconds, strictly < 60s)
  - metadata     (Hindi + English SEO title, description, tags, hashtags)

Uses Google Gemini API if GEMINI_API_KEY is set, otherwise uses a rich zero-cost Hindi template.
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

    if mode == "long":
        length_rule = (
            "This is a 3.5-minute YouTube full-detail video. "
            "Each scene narration MUST be 55-70 spoken Hindi words (detailed, clear, helpful, natural teacher/anchor tone)."
        )
    else:
        length_rule = (
            "This is a YouTube Short / Instagram Reel that MUST stay strictly under 50 seconds total. "
            "Each scene narration MUST be 22-32 spoken Hindi words (punchy, fast-paced, energetic)."
        )

    prompt = (
        "You are a professional Hindi education & govt-job YouTube anchor for My Admission Guru (myadmissionguru.com).\n"
        f"Rewrite ONLY the 'narration' field of each scene below into natural, crisp, engaging spoken Hindi (Devanagari script).\n"
        "Rules:\n"
        f"- {length_rule}\n"
        "- Keep all numbers, dates, fees, post counts, and exam names 100% accurate.\n"
        "- No markdown symbols, no emojis, no bullet characters.\n"
        "- Return STRICT JSON array of strings, exact same length as input scenes.\n\n"
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
            timeout=30,
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
    course = str(payload.get("course") or title).strip()
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
            ("SC / ST / Female / PwBD", "नियमानुसार छूट / Concessional"),
            ("पेमेंट मोड", "UPI / Debit Card / Net Banking"),
        ]

    age_bullets = parse_bullets(str(payload.get("age_limit") or ""), limit=4)
    if not age_bullets:
        age_bullets = [
            "न्यूनतम आयु: 18 वर्ष (पद के अनुसार)",
            "अधिकतम आयु: ऑफिशियल नोटिफिकेशन के अनुसार",
            "OBC (3 वर्ष) और SC/ST (5 वर्ष) को आयु में छूट",
        ]

    elig_bullets = parse_bullets(str(payload.get("eligibility") or ""), limit=4)
    if not elig_bullets:
        elig_bullets = [
            f"शैक्षणिक योग्यता: {qual}",
            "मान्यता प्राप्त बोर्ड या विश्वविद्यालय से उत्तीर्ण होना अनिवार्य है",
            "पद-वार विस्तृत योग्यता के लिए ऑफिशियल नोटिफिकेशन ज़रूर पढ़ें",
        ]

    steps_bullets = parse_bullets(str(payload.get("how_to_apply") or ""), limit=4)
    if not steps_bullets:
        steps_bullets = [
            "myadmissionguru.com पर जाएं और इस अपडेट का पेज खोलें।",
            "Important Links टेबल में डायरेक्ट ऑफिशियल लिंक पर क्लिक करें।",
            "अपना रजिस्ट्रेशन नंबर, मोबाइल और ज़रूरी डिटेल्स सही से भरें।",
            "फाइनल सबमिट करके कन्फर्मेशन पेज का प्रिंट या PDF सेव रखें।",
        ]

    # =====================================================================
    # LONG VIDEO SCENES (16:9 Horizontal — 9 rich scenes -> 3:15 to 3:45 min)
    # =====================================================================
    long_scenes: list[dict[str, Any]] = [
        # Scene 1: Intro & Overview (~24s)
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
                f"नमस्कार दोस्तों, My Admission Guru में आपका बहुत-बहुत स्वागत है। {meta['hook_hi']} "
                f"{org} की तरफ से {title} को लेकर ऑफिशियल नोटिफिकेशन जारी कर दिया गया है। "
                + (f"इस भर्ती में कुल {vac} पदों पर नियुक्तियां की जानी हैं, जो सरकारी नौकरी की तैयारी कर रहे छात्रों के लिए एक शानदार अवसर है। " if vac > 0 and u_type == "form" else "लाखों उम्मीदवार इस अपडेट का बेसब्री से इंतज़ार कर रहे थे। ")
                + "आज के इस पूरे वीडियो में हम आपको हिंदी में एक-एक जानकारी विस्तार से समझाएंगे, इसलिए वीडियो को अंत तक ज़रूर देखें।"
            ),
        },
        # Scene 2: Post / Update Highlights (~22s)
        {
            "id": "overview",
            "kind": "table",
            "heading": "भर्ती / अपडेट की मुख्य जानकारी",
            "subheading": org,
            "rows": [
                ("भर्ती बोर्ड", org),
                ("पद / परीक्षा का नाम", course[:75]),
                ("कुल वैकेंसी", vac_str if u_type == "form" else "ऑफिशियल नोटिस देखें"),
                ("योग्यता स्तर", qual[:75]),
            ],
            "narration": (
                f"सबसे पहले इस नोटिफिकेशन का पूरा ओवरव्यू समझ लेते हैं। यह परीक्षा और प्रक्रिया {org} द्वारा आयोजित की जा रही है। "
                f"इसमें {course} से जुड़े महत्वपूर्ण विवरण शामिल हैं। "
                + (f"योग्यता की बात करें तो {qual} वाले उम्मीदवार इस भर्ती में शामिल हो सकते हैं। " if u_type == "form" else "उम्मीदवारों को सलाह दी जाती है कि वे ऑफिशियल पोर्टल के साथ-साथ myadmissionguru.com पर दिए गए डायरेक्ट लिंक से अपनी पूरी डिटेल्स वेरिफाई करें। ")
                + "गलत जानकारी से बचने के लिए हमेशा सत्यापित ऑफिशियल नोटिस पर ही भरोसा करें।"
            ),
        },
        # Scene 3: Important Dates (~24s)
        {
            "id": "dates",
            "kind": "table",
            "heading": "महत्वपूर्ण तिथियां (Important Dates)",
            "subheading": "आखिरी तारीख का इंतज़ार न करें — सर्वर स्लो हो सकता है",
            "rows": dates_rows,
            "narration": (
                "अब बात करते हैं सबसे ज़रूरी सेक्शन यानी महत्वपूर्ण तिथियों की। "
                + (f"ऑनलाइन आवेदन की प्रक्रिया {apply_start} से शुरू हो चुकी है। " if apply_start else "")
                + (f"फॉर्म भरने की अंतिम तिथि {apply_end} निर्धारित की गई है। " if apply_end else "")
                + (f"लिखित या ऑनलाइन परीक्षा की तिथि {exam_date} प्रस्तावित है। " if exam_date else "")
                + "हमारी हमेशा यही सलाह रहती है कि अंतिम तिथि से कम से कम तीन से चार दिन पहले अपना काम पूरा कर लें, क्योंकि आखिरी दिनों में सरकारी वेबसाइट का सर्वर बहुत धीमा हो जाता है और कई छात्रों का फॉर्म छूट जाता है।"
            ),
        },
    ]

    if u_type == "form":
        # Scene 4: Eligibility (~24s)
        long_scenes.append(
            {
                "id": "eligibility",
                "kind": "bullets",
                "heading": "शैक्षणिक योग्यता (Educational Qualification)",
                "subheading": qual[:85],
                "bullets": elig_bullets,
                "narration": (
                    f"चलिए अब शैक्षणिक योग्यता को ध्यान से समझते हैं। इस भर्ती के लिए मुख्य योग्यता {qual} रखी गई है। "
                    "आपकी डिग्री या सर्टिफिकेट किसी मान्यता प्राप्त बोर्ड या विश्वविद्यालय से होना अनिवार्य है। "
                    "यदि इस नोटिफिकेशन में एक से अधिक पद शामिल हैं, तो कुछ विशेष पदों के लिए टाइपिंग टेस्ट, कंप्यूटर सर्टिफिकेट या संबंधित विषय में डिग्री की आवश्यकता हो सकती है। "
                    "इसलिए आवेदन करने से पहले पद-वार योग्यता की जांच अवश्य कर लें।"
                ),
            }
        )
        # Scene 5: Age Limit & Relaxation (~24s)
        long_scenes.append(
            {
                "id": "age_limit",
                "kind": "bullets",
                "heading": "आयु सीमा और छूट (Age Limit & Relaxation)",
                "subheading": "सरकारी नियमानुसार श्रेणी-वार आयु में छूट लागू",
                "bullets": age_bullets,
                "narration": (
                    "आयु सीमा की बात करें तो सामान्य वर्ग के उम्मीदवारों के लिए न्यूनतम और अधिकतम आयु सीमा स्क्रीन पर दिखाई गई है। "
                    + (f"{age_bullets[0]}। " if age_bullets else "")
                    + "आरक्षित वर्गों को भारत सरकार के नियमों के अनुसार ऊपरी आयु सीमा में विशेष छूट मिलती है। "
                    "ओबीसी नॉन-क्रीमी लेयर के उम्मीदवारों को तीन वर्ष, एससी और एसटी वर्ग के उम्मीदवारों को पांच वर्ष, तथा दिव्यांग और पूर्व सैनिक अभ्यर्थियों को अतिरिक्त छूट प्रदान की जाती है। "
                    "अपनी जन्म तिथि की गणना नोटिफिकेशन की कट-ऑफ तारीख के अनुसार ही करें।"
                ),
            }
        )
        # Scene 6: Application Fee (~22s)
        long_scenes.append(
            {
                "id": "fees",
                "kind": "table",
                "heading": "आवेदन शुल्क (Application Fee)",
                "subheading": "ऑनलाइन पेमेंट: UPI / डेबिट कार्ड / क्रेडिट कार्ड / नेट बैंकिंग",
                "rows": fee_rows,
                "narration": (
                    "अब आवेदन शुल्क की पूरी जानकारी देख लेते हैं। श्रेणी के अनुसार निर्धारित फीस आपकी स्क्रीन पर दी गई है। "
                    + " ".join(f"{k} के लिए {v}।" for k, v in fee_rows[:2])
                    + " शुल्क का भुगतान पूरी तरह ऑनलाइन माध्यम से यूपीआई, डेबिट कार्ड, क्रेडिट कार्ड या नेट बैंकिंग द्वारा किया जा सकता है। "
                    "पेमेंट करने के बाद ट्रांजैक्शन रसीद और कन्फर्मेशन पेज को सुरक्षित ज़रूर सेव कर लें, ताकि भविष्य में कोई समस्या न आए।"
                ),
            }
        )
        # Scene 7: Selection Process & Exam Pattern (~24s)
        long_scenes.append(
            {
                "id": "selection",
                "kind": "bullets",
                "heading": "चयन प्रक्रिया (Selection Process)",
                "subheading": "स्टेज-बाय-स्टेज तैयारी की सही रणनीति",
                "bullets": [
                    "चरण 1: लिखित परीक्षा / कंप्यूटर आधारित टेस्ट (CBT)",
                    "चरण 2: स्किल टेस्ट / फिजिकल टेस्ट (पद के अनुसार)",
                    "चरण 3: डॉक्यूमेंट वेरिफिकेशन (DV) और मेडिकल जांच",
                    "फाइनल मेरिट लिस्ट: परीक्षा में प्राप्त अंकों के आधार पर",
                ],
                "narration": (
                    "चयन प्रक्रिया की बात करें तो उम्मीदवारों को आमतौर पर लिखित परीक्षा या कंप्यूटर आधारित टेस्ट यानी सीबीटी से गुजरना होता है। "
                    "इसके बाद पद की आवश्यकता के अनुसार स्किल टेस्ट, टाइपिंग टेस्ट या फिजिकल परीक्षा आयोजित की जाती है। "
                    "अंतिम चरण में दस्तावेज़ सत्यापन और मेडिकल परीक्षण के बाद फाइनल मेरिट लिस्ट जारी होती है। "
                    "ध्यान रखें कि अधिकांश प्रतियोगी परीक्षाओं में नेगेटिव मार्किंग भी होती है, इसलिए सटीकता यानी एक्यूरेसी पर विशेष ध्यान देना ज़रूरी है।"
                ),
            }
        )
    elif u_type == "admit_card":
        long_scenes += [
            {
                "id": "ac_docs",
                "kind": "bullets",
                "heading": "परीक्षा केंद्र पर क्या-क्या ले जाएं?",
                "subheading": "इन दस्तावेज़ों के बिना परीक्षा हॉल में एंट्री नहीं मिलेगी",
                "bullets": [
                    "एडमिट कार्ड का स्पष्ट A4 प्रिंटआउट (रंगीन या ब्लैक एंड व्हाइट)",
                    "1 मूल फोटो पहचान पत्र (आधार कार्ड / पैन / वोटर आईडी / ड्राइविंग लाइसेंस)",
                    "2 हालिया पासपोर्ट साइज़ रंगीन फोटोग्राफ",
                    "रिपोर्टिंग टाइम से कम से कम 45 मिनट पहले केंद्र पर पहुंचें",
                ],
                "narration": (
                    "परीक्षा केंद्र पर जाते समय किन दस्तावेज़ों को साथ रखना अनिवार्य है, इसे बहुत ध्यान से समझ लें। "
                    "सबसे पहले अपने एडमिट कार्ड का साफ-सुथरा ए-फोर प्रिंटआउट निकाल लें। "
                    "इसके साथ एक मूल सरकारी फोटो पहचान पत्र जैसे आधार कार्ड, पैन कार्ड, वोटर आईडी या ड्राइविंग लाइसेंस ज़रूर रखें, जिसमें आपकी जन्म तिथि एडमिट कार्ड से बिल्कुल मेल खाती हो। "
                    "साथ ही दो ताज़ा पासपोर्ट साइज़ फोटो भी रख लें और रिपोर्टिंग टाइम से कम से कम पैंतालीस मिनट पहले केंद्र पर पहुंच जाएं।"
                ),
            },
            {
                "id": "ac_check",
                "kind": "bullets",
                "heading": "एडमिट कार्ड में ये 4 चीज़ें ज़रूर चेक करें",
                "subheading": "गलती होने पर तुरंत हेल्पडेस्क से संपर्क करें",
                "bullets": [
                    "आपका नाम, पिता का नाम और जन्म तिथि की स्पेलिंग",
                    "फोटो और हस्ताक्षर स्पष्ट रूप से दिखाई दे रहे हों",
                    "परीक्षा तिथि, शिफ्ट टाइमिंग और रिपोर्टिंग गेट बंद होने का समय",
                    "परीक्षा केंद्र का पूरा पता और लोकेशन पहले से चेक कर लें",
                ],
                "narration": (
                    "एडमिट कार्ड डाउनलोड करने के तुरंत बाद चार ज़रूरी जानकारियों की जांच करना न भूलें। "
                    "पहली, आपका नाम, पिता का नाम और जन्म तिथि बिल्कुल सही लिखी हो। "
                    "दूसरी, आपकी फोटो और सिग्नेचर साफ दिखाई दे रहे हों। "
                    "तीसरी, आपकी परीक्षा की तारीख, शिफ्ट का समय और गेट बंद होने का समय नोट कर लें। "
                    "और चौथी, परीक्षा केंद्र का पूरा पता एक दिन पहले ही गूगल मैप पर देख लें ताकि परीक्षा के दिन किसी तरह की देरी या तनाव न हो।"
                ),
            },
            {
                "id": "ac_rules",
                "kind": "bullets",
                "heading": "परीक्षा हॉल के ज़रूरी नियम",
                "subheading": "प्रतिबंधित वस्तुएं घर पर ही छोड़ कर जाएं",
                "bullets": [
                    "मोबाइल फोन, स्मार्टवॉच, ब्लूटूथ और कैलकुलेटर सख्त मना हैं",
                    "कोई भी इलेक्ट्रॉनिक गैजेट या कागज़ की पर्ची साथ न रखें",
                    "सिर्फ पारदर्शी पानी की बोतल और साधारण बॉल पेन (नियम अनुसार)",
                    "एडमिट कार्ड पर दिए गए सभी निर्देश एक बार पूरा पढ़ें",
                ],
                "narration": (
                    "परीक्षा केंद्र के नियमों का पालन करना बेहद ज़रूरी है। परीक्षा हॉल के अंदर मोबाइल फोन, स्मार्टवॉच, ब्लूटूथ डिवाइस, कैलकुलेटर या किसी भी तरह का इलेक्ट्रॉनिक गैजेट ले जाना पूरी तरह प्रतिबंधित है। "
                    "बेहतर यही होगा कि आप ऐसी कोई भी चीज़ अपने साथ न ले जाएं या बाहर सुरक्षित व्यवस्था कर लें। "
                    "एडमिट कार्ड के दूसरे पेज पर दिए गए सभी कोविड या सामान्य निर्देशों को एक बार शांति से ज़रूर पढ़ लें।"
                ),
            },
            {
                "id": "ac_revision",
                "kind": "bullets",
                "heading": "अंतिम दिनों में रिवीजन कैसे करें?",
                "subheading": "आखिरी समय में स्मार्ट रणनीति ही सिलेक्शन दिलाती है",
                "bullets": [
                    "नया टॉपिक पढ़ने के बजाय पुराने नोट्स और फॉर्मूले दोहराएं",
                    "पिछले वर्षों के सबसे ज़्यादा पूछे गए प्रश्न (PYQs) हल करें",
                    "रोज़ाना 1 फुल मॉक टेस्ट दें और गलतियों का विश्लेषण करें",
                    "पर्याप्त नींद लें और परीक्षा में नेगेटिव मार्किंग से बचें",
                ],
                "narration": (
                    "अब जब एडमिट कार्ड आ चुका है और परीक्षा में बहुत कम दिन बचे हैं, तो नया सिलेबस शुरू करने की गलती बिल्कुल न करें। "
                    "केवल अपने शॉर्ट नोट्स, महत्वपूर्ण फॉर्मूले और करंट अफेयर्स का तेज़ी से रिवीजन करें। "
                    "पिछले वर्षों के प्रश्न पत्र हल करने से आपको परीक्षा के असली स्तर का अंदाज़ा लग जाता है। "
                    "परीक्षा के दौरान शांत दिमाग रखें, पहले आसान सवाल हल करें और तुक्का लगाने से बचें ताकि नेगेटिव मार्किंग आपका स्कोर कम न करे।"
                ),
            },
        ]
    else:
        # answer_key / result
        long_scenes += [
            {
                "id": "ak_score",
                "kind": "bullets",
                "heading": "अपना सही स्कोर (Raw Marks) कैसे निकालें?",
                "subheading": "नेगेटिव मार्किंग के साथ सटीक गणना करें",
                "bullets": [
                    "सही उत्तरों की संख्या × प्रति प्रश्न अंक जोड़ें",
                    "गलत उत्तरों की संख्या × नेगेटिव मार्किंग अंक घटाएं",
                    "छोड़े गए (Unattempted) प्रश्नों के 0 अंक होते हैं",
                    "नॉर्मलाइज़ेशन के बाद फाइनल स्कोर में थोड़ा बदलाव संभव है",
                ],
                "narration": (
                    "आंसर की या रिस्पॉन्स शीट देखने के बाद अपना सटीक रॉ स्कोर निकालना बहुत आसान है। "
                    "सबसे पहले अपने सभी सही उत्तरों को गिनें और उन्हें प्रति प्रश्न मिलने वाले अंकों से गुणा करें। "
                    "इसके बाद अपने गलत उत्तरों की गिनती करें और परीक्षा के नियम अनुसार नेगेटिव मार्किंग के अंक कुल स्कोर में से घटा दें। "
                    "जिन सवालों को आपने नहीं छुआ है, उनका कोई अंक नहीं कटता। यदि परीक्षा कई शिफ्टों में हुई है, तो फाइनल रिजल्ट में नॉर्मलाइज़ेशन का फायदा भी मिल सकता है।"
                ),
            },
            {
                "id": "ak_objection",
                "kind": "bullets",
                "heading": "गलत प्रश्न पर आपत्ति (Objection) कैसे दर्ज करें?",
                "subheading": "तय समय सीमा के अंदर ऑफिशियल प्रूफ अपलोड करें",
                "bullets": [
                    "ऑफिशियल पोर्टल पर लॉगिन करके 'Raise Objection' विकल्प चुनें",
                    "गलत प्रश्न की Question ID और सही विकल्प सेलेक्ट करें",
                    "प्रमाण के रूप में NCERT या मानक सरकारी पुस्तक का पेज अपलोड करें",
                    "निर्धारित आपत्ति शुल्क जमा करें और रसीद सुरक्षित रखें",
                ],
                "narration": (
                    "यदि आपको लगता है कि प्रोविजनल आंसर की में किसी प्रश्न का उत्तर गलत दिया गया है, तो आप समय सीमा के भीतर ऑनलाइन आपत्ति यानी ऑब्जेक्शन दर्ज कर सकते हैं। "
                    "इसके लिए पोर्टल पर लॉगिन करके संबंधित क्वेश्चन आईडी चुनें और प्रमाण के तौर पर एनसीईआरटी या किसी प्रामाणिक सरकारी पुस्तक का स्क्रीनशॉट अपलोड करें। "
                    "यदि आपकी आपत्ति सही पाई जाती है, तो फाइनल आंसर की में सुधार किया जाता है और कई बोर्ड आपत्ति शुल्क भी वापस कर देते हैं।"
                ),
            },
            {
                "id": "ak_next",
                "kind": "bullets",
                "heading": "आगे की प्रक्रिया (Cut-Off और Result)",
                "subheading": "अगले चरण के लिए अभी से तैयारी शुरू कर दें",
                "bullets": [
                    "सभी आपत्तियों की जांच के बाद फाइनल आंसर की जारी होगी",
                    "इसके बाद श्रेणी-वार कट-ऑफ और मेरिट लिस्ट घोषित की जाएगी",
                    "क्वालीफाई होने वाले छात्रों को अगले चरण (Tier-2 / DV) के लिए बुलाया जाएगा",
                    "अपने सभी मूल दस्तावेज़ (मार्कशीट, जाति, निवास) तैयार रखें",
                ],
                "narration": (
                    "अब जानते हैं कि आगे क्या होने वाला है। ऑब्जेक्शन विंडो बंद होने के बाद विशेषज्ञ समिति सभी आपत्तियों की जांच करेगी और फिर फाइनल आंसर की जारी की जाएगी। "
                    "उसी फाइनल आंसर की के आधार पर आपका रिजल्ट और श्रेणी-वार कट-ऑफ तैयार होगा। "
                    "यदि आपका स्कोर पिछले वर्ष की कट-ऑफ के आसपास या उससे ऊपर बन रहा है, तो बिना समय गंवाए अगले चरण यानी टियर-टू, स्किल टेस्ट या डॉक्यूमेंट वेरिफिकेशन की तैयारी आज से ही शुरू कर दें।"
                ),
            },
            {
                "id": "ak_docs",
                "kind": "bullets",
                "heading": "डॉक्यूमेंट वेरिफिकेशन के लिए ज़रूरी कागज़ात",
                "subheading": "रिजल्ट के बाद समय कम मिलता है — पहले से तैयार रखें",
                "bullets": [
                    "10वीं, 12वीं और ग्रेजुएशन की मूल मार्कशीट और सर्टिफिकेट",
                    "नवीनतम जाति प्रमाण पत्र (OBC-NCL / SC / ST / EWS)",
                    "मूल निवास प्रमाण पत्र और आधार / पैन कार्ड",
                    "ऑनलाइन एप्लीकेशन फॉर्म और एडमिट कार्ड की कॉपी",
                ],
                "narration": (
                    "अक्सर छात्र रिजल्ट आने के बाद दस्तावेज़ बनवाने के लिए भागदौड़ करते हैं, जिससे कई बार दिक्कत आ जाती है। "
                    "इसलिए अभी से अपनी दसवीं, बारहवीं और ग्रेजुएशन की मार्कशीट, जाति प्रमाण पत्र, ईडब्ल्यूएस सर्टिफिकेट, निवास प्रमाण पत्र और आवेदन फॉर्म की प्रति एक फाइल में व्यवस्थित करके रख लें। "
                    "खासकर ओबीसी नॉन-क्रीमी लेयर और ईडब्ल्यूएस सर्टिफिकेट निर्धारित फॉर्मेट और वैध वित्तीय वर्ष का ही होना चाहिए।"
                ),
            },
        ]

    # Scene 8: Step-by-Step How to Apply / Download (~24s)
    long_scenes.append(
        {
            "id": "steps",
            "kind": "bullets",
            "heading": f"{meta['action_hi']} कैसे करें? (Step-by-Step)",
            "subheading": "बिना किसी गलती के पूरा प्रोसेस समझें",
            "bullets": steps_bullets,
            "narration": (
                f"अब चलिए स्टेप-बाय-स्टेप जानते हैं कि आप घर बैठे अपने मोबाइल या लैपटॉप से {meta['action_hi']} कैसे कर सकते हैं। "
                "सबसे पहले गूगल पर myadmissionguru.com सर्च करें या वीडियो के डिस्क्रिप्शन में दिए गए सीधे लिंक पर क्लिक करें। "
                f"वहां आपको {title} का पूरा पेज मिलेगा। नीचे स्क्रॉल करने पर Important Links की टेबल में डायरेक्ट ऑफिशियल लिंक दिया गया है। "
                "उस पर क्लिक करके अपनी सही जानकारी भरें, सभी विवरण दो बार जांच लें और फाइनल कन्फर्मेशन पेज का पीडीएफ ज़रूर सेव कर लें।"
            ),
        }
    )

    # Scene 9: Preparation Notes, Direct Link & Outro CTA (~24s)
    long_scenes.append(
        {
            "id": "cta",
            "kind": "cta",
            "heading": "डायरेक्ट लिंक, सिलेबस और फ्री नोट्स PDF",
            "subheading": "myadmissionguru.com",
            "bullets": [
                f"डायरेक्ट {meta['action_hi']} लिंक वीडियो के डिस्क्रिप्शन में है",
                "फ्री 4-पेज रिवीजन चीटशीट और सिलेबस PDF डाउनलोड करें",
                "पिछले वर्षों के हल प्रश्न पत्र (PYQs) और ₹99 सिलेक्शन ई-बुक",
                "रोज़ाना सरकारी नौकरी अपडेट के लिए चैनल सब्सक्राइब करें",
            ],
            "narration": (
                f"दोस्तों, {meta['action_hi']} का डायरेक्ट ऑफिशियल लिंक, पूरा सिलेबस और फ्री रिवीजन नोट्स पीडीएफ हमने वीडियो के डिस्क्रिप्शन बॉक्स में दे दिया है। "
                "आप सीधे myadmissionguru.com पर जाकर फ्री चार-पेज की रिवीजन चीटशीट और पिछले वर्षों के महत्वपूर्ण प्रश्न भी डाउनलोड कर सकते हैं। "
                "अगर आपके मन में इस भर्ती या परीक्षा से जुड़ा कोई भी सवाल है, तो नीचे कमेंट बॉक्स में ज़रूर पूछें। "
                "वीडियो पसंद आया हो तो लाइक करें, अपने दोस्तों के साथ शेयर करें और रोज़ाना सटीक सरकारी नौकरी अपडेट के लिए My Admission Guru चैनल को सब्सक्राइब ज़रूर करें। धन्यवाद!"
            ),
        }
    )

    # =====================================================================
    # SHORT / REEL SCENES (9:16 Portrait — 3 punchy scenes -> 35 to 50 sec, < 60s!)
    # =====================================================================
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
                f"{meta['hook_hi']} {org} ने {title} जारी कर दिया है। "
                + (f"इसमें कुल {vac} पदों पर भर्ती निकाली गई है। " if vac > 0 and u_type == "form" else "ऑफिशियल लिंक अभी लाइव हो चुका है। ")
            ),
        },
        {
            "id": "s_dates",
            "kind": "table",
            "heading": "ज़रूरी तारीखें और योग्यता",
            "subheading": "आखिरी तारीख से पहले चेक करें",
            "rows": dates_rows[:3],
            "narration": (
                (f"अंतिम तिथि {apply_end} है। " if apply_end else "")
                + (f"परीक्षा तिथि {exam_date} तय की गई है। " if exam_date else "")
                + (f"योग्यता {qual} रखी गई है। " if u_type == "form" else "अपना रजिस्ट्रेशन नंबर तैयार रखें। ")
            ),
        },
        {
            "id": "s_cta",
            "kind": "cta",
            "heading": "डायरेक्ट लिंक कहाँ मिलेगा?",
            "subheading": "myadmissionguru.com",
            "bullets": [
                "Google पर सर्च करें: myadmissionguru.com",
                f"डायरेक्ट {meta['action_hi']} लिंक + फ्री नोट्स PDF",
                "Follow & Subscribe करें रोज़ाना अपडेट के लिए!",
            ],
            "narration": (
                f"पूरी जानकारी, डायरेक्ट {meta['action_hi']} लिंक और फ्री नोट्स के लिए अभी जाएं "
                "myadmissionguru.com पर, लिंक बायो और डिस्क्रिप्शन में है। ऐसे ही अपडेट के लिए अभी फॉलो और सब्सक्राइब करें!"
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
        "👉 Direct Link, Official Notification & Free Notes PDF:",
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
