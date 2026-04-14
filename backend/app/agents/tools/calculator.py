import ast
import operator

from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression. Use for arithmetic, percentages."""

    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def safe_eval(node):
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in allowed_operators:
                raise ValueError("Unsupported operator")
            return allowed_operators[op_type](safe_eval(node.left), safe_eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in allowed_operators:
                raise ValueError("Unsupported operator")
            return allowed_operators[op_type](safe_eval(node.operand))
        raise ValueError("Unsafe expression")

    try:
        tree = ast.parse(expression, mode="eval")
        result = safe_eval(tree.body)
        return f"Result: {result}"
    except Exception as exc:
        return f"Error: {str(exc)}"
