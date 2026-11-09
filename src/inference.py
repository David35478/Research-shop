from anthropic import Anthropic
import os
from src.config import load_config


def get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment")

    return Anthropic(
        api_key=api_key,
        base_url="https://api.mwapi.dev"
    )


def generate_report(topic: str) -> tuple[str, float]:
    """
    Generate a short research report using GLM model via z.ai
    Returns: (report_text, estimated_cost_usd)
    """
    cfg = load_config()
    model = cfg.get("model", "claude-haiku-5-5")
    max_tokens = cfg.get("max_tokens", 1000)

    client = get_client()

    response = client.messages.create(
        model=model,
        system=(
            "You are a concise crypto and market research analyst. "
            "Write clear, factual, short research reports. "
            "Avoid hype. Focus on key facts, trends, and risks."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Write a short research report (maximum 400 words) about: {topic}"
            }
        ],
        max_tokens=max_tokens
    )

    content = "".join(block.text for block in response.content if block.type == "text")

    # Rough cost estimate (adjust later with real z.ai pricing)
    # Rough cost estimate (adjust later with real relay pricing)
    tokens = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 800
    estimated_cost = tokens * 0.000012   # approximate

    return content, estimated_cost
