#include <stdio.h>

int main(void) {
    char buffer[256];
    if (!fgets(buffer, sizeof(buffer), stdin)) {
        return 2;
    }
    fputs(buffer, stdout);
    return 0;
}
