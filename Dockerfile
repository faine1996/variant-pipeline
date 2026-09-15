FROM python:3.12-slim

WORKDIR /app

# No runtime dependencies beyond the standard library (see TECHNOLOGIES.md),
# so there is no requirements.txt to install here. If one is ever added,
# it belongs here, before COPY src/, so editing source code doesn't
# invalidate Docker's cached dependency-install layer:
#   COPY requirements.txt .
#   RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/

ENV PYTHONPATH=/app/src

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

ENTRYPOINT ["python", "-m"]
CMD ["pipeline.convert"]