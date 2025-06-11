from lark.tree import Tree
from lark.lexer import Token

def type_expression(e, env):
    """
    Vérifie le type d'une expression.
    :param e: L'expression à vérifier.
    :param env: L'environnement des variables (dictionnaire {nom: type}).
    :return: Le type de l'expression (par exemple, "int" ou "char*").
    """
    if isinstance(e, Token):
        if e.type == "IDENTIFIER":
            if e.value not in env:
                raise TypeError(f"Variable '{e.value}' non déclarée.")
            return env[e.value]['type']
        if e.type == "NUMBER":
            return "int"
        if e.type == "STRING":
            return "char*"
        raise TypeError(f"Token non reconnu : {e.type}")

    if isinstance(e, Tree):
        if e.data == "var":
            var_name = e.children[0].value
            if var_name not in env:
                raise TypeError(f"Variable '{var_name}' non déclarée.")
            return env[var_name]['type']
        if e.data == "number":
            return "int"
        if e.data == "string":
            return "char*"
        if e.data == "arr_access":
            var_name = e.children[0].value
            if var_name not in env:
                raise TypeError(f"Variable '{var_name}' non déclarée.")
            if env[var_name]['type'] not in ("int[]", "char*[]"):
                raise TypeError(f"'{var_name}' n'est pas un tableau.")
            return env[var_name]['type'][0:-2]
        if e.data == "opbin":
            left_type = type_expression(e.children[0], env)
            right_type = type_expression(e.children[2], env)
            if left_type != right_type:
                raise TypeError(f"Opération {e.children[1].value} entre types incompatibles : {left_type} et {right_type}.")
            return left_type
        if e.data == "function_call":
            func_name = e.children[0].value
            if func_name not in env or env[func_name]['type'] != 'function':
                raise TypeError(f"Fonction '{func_name}' non déclarée ou de type incorrect.")
            if len(e.children) - 1 != len(env[func_name]['params']):
                raise TypeError(f"Nombre d'arguments incorrect pour la fonction '{func_name}'.")
            for i, arg in enumerate(e.children[1:]):
                arg_type = type_expression(arg, env)
                if arg_type != env[func_name]['params'][i]:
                    raise TypeError(f"Type d'argument incorrect pour '{func_name}': attendu {env[func_name]['params'][i]}, obtenu {arg_type}.")
            return env[func_name]['return_type']
        if e.data == 'simple_decl_type':
            return e.children[0].value
        if e.data == 'array_decl_type':
            return f"{e.children[0].value}[]"
        if e.data == "return_statement":
            exp_type = type_expression(e.children[0], env)
            if exp_type != env['return_type']:
                raise TypeError(f"Type de retour incorrect : attendu {env['return_type']}, obtenu {exp_type}.")
        raise TypeError(f"Expression non reconnue : {e.data}")

def type_commande(c, env):
    """
    Vérifie le type d'une commande.
    :param c: La commande à vérifier.
    :param env: L'environnement des variables (dictionnaire {nom: type}).
    """
    if isinstance(c, Token):
        raise TypeError(f"Commande inattendue : {c.type}")

    if c.data == "declaration":
        if len(c.children) == 3:    
            var_type = c.children[0].value 
            var_name = c.children[1].value
            exp_type = type_expression(c.children[2], env)
            if var_type != exp_type:
                raise TypeError(f"Incompatibilité de type pour la déclaration de '{var_name}'.")
        elif len(c.children) == 2:
            var_type = c.children[0].value  
            var_name = c.children[1].value
    elif c.data == "array_declaration_init":
        var_type = c.children[0].value
        var_name = c.children[2].value
        for i in range(len(c.children[3].children)):
            if c.children[3].children[i].children[0].type == "NUMBER" and var_type != "int":
                raise TypeError(f"Incompatibilité de type pour la déclaration de '{var_name}'.")
        if int(c.children[1].children[0]) != len(c.children[3].children):
            raise TypeError(f"Le nombre d'éléments pour '{var_name}' ne correspond pas à la taille déclarée.") 
    elif c.data == "array_declaration":
            var_type = c.children[0].value  
            var_name = c.children[2].value
    elif c.data == "affectation":
        var_name = c.children[0].value
        exp_type = type_expression(c.children[1], env)
        if var_name not in env:
            raise TypeError(f"Variable '{var_name}' non déclarée.")
        if env[var_name]['type'] != exp_type:
            raise TypeError(f"Incompatibilité de type pour la variable '{var_name}'.")
    elif c.data == "arr_affectation":
        var_name = c.children[0].value
        rank = c.children[1].value
        exp_type = type_expression(c.children[2], env)
        if var_name not in env:
            raise TypeError(f"Variable '{var_name}' non déclarée.")
        if env[var_name]['type'] not in ("int[]", "char*[]"):
            raise TypeError(f"'{var_name}' n'est pas un tableau.")
        if env[var_name]['size'] < rank:
            raise TypeError(f"Index {rank} hors limites pour le tableau '{var_name}'.")
    elif c.data == "print":
        exp_type = type_expression(c.children[0], env)
        if exp_type not in ("int", "char*"):
            raise TypeError("printf ne peut imprimer que des entiers ou des chaînes de caractères.")
    elif c.data == "while":
        if c.children[0].data != 'opbin':
            raise TypeError("La condition d'une boucle while doit être une expression binaire.")
        type_commande(c.children[1].children, env)
    elif c.data == "ite":
        if c.children[0].data != 'opbin':
            raise TypeError("La condition d'une instruction if doit être une expression binaire.")
        type_commande(c.children[1].children, env)
        if len(c.children) > 2:
            type_commande(c.children[2], env)
    elif c.data == "sequence":
        type_commande(c.children[0], env)
        type_commande(c.children[1], env)
    elif c.data == "return_statement":
        None
    elif c.data == "skip":
        pass
    else:
        raise TypeError(f"Commande non reconnue : {c.data}")