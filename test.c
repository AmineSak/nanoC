

int sum_array(int[10] arr) {
    int s = 0;
    for (int i = 0; i < 10; i++) {
        s = s + arr[i];
        printf(arr[i]);
    }
    return(s);
}

int fib(int n, int[10] memo) {
    if (n <= 1) { 
        return(n);
    }
    return(fib(n - 1, memo) + fib(n - 2, memo));
}

int main() {
    int[10] my_arr = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100};
    int total = sum_array(my_arr);
    
    if (total > 500) {
        printf(1);
    } else {
        printf(0);
    }

    
    printf(total);
    printf(fib(7, my_arr));
    return(0);
}