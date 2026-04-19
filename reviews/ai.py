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
    "medium": "2-3 sentences — like a quick phone message, not an essay",
    "detailed": "3-5 sentences — still conversational, not a formal review",
}


# Hard-banned phrases. The model reaches for these by default and they make
# reviews sound fake. The list is intentionally long so the model is forced
# to find natural alternatives instead of its usual shortcuts.
FORBIDDEN_PHRASES = [
    # English clichés
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
]


# Few-shot examples keyed by star rating — real reviews sound different at
# each rating. Include gentle imperfections: run-on sentences, missing
# punctuation, specific sensory detail, anticlimactic endings.
FEW_SHOT_EXAMPLES = {
    5: [
        # English
        "Ordered the chicken biryani and it came hot with a boiled egg on top. Raita was plenty. Took 20 mins so not super fast but the food was worth it. Will come again for sure.",
        # Hinglish (Roman)
        "Bhai paneer butter masala hum log regularly order karte hain yahan se, taste consistent hai har baar. Delivery bhi usually on time. Thoda spicy hota hai but that's how we like it.",
        # Hinglish (Devanagari)
        "हमेशा family के साथ आते हैं, staff अब पहचानता है। कल बेटे का birthday था तो उन्होंने बिना बोले cake cut करवा दिया। small gesture but nice.",
        # Hindi (Devanagari)
        "सर्विस अच्छी थी, खाना भी गरम आया। थाली में दाल थोड़ी कम थी लेकिन बोलने पर तुरंत और दे दी।",
        # Marathi (Devanagari)
        "आम्ही नेहमी शनिवारी इथे येतो. जेवण वेळेवर मिळतं, चव पण बरी आहे. पावभाजी विशेषतः छान असते.",
    ],
    4: [
        "Good place overall. We ordered the schezwan noodles and it was decent, not too oily. Staff was polite but we had to wait around 15 mins. AC was on which was a plus in this heat.",
        "Haircut mila thik thaak, pehle wale ne 200 charge kiye the yahan 150 me ho gaya. Waiting thoda tha Saturday tha isliye. Shop clean hai.",
        "Delivery 10 मिनट late थी but खाना ठीक था. Portion थोड़ा छोटा लगा for the price लेकिन taste अच्छा था.",
        "ठीक ठाक अनुभव होता. कामगारांनी कुठलीही घाई केली नाही. किंमत थोडी जास्त वाटली पण काम व्यवस्थित झालं.",
    ],
    3: [
        "Food was okay. Dosa was a bit soggy but the chutney was good. Service was slow on a weekday evening, not sure why. Would come back but maybe try something else.",
        "Accha hai but kuch special nahi laga. Bill normal tha, paisa vasool. Staff ne bola baith jao, fir 10 min baad menu aaya.",
        "Average. Hair wash kiya aur cut karwaya, fine lag raha hai. Price zyada hi lagaya but area ke according thik hai.",
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
- hinglish: Hindi-English mix in Roman script, natural code-switching. "Paneer tikka ka taste kaafi acha tha, but service thodi slow thi."
- hinglish_devanagari: Same Hindi-English code-switching but written in Devanagari. English words stay in Roman. "Paneer tikka का taste ठीक था, service थोड़ी slow थी."
- minglish: Marathi-English mix in Roman script. "Jevan chan hota, staff pan helpful hote but parking problem ahe."
- hindi: Pure Hindi in Devanagari script. Conversational, not formal. "खाना अच्छा था। स्टाफ ने ठीक से बात की।"
- marathi: Pure Marathi in Devanagari script. Conversational. "जेवण बरं होतं. सेवा पण व्यवस्थित होती."
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
1. Write like a normal customer, not a marketer. Boring is good. Specific is better.
2. Name at least one concrete thing — a dish, a staff member's role, a specific product, a visible detail. If the customer gave "Specific items", weave one or two into the reviews naturally.
3. Allow small natural imperfections: missing Oxford commas, a slightly run-on sentence, mid-sentence lowercase "i", a typo like "recieved" is fine in 1 of 4 variants only. Do NOT overdo this — 80% clean, 20% rough.
4. Vary sentence lengths. A review with 3 equal-length sentences reads like a template.
5. Do not start two variants with the same word or phrase.
6. Match the mood to the star rating — a 3-star review should NOT say "amazing". A 5-star should be warm and specific, not breathless.
7. If rating is 4/5, it's fine to mention one small complaint or neutral observation — real humans do this.
8. Never use the FORBIDDEN PHRASES above. If tempted, pick a plainer alternative.

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
