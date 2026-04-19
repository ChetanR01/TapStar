"""
AI review generation — PromptBuilder + Anthropic call.

Takes customer input (rating/categories/items/language) + effective business settings,
produces 4 Google-review variants in different Indian language styles.

Authenticity strategy:
- Inject business-type-specific vocabulary and style hints (reviews/business_types.py)
- Use few-shot examples of genuinely mundane, human-written reviews so the model
  doesn't fall back to corporate-marketing register ("top class", "highly recommend")
- Maintain a hard-coded forbidden-phrase list of over-used clichés
- Tune length/tone to the actual star rating (3-star = measured, 5-star = warm-not-breathless)

Graceful fallback to pre-written variants if the API key is missing or the call fails.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from businesses.models import Business
from settings_mgr.services import EffectiveSettings

from .business_types import prompt_hints_for
from .fallback import build_fallback_variants

logger = logging.getLogger(__name__)


LENGTH_DESCRIPTIONS = {
    "short": "1-2 short sentences",
    "medium": "3-4 sentences — like a quick phone message, not an essay",
    "detailed": "5-7 sentences — still conversational, not a formal review",
}


# Hard-banned phrases. Two categories:
#
# (1) Corporate hype — reviews that read like marketing. Bans force the model
#     to write like a real customer instead of reaching for clichés.
# (2) Complaint / caveat patterns — since this tool exists to help owners get
#     positive reviews, we explicitly forbid "had to wait", "thoda slow", "but
#     the food was good" type constructions, backhanded compliments like "for
#     the area" or "for what it is", and anything that describes service, food,
#     or timing as slow / late / small / delayed.
FORBIDDEN_PHRASES = [
    # --- Corporate hype / clichés ---
    "highly recommend", "highly recommended", "top class", "top-notch", "five star", "5 star",
    "exceptional experience", "world class", "one of the best", "must visit", "must-visit",
    "amazing experience", "fantastic experience", "incredible experience", "outstanding",
    "second to none", "par excellence", "exceeded expectations", "exceeded my expectations",
    "absolutely loved", "loved every moment", "will definitely be back", "will definitely return",
    "can't wait to come back", "cant wait to come back", "hats off", "kudos",
    # Hinglish / Hindi shortcuts
    "ekdum top class", "ekdam top class", "ek dam top class",
    "ekdum jhakaas", "ekdam jhakaas", "ek number", "ek dum mast",
    "mast hai bhai", "bhai kasam", "kasam se", "saala bahut accha",
    # Marathi / Minglish shortcuts
    "ekdam bhari", "ekdum bhari", "kasla bhari", "lay bhari bhai",
    # Generic hype
    "best in town", "best in city", "one-stop shop", "hidden gem",
    "truly amazing", "simply amazing", "unbelievably good", "never disappoints",

    # --- Complaints / caveats / backhanded compliments (new) ---
    # Any form of "there was a wait" or "it was slow/late"
    "had to wait", "little wait", "a bit of a wait", "worth the wait", "long wait",
    "was slow", "a bit slow", "bit slow", "slightly slow", "service was slow",
    "was late", "a bit late", "slightly late", "came late", "delivery was late",
    "thoda late", "thoda slow", "thoda wait", "wait karna pada", "wait karava lagla",
    "थोड़ा late", "थोड़ा slow", "थोड़ा wait", "wait करना पड़ा", "थांबावं लागलं",
    # Portion / size / quantity complaints
    "portion was small", "small portion", "portion small", "not enough",
    "thoda chota", "थोड़ा छोटा", "थोड़ी कम", "थोडं कमी",
    # Price complaints / "for the area" / "for the price" backhanded framings
    "for the area", "for the price", "for what it is", "for what we paid",
    "area ke hisaab se", "price ke hisaab se", "paisa zyada laga",
    "क्षेत्र के अनुसार", "area ke hisaab",
    # Caveat openers — "but ... good"
    "not the best", "not super", "not very", "nothing great", "nothing special",
    "could be better", "could have been better", "room for improvement",
    "kuch special nahi", "kuch khaas nahi", "kuch khas nahi",
    "कुछ खास नहीं", "कुछ special नहीं",
    # Negative framing that sneaks in
    "not too bad", "not bad at all", "not that great",
]


# Few-shot examples keyed by star rating — real reviews sound different at
# each rating, but ALL examples must be cleanly positive. No "but" caveats,
# no mention of waits / delays / small portions / price complaints / "for
# the area" framings. Small imperfections (missing commas, code-switching,
# contractions) are encouraged; negativity is not.
FEW_SHOT_EXAMPLES = {
    5: [
        # English
        "Chicken biryani came hot with a boiled egg on top, raita was enough for two. Family liked it, we're definitely coming back this weekend.",
        # Hinglish (Roman)
        "Paneer butter masala yahan ka regular hai humare ghar mein. Taste har baar consistent hota hai, delivery bhi smooth rehti hai. Recommend karta hu.",
        # Hinglish (Devanagari)
        "हमेशा family के साथ आते हैं, staff अब पहचानता है। कल बेटे का birthday था तो उन्होंने बिना बोले cake cut करवा दिया, nice gesture.",
        # Hindi (Devanagari)
        "सर्विस अच्छी रही, खाना गरम और ताज़ा आया। staff ने पूछ-पूछ के हर चीज़ serve की।",
        # Marathi (Devanagari)
        "आम्ही नेहमी शनिवारी इथे येतो. जेवण चांगलं असतं, चव मस्त. पावभाजी विशेषतः छान लागली.",
    ],
    4: [
        "Good place. Schezwan noodles had the right kick, portion looked right for one person. AC was working, staff was helpful when we asked for a menu change.",
        "Haircut achcha kiya bhaiya ne, style bilkul waisa hi jo maine bola tha. Shop clean hai, mirror bhi achcha lighting hai.",
        "खाना गरम और fresh मिला, taste घर जैसा लगा। delivery boy ने polite तरीके से handover किया और बिल भी सही था।",
        "काम व्यवस्थित झालं. कामगार शांतपणे बोलले, जे सांगितलं ते नीट केलं. परत येऊ असं वाटतं.",
    ],
    3: [
        # 3-star: short, brief, neutral-positive. Not complaining, not gushing.
        "Okay experience. Simple food, done right, nothing fancy. Will visit again when in the area.",
        "Theek raha. Jo order kiya wahi mila, bill bhi normal tha. Staff ne respect se baat ki.",
        "Average experience raha. Service normal thi, staff ne help ki, jo chahiye tha wo mil gaya.",
    ],
}


PROMPT_TEMPLATE = """You are writing Google reviews that sound like a real Indian customer typed them on their phone — not a copywriter.

BUSINESS CONTEXT:
- Name: "{business_name}"
- Type: {business_type}
- Location/branch: {location_name}
{business_vocabulary_section}{business_style_section}
CUSTOMER INPUT:
- Star rating given: {star_rating}/5 ({rating_mood})
- Things they noticed / liked: {categories}
- Specific items or services: {items}
- Language mode requested: {language_mode}
- Tone mode requested: {tone_mode}
- Target review length: {length} ({length_description})

LANGUAGE DEFINITIONS:
- hinglish: Hindi-English mix in Roman script, natural code-switching. "Paneer tikka ka taste kaafi acha tha, staff ne jaldi serve kiya."
- hinglish_devanagari: Same Hindi-English code-switching but written in Devanagari. English words stay in Roman. "Paneer tikka का taste अच्छा था, staff ने जल्दी serve किया।"
- minglish: Marathi-English mix in Roman script. "Jevan chan hota, staff pan helpful hote, parking suddhya chi vyavastha hoti."
- hindi: Pure Hindi in Devanagari script. Conversational, not formal. "खाना अच्छा था। स्टाफ ने ठीक से बात की।"
- marathi: Pure Marathi in Devanagari script. Conversational. "जेवण छान होतं. सेवा पण व्यवस्थित होती."
- english: Natural Indian English — not British/American. Indian sentence rhythm, mild informality.
- random: Distribute across 4 different styles. No two variants in the same language.

TONE DEFINITIONS:
- casual: Feels like a WhatsApp message to a friend. Contractions, missing commas, direct.
- formal: Polite, structured. Used for professional services like doctors, lawyers.
- enthusiastic: Warm and specific — NOT hype. A happy customer, not a marketer.
- random: Vary tone across variants to match each language.

{custom_keywords_instruction}
{blocked_phrases_instruction}
{business_name_instruction}

FORBIDDEN PHRASES — do NOT use any of these in any variant:
{forbidden_block}

HOW REAL REVIEWS SOUND (follow this feel, not the exact words):
{few_shot_block}

CRITICAL RULES:
1. Write like a normal happy customer, not a marketer. Specific and grounded. Boring is fine; fake is not.
2. Name at least one concrete thing — a dish, a staff member's role, a specific product, a visible detail. If the customer gave "Specific items", weave one or two into the reviews naturally.
3. Allow small natural imperfections: missing Oxford commas, a contraction, mid-sentence lowercase "i". These make it feel typed on a phone. Do NOT introduce typos in every variant — 80%+ should be clean.
4. Vary sentence lengths. A review with three equal-length sentences reads like a template.
5. Do not start two variants with the same word or phrase.
6. Match mood to the star rating:
   - 5 stars → warm and specific, not breathless. Reads like a returning customer.
   - 4 stars → positive and relaxed. Still recommending without reservation.
   - 3 stars → brief and neutral-positive. "Okay", "fine", "decent" is the ceiling — never "amazing", never complaining either.
7. KEEP IT POSITIVE — THIS IS THE MOST IMPORTANT RULE.
   - NEVER insert complaints, caveats, or "but..." qualifiers, even to "balance" the review.
   - Do NOT mention: waits, queues, delays, "late", slow service, small portion size, price complaints, hot weather, anything the customer might gripe about.
   - Do NOT use backhanded framings: "for the area", "for the price", "for what it is", "not the best but", "nothing special but", "area ke hisaab se", "paisa vasool" used as a consolation.
   - If you can't say something cleanly positive about some aspect, just don't mention it.
   - Even natural-sounding negative detail is banned here. A real review might say "had to wait 15 mins but it was worth it" — we don't want that. Write as if the wait never happened.
8. Never use the FORBIDDEN PHRASES above. If tempted, pick a plainer, cleaner alternative.

OUTPUT FORMAT — respond with ONLY this JSON, no explanation, no markdown fences:
{{
  "variants": [
    {{"variant_number": 1, "language": "...", "tone": "...", "text": "..."}},
    {{"variant_number": 2, "language": "...", "tone": "...", "text": "..."}},
    {{"variant_number": 3, "language": "...", "tone": "...", "text": "..."}},
    {{"variant_number": 4, "language": "...", "tone": "...", "text": "..."}}
  ]
}}
"""


_RATING_MOOD = {
    1: "frustrated — but this path is filtered out, you'll rarely see it here",
    2: "disappointed — filtered out in most setups",
    3: "mildly positive; measured, honest, NOT effusive",
    4: "happy, small caveat is fine",
    5: "warm and specific, not gushing",
}


@dataclass
class GenerationInput:
    business: Business
    location_name: str
    star_rating: int
    categories: list[str]
    items: list[str]
    language_mode: str
    tone_mode: str


class PromptBuilder:
    def __init__(self, gen_input: GenerationInput, effective: EffectiveSettings):
        self.input = gen_input
        self.settings = effective

    def build(self) -> str:
        custom_keywords_instruction = ""
        if self.settings.custom_keywords:
            kw = ", ".join(f'"{k}"' for k in self.settings.custom_keywords)
            custom_keywords_instruction = (
                f"KEYWORDS TO WEAVE IN (only if they fit naturally, never force): {kw}"
            )

        # Combine the owner's blocked phrases with our global forbidden list
        owner_blocked = list(self.settings.blocked_phrases or [])
        blocked_phrases_instruction = ""
        if owner_blocked:
            bp = ", ".join(f'"{b}"' for b in owner_blocked)
            blocked_phrases_instruction = (
                f"OWNER-SPECIFIC BLOCKED PHRASES (hard ban): {bp}"
            )

        business_name_instruction = ""
        if self.settings.mention_business_name:
            business_name_instruction = (
                f'BUSINESS NAME: Naturally mention "{self.input.business.name}" in at least 2 of the 4 variants. '
                f'Don\'t awkwardly stuff it — if it doesn\'t fit, skip it.'
            )

        length = self.settings.review_length
        length_description = LENGTH_DESCRIPTIONS.get(length, LENGTH_DESCRIPTIONS["medium"])

        vocabulary_hints, style_hints = prompt_hints_for(self.input.business.business_type)
        business_vocabulary_section = (
            f"- Vocabulary typical of this business type: {vocabulary_hints}\n"
            if vocabulary_hints else ""
        )
        business_style_section = (
            f"- How real customers sound here: {style_hints}\n"
            if style_hints else ""
        )

        # Few-shot block — pick examples matching the rating plus one adjacent so
        # the model sees realistic rhythm at this star level.
        examples = list(FEW_SHOT_EXAMPLES.get(self.input.star_rating, FEW_SHOT_EXAMPLES[5]))
        # Add one example from a neighbouring rating so model sees contrast
        neighbour = self.input.star_rating - 1 if self.input.star_rating >= 4 else 5
        if neighbour in FEW_SHOT_EXAMPLES and FEW_SHOT_EXAMPLES[neighbour]:
            examples.append(FEW_SHOT_EXAMPLES[neighbour][0])
        few_shot_block = "\n".join(f'- "{e}"' for e in examples)

        forbidden_block = ", ".join(f'"{p}"' for p in FORBIDDEN_PHRASES)

        return PROMPT_TEMPLATE.format(
            business_type=self.input.business.get_business_type_display(),
            business_name=self.input.business.name,
            location_name=self.input.location_name or "Main",
            star_rating=self.input.star_rating,
            rating_mood=_RATING_MOOD.get(self.input.star_rating, "positive"),
            categories=", ".join(self.input.categories) or "general experience",
            items=", ".join(self.input.items) or "none specified",
            language_mode=self.input.language_mode,
            tone_mode=self.input.tone_mode,
            length=length,
            length_description=length_description,
            business_vocabulary_section=business_vocabulary_section,
            business_style_section=business_style_section,
            custom_keywords_instruction=custom_keywords_instruction,
            blocked_phrases_instruction=blocked_phrases_instruction,
            business_name_instruction=business_name_instruction,
            forbidden_block=forbidden_block,
            few_shot_block=few_shot_block,
        )


def _parse_variants(raw_text: str) -> list[dict]:
    """Extract the variants array from model output. Tolerates leading/trailing whitespace."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) < 1:
        raise ValueError("No variants in response")
    normalised: list[dict] = []
    for i, v in enumerate(variants[:4], start=1):
        normalised.append({
            "variant_number": int(v.get("variant_number") or i),
            "language": str(v.get("language") or "english").strip().lower(),
            "tone": str(v.get("tone") or "casual").strip().lower(),
            "text": str(v.get("text") or "").strip(),
        })
    return normalised


def _has_blocked_phrase(text: str, blocked: list[str]) -> bool:
    lowered = text.lower()
    return any(b.strip().lower() in lowered for b in blocked if b.strip())


def _has_forbidden_cliche(text: str) -> bool:
    """Check against the global FORBIDDEN_PHRASES list."""
    return _has_blocked_phrase(text, FORBIDDEN_PHRASES)


def _call_anthropic(prompt: str) -> str:
    import anthropic  # imported lazily so missing key doesn't break imports

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
        elif hasattr(block, "text"):
            parts.append(block.text)
    return "".join(parts)


def generate_variants(gen_input: GenerationInput, effective: EffectiveSettings) -> tuple[list[dict], bool]:
    """
    Generate 4 review variants.

    Returns (variants, used_fallback). If the API fails, returns pre-written fallback
    variants and used_fallback=True so the caller can log/surface it if needed.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — serving fallback variants")
        return build_fallback_variants(gen_input.language_mode, gen_input.business.name), True

    prompt = PromptBuilder(gen_input, effective).build()
    owner_blocked = list(effective.blocked_phrases or [])

    try:
        raw = _call_anthropic(prompt)
        variants = _parse_variants(raw)

        # Two-gate clean-up: owner-blocked + our global forbidden list
        needs_retry = any(
            _has_blocked_phrase(v["text"], owner_blocked) or _has_forbidden_cliche(v["text"])
            for v in variants
        )
        if needs_retry:
            logger.info("Blocked/forbidden phrase detected — regenerating once")
            retry_prompt = prompt + (
                "\n\nREMINDER: Your previous draft used a forbidden or owner-blocked phrase. "
                "Regenerate with zero usage of those phrases. Use plainer, more human alternatives."
            )
            raw = _call_anthropic(retry_prompt)
            variants = _parse_variants(raw)
            clean = [
                v for v in variants
                if not _has_blocked_phrase(v["text"], owner_blocked)
                and not _has_forbidden_cliche(v["text"])
            ]
            if len(clean) < 4:
                pads = build_fallback_variants(gen_input.language_mode, gen_input.business.name)
                for p in pads:
                    if len(clean) >= 4:
                        break
                    if (not _has_blocked_phrase(p["text"], owner_blocked)
                            and not _has_forbidden_cliche(p["text"])):
                        clean.append(p)
            variants = clean[:4]

        while len(variants) < 4:
            pads = build_fallback_variants(gen_input.language_mode, gen_input.business.name)
            variants.append(pads[len(variants) % 4])

        for i, v in enumerate(variants, start=1):
            v["variant_number"] = i

        return variants, False

    except Exception as exc:
        logger.exception("AI generation failed, using fallback: %s", exc)
        return build_fallback_variants(gen_input.language_mode, gen_input.business.name), True
