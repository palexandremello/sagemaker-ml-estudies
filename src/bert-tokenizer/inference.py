import os
import json
import torch
import subprocess
import sys
from transformers import AutoTokenizer, AutoModel

model_name = 'neuralmind/bert-base-portuguese-cased'

class HuggingFaceTokenizer:
    _instance = None

    def __init__(self):
        if HuggingFaceTokenizer._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.model = AutoModel.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model.eval()
            HuggingFaceTokenizer._instance = self

    @staticmethod
    def get_instance():
        if HuggingFaceTokenizer._instance is None:
            HuggingFaceTokenizer()
        return HuggingFaceTokenizer._instance

    def predict(self, text):
        input_token = self.tokenizer.tokenize(text) 
        input_id_token = self.tokenizer.convert_tokens_to_ids(input_token)
        return list(input_token), list(input_id_token)
        
hf_model = HuggingFaceTokenizer.get_instance()


def model_fn(model_dir: str) -> HuggingFaceTokenizer:
    print(model_dir)
    """
    Load the model from the model directory.
    """
    return HuggingFaceTokenizer.get_instance()

def input_fn(request_body, request_content_type):
    """
    Parse the input data payload.
    """
    if request_content_type == 'application/json':
        return json.loads(request_body)
    else:
        raise ValueError(f"Unsupported content type: {request_content_type}")

def predict_fn(input_data, model: HuggingFaceTokenizer):
    """
    Perform prediction on the input data.
    """
    input_tokens, input_id_tokens = model.predict(input_data["text"])
    return {"tokens": input_tokens, "id_tokens": input_id_tokens}

def output_fn(prediction, content_type):
    """
    Format the prediction output.
    """
    if content_type == 'application/json':
        return json.dumps(prediction), content_type
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
