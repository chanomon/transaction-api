# Transaction Execution API

El servicio no administra saldos, solo valida las reglas de negocio de entrada, ejecuta la transacción contra un proveedor externo (mockeado con WireMock) y persiste el resultado que ese proveedor retorna.

## Stack técnico

| Aspecto | Elección | Por qué |
|---|---|---|
| Lenguaje / framework | Python 3.11 + FastAPI | Porque es el lenguaje que mas uso. FastAPI tiene capacidad de alto rendimiento y puede manejar muchas peticiones. de DB externas. Buen soporte de dependencias, facil de trabajar. |
| Persistencia | PostgreSQL (vía SQLAlchemy ORM, driver `psycopg2`, sesiones síncronas) | Es un dominio transaccional (transacciones financieras)un tipo `NUMERIC` exacto para montos (no float). Para el volumen esperado. Es el DB que mas he usado. |
| Proveedor externo | WireMock (`docker-compose`), cliente HTTP con `httpx` | Permite mockear el proveedor con escenarios configurables (éxito, fondos insuficientes, error 5xx). El más recomendado y básico que encontre. |
| Resiliencia hacia el proveedor | `tenacity` (reintentos con backoff exponencial) | Reintenta automáticamente ante timeouts o errores de conexión (no ante errores de negocio 4xx/5xx del proveedor, que se consideran respuestas válidas y se persisten tal cual). |
| Contenerización | Docker + docker-compose (`app`, `postgres`, `wiremock`) | Un solo comando levanta todo el sistema de punta a punta, reproducible en cualquier máquina. |


## Estructura del proyecto

```
app/
  api/transactions/       # Endpoints (capa HTTP)
  services/                # Lógica de orquestación (reglas de negocio + llamada al proveedor)
  repositories/             # Acceso a datos (SQLAlchemy)
  clients/                  # Cliente HTTP hacia el proveedor externo
  models/
    schemas.py               # Modelos Pydantic (request/response)
    db_models.py              # Modelo ORM (tabla transactions)
  core/
    config.py                 # Configuración (variables de entorno)
    database.py                # Engine, sesión y creación de tablas
tests/
  unit/                     # Tests unitarios (validaciones de negocio)
  integration/               # Tests de integración (ver nota en "Testing")
wiremock/mappings/         # Escenarios mockeados del proveedor externo
docker-compose.yml
Dockerfile
documentacion.txt          # Bitácora de bugs encontrados y solucionados
```

La separación en capas (API → Service → Repository/Client) busca que la lógica de negocio no dependa directamente de SQLAlchemy ni de `httpx`: el `TransactionService` no sabe si la persistencia es Postgres o el proveedor es WireMock, solo conoce las interfaces de `TransactionRepository` y `ProviderClient`.

## Autenticación

Todos los endpoints bajo `/api/v1/transactions` (`POST` y `GET`) requieren una API key estática enviada en el header `X-API-Key`. Se implementa como una dependencia de FastAPI (`app/core/security.py`) enganchada a nivel de router, así que no hay forma de llegar a los endpoints de transacciones sin el header correcto: sin key o con una key incorrecta, la API responde `401 Unauthorized`.

El endpoint `GET /health` se deja intencionalmente **sin** autenticación: es el que consultaría un load balancer o un orquestador (healthcheck de Docker, probes de Kubernetes) para saber si el proceso sigue vivo, y esos sistemas no tienen forma de conocer la API key — protegerlo tumbaría el servicio por falsos positivos de "unhealthy".

La comparación de la key contra el valor esperado usa `secrets.compare_digest()` en vez de `==`: es una comparación de tiempo constante, para que un atacante no pueda inferir la key midiendo cuánto tarda la respuesta ante distintos intentos (timing attack). El valor real vive en `.env` (no versionado) y se inyecta a la app vía `docker-compose.yml`.

**Nota de alcance:** esta es una autenticación básica servicio-a-servicio, apropiada para el tamaño de este challenge. En un entorno productivo con múltiples clientes/roles, lo natural sería evolucionar a JWT (rotación de credenciales sin reiniciar el servicio, expiración, scopes por cliente); no se implementó aquí para no sobre-ingenierizar dado el alcance y tiempo disponibles.

### Protección contra SQL injection

Tanto el `POST` como el `GET` construyen sus queries con el lenguaje de expresiones de SQLAlchemy (`select(...).where(Transaction.account_id == filters["accountId"])` en `TransactionRepository.list_transactions`, y asignación de atributos ORM en `create`), nunca con concatenación de strings. Esto hace que cualquier valor de entrada se envíe como parámetro vinculado (bound parameter) a la base de datos, no como texto SQL interpretable.

Se probó explícitamente enviando un payload de inyección como filtro:
```bash
curl -G "http://localhost:8000/api/v1/transactions/" \
  --data-urlencode "accountId=x'; DROP TABLE transactions; --" \
  -H "X-API-Key: <tu-api-key>" \
  -w "\nHTTP %{http_code}\n"
```
El payload se compara como un valor literal de `account_id` (que no existe), sin ejecutar ningún SQL adicional — la tabla y los datos existentes no se ven afectados.

## Endurecimiento de contenedores

Docker por sí solo no es una capa de seguridad (aislamiento ≠ control de acceso); por defecto un contenedor corre como root y puede exponer más de lo necesario al host. Se aplicaron dos ajustes sobre la configuración inicial:

**1. Usuario no-root con grupo dedicado (`Dockerfile`).** La imagen ya no corre `uvicorn` como `root`. Se crea un grupo `appgroup` con el mismo GID que el grupo del usuario del host dueño del código (para que los permisos de lectura/ejecución del volumen montado (`./app:/app`) apliquen correctamente sin necesidad de compartir un UID específico), y un usuario `appuser` cuyo grupo primario es ese `appgroup`. La app se ejecuta con `USER appuser` a partir de ese punto — si el proceso de la app fuera comprometido, el atacante no obtiene privilegios de root dentro del contenedor.

**2. Puertos internos sin exponer al host (`docker-compose.yml`).** `postgres` (`5432`) y `wiremock` (`8080`) ya no publican su puerto al host: solo son alcanzables dentro de la red interna `transaction-network`, desde el contenedor `app`. Antes, cualquiera con acceso a la máquina podía conectarse directo a Postgres o a WireMock sin pasar por la API ni por el `X-API-Key`, lo cual anulaba cualquier control de acceso a nivel de aplicación. Solo `app` (puerto `8000`) sigue expuesto al host, que es el único punto de entrada que debe existir.

## Cómo levantar el proyecto

Requisitos: Docker y Docker Compose.

**1. Configurar variables de entorno.** El proyecto necesita un archivo `.env` en la raíz (no versionado en git). Copia el template y ajusta los valores:
```bash
cp .env.example .env
```
Genera un valor para `API_KEY` (por ejemplo con `openssl rand -hex 32`) y pégalo en `.env` — sin este archivo, la app falla al arrancar porque `API_KEY` no tiene valor por default, y `docker-compose.yml` tampoco puede resolver `POSTGRES_USER`/`DATABASE_URL`/etc.

**2. Ajustar el GID del contenedor al de tu usuario en el host.** El `Dockerfile` crea un usuario no-root (`appuser`) cuyo grupo (`appgroup`) debe tener el mismo GID que el dueño del código en tu máquina, para que el contenedor pueda leer/ejecutar el volumen montado `./app:/app` (ver [Endurecimiento de contenedores](#endurecimiento-de-contenedores)).

Obtén tu GID:
```bash
id -g $USER
```
Reemplaza el valor en la línea `RUN groupadd -g <GID> appgroup` del `Dockerfile` con ese número (por defecto trae `1000`, que es el GID típico del primer usuario en muchas distros, pero conviene confirmarlo en vez de asumirlo).

Asegúrate también de que `./app` en el host pertenezca a ese mismo grupo:
```bash
ls -ld app
```
Si el grupo mostrado no coincide con el GID que vas a usar en el `Dockerfile`, ajústalo:
```bash
chgrp -R $(id -gn $USER) app
```

**3. Levantar los servicios:**
```bash
docker compose up -d --build
```

Esto levanta 3 servicios:
- `app` — la API, en `http://localhost:8000` (docs interactivas en `http://localhost:8000/docs`)
- `postgres` — base de datos (solo accesible dentro de la red interna de Docker, no expuesta al host)
- `wiremock` — proveedor externo mockeado (solo accesible dentro de la red interna de Docker, no expuesto al host)

Las tablas se crean automáticamente al arrancar la app (no se usan migraciones de Alembic por simplicidad; para un entorno productivo real se recomendaría migrar a Alembic).

### Probar los endpoints

**Health check (no requiere `X-API-Key`):**
```bash
curl http://localhost:8000/health -w "\nHTTP %{http_code}\n"
```

Todos los endpoints bajo `/api/v1/transactions` requieren el header `X-API-Key` (ver sección [Autenticación](#autenticación)).

**Crear una transacción:**
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <tu-api-key>" \
  -d '{
    "accountId": "acc-success",
    "type": "CREDIT",
    "amount": 1500.00,
    "currency": "MXN",
    "description": "Transferencia recibida"
  }' \
  -w "\nHTTP %{http_code}\n"
```

**Consultar transacciones (con filtros y paginación):**

Cada respuesta es un arreglo JSON; se pipea a `jq -c '.[]'` para que cada transacción se imprima en su propia línea (requiere tener `jq` instalado):
```bash
# todas las transacciones (paginadas, default page=1, limit=20)
curl -s "http://localhost:8000/api/v1/transactions/" -H "X-API-Key: <tu-api-key>" | jq -c '.[]'

# filtrando por cuenta
curl -s "http://localhost:8000/api/v1/transactions/?accountId=acc-success" -H "X-API-Key: <tu-api-key>" | jq -c '.[]'

# filtrando por status
curl -s "http://localhost:8000/api/v1/transactions/?status=APPROVED" -H "X-API-Key: <tu-api-key>" | jq -c '.[]'

# filtrando por type
curl -s "http://localhost:8000/api/v1/transactions/?type=CREDIT" -H "X-API-Key: <tu-api-key>" | jq -c '.[]'

# combinando filtros + paginación
curl -s "http://localhost:8000/api/v1/transactions/?accountId=acc-success&status=APPROVED&type=CREDIT&page=1&limit=5" -H "X-API-Key: <tu-api-key>" | jq -c '.[]'
```

El mock del proveedor (`wiremock/mappings/`) responde distinto según el `accountId` enviado, para poder probar los distintos escenarios sin tocar código. Los dos casos especiales tienen prioridad; **cualquier otro `accountId` (incluyendo `acc-success`, que ya no es un caso especial) cae en la respuesta genérica de éxito**:
- `acc-fail` → fondos insuficientes (`REJECTED` / `INSUFFICIENT_FUNDS`)
- `acc-500` → error 500 del proveedor (la app lo captura y persiste como `REJECTED` / `PROVIDER_UNAVAILABLE`, sin caerse)
- cualquier otro `accountId` → aprobado (`APPROVED`), respuesta genérica de éxito

**Proveedor totalmente inalcanzable (contenedor `wiremock` caído, timeout o conexión rechazada):** este caso se distingue de los dos anteriores. En `acc-fail`/`acc-500` el proveedor sí respondió (con un rechazo de negocio o con su propio error), así que hay una transacción real que persistir como `201 Created` + `REJECTED`. Si el proveedor nunca responde, no hubo ninguna evaluación de la transacción, así que la API no la reporta como si el proveedor la hubiera rechazado: persiste el intento como `REJECTED` / `PROVIDER_UNREACHABLE` para no perder rastro de auditoría, pero responde `503 Service Unavailable` en vez de `201`, dejando claro que la petición no pudo completarse por una falla de infraestructura, no por una decisión de negocio.

Ejemplo de `201` + `REJECTED` (el proveedor sí respondió, con su propio error):
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <tu-api-key>" \
  -d '{
    "accountId": "acc-500",
    "type": "CREDIT",
    "amount": 1500.00,
    "currency": "MXN",
    "description": "Transferencia recibida"
  }' \
  -w "\nHTTP %{http_code}\n"
```

Ejemplo de `503` (proveedor totalmente inalcanzable, primero se tumba `wiremock`):
```bash
docker compose stop wiremock

curl -X POST http://localhost:8000/api/v1/transactions/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <tu-api-key>" \
  -d '{
    "accountId": "acc-123456",
    "type": "CREDIT",
    "amount": 1500.00,
    "currency": "MXN",
    "description": "Transferencia recibida"
  }' \
  -w "\nHTTP %{http_code}\n"

docker compose start wiremock
```

## Reglas de negocio implementadas

Validadas en el servicio **antes** de llamar al proveedor externo (`app/models/schemas.py` y `app/services/transaction_service.py`):

1. Monto estrictamente mayor a $1.00 (`amount > 1.00`).
2. Transacciones `DEBIT` no pueden exceder $10,000.00; `CREDIT` no tiene límite.
3. Solo se acepta la moneda `MXN`.

Si alguna falla, la API responde `422 Unprocessable Entity` con el detalle del error, sin llegar a contactar al proveedor.

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit -v
```

- **Tests unitarios** (`tests/unit/`): cubren las validaciones de negocio del modelo `TransactionRequest` (monto mínimo, límite de débito, tipo válido). Corren sin necesidad de Docker ni base de datos.
- **Tests de integración** (`tests/integration/`): existen pero están en pausa en este momento (no son parte de la entrega priorizada); ejercitan los endpoints reales contra los servicios de `docker-compose`. Quedan como trabajo pendiente de estabilizar.

## Uso de Inteligencia Artificial

Se usó Claude (Anthropic) como asistente durante el desarrollo, principalmente para:
- Debugging de un bug de arquitectura: el proyecto mezclaba código asíncrono (SQLAlchemy `AsyncSession`, driver `asyncpg`, `httpx.AsyncClient`) con partes síncronas, lo que causaba fallos de conexión a la base de datos y respuestas incorrectas en los endpoints. Claude ayudó a diagnosticar la causa raíz (inspección de logs del contenedor, comparación de drivers) y a migrar el stack completo a un modelo síncrono consistente.
- Detección de un bug puntual en el endpoint `GET /transactions`: una validación de query params (`status`, `type`) construía una excepción pero nunca la lanzaba (`raise` faltante), lo que dejaba pasar valores inválidos hasta la base de datos y producía un `500` en vez de un `400` controlado.
- Redacción de este README y de `documentacion.txt` (bitácora de cambios).

Todo el código fue revisado, entendido y ajustado por mí; puedo explicar el razonamiento detrás de cada decisión de diseño listada arriba.

## Posibles mejoras futuras (fuera de alcance de este challenge)

- Migraciones con Alembic en vez de `create_all` automático.
- Circuit breaker explícito hacia el proveedor externo (hoy solo hay reintentos con backoff).
- Estabilizar y ejecutar los tests de integración end-to-end.
- Índices/particionamiento adicionales en `transactions` si el volumen real de "millones de transacciones diarias" lo requiere.
- **Idempotencia en `POST /transactions`:** los reintentos automáticos ante timeout/error de conexión (`tenacity`, en `provider_client.py`) pueden re-ejecutar una transacción que el proveedor sí alcanzó a procesar pero cuya respuesta se perdió, generando doble ejecución. La solución estándar es un idempotency key enviado por el cliente, que el servicio use para detectar reintentos y devolver el resultado ya existente en vez de ejecutar de nuevo.
- **Autorización por cuenta:** la API key actual autentica al *servicio* que llama, pero no valida que ese llamador tenga permiso sobre el `accountId` específico que está consultando o afectando — cualquier poseedor de la key puede operar sobre cualquier cuenta. Razonable para el alcance de este challenge (sin concepto de usuarios/roles), pero sería un gap real en un entorno multi-tenant.
