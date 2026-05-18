"""
AI review generation — PromptBuilder + Anthropic call with prompt caching.

Two-part prompt structure for cache efficiency:

- SYSTEM (cached, ephemeral): persona, language/tone definitions, critical
  rules, the OUTPUT FORMAT spec, a short curated steering list of bad
  phrases, and few-shot examples. This is identical for every Tapstar
  request, so the cache hits on every call inside the 5-min TTL.
- USER (dynamic): business context, allowed topics, the customer's input,
  variant count, length constraint, owner-specific blocked phrases.

The full FORBIDDEN_PHRASES list is enforced post-hoc by a regex check
(``_has_forbidden_cliche``). Sending all 100+ to the model on every call
was duplicate work, so the prompt keeps only the worst offenders inline
for steering.

Graceful fallback to pre-written variants if the API key is missing or
the call fails.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from businesses.models import Business
from settings_mgr.services import EffectiveSettings

from .business_types import prompt_hints_for
from .fallback import build_fallback_variants

logger = logging.getLogger(__name__)


# How many variants we generate per API call. The frontend lets the
# customer retry up to MAX_RETRIES times to top up; each retry is a
# separate API call returning the same count.
DEFAULT_VARIANT_COUNT = 2
MAX_VARIANT_COUNT = 4
MAX_RETRIES = 2  # so total possible API calls per session = 1 + 2 = 3


LENGTH_DESCRIPTIONS = {
    "short": "1-2 short sentences",
    "medium": "3-4 sentences — like a quick phone message, not an essay",
    "detailed": "5-7 sentences — still conversational, not a formal review",
}

LENGTH_HARD_CONSTRAINT = {
    "short":    "HARD LENGTH RULE: every variant MUST be exactly 1 or 2 sentences.",
    "medium":   "HARD LENGTH RULE: every variant MUST be exactly 3 or 4 sentences.",
    "detailed": "HARD LENGTH RULE: every variant MUST be exactly 5, 6, or 7 sentences. Count before finalising.",
}


# Curated steering list — the worst clichés we want the model actively
# steering AWAY from. The full ban list is enforced post-hoc in code.
STEERING_BAD_PHRASES = [
    "highly recommend", "top class", "top-notch", "must visit", "hidden gem",
    "exceeded expectations", "world class", "amazing experience", "fantastic experience",
    "ekdum top class", "ekdam jhakaas", "ek number", "mast hai bhai",
    "had to wait", "worth the wait", "for the area", "for the price",
    "not the best", "could be better", "kuch khaas nahi",
]


# Full forbidden list — checked AFTER generation, not sent to the model.
# Keeping it server-side is ~600 tokens cheaper per call.
FORBIDDEN_PHRASES = [
    # --- Corporate hype / clichés ---
    "highly recommend", "highly recommended", "top class", "top-notch", "five star", "5 star",
    "exceptional experience", "world class", "one of the best", "must visit", "must-visit",
    "amazing experience", "fantastic experience", "incredible experience", "outstanding",
    "second to none", "par excellence", "exceeded expectations", "exceeded my expectations",
    "absolutely loved", "loved every moment", "will definitely be back", "will definitely return",
    "can't wait to come back", "cant wait to come back", "hats off", "kudos",
    "ekdum top class", "ekdam top class", "ek dam top class",
    "ekdum jhakaas", "ekdam jhakaas", "ek number", "ek dum mast",
    "mast hai bhai", "bhai kasam", "kasam se", "saala bahut accha",
    "ekdam bhari", "ekdum bhari", "kasla bhari", "lay bhari bhai",
    "best in town", "best in city", "one-stop shop", "hidden gem",
    "truly amazing", "simply amazing", "unbelievably good", "never disappoints",
    # --- Complaints / caveats ---
    "had to wait", "little wait", "a bit of a wait", "worth the wait", "long wait",
    "was slow", "a bit slow", "bit slow", "slightly slow", "service was slow",
    "was late", "a bit late", "slightly late", "came late", "delivery was late",
    "thoda late", "thoda slow", "thoda wait", "wait karna pada", "wait karava lagla",
    "थोड़ा late", "थोड़ा slow", "थोड़ा wait", "wait करना पड़ा", "थांबावं लागलं",
    "portion was small", "small portion", "portion small", "not enough",
    "thoda chota", "थोड़ा छोटा", "थोड़ी कम", "थोडं कमी",
    "for the area", "for the price", "for what it is", "for what we paid",
    "area ke hisaab se", "price ke hisaab se", "paisa zyada laga",
    "क्षेत्र के अनुसार", "area ke hisaab",
    "not the best", "not super", "not very", "nothing great", "nothing special",
    "could be better", "could have been better", "room for improvement",
    "kuch special nahi", "kuch khaas nahi", "kuch khas nahi",
    "कुछ खास नहीं", "कुछ special नहीं",
    "not too bad", "not bad at all", "not that great",
]


# Few-shot examples. Keep these small but high-signal — they go in the
# cached system prompt, so paying for them once is cheap.
#
# CRITICAL constraints on these examples:
# 1. Strictly POSITIVE — no caveats, no waits, no complaints.
# 2. Strictly TRUTHFUL — no invented weekdays, dates, names, dishes.
# 3. Strictly BUSINESS-AGNOSTIC — work for gym, clinic, retail, restaurant.
#
# Marathi examples have been rewritten by a native speaker — no Hindi-isms
# like "जगह" (use "जागा"), no awkward "तेच नीट" doublings, proper
# Marathi verb conjugation ("होतं/आहे" not Hindi "था/है").
FEW_SHOT_EXAMPLES = {
    5: [
        "Genuinely happy with the visit. Staff was attentive and walked us through everything, place was well kept and the experience felt smooth end to end.",
        "Yahan ka experience kaafi achha raha. Staff polite tha, properly attend kiya, jo expect kiya tha wo bhi mila.",
        "Staff ने अच्छे से help की, properly समझाया भी। जगह clean थी और overall experience smooth रहा।",
        "अनुभव बढ़िया रहा। staff ने ध्यान से काम किया, जगह व्यवस्थित थी और जो चाहिए था वही मिला।",
        "इथला अनुभव खूप छान होता. कर्मचाऱ्यांनी नीट लक्ष दिलं आणि जे हवं होतं ते व्यवस्थित मिळालं. जागा स्वच्छ आणि नीटनेटकी होती.",
        "Ithla anubhav khup chhan hota. Staff nit bolla ani sagla vyavasthit zhala. Jaaga svachh ani nit-netaki hoti.",
    ],
    4: [
        "Solid experience. Staff was polite and the place was easy to deal with, what we got matched what we expected.",
        "Theek thaak experience tha. Staff helpful tha, baat properly samjhayi, jagah bhi properly maintained thi.",
        "अच्छा रहा। staff helpful था, properly attend किया और जो चाहिए था वही मिला।",
        "अनुभव चांगला होता. कर्मचारी शांतपणे बोलले आणि जे हवं होतं तेच मिळालं.",
    ],
    3: [
        "Okay experience. Did the job, staff was respectful, no complaints.",
        "Theek raha. Jo chahiye tha wahi mila, staff ne respect se baat ki.",
        "बरं होतं. कामाचं काम झालं, कर्मचारी नीट बोलले.",
    ],
}


# ---------------------------------------------------------------------------
# STATIC SYSTEM PROMPT — cached. Identical for every Tapstar request.
# ---------------------------------------------------------------------------
def _build_few_shot_block() -> str:
    blocks = []
    for rating in sorted(FEW_SHOT_EXAMPLES.keys(), reverse=True):
        examples = FEW_SHOT_EXAMPLES[rating]
        blocks.append(f"{rating}-star feel:")
        for e in examples:
            blocks.append(f'- "{e}"')
    return "\n".join(blocks)


SYSTEM_PROMPT = f"""You are writing Google reviews that sound like a real Indian customer typed them on their phone — not a copywriter.

LANGUAGE DEFINITIONS:
- hinglish: Hindi-English mix in Roman script, natural code-switching. "Paneer tikka ka taste kaafi acha tha, staff ne jaldi serve kiya."
- hinglish_devanagari: Same Hindi-English code-switching but written in Devanagari. English words stay in Roman. "Paneer tikka का taste अच्छा था, staff ने जल्दी serve किया।"
- minglish: Marathi-English mix in Roman script. Use Marathi words like "jaaga" (NOT Hindi "jagah"), "chhan/chaan", "ahe/aahe", "barobar", "nit/neet". "Jevan chhan hota, staff pan helpful hote, jaaga pan vyavasthit hoti."
- hindi: Pure Hindi in Devanagari. Conversational, not formal. "खाना अच्छा था। स्टाफ ने ठीक से बात की।"
- marathi: Pure Marathi in Devanagari. Conversational. CRITICAL: this is MARATHI, not Hindi.
  - Use Marathi words: "जागा" (not Hindi "जगह"), "आहे/होतं/होती" (not Hindi "है/था/थी"), "माझं/आमचं" (not Hindi "मेरा/हमारा"), "कर्मचारी" or "स्टाफ", "नीट/व्यवस्थित", "छान/चांगलं/बरं".
  - Marathi sentences end with "." (period), NOT "।" (Hindi danda).
  - Avoid awkward doublings like "तेच नीट मिळालं" — write "तेच मिळालं" or "नीट मिळालं", not both.
  - Examples: "जेवण छान होतं. सेवा पण व्यवस्थित होती." / "इथला अनुभव खूप छान होता. कर्मचारी नीट लक्ष देत होते."
- english: Natural Indian English — not British/American. Indian sentence rhythm, mild informality.
- random: Distribute across different styles. No two variants in the same language.

TONE DEFINITIONS:
- casual: Feels like a WhatsApp message. Contractions, missing commas, direct.
- formal: Polite, structured. Used for professional services like doctors, lawyers.
- enthusiastic: Warm and specific — NOT hype. A happy customer, not a marketer.
- random: Vary tone across variants to match each language.

STEERING — phrases to actively AVOID (the server enforces a longer ban list):
{", ".join(f'"{p}"' for p in STEERING_BAD_PHRASES)}

HOW REAL REVIEWS SOUND (follow this feel, not the exact words):
{_build_few_shot_block()}

CRITICAL RULES:
1. Write like a normal happy customer, not a marketer. Specific and grounded. Boring is fine; fake is not.
2. STAY INSIDE THE ALLOWED TOPICS that the user message provides. NEVER mention a topic outside that list. If in doubt, leave it out.
3. DO NOT FABRICATE FACTS — the customer must not feel the review is made up.
   - Do NOT invent days, dates, times, weather, seasons, festivals, or visit history.
   - Do NOT invent staff names, owner names, family members, distances, trip purposes, or monetary figures.
   - Do NOT invent menu items, dishes, services, products, brands, or treatments. ONLY mention items the user message lists under "Specific items / services". If that list is empty, do NOT name any specific item.
   - Do NOT invent quantities, companions, or events unless given.
4. Allow small natural imperfections: missing Oxford commas, a contraction, mid-sentence lowercase "i". Don't introduce typos in every variant — 80%+ should be clean.
5. Vary sentence lengths. Don't start two variants with the same word.
6. Match mood to the star rating: 5★ warm and specific, 4★ positive and relaxed, 3★ brief and neutral-positive ("okay", "fine", "decent" is the ceiling — never "amazing", never complaining).
7. KEEP IT POSITIVE. NEVER insert complaints, caveats, or "but..." qualifiers. Do NOT mention waits, queues, delays, slow service, small portions, price complaints. Do NOT use backhanded framings ("for the area", "for the price", "not the best but"). If you can't say something cleanly positive about an aspect, just don't mention it.
8. The language used in each variant MUST match the requested language mode exactly. For pure marathi/hindi, the entire review is in that script — only English brand names or "Quality" / "Staff" type words may stay in Roman.

OUTPUT FORMAT — respond with ONLY this JSON, no explanation, no markdown fences:
{{"variants": [{{"variant_number": 1, "language": "...", "tone": "...", "text": "..."}}, ...]}}
The number of objects in "variants" must equal the count the user message requests.
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
    enabled_category_labels: list[str] = field(default_factory=list)
    focus_categories: list[str] = field(default_factory=list)
    variant_count: int = DEFAULT_VARIANT_COUNT


class PromptBuilder:
    """Builds the per-request USER message. The SYSTEM prompt is static."""

    def __init__(self, gen_input: GenerationInput, effective: EffectiveSettings):
        self.input = gen_input
        self.settings = effective

    def build_user_message(self) -> str:
        n = max(1, min(int(self.input.variant_count or DEFAULT_VARIANT_COUNT), MAX_VARIANT_COUNT))

        vocabulary_hints, style_hints = prompt_hints_for(self.input.business.business_type)
        vocab_line = f"- Vocabulary typical of this business type: {vocabulary_hints}\n" if vocabulary_hints else ""
        style_line = f"- How real customers sound here: {style_hints}\n" if style_hints else ""

        length = self.settings.review_length
        length_desc = LENGTH_DESCRIPTIONS.get(length, LENGTH_DESCRIPTIONS["medium"])
        length_rule = LENGTH_HARD_CONSTRAINT.get(length, LENGTH_HARD_CONSTRAINT["medium"])

        enabled_labels = self.input.enabled_category_labels or ["general experience"]
        enabled_block = "\n".join(f"- {label}" for label in enabled_labels)

        focus = self.input.focus_categories or self.input.categories
        focus_value = ", ".join(focus) if focus else "(none — pick ONE topic from ALLOWED TOPICS at random and anchor every variant on it)"

        custom_kw_line = ""
        if self.settings.custom_keywords:
            kw = ", ".join(f'"{k}"' for k in self.settings.custom_keywords)
            custom_kw_line = f"KEYWORDS TO WEAVE IN (only if they fit naturally, never force): {kw}\n"

        owner_blocked = list(self.settings.blocked_phrases or [])
        owner_block_line = ""
        if owner_blocked:
            bp = ", ".join(f'"{b}"' for b in owner_blocked)
            owner_block_line = f"OWNER-SPECIFIC BLOCKED PHRASES (hard ban): {bp}\n"

        name_line = ""
        if self.settings.mention_business_name:
            name_line = (
                f'BUSINESS NAME: Naturally mention "{self.input.business.name}" in at least one variant '
                f'(or roughly half if more than two). Don\'t awkwardly stuff it.\n'
            )

        items_value = ", ".join(self.input.items) if self.input.items else "(none — do NOT name any specific item, dish, product, or service)"

        return f"""BUSINESS CONTEXT:
- Name: "{self.input.business.name}"
- Type: {self.input.business.get_business_type_display()}
- Location/branch: {self.input.location_name or "Main"}
{vocab_line}{style_line}
ALLOWED TOPICS — the ONLY topics you may write about:
{enabled_block}

CUSTOMER INPUT:
- Star rating: {self.input.star_rating}/5 ({_RATING_MOOD.get(self.input.star_rating, "positive")})
- Categories customer picked: {", ".join(self.input.categories) if self.input.categories else "(none)"}
- Focus categories for this generation: {focus_value}
- Specific items / services the customer picked: {items_value}
- Language mode requested: {self.input.language_mode}
- Tone mode requested: {self.input.tone_mode}
- Target review length: {length} ({length_desc})

{length_rule}

{custom_kw_line}{owner_block_line}{name_line}
Generate exactly {n} variant{"s" if n != 1 else ""}. Return only the JSON object specified in the system prompt."""


def _parse_variants(raw_text: str, expected: int) -> list[dict]:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) < 1:
        raise ValueError("No variants in response")
    normalised: list[dict] = []
    for i, v in enumerate(variants[:expected], start=1):
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
    return _has_blocked_phrase(text, FORBIDDEN_PHRASES)


def _call_anthropic(user_msg: str, system_extra: str = "") -> tuple[str, dict[str, int]]:
    """
    Make the Anthropic call, optionally with prompt caching on the system block.

    Caching is gated on ``settings.ANTHROPIC_PROMPT_CACHE`` because at low
    traffic (gaps > 5 min between calls) every cache write expires before
    being read, costing 25% more than no caching at all. Returns the
    model's text output plus a usage dict so callers can log behaviour.
    ``system_extra`` is appended to the user message on retries (small and
    dynamic, never cached).
    """
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_block: Any = SYSTEM_PROMPT
    if settings.ANTHROPIC_PROMPT_CACHE:
        system_block = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    message = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1200,
        system=system_block,
        messages=[{
            "role": "user",
            "content": user_msg + (("\n\n" + system_extra) if system_extra else ""),
        }],
    )
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
        elif hasattr(block, "text"):
            parts.append(block.text)

    usage = getattr(message, "usage", None)
    usage_dict = {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }
    return "".join(parts), usage_dict


def generate_variants(gen_input: GenerationInput, effective: EffectiveSettings) -> tuple[list[dict], bool]:
    """
    Generate ``gen_input.variant_count`` review variants.

    Returns (variants, used_fallback). On API failure or missing key,
    returns pre-written fallback variants and used_fallback=True.
    """
    n = max(1, min(int(gen_input.variant_count or DEFAULT_VARIANT_COUNT), MAX_VARIANT_COUNT))

    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — serving fallback variants")
        return build_fallback_variants(
            gen_input.language_mode, gen_input.business.name, effective.review_length, count=n
        ), True

    user_msg = PromptBuilder(gen_input, effective).build_user_message()
    owner_blocked = list(effective.blocked_phrases or [])

    try:
        raw, usage = _call_anthropic(user_msg)
        logger.info(
            "anthropic.usage cache=%s in=%s out=%s cache_read=%s cache_create=%s",
            "on" if settings.ANTHROPIC_PROMPT_CACHE else "off",
            usage["input_tokens"], usage["output_tokens"],
            usage["cache_read_input_tokens"], usage["cache_creation_input_tokens"],
        )
        variants = _parse_variants(raw, n)

        needs_retry = any(
            _has_blocked_phrase(v["text"], owner_blocked) or _has_forbidden_cliche(v["text"])
            for v in variants
        )
        if needs_retry:
            logger.info("Blocked/forbidden phrase detected — regenerating once")
            retry_hint = (
                "REMINDER: Your previous draft used a forbidden or owner-blocked phrase. "
                "Regenerate with zero usage of those phrases. Use plainer, more human alternatives."
            )
            raw, _ = _call_anthropic(user_msg, system_extra=retry_hint)
            variants = _parse_variants(raw, n)
            clean = [
                v for v in variants
                if not _has_blocked_phrase(v["text"], owner_blocked)
                and not _has_forbidden_cliche(v["text"])
            ]
            if len(clean) < n:
                pads = build_fallback_variants(
                    gen_input.language_mode, gen_input.business.name,
                    effective.review_length, count=n,
                )
                for p in pads:
                    if len(clean) >= n:
                        break
                    if (not _has_blocked_phrase(p["text"], owner_blocked)
                            and not _has_forbidden_cliche(p["text"])):
                        clean.append(p)
            variants = clean[:n]

        while len(variants) < n:
            pads = build_fallback_variants(
                gen_input.language_mode, gen_input.business.name,
                effective.review_length, count=n,
            )
            variants.append(pads[len(variants) % n])

        for i, v in enumerate(variants, start=1):
            v["variant_number"] = i

        return variants, False

    except Exception as exc:
        logger.exception("AI generation failed, using fallback: %s", exc)
        return build_fallback_variants(
            gen_input.language_mode, gen_input.business.name,
            effective.review_length, count=n,
        ), True
