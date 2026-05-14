-- Sample seed for the jobs table (used for offline demos).
-- Run automatically by `python -m utils.seed_db` if no jobs exist.

INSERT INTO jobs (source, external_id, company, title, location, remote, salary_min, salary_max,
                  salary_currency, description, apply_url, posted_at, fetched_at, visa_sponsorship, tags)
VALUES
('demo', 'demo-1', 'Acme AI', 'Senior Data Engineer',
 'San Francisco, CA', 1, 160000, 210000, 'USD',
 'Build large-scale data pipelines in Python and SQL. Snowflake, Airflow, dbt.',
 'https://example.com/jobs/acme-1', datetime('now', '-2 hours'),
 datetime('now'), 1, 'python,sql,airflow,dbt,snowflake'),

('demo', 'demo-2', 'Nimbus Cloud', 'Backend Engineer (Python)',
 'Remote — USA', 1, 140000, 180000, 'USD',
 'FastAPI, PostgreSQL, AWS. Ship features end-to-end on the API team.',
 'https://example.com/jobs/nimbus-1', datetime('now', '-6 hours'),
 datetime('now'), 0, 'python,fastapi,aws,postgres'),

('demo', 'demo-3', 'Lumen Health', 'ML Engineer — NLP',
 'New York, NY', 0, 170000, 220000, 'USD',
 'Build NLP models for clinical text. PyTorch, transformers, MLOps.',
 'https://example.com/jobs/lumen-1', datetime('now', '-12 hours'),
 datetime('now'), 1, 'python,pytorch,nlp,mlops');
