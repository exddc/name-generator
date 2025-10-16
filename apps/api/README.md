# API

## Getting Started

### Requirements

- **Python 3.12 or higher**
- **Poetry**: Install Poetry with: `curl -sSL https://install.python-poetry.org | python3 -`
- **Git**

### Installation

Clone the repository:

```bash
git clone https://github.com/timo-weiss/domain-generator.git
cd domain-generator/apps/api
```

Install dependencies:

```bash
poetry install
```

Run the application:

```bash
poetry run uvicorn api.main:singleton --host 0.0.0.0 --port 8000
```

API documentation is available at http://localhost:8000/docs.