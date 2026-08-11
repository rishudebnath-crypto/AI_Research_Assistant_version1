from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from database import get_document_chunks, merged_summary_exists, get_merged_summary, save_merged_summary, local_summary_exists, get_local_summary, save_local_summary
from typing import List
from schemas import PaperSummary, Flashcard, QuizQuestion
import time
from groq import APIStatusError, RateLimitError
from concurrent.futures import ThreadPoolExecutor
import random

load_dotenv()

llm1 = ChatGroq(model='openai/gpt-oss-20b', temperature=0)
llm2 = ChatGroq(model='openai/gpt-oss-120b', temperature=0)
llm3 = ChatGroq(model='qwen/qwen3.6-27b', temperature=0)
llm4 = ChatGroq(model='llama-3.3-70b-versatile')

SUMMARY_WINDOW_SIZE = 4
MERGE_SUMMARY_WINDOW_SIZE = 2
MAX_CONCURRENCY = 3

SUMMARY_LENGTH_INSTRUCTIONS = {
    "short": """
Produce a concise research report of approximately 150-250 words.
Focus only on the research objective, core methodology, major findings,
and conclusion. Avoid secondary details.
""",

    "medium": """
Produce a balanced research report of approximately 300-500 words.
Include the research objective, important concepts, methodology,
major experiments, key findings, important observations, and conclusion.
Include relevant technical details but avoid excessive detail.
""",

    "long": """
Produce a comprehensive research report of approximately 600-900 words.
Provide detailed coverage of the research objective, important concepts,
methodology, mathematical ideas, experimental setup, results,
important observations, limitations, and conclusion.
Preserve relevant technical details and explain important findings
rather than merely listing them.
"""
}

structured_llm2 = llm2.with_structured_output(PaperSummary)
structured_llm_flashcard = llm4.with_structured_output(Flashcard)
structured_llm_quiz = llm4.with_structured_output(QuizQuestion)

flashcard_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert AI Research Assistant.

Your task is to generate exactly ONE high-quality flashcard
from the provided section of a research paper.

Requirements:

- Generate the question using only information present in the provided text.
- The question should test an important concept, methodology,
  mathematical idea, experiment, result, or observation.
- Prefer questions that test understanding rather than trivial factual recall.
- Provide a detailed and accurate answer to the question.
- The answer must be fully supported by the provided text.
- Do not use information from outside the provided text.
- Do not invent or assume information.
- Generate exactly one question and one answer.

The question and answer should be useful for studying and
understanding the research paper.
"""
    ),

    (
        "human",
        """
Research Paper Section:

{text}
"""
    )
])

quiz_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert AI Research Assistant.

Your task is to generate exactly ONE high-quality multiple-choice
quiz question from the provided section of a research paper.

Requirements:

- Generate exactly one question.
- Generate exactly four distinct answer options.
- Only one option must be correct.
- The correct_answer must exactly match one of the four options.
- Base the question entirely on the provided research paper section.
- Focus on an important concept, methodology, mathematical idea,
  experiment, result, or observation.
- Prefer questions that test understanding rather than trivial recall.
- The explanation must clearly explain why the correct answer
  is supported by the provided text.
- Do not use information from outside the provided text.
- Do not invent or assume information.

The question should be useful for testing understanding
of the research paper.
"""
    ),

    (
        "human",
        """
Research Paper Section:

{text}
"""
    )
])

local_summary_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert AI Research Assistant.

Your task is to summarize ONE section of a research paper.

Focus on preserving:

- research objectives
- important concepts
- methodology
- mathematical ideas
- experiments
- important observations

Do not invent information.

Produce a coherent plain-text summary.
"""
    ),

    (
        "human",
        """
Research Paper Section:

{text}
"""
    )
])

merge_summary_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert AI Research Assistant.

You are given multiple summaries extracted from different
sections of the SAME research paper.

Merge them into a single coherent summary.

Requirements:

- preserve all important information
- remove repetition
- improve coherence
- maintain logical flow
- do not invent information

Return plain text only.
"""
    ),

    (
        "human",
        """
Summaries:

{text}
"""
    )
])

paper_summary_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert AI Research Assistant.

You are given a complete summary of a research paper.

Generate a structured research report.

Summary Requirements:

{summary_length_instruction}

Populate every field of the PaperSummary schema.

Do not invent information.

If a field is not supported by the paper,
state that it is not discussed.
"""
    ),

    (
        "human",
        """
Complete Research Paper Summary:

{text}
"""
    )
])

local_summary_chain = (
    local_summary_prompt
    | llm1
    | StrOutputParser()
)

merge_summary_chain = (
    merge_summary_prompt
    | llm3
    | StrOutputParser()
)

paper_summary_chain = (
    paper_summary_prompt
    | structured_llm2
)

flashcard_chain = (
    flashcard_prompt 
    | structured_llm_flashcard
)

quiz_chain = (
    quiz_prompt
    | structured_llm_quiz
)

def invoke_with_retry(chain, inputs, max_retries = 3, initial_delay = 2):

    for attempt in range(max_retries + 1):

        try:
            return chain.invoke(inputs)

        except RateLimitError:

            if attempt == max_retries:
                raise 

            delay = initial_delay*(2**attempt)
            print(
                f"Rate limit reached."
                f"Retrying in {delay} seconds"
            )

            time.sleep(delay)

        except APIStatusError as error:

            if error.status_code in (500, 502, 503, 504):

                if attempt == max_retries:
                    raise

                delay = initial_delay*(2**attempt)

                print(
                    f"Temporary API error {error.status_code}."
                    f"Retrying in {delay} seconds."
                )

                time.sleep(delay)

            else:
                raise 

def build_chunk_windows(document_id: int, window_size: int = SUMMARY_WINDOW_SIZE) -> List[str]:

    chunks = get_document_chunks(document_id)
    windows = []

    for i in range(0, len(chunks), window_size):

        window = chunks[i : i+window_size]
        windows.append(
            '\n\n'.join(window)
        )

    return windows

def generate_random_window(document_id: int):

    windows = build_chunk_windows(document_id)

    if not len(windows):
        raise ValueError('No documents found')

    random_index = random.randrange(len(windows))

    return random_index+1, windows[random_index]

def generate_local_summary(
    document_id: int,
    window_number: int,
    window: str
) -> str:

    print(f"Starting window {window_number}")

    if local_summary_exists(document_id, window_number):

        print(f"Using cached summary for window {window_number}")

        return get_local_summary(
            document_id,
            window_number
        )

    local_summary = invoke_with_retry(
        chain=local_summary_chain,
        inputs={
            "text": window
        }
    )

    save_local_summary(
        document_id,
        window_number,
        local_summary
    )

    return local_summary

def generate_summary(document_id: int, summary_length: str) -> PaperSummary:

    windows = build_chunk_windows(document_id)
    if len(windows) == 0:
        raise ValueError('No document found')

    local_summaries = [None] * len(windows)

    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENCY
    ) as executor:

        futures = []

        for window_number, window in enumerate(
            windows,
            start=1
        ):

            future = executor.submit(
                generate_local_summary,
                document_id,
                window_number,
                window
            )

            futures.append(future)

        for i, future in enumerate(futures):

            local_summaries[i] = future.result()

    if merged_summary_exists(document_id):
        merged_summary = get_merged_summary(document_id)
    
    else:
        while len(local_summaries) > 1:

            merged_summaries = []
            for i in range(0, len(local_summaries), MERGE_SUMMARY_WINDOW_SIZE):

                group_summary = "\n\n".join(local_summaries[i : i+MERGE_SUMMARY_WINDOW_SIZE])

                merge_summary = invoke_with_retry(
                    chain=merge_summary_chain,
                    inputs={
                        'text': group_summary
                    }
                )

                merged_summaries.append(merge_summary)

            local_summaries = merged_summaries
        merged_summary = local_summaries[0]
        save_merged_summary(document_id, merged_summary)

    final_summary = invoke_with_retry(
        chain=paper_summary_chain,
        inputs={
            'summary_length_instruction': SUMMARY_LENGTH_INSTRUCTIONS[summary_length],
            'text': merged_summary
        }
    )

    return final_summary
    
def generate_flashcard(document_id: int) -> Flashcard:

    window_number, window = generate_random_window(document_id)

    flashcard = invoke_with_retry(
        chain=flashcard_chain,
        inputs={
            'text': window
        }
    )

    return {
        'window number': window_number,
        'flashcard': flashcard
    }

def generate_quiz(
    document_id: int,
    number_of_questions: int = 5
):

    windows = build_chunk_windows(document_id)

    if not windows:
        raise ValueError("No document found")

    number_of_questions = min(
        number_of_questions,
        len(windows)
    )

    selected_indices = random.sample(
        range(len(windows)),
        number_of_questions
    )

    def generate_question(index: int):

        quiz_question = invoke_with_retry(
            chain=quiz_chain,
            inputs={
                "text": windows[index]
            }
        )

        return {
            "window_number": index + 1,
            "quiz_question": quiz_question
        }

    with ThreadPoolExecutor(
        max_workers=MAX_CONCURRENCY
    ) as executor:

        futures = [
            executor.submit(
                generate_question,
                index
            )
            for index in selected_indices
        ]

        quiz_questions = [
            future.result()
            for future in futures
        ]

    return quiz_questions