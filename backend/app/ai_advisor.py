from __future__ import annotations

import json
from typing import Any

from .config import GEMINI_API_KEY, GEMINI_MODEL


def _fallback(question: str, assessment: dict[str, Any]) -> str:
    drivers = assessment.get("drivers", [])[:3]
    driver_text = ", ".join(
        f"{d['label']} ({d['value']}{d['unit']})" for d in drivers
    ) or "available environmental signals"

    q = question.lower()
    if "why" in q or "risk" in q:
        return (
            f"FarmGuard rates current stress as {assessment['level']} ({assessment['score']}/100). "
            f"The strongest contributing signals are {driver_text}. {assessment['recommendation']}"
        )
    if "what should" in q or "action" in q or "do" in q:
        return f"Recommended next step: {assessment['action']}. {assessment['recommendation']}"
    return (
        f"Based on the current FarmGuard assessment, risk is {assessment['level']} at "
        f"{assessment['score']}/100. {assessment['recommendation']}"
    )


def answer_question(question: str, assessment: dict[str, Any], latest: dict[str, Any]) -> dict[str, Any]:
    """Use Gemini only as the explanation layer; the deterministic engine owns the risk score."""
    if not GEMINI_API_KEY:
        return {
            "answer": _fallback(question, assessment),
            "provider": "local-explainer",
            "model": None,
        }

    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        context = {
            "latest_environmental_reading": latest,
            "farmguard_assessment": assessment,
        }
        prompt = f"""
You are the explanation layer for Conduit FarmGuard, a hackathon prototype using JKUAT environmental data.

Important rules:
- Never invent sensor values.
- Never change the risk score, level, or recommendation produced by the deterministic FarmGuard engine.
- Explain the result in simple farmer-friendly language.
- Be concise: 2 to 5 sentences.
- Do not claim the system replaces an agronomist or local field inspection.
- If soil moisture is absent, explicitly say that irrigation should be confirmed by field/soil inspection.

Ground truth JSON:
{json.dumps(context, default=str)}

User question: {question}
""".strip()

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return {"answer": text, "provider": "gemini", "model": GEMINI_MODEL}
    except Exception as exc:
        return {
            "answer": _fallback(question, assessment),
            "provider": "local-explainer",
            "model": None,
            "warning": f"Gemini unavailable; used local explanation. {type(exc).__name__}: {exc}",
        }
