"""
EarthAI Platform - Expert System & Fuzzy Logic Module
Implements rule-based reasoning and fuzzy inference for environmental decision-making
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from collections import defaultdict
import skfuzzy as fuzz
from skfuzzy import control as ctrl

logger = logging.getLogger(__name__)


# ==================== Expert System ====================

class RuleOperator(Enum):
    """Logical operators for rule conditions"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "=="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    BETWEEN = "BETWEEN"
    IN = "IN"


@dataclass
class Condition:
    """Single condition in a rule"""
    variable: str
    operator: RuleOperator
    value: Any
    weight: float = 1.0
    
    def evaluate(self, facts: Dict[str, Any]) -> bool:
        """Evaluate condition against facts"""
        if self.variable not in facts:
            return False
        
        fact_value = facts[self.variable]
        
        if self.operator == RuleOperator.GREATER_THAN:
            return fact_value > self.value
        elif self.operator == RuleOperator.LESS_THAN:
            return fact_value < self.value
        elif self.operator == RuleOperator.EQUAL:
            return fact_value == self.value
        elif self.operator == RuleOperator.GREATER_EQUAL:
            return fact_value >= self.value
        elif self.operator == RuleOperator.LESS_EQUAL:
            return fact_value <= self.value
        elif self.operator == RuleOperator.BETWEEN:
            return self.value[0] <= fact_value <= self.value[1]
        elif self.operator == RuleOperator.IN:
            return fact_value in self.value
        
        return False
    
    def __str__(self):
        if self.operator == RuleOperator.BETWEEN:
            return f"{self.variable} BETWEEN {self.value[0]} AND {self.value[1]}"
        return f"{self.variable} {self.operator.value} {self.value}"


@dataclass
class Rule:
    """Production rule for expert system"""
    id: str
    name: str
    conditions: List[Condition]
    conclusion: str
    action: str
    confidence: float = 1.0
    priority: int = 0
    enabled: bool = True
    
    def evaluate(self, facts: Dict[str, Any]) -> Tuple[bool, float]:
        """Evaluate rule against facts"""
        if not self.enabled:
            return False, 0.0
        
        if not self.conditions:
            return True, self.confidence
        
        # Evaluate all conditions
        results = [cond.evaluate(facts) for cond in self.conditions]
        weights = [cond.weight for cond in self.conditions]
        
        # Calculate weighted confidence
        if results:
            weighted_sum = sum(r * w for r, w in zip(results, weights))
            total_weight = sum(weights)
            confidence = (weighted_sum / total_weight) * self.confidence
            
            # Rule fires if all conditions are met
            fires = all(results)
            return fires, confidence if fires else 0.0
        
        return True, self.confidence


@dataclass
class InferenceResult:
    """Result from inference engine"""
    rule_id: str
    rule_name: str
    conclusion: str
    action: str
    confidence: float
    triggered_conditions: List[str]
    timestamp: str = field(default_factory=lambda: str(np.datetime64('now')))


class KnowledgeBase:
    """Knowledge base for storing facts and rules"""
    
    def __init__(self, knowledge_file: Optional[str] = None):
        self.facts: Dict[str, Any] = {}
        self.rules: Dict[str, Rule] = {}
        self.fact_history: List[Dict[str, Any]] = []
        
        if knowledge_file:
            self.load_from_file(knowledge_file)
    
    def add_fact(self, name: str, value: Any, source: str = "user"):
        """Add a fact to the knowledge base"""
        self.facts[name] = {"value": value, "source": source, "timestamp": str(np.datetime64('now'))}
        self.fact_history.append({name: value})
        logger.debug(f"Added fact: {name} = {value}")
    
    def get_fact(self, name: str) -> Optional[Any]:
        """Get fact value"""
        fact = self.facts.get(name)
        return fact["value"] if fact else None
    
    def add_rule(self, rule: Rule):
        """Add a rule to the knowledge base"""
        self.rules[rule.id] = rule
        logger.debug(f"Added rule: {rule.name}")
    
    def remove_rule(self, rule_id: str):
        """Remove a rule from the knowledge base"""
        if rule_id in self.rules:
            del self.rules[rule_id]
    
    def load_from_file(self, filepath: str):
        """Load knowledge base from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Load facts
        for name, value in data.get("facts", {}).items():
            self.add_fact(name, value)
        
        # Load rules
        for rule_data in data.get("rules", []):
            conditions = [
                Condition(
                    c["variable"],
                    RuleOperator(c["operator"]),
                    c["value"],
                    c.get("weight", 1.0)
                )
                for c in rule_data["conditions"]
            ]
            
            rule = Rule(
                id=rule_data["id"],
                name=rule_data["name"],
                conditions=conditions,
                conclusion=rule_data["conclusion"],
                action=rule_data["action"],
                confidence=rule_data.get("confidence", 1.0),
                priority=rule_data.get("priority", 0)
            )
            self.add_rule(rule)
    
    def save_to_file(self, filepath: str):
        """Save knowledge base to JSON file"""
        data = {
            "facts": {name: fact["value"] for name, fact in self.facts.items()},
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "conditions": [
                        {
                            "variable": c.variable,
                            "operator": c.operator.value,
                            "value": c.value,
                            "weight": c.weight
                        }
                        for c in rule.conditions
                    ],
                    "conclusion": rule.conclusion,
                    "action": rule.action,
                    "confidence": rule.confidence,
                    "priority": rule.priority
                }
                for rule in self.rules.values()
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class InferenceEngine:
    """Forward chaining inference engine"""
    
    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.inference_log: List[InferenceResult] = []
        self.max_iterations = 100
    
    def infer(self, goal: Optional[str] = None) -> List[InferenceResult]:
        """Run forward chaining inference"""
        
        results = []
        fired_rules = set()
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            new_facts_added = False
            
            # Get current facts
            facts = {name: fact["value"] for name, fact in self.kb.facts.items()}
            
            # Sort rules by priority
            sorted_rules = sorted(
                self.kb.rules.values(),
                key=lambda r: r.priority,
                reverse=True
            )
            
            # Evaluate each rule
            for rule in sorted_rules:
                if rule.id in fired_rules:
                    continue
                
                fires, confidence = rule.evaluate(facts)
                
                if fires and confidence > 0.5:
                    fired_rules.add(rule.id)
                    new_facts_added = True
                    
                    # Record inference
                    result = InferenceResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        conclusion=rule.conclusion,
                        action=rule.action,
                        confidence=confidence,
                        triggered_conditions=[str(c) for c in rule.conditions]
                    )
                    results.append(result)
                    self.inference_log.append(result)
                    
                    # Add inferred fact
                    self.kb.add_fact(rule.conclusion, True, f"inferred_from_{rule.id}")
                    
                    logger.info(f"Rule fired: {rule.name} (confidence: {confidence:.2f})")
                    
                    # Check if goal reached
                    if goal and rule.conclusion == goal:
                        return results
            
            # If no new rules fired, stop
            if not new_facts_added:
                break
        
        return results
    
    def explain(self, result: InferenceResult) -> str:
        """Generate explanation for inference result"""
        explanation = [
            f"Rule '{result.rule_name}' (ID: {result.rule_id}) was triggered because:",
            "Conditions met:"
        ]
        
        for condition in result.triggered_conditions:
            explanation.append(f"  - {condition}")
        
        explanation.extend([
            f"",
            f"Conclusion: {result.conclusion}",
            f"Confidence: {result.confidence:.2%}",
            f"Suggested Action: {result.action}",
            f"Timestamp: {result.timestamp}"
        ])
        
        return "\n".join(explanation)
    
    def get_inference_chain(self, conclusion: str) -> List[InferenceResult]:
        """Get chain of inferences leading to a conclusion"""
        return [
            result for result in self.inference_log
            if result.conclusion == conclusion
        ]


# ==================== Fuzzy Logic System ====================

class FuzzyVariable:
    """Fuzzy linguistic variable"""
    
    def __init__(
        self,
        name: str,
        universe: np.ndarray,
        membership_functions: Dict[str, Any]
    ):
        self.name = name
        self.universe = universe
        self.membership_functions = membership_functions
        self.antecedent = ctrl.Antecedent(universe, name)
        
        # Add membership functions
        for mf_name, mf_params in membership_functions.items():
            if isinstance(mf_params, dict):
                self.antecedent[mf_name] = fuzz.trapmf(
                    universe,
                    mf_params.get("points", [0, 0.25, 0.5, 0.75])
                )
            else:
                self.antecedent[mf_name] = mf_params
    
    def __getitem__(self, key: str):
        return self.antecedent[key]
    
    def __getattr__(self, name: str):
        return getattr(self.antecedent, name)


class FuzzyOutput:
    """Fuzzy output variable"""
    
    def __init__(
        self,
        name: str,
        universe: np.ndarray,
        membership_functions: Dict[str, Any],
        defuzz_method: str = "centroid"
    ):
        self.name = name
        self.universe = universe
        self.membership_functions = membership_functions
        self.defuzz_method = defuzz_method
        self.consequent = ctrl.Consequent(universe, name)
        
        # Add membership functions
        for mf_name, mf_params in membership_functions.items():
            if isinstance(mf_params, dict):
                self.consequent[mf_name] = fuzz.trapmf(
                    universe,
                    mf_params.get("points", [0, 0.25, 0.5, 0.75])
                )
            else:
                self.consequent[mf_name] = mf_params
    
    def __getitem__(self, key: str):
        return self.consequent[key]
    
    def __getattr__(self, name: str):
        return getattr(self.consequent, name)


class FuzzyRule:
    """Fuzzy rule"""
    
    def __init__(
        self,
        antecedents: List[Tuple[FuzzyVariable, str]],
        consequent: Tuple[FuzzyOutput, str],
        operator: str = "AND"
    ):
        self.antecedents = antecedents
        self.consequent = consequent
        self.operator = operator
        self.rule = self._build_rule()
    
    def _build_rule(self) -> ctrl.Rule:
        """Build skfuzzy rule"""
        if self.operator == "AND":
            antecedent = self.antecedents[0][0][self.antecedents[0][1]]
            for var, term in self.antecedents[1:]:
                antecedent = antecedent & var[term]
        else:  # OR
            antecedent = self.antecedents[0][0][self.antecedents[0][1]]
            for var, term in self.antecedents[1:]:
                antecedent = antecedent | var[term]
        
        consequent = self.consequent[0][self.consequent[1]]
        
        return ctrl.Rule(antecedent, consequent)


class FuzzyInferenceSystem:
    """Fuzzy inference system for environmental decision-making"""
    
    def __init__(self, name: str = "EarthSystemFIS"):
        self.name = name
        self.inputs: Dict[str, FuzzyVariable] = {}
        self.outputs: Dict[str, FuzzyOutput] = {}
        self.rules: List[FuzzyRule] = []
        self.control_system: Optional[ctrl.ControlSystem] = None
        self.simulation: Optional[ctrl.ControlSystemSimulation] = None
        self.initialized = False
    
    def add_input(
        self,
        name: str,
        universe: np.ndarray,
        membership_functions: Dict[str, Any]
    ):
        """Add input variable"""
        self.inputs[name] = FuzzyVariable(name, universe, membership_functions)
        self.initialized = False
    
    def add_output(
        self,
        name: str,
        universe: np.ndarray,
        membership_functions: Dict[str, Any],
        defuzz_method: str = "centroid"
    ):
        """Add output variable"""
        self.outputs[name] = FuzzyOutput(name, universe, membership_functions, defuzz_method)
        self.initialized = False
    
    def add_rule(
        self,
        antecedents: List[Tuple[str, str]],  # [(input_name, term), ...]
        consequent: Tuple[str, str],  # (output_name, term)
        operator: str = "AND"
    ):
        """Add fuzzy rule"""
        # Resolve antecedents
        resolved_ants = []
        for input_name, term in antecedents:
            if input_name not in self.inputs:
                raise ValueError(f"Unknown input: {input_name}")
            resolved_ants.append((self.inputs[input_name], term))
        
        # Resolve consequent
        output_name, term = consequent
        if output_name not in self.outputs:
            raise ValueError(f"Unknown output: {output_name}")
        
        rule = FuzzyRule(resolved_ants, (self.outputs[output_name], term), operator)
        self.rules.append(rule)
        self.initialized = False
    
    def build(self):
        """Build control system"""
        if not self.rules:
            raise ValueError("No rules defined")
        
        # Build control system
        rules = [rule.rule for rule in self.rules]
        self.control_system = ctrl.ControlSystem(rules)
        self.simulation = ctrl.ControlSystemSimulation(self.control_system)
        self.initialized = True
        
        logger.info(f"FIS built with {len(self.rules)} rules")
    
    def compute(
        self,
        inputs: Dict[str, float]
    ) -> Dict[str, float]:
        """Compute fuzzy inference"""
        
        if not self.initialized:
            self.build()
        
        # Set inputs
        for name, value in inputs.items():
            if name not in self.inputs:
                raise ValueError(f"Unknown input: {name}")
            self.simulation.input[name] = value
        
        # Compute
        self.simulation.compute()
        
        # Get outputs
        outputs = {}
        for name in self.outputs:
            outputs[name] = self.simulation.output[name]
        
        return outputs
    
    def visualize_membership(self, variable_name: str):
        """Visualize membership functions"""
        import matplotlib.pyplot as plt
        
        if variable_name in self.inputs:
            var = self.inputs[variable_name]
        elif variable_name in self.outputs:
            var = self.outputs[variable_name]
        else:
            raise ValueError(f"Unknown variable: {variable_name}")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for term_name in var.membership_functions:
            mf = var.antecedent[term_name].mf if hasattr(var, 'antecedent') else var.consequent[term_name].mf
            ax.plot(var.universe, mf, label=term_name)
        
        ax.set_title(f"Membership Functions: {variable_name}")
        ax.set_xlabel("Value")
        ax.set_ylabel("Membership Degree")
        ax.legend()
        ax.grid(True)
        
        return fig


# ==================== Pre-built Earth System Models ====================

class LandslideExpertSystem:
    """Expert system for landslide risk assessment"""
    
    def __init__(self):
        self.kb = KnowledgeBase()
        self.engine = InferenceEngine(self.kb)
        self._setup_rules()
    
    def _setup_rules(self):
        """Setup landslide assessment rules"""
        
        rules = [
            Rule(
                id="LS001",
                name="High Slope Risk",
                conditions=[
                    Condition("slope_angle", RuleOperator.GREATER_THAN, 30),
                    Condition("soil_type", RuleOperator.IN, ["loose_soil", "sandy_soil"])
                ],
                conclusion="high_slope_failure_risk",
                action="Implement slope stabilization measures and continuous monitoring",
                confidence=0.9,
                priority=10
            ),
            Rule(
                id="LS002",
                name="Rainfall Trigger",
                conditions=[
                    Condition("rainfall_24h", RuleOperator.GREATER_THAN, 100),
                    Condition("slope_angle", RuleOperator.GREATER_THAN, 20)
                ],
                conclusion="rainfall_triggered_landslide_risk",
                action="Issue immediate evacuation warning for high-risk areas",
                confidence=0.85,
                priority=9
            ),
            Rule(
                id="LS003",
                name="Seismic Risk",
                conditions=[
                    Condition("earthquake_magnitude", RuleOperator.GREATER_THAN, 5.0),
                    Condition("slope_angle", RuleOperator.GREATER_THAN, 15)
                ],
                conclusion="seismic_landslide_risk",
                action="Activate emergency response protocol and inspect critical slopes",
                confidence=0.8,
                priority=8
            ),
            Rule(
                id="LS004",
                name="Vegetation Protection",
                conditions=[
                    Condition("vegetation_cover", RuleOperator.GREATER_THAN, 0.7),
                    Condition("slope_angle", RuleOperator.LESS_THAN, 45)
                ],
                conclusion="vegetation_stabilized_slope",
                action="Maintain vegetation cover and monitor for changes",
                confidence=0.75,
                priority=5
            ),
            Rule(
                id="LS005",
                name="Groundwater Risk",
                conditions=[
                    Condition("groundwater_level", RuleOperator.GREATER_THAN, 0.8),
                    Condition("soil_saturation", RuleOperator.GREATER_THAN, 0.9)
                ],
                conclusion="groundwater_induced_landslide_risk",
                action="Install drainage systems and reduce groundwater pressure",
                confidence=0.85,
                priority=8
            ),
            Rule(
                id="LS006",
                name="Low Risk Assessment",
                conditions=[
                    Condition("slope_angle", RuleOperator.LESS_THAN, 15),
                    Condition("rainfall_24h", RuleOperator.LESS_THAN, 50),
                    Condition("vegetation_cover", RuleOperator.GREATER_THAN, 0.5)
                ],
                conclusion="low_landslide_risk",
                action="Continue routine monitoring and maintenance",
                confidence=0.7,
                priority=1
            )
        ]
        
        for rule in rules:
            self.kb.add_rule(rule)
    
    def assess(
        self,
        slope_angle: float,
        soil_type: str,
        rainfall_24h: float,
        vegetation_cover: float,
        groundwater_level: float = 0.5,
        soil_saturation: float = 0.5,
        earthquake_magnitude: float = 0.0
    ) -> List[InferenceResult]:
        """Assess landslide risk based on input parameters"""
        
        # Add facts
        self.kb.add_fact("slope_angle", slope_angle)
        self.kb.add_fact("soil_type", soil_type)
        self.kb.add_fact("rainfall_24h", rainfall_24h)
        self.kb.add_fact("vegetation_cover", vegetation_cover)
        self.kb.add_fact("groundwater_level", groundwater_level)
        self.kb.add_fact("soil_saturation", soil_saturation)
        self.kb.add_fact("earthquake_magnitude", earthquake_magnitude)
        
        # Run inference
        results = self.engine.infer()
        
        return results
    
    def get_risk_level(self, results: List[InferenceResult]) -> Tuple[str, float]:
        """Determine overall risk level from inference results"""
        
        if not results:
            return "unknown", 0.0
        
        # Find highest confidence result
        highest = max(results, key=lambda r: r.confidence)
        
        if "high" in highest.conclusion or "risk" in highest.conclusion:
            return "high", highest.confidence
        elif "medium" in highest.conclusion:
            return "medium", highest.confidence
        elif "low" in highest.conclusion:
            return "low", highest.confidence
        
        return "unknown", highest.confidence


class LandslideFuzzySystem:
    """Fuzzy logic system for landslide susceptibility assessment"""
    
    def __init__(self):
        self.fis = FuzzyInferenceSystem("LandslideFIS")
        self._setup_variables()
        self._setup_rules()
    
    def _setup_variables(self):
        """Setup fuzzy variables"""
        
        # Slope angle (degrees)
        slope_universe = np.linspace(0, 90, 100)
        self.fis.add_input("slope_angle", slope_universe, {
            "flat": {"points": [0, 0, 5, 10]},
            "gentle": {"points": [5, 10, 15, 20]},
            "moderate": {"points": [15, 25, 35, 45]},
            "steep": {"points": [35, 50, 90, 90]}
        })
        
        # Rainfall (mm)
        rainfall_universe = np.linspace(0, 300, 100)
        self.fis.add_input("rainfall", rainfall_universe, {
            "dry": {"points": [0, 0, 10, 25]},
            "light": {"points": [10, 25, 50, 75]},
            "moderate": {"points": [50, 75, 100, 150]},
            "heavy": {"points": [100, 150, 300, 300]}
        })
        
        # Vegetation cover (0-1)
        veg_universe = np.linspace(0, 1, 100)
        self.fis.add_input("vegetation", veg_universe, {
            "sparse": {"points": [0, 0, 0.2, 0.3]},
            "moderate": {"points": [0.2, 0.4, 0.6, 0.8]},
            "dense": {"points": [0.7, 0.85, 1, 1]}
        })
        
        # Landslide susceptibility (0-1)
        susceptibility_universe = np.linspace(0, 1, 100)
        self.fis.add_output("susceptibility", susceptibility_universe, {
            "very_low": {"points": [0, 0, 0.1, 0.2]},
            "low": {"points": [0.1, 0.2, 0.3, 0.4]},
            "moderate": {"points": [0.3, 0.4, 0.6, 0.7]},
            "high": {"points": [0.6, 0.7, 0.85, 0.95]},
            "very_high": {"points": [0.85, 0.95, 1, 1]}
        })
    
    def _setup_rules(self):
        """Setup fuzzy rules"""
        
        rules = [
            # High slope + heavy rain = very high risk
            ([("slope_angle", "steep"), ("rainfall", "heavy")], ("susceptibility", "very_high")),
            # Moderate slope + moderate rain = moderate risk
            ([("slope_angle", "moderate"), ("rainfall", "moderate")], ("susceptibility", "moderate")),
            # Gentle slope + light rain = low risk
            ([("slope_angle", "gentle"), ("rainfall", "light")], ("susceptibility", "low")),
            # Flat + dry = very low risk
            ([("slope_angle", "flat"), ("rainfall", "dry")], ("susceptibility", "very_low")),
            # High slope + dense vegetation = moderate risk
            ([("slope_angle", "steep"), ("vegetation", "dense")], ("susceptibility", "moderate")),
            # Moderate slope + sparse vegetation = high risk
            ([("slope_angle", "moderate"), ("vegetation", "sparse")], ("susceptibility", "high")),
            # Steep + heavy rain + sparse vegetation = very high
            ([("slope_angle", "steep"), ("rainfall", "heavy"), ("vegetation", "sparse")], ("susceptibility", "very_high")),
        ]
        
        for antecedents, consequent in rules:
            self.fis.add_rule(antecedents, consequent)
    
    def assess(
        self,
        slope_angle: float,
        rainfall: float,
        vegetation: float
    ) -> Dict[str, float]:
        """Assess landslide susceptibility"""
        
        inputs = {
            "slope_angle": slope_angle,
            "rainfall": rainfall,
            "vegetation": vegetation
        }
        
        return self.fis.compute(inputs)


# Example usage
if __name__ == "__main__":
    # Test Expert System
    print("=== Landslide Expert System ===")
    expert_system = LandslideExpertSystem()
    
    results = expert_system.assess(
        slope_angle=45,
        soil_type="loose_soil",
        rainfall_24h=120,
        vegetation_cover=0.3,
        groundwater_level=0.9,
        soil_saturation=0.95
    )
    
    print(f"Number of rules triggered: {len(results)}")
    for result in results:
        print(f"\nRule: {result.rule_name}")
        print(f"Confidence: {result.confidence:.2%}")
        print(f"Conclusion: {result.conclusion}")
        print(f"Action: {result.action}")
    
    risk_level, confidence = expert_system.get_risk_level(results)
    print(f"\nOverall Risk Level: {risk_level.upper()} (confidence: {confidence:.2%})")
    
    # Test Fuzzy System
    print("\n=== Landslide Fuzzy System ===")
    fuzzy_system = LandslideFuzzySystem()
    
    result = fuzzy_system.assess(
        slope_angle=35,
        rainfall=150,
        vegetation=0.2
    )
    
    print(f"Fuzzy Assessment Results:")
    for output_name, value in result.items():
        print(f"  {output_name}: {value:.3f}")
    
    # Interpret result
    susceptibility = result.get("susceptibility", 0)
    if susceptibility > 0.8:
        print("Risk Level: VERY HIGH")
    elif susceptibility > 0.6:
        print("Risk Level: HIGH")
    elif susceptibility > 0.4:
        print("Risk Level: MODERATE")
    elif susceptibility > 0.2:
        print("Risk Level: LOW")
    else:
        print("Risk Level: VERY LOW")
