from pydantic import BaseModel, Field
from typing import List

class PaperSummary(BaseModel):

    title: str = Field(description='Generate the Title of the Paper')

    paper_overview: str = Field(description='A concise overview of the Paper.')

    research_problem: str = Field(description='Give a brief overview on the fundamental research problem the paper is trying to solve')

    motivation: str = Field(description='Give the motivation behind this paper')

    methodology: str = Field(description='Give the methodology used to carry out the experiments in the paper')

    experimental_setup: str = Field(description='Give an overview of the experimental setup used to obtain all the results in the paper')

    key_results: str = Field(description='Describe the results obtained in the paper')

    conclusion: str = Field(description='Provide the fundamental conclusion of the paper')

    future_improvement: str = Field(description='Describe the scope for further improvements in the results of the paper')

    limitations: str = Field(
        description=(
            "Summarize the limitations explicitly discussed by the authors. "
            "If none are mentioned, leave this field empty."
        )
        )

    keywords: list[str] = Field(
        description=(
            "Return between 5 and 10 important technical keywords."
        )
        )

class Flashcard(BaseModel):

    question: str = Field(
        description="Generate a question based only on the provided section of the research paper"
    )

    answer: str = Field(
        description="Provide a detailed answer to the question using only information supported by the provided section"
    )

class QuizQuestion(BaseModel):

    question: str = Field(description='Generate a question based only on the provided research paper section')

    options: List[str] = Field(description='Generate exactly 4 answer options')

    correct_answer: str = Field(description='Provide the correct answer which must exactly match with one of the 4 provided options.')

    explanation: str = Field(description='Explain why the correct answer is supported by the provided research paper section')