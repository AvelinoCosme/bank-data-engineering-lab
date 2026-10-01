import pandas as pd

from src.transform import (
    transformar_clientes,
    transformar_contas,
    transformar_transacoes,
)


# =========================================================
# CLIENTES
# =========================================================

def test_transformar_clientes_normaliza_texto_e_data():

    entrada = pd.DataFrame({
        "nome": ["  Maria Fernandes  "],
        "provincia": ["  luanda  "],
        "data_nascimento": ["1990-05-10"],
    })

    resultado = transformar_clientes(entrada)

    assert resultado.loc[0, "nome"] == "Maria Fernandes"
    assert resultado.loc[0, "provincia"] == "LUANDA"

    assert pd.api.types.is_datetime64_any_dtype(
        resultado["data_nascimento"]
    )


def test_transformar_clientes_data_invalida_vira_nat():

    entrada = pd.DataFrame({
        "nome": ["Maria"],
        "provincia": ["Luanda"],
        "data_nascimento": ["DATA_INVALIDA"],
    })

    resultado = transformar_clientes(entrada)

    assert pd.isna(
        resultado.loc[0, "data_nascimento"]
    )


# =========================================================
# CONTAS
# =========================================================

def test_transformar_contas_normaliza_campos():

    entrada = pd.DataFrame({
        "numero_conta": ["  000100000001  "],
        "tipo_conta": ["  corrente "],
        "moeda": [" aoa "],
        "estado": [" ativa "],
        "data_abertura": ["2026-01-15"],
    })

    resultado = transformar_contas(entrada)

    assert resultado.loc[0, "numero_conta"] == "000100000001"
    assert resultado.loc[0, "tipo_conta"] == "CORRENTE"
    assert resultado.loc[0, "moeda"] == "AOA"
    assert resultado.loc[0, "estado"] == "ATIVA"

    assert pd.api.types.is_datetime64_any_dtype(
        resultado["data_abertura"]
    )


# =========================================================
# TRANSACOES
# =========================================================

def test_transformar_transacoes_normaliza_campos():

    entrada = pd.DataFrame({
        "tipo_transacao": [" credito "],
        "status": [" processada "],
        "valor": ["1500.50"],
        "data_transacao": ["2026-09-30 10:00:00"],
        "updated_at": ["2026-09-30 10:05:00"],
    })

    resultado = transformar_transacoes(entrada)

    assert resultado.loc[0, "tipo_transacao"] == "CREDITO"
    assert resultado.loc[0, "status"] == "PROCESSADA"

    assert resultado.loc[0, "valor"] == 1500.50

    assert pd.api.types.is_numeric_dtype(
        resultado["valor"]
    )

    assert pd.api.types.is_datetime64_any_dtype(
        resultado["data_transacao"]
    )

    assert pd.api.types.is_datetime64_any_dtype(
        resultado["updated_at"]
    )


def test_valor_invalido_vira_nan():

    entrada = pd.DataFrame({
        "tipo_transacao": ["DEBITO"],
        "status": ["PROCESSADA"],
        "valor": ["VALOR_INVALIDO"],
        "data_transacao": ["2026-09-30"],
        "updated_at": ["2026-09-30"],
    })

    resultado = transformar_transacoes(entrada)

    assert pd.isna(
        resultado.loc[0, "valor"]
    )


def test_data_transacao_invalida_vira_nat():

    entrada = pd.DataFrame({
        "tipo_transacao": ["DEBITO"],
        "status": ["PROCESSADA"],
        "valor": ["1000"],
        "data_transacao": ["DATA_INVALIDA"],
        "updated_at": ["2026-09-30"],
    })

    resultado = transformar_transacoes(entrada)

    assert pd.isna(
        resultado.loc[0, "data_transacao"]
    )


def test_updated_at_invalido_vira_nat():

    entrada = pd.DataFrame({
        "tipo_transacao": ["DEBITO"],
        "status": ["PROCESSADA"],
        "valor": ["1000"],
        "data_transacao": ["2026-09-30"],
        "updated_at": ["DATA_INVALIDA"],
    })

    resultado = transformar_transacoes(entrada)

    assert pd.isna(
        resultado.loc[0, "updated_at"]
    )


# =========================================================
# IMUTABILIDADE
# =========================================================

def test_transformacao_nao_modifica_dataframe_original():

    entrada = pd.DataFrame({
        "tipo_transacao": [" credito "],
        "status": [" processada "],
        "valor": ["1000"],
        "data_transacao": ["2026-09-30"],
        "updated_at": ["2026-09-30"],
    })

    original = entrada.copy(deep=True)

    transformar_transacoes(entrada)

    pd.testing.assert_frame_equal(
        entrada,
        original
    )