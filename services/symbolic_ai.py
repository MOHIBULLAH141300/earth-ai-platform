"""
EarthAI Platform - Symbolic AI (GOFAI) Module
Implements knowledge representation, logical reasoning, and rule-based inference
"""

import re
from typing import Dict, List, Optional, Tuple, Any, Union, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


# ==================== Knowledge Representation ====================

@dataclass
class Concept:
    """Represents a concept in the knowledge base"""
    name: str
    category: str
    properties: Dict[str, Any] = field(default_factory=dict)
    synonyms: List[str] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    def __hash__(self):
        return hash(self.name)
    
    def add_property(self, property_name: str, value: Any):
        self.properties[property_name] = value
    
    def add_relationship(self, relation_type: str, target: str):
        self.relationships.setdefault(relation_type, []).append(target)
    
    def __repr__(self):
        return f"Concept({self.name}, {self.category})"


@dataclass
class Fact:
    """Represents a fact in the knowledge base"""
    subject: str
    predicate: str
    object: Union[str, float, int, bool]
    confidence: float = 1.0
    source: str = "asserted"
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.subject, self.predicate, str(self.object)))
    
    def to_triple(self) -> Tuple[str, str, Any]:
        return (self.subject, self.predicate, self.object)
    
    def __repr__(self):
        return f"Fact({self.subject} {self.predicate} {self.object})"


@dataclass
class Rule:
    """Represents an inference rule"""
    id: str
    name: str
    premises: List[Tuple[str, str, Any]]  # List of (subject, predicate, object) patterns
    conclusion: Tuple[str, str, Any]
    conditions: List[Callable] = field(default_factory=list)
    confidence: float = 1.0
    priority: int = 0
    
    def match_premises(self, facts: List[Fact], bindings: Dict[str, str] = None) -> List[Dict[str, str]]:
        """Match rule premises against facts, returning variable bindings"""
        if bindings is None:
            bindings = {}
        
        matches = []
        
        for premise in self.premises:
            premise_matches = self._match_premise(premise, facts, bindings.copy())
            if not premise_matches:
                return []
            
            if not matches:
                matches = premise_matches
            else:
                # Combine with existing matches
                new_matches = []
                for existing in matches:
                    for new_match in premise_matches:
                        combined = existing.copy()
                        combined.update(new_match)
                        if self._consistent_bindings(existing, new_match):
                            new_matches.append(combined)
                matches = new_matches
                
                if not matches:
                    return []
        
        return matches
    
    def _match_premise(
        self,
        premise: Tuple[str, str, Any],
        facts: List[Fact],
        bindings: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Match a single premise against facts"""
        matches = []
        
        subj_pattern = premise[0]
        pred_pattern = premise[1]
        obj_pattern = premise[2]
        
        for fact in facts:
            # Check predicate match (must be exact or variable)
            if pred_pattern.startswith("?"):
                pred_match = True
            elif pred_pattern != fact.predicate:
                continue
            else:
                pred_match = True
            
            # Check subject match
            if subj_pattern.startswith("?"):
                subj_match = True
                # Add binding
                var_name = subj_pattern[1:]
                if var_name in bindings and bindings[var_name] != fact.subject:
                    continue
                bindings[var_name] = fact.subject
            elif subj_pattern != fact.subject:
                continue
            else:
                subj_match = True
            
            # Check object match
            if isinstance(obj_pattern, str) and obj_pattern.startswith("?"):
                obj_match = True
                var_name = obj_pattern[1:]
                if var_name in bindings and bindings[var_name] != str(fact.object):
                    continue
                bindings[var_name] = str(fact.object)
            elif str(obj_pattern) != str(fact.object):
                continue
            else:
                obj_match = True
            
            if pred_match and subj_match and obj_match:
                matches.append(bindings.copy())
        
        return matches
    
    def _consistent_bindings(self, bindings1: Dict[str, str], bindings2: Dict[str, str]) -> bool:
        """Check if two sets of bindings are consistent"""
        for var, val in bindings1.items():
            if var in bindings2 and bindings2[var] != val:
                return False
        return True
    
    def apply(self, bindings: Dict[str, str]) -> Optional[Fact]:
        """Apply bindings to conclusion to generate new fact"""
        conclusion = list(self.conclusion)
        
        for i, component in enumerate(conclusion):
            if isinstance(component, str) and component.startswith("?"):
                var_name = component[1:]
                if var_name in bindings:
                    conclusion[i] = bindings[var_name]
                else:
                    return None  # Unbound variable
        
        return Fact(
            subject=conclusion[0],
            predicate=conclusion[1],
            object=conclusion[2],
            confidence=self.confidence,
            source=f"inferred_from_{self.id}"
        )


# ==================== Knowledge Base ====================

class SymbolicKnowledgeBase:
    """Knowledge base for symbolic AI"""
    
    def __init__(self, name: str = "earth_kb"):
        self.name = name
        self.concepts: Dict[str, Concept] = {}
        self.facts: Set[Fact] = set()
        self.rules: List[Rule] = []
        self.inferred_facts: Set[Fact] = set()
        self.fact_index: Dict[str, Set[Fact]] = defaultdict(set)
        
    def add_concept(self, concept: Concept):
        """Add concept to knowledge base"""
        self.concepts[concept.name] = concept
        
        # Add synonyms
        for syn in concept.synonyms:
            if syn not in self.concepts:
                self.concepts[syn] = concept
    
    def add_fact(self, fact: Fact):
        """Add fact to knowledge base"""
        self.facts.add(fact)
        
        # Index by subject
        self.fact_index[fact.subject].add(fact)
        
        # Index by predicate
        self.fact_index[fact.predicate].add(fact)
        
        # Index by object
        self.fact_index[str(fact.object)].add(fact)
        
        logger.debug(f"Added fact: {fact}")
    
    def query(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        object: Optional[Any] = None
    ) -> List[Fact]:
        """Query facts by pattern"""
        # Start with all facts
        candidates = self.facts.copy()
        
        # Filter by subject
        if subject and not subject.startswith("?"):
            candidates = candidates & self.fact_index.get(subject, set())
        
        # Filter by predicate
        if predicate and not predicate.startswith("?"):
            candidates = candidates & self.fact_index.get(predicate, set())
        
        # Filter by object
        if object is not None and not (isinstance(object, str) and object.startswith("?")):
            candidates = {f for f in candidates if str(f.object) == str(object)}
        
        return list(candidates)
    
    def add_rule(self, rule: Rule):
        """Add inference rule"""
        self.rules.append(rule)
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug(f"Added rule: {rule.name}")
    
    def get_related_concepts(self, concept_name: str, relation_type: Optional[str] = None) -> List[str]:
        """Get concepts related to given concept"""
        concept = self.concepts.get(concept_name)
        if not concept:
            return []
        
        if relation_type:
            return concept.relationships.get(relation_type, [])
        
        # Return all related concepts
        related = []
        for rel_type, targets in concept.relationships.items():
            related.extend(targets)
        
        return related


# ==================== Inference Engine ====================

class ForwardChainingEngine:
    """Forward chaining inference engine"""
    
    def __init__(self, knowledge_base: SymbolicKnowledgeBase):
        self.kb = knowledge_base
        self.max_iterations = 1000
        self.confidence_threshold = 0.5
    
    def infer(self, goal: Optional[Fact] = None) -> List[Fact]:
        """Run forward chaining inference"""
        inferred = []
        iteration = 0
        
        # Work with all facts including previously inferred
        working_facts = self.kb.facts | self.kb.inferred_facts
        
        while iteration < self.max_iterations:
            iteration += 1
            new_inferences = []
            
            # Try each rule
            for rule in self.kb.rules:
                # Match premises
                bindings_list = rule.match_premises(list(working_facts))
                
                for bindings in bindings_list:
                    # Check additional conditions
                    conditions_met = all(
                        condition(bindings) for condition in rule.conditions
                    ) if rule.conditions else True
                    
                    if conditions_met:
                        # Apply rule
                        new_fact = rule.apply(bindings)
                        
                        if new_fact and new_fact not in working_facts:
                            if new_fact.confidence >= self.confidence_threshold:
                                new_inferences.append(new_fact)
            
            if not new_inferences:
                break
            
            # Add new inferences
            for fact in new_inferences:
                working_facts.add(fact)
                self.kb.inferred_facts.add(fact)
                self.kb.add_fact(fact)
                inferred.append(fact)
                
                # Check if goal reached
                if goal and fact == goal:
                    logger.info(f"Goal reached: {goal}")
                    return inferred
            
            logger.info(f"Iteration {iteration}: {len(new_inferences)} new facts inferred")
        
        return inferred


class BackwardChainingEngine:
    """Backward chaining inference engine"""
    
    def __init__(self, knowledge_base: SymbolicKnowledgeBase):
        self.kb = knowledge_base
        self.max_depth = 20
    
    def prove(self, goal: Fact, depth: int = 0, visited: Set[str] = None) -> Tuple[bool, List[Fact]]:
        """Try to prove a goal using backward chaining"""
        if visited is None:
            visited = set()
        
        if depth > self.max_depth:
            return False, []
        
        goal_key = f"{goal.subject}-{goal.predicate}-{goal.object}"
        if goal_key in visited:
            return False, []
        visited.add(goal_key)
        
        # Check if goal is in facts
        if goal in self.kb.facts or goal in self.kb.inferred_facts:
            return True, [goal]
        
        # Find rules that can derive the goal
        for rule in self.kb.rules:
            # Check if rule conclusion matches goal
            conclusion = rule.conclusion
            
            if conclusion[1] == goal.predicate:  # Same predicate
                # Try to unify conclusion with goal
                bindings = self._unify_conclusion(conclusion, goal)
                
                if bindings is not None:
                    # Try to prove all premises
                    all_proven = True
                    proof_chain = []
                    
                    for premise in rule.premises:
                        # Apply bindings to premise
                        premise_fact = self._apply_bindings(premise, bindings)
                        
                        # Recursively prove premise
                        proven, chain = self.prove(premise_fact, depth + 1, visited.copy())
                        
                        if not proven:
                            all_proven = False
                            break
                        
                        proof_chain.extend(chain)
                    
                    if all_proven:
                        # Add inferred fact
                        inferred = rule.apply(bindings)
                        if inferred:
                            self.kb.inferred_facts.add(inferred)
                            proof_chain.append(inferred)
                            return True, proof_chain
        
        return False, []
    
    def _unify_conclusion(
        self,
        conclusion: Tuple[str, str, Any],
        goal: Fact
    ) -> Optional[Dict[str, str]]:
        """Try to unify rule conclusion with goal"""
        bindings = {}
        
        # Check predicate
        if conclusion[1] != goal.predicate:
            return None
        
        # Unify subject
        if conclusion[0].startswith("?"):
            bindings[conclusion[0][1:]] = goal.subject
        elif conclusion[0] != goal.subject:
            return None
        
        # Unify object
        if isinstance(conclusion[2], str) and conclusion[2].startswith("?"):
            bindings[conclusion[2][1:]] = str(goal.object)
        elif str(conclusion[2]) != str(goal.object):
            return None
        
        return bindings
    
    def _apply_bindings(
        self,
        pattern: Tuple[str, str, Any],
        bindings: Dict[str, str]
    ) -> Fact:
        """Apply bindings to a pattern to create a fact"""
        result = list(pattern)
        
        for i, component in enumerate(result):
            if isinstance(component, str) and component.startswith("?"):
                var_name = component[1:]
                if var_name in bindings:
                    result[i] = bindings[var_name]
        
        return Fact(
            subject=result[0],
            predicate=result[1],
            object=result[2]
        )


# ==================== Natural Language Interface ====================

class NLParser:
    """Simple natural language parser for knowledge base queries"""
    
    def __init__(self, knowledge_base: SymbolicKnowledgeBase):
        self.kb = knowledge_base
        
        # Define parsing patterns
        self.patterns = {
            "what_is": re.compile(r"what is (.+?)(\?|$)", re.IGNORECASE),
            "what_are": re.compile(r"what are (.+?)(\?|$)", re.IGNORECASE),
            "is_a": re.compile(r"is (.+?) a (.+?)(\?|$)", re.IGNORECASE),
            "has_property": re.compile(r"does (.+?) have (.+?)(\?|$)", re.IGNORECASE),
            "relationship": re.compile(r"what is the relationship between (.+?) and (.+?)(\?|$)", re.IGNORECASE),
            "cause_effect": re.compile(r"what causes (.+?)(\?|$)", re.IGNORECASE),
        }
    
    def parse(self, query: str) -> Dict[str, Any]:
        """Parse natural language query"""
        
        # Try each pattern
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(query)
            if match:
                return {
                    "pattern": pattern_name,
                    "groups": match.groups()
                }
        
        return {"pattern": "unknown", "groups": (query,)}
    
    def execute(self, query: str) -> str:
        """Parse and execute natural language query"""
        parsed = self.parse(query)
        
        if parsed["pattern"] == "what_is":
            concept_name = parsed["groups"][0].strip()
            return self._describe_concept(concept_name)
        
        elif parsed["pattern"] == "what_are":
            concept_name = parsed["groups"][0].strip()
            return self._list_instances(concept_name)
        
        elif parsed["pattern"] == "is_a":
            subject = parsed["groups"][0].strip()
            category = parsed["groups"][1].strip()
            return self._check_is_a(subject, category)
        
        elif parsed["pattern"] == "has_property":
            subject = parsed["groups"][0].strip()
            property_name = parsed["groups"][1].strip()
            return self._check_property(subject, property_name)
        
        elif parsed["pattern"] == "relationship":
            concept1 = parsed["groups"][0].strip()
            concept2 = parsed["groups"][1].strip()
            return self._find_relationship(concept1, concept2)
        
        elif parsed["pattern"] == "cause_effect":
            effect = parsed["groups"][0].strip()
            return self._find_causes(effect)
        
        return f"I don't understand the query: '{query}'"
    
    def _describe_concept(self, concept_name: str) -> str:
        """Describe a concept"""
        concept = self.kb.concepts.get(concept_name)
        
        if not concept:
            return f"I don't know about '{concept_name}'"
        
        description = f"{concept.name} is a {concept.category}."
        
        if concept.properties:
            props = ", ".join([f"{k}={v}" for k, v in concept.properties.items()])
            description += f" Properties: {props}."
        
        if concept.relationships:
            rels = []
            for rel_type, targets in concept.relationships.items():
                rels.append(f"{rel_type}: {', '.join(targets)}")
            description += " " + "; ".join(rels)
        
        return description
    
    def _list_instances(self, concept_name: str) -> str:
        """List instances of a concept"""
        concept = self.kb.concepts.get(concept_name)
        
        if not concept:
            return f"I don't know about '{concept_name}'"
        
        # Find all instances (facts where subject has this type)
        instances = self.kb.query(predicate="type", object=concept_name)
        
        if not instances:
            return f"No instances of '{concept_name}' found"
        
        names = [f.subject for f in instances]
        return f"Instances of {concept_name}: {', '.join(names)}"
    
    def _check_is_a(self, subject: str, category: str) -> str:
        """Check if subject is a category"""
        # Check facts
        facts = self.kb.query(subject=subject, predicate="type", object=category)
        
        if facts:
            return f"Yes, {subject} is a {category}"
        
        # Check if subject has parent that is category
        parent_facts = self.kb.query(subject=subject, predicate="subclass_of")
        for fact in parent_facts:
            parent = fact.object
            parent_facts = self.kb.query(subject=parent, predicate="type", object=category)
            if parent_facts:
                return f"Yes, {subject} is a {category} (via {parent})"
        
        return f"No, I don't know if {subject} is a {category}"
    
    def _check_property(self, subject: str, property_name: str) -> str:
        """Check if subject has property"""
        facts = self.kb.query(subject=subject, predicate=property_name)
        
        if facts:
            values = [str(f.object) for f in facts]
            return f"Yes, {subject} has {property_name}: {', '.join(values)}"
        
        return f"No information about {property_name} for {subject}"
    
    def _find_relationship(self, concept1: str, concept2: str) -> str:
        """Find relationship between two concepts"""
        concept = self.kb.concepts.get(concept1)
        
        if not concept:
            return f"I don't know about '{concept1}'"
        
        relationships = []
        for rel_type, targets in concept.relationships.items():
            if concept2 in targets:
                relationships.append(rel_type)
        
        if relationships:
            return f"{concept1} is related to {concept2} by: {', '.join(relationships)}"
        
        # Check reverse
        concept2_obj = self.kb.concepts.get(concept2)
        if concept2_obj:
            for rel_type, targets in concept2_obj.relationships.items():
                if concept1 in targets:
                    relationships.append(f"{rel_type} (reverse)")
        
        if relationships:
            return f"{concept1} is related to {concept2} by: {', '.join(relationships)}"
        
        return f"No direct relationship found between {concept1} and {concept2}"
    
    def _find_causes(self, effect: str) -> str:
        """Find causes of an effect"""
        # Look for causes in facts
        cause_facts = self.kb.query(predicate="causes", object=effect)
        
        if cause_facts:
            causes = [f.subject for f in cause_facts]
            return f"Causes of {effect}: {', '.join(causes)}"
        
        # Check rules
        causes = []
        for rule in self.kb.rules:
            if rule.conclusion[2] == effect:
                causes.append(rule.name)
        
        if causes:
            return f"Potential causes of {effect}: {', '.join(causes)}"
        
        return f"No known causes found for {effect}"


# ==================== Earth System Ontology ====================

class EarthSystemOntology:
    """Pre-built ontology for Earth system modeling"""
    
    def __init__(self):
        self.kb = SymbolicKnowledgeBase("earth_ontology")
        self._setup_ontology()
    
    def _setup_ontology(self):
        """Setup Earth system ontology"""
        
        # Geographic features
        geographic_features = [
            Concept("mountain", "geographic_feature", 
                   properties={"elevation_min": 600, "slope_typical": "steep"}),
            Concept("hill", "geographic_feature",
                   properties={"elevation_min": 100, "elevation_max": 600}),
            Concept("plain", "geographic_feature",
                   properties={"slope_typical": "flat", "elevation_max": 200}),
            Concept("valley", "geographic_feature",
                   properties={"elevation_typical": "low", "formed_by": "erosion"}),
            Concept("river", "geographic_feature",
                   properties={"flow_direction": "downhill", "water_type": "freshwater"}),
            Concept("lake", "geographic_feature",
                   properties={"water_type": "freshwater", "enclosed": True}),
            Concept("ocean", "geographic_feature",
                   properties={"water_type": "saltwater", "size": "very_large"}),
        ]
        
        for concept in geographic_features:
            self.kb.add_concept(concept)
        
        # Soil types
        soil_types = [
            Concept("clay_soil", "soil_type",
                   properties={"particle_size": "small", "water_retention": "high"}),
            Concept("sandy_soil", "soil_type",
                   properties={"particle_size": "large", "water_retention": "low"}),
            Concept("loam", "soil_type",
                   properties={"texture": "balanced", "fertility": "high"}),
            Concept("rocky_soil", "soil_type",
                   properties={"stability": "high", "erosion_risk": "low"}),
        ]
        
        for concept in soil_types:
            self.kb.add_concept(concept)
        
        # Natural hazards
        hazards = [
            Concept("landslide", "natural_hazard",
                   properties={"trigger": "gravity", "speed": "variable"},
                   relationships={"caused_by": ["heavy_rain", "earthquake", "deforestation"],
                                "affects": ["infrastructure", "human_life"]}),
            Concept("earthquake", "natural_hazard",
                   properties={"origin": "tectonic", "prediction": "difficult"},
                   relationships={"caused_by": ["plate_movement"],
                                "triggers": ["landslide", "tsunami"]}),
            Concept("flood", "natural_hazard",
                   properties={"trigger": "water", "area": "widespread"},
                   relationships={"caused_by": ["heavy_rain", "dam_failure"],
                                "affects": ["agriculture", "property"]}),
            Concept("wildfire", "natural_hazard",
                   properties={"trigger": "heat", "spread": "fast"},
                   relationships={"caused_by": ["drought", "lightning", "human_activity"],
                                "affects": ["forest", "wildlife"]}),
            Concept("drought", "natural_hazard",
                   properties={"duration": "long", "area": "widespread"},
                   relationships={"caused_by": ["climate_change", "lack_of_rain"],
                                "affects": ["agriculture", "water_supply"]}),
        ]
        
        for concept in hazards:
            self.kb.add_concept(concept)
        
        # Vegetation types
        vegetation = [
            Concept("forest", "vegetation",
                   properties={"density": "high", "carbon_absorption": "high"},
                   relationships={"prevents": ["erosion", "landslide"]}),
            Concept("grassland", "vegetation",
                   properties={"density": "medium", "root_depth": "shallow"}),
            Concept("wetland", "vegetation",
                   properties={"water_content": "high", "biodiversity": "high"}),
            Concept("desert", "vegetation",
                   properties={"density": "very_low", "water_availability": "scarce"}),
        ]
        
        for concept in vegetation:
            self.kb.add_concept(concept)
        
        # Add relationships between concepts
        mountain = self.kb.concepts["mountain"]
        mountain.add_relationship("has_soil_type", "rocky_soil")
        mountain.add_relationship("has_vegetation", "forest")
        mountain.add_relationship("susceptible_to", "landslide")
        
        forest = self.kb.concepts["forest"]
        forest.add_relationship("prevents", "landslide")
        forest.add_relationship("prevents", "erosion")
        forest.add_relationship("located_on", "mountain")
        forest.add_relationship("located_on", "hill")
        
        # Add inference rules
        rules = [
            Rule(
                id="R001",
                name="Mountain Landslide Risk",
                premises=[
                    ("?x", "type", "mountain"),
                    ("?x", "has_vegetation", "sparse")
                ],
                conclusion=("?x", "has_risk", "landslide"),
                confidence=0.8,
                priority=10
            ),
            Rule(
                id="R002",
                name="Forest Protection",
                premises=[
                    ("?x", "has_vegetation", "forest"),
                    ("?x", "slope", "?s")
                ],
                conclusion=("?x", "reduces_risk", "landslide"),
                conditions=[lambda b: float(b.get("s", 0)) < 45],
                confidence=0.75,
                priority=8
            ),
            Rule(
                id="R003",
                name="Clay Soil Risk",
                premises=[
                    ("?x", "has_soil_type", "clay_soil"),
                    ("?x", "has_rainfall", "heavy")
                ],
                conclusion=("?x", "has_risk", "landslide"),
                confidence=0.85,
                priority=9
            ),
            Rule(
                id="R004",
                name="Earthquake Trigger",
                premises=[
                    ("?x", "experienced", "earthquake"),
                    ("?x", "slope", "?s")
                ],
                conclusion=("?x", "has_risk", "landslide"),
                conditions=[lambda b: float(b.get("s", 0)) > 15],
                confidence=0.9,
                priority=10
            ),
        ]
        
        for rule in rules:
            self.kb.add_rule(rule)
        
        # Add sample facts
        facts = [
            Fact("area_1", "type", "mountain"),
            Fact("area_1", "elevation", 1500),
            Fact("area_1", "slope", 35),
            Fact("area_1", "has_soil_type", "clay_soil"),
            Fact("area_1", "has_vegetation", "sparse"),
            Fact("area_1", "has_rainfall", "heavy"),
            
            Fact("area_2", "type", "hill"),
            Fact("area_2", "elevation", 400),
            Fact("area_2", "slope", 25),
            Fact("area_2", "has_soil_type", "loam"),
            Fact("area_2", "has_vegetation", "forest"),
            
            Fact("area_3", "type", "plain"),
            Fact("area_3", "elevation", 50),
            Fact("area_3", "slope", 2),
            Fact("area_3", "has_soil_type", "sandy_soil"),
        ]
        
        for fact in facts:
            self.kb.add_fact(fact)
    
    def query(self, **kwargs) -> List[Fact]:
        """Query the ontology"""
        return self.kb.query(**kwargs)
    
    def reason(self, goal: Optional[Fact] = None) -> List[Fact]:
        """Run forward chaining inference"""
        engine = ForwardChainingEngine(self.kb)
        return engine.infer(goal)
    
    def ask(self, query: str) -> str:
        """Natural language interface"""
        parser = NLParser(self.kb)
        return parser.execute(query)
    
    def get_concept(self, name: str) -> Optional[Concept]:
        """Get concept by name"""
        return self.kb.concepts.get(name)


# Example usage
if __name__ == "__main__":
    print("=== Earth System Ontology ===\n")
    
    # Create ontology
    ontology = EarthSystemOntology()
    
    # Test natural language queries
    queries = [
        "What is mountain?",
        "What is landslide?",
        "Is area_1 a mountain?",
        "Does area_1 have vegetation?",
        "What is the relationship between mountain and landslide?",
        "What causes landslide?",
    ]
    
    print("Natural Language Queries:")
    for query in queries:
        print(f"\nQ: {query}")
        print(f"A: {ontology.ask(query)}")
    
    # Test inference
    print("\n\n=== Inference ===")
    inferred = ontology.reason()
    
    print(f"Inferred facts ({len(inferred)}):")
    for fact in inferred:
        print(f"  {fact}")
    
    # Check specific risk
    print("\n\nRisk Assessment:")
    risk_facts = ontology.query(predicate="has_risk", object="landslide")
    for fact in risk_facts:
        print(f"  {fact.subject}: {fact.predicate} {fact.object} (confidence: {fact.confidence:.2f})")
