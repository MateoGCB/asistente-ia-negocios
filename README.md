# Comanda — pedidos online para locales de comida

*Comanda es un nombre provisorio.*

Plataforma para que locales gastronómicos publiquen su menú, reciban pedidos online y los gestionen desde un panel. Es multi-tenant: muchos dueños conviven en la misma base y cada uno ve solo sus propios datos.

- El **dueño** se registra, crea sus sucursales y sus menús, y atiende los pedidos que llegan.
- El **cliente final** abre el enlace público de una sucursal desde el celular, elige platos y hace el pedido sin crear una cuenta.

El proyecto empezó como la base de un asistente de atención al cliente con IA para pequeños negocios. **Esa integración no está implementada**: hoy el sistema es la plataforma de menús y pedidos sobre la que se construiría.

## Qué funciona hoy

**Backend** (Python + FastAPI + SQLite, en `backend/`)

- Registro e inicio de sesión con JWT; emails validados y normalizados, reglas de contraseña.
- Sucursales con enlace público propio (`slug`), plazo de retiro configurable y archivado sin perder pedidos.
- Menús y platos (con categorías, precios exactos y platos agotados), compartibles entre sucursales.
- Pedidos públicos validados de punta a punta (el total lo calcula siempre el servidor), numerados por sucursal y sin choques aunque lleguen a la vez.
- Máquina de estados de pedidos (pendiente → confirmado → en preparación → listo → entregado, o cancelado) y cancelación automática de los pedidos listos que no se retiran a tiempo.
- Aislamiento total entre dueños: un recurso ajeno responde 404, como si no existiera.

**Panel del dueño** (React, en `frontend/`)

- Cuenta: registro con las reglas de contraseña a la vista, inicio y cierre de sesión, aviso cuando la sesión vence.
- Sucursales: crear, editar, asignar o quitar el menú, copiar el enlace público y archivar con confirmación.
- Menús: crear, borrar (con el motivo si una sucursal activa lo usa) y un editor de platos agrupados por categoría.
- Pedidos: selector de sucursal, pestañas Activos e Historial (paginado), filtro por estado y un botón por tarjeta con la acción siguiente. Los activos se actualizan solos cada 15 segundos.

**Página pública del cliente** (`/pedir/<slug>`, pensada para celular)

- Menú por categorías (los platos agotados no se muestran), carrito con límites (cantidades, cantidad de platos y total máximo), resumen con nombre, teléfono y notas, y el número de pedido final en grande.
- Si el enlace no existe, la sucursal está archivada o no tiene menú, muestra una sola pantalla: «Este local no está disponible».

## Requisitos

- Python **3.13** (evitar 3.14 por un problema de compatibilidad con SQLAlchemy).
- Node.js **20** o superior y npm.

## Cómo levantarlo

**1. Backend** (desde la raíz del repo):

```bash
python -m venv venv
source venv/Scripts/activate        # en PowerShell: venv\Scripts\Activate.ps1
cd backend
pip install -r requirements-dev.txt
cp .env.example .env                # y completá SECRET_KEY (ver abajo)
fastapi dev main.py                 # http://localhost:8000 (documentación en /docs)
```

Para generar la `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`. Sin ella el servidor no arranca, a propósito.

**2. Frontend** (en otra terminal):

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

El backend acepta por defecto pedidos del navegador desde `http://localhost:5173`, así que con los valores por defecto ya funcionan juntos. El servidor y los tests del backend se ejecutan siempre desde `backend/`.

## Tests

**Backend** (desde `backend/`, con el entorno virtual activado):

```bash
pytest                    # toda la suite
pytest -m "not slow"      # sin las pruebas de concurrencia con hilos reales
```

Cada prueba usa su propia base SQLite temporal y una clave de prueba: nunca toca la base real ni el `.env`.

**Frontend** (desde `frontend/`):

```bash
npm test                  # tests unitarios y de componentes (Vitest + Testing Library)
npm run typecheck         # TypeScript estricto
npm run lint              # ESLint
npm run build             # versión de producción en dist/
```

**De punta a punta** (desde `frontend/`): recorre registro, inicio de sesión, sucursal, menú, pedido del cliente y su avance hasta entregado, con un navegador real.

```bash
npx playwright install chromium   # solo la primera vez: descarga el navegador
npm run e2e
```

Necesita el entorno virtual del backend creado en la raíz (`venv/`) con sus dependencias instaladas. Levanta solo el backend (puerto 8011) y el frontend (puerto 5174) con una base temporal en `frontend/.e2e-tmp/`, que se borra al terminar.

## Configuración

| Variable | Dónde | Para qué |
|---|---|---|
| `SECRET_KEY` | `backend/.env` | Firma de los tokens. Obligatoria. |
| `DATABASE_URL` | `backend/.env` | Opcional. Por defecto `backend/businesses.db`, ubicada a partir de `database.py`. |
| `CORS_ORIGINS` | `backend/.env` | Opcional. Orígenes del navegador permitidos, separados por comas. Por defecto `http://localhost:5173`. Nunca acepta `*`. |
| `VITE_API_URL` | `frontend/.env` | Opcional. Dirección del backend. Por defecto `http://localhost:8000`. |

Los `.env` no se suben al repositorio (las plantillas son los `.env.example`). Una variable ya definida en el entorno tiene prioridad sobre el `.env`. Todo lo que empieza con `VITE_` termina en el código que se manda al navegador: nunca pongas secretos ahí.

## Stack

- **Backend:** FastAPI, Pydantic, SQLAlchemy (SQLite), passlib + bcrypt (contraseñas; `bcrypt<5.0.0` fijado por incompatibilidad), python-jose (JWT), python-dotenv, email-validator y pytest. Versiones fijadas en `backend/requirements.txt` y `backend/requirements-dev.txt`.
- **Frontend:** React 19, Vite, TypeScript estricto, Tailwind CSS 4, React Router, TanStack Query, React Hook Form + Zod, Lucide (iconos), Motion (animaciones puntuales), fuentes autoalojadas, Vitest + Testing Library y Playwright. Los tipos de la API se generan desde el backend con `npm run gen:api`.

## Estructura del proyecto

```
asistente-ia/
├── README.md
├── .gitignore
├── venv/                      # entorno virtual (no se sube)
├── frontend/                  # panel del dueño y página pública del cliente (React + Vite)
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


Dentro de `frontend/`:

```
frontend/
├── src/
│   ├── api/          # cliente HTTP, sesión (token), errores y tipos generados de la API
│   ├── app/          # rutas, layouts (AppShell, PublicLayout), guardias de sesión, proveedores
│   ├── components/   # Button, TextField, StatusBadge, OrderCard, MenuItemRow, CartBar, ...
│   ├── features/     # pantallas por área: auth, businesses, menus, orders, public
│   ├── lib/          # dinero en centavos, fechas, validaciones, límites, estados de pedidos
│   ├── styles/       # tokens.css (única fuente de colores, tipografía, espaciado) y base.css
│   └── config.ts     # APP_NAME (nombre provisorio) y API_URL
├── tests/            # Vitest + Testing Library
├── e2e/              # recorrido de punta a punta con Playwright
└── .env.example      # VITE_API_URL
```

## Endpoints

Documentación interactiva completa en `/docs`. Resumen:

**Autenticación**

- `POST /auth/register` · `POST /auth/login` (devuelve un JWT).
- El email se valida y se guarda en minúsculas; el login no distingue mayúsculas. El nombre va de 1 a 100 caracteres, sin espacios en los extremos.
- Contraseña (solo al registrarse): mínimo 8 caracteres, máximo 72 **bytes** en UTF-8 (límite de bcrypt: una letra con tilde ocupa 2 bytes) y al menos una letra y un número. Si no cumple, 422. El login nunca aplica estas reglas: una contraseña incorrecta siempre da el mismo 401.

**Del dueño (requieren JWT; un recurso ajeno responde 404, como si no existiera)**

- Negocios (cada negocio es una sucursal): `POST /businesses/`, `GET /businesses/`, `GET|PATCH|DELETE /businesses/{business_id}`, `DELETE /businesses/{business_id}/menu` (le quita el menú a la sucursal sin borrar el menú; repetirlo también da 200). Cada sucursal tiene un `slug` público, generado automáticamente y no editable, y un plazo de retiro configurable al crearla o editarla (`pickup_timeout_hours`, de 1 a 72 horas, por defecto 24). `name` va de 1 a 100 caracteres e `industry` de 1 a 60.
- Menús y platos: `POST|GET /menus/` (el listado trae `id`, `name` e `items_count`), `DELETE /menus/{menu_id}`, `POST|GET /menus/{menu_id}/items`, `PATCH|DELETE /menus/{menu_id}/items/{item_id}`. El nombre del menú y el del plato van de 1 a 100 caracteres y la descripción del plato de 1 a 500. Un plato se puede marcar como agotado (`available: false`); un plato que ya figura en pedidos no se puede borrar. Un menú usado por alguna sucursal activa no se puede borrar (409: primero hay que quitárselo); si solo lo usan sucursales archivadas, se borra junto con sus platos y esas sucursales quedan sin menú. Los pedidos viejos no cambian, porque guardan su copia del nombre y el precio.
- Pedidos de una sucursal:
  - `GET /businesses/{business_id}/orders?view=active` (por defecto): pedidos en curso, del más viejo al más nuevo.
  - `GET /businesses/{business_id}/orders?view=history`: entregados y cancelados, del más nuevo al más viejo, paginado (`page`, `page_size` hasta 50).
  - `GET /businesses/{business_id}/orders?status=<estado>`: filtro por un estado.
  - `GET /businesses/{business_id}/orders/{order_id}`: detalle.
  - `PATCH /businesses/{business_id}/orders/{order_id}/status`: avanza el pedido por `pending → confirmed → preparing → ready → delivered`, o lo cancela (desde cualquier estado no final).

**Públicos (sin JWT, para el cliente final)**

- `GET /public/{slug}/menu`: el menú de la sucursal, solo con los platos disponibles (los agotados no se muestran).
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

## Historia del desarrollo

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
14. **Backend listo para el frontend**: CORS configurable con `CORS_ORIGINS`, emails validados y normalizados a minúsculas, reglas de contraseña al registrarse, listado y borrado de menús (protegido si una sucursal activa lo usa) y un endpoint para quitarle el menú a una sucursal.
15. **Frontend**: panel del dueño y página pública del cliente en React, con un sistema de diseño basado en tokens, tipos generados desde la API, dinero en centavos enteros, tests unitarios y de componentes y un smoke de punta a punta con Playwright (que encontró y ayudó a corregir tres carreras entre redirecciones).

### Bugs reales resueltos en el camino

- Incompatibilidad Python 3.14 + SQLAlchemy → migración a un entorno virtual con Python 3.13.
- `declarative_base` sin paréntesis (error propio) → diagnosticado aislando el problema en una carpeta de prueba mínima, fuera del proyecto.
- Reutilización de IDs por defecto en SQLite → resuelto activando `sqlite_autoincrement`.
- `passlib` incompatible con `bcrypt>=5.0.0` (mensaje de error engañoso, sobre longitud de contraseña) → resuelto fijando `bcrypt<5.0.0`.
- Deducir el dueño de un menú a través de los negocios que lo usan permitía que otro usuario se apropiara de un menú ajeno asignándolo por PATCH → resuelto dándole a cada menú su propio `owner_id`.
- `PATCH` con `{"name": null}` dejaba el negocio roto (`exclude_unset` no excluye un `null` mandado a propósito) → resuelto con `exclude_none` y columnas `NOT NULL`.
- Numerar pedidos con `MAX + 1` fallaba con pedidos simultáneos (dos podían calcular el mismo número; los reintentos solo lo hacían menos probable) → resuelto con un contador por sucursal incrementado en un único `UPDATE ... RETURNING`.
- SQLite descarta la zona horaria al guardar fechas: una hora en UTC-3 quedaba guardada como si fuera UTC → resuelto con un tipo de columna propio que convierte a UTC antes de guardar.

## Estado y próximos pasos

Lo que todavía **no** está hecho, para que nadie se lleve una sorpresa:

- **Integración con IA:** no implementada. Era la idea original del proyecto y está en pausa.
- **Rate limiting del endpoint público de pedidos:** falta. Hoy cualquiera puede generar pedidos sin límite; es lo primero a resolver antes de publicar.
- **Token de sesión en `localStorage`:** funciona, pero un ataque XSS podría leerlo. Una alternativa más segura sería una cookie `HttpOnly`. El token dura 60 minutos y no se renueva solo.
- **Tema oscuro:** los colores ya están definidos, pero no hay un interruptor para activarlo.
- **Logo y nombre definitivos:** «Comanda» es provisorio y no hay logo.
- **Base de datos:** SQLite sin migraciones. Falta Alembic y la migración a PostgreSQL (con foreign keys reales).
- Otros pendientes: gestión de sucursales archivadas (ver, restaurar, eliminar con plazo de retención), tabla de preguntas frecuentes y WhatsApp como canal del cliente final.
