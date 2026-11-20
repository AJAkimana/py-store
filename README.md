## D2DStore - GraphQL
D2DStore: Day to Day transaction management

### Technologies
- Language: Python 3.12 (version pinned in `.python-version`)
- Framework: Django 5.2 LTS
- API: GraphQL (graphene-django 3.2, JWT auth with django-graphql-jwt 0.4), plus a small DRF API
- Database: PostgreSQL 14 or later (Django 5.2 refuses older servers)
- Package manager: Pipenv (`Pipfile` / `Pipfile.lock`); production installs from `requirements.txt`

### Installation
#### macOS: build prerequisites
`psycopg2` is compiled from source, so it needs OpenSSL and the PostgreSQL client tools.
Put the PostgreSQL version you run first on the `PATH`, so `pg_config` (used to build `psycopg2`)
and `pg_dump` (used by `dbbackup`) match the server. A `pg_dump` older than the server refuses to run.
```bash
brew install openssl@3 postgresql@16
export PATH="$(brew --prefix postgresql@16)/bin:$PATH"
export LDFLAGS="-L$(brew --prefix openssl@3)/lib"
export CPPFLAGS="-I$(brew --prefix openssl@3)/include"
```

#### Python setup
```bash
pyenv install -s "$(cat .python-version)"   # or any Python 3.12
pipenv install --dev
cp .env.example app.env                      # then fill in the values
pipenv run migrate
pipenv run start
```

### Common commands
| Command | What it does |
|---|---|
| `pipenv run start` | Development server (production runs gunicorn, see `deploy/`) |
| `pipenv run migrate` | Apply migrations |
| `pipenv run manage test` | Run the tests |
| `pipenv run format` / `format-check` | Format with autopep8 / check formatting (settings in `pyproject.toml`) |
| `pipenv run lint` | pylint with pylint-django; fails below the `fail-under` score in `pyproject.toml` |
| `pipenv run graphql-schema` | Export the GraphQL schema to `schema.graphql` |

### Updating dependencies
1. Change versions in `Pipfile`, then run `pipenv lock` and `pipenv sync --dev`.
2. Regenerate the production file: `pipenv requirements --hash > requirements.txt`.
3. Run the tests, `pipenv run lint` and `pipenv run manage check --deploy` before deploying.
