FROM python:3.11.9-slim

WORKDIR /workspace

# Install system dependencies for duckdb CLI and other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY dlt/airtable_pipeline/requirements.txt dlt/airtable_pipeline/requirements.txt
COPY dbt/requirements.txt dbt/requirements.txt

# Install dlt and dbt dependencies with pinned versions
RUN pip install --no-cache-dir \
    dlt[duckdb]==1.30.0 \
    requests==2.31.0 \
    dbt-duckdb==1.8.0 \
    dbt-core==1.8.0 \
    duckdb==1.0.0

# Set up environment variables for dbt
ENV DBT_PROFILES_DIR=/workspace/dbt
ENV DBT_PROJECT_DIR=/workspace/dbt

# Verify tools are available
RUN python --version && dbt --version && which duckdb

CMD ["/bin/bash"]
