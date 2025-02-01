from pydantic import BaseModel, create_model, Field
from inspect import signature, Parameter
from typing import Callable, Dict, Any, List


# Example user tool
def obtener_clima(ciudad: str):
    """
    Obtiene el clima de la ciudad dada.
    ------
    ciudad: Nombre de la ciudad para la que se quiere obtener el clima.
    """
    # Example mock
    return f"El clima en {ciudad} es soleado con 25 grados."


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
