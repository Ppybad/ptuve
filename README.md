# PTUVE — Descargas de Audio con Arquitectura Hexagonal

## Arquitectura

Este proyecto implementa Arquitectura Hexagonal para mantener un fuerte desacoplamiento entre el dominio y las tecnologías externas, y utiliza procesamiento asíncrono con Celery/Redis para ejecutar descargas fuera del ciclo de vida de la petición HTTP.

- Núcleo de Dominio
  - Puerto/Contrato: `IDownloader` (interfaz del motor de descarga).
  - Factoría: `get_downloader()` decide la implementación concreta sin acoplar la capa de entrada.
- Infraestructura
  - Adaptador: `YtDlpAdapter` implementa `IDownloader` con yt-dlp.
  - Persistencia: PostgreSQL (SQLAlchemy) para tareas y metadatos.
  - Broker/Cola: Redis + Celery para orquestar tareas de fondo.
  - Almacenamiento: Volumen compartido `/downloads` para archivos `.m4a`.
- Capa de Entrada
  - API: FastAPI expone endpoints REST (crear, listar, consultar, reintentar, eliminar y servir archivo).
  - Cliente: Dashboard en React consume la API con Axios.

Flujo general:
1) El usuario envía una URL al endpoint de creación; la API guarda una tarea `PENDING` y encola un job en Celery.
2) El Worker (Celery) toma la tarea, marca `PROCESSING`, invoca `get_downloader()` y descarga el `.m4a` a `/downloads`.
3) Al finalizar, actualiza la tarea a `COMPLETED` con `file_path` y `title` (o `FAILED` si hubo error).
4) El Dashboard lista/pagina/filtra tareas y permite descargar el archivo final desde la API.

## Stack Tecnológico

- Backend: FastAPI, SQLAlchemy, Celery, Redis, PostgreSQL
- Motor de descarga: yt-dlp (ffmpeg en la imagen de backend)
- Frontend: React + Vite + TypeScript + Tailwind CSS + Axios + Lucide Icons
- Contenerización: Docker & Docker Compose

## Guía de Inicio

Requisitos: Docker y Docker Compose.

1) Levantar toda la solución

```bash
docker compose up -d --build
```

2) Acceder a los servicios

- Dashboard (Frontend): http://localhost:8081
- API (Backend): http://localhost:8000

Notas:
- La API habilita CORS para http://localhost:8081.
- El volumen compartido `/downloads` almacena los archivos `.m4a` generados por el worker.

## Diagrama de Flujo (Mermaid)

```mermaid
flowchart LR
    A[Usuario pega URL en Dashboard] -->|Axios| B[POST /api/v1/downloads]
    B --> C[(PostgreSQL)\nTarea PENDING]
    B --> D{Publica en\nCelery/Redis}
    D --> E[Worker Celery]
    E --> F[get_downloader()\n-> YtDlpAdapter]
    F --> G[yt-dlp descarga\n.m4a a /downloads]
    G --> H[Actualiza DB:\nCOMPLETED/FAILED + metadatos]
    H --> I[GET /api/v1/downloads\npaginado/filtrado]
    I --> J[GET /api/v1/downloads/{id}/file\nsirve .m4a]
```

---

Arquitectura Hexagonal garantiza que el dominio no dependa de detalles de infraestructura; cambiar el motor de descarga o la capa de persistencia no impacta la API ni el core.

