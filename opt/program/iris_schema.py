from pydantic import BaseModel
from typing import List

# Schema para uma única instância de dados de entrada
class IrisFeatures(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# Schema para a requisição de invocação
class InvocationRequest(BaseModel):
    instances: List[IrisFeatures]

# Schema para a resposta de predição
class Prediction(BaseModel):
    species: str

class InvocationResponse(BaseModel):
    predictions: List[Prediction]
