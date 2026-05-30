import os

from flask import Blueprint, current_app, jsonify, render_template, request
from werkzeug.utils import secure_filename

from api import db
from api.models import Edital

bp = Blueprint("editais", __name__)

ALLOWED_EXTENSIONS = {"pdf"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.get("/")
def index():
    """Renderiza a página principal com o formulário de upload."""
    return render_template("index.html")


@bp.post("/upload")
def upload():
    """Recebe o PDF, persiste o registro e dispara o processamento.

    Returns:
        JSON com job_id e status inicial, HTTP 202.
    """
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]

    if not file.filename or not _allowed_file(file.filename):
        return jsonify({"error": "Apenas arquivos PDF são aceitos"}), 400

    filename = secure_filename(file.filename)
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    edital = Edital(filename=filename, status="processing")
    db.session.add(edital)
    db.session.commit()

    # TODO: substituir por task Celery quando fila estiver configurada
    from api.services.edital_service import processar_edital
    processar_edital(edital.id, filepath)

    return jsonify({"job_id": edital.id, "status": edital.status}), 202


@bp.get("/editais/<int:edital_id>")
def resultado(edital_id: int):
    """Retorna o resultado extraído de um edital pelo seu ID."""
    edital = db.get_or_404(Edital, edital_id)
    return jsonify(edital.to_dict())


@bp.get("/historico")
def historico():
    """Lista todos os editais processados em ordem cronológica decrescente."""
    editais = Edital.query.order_by(Edital.criado_em.desc()).all()
    return jsonify([e.to_dict() for e in editais])
