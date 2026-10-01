import pandas as pd

def validar_clientes(df):

    print("\nValidando qualidade dos dados de clientes...")

    erros = []

    # 1. cliente_id não pode ser NULL
    if df["cliente_id"].isnull().any():
        erros.append("Existem cliente_id nulos.")

    # 2. cliente_id não pode estar duplicado
    if df["cliente_id"].duplicated().any():
        erros.append("Existem cliente_id duplicados.")

    # 3. nome não pode ser NULL
    if df["nome"].isnull().any():
        erros.append("Existem nomes nulos.")

    # 4. NIF não pode ser NULL
    if df["nif"].isnull().any():
        erros.append("Existem NIFs nulos.")

    # 5. NIF deve ser único
    if df["nif"].duplicated().any():
        erros.append("Existem NIFs duplicados.")

    # Resultado da validação
    if erros:
        print("Falha na qualidade dos dados!")

        for erro in erros:
            print(f"- {erro}")

        return False

    print("Data Quality OK!")
    return True

def validar_contas(df_contas, df_clientes):

    print("\nValidando qualidade dos dados de contas...")

    erros = []

    if df_contas["conta_id"].isnull().any():
        erros.append("Existem conta_id nulos.")

    if df_contas["conta_id"].duplicated().any():
        erros.append("Existem conta_id duplicados.")

    if df_contas["cliente_id"].isnull().any():
        erros.append("Existem cliente_id nulos nas contas.")

    if df_contas["numero_conta"].isnull().any():
        erros.append("Existem numeros de conta nulos.")

    if df_contas["numero_conta"].duplicated().any():
        erros.append("Existem numeros de conta duplicados.")

    # Integridade referencial
    clientes_validos = set(df_clientes["cliente_id"])

    clientes_inexistentes = ~df_contas["cliente_id"].isin(
        clientes_validos
    )

    if clientes_inexistentes.any():
        erros.append(
            "Existem contas associadas a clientes inexistentes."
        )

    if erros:
        print("Falha na qualidade dos dados!")

        for erro in erros:
            print(f"- {erro}")

        return False

    print("Data Quality OK!")
    return True

def validar_transacoes(df_transacoes, df_contas):

    print("\nValidando qualidade dos dados de transacoes...")

    erros = []

    # Chave da transacao
    if df_transacoes["transacao_id"].isnull().any():
        erros.append("Existem transacao_id nulos.")

    if df_transacoes["transacao_id"].duplicated().any():
        erros.append("Existem transacao_id duplicados.")

    # Conta
    if df_transacoes["conta_id"].isnull().any():
        erros.append("Existem conta_id nulos nas transacoes.")

    contas_validas = set(df_contas["conta_id"])

    contas_inexistentes = ~df_transacoes["conta_id"].isin(
        contas_validas
    )

    if contas_inexistentes.any():
        erros.append(
            "Existem transacoes associadas a contas inexistentes."
        )

    # Valor
    if df_transacoes["valor"].isnull().any():
        erros.append("Existem valores de transacao invalidos.")

    if (df_transacoes["valor"] <= 0).any():
        erros.append(
            "Existem transacoes com valor menor ou igual a zero."
        )

    # Data
    if df_transacoes["data_transacao"].isnull().any():
        erros.append(
            "Existem datas de transacao invalidas."
        )

    # Tipo da transacao
    tipos_validos = {"DEBITO", "CREDITO"}

    if not df_transacoes["tipo_transacao"].isin(
        tipos_validos
    ).all():
        erros.append(
            "Existem tipos de transacao invalidos."
        )

    # Status
    status_validos = {
        "PROCESSADA",
        "PENDENTE",
        "CANCELADA"
    }

    if not df_transacoes["status"].isin(
        status_validos
    ).all():
        erros.append(
            "Existem status de transacao invalidos."
        )

    if erros:
        print("Falha na qualidade dos dados!")

        for erro in erros:
            print(f"- {erro}")

        return False

    print("Data Quality OK!")

    return True

def classificar_transacoes(df, contas_validas):
    """
    Classifica cada transacao em:

        - valida
        - rejeitada

    Um registro rejeitado pode possuir mais de um erro.

    Retorna:
        df_validos
        df_rejeitados
    """

    df = df.copy()

    registros_validos = []
    registros_rejeitados = []

    # Conjunto de contas existentes no sistema.
    # set() torna a verificacao mais eficiente.
    contas_existentes = set(
        contas_validas["conta_id"]
        .dropna()
        .astype(int)
        .tolist()
    )

    tipos_validos = {
        "DEBITO",
        "CREDITO"
    }

    status_validos = {
        "PROCESSADA",
        "PENDENTE",
        "CANCELADA"
    }

    for _, registro in df.iterrows():

        erros_codigo = []
        erros_mensagem = []

        # =================================================
        # CONTA
        # =================================================

        if pd.isna(registro["conta_id"]):

            erros_codigo.append(
                "MISSING_ACCOUNT"
            )

            erros_mensagem.append(
                "conta_id obrigatorio"
            )

        else:

            try:
                conta_id = int(
                    registro["conta_id"]
                )

                if conta_id not in contas_existentes:

                    erros_codigo.append(
                        "ACCOUNT_NOT_FOUND"
                    )

                    erros_mensagem.append(
                        f"Conta {conta_id} nao encontrada"
                    )

            except (ValueError, TypeError):

                erros_codigo.append(
                    "INVALID_ACCOUNT"
                )

                erros_mensagem.append(
                    "conta_id invalido"
                )

        # =================================================
        # VALOR
        # =================================================

        if pd.isna(registro["valor"]):

            erros_codigo.append(
                "MISSING_AMOUNT"
            )

            erros_mensagem.append(
                "valor obrigatorio"
            )

        else:

            try:
                valor = float(
                    registro["valor"]
                )

                if valor <= 0:

                    erros_codigo.append(
                        "INVALID_AMOUNT"
                    )

                    erros_mensagem.append(
                        "valor deve ser maior que zero"
                    )

            except (ValueError, TypeError):

                erros_codigo.append(
                    "INVALID_AMOUNT"
                )

                erros_mensagem.append(
                    "valor nao numerico"
                )

        # =================================================
        # TIPO DA TRANSACAO
        # =================================================

        tipo = registro.get(
            "tipo_transacao"
        )

        if pd.isna(tipo):

            erros_codigo.append(
                "MISSING_TRANSACTION_TYPE"
            )

            erros_mensagem.append(
                "tipo_transacao obrigatorio"
            )

        elif str(tipo).strip().upper() not in tipos_validos:

            erros_codigo.append(
                "INVALID_TRANSACTION_TYPE"
            )

            erros_mensagem.append(
                f"tipo_transacao invalido: {tipo}"
            )

        # =================================================
        # STATUS
        # =================================================

        status = registro.get(
            "status"
        )

        if pd.isna(status):

            erros_codigo.append(
                "MISSING_STATUS"
            )

            erros_mensagem.append(
                "status obrigatorio"
            )

        elif str(status).strip().upper() not in status_validos:

            erros_codigo.append(
                "INVALID_STATUS"
            )

            erros_mensagem.append(
                f"status invalido: {status}"
            )

        # =================================================
        # DATA DA TRANSACAO
        # =================================================

        data_transacao = registro.get(
            "data_transacao"
        )

        if pd.isna(data_transacao):

            erros_codigo.append(
                "INVALID_TRANSACTION_DATE"
            )

            erros_mensagem.append(
                "data_transacao ausente ou invalida"
            )

        # =================================================
        # UPDATED_AT
        # =================================================

        updated_at = registro.get(
            "updated_at"
        )

        if pd.isna(updated_at):

            erros_codigo.append(
                "INVALID_UPDATED_AT"
            )

            erros_mensagem.append(
                "updated_at ausente ou invalido"
            )

        # =================================================
        # RESULTADO DO REGISTRO
        # =================================================

        registro_dict = registro.to_dict()

        if erros_codigo:

            registro_dict["error_code"] = "|".join(
                erros_codigo
            )

            registro_dict["error_message"] = " | ".join(
                erros_mensagem
            )

            registros_rejeitados.append(
                registro_dict
            )

        else:

            registros_validos.append(
                registro_dict
            )

    # =====================================================
    # DATAFRAMES RESULTANTES
    # =====================================================

    df_validos = pd.DataFrame(
        registros_validos
    )

    df_rejeitados = pd.DataFrame(
        registros_rejeitados
    )

    # =====================================================
    # INVARIANTE
    # =====================================================

    total_entrada = len(df)

    total_classificado = (
        len(df_validos)
        +
        len(df_rejeitados)
    )

    if total_entrada != total_classificado:

        raise ValueError(
            "Erro de classificacao no Data Quality. "
            f"Entrada={total_entrada}, "
            f"classificados={total_classificado}"
        )

    print(
        "\nData Quality por registro:"
    )

    print(
        f"Recebidos: {total_entrada}"
    )

    print(
        f"Validos: {len(df_validos)}"
    )

    print(
        f"Rejeitados: {len(df_rejeitados)}"
    )

    return (
        df_validos,
        df_rejeitados
    )
