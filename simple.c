
int fib(int n) {
    if (n <= 1) { 
        return(n);
    }
    return(fib(n - 1) + fib(n - 2));
}

int main(int x) {
    int result = fib(x);
    printf(result); 
    return(0);      
}