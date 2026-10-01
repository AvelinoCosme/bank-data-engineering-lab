from sqlalchemy import text

from src.database import engine


def test_conexao_postgresql():

    with engine.connect() as connection:

        resultado = connection.execute(
            text("""
                SELECT
                    current_database(),
                    current_user;
            """)
        ).fetchone()

    assert resultado is not None
    assert resultado[0] == "banco_lab"
    assert resultado[1] == "banco_engineer"


def test_schemas_principais_existem():

    schemas_esperados = {
        "banking",
        "staging",
        "dw",
        "etl",
        "mart"
    }

    with engine.connect() as connection:

        resultado = connection.execute(
            text("""
                SELECT schema_name
                FROM information_schema.schemata;
            """)
        )

        schemas_existentes = {
            linha[0]
            for linha in resultado
        }

    assert schemas_esperados.issubset(
        schemas_existentes
    )


def test_fact_transacao_sem_duplicidade():

    with engine.connect() as connection:

        resultado = connection.execute(
            text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(DISTINCT transacao_id) AS distintos
                FROM dw.fact_transacao;
            """)
        ).fetchone()

    total = resultado[0]
    distintos = resultado[1]

    assert total == distintos


def test_fact_transacao_integridade_dimensional():

    with engine.connect() as connection:

        resultado = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM dw.fact_transacao f

                LEFT JOIN dw.dim_cliente c
                    ON f.cliente_key = c.cliente_key

                LEFT JOIN dw.dim_conta ct
                    ON f.conta_key = ct.conta_key

                LEFT JOIN dw.dim_tempo t
                    ON f.tempo_key = t.tempo_key

                WHERE
                    c.cliente_key IS NULL
                    OR ct.conta_key IS NULL
                    OR t.tempo_key IS NULL;
            """)
        ).scalar_one()

    assert resultado == 0


def test_dim_cliente_apenas_uma_versao_atual():

    with engine.connect() as connection:

        resultado = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM (
                    SELECT cliente_id
                    FROM dw.dim_cliente
                    WHERE atual = TRUE
                    GROUP BY cliente_id
                    HAVING COUNT(*) > 1
                ) problemas;
            """)
        ).scalar_one()

    assert resultado == 0