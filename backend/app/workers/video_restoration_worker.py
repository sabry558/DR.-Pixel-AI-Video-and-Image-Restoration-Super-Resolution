from app.services.rabbitmq_service import app

@app.task(queue="video_restoration")
def _route_video_restoration(defect_payload):
    return defect_payload