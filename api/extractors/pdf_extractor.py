"""Extrator de campos de editais de concurso público a partir de PDF.

Uso standalone: python -m api.extractors.pdf_extractor <caminho.pdf>.
"""

import re
import sys

import pdfplumber


def extrair_texto(filepath: str) -> str:
    """Extrai o texto bruto de todas as páginas do PDF.

    Args:
        filepath: caminho absoluto ou relativo para o arquivo PDF.

    Returns:
        Texto concatenado de todas as páginas, separadas por newline.
    """
    with pdfplumber.open(filepath) as pdf:
        paginas = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(paginas)


def _buscar(padrao: str, texto: str, flags=re.IGNORECASE) -> str | None:
    match = re.search(padrao, texto, flags)
    return match.group(1).strip() if match else None


def extrair_campos(filepath: str) -> dict:
    """Extrai os campos estruturados de um edital de concurso público.

    Args:
        filepath: caminho para o arquivo PDF do edital.

    Returns:
        Dicionário com os campos extraídos. Valor None quando não encontrado.
    """
    texto = extrair_texto(filepath)

    return {
        "cargos": _extrair_cargos(texto),
        "salarios": _extrair_salarios(texto),
        "escolaridade": _extrair_escolaridade(texto),
        "vagas": _extrair_vagas(texto),
        "cidade_estado": _extrair_cidade_estado(texto),
        "data_prova": _extrair_data_prova(texto),
        "periodo_inscricao": _extrair_periodo_inscricao(texto),
    }


def _extrair_cargos(texto: str) -> str | None:
    match = _buscar(r"cargo[s]?\s*[:\-–]\s*(.+)", texto)
    return match


def _extrair_salarios(texto: str) -> str | None:
    match = _buscar(r"vencimento[s]?\s*[:\-–]?\s*(R\$\s*[\d.,]+)", texto)
    if not match:
        match = _buscar(r"sal[aá]rio[s]?\s*[:\-–]?\s*(R\$\s*[\d.,]+)", texto)
    return match


def _extrair_escolaridade(texto: str) -> str | None:
    padroes = [
        r"escolaridade\s*[:\-–]\s*(.+)",
        r"nível\s+de\s+escolaridade\s*[:\-–]\s*(.+)",
        r"requisito[s]?\s*[:\-–]\s*(.+)",
    ]
    for padrao in padroes:
        resultado = _buscar(padrao, texto)
        if resultado:
            return resultado
    return None


def _extrair_vagas(texto: str) -> str | None:
    return _buscar(r"(\d+)\s*(?:vaga[s]?|vagas)", texto)


def _extrair_cidade_estado(texto: str) -> str | None:
    padrao = r"município\s+de\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)\s*/?\s*([A-Z]{2})?"
    return _buscar(padrao, texto)


def _extrair_data_prova(texto: str) -> str | None:
    padroes = [
        r"data\s+da\s+prova\s*[:\-–]\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"prova\s+objetiva\s*[:\-–]\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"realiza[çc][ãa]o\s+da\s+prova\s*[:\-–]\s*(\d{1,2}/\d{1,2}/\d{4})",
    ]
    for padrao in padroes:
        resultado = _buscar(padrao, texto)
        if resultado:
            return resultado
    return None


def _extrair_periodo_inscricao(texto: str) -> str | None:
    return _buscar(
        r"inscri[çc][õo]es?\s*[:\-–]?\s*(?:de\s+)?(\d{1,2}/\d{1,2}/\d{4})\s+a[té]?\s+(\d{1,2}/\d{1,2}/\d{4})",
        texto,
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m api.extractors.pdf_extractor <arquivo.pdf>")
        sys.exit(1)

    campos = extrair_campos(sys.argv[1])
    for campo, valor in campos.items():
        print(f"{campo:20s}: {valor or '(não encontrado)'}")
