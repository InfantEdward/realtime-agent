import json
import os
from app.models.config_model import ConfigModel
from app.models.app_config_model import AppConfigModel
import app.user_tools as user_tools
import app.route_tool as route_tool_module
from app.utils.tool_utils import build_route_schema


# Paths to config files
AGENTS_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../static/agents.json"
)
APP_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "../static/app_config.json"
)


def load_agent_configs(path: str) -> list[ConfigModel]:
    """Read agents.json and return a list of ConfigModel with tools attached."""
    agents: list[ConfigModel] = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            raw_agents = json.load(f)
            agents = [
                ConfigModel(
                    name=raw["name"],
                    description=raw.get("description"),
                    **raw["config"],
                )
                for raw in raw_agents
            ]
    for cfg in agents:
        if (
            cfg.TOOL_NAMES
            and cfg.TOOL_SCHEMA_LIST
            and len(cfg.TOOL_NAMES) != len(cfg.TOOL_SCHEMA_LIST)
        ):
            raise ValueError(
                f"Agent '{cfg.name}' has mismatched lengths for TOOL_NAMES ({len(cfg.TOOL_NAMES)}) "
                f"and TOOL_SCHEMA_LIST ({len(cfg.TOOL_SCHEMA_LIST)}). They must match."
            )
    # Collect all agent names and descriptions for dynamic schema
    all_agent_names = [cfg.name for cfg in agents]
    agent_descriptions = {cfg.name: cfg.description or "" for cfg in agents}
    is_single_agent = len(agents) == 1
    for cfg in agents:
        tool_list = []
        # --- Restriction: Only one route tool allowed per agent ---
        route_tool_count = 0
        for tname in cfg.TOOL_NAMES or []:
            if hasattr(route_tool_module, tname):
                route_tool_count += 1
        if route_tool_count > 1:
            raise ValueError(
                f"Agent '{cfg.name}' has more than one route tool in TOOL_NAMES. "
                "Only one route tool is allowed per agent."
            )
        # ---------------------------------------------------------
        for tname in cfg.TOOL_NAMES or []:
            # If only one agent, ignore route tool even if listed
            if is_single_agent and hasattr(route_tool_module, tname):
                continue
            if hasattr(user_tools, tname):
                tool_list.append(getattr(user_tools, tname))
            elif hasattr(route_tool_module, tname):
                tool_obj = getattr(route_tool_module, tname)
                params = getattr(route_tool_module, "schema_params", None)
                if not (
                    params
                    and hasattr(params, "get")
                    and tool_obj.name == tname
                ):
                    raise ValueError(
                        f"Schema parameters are missing or incomplete for tool '{tname}' in agent '{cfg.name}'."
                    )
                schema = build_route_schema(
                    fields=params["FIELDS"],
                    current_agent_field=params["CURRENT_AGENT_FIELD"],
                    target_agent_field=params["TARGET_AGENT_FIELD"],
                    required=params.get("REQUIRED_FIELDS"),
                    agent_names=all_agent_names,
                    agent_descriptions=agent_descriptions,
                )
                tool_obj.schema = {
                    "type": "function",
                    "name": tool_obj.name,
                    "description": params["DESCRIPTION"],
                    "parameters": schema,
                }
                tool_list.append(tool_obj)
            else:
                raise ValueError(
                    f"Unknown tool '{tname}' for agent '{cfg.name}'"
                )
        cfg.TOOL_LIST = tool_list
    return agents


def load_app_config(path: str) -> AppConfigModel | None:
    """Read app_config.json and return an AppConfigModel or None if missing."""
    data: dict = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    # Override properties from env vars if set
    env_level = os.getenv("LOG_LEVEL")
    if env_level is not None:
        data["LOG_LEVEL"] = env_level
    env_dir = os.getenv("LOG_DIR")
    if env_dir is not None:
        data["LOG_DIR"] = env_dir
    env_exc = os.getenv("EXC_INFO")
    if env_exc is not None:
        data["EXC_INFO"] = env_exc.lower() in ("true", "1", "yes")
    return AppConfigModel(**data)


# Initialize configurations
AGENTS = load_agent_configs(AGENTS_CONFIG_PATH)
APP_CONFIG = load_app_config(APP_CONFIG_PATH)


def get_agent_configs() -> list[ConfigModel]:
    """Returns a list of ConfigModel objects loaded from agents.json."""
    return AGENTS


def get_app_config() -> AppConfigModel | None:
    """Returns the AppConfigModel loaded from app_config.json."""
    return APP_CONFIG
