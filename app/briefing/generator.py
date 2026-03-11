"""
generator.py — Calls Claude API to generate the morning briefing (CC-05)
"""

import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1500


def generate_briefing(system_prompt: str, user_prompt: str) -> str:
    """
    Call Claude API with system + user prompts.
    Returns the generated briefing text.
    Uses ANTHROPIC_API_KEY from environment.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text
