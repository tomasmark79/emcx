m       make
        TMPFILE=`mktemp ${EMCX_TMPDIR:-/tmp}/up.XXXXXX` || exit 1
        make 2> $TMPFILE
        emcx-edit $TMPFILE
        rm $TMPFILE
