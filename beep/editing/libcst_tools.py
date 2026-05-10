"""LibCST-based safe Python code editing."""

from __future__ import annotations

from pathlib import Path

import libcst as cst


def add_import(source: str, module: str, names: list[str]) -> str:
    """Add an import statement to a Python file while preserving formatting."""
    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return source

    import_stmt = _build_import(module, names)
    transformer = _AddImportTransformer(import_stmt)
    modified = tree.visit(transformer)
    return modified.code


def rename_symbol(source: str, old_name: str, new_name: str) -> str:
    """Rename a function or class throughout a file."""
    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return source

    transformer = _RenameSymbolTransformer(old_name, new_name)
    modified = tree.visit(transformer)
    return modified.code


def add_function_stub(
    source: str,
    function_name: str,
    params: list[str],
    return_type: str = "None",
    docstring: str = "",
) -> str:
    """Append a new function definition to the source."""
    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return source

    params_str = ", ".join(params) if params else "self"
    body = [cst.Pass()]
    if docstring:
        body.insert(0, cst.Expr(cst.SimpleString(f'"""{docstring}"""')))

    func = cst.FunctionDef(
        name=cst.Name(function_name),
        params=cst.Parameters(
            params=[cst.Param(name=cst.Name(p)) for p in params.split(",") if p.strip()]
        ),
        body=cst.IndentedBlock(body=body),
        returns=cst.Name(return_type) if return_type else None,
    )

    new_body = list(tree.body) + [cst.SimpleStatementLine(body=[]), func]
    modified = tree.with_changes(body=new_body)
    return modified.code


class _AddImportTransformer(cst.CSTTransformer):
    def __init__(self, import_stmt: cst.CSTNode) -> None:
        self._import = import_stmt
        self._added = False

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.Module:
        if not self._added:
            return updated_node.with_changes(body=[self._import, *updated_node.body])
        return updated_node

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine:
        if not self._added and isinstance(updated_node.body[0], (cst.Import, cst.ImportFrom)):
            return updated_node
        return updated_node


class _RenameSymbolTransformer(cst.CSTTransformer):
    def __init__(self, old_name: str, new_name: str) -> None:
        self._old = old_name
        self._new = new_name

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if updated_node.value == self._old:
            return updated_node.with_changes(value=self._new)
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if updated_node.name.value == self._old:
            return updated_node.with_changes(name=cst.Name(self._new))
        return updated_node

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if updated_node.name.value == self._old:
            return updated_node.with_changes(name=cst.Name(self._new))
        return updated_node


def _build_import(module: str, names: list[str]) -> cst.CSTNode:
    if len(names) == 1 and names[0] == "*":
        return cst.SimpleStatementLine(
            body=[
                cst.ImportFrom(
                    module=_dotted_name(module),
                    names=[cst.ImportAlias(name=cst.Name("*"))],
                )
            ]
        )
    return cst.SimpleStatementLine(
        body=[
            cst.ImportFrom(
                module=_dotted_name(module),
                names=[cst.ImportAlias(name=cst.Name(n)) for n in names],
            )
        ]
    )


def _dotted_name(module: str) -> cst.BaseExpression:
    parts = module.split(".")
    if len(parts) == 1:
        return cst.Name(parts[0])
    result: cst.BaseExpression = cst.Name(parts[0])
    for part in parts[1:]:
        result = cst.Attribute(value=result, attr=cst.Name(part))
    return result
