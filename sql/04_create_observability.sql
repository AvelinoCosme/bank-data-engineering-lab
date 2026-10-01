CREATE SCHEMA IF NOT EXISTS etl;


-- =====================================================
-- HISTORICO DE EXECUCOES
-- =====================================================

CREATE TABLE IF NOT EXISTS etl.pipeline_run (

    run_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    pipeline_name VARCHAR(100)
        NOT NULL,

    started_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    finished_at TIMESTAMP,

    status VARCHAR(30)
        NOT NULL DEFAULT 'RUNNING',

    rows_extracted BIGINT
        NOT NULL DEFAULT 0,

    rows_valid BIGINT
        NOT NULL DEFAULT 0,

    rows_rejected BIGINT
        NOT NULL DEFAULT 0,

    rows_loaded BIGINT
        NOT NULL DEFAULT 0,

    watermark_start_at TIMESTAMP,

    watermark_start_id BIGINT,

    watermark_end_at TIMESTAMP,

    watermark_end_id BIGINT,

    error_message TEXT,

    CONSTRAINT chk_pipeline_run_status
    CHECK (
        status IN (
            'RUNNING',
            'SUCCESS',
            'SUCCESS_WITH_REJECTIONS',
            'FAILED'
        )
    )
);


-- =====================================================
-- QUARENTENA DE TRANSACOES
-- =====================================================

CREATE TABLE IF NOT EXISTS etl.quarantine_transacoes (

    quarantine_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    run_id BIGINT
        NOT NULL,

    transacao_id BIGINT,

    conta_id BIGINT,

    tipo_transacao VARCHAR(100),

    valor NUMERIC(18,2),

    descricao VARCHAR(500),

    data_transacao TIMESTAMP,

    status_original VARCHAR(100),

    updated_at TIMESTAMP,

    error_code VARCHAR(100)
        NOT NULL,

    error_message TEXT
        NOT NULL,

    quarantined_at TIMESTAMP
        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    raw_record JSONB,

    CONSTRAINT fk_quarantine_run
        FOREIGN KEY (run_id)
        REFERENCES etl.pipeline_run(run_id)
);


-- =====================================================
-- INDICES
-- =====================================================

CREATE INDEX IF NOT EXISTS
idx_pipeline_run_pipeline_started
ON etl.pipeline_run (
    pipeline_name,
    started_at DESC
);


CREATE INDEX IF NOT EXISTS
idx_quarantine_run
ON etl.quarantine_transacoes (
    run_id
);


CREATE INDEX IF NOT EXISTS
idx_quarantine_error_code
ON etl.quarantine_transacoes (
    error_code
);

-- ============================================================
-- AJUSTE DO STATUS DA PIPELINE
-- Necessário para comportar SUCCESS_WITH_REJECTIONS
-- ============================================================

ALTER TABLE etl.pipeline_control
ALTER COLUMN status TYPE VARCHAR(30);

-- ============================================================
-- CONTROLE DE ARQUIVOS PROCESSADOS
-- Evita reprocessamento do mesmo conteúdo de arquivo.
-- O SHA-256 identifica o conteúdo, independentemente do nome.
-- ============================================================

CREATE TABLE IF NOT EXISTS etl.processed_file (
    processed_file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_name VARCHAR(100) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,

    run_id BIGINT,
    status VARCHAR(30) NOT NULL,

    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_processed_file_run
        FOREIGN KEY (run_id)
        REFERENCES etl.pipeline_run(run_id),

    CONSTRAINT uq_processed_file
        UNIQUE (pipeline_name, file_hash)
);

CREATE INDEX IF NOT EXISTS idx_processed_file_pipeline
ON etl.processed_file (
    pipeline_name,
    processed_at DESC
);