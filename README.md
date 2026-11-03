# Asistente de atención al cliente con IA — backend

Backend en Python (FastAPI) para un asistente de atención al cliente con IA pensado para pequeños negocios. Un negocio se conecta a esto (WhatsApp o web) y responde consultas de sus clientes usando el contexto propio de ese negocio, sin que el dueño toque código. Diseñado desde el principio con mentalidad multi-tenant: múltiples negocios y usuarios conviven en la misma base, separados solo por datos.

## Stack

Python 3.13 (evitar 3.14 por un bug de compatibilidad conocido con SQLAlchemy — ver línea de tiempo).

## Instalación

Crear y activar el entorno virtual:

```bash
python -m venv venv
source venv/Scripts/activate
```

En Windows con PowerShell, en lugar del segundo comando:

```bash
venv\Scripts\Activate.ps1
```

Instalar todas las dependencias:

```bash
pip install "fastapi[standard]"
pip install sqlalchemy
pip install "passlib[bcrypt]"
pip install "bcrypt<5.0.0"
pip install "python-jose[cryptography]"
pip install python-dotenv
```

Configurar las variables de entorno: copiar `.env.example` a `.env` y completar `SECRET_KEY` con una clave generada así:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

El `.env` está en `.gitignore` y **nunca** se sube al repo. Sin `SECRET_KEY` el servidor no arranca, a propósito.

### Para qué se usa cada librería

- **fastapi[standard]**: framework web — endpoints, validación, servidor de desarrollo.
- **pydantic** (viene con FastAPI): validación de datos que viajan por HTTP (`schemas/`).
- **sqlalchemy**: ORM — modelos de tabla (`models/`) y queries contra SQLite.
- **passlib[bcrypt]**: hashing de contraseñas.
- **bcrypt<5.0.0**: versión fijada — `passlib` es incompatible con `bcrypt>=5.0.0`.
- **python-jose[cryptography]**: generación y verificación de JWT.
- **python-dotenv**: carga las variables del archivo `.env` (por ejemplo `SECRET_KEY`).

## Levantar el servidor

```bash
fastapi dev main.py
```

Documentación interactiva: `http://127.0.0.1:8000/docs`

## Estructura del proyecto

```
asistente-ia/
├── main.py            # punto de entrada — crea la app y engancha los routers
├── database.py         # conexión a SQLite, engine, sesión, get_db()
├── security.py          # hashing de contraseñas, JWT, get_current_user
├── .env.example          # plantilla de variables de entorno (el .env real no se sube)
├── models/               # tablas reales (SQLAlchemy)
│   ├── business_models.py
│   ├── menu_models.py
│   └── user_models.py
├── schemas/                # forma de los datos que viajan por HTTP (Pydantic)
│   ├── business_schemas.py
│   ├── menu_schemas.py
│   └── user_schemas.py
├── routers/                  # endpoints — solo saben de HTTP
│   ├── business_router.py
│   ├── menu_routers.py
│   └── user_routers.py
└── services/                   # lógica real — nunca saben de HTTP
    ├── business_services.py
    ├── menu_services.py
    └── user_services.py
```

## Aislamiento entre usuarios

Para probar, registrá usuarios propios con `POST /auth/register` desde `/docs`. Cada usuario ve y administra únicamente sus propios negocios, menús e ítems: un recurso ajeno responde 404, como si no existiera.

## Línea de tiempo del desarrollo

1. **FastAPI desde cero**: primer endpoint, path parameters, query parameters, decoradores, Pydantic, documentación automática (`/docs`).
2. **CRUD completo de `/businesses/`**: create, list, get individual, update parcial (PATCH), delete. IDs generados por el servidor, nunca reutilizados. Persistencia en memoria (diccionario) como primer paso, con separación de modelo de entrada/salida (`BusinessCreate` / `Business`).
3. **Reorganización en arquitectura por capas**: `schemas/`, `routers/`, `services/`, `models/`, usando `APIRouter` e imports explícitos, inspirada en la estructura de un proyecto previo (Viandas, Node/Express/Sequelize) adaptada a Python/FastAPI.
4. **Persistencia real con SQLite + SQLAlchemy**: reemplazo del diccionario en memoria por una base real, con `Depends`/`Session`/`get_db`, y confirmación de que los datos sobreviven a un reinicio del servidor.
5. **Autenticación completa**: modelo `User`, hashing de contraseñas (passlib/bcrypt), registro (`POST /auth/register`), login con JWT (`POST /auth/login`), y protección de todos los endpoints de `businesses` exigiendo un token válido.
6. **Multi-tenant real**: cada `Business` ligado a su `User` dueño vía foreign key (`owner_id`), con todos los endpoints filtrando por dueño. Un usuario nunca puede ver, editar o borrar negocios ajenos — recibe 404, no un error que revele que existen.
7. **Menús con dueño propio**: modelos `Menu` y `MenuItem` (categorías con Enum, precios con `Decimal`/`Numeric(10, 2)` y validación de precio positivo). Cada menú tiene su propio `owner_id` sacado del token; varias sucursales de un mismo dueño pueden compartir un menú, y asignar un menú ajeno a un negocio se rechaza. Endpoints: `POST /menus/`, y crear, listar, editar y borrar ítems en `/menus/{menu_id}/items`, todos con chequeo de dueño.
8. **Endurecimiento**: `response_model` en todas las respuestas de negocios (no se expone `owner_id`), `201` en las creaciones, PATCH que ignora `null` para no dejar datos rotos, y `SECRET_KEY` fuera del código, en un `.env` que no se sube al repo.

### Bugs reales resueltos en el camino

- Incompatibilidad Python 3.14 + SQLAlchemy → migración a un entorno virtual con Python 3.13.
- `declarative_base` sin paréntesis (error propio) → diagnosticado aislando el problema en una carpeta de prueba mínima, fuera del proyecto.
- Reutilización de IDs por defecto en SQLite → resuelto activando `sqlite_autoincrement`.
- `passlib` incompatible con `bcrypt>=5.0.0` (mensaje de error engañoso, sobre longitud de contraseña) → resuelto fijando `bcrypt<5.0.0`.
- Deducir el dueño de un menú a través de los negocios que lo usan permitía que otro usuario se apropiara de un menú ajeno asignándolo por PATCH → resuelto dándole a cada menú su propio `owner_id`.
- `PATCH` con `{"name": null}` dejaba el negocio roto (`exclude_unset` no excluye un `null` mandado a propósito) → resuelto con `exclude_none` y columnas `NOT NULL`.

## Próximos pasos

- Completar el CRUD de menús: listar y borrar menús (decidiendo qué pasa con sus ítems y con los negocios que lo usan) y poder quitarle el menú a un negocio.
- Validación de emails y contraseñas al registrarse.
- Hacer cumplir las foreign keys en SQLite (`PRAGMA foreign_keys`).
- Tests automáticos con `pytest` y migraciones con Alembic.
- Tabla de preguntas frecuentes ligada a `Business`.
- Integración real con la API de Claude — el corazón del proyecto: system prompt + contexto del negocio (datos, catálogo, FAQ) + historial de conversación.
- Frontend web (React) para el panel de administración de los dueños de negocio.
- Conexión con WhatsApp como interfaz del cliente final.
