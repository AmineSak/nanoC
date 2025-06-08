from lark import Lark, Tree

cpt = 0
# Grammar including arrays, variables, and for-loop
g = Lark(r"""
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/|"0"
INC: "++"
OPBIN: /[+\-*\/<=>]/

liste_var:                            -> vide
    | IDENTIFIER ("," IDENTIFIER)*    -> vars

liste_values: expression ("," expression)* -> liste_values

expression: IDENTIFIER "[" expression "]" -> arr_access
          | IDENTIFIER                   -> var
          | expression OPBIN expression  -> opbin
          | NUMBER                       -> number

commande: commande (";" commande)*                                  -> sequence
        | "for" "(" "int" IDENTIFIER "=" expression ";" expression ";" IDENTIFIER INC ")" "{" commande "}"  -> forloop
        | "while" "(" expression ")" "{" commande "}"              -> while
        | IDENTIFIER "[" expression "]" "=" expression             -> arr_affectation
        | IDENTIFIER "=" expression                               -> affectation
        | "int" "[" expression "]" IDENTIFIER "=" "{" liste_values "}" -> declinit
        | "int" "[" expression "]" IDENTIFIER                      -> decl
        | "int" IDENTIFIER "=" expression                         -> vardeclinit
        | "int" IDENTIFIER                                        -> vardecl
        | "if" "(" expression ")" "{" commande "}" ("else" "{" commande "}")? -> ite
        | "printf" "(" expression ")"                             -> print
        | "skip"                                                  -> skip

program: "main" "(" liste_var ")" "{" commande ";" "return" "(" expression ")" "}"

%import common.WS
%ignore WS
""", start="program")

# Pretty‐printing
def pp_expression(e):
    if e.data in ("var", "number"):
        return e.children[0].value
    if e.data == "arr_access":
        name = e.children[0].value
        idx  = pp_expression(e.children[1])
        return f"{name}[{idx}]"
    left, op, right = e.children
    return f"{pp_expression(left)} {op.value} {pp_expression(right)}"

def pp_commande(c):
    if c.data == "forloop":
        var  = c.children[0].value
        init = pp_expression(c.children[1])
        cond = pp_expression(c.children[2])
        # <- grab the last child, not the ++ token
        body = pp_commande(c.children[-1])
        return f"for (int {var} = {init}; {cond}; {var}++) {{{body}}}"
    if c.data == "decl":
        length = pp_expression(c.children[0])
        name   = c.children[1].value
        return f"int[{length}] {name}"
    if c.data == "declinit":
        length    = pp_expression(c.children[0])
        name      = c.children[1].value
        inits     = c.children[2].children
        vals_txt  = ", ".join(pp_expression(v) for v in inits)
        return f"int[{length}] {name} = {{{vals_txt}}}"
    if c.data == "vardecl":
        name = c.children[0].value
        return f"int {name}"
    if c.data == "vardeclinit":
        name = c.children[0].value
        expr = pp_expression(c.children[1])
        return f"int {name} = {expr}"
    if c.data == "arr_affectation":
        name = c.children[0].value
        idx  = pp_expression(c.children[1])
        expr = pp_expression(c.children[2])
        return f"{name}[{idx}] = {expr}"
    if c.data == "affectation":
        name = c.children[0].value
        expr = pp_expression(c.children[1])
        return f"{name} = {expr}"
    if c.data == "skip":
        return "skip"
    if c.data == "print":
        return f"printf({pp_expression(c.children[0])})"
    if c.data == "while":
        cond = pp_expression(c.children[0])
        body = pp_commande(c.children[1])
        return f"while ({cond}) {{{body}}}"
    if c.data == "ite":
        cond = pp_expression(c.children[0])
        t    = pp_commande(c.children[1])
        f    = pp_commande(c.children[2]) if len(c.children) > 2 else ""
        return f"if ({cond}) {{{t}}}" + (f" else {{{f}}}" if f else "")
    if c.data == "sequence":
        first = pp_commande(c.children[0])
        rest  = pp_commande(c.children[1])
        return f"{first} ; {rest}"
    return ""

# declarations and variables
def find_array_decls(tree):
    names = []
    if isinstance(tree, Tree):
        if tree.data in ("decl", "declinit"):
            names.append(tree.children[1].value)
        for ch in tree.children:
            names += find_array_decls(ch)
    return names

def find_var_decls(tree):
    names = []
    if isinstance(tree, Tree):
        if tree.data in ("vardecl", "vardeclinit"):
            names.append(tree.children[0].value)
        if tree.data == "forloop":
            names.append(tree.children[0].value)
        for ch in tree.children:
            names += find_var_decls(ch)
    return names


# asm generation

# Map basic and relational ops to ASM
op2asm = {
    "+": "add rax, rbx",
    "-": "sub rax, rbx",
    "<": "cmp rax, rbx\nsetl al\nmovzx rax, al",
    ">": "cmp rax, rbx\nsetg al\nmovzx rax, al"
}

def asm_expression(e):
    if e.data == "var":
        return f"mov rax, [{e.children[0].value}]"
    if e.data == "number":
        return f"mov rax, {e.children[0].value}"
    if e.data == "arr_access":
        name = e.children[0].value
        idx  = e.children[1]
        return (
            f"{asm_expression(idx)}\n"
            "mov rcx, rax\n"
            "shl rcx, 3\n"
            f"mov rbx, [{name}]\n"
            "mov rax, [rbx + rcx]"
        )
    left, op, right = e.children
    left_code  = asm_expression(left)
    right_code = asm_expression(right)
    return (
        f"{left_code}\n"
        "push rax\n"
        f"{right_code}\n"
        "mov rbx, rax\n"
        "pop rax\n"
        f"{op2asm[op.value]}"
    )

def asm_commande(c):
    global cpt
    if c.data == "forloop":
        var       = c.children[0].value
        init_expr = c.children[1]
        cond_expr = c.children[2]
        inc_var   = c.children[3].value
        # <- again, the body is the last child
        body      = c.children[-1]

        idx       = cpt; cpt += 1
        code = (
            f"{asm_expression(init_expr)}\n"
            f"mov [{var}], rax\n"
            f"loop{idx}: {asm_expression(cond_expr)}\n"
            "cmp rax, 0\n"
            f"jz end{idx}\n"
            # recurse on the real body Tree
            f"{asm_commande(body)}\n"
            f"mov rax, [{inc_var}]\n"
            "add rax, 1\n"
            f"mov [{inc_var}], rax\n"
            f"jmp loop{idx}\n"
            f"end{idx}: nop"
        )
        return code

    if c.data == "decl":
        length = c.children[0]
        name   = c.children[1].value
        return (
            f"{asm_expression(length)}\n"
            "mov rdi, rax\n"
            "shl rdi, 3\n"
            "call malloc\n"
            f"mov [{name}], rax"
        )
    if c.data == "declinit":
        length = c.children[0]
        name   = c.children[1].value
        vals   = c.children[2].children
        code = (
            f"{asm_expression(length)}\n"
            "mov rdi, rax\n"
            "shl rdi, 3\n"
            "call malloc\n"
            f"mov [{name}], rax\n"
        )
        for i, val in enumerate(vals):
            code += (
                f"{asm_expression(val)}\n"
                f"mov rbx, [{name}]\n"
                f"mov [rbx + {8*i}], rax\n"
            )
        return code

    if c.data == "vardecl":
        return ""  # storage reserved in .data
    if c.data == "vardeclinit":
        name = c.children[0].value
        expr = c.children[1]
        return (
            f"{asm_expression(expr)}\n"
            f"mov [{name}], rax"
        )

    if c.data == "arr_affectation":
        name, idx, val = c.children[0].value, c.children[1], c.children[2]
        return (
            f"{asm_expression(idx)}\n"
            "mov rcx, rax\n"
            "shl rcx, 3\n"
            f"mov rdx, [{name}]\n"
            f"{asm_expression(val)}\n"
            "mov [rdx + rcx], rax"
        )
    if c.data == "affectation":
        var = c.children[0].value
        return f"{asm_expression(c.children[1])}\nmov [{var}], rax"
    if c.data == "skip":
        return "nop"
    if c.data == "print":
        return (
            f"{asm_expression(c.children[0])}\n"
            "mov rsi, rax\n"
            "mov rdi, fmt_int\n"
            "xor rax, rax\n"
            "call printf\n"
        )
    if c.data == "while":
        cond, body = c.children
        idx = cpt; cpt += 1
        return (
            f"loop{idx}: {asm_expression(cond)}\n"
            "cmp rax, 0\n"
            f"jz end{idx}\n"
            f"{asm_commande(body)}\n"
            f"jmp loop{idx}\n"
            f"end{idx}: nop"
        )
    if c.data == "sequence":
        return asm_commande(c.children[0]) + "\n" + asm_commande(c.children[1])
    return ""

def asm_program(p):
    with open("moule.asm") as f:
        template = f.read()
    # return expression
    ret_code = asm_expression(p.children[2])
    template = template.replace("RETOUR", ret_code)

    # init args
    init_vars = ""
    decls = []
    for i, arg in enumerate(p.children[0].children):
        init_vars += (
            "mov rbx, [argv]\n"
            f"mov rdi, [rbx + {(i+1)*8}]\n"
            "call atoi\n"
            f"mov [{arg.value}], rax\n"
        )
        decls.append(arg.value)

    # collect arrays & vars
    arrs = set(find_array_decls(p.children[1]))
    vars = set(find_var_decls(p.children[1]))
    for name in arrs | vars:
        decls.append(name)

    # build .data declarations
    decl_section = "".join(f"{name}: dq 0\n" for name in decls)
    template = template.replace("DECL_VARS", decl_section)
    template = template.replace("INIT_VARS", init_vars)

    # commands
    cmd_code = asm_commande(p.children[1])
    template = template.replace("COMMANDE", cmd_code)
    return template

if __name__ == "__main__":
    with open("simple.c") as f:
        src = f.read()
    ast = g.parse(src)
    # pretty-print
    print(pp_commande(ast.children[1]) + "; return " + pp_expression(ast.children[2]))
    # write ASM
    asm_code = asm_program(ast)
    with open("output.asm", "w") as out:
        out.write(asm_code)
    print("Wrote output.asm")
