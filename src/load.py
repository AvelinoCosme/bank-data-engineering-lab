from sqlalchemy import text
from database import engine
import json
import math
import pandas as pd


def carregar_staging(df, tabela):
    """
    Carrega o batch atual na camada staging.

    Nesta versao do laboratorio usamos replace
    intencionalmente: staging representa o batch
    corrente recebido pela pipeline.
    """

    df.to_sql(
        name=tabela,
        con=engine,
        schema="staging",
        if_exists="replace",
        index=False
    )

    print(
        f"staging.{tabela}: "
        f"{len(df)} linhas carregadas."
    )


# =========================================================
# DIM_CLIENTE - SCD TYPE 2
# =========================================================

def carregar_dim_cliente(df):

    buscar_atual = text("""
        SELECT
            cliente_key,
            nome,
            nif,
            data_nascimento,
            provincia,
            ativo,
            data_cadastro
        FROM dw.dim_cliente
        WHERE cliente_id = :cliente_id
          AND atual = TRUE;
    """)

    inserir_cliente = text("""
        INSERT INTO dw.dim_cliente (
            cliente_id,
            nome,
            nif,
            data_nascimento,
            provincia,
            ativo,
            data_cadastro,
            data_inicio,
            data_fim,
            atual
        )
        VALUES (
            :cliente_id,
            :nome,
            :nif,
            :data_nascimento,
            :provincia,
            :ativo,
            :data_cadastro,
            CURRENT_TIMESTAMP,
            NULL,
            TRUE
        );
    """)

    fechar_versao = text("""
        UPDATE dw.dim_cliente
        SET
            data_fim = CURRENT_TIMESTAMP,
            atual = FALSE
        WHERE cliente_key = :cliente_key;
    """)

    novos = 0
    alterados = 0
    sem_alteracao = 0

    with engine.begin() as connection:

        for _, cliente in df.iterrows():

            resultado = connection.execute(
                buscar_atual,
                {
                    "cliente_id": int(
                        cliente["cliente_id"]
                    )
                }
            )

            atual = resultado.mappings().fetchone()

            dados_novos = {
                "cliente_id": int(
                    cliente["cliente_id"]
                ),
                "nome": cliente["nome"],
                "nif": cliente["nif"],
                "data_nascimento":
                    cliente["data_nascimento"],
                "provincia":
                    cliente["provincia"],
                "ativo":
                    bool(cliente["ativo"]),
                "data_cadastro":
                    cliente["data_cadastro"]
            }

            # Primeiro aparecimento do cliente
            if atual is None:

                connection.execute(
                    inserir_cliente,
                    dados_novos
                )

                novos += 1
                continue

            data_nascimento_nova = (
                cliente["data_nascimento"].date()
                if hasattr(
                    cliente["data_nascimento"],
                    "date"
                )
                else cliente["data_nascimento"]
            )

            mudou = (
                atual["nome"] != cliente["nome"]
                or atual["nif"] != cliente["nif"]
                or atual["data_nascimento"]
                != data_nascimento_nova
                or atual["provincia"]
                != cliente["provincia"]
                or atual["ativo"]
                != bool(cliente["ativo"])
            )

            if mudou:

                connection.execute(
                    fechar_versao,
                    {
                        "cliente_key":
                            atual["cliente_key"]
                    }
                )

                connection.execute(
                    inserir_cliente,
                    dados_novos
                )

                alterados += 1

            else:

                sem_alteracao += 1

    print(
        "dw.dim_cliente SCD2: "
        f"{novos} novos, "
        f"{alterados} alterados, "
        f"{sem_alteracao} sem alteracao."
    )


# =========================================================
# DIM_CONTA
# =========================================================

def carregar_dim_conta(df):

    query = text("""
        INSERT INTO dw.dim_conta (
            conta_id,
            cliente_id,
            numero_conta,
            tipo_conta,
            moeda,
            estado,
            data_abertura
        )
        VALUES (
            :conta_id,
            :cliente_id,
            :numero_conta,
            :tipo_conta,
            :moeda,
            :estado,
            :data_abertura
        )

        ON CONFLICT (conta_id)

        DO UPDATE SET
            cliente_id = EXCLUDED.cliente_id,
            numero_conta = EXCLUDED.numero_conta,
            tipo_conta = EXCLUDED.tipo_conta,
            moeda = EXCLUDED.moeda,
            estado = EXCLUDED.estado,
            data_abertura = EXCLUDED.data_abertura;
    """)

    registros = df[
        [
            "conta_id",
            "cliente_id",
            "numero_conta",
            "tipo_conta",
            "moeda",
            "estado",
            "data_abertura"
        ]
    ].to_dict(
        orient="records"
    )

    with engine.begin() as connection:

        connection.execute(
            query,
            registros
        )

    print(
        f"dw.dim_conta: "
        f"{len(registros)} registros processados."
    )


# =========================================================
# VALIDACAO DO LOOKUP TEMPORAL
# =========================================================

def validar_lookup_transacoes(df):
    """
    Cada transacao precisa encontrar exatamente:

        1 conta
        1 versao temporal do cliente
        1 data em dim_tempo

    Qualquer valor diferente de 1 interrompe a pipeline.
    """

    query = text("""
        SELECT
            COUNT(*) AS quantidade
        FROM dw.dim_conta dco

        INNER JOIN dw.dim_cliente dc
            ON dc.cliente_id = dco.cliente_id
           AND dc.data_inicio <= :data_transacao
           AND (
                dc.data_fim > :data_transacao
                OR dc.data_fim IS NULL
           )

        INNER JOIN dw.dim_tempo dt
            ON dt.data =
               CAST(:data_transacao AS DATE)

        WHERE dco.conta_id = :conta_id;
    """)

    erros = []

    with engine.connect() as connection:

        for _, transacao in df.iterrows():

            resultado = connection.execute(
                query,
                {
                    "conta_id":
                        int(transacao["conta_id"]),
                    "data_transacao":
                        transacao["data_transacao"]
                }
            ).scalar_one()

            if resultado != 1:

                erros.append(
                    {
                        "transacao_id":
                            int(
                                transacao[
                                    "transacao_id"
                                ]
                            ),
                        "matches":
                            int(resultado)
                    }
                )

    if erros:

        detalhes = ", ".join(
            [
                (
                    f"transacao_id="
                    f"{erro['transacao_id']} "
                    f"(matches={erro['matches']})"
                )
                for erro in erros
            ]
        )

        raise ValueError(
            "Lookup dimensional invalido. "
            "Cada transacao deve encontrar "
            "exatamente uma combinacao "
            "dimensional. "
            f"Problemas: {detalhes}"
        )

    print(
        "Lookup temporal validado: "
        f"{len(df)} transacoes OK."
    )


# =========================================================
# FACT_TRANSACAO
# =========================================================

def carregar_fact_transacao(df):

    # Antes de carregar qualquer coisa,
    # validamos todos os lookups.
    validar_lookup_transacoes(df)

    query = text("""
        INSERT INTO dw.fact_transacao (
            transacao_id,
            cliente_key,
            conta_key,
            tempo_key,
            tipo_transacao,
            valor,
            status,
            data_transacao
        )

        SELECT
            :transacao_id,
            dc.cliente_key,
            dco.conta_key,
            dt.tempo_key,
            :tipo_transacao,
            :valor,
            :status,
            :data_transacao

        FROM dw.dim_conta dco

        INNER JOIN dw.dim_cliente dc
            ON dc.cliente_id = dco.cliente_id
           AND dc.data_inicio <= :data_transacao
           AND (
                dc.data_fim > :data_transacao
                OR dc.data_fim IS NULL
           )

        INNER JOIN dw.dim_tempo dt
            ON dt.data =
               CAST(:data_transacao AS DATE)

        WHERE dco.conta_id = :conta_id

        ON CONFLICT (transacao_id)

        DO UPDATE SET
            cliente_key =
                EXCLUDED.cliente_key,
            conta_key =
                EXCLUDED.conta_key,
            tempo_key =
                EXCLUDED.tempo_key,
            tipo_transacao =
                EXCLUDED.tipo_transacao,
            valor =
                EXCLUDED.valor,
            status =
                EXCLUDED.status,
            data_transacao =
                EXCLUDED.data_transacao;
    """)

    registros = df[
        [
            "transacao_id",
            "conta_id",
            "tipo_transacao",
            "valor",
            "status",
            "data_transacao"
        ]
    ].to_dict(
        orient="records"
    )

    carregados = 0

    with engine.begin() as connection:

        for registro in registros:

            resultado = connection.execute(
                query,
                registro
            )

            carregados += resultado.rowcount

    if carregados != len(registros):

        raise ValueError(
            "Quantidade carregada na fact "
            "diferente da quantidade esperada. "
            f"Esperado={len(registros)}, "
            f"carregado={carregados}."
        )

    print(
        "dw.fact_transacao: "
        f"{carregados} registros "
        "efetivamente carregados."
    )

    return carregados
def preparar_valor_json(valor):
    """
    Converte tipos Pandas/NumPy/Python para valores
    que possam ser serializados com segurança em JSON.
    """

    if valor is None:
        return None

    # NaN, NaT e outros valores nulos do Pandas
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    # Datas Pandas/Python
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()

    # Tipos NumPy geralmente possuem .item()
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except (ValueError, TypeError):
            pass

    # float NaN/Infinity não devem ir para JSON
    if isinstance(valor, float):
        if math.isnan(valor) or math.isinf(valor):
            return None

    return valor


def carregar_quarantine_transacoes(
    df_rejeitados,
    run_id
):
    """
    Persiste registros rejeitados pelo Data Quality.

    Cada registro fica associado ao run_id responsável
    pela rejeição e mantém uma cópia do registro recebido
    em raw_record (JSONB).
    """

    if df_rejeitados.empty:

        print(
            "Quarantine: nenhum registro rejeitado."
        )

        return 0

    query = text("""
        INSERT INTO etl.quarantine_transacoes (
            run_id,
            transacao_id,
            conta_id,
            tipo_transacao,
            valor,
            descricao,
            data_transacao,
            status_original,
            updated_at,
            error_code,
            error_message,
            raw_record
        )
        VALUES (
            :run_id,
            :transacao_id,
            :conta_id,
            :tipo_transacao,
            :valor,
            :descricao,
            :data_transacao,
            :status_original,
            :updated_at,
            :error_code,
            :error_message,
            CAST(:raw_record AS JSONB)
        );
    """)

    registros = []

    for _, linha in df_rejeitados.iterrows():

        # ---------------------------------------------
        # RAW RECORD
        # ---------------------------------------------

        raw_dict = {}

        for coluna, valor in linha.items():

            # error_code e error_message são metadados
            # de DQ e não fazem parte do registro original.
            if coluna in {
                "error_code",
                "error_message"
            }:
                continue

            raw_dict[coluna] = preparar_valor_json(
                valor
            )

        raw_record = json.dumps(
            raw_dict,
            ensure_ascii=False,
            allow_nan=False
        )

        # ---------------------------------------------
        # CAMPOS ESTRUTURADOS
        # ---------------------------------------------

        transacao_id = preparar_valor_json(
            linha.get("transacao_id")
        )

        conta_id = preparar_valor_json(
            linha.get("conta_id")
        )

        valor = preparar_valor_json(
            linha.get("valor")
        )

        data_transacao = preparar_valor_json(
            linha.get("data_transacao")
        )

        updated_at = preparar_valor_json(
            linha.get("updated_at")
        )

        registros.append({
            "run_id": int(run_id),

            "transacao_id": (
                int(transacao_id)
                if transacao_id is not None
                else None
            ),

            "conta_id": (
                int(conta_id)
                if conta_id is not None
                else None
            ),

            "tipo_transacao": preparar_valor_json(
                linha.get("tipo_transacao")
            ),

            "valor": valor,

            "descricao": preparar_valor_json(
                linha.get("descricao")
            ),

            "data_transacao": data_transacao,

            "status_original": preparar_valor_json(
                linha.get("status")
            ),

            "updated_at": updated_at,

            "error_code": str(
                linha["error_code"]
            ),

            "error_message": str(
                linha["error_message"]
            ),

            "raw_record": raw_record
        })

    # ---------------------------------------------
    # CARGA
    # ---------------------------------------------

    with engine.begin() as connection:

        resultado = connection.execute(
            query,
            registros
        )

        carregados = resultado.rowcount

    if carregados != len(registros):

        raise ValueError(
            "Quantidade carregada na quarantine "
            "diferente da quantidade esperada. "
            f"Esperado={len(registros)}, "
            f"carregado={carregados}."
        )

    print(
        "etl.quarantine_transacoes: "
        f"{carregados} registros rejeitados carregados."
    )

    return carregados