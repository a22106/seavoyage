"""
Progress callback system for route calculation
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any
from enum import Enum


class ProgressStage(Enum):
    """Stages of route calculation progress"""
    INITIALIZATION = "initialization"
    NETWORK_LOADING = "network_loading"
    RESTRICTION_PROCESSING = "restriction_processing"
    PATHFINDING = "pathfinding"
    ROUTE_OPTIMIZATION = "route_optimization"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressInfo:
    """Information about current progress"""
    stage: ProgressStage
    percent: float  # 0.0 to 100.0
    message: str
    details: Optional[dict] = None
    
    def __str__(self) -> str:
        return f"[{self.stage.value}] {self.percent:.1f}% - {self.message}"


class ProgressCallback(ABC):
    """Abstract base class for progress callbacks"""
    
    @abstractmethod
    def __call__(self, progress: ProgressInfo) -> None:
        """Called when progress is updated
        
        Parameters
        ----------
        progress : ProgressInfo
            Current progress information
        """
        pass


class SimpleProgressCallback(ProgressCallback):
    """Simple progress callback that prints to stdout"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        
    def __call__(self, progress: ProgressInfo) -> None:
        if self.verbose:
            print(f"\r{progress}", end="", flush=True)
            if progress.stage == ProgressStage.COMPLETED or progress.stage == ProgressStage.ERROR:
                print()  # New line after completion


class FunctionProgressCallback(ProgressCallback):
    """Progress callback that calls a user-defined function"""
    
    def __init__(self, func: Callable[[ProgressInfo], None]):
        self.func = func
        
    def __call__(self, progress: ProgressInfo) -> None:
        self.func(progress)


class ProgressTracker:
    """Utility class to manage progress tracking"""
    
    def __init__(self, callback: Optional[ProgressCallback] = None):
        self.callback = callback
        self._stage_weights = {
            ProgressStage.INITIALIZATION: 5,
            ProgressStage.NETWORK_LOADING: 20,
            ProgressStage.RESTRICTION_PROCESSING: 15,
            ProgressStage.PATHFINDING: 50,
            ProgressStage.ROUTE_OPTIMIZATION: 5,
            ProgressStage.FINALIZATION: 5,
        }
        self._current_stage = ProgressStage.INITIALIZATION
        self._stage_progress = {stage: 0.0 for stage in ProgressStage}
        
    def update(self, stage: ProgressStage, percent: float, message: str, 
               details: Optional[dict] = None) -> None:
        """Update progress for current stage
        
        Parameters
        ----------
        stage : ProgressStage
            Current stage of calculation
        percent : float
            Progress percentage within the stage (0-100)
        message : str
            Human-readable progress message
        details : dict, optional
            Additional details about the progress
        """
        if self.callback is None:
            return
            
        self._current_stage = stage
        self._stage_progress[stage] = percent
        
        # Calculate overall progress
        total_percent = self._calculate_total_progress()
        
        progress_info = ProgressInfo(
            stage=stage,
            percent=total_percent,
            message=message,
            details=details
        )
        
        self.callback(progress_info)
        
    def _calculate_total_progress(self) -> float:
        """Calculate total progress across all stages"""
        total_weight = sum(self._stage_weights.values())
        weighted_progress = 0.0
        
        completed_weight = 0.0
        for stage, weight in self._stage_weights.items():
            if stage == self._current_stage:
                # Current stage is partially complete
                weighted_progress += (self._stage_progress[stage] / 100.0) * weight
                break
            else:
                # Previous stages are fully complete
                completed_weight += weight
                
        weighted_progress += completed_weight
        return (weighted_progress / total_weight) * 100.0
        
    def complete(self, message: str = "Route calculation completed") -> None:
        """Mark progress as completed"""
        if self.callback:
            self.callback(ProgressInfo(
                stage=ProgressStage.COMPLETED,
                percent=100.0,
                message=message
            ))
            
    def error(self, message: str, error: Optional[Exception] = None) -> None:
        """Mark progress as error"""
        if self.callback:
            details = {"error": str(error)} if error else None
            self.callback(ProgressInfo(
                stage=ProgressStage.ERROR,
                percent=self._calculate_total_progress(),
                message=message,
                details=details
            ))