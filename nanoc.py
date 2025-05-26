from lark import Lark
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

expression: IDENTIFIER                -> var
    | NUMBER                          -> number
    | expression OPBIN expression     -> opbin

commande: TYPE IDENTIFIER "=" expression ";" -> declaration
    | TYPE "[" expression "]" IDENTIFIER "=" "{" NUMBER ("," NUMBER)* "}"";" -> array_declaration
    | IDENTIFIER "=" expression ";"         -> affectation
    | "while" "(" expression ")" "{" (commande)* "}" -> while
    | "if" "(" expression ")" "{" (commande)* "}" ("else" "{" (commande)* "}")? -> ite
    | "printf" "(" expression ")" ";"       -> print
    | "skip" ";"                            -> skip
    | commande ";" commande                 -> sequence

program: "main" "(" (liste_var)* ")" "{" (commande)* "return" "(" expression ")" ";" "}"
%import common.WS
%ignore WS
""",
    start="program",
)


def get_vars_expression(e):
    pass


def get_vars_commande(c):
    pass


op2asm = {"+": "add rax, rbx", "-": "sub rax, rbx"}


def asm_expression(e):
    if e.data == "var":
        return f"mov rax, [{e.children[0].value}]"
    if e.data == "number":
        return f"mov rax, {e.children[0].value}"
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

    
def asm_commande(c):
    global cpt
    #print(c)
    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        exp = c.children[2]
        env[var_name] = var_type
        if var_type == "int":
            return f"{asm_expression(exp)}\nmov [{var_name}], rax"
        elif var_type == "char*":
            return f"{asm_expression(exp)}\nmov [{var_name}], rax"
    if c.data == "array_declaration":
        var_type = c.children[0].value
        nbr = c.children[1]
        if var_type == "int":
            size = 32
        elif var_type == "char*":
            size = 8
        #taille = nbr*size
        var_name = c.children[2].value
        env[var_name] = f"{var_type}[]"
        """
        suite"""
    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        if var.value not in env:
            raise TypeError(f"Variable '{var.value}' non déclarée.")
        return f"{asm_expression(exp)}\nmov [{var.value}], rax"
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
    for c in p.children[0].children:
        env[c.children[1].value] = c.children[0].value
    for i in range(1,len(p.children)-1):
        type_commande(p.children[i], env)
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
    for i in range(1,len(p.children) - 1):
        asm_c = asm_commande(p.children[i])
        commande += f"{asm_c}\n"
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
    # print(pp_commande(ast))
    print(asm_program(ast))
    # print(pp_commande(ast))
# print(ast.children)
# print(ast.children[0].type)
# print(ast.children[0].value)
