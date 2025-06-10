# nanoC

# Compilateur pour Notre Langage

Ce document fournit une description détaillée des fonctionnalités et de l'implémentation de notre compilateur, en se concentrant sur le typage statique, les fonctions, les chaînes de caractères et les tableaux.

## Typage

Pour ce compilateur, nous avons implémenté un **typage statique**. Cela signifie que chaque variable, expression, fonction ou tableau est vérifié au moment de la compilation pour s’assurer que les types utilisés sont compatibles avec les opérations effectuées.

Pour réaliser cela, nous avons intégré deux dictionnaires : un pour les variables globales et un pour les variables locales au sein des fonctions. Chacun de ces dictionnaires stocke, à chaque déclaration, la variable, son type, ainsi que les paramètres et le type de retour pour les fonctions, et la taille de chaque tableau déclaré.

Nous avions contraint, à l'origine l'utilisateur à n'utiliser que des `NUMBER` (nombres littéraux) pour la déclaration de la taille d'un tableau. En effet, dans le cas d'une expression (comme `x + z` par exemple), la valeur réelle est stockée dans le code assembleur et n'est connue qu'à l'exécution, ce qui rend impossible la vérification de la cohérence de la taille pendant la phase de compilation en Python. Finalement, nous avons retiré cette contraite pour pouvoir réaliser des opérations tel que le balayage des valeurs d'un tableau avec une boucle loop, ce qui peut néanmoins amener à des erreurs si l'indice de tableau est plus grand que la taille du tableau.

Nous avons créé deux fonctions externes pour le typage, qui prennent en entrée l'arbre de syntaxe abstraite (AST) à vérifier et un dictionnaire de variables :

- **`type_expression`**: Cette fonction analyse récursivement chaque expression de l’AST.

 - Elle vérifie que chaque variable utilisée a bien été déclarée et récupère son type.
 - Elle s’assure que les opérations binaires (addition, comparaison, etc.) sont réalisées entre des types compatibles.
 - Lors d’un appel de fonction, elle vérifie que la fonction existe, que le nombre et le type des arguments sont corrects, et elle retourne le type de retour attendu.

- **`type_commande`**: Cette fonction vérifie les instructions du programme.
 - Pour chaque déclaration ou affectation, elle s’assure que le type de la variable correspond au type de l’expression affectée.
 - Pour les tableaux, elle vérifie que la taille et le type des éléments sont cohérents.
 - Les conditions des structures de contrôle (`if`, `while`) doivent être des expressions booléennes valides.
 - Les instructions `return` sont vérifiées pour s’assurer que le type retourné correspond à celui attendu par la fonction.

Si une incohérence de type est détectée (par exemple, une addition entre un entier et une chaîne, ou un mauvais nombre d’arguments lors d’un appel de fonction), une exception `TypeError` est levée avec un message explicite. Cela permet d’arrêter la compilation et d’indiquer précisément l’erreur à l’utilisateur.

---

## Fonctions

Pour notre compilateur, nous avons adopté la convention d'appel **System V AMD64 ABI**.

### 1. Capacités Actuelles

#### A. Définition d’une fonction

Les fonctions peuvent être définies avec un type de retour, un nom unique et une liste de paramètres. Le corps est délimité par des accolades `{}`.

```c
int add(int a, int b) {
 int result = a + b;
 return(result);
}
```

#### B. Appels de fonctions

Les fonctions peuvent être appelées depuis `main` ou toute autre fonction. Les arguments sont passés entre parenthèses.

```c
int main() {
 // Appel de la fonction 'add' avec les arguments 3 et 5.
 int sum = add(3, 5);
 printf(sum); // Affiche 8
 return(0);
}
```

#### C. Paramètres

- **Passage par valeur** : Les types simples comme `int` sont passés par valeur. La fonction reçoit une copie, et les modifications dans la fonction n’affectent pas la variable d’origine.
- **Passage par référence (pour les tableaux)** : Les tableaux sont passés par référence. La fonction reçoit un pointeur vers le premier élément du tableau. Les modifications du contenu du tableau dans la fonction affecteront le tableau d’origine.
- **Limite de paramètres** : Jusqu’à 6 paramètres sont supportés, correspondant aux registres `rdi`, `rsi`, `rdx`, `rcx`, `r8` et `r9`.

```c
// 'arr' est un pointeur vers la mémoire du tableau original.
void modify_array(int[] arr) {
 arr[0] = 99;
}

int main() {
 int[1] my_arr = {0};
 modify_array(my_arr);
 printf(my_arr[0]); // Affiche 99
}
```

#### D. Valeurs de retour

- **Retour explicite** : Les fonctions peuvent utiliser l’instruction `return(expression);` pour sortir à tout moment et retourner une valeur.
- **Retour implicite** : Si une fonction atteint la fin de son corps sans `return` explicite, le comportement est indéfini (elle retournera probablement la dernière valeur présente dans le registre `rax`). Toutes les fonctions doivent inclure un `return` pour garantir un comportement prévisible.
- **Types de retour** : Seuls les types simples comme `int` et les pointeurs peuvent être retournés.

#### E. Récursivité

Les appels récursifs sont entièrement supportés, chaque appel disposant de sa propre pile pour les variables locales.

```c
int factorial(int n) {
 if (n <= 1) {
 return(1);
 }
 return(n * factorial(n - 1));
}
```

### 2. Limitations Connues

- **Pas de surcharge de fonction** : Deux fonctions ne peuvent pas avoir le même nom, même si elles ont des paramètres différents.
- **Pas de déclarations anticipées** : Une fonction doit être définie avant d’être appelée. Le compilateur ne supporte pas les prototypes à la manière du C.
- **Types de retour limités** : Les fonctions ne peuvent pas retourner des tableaux directement. Pour cela, il faut retourner un pointeur vers un tableau alloué sur le tas.
- **Pas de fonctions variadiques** : Les fonctions avec un nombre variable d’arguments (comme `printf` en C) ne peuvent pas être définies, seulement appelées.
- **Portée globale uniquement** : Les fonctions ne peuvent pas être définies à l’intérieur d’autres fonctions (pas de fonctions imbriquées).

### 3. Améliorations Potentielles

#### A. Déclarations anticipées (Prototypes)

- **Problème** : Actuellement, les fonctions doivent être définies dans un ordre "ascendant".
 ```c
 // Ceci échouera à la compilation car `bar` est appelé avant d’être défini.
 int foo() {
  return(bar());
 }
 int bar() {
  return(1);
 }
 ```
- **Amélioration** : Implémenter une stratégie de compilation en deux passes.
 1. **Passe 1 (Remplissage de la table des symboles)** : Parcourir le fichier et enregistrer les noms, types de paramètres et types de retour des fonctions dans une table des symboles globale, sans générer de code.
 2. **Passe 2 (Génération de code)** : Générer le code assembleur. Lorsqu’un appel de fonction est rencontré, sa signature est vérifiée via la table des symboles, même si le corps de la fonction n’a pas encore été compilé.

#### B. Support du type de retour `void`

- **Problème** : Chaque fonction doit actuellement avoir un type de retour comme `int`. Il n’existe pas de moyen d’indiquer qu’une fonction ne retourne rien.
- **Amélioration** :
 - Ajouter `void` comme `TYPE` dans la grammaire.
 - Dans `asm_function`, si le type de retour est `void`, s'assurer que les instructions `return` ne comportent pas d'expression (ex. `return;`).
 - L’épilogue de la fonction resterait identique, un `ret` étant toujours nécessaire.

#### C. Fonctions imbriquées (avancé)

- **Problème** : Toutes les fonctions existent au niveau global.
- **Amélioration** : Pour supporter les fonctions imbriquées, le compilateur devrait gérer les _closures_, ce qui implique :
 - Passer un "lien statique" (pointeur vers la pile de la fonction parente) comme paramètre caché à la fonction imbriquée.
 - Lorsqu’une fonction imbriquée accède à une variable de sa fonction parente, elle utiliserait ce lien statique pour retrouver le cadre de pile de la fonction parente et accéder à la variable.
 - C’est une fonctionnalité complexe à mettre en œuvre.

---

## Les `char ` et `char *`

Le programme-test si dessous illustre, en quelques lignes, l’ensemble des primitives que notre compilateur sait déjà transformer en assembleur : déclaration et affectation de caractères (char C = 'A') ; création d’une chaîne littérale et d’un pointeur vers celle-ci (char *S = "960BNK"), puis extraction d’un caractère individuel par indexation (t = S[3], soit le 'B' de « 960BNK ») ; concaténation de chaînes avec l’opérateur + (a = S + S, donnant « 960BNK960BNK ») ; appel des fonctions intégrées len (longueur = 6) et atoi (conversion ASCII→entier, donnant 960). Enfin, six appels successifs à printf démontrent la gestion automatique des formats : impression d’un caractère, d’une chaîne, d’un caractère extrait, d’une chaîne résultant d’une concaténation, puis d’un entier produit par len et d’un entier produit par atoi. 

```c
main() {
    char C = 'A';
    char *S="960BNK";
    char t;
    t = S[3];
    a= S+S;
    L=len(S);
    K=atoi(S);

    
    printf(C);
    printf(S);
    printf(t);
    printf(a);
    printf(L);
    printf(K)
    
}
```

Le compilateur est implémenté dans charCode.py ; ce script traduit le langage source en assembleur en s’appuyant sur le gabarit char_moule.asm, puis le code généré est appelé depuis la fonction main de char_main.c pour produire l’exécutable final.
Nous n’avons pas encore relié le type char aux fonctions ni aux tableaux : associer correctement le typage, la gestion d’adressage (char*), la pile d’appels et les offsets des arguments s’est révélé nettement plus ardu que prévu. En l’état, la logique qui pilote déjà les caractères simples et les chaînes devenait trop complexe pour rester cohérente avec le reste du projet ; nous avons donc choisi de stabiliser d’abord les opérations élémentaires (char, char*, concaténation, indexation) avant d’étendre le support aux paramètres de fonction et aux listes.

---

## Les Tableaux

### 1. Déclaration des tableaux

Deux formes de déclarations sont supportées dans la grammaire :

- **Sans initialisation** :

 ```c
 int[10] tab;
 ```

 Cette commande alloue dynamiquement un tableau de 10 cases d’entiers.

- **Avec initialisation** :
 ```c
 int[3] tab = {1, 2, 3};
 ```
 Cela crée un tableau de 3 cases initialisées avec les valeurs fournies.

L’analyseur syntaxique détecte ces formes via les règles de la grammaire. En backend, la mémoire est allouée dynamiquement avec un appel à `malloc`, et les cases sont initialisées si nécessaire.

### 2. Accès et affectation

Les tableaux peuvent être manipulés de deux manières principales :

- **Accès en lecture** :

 ```c
 x = tab[i];
 ```

 Correspond à un chargement de l’adresse de base du tableau, additionnée de l’offset `i * 8` (chaque entier étant codé sur 8 octets).

- **Accès en écriture** :
 ```c
 tab[i] = val;
 ```
 Génère du code assembleur qui calcule l’adresse de la i-ème case et y stocke la valeur.

### 3. Parcours avec des boucles

Une boucle `for` permet de parcourir facilement les tableaux :

```c
for (int i = 0; i < 10; i++) {
 printf(tab[i]);
}
```

Cette structure est reconnue par la grammaire et génère du code assembleur avec des sauts conditionnels (`jz`, `jmp`) pour répéter l’exécution d’un bloc. Pour l'instant, l’incrémentation `i++` est la seule opération supportée sur la variable de la boucle.

### 4. Génération de code assembleur

Le compilateur génère du code assembleur x86-64 à partir de l’AST. Pour les tableaux :

- L’adresse mémoire du tableau est stockée dans une variable (ex : `tab: dq 0`).
- Chaque accès effectue un calcul d’adresse en décalant l’index de 3 bits (`shl rcx, 3`), ce qui équivaut à une multiplication par 8 pour obtenir un offset en octets.
- L’initialisation avec des valeurs stocke chaque valeur dans la bonne case mémoire après l'allocation.

Exemple de code assembleur généré pour l'initialisation `int[3] tab = {1, 2, 3};` :

```nasm
; Allouer 3 * 8 = 24 octets
mov rdi, 3
shl rdi, 3
call malloc
mov [tab_pointer], rax ; Stocke l'adresse retournée par malloc

; Initialiser les valeurs
mov rbx, [tab_pointer] ; Charge l'adresse de base du tableau
mov rax, 1
mov [rbx + 0], rax ; tab[0] = 1
mov rax, 2
mov [rbx + 8], rax ; tab[1] = 2
mov rax, 3
mov [rbx + 16], rax ; tab[2] = 3
```

