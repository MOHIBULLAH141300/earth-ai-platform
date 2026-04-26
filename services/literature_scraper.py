"""
Literature Scraping & Research Integration Module
Fetches latest research from ArXiv, DOAJ, and RSS feeds
Integrates findings into the AI knowledge base for model adaptation
"""

import asyncio
import aiohttp
import feedparser
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import hashlib
from abc import ABC, abstractmethod
import sqlite3
from enum import Enum

logger = logging.getLogger(__name__)


class ResearchSource(Enum):
    """Available research sources"""
    ARXIV = "arxiv"
    DOAJ = "doaj"
    PUBMED = "pubmed"
    SCIENCEDIRECT = "sciencedirect"
    RSS = "rss"


@dataclass
class ResearchPaper:
    """Represents a research paper/article"""
    title: str
    authors: List[str]
    abstract: str
    publication_date: str
    source: ResearchSource
    url: str
    keywords: List[str]
    doi: Optional[str] = None
    citations: int = 0
    pdf_url: Optional[str] = None
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "source": self.source.value
        }
    
    def get_hash(self) -> str:
        """Generate unique hash for paper"""
        content = f"{self.title}{self.authors[0] if self.authors else ''}"
        return hashlib.md5(content.encode()).hexdigest()


class ResearchSourceConnector(ABC):
    """Abstract base for research source connectors"""
    
    @abstractmethod
    async def fetch_papers(self, query: str, max_results: int = 50) -> List[ResearchPaper]:
        """Fetch papers from source matching query"""
        pass
    
    @abstractmethod
    async def fetch_by_topic(self, topic: str, days_back: int = 7) -> List[ResearchPaper]:
        """Fetch recent papers on specific topic"""
        pass


class ArxivConnector(ResearchSourceConnector):
    """ArXiv API connector for ML/AI papers"""
    
    BASE_URL = "http://export.arxiv.org/api/query?"
    
    async def fetch_papers(self, query: str, max_results: int = 50) -> List[ResearchPaper]:
        """Fetch papers from ArXiv"""
        try:
            params = {
                "search_query": f"cat:cs.AI AND ({query})",
                "start": 0,
                "max_results": min(max_results, 100),
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.error(f"ArXiv API error: {resp.status}")
                        return []
                    
                    content = await resp.text()
                    return self._parse_arxiv_response(content)
        except Exception as e:
            logger.error(f"ArXiv fetch error: {e}")
            return []
    
    async def fetch_by_topic(self, topic: str, days_back: int = 7) -> List[ResearchPaper]:
        """Fetch recent ArXiv papers on topic"""
        query = f"({topic} OR landslide OR hazard OR risk)"
        return await self.fetch_papers(query, max_results=30)
    
    def _parse_arxiv_response(self, xml_content: str) -> List[ResearchPaper]:
        """Parse ArXiv XML response"""
        papers = []
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_content)
            
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                try:
                    title = entry.find('{http://www.w3.org/2005/Atom}title').text
                    authors = [
                        author.find('{http://www.w3.org/2005/Atom}name').text
                        for author in entry.findall('{http://www.w3.org/2005/Atom}author')
                    ]
                    abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text
                    published = entry.find('{http://www.w3.org/2005/Atom}published').text
                    url = entry.find('{http://www.w3.org/2005/Atom}id').text
                    
                    # Extract PDF URL
                    pdf_url = None
                    for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                        if link.get('type') == 'application/pdf':
                            pdf_url = link.get('href')
                    
                    paper = ResearchPaper(
                        title=title.strip(),
                        authors=authors,
                        abstract=abstract.strip(),
                        publication_date=published,
                        source=ResearchSource.ARXIV,
                        url=url,
                        keywords=self._extract_keywords(title, abstract),
                        pdf_url=pdf_url,
                        doi=None
                    )
                    papers.append(paper)
                except Exception as e:
                    logger.debug(f"Error parsing ArXiv entry: {e}")
                    continue
        except Exception as e:
            logger.error(f"ArXiv XML parsing error: {e}")
        
        return papers
    
    def _extract_keywords(self, title: str, abstract: str) -> List[str]:
        """Extract keywords from title and abstract"""
        # Simple keyword extraction (can be enhanced with NLP)
        keywords = []
        common_keywords = [
            "landslide", "susceptibility", "hazard", "risk", "model", "prediction",
            "machine learning", "deep learning", "climate", "geospatial", "satellite",
            "neural network", "classification", "regression", "forest", "ensemble"
        ]
        
        combined_text = (title + " " + abstract).lower()
        for keyword in common_keywords:
            if keyword in combined_text:
                keywords.append(keyword)
        
        return keywords[:5]  # Return top 5


class DOAJConnector(ResearchSourceConnector):
    """DOAJ (Directory of Open Access Journals) connector"""
    
    BASE_URL = "https://doaj.org/api/v1/search/articles"
    
    async def fetch_papers(self, query: str, max_results: int = 50) -> List[ResearchPaper]:
        """Fetch papers from DOAJ"""
        try:
            params = {
                "q": query,
                "page": 1,
                "pageSize": min(max_results, 100)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        logger.error(f"DOAJ API error: {resp.status}")
                        return []
                    
                    data = await resp.json()
                    return self._parse_doaj_response(data)
        except Exception as e:
            logger.error(f"DOAJ fetch error: {e}")
            return []
    
    async def fetch_by_topic(self, topic: str, days_back: int = 7) -> List[ResearchPaper]:
        """Fetch recent DOAJ papers"""
        query = f'(title:"{topic}" OR abstract:"{topic}") AND (landslide OR hazard)'
        return await self.fetch_papers(query, max_results=30)
    
    def _parse_doaj_response(self, data: Dict) -> List[ResearchPaper]:
        """Parse DOAJ JSON response"""
        papers = []
        try:
            results = data.get("results", [])
            for item in results:
                bibjson = item.get("bibjson", {})
                
                paper = ResearchPaper(
                    title=bibjson.get("title", ""),
                    authors=[author.get("name", "") for author in bibjson.get("author", [])],
                    abstract=bibjson.get("abstract", ""),
                    publication_date=bibjson.get("year", datetime.now().isoformat()),
                    source=ResearchSource.DOAJ,
                    url=bibjson.get("link", [{}])[0].get("url", "") if bibjson.get("link") else "",
                    keywords=bibjson.get("keywords", []),
                    doi=bibjson.get("identifier", [{}])[0].get("id", "") if bibjson.get("identifier") else None
                )
                papers.append(paper)
        except Exception as e:
            logger.error(f"DOAJ parsing error: {e}")
        
        return papers


class RSSConnector(ResearchSourceConnector):
    """RSS feed connector for research feeds"""
    
    def __init__(self, feed_urls: List[str]):
        self.feed_urls = feed_urls
    
    async def fetch_papers(self, query: str, max_results: int = 50) -> List[ResearchPaper]:
        """Fetch papers from RSS feeds"""
        papers = []
        for feed_url in self.feed_urls:
            try:
                papers.extend(await self._fetch_feed(feed_url))
            except Exception as e:
                logger.error(f"RSS fetch error for {feed_url}: {e}")
        
        # Filter by query
        filtered = [p for p in papers if query.lower() in p.title.lower() or query.lower() in p.abstract.lower()]
        return filtered[:max_results]
    
    async def fetch_by_topic(self, topic: str, days_back: int = 7) -> List[ResearchPaper]:
        """Fetch recent papers by topic"""
        return await self.fetch_papers(topic, max_results=50)
    
    async def _fetch_feed(self, feed_url: str) -> List[ResearchPaper]:
        """Fetch single RSS feed"""
        papers = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                paper = ResearchPaper(
                    title=entry.get("title", ""),
                    authors=[entry.get("author", "Unknown")],
                    abstract=entry.get("summary", ""),
                    publication_date=entry.get("published", datetime.now().isoformat()),
                    source=ResearchSource.RSS,
                    url=entry.get("link", ""),
                    keywords=[],
                    doi=None
                )
                papers.append(paper)
        except Exception as e:
            logger.error(f"RSS parsing error: {e}")
        
        return papers


class LiteratureKnowledgeBase:
    """Manages literature database and knowledge extraction"""
    
    def __init__(self, db_path: str = "data/research_knowledge.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        Path(self.db_path).parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT,
                abstract TEXT,
                publication_date TEXT,
                source TEXT,
                url TEXT UNIQUE,
                keywords TEXT,
                doi TEXT,
                citations INTEGER DEFAULT 0,
                pdf_url TEXT,
                relevance_score REAL DEFAULT 0.0,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY,
                paper_id TEXT,
                insight_type TEXT,
                insight_content TEXT,
                relevant_to TEXT,
                confidence REAL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_id) REFERENCES papers(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def store_papers(self, papers: List[ResearchPaper]) -> int:
        """Store papers in knowledge base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stored_count = 0
        try:
            for paper in papers:
                paper_id = paper.get_hash()
                
                try:
                    cursor.execute("""
                        INSERT INTO papers 
                        (id, title, authors, abstract, publication_date, source, url, keywords, doi, pdf_url, relevance_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        paper.title,
                        json.dumps(paper.authors),
                        paper.abstract,
                        paper.publication_date,
                        paper.source.value,
                        paper.url,
                        json.dumps(paper.keywords),
                        paper.doi,
                        paper.pdf_url,
                        paper.relevance_score
                    ))
                    stored_count += 1
                except sqlite3.IntegrityError:
                    # Paper already exists, update if needed
                    pass
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error storing papers: {e}")
        finally:
            conn.close()
        
        return stored_count
    
    def get_relevant_papers(self, topic: str, limit: int = 10) -> List[Dict]:
        """Get papers relevant to topic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = f"%{topic}%"
        cursor.execute("""
            SELECT * FROM papers 
            WHERE title LIKE ? OR abstract LIKE ? OR keywords LIKE ?
            ORDER BY relevance_score DESC, publication_date DESC
            LIMIT ?
        """, (query, query, query, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "title": row[1],
                "authors": json.loads(row[2]),
                "abstract": row[3],
                "publication_date": row[4],
                "source": row[5],
                "url": row[6],
                "keywords": json.loads(row[7]),
                "doi": row[8],
                "citations": row[9]
            })
        
        conn.close()
        return results
    
    def extract_insights(self, paper: ResearchPaper) -> List[Dict]:
        """Extract actionable insights from paper for model improvement"""
        insights = []
        
        # Simple heuristic-based insight extraction (can be enhanced with NLP/LLM)
        abstract_lower = paper.abstract.lower()
        
        # Methodology insights
        if "neural network" in abstract_lower or "deep learning" in abstract_lower:
            insights.append({
                "type": "methodology",
                "content": "Deep learning approach mentioned - consider DL models",
                "relevant_to": "model_selection",
                "confidence": 0.8
            })
        
        if "ensemble" in abstract_lower:
            insights.append({
                "type": "methodology",
                "content": "Ensemble methods recommended",
                "relevant_to": "model_architecture",
                "confidence": 0.7
            })
        
        # Data insights
        if "satellite" in abstract_lower or "remote sensing" in abstract_lower:
            insights.append({
                "type": "data_source",
                "content": "Satellite/remote sensing data recommended",
                "relevant_to": "data_selection",
                "confidence": 0.85
            })
        
        # Performance insights
        if "accuracy" in abstract_lower or "f1" in abstract_lower:
            insights.append({
                "type": "performance_metric",
                "content": "Consider F1 score and accuracy as performance metrics",
                "relevant_to": "evaluation",
                "confidence": 0.6
            })
        
        return insights


class LiteratureScraperService:
    """Main service for literature scraping and integration"""
    
    def __init__(self):
        self.arxiv_connector = ArxivConnector()
        self.doaj_connector = DOAJConnector()
        self.rss_feeds = [
            "https://arxiv.org/rss/cs.AI",
            "https://arxiv.org/rss/cs.LG"
        ]
        self.rss_connector = RSSConnector(self.rss_feeds)
        self.knowledge_base = LiteratureKnowledgeBase()
        self.update_interval = 24  # hours
    
    async def scrape_latest_research(self, topics: List[str], days_back: int = 7) -> Dict:
        """Scrape latest research across all sources"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "total_papers": 0,
            "total_stored": 0
        }
        
        tasks = []
        
        # ArXiv
        for topic in topics:
            tasks.append(self.arxiv_connector.fetch_by_topic(topic, days_back))
        
        # DOAJ
        for topic in topics:
            tasks.append(self.doaj_connector.fetch_by_topic(topic, days_back))
        
        # RSS
        for topic in topics:
            tasks.append(self.rss_connector.fetch_by_topic(topic, days_back))
        
        paper_batches = await asyncio.gather(*tasks)
        
        all_papers = []
        for i, batch in enumerate(paper_batches):
            all_papers.extend(batch)
        
        results["total_papers"] = len(all_papers)
        results["total_stored"] = self.knowledge_base.store_papers(all_papers)
        
        logger.info(f"Scraped {results['total_papers']} papers, stored {results['total_stored']}")
        
        return results
    
    def get_insights_for_task(self, task_type: str) -> List[Dict]:
        """Get research insights for specific task"""
        topic_mapping = {
            "landslide_susceptibility": "landslide susceptibility prediction",
            "flood_prediction": "flood forecasting risk assessment",
            "earthquake_damage": "earthquake damage prediction",
            "drought_monitoring": "drought monitoring prediction"
        }
        
        topic = topic_mapping.get(task_type, task_type)
        papers = self.knowledge_base.get_relevant_papers(topic, limit=5)
        
        all_insights = []
        for paper in papers:
            paper_obj = ResearchPaper(
                title=paper["title"],
                authors=paper["authors"],
                abstract=paper["abstract"],
                publication_date=paper["publication_date"],
                source=ResearchSource(paper["source"]),
                url=paper["url"],
                keywords=paper["keywords"],
                doi=paper["doi"]
            )
            insights = self.knowledge_base.extract_insights(paper_obj)
            all_insights.extend(insights)
        
        return all_insights


# Singleton instance
_literature_service = None

def get_literature_service() -> LiteratureScraperService:
    """Get or create literature scraper service"""
    global _literature_service
    if _literature_service is None:
        _literature_service = LiteratureScraperService()
    return _literature_service
