import pandas as pd


def transformar_clientes(df):

    print("\nIniciando transformacao de clientes...")

    # Cria uma cópia para não modificar o DataFrame original
    df = df.copy()

    # Remove espaços no início/fim dos textos
    df["nome"] = df["nome"].str.strip()
    df["provincia"] = df["provincia"].str.strip()

    # Padroniza a província
    df["provincia"] = df["provincia"].str.upper()

    # Garante que a data seja tratada como datetime
    df["data_nascimento"] = pd.to_datetime(
        df["data_nascimento"],
        errors="coerce"
    )

    print("Transformacao de clientes concluida.")

    return df

def transformar_contas(df):

    print("\nIniciando transformacao de contas...")

    df = df.copy()

    # Remove espaços
    df["numero_conta"] = df["numero_conta"].str.strip()
    df["tipo_conta"] = df["tipo_conta"].str.strip().str.upper()
    df["moeda"] = df["moeda"].str.strip().str.upper()
    df["estado"] = df["estado"].str.strip().str.upper()

    # Converte a data
    df["data_abertura"] = pd.to_datetime(
        df["data_abertura"],
        errors="coerce"
    )

    print("Transformacao de contas concluida.")

    return df

def transformar_transacoes(df):

    print("\nIniciando transformacao de transacoes...")

    df = df.copy()

    # Padronizar campos de texto
    df["tipo_transacao"] = (
        df["tipo_transacao"]
        .str.strip()
        .str.upper()
    )

    df["status"] = (
        df["status"]
        .str.strip()
        .str.upper()
    )

    # Garantir tipo numérico
    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce"
    )

    # Garantir datetime válido
    df["data_transacao"] = pd.to_datetime(
        df["data_transacao"],
        errors="coerce"
    )
    # Garantir datetime válido
    df["data_transacao"] = pd.to_datetime(
        df["data_transacao"],
        errors="coerce"
    )

    df["updated_at"] = pd.to_datetime(
        df["updated_at"],
        errors="coerce"
    )



    print("Transformacao de transacoes concluida.")

    return df

