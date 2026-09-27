FROM python:3.11.9-slim

WORKDIR /workspace

# Install system dependencies for duckdb CLI and other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and install duckdb CLI binary
RUN mkdir ~/.local && \
	mkdir ~/.local/bin && \
	curl https://install.duckdb.org | bash

# Copy and install Python dependencies
COPY dlt/airtable_pipeline/requirements.txt dlt/airtable_pipeline/requirements.txt
COPY dbt/requirements.txt dbt/requirements.txt

# Install requirements files first (includes dlt[duckdb])
RUN pip install --no-cache-dir -r dlt/airtable_pipeline/requirements.txt
RUN pip install --no-cache-dir -r dbt/requirements.txt

# Install additional dependencies
RUN pip install --no-cache-dir \
    requests==2.31.0 \
    dbt-duckdb==1.8.0 \
    dbt-core==1.8.0

# Set up environment variables for dbt and duckdb
ENV DBT_PROFILES_DIR=/workspace/dbt
ENV DBT_PROJECT_DIR=/workspace/dbt
ENV PATH=/root/.local/bin:$PATH

# Verify tools are available
RUN python --version
RUN dbt --version
RUN duckdb --version

CMD ["/bin/bash"]
