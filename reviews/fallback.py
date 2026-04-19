"""Pre-written fallback variants used when the Anthropic API is unavailable.

The goal: sound like a real, happy customer typing on their phone — but
keep every review cleanly positive. No "but" caveats, no mentions of
waits/delays/pricing complaints. These are what an owner would actually
want to see on their Google listing.
"""

import random


FALLBACK_BY_LANGUAGE = {
    "english": [
        ("casual", "Went here on a Saturday, food came hot and fresh. Staff answered our questions without rushing and the place was clean."),
        ("enthusiastic", "Liked this place. Ordered two items, both came nicely plated. Staff was friendly and chatty in a good way."),
        ("formal", "A good experience overall. The staff were attentive and the quality of what we received was consistent with what we hoped for."),
    ],
    "hinglish": [
        ("casual", "Taste accha tha, staff ne jaldi serve kiya. Bhaiya ne menu recommend kiya aur wahi sahi tha."),
        ("enthusiastic", "Yahan regular customer hai hum. Quality har baar consistent rehti hai aur staff ka behaviour bhi polite hai."),
        ("formal", "Kaafi accha anubhav raha. Staff ne patience ke saath help ki aur jo order kiya wahi exactly mila. Aage bhi aayenge."),
    ],
    "hinglish_devanagari": [
        ("casual", "Taste अच्छा था, staff ने जल्दी serve किया। menu recommendation भी helpful थी।"),
        ("enthusiastic", "हम regular आते हैं यहाँ, quality हमेशा consistent रहती है। staff का behaviour भी polite है।"),
        ("formal", "अनुभव अच्छा रहा। staff ने patience के साथ help की और जो order किया वो exactly मिला।"),
    ],
    "minglish": [
        ("casual", "Jevan chan hota, chava pan mast. Staff ne sangitla te nit kela."),
        ("enthusiastic", "Aamhi regular customer aahot. Quality consistent aste aani staff pan changla aahe."),
        ("formal", "Anubhav baryapaiki hota. Staff vyavasthit hota aani jo order kela to velevar milala."),
    ],
    "hindi": [
        ("casual", "शनिवार को गए थे, खाना गरम और fresh मिला। staff ने बढ़िया तरीके से serve किया।"),
        ("enthusiastic", "अच्छी जगह है, हम अक्सर यहाँ आते हैं। quality में कमी नहीं आती और staff भी polite है।"),
        ("formal", "संतोषजनक अनुभव रहा। व्यवस्था ठीक थी और staff का व्यवहार भी अच्छा था।"),
    ],
    "marathi": [
        ("casual", "शनिवारी गेलो होतो, जेवण गरम होतं आणि staff पण बोलायला छान होता."),
        ("enthusiastic", "आम्ही नेहमी येतो इथे, चव नेहमी सारखी असते आणि staff पण व्यवस्थित आहे."),
        ("formal", "अनुभव समाधानकारक होता. कर्मचारी व्यवस्थित होते आणि जे मागवलं ते वेळेत मिळालं."),
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
