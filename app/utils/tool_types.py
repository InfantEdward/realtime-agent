from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any


@dataclass
class UserTool:
    func: Callable[..., str]
    name: str
    description: str = ""
    schema: Optional[Dict[str, Any]] = None


@dataclass
class RouteTool:
    func: Callable[[str, str, str], str]
    name: str
    description: str = ""
    schema: Optional[Dict[str, Any]] = None
