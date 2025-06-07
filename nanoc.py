from lark import Lark, Tree, Token
#Working code for char *
cpt = 0
declared_strings = set()
declared_chars=set()

g = Lark("""
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/ | "0"
STRING: /"[^\"]*"/
OPBIN: /[-*\/>=]/  // Exclude '+'

liste_var:                            -> vide
    | IDENTIFIER ("," IDENTIFIER)*    -> vars

expression: string_expr               -> string_expression
          | int_expr                  -> int_expression

string_expr: STRING
           | IDENTIFIER
           | string_expr "+" string_expr -> str_concat

int_expr: NUMBER
        | IDENTIFIER
        | IDENTIFIER "[" expression "]"  ->str_index
        | int_expr OPBIN int_expr        -> opbin
        | "len" "(" string_expr ")"      -> strlen
        | "atoi" "(" string_expr ")"     -> atoi

commande: commande (";" commande)*                                  -> sequence
        | "char" "*" IDENTIFIER "=" STRING                         -> string_decl
        | "char" "*" IDENTIFIER                                    -> string_decl_empty
        | IDENTIFIER "=" expression                                -> affectation
        | IDENTIFIER "[" expression "]" "=" expression             -> arr_affectation
        | "while" "(" expression ")" "{" commande "}"              -> while
        | "if" "(" expression ")" "{" commande "}" ("else" "{" commande "}")? -> ite
        | "printf" "(" expression ")"                              -> print
        | "skip"                                                   -> skip
        | "return" "(" expression ")"                              -> ret

program: "main" "(" liste_var ")" "{" commande "}"

%import common.WS
%ignore WS
""", start="program")

def get_vars_expression(e):
    vars_set = set()
    if isinstance(e, Token):
        if e.type == "IDENTIFIER":
            vars_set.add(e.value)
    elif isinstance(e, Tree):
        for child in e.children:
            vars_set.update(get_vars_expression(child))
    return vars_set

def get_vars_commande(c):
    vars_set = set()
    if hasattr(c, 'data'):
        if c.data == "string_decl":
            declared_strings.add(c.children[0].value)

        elif c.data == "string_decl_empty":
            declared_strings.add(c.children[0].value)

        elif c.data == "affectation":
            var_name = c.children[0].value
            expr     = c.children[1]

            if expr.data == "int_expression":
                child = expr.children[0]
                if isinstance(child, Tree) and child.data == "str_index":
                    declared_chars.add(var_name)

            if expr.data == "string_expression":
                declared_strings.add(var_name)

            vars_set.add(var_name)
            vars_set.update(get_vars_expression(expr))
        elif c.data == "sequence":
            for child in c.children:
                vars_set.update(get_vars_commande(child))
        elif c.data in ("while", "ite"):
            vars_set.update(get_vars_expression(c.children[0]))
            vars_set.update(get_vars_commande(c.children[1]))
            if len(c.children) == 3:
                vars_set.update(get_vars_commande(c.children[2]))
        elif c.data in ("print", "ret"):
            vars_set.update(get_vars_expression(c.children[0]))
    return vars_set

op2asm = {"+": "add rax, rbx", "-": "sub rax, rbx"}

def extract_string_literals(node, acc=None):
    if acc is None:
        acc = set()
    if isinstance(node, Tree):
        # déjà existant :
        if node.data == "string_expr" \
           and isinstance(node.children[0], Token) \
           and node.children[0].type == "STRING":
            acc.add(node.children[0].value)

        # nouveau : attrape le literal dans string_decl
        if node.data == "string_decl":
            token = node.children[1]
            if isinstance(token, Token) and token.type == "STRING":
                acc.add(token.value)

        for child in node.children:
            extract_string_literals(child, acc)
    return acc

def asm_expression(e):
    global cpt

    if isinstance(e, Tree) and e.data in (
       "string_expression",
        "string_expr",        # <-- ajouté !
        "int_expression",
       "int_expr"
    ):
       return asm_expression(e.children[0])

    
    if isinstance(e, Tree) and e.data == "str_concat":
        left  = asm_expression(e.children[0])
        right = asm_expression(e.children[1])
        return f"""{left}
push rax
{right}
mov rsi, rax
pop rdi
call strcat_custom"""

    
    if isinstance(e, Tree) and e.data == "str_index":
        var_tok  = e.children[0]
        idx_tree = e.children[1]

        asm_idx  = asm_expression(idx_tree)
        asm_base = f"mov rbx, [{var_tok.value}]"
        return f"""{asm_idx}
push rax
{asm_base}
pop rax
add rax, rbx
movzx rax, byte [rax]"""

    if isinstance(e, Token):
        if e.type == "STRING":
            label = f"str_{abs(hash(e))%(10**8)}"
            return f"lea rax, [{label}] ; {e.value}"
        if e.type == "IDENTIFIER":
            return f"mov rax, [{e.value}]"
        if e.type == "NUMBER":
            return f"mov rax, {e.value}"
 
    if isinstance(e, Tree) and e.data == "opbin":
        left  = asm_expression(e.children[0])
        right = asm_expression(e.children[2])
        op    = e.children[1].value
        return f"""{left}
push rax
{right}
mov rbx, rax
pop rax
{op2asm[op]}"""

    if isinstance(e, Tree) and e.data in ("strlen", "atoi"):
        inner = asm_expression(e.children[0])
        call  = "strlen" if e.data=="strlen" else "atoi"
        return f"""{inner}
mov rdi, rax
call {call}"""

    


def asm_commande(c):
    global cpt
    if c.data == "string_decl":
        var = c.children[0].value
        label = f"str_{abs(hash(c.children[1])) % (10 ** 8)}"
        return f"lea rax, [{label}] \nmov [{var}], rax"

    if c.data == "string_decl_empty":
        var = c.children[0].value
        return f"""mov rdi, 1 
call malloc
mov byte [rax], 0
mov [{var}], rax"""


    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        return f"{asm_expression(exp)}\nmov [{var.value}], rax"

    if c.data == "arr_affectation":
        var = c.children[0].value
        index = c.children[1]
        exp = c.children[2]
        return f"""{asm_expression(index)}
push rax
{asm_expression(exp)}
pop rbx
mov rcx, rax
mov rax, [{var}]
add rax, rbx
mov [rax], rcx"""

    if c.data == "skip":
        return "nop"

    if c.data == "print":
        exp = c.children[0]
        asm = asm_expression(exp)

        
        raw = exp
        while isinstance(raw, Tree) and raw.data in (
            "string_expression", "string_expr",
            "int_expression",  "int_expr"
        ):
            raw = raw.children[0]

        is_char = False
        if isinstance(raw, Tree) and raw.data == "str_index":
            is_char = True
        elif isinstance(raw, Token) \
             and raw.type == "IDENTIFIER" \
             and raw.value in declared_chars:
            is_char = True

        is_str = False
        if isinstance(raw, Token) and raw.type == "STRING":
            is_str = True
        elif isinstance(raw, Tree) and raw.data == "str_concat":
            is_str = True
        elif isinstance(raw, Token) \
             and raw.type == "IDENTIFIER" \
             and raw.value in declared_strings:
            is_str = True

        if is_char:
            fmt = "fmt_char"
        elif is_str:
            fmt = "fmt_str"
        else:
            fmt = "fmt_int"

        return f"""{asm}
    mov rdi, {fmt}
    mov rsi, rax
    xor rax, rax
    call printf"""

    if c.data == "while":
        idx = cpt
        cpt += 1
        cond = c.children[0]
        body = c.children[1]
        return f"""loop{idx}:
{asm_expression(cond)}
cmp rax, 0
jz end{idx}
{asm_commande(body)}
jmp loop{idx}
end{idx}: nop"""

    if c.data == "ite":
        cond = c.children[0]
        then_block = c.children[1]
        idx = cpt
        cpt += 1
        if len(c.children) == 3:
            else_block = c.children[2]
            return f"""{asm_expression(cond)}
cmp rax, 0
jz else{idx}
{asm_commande(then_block)}
jmp end{idx}
else{idx}:
{asm_commande(else_block)}
end{idx}: nop"""
        else:
            return f"""{asm_expression(cond)}
cmp rax, 0
jz end{idx}
{asm_commande(then_block)}
end{idx}: nop"""

    if c.data == "sequence":
        parts = []
        for child in c.children:
            code = asm_commande(child)
            if code is None:
                raise RuntimeError(f"asm_commande non-géré pour : {child.data}")
            parts.append(code)
        return "\n".join(parts)

    if c.data == "ret":
        return f"{asm_expression(c.children[0])}"
    


def asm_program(p):
    global cpt
    cpt = 0

    declared_strings.clear()
    
    get_vars_commande(p.children[1])

    init_vars = ""
    input_vars = []
    if hasattr(p.children[0], 'children'):
        for i, c in enumerate(p.children[0].children):
            name   = c.value
            offset = (i+1)*8
            input_vars.append(name)

            if name in declared_strings:
                init_vars += f"""\
mov rbx, [argv]
mov rdi, [rbx + {offset}]
mov [{name}], rdi

"""
            else:
                
                init_vars += f"""\
mov rbx, [argv]
mov rdi, [rbx + {offset}]
call atoi
mov [{name}], rax

"""

    
    used_vars = get_vars_commande(p.children[1])
    used_vars.update(input_vars)
    used_vars = sorted(used_vars)

    decl_vars = ""
    for var in used_vars:
        decl_vars += f"{var}: dq 0\n"

    
    string_literals = extract_string_literals(p)
    string_section = ""
    for s in string_literals:
        label   = f"str_{abs(hash(s)) % (10**8)}"
        escaped = s[1:-1].replace('\\', '\\\\').replace('"', '\\"')
        string_section += f'{label}: db "{escaped}", 0\n'

    with open("moule.asm") as f:
        prog_asm = f.read()

    prog_asm = prog_asm.replace("INIT_VARS",   init_vars)
    prog_asm = prog_asm.replace("DECL_VARS",   decl_vars + string_section)
    prog_asm = prog_asm.replace("COMMANDE",     asm_commande(p.children[1]))
    prog_asm = prog_asm.replace("RETOUR",       "nop")

    return prog_asm


# === Pretty-printer ===

def pp_expression(e):
    if isinstance(e, Tree) and e.data == "string_expression":
        return pp_expression(e.children[0])
    if isinstance(e, Tree) and e.data == "int_expression":
        return pp_expression(e.children[0])
    if isinstance(e, Tree) and e.data == "var":
        return e.children[0].value
    if isinstance(e, Tree) and e.data == "number":
        return e.children[0].value
    if isinstance(e, Tree) and e.data == "string_expr":
        return e.children[0].value
    if isinstance(e, Tree) and e.data == "str_concat":
        return f"{pp_expression(e.children[0])} + {pp_expression(e.children[1])}"
    if isinstance(e, Tree) and e.data == "str_index":
        return f"{e.children[0].value}[{pp_expression(e.children[1])}]"
    if isinstance(e, Tree) and e.data == "opbin":
        return f"{pp_expression(e.children[0])} {e.children[1].value} {pp_expression(e.children[2])}"
    if isinstance(e, Tree) and e.data == "strlen":
        return f"len({pp_expression(e.children[0])})"
    if isinstance(e, Tree) and e.data == "atoi":
        return f"atoi({pp_expression(e.children[0])})"
    return "<?>"

def pp_commande(c):
    if c.data == "sequence":
        return "; ".join(pp_commande(ch) for ch in c.children)
    if c.data == "string_decl":
        return f"char *{c.children[0].value} = {c.children[1].value}"
    if c.data == "string_decl_empty":
        return f"char *{c.children[0].value}"
    if c.data == "affectation":
        return f"{c.children[0].value} = {pp_expression(c.children[1])}"
    if c.data == "arr_affectation":
        return f"{c.children[0].value}[{pp_expression(c.children[1])}] = {pp_expression(c.children[2])}"
    if c.data == "print":
        return f"printf({pp_expression(c.children[0])})"
    if c.data == "while":
        return f"while({pp_expression(c.children[0])}) {{ {pp_commande(c.children[1])} }}"
    if c.data == "ret":
        return f"return({pp_expression(c.children[0])})"
    if c.data == "ite":
        cond = pp_expression(c.children[0])
        then = pp_commande(c.children[1])
        if len(c.children) == 3:
            els = pp_commande(c.children[2])
            return f"if({cond}) {{ {then} }} else {{ {els} }}"
        return f"if({cond}) {{ {then} }}"
    if c.data == "skip":
        return "skip"
    return "<?>"

def pp_program(p):
    args = []
    if isinstance(p.children[0], Tree):
        args = [c.value for c in p.children[0].children]
    header = f"main({', '.join(args)})"
    body = pp_commande(p.children[1])
    return f"{header} {{ {body} }}"

# === Entrée principale ===

if __name__ == "__main__":
    with open("simple.c") as f:
        src = f.read()
    ast = g.parse(src)
    #print(pp_program(ast))
    print(asm_program(ast))
