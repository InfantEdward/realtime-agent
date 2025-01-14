from pydantic import BaseModel, create_model, Field
from inspect import signature, Parameter
from typing import Callable, Dict, Any, List


def extract_function_description(func: Callable) -> str:
    """
    Extracts the main function description from the docstring of a function.

    Args:
        func (Callable): The function whose docstring is to be extracted.

    Returns:
        str: The main description of the function.
    """
    docstring = func.__doc__
    if not docstring:
        return ""
    if "------" in docstring:
        return docstring.split("------", 1)[0].strip()
    return docstring.strip()


def parse_param_descriptions(docstring):
    """
    Extracts parameter descriptions from the docstring.

    Args:
        docstring (str): The function's docstring.

    Returns:
        dict: A dictionary mapping parameter names to descriptions.
    """
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
    """
    Creates a Pydantic BaseModel subclass from the parameters of a given function,
    including parameter descriptions.

    Args:
        func (Callable): The function to create a model for.

    Returns:
        Type[BaseModel]: A dynamically created BaseModel subclass.
    """
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
    """
    Generates a schema for a given tool function and its corresponding Pydantic model.

    Args:
        tool (Callable): The tool function.
        model (BaseModel): The Pydantic model representing the tool's parameters.

    Returns:
        Dict[str, Any]: The schema representing the tool and its parameters.
    """
    param_schema = model.model_json_schema()
    properties = param_schema.get("properties")
    required = param_schema.get("required")

    for property in properties.values():
        property.pop("title")

    schema = {
        "type": "function",
        "name": tool.__name__,
        "description": tool.__doc__.strip(),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }
    return schema


def get_tool_schema_from_tool(tool: Callable) -> Dict[str, Any]:
    """
    Generates a schema for a given tool function.

    Args:
        tool (Callable): The tool function.

    Returns:
        Dict[str, Any]: The schema representing the tool and its parameters.
    """
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
