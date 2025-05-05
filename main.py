from lark import Lark

g = Lark(
    """
        IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
        OPBIN: /[+\-*\/]/
        NUMBER: /[0-9][0-9]*/
        
    list_identifier: -> vide
        | IDENTIFIER ("," IDENTIFIER)* -> vars
    expression: IDENTIFIER -> var
        | expression OPBIN expression -> opbin
        | NUMBER -> number
    commande: -> vide
        | commande ";" commande -> sequence
        | "while" "(" expression ")" "{" commande "}" -> while
        | IDENTIFIER "=" expression                 -> affectation
        | "if" "(" expression ")" "{" commande "}" ("else" "{" commande "}")? -> ifelse 
        | "printf" "(" expression ")" -> print
        | "skip"    -> skip
    program: "main" "(" list_identifier ")" "{" commande "return" "(" expression ")" "}"

    %import common.WS
    %ignore WS
    """,
    start="program",
)

global id
id = 0


def pp_list_identifier(l):
    L = f"{l.children[0].value}"
    for i in range(1, len(l.children)):
        L += f" ,{l.children[i].value}"
    return L


def pp_expression(e):
    if e.data in ("var", "number"):
        return f"{e.children[0].value}"
    if e.data == "opbin":
        left_e = e.children[0]
        right_e = e.children[2]
        return f"{pp_expression(left_e)} {e.children[1].value} {pp_expression(right_e)}"


def asm_exp(e):
    if e.data == "number":
        return f"mov rax,{e.children[0].value}"
    if e.data == "var":
        return f"mov rax,[{e.children[0].value}]"
    if e.data == "opbin":
        left_e = e.children[0]
        op = e.children[1]
        right_e = e.children[2]
        op2asm = {"+": "add rax,rbx", "-": "sub rbx,rax"}
        return f"""{asm_exp(left_e)}
push rax
{asm_exp(right_e)}
mov rbx,rax
{op2asm[op]}"""


def asm_commande(c):
    global id
    if c.data == "skip":
        return "nop\n"
    if c.data == "while":
        id += 1
        e = c.children[0]
        body = c.children[1]
        while_id = id
        return f"""at{while_id}:{asm_exp(e)}
cmp rax,0
jz end{while_id}
{asm_commande(body)}
jmp at{while_id}
end{while_id}: nop"""
    if c.data == "sequence":
        c1 = c.children[0]
        c2 = c.children[1]
        return f"{asm_commande(c1)} \n {asm_commande(c2)}"
    if c.data == "print":
        return f"""{asm_exp(c.children[0])}
mov rdi,fmt_int
mov rsi,rax
xor rax,rax
call printf"""
    if c.data == "affectation":
        l = c.children[0]
        expression = c.children[1]
        return f"""{asm_exp(expression)}
mov [{l.value}],rax"""


def pp_commande(c):
    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        return f"{var.value} = {pp_expression(exp)}"
    if c.data == "print":
        return f"printf({pp_expression(c.children[0])})"
    if c.data == "skip":
        return "skip"
    if c.data == "while":
        e = c.children[0]
        body = c.children[1]
        return f"while({pp_expression(e)}) {{\n{pp_commande(body)}}} \n"
    if c.data == "sequence":
        c1 = c.children[0]
        c2 = c.children[1]
        return f"{pp_commande(c1) } ; {pp_commande(c2)}"


def pp_program(c):
    return f"main ({pp_list_identifier(c.children[0])}) {{\n{pp_commande(c.children[1])} return({pp_expression(c.children[2])})}}"


def asm_program(p):
    with open("moule.asm") as f:
        prog_asm = f.read()
    exp = p.children[2]
    commande = p.children[1]
    prog_asm = prog_asm.replace("RETOUR", asm_exp(exp))
    prog_asm = prog_asm.replace("COMMANDE", asm_commande(commande))
    init_vars = ""
    decl_vars = ""
    for i, c in enumerate(p.children[0].children):
        t = f"""mov rbx,[argv]
mov rdi, [rbx + {(i+1)*8}]
call atoi
mov [{c.value}], rax"""
        init_vars += t
        decl_vars += f"{c.value}: dq 0 \n"
    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("DECL_VARS", decl_vars)
    return prog_asm


if __name__ == "__main__":
    with open("simple.c") as f:
        src = f.read()
    ast = g.parse(src)
    print(asm_program(ast))
