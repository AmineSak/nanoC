from lark import Lark

from typage import type_commande, type_expression

env = {}
cpt = 0
func_env = {}  # Store function definitions


g = Lark(
    """
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9]*/
NUMBER: /[1-9][0-9]*/ | "0"
OPBIN: "+" | "-" | "*" | ">" | "==" | "!=" | "<" | ">=" | "<="
TYPE: "int" | "char*"

typed_var: TYPE IDENTIFIER -> typed_var

liste_var:                            -> vide
    | typed_var ("," typed_var)*      -> vars

expression: IDENTIFIER                -> var
    | NUMBER                          -> number
    | expression OPBIN expression     -> opbin
    | IDENTIFIER "(" (expression ("," expression)*)? ")" -> function_call

commande: TYPE IDENTIFIER "=" expression ";" -> declaration
    | TYPE "[" expression "]" IDENTIFIER "=" "{" NUMBER ("," NUMBER)* "}"";" -> array_declaration
    | IDENTIFIER "=" expression ";"         -> affectation
    | "while" "(" expression ")" "{" block "}" -> while
    | "if" "(" expression ")" "{" block "}" ("else" "{" block "}")? -> ite
    | "printf" "(" expression ")" ";"       -> print
    | "skip" ";"                            -> skip
    | commande ";" commande                 -> sequence
    | "return" "(" expression ")" ";"       -> return_statement
    | IDENTIFIER "[" expression "]" "=" expression             -> arr_affectation

block: (commande)* -> block

main: TYPE "main" "(" liste_var ")" "{" block "}" -> main

function: typed_var "(" liste_var ")" "{" block "}" -> function

program: function* main -> program

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
    "<": "cmp rax, rbx\nsetl al\nmovzx rax, al",
    ">=": "cmp rax, rbx\nsetge al\nmovzx rax, al",
    "<=": "cmp rax, rbx\nsetle al\nmovzx rax, al",
    "==": "cmp rax, rbx\nsete al\nmovzx rax, al",
    "!=": "cmp rax, rbx\nsetne al\nmovzx rax, al",
}


def asm_expression(e, local_vars=None, params=None):
    if local_vars is None:
        local_vars = {}
    if params is None:
        params = {}

    if e.data == "var":
        var_name = e.children[0].value
        # Parameters are now treated the same as local variables
        if var_name in local_vars:
            offset = local_vars[var_name]
            return f"mov rax, [rbp{offset}]"
        # The `params` dictionary is no longer needed here.
        # We can remove the `elif var_name in params:` block entirely.
        else:
            # Otherwise it's a global variable
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

        # System V AMD64 ABI uses these registers for the first 6 integer/pointer arguments
        arg_registers = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]

        if len(args) > len(arg_registers):
            raise NotImplementedError("More than 6 arguments are not supported yet.")

        if func_name not in func_env and func_name not in ["printf", "atoi"]:
            raise TypeError(f"Function '{func_name}' not defined.")

        asm_code = ""
        # 1. Evaluate all arguments and push them onto the stack to save them.
        # We do this to avoid an argument's evaluation clobbering a register
        # needed for another argument.
        for arg in args:
            asm_code += asm_expression(arg, local_vars, params) + "\n"
            asm_code += "push rax\n"

        # 2. Pop the evaluated arguments from the stack into the correct registers.
        # Note: we pop in reverse order of how they were pushed.
        for i in range(len(args)):
            reg = arg_registers[i]
            asm_code += f"pop {reg}\n"

        # Special handling for printf which needs rax to be 0 for varargs
        if func_name == "printf":
            asm_code += "xor rax, rax\n"

        # 3. Call the function
        asm_code += f"call {func_name}\n"

        # 4. No stack cleanup (`add rsp, ...`) is needed because the callee doesn't clean
        # the registers, and we didn't leave anything on the stack.

        return asm_code


def asm_commande(c, local_vars=None, params=None, func_name=None):
    global cpt

    if local_vars is None:
        local_vars = {}
    if params is None:
        params = {}

    if c.data == "declaration":
        var_type = c.children[0].value
        var_name = c.children[1].value
        exp = c.children[2]

        # Add to environment
        env[var_name] = var_type

        # FIXED: Always treat main function variables as locals
        # Calculate offset from rbp (always negative for locals)
        offset = -(8 + 8 * len(local_vars))
        local_vars[var_name] = offset

        exp_asm = asm_expression(exp, local_vars, params)
        return f"{exp_asm}\nmov [rbp{offset}], rax  ; local var {var_name}"

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
mov rsi, rax
mov rdi, fmt_int
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

    if c.data == "while":
        exp = c.children[0]
        block = c.children[1]  # This is now a Tree('block', ...)

        body_asm = ""
        for cmd in block.children:  # We can now loop through the block's children
            body_asm += asm_commande(cmd, local_vars, params, func_name) + "\n"

        idx = cpt
        cpt += 1
        return f"""
loop{idx}:
    {asm_expression(exp, local_vars, params)}
    cmp rax, 0
    jz end{idx}
    {body_asm}
    jmp loop{idx}
end{idx}:
    nop
"""

    if c.data == "ite":
        condition = c.children[0]
        then_block = c.children[1]  # This is the Tree for the 'then' block
        idx = cpt
        cpt += 1

        # Compile the 'then' block
        then_asm = ""
        for cmd in then_block.children:
            then_asm += asm_commande(cmd, local_vars, params, func_name) + "\n"

        if len(c.children) > 2:  # There's an else clause
            else_block = c.children[2]  # This is the Tree for the 'else' block

            # Compile the 'else' block
            else_asm = ""
            for cmd in else_block.children:
                else_asm += asm_commande(cmd, local_vars, params, func_name) + "\n"

            return f"""
    {asm_expression(condition, local_vars, params)}
    cmp rax, 0
    jz else{idx}
{then_asm}
    jmp endif{idx}
else{idx}:
{else_asm}
endif{idx}:
    nop
"""
        else:  # No else clause
            return f"""
    {asm_expression(condition, local_vars, params)}
    cmp rax, 0
    jz endif{idx}
{then_asm}
endif{idx}:
    nop
"""

    if c.data == "sequence":
        d = c.children[0]
        tail = c.children[1]
        return f"{asm_commande(d, local_vars, params)}\n{asm_commande(tail, local_vars, params)}"
    elif c.data == "return_statement":
        if func_name is None:
            raise Exception("Return statement found outside of a function.")

        # 1. Evaluate the expression. The result goes into RAX.
        exp_asm = asm_expression(c.children[0], local_vars, params)

        # 2. Jump to the function's epilogue.
        return f"""{exp_asm}
    jmp {func_name}_epilogue
"""


def asm_function(f):
    global func_env
    # ... (extract func_name, etc. as before) ...
    return_type = f.children[0].children[0].value
    func_name = f.children[0].children[1].value
    params_tree = f.children[1].children if hasattr(f.children[1], "children") else []

    # ... (Store in func_env as before) ...
    func_env[func_name] = {"return_type": return_type, "params": []}

    # These are the registers where the parameters will arrive
    arg_registers = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]

    # We will treat parameters as local variables stored on the stack.
    # This is different from the old param_offsets.
    local_vars = {}

    # Prologue
    asm_code = f"""
; Function: {func_name}
{func_name}:
    push rbp                ; Save old base pointer
    mov rbp, rsp            ; Set new base pointer
    sub rsp, 128            ; Reserve stack space for local variables
"""

    # NEW: Copy parameters from registers to the stack
    if len(params_tree) > len(arg_registers):
        raise NotImplementedError("More than 6 arguments are not supported yet.")

    for i, param in enumerate(params_tree):
        param_type = param.children[0].value
        param_name = param.children[1].value
        reg = arg_registers[i]

        # Calculate a *local variable* offset for the parameter
        offset = -(8 + 8 * len(local_vars))
        local_vars[param_name] = offset

        # Add the instruction to save the register to the stack
        asm_code += (
            f"    mov [rbp{offset}], {reg} ; Save parameter '{param_name}' from {reg}\n"
        )
        func_env[func_name]["params"].append((param_type, param_name))

    block_node = f.children[2]

    # 2. Loop through the commands INSIDE the block node.
    for cmd in block_node.children:
        asm_code += asm_commande(cmd, local_vars, {}, func_name) + "\n"

    # This part is now correct
    asm_code += f"""
{func_name}_epilogue:
    mov rsp, rbp
    pop rbp
    ret
"""
    return asm_code


def asm_program(p):
    # Process functions
    functions_asm = ""
    main_idx = 0
    for i in range(len(p.children)):
        if hasattr(p.children[i], "data") and p.children[i].data == "function":
            functions_asm += asm_function(p.children[i])
        if hasattr(p.children[i], "data") and p.children[i].data == "main":
            main_idx = i
            break

    main = p.children[main_idx].children

    # Process main parameters - these become global variables
    for c in main[1].children:
        env[c.children[1].value] = c.children[0].value

    with open("moule.asm") as f:
        prog_asm = f.read()

    # FIXED: Create local vars for main function too
    main_local_vars = {}
    init_vars = ""
    decl_vars = ""
    commande = ""

    # Process main parameters for init vars and declarations
    for i, c in enumerate(main[1].children):
        if env[c.children[1].value] == "int":
            init_vars += f"""mov rbx, [argv]
mov rdi, [rbx + {(i+1)*8}]
call atoi
mov [{c.children[1].value}], rax
"""
            decl_vars += f"{c.children[1].value}: dq 0\n"
        elif env[c.children[1].value] == "char*":
            decl_vars += f"{c.children[1].value}: dq 0\n"

    # Add function declarations
    for func_name, _ in func_env.items():
        decl_vars += f"; Function {func_name} is defined in the text section\n"

    block_node = main[2]

    # 2. Loop through the commands inside the block.
    for cmd in block_node.children:
        # Pass the actual command, not the block, to asm_commande
        asm_c = asm_commande(cmd, main_local_vars, {}, "main")
        commande += f"{asm_c}\n"

    # This part is now correct
    commande += """main_epilogue:
    mov rsp, rbp
    pop rbp
    ret
"""

    # REMOVE the old RETOUR logic.
    prog_asm = prog_asm.replace("INIT_VARS", init_vars)
    prog_asm = prog_asm.replace("DECL_VARS", decl_vars)
    prog_asm = prog_asm.replace("COMMANDE", commande)
    # The 'RETOUR' placeholder is no longer used, so we can remove its replacement logic.
    prog_asm = prog_asm.replace(
        "RETOUR", ""
    )  # Or just ensure it's not in the template.
    prog_asm = prog_asm.replace("FUNCTIONS", functions_asm)

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
    if c.data == "arr_affectation":
        name = c.children[0].value
        idx = pp_expression(c.children[1])
        expr = pp_expression(c.children[2])
        return f"{name}[{idx}] = {expr}"
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
