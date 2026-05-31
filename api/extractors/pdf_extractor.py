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


def _buscar(padrao: str, texto: str, flags: int = re.IGNORECASE) -> str | None:
    match = re.search(padrao, texto, flags)
    return match.group(1).strip() if match else None


def _encontrar_linhas_cargos(pdf) -> list[dict]:
    """Localiza e parseia a tabela principal de cargos do edital.

    Returns:
        Lista de dicts com cargo, escolaridade, vagas e salario. Vazia se não encontrada.
    """
    for page in pdf.pages:
        for table in page.extract_tables():
            if not table:
                continue
            header = " ".join(str(c or "") for c in table[0]).lower()
            if "cargo" in header and ("vencimento" in header or "escolaridade" in header):
                linhas = []
                for row in table:
                    if len(row) < 9:
                        continue
                    codigo = str(row[0] or "").strip()
                    if not codigo.isdigit():
                        continue
                    vagas = str(row[4] or row[5] or "").replace("\n", " ").strip()
                    salario = str(row[8] or "").split("\n")[0].strip()
                    linhas.append(
                        {
                            "cargo": str(row[2] or "").replace("\n", " ").strip(),
                            "escolaridade": str(row[3] or "").replace("\n", " ").strip(),
                            "vagas": vagas,
                            "salario": salario,
                        }
                    )
                if linhas:
                    return linhas
    return []


def _encontrar_texto_cronograma(pdf) -> str:
    """Extrai o texto das páginas que compõem o cronograma de execução.

    Returns:
        Texto concatenado das páginas do cronograma. Vazio se não encontrado.
    """
    textos = []
    collecting = False
    for page in pdf.pages:
        texto = page.extract_text() or ""
        if re.search(r"PROCEDIMENTOS\s+DATAS", texto, re.IGNORECASE):
            collecting = True
        if collecting:
            textos.append(texto)
            if len(textos) >= 4:
                break
    return "\n".join(textos)


def extrair_campos(filepath: str) -> dict:
    """Extrai os campos estruturados de um edital de concurso público.

    Args:
        filepath: caminho para o arquivo PDF do edital.

    Returns:
        Dicionário com os campos extraídos. Valor None quando não encontrado.
    """
    with pdfplumber.open(filepath) as pdf:
        texto = "\n".join(page.extract_text() or "" for page in pdf.pages)
        linhas_cargos = _encontrar_linhas_cargos(pdf)
        texto_cronograma = _encontrar_texto_cronograma(pdf)

    return {
        "cargos": _extrair_cargos(linhas_cargos, texto),
        "salarios": _extrair_salarios(linhas_cargos, texto),
        "escolaridade": _extrair_escolaridade(linhas_cargos, texto),
        "vagas": _extrair_vagas(linhas_cargos, texto),
        "cidade_estado": _extrair_cidade_estado(texto),
        "data_prova": _extrair_data_prova(texto_cronograma, texto),
        "periodo_inscricao": _extrair_periodo_inscricao(texto_cronograma, texto),
    }


def _extrair_cargos(linhas: list[dict], texto: str) -> str | None:
    if linhas:
        nomes = [linha["cargo"] for linha in linhas if linha["cargo"]]
        return ", ".join(nomes) if nomes else None
    return _buscar(r"cargo[s]?\s*[:\-–]\s*(.+)", texto)


def _extrair_salarios(linhas: list[dict], texto: str) -> str | None:
    if linhas:
        salarios = [linha["salario"] for linha in linhas if linha["salario"]]
        return ", ".join(salarios) if salarios else None
    resultado = _buscar(r"vencimento[s]?\s*[:\-–]?\s*(R\$\s*[\d.,]+)", texto)
    if not resultado:
        resultado = _buscar(r"sal[aá]rio[s]?\s*[:\-–]?\s*(R\$\s*[\d.,]+)", texto)
    return resultado


def _extrair_escolaridade(linhas: list[dict], texto: str) -> str | None:
    if linhas:
        vistos: set[str] = set()
        niveis = []
        for linha in linhas:
            esc = linha["escolaridade"]
            nivel_match = re.match(r"(Ensino\s+\S+\s+\S+)", esc, re.IGNORECASE)
            nivel = nivel_match.group(1).rstrip(".,;:") if nivel_match else esc.split(".")[0]
            if nivel and nivel not in vistos:
                vistos.add(nivel)
                niveis.append(nivel)
        return "; ".join(niveis) if niveis else None
    for padrao in [
        r"escolaridade\s*[:\-–]\s*(.+)",
        r"nível\s+de\s+escolaridade\s*[:\-–]\s*(.+)",
        r"requisito[s]?\s*[:\-–]\s*(.+)",
    ]:
        resultado = _buscar(padrao, texto)
        if resultado:
            return resultado
    return None


def _extrair_vagas(linhas: list[dict], texto: str) -> str | None:
    if linhas:
        entradas = [f"{linha['cargo']}: {linha['vagas']}" for linha in linhas if linha["vagas"]]
        return ", ".join(entradas) if entradas else None
    return _buscar(r"(\d+)\s*(?:vaga[s]?|vagas)", texto)


def _extrair_cidade_estado(texto: str) -> str | None:
    cidade_pat = r"[A-ZÀ-Ú][a-zà-úÀ-ÿ]+(?:\s+[A-ZÀ-Ú][a-zà-úÀ-ÿ]+)*"
    # Prefer pattern with explicit UF slash (e.g. "Municipal de Palhoça/SC")
    for prefixo in (r"[Mm]unicip(?:al|io|ío)\s+de", r"prefeitura\s+(?:municipal\s+)?de"):
        match = re.search(rf"{prefixo}\s+({cidade_pat})/([A-Z]{{2}})\b", texto, re.IGNORECASE)
        if match:
            return f"{match.group(1).strip()}/{match.group(2)}"
    # Fallback: without UF
    match = re.search(
        rf"[Mm]unicip(?:al|io|ío)\s+de\s+({cidade_pat})",
        texto,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _extrair_data_prova(texto_cronograma: str, texto: str) -> str | None:
    padroes = [
        r"[Aa]plica[çc][ãa]o\s+das?\s+[Pp]rovas?\s+[Tt]e[oó]rico.+?(\d{1,2}/\d{2}/\d{4})",
        r"realiza[çc][ãa]o\s+das?\s+provas?\s+te[oó]rico.objetivas?\s+(\d{1,2}/\d{2}/\d{4})",
        r"data\s+das?\s+provas?\s*[:\-–]\s*(\d{1,2}/\d{2}/\d{4})",
        r"prova\s+objetiva\s*[:\-–]\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"realiza[çc][ãa]o\s+da\s+prova\s*[:\-–]\s*(\d{1,2}/\d{1,2}/\d{4})",
    ]
    for fonte in (texto_cronograma, texto):
        for padrao in padroes:
            resultado = _buscar(padrao, fonte, re.IGNORECASE | re.DOTALL)
            if resultado:
                return resultado
    return None


def _extrair_periodo_inscricao(texto_cronograma: str, texto: str) -> str | None:
    padrao = (
        r"per[ií]odo\s+de\s+inscri[çc][õo]es?\b.{0,120}?"
        r"(\d{1,2}/\d{1,2}(?:/\d{4})?)\s+a\s+(\d{1,2}/\d{1,2}(?:/\d{4})?)"
    )
    for fonte in (texto_cronograma, texto):
        match = re.search(padrao, fonte, re.IGNORECASE | re.DOTALL)
        if match:
            return f"{match.group(1)} a {match.group(2)}"
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m api.extractors.pdf_extractor <arquivo.pdf>")
        sys.exit(1)

    campos = extrair_campos(sys.argv[1])
    for campo, valor in campos.items():
        print(f"{campo:20s}: {valor or '(não encontrado)'}")
