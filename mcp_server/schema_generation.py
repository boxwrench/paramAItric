"""Generate host-facing JSON schemas from validated input dataclasses."""
from __future__ import annotations

import ast
import dataclasses
import inspect
import re
import textwrap
import types
import typing
from typing import Any, get_args, get_origin, get_type_hints

from mcp_server import schemas


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


INPUTS = {
    _snake(name.removesuffix("Input")): value
    for name, value in vars(schemas).items()
    if name.endswith("Input") and dataclasses.is_dataclass(value)
}


def _json_type(annotation: Any) -> dict:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (types.UnionType, typing.Union):
        concrete = [arg for arg in args if arg is not type(None)]
        return _json_type(concrete[0]) if len(concrete) == 1 else {}
    if origin is list:
        return {"type": "array", "items": _json_type(args[0]) if args else {}}
    if origin is dict:
        return {"type": "object"}
    return {bool: {"type": "boolean"}, int: {"type": "integer"},
            float: {"type": "number"}, str: {"type": "string"}}.get(annotation, {})


class PayloadVisitor(ast.NodeVisitor):
    def __init__(self, names: set[str]) -> None:
        self.names, self.required, self.defaults = names, set(), {}
        self.validators, self.enums = {}, {}

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if (isinstance(node.value, ast.Name) and node.value.id == "payload"
                and isinstance(node.slice, ast.Constant) and node.slice.value in self.names):
            self.required.add(node.slice.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "payload" and node.func.attr == "get" and node.args):
            key = node.args[0].value if isinstance(node.args[0], ast.Constant) else None
            if key in self.names and len(node.args) > 1:
                try:
                    self.defaults[key] = ast.literal_eval(node.args[1])
                except (ValueError, TypeError):
                    pass
        if isinstance(node.func, ast.Name) and len(node.args) > 1:
            key = node.args[1].value if isinstance(node.args[1], ast.Constant) else None
            if key in self.names and node.func.id.startswith("_require_"):
                self.validators[key] = node.func.id
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        test = node.test
        if (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
                and test.left.id in self.names and len(test.ops) == 1):
            field, op, right = test.left.id, test.ops[0], test.comparators[0]
            if isinstance(op, ast.NotIn) and isinstance(right, (ast.Set, ast.List, ast.Tuple)):
                values = [item.value for item in right.elts if isinstance(item, ast.Constant)]
                if values and all(isinstance(value, str) for value in values):
                    self.enums[field] = values
            elif isinstance(op, ast.NotEq) and isinstance(right, ast.Constant) and isinstance(right.value, str):
                self.enums[field] = [right.value]
        self.generic_visit(node)


def _payload_schema(input_class: type, allow_units: bool) -> dict:
    fields, hints = list(dataclasses.fields(input_class)), get_type_hints(input_class)
    visitor = PayloadVisitor({field.name for field in fields})
    visitor.visit(ast.parse(textwrap.dedent(inspect.getsource(input_class.from_payload))))
    properties = {}
    for field in fields:
        name, prop = field.name, _json_type(hints.get(field.name, Any))
        prop["description"] = _description(name)
        validator = visitor.validators.get(name)
        if validator == "_require_positive_number":
            prop["exclusiveMinimum"] = 0
        elif validator == "_require_non_negative_number":
            prop["minimum"] = 0
        elif validator == "_require_non_empty_string":
            prop["minLength"] = 1
        if name in visitor.defaults:
            prop["default"] = visitor.defaults[name]
        if name in visitor.enums:
            prop["enum"] = visitor.enums[name]
        if name.endswith("_cm"):
            prop["x-unit-selector"] = "units"
        if name.endswith("_deg"):
            prop["x-unit"] = "degrees"
        properties[name] = prop
    if allow_units:
        properties["units"] = {"type": "string", "enum": ["cm", "mm", "in"],
                               "default": "cm", "description": "Unit for every field ending in _cm."}
    result = {"type": "object", "properties": properties, "additionalProperties": False}
    required = [field.name for field in fields if field.name in visitor.required]
    if required:
        result["required"] = required
    return result


def _description(name: str) -> str:
    if name == "output_path":
        return "STL path; a bare filename is saved in Documents/ParamAItric Exports."
    if name.endswith("_cm"):
        return "Dimension in selected units (cm by default), normalized to centimeters."
    if name.endswith("_deg"):
        return "Angle in degrees."
    if name.endswith("_name"):
        return "Human-readable CAD entity name."
    return name.replace("_", " ").capitalize() + "."


MANUAL = {
    "get_workflow_requirements": {
        "type": "object",
        "properties": {
            "workflow": {
                "type": "string",
                "minLength": 1,
                "description": "Name of the workflow to get requirements/schema for (e.g. spacer, cylinder, bracket, etc.)."
            }
        },
        "required": ["workflow"],
        "additionalProperties": False
    },
    "build_workflow": {
        "type": "object",
        "properties": {
            "workflow": {
                "type": "string",
                "minLength": 1,
                "description": "Name of the workflow to build (e.g. spacer, cylinder, bracket, etc.)."
            },
            "parameters": {
                "type": "object",
                "description": "Workflow parameters matching the schema from cad_get_requirements."
            }
        },
        "required": ["workflow", "parameters"],
        "additionalProperties": False
    },
    "inspect_design": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "minLength": 1,
                "description": "Name of the inspection operation (e.g. list_design_bodies, get_body_info, get_body_faces, get_body_edges, find_face)."
            },
            "parameters": {
                "type": "object",
                "description": "Parameters for the specified inspection operation."
            }
        },
        "required": ["operation", "parameters"],
        "additionalProperties": False
    },
    "recommend_workflow": {"type": "object", "properties": {
        "intent": {"type": "string", "minLength": 1}, "constraints": {"type": "object"}},
        "required": ["intent"], "additionalProperties": False},
    "list_design_bodies": {"type": "object", "properties": {}, "additionalProperties": False},
    "get_body_info": {"type": "object", "properties": {"body_token": {"type": "string", "minLength": 1}}, "required": ["body_token"], "additionalProperties": False},
    "get_body_faces": {"type": "object", "properties": {"body_token": {"type": "string", "minLength": 1}}, "required": ["body_token"], "additionalProperties": False},
    "get_body_edges": {"type": "object", "properties": {"body_token": {"type": "string", "minLength": 1}}, "required": ["body_token"], "additionalProperties": False},
    "find_face": {"type": "object", "properties": {"body_token": {"type": "string", "minLength": 1}, "selector": {"type": "string", "enum": ["top", "bottom", "left", "right", "front", "back"]}}, "required": ["body_token", "selector"], "additionalProperties": False},
    "convert_bodies_to_components": {"type": "object", "properties": {
        "body_tokens": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
        "component_names": {"type": "array", "items": {"type": "string"}}},
        "required": ["body_tokens"], "additionalProperties": False},
}


def tool_input_schema(tool_name: str, method_name: str) -> dict | None:
    input_class = INPUTS.get(method_name)
    payload = (_payload_schema(input_class, method_name.startswith("create_"))
               if input_class else MANUAL.get(method_name))
    if payload is None:
        return None
    return {"type": "object", "properties": {"payload": payload},
            "required": ["payload"], "additionalProperties": False,
            "title": f"{tool_name}Arguments"}
