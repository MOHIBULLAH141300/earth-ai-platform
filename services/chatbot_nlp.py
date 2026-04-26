"""
Chatbot & NLP Interface Layer
Natural language understanding and routing for client interactions
"""

import logging
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime
import re

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not installed, using fallback NLP")

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Supported task types"""
    LANDSLIDE_SUSCEPTIBILITY = "landslide_susceptibility"
    FLOOD_PREDICTION = "flood_prediction"
    EARTHQUAKE_DAMAGE = "earthquake_damage"
    DROUGHT_MONITORING = "drought_monitoring"
    CROP_YIELD_PREDICTION = "crop_yield_prediction"
    CLIMATE_ANALYSIS = "climate_analysis"
    CUSTOM_MODEL = "custom_model"


class IntentType(Enum):
    """Intent types for NLP understanding"""
    DATA_ANALYSIS = "data_analysis"
    MODEL_TRAINING = "model_training"
    PREDICTION = "prediction"
    VISUALIZATION = "visualization"
    LITERATURE_SEARCH = "literature_search"
    SYSTEM_STATUS = "system_status"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class UserQuery:
    """Represents a user query"""
    text: str
    user_id: Optional[str] = None
    timestamp: str = None
    location: Optional[str] = None
    context: Optional[Dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ParsedIntent:
    """Parsed user intent"""
    intent: IntentType
    task_type: Optional[TaskType]
    confidence: float
    parameters: Dict[str, Any]
    original_query: str
    entities: List[str]


class NLPProcessor:
    """NLP processing for intent and entity extraction"""
    
    def __init__(self, use_transformers: bool = True):
        self.use_transformers = use_transformers and TRANSFORMERS_AVAILABLE
        
        # Initialize transformers if available
        if self.use_transformers:
            try:
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli"
                )
                self.ner_pipeline = pipeline("ner", model="dbmdz/bert-base-cased-finetuned-conll03-english")
            except Exception as e:
                logger.warning(f"Failed to load transformers: {e}, using fallback")
                self.use_transformers = False
        
        # Fallback patterns
        self.intent_patterns = self._init_intent_patterns()
        self.task_patterns = self._init_task_patterns()
    
    def _init_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Initialize regex patterns for intent detection"""
        return {
            IntentType.DATA_ANALYSIS: [
                r"(analyze|explore|examine|study)\s+(data|dataset)",
                r"(show|display|visualize)\s+(data|statistics)",
                r"(what|how|which).*(data|information)",
                r"(get|fetch|retrieve).*(data|information)"
            ],
            IntentType.MODEL_TRAINING: [
                r"(train|build|create|develop)\s+(model|ai|ml)",
                r"(fit|learn).*(model|algorithm)",
                r"(improve|optimize).*(model|performance)",
                r"(train|teach).*model"
            ],
            IntentType.PREDICTION: [
                r"(predict|forecast|estimate|project)",
                r"(what|when|where).*(will|happen|occur)",
                r"(risk|hazard|probability)",
                r"(susceptibility|vulnerability)"
            ],
            IntentType.VISUALIZATION: [
                r"(plot|map|chart|graph|visualize|show)",
                r"(create).*(map|visualization)",
                r"(display|draw).*(result|output)"
            ],
            IntentType.LITERATURE_SEARCH: [
                r"(search|find|look for).*(paper|research|literature|article)",
                r"(what|latest).*(research|study)",
                r"(find|show).*(reference|citation)"
            ],
            IntentType.SYSTEM_STATUS: [
                r"(status|health|check).*(system|server)",
                r"(how).*(system|platform|service)",
                r"(available|working|active)"
            ],
            IntentType.HELP: [
                r"(help|assist|support|guide)",
                r"(how).*(?!.*predict|train|model)",
                r"(what can you do|what do you do)"
            ]
        }
    
    def _init_task_patterns(self) -> Dict[TaskType, List[str]]:
        """Initialize regex patterns for task detection"""
        return {
            TaskType.LANDSLIDE_SUSCEPTIBILITY: [
                r"(landslide|sliding|slope)",
                r"(landslide|slope).*susceptibility",
                r"(mass movement|rockslide)"
            ],
            TaskType.FLOOD_PREDICTION: [
                r"(flood|inundation|overflow|swelling)",
                r"(flood).*(?:prediction|mapping|risk)",
                r"(river|water).*flood"
            ],
            TaskType.EARTHQUAKE_DAMAGE: [
                r"(earthquake|seismic|tremor)",
                r"(earthquake|seismic).*(?:damage|impact|loss)",
                r"(ground shaking|seismic intensity)"
            ],
            TaskType.DROUGHT_MONITORING: [
                r"(drought|dry|water stress)",
                r"(drought|water).*monitoring",
                r"(precipitation|rainfall).*(deficit|lack)"
            ],
            TaskType.CROP_YIELD_PREDICTION: [
                r"(crop|yield|harvest|agriculture|farming)",
                r"(crop).*(?:yield|production|forecast)",
                r"(farm|agriculture).*prediction"
            ],
            TaskType.CLIMATE_ANALYSIS: [
                r"(climate|weather|temperature|rainfall)",
                r"(climate|weather).*(?:analysis|prediction|modeling)",
                r"(temperature|precipitation).*trend"
            ]
        }
    
    def extract_intent(self, query: str) -> ParsedIntent:
        """Extract intent from query"""
        query_lower = query.lower()
        
        if self.use_transformers:
            return self._extract_intent_transformers(query)
        else:
            return self._extract_intent_patterns(query)
    
    def _extract_intent_patterns(self, query: str) -> ParsedIntent:
        """Fallback: Extract intent using regex patterns"""
        query_lower = query.lower()
        
        # Detect intent
        best_intent = IntentType.UNKNOWN
        best_score = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    best_intent = intent
                    best_score = max(best_score, 0.7)
        
        # Detect task type
        task_type = None
        task_score = 0.0
        
        for task, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    task_type = task
                    task_score = 0.8
                    break
        
        # Extract entities
        entities = self._extract_entities_pattern(query)
        
        # Extract parameters
        parameters = self._extract_parameters(query, task_type)
        
        confidence = max(best_score, task_score)
        if best_intent == IntentType.UNKNOWN and task_type:
            confidence = 0.6
        
        return ParsedIntent(
            intent=best_intent,
            task_type=task_type,
            confidence=confidence,
            parameters=parameters,
            original_query=query,
            entities=entities
        )
    
    def _extract_intent_transformers(self, query: str) -> ParsedIntent:
        """Extract intent using transformer models"""
        intent_labels = [e.value for e in IntentType]
        task_labels = [t.value for t in TaskType]
        
        try:
            # Classify intent
            intent_result = self.classifier(query, intent_labels)
            best_intent_label = intent_result["labels"][0]
            intent_confidence = intent_result["scores"][0]
            best_intent = IntentType(best_intent_label)
            
            # Classify task
            task_type = None
            task_confidence = 0.0
            try:
                task_result = self.classifier(query, task_labels)
                task_label = task_result["labels"][0]
                task_confidence = task_result["scores"][0]
                if task_confidence > 0.5:
                    task_type = TaskType(task_label)
            except:
                pass
            
            # Extract entities
            entities = self._extract_entities_ner(query)
            
            # Extract parameters
            parameters = self._extract_parameters(query, task_type)
            
            return ParsedIntent(
                intent=best_intent,
                task_type=task_type,
                confidence=max(intent_confidence, task_confidence),
                parameters=parameters,
                original_query=query,
                entities=entities
            )
        except Exception as e:
            logger.error(f"Transformer inference error: {e}")
            return self._extract_intent_patterns(query)
    
    def _extract_entities_pattern(self, query: str) -> List[str]:
        """Extract entities using regex"""
        entities = []
        
        # Location patterns
        location_pattern = r"(area|region|zone|city|state)\s+of\s+(\w+)|(\w+)\s+(area|region|zone)"
        locations = re.findall(location_pattern, query, re.IGNORECASE)
        entities.extend([loc for match in locations for loc in match if loc])
        
        # Date patterns
        date_pattern = r"(from|since|between|during)\s+(\d{1,4}[-/]\d{1,2}[-/]\d{1,4})"
        dates = re.findall(date_pattern, query, re.IGNORECASE)
        entities.extend([date[1] for date in dates])
        
        # Numeric patterns
        number_pattern = r"(\d+(?:\.?\d+)?)\s*(meter|km|hectare|pixel|resolution)"
        numbers = re.findall(number_pattern, query, re.IGNORECASE)
        entities.extend([f"{num[0]}{num[1]}" for num in numbers])
        
        return entities[:10]
    
    def _extract_entities_ner(self, query: str) -> List[str]:
        """Extract entities using NER"""
        if not self.use_transformers:
            return self._extract_entities_pattern(query)
        
        try:
            entities = []
            ner_results = self.ner_pipeline(query)
            
            for result in ner_results:
                if result["score"] > 0.7:
                    entity = result["word"].replace("##", "")
                    entity_type = result["entity"]
                    entities.append(f"{entity}({entity_type})")
            
            return entities[:10]
        except Exception as e:
            logger.debug(f"NER error: {e}")
            return self._extract_entities_pattern(query)
    
    def _extract_parameters(self, query: str, task_type: Optional[TaskType]) -> Dict[str, Any]:
        """Extract parameters from query"""
        parameters = {}
        
        # Extract bounds (geographic)
        bounds_pattern = r"(latitude|lat)\s*[:\s=]+\s*([-\d.]+)\s*to\s*([-\d.]+)|" \
                        r"(longitude|lon)\s*[:\s=]+\s*([-\d.]+)\s*to\s*([-\d.]+)"
        bounds = re.findall(bounds_pattern, query, re.IGNORECASE)
        if bounds:
            parameters["has_bounds"] = True
        
        # Extract date range
        date_pattern = r"(from|between)\s+(\d{4}[-/]\d{2}[-/]\d{2})\s+(to|and)\s+(\d{4}[-/]\d{2}[-/]\d{2})"
        dates = re.findall(date_pattern, query, re.IGNORECASE)
        if dates:
            parameters["date_range"] = {"start": dates[0][1], "end": dates[0][3]}
        
        # Check for data sources
        if "sentinel" in query.lower():
            parameters["data_sources"] = ["sentinel"]
        elif "modis" in query.lower():
            parameters["data_sources"] = ["modis"]
        elif "terrain" in query.lower():
            parameters["data_sources"] = ["terrain"]
        
        # Check for model type preference
        model_keywords = ["random forest", "neural network", "cnn", "lstm", "ensemble", "gbm"]
        for keyword in model_keywords:
            if keyword in query.lower():
                parameters["preferred_model"] = keyword
                break
        
        # Check for visualization type
        viz_keywords = ["map", "chart", "graph", "heatmap", "distribution"]
        for keyword in viz_keywords:
            if keyword in query.lower():
                parameters["visualization_type"] = keyword
                break
        
        return parameters


class ChatbotResponseBuilder:
    """Build responses for different intents"""
    
    @staticmethod
    def build_response(parsed_intent: ParsedIntent, data: Optional[Dict] = None) -> Dict:
        """Build response based on parsed intent"""
        response = {
            "status": "success",
            "intent": parsed_intent.intent.value,
            "task_type": parsed_intent.task_type.value if parsed_intent.task_type else None,
            "confidence": parsed_intent.confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        if parsed_intent.intent == IntentType.DATA_ANALYSIS:
            response["action"] = "initiate_analysis"
            response["message"] = f"Starting data analysis for {parsed_intent.task_type.value if parsed_intent.task_type else 'your query'}..."
            response["parameters"] = parsed_intent.parameters
        
        elif parsed_intent.intent == IntentType.MODEL_TRAINING:
            response["action"] = "train_model"
            response["message"] = f"Preparing to train model for {parsed_intent.task_type.value if parsed_intent.task_type else 'your task'}..."
            response["parameters"] = parsed_intent.parameters
        
        elif parsed_intent.intent == IntentType.PREDICTION:
            response["action"] = "generate_prediction"
            response["message"] = f"Generating predictions for {parsed_intent.task_type.value if parsed_intent.task_type else 'the requested area'}..."
            response["parameters"] = parsed_intent.parameters
        
        elif parsed_intent.intent == IntentType.VISUALIZATION:
            response["action"] = "create_visualization"
            response["message"] = "Creating visualization of results..."
            response["parameters"] = parsed_intent.parameters
        
        elif parsed_intent.intent == IntentType.LITERATURE_SEARCH:
            response["action"] = "search_literature"
            response["message"] = "Searching latest research literature..."
            response["parameters"] = parsed_intent.parameters
        
        elif parsed_intent.intent == IntentType.SYSTEM_STATUS:
            response["action"] = "get_status"
            response["message"] = "Checking system status..."
            response["data"] = data or {}
        
        else:
            response["status"] = "error"
            response["message"] = "I didn't quite understand your request. Could you please rephrase?"
            response["suggestions"] = [
                "Ask me to analyze data for a specific region",
                "Request a prediction for landslide susceptibility",
                "Ask for the latest research on your topic"
            ]
        
        return response


class ChatbotService:
    """Main chatbot service"""
    
    def __init__(self):
        self.nlp_processor = NLPProcessor(use_transformers=TRANSFORMERS_AVAILABLE)
        self.response_builder = ChatbotResponseBuilder()
        self.conversation_history: Dict[str, List[Dict]] = {}
    
    def process_query(self, query: UserQuery) -> Dict:
        """Process user query and return response"""
        logger.info(f"Processing query from {query.user_id}: {query.text}")
        
        try:
            # Parse intent
            parsed_intent = self.nlp_processor.extract_intent(query.text)
            
            # Store in history
            if query.user_id:
                if query.user_id not in self.conversation_history:
                    self.conversation_history[query.user_id] = []
                
                self.conversation_history[query.user_id].append({
                    "query": query.text,
                    "intent": parsed_intent.intent.value,
                    "timestamp": query.timestamp,
                    "parameters": parsed_intent.parameters
                })
            
            # Build response
            response = self.response_builder.build_response(parsed_intent)
            response["user_id"] = query.user_id
            
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "message": f"An error occurred: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Get conversation history for user"""
        return self.conversation_history.get(user_id, [])
    
    def suggest_next_actions(self, parsed_intent: ParsedIntent) -> List[str]:
        """Suggest next actions based on parsed intent"""
        suggestions = []
        
        if parsed_intent.intent == IntentType.DATA_ANALYSIS:
            suggestions = [
                "Would you like to train a model on this data?",
                "Should I generate predictions?",
                "Would you like to visualize this data?"
            ]
        elif parsed_intent.intent == IntentType.MODEL_TRAINING:
            suggestions = [
                "Model training started. Check progress in dashboard.",
                "Would you like to make predictions with this model?",
                "View model performance metrics?"
            ]
        elif parsed_intent.intent == IntentType.PREDICTION:
            suggestions = [
                "Visualize the prediction results?",
                "Download prediction maps?",
                "Compare with other models?"
            ]
        
        return suggestions


# Singleton instance
_chatbot_service = None

def get_chatbot_service() -> ChatbotService:
    """Get or create chatbot service"""
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service
