import ast
import sys

STRATEGY_ENGINE_PATH = r"d:\Infinite\Infinity\Strategy\strategy_engine.py"
ALLOWED_FUNCTIONS = {"_hash_obj", "_hash_bytes", "_hash_file_stream"}

class CryptoCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.unauthorized_sites = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        prev_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_Call(self, node):
        # Detect hashlib.sha256
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "hashlib" and node.func.attr == "sha256":
                if self.current_function not in ALLOWED_FUNCTIONS:
                    self.unauthorized_sites.append((node.lineno, self.current_function))
        self.generic_visit(node)

def test_ast_crypto_lint():
    print(f"Running Phase 79 AST Crypto Lint on {STRATEGY_ENGINE_PATH}...")
    
    with open(STRATEGY_ENGINE_PATH, "r", encoding="utf-8") as f:
        source_code = f.read()
        
    tree = ast.parse(source_code)
    visitor = CryptoCallVisitor()
    visitor.visit(tree)
    
    if visitor.unauthorized_sites:
        print("FAIL: Found unauthorized hashlib.sha256 calls!")
        for lineno, func_name in visitor.unauthorized_sites:
            func_display = func_name if func_name else "<module level>"
            print(f"Line {lineno}: enclosed in {func_display}")
        sys.exit(1)
    else:
        print("PASS: AST Crypto lint passed. All hashlib.sha256 calls are within authorized functions.")
        sys.exit(0)

if __name__ == "__main__":
    test_ast_crypto_lint()
