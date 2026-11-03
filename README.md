# Asistente de atención al cliente con IA — backend

Backend en Python (FastAPI) para un asistente de atención al cliente con IA pensado para pequeños negocios. Un negocio se conecta a esto (WhatsApp o web) y responde consultas de sus clientes usando el contexto propio de ese negocio, sin que el dueño toque código. Diseñado desde el principio con mentalidad multi-tenant: múltiples negocios y usuarios conviven en la misma base, separados solo por datos.

## Stack

Python 3.13 (evitar 3.14 por un bug de compatibilidad conocido con SQLAlchemy — ver línea de tiempo).

## Instalación

El repositorio tiene el backend en `backend/`; el frontend (React) está pendiente y va a vivir en `frontend/`. El entorno virtual `venv/` se crea en la raíz del repo; **el servidor y los tests se ejecutan siempre desde `backend/`**.

Crear y activar el entorno virtual (desde la raíz del repo):

```bash
python -m venv venv
source venv/Scripts/activate
```

En Windows con PowerShell, en lugar del segundo comando:

```bash
venv\Scripts\Activate.ps1
```

Entrar al backend e instalar las dependencias (las versiones están fijadas en `requirements.txt`; `requirements-dev.txt` agrega `pytest`):

```bash
cd backend
pip install -r requirements-dev.txt
```

Para producción alcanza con `pip install -r requirements.txt`.

Configurar las variables de entorno (dentro de `backend/`): copiar `.env.example` a `.env` y completar `SECRET_KEY` con una clave generada así:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

El `.env` está en `.gitignore` y **nunca** se sube al repo. Sin `SECRET_KEY` el servidor no arranca, a propósito. Opcionalmente, `DATABASE_URL` cambia la base; por defecto es `backend/businesses.db`, ubicada a partir de `database.py` (no depende de la carpeta desde donde se lance el servidor). Una variable ya definida en el entorno tiene prioridad sobre el `.env`.

### Para qué se usa cada librería

- **fastapi[standard]**: framework web — endpoints, validación, servidor de desarrollo.
- **pydantic** (viene con FastAPI): validación de datos que viajan por HTTP (`schemas/`).
- **sqlalchemy**: ORM — modelos de tabla (`models/`) y queries contra SQLite.
- **passlib[bcrypt]**: hashing de contraseñas.
- **bcrypt<5.0.0**: versión fijada — `passlib` es incompatible con `bcrypt>=5.0.0`.
- **python-jose[cryptography]**: generación y verificación de JWT.
- **python-dotenv**: carga las variables del archivo `.env` (por ejemplo `SECRET_KEY`).
- **pytest** (solo desarrollo): la suite de tests.

## Levantar el servidor

Desde `backend/`, con el entorno virtual activado:

```bash
cd backend
fastapi dev main.py
```

Documentación interactiva: `http://127.0.0.1:8000/docs`

## Tests

Desde `backend/`, con las dependencias de desarrollo instaladas:

```bash
cd backend
pytest
```

Saltear las pruebas lentas (concurrencia con hilos reales): `pytest -m "not slow"`.

Los tests no usan el `.env` ni el `businesses.db` reales: cada prueba trabaja sobre su propia copia de una base SQLite temporal y usa una `SECRET_KEY` de prueba. Todos los datos de prueba son ficticios. La suite cubre autenticación, negocios, slugs, archivado, menús, menú público, creación de pedidos, estados, cancelación automática, concurrencia y fechas (`backend/tests/test_<tema>.py`; las fixtures compartidas están en `backend/tests/conftest.py`).

## Estructura del proyecto

```
asistente-ia/
├── README.md
├── .gitignore
├── venv/                      # entorno virtual (no se sube)
├── frontend/                  # PENDIENTE: panel web en React (todavía no existe)
└── backend/                   # todo el backend; servidor y tests se ejecutan desde acá
    ├── main.py                # punto de entrada — crea la app y engancha los routers
    ├── database.py            # conexión a SQLite, engine, sesión, get_db()
    ├── security.py            # hashing de contraseñas, JWT, get_current_user
    ├── .env.example           # plantilla de variables de entorno (el .env real no se sube)
    ├── requirements.txt       # dependencias de la app (versiones fijadas)
    ├── requirements-dev.txt   # + herramientas de desarrollo (pytest)
    ├── pytest.ini             # configuración de la suite (carpeta, marcador slow)
    ├── models/                # tablas reales (SQLAlchemy)
    │   ├── business_models.py
    │   ├── custom_types.py      # UTCDateTime: fechas siempre en UTC
    │   ├── menu_models.py
    │   ├── order_models.py
    │   └── user_models.py
    ├── schemas/               # forma de los datos que viajan por HTTP (Pydantic)
    │   ├── business_schemas.py
    │   ├── common_schemas.py
    │   ├── menu_schemas.py
    │   ├── order_schemas.py
    │   ├── public_schemas.py
    │   └── user_schemas.py
    ├── routers/               # endpoints — solo saben de HTTP
    │   ├── business_router.py
    │   ├── menu_routers.py
    │   ├── order_routers.py     # pedidos, lado del dueño (JWT)
    │   ├── public_routers.py    # menú y pedidos, lado del cliente (sin JWT)
    │   └── user_routers.py
    ├── services/              # lógica real — nunca saben de HTTP
    │   ├── business_services.py
    │   ├── menu_services.py
    │   ├── order_services.py
    │   ├── public_services.py
    │   └── user_services.py
    ├── utils/
    │   └── datetime_utils.py    # utc_now() y to_utc()
    └── tests/                 # suite de pytest (conftest.py + test_<tema>.py)
```

## Endpoints

Documentación interactiva completa en `/docs`. Resumen:

**Autenticación**

- `POST /auth/register` · `POST /auth/login` (devuelve un JWT).

**Del dueño (requieren JWT; un recurso ajeno responde 404, como si no existiera)**

- Negocios (cada negocio es una sucursal): `POST /businesses/`, `GET /businesses/`, `GET|PATCH|DELETE /businesses/{business_id}`. Cada sucursal tiene un `slug` público, generado automáticamente y no editable, y un plazo de retiro configurable al crearla o editarla (`pickup_timeout_hours`, de 1 a 72 horas, por defecto 24). `name` va de 1 a 100 caracteres e `industry` de 1 a 60.
- Menús y platos: `POST /menus/`, `POST|GET /menus/{menu_id}/items`, `PATCH|DELETE /menus/{menu_id}/items/{item_id}`. El nombre del menú y el del plato van de 1 a 100 caracteres y la descripción del plato de 1 a 500. Un plato se puede marcar como agotado (`available: false`); un plato que ya figura en pedidos no se puede borrar.
- Pedidos de una sucursal:
  - `GET /businesses/{business_id}/orders?view=active` (por defecto): pedidos en curso, del más viejo al más nuevo.
  - `GET /businesses/{business_id}/orders?view=history`: entregados y cancelados, del más nuevo al más viejo, paginado (`page`, `page_size` hasta 50).
  - `GET /businesses/{business_id}/orders?status=<estado>`: filtro por un estado.
  - `GET /businesses/{business_id}/orders/{order_id}`: detalle.
  - `PATCH /businesses/{business_id}/orders/{order_id}/status`: avanza el pedido por `pending → confirmed → preparing → ready → delivered`, o lo cancela (desde cualquier estado no final).

**Públicos (sin JWT, para el cliente final)**

- `GET /public/{slug}/menu`: el menú de la sucursal, solo con los platos disponibles.
- `POST /public/{slug}/orders`: crea un pedido. El total lo calcula siempre el servidor con los precios actuales; cada pedido guarda una copia del nombre y el precio de cada plato. El teléfono lleva entre 6 y 15 dígitos (puede tener `+` al comienzo, espacios y guiones, pero no dos espacios ni dos guiones seguidos).

## Reglas de negocio destacadas

- **Número de pedido por sucursal** (#1, #2…): sale de un contador por sucursal que se incrementa de forma atómica, así dos pedidos simultáneos nunca reciben el mismo número ni dejan huecos.
- **Cambios de estado atómicos**: si dos personas cambian el mismo pedido a la vez, una gana y la otra recibe 409 ("el pedido cambió, recargá").
- **Cancelación automática por no retiro**: un pedido listo que no se retira dentro del plazo de la sucursal pasa a cancelado (`not_picked_up`). Se evalúa al consultar, sin tareas programadas.
- **Archivado de negocios (borrado lógico)**: `DELETE /businesses/{id}` no elimina la fila, la archiva. Un negocio archivado se comporta como inexistente en toda la API (incluido su menú público), pero sus pedidos se conservan y su slug nunca se reutiliza.
- **Fechas**: todas se guardan y se devuelven en UTC.
- **Textos**: se recortan los espacios de los bordes antes de validar el largo, así que un campo obligatorio vacío o de solo espacios da 422.
- **Regla de `null`**: en un campo opcional con valor por defecto, `null` significa "no lo mandé": al crear se usa el valor por defecto (por ejemplo, `pickup_timeout_hours: null` da 24) y en un `PATCH` se ignora. Un campo obligatorio con `null` da 422.

## Aislamiento entre usuarios

Para probar, registrá usuarios propios con `POST /auth/register` desde `/docs`. Cada usuario ve y administra únicamente sus propios negocios, menús, platos y pedidos: un recurso ajeno responde 404, como si no existiera.

## Línea de tiempo del desarrollo

1. **FastAPI desde cero**: primer endpoint, path parameters, query parameters, decoradores, Pydantic, documentación automática (`/docs`).
2. **CRUD completo de `/businesses/`**: create, list, get individual, update parcial (PATCH), delete. IDs generados por el servidor, nunca reutilizados. Persistencia en memoria (diccionario) como primer paso, con separación de modelo de entrada/salida (`BusinessCreate` / `Business`).
3. **Reorganización en arquitectura por capas**: `schemas/`, `routers/`, `services/`, `models/`, usando `APIRouter` e imports explícitos, inspirada en la estructura de un proyecto previo (Viandas, Node/Express/Sequelize) adaptada a Python/FastAPI.
4. **Persistencia real con SQLite + SQLAlchemy**: reemplazo del diccionario en memoria por una base real, con `Depends`/`Session`/`get_db`, y confirmación de que los datos sobreviven a un reinicio del servidor.
5. **Autenticación completa**: modelo `User`, hashing de contraseñas (passlib/bcrypt), registro (`POST /auth/register`), login con JWT (`POST /auth/login`), y protección de todos los endpoints de `businesses` exigiendo un token válido.
6. **Multi-tenant real**: cada `Business` ligado a su `User` dueño vía foreign key (`owner_id`), con todos los endpoints filtrando por dueño. Un usuario nunca puede ver, editar o borrar negocios ajenos — recibe 404, no un error que revele que existen.
7. **Menús con dueño propio**: modelos `Menu` y `MenuItem` (categorías con Enum, precios con `Decimal`/`Numeric(10, 2)` y validación de precio positivo). Cada menú tiene su propio `owner_id` sacado del token; varias sucursales de un mismo dueño pueden compartir un menú, y asignar un menú ajeno a un negocio se rechaza. Endpoints: `POST /menus/`, y crear, listar, editar y borrar ítems en `/menus/{menu_id}/items`, todos con chequeo de dueño.
8. **Endurecimiento**: `response_model` en todas las respuestas de negocios (no se expone `owner_id`), `201` en las creaciones, PATCH que ignora `null` para no dejar datos rotos, y `SECRET_KEY` fuera del código, en un `.env` que no se sube al repo.
9. **Menú público y pedidos del cliente final**: cada sucursal tiene un `slug` público; el cliente ve el menú sin registrarse y hace pedidos que validan platos, disponibilidad, cantidades y datos de contacto. El pedido se crea completo o no se crea (una sola transacción), con un número visible por sucursal.
10. **Gestión de pedidos del dueño**: listados de activos e historial paginado, detalle y una máquina de estados con transiciones validadas; cancelación automática de pedidos listos no retirados, según el plazo de cada sucursal.
11. **Robustez y cierre**: contador atómico de números de pedido (probado con pedidos simultáneos reales), cambios de estado atómicos con `UPDATE` condicional, un tipo de columna propio para que todas las fechas queden en UTC, y archivado de negocios (borrado lógico) con slugs que nunca se reutilizan.
12. **Suite de tests con pytest**: más de 300 pruebas versionadas, cada una con su propia base temporal (nunca la real), que cubren todo lo anterior, incluidas carreras con hilos reales. Al armarla se agregaron validaciones de largo en negocios, menús y platos, el plazo de retiro al crear, límites de dígitos en el teléfono y dependencias fijadas en `requirements.txt`.
13. **Un solo repositorio para backend y frontend**: el backend se mudó a `backend/` (con `git mv`, conservando el historial) para preparar el frontend, y la ruta por defecto de la base pasó a armarse a partir de `database.py`, para no crear bases vacías según la carpeta desde donde se lance el servidor.

### Bugs reales resueltos en el camino

- Incompatibilidad Python 3.14 + SQLAlchemy → migración a un entorno virtual con Python 3.13.
- `declarative_base` sin paréntesis (error propio) → diagnosticado aislando el problema en una carpeta de prueba mínima, fuera del proyecto.
- Reutilización de IDs por defecto en SQLite → resuelto activando `sqlite_autoincrement`.
- `passlib` incompatible con `bcrypt>=5.0.0` (mensaje de error engañoso, sobre longitud de contraseña) → resuelto fijando `bcrypt<5.0.0`.
- Deducir el dueño de un menú a través de los negocios que lo usan permitía que otro usuario se apropiara de un menú ajeno asignándolo por PATCH → resuelto dándole a cada menú su propio `owner_id`.
- `PATCH` con `{"name": null}` dejaba el negocio roto (`exclude_unset` no excluye un `null` mandado a propósito) → resuelto con `exclude_none` y columnas `NOT NULL`.
- Numerar pedidos con `MAX + 1` fallaba con pedidos simultáneos (dos podían calcular el mismo número; los reintentos solo lo hacían menos probable) → resuelto con un contador por sucursal incrementado en un único `UPDATE ... RETURNING`.
- SQLite descarta la zona horaria al guardar fechas: una hora en UTC-3 quedaba guardada como si fuera UTC → resuelto con un tipo de columna propio que convierte a UTC antes de guardar.

## Próximos pasos

- Rate limiting en el endpoint público de pedidos (antes de publicar).
- Gestión de negocios archivados: ver, restaurar y, eventualmente, eliminar con un plazo de retención.
- Completar el CRUD de menús: listar y borrar menús (decidiendo qué pasa con sus ítems y con los negocios que lo usan) y poder quitarle el menú a un negocio.
- Validación de emails y contraseñas al registrarse.
- Hacer cumplir las foreign keys en SQLite (`PRAGMA foreign_keys`).
- Migraciones con Alembic.
- Migración a PostgreSQL.
- Tabla de preguntas frecuentes ligada a `Business`.
- Integración con un asistente de IA (en pausa).
- Frontend web (React) para el panel de administración de los dueños de negocio.
- Conexión con WhatsApp como interfaz del cliente final.
