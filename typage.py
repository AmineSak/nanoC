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
            return env[e.value]
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
            return env[var_name]
        if e.data == "number":
            return "int"
        if e.data == "string":
            return "char*"
        if e.data == "opbin":
            left_type = type_expression(e.children[0], env)
            right_type = type_expression(e.children[2], env)
            if left_type != right_type:
                raise TypeError(f"Opération {e.children[1].value} entre types incompatibles : {left_type} et {right_type}.")
            return left_type
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
            env[var_name] = var_type 
        elif len(c.children) == 2:
            var_type = c.children[0].value  
            var_name = c.children[1].value
            env[var_name] = var_type
    elif c.data == "array_declaration":
        var_type = c.children[0].value
        var_name = c.children[2].value
        print(c.children[1].value)
        for i in range(3, len(c.children)):
            if c.children[i].type == "NUMBER" and var_type != "int":
                raise TypeError(f"Incompatibilité de type pour la déclaration de '{var_name}'.")
        if int(c.children[1].value) != len(c.children) - 3:
            raise TypeError(f"Le nombre d'éléments pour '{var_name}' ne correspond pas à la taille déclarée.")    
    elif c.data == "affectation":
        var_name = c.children[0].value
        exp_type = type_expression(c.children[1], env)
        if var_name not in env:
            raise TypeError(f"Variable '{var_name}' non déclarée.")
        if env[var_name] != exp_type:
            raise TypeError(f"Incompatibilité de type pour la variable '{var_name}'.")
    elif c.data == "print":
        exp_type = type_expression(c.children[0], env)
        if exp_type not in ("int", "char*"):
            raise TypeError("printf ne peut imprimer que des entiers ou des chaînes de caractères.")
    elif c.data == "while":
        cond_type = type_expression(c.children[0], env)
        if cond_type != "int":
            raise TypeError("La condition d'une boucle while doit être un entier.")
        type_commande(c.children[1], env)
    elif c.data == "sequence":
        type_commande(c.children[0], env)
        type_commande(c.children[1], env)
    elif c.data == "skip":
        pass
    else:
        raise TypeError(f"Commande non reconnue : {c.data}")