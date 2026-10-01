CREATE TABLE IF NOT EXISTS banking.clientes (
    cliente_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    nif VARCHAR(20) UNIQUE NOT NULL,
    data_nascimento DATE NOT NULL,
    telefone VARCHAR(30),
    email VARCHAR(150),
    provincia VARCHAR(100) NOT NULL,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN NOT NULL DEFAULT TRUE
);
-- 2. TABELA DE CONTAS
CREATE TABLE IF NOT EXISTS banking.contas (

    conta_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cliente_id BIGINT NOT NULL,

    numero_conta VARCHAR(30) UNIQUE NOT NULL,

    tipo_conta VARCHAR(50) NOT NULL
        CHECK (tipo_conta IN ('CORRENTE', 'POUPANCA')),

    moeda VARCHAR(10) NOT NULL
        CHECK (moeda IN ('AOA', 'USD', 'EUR')),

    saldo NUMERIC(18,2) NOT NULL DEFAULT 0,

    estado VARCHAR(20) NOT NULL
        CHECK (estado IN ('ATIVA', 'BLOQUEADA', 'ENCERRADA')),

    data_abertura DATE NOT NULL DEFAULT CURRENT_DATE,

    FOREIGN KEY (cliente_id)
        REFERENCES banking.clientes(cliente_id)
);
CREATE TABLE IF NOT EXISTS banking.transacoes (

    transacao_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    conta_id BIGINT NOT NULL,

    tipo_transacao VARCHAR(25) NOT NULL
        CHECK (tipo_transacao IN ('DEBITO', 'CREDITO')),

    valor NUMERIC(18,2) NOT NULL
        CHECK (valor > 0),

    descricao VARCHAR(100),

    data_transacao TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    status VARCHAR(20) NOT NULL
        CHECK (status IN ('PROCESSADA', 'PENDENTE', 'CANCELADA')),

    FOREIGN KEY (conta_id)
        REFERENCES banking.contas(conta_id)
);

CREATE TABLE IF NOT EXISTS banking.cartoes (

    cartao_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    conta_id BIGINT NOT NULL,

    numero_cartao VARCHAR(30) UNIQUE NOT NULL,

    tipo_cartao VARCHAR(25) NOT NULL
        CHECK (tipo_cartao IN ('DEBITO', 'CREDITO')),

    bandeira VARCHAR(15) NOT NULL
        CHECK (bandeira IN ('VISA', 'MASTERCARD')),

    data_emissao DATE NOT NULL
        DEFAULT CURRENT_DATE,

    data_validade DATE NOT NULL check(data_validade>data_emissao),

    estado VARCHAR(25) NOT NULL
        CHECK (estado IN ('ATIVO', 'BLOQUEADO', 'CANCELADO')),

    limite_credito NUMERIC(18,2) NOT NULL DEFAULT 0
        CHECK (limite_credito >= 0),

    FOREIGN KEY (conta_id)
        REFERENCES banking.contas(conta_id)
);
CREATE TABLE IF NOT EXISTS banking.creditos (

    credito_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cliente_id BIGINT NOT NULL,

    tipo_credito VARCHAR(25) NOT NULL
        CHECK (tipo_credito IN ('PESSOAL', 'HABITACAO', 'AUTOMOVEL')),

    valor_credito NUMERIC(18,2) NOT NULL
        CHECK (valor_credito > 0),

    taxa_juro NUMERIC(5,2) NOT NULL
        CHECK (taxa_juro >= 0),

    prazo_meses INTEGER NOT NULL
        CHECK (prazo_meses > 0),

    data_concessao DATE NOT NULL
        DEFAULT CURRENT_DATE,

    data_vencimento DATE NOT NULL,

    estado VARCHAR(25) NOT NULL
        CHECK (estado IN ('ATIVO', 'LIQUIDADO', 'INCUMPRIMENTO')),

    FOREIGN KEY (cliente_id)
        REFERENCES banking.clientes(cliente_id),

    CHECK (data_vencimento > data_concessao)
);