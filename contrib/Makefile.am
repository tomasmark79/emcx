
noinst_DATA = README.xterm

SCRIPTS_IN = \
	emcx.csh.in \
	emcx.fish.in \
	emcx.sh.in \
	emcx-wrapper.csh.in \
	emcx-wrapper.fish.in \
	emcx-wrapper.sh.in
SCRIPTS_OUT = \
	emcx.csh \
	emcx.fish \
	emcx.sh \
	emcx-wrapper.csh \
	emcx-wrapper.fish \
	emcx-wrapper.sh

pkglibexec_SCRIPTS = $(SCRIPTS_OUT)

cfgdir = $(sysconfdir)/@PACKAGE@
cfg_DATA = \
	$(LIBFILES_ADD)

CLEANFILES = $(SCRIPTS_OUT)

# Files processed by configure don't need to be here
EXTRA_DIST = \
	$(SCRIPTS_IN) \
	$(noinst_DATA)

emcx.csh: $(top_builddir)/config.status $(srcdir)/emcx.csh.in
	$(SED) "s%@""pkglibexecdir@%$(pkglibexecdir)%" $(srcdir)/emcx.csh.in > emcx.csh

emcx.fish: $(top_builddir)/config.status $(srcdir)/emcx.fish.in
	$(SED) "s%@""pkglibexecdir@%$(pkglibexecdir)%" $(srcdir)/emcx.fish.in > emcx.fish

emcx.sh: $(top_builddir)/config.status $(srcdir)/emcx.sh.in
	$(SED) "s%@""pkglibexecdir@%$(pkglibexecdir)%" $(srcdir)/emcx.sh.in > emcx.sh

emcx-wrapper.csh: $(top_builddir)/config.status $(srcdir)/emcx-wrapper.csh.in
	$(SED) "s%@""bindir@%$(bindir)%" $(srcdir)/emcx-wrapper.csh.in > emcx-wrapper.csh

emcx-wrapper.fish: $(top_builddir)/config.status $(srcdir)/emcx-wrapper.fish.in
	$(SED) "s%@""bindir@%$(bindir)%" $(srcdir)/emcx-wrapper.fish.in > emcx-wrapper.fish

emcx-wrapper.sh: $(top_builddir)/config.status $(srcdir)/emcx-wrapper.sh.in
	$(SED) "s%@""bindir@%$(bindir)%" $(srcdir)/emcx-wrapper.sh.in > emcx-wrapper.sh

