"""
lambda_handler.py
Punto de entrada para AWS Lambda + Mangum (ASGI adapter).
"""
from mangum import Mangum
from api.main import app

handler = Mangum(app, lifespan="on")
