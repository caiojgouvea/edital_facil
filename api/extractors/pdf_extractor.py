"""Extrator de campos de editais de concurso público a partir de PDF.

Uso standalone: python -m api.extractors.pdf_extractor <caminho.pdf>.
"""

import re
import sys

import pdfplumber

from api.services.llm import extrair_json

_PROMPT_TEMPLATE = """Você é um extrator de dados de editais de concurso público brasileiro.

Extraia as informações abaixo do edital e retorne SOMENTE um JSON válido, sem markdown, sem
explicações.

Estrutura esperada:
{{
  "municipio": "Nome do município ou null",
  "uf": "Sigla do estado com 2 letras (ex: SC) ou null",
  "orgao": "Nome do órgão ou entidade realizadora (ex: TCE-SC, Câmara Municipal) ou null",
  "banca": "Nome da banca organizadora (ex: CESPE, FGV, VUNESP) ou null",
  "data_prova": "DD/MM/AAAA ou null",
  "data_prova_iso": "YYYY-MM-DD ou null",
  "inscricao_inicio": "DD/MM/AAAA ou null",
  "inscricao_inicio_iso": "YYYY-MM-DD ou null",
  "inscricao_fim": "DD/MM/AAAA ou null",
  "inscricao_fim_iso": "YYYY-MM-DD ou null",
  "cargos": [
    {{
      "nome": "nome do cargo",
      "area": "área de habilitação ou null",
      "salario": "R$ valor ou null",
      "salario_valor": numero em float ou null,
      "vagas": "número + CR ou somente número ou null",
      "vagas_numero": numero inteiro (ignorar CR) ou null,
      "escolaridade": "nível exigido ou null",
      "beneficios": "um benefício por linha no formato Nome: R$ valor, ou null"
    }}
  ]
}}

Regras:
- Se um cargo tiver múltiplas áreas de habilitação, crie um item por área
- Use null (não string vazia) quando não encontrar a informação
- Para vagas, inclua CR no campo "vagas" quando houver cadastro de reserva (ex: "5 + CR"), \
mas em "vagas_numero" coloque apenas o número inteiro
- Para salário, procure por: "vencimento", "vencimento inicial", "remuneração", "subsídio" seguido \
de valor em reais. Formate "salario" como "R$ X.XXX,XX" e "salario_valor" como número float
- Para escolaridade, procure por: "ensino superior", "ensino médio", "graduação em", "diploma de", \
"bacharel em", "nível superior". Inclua a área quando especificada
- Para benefícios, liste um por linha: auxílio-alimentação, auxílio-saúde, vale-transporte, etc.
- Se o salário for igual para todas as áreas de habilitação de um cargo, repita-o em cada item
- "orgao" é quem realiza o concurso (prefeitura, tribunal, câmara); "banca" é quem organiza a prova

Edital:
{texto}"""


# Padrões para localizar seções relevantes espalhadas pelo documento
_SECOES_CHAVE = [
    r"remuner[aã]",
    r"vencimento\s+(?:inicial|b[aá]sico)",
    r"per[ií]odo\s+de\s+inscri",
    r"das\s+provas?",
    r"data\s+(?:provável|da\s+realiza)",
    r"PROCEDIMENTOS\s+DATAS",
    r"cronograma\s+de\s+execu",
    r"dos?\s+benef[ií]cios?",
    r"requisitos?\s+(?:do\s+cargo|para\s+(?:investidura|o\s+cargo))",
    r"anexo\s+ii",
]


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


def _montar_trecho(texto: str) -> str:
    """Seleciona as partes mais relevantes do texto para enviar ao LLM.

    Sempre inclui o início do edital (cargo, vagas, requisitos básicos) e
    busca ativamente seções-chave ao longo do documento inteiro — salário,
    cronograma, benefícios — para incluí-las mesmo que estejam no final.
    """
    secoes: list[str] = [texto[:30000]]
    vistos: set[int] = set()

    for padrao in _SECOES_CHAVE:
        for match in re.finditer(padrao, texto, re.IGNORECASE):
            # Bloco de 2500 chars centrado no match; evita sobreposição com início
            inicio = max(30000, match.start() - 200)
            # Arredonda para bloco de 1000 para evitar duplicatas próximas
            chave = inicio // 1000
            if chave in vistos:
                continue
            vistos.add(chave)
            secoes.append(texto[inicio : inicio + 2500])

    return "\n\n[...]\n\n".join(secoes)


def extrair_campos(filepath: str) -> dict:
    """Extrai os campos estruturados de um edital de concurso público via LLM.

    Args:
        filepath: caminho para o arquivo PDF do edital.

    Returns:
        Dicionário com todos os campos extraídos.
        Retorna estrutura vazia em caso de falha.
    """
    texto = extrair_texto(filepath)
    trecho = _montar_trecho(texto)
    prompt = _PROMPT_TEMPLATE.format(texto=trecho)

    resultado = extrair_json(prompt, max_tokens=3000)

    if not resultado:
        return {
            "municipio": None,
            "uf": None,
            "orgao": None,
            "banca": None,
            "data_prova": None,
            "data_prova_iso": None,
            "inscricao_inicio": None,
            "inscricao_inicio_iso": None,
            "inscricao_fim": None,
            "inscricao_fim_iso": None,
            "cargos": [],
        }

    resultado.setdefault("cargos", [])
    for key in (
        "municipio",
        "uf",
        "orgao",
        "banca",
        "data_prova",
        "data_prova_iso",
        "inscricao_inicio",
        "inscricao_inicio_iso",
        "inscricao_fim",
        "inscricao_fim_iso",
    ):
        resultado.setdefault(key, None)

    return resultado


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m api.extractors.pdf_extractor <arquivo.pdf>")
        sys.exit(1)

    campos = extrair_campos(sys.argv[1])
    municipio = campos.get("municipio") or ""
    uf = campos.get("uf") or ""
    cidade_estado = f"{municipio}/{uf}" if municipio and uf else "(não encontrado)"
    print(f"{'cidade_estado':20s}: {cidade_estado}")
    print(f"{'orgao':20s}: {campos.get('orgao') or '(não encontrado)'}")
    print(f"{'banca':20s}: {campos.get('banca') or '(não encontrado)'}")
    print(f"{'data_prova':20s}: {campos.get('data_prova') or '(não encontrado)'}")
    inscricao = (
        f"{campos.get('inscricao_inicio')} a {campos.get('inscricao_fim')}"
        if campos.get("inscricao_inicio")
        else "(não encontrado)"
    )
    print(f"{'inscricao':20s}: {inscricao}")
    print()
    for cargo in campos.get("cargos", []):
        print(f"  Cargo     : {cargo.get('nome')}")
        print(f"  Área      : {cargo.get('area') or '—'}")
        print(f"  Salário   : {cargo.get('salario') or '—'} ({cargo.get('salario_valor') or '—'})")
        print(f"  Vagas     : {cargo.get('vagas') or '—'} ({cargo.get('vagas_numero') or '—'})")
        print(f"  Escolar.  : {cargo.get('escolaridade') or '—'}")
        print(f"  Benefícios: {cargo.get('beneficios') or '—'}")
        print()
