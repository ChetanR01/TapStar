"""Pre-written fallback variants used when the Anthropic API is unavailable.

Structure: each (language, tone) pair is a list of sentences ordered so the
first N read well on their own. `build_fallback_variants` picks a different
N depending on the owner's ``review_length`` setting:

  short    → 1 sentence
  medium   → 3 sentences
  detailed → 5-6 sentences (whatever is available)

Every sentence must be cleanly positive — no "but" caveats, no mention of
waits/delays/price complaints/backhanded framings. That's the whole point.
"""

import random


# Target sentence counts per length setting. "detailed" takes whatever is
# available (we wrote 5-6 sentences for each entry) up to this cap.
LENGTH_SENTENCE_COUNT = {
    "short": 1,
    "medium": 3,
    "detailed": 6,
}


# Each entry is (tone, [sentence, sentence, ...]). Every sentence reads well
# on its own so truncating to N is fine.
FALLBACK_BY_LANGUAGE: dict[str, list[tuple[str, list[str]]]] = {
    "english": [
        ("casual", [
            "Went here on a Saturday and enjoyed our visit.",
            "The food came hot and fresh, exactly how we ordered it.",
            "Staff answered our questions without rushing us at any point.",
            "The place was clean and well-lit, nice seating for a family.",
            "Pricing felt fair and billing was quick.",
            "Will be back soon for sure.",
        ]),
        ("enthusiastic", [
            "Really liked this place.",
            "Ordered two items and both came nicely plated.",
            "Staff was friendly and chatty in a good way.",
            "The ambience was warm and we didn't feel rushed.",
            "Quality of what we received felt consistent with the price.",
            "Already planning our next visit with the family.",
        ]),
        ("formal", [
            "A very good experience overall.",
            "The staff were attentive and professional throughout.",
            "Quality of what we received matched exactly what we hoped for.",
            "Seating arrangement was comfortable and the place was well maintained.",
            "Billing was transparent and handled quickly.",
            "Would happily recommend to friends and family.",
        ]),
    ],
    "hinglish": [
        ("casual", [
            "Taste accha tha, staff ne jaldi serve kiya.",
            "Bhaiya ne menu recommend kiya aur wahi sahi tha.",
            "Jagah clean thi aur seating bhi comfortable lagi.",
            "Price bhi reasonable lagaa, paisa vasool.",
            "Order exactly waisa hi mila jaisa bola tha.",
            "Agli baar family ko bhi le aayenge.",
        ]),
        ("enthusiastic", [
            "Yahan regular customer hai hum.",
            "Quality har baar consistent rehti hai.",
            "Staff ka behaviour polite hai, baat achche se karte hain.",
            "Jo bhi order kiya wo fresh aur garam mila.",
            "Place bhi theek thaak maintained hai.",
            "Sach me bahut mazaa aaya, zaroor wapas aayenge.",
        ]),
        ("formal", [
            "Kaafi accha anubhav raha.",
            "Staff ne patience ke saath help ki aur professional tha.",
            "Jo order kiya wahi exactly mila, quality bhi uchchit thi.",
            "Seating comfortable thi aur jagah saaf suthri thi.",
            "Billing bhi turant aur transparent thi.",
            "Aage bhi aayenge, dosto ko bhi bolenge.",
        ]),
    ],
    "hinglish_devanagari": [
        ("casual", [
            "Taste अच्छा था, staff ने जल्दी serve किया।",
            "Menu recommendation भी helpful थी।",
            "जगह clean थी और seating भी comfortable लगी।",
            "Price reasonable लगा, value for money।",
            "Order exactly वैसा ही मिला जैसा बोला था।",
            "अगली बार family को भी ले आएंगे।",
        ]),
        ("enthusiastic", [
            "हम regular आते हैं यहाँ।",
            "Quality हमेशा consistent रहती है।",
            "Staff का behaviour polite है, बात अच्छे से करते हैं।",
            "जो भी order किया वो fresh और गरम मिला।",
            "Place भी properly maintained है।",
            "सच में अच्छा लगा, ज़रूर वापस आएंगे।",
        ]),
        ("formal", [
            "अनुभव अच्छा रहा।",
            "Staff ने patience के साथ help की।",
            "जो order किया वो exactly मिला और quality बढ़िया थी।",
            "Seating comfortable थी और जगह साफ-सुथरी थी।",
            "Billing भी transparent और जल्दी हो गया।",
            "आगे भी आएंगे, दोस्तों को भी recommend करेंगे।",
        ]),
    ],
    "minglish": [
        ("casual", [
            "Jevan chan hota.",
            "Staff ne sangitla te nit kela, kuthali ghai keli nahi.",
            "Jagah swachchha hoti ani seating pan comfortable.",
            "Chava mast hota ani velevar serve jhala.",
            "Kimmat pan baryapaiki, vasta ka layak.",
            "Parat yeu asa vatte aahe.",
        ]),
        ("enthusiastic", [
            "Aamhi regular customer aahot yacha.",
            "Quality consistent aste neeam sari.",
            "Staff pan changla aahe, bolayala mast.",
            "Jevan fresh ani garam milat asla.",
            "Ambience suddhya suddhya aani familyfriendly.",
            "Nakki parat yenar, aaptyanna pan sangen.",
        ]),
        ("formal", [
            "Anubhav baryapaiki hota.",
            "Staff vyavasthit hota aani vinamra hota.",
            "Jo order kela to velevar aani exactly milala.",
            "Jagah swachchha aani upchaarik hoti.",
            "Bill pan paardarshak aani jaldi zhala.",
            "Aaplya mitranna pan recommend karen.",
        ]),
    ],
    "hindi": [
        ("casual", [
            "शनिवार को गए थे, माहौल अच्छा लगा।",
            "खाना गरम और fresh मिला।",
            "स्टाफ ने बढ़िया तरीके से serve किया।",
            "जगह साफ-सुथरी थी और बैठने की जगह भी ठीक थी।",
            "रेट भी सही लगा, पैसा वसूल।",
            "अगली बार परिवार को भी लाएंगे।",
        ]),
        ("enthusiastic", [
            "बहुत अच्छी जगह है, हम अक्सर यहाँ आते हैं।",
            "Quality में कभी कमी नहीं आती।",
            "स्टाफ भी polite है और जल्दी मदद करता है।",
            "हर बार fresh और गरम खाना मिलता है।",
            "जगह की सजावट भी मन को भाती है।",
            "ज़रूर फिर आएंगे और दोस्तों को भी बताएंगे।",
        ]),
        ("formal", [
            "संतोषजनक अनुभव रहा।",
            "व्यवस्था ठीक थी और staff का व्यवहार सभ्य था।",
            "जो order किया वही exactly मिला।",
            "बैठने की जगह comfortable और जगह साफ थी।",
            "मूल्य भी उचित लगा और बिलिंग पारदर्शी थी।",
            "मैं अपने मित्रों को भी इसकी सलाह दूंगा।",
        ]),
    ],
    "marathi": [
        ("casual", [
            "शनिवारी गेलो होतो, वातावरण छान होतं.",
            "जेवण गरम आणि ताजं होतं.",
            "स्टाफ पण बोलायला चांगला होता.",
            "जागा स्वच्छ होती आणि बसण्याची सोय पण बरी होती.",
            "किंमत पण योग्य वाटली.",
            "परत नक्की येऊ, कुटुंबाला पण घेऊन येऊ.",
        ]),
        ("enthusiastic", [
            "आम्ही नेहमी येतो इथे.",
            "चव नेहमी सारखी असते.",
            "स्टाफ पण व्यवस्थित आणि मदतीला तत्पर आहे.",
            "जेवण ताजं आणि गरम असतं प्रत्येक वेळी.",
            "जागेची साज-सजावट पण आवडली.",
            "नक्की परत येणार, मित्रांना पण सांगणार.",
        ]),
        ("formal", [
            "अनुभव समाधानकारक होता.",
            "कर्मचारी व्यवस्थित आणि सभ्य होते.",
            "जे मागवलं ते वेळेत मिळालं.",
            "जागा स्वच्छ आणि बसण्याची सोय आरामदायी होती.",
            "किंमत योग्य वाटली आणि बिलिंग पारदर्शक होतं.",
            "मित्रांना पण शिफारस करेन.",
        ]),
    ],
}


def _pick_sentences(sentences: list[str], length: str) -> str:
    """Take the first N sentences for the requested length."""
    n = LENGTH_SENTENCE_COUNT.get(length, LENGTH_SENTENCE_COUNT["medium"])
    n = max(1, min(n, len(sentences)))
    return " ".join(sentences[:n])


def build_fallback_variants(
    language_mode: str,
    business_name: str | None = None,
    length: str = "medium",
) -> list[dict]:
    """Return 4 variants using pre-written text, at the requested length."""
    if language_mode == "random":
        pool = []
        for lang, entries in FALLBACK_BY_LANGUAGE.items():
            for tone, sentences in entries:
                pool.append((lang, tone, sentences))
        random.shuffle(pool)
        picks = pool[:4]
    else:
        entries = FALLBACK_BY_LANGUAGE.get(language_mode) or FALLBACK_BY_LANGUAGE["english"]
        picks = []
        for i in range(4):
            tone, sentences = entries[i % len(entries)]
            picks.append((language_mode, tone, sentences))

    variants = []
    for idx, (lang, tone, sentences) in enumerate(picks, start=1):
        text = _pick_sentences(sentences, length)
        if business_name and business_name.lower() not in text.lower() and idx % 2 == 0:
            text = f"{text} — {business_name}"
        variants.append({
            "variant_number": idx,
            "language": lang,
            "tone": tone,
            "text": text,
        })
    return variants
