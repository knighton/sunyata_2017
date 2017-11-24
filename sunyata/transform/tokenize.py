import spacy
from spacy.tokenizer import Tokenizer

from .base import Transformer


class Tokenize(Transformer):
    def __init__(self):
        nlp = spacy.load('en')
        self.tok = Tokenizer(nlp.vocab)

    def transform(self, xx):
        rrr = []
        for doc in self.tok.pipe(xx):
            rrr.append(list(doc))
        return rrr
