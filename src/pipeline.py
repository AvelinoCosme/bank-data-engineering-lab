from extract import (
    extrair_tabela,
    extrair_transacoes_incrementais
)

from pipeline_control import (
    obter_watermark,
    iniciar_pipeline,
    atualizar_metricas_run,
    finalizar_pipeline_sucesso,
    finalizar_pipeline_erro
)

from load import (
    carregar_staging,
    carregar_dim_cliente,
    carregar_dim_conta,
    carregar_fact_transacao
)

from transform import (
    transformar_clientes,
    transformar_contas,
    transformar_transacoes
)

from data_quality import (
    validar_clientes,
    validar_contas,
    validar_transacoes
)


def executar_pipeline():

    print("=== INICIO DA PIPELINE ===")

    # =====================================================
    # CLIENTES
    # =====================================================

    df_clientes = extrair_tabela(
        "banking",
        "clientes"
    )

    carregar_staging(
        df_clientes,
        "clientes"
    )

    df_clientes_transformado = transformar_clientes(
        df_clientes
    )

    qualidade_clientes_ok = validar_clientes(
        df_clientes_transformado
    )

    if not qualidade_clientes_ok:
        raise ValueError(
            "Falha na qualidade dos dados de clientes."
        )

    carregar_dim_cliente(
        df_clientes_transformado
    )

    # =====================================================
    # CONTAS
    # =====================================================

    df_contas = extrair_tabela(
        "banking",
        "contas"
    )

    carregar_staging(
        df_contas,
        "contas"
    )

    df_contas_transformado = transformar_contas(
        df_contas
    )

    qualidade_contas_ok = validar_contas(
        df_contas_transformado,
        df_clientes_transformado
    )

    if not qualidade_contas_ok:
        raise ValueError(
            "Falha na qualidade dos dados de contas."
        )

    carregar_dim_conta(
        df_contas_transformado
    )

    # =====================================================
    # TRANSACOES
    # =====================================================

    pipeline_name = "transacoes_pipeline"

    (
        watermark_temporal,
        watermark_id
    ) = obter_watermark(
        pipeline_name
    )

    print("\nWatermark atual:")
    print(
        f"updated_at = {watermark_temporal}"
    )
    print(
        f"transacao_id = {watermark_id}"
    )

    # -----------------------------------------------------
    # CRIA A EXECUCAO
    # -----------------------------------------------------

    run_id = iniciar_pipeline(
        pipeline_name,
        watermark_temporal,
        watermark_id
    )

    try:

        # =================================================
        # EXTRACT
        # =================================================

        df_transacoes = extrair_transacoes_incrementais(
            watermark_temporal,
            watermark_id
        )

        rows_extracted = len(
            df_transacoes
        )

        atualizar_metricas_run(
            run_id,
            rows_extracted=rows_extracted
        )

        # =================================================
        # ZERO REGISTROS
        # =================================================

        if df_transacoes.empty:

            print(
                "Nenhuma transacao nova "
                "ou alterada encontrada."
            )

            finalizar_pipeline_sucesso(
                pipeline_name=pipeline_name,
                run_id=run_id,
                watermark_end_at=watermark_temporal,
                watermark_end_id=watermark_id,
                rows_extracted=0,
                rows_valid=0,
                rows_rejected=0,
                rows_loaded=0
            )

            print(
                "\n=== PIPELINE "
                "CONCLUIDA COM SUCESSO ==="
            )

            return

        # =================================================
        # STAGING
        # =================================================

        carregar_staging(
            df_transacoes,
            "transacoes"
        )

        # =================================================
        # TRANSFORM
        # =================================================

        df_transacoes_transformado = (
            transformar_transacoes(
                df_transacoes
            )
        )

        # =================================================
        # DATA QUALITY
        # =================================================

        qualidade_transacoes_ok = validar_transacoes(
            df_transacoes_transformado,
            df_contas_transformado
        )

        if not qualidade_transacoes_ok:

            raise ValueError(
                "Falha na qualidade "
                "dos dados de transacoes."
            )

        # Nesta etapa, todos os registros
        # que passaram no DQ sao validos.
        rows_valid = len(
            df_transacoes_transformado
        )

        rows_rejected = 0

        atualizar_metricas_run(
            run_id,
            rows_valid=rows_valid,
            rows_rejected=rows_rejected
        )

        # =================================================
        # LOAD
        # =================================================

        rows_loaded = carregar_fact_transacao(
            df_transacoes_transformado
        )

        atualizar_metricas_run(
            run_id,
            rows_loaded=rows_loaded
        )

        # =================================================
        # NOVO WATERMARK
        # =================================================

        ultima_linha = (
            df_transacoes_transformado
            .iloc[-1]
        )

        novo_watermark_temporal = (
            ultima_linha["updated_at"]
        )

        novo_watermark_id = int(
            ultima_linha["transacao_id"]
        )

        # =================================================
        # FINALIZACAO
        # =================================================

        finalizar_pipeline_sucesso(
            pipeline_name=pipeline_name,
            run_id=run_id,
            watermark_end_at=novo_watermark_temporal,
            watermark_end_id=novo_watermark_id,
            rows_extracted=rows_extracted,
            rows_valid=rows_valid,
            rows_rejected=rows_rejected,
            rows_loaded=rows_loaded
        )

    except Exception as erro:

        finalizar_pipeline_erro(
            pipeline_name=pipeline_name,
            run_id=run_id,
            error_message=erro
        )

        raise

    print(
        "\n=== PIPELINE "
        "CONCLUIDA COM SUCESSO ==="
    )


if __name__ == "__main__":
    executar_pipeline()