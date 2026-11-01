import os
import logging

logger = logging.getLogger(__name__)

async def generate(system_prompt, user_prompt):
    """Use OpenAI when configured; return None for local fallback."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=key)
        result = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            temperature=0.4
        )
        return result.choices[0].message.content or None
    except Exception:
        logger.exception("OpenAI response generation failed; using the local demo response.")
        return None
