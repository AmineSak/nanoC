from lark import Lark, Tree
from typage import type_expression, type_commande

env = {}
cpt = 0
g = Lark(
    """
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/ | "0"
OPBIN: "+" | "-" | "*" | "/" | ">"
TYPE: "int" | "char*" | "void" | "int[]" | "char*[]"

typed_var: TYPE IDENTIFIER -> typed_var

liste_var:                            -> vide
    | typed_var ("," typed_var)*      -> vars

liste_values: expression ("," expression)* -> liste_values

expression: IDENTIFIER                -> var
    | IDENTIFIER "[" expression "]"   -> array_access
    | NUMBER                          -> number
    | expression OPBIN expression     -> opbin

commande: TYPE IDENTIFIER ("=" expression)* ";" -> declaration
    | TYPE "[" expression "]" IDENTIFIER "=" "{" liste_values "}"";" -> array_declaration
    | TYPE "[" expression "]" IDENTIFIER ";" -> array_decl
    | IDENTIFIER "=" expression ";"         -> affectation
    | IDENTIFIER "[" expression "]" "=" expression      -> array_affectation
    | "while" "(" expression ")" "{" (commande)* "}" -> while
    | "if" "(" expression ")" "{" (commande)* "}" ("else" "{" (commande)* "}")? -> ite
    | "printf" "(" expression ")" ";"       -> print
    | "skip" ";"                            -> skip
    | commande ";" commande                 -> sequence

program: TYPE "main" "(" (liste_var)* ")" "{" (commande)* "return" "(" expression ")" ";" "}"
%import common.WS
%ignore WS
""",
    start="program",
)

"""valeur expression:
return f""{asm_expression(nbr)}
mov rbx, {size}
mul rbx
""
"""


def get_vars_expression(e):
    pass


def get_vars_commande(c):
    pass


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
    if e.data == "array_access":
        name = e.children[0].value
        idx  = e.children[1]
        return (
            f"{asm_expression(idx)}\n"
            "mov rcx, rax\n"
            "shl rcx, 3\n"
            f"mov rbx, [{name}]\n"
            "mov rax, [rbx + rcx]"
        )
    if e.data == "opbin":
        e_left = e.children[0]
        e_op = e.children[1]
        e_right = e.children[2]
        asm_left = asm_expression(e_left)
        asm_right = asm_expression(e_right)
        return f"""{asm_left} 
push rax
{asm_right}
mov rbx, rax
pop rax
{op2asm[e_op.value]}"""


def eval_expression(e, env):
    return None
    

def asm_commande(c):
    global cpt
    if c.data == "declaration":
        if len(c.children) == 3:    
            var_type = c.children[0].value
            var_name = c.children[1].value
            exp = c.children[2]
            env[var_name] = var_type
            if var_type == "int":
                return f"{asm_expression(exp)}\nmov [{var_name}], rax"
            elif var_type == "char*":
                return f"{asm_expression(exp)}\nmov [{var_name}], rax"
        elif len(c.children) == 2:
            var_type = c.children[0].value
            var_name = c.children[1].value
            env[var_name] = var_type
    if c.data == "array_declaration":
        var_type = c.children[0].value
        nbr = c.children[1]
        if not isinstance(nbr.children[0], int):
            raise TypeError("Le nombre d'éléments du tableau doit être un entier.")
        if var_type == "int":
            size = 32
        elif var_type == "char*":
            size = 8
        var_name = c.children[2].value
        env[var_name] = f"{var_type}[]"
        type_commande(c, env)
        return (
            f"{asm_expression(nbr)}\n"
            "mov rdi, rax\n"
            "shl rdi, 3\n"
            "call malloc\n"
            f"mov [{var_name}], rax"
        )
    if c.data == "array_decl":
        var_type = c.children[0].value
        nbr = c.children[1]
        if not isinstance(nbr.value, int):
            raise TypeError("Le nombre d'éléments du tableau doit être un entier.")
        if var_type == "int":
            size = 32
        elif var_type == "char*":
            size = 8
        var_name = c.children[2].value
        env[var_name] = f"{var_type}[]"
        print(env)
        type_commande(c, env)
        vals   = c.children[3].children
        code = (
            f"{asm_expression(nbr)}\n"
            "mov rdi, rax\n"
            "shl rdi, 3\n"
            "call malloc\n"
            f"mov [{var_name}], rax\n"
        )
        for i, val in enumerate(vals):
            code += (
                f"{asm_expression(val)}\n"
                f"mov rbx, [{var_name}]\n"
                f"mov [rbx + {size*i}], rax\n"
            )
        return code
    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        if var.value not in env:
            raise TypeError(f"Variable '{var.value}' non déclarée.")
        return f"{asm_expression(exp)}\nmov [{var.value}], rax"
    if c.data == "array_affectation":
        name, idx, val = c.children[0].value, c.children[1], c.children[2]
        return (
            f"{asm_expression(idx)}\n"
            "mov rcx, rax\n"
            "shl rcx, 3\n"
            f"mov rdx, [{name}]\n"
            f"{asm_expression(val)}\n"
            "mov [rdx + rcx], rax"
        )
    if c.data == "skip":
        return "nop"
    if c.data == "print":
        exp_type = type_expression(c.children[0], {})
        if exp_type == "int":
            return f"""{asm_expression(c.children[0])}
mov rsi, fmt
mov rdi, rax
xor rax, rax
call printf
"""
        elif exp_type == "char*":
            return f"""{asm_expression(c.children[0])}
mov rsi, rax
mov rdi, fmt_str
xor rax, rax
call printf
"""
    if c.data == "while":
        exp = c.children[0]
        body = c.children[1]
        idx = cpt
        cpt += 1
        return f"""loop{idx}:{asm_expression(exp)}
cmp rax, 0
jz end{idx}
{asm_commande(body)}
jmp loop{idx}
end{idx}: nop
"""
    if c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        return f"{asm_commande(d)}\n {asm_commande(tail)}"


def asm_program(p):
    return_type = p.children[0].value
    for c in p.children[1].children:
        env[c.children[1].value] = c.children[0].value
    ret_type = type_expression(p.children[-1], env)
    if ret_type != "int":
        raise TypeError("Le type de retour de la fonction main doit être un entier.")
    with open("moule.asm") as f:
        prog_asm = f.read()
    ret = asm_expression(p.children[-1])
    prog_asm = prog_asm.replace("RETOUR", ret)
    init_vars = ""
    decl_vars = ""
    commande = ""
    for i in range(2,len(p.children) - 1):
        asm_c = asm_commande(p.children[i])
        commande += f"{asm_c}\n"
    for i in range(2,len(p.children)-1):
        type_commande(p.children[i], env)
    for i, c in enumerate(env.keys()):
        if env[c] == "int":
            init_vars += f"""mov rbx, [argv]
mov rdi, [rbx + {(i+1)*8}]
call atoi
mov [{c}], rax
"""
            decl_vars += f"{c}: dq 0\n"
        elif env[c] == "char*":
            decl_vars += f"{c}: db 0\n"
        elif env[c] in ("int[]", "char*[]"):
            decl_vars += f"{c}: dq 0\n"
    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("DECL_VARS", decl_vars)
    prog_asm = prog_asm.replace("COMMANDE", commande)
    return prog_asm

def pp_expression(e):
    if e.data in ("var", "number"):
        return f"{e.children[0].value}"
    e_left = e.children[0]
    e_op = e.children[1]
    e_right = e.children[2]
    return f"{pp_expression(e_left)} {e_op.value} {pp_expression(e_right)}"


def pp_commande(c):
    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        exp = c.children[2]
        return f"{var_type} {var_name} = {pp_expression(exp)}"
    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        return f"{var.value} = {pp_expression(exp)}"
    if c.data == "skip":
        return "skip"
    if c.data == "print":
        return f"printf({pp_expression(c.children[0])})"
    if c.data == "while":
        exp = c.children[0]
        body = c.children[1]
        return f"while ( {pp_expression(exp)} ) {{{pp_commande(body)}}}"
    if c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        return f"{pp_commande(d)} ; {pp_commande(tail)}"


if __name__ == "__main__":
    with open("simple.c") as f:
        src = f.read()
    ast = g.parse(src)
    #print(ast)
    # print(pp_commande(ast))
    print(asm_program(ast))
    # print(pp_commande(ast))
# print(ast.children)
# print(ast.children[0].type)
# print(ast.children[0].value)
