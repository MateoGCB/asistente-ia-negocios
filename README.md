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
```

### Para qué se usa cada librería

- **fastapi[standard]**: framework web — endpoints, validación, servidor de desarrollo.
- **pydantic** (viene con FastAPI): validación de datos que viajan por HTTP (`schemas/`).
- **sqlalchemy**: ORM — modelos de tabla (`models/`) y queries contra SQLite.
- **passlib[bcrypt]**: hashing de contraseñas.
- **bcrypt<5.0.0**: versión fijada — `passlib` es incompatible con `bcrypt>=5.0.0`.
- **python-jose[cryptography]**: generación y verificación de JWT.

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
├── models/               # tablas reales (SQLAlchemy)
│   ├── business_models.py
│   └── user_models.py
├── schemas/                # forma de los datos que viajan por HTTP (Pydantic)
│   ├── business_schemas.py
│   └── user_schemas.py
├── routers/                  # endpoints — solo saben de HTTP
│   ├── business_router.py
│   └── user_router.py
└── services/                   # lógica real — nunca saben de HTTP
    ├── business_services.py
    └── user_services.py
```

## Usuarios de prueba

| Nombre | Email | Contraseña |
| ------ | ----- | ---------- |
| Mateo  | Mail  | 123        |
| Bruno  | Mail1 | 1234       |

Cada uno ve y administra únicamente sus propios negocios (`GET /businesses/` filtra por dueño).

## Línea de tiempo del desarrollo

1. **FastAPI desde cero**: primer endpoint, path parameters, query parameters, decoradores, Pydantic, documentación automática (`/docs`).
2. **CRUD completo de `/businesses/`**: create, list, get individual, update parcial (PATCH), delete. IDs generados por el servidor, nunca reutilizados. Persistencia en memoria (diccionario) como primer paso, con separación de modelo de entrada/salida (`BusinessCreate` / `Business`).
3. **Reorganización en arquitectura por capas**: `schemas/`, `routers/`, `services/`, `models/`, usando `APIRouter` e imports explícitos, inspirada en la estructura de un proyecto previo (Viandas, Node/Express/Sequelize) adaptada a Python/FastAPI.
4. **Persistencia real con SQLite + SQLAlchemy**: reemplazo del diccionario en memoria por una base real, con `Depends`/`Session`/`get_db`, y confirmación de que los datos sobreviven a un reinicio del servidor.
5. **Autenticación completa**: modelo `User`, hashing de contraseñas (passlib/bcrypt), registro (`POST /auth/register`), login con JWT (`POST /auth/login`), y protección de todos los endpoints de `businesses` exigiendo un token válido.
6. **Multi-tenant real**: cada `Business` ligado a su `User` dueño vía foreign key (`owner_id`), con todos los endpoints filtrando por dueño. Un usuario nunca puede ver, editar o borrar negocios ajenos — recibe 404, no un error que revele que existen.

### Bugs reales resueltos en el camino

- Incompatibilidad Python 3.14 + SQLAlchemy → migración a un entorno virtual con Python 3.13.
- `declarative_base` sin paréntesis (error propio) → diagnosticado aislando el problema en una carpeta de prueba mínima, fuera del proyecto.
- Reutilización de IDs por defecto en SQLite → resuelto activando `sqlite_autoincrement`.
- `passlib` incompatible con `bcrypt>=5.0.0` (mensaje de error engañoso, sobre longitud de contraseña) → resuelto fijando `bcrypt<5.0.0`.

## Próximos pasos

- Integración real con la API de Claude — el corazón del proyecto: system prompt + contexto del negocio (datos, catálogo, FAQ) + historial de conversación.
- Tablas adicionales ligadas a `Business` (menú, preguntas frecuentes), con el mismo patrón de foreign key usado para `User`.
- Frontend web (React) para el panel de administración de los dueños de negocio.
- Conexión con WhatsApp como interfaz del cliente final.
