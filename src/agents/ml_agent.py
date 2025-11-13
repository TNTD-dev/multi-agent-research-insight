"""
Machine Learning Agent - performs topic modelling, clustering, and quality scoring.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from src.agents.state import ResearchState
from src.utils.logger import default_logger as logger

try:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    import numpy as np

    ML_AVAILABLE = True
except ImportError:  # pragma: no cover
    ML_AVAILABLE = False
    logger.warning("scikit-learn not installed. ML features are disabled.")


class MLAgent:
    """Agent responsible for ML-based analysis of research sources."""

    def __init__(self, llm, config):
        self.llm = llm
        self.config = config
        self.vectorizer = None
        self.cluster_model = None

    def topic_modelling(self, documents: List[str], n_topics: int) -> List[Dict[str, object]]:
        if not ML_AVAILABLE or len(documents) < 3:
            return []

        vectorizer = CountVectorizer(max_features=100, stop_words="english")
        doc_term_matrix = vectorizer.fit_transform(documents)

        lda = LatentDirichletAllocation(n_components=min(n_topics, len(documents)), random_state=self.config.ml.random_state)
        lda.fit(doc_term_matrix)

        feature_names = vectorizer.get_feature_names_out()
        topics: List[Dict[str, object]] = []
        for topic_idx, topic in enumerate(lda.components_):
            top_indices = topic.argsort()[-8:][::-1]
            top_words = [feature_names[i] for i in top_indices]
            topics.append(
                {
                    "topic_id": topic_idx + 1,
                    "keywords": top_words[:5],
                    "all_keywords": top_words,
                    "weight": float(topic.sum()),
                }
            )

        logger.info("ML: extracted %d topics", len(topics))
        return topics

    def cluster_papers(self, documents: List[str], sources: List) -> Dict[str, object]:
        if not ML_AVAILABLE or len(documents) < 2:
            return {}

        n_clusters = min(self.config.ml.n_clusters, max(2, len(documents) // 2))
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words="english")
        tfidf_matrix = self.vectorizer.fit_transform(documents)

        self.cluster_model = KMeans(n_clusters=n_clusters, random_state=self.config.ml.random_state)
        labels = self.cluster_model.fit_predict(tfidf_matrix)

        clusters = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters[int(label)].append(
                {
                    "title": sources[idx].get("title", "")[:60],
                    "source_id": sources[idx].get("id", ""),
                    "summary": sources[idx].get("summary", "")[:100],
                }
            )

        feature_names = self.vectorizer.get_feature_names_out()
        themes = {}
        for cluster_id in range(n_clusters):
            center = self.cluster_model.cluster_centers_[cluster_id]
            top_indices = center.argsort()[-5:][::-1]
            themes[cluster_id] = [feature_names[i] for i in top_indices]

        logger.info("ML: clustered papers into %d clusters", n_clusters)
        return {
            "n_clusters": n_clusters,
            "clusters": dict(clusters),
            "cluster_themes": themes,
            "cluster_sizes": {cid: len(items) for cid, items in clusters.items()},
        }

    def ml_quality_scores(self, sources: List) -> List[Dict[str, object]]:
        if not ML_AVAILABLE:
            return []

        scores: List[Dict[str, object]] = []
        for source in sources:
            title_length = len(source.get("title", ""))
            summary_length = len(source.get("summary", ""))
            citation_log = np.log1p(source.get("citation_count", 0))
            num_authors = len(source.get("authors", []))
            is_recent = 1 if any(year in str(source.get("published", "")) for year in ("2023", "2024", "2025")) else 0

            ml_score = (
                min(20, title_length / 5)
                + min(30, summary_length / 50)
                + min(30, citation_log * 5)
                + min(10, num_authors * 2)
                + is_recent * 10
            )

            scores.append(
                {
                    "title": source.get("title", "")[:60],
                    "ml_score": round(float(ml_score), 1),
                    "grade": "A"
                    if ml_score >= 80
                    else "B"
                    if ml_score >= 65
                    else "C"
                    if ml_score >= 50
                    else "D",
                }
            )

        scores.sort(key=lambda item: item["ml_score"], reverse=True)
        logger.info("ML: scored %d papers", len(scores))
        return scores

    def analyze(self, state: ResearchState) -> Dict[str, object]:
        if not ML_AVAILABLE or not self.config.ml.enable_ml:
            logger.warning("ML: Analysis skipped (ML unavailable or disabled).")
            return {
                "ml_topics": [],
                "paper_clusters": {},
                "ml_quality_scores": [],
                "ml_insights": {"status": "unavailable"},
            }

        sources = state.validated_sources
        documents = [f"{source.get('title', '')} {source.get('summary', '')}" for source in sources]

        topics = self.topic_modelling(documents, self.config.ml.n_topics)
        clusters = self.cluster_papers(documents, sources)
        quality_scores = self.ml_quality_scores(sources)

        insights = {
            "dominant_cluster": (
                max(clusters.get("cluster_sizes", {}).items(), key=lambda item: item[1])[0]
                if clusters.get("cluster_sizes")
                else None
            ),
            "top_topic": topics[0] if topics else None,
            "average_ml_score": round(
                sum(score["ml_score"] for score in quality_scores) / len(quality_scores), 1
            )
            if quality_scores
            else 0,
        }

        logger.info("ML: analysis complete")
        return {
            "ml_topics": topics,
            "paper_clusters": clusters,
            "ml_quality_scores": quality_scores,
            "ml_insights": insights,
        }
