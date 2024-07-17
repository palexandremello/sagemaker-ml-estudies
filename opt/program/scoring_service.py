import pickle
from sklearn.tree import DecisionTreeClassifier
import pandas as pd
from typing import List
from pydantic import BaseModel

# Schemas
class IrisFeatures(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

class InvocationRequest(BaseModel):
    instances: List[IrisFeatures]

class Prediction(BaseModel):
    species: str

class InvocationResponse(BaseModel):
    predictions: List[Prediction]

class ScoringService:
    model_path = "/opt/ml/model/decision-tree-model.pkl"
    model = None  # Where we keep the model when it's loaded

    @classmethod
    def get_model(cls) -> DecisionTreeClassifier:
        """Get the model object for this instance, loading it if it's not already loaded."""
        if cls.model is None:
            with open(cls.model_path, 'rb') as model_file:
                cls.model = pickle.load(model_file)
        return cls.model

    @classmethod
    def predict(cls, request: InvocationRequest) -> InvocationResponse:
        """For the input, do the predictions and return them.

        Args:
            request (InvocationRequest): The data on which to do the predictions.
        
        Returns:
            InvocationResponse: The prediction results.
        """
        clf = cls.get_model()
        input_data = pd.DataFrame([instance.dict() for instance in request.instances])
        predictions = clf.predict(input_data)
        response = InvocationResponse(
            predictions=[Prediction(species=pred) for pred in predictions]
        )
        return response
