import pandas as pd
from sqlalchemy import text

from database import engine


def extrair_tabela(schema, tabela):
    """
    Extracao full-load de uma tabela.

    Usada atualmente para dimensoes pequenas,
    como clientes e contas.
    """

    query = f"""
        SELECT *
        FROM {schema}.{tabela};
    """

    df = pd.read_sql(
        query,
        engine
    )

    print(
        f"Tabela {schema}.{tabela} extraida: "
        f"{len(df)} linhas."
    )

    return df


def extrair_transacoes_incrementais(
    watermark_temporal,
    watermark_id
):
    """
    Extracao incremental usando watermark composto:

        (updated_at, transacao_id)

    Isso permite detectar:
        - novos registros;
        - registros antigos atualizados;
        - varios registros com o mesmo updated_at.
    """

    query = text("""
        SELECT *
        FROM banking.transacoes
        WHERE
            updated_at > :watermark_temporal

            OR (
                updated_at = :watermark_temporal
                AND transacao_id > :watermark_id
            )

        ORDER BY
            updated_at,
            transacao_id;
    """)

    df = pd.read_sql(
        query,
        engine,
        params={
            "watermark_temporal": watermark_temporal,
            "watermark_id": watermark_id
        }
    )

    print(
        "Transacoes incrementais extraidas: "
        f"{len(df)} linhas."
    )

    return df