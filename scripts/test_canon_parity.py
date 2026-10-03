"""
The contract and the dry-run tool each carry their own copy of the
canonicalisation rules, because an Intelligent Contract is a single file and
cannot import a shared module. Duplication is fine; silent drift is not. If
these two ever disagree, the dry run starts approving clues the chain will
reject, which is worse than having no dry run at all.
"""
import ast, re, sys

def bodies(path, names):
    tree = ast.parse(open(path).read())
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]   # drop the docstring
            out[node.name] = ast.dump(ast.Module(body=body, type_ignores=[]))
    return out

def consts(path, names):
    out = {}
    for line in open(path).read().splitlines():
        for n in names:
            if line.startswith(f"{n} = ") or line.startswith(f"{n}="):
                out[n] = re.sub(r"\s*#.*$", "", line).strip()
    return out

FNS = {"canonicalise", "cut_window", "normalise_answer"}
CONSTS = {"_WS", "_KEEP", "MAX_PAGE_CHARS", "MIN_WINDOW_CHARS"}

a = bodies("contracts/proof_of_hunt.py", FNS)
b = bodies("scripts/dryrun_clues.py", FNS)
ca = consts("contracts/proof_of_hunt.py", CONSTS)
cb = consts("scripts/dryrun_clues.py", CONSTS)

fails = []
for n in sorted(FNS):
    if n not in a or n not in b:
        fails.append(f"{n} missing from one side")
    elif a[n] != b[n]:
        fails.append(f"{n} body differs")
    else:
        print(f"  ok   {n} is identical on both sides")
for n in sorted(CONSTS):
    if ca.get(n) != cb.get(n):
        fails.append(f"{n} differs: {ca.get(n)!r} vs {cb.get(n)!r}")
    else:
        print(f"  ok   {n} is identical on both sides")

if fails:
    print("\ncanonicalisation has drifted:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("\ncanonicalisation parity holds")
