import pandas as pd

from src.data_quality import classificar_transacoes


def criar_contas_validas():
    """Contas existentes usadas nos testes."""
    return pd.DataFrame({
        "conta_id": [1, 6]
    })


def criar_transacao_valida():
    """Cria uma transacao valida que pode ser alterada em cada teste."""
    return {
        "transacao_id": 100,
        "conta_id": 1,
        "tipo_transacao": "DEBITO",
        "valor": 1000.00,
        "status": "PROCESSADA",
        "data_transacao": pd.Timestamp("2026-09-30 10:00:00"),
        "updated_at": pd.Timestamp("2026-09-30 10:05:00"),
    }


def test_transacao_valida():
    df = pd.DataFrame([criar_transacao_valida()])
    contas = criar_contas_validas()

    validos, rejeitados = classificar_transacoes(df, contas)

    assert len(validos) == 1
    assert len(rejeitados) == 0


def test_valor_negativo_deve_ser_rejeitado():
    transacao = criar_transacao_valida()
    transacao["valor"] = -100

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1
    assert "INVALID_AMOUNT" in rejeitados.iloc[0]["error_code"]


def test_conta_inexistente_deve_ser_rejeitada():
    transacao = criar_transacao_valida()
    transacao["conta_id"] = 999999

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1
    assert "ACCOUNT_NOT_FOUND" in rejeitados.iloc[0]["error_code"]


def test_tipo_transacao_invalido_deve_ser_rejeitado():
    transacao = criar_transacao_valida()
    transacao["tipo_transacao"] = "TRANSFERENCIA_INVALIDA"

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1
    assert (
        "INVALID_TRANSACTION_TYPE"
        in rejeitados.iloc[0]["error_code"]
    )


def test_status_invalido_deve_ser_rejeitado():
    transacao = criar_transacao_valida()
    transacao["status"] = "DESCONHECIDO"

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1
    assert "INVALID_STATUS" in rejeitados.iloc[0]["error_code"]


def test_data_transacao_invalida_deve_ser_rejeitada():
    transacao = criar_transacao_valida()
    transacao["data_transacao"] = pd.NaT

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1
    assert (
        "INVALID_TRANSACTION_DATE"
        in rejeitados.iloc[0]["error_code"]
    )


def test_updated_at_invalido_deve_ser_rejeitado():
    transacao = criar_transacao_valida()
    transacao["updated_at"] = pd.NaT

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1
    assert "INVALID_UPDATED_AT" in rejeitados.iloc[0]["error_code"]


def test_multiplos_erros_no_mesmo_registro():
    transacao = criar_transacao_valida()

    transacao["conta_id"] = 999999
    transacao["valor"] = -100
    transacao["status"] = "INVALIDO"

    df = pd.DataFrame([transacao])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(validos) == 0
    assert len(rejeitados) == 1

    erros = rejeitados.iloc[0]["error_code"]

    assert "ACCOUNT_NOT_FOUND" in erros
    assert "INVALID_AMOUNT" in erros
    assert "INVALID_STATUS" in erros


def test_invariante_total_entrada_igual_total_classificado():
    transacao_valida = criar_transacao_valida()

    transacao_invalida = criar_transacao_valida()
    transacao_invalida["transacao_id"] = 101
    transacao_invalida["valor"] = -500

    df = pd.DataFrame([
        transacao_valida,
        transacao_invalida
    ])

    validos, rejeitados = classificar_transacoes(
        df,
        criar_contas_validas()
    )

    assert len(df) == len(validos) + len(rejeitados)
    assert len(validos) == 1
    assert len(rejeitados) == 1