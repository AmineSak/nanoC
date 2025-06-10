int recurs(int n) {
    if (n <= 10) { 
        return(n);
    }
    return(n + recurs(n - 1));
}




int main() {
    int[6] tab = {1,2,4,5,6,8};
    for (int i = 0; i < 5; i++){
        int val = tab[i];
        printf(val);
    }
    
    return(0);      
}