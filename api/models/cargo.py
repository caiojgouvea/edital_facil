from api import db


class Cargo(db.Model):
    """Cargo extraído de um edital, com todos os seus atributos."""

    __tablename__ = "cargos"

    id = db.Column(db.Integer, primary_key=True)
    edital_id = db.Column(db.Integer, db.ForeignKey("editais.id"), nullable=False)

    nome = db.Column(db.Text, nullable=False)
    area = db.Column(db.Text)

    # Campos de exibição
    salario = db.Column(db.Text)
    vagas = db.Column(db.Text)
    escolaridade = db.Column(db.Text)
    beneficios = db.Column(db.Text)

    # Campos normalizados para filtragem futura
    salario_valor = db.Column(db.Float)
    vagas_numero = db.Column(db.Integer)

    def to_dict(self) -> dict:
        """Serializa o cargo para dicionário compatível com JSON."""
        return {
            "id": self.id,
            "nome": self.nome,
            "area": self.area,
            "salario": self.salario,
            "salario_valor": self.salario_valor,
            "vagas": self.vagas,
            "vagas_numero": self.vagas_numero,
            "escolaridade": self.escolaridade,
            "beneficios": self.beneficios,
        }
