#silent
w       delete trailing whitespace
        TMPFILE=`mktemp ${EMCX_TMPDIR:-/tmp}/up.XXXXXX` || exit 1
        cat %b > $TMPFILE
        cat $TMPFILE | sed 's/[ \t]*$//' > %b
