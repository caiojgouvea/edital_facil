"""Cliente LLM unificado via LiteLLM.

Para trocar de provedor, basta alterar duas variáveis no .env:
  - Anthropic: LLM_MODEL=claude-haiku-4-5-20251001  + ANTHROPIC_API_KEY
  - OpenAI:    LLM_MODEL=gpt-4o-mini               + OPENAI_API_KEY
  - Google:    LLM_MODEL=gemini/gemini-1.5-flash    + GEMINI_API_KEY
"""

import logging
import os

import litellm

litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
_CHAVES = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")


def completar(prompt: str, max_tokens: int = 512) -> str | None:
    """Envia um prompt ao LLM configurado e retorna a resposta em texto.

    Args:
        prompt: texto do prompt a enviar.
        max_tokens: limite de tokens na resposta.

    Returns:
        Conteúdo da resposta como string, ou None se não houver chave
        configurada ou ocorrer algum erro na chamada.
    """
    if not any(os.getenv(k) for k in _CHAVES):
        return None

    try:
        response = litellm.completion(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception:
        return None
