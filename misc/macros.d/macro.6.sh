#silent
e       execute something
        TMPFILE=`mktemp ${EMCX_TMPDIR:-/tmp}/up.XXXXXX` || exit 1
        cat %b > $TMPFILE
        sh $TMPFILE > %b
