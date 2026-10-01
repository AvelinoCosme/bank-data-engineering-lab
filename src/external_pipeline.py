import pandas as pd

from extract import extrair_tabela

from transform import transformar_transacoes

from data_quality import classificar_transacoes

from load import (
    carregar_staging,
    carregar_fact_transacao,
    carregar_quarantine_transacoes
)

from pipeline_control import (
    obter_watermark,
    iniciar_pipeline,
    atualizar_metricas_run,
    finalizar_pipeline_sucesso,
    finalizar_pipeline_erro
)

from file_control import (
    calcular_hash_arquivo,
    arquivo_ja_processado,
    registrar_arquivo_processado
)


PIPELINE_NAME = "transacoes_externas_pipeline"

CSV_PATH = "data/transacoes_externas.csv"


def executar_pipeline_externa():

    print("\n=== INICIO DA PIPELINE EXTERNA ===")

    # =========================================================
    # 1. IDENTIFICACAO DO ARQUIVO
    # =========================================================

    file_hash = calcular_hash_arquivo(
        CSV_PATH
    )

    print(f"Arquivo: {CSV_PATH}")
    print(f"SHA-256: {file_hash}")

    # =========================================================
    # 2. CONTROLE DE IDEMPOTENCIA DO ARQUIVO
    # =========================================================
    #
    # Para arquivos, o mecanismo principal de idempotencia
    # e o hash SHA-256.
    #
    # Se o mesmo conteudo ja foi processado com sucesso,
    # nao criamos um novo run e nao reprocessamos o arquivo.
    # =========================================================

    if arquivo_ja_processado(
        PIPELINE_NAME,
        file_hash
    ):

        print(
            "Arquivo ja processado com sucesso. "
            "Nenhum novo processamento necessario."
        )

        print(
            "\n=== PIPELINE EXTERNA CONCLUIDA ==="
        )

        return

    # =========================================================
    # 3. ESTADO ATUAL DA PIPELINE
    # =========================================================
    #
    # O watermark e mantido como metadado operacional.
    #
    # Para esta fonte CSV, ele nao e o mecanismo principal
    # utilizado para decidir se o arquivo deve ser processado.
    # =========================================================

    (
        watermark_start_at,
        watermark_start_id
    ) = obter_watermark(
        PIPELINE_NAME
    )

    # =========================================================
    # 4. INICIO DO RUN
    # =========================================================

    run_id = iniciar_pipeline(
        PIPELINE_NAME,
        watermark_start_at,
        watermark_start_id
    )

    try:

        # =====================================================
        # 5. EXTRACT - CSV
        # =====================================================

        print(
            f"Lendo arquivo: {CSV_PATH}"
        )

        df_transacoes = pd.read_csv(
            CSV_PATH
        )

        rows_extracted = len(
            df_transacoes
        )

        print(
            "Transacoes externas extraidas: "
            f"{rows_extracted} linhas."
        )

        atualizar_metricas_run(
            run_id,
            rows_extracted=rows_extracted
        )

        # =====================================================
        # 6. ARQUIVO VAZIO
        # =====================================================

        if df_transacoes.empty:

            finalizar_pipeline_sucesso(
                pipeline_name=PIPELINE_NAME,
                run_id=run_id,
                watermark_end_at=watermark_start_at,
                watermark_end_id=watermark_start_id,
                rows_extracted=0,
                rows_valid=0,
                rows_rejected=0,
                rows_loaded=0
            )

            registrar_arquivo_processado(
                pipeline_name=PIPELINE_NAME,
                file_path=CSV_PATH,
                file_hash=file_hash,
                run_id=run_id,
                status="SUCCESS"
            )

            print(
                "\n=== PIPELINE EXTERNA "
                "CONCLUIDA ==="
            )

            return

        # =====================================================
        # 7. STAGING
        # =====================================================

        carregar_staging(
            df_transacoes,
            "transacoes_externas"
        )

        # =====================================================
        # 8. TRANSFORM
        # =====================================================

        df_transformado = (
            transformar_transacoes(
                df_transacoes
            )
        )

        # =====================================================
        # 9. DADOS DE REFERENCIA
        # =====================================================

        df_contas = extrair_tabela(
            "banking",
            "contas"
        )

        # =====================================================
        # 10. DATA QUALITY
        # =====================================================

        (
            df_validos,
            df_rejeitados
        ) = classificar_transacoes(
            df_transformado,
            df_contas
        )

        rows_valid = len(
            df_validos
        )

        rows_rejected = len(
            df_rejeitados
        )

        # =====================================================
        # 11. INVARIANTE DE DATA QUALITY
        # =====================================================
        #
        # Tudo o que foi extraido deve terminar exatamente
        # em um dos dois grupos:
        #
        # validos OU rejeitados.
        # =====================================================

        if (
            rows_extracted
            != rows_valid + rows_rejected
        ):

            raise ValueError(
                "Invariante de Data Quality violada: "
                f"extraidos={rows_extracted}, "
                f"validos={rows_valid}, "
                f"rejeitados={rows_rejected}"
            )

        atualizar_metricas_run(
            run_id,
            rows_valid=rows_valid,
            rows_rejected=rows_rejected
        )

        # =====================================================
        # 12. QUARANTINE
        # =====================================================

        quarantine_loaded = (
            carregar_quarantine_transacoes(
                df_rejeitados,
                run_id
            )
        )

        if (
            quarantine_loaded
            != rows_rejected
        ):

            raise ValueError(
                "Quantidade enviada para quarantine "
                "diferente da quantidade rejeitada. "
                f"rejeitados={rows_rejected}, "
                f"quarantine={quarantine_loaded}"
            )

        # =====================================================
        # 13. LOAD DOS REGISTROS VALIDOS
        # =====================================================

        if df_validos.empty:

            rows_loaded = 0

            print(
                "Nenhuma transacao valida "
                "para carregar no DW."
            )

        else:

            rows_loaded = (
                carregar_fact_transacao(
                    df_validos
                )
            )

        # =====================================================
        # 14. VALIDACAO DA CARGA
        # =====================================================

        if (
            rows_loaded
            != rows_valid
        ):

            raise ValueError(
                "Quantidade carregada no DW "
                "diferente da quantidade de "
                "registros validos. "
                f"validos={rows_valid}, "
                f"carregados={rows_loaded}"
            )

        atualizar_metricas_run(
            run_id,
            rows_loaded=rows_loaded
        )

        # =====================================================
        # 15. CURSOR TECNICO DA EXECUCAO
        # =====================================================
        #
        # A idempotencia da ingestao do arquivo e controlada
        # pelo SHA-256 em etl.processed_file.
        #
        # O cursor abaixo e mantido como metadado adicional
        # da execucao.
        # =====================================================

        df_cursor = (
            df_transformado
            .sort_values(
                [
                    "updated_at",
                    "transacao_id"
                ],
                na_position="first"
            )
        )

        linhas_cursor_validas = (
            df_cursor[
                df_cursor["updated_at"].notna()
                &
                df_cursor["transacao_id"].notna()
            ]
        )

        if linhas_cursor_validas.empty:

            watermark_end_at = (
                watermark_start_at
            )

            watermark_end_id = (
                watermark_start_id
            )

        else:

            ultima_linha = (
                linhas_cursor_validas.iloc[-1]
            )

            watermark_end_at = (
                ultima_linha["updated_at"]
            )

            watermark_end_id = int(
                ultima_linha["transacao_id"]
            )

        # =====================================================
        # 16. STATUS FINAL
        # =====================================================

        status_arquivo = (
            "SUCCESS_WITH_REJECTIONS"
            if rows_rejected > 0
            else "SUCCESS"
        )

        # =====================================================
        # 17. FINALIZACAO DA PIPELINE
        # =====================================================

        finalizar_pipeline_sucesso(
            pipeline_name=PIPELINE_NAME,
            run_id=run_id,
            watermark_end_at=watermark_end_at,
            watermark_end_id=watermark_end_id,
            rows_extracted=rows_extracted,
            rows_valid=rows_valid,
            rows_rejected=rows_rejected,
            rows_loaded=rows_loaded
        )

        # =====================================================
        # 18. REGISTRO DO ARQUIVO PROCESSADO
        # =====================================================
        #
        # Somente chegamos aqui depois de a carga principal
        # ter terminado com sucesso.
        #
        # O manifesto passa a reconhecer este conteudo pelo
        # seu SHA-256.
        # =====================================================

        registrar_arquivo_processado(
            pipeline_name=PIPELINE_NAME,
            file_path=CSV_PATH,
            file_hash=file_hash,
            run_id=run_id,
            status=status_arquivo
        )

    except Exception as erro:

        # =====================================================
        # 19. FALHA
        # =====================================================
        #
        # Em caso de erro:
        #
        # - o run fica FAILED;
        # - o arquivo NAO e registrado como concluido;
        # - portanto pode ser reprocessado.
        # =====================================================

        finalizar_pipeline_erro(
            pipeline_name=PIPELINE_NAME,
            run_id=run_id,
            error_message=erro
        )

        raise

    print(
        "\n=== PIPELINE EXTERNA "
        "CONCLUIDA ==="
    )


if __name__ == "__main__":

    executar_pipeline_externa()