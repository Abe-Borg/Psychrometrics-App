"""
Abstract base class for psychrometric process solvers.
"""

from abc import ABC, abstractmethod

from app.models.process import ProcessInput, ProcessOutput


class ProcessSolver(ABC):
    """Base class for all process solvers."""

    @abstractmethod
    def solve(self, process_input: ProcessInput) -> ProcessOutput:
        """Solve the process and return the result."""
        ...
