from lark import Lark


# enbf
g = Lark("""
IDENTIFIER: /[A-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/ | "0"
OPBIN : /[+\-*\/>]/
WHILE : "while"
IF : "if"
ELSE : "else"
PRINT: "printf"
liste_var:                                           -> vide
         | IDENTIFIER ("," IDENTIFIER)*              -> vars
expression: IDENTIFIER                               -> var
         | expression OPBIN expression               -> opbin
         | NUMBER                                    -> number
commande:  commande (";" commande)*                  -> sequence
         | "while" "(" expression ")" "{" commande "}"    -> while
         | IDENTIFIER "=" expression                 -> affectation
         | IF "(" expression ")" "{" commande "}" (ELSE "{"commande"}")?      -> ite
         | PRINT "(" expression ")"                  -> print
         | "skip"                                    -> skip
programme: "main" "(" liste_var ")" "{" commande "return" "(" expression ")" "}"
         

         %import common.WS
         %ignore WS
""", start = 'commande')


def pp_expression(e):
    if e.data in ("var", "number"):
        return f"{e.children[0].value}"
    if e.data == "opbin":
        e_left = e.children[0]
        e_op = e.children[1].value
        e_right = e.children[2]
        return f"{pp_expression(e_left)} {e_op} {pp_expression(e_right)}"
    return "--"

def pp_commande(c):
    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        return f"{var.value} = {pp_expression(exp)}"
    elif c.data == "printf":
        return f"printf({pp_expression(c.children[0])})"
    elif c.data == "skip" : return "skip"
    elif c.data == "while":
        exp = c.children[0]
        body = c.children[1]
        return f"while ( {pp_expression(exp)} ) {{ {pp_commande(body)} }}"
    elif c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        return f"{pp_commande(d)} ; {pp_commande(tail)}"
    return "--"

if __name__ == "__main__":
    with open("simple.c", "r") as f:
        src = f.read()

    ast = g.parse("y = x + 3")
    print(ast.pretty())

    print(pp_commande(ast))
    #print(ast.data)
    #print(ast.children)
    #print(ast.children[0].type)
    #print(ast.children[0].value)