#import <Foundation/Foundation.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    @autoreleasepool {
        NSDictionary *info = [[NSBundle mainBundle] infoDictionary];
        NSString *root = info[@"WhisprProjectRoot"];
        NSString *python = info[@"WhisprPython"];
        NSString *script = info[@"WhisprMainScript"];
        if (root.length == 0 || python.length == 0 || script.length == 0) {
            fputs("Whispr Local is missing its launch paths. Rebuild the app.\n", stderr);
            return 78;
        }
        if (chdir(root.fileSystemRepresentation) != 0) {
            perror("Whispr Local could not open its project folder");
            return 72;
        }
        char *const arguments[] = {(char *)python.fileSystemRepresentation,
                                   (char *)script.fileSystemRepresentation, NULL};
        execv(python.fileSystemRepresentation, arguments);
        perror("Whispr Local could not start Python");
        return 71;
    }
}
