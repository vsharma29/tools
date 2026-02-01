"""AWS Lambda handler — wraps the FastAPI app with Mangum."""

from mangum import Mangum
from src.api import app

handler = Mangum(app, lifespan="auto")
