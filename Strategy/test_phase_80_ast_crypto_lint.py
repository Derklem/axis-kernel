import ast
import sys

STRATEGY_ENGINE_PATH = r"d:\Infinite\Infinity\Strategy\strategy_engine.py"
ALLOWED_FUNCTIONS = {
    "_hash_obj", "_hash_bytes", "_hash_file_stream",
    "_append_metabolic_receipts", "_recompute_metabolic_receipts_head",
    "_emit_ecosystem_observation", "_emit_ecosystem_mutation_receipt"
}

def add_parent_pointers(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

class CryptoCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.unauthorized_sites = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        prev_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_function

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "hashlib" and alias.asname is not None:
                self.unauthorized_sites.append((node.lineno, f"Aliased import of hashlib: 'import hashlib as {alias.asname}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module == "hashlib":
            self.unauthorized_sites.append((node.lineno, f"Unauthorized from-import: 'from hashlib import ...'"))
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id == "hashlib":
            parent = getattr(node, "parent", None)
            if not (isinstance(parent, ast.Attribute) and parent.attr == "sha256"):
                # Exception for the actual Import node, but Import doesn't use ast.Name for the module name.
                self.unauthorized_sites.append((node.lineno, "Bare reference to 'hashlib' outside of 'hashlib.sha256'"))
        elif node.id == "sha256":
            self.unauthorized_sites.append((node.lineno, "Naked reference to 'sha256'"))
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == "hashlib" and node.attr == "sha256":
            parent = getattr(node, "parent", None)
            if isinstance(parent, ast.Call) and parent.func == node:
                if self.current_function not in ALLOWED_FUNCTIONS:
                    self.unauthorized_sites.append((node.lineno, f"hashlib.sha256 call inside unauthorized function: {self.current_function}"))
            else:
                self.unauthorized_sites.append((node.lineno, "Unauthorized aliasing or assignment of 'hashlib.sha256'"))
        self.generic_visit(node)

def verify_crypto_lint():
    with open(STRATEGY_ENGINE_PATH, "r", encoding="utf-8") as f:
        source_code = f.read()
        
    tree = ast.parse(source_code)
    add_parent_pointers(tree)
    
    visitor = CryptoCallVisitor()
    visitor.visit(tree)
    
    if visitor.unauthorized_sites:
        errors = [f"Line {lineno}: {reason}" for lineno, reason in visitor.unauthorized_sites]
        return False, errors
    return True, []

def test_ast_crypto_lint():
    print(f"Running Phase 81 AST Crypto Lint Preflight on {STRATEGY_ENGINE_PATH}...")
    ok, errors = verify_crypto_lint()
    
    if not ok:
        print("FAIL: Found unauthorized hashlib operations!")
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("PASS: AST Crypto lint passed. Cryptographic domain is strictly isolated.")
        sys.exit(0)

if __name__ == "__main__":
    test_ast_crypto_lint()
# Phase 82 Recovery Test Tamper
# Phase 83 Optimization Test Tamper
# Phase 85 Hardening Test Tamper
