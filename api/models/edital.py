from datetime import UTC, datetime

from api import db


class Edital(db.Model):
    """Registro de um edital processado com metadados gerais e lista de cargos."""

    __tablename__ = "editais"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default="processing")  # processing | done | error

    # Campos gerais do edital
    cidade_estado = db.Column(db.Text)
    data_prova = db.Column(db.Text)
    periodo_inscricao = db.Column(db.Text)

    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    cargos = db.relationship("Cargo", backref="edital", lazy=True, cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Serializa o edital para dicionário compatível com JSON."""
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "cidade_estado": self.cidade_estado,
            "data_prova": self.data_prova,
            "periodo_inscricao": self.periodo_inscricao,
            "cargos": [c.to_dict() for c in self.cargos],
            "criado_em": self.criado_em.isoformat(),
        }
