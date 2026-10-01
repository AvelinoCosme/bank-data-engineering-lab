CREATE TABLE IF NOT EXISTS dw.dim_cliente (
    cliente_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cliente_id BIGINT NOT NULL,

    nome VARCHAR(150) NOT NULL,

    nif VARCHAR(20) NOT NULL,

    data_nascimento DATE NOT NULL,

    provincia VARCHAR(100) NOT NULL,

    ativo BOOLEAN NOT NULL,

    data_cadastro TIMESTAMP NOT NULL,

    data_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_dim_cliente_cliente_id
        UNIQUE (cliente_id)
);
CREATE TABLE IF NOT EXISTS dw.dim_conta (
    conta_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    conta_id BIGINT NOT NULL,

    cliente_id BIGINT NOT NULL,

    numero_conta VARCHAR(30) NOT NULL,

    tipo_conta VARCHAR(50) NOT NULL,

    moeda VARCHAR(10) NOT NULL,

    estado VARCHAR(20) NOT NULL,

    data_abertura DATE NOT NULL,

    data_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_dim_conta_conta_id
        UNIQUE (conta_id)
);
CREATE TABLE IF NOT EXISTS dw.dim_tempo (
    tempo_key INTEGER PRIMARY KEY,

    data DATE NOT NULL UNIQUE,

    dia INTEGER NOT NULL,

    mes INTEGER NOT NULL,

    nome_mes VARCHAR(20) NOT NULL,

    trimestre INTEGER NOT NULL,

    ano INTEGER NOT NULL,

    dia_semana INTEGER NOT NULL,

    nome_dia_semana VARCHAR(20) NOT NULL,

    fim_de_semana BOOLEAN NOT NULL
);
INSERT INTO dw.dim_tempo (
    tempo_key,
    data,
    dia,
    mes,
    nome_mes,
    trimestre,
    ano,
    dia_semana,
    nome_dia_semana,
    fim_de_semana
)
SELECT
    TO_CHAR(data_calendario, 'YYYYMMDD')::INTEGER AS tempo_key,

    data_calendario::DATE AS data,

    EXTRACT(DAY FROM data_calendario)::INTEGER AS dia,

    EXTRACT(MONTH FROM data_calendario)::INTEGER AS mes,

    CASE EXTRACT(MONTH FROM data_calendario)::INTEGER
        WHEN 1 THEN 'Janeiro'
        WHEN 2 THEN 'Fevereiro'
        WHEN 3 THEN 'Marco'
        WHEN 4 THEN 'Abril'
        WHEN 5 THEN 'Maio'
        WHEN 6 THEN 'Junho'
        WHEN 7 THEN 'Julho'
        WHEN 8 THEN 'Agosto'
        WHEN 9 THEN 'Setembro'
        WHEN 10 THEN 'Outubro'
        WHEN 11 THEN 'Novembro'
        WHEN 12 THEN 'Dezembro'
    END AS nome_mes,

    EXTRACT(QUARTER FROM data_calendario)::INTEGER AS trimestre,

    EXTRACT(YEAR FROM data_calendario)::INTEGER AS ano,

    EXTRACT(ISODOW FROM data_calendario)::INTEGER AS dia_semana,

    CASE EXTRACT(ISODOW FROM data_calendario)::INTEGER
        WHEN 1 THEN 'Segunda-feira'
        WHEN 2 THEN 'Terca-feira'
        WHEN 3 THEN 'Quarta-feira'
        WHEN 4 THEN 'Quinta-feira'
        WHEN 5 THEN 'Sexta-feira'
        WHEN 6 THEN 'Sabado'
        WHEN 7 THEN 'Domingo'
    END AS nome_dia_semana,

    CASE
        WHEN EXTRACT(ISODOW FROM data_calendario) IN (6, 7)
        THEN TRUE
        ELSE FALSE
    END AS fim_de_semana

FROM generate_series(
    '2020-01-01'::DATE,
    '2030-12-31'::DATE,
    '1 day'::INTERVAL
) AS data_calendario

ON CONFLICT (tempo_key)
DO NOTHING;
CREATE TABLE IF NOT EXISTS dw.fact_transacao (
    transacao_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transacao_id BIGINT NOT NULL,

    cliente_key BIGINT NOT NULL,

    conta_key BIGINT NOT NULL,

    tempo_key INTEGER NOT NULL,

    tipo_transacao VARCHAR(25) NOT NULL,

    valor NUMERIC(18,2) NOT NULL,

    status VARCHAR(20) NOT NULL,

    data_transacao TIMESTAMP NOT NULL,

    data_carga TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_transacao_transacao_id
        UNIQUE (transacao_id),

    CONSTRAINT fk_fact_transacao_cliente
        FOREIGN KEY (cliente_key)
        REFERENCES dw.dim_cliente(cliente_key),

    CONSTRAINT fk_fact_transacao_conta
        FOREIGN KEY (conta_key)
        REFERENCES dw.dim_conta(conta_key),

    CONSTRAINT fk_fact_transacao_tempo
        FOREIGN KEY (tempo_key)
        REFERENCES dw.dim_tempo(tempo_key)
);