from openai import OpenAI
import os
from src.config import load_config


def get_client():
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        raise ValueError("ZAI_API_KEY is not set in environment")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.z.ai/api/paas/v4/"
    )


def generate_report(topic: str) -> tuple[str, float]:
    """
    Generate a short research report using GLM model via z.ai
    Returns: (report_text, estimated_cost_usd)
    """
    cfg = load_config()
    model = cfg.get("model", "glm-5.3")
    max_tokens = cfg.get("max_tokens", 1000)

    client = get_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise crypto and market research analyst. "
                    "Write clear, factual, short research reports. "
                    "Avoid hype. Focus on key facts, trends, and risks."
                )
            },
            {
                "role": "user",
                "content": f"Write a short research report (maximum 400 words) about: {topic}"
            }
        ],
        max_tokens=max_tokens,
        temperature=0.6
    )

    content = response.choices[0].message.content

    # Rough cost estimate (adjust later with real z.ai pricing)
    tokens = response.usage.total_tokens if response.usage else 800
    estimated_cost = tokens * 0.000012   # approximate

    return content, estimated_cost
