CREATE SCHEMA IF NOT EXISTS etl;

CREATE TABLE IF NOT EXISTS etl.pipeline_control (
    pipeline_name VARCHAR(100) PRIMARY KEY,

    last_processed_id BIGINT,

    last_run_start TIMESTAMP,

    last_run_end TIMESTAMP,

    status VARCHAR(20),

    rows_processed BIGINT NOT NULL DEFAULT 0,

    error_message TEXT
);