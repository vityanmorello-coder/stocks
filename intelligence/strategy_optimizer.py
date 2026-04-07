"""
STRATEGY OPTIMIZER
Genetic algorithm-based parameter optimization for trading strategies
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable, Any
from dataclasses import dataclass
import random
import logging
from concurrent.futures import ProcessPoolExecutor
import json

logger = logging.getLogger(__name__)


@dataclass
class ParameterSpace:
    """Define parameter search space"""
    name: str
    min_value: float
    max_value: float
    step: float = None
    is_integer: bool = False
    
    def random_value(self) -> float:
        """Generate random value in range"""
        if self.is_integer:
            return random.randint(int(self.min_value), int(self.max_value))
        else:
            return random.uniform(self.min_value, self.max_value)
    
    def clip_value(self, value: float) -> float:
        """Clip value to valid range"""
        value = max(self.min_value, min(self.max_value, value))
        if self.is_integer:
            value = int(round(value))
        elif self.step:
            value = round(value / self.step) * self.step
        return value


@dataclass
class Individual:
    """Individual in genetic algorithm population"""
    genes: Dict[str, float]
    fitness: float = 0.0
    
    def to_dict(self):
        return {
            'genes': self.genes,
            'fitness': self.fitness
        }


class GeneticOptimizer:
    """Genetic algorithm optimizer for trading strategies"""
    
    def __init__(self, parameter_spaces: List[ParameterSpace],
                 population_size: int = 50,
                 generations: int = 30,
                 mutation_rate: float = 0.2,
                 crossover_rate: float = 0.7,
                 elitism_rate: float = 0.1):
        
        self.parameter_spaces = {ps.name: ps for ps in parameter_spaces}
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = int(population_size * elitism_rate)
        
        self.population: List[Individual] = []
        self.best_individual: Individual = None
        self.generation_history: List[Dict] = []
    
    def optimize(self, fitness_function: Callable, **kwargs) -> Dict:
        """Run genetic algorithm optimization"""
        
        logger.info(f"Starting genetic optimization: {self.generations} generations, {self.population_size} population")
        
        self._initialize_population()
        
        self._evaluate_population(fitness_function, **kwargs)
        
        for generation in range(self.generations):
            logger.info(f"Generation {generation + 1}/{self.generations}")
            
            new_population = self._evolve_population()
            
            self.population = new_population
            
            self._evaluate_population(fitness_function, **kwargs)
            
            self._update_best()
            
            gen_stats = self._get_generation_stats(generation + 1)
            self.generation_history.append(gen_stats)
            
            logger.info(f"  Best fitness: {gen_stats['best_fitness']:.4f}")
            logger.info(f"  Avg fitness: {gen_stats['avg_fitness']:.4f}")
        
        return self._get_optimization_results()
    
    def _initialize_population(self):
        """Create initial random population"""
        
        self.population = []
        
        for _ in range(self.population_size):
            genes = {
                name: space.random_value()
                for name, space in self.parameter_spaces.items()
            }
            
            self.population.append(Individual(genes=genes))
    
    def _evaluate_population(self, fitness_function: Callable, **kwargs):
        """Evaluate fitness for all individuals"""
        
        for individual in self.population:
            try:
                individual.fitness = fitness_function(individual.genes, **kwargs)
            except Exception as e:
                logger.error(f"Fitness evaluation failed: {e}")
                individual.fitness = -999999
    
    def _evolve_population(self) -> List[Individual]:
        """Create new generation through selection, crossover, and mutation"""
        
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        
        new_population = self.population[:self.elitism_count].copy()
        
        while len(new_population) < self.population_size:
            parent1 = self._tournament_selection()
            parent2 = self._tournament_selection()
            
            if random.random() < self.crossover_rate:
                child1, child2 = self._crossover(parent1, parent2)
            else:
                child1, child2 = parent1, parent2
            
            if random.random() < self.mutation_rate:
                child1 = self._mutate(child1)
            if random.random() < self.mutation_rate:
                child2 = self._mutate(child2)
            
            new_population.append(child1)
            if len(new_population) < self.population_size:
                new_population.append(child2)
        
        return new_population[:self.population_size]
    
    def _tournament_selection(self, tournament_size: int = 3) -> Individual:
        """Select individual using tournament selection"""
        
        tournament = random.sample(self.population, tournament_size)
        return max(tournament, key=lambda x: x.fitness)
    
    def _crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """Perform crossover between two parents"""
        
        child1_genes = {}
        child2_genes = {}
        
        for param_name in self.parameter_spaces.keys():
            if random.random() < 0.5:
                child1_genes[param_name] = parent1.genes[param_name]
                child2_genes[param_name] = parent2.genes[param_name]
            else:
                child1_genes[param_name] = parent2.genes[param_name]
                child2_genes[param_name] = parent1.genes[param_name]
        
        return Individual(genes=child1_genes), Individual(genes=child2_genes)
    
    def _mutate(self, individual: Individual) -> Individual:
        """Mutate individual's genes"""
        
        mutated_genes = individual.genes.copy()
        
        for param_name, space in self.parameter_spaces.items():
            if random.random() < 0.3:
                mutation_strength = 0.2
                current_value = mutated_genes[param_name]
                range_size = space.max_value - space.min_value
                
                mutation = random.gauss(0, mutation_strength * range_size)
                new_value = current_value + mutation
                
                mutated_genes[param_name] = space.clip_value(new_value)
        
        return Individual(genes=mutated_genes)
    
    def _update_best(self):
        """Update best individual found so far"""
        
        current_best = max(self.population, key=lambda x: x.fitness)
        
        if self.best_individual is None or current_best.fitness > self.best_individual.fitness:
            self.best_individual = Individual(
                genes=current_best.genes.copy(),
                fitness=current_best.fitness
            )
    
    def _get_generation_stats(self, generation: int) -> Dict:
        """Get statistics for current generation"""
        
        fitnesses = [ind.fitness for ind in self.population]
        
        return {
            'generation': generation,
            'best_fitness': max(fitnesses),
            'avg_fitness': np.mean(fitnesses),
            'worst_fitness': min(fitnesses),
            'std_fitness': np.std(fitnesses),
            'best_genes': max(self.population, key=lambda x: x.fitness).genes.copy()
        }
    
    def _get_optimization_results(self) -> Dict:
        """Get final optimization results"""
        
        return {
            'best_parameters': self.best_individual.genes,
            'best_fitness': self.best_individual.fitness,
            'generation_history': self.generation_history,
            'total_generations': self.generations,
            'population_size': self.population_size
        }


class GridSearchOptimizer:
    """Grid search optimizer (exhaustive search)"""
    
    def __init__(self, parameter_spaces: List[ParameterSpace]):
        self.parameter_spaces = parameter_spaces
    
    def optimize(self, fitness_function: Callable, **kwargs) -> Dict:
        """Run grid search optimization"""
        
        logger.info("Starting grid search optimization")
        
        param_grids = self._create_parameter_grids()
        
        total_combinations = np.prod([len(grid) for grid in param_grids.values()])
        logger.info(f"Total combinations to test: {total_combinations}")
        
        best_params = None
        best_fitness = -float('inf')
        all_results = []
        
        combinations = self._generate_combinations(param_grids)
        
        for i, params in enumerate(combinations):
            if i % 100 == 0:
                logger.info(f"Testing combination {i}/{total_combinations}")
            
            try:
                fitness = fitness_function(params, **kwargs)
                
                all_results.append({
                    'parameters': params.copy(),
                    'fitness': fitness
                })
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_params = params.copy()
                    
            except Exception as e:
                logger.error(f"Fitness evaluation failed: {e}")
        
        all_results.sort(key=lambda x: x['fitness'], reverse=True)
        
        return {
            'best_parameters': best_params,
            'best_fitness': best_fitness,
            'all_results': all_results[:100],
            'total_tested': len(all_results)
        }
    
    def _create_parameter_grids(self) -> Dict[str, List[float]]:
        """Create parameter grids"""
        
        grids = {}
        
        for space in self.parameter_spaces:
            if space.step:
                grid = np.arange(space.min_value, space.max_value + space.step, space.step)
            else:
                num_points = 10
                grid = np.linspace(space.min_value, space.max_value, num_points)
            
            if space.is_integer:
                grid = [int(x) for x in grid]
            
            grids[space.name] = list(grid)
        
        return grids
    
    def _generate_combinations(self, param_grids: Dict[str, List[float]]) -> List[Dict]:
        """Generate all parameter combinations"""
        
        import itertools
        
        param_names = list(param_grids.keys())
        param_values = [param_grids[name] for name in param_names]
        
        combinations = []
        for values in itertools.product(*param_values):
            combination = dict(zip(param_names, values))
            combinations.append(combination)
        
        return combinations


class BayesianOptimizer:
    """Bayesian optimization (simplified)"""
    
    def __init__(self, parameter_spaces: List[ParameterSpace], n_iterations: int = 50):
        self.parameter_spaces = {ps.name: ps for ps in parameter_spaces}
        self.n_iterations = n_iterations
        self.observations = []
    
    def optimize(self, fitness_function: Callable, **kwargs) -> Dict:
        """Run Bayesian optimization"""
        
        logger.info(f"Starting Bayesian optimization: {self.n_iterations} iterations")
        
        for i in range(5):
            params = {name: space.random_value() for name, space in self.parameter_spaces.items()}
            fitness = fitness_function(params, **kwargs)
            self.observations.append({'params': params, 'fitness': fitness})
        
        for i in range(5, self.n_iterations):
            params = self._suggest_next_params()
            fitness = fitness_function(params, **kwargs)
            self.observations.append({'params': params, 'fitness': fitness})
            
            if i % 10 == 0:
                logger.info(f"Iteration {i}/{self.n_iterations}, Best: {max(obs['fitness'] for obs in self.observations):.4f}")
        
        best_observation = max(self.observations, key=lambda x: x['fitness'])
        
        return {
            'best_parameters': best_observation['params'],
            'best_fitness': best_observation['fitness'],
            'all_observations': sorted(self.observations, key=lambda x: x['fitness'], reverse=True)[:50]
        }
    
    def _suggest_next_params(self) -> Dict:
        """Suggest next parameters to try (simplified acquisition function)"""
        
        best_obs = max(self.observations, key=lambda x: x['fitness'])
        
        params = {}
        for name, space in self.parameter_spaces.items():
            if random.random() < 0.3:
                params[name] = space.random_value()
            else:
                best_value = best_obs['params'][name]
                range_size = space.max_value - space.min_value
                noise = random.gauss(0, 0.1 * range_size)
                params[name] = space.clip_value(best_value + noise)
        
        return params


def create_fitness_function_from_backtest(backtester, data: pd.DataFrame, 
                                          strategy_func: Callable) -> Callable:
    """Create fitness function from backtester"""
    
    def fitness_function(params: Dict, **kwargs) -> float:
        """Fitness function for optimization"""
        
        try:
            results = backtester.run_backtest(data, strategy_func, **params)
            
            sharpe = results.sharpe_ratio
            total_return = results.total_return_pct
            max_dd = results.max_drawdown_pct
            win_rate = results.win_rate
            
            fitness = (
                sharpe * 0.3 +
                (total_return / 100) * 0.3 +
                (100 - max_dd) / 100 * 0.2 +
                win_rate / 100 * 0.2
            )
            
            return fitness
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return -999999
    
    return fitness_function


if __name__ == "__main__":
    print("Strategy Optimizer Loaded")
    print("Optimization Methods:")
    print("  - Genetic Algorithm")
    print("  - Grid Search")
    print("  - Bayesian Optimization")
