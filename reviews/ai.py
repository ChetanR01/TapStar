"""
AI review generation — PromptBuilder + Anthropic call.

Takes customer input (rating/categories/items/language) + effective business settings,
produces 4 Google-review variants in different Indian language styles.

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

from .fallback import build_fallback_variants

logger = logging.getLogger(__name__)


LENGTH_DESCRIPTIONS = {
    "short": "1-2 sentences",
    "medium": "3-4 sentences",
    "detailed": "5-7 sentences",
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


PROMPT_TEMPLATE = """You are generating Google reviews for a {business_type} called "{business_name}".

CUSTOMER INPUT:
- Star rating: {star_rating}/5
- Categories they experienced: {categories}
- Specific items/services: {items}
- Language mode: {language_mode}
- Tone mode: {tone_mode}
- Review length: {length}

LANGUAGE DEFINITIONS:
- hinglish: Mix of Hindi and English in Roman script. Natural code-switching like real Indian customers text. Example: "Bhai ekdum mast tha, staff bhi bahut helpful tha!"
- minglish: Mix of Marathi and English in Roman script. Example: "Chan jevan hota, nakki parayanda yeil!"
- hindi: Pure Hindi in Devanagari script. Formal or informal based on tone.
- marathi: Pure Marathi in Devanagari script.
- english: Natural Indian English — not British/American formal. Indian rhythm and expressions.
- random: Distribute across all 5 styles — no two variants same language.

TONE DEFINITIONS:
- casual: Friendly, bhai-type, feels like a WhatsApp message. Can use emoji sparingly.
- formal: Polite, structured. Suits professional services.
- enthusiastic: Excited, lots of positive energy, exclamation marks.
- random: Vary tone across variants.

{custom_keywords_instruction}
{blocked_phrases_instruction}
{business_name_instruction}

CRITICAL AUTHENTICITY RULES - STRICTLY FOLLOW:
1. Write exactly like a real Indian customer wrote this on their phone
2. Do NOT use corporate marketing language ("exceptional experience", "highly recommend", "five-star service")
3. Each variant must feel genuinely different — different structure, different expressions, not just translation
4. Allow natural minor imperfections — casual punctuation, emoji in casual tone, informal grammar in Hinglish
5. Reference the specific items/categories selected — make review feel personal and specific
6. Keep it {length_description}
7. Never start two variants with the same first word

OUTPUT FORMAT - respond with ONLY this JSON, no explanation, no markdown:
{{
  "variants": [
    {{"variant_number": 1, "language": "hinglish", "tone": "casual", "text": "..."}},
    {{"variant_number": 2, "language": "english", "tone": "enthusiastic", "text": "..."}},
    {{"variant_number": 3, "language": "minglish", "tone": "casual", "text": "..."}},
    {{"variant_number": 4, "language": "hindi", "tone": "formal", "text": "..."}}
  ]
}}
"""


class PromptBuilder:
    def __init__(self, gen_input: GenerationInput, effective: EffectiveSettings):
        self.input = gen_input
        self.settings = effective

    def build(self) -> str:
        custom_keywords_instruction = ""
        if self.settings.custom_keywords:
            kw = ", ".join(f'"{k}"' for k in self.settings.custom_keywords)
            custom_keywords_instruction = (
                f"KEYWORDS TO INCLUDE: Naturally include these words/phrases somewhere in the reviews "
                f"(only if they fit naturally, don't force them): {kw}"
            )

        blocked_phrases_instruction = ""
        if self.settings.blocked_phrases:
            bp = ", ".join(f'"{b}"' for b in self.settings.blocked_phrases)
            blocked_phrases_instruction = (
                f"BLOCKED PHRASES: NEVER use these words or phrases in any variant: {bp}"
            )

        business_name_instruction = ""
        if self.settings.mention_business_name:
            business_name_instruction = (
                f'BUSINESS NAME: Mention "{self.input.business.name}" naturally in at least 2 of the 4 variants.'
            )

        length = self.settings.review_length
        length_description = LENGTH_DESCRIPTIONS.get(length, "3-4 sentences")

        return PROMPT_TEMPLATE.format(
            business_type=self.input.business.get_business_type_display(),
            business_name=self.input.business.name,
            star_rating=self.input.star_rating,
            categories=", ".join(self.input.categories) or "general experience",
            items=", ".join(self.input.items) or "none specified",
            language_mode=self.input.language_mode,
            tone_mode=self.input.tone_mode,
            length=length,
            length_description=length_description,
            custom_keywords_instruction=custom_keywords_instruction,
            blocked_phrases_instruction=blocked_phrases_instruction,
            business_name_instruction=business_name_instruction,
        )


def _parse_variants(raw_text: str) -> list[dict]:
    """Extract the variants array from model output. Tolerates leading/trailing whitespace."""
    cleaned = raw_text.strip()
    # Strip accidental markdown fences
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


def _call_anthropic(prompt: str) -> str:
    import anthropic  # imported lazily so missing key doesn't break imports

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    # content is a list of blocks — concat text blocks
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

    try:
        raw = _call_anthropic(prompt)
        variants = _parse_variants(raw)

        # Blocked phrase check — single regeneration attempt
        if effective.blocked_phrases and any(
            _has_blocked_phrase(v["text"], effective.blocked_phrases) for v in variants
        ):
            logger.info("Blocked phrase detected in AI output — regenerating once")
            retry_prompt = prompt + "\n\nREMINDER: You included a blocked phrase in your previous attempt. Regenerate with ZERO usage of the blocked phrases listed above."
            raw = _call_anthropic(retry_prompt)
            variants = _parse_variants(raw)
            # Drop any still-dirty variants and pad with fallbacks if needed
            clean = [v for v in variants if not _has_blocked_phrase(v["text"], effective.blocked_phrases)]
            if len(clean) < 4:
                pads = build_fallback_variants(gen_input.language_mode, gen_input.business.name)
                for p in pads:
                    if len(clean) >= 4:
                        break
                    if not _has_blocked_phrase(p["text"], effective.blocked_phrases):
                        clean.append(p)
            variants = clean[:4]

        # Ensure we always return 4
        while len(variants) < 4:
            pads = build_fallback_variants(gen_input.language_mode, gen_input.business.name)
            variants.append(pads[len(variants) % 4])

        # Re-number sequentially
        for i, v in enumerate(variants, start=1):
            v["variant_number"] = i

        return variants, False

    except Exception as exc:
        logger.exception("AI generation failed, using fallback: %s", exc)
        return build_fallback_variants(gen_input.language_mode, gen_input.business.name), True
