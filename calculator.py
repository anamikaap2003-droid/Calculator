"""Expression engine for the calculator. Uses Python's AST, not eval()."""
import ast
import math
import operator
import re

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log10,
    "ln": math.log,
    "pi": math.pi,
    "e": math.e,
}
MAX_EXPRESSION_LENGTH = 250


class CalculatorError(ValueError):
    """Raised when the calculator expression is invalid or unsafe."""


def _prepare_expression(expression: str) -> str:
    expression = expression.strip()
    if not expression:
        raise CalculatorError("Enter a calculation first.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculatorError("That calculation is too long.")
    # Calculator-style percentage: 50% -> (50/100). In this app, % is remainder;
    # use the explicit percent key only when followed by a value is desired.
    # Multiplication symbol and division symbol are accepted for display-style input.
    expression = expression.replace("×", "*").replace("÷", "/").replace("−", "-")
    expression = expression.replace("π", "pi")
    # Support implicit multiplication for common calculator input: 2(3+4), 2pi, (2+3)(4+5).
    expression = re.sub(r"(?<=[0-9.)])\s*(?=(?:pi|e|sqrt|abs|round|sin|cos|tan|log|ln)\b)", "*", expression)
    expression = re.sub(r"(?<=[0-9.)])\s*(?=\()", "*", expression)
    expression = re.sub(r"(?<=\))\s*(?=[0-9])", "*", expression)
    return expression


def _evaluate_node(node):
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):
            raise CalculatorError("Boolean values are not supported.")
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise CalculatorError("Cannot divide by zero.")
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise CalculatorError("Exponent is too large.")
        try:
            result = _BINARY_OPERATORS[type(node.op)](left, right)
        except (OverflowError, ZeroDivisionError, ValueError) as exc:
            raise CalculatorError(str(exc) or "This calculation is not supported.") from exc
        return _validate_result(result)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _evaluate_node(node.operand) if isinstance(node.op, ast.UAdd) else -_evaluate_node(node.operand)

    if isinstance(node, ast.Name) and node.id in ("pi", "e"):
        return _FUNCTIONS[node.id]

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
        name = node.func.id
        if name in ("pi", "e"):
            raise CalculatorError(f"{name} is a constant, not a function.")
        if node.keywords:
            raise CalculatorError("Named function arguments are not supported.")
        args = [_evaluate_node(arg) for arg in node.args]
        expected = 2 if name == "round" else 1
        if len(args) not in ([1, 2] if name == "round" else [1]):
            raise CalculatorError(f"{name}() received the wrong number of arguments.")
        try:
            if name in ("sqrt", "log", "ln") and args[0] <= 0 and name != "sqrt":
                raise CalculatorError("Logarithm input must be greater than zero.")
            if name == "sqrt" and args[0] < 0:
                raise CalculatorError("Square root of a negative number is not a real number.")
            return _validate_result(_FUNCTIONS[name](*args))
        except (ValueError, OverflowError, TypeError) as exc:
            if isinstance(exc, CalculatorError):
                raise
            raise CalculatorError(str(exc) or "Invalid function input.") from exc

    raise CalculatorError("Unsupported expression. Use numbers, operators, parentheses, and supported functions.")


def _validate_result(value):
    if isinstance(value, complex):
        raise CalculatorError("The result is not a real number.")
    if isinstance(value, float) and not math.isfinite(value):
        raise CalculatorError("The result is too large to display.")
    if isinstance(value, int) and value.bit_length() > 4096:
        raise CalculatorError("The result is too large.")
    return value


def evaluate_expression(expression: str):
    """Safely evaluate arithmetic expressions such as 12 + 3 * (8 - 2) / 4."""
    prepared = _prepare_expression(expression)
    try:
        tree = ast.parse(prepared, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("Check the expression and operators.") from exc
    return _validate_result(_evaluate_node(tree))


def format_result(value, precision=12):
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if abs(value) < 1e-12:
            value = 0.0
        rounded = round(value, precision)
        if rounded.is_integer():
            return f"{int(rounded):,}"
        return f"{rounded:,.{precision}f}".rstrip("0").rstrip(".")
    return str(value)
