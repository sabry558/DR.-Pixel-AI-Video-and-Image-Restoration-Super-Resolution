from app.services.rabbitmq_service import app

@app.task(queue="light_enhacement")
def _route_light_enhacement(defect_payload):
    return defect_payload