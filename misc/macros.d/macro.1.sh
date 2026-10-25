#silent
u       Upper case selection
        TMPFILE=`mktemp ${EMCX_TMPDIR:-/tmp}/up.XXXXXX` || exit 1
        cat %b > $TMPFILE
        cat $TMPFILE| sed 's/\(.*\)/\U\1/' >%b
        rm -f $TMPFILE
