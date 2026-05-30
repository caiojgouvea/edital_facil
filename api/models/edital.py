from datetime import UTC, datetime

from api import db


class Edital(db.Model):
    """Registro de um edital processado, com os campos extraídos e status do job."""

    __tablename__ = "editais"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="processing")  # processing | done | error

    # Campos extraídos
    cargos = db.Column(db.Text)
    salarios = db.Column(db.Text)
    escolaridade = db.Column(db.Text)
    vagas = db.Column(db.Text)
    cidade_estado = db.Column(db.Text)
    data_prova = db.Column(db.Text)
    periodo_inscricao = db.Column(db.Text)

    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Serializa o registro para dicionário compatível com JSON."""
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "cargos": self.cargos,
            "salarios": self.salarios,
            "escolaridade": self.escolaridade,
            "vagas": self.vagas,
            "cidade_estado": self.cidade_estado,
            "data_prova": self.data_prova,
            "periodo_inscricao": self.periodo_inscricao,
            "criado_em": self.criado_em.isoformat(),
        }
