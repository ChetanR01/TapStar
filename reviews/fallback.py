"""Pre-written fallback variants used when the Anthropic API is unavailable.

Constraints — these are the same rules the AI prompt enforces:

- Strictly POSITIVE. No "but", no caveats, no waits/delays/price complaints.
- Strictly TRUTHFUL. No fabricated specifics: no day-of-week claims, no
  "visited on Saturday", no invented staff names, no invented dishes /
  products / services / treatments. Every sentence must be defensible
  for any business type.
- Strictly BUSINESS-AGNOSTIC. The same line should make sense for a gym,
  a salon, a clinic, a hardware store, or a restaurant. No "khaana",
  "menu", "order", "serve", "jevan" — pick neutral words like "what we
  received", "the place", "staff", "experience".

Structure: each (language, tone) pair is a list of sentences ordered so
the first N read well on their own. ``build_fallback_variants`` picks N
based on the owner's review_length setting.
"""

import random


LENGTH_SENTENCE_COUNT = {
    "short": 1,
    "medium": 3,
    "detailed": 6,
}


# Each entry is (tone, [sentence, sentence, ...]). Every sentence reads well
# on its own so truncating to N is fine. Sentences avoid: weekday/date/time,
# menu/food/order/serve, fabricated names, "but" caveats, complaints.
FALLBACK_BY_LANGUAGE: dict[str, list[tuple[str, list[str]]]] = {
    "english": [
        ("casual", [
            "Had a good experience here.",
            "Staff was helpful and answered our questions properly.",
            "The place was clean and well kept.",
            "What we got was exactly what we were looking for.",
            "Pricing felt fair for what is offered.",
            "Will be back again.",
        ]),
        ("enthusiastic", [
            "Really liked this place.",
            "Staff was friendly and easy to talk to.",
            "Everything was handled smoothly from start to finish.",
            "The place felt well looked after and comfortable.",
            "Quality of what we received was consistent.",
            "Already planning to visit again.",
        ]),
        ("formal", [
            "A good experience overall.",
            "Staff were attentive and professional throughout.",
            "Quality of the work was consistent with expectations.",
            "The place was well maintained and easy to navigate.",
            "Billing was straightforward and quick.",
            "Would happily recommend to friends.",
        ]),
    ],
    "hinglish": [
        ("casual", [
            "Achha experience raha yahan.",
            "Staff helpful tha aur sab kuch properly samjha diya.",
            "Jagah clean thi aur properly maintained lagi.",
            "Jo chahiye tha exactly wahi mila.",
            "Rate bhi reasonable lagaa.",
            "Wapas zaroor aayenge.",
        ]),
        ("enthusiastic", [
            "Yahan ka experience kaafi accha raha.",
            "Staff polite hai aur properly attend karte hain.",
            "Quality consistent rehti hai har baar.",
            "Jagah achchi tarah maintained hai.",
            "Jo expect kiya tha wo bhi mila.",
            "Aage bhi aana banta hai.",
        ]),
        ("formal", [
            "Kaafi accha anubhav raha.",
            "Staff ne patience ke saath help ki aur professional tha.",
            "Quality expectation ke according thi.",
            "Jagah saaf-suthri aur achhi tarah maintained thi.",
            "Billing transparent thi aur quickly handle ki gayi.",
            "Dosto ko bhi recommend karunga.",
        ]),
    ],
    "hinglish_devanagari": [
        ("casual", [
            "अच्छा experience रहा यहाँ।",
            "Staff helpful था और सब कुछ properly समझा दिया।",
            "जगह clean थी और maintained लगी।",
            "जो चाहिए था exactly वही मिला।",
            "Rate भी reasonable लगा।",
            "वापस ज़रूर आएंगे।",
        ]),
        ("enthusiastic", [
            "यहाँ का experience अच्छा रहा।",
            "Staff polite है और properly attend करते हैं।",
            "Quality हर बार consistent रहती है।",
            "जगह properly maintained है।",
            "जो expect किया था वो भी मिला।",
            "आगे भी आना बनता है।",
        ]),
        ("formal", [
            "अनुभव अच्छा रहा।",
            "Staff ने patience के साथ help की।",
            "Quality expectation के according थी।",
            "जगह साफ-सुथरी और maintained थी।",
            "Billing भी transparent और जल्दी हो गई।",
            "दोस्तों को भी recommend करूँगा।",
        ]),
    ],
    "minglish": [
        ("casual", [
            "Anubhav changla hota.",
            "Staff helpful hota ani sagle nit samjawla.",
            "Jagah swachchha aani vyavasthit hoti.",
            "Je havya hote te nit milala.",
            "Kimmat pan baryapaiki vatli.",
            "Parat yeu asa vatto.",
        ]),
        ("enthusiastic", [
            "Yethla anubhav khup chaan hota.",
            "Staff polite aahe ani nit attend kartat.",
            "Quality consistent aste prati vela.",
            "Jagah vyavasthit maintained aahe.",
            "Je expect kele te pan milala.",
            "Pudhe pan yeil mhante.",
        ]),
        ("formal", [
            "Anubhav samadhanakarak hota.",
            "Staff vyavasthit hota aani vinamra hota.",
            "Quality apekshepramane hoti.",
            "Jagah swachchha aani nitanitki hoti.",
            "Bill paardarshak aani lavkar zhala.",
            "Mitranna pan recommend karen.",
        ]),
    ],
    "hindi": [
        ("casual", [
            "अनुभव अच्छा रहा।",
            "स्टाफ helpful था और हर बात ठीक से समझा दी।",
            "जगह साफ-सुथरी थी और व्यवस्थित लगी।",
            "जो चाहिए था वही exactly मिला।",
            "रेट भी सही लगा।",
            "अगली बार ज़रूर आएंगे।",
        ]),
        ("enthusiastic", [
            "यहाँ का अनुभव बहुत अच्छा रहा।",
            "स्टाफ polite है और जल्दी मदद करता है।",
            "Quality में consistency दिखती है।",
            "जगह की देखभाल अच्छे से की गई है।",
            "जो उम्मीद थी वही मिला।",
            "आगे फिर आना बनता है।",
        ]),
        ("formal", [
            "संतोषजनक अनुभव रहा।",
            "व्यवस्था ठीक थी और staff का व्यवहार सभ्य था।",
            "Quality अपेक्षा के अनुरूप थी।",
            "जगह comfortable और साफ थी।",
            "मूल्य उचित लगा और बिलिंग पारदर्शी थी।",
            "मित्रों को भी इसकी सलाह दूँगा।",
        ]),
    ],
    "marathi": [
        ("casual", [
            "अनुभव छान होता.",
            "स्टाफ मदतीला तत्पर होता आणि नीट समजावलं.",
            "जागा स्वच्छ आणि व्यवस्थित होती.",
            "जे हवं होतं तेच नीट मिळालं.",
            "किंमत पण योग्य वाटली.",
            "परत नक्की येऊ.",
        ]),
        ("enthusiastic", [
            "इथला अनुभव खूप छान होता.",
            "स्टाफ नम्र आहे आणि नीट लक्ष देतात.",
            "Quality प्रत्येक वेळी सारखी असते.",
            "जागेची निगा नीट राखली आहे.",
            "जे अपेक्षित होतं तेच मिळालं.",
            "पुढेही नक्की येणार.",
        ]),
        ("formal", [
            "अनुभव समाधानकारक होता.",
            "कर्मचारी व्यवस्थित आणि सभ्य होते.",
            "Quality अपेक्षेप्रमाणे होती.",
            "जागा स्वच्छ आणि नीट होती.",
            "बिलिंग पारदर्शक आणि लवकर झालं.",
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
