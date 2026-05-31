from datetime import date

from api import db
from api.extractors.pdf_extractor import extrair_campos
from api.models import Cargo, Edital


def _parse_date(iso: str | None) -> date | None:
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def processar_edital(edital_id: int, filepath: str) -> None:
    """Executa a extração de campos e atualiza o registro no banco.

    Args:
        edital_id: ID do registro Edital já persistido.
        filepath: caminho local do PDF salvo.
    """
    edital = db.session.get(Edital, edital_id)
    if not edital:
        return

    try:
        campos = extrair_campos(filepath)

        edital.municipio = campos.get("municipio")
        edital.uf = campos.get("uf")
        edital.orgao = campos.get("orgao")
        edital.banca = campos.get("banca")

        edital.data_prova = campos.get("data_prova")
        edital.data_prova_dt = _parse_date(campos.get("data_prova_iso"))

        inicio_txt = campos.get("inscricao_inicio")
        fim_txt = campos.get("inscricao_fim")
        edital.inscricao_inicio = _parse_date(campos.get("inscricao_inicio_iso"))
        edital.inscricao_fim = _parse_date(campos.get("inscricao_fim_iso"))

        if inicio_txt and fim_txt:
            edital.periodo_inscricao = f"{inicio_txt} a {fim_txt}"
        elif inicio_txt:
            edital.periodo_inscricao = inicio_txt

        for dado in campos.get("cargos", []):
            cargo = Cargo(
                edital_id=edital.id,
                nome=dado.get("nome") or "",
                area=dado.get("area"),
                salario=dado.get("salario"),
                salario_valor=dado.get("salario_valor"),
                vagas=dado.get("vagas"),
                vagas_numero=dado.get("vagas_numero"),
                escolaridade=dado.get("escolaridade"),
                beneficios=dado.get("beneficios"),
            )
            db.session.add(cargo)

        edital.status = "done"
    except Exception as exc:
        edital.status = "error"
        raise exc
    finally:
        db.session.commit()
