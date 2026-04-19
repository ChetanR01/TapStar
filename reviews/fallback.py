"""Pre-written fallback variants used when the Anthropic API is unavailable."""

import random

FALLBACK_BY_LANGUAGE = {
    "english": [
        ("casual", "Really enjoyed our visit. Food was good and the staff were friendly. Will come back."),
        ("enthusiastic", "Had a fantastic time here! Everything was just right and the place had a lovely vibe."),
        ("formal", "Good overall experience. The service was attentive and the quality of offerings was consistent."),
    ],
    "hinglish": [
        ("casual", "Bhai mast experience tha, khana bhi accha aur staff bhi friendly. Zaroor wapas aayenge."),
        ("enthusiastic", "Ekdum top class! Maza aa gaya, service fast aur taste bhi jhakaas."),
        ("formal", "Achcha experience raha. Staff polite the aur quality bhi theek-thaak thi."),
    ],
    "minglish": [
        ("casual", "Chhan experience hota. Jevan mast ani staff pan friendly hota. Nakki parat yeu."),
        ("enthusiastic", "Kasla bhaari location hai! Sagla jhakaas — jevan, service, sagla."),
        ("formal", "Changla anubhav hota. Service baryapaiki hoti aani darjja suddhyacha hota."),
    ],
    "hindi": [
        ("casual", "बहुत अच्छा लगा यहाँ आकर। खाना ठीक था और स्टाफ भी अच्छा था।"),
        ("enthusiastic", "कमाल की जगह है! हर चीज़ बढ़िया थी, मज़ा आ गया।"),
        ("formal", "सेवा संतोषजनक रही। गुणवत्ता और व्यवहार दोनों सराहनीय थे।"),
    ],
    "marathi": [
        ("casual", "मस्त अनुभव होता. जेवण चांगलं आणि स्टाफ पण छान होता."),
        ("enthusiastic", "अप्रतिम जागा आहे! सगळंच मस्त — जेवण, वातावरण, सेवा."),
        ("formal", "सेवा समाधानकारक होती. गुणवत्ता आणि व्यवस्था दोन्ही उत्तम."),
    ],
}


def build_fallback_variants(language_mode: str, business_name: str | None = None) -> list[dict]:
    """Return 4 variants using pre-written text. Used when AI is unavailable."""
    if language_mode == "random":
        # Pick 4 different language/tone combos
        pool = []
        for lang, entries in FALLBACK_BY_LANGUAGE.items():
            for tone, text in entries:
                pool.append((lang, tone, text))
        random.shuffle(pool)
        picks = pool[:4]
    else:
        entries = FALLBACK_BY_LANGUAGE.get(language_mode) or FALLBACK_BY_LANGUAGE["english"]
        picks = []
        # Cycle through 4 tones (allowing a repeat if needed)
        for i in range(4):
            tone, text = entries[i % len(entries)]
            picks.append((language_mode, tone, text))

    variants = []
    for idx, (lang, tone, text) in enumerate(picks, start=1):
        if business_name and business_name.lower() not in text.lower() and idx % 2 == 0:
            # Lightly personalise every other variant
            text = f"{text} — {business_name}"
        variants.append({
            "variant_number": idx,
            "language": lang,
            "tone": tone,
            "text": text,
        })
    return variants
