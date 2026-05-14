from typing import List
from dataclasses import dataclass
import re
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# =========================================================
# Embedding Model
# =========================================================

embedding_model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)


# =========================================================
# Chunk Dataclass
# =========================================================

@dataclass
class Chunk:
    text: str
    section: str
    start_idx: int
    end_idx: int


# =========================================================
# Academic Chunker
# =========================================================

class AcademicChunker:

    def __init__(
        self,
        similarity_threshold: float = 0.72,
        max_chunk_tokens: int = 400,
        min_chunk_tokens: int = 120,
        overlap_sentences: int = 2,
    ):

        self.similarity_threshold = similarity_threshold
        self.max_chunk_tokens = max_chunk_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.overlap_sentences = overlap_sentences

    # =====================================================
    # Sentence Split
    # =====================================================

    def split_sentences(self, text: str) -> List[str]:

        text = re.sub(r"\s+", " ", text)

        # 避免公式断裂
        text = text.replace("\n", " ")

        sentences = re.split(
            r'(?<=[.!?])\s+',
            text
        )

        return [
            s.strip()
            for s in sentences
            if s.strip()
        ]

    # =====================================================
    # Section Split
    # =====================================================

    def split_sections(self, text: str):

        pattern = r"""
        (?=
            \n?[0-9]+\.\s+[A-Z]
            |
            \n?(ABSTRACT|Abstract)
            |
            \n?(INTRODUCTION|Introduction)
            |
            \n?(METHOD|Method|Methods)
            |
            \n?(EXPERIMENT|Experiment|Experiments)
            |
            \n?(RESULT|Results)
            |
            \n?(CONCLUSION|Conclusion)
            |
            \n?(REFERENCES|References)
        )
        """

        sections = re.split(
            pattern,
            text,
            flags=re.VERBOSE
        )

        cleaned = []

        current_title = "Unknown"

        for sec in sections:

            if not sec:
                continue

            sec = sec.strip()

            if len(sec) < 5:
                continue

            # 标题识别
            first_line = sec.split("\n")[0]

            if len(first_line) < 80:
                current_title = first_line

            cleaned.append(
                (current_title, sec)
            )

        return cleaned

    # =====================================================
    # Approximate Token Count
    # =====================================================

    def token_count(self, text: str):

        return int(len(text.split()) * 1.3)

    # =====================================================
    # Semantic Chunking
    # =====================================================

    def semantic_chunk(
        self,
        section_text: str,
        section_name: str,
    ) -> List[Chunk]:

        sentences = self.split_sentences(section_text)

        if len(sentences) == 0:
            return []

        if len(sentences) == 1:

            return [
                Chunk(
                    text=sentences[0],
                    section=section_name,
                    start_idx=0,
                    end_idx=1,
                )
            ]

        embeddings = embedding_model.encode(
            sentences,
            normalize_embeddings=True
        )

        similarities = []

        for i in range(len(sentences) - 1):

            sim = cosine_similarity(
                [embeddings[i]],
                [embeddings[i + 1]]
            )[0][0]

            similarities.append(sim)

        dynamic_threshold = min(
            self.similarity_threshold,
            np.percentile(similarities, 25)
        )

        chunks = []

        current_chunk = [sentences[0]]

        chunk_start = 0

        for i in range(1, len(sentences)):

            sim = similarities[i - 1]

            current_text = " ".join(current_chunk)

            should_split = False

            # 语义突变
            if sim < dynamic_threshold:
                should_split = True

            # token 超限
            if self.token_count(current_text) > self.max_chunk_tokens:
                should_split = True

            if should_split:

                if self.token_count(current_text) >= self.min_chunk_tokens:

                    chunk_text = " ".join(current_chunk)

                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            section=section_name,
                            start_idx=chunk_start,
                            end_idx=i,
                        )
                    )

                    # overlap
                    overlap = current_chunk[
                        -self.overlap_sentences:
                    ]

                    current_chunk = overlap.copy()

                    chunk_start = i - len(overlap)

            current_chunk.append(sentences[i])

        # last chunk
        if current_chunk:

            chunks.append(
                Chunk(
                    text=" ".join(current_chunk),
                    section=section_name,
                    start_idx=chunk_start,
                    end_idx=len(sentences),
                )
            )

        return chunks

    # =====================================================
    # Main API
    # =====================================================

    def chunk(self, text: str) -> List[Chunk]:

        sections = self.split_sections(text)

        all_chunks = []

        for section_name, section_text in sections:

            chunks = self.semantic_chunk(
                section_text,
                section_name
            )

            all_chunks.extend(chunks)

        return all_chunks