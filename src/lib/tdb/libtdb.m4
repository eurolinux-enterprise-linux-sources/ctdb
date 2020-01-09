dnl Check to see if we should use the included tdb

INCLUDED_TDB=auto
AC_ARG_WITH(included-tdb,
    [AC_HELP_STRING([--with-included-tdb], [use bundled tdb library, not from system])],
    [ INCLUDED_TDB=$withval ])

AC_SUBST(TDB_LIBS)
AC_SUBST(TDB_CFLAGS)

if test x"$INCLUDED_TDB" != x"yes" ; then
    AC_CHECK_HEADERS(tdb.h)
    AC_CHECK_LIB(tdb, tdb_transaction_write_lock_mark, [ TDB_LIBS="-ltdb" ])
    if test x"$ac_cv_header_tdb_h" = x"no" -o x"$ac_cv_lib_tdb_tdb_transaction_write_lock_mark" = x"no" ; then
        INCLUDED_TDB=yes
        TDB_CFLAGS=""
    else
        INCLUDED_TDB=no
    fi
fi

AC_MSG_CHECKING(whether to use included tdb)
AC_MSG_RESULT($INCLUDED_TDB)
if test x"$INCLUDED_TDB" != x"no" ; then
    dnl find the tdb sources. This is meant to work both for 
    dnl tdb standalone builds, and builds of packages using tdb
    tdbdir=""
    tdbpaths=". lib/tdb tdb ../tdb ../lib/tdb"
    for d in $tdbpaths; do
    	if test -f "$srcdir/$d/common/tdb.c"; then
    		tdbdir="$d"		
    		AC_SUBST(tdbdir)
    		break;
    	fi
    done
    if test x"$tdbdir" = "x"; then
       AC_MSG_ERROR([cannot find tdb source in $tdbpaths])
    fi
    TDB_OBJ="common/tdb.o common/dump.o common/transaction.o common/error.o common/traverse.o"
    TDB_OBJ="$TDB_OBJ common/freelist.o common/freelistcheck.o common/io.o common/lock.o common/open.o common/check.o common/hash.o common/summary.o common/rescue.o"
    AC_SUBST(TDB_OBJ)

    TDB_LIBS=""
    AC_SUBST(TDB_LIBS)

    TDB_CFLAGS="-I$tdbdir/include"
    AC_SUBST(TDB_CFLAGS)
fi

AC_CHECK_FUNCS(mmap pread pwrite getpagesize utime)
AC_CHECK_HEADERS(getopt.h sys/select.h sys/time.h)

AC_HAVE_DECL(pread, [#include <unistd.h>])
AC_HAVE_DECL(pwrite, [#include <unistd.h>])

if test x"$VERSIONSCRIPT" != "x"; then
    EXPORTSFILE=tdb.exports
    AC_SUBST(EXPORTSFILE)
fi
