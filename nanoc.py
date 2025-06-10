from lark import Lark, Tree, Token
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
    STRING: /"[^\"]*"/
    OPBIN: "+" | "-" | "*" | "/" | "==" | "!=" | ">" | "<" | ">=" | "<="
    TYPE: "int" | "char" | "char*" | "int[]" | "char*[]"

    var_decl: TYPE "[" NUMBER? "]" IDENTIFIER -> array_decl_type
            | TYPE IDENTIFIER                  -> simple_decl_type

    liste_var:                          -> vide
        | var_decl ("," var_decl)*      -> vars

    liste_values: expression ("," expression)* -> liste_values

    expression: IDENTIFIER "[" expression "]" -> arr_access
        | IDENTIFIER                -> var
        | NUMBER                          -> number
        | STRING                          -> string_expr
        | expression OPBIN expression     -> opbin
        | IDENTIFIER "(" (expression ("," expression)*)? ")" -> function_call

    commande: "for" "(" TYPE IDENTIFIER "=" expression ";" expression ";" IDENTIFIER "++" ")" "{" block "}" -> forloop
        | TYPE "[" expression "]" IDENTIFIER "=" "{" liste_values "}" ";" -> array_declaration_init
        | TYPE "[" expression "]" IDENTIFIER ";"                         -> array_declaration
        | TYPE IDENTIFIER "=" expression ";"                             -> declaration
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


def asm_expression(e, local_vars):
    """Compiles an expression. local_vars is the map of local names to [rbp-offset]."""
    if e.data == "number":
        return f"mov rax, {e.children[0].value}"

    if e.data == "string_expr":
        None

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

        # Get the base address of the array (it's a pointer)
        if name in local_vars:
            base_addr_location = f"[rbp{local_vars[name]['off']}]"
        elif name in env:
            base_addr_location = f"[{name}]"
        else:
            raise NameError(f"Array '{name}' not defined.")

        # Calculate index and access memory
        return f"""
    {asm_expression(idx_expr, local_vars)}
    mov rbx, rax                     ; rbx holds the index
    mov rax, {base_addr_location}    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)
"""

    if e.data == "opbin":
        if type_expression(e.children[0], env) == "char*" or type_expression(e.children[0], env) == "char":
            if e.children[1].value != "+":
                raise TypeError("Opération non supportée pour les char* ou char.")
            type_commande(e, env)
            None
        else:
            type_commande(e, env)
            left_asm = asm_expression(e.children[0], local_vars)
            right_asm = asm_expression(e.children[2], local_vars)
            op = e.children[1].value
            return f"""
    {right_asm}
    push rax
    {left_asm}
    pop rbx
    {op2asm[op]}
"""

    if e.data == "function_call":
        func_name = e.children[0].value
        args = e.children[1:]
        arg_registers = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        if len(args) > len(arg_registers):
            raise NotImplementedError(
                "Functions with more than 6 arguments are not supported."
            )

        asm_code = ""
        for arg in args:
            asm_code += asm_expression(arg, local_vars) + "\n"
            asm_code += "push rax\n"
        for i in range(len(args)):
            asm_code += f"pop {arg_registers[i]}\n"

        # Special handling for printf
        if func_name == "printf":
            asm_code += "xor rax, rax\n"

        asm_code += f"call {func_name}\n"
        return asm_code


def asm_commande(c, local_vars, func_name):
    """Compiles a command. Needs local_vars for context and func_name for returns."""
    global cpt

    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        if var_type != type_expression(c.children[2], env):
            print(env)
            print(c.children[2])
            print(type_expression(c.children[2], env))
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
        env[arr_name] = {"type": f"{var_type}[]", 'size': size_expr.children[0].value}
        print(env)
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
        return f"""
    {asm_expression(c.children[0], local_vars)}
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf
"""
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
    local_vars[func_name] = {"type": "function", 'params': []}
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
            local_vars[func_name]["params"].append(f"{param_type}[]")
        else:
            env[func_name]["params"].append(param_type)
            local_vars[func_name]["params"].append(param_type)
        param_name = param_decl.children[-1].value
        offset = -(8 * (1 + len(local_vars)))
        local_vars[param_name] = {'off': offset, 'type': param_type}
        asm_code += (
            f"    mov [rbp{offset}], {arg_registers[i]} ; Save param '{param_name}'\n"
        )
    env[func_name]["return_type"] = type_expression(return_type_decl, local_vars)
    local_vars[func_name]["return_type"] = type_expression(return_type_decl, local_vars)
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
    functions_asm = ""
    main_node = None
    for child in p.children:
        if child.data == "function":
            functions_asm += asm_function(child)
        elif child.data == "main":
            main_node = child
    main_params = main_node.children[1].children
    main_block = main_node.children[2]
    decl_vars = ""
    init_vars = ""
    for i, param in enumerate(main_params):
        var_name = param.children[1].value
        var_type = param.children[0].value
        env[var_name] = {"type": var_type}  #{"type": "global_var"}
        decl_vars += f"{var_name}: dq 0\n"
        init_vars += f"""
    mov rdi, [argv_ptr]
    mov rdi, [rdi + {(i+1)*8}]
    call atoi
    mov [{var_name}], rax
"""
    main_local_vars = {}
    main_commande_asm = ""
    env["main"] = {"type": "function", 'params': [], 'return_type': main_node.children[0]}
    for cmd in main_block.children:
        main_commande_asm += asm_commande(cmd, main_local_vars, "main")
        #type_commande(cmd, env)
    with open("moule.asm") as f:
        prog_asm = f.read()

    prog_asm = prog_asm.replace("DECL_VARS", decl_vars)
    prog_asm = prog_asm.replace("FUNCTIONS", functions_asm)
    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("COMMANDE", main_commande_asm)
    return prog_asm


def indent(text, amount=4):
    """Indents each line of a string with spaces."""
    return "".join(" " * amount + line for line in text.splitlines(True))


def pp_expression(e):
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
