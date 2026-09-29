FROM python:3.11.9-slim

WORKDIR /workspace

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

# Set up environment variables for dbt
ENV DBT_PROFILES_DIR=/workspace/dbt
ENV DBT_PROJECT_DIR=/workspace/dbt

# Install dbt packages. They go outside /workspace because the repo is
# mounted over /workspace at runtime, which would hide them.
ENV DBT_PACKAGES_DIR=/opt/dbt_packages
COPY dbt/dbt_project.yml dbt/packages.yml dbt/package-lock.yml dbt/
RUN dbt deps

# Verify tools are available
RUN python --version
RUN dbt --version

CMD ["/bin/bash"]
