from elasticsearch_dsl import (
    DocType, Text, Date, Completion,
    analyzer, token_filter,
    Integer
)

from random import randint



title_analyzer = analyzer(
    "title_analyzer",
    tokenizer = "whitespace",
    filter=["lowercase", token_filter("ascii_fold", "asciifolding")]
)


class Video(DocType):
    title = Text()
    title_suggest = Completion(analyzer=title_analyzer)
    number = Integer()
    publish_date = Date()
    def clean(self):
        self.title_suggest = {
            "input": [self.title],
            "weight": 1,
        }
        self.number = randint(10, 20)

    class Meta:
        index = "ytvideo"

