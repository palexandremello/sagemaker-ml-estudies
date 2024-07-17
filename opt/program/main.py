import logging
from fastapi import FastAPI, Response, status
from program.iris_schema import InvocationRequest, InvocationResponse
from program.scoring_service import ScoringService

app = FastAPI(title="Iris Dataset Classification Model")

# Preload the model
ScoringService.get_model()

@app.get("/ping")
def ping(response: Response) -> Response:
    health = ScoringService.get_model() is not None
    response.status_code = status.HTTP_200_OK if health else status.HTTP_404_NOT_FOUND
    return response

@app.post("/invocations", response_model=InvocationResponse)
def transformation(invocation_req: InvocationRequest) -> InvocationResponse:
    result = ScoringService.predict(invocation_req)
    return result
