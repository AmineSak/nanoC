from lark import Lark

from typage import type_commande, type_expression

env = {}
cpt = 0
func_env = {}  # Store function definitions
g = Lark(
    """
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/ | "0"
OPBIN: "+" | "-" | "*" | ">"
TYPE: "int" | "char*"

typed_var: TYPE IDENTIFIER -> typed_var

liste_var:                            -> vide
    | typed_var ("," typed_var)*      -> vars

expression: IDENTIFIER                -> var
    | NUMBER                          -> number
    | expression OPBIN expression     -> opbin
    | IDENTIFIER "(" (expression ("," expression)*)? ")" -> function_call

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
    start="program",
)


def get_vars_expression(e):
    pass


def get_vars_commande(c):
    pass


op2asm = {
    "+": "add rax, rbx",
    "-": "sub rax, rbx",
    "*": "imul rax, rbx",
    ">": "cmp rax, rbx\nsetg al\nmovzx rax, al",
}


def asm_expression(e, local_vars=None, params=None):
    if local_vars is None:
        local_vars = {}
    if params is None:
        params = {}

    if e.data == "var":
        var_name = e.children[0].value
        # Check if it's a local variable
        if var_name in local_vars:
            offset = local_vars[var_name]
            return f"mov rax, [rbp+{offset}]"
        # Check if it's a parameter
        elif var_name in params:
            offset = params[var_name]
            return f"mov rax, [rbp+{offset}]"
        # Otherwise it's a global variable
        else:
            return f"mov rax, [{var_name}]"

    if e.data == "number":
        return f"mov rax, {e.children[0].value}"

    if e.data == "opbin":
        e_left = e.children[0]
        e_op = e.children[1]
        e_right = e.children[2]
        asm_left = asm_expression(e_left, local_vars, params)
        asm_right = asm_expression(e_right, local_vars, params)
        return f"""{asm_left}
push rax
{asm_right}
mov rbx, rax
pop rax
{op2asm[e_op.value]}"""

    if e.data == "function_call":
        func_name = e.children[0].value
        args = e.children[1:] if len(e.children) > 1 else []

        if func_name not in func_env:
            raise TypeError(f"Function '{func_name}' not defined.")

        # Push arguments in reverse order (C calling convention)
        asm_code = ""
        for arg in reversed(args):
            arg_asm = asm_expression(arg, local_vars, params)
            asm_code += f"{arg_asm}\npush rax\n"

        # Call the function
        asm_code += f"call {func_name}\n"

        # Clean up the stack
        if args:
            asm_code += f"add rsp, {8 * len(args)}  ; Clean up {len(args)} arguments\n"

        return asm_code


def asm_commande(c, local_vars=None, params=None):
    global cpt

    if local_vars is None:
        local_vars = {}
    if params is None:
        params = {}

    # print(c)
    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        exp = c.children[2]

        # Add to environment
        env[var_name] = var_type

        # If we're in a function, store as local variable
        if local_vars is not None:
            # Calculate offset from rbp (always negative for locals)
            offset = -(8 + 8 * len(local_vars))  # 8 bytes per variable (64-bit)
            local_vars[var_name] = offset

            exp_asm = asm_expression(exp, local_vars, params)
            return f"{exp_asm}\nmov [rbp{offset}], rax  ; local var {var_name}"
        else:
            # Global variable
            if var_type == "int":
                return (
                    f"{asm_expression(exp, local_vars, params)}\nmov [{var_name}], rax"
                )
            elif var_type == "char*":
                return (
                    f"{asm_expression(exp, local_vars, params)}\nmov [{var_name}], rax"
                )

    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        var_name = var.value

        # Check if it's a local variable
        if var_name in local_vars:
            offset = local_vars[var_name]
            return f"{asm_expression(exp, local_vars, params)}\nmov [rbp{offset}], rax"
        # Check if it's a parameter
        elif var_name in params:
            offset = params[var_name]
            return f"{asm_expression(exp, local_vars, params)}\nmov [rbp+{offset}], rax"
        # Otherwise it's a global
        else:
            if var_name not in env:
                raise TypeError(f"Variable '{var_name}' non déclarée.")
            return f"{asm_expression(exp, local_vars, params)}\nmov [{var_name}], rax"

    if c.data == "skip":
        return "nop"

    if c.data == "print":
        exp_type = type_expression(c.children[0], env)
        if exp_type == "int":
            return f"""{asm_expression(c.children[0], local_vars, params)}
mov rsi, fmt
mov rdi, rax
xor rax, rax
call printf
"""
        elif exp_type == "char*":
            return f"""{asm_expression(c.children[0], local_vars, params)}
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
        return f"""loop{idx}:{asm_expression(exp, local_vars, params)}
cmp rax, 0
jz end{idx}
{asm_commande(body, local_vars, params)}
jmp loop{idx}
end{idx}: nop
"""

    if c.data == "ite":
        condition = c.children[0]
        then_body = c.children[1]
        idx = cpt
        cpt += 1

        if len(c.children) > 2:  # There's an else clause
            else_body = c.children[2]
            return f"""{asm_expression(condition, local_vars, params)}
cmp rax, 0
jz else{idx}
{asm_commande(then_body, local_vars, params)}
jmp endif{idx}
else{idx}:
{asm_commande(else_body, local_vars, params)}
endif{idx}: nop
"""
        else:
            return f"""{asm_expression(condition, local_vars, params)}
cmp rax, 0
jz endif{idx}
{asm_commande(then_body, local_vars, params)}
endif{idx}: nop
"""

    if c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        return f"{asm_commande(d, local_vars, params)}\n{asm_commande(tail, local_vars, params)}"


def asm_function(f):
    global func_env

    # Extract function information
    return_type = f.children[0].children[0].value
    func_name = f.children[0].children[1].value
    params_tree = f.children[1].children if hasattr(f.children[1], "children") else []
    body = f.children[2]
    return_exp = f.children[3]

    # Store function in environment
    func_env[func_name] = {"return_type": return_type, "params": []}

    # Create parameter mapping (parameter -> stack position)
    param_offsets = {}
    for i, param in enumerate(params_tree):
        param_type = param.children[0].value
        param_name = param.children[1].value

        # Parameters start at [rbp+16] (rbp+8 is return address)
        offset = 16 + (i * 8)  # 8 bytes per parameter (64-bit)
        param_offsets[param_name] = offset

        # Add to function environment
        func_env[func_name]["params"].append((param_type, param_name))

    # Create local variable mapping
    local_vars = {}

    # Function prologue
    asm_code = f"""
; Function: {func_name}
{func_name}:
    push rbp                ; Save old base pointer
    mov rbp, rsp            ; Set new base pointer
    sub rsp, 128            ; Reserve stack space for local variables (adjust as needed)
"""

    # Function body
    asm_code += asm_commande(body, local_vars, param_offsets)

    # Return expression
    asm_code += f"""
    ; Return value
    {asm_expression(return_exp, local_vars, param_offsets)}
    
    ; Function epilogue
    mov rsp, rbp            ; Restore stack pointer
    pop rbp                 ; Restore base pointer
    ret                     ; Return to caller
"""

    return asm_code


def asm_program(p):
    # Process functions
    functions_asm = ""
    for i in range(len(p.children)):
        if hasattr(p.children[i], "data") and p.children[i].data == "function":
            functions_asm += asm_function(p.children[i])

    # Find main function node
    main_idx = -1
    for i in range(len(p.children)):
        if isinstance(p.children[i], str) and p.children[i] == "main":
            main_idx = i
            break

    # Process main parameters
    for c in p.children[main_idx - 1].children:
        env[c.children[1].value] = c.children[0].value

    # Type check commands
    for i in range(main_idx + 1, len(p.children) - 1):
        type_commande(p.children[i], env)

    # Check return type
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

    # Process main parameters for init vars and declarations
    for i, c in enumerate(p.children[main_idx - 1].children):
        if env[c.children[1].value] == "int":
            init_vars += f"""mov rbx, [argv]
mov rdi, [rbx + {(i+1)*8}]
call atoi
mov [{c.children[1].value}], rax
"""
            decl_vars += f"{c.children[1].value}: dq 0\n"
        elif env[c.children[1].value] == "char*":
            decl_vars += f"{c.children[1].value}: db 0\n"

    # Add function declarations
    for func_name, func_info in func_env.items():
        if func_info["return_type"] == "int":
            decl_vars += f"; Function {func_name} is defined in the text section\n"

    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("DECL_VARS", decl_vars)

    # Process main function commands
    for i in range(main_idx + 1, len(p.children) - 1):
        asm_c = asm_commande(p.children[i])
        commande += f"{asm_c}\n"

    prog_asm = prog_asm.replace("COMMANDE", commande)

    # Add functions before _start
    prog_asm = prog_asm.replace("; FUNCTIONS", functions_asm)

    return prog_asm


def pp_list_typed_vars(l):
    if not hasattr(l, "children") or not l.children:
        return ""

    typed_var = l.children[0]
    type = typed_var.children[0].value
    var = typed_var.children[1].value
    L = f"{type} {var}"

    for i in range(1, len(l.children)):
        typed_var = l.children[i]
        type = typed_var.children[0].value
        var = typed_var.children[1].value
        L += f", {type} {var}"
    return L


def pp_expression(e):
    if e.data in ("var", "number"):
        return f"{e.children[0].value}"

    if e.data == "function_call":
        func_name = e.children[0].value
        args = []
        for i in range(1, len(e.children)):
            args.append(pp_expression(e.children[i]))
        return f"{func_name}({', '.join(args)})"

    e_left = e.children[0]
    e_op = e.children[1]
    e_right = e.children[2]
    return f"{pp_expression(e_left)} {e_op.value} {pp_expression(e_right)}"


def pp_commande(c):
    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        exp = c.children[2]
        return f"{var_type} {var_name} = {pp_expression(exp)};"
    if c.data == "affectation":
        var = c.children[0]
        exp = c.children[1]
        return f"{var.value} = {pp_expression(exp)};"
    if c.data == "skip":
        return "skip;"
    if c.data == "print":
        return f"printf({pp_expression(c.children[0])});"
    if c.data == "while":
        exp = c.children[0]
        body = c.children[1]
        return f"while ({pp_expression(exp)}) {{{pp_commande(body)}}}"
    if c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        return f"{pp_commande(d)} {pp_commande(tail)}"
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
    return f"{output_type} {name}({list_typed_vars}) {{{body} \nreturn({exp});}} "


if __name__ == "__main__":
    with open("simple.c") as f:
        src = f.read()
    ast = g.parse(src)

    # Generate assembly
    asm_code = asm_program(ast)

    # Write assembly to file
    with open("output.asm", "w") as f:
        f.write(asm_code)

    print("Compilation complete. Assembly written to output.asm")
