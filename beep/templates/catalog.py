"""Built-in template definitions for the templates domain."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Template:
    """A code generation template."""

    name: str
    description: str
    category: str
    content: str
    variables: list[str] = field(default_factory=list)
    file_extension: str = ""
    source: str = "builtin"


BUILTIN_TEMPLATES: list[Template] = [
    Template(
        name="fastapi-route",
        description="FastAPI route with error handling",
        category="python",
        file_extension=".py",
        variables=["route_name", "path"],
        content='''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class {route_name}Request(BaseModel):
    pass


class {route_name}Response(BaseModel):
    pass


@router.get("/{path}", response_model={route_name}Response)
async def {route_name}():
    """{route_name} endpoint."""
    return {route_name}Response()
''',
    ),
    Template(
        name="react-component",
        description="React functional component with TypeScript",
        category="typescript",
        file_extension=".tsx",
        variables=["component_name"],
        content='''import React from "react";

interface {component_name}Props {{
  // Add props here
}}

export const {component_name}: React.FC<{component_name}Props> = (props) => {{
  return (
    <div>
      <h1>{component_name}</h1>
    </div>
  );
}};

export default {component_name};
''',
    ),
    Template(
        name="python-class",
        description="Python class with type hints and docstrings",
        category="python",
        file_extension=".py",
        variables=["class_name"],
        content='''"""{class_name} module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class {class_name}:
    """{class_name} description."""

    def __init__(self) -> None:
        """Initialize {class_name}."""
        pass

    def __str__(self) -> str:
        """Return string representation."""
        return f"{class_name}()"
''',
    ),
    Template(
        name="pytest-test",
        description="Pytest test file with fixtures",
        category="python",
        file_extension=".py",
        variables=["module_name"],
        content='''"""Tests for {module_name}."""

import pytest


@pytest.fixture
def setup_{module_name}():
    """Setup test fixtures."""
    yield


def test_{module_name}_creation(setup_{module_name}):
    """Test {module_name} creation."""
    assert True


def test_{module_name}_behavior(setup_{module_name}):
    """Test {module_name} behavior."""
    assert True
''',
    ),
    Template(
        name="go-handler",
        description="Go HTTP handler with error handling",
        category="go",
        file_extension=".go",
        variables=["handler_name"],
        content='''package main

import (
	"encoding/json"
	"net/http"
)

type {handler_name}Request struct {{
}}

type {handler_name}Response struct {{
}}

func {handler_name}Handler(w http.ResponseWriter, r *http.Request) {{
	if r.Method != http.MethodGet {{
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode({handler_name}Response{{}})
}}
''',
    ),
]