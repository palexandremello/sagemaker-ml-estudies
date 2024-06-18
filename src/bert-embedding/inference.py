import os
import json
import torch
import subprocess
import sys
from transformers import AutoTokenizer, AutoModel



model_name = 'neuralmind/bert-base-portuguese-cased'

class HuggingFaceEmbeddings:
    _instance = None

    def __init__(self):
        if HuggingFaceEmbeddings._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.model = AutoModel.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model.eval()
            HuggingFaceEmbeddings._instance = self

    @staticmethod
    def get_instance():
        if HuggingFaceEmbeddings._instance is None:
            HuggingFaceEmbeddings()
        return HuggingFaceEmbeddings._instance

    def predict(self, text):
        inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state
        pooled_embeddings = torch.mean(embeddings, dim=1)
        return pooled_embeddings.numpy()[0].tolist()
        
hf_model = HuggingFaceEmbeddings.get_instance()


def model_fn(model_dir: str) -> HuggingFaceEmbeddings:
    print(model_dir)
    """
    Load the model from the model directory.
    """
    return HuggingFaceEmbeddings.get_instance()

def input_fn(request_body, request_content_type):
    """
    Parse the input data payload.
    """
    if request_content_type == 'application/json':
        return json.loads(request_body)
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model: HuggingFaceEmbeddings):
    """
    Perform prediction on the input data.
    """
    embeddings = model.predict(input_data["text"])
    return embeddings

def output_fn(prediction, content_type):
    """
    Format the prediction output.
    """
    if content_type == 'application/json':
        return json.dumps(prediction), content_type
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
