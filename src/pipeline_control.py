from datetime import datetime

from sqlalchemy import text

from database import engine


WATERMARK_INICIAL = datetime(1900, 1, 1)


# =========================================================
# WATERMARK / ESTADO DA PIPELINE
# =========================================================

def obter_watermark(pipeline_name):
    """
    Retorna o watermark composto:

        (last_processed_at, last_processed_id)

    pipeline_control guarda o ESTADO atual da pipeline.
    """

    query = text("""
        SELECT
            last_processed_at,
            last_processed_id
        FROM etl.pipeline_control
        WHERE pipeline_name = :pipeline_name;
    """)

    with engine.connect() as connection:

        resultado = connection.execute(
            query,
            {"pipeline_name": pipeline_name}
        ).fetchone()

    if resultado is None:
        return WATERMARK_INICIAL, 0

    last_processed_at = (
        resultado[0]
        if resultado[0] is not None
        else WATERMARK_INICIAL
    )

    last_processed_id = (
        int(resultado[1])
        if resultado[1] is not None
        else 0
    )

    return last_processed_at, last_processed_id


# =========================================================
# INICIO DA EXECUCAO
# =========================================================

def iniciar_pipeline(
    pipeline_name,
    watermark_start_at,
    watermark_start_id
):
    """
    Faz duas coisas:

    1. Atualiza pipeline_control para RUNNING.
    2. Cria uma nova execucao em pipeline_run.

    Retorna run_id.
    """

    atualizar_control = text("""
        INSERT INTO etl.pipeline_control (
            pipeline_name,
            last_processed_at,
            last_processed_id,
            last_run_start,
            status,
            rows_processed,
            error_message
        )
        VALUES (
            :pipeline_name,
            :watermark_start_at,
            :watermark_start_id,
            CURRENT_TIMESTAMP,
            'RUNNING',
            0,
            NULL
        )

        ON CONFLICT (pipeline_name)
        DO UPDATE SET
            last_run_start = CURRENT_TIMESTAMP,
            last_run_end = NULL,
            status = 'RUNNING',
            rows_processed = 0,
            error_message = NULL;
    """)

    criar_run = text("""
        INSERT INTO etl.pipeline_run (
            pipeline_name,
            started_at,
            status,
            watermark_start_at,
            watermark_start_id
        )
        VALUES (
            :pipeline_name,
            CURRENT_TIMESTAMP,
            'RUNNING',
            :watermark_start_at,
            :watermark_start_id
        )
        RETURNING run_id;
    """)

    # As duas operações fazem parte
    # da mesma transação de banco.
    with engine.begin() as connection:

        connection.execute(
            atualizar_control,
            {
                "pipeline_name": pipeline_name,
                "watermark_start_at": watermark_start_at,
                "watermark_start_id": watermark_start_id
            }
        )

        run_id = connection.execute(
            criar_run,
            {
                "pipeline_name": pipeline_name,
                "watermark_start_at": watermark_start_at,
                "watermark_start_id": watermark_start_id
            }
        ).scalar_one()

    print(
        f"Pipeline '{pipeline_name}' iniciada. "
        f"run_id={run_id}"
    )

    return run_id


# =========================================================
# METRICAS DURANTE A EXECUCAO
# =========================================================

def atualizar_metricas_run(
    run_id,
    rows_extracted=None,
    rows_valid=None,
    rows_rejected=None,
    rows_loaded=None
):
    """
    Atualiza as metricas conhecidas da execucao.

    None significa:
        nao alterar aquela metrica.
    """

    campos = []
    parametros = {"run_id": run_id}

    if rows_extracted is not None:
        campos.append(
            "rows_extracted = :rows_extracted"
        )
        parametros["rows_extracted"] = rows_extracted

    if rows_valid is not None:
        campos.append(
            "rows_valid = :rows_valid"
        )
        parametros["rows_valid"] = rows_valid

    if rows_rejected is not None:
        campos.append(
            "rows_rejected = :rows_rejected"
        )
        parametros["rows_rejected"] = rows_rejected

    if rows_loaded is not None:
        campos.append(
            "rows_loaded = :rows_loaded"
        )
        parametros["rows_loaded"] = rows_loaded

    if not campos:
        return

    query = text(f"""
        UPDATE etl.pipeline_run
        SET {", ".join(campos)}
        WHERE run_id = :run_id;
    """)

    with engine.begin() as connection:
        connection.execute(
            query,
            parametros
        )


# =========================================================
# SUCCESS
# =========================================================

def finalizar_pipeline_sucesso(
    pipeline_name,
    run_id,
    watermark_end_at,
    watermark_end_id,
    rows_extracted,
    rows_valid,
    rows_rejected,
    rows_loaded
):
    """
    Finaliza a execucao e avanca o watermark.

    Se houver rejeicoes:
        SUCCESS_WITH_REJECTIONS

    Caso contrario:
        SUCCESS
    """

    status_final = (
        "SUCCESS_WITH_REJECTIONS"
        if rows_rejected > 0
        else "SUCCESS"
    )

    atualizar_control = text("""
        UPDATE etl.pipeline_control
        SET
            last_processed_at = :watermark_end_at,
            last_processed_id = :watermark_end_id,
            last_run_end = CURRENT_TIMESTAMP,
            status = :status_control,
            rows_processed = :rows_loaded,
            error_message = NULL
        WHERE pipeline_name = :pipeline_name;
    """)

    finalizar_run = text("""
        UPDATE etl.pipeline_run
        SET
            finished_at = CURRENT_TIMESTAMP,
            status = :status_run,
            rows_extracted = :rows_extracted,
            rows_valid = :rows_valid,
            rows_rejected = :rows_rejected,
            rows_loaded = :rows_loaded,
            watermark_end_at = :watermark_end_at,
            watermark_end_id = :watermark_end_id,
            error_message = NULL
        WHERE run_id = :run_id;
    """)

    # Control + histórico são atualizados
    # atomicamente.
    with engine.begin() as connection:

        connection.execute(
            atualizar_control,
            {
                "pipeline_name": pipeline_name,
                "watermark_end_at": watermark_end_at,
                "watermark_end_id": watermark_end_id,
                "status_control": status_final,
                "rows_loaded": rows_loaded
            }
        )

        connection.execute(
            finalizar_run,
            {
                "run_id": run_id,
                "status_run": status_final,
                "rows_extracted": rows_extracted,
                "rows_valid": rows_valid,
                "rows_rejected": rows_rejected,
                "rows_loaded": rows_loaded,
                "watermark_end_at": watermark_end_at,
                "watermark_end_id": watermark_end_id
            }
        )

    print(
        f"Pipeline '{pipeline_name}' finalizada. "
        f"run_id={run_id} | "
        f"status={status_final}"
    )


# =========================================================
# FAILED
# =========================================================

def finalizar_pipeline_erro(
    pipeline_name,
    run_id,
    error_message
):
    """
    Registra a falha.

    IMPORTANTE:
    o watermark NAO e alterado.
    """

    atualizar_control = text("""
        UPDATE etl.pipeline_control
        SET
            last_run_end = CURRENT_TIMESTAMP,
            status = 'FAILED',
            error_message = :error_message
        WHERE pipeline_name = :pipeline_name;
    """)

    finalizar_run = text("""
        UPDATE etl.pipeline_run
        SET
            finished_at = CURRENT_TIMESTAMP,
            status = 'FAILED',
            error_message = :error_message
        WHERE run_id = :run_id;
    """)

    with engine.begin() as connection:

        connection.execute(
            atualizar_control,
            {
                "pipeline_name": pipeline_name,
                "error_message": str(error_message)
            }
        )

        connection.execute(
            finalizar_run,
            {
                "run_id": run_id,
                "error_message": str(error_message)
            }
        )

    print(
        f"Pipeline '{pipeline_name}' falhou. "
        f"run_id={run_id}"
    )