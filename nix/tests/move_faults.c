/* Test-only fault injection: a filesystem that rejects ext2 attributes.
 * Used exclusively by isolated TUI sessions; never loaded by installed MC.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int
in_directory (const char *path, const char *variable)
{
    const char *directory = getenv (variable);
    size_t length = directory == NULL ? 0 : strlen (directory);

    return length != 0 && strncmp (path, directory, length) == 0 && path[length] == '/';
}

int
fgetflags (const char *path, unsigned long *flags)
{
    int (*original) (const char *, unsigned long *) = dlsym (RTLD_NEXT, "fgetflags");

    if (in_directory (path, "EMCX_TEST_MOVE_SOURCE"))
    {
        *flags = 0;
        return 0;
    }
    return original (path, flags);
}

int
fsetflags (const char *path, unsigned long flags)
{
    int (*original) (const char *, unsigned long) = dlsym (RTLD_NEXT, "fsetflags");

    if (in_directory (path, "EMCX_TEST_MOVE_TARGET"))
    {
        FILE *log = fopen (getenv ("EMCX_TEST_MOVE_LOG"), "a");
        if (log != NULL)
        {
            fputs ("fsetflags: EOPNOTSUPP\n", log);
            fclose (log);
        }
        errno = EOPNOTSUPP;
        return -1;
    }
    return original (path, flags);
}

ssize_t
read (int fd, void *buffer, size_t count)
{
    ssize_t (*original) (int, void *, size_t) = dlsym (RTLD_NEXT, "read");
    char link[64], path[PATH_MAX];
    ssize_t length;

    snprintf (link, sizeof (link), "/proc/self/fd/%d", fd);
    length = readlink (link, path, sizeof (path) - 1);
    if (length >= 0)
    {
        path[length] = '\0';
        if (in_directory (path, "EMCX_TEST_MOVE_SOURCE"))
            usleep (50000);
    }
    return original (fd, buffer, count);
}
