"""
PERFORMANCE OPTIMIZER
Advanced caching, data pipeline optimization, and memory management
"""

import pandas as pd
import numpy as np
from functools import lru_cache, wraps
from datetime import datetime, timedelta
import hashlib
import json
import pickle
import time
from typing import Dict, List, Any, Callable
import logging

logger = logging.getLogger(__name__)


class DataCache:
    """Intelligent data caching system"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Any:
        """Get cached value"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                self.hits += 1
                return entry['data']
            else:
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, data: Any):
        """Set cached value"""
        self.cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self.cache)
        }


def cached_market_data(ttl: int = 300):
    """Decorator for caching market data"""
    cache = DataCache(ttl_seconds=ttl)
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = cache._generate_key(*args, **kwargs)
            
            cached_result = cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache HIT for {func.__name__}")
                return cached_result
            
            logger.debug(f"Cache MISS for {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(key, result)
            
            return result
        
        wrapper.cache = cache
        return wrapper
    
    return decorator


class DataPipelineOptimizer:
    """Optimize data processing pipelines"""
    
    @staticmethod
    def batch_indicator_calculation(df: pd.DataFrame, indicators: List[str]) -> pd.DataFrame:
        """Calculate multiple indicators in optimized batches"""
        
        if df.empty:
            return df
        
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series([0] * len(df)))
        
        for indicator in indicators:
            if indicator == 'ema_20':
                df['ema_20'] = close.ewm(span=20, adjust=False).mean()
            
            elif indicator == 'ema_50':
                df['ema_50'] = close.ewm(span=50, adjust=False).mean()
            
            elif indicator == 'ema_200':
                df['ema_200'] = close.ewm(span=200, adjust=False).mean()
            
            elif indicator == 'rsi':
                delta = close.diff()
                gain = delta.where(delta > 0, 0)
                loss = (-delta).where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss
                df['rsi'] = 100 - (100 / (1 + rs))
            
            elif indicator == 'macd':
                ema_12 = close.ewm(span=12, adjust=False).mean()
                ema_26 = close.ewm(span=26, adjust=False).mean()
                df['macd'] = ema_12 - ema_26
                df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
                df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            elif indicator == 'bollinger':
                df['bb_middle'] = close.rolling(window=20).mean()
                bb_std = close.rolling(window=20).std()
                df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
                df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            elif indicator == 'atr':
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                df['atr'] = tr.rolling(window=14).mean()
            
            elif indicator == 'stochastic':
                low_14 = low.rolling(window=14).min()
                high_14 = high.rolling(window=14).max()
                df['stoch_k'] = 100 * ((close - low_14) / (high_14 - low_14))
                df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            elif indicator == 'adx':
                plus_dm = high.diff()
                minus_dm = -low.diff()
                plus_dm[plus_dm < 0] = 0
                minus_dm[minus_dm < 0] = 0
                
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                
                atr = tr.rolling(window=14).mean()
                plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr)
                minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr)
                
                dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
                df['adx'] = dx.rolling(window=14).mean()
        
        return df
    
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame memory usage"""
        
        for col in df.columns:
            col_type = df[col].dtype
            
            if col_type != object:
                c_min = df[col].min()
                c_max = df[col].max()
                
                if str(col_type)[:3] == 'int':
                    if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                        df[col] = df[col].astype(np.int8)
                    elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                        df[col] = df[col].astype(np.int16)
                    elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                        df[col] = df[col].astype(np.int32)
                
                elif str(col_type)[:5] == 'float':
                    if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                        df[col] = df[col].astype(np.float32)
        
        return df
    
    @staticmethod
    def parallel_symbol_processing(symbols: List[str], process_func: Callable, max_workers: int = 4) -> Dict:
        """Process multiple symbols in parallel"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {executor.submit(process_func, symbol): symbol for symbol in symbols}
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    results[symbol] = future.result()
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    results[symbol] = None
        
        return results


class PerformanceMonitor:
    """Monitor system performance"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str):
        """End timing and record"""
        if operation in self.start_times:
            elapsed = time.time() - self.start_times[operation]
            
            if operation not in self.metrics:
                self.metrics[operation] = []
            
            self.metrics[operation].append(elapsed)
            del self.start_times[operation]
            
            return elapsed
        return None
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        stats = {}
        
        for operation, times in self.metrics.items():
            stats[operation] = {
                'count': len(times),
                'total': sum(times),
                'avg': np.mean(times),
                'min': min(times),
                'max': max(times),
                'std': np.std(times)
            }
        
        return stats
    
    def print_report(self):
        """Print performance report"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("PERFORMANCE REPORT")
        print("="*60)
        
        for operation, metrics in stats.items():
            print(f"\n{operation}:")
            print(f"  Count: {metrics['count']}")
            print(f"  Total: {metrics['total']:.3f}s")
            print(f"  Avg: {metrics['avg']:.3f}s")
            print(f"  Min: {metrics['min']:.3f}s")
            print(f"  Max: {metrics['max']:.3f}s")
            print(f"  Std: {metrics['std']:.3f}s")
        
        print("="*60 + "\n")


def performance_tracked(monitor: PerformanceMonitor, operation_name: str):
    """Decorator to track function performance"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor.start_timer(operation_name)
            result = func(*args, **kwargs)
            monitor.end_timer(operation_name)
            return result
        return wrapper
    return decorator


class MemoryOptimizer:
    """Optimize memory usage"""
    
    @staticmethod
    def get_memory_usage() -> Dict:
        """Get current memory usage"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            'rss_mb': mem_info.rss / 1024 / 1024,
            'vms_mb': mem_info.vms / 1024 / 1024,
            'percent': process.memory_percent()
        }
    
    @staticmethod
    def cleanup_old_data(data_dict: Dict, max_age_hours: int = 24):
        """Remove old data from dictionary"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        keys_to_remove = []
        for key, value in data_dict.items():
            if isinstance(value, dict) and 'timestamp' in value:
                if value['timestamp'] < cutoff_time:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del data_dict[key]
        
        return len(keys_to_remove)


class QueryOptimizer:
    """Optimize data queries"""
    
    @staticmethod
    def filter_dataframe_efficient(df: pd.DataFrame, conditions: Dict) -> pd.DataFrame:
        """Efficiently filter DataFrame with multiple conditions"""
        
        mask = pd.Series([True] * len(df), index=df.index)
        
        for column, condition in conditions.items():
            if column not in df.columns:
                continue
            
            if isinstance(condition, dict):
                if 'min' in condition:
                    mask &= df[column] >= condition['min']
                if 'max' in condition:
                    mask &= df[column] <= condition['max']
                if 'equals' in condition:
                    mask &= df[column] == condition['equals']
                if 'in' in condition:
                    mask &= df[column].isin(condition['in'])
            else:
                mask &= df[column] == condition
        
        return df[mask]
    
    @staticmethod
    def aggregate_efficiently(df: pd.DataFrame, group_by: str, agg_funcs: Dict) -> pd.DataFrame:
        """Efficient aggregation"""
        return df.groupby(group_by).agg(agg_funcs)


if __name__ == "__main__":
    print("Performance Optimizer Module Loaded")
    print("Features:")
    print("  - Intelligent data caching")
    print("  - Batch indicator calculation")
    print("  - Memory optimization")
    print("  - Performance monitoring")
    print("  - Parallel processing")
