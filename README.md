# DR. Pixel Backend Setup

This repository uses three runtime pieces:

- Docker services for PostgreSQL, pgAdmin, and RabbitMQ.
- The FastAPI API in the `pixel_env` Conda environment.
- The Celery worker stack in `pixel_env` for the `video_classifier` and `video_restoration` queues.
- The `light_enhacement` worker in the `DarkIR_env` Conda environment, because that path imports DarkIR code at runtime.

## Prerequisites

Make sure Docker and Conda are installed before starting.

## 1. Start the infrastructure

From the `backend/` folder, start the Docker services first:

```bash
cd backend
docker compose up -d
```

This starts PostgreSQL on port `5433`, pgAdmin on port `5050`, and RabbitMQ on port `5672`.

## 2. Set up the API environment

Create the API environment, activate it, install the backend dependencies, and start FastAPI:

```bash
conda create -n pixel_env python=3.12
conda activate pixel_env
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API entry point is [backend/app/main.py](backend/app/main.py), which creates the FastAPI app and initializes the database on startup.

## 3. Set up the DarkIR environment

Create the DarkIR environment once, then install the model dependencies it needs:

```bash
conda create -n DarkIR_env python=3.10
conda activate DarkIR_env
pip install -r models/Darkir/requirements.txt
```

## 4. Run the Celery workers

Run the worker process from `pixel_env` for the classifier and restoration queues. The `light_enhacement` queue loads DarkIR modules directly, so that worker must run from `DarkIR_env`:

```bash
conda activate pixel_env
celery -A app.services.rabbitmq_service.app worker --loglevel=info --queues=video_classifier,video_restoration

conda activate DarkIR_env
celery -A app.services.rabbitmq_service.app worker --loglevel=info --queues=light_enhacement
```

The Celery app is defined in [backend/app/services/rabbitmq_service.py](backend/app/services/rabbitmq_service.py) and includes these worker modules:

- [backend/app/workers/video_classifier_worker.py](backend/app/workers/video_classifier_worker.py)
- [backend/app/workers/light_enhancement_worker.py](backend/app/workers/light_enhancement_worker.py)
- [backend/app/workers/video_restoration_worker.py](backend/app/workers/video_restoration_worker.py)

## Expected startup order

1. Run `docker compose up -d` inside `backend/`.
2. Start the API with `uvicorn app.main:app  --host 0.0.0.0 --port 8000` in `pixel_env`.
3. Start the `video_classifier` and `video_restoration` workers in `pixel_env`.
4. Start the `light_enhacement` worker in `DarkIR_env`.

If you only need the API, `pixel_env` is enough. If you need low-light restoration, `DarkIR_env` is required for the `light_enhacement` Celery worker.

