import hashlib
from pathlib import Path

from sqlalchemy import text

from database import engine


def calcular_hash_arquivo(file_path):
    """
    Calcula o SHA-256 do conteúdo de um arquivo.
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(8192), b""):
            sha256.update(bloco)

    return sha256.hexdigest()


def arquivo_ja_processado(pipeline_name, file_hash):
    """
    Verifica se este conteúdo já foi processado com sucesso.
    """

    query = text("""
        SELECT EXISTS (
            SELECT 1
            FROM etl.processed_file
            WHERE pipeline_name = :pipeline_name
              AND file_hash = :file_hash
              AND status IN (
                    'SUCCESS',
                    'SUCCESS_WITH_REJECTIONS'
              )
        );
    """)

    with engine.connect() as connection:
        return bool(
            connection.execute(
                query,
                {
                    "pipeline_name": pipeline_name,
                    "file_hash": file_hash
                }
            ).scalar_one()
        )


def registrar_arquivo_processado(
    pipeline_name,
    file_path,
    file_hash,
    run_id,
    status
):
    """
    Registra no manifesto um arquivo concluído com sucesso.
    """

    file_name = Path(file_path).name

    query = text("""
        INSERT INTO etl.processed_file (
            pipeline_name,
            file_name,
            file_hash,
            run_id,
            status
        )
        VALUES (
            :pipeline_name,
            :file_name,
            :file_hash,
            :run_id,
            :status
        )
        ON CONFLICT (pipeline_name, file_hash)
        DO UPDATE SET
            file_name = EXCLUDED.file_name,
            run_id = EXCLUDED.run_id,
            status = EXCLUDED.status,
            processed_at = CURRENT_TIMESTAMP;
    """)

    with engine.begin() as connection:
        connection.execute(
            query,
            {
                "pipeline_name": pipeline_name,
                "file_name": file_name,
                "file_hash": file_hash,
                "run_id": run_id,
                "status": status
            }
        )

    print(
        f"Arquivo registrado no manifesto: "
        f"{file_name}"
    )