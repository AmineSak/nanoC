from lark import Lark

from typage import type_commande, type_expression

env = {}
cpt = 0
g = Lark(
    """
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/ | "0"
OPBIN: "+" | "-" | "*" | "/" | ">"
TYPE: "int" | "char*"

typed_var: TYPE IDENTIFIER -> typed_var

liste_var:                            -> vide
    | typed_var ("," typed_var)*      -> vars

expression: IDENTIFIER                -> var
    | NUMBER                          -> number
    | expression OPBIN expression     -> opbin

commande: TYPE IDENTIFIER "=" expression ";" -> declaration
    | IDENTIFIER "=" expression ";"         -> affectation
    | "while" "(" expression ")" "{" (commande)* "}" -> while
    | "if" "(" expression ")" "{" (commande)* "}" ("else" "{" (commande)* "}")? -> ite
    | "printf" "(" expression ")" ";"       -> print
    | "skip" ";"                            -> skip
    | commande ";" commande                 -> sequence

program: function* TYPE "main" "(" liste_var ")" "{" (commande)* "return" "(" expression ")" ";" "}"
function:  -> vide
| typed_var "(" liste_var ")" "{" commande "return" "(" expression ")" "}" -> function
%import common.WS
%ignore WS
""",
    start="function",
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
    # print(c)
    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        exp = c.children[2]
        env[var_name] = var_type
        if var_type == "int":
            return f"{asm_expression(exp)}\nmov [{var_name}], rax"
        elif var_type == "char*":
            return f"{asm_expression(exp)}\nmov [{var_name}], rax"
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
    # print(env)
    for i in range(1, len(p.children) - 1):
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
    for i, c in enumerate(p.children[0].children):
        if env[c.children[1].value] == "int":
            init_vars += f"""mov rbx, [argv]
mov rdi, [rbx + {(i+1)*8}]
call atoi
mov [{c.children[1].value}], rax
"""
            decl_vars += f"{c.children[1].value}: dq 0\n"
        elif env[c.children[1].value] == "char*":
            decl_vars += f"{c.children[1].value}: db 0\n"
    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("DECL_VARS", decl_vars)
    for i in range(1, len(p.children) - 1):
        asm_c = asm_commande(p.children[i])
        commande += f"{asm_c}\n"
    prog_asm = prog_asm.replace("COMMANDE", asm_c)
    return prog_asm


def pp_list_typed_vars(l):
    typed_var = l.children[0]
    type = typed_var.children[0].value
    var = typed_var.children[1].value
    L = f"{type} {var}"

    for i in range(1, len(l.children)):
        typed_var = l.children[i]
        type = typed_var.children[0].value
        var = typed_var.children[1].value
        L += f",{type} {var}"
    return L


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
    if c.data == "ite":
        condition = c.children[0]
        then_body = c.children[1]
        if len(c.children) > 2:
            else_body = c.children[2]
            return f"if ({pp_expression(condition)}) {{{pp_commande(then_body)}}} else {{{pp_commande(else_body)}}}"
        return f"if ({pp_expression(condition)}) {{{pp_commande(then_body)}}}"

    

def pp_function(f):
    output_type = f.children[0].children[0].value
    name = f.children[0].children[1].value
    list_typed_vars = pp_list_typed_vars(f.children[1])
    body = pp_commande(f.children[2])
    exp = pp_expression(f.children[3])
    return f"{output_type} {name} ({list_typed_vars}) {{{body} \n return({exp})}} "


if __name__ == "__main__":
    with open("simple.c") as f:
        src = f.read()
    # ast = g.parse("""int hello_1(int X, long Y) { x=y
    #   return(x+y)}""")
    ast = g.parse(
        """int foo(int x, int y) {
    int z = x + y;
    return(z)
}
"""
    )
    print(pp_function(ast))
