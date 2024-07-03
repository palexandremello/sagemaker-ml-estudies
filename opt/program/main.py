import logging

from fastapi import FastAPI, Response, status

from program.scoring_service import ScoringService
from program.word2vec_schema import (
    InvocationRequest,
    InvocationResponse,
    WordSimilarity,
)


app = FastAPI(title="Word Similarity API")

# model load
ScoringService.get_model()


#fiz uma modificação
@app.get("/ping")
def ping(response: Response) -> Response:
    health = ScoringService.get_model()
    response.status_code = status.HTTP_200_OK if health else status.HTTP_404_NOT_FOUND

    return response


@app.post("/invocations", response_model=InvocationResponse)
def transformation(invocation_req: InvocationRequest) -> InvocationResponse:
    result = ScoringService.predict(invocation_req.word)
    word_similarities = []
    if result:
        for word, similarity in result:
            word_similarities.append(WordSimilarity(word=word, similarity=similarity))
    return InvocationResponse(word_similarities=word_similarities)
