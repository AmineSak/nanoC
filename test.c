
int recurs(int n) {
    if (n <= 10) { 
        return(n);
    }
    return(n + recurs(n - 1));
}

int main() {
    int a = 12;
    int result = recurs(a);
    printf(result); 
    return(0);      
}