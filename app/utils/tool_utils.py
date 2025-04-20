import json
import asyncio
from logging import Logger
from pydantic import BaseModel, create_model, Field
from inspect import signature, Parameter
from typing import Callable, Dict, Any, List, Tuple, Union, Optional
from app.utils.tool_types import UserTool, RouteTool
from functools import wraps


def extract_function_description(func: Callable) -> str:
    docstring = func.__doc__
    if not docstring:
        return ""
    if "------" in docstring:
        return docstring.split("------", 1)[0].strip()
    return docstring.strip()


def parse_param_descriptions(docstring):
    if not docstring or "------" not in docstring:
        return {}
    _, param_section = docstring.split("------", 1)
    descriptions = {}
    for line in param_section.strip().splitlines():
        line = line.strip()
        if line and ":" in line:
            param, desc = line.split(":", 1)
            descriptions[param.strip()] = desc.strip()
    return descriptions


def create_pydantic_model_with_descriptions(func: Callable) -> BaseModel:
    sig = signature(func)
    docstring = func.__doc__
    param_descriptions = parse_param_descriptions(docstring)
    fields = {}

    for param_name, param in sig.parameters.items():
        if param.annotation != Parameter.empty:
            field_type = param.annotation
        else:
            field_type = str

        field_kwargs = {"description": param_descriptions.get(param_name, "")}
        if param.default != Parameter.empty:
            fields[param_name] = (
                field_type,
                Field(default=param.default, **field_kwargs),
            )
        else:
            fields[param_name] = (field_type, Field(..., **field_kwargs))

    return create_model(func.__name__ + "Model", **fields)


def get_tool_schema_from_tool_and_model(
    tool: Callable, model: BaseModel
) -> Dict[str, Any]:
    param_schema = model.model_json_schema()
    properties = param_schema.get("properties", {})
    required = param_schema.get("required", [])

    # Remove "title" from each property
    for prop in properties.values():
        prop.pop("title", None)

    return {
        "type": "function",
        "name": tool.__name__,
        "description": extract_function_description(tool),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def build_route_schema(
    fields: Dict[str, str],
    current_agent_field: str,
    target_agent_field: str,
    required: Optional[List[str]] = None,
    agent_names: Optional[List[str]] = None,
    agent_descriptions: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    # Validate required fields
    if current_agent_field not in fields:
        raise ValueError(f"Missing current agent field: {current_agent_field}")
    if target_agent_field not in fields:
        raise ValueError(f"Missing target agent field: {target_agent_field}")
    for k in fields:
        if not isinstance(k, str):
            raise ValueError(f"Field name must be a string: {k}")
    properties = {}
    for name, desc in fields.items():
        if name == target_agent_field:
            # Use anyOf for agent selection, including agent descriptions; fallback enum commented
            properties[name] = {
                "type": "string",
                # "anyOf": [
                #     {
                #         "const": agent_name,
                #         # "title": agent_name,
                #         "description": (
                #             agent_descriptions.get(agent_name, "")
                #             if agent_descriptions
                #             else ""
                #         ),
                #     }
                #     for agent_name in (agent_names or [])
                # ],
                "enum": agent_names,
                "description": desc,
                # "enum": agent_names,
            }
        else:
            properties[name] = {
                "type": "string",
                "description": desc,
            }
    req = required or list(fields.keys())
    return {
        "type": "object",
        "properties": properties,
        "required": req,
    }


def get_tool_schema_from_tool(tool: Callable) -> Dict[str, Any]:
    model = create_pydantic_model_with_descriptions(tool)
    return get_tool_schema_from_tool_and_model(tool, model)


def validate_schema_list(schema_list: List[Dict[str, Any]]) -> bool:
    def validate_schema(schema: Dict[str, Any]) -> bool:
        expected_keys = {"type", "name", "description", "parameters"}
        if not all(key in schema for key in expected_keys):
            return False
        if schema["type"] != "function":
            return False
        if not isinstance(schema["parameters"], dict):
            return False
        param_keys = {"type", "properties", "required"}
        if not all(key in schema["parameters"] for key in param_keys):
            return False
        return True

    try:
        for schema in schema_list:
            if not validate_schema(schema):
                raise ValueError(f"Invalid schema format: {schema}")
        return True
    except ValueError as e:
        print(f"Schema validation error: {e}")
        return False


def validate_args_against_schema(
    schema: Dict[str, Any], args: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """
    Validate that the args dict contains all required parameters defined in the schema.
    Returns a tuple: (is_valid, missing_fields).
    """
    try:
        required = schema.get("parameters", {}).get("required", [])
        missing_fields = [param for param in required if param not in args]
        return len(missing_fields) == 0, missing_fields
    except Exception:
        return False, ["Error validating schema"]


def user_tool(func: Callable) -> UserTool:
    """Decorator to register a function as a UserTool."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    # Generate and attach schema
    return UserTool(
        func=wrapper,
        name=func.__name__,
        description=extract_function_description(func),
    )


def route_tool(func: Callable) -> RouteTool:
    """Decorator to register a function as a RouteTool."""

    @wraps(func)
    def wrapper(
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return func(*args, **kwargs)

    # Generate and attach schema
    return RouteTool(
        func=wrapper,
        name=func.__name__,
        description=extract_function_description(func),
    )


def find_tool_by_name(
    tools: List[Union[UserTool, RouteTool]],
    tool_name: str,
    logger: Logger,
) -> Union[UserTool, RouteTool, None]:
    """
    Finds a tool object by name from the provided list, logging an error if not found.
    """
    tool = next((t for t in tools or [] if t.name == tool_name), None)
    if tool is None:
        logger.error(f"No matching tool wrapper found for: {tool_name}")
    return tool


async def handle_user_tool_call(
    tool_obj: UserTool,
    arguments: str,
    logger: Logger,
) -> str:
    """
    Handles the logic for UserTool objects and returns the result.
    """
    try:
        logger.info(f"Invoking UserTool: {tool_obj.name}")
        args = json.loads(arguments) if arguments else {}
        result = (
            await tool_obj.func(**args)
            if asyncio.iscoroutinefunction(tool_obj.func)
            else tool_obj.func(**args)
        )
        return str(result)
    except Exception as e:
        logger.error(f"Error executing UserTool {tool_obj.name}: {e}")
        return f"Error: {e}"


async def handle_route_tool_call(
    tool_obj: RouteTool,
    arguments: str,
    agent_switch_message: str,
    logger: Logger,
) -> Tuple[str, Dict, bool]:
    """
    Handles the logic for RouteTool objects and returns the result along with parsed arguments and validation flag.
    """
    try:
        logger.info(f"RouteTool call received: {tool_obj.name}")
        args = json.loads(arguments) if arguments else {}
        # Route handling deferred to agent or caller
        correct_args, missing_fields = validate_args_against_schema(
            tool_obj.schema, args
        )
        if not correct_args:
            logger.error(
                f"Missing required fields for tool '{tool_obj.name}': {missing_fields}"
            )
            return (
                f"Error: Missing required fields: {', '.join(missing_fields)}",
                {},
                False,
            )

        try:
            _ = (
                await tool_obj.func(**args)
                if asyncio.iscoroutinefunction(tool_obj.func)
                else tool_obj.func(**args)
            )
        except Exception as func_error:
            logger.warning(
                f"Tool function '{tool_obj.name}' failed during execution: {func_error}"
            )

        return agent_switch_message, args, True
    except Exception as e:
        logger.error(f"Error handling RouteTool {tool_obj.name}: {e}")
        return f"Error: {e}", {}, False


def format_string(template: str, data: Dict[str, Any]) -> str:
    """
    Formats a string using the provided template and data.
    If a key is missing in the data, it leaves the placeholder unchanged.
    """

    class SafeDict(dict):
        def __missing__(self, key):
            return f"{{{key}}}"

    if not data:
        return template
    return template.format_map(SafeDict(data))
