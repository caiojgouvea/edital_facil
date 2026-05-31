from datetime import UTC, datetime

from api import db


class Edital(db.Model):
    """Registro de um edital processado com metadados gerais e lista de cargos."""

    __tablename__ = "editais"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="processing")  # processing | done | error

    # Campos de exibição (texto livre retornado pelo LLM)
    data_prova = db.Column(db.Text)
    periodo_inscricao = db.Column(db.Text)

    # Campos normalizados para filtragem futura
    municipio = db.Column(db.Text)
    uf = db.Column(db.String(2))
    orgao = db.Column(db.Text)
    banca = db.Column(db.Text)
    data_prova_dt = db.Column(db.Date)
    inscricao_inicio = db.Column(db.Date)
    inscricao_fim = db.Column(db.Date)

    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    cargos = db.relationship("Cargo", backref="edital", lazy=True, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Serializa o edital para dicionário compatível com JSON."""
        cidade_estado = f"{self.municipio}/{self.uf}" if self.municipio and self.uf else None
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "cidade_estado": cidade_estado,
            "municipio": self.municipio,
            "uf": self.uf,
            "orgao": self.orgao,
            "banca": self.banca,
            "data_prova": self.data_prova,
            "data_prova_dt": self.data_prova_dt.isoformat() if self.data_prova_dt else None,
            "periodo_inscricao": self.periodo_inscricao,
            "inscricao_inicio": (
                self.inscricao_inicio.isoformat() if self.inscricao_inicio else None
            ),
            "inscricao_fim": self.inscricao_fim.isoformat() if self.inscricao_fim else None,
            "cargos": [c.to_dict() for c in self.cargos],
            "criado_em": self.criado_em.isoformat(),
        }
