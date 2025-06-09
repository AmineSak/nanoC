from lark import Lark,Tree,Token
from typage import type_expression, type_commande

# Global state for the compiler
env = {}  # Symbol table for global variables and functions
cpt = 0  # Counter for generating unique labels
declared_strings = set()
declared_chars=set()

g = Lark(
    """
    IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
    NUMBER: /[1-9][0-9]*/ | "0"
    OPBIN: "+" | "-" | "*" | "/" | "==" | "!=" | ">" | "<" | ">=" | "<="
    TYPE: "int" | "char*" | "int[]" | "char*[]"
    STRING: /"[^\"]*"/

    var_decl: TYPE "[" NUMBER? "]" IDENTIFIER -> array_decl_type
            | TYPE IDENTIFIER                  -> simple_decl_type

    liste_var:                          -> vide
        | var_decl ("," var_decl)*      -> vars

    liste_values: expression ("," expression)* -> liste_values

    expression: IDENTIFIER "[" expression "]" -> arr_access
        | IDENTIFIER                -> var
        | NUMBER                          -> number
        | expression OPBIN expression     -> opbin
        | IDENTIFIER "(" (expression ("," expression)*)? ")" -> function_call
        | string_expr               -> string_expression
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

    commande: "for" "(" TYPE IDENTIFIER "=" expression ";" expression ";" IDENTIFIER "++" ")" "{" block "}" -> forloop
        | TYPE "[" expression "]" IDENTIFIER "=" "{" liste_values "}" ";" -> array_declaration_init
        | TYPE "[" expression "]" IDENTIFIER ";"                         -> array_declaration
        | TYPE IDENTIFIER "=" expression ";"                             -> declaration
        | "char" "*" IDENTIFIER "=" STRING                               -> string_decl
        | "char" "*" IDENTIFIER                                          -> string_decl_empty
        | IDENTIFIER "[" expression "]" "=" expression ";"               -> arr_affectation
        | IDENTIFIER "=" expression ";"                                  -> affectation
        | "while" "(" expression ")" "{" block "}"                       -> while
        | "if" "(" expression ")" "{" block "}" ("else" "{" block "}")?   -> ite
        | "printf" "(" expression ")" ";"                                -> print
        | "return" "(" expression ")" ";"                                -> return_statement
        | "skip" ";"                                                     -> skip
        | commande ";" commande                                          -> sequence

    block: (commande)* -> block
    program: (function)* main -> program
    main: TYPE "main" "(" liste_var ")" "{" block "}" -> main
    function: var_decl "(" liste_var ")" "{" block "}" -> function

    %import common.WS
    %ignore WS
    """,
    start="program",
)

op2asm = {
    "+": "add rax, rbx",
    "-": "sub rax, rbx",
    "*": "imul rax, rbx",
    "/": "cqo\nidiv rbx",
    ">": "cmp rax, rbx\nsetg al\nmovzx rax, al",
    "<": "cmp rax, rbx\nsetl al\nmovzx rax, al",
    ">=": "cmp rax, rbx\nsetge al\nmovzx rax, al",
    "<=": "cmp rax, rbx\nsetle al\nmovzx rax, al",
    "==": "cmp rax, rbx\nsete al\nmovzx rax, al",
    "!=": "cmp rax, rbx\nsetne al\nmovzx rax, al",
}


from lark import Tree, Token

def asm_expression(e, local_vars):
    """Compiles an expression. local_vars is the map of local names to [rbp-offset]."""
    global cpt

    if isinstance(e, Token):
        if e.type == "NUMBER":
            return f"mov rax, {e.value}"
        elif e.type == "STRING":
            label = f"str_{abs(hash(e)) % (10**8)}"
            return f"lea rax, [{label}] ; {e.value}"
        elif e.type == "IDENTIFIER":
            return f"mov rax, [{e.value}]"
        else:
            raise NotImplementedError(f"Unsupported token type: {e.type!r}")

    if e.data == "number":
        return f"mov rax, {e.children[0].value}"

    
    if e.data == "var":
        var_name = e.children[0].value
        if var_name in local_vars:
            offset = local_vars[var_name]["off"]
            return f"mov rax, [rbp{offset}]"
        elif var_name in env:
            return f"mov rax, [{var_name}]"
        else:
            raise NameError(f"Variable '{var_name}' not defined.")

    
    if e.data == "arr_access":
        name = e.children[0].value
        idx_expr = e.children[1]
        if name in local_vars:
            base_addr = f"[rbp{local_vars[name]['off']}]"
        elif name in env:
            base_addr = f"[{name}]"
        else:
            raise NameError(f"Array '{name}' not defined.")
        return f"""
    {asm_expression(idx_expr, local_vars)}
    mov rbx, rax
    mov rax, {base_addr}
    mov rax, [rax + rbx * 8]
"""

    if e.data == "opbin":
        left, op_tok, right = e.children
        left_asm  = asm_expression(left,  local_vars)
        right_asm = asm_expression(right, local_vars)
        asm_op    = op2asm[op_tok.value]
        return f"""
    {right_asm}
    push rax
    {left_asm}
    pop rbx
    {asm_op}
"""

    if e.data == "function_call":
        func_name = e.children[0].value
        args      = e.children[1:]
        arg_regs  = ["rdi","rsi","rdx","rcx","r8","r9"]
        if len(args) > len(arg_regs):
            raise NotImplementedError("Only up to 6 args supported.")
        asm = ""

        for arg in args:
            asm += asm_expression(arg, local_vars) + "\npush rax\n"
       
        for i in range(len(args)):
            asm += f"pop {arg_regs[i]}\n"
        if func_name == "printf":
            asm += "xor rax, rax\n"
        asm += f"call {func_name}\n"
        return asm

    if e.data == "str_concat":
        left, right = e.children
        left_asm     = asm_expression(left,  local_vars)
        right_asm    = asm_expression(right, local_vars)
        return f"""{left_asm}
push rax
{right_asm}
mov rsi, rax
pop rdi
call strcat_custom"""


    if e.data == "str_index":
        var_tok, idx = e.children
        idx_asm      = asm_expression(idx, local_vars)
        base_asm     = f"mov rbx, [{var_tok.value}]"
        return f"""{idx_asm}
push rax
{base_asm}
pop rax
add rax, rbx
movzx rax, byte [rax]"""

    if e.data in ("strlen","atoi"):
        inner = asm_expression(e.children[0], local_vars)
        call  = "strlen" if e.data=="strlen" else "atoi"
        return f"""{inner}
mov rdi, rax
call {call}"""

    #
    raise NotImplementedError(f"Unhandled expression node: {e!r}")


def asm_commande(c, local_vars, func_name):
    """Compiles a command. Needs local_vars for context and func_name for returns."""
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

    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        if var_type != type_expression(c.children[2], env):
            raise TypeError(
                f"Incompatibilité de type pour la déclaration de '{var_name}'."
            )
        offset = -(8 * (1 + len(local_vars)))
        local_vars[var_name] = {'off': offset, 'type': var_type}
        env[var_name] = {"type": var_type}
        exp_asm = asm_expression(c.children[2], local_vars)
        return f"""
    {exp_asm}
    mov [rbp{offset}], rax  ; local var {var_name}
"""
    if c.data == "array_declaration":
        var_type = c.children[0].value
        arr_name = c.children[2].value
        size_expr = c.children[1]

        if not isinstance(size_expr.children[0], int):
            raise TypeError("Le nombre d'éléments du tableau doit être un entier.")

        if var_type == "int":
            size = 32
        elif var_type == "char*":
            size = 8
            
        # Create a local variable for the *pointer* to the array
        offset = -(8 * (1 + len(local_vars)))
        local_vars[arr_name] = {'off': offset, 'type': var_type}
        env[arr_name] = {"type": f"{var_type}[]", 'size': size_expr}
        type_commande(c, env)

        return f"""
    ; Allocate memory for array '{arr_name}'
    {asm_expression(size_expr, local_vars)}
    mov rdi, rax             ; Number of elements
    mov rax, {size}          ; Size of each element (int or pointer)
    imul rdi, rax            ; Total bytes
    call malloc
    mov [rbp{offset}], rax    ; Store pointer in local variable '{arr_name}'
"""
    if c.data == "array_declaration_init":
        arr_name = c.children[2].value
        size_expr = c.children[1]
        var_type = c.children[0].value
        offset = -(8 * (1 + len(local_vars)))
        local_vars[arr_name] = {'off': offset, 'type': var_type}
        env[arr_name] = {"type": f"{var_type}[]", 'size': size_expr}
        type_commande(c, env)

        if var_type == "int":
            size = 8
        elif var_type == "char*":
            size = 8

        code = f"""
    ; Allocate memory for array '{arr_name}'
    {asm_expression(size_expr, local_vars)}
    mov rdi, rax
    mov rax, {size}
    imul rdi, rax
    call malloc
    mov [rbp{offset}], rax
"""
        liste_values_node = c.children[3]
        for i, val_expr in enumerate(liste_values_node.children):
            code += f"""
    ; Initialize {arr_name}[{i}]
    {asm_expression(val_expr, local_vars)}
    mov rbx, [rbp{offset}]
    mov [rbx + {i*size}], rax
"""
        return code

    if c.data == "affectation":
        var_name = c.children[0].value
        exp_asm = asm_expression(c.children[1], local_vars)
        if var_name in local_vars:
            offset = local_vars[var_name]["off"]
            return f"{exp_asm}\nmov [rbp{offset}], rax"
        elif var_name in env:
            return f"{exp_asm}\nmov [{var_name}], rax"
        else:
            raise NameError(f"Variable '{var_name}' not defined.")

    if c.data == "arr_affectation":
        arr_name = c.children[0].value
        idx_expr = c.children[1]
        val_expr = c.children[2]
        if arr_name not in local_vars and arr_name not in env:
            raise NameError(f"Array '{arr_name}' not defined.")

        base_addr_location = (
            f"[rbp{local_vars[arr_name]["off"]}]"
            if arr_name in local_vars
            else f"[{arr_name}]"
        )

        return f"""
    {asm_expression(val_expr, local_vars)}
    push rax
    {asm_expression(idx_expr, local_vars)}
    mov rbx, rax
    pop rax
    mov rcx, {base_addr_location}
    mov [rcx + rbx * 8], rax
"""

    if c.data == "return_statement":
        exp_asm = asm_expression(c.children[0], local_vars)
        if env[func_name]["return_type"] != type_expression(c.children[0], local_vars):
            raise TypeError(
                f"Type de retour incorrect pour '{func_name}': attendu {env[func_name]['return_type']}, obtenu {type_expression(c.children[0], local_vars)}."
            )
        return f"""
    {exp_asm}
    jmp {func_name}_epilogue
"""
    if c.data == "forloop":
        loop_var = c.children[1].value
        init_expr = c.children[2]
        cond_expr = c.children[3]
        body_block = c.children[5]
        offset = -(8 * (1 + len(local_vars)))
        local_vars[loop_var] = {'off': offset, 'type': 'int'}
        body_asm = ""
        for cmd in body_block.children:
            body_asm += asm_commande(cmd, local_vars, func_name)
        idx = cpt
        cpt += 1
        return f"""
    ; For loop init
    {asm_expression(init_expr, local_vars)}
    mov [rbp{offset}], rax
for_loop_{idx}:
    ; For loop condition
    {asm_expression(cond_expr, local_vars)}
    cmp rax, 0
    jz for_end_{idx}
    ; For loop body
    {body_asm}
    ; For loop increment
    inc qword [rbp{offset}]
    jmp for_loop_{idx}
for_end_{idx}:
    nop
"""
    if c.data == "while":
        exp = c.children[0]
        block = c.children[1]
        body_asm = "".join(
            [asm_commande(cmd, local_vars, func_name) for cmd in block.children]
        )
        idx = cpt
        cpt += 1
        return f"""
loop{idx}:
    {asm_expression(exp, local_vars)}
    cmp rax, 0
    jz end{idx}
    {body_asm}
    jmp loop{idx}
end{idx}: nop
"""
    if c.data == "ite":
        cond_asm = asm_expression(c.children[0], local_vars)
        then_block = c.children[1]
        then_asm = "".join(
            [asm_commande(cmd, local_vars, func_name) for cmd in then_block.children]
        )
        idx = cpt
        cpt += 1
        if len(c.children) > 2:
            else_block = c.children[2]
            else_asm = "".join(
                [
                    asm_commande(cmd, local_vars, func_name)
                    for cmd in else_block.children
                ]
            )
            return f"""
    {cond_asm}
    cmp rax, 0
    jz else{idx}
{then_asm}
    jmp endif{idx}
else{idx}:
{else_asm}
endif{idx}: nop
"""
        else:
            return f"""
    {cond_asm}
    cmp rax, 0
    jz endif{idx}
{then_asm}
endif{idx}: nop
"""
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
    if c.data == "skip":
        return "nop"
    if c.data == "sequence":
        return (
            asm_commande(c.children[0], local_vars, func_name)
            + "\n"
            + asm_commande(c.children[1], local_vars, func_name)
        )
    return ""


def asm_function(f):
    return_type_decl = f.children[0]
    if return_type_decl.data == "array_decl_type":
        raise TypeError(
            "Functions cannot return arrays directly. Return a pointer instead."
        )
    func_name = return_type_decl.children[1].value
    params_tree = f.children[1].children
    block_node = f.children[2]

    env[func_name] = {"type": "function", 'params': []}
    local_vars = {}
    arg_registers = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]

    asm_code = f"""
; --- Function: {func_name} ---
{func_name}:
    push rbp
    mov rbp, rsp
    sub rsp, 256
"""
    for i, param_decl in enumerate(params_tree):
        param_type = param_decl.children[0].value
        if param_decl.data == "array_decl_type":
            env[func_name]["params"].append(f"{param_type}[]")
        else:
            env[func_name]["params"].append(param_type)
        param_name = param_decl.children[-1].value
        offset = -(8 * (1 + len(local_vars)))
        local_vars[param_name] = {'off': offset, 'type': param_type}
        asm_code += (
            f"    mov [rbp{offset}], {arg_registers[i]} ; Save param '{param_name}'\n"
        )
    env[func_name]["return_type"] = type_expression(return_type_decl, local_vars)
    for cmd in block_node.children:
        asm_code += asm_commande(cmd, local_vars, func_name) + "\n"
    asm_code += f"""
{func_name}_epilogue:
    mov rsp, rbp
    pop rbp
    ret
"""
    return asm_code


def asm_program(p):
    
    global cpt
    cpt = 0
    declared_strings.clear()

    functions_asm = ""
    main_node = None
    for child in p.children:
        if child.data == "function":
            functions_asm += asm_function(child)
        elif child.data == "main":
            main_node = child

    env["main"] = {
        "type": "function",
        "params": [],
        "return_type": main_node.children[0]
    }

    main_params = main_node.children[1].children  
    init_vars = ""
    input_vars = []
    for i, param in enumerate(main_params):
        var_type = param.children[0].value
        var_name = param.children[1].value
        env[var_name] = {"type": var_type}
        input_vars.append(var_name)


        offset = (i+1)*8
        if var_type.lower() == "string":
            init_vars += f"""\
    mov rbx, [argv_ptr]
    mov rdi, [rbx + {offset}]
    mov [{var_name}], rdi

"""
        else:
            init_vars += f"""\
    mov rbx, [argv_ptr]
    mov rdi, [rbx + {offset}]
    call atoi
    mov [{var_name}], rax

"""

    main_block = main_node.children[2]
    used_vars = get_vars_commande(main_block)
    used_vars.update(input_vars)
    used_vars = sorted(used_vars)

    decl_vars = ""
    for v in used_vars:
        decl_vars += f"{v}: dq 0\n"

    string_literals = extract_string_literals(p)
    string_section = ""
    for s in string_literals:
        label   = f"str_{abs(hash(s)) % (10**8)}"
        escaped = s[1:-1].replace('\\', '\\\\').replace('"', '\\"')
        string_section += f'{label}: db "{escaped}", 0\n'

    main_commande_asm = ""
    main_local = {}
    for cmd in main_block.children:
        main_commande_asm += asm_commande(cmd, main_local, "main")

    with open("moule.asm") as f:
        prog_asm = f.read()

    prog_asm = prog_asm.replace("FUNCTIONS", functions_asm)
    prog_asm = prog_asm.replace("DECL_VARS", decl_vars + string_section)
    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("COMMANDE", main_commande_asm)
    prog_asm = prog_asm.replace("RETOUR", "nop")

    return prog_asm


def indent(text, amount=4):
    """Indents each line of a string with spaces."""
    return "".join(" " * amount + line for line in text.splitlines(True))
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



def extract_string_literals(node, acc=None):
    if acc is None:
        acc = set()
    if isinstance(node, Tree):
        
        if node.data == "string_expr" \
           and isinstance(node.children[0], Token) \
           and node.children[0].type == "STRING":
            acc.add(node.children[0].value)

        
        if node.data == "string_decl":
            token = node.children[1]
            if isinstance(token, Token) and token.type == "STRING":
                acc.add(token.value)

        for child in node.children:
            extract_string_literals(child, acc)
    return acc

def pp_expression(e):
    if isinstance(e, Tree) and e.data == "string_expression":
        return pp_expression(e.children[0])
    if isinstance(e, Tree) and e.data == "int_expression":
        return pp_expression(e.children[0])
    if isinstance(e, Tree) and e.data == "string_expr":
        return e.children[0].value
    if isinstance(e, Tree) and e.data == "str_concat":
        return f"{pp_expression(e.children[0])} + {pp_expression(e.children[1])}"
    if isinstance(e, Tree) and e.data == "str_index":
        return f"{e.children[0].value}[{pp_expression(e.children[1])}]"
    if isinstance(e, Tree) and e.data == "strlen":
        return f"len({pp_expression(e.children[0])})"
    if isinstance(e, Tree) and e.data == "atoi":
        return f"atoi({pp_expression(e.children[0])})"
    
    if e.data == "number" or e.data == "var":
        return e.children[0].value
    if e.data == "arr_access":
        name = e.children[0].value
        idx = pp_expression(e.children[1])
        return f"{name}[{idx}]"
    if e.data == "opbin":
        left = pp_expression(e.children[0])
        op = e.children[1].value
        right = pp_expression(e.children[2])
        return f"({left} {op} {right})"
    if e.data == "function_call":
        func_name = e.children[0].value
        args_str = ", ".join(pp_expression(arg) for arg in e.children[1:])
        return f"{func_name}({args_str})"


def pp_var_decl(v):
    if v.data == "simple_decl_type":
        type_name = v.children[0].value
        var_name = v.children[1].value
        return f"{type_name} {var_name}"
    if v.data == "array_decl_type":
        type_name = v.children[0].value
        size_node = v.children[1]
        size_str = size_node.value if size_node else ""
        var_name = v.children[2].value
        return f"{type_name}[{size_str}] {var_name}"


def pp_block(b):
    return "".join(pp_commande(cmd) for cmd in b.children)


def pp_commande(c):
    if c.data == "string_decl":
        return f"char *{c.children[0].value} = {c.children[1].value}"
    if c.data == "string_decl_empty":
        return f"char *{c.children[0].value}"
    if c.data == "declaration":
        type_name = c.children[0].value
        var_name = c.children[1].value
        expr = pp_expression(c.children[2])
        return f"{type_name} {var_name} = {expr};\n"
    if c.data == "array_declaration":
        type_name = c.children[0].value
        size = pp_expression(c.children[1])
        name = c.children[2].value
        return f"{type_name}[{size}] {name};\n"
    if c.data == "array_declaration_init":
        type_name = c.children[0].value
        size = pp_expression(c.children[1])
        name = c.children[2].value
        vals_str = ", ".join(pp_expression(v) for v in c.children[3].children)
        return f"{type_name}[{size}] {name} = {{ {vals_str} }};\n"
    if c.data == "affectation":
        name = c.children[0].value
        expr = pp_expression(c.children[1])
        return f"{name} = {expr};\n"
    if c.data == "arr_affectation":
        name = c.children[0].value
        idx = pp_expression(c.children[1])
        expr = pp_expression(c.children[2])
        return f"{name}[{idx}] = {expr};\n"
    if c.data == "return_statement":
        expr = pp_expression(c.children[0])
        return f"return({expr});\n"
    if c.data == "print":
        expr = pp_expression(c.children[0])
        return f"printf({expr});\n"
    if c.data == "skip":
        return "skip;\n"
    if c.data == "sequence":
        return pp_commande(c.children[0]) + pp_commande(c.children[1])
    if c.data == "while":
        cond = pp_expression(c.children[0])
        body = pp_block(c.children[1])
        return f"while ({cond}) {{\n{indent(body)}}}\n"
    if c.data == "ite":
        cond = pp_expression(c.children[0])
        then_body = pp_block(c.children[1])
        if_str = f"if ({cond}) {{\n{indent(then_body)}}}\n"
        if len(c.children) > 2:
            else_body = pp_block(c.children[2])
            if_str = if_str.strip() + f" else {{\n{indent(else_body)}}}\n"
        return if_str
    if c.data == "forloop":
        type_name = c.children[0].value
        loop_var = c.children[1].value
        init = pp_expression(c.children[2])
        cond = pp_expression(c.children[3])
        body = pp_block(c.children[5])
        return f"for ({type_name} {loop_var} = {init}; {cond}; {loop_var}++) {{\n{indent(body)}}}\n"


def pp_function(f):
    return_decl = pp_var_decl(f.children[0])
    params = ", ".join(pp_var_decl(p) for p in f.children[1].children)
    body = pp_block(f.children[2])
    return f"{return_decl}({params}) {{\n{indent(body)}}}\n"


def pp_program(p):
    output = []
    for child in p.children:
        if child.data == "function":
            output.append(pp_function(child))
        elif child.data == "main":
            # Main is parsed like a function, so we can use pp_function
            type_name = child.children[0].value
            params = ", ".join(pp_var_decl(p) for p in child.children[1].children)
            body = pp_block(child.children[2])
            output.append(f"{type_name} main({params}) {{\n{indent(body)}}}\n")
    return "\n".join(output)


if __name__ == "__main__":
    with open("test.c") as f:
        src = f.read()
    ast = g.parse(src)
    print(ast)

    print("--- Pretty-Printed Source ---")
    print(pp_program(ast))
    print("-----------------------------\n")

    # Generate assembly
    print("--- Compilation ---")
    asm_code = asm_program(ast)

    # Write assembly to file
    with open("output.asm", "w") as f:
        f.write(asm_code)

    print("Compilation complete. Assembly written to output.asm")
