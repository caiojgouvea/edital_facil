from api import db
from api.extractors.pdf_extractor import extrair_campos
from api.models import Edital


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
        edital.cargos = campos.get("cargos")
        edital.salarios = campos.get("salarios")
        edital.escolaridade = campos.get("escolaridade")
        edital.vagas = campos.get("vagas")
        edital.cidade_estado = campos.get("cidade_estado")
        edital.data_prova = campos.get("data_prova")
        edital.periodo_inscricao = campos.get("periodo_inscricao")
        edital.status = "done"
    except Exception as exc:
        edital.status = "error"
        raise exc
    finally:
        db.session.commit()
