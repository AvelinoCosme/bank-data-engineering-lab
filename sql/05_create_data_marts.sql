CREATE SCHEMA IF NOT EXISTS mart;


CREATE OR REPLACE VIEW mart.vw_transacoes_detalhadas AS
SELECT
    -- Identificação da transação
    f.transacao_id,

    -- Cliente
    c.cliente_id,
    c.nome AS cliente_nome,
    c.provincia,
    c.ativo AS cliente_ativo,

    -- Conta
    ct.conta_id,
    ct.tipo_conta,
    ct.moeda,
    ct.estado AS conta_estado,

    -- Transação
    f.tipo_transacao,
    f.valor,
    f.status AS transacao_status,
    f.data_transacao,

    -- Dimensão temporal
    t.data,
    t.dia,
    t.mes,
    t.nome_mes,
    t.trimestre,
    t.ano,
    t.dia_semana,
    t.nome_dia_semana,
    t.fim_de_semana

FROM dw.fact_transacao f

INNER JOIN dw.dim_cliente c
    ON f.cliente_key = c.cliente_key

INNER JOIN dw.dim_conta ct
    ON f.conta_key = ct.conta_key

INNER JOIN dw.dim_tempo t
    ON f.tempo_key = t.tempo_key;

DROP MATERIALIZED VIEW IF EXISTS mart.mv_resumo_transacoes_diarias;

CREATE MATERIALIZED VIEW mart.mv_resumo_transacoes_diarias AS
SELECT
    data,
    ano,
    mes,
    nome_mes,
    trimestre,

    COUNT(*) AS quantidade_transacoes,

    SUM(valor) AS volume_total,

    COALESCE(
    SUM(valor) FILTER (
        WHERE tipo_transacao = 'CREDITO'
    ),
    0
    ) AS volume_credito,

    COALESCE(
    SUM(valor) FILTER (
        WHERE tipo_transacao = 'DEBITO'
    ),
    0
    ) AS volume_debito,

    COUNT(*) FILTER (
        WHERE tipo_transacao = 'CREDITO'
    ) AS quantidade_creditos,

    COUNT(*) FILTER (
        WHERE tipo_transacao = 'DEBITO'
    ) AS quantidade_debitos,

    COUNT(*) FILTER (
        WHERE transacao_status = 'PROCESSADA'
    ) AS quantidade_processadas,

    COUNT(*) FILTER (
        WHERE transacao_status = 'PENDENTE'
    ) AS quantidade_pendentes,

    COUNT(*) FILTER (
        WHERE transacao_status = 'CANCELADA'
    ) AS quantidade_canceladas,

    AVG(valor) AS valor_medio

FROM mart.vw_transacoes_detalhadas

GROUP BY
    data,
    ano,
    mes,
    nome_mes,
    trimestre;

CREATE UNIQUE INDEX idx_mv_resumo_transacoes_diarias_data
ON mart.mv_resumo_transacoes_diarias (data); 

DROP MATERIALIZED VIEW IF EXISTS mart.mv_resumo_provincias;

CREATE MATERIALIZED VIEW mart.mv_resumo_provincias AS
SELECT
    provincia,

    COUNT(DISTINCT cliente_id) AS quantidade_clientes,
    COUNT(*) AS quantidade_transacoes,

    COALESCE(
        SUM(valor) FILTER (
            WHERE tipo_transacao = 'CREDITO'
        ),
        0
    ) AS volume_credito,

    COALESCE(
        SUM(valor) FILTER (
            WHERE tipo_transacao = 'DEBITO'
        ),
        0
    ) AS volume_debito,

    SUM(valor) AS volume_movimentado,

    AVG(valor) AS valor_medio_transacao

FROM mart.vw_transacoes_detalhadas

GROUP BY provincia;
CREATE UNIQUE INDEX idx_mv_resumo_provincias_provincia
ON mart.mv_resumo_provincias (provincia);