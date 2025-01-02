# Project Overview

This project is a containerized application composed of multiple services orchestrated with Docker Compose. The core services include:

-   Domain Checker Service: A Python-based service to check domain availability.
-   Postgres: A relational database for storing domain-related data.

## Project Structure

```plaintext
.
├── domain_checker/ # Domain Checker service code and related files
│ ├── src/ # Source code for the domain_checker service
│ ├── tests/ # Unit tests for the domain_checker service
│ ├── Dockerfile # Dockerfile for the domain_checker service
│ └── pyproject.toml # Poetry configuration for the domain_checker
├── docker-compose.yaml # Orchestrates services
├── .env # Environment variables for services
└── README.md # Project documentation (this file)
```

### Key Files

-   domain_checker/: Contains the domain_checker service implementation.
-   docker-compose.yaml: Defines the services, networks, and volumes used by the project.
-   .env: Stores environment variables (e.g., database credentials) used in the docker-compose.yaml file.

## Prerequisites

Ensure the following are installed on your system:

-   Docker
-   Docker Compose

## Setup

### Clone the Repository:

    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

### Create the .env File:

Copy the example .env file or create a new one in the root directory:

```plaintext
DOMAIN_CHECKER_PORT=8000
DB_PORT=5432
DB_USER=admin
DB_PASSWORD=securepassword
DB_NAME=domain_checker
```

### Build Services:

Run the following command to build the domain_checker service and its dependencies:

```bash
docker-compose build
```

## Running the Application

Start the services using Docker Compose:

```bash
docker-compose up -d
```

### Access Services

-   Domain Checker: Visit http://localhost:8000 in your browser or use a tool like curl to interact with the service.

### Check Container Status

To check if the services are running:

```bash
docker ps
```

## Development Workflow

### Run Tests:

Inside the domain_checker directory, run tests with:

```bash
poetry run pytest
```

### Add New Features:

Update the source files in src/domain_checker/ and rebuild the service:

```bash
docker-compose build domain_checker
```

### Restart Services:

Apply updates by restarting services:

```bash
docker-compose up -d
```
