"""
EarthAI Platform - Probabilistic Graphical Models Module
Implements Bayesian Networks, Markov Networks for uncertainty quantification
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class Node:
    """Node in a probabilistic graphical model"""
    name: str
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    states: List[Any] = field(default_factory=list)
    cpt: Optional[np.ndarray] = None  # Conditional Probability Table
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        if isinstance(other, Node):
            return self.name == other.name
        return self.name == other


@dataclass
class BayesianNetwork:
    """Bayesian Network for probabilistic reasoning"""
    name: str
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Tuple[str, str]] = field(default_factory=list)
    
    def add_node(self, node: Node):
        """Add node to network"""
        self.nodes[node.name] = node
    
    def add_edge(self, parent: str, child: str):
        """Add directed edge"""
        if parent in self.nodes and child in self.nodes:
            self.nodes[parent].children.append(child)
            self.nodes[child].parents.append(parent)
            self.edges.append((parent, child))
    
    def get_parents(self, node_name: str) -> List[str]:
        """Get parent nodes"""
        return self.nodes[node_name].parents if node_name in self.nodes else []
    
    def get_children(self, node_name: str) -> List[str]:
        """Get child nodes"""
        return self.nodes[node_name].children if node_name in self.nodes else []
    
    def get_ancestors(self, node_name: str) -> Set[str]:
        """Get all ancestors of a node"""
        ancestors = set()
        queue = deque([node_name])
        
        while queue:
            current = queue.popleft()
            parents = self.get_parents(current)
            for parent in parents:
                if parent not in ancestors:
                    ancestors.add(parent)
                    queue.append(parent)
        
        return ancestors
    
    def get_descendants(self, node_name: str) -> Set[str]:
        """Get all descendants of a node"""
        descendants = set()
        queue = deque([node_name])
        
        while queue:
            current = queue.popleft()
            children = self.get_children(current)
            for child in children:
                if child not in descendants:
                    descendants.add(child)
                    queue.append(child)
        
        return descendants
    
    def is_d_separated(
        self,
        node_a: str,
        node_b: str,
        evidence: Set[str] = None
    ) -> bool:
        """Check if node_a and node_b are d-separated given evidence"""
        if evidence is None:
            evidence = set()
        
        # Find all paths between a and b
        paths = self._find_all_paths(node_a, node_b)
        
        # Check if all paths are blocked
        for path in paths:
            if not self._is_path_blocked(path, evidence):
                return False
        
        return True
    
    def _find_all_paths(
        self,
        start: str,
        end: str
    ) -> List[List[str]]:
        """Find all undirected paths between two nodes"""
        paths = []
        visited = set()
        
        def dfs(current, path):
            if current == end:
                paths.append(path.copy())
                return
            
            visited.add(current)
            
            # Get neighbors (both parents and children)
            neighbors = set(self.get_parents(current))
            neighbors.update(self.get_children(current))
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    path.append(neighbor)
                    dfs(neighbor, path)
                    path.pop()
            
            visited.remove(current)
        
        dfs(start, [start])
        return paths
    
    def _is_path_blocked(
        self,
        path: List[str],
        evidence: Set[str]
    ) -> bool:
        """Check if a path is blocked given evidence"""
        
        for i in range(1, len(path) - 1):
            node = path[i]
            prev_node = path[i - 1]
            next_node = path[i + 1]
            
            # Check if this is a chain, fork, or collider
            is_chain = (prev_node in self.get_parents(node) and next_node in self.get_children(node)) or \
                      (prev_node in self.get_children(node) and next_node in self.get_parents(node))
            
            is_fork = (prev_node in self.get_parents(node) and next_node in self.get_parents(node))
            
            is_collider = (prev_node in self.get_children(node) and next_node in self.get_children(node))
            
            # Chain or fork: blocked if middle node is in evidence
            if (is_chain or is_fork) and node in evidence:
                return True
            
            # Collider: blocked if middle node is NOT in evidence
            # and none of its descendants are in evidence
            if is_collider and node not in evidence:
                descendants = self.get_descendants(node)
                if not any(d in evidence for d in descendants):
                    return True
        
        return False


class BayesianInference:
    """Inference engine for Bayesian networks"""
    
    def __init__(self, network: BayesianNetwork):
        self.network = network
    
    def variable_elimination(
        self,
        query_vars: List[str],
        evidence: Dict[str, Any]
    ) -> Dict[str, np.ndarray]:
        """Variable elimination for exact inference"""
        
        # Get all relevant variables
        all_vars = set(query_vars)
        for qv in query_vars:
            all_vars.update(self.network.get_ancestors(qv))
        
        for ev_var in evidence:
            all_vars.update(self.network.get_ancestors(ev_var))
        
        # Remove evidence variables
        hidden_vars = all_vars - set(query_vars) - set(evidence.keys())
        
        # Create factors
        factors = self._create_factors(evidence)
        
        # Eliminate hidden variables one by one
        elimination_order = self._get_elimination_order(hidden_vars)
        
        for var in elimination_order:
            # Find all factors containing this variable
            relevant_factors = [f for f in factors if var in f["variables"]]
            other_factors = [f for f in factors if var not in f["variables"]]
            
            if relevant_factors:
                # Multiply and marginalize
                combined = self._multiply_factors(relevant_factors)
                marginalized = self._marginalize_factor(combined, var)
                
                factors = other_factors + [marginalized]
        
        # Multiply remaining factors
        if factors:
            result_factor = self._multiply_factors(factors)
        else:
            return {qv: np.ones(len(self.network.nodes[qv].states)) / len(self.network.nodes[qv].states) 
                    for qv in query_vars}
        
        # Normalize and extract marginals
        results = {}
        for qv in query_vars:
            if qv in result_factor["variables"]:
                marginal = self._marginalize_factor(result_factor, 
                                                     *[v for v in result_factor["variables"] if v != qv])
                results[qv] = marginal["values"] / marginal["values"].sum()
            else:
                results[qv] = np.ones(len(self.network.nodes[qv].states)) / len(self.network.nodes[qv].states)
        
        return results
    
    def _create_factors(self, evidence: Dict[str, Any]) -> List[Dict]:
        """Create factors from network CPTs with evidence applied"""
        factors = []
        
        for node_name, node in self.network.nodes.items():
            variables = [node_name] + node.parents
            values = node.cpt.copy() if node.cpt is not None else None
            
            if values is None:
                continue
            
            # Apply evidence
            if node_name in evidence:
                state_idx = node.states.index(evidence[node_name])
                values = np.zeros_like(values)
                values[..., state_idx] = 1.0
            
            for parent in node.parents:
                if parent in evidence:
                    parent_idx = node.parents.index(parent)
                    state_idx = self.network.nodes[parent].states.index(evidence[parent])
                    
                    # Set all other states to 0
                    new_values = np.zeros_like(values)
                    indices = [slice(None)] * values.ndim
                    indices[parent_idx] = state_idx
                    new_values[tuple(indices)] = values[tuple(indices)]
                    values = new_values
            
            # Remove dimensions that are fully determined
            # (This is a simplification; full implementation would reduce factors)
            
            factors.append({
                "variables": variables,
                "values": values,
                "node_states": {node_name: node.states}
            })
        
        return factors
    
    def _multiply_factors(self, factors: List[Dict]) -> Dict:
        """Multiply multiple factors"""
        if len(factors) == 1:
            return factors[0]
        
        # Get union of all variables
        all_variables = []
        for f in factors:
            for v in f["variables"]:
                if v not in all_variables:
                    all_variables.append(v)
        
        # Create result tensor
        shape = []
        for v in all_variables:
            if v in factors[0]["node_states"]:
                shape.append(len(factors[0]["node_states"][v]))
            else:
                # Find from other factors
                for f in factors:
                    if v in f.get("node_states", {}):
                        shape.append(len(f["node_states"][v]))
                        break
        
        result = np.ones(shape)
        
        # Multiply all factors
        for factor in factors:
            # Align factor with result dimensions
            aligned = self._align_factor(factor, all_variables)
            result = result * aligned
        
        return {
            "variables": all_variables,
            "values": result,
            "node_states": {v: factors[0]["node_states"].get(v, [0, 1]) 
                           for v in all_variables if v in factors[0].get("node_states", {})}
        }
    
    def _align_factor(self, factor: Dict, target_variables: List[str]) -> np.ndarray:
        """Align factor to target variable ordering"""
        values = factor["values"]
        
        # Create mapping from factor variables to target variables
        perm = []
        for v in target_variables:
            if v in factor["variables"]:
                perm.append(factor["variables"].index(v))
            else:
                # Variable not in factor, add dimension of size 1
                values = np.expand_dims(values, axis=len(perm))
                perm.append(-1)
        
        # Transpose to match target ordering
        values = np.moveaxis(values, list(range(len(perm))), 
                            [i for i, p in enumerate(perm) if p >= 0])
        
        # Expand dimensions for missing variables
        for i, p in enumerate(perm):
            if p == -1:
                values = np.expand_dims(values, axis=i)
        
        # Broadcast to full shape
        target_shape = []
        for v in target_variables:
            if v in factor.get("node_states", {}):
                target_shape.append(len(factor["node_states"][v]))
            else:
                # Get from network
                if v in self.network.nodes:
                    target_shape.append(len(self.network.nodes[v].states))
                else:
                    target_shape.append(2)  # Default binary
        
        return np.broadcast_to(values, target_shape)
    
    def _marginalize_factor(self, factor: Dict, *variables: str) -> Dict:
        """Marginalize out variables from factor"""
        remaining_vars = [v for v in factor["variables"] if v not in variables]
        
        if not remaining_vars:
            return {
                "variables": [],
                "values": factor["values"].sum(),
                "node_states": {}
            }
        
        axes = [factor["variables"].index(v) for v in variables if v in factor["variables"]]
        marginalized = np.sum(factor["values"], axis=tuple(axes))
        
        return {
            "variables": remaining_vars,
            "values": marginalized,
            "node_states": {v: factor["node_states"][v] for v in remaining_vars if v in factor["node_states"]}
        }
    
    def _get_elimination_order(self, variables: Set[str]) -> List[str]:
        """Get elimination order using min-fill heuristic"""
        # Simplified: just return sorted by number of neighbors
        return sorted(variables, key=lambda v: len(self.network.get_parents(v)) + 
                     len(self.network.get_children(v)))
    
    def likelihood_weighting(
        self,
        query_vars: List[str],
        evidence: Dict[str, Any],
        n_samples: int = 10000
    ) -> Dict[str, np.ndarray]:
        """Approximate inference using likelihood weighting"""
        
        samples = defaultdict(lambda: defaultdict(float))
        total_weight = 0.0
        
        for _ in range(n_samples):
            sample = {}
            weight = 1.0
            
            # Sample in topological order
            ordered_nodes = self._topological_sort()
            
            for node_name in ordered_nodes:
                node = self.network.nodes[node_name]
                
                if node_name in evidence:
                    # Evidence: weight by likelihood
                    sample[node_name] = evidence[node_name]
                    
                    # Calculate likelihood
                    parent_values = [sample[p] for p in node.parents]
                    state_idx = node.states.index(evidence[node_name])
                    
                    if parent_values:
                        # Get from CPT
                        parent_indices = [self.network.nodes[p].states.index(sample[p]) 
                                        for p in node.parents]
                        likelihood = node.cpt[tuple(parent_indices + [state_idx])]
                    else:
                        # Prior probability
                        likelihood = node.cpt[state_idx]
                    
                    weight *= likelihood
                else:
                    # Sample from conditional distribution
                    parent_values = [sample[p] for p in node.parents]
                    
                    if parent_values:
                        parent_indices = [self.network.nodes[p].states.index(sample[p]) 
                                        for p in node.parents]
                        probs = node.cpt[tuple(parent_indices)]
                    else:
                        probs = node.cpt
                    
                    # Normalize
                    probs = probs / probs.sum()
                    
                    # Sample
                    sample[node_name] = np.random.choice(node.states, p=probs)
            
            # Update counts
            for qv in query_vars:
                samples[qv][sample[qv]] += weight
            
            total_weight += weight
        
        # Normalize
        results = {}
        for qv in query_vars:
            counts = np.array([samples[qv].get(s, 0) for s in self.network.nodes[qv].states])
            results[qv] = counts / total_weight if total_weight > 0 else counts / len(counts)
        
        return results
    
    def _topological_sort(self) -> List[str]:
        """Topological sort of network nodes"""
        in_degree = {n: len(self.network.get_parents(n)) for n in self.network.nodes}
        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for child in self.network.get_children(node):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        
        return result


class MarkovNetwork:
    """Markov Random Field for spatial dependency modeling"""
    
    def __init__(self, name: str):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Tuple[str, str]] = []
        self.cliques: List[Set[str]] = []
        self.potentials: Dict[frozenset, np.ndarray] = {}
    
    def add_node(self, node: Node):
        """Add node to network"""
        self.nodes[node.name] = node
    
    def add_edge(self, node1: str, node2: str):
        """Add undirected edge"""
        self.edges.append((node1, node2))
        self.nodes[node1].children.append(node2)
        self.nodes[node2].children.append(node1)
    
    def add_clique(self, nodes: Set[str]):
        """Add clique to network"""
        self.cliques.append(nodes)
    
    def set_potential(self, clique: Set[str], potential: np.ndarray):
        """Set potential for a clique"""
        self.potentials[frozenset(clique)] = potential
    
    def gibbs_sampling(
        self,
        evidence: Dict[str, Any],
        n_samples: int = 10000,
        burn_in: int = 1000
    ) -> Dict[str, Dict[Any, float]]:
        """Gibbs sampling for approximate inference"""
        
        # Initialize random sample
        current_sample = {}
        for node_name, node in self.nodes.items():
            if node_name in evidence:
                current_sample[node_name] = evidence[node_name]
            else:
                current_sample[node_name] = np.random.choice(node.states)
        
        # Collect samples
        counts = defaultdict(lambda: defaultdict(int))
        
        for i in range(n_samples + burn_in):
            # Update each variable
            for node_name, node in self.nodes.items():
                if node_name in evidence:
                    continue
                
                # Calculate conditional probability
                probs = self._conditional_probability(node_name, current_sample)
                
                # Sample
                current_sample[node_name] = np.random.choice(node.states, p=probs)
            
            # Record after burn-in
            if i >= burn_in:
                for node_name in self.nodes:
                    if node_name not in evidence:
                        counts[node_name][current_sample[node_name]] += 1
        
        # Normalize
        results = {}
        for node_name in self.nodes:
            if node_name not in evidence:
                node_counts = counts[node_name]
                total = sum(node_counts.values())
                results[node_name] = {state: count / total 
                                     for state, count in node_counts.items()}
        
        return results
    
    def _conditional_probability(
        self,
        node_name: str,
        current_sample: Dict[str, Any]
    ) -> np.ndarray:
        """Calculate conditional probability for Gibbs sampling"""
        node = self.nodes[node_name]
        
        # Get neighbors
        neighbors = set(node.children)
        
        # Calculate unnormalized probabilities
        probs = np.ones(len(node.states))
        
        for clique in self.cliques:
            if node_name in clique:
                # Get clique potential
                potential = self.potentials.get(frozenset(clique), np.ones([2] * len(clique)))
                
                # Extract relevant slice
                indices = []
                for c_node in sorted(clique):
                    if c_node == node_name:
                        indices.append(slice(None))
                    else:
                        state_idx = self.nodes[c_node].states.index(current_sample[c_node])
                        indices.append(state_idx)
                
                clique_probs = potential[tuple(indices)]
                probs = probs * clique_probs
        
        # Normalize
        probs = probs / probs.sum() if probs.sum() > 0 else np.ones(len(probs)) / len(probs)
        
        return probs


class EarthSystemBayesianNetwork:
    """Pre-built Bayesian Network for Earth system modeling"""
    
    def __init__(self, model_type: str = "landslide"):
        self.model_type = model_type
        self.network = BayesianNetwork(f"{model_type}_bn")
        self.inference = None
        
        if model_type == "landslide":
            self._build_landslide_network()
        elif model_type == "climate":
            self._build_climate_network()
        elif model_type == "flood":
            self._build_flood_network()
        
        self.inference = BayesianInference(self.network)
    
    def _build_landslide_network(self):
        """Build landslide susceptibility Bayesian network"""
        
        # Define nodes
        nodes = {
            "elevation": Node("elevation", states=["low", "medium", "high"]),
            "slope": Node("slope", states=["flat", "gentle", "moderate", "steep"]),
            "soil_type": Node("soil_type", states=["rocky", "clay", "sand", "loam"]),
            "vegetation": Node("vegetation", states=["sparse", "moderate", "dense"]),
            "rainfall": Node("rainfall", states=["dry", "normal", "wet", "heavy"]),
            "groundwater": Node("groundwater", states=["low", "medium", "high"]),
            "seismic_activity": Node("seismic_activity", states=["none", "light", "moderate", "strong"]),
            "landslide_risk": Node("landslide_risk", states=["very_low", "low", "moderate", "high", "very_high"])
        }
        
        # Add nodes
        for node in nodes.values():
            self.network.add_node(node)
        
        # Add edges (causal relationships)
        edges = [
            ("elevation", "slope"),
            ("soil_type", "groundwater"),
            ("rainfall", "groundwater"),
            ("rainfall", "landslide_risk"),
            ("slope", "landslide_risk"),
            ("soil_type", "landslide_risk"),
            ("vegetation", "landslide_risk"),
            ("groundwater", "landslide_risk"),
            ("seismic_activity", "landslide_risk")
        ]
        
        for parent, child in edges:
            self.network.add_edge(parent, child)
        
        # Set CPTs (simplified for demonstration)
        self._set_landslide_cpts()
    
    def _set_landslide_cpts(self):
        """Set conditional probability tables for landslide network"""
        
        # Slope given elevation
        # P(Slope | Elevation)
        self.network.nodes["slope"].cpt = np.array([
            [0.6, 0.3, 0.1, 0.0],   # Elevation: low
            [0.1, 0.4, 0.4, 0.1],   # Elevation: medium
            [0.0, 0.1, 0.3, 0.6]    # Elevation: high
        ])
        
        # Groundwater given soil_type and rainfall
        # P(Groundwater | Soil, Rainfall)
        self.network.nodes["groundwater"].cpt = np.zeros((4, 4, 3))  # Soil, Rainfall, Groundwater
        
        for soil in range(4):
            for rain in range(4):
                if soil == 0:  # rocky
                    self.network.nodes["groundwater"].cpt[soil, rain] = [0.7, 0.2, 0.1]
                elif soil == 1:  # clay
                    self.network.nodes["groundwater"].cpt[soil, rain] = [0.1, 0.3, 0.6]
                elif soil == 2:  # sand
                    self.network.nodes["groundwater"].cpt[soil, rain] = [0.5, 0.3, 0.2]
                else:  # loam
                    self.network.nodes["groundwater"].cpt[soil, rain] = [0.3, 0.4, 0.3]
        
        # Landslide risk given all parents
        # Simplified: just use a few key factors
        n_risk_states = 5
        self.network.nodes["landslide_risk"].cpt = np.zeros((
            4,  # slope
            4,  # soil
            3,  # vegetation
            4,  # rainfall
            3,  # groundwater
            4,  # seismic
            n_risk_states
        ))
        
        # Set simple heuristic probabilities
        for slope in range(4):
            for soil in range(4):
                for veg in range(3):
                    for rain in range(4):
                        for gw in range(3):
                            for seismic in range(4):
                                # Calculate risk score
                                risk_score = 0
                                
                                # Slope contribution
                                risk_score += slope * 2
                                
                                # Soil contribution
                                risk_score += soil * 1.5
                                
                                # Vegetation (inverse)
                                risk_score += (2 - veg) * 1
                                
                                # Rainfall contribution
                                risk_score += rain * 2
                                
                                # Groundwater contribution
                                risk_score += gw * 2
                                
                                # Seismic contribution
                                risk_score += seismic * 2.5
                                
                                # Normalize to 0-4
                                normalized_risk = min(4, int(risk_score / 6))
                                
                                # Set probability distribution
                                probs = np.ones(n_risk_states) * 0.05
                                probs[normalized_risk] = 0.8
                                
                                self.network.nodes["landslide_risk"].cpt[
                                    slope, soil, veg, rain, gw, seismic
                                ] = probs / probs.sum()
    
    def predict_risk(
        self,
        evidence: Dict[str, Any],
        method: str = "variable_elimination"
    ) -> Dict[str, float]:
        """Predict landslide risk given evidence"""
        
        if method == "variable_elimination":
            results = self.inference.variable_elimination(
                ["landslide_risk"],
                evidence
            )
        elif method == "likelihood_weighting":
            results = self.inference.likelihood_weighting(
                ["landslide_risk"],
                evidence,
                n_samples=10000
            )
        else:
            raise ValueError(f"Unknown inference method: {method}")
        
        # Convert to readable format
        risk_probs = results["landslide_risk"]
        states = self.network.nodes["landslide_risk"].states
        
        return {state: float(prob) for state, prob in zip(states, risk_probs)}
    
    def _build_climate_network(self):
        """Build climate prediction Bayesian network"""
        pass  # Implementation similar to landslide
    
    def _build_flood_network(self):
        """Build flood risk Bayesian network"""
        pass  # Implementation similar to landslide


# Example usage
if __name__ == "__main__":
    print("=== Landslide Bayesian Network ===")
    
    # Create network
    bn = EarthSystemBayesianNetwork("landslide")
    
    # Evidence
    evidence = {
        "elevation": "high",
        "slope": "steep",
        "soil_type": "clay",
        "vegetation": "sparse",
        "rainfall": "heavy",
        "groundwater": "high",
        "seismic_activity": "moderate"
    }
    
    # Predict risk
    risk_probs = bn.predict_risk(evidence, method="variable_elimination")
    
    print("\nLandslide Risk Probabilities:")
    for state, prob in risk_probs.items():
        print(f"  {state}: {prob:.3f}")
    
    # Determine highest risk
    max_risk = max(risk_probs, key=risk_probs.get)
    print(f"\nHighest Risk: {max_risk} ({risk_probs[max_risk]:.1%})")
