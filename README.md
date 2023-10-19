## D2DStore - GraphQL
D2DStore: Day to Day transaction management
### Technologies
- Language: Python 3.8(Django)
- API: GraphQL
- Database: Postgres
- Package manager: Pipenv
### Installation
#### For MAC, Set up SSL path env variables
```bash
export PATH="/usr/local/Cellar/openssl@3/3.1.3/bin:$PATH"
export LDFLAGS="-L/usr/local/Cellar/openssl@3/3.1.3/lib"
export CPPFLAGS="-I/usr/local/Cellar/openssl@3/3.1.3/include"
export PKG_CONFIG_PATH="/usr/local/Cellar/openssl@3/3.1.3/lib/pkgconfig"
```
#### Python Setup
```bash
export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=true
export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=true
```

