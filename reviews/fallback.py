"""Pre-written fallback variants used when the Anthropic API is unavailable.

The goal: sound like what a real customer might type, not like stock copy.
Kept intentionally plain — short, specific, small imperfections allowed.
"""

import random


FALLBACK_BY_LANGUAGE = {
    "english": [
        ("casual", "Came here on a Saturday, service was a bit slow but the food was worth the wait. Will come again."),
        ("enthusiastic", "Liked this place. Ordered two items, both came hot and the portion size was decent. Staff was friendly too."),
        ("formal", "A satisfactory experience overall. The staff were attentive and the quality of what we received matched the price."),
    ],
    "hinglish": [
        ("casual", "Order thoda late aaya but taste accha tha, paisa vasool lagaa. Bhaiya ne bola weekend hai isliye."),
        ("enthusiastic", "Yahan regular customer hai hum, quality consistent rehti hai. Pricing bhi area ke hisaab se theek hai."),
        ("formal", "Kaafi accha anubhav raha. Staff ne time diya aur jo bola wahi mila. Aage bhi aayenge."),
    ],
    "hinglish_devanagari": [
        ("casual", "Order थोड़ा late आया पर taste अच्छा था, staff ने जल्दी से serve किया। weekend था इसलिए crowd ज़्यादा था।"),
        ("enthusiastic", "हम regular आते हैं यहाँ, quality हमेशा consistent रहती है। pricing area के हिसाब से fair है।"),
        ("formal", "अनुभव अच्छा रहा। staff ने बिना rush किये help की और जो order किया वो exactly मिला।"),
    ],
    "minglish": [
        ("casual", "Weekend la gelo hoto, thoda wait karava lagla pan jevan chan hota. Staff pan normal helpful hote."),
        ("enthusiastic", "Ekdam regular customer ahe aamhi. Chava consistent aste, pricing pan reasonable wattate aamhala."),
        ("formal", "Anubhav baryapaiki hota. Staff ne garaj nusta velevar thamb sangitla aani tabbal order milala."),
    ],
    "hindi": [
        ("casual", "शनिवार को गए थे, थोड़ा wait करना पड़ा। खाना गरम था और staff ने ठीक से बात की।"),
        ("enthusiastic", "अच्छी जगह है, हम अक्सर यहाँ आते हैं। रेट ठीक है और quality में कमी नहीं आती।"),
        ("formal", "संतोषजनक अनुभव रहा। व्यवस्था ठीक थी और मूल्य भी क्षेत्र के अनुसार उचित लगा।"),
    ],
    "marathi": [
        ("casual", "शनिवारी गेलो होतो, थोडं थांबावं लागलं पण जेवण गरम होतं. स्टाफ पण बोलायला चांगला होता."),
        ("enthusiastic", "आम्ही नेहमी येतो इथे, चव नेहमी सारखी असते. किंमत पण परवडेल अशी आहे."),
        ("formal", "अनुभव समाधानकारक होता. कर्मचारी व्यवस्थित होते आणि जे मागवलं तेच वेळेत मिळालं."),
    ],
}


def build_fallback_variants(language_mode: str, business_name: str | None = None) -> list[dict]:
    """Return 4 variants using pre-written text. Used when AI is unavailable."""
    if language_mode == "random":
        pool = []
        for lang, entries in FALLBACK_BY_LANGUAGE.items():
            for tone, text in entries:
                pool.append((lang, tone, text))
        random.shuffle(pool)
        picks = pool[:4]
    else:
        entries = FALLBACK_BY_LANGUAGE.get(language_mode) or FALLBACK_BY_LANGUAGE["english"]
        picks = []
        for i in range(4):
            tone, text = entries[i % len(entries)]
            picks.append((language_mode, tone, text))

    variants = []
    for idx, (lang, tone, text) in enumerate(picks, start=1):
        if business_name and business_name.lower() not in text.lower() and idx % 2 == 0:
            text = f"{text} — {business_name}"
        variants.append({
            "variant_number": idx,
            "language": lang,
            "tone": tone,
            "text": text,
        })
    return variants
