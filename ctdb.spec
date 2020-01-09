%global _hardened_build 1

%define initdir %{_sysconfdir}/rc.d/init.d
%define with_systemd 1

Summary: A Clustered Database based on Samba's Trivial Database (TDB)
Name: ctdb
Version: 2.5.1
Release: 2%{?dist}
License: GPLv3+
Group: System Environment/Daemons
URL: http://ctdb.samba.org/

Source0: https://ftp.samba.org/pub/ctdb/%{name}-%{version}.tar.gz

Requires: chkconfig coreutils psmisc
Requires: fileutils sed
Requires: tdb-tools
%if %{with_systemd}
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
%else
Requires(preun): chkconfig initscripts
Requires(post): chkconfig
Requires(postun): initscripts
%endif

BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: autoconf net-tools popt-devel
# For make check
BuildRequires: procps iproute

# Always use the bundled versions of these libraries.
%define with_included_talloc 0
%define with_included_tdb 0
%define with_included_tevent 0

# If the above options are changed then mandate minimum system
# versions.
%define libtalloc_version 2.0.8
%define libtdb_version 1.2.11
%define libtevent_version 0.9.18

%if ! %with_included_talloc
BuildRequires: libtalloc-devel >= %{libtalloc_version}
%endif
%if ! %with_included_tdb
BuildRequires: libtdb-devel >= %{libtdb_version}
%endif
%if ! %with_included_tevent
BuildRequires: libtevent-devel >= %{libtevent_version}
%endif


%description
CTDB is a cluster implementation of the TDB database used by Samba and other
projects to store temporary data. If an application is already using TDB for
temporary data it is very easy to convert that application to be cluster aware
and use CTDB instead.

%package devel
Group: Development/Libraries
Summary: CTDB clustered database development package
Requires: ctdb = %{version}-%{release}
Provides: ctdb-static = %{version}-%{release}
%description devel
Libraries, include files, etc you can use to develop CTDB applications.
CTDB is a cluster implementation of the TDB database used by Samba and other
projects to store temporary data. If an application is already using TDB for
temporary data it is very easy to convert that application to be cluster aware
and use CTDB instead.

%package tests
Summary: CTDB clustered database test suite
Group: Development/Tools
Requires: ctdb = %{version}
Requires: nc

%description tests
Test suite for CTDB.
CTDB is a cluster implementation of the TDB database used by Samba and other
projects to store temporary data. If an application is already using TDB for
temporary data it is very easy to convert that application to be cluster aware
and use CTDB instead.

#######################################################################

%prep
%setup -q
# setup the init script and sysconfig file
%setup -T -D -n ctdb-%{version} -q

%build

CC="gcc"

## always run autogen.sh
./autogen.sh

CFLAGS="$(echo '%{optflags}') $EXTRA -D_GNU_SOURCE -DCTDB_VERS=\"%{version}-%{release}\"" %configure \
%if %with_included_talloc
        --with-included-talloc \
%endif
%if %with_included_tdb
        --with-included-tdb \
%endif
%if %with_included_tevent
        --with-included-tevent
%endif

make showflags
make %{_smp_mflags}

# make test does not work in koji
#%check
#make test

%install
# Clean up in case there is trash left from a previous build
rm -rf %{buildroot}

# Create the target build directory hierarchy
mkdir -p %{buildroot}%{_sysconfdir}/sysconfig
mkdir -p %{buildroot}%{_sysconfdir}/sudoers.d
mkdir -p %{buildroot}%{initdir}

make DESTDIR=%{buildroot} install

make DESTDIR=%{buildroot} docdir=%{_docdir} install install_tests

install -m644 config/ctdb.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/ctdb

%if %{with_systemd}
mkdir -p %{buildroot}%{_unitdir}
install -m 755 config/ctdb.service %{buildroot}%{_unitdir}
%else
mkdir -p %{buildroot}%{initdir}
install -m755 config/ctdb.init %{buildroot}%{initdir}/ctdb
%endif

# create /run/ctdbd
mkdir -p %{buildroot}%{_tmpfilesdir}
echo "d /run/ctdb  755 root root" >> %{buildroot}%{_tmpfilesdir}/%{name}.conf

mkdir -p %{buildroot}/run
install -d -m 0755 %{buildroot}/run/ctdb/

install -d -m 0755 %{buildroot}%{_localstatedir}/lib/ctdb/

mkdir -p %{buildroot}%{_docdir}/ctdb/tests/bin
install -m755 tests/bin/ctdb_transaction %{buildroot}%{_docdir}/ctdb/tests/bin


# Remove "*.old" files
find %{buildroot} -name "*.old" -exec rm -f {} \;

cp -r COPYING web %{buildroot}%{_docdir}/ctdb

%clean
rm -rf %{buildroot}

%if %{with_systemd}
%post
%systemd_post ctdb.service

%preun
%systemd_preun ctdb.service

%postun
%systemd_postun_with_restart ctdb.service
%else
%post
/sbin/chkconfig --add ctdb

%preun
if [ "$1" -eq "0" ] ; then
 /sbin/service ctdb stop > /dev/null 2>&1
 /sbin/chkconfig --del ctdb
fi

%postun
if [ "$1" -ge "1" ]; then
 /sbin/service ctdb condrestart >/dev/null 2>&1 || true
fi
%endif

# Files section

%files
%defattr(-,root,root,-)

%config(noreplace) %{_sysconfdir}/sysconfig/ctdb
%config(noreplace) %{_sysconfdir}/ctdb/notify.sh
%config(noreplace) %{_sysconfdir}/ctdb/debug-hung-script.sh
%config(noreplace) %{_sysconfdir}/ctdb/ctdb-crash-cleanup.sh
%config(noreplace) %{_sysconfdir}/ctdb/gcore_trace.sh
%config(noreplace) %{_sysconfdir}/ctdb/functions
%config(noreplace) %{_sysconfdir}/ctdb/debug_locks.sh
%dir /run/ctdb/
%dir %{_localstatedir}/lib/ctdb/
%{_tmpfilesdir}/%{name}.conf

%if %{with_systemd}
%{_unitdir}/ctdb.service
%else
%attr(755,root,root) %{initdir}/ctdb
%endif

%{_docdir}/ctdb
%dir %{_sysconfdir}/ctdb
%{_sysconfdir}/ctdb/statd-callout
%dir %{_sysconfdir}/ctdb/nfs-rpc-checks.d
%{_sysconfdir}/ctdb/nfs-rpc-checks.d/10.statd.check
%{_sysconfdir}/ctdb/nfs-rpc-checks.d/20.nfsd.check
%{_sysconfdir}/ctdb/nfs-rpc-checks.d/30.lockd.check
%{_sysconfdir}/ctdb/nfs-rpc-checks.d/40.mountd.check
%{_sysconfdir}/ctdb/nfs-rpc-checks.d/50.rquotad.check
%{_sysconfdir}/sudoers.d/ctdb
%{_sysconfdir}/ctdb/events.d/
%{_sbindir}/ctdbd
%{_sbindir}/ctdbd_wrapper
%{_bindir}/ctdb
%{_bindir}/smnotify
%{_bindir}/ping_pong
%{_bindir}/ltdbtool
%{_bindir}/ctdb_diagnostics
%{_bindir}/onnode
%{_bindir}/ctdb_lock_helper

%{_mandir}/man1/ctdb.1.gz
%{_mandir}/man1/ctdbd.1.gz
%{_mandir}/man1/onnode.1.gz
%{_mandir}/man1/ltdbtool.1.gz
%{_mandir}/man1/ping_pong.1.gz

%files devel
%defattr(-,root,root,-)
%{_includedir}/ctdb.h
%{_includedir}/ctdb_client.h
%{_includedir}/ctdb_protocol.h
%{_includedir}/ctdb_private.h
%{_includedir}/ctdb_typesafe_cb.h
%{_libdir}/pkgconfig/ctdb.pc

%files tests
%defattr(-,root,root,-)
%dir %{_datadir}/%{name}-tests
%{_datadir}/%{name}-tests/*
%dir %{_libdir}/%{name}-tests
%{_libdir}/%{name}-tests/*
%{_bindir}/ctdb_run_tests
%{_bindir}/ctdb_run_cluster_tests
%doc tests/README

%changelog
* Fri Jan 24 2014 Daniel Mach <dmach@redhat.com> - 2.5.1-2
- Mass rebuild 2014-01-24

* Mon Jan 13 2014 Sumit Bose <sbose@redhat.com> - 2.5.1-1
- Update to ctdb version 2.5.1
- Resolves: rhbz#1040426

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 2.1-4
- Mass rebuild 2013-12-27

* Fri May 17 2013 Sumit Bose <sbose@redhat.com> - 2.1-3
- added _hardened_build to spec file
  Resolves: rhbz#955324

* Mon Mar 25 2013 Sumit Bose <sbose@redhat.com> - 2.1-2
- added updated patch files

* Mon Mar 25 2013 Sumit Bose <sbose@redhat.com> - 2.1-1
- Update to ctdb version  2.1
- added fix for tevent configure check
- make sure autogen.sh is called before configure
  Resolves: rhbz#925204

* Wed Feb 13 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2.39-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Wed Sep 05 2012 Václav Pavlín <vpavlin@redhat.com> - 1.2.39-5
- Scriptlets replaced with new systemd macros (#850072)

* Wed Aug 22 2012 Sumit Bose <sbose@redhat.com> - 1.2.39-4
- Add cleanups for systemd (#850861)

* Wed Jul 18 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2.39-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Wed Jun 06 2012 Sumit Bose <sbose@redhat.com> - 1.2.39-2
 - Add systemd fixes (#829235).

* Wed Feb 01 2012 Sumit Bose <sbose@redhat.com> - 1.2.39-1
 - Update to ctdb version 1.2.39
 - Added support for systemd

- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2.28-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Mon Jun 27 2011 Michael Schwendt <mschwendt@fedoraproject.org> - 1.2.28-2
- Provide virtual -static package to meet guidelines (#700029).

* Mon Apr 18 2011 Sumit Bose <sbose@redhat.com> - 1.2.28-1
 - Update to ctdb version 1.2.28

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.114-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Feb 08 2011 Sumit Bose <sbose@redhat.com> - 1.0.114-1
 - Changed $RPM_BUILD_ROOT to %{buildroot}
 - Update to ctdb version 1.0.114
 - Added patch to fix configure issue
 - Added assorted backport patches recommended by upstream developer

* Thu Jan 14 2010 Sumit Bose <sbose@redhat.com> - 1.0.113-1
 - Update to ctdb version 1.0.113

* Wed Jan 13 2010 : Version 1.0.113
 - Incorrect use of dup2() could cause ctdb to spin eating 100% cpu.

* Tue Jan 12 2010 : Version 1.0.112
  - Revert the use of wbinfo --ping-dc as it is proving too unreliable.
  - Minor testsuite changes.

* Fri Dec 18 2009 : Version 1.0.111
 - Fix a logging bug when an eventscript is aborted that could cause a crash.
 - Add back cb_status that was lost in a previous commit.

* Fri Dec 18 2009 : Version 1.0.110
 - Metxe: fix for filedescriptor leak in the new eventscript code.
 - Rusty: fix for a crash bug in the eventscript code.

* Thu Dec 17 2009 : Version 1.0.109
 - Massive eventscript updates. (bz58828)
 - Nice the daemon instead of using realtime scheduler, also use mlockall() to
   reduce the risk of blockign due to paging.
 - Workarounds for valgrind when forking once for each script. Valgrind
   consumes massive cpu when terminating the scripts on virtual systems.
 - Sync the tdb library with upstream, and use the new TDB_DISALLOW_NESTING
   flag.
 - Add new command "ctdb dumpdbbackup"
 - Start using the new tdb check framework to validate tdb files upon startup.
 - A new framework where we can control health for individual tdb databases.
 - Fix a crash bug in the logging code.
 - New transaction code for persistent databases.
 - Various other smaller fixes.

* Tue Dec 8 2009 Sumit Bose <sbose@redhat.com> - 1.0.108-1
 - Update to ctdb version 1.0.108
 - added fix for bz537223
 - added tdb-tools to Requires, fixes bz526479

* Wed Dec 2 2009 Sumit Bose <sbose@redhat.com> - 1.0.107-1
 - Update to ctdb version 1.0.107

* Wed Dec 2 2009 : Version 1.0.107
 - fix for rusty to solve a double-free that can happen when there are
   multiple packets queued and the connection is destroyed before
   all packets are processed.

* Tue Dec 1 2009 : Version 1.0.106
 - Buildscript changes from Michael Adam
 - Dont do a full recovery when there is a mismatch detected for ip addresses,
   just do a less disruptive ip-reallocation
 - When starting ctdbd, wait until all initial recoveries have finished
   before we issue the "startup" event.
   So dont start services or monitoring until the cluster has
   stabilized.
 - Major eventscript overhaul by Ronnie, Rusty and Martins and fixes of a few
   bugs found.

* Thu Nov 19 2009 : Version 1.0.105
 - Fix a bug where we could SEGV if multiple concurrent "ctdb eventscript ..."
   are used and some of them block.
 - Monitor the daemon from the syslog child process so we shutdown cleanly when
   the main daemon terminates.
 - Add a 500k line ringbuffer in memory where all log messages are stored.
 - Add a "ctdb getlog <level>" command to pull log messages from the in memory
   ringbuffer.
 - From martin : fixes to cifs and nfs autotests
 - from michael a : fix a bashism in 11.natgw

* Fri Nov 6 2009 : Version 1.0.104
 - Suggestion from Metze, we can now use killtcp to kill local connections
   for nfs so change the killtcp script to kill both directions of an NFS
   connection.
   We used to deliberately only kill one direction in these cases due to
   limitations.
 - Suggestion from christian Ambach, when using natgw, try to avoid using a
   UNHEALTHY node as the natgw master.
 - From Michael Adam: Fix a SEGV bug in the recent change to the eventscripts
   to allow the timeout to apply to each individual script.
 - fix a talloc bug in teh vacuuming code that produced nasty valgrind
   warnings.
 - From Rusty: Set up ulimit to create core files for ctdb, and spawned
   processes by default. This is useful for debugging and testing but can be
   disabled by setting CTDB_SUPRESS_COREFILE=yes in the sysconfig file.
 - Remove the wbinfo -t check from the startup check that winbindd is happy.
 - Enhance the test for bond devices so we also check if the sysadmin have
   disabled all slave devices using "ifdown".

* Tue Nov 3 2009 : Version 1.0.103
 - Dont use vacuuming on persistent databases
 - Michael A : transaction updates to persistent databases
 - Dont activate service automatically when installing the RPM. Leave this to
   the admin.
 - Create a child process to send all log messages to, to prevent a hung/slow
   syslogd from blocking the main daemon. In this case, discard log messages
   instead and let the child process block.
 - Michael A: updates to log messages

* Thu Oct 29 2009 : Version 1.0.102
 - Wolfgang: fix for the vacuuming code
 - Wolfgang: stronger tests for persistent database filename tests
 - Improve the log message when we refuse to startup since wbinfo -t fails
   to make it easier to spot in the log.
 - Update the uptime command output and the man page to indicate that
   "time since last ..." if from either the last recovery OR the last failover
 - Michael A: transaction updates

* Wed Oct 28 2009 : Version 1.0.101
 - create a separate context for non-monitoring events so they dont interfere
   with the monitor event
 - make sure to return status 0 in teh callback when we abort an event

* Wed Oct 28 2009 : Version 1.0.100
 - Change eventscript handling to allow EventScriptTimeout for each individual
   script instead of for all scripts as a whole.
 - Enhanced logging from the eventscripts, log the name and the duration for
   each script as it finishes.
 - Add a check to use wbinfo -t for the startup event of samba
 - TEMP: allow clients to attach to databases even when teh node is in recovery
   mode
 - dont run the monitor event as frequently after an event has failed
 - DEBUG: in the eventloops, check the local time and warn if the time changes
   backward or rapidly forward
 - From Metze, fix a bug where recovery master becoming unhealthy did not
   trigger an ip failover.
 - Disable the multipath script by default
 - Automatically re-activate the reclock checking if the reclock file is
   specified at runtime. Update manpage to reflect this.
 - Add a mechanism where samba can register a SRVID and if samba unexpectedly
   disconnects, a message will be broadcasted to all other samba daemons.
 - Log the pstree on hung scripts to a file in /tmp isntead of
   /var/log/messages
 - change ban count before unhealthy/banned to 10

* Thu Oct 22 2009 : Version 1.0.99
 - Fix a SEGV in the new db priority code.
 - From Wolfgang : eliminate a ctdb_fatal() if there is a dmaster violation
   detected.
 - During testing we often add/delete eventscripts at runtime. This could cause
   an eventscript to fail and mark the node unhealthy if an eventscript was
   deleted while we were listing the names. Handle the errorcode and make sure
   the node does not becomne unhealthy in this case.
 - Lower the debuglevel for the messages when ctdb creates a filedescruiptor so
   we dont spam the logs with these messages.
 - Dont have the RPM automatically restart ctdb
 - Volker : add a missing transaction_cancel() in the handling of persistent
   databases
 - Treat interfaces with the anme ethX* as bond devices in 10.interfaces so we
   do the correct test for if they are up or not.

* Tue Oct 20 2009 : Version 1.0.98
 - Fix for the vacuuming database from Wolfgang M
 - Create a directory where the test framework can put temporary overrides
   to variables and functions.
 - Wait a lot longer before shutting down the node when the reclock file
   is incorrectly configured, and log where it is configured.
 - Try to avoid running the "monitor" event when databases are frozen.
 - Add logging for every time we create a filedescriptor so we can trap
   fd leaks.

* Thu Oct 14 2009 : Version 1.0.97
 - From martins : update onnode.
   Update onnode to allow specifying an alternative nodes file from
   the command line and also to be able to specify hostnames on the
   list of targets :
   onnode host1,host2,...
* Wed Oct 14 2009 Sumit Bose <sbose@redhat.com> - 1.0.96-1
 - Update to ctdb version 1.0.96

* Tue Oct 13 2009 : Version 1.0.96
 - Add more debugging output when eventscripts have trouble. Print a
   "pstree -p" to the log when scripts have hung.
 - Update the initscript,  only print the "No reclock file used" warning
   when we do "service ctdb start", dont also print them for all other
   actions.
 - When changing between unhealthy/healthy state, push a request to the
   recovery master to perform an ip reallocation   instead of waiting for the
   recovery master to pull and check the state change.
 - Fix a bug in the new db-priority handling where a pre-.95 recovery master
   could no longer lock the databases on a post-.95 daemon.
 - Always create the nfs state directories during the "monitor" event.
   This makes it easier to configure and enable nfs at runtime.
 - From Volker, forward-port a simper deadlock avoiding patch from the 1.0.82
   branch. This is a simpler versionof the "db priority lock order" patch
   that went into 1.0.95, and will be kept for a few versions until samba
   has been updated to use the functionality from 1.0.95.

* Mon Oct 12 2009 : Version 1.0.95
 - Add database priorities. Allow samba to set the priority of databases
   and lock the databases in priority order during recovery
   to avoid a deadlock when samba locks one database then blocks indefinitely
   while waiting for the second databaso to become locked.
 - Be aggressive and ban nodes where the recovery transaction start call
   fails.

* Thu Oct 10 2009 : Version 1.0.94
 - Be very aggressive and quickly ban nodes that can not freeze their databases

* Tue Oct 8 2009 : Version 1.0.93
 - When adding an ip, make sure to update this assignment on all nodes
   so it wont show up as -1 on other nodes.
 - When adding an ip and immediately deleting it, it was possible that
   the daemon would crash accessing already freed memory.
   Readjust the memory hierarchy so the destructors are called in the right
   order.
 - Add a handshake to the recovery daemon to eliminate some rare cases where
   addip/delip might cause a recovery to occur.
 - updated onnode documenation from Martin S
 - Updates to the natgw eventscript to allow disabling natgw at runtime

* Fri Oct 2 2009 : Version 1.0.92
 - Test updates and merge from martin
 - Add notification for "startup"
 - Add documentation for notification
 - from martin, a fix for restarting vsftpd in the eventscript

* Wed Sep 29 2009 Sumit Bose <sbose@redhat.com> - 1.0.91-1
 - Update to ctdb version 1.0.91

* Tue Sep 29 2009 : Version 1.0.91
 - New vacuum and repack design from Wolgang Mueller.
 - Add a new eventscript 01.reclock that will first mark a node unhealthy and
   later ban the node if the reclock file can not be accessed.
 - Add machinereadable output to the ctdb getreclock command
 - merge transaction updates from Michael Adam
 - In the new banning code, reset the culprit count to 0 for all nodes that
   could successfully compelte a full recovery.
 - dont mark the recovery master as a ban culprit because a node in the cluster
   needs a recovery. this happens naturally when using ctdb recover command so
   dont make this cause a node to be banned.

* Wed Sep 23 2009 Sumit Bose <sbose@redhat.com> - 1.0.90-1
 - Update to ctdb version 1.0.90

* Sat Sep 12 2009 : Version 1.0.90
 - Be more forgiving for eventscripts that hang during startup
 - Fix for a banning bug in the new banning logic

* Thu Sep 3 2009 : Version 1.0.89
 - Make it possible to manage winbind independently of samba.
 - Add new prototype banning code
 - Overwrite the vsftpd state file instead of appending. This eliminates
   annoying errors in the log.
 - Redirect some iptables commands to dev null
 - From Michael A, explicitely set the broadcast when we takeover a public ip
 - Remove a reclock file check we no longer need
 - Skip any persistent database files ending in .bak

* Mon Aug 17 2009 Sumit Bose <sbose@redhat.com> - 1.0.88-1
 - Update to ctdb version 1.0.88

* Mon Aug 17 2009 : Version 1.0.88
 - Add a new state for eventscripts : DISABLED.
   Add two new commands "ctdb enablescript/disablescript" to enable/disable
   eventscripts at runtime.
 - Bugfixes for TDB from rusty.
 - Merge/Port changes from upstream TDB library by rusty.
 - Additional new tests from MartinS. Tests for stop/continue.
 - Initial patch to rework vacuuming/repacking process from Wolfgang Mueller.
 - Updates from Michael Adam for persistent writes.
 - Updates from MartinS to handle the new STOPPED bit in the test framework.
 - Make it possible to enable/disable the RECMASTER and LMASTER roles
   at runtime. Add two new commands
   "ctdb setlmasterrole/setrecmasterrole on/off"
 - Make it possible to enable/disable the natgw feature at runtime. Add
   the command "ctdb setnatgwstate on/off"

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.87-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Fri Jul 17 2009 Sumit Bose <sbose@redhat.com> - 1.0.87-1
 - Update to ctdb version 1.0.87

* Fri Jul 17 2009 : Version 1.0.87
 - Add a new event "stopped" that is called when a node is stopped.
 - Documentation of the STOPPED flag and the stop/continue commands
 - Make it possible to start a node in STOPPED mode.
 - Add a new node flag : STOPPED and commands "ctdb stop" "ctdb continue"
   These commands are similar to "diasble/enable" but will also remove the node
   from the vnnmap, while disable only fails all ip addresses over.
 - tests for NFS , CIFS by martins
 - major updates to the init script by martins
 - Send gratious arps with a 1.1 second stride instead of a 1 second stride to
   workaround interesting "features" of common linux stacks.
 - Various test enhancements from martins:
   - additional other tests
   - add tests for grat arp generation, ping during failover, ssh and failover
   - New/updated tcp tickle tests and supprot functions
   - provide better debugging when a test fails
   - make ctdbd restarts more reliable in the tests
   - update the "wait bar" to  make the wait progress in tests more obvious
   - various cleanups
 - when dispatching a message to a handler, make the message a real talloc
   object so that we can reparent the object in the tallic hierarchy.
 - document the ipreallocate command
 - Updates to enable/disable to use the ipreallocate command to block until the
   following ipreallocation has completed.
 - Update the main daemon and the tools to allow debug level to be a string
   instead of an integer.
 - Update the sysconfig file to show using string literals instead of numeric
   values for the debuglevels used.
 - If no debuglevel is specific, make "ctdb setdebug" show the available
   options.
 - When trying to allocate network packets, add explicit checks if the network
   transport has been shutdown before trying and failing, to make log messages
   easier to read. Add this extra check and logging to every plave packets are
   allocated.

* Wed Jul 1 2009 Sumit Bose <sbose@redhat.com> - 1.0.86-1
 - Update to ctdb version 1.0.86

* Tue Jun 30 2009 : Version 1.0.86
 - Do not access the reclock at all if VerifyRecoveryLock is zero, not even try
   to probe it.
 - Allow setting the reclock file as "", which means that no reclock file at
   all should be used.
 - Document that a reclock file is no longer required, but that it is
   dangerous.
 - Add a control that can be used to set/clear/change the reclock file in the
   daemon during runtime.
 - Update the recovery daemon to poll whether a reclock file should be sued and
   if so which file at runtime in each monitoring cycle.
 - Automatically disable VerifyRecoveryLock everytime a user changes the
   location of the reclock file.
 - do not allow the VerifyRecoveryLock to be set using ctdb setvar if there is
   no recovery lock file specified.
 - Add two commands "ctdb getreclock" and "ctdb setreclock" to modify the
   reclock file.

* Tue Jun 23 2009 : Version 1.0.85
 - From William Jojo : Dont use getopt on AIX
 - Make it possible to use "ctdb listnodes" also when the daemon is not running
 - Provide machinereadable output to "ctdb listnodes"
 - Dont list DELETED nodes in the ctdb listnodes output
 - Try to avoid causing a recovery for the average case when
   adding/deleting/moving an ip
 - When banning a node, drop the IPs on that node only and not all nodes.
 - Add tests for NFS and CIFS tickles
 - Rename 99.routing to 11.routing so it executes before NFS and LVS scripts
 - Increase the default timeout before we deem an unresponsive recovery daemon
   hung and shutdown
 - Reduce the reclock timout to 5 seconds
 - Spawn a child process in the recovery daemon ot check the reclock file to
   avoid blocking the process if the underlying filesystem is unresponsive
 - fix for filedescriptor leak when a child process timesout
 - Dont log errors if waitpid() returns -1
 - Onnode updates by Martins
 - Test and initscript cleanups from Martin S

* Fri Jun 5 2009 Sumit Bose <sbose@redhat.com> - 1.0.84-1
 - Update to ctdb version 1.0.84

* Tue Jun 2 2009 : Version 1.0.84
 - Fix a bug in onnode that could not handle dead nodes

* Tue Jun 2 2009 : Version 1.0.83
 - Document how to remove a ndoe from a running cluster.
 - Hide all deleted nodes from ctdb output.
 - Lower the loglevel on some eventscript related items
 - Dont queue packets to deleted nodes
 - When building initial vnnmap, ignode any nonexisting nodes
 - Add a new nodestate : DELETED that is used when deleting a node from an
   existing cluster.
 - dont remove the ctdb socket when shutting down. This prevents a race in the
   initscripts when restarting ctdb quickly after stopping it.
 - TDB nesting reworked.
 - Remove obsolete ipmux
 - From Flavio Carmo Junior: Add eventscript and documentation for ClamAV
   antivirus engine
 - From Sumit Bose: fix the regex in the test to handle the new ctdb
   statistics output that was recently added.
 - change the socket type we use for grauitious arps from the obsolete
   AF_INET/SOCK_PACKET to instead use PF_PACKET/SOCK_RAW.
 - Check return codes for some functions, from Sumit Bose, based on codereview
   by Jim Meyering.
 - Sumit Bose: Remove structure memeber node_list_file that is no longer used.
 - Sumit Bose: fix configure warning for netfilter.h
 - Updates to the webpages by Volker.
 - Remove error messages about missing /var/log/log.ctdb file from
   ctdb_diagnostics.sh from christian Ambach
 - Additional error logs if hte eventscript switching from dameon to client
   mode fails.
 - track how long it takes for ctdbd and the recovery daemon to perform the
   rec-lock fcntl() lock attemt and show this in the ctdb statistics output.

* Thu May 14 2009 Sumit Bose <sbose@redhat.com> - 1.0.82-1
 - Update to ctdb version 1.0.82

* Thu May 14 2009 : Version 1.0.82
 - Update the "ctdb lvsmaster" command to return -1 on error.
 - Add a -Y flag to "ctdb lvsmaster"
 - RHEL5 apache leaks semaphores when crashing. Add semaphore cleanup to the
   41.httpd eventscript and try to restart apache when it has crashed.
 - Fixes to some tests
 - Add a -o option to "onnode" which will redirect all stdout to a file for
   each of the nodes.
 - Add a natgw and a lvs node specifier to onnode so that we can use
   "onnode natgw ..."
 - Assign the natgw address to lo instead of the private network so it can also
   be used where private and public networks are the same.
 - Add GPL boilerplates to two missing scripts.
 - Change the natgw prefix NATGW_ to CTDB_NATGW_

* Fri May 8 2009 Sumit Bose <sbose@redhat.com> - 1.0.81-1
 - Update to ctdb version 1.0.81

* Fri May 8 2009 : Version 1.0.81
 - use smbstatus -np instead of smbstatus -n in the 50.samba eventscript
   since this avoids performing an expensive traverse on the locking and brlock
   databases.
 - make ctdb automatically terminate all traverse child processes clusterwide
   associated to a client application that terminates before the traversal is
   completed.
 - From Sumit Bose : fixes to AC_INIT handling.
 - From Michael Adam, add Tridge's "ping_pong" tool the the ctdb distro since
   this is very useful for testing the backend filesystem.
 - From Sumit bose, add support for additional 64 bit platforms.
 - Add a link from the webpage to Michael Adams SambaXP paper on CTDB.

* Fri May 1 2009 : Version 1.0.80
 - change init shutdown level to 01 for ctdb so it stops before any of the
   other services
 - if we can not pull a database from a remote node during recovery, mark that
   node as a culprit so it becomes banned
 - increase the loglevel when we volunteer to drop all ip addresses after
   beeing in recovery mode for too long. Make this timeout tuneable with
   "RecoveryDropAllIPs" and have it default to 60 seconds
 - Add a new flag TDB_NO_NESTING to the tdb layer to prevent nested
   transactions which ctdb does not use and does not expect. Have ctdb set this
   flag to prevent nested transactions from occuring.
 - dont unconditionally kill off ctdb and restrat it on "service ctdb start".
   Fail "service ctdb start" with an error if ctdb is already running.
 - Add a new tunable "VerifyRecoveryLock" that can be set to 0 to prevent the
   main ctdb daemon to verify that the recovery master has locked the reclock
   file correctly before allowing it to set the recovery mode to active.
 - fix a cosmetic bug with ctdb statistics where certain counters could become
   negative.

* Thu Apr 30 2009 Sumit Bose <sbose@redhat.com> - 1.0.79-2
 - fixed a ppc64 build issue

* Wed Apr 29 2009 Sumit Bose <sbose@redhat.com> - 1.0.79-1
 - Update to ctdb version 1.0.79

* Wed Apr 8 2009 : Version 1.0.79
 - From Mathieu Parent: add a ctdb pkgconfig file
 - Fix bug 6250
 - add a funciton remove_ip to safely remove an ip from an interface, taking
   care to workaround an issue with linux alias interfaces.
 - Update the natgw eventscript to use the safe remove_ip() function
 - fix a bug in the eventscript child process that would cause the socket to be
   removed.
 - dont verify nodemap on banned nodes during cluster monitoring
 - Update the dodgy SeqnumInterval to have ms resolution

* Tue Mar 31 2009 : Version 1.0.78
 - Add a notify mechanism so we can send snmptraps/email to external management
   systems when the node becomes unhealthy
 - include 11.natgw eventscript in thew install so that the NATGW feature works

* Tue Mar 31 2009 : Version 1.0.77
 - Update the 99.routing eventscript to also try to add the routes (back)
   during a releaseip event. Similar to the reasons why we must add addresses
   back during releaseip in 10.interfaces

* Wed Mar 24 2009 : Version 1.0.76
 - Add a debugging command "xpnn" which can print the pnn of the node even when
   ctdbd is not running.
 - Redo the NATGW implementation to allow multiple disjoing NATGW groups in the
   same cluster.

* Tue Mar 24 2009 : Version 1.0.75
 - Various updates to LVS
 - Fix a bug in the killtcp control where we did not set the port correctly
 - add a new "ctdb scriptstatus" command that shows the status of the
   eventrscripts.

* Mon Mar 16 2009 : Version 1.0.74
 - Fixes to AIX from C Cowan.
 - Fixes to ctdb_diagnostics so we collect correct GPFS data
 - Fixes to the net conf list command in ctdb_diagnostics
 - Check the static-routes file IFF it exists in ctdb_diagnostics

* Thu Mar 05 2009 Sumit Bose <sbose@redhat.com> - 1.0.73-1
 - Update to ctdb version 1.0.73

* Wed Mar 4 2009 : Version 1.0.73
 - Add possibility to disable the check of shares for NFS and Samba
 - From Sumit Bose, fix dependencies so make -j works

* Tue Feb 24 2009 Sumit Bose <sbose@redhat.com> - 1.0.72-3
 - fix a make -j dependency problem

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.72-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Wed Feb 18 2009 Sumit Bose <sbose@redhat.com> - 1.0.72-1
 - Update to ctdb version 1.0.72

* Wed Feb 18 2009 : Version 1.0.72
 - Updates to test scripts by martin s
 - Adding a COPYING file
 - Use netstat to check for services and ports and fallback to netcat
   only if netstat is unavailable.

* Thu Feb 17 2009 Sumit Bose <sbose@redhat.com> - 1.0.71-5
 - more fixed according to https://bugzilla.redhat.com/show_bug.cgi?id=459444

* Thu Feb 8 2009 Sumit Bose <sbose@redhat.com> - 1.0.71-4
 - added upstream patch with license file

* Thu Feb 6 2009 Sumit Bose <sbose@redhat.com> - 1.0.71-3
 - fixed package according to https://bugzilla.redhat.com/show_bug.cgi?id=459444

* Thu Feb 5 2009 Guenther Deschner <gdeschner@redhat.com> - 1.0.71-2
 - Update to ctdb version 1.0.71

* Sun Feb 01 2009 : Version 1.0.71
 - Additional ipv6 fixes from Michael Adams

* Thu Jan 15 2009 : Version 1.0.70
 - IPv6 support is completed. this is backward compatible with ipv4-only
   systems. To use IPv6 with samba and ctdb you need current GIT of samba 3.3
   or michael adams samba-ctdeb branch.
 - Many enhancements to the build system and scripts to make it more SUSE
   friendly by Michael Adams.
 - Change of how the naming of the package is structured. We are now
   using "1.0.70" as a release and "-1" as the revision instead of as
   previously using "1.0" as release and ".70" as the revision.
   By Michael Adams.

* Wed Dec 17 2008 : Version 1.0.69
 - Various fixes to scripts by M Adam
 - Dont call ctdb_fatal() when the transport is down during shutdown

* Thu Dec 11 2008 : Version 1.0.68
 - Fixes for monitoring of interfaces status from Michael Adam.
 - Use -q instead of >/dev/null for grep to enhance readability of the
   scripts from Michael Adam.
 - Update to the "ctdb recover" command. This command now block until the
   has completed. This makes it much easier to use in scripts and avoids
   the common workaround :
      ctdb recover
      ... loop while waiting for recovery completes ...
      continue ...
 - Add a CTDB_TIMEOUT variable. If set, this variable provides an automatic
   timeout for "ctdb <command>", similar to using -T <timeout>
 - Set a unique errorcode for "ctdb <command>" when it terminates due to a
   timeout so that scripts can distinguish between a hung command and what was
   just a failure.
 - Update "ctdb ban/unban" so that if the cluster is in recovery these commands
   blocks and waits until after recovery is complete before the perform the
   ban/unban operation. This is necessary since the recovery process can cause
   nodes to become automatically unbanned.
 - Update "ctdb ban/unban" to block until the recovery that will follow shortly
   after this command has completed.
   This makes it much easier to use in scripts and avoids the common
   workaround :
      ctdb ban/unban
      ... loop while waiting for recovery completes ...
      continue ...
 - Bugfix for the new flags handling in 1.0.67. Abort and restart monitoring
   if we failed to get proper nodemaps from a remote node instead of
   dereferencing a null pointer.
 - If ctdbd was explicitely started with the '--socket' argument, make
   ctdbd automatically set CTDB_SOCKET to the specified argument.
   This ensures that eventscripts spawned by the ctdb daemon will default to
   using the same socket and talk to the correct daemon.
   This primarily affects running multiple daemons on the same host and where
   you want each instance of ctdb daemons have their eventscripts talk to the
   "correct" daemon.
 - Update "ctdb ping" to return an error code if the ping fail so that it
   can be used in scripts.
 - Update to how to synchronize management of node flags across the cluster.

* Tue Dec 02 2008 : Version 1.0.67
 - Add a document describing the recovery process.
 - Fix a bug in "ctdb setdebug" where it would refuse to set a negative
   debug level.
 - Print the list of literals for debug names if an invalid one was given
   to "ctdb setdebug"
 - Redesign how "ctdb reloadnodes" works and reduce the amont of tcp teardowns
   used during this event.
 - Make it possible to delete a public ip from all nodes at once using
   "ctdb delip -n all"

* Sun Nov 23 2008 : Version 1.0.66
 - Allow to change the recmaster even when we are not frozen.
 - Remove two redundant SAMBA_CHECK variables from the sysconf example
 - After a node failure it can take very long before some lock operations
   ctdb needs to perform are allowed/works with gpfs again. Workaround this
   by treating a hang/timeout as success.
 - Dont override CTDB_BASE is fet in the shell already
 - Always send keepalive packets regardless of whether the link is idle or not.
 - Rewrite the disable/enable flag update logic to prevent a race between
   "ctdb disable/enable" and the recovery daemon when updating the flags to
   all nodes.

* Wed Nov 12 2008 : Version 1.0.65
 - Update the sysconfig example: The default debug level is 2 (NOTICE) and not
   0 (ERROR)
 - Add support for a CTDB_SOCKET environment variable for the ctdb command
   line tool. If set, this overrides the default socket the ctdb tool will
   use.
 - Add logging of high latency operations.

* Tue Oct 21 2008 : Version 1.0.64
 - Add a context and a timed event so that once we have been in recovery for
   too long we drop all public addresses.

* Sun Oct 19 2008 : Version 1.0.63
 - Remove logging of "periodic cleanup ..." in 50.samba
 - When we reload a nodes file, we must detect this and reload the file also
   in the recovery daemon before we try to dereference somethoung beyond the end
   of the nodes array.

* Wed Oct 15 2008 : Version 1.0.62
 - Allow multiple eventscritps using the same prefix number.
   It is undefined which order scripts with the same prefix will execute in.

* Tue Oct 14 2008 : Version 1.0.61
 - Use "route add -net" instead of "ip route add" when adding routes in 99.routing
 - lower the loglevel os several debug statements
 - check the status returned from ctdb_ctrl_get_tickles() before we try to
   print them out to the screen.
 - install a new eventscript 20.multipathd whoich can be used to monitor that
   multipath devices are healthy

* Tue Oct 14 2008 : Version 1.0.60
 - Verify that nodes we try to ban/unban are reachable and print an error othervise.
 - Update the client and server sides of TAKEIP/RELEASEIP/GETPUBLICIPS and
   GETNODEMAP to fall back to the old style ipv4-only controls if the new
   ipv4/ipv6 controls fail. This allows an ipv4/v6 enabled ctdb daemon to
   interoperate with earlier ipv4-only versions of the daemons.
 - From Mathieu Parent : log debian systems log the package versions in ctdb
   diagnostics
 - From Mathieu Parent : specify logdir location for debian (this patch was
   later reversed)
 - From Michael Adams : allow # comments in nodes/public_addresses files

* Mon Oct 06 2008 : Version 1.0.59
 - Updated "reloadnodes" logic. Instead of bouncing the entire tcp layer it is
  sufficient to just close and reopen all outgoing tcp connections.
 - New eventscript 99.routing which can be used to re-attach routes to public
   interfaces after a takeip event. (routes may be deleted by the kernel when we
   release an ip)
 - IDR tree fix from Jim Houston
 - Better handling of critical events if the local clock is suddenly changed
   forward by a lot.
 - Fix three slow memory leaks in the recovery daemon
 - New ctdb command : ctdb recmaster   which prints the pnn of the recmaster
 - Onnode enhancements from Martin S : "healthy" and "connected" are now
   possible nodespecifiers
 - From Martin S : doc fixes
 - lowering some debug levels for some nonvital informational messages
 - Make the daemon daemon monitoring stronger and allow ctdbd to detect a hung
   recovery daemon.
 - From C Cowan : patches to compile ipv6 under AIX
 - zero out some structs to keep valgrind happy

* Mon Sep 8 2008 Abhijith Das <adas@redhat.com> - 1.0.58-1
 - This release repackages upstream's version 1.0.58 for fedora

* Wed Aug 27 2008 : Version 1.0.58
 - revert the name change tcp_tcp_client back to tcp_control_tcp so
   samba can build.
 - Updates to the init script from Abhijith Das <adas@redhat.com>

* Mon Aug 25 2008 : Version 1.0.57
 - initial support for IPv6

* Mon Aug 11 2008 : Version 1.0.56
 - fix a memory leak in the recovery daemon.

* Mon Aug 11 2008 : Version 1.0.55
 - Fix the releaseip message we seond to samba.

* Fri Aug 8 2008 : Version 1.0.54
 - fix a looping error in the transaction code
 - provide a more detailed error code for persistent store errors
   so clients can make more intelligent choices on how to try to recover

* Thu Aug 7 2008 : Version 1.0.53
 - Remove the reclock.pnn file   it can cause gpfs to fail to umount
 - New transaction code

* Mon Aug 4 2008 : Version 1.0.52
 - Send an explicit gratious arp when starting sending the tcp tickles.
 - When doing failover, issue a killtcp to non-NFS/non-CIFS clients
   so that they fail quickly. NFS and CIFS already fail and recover
   quickly.
 - Update the test scripts to handle CTRL-C to kill off the test.

* Mon Jul 28 2008 : Version 1.0.51
 - Strip off the vlan tag from bond devices before we check in /proc
   if the interface is up or not.
 - Use testparm in the background in the scripts to allow probing
   that the shares do exist.
 - Fix a bug in the logging code to handle multiline entries better
 - Rename private elements from private to private_data

* Fri Jul 18 2008 : Version 1.0.50
 - Dont assume that just because we can establish a TCP connection
   that we are actually talking to a functioning ctdb daemon.
   So dont mark the node as CONNECTED just because the tcp handshake
   was successful.
 - Dont try to set the recmaster to ourself during elections for those
   cases we know this will fail. To remove some annoying benign but scary
   looking entries from the log.
 - Bugfix for eventsystem for signal handling that could cause a node to
   hang.

* Thu Jul 17 2008 : Version 1.0.49
 - Update the safe persistent update fix to work with unpatched samba
   servers.

* Thu Jul 17 2008 : Version 1.0.48
 - Update the spec file.
 - Do not start new user-triggered eventscripts if we are already
   inside recovery mode.
 - Add two new controls to start/cancel a persistent update.
   A client such as samba can use these to tell ctdbd that it will soon
   be writing directly to the persistent database tdb file. So if
   samba is -9ed before it has eitehr done the persistent_store or
   canceled the operation, ctdb knows that the persistent databases
   'may' be out of sync and therefore a full blown recovery is called for.
 - Add two new options :
   CTDB_SAMBA_SKIP_CONF_CHECK and CTDB_SAMBA_CHECK_PORTS that can be used
   to override what checks to do when monitoring samba health.
   We can no longer use the smbstatus, net or testparm commands to check
   if samba or its config is healthy since these commands may block
   indefinitely and thus can not be used in scripts.

* Fri Jul 11 2008 : Version 1.0.47
 - Fix a double free bug where if a user striggered (ctdb eventscript)
   hung and while the timeout handler was being processed a new user
   triggered eventscript was started we would free state twice.
 - Rewrite of onnode and associated documentation.

* Thu Jul 10 2008 : Version 1.0.46
 - Document both the LVS:cingle-ip-address and the REMOTE-NODE:wan-accelerator
   capabilities.
 - Add commands "ctdb pnn", "ctdb lvs", "ctdb lvsmaster".
 - LVS improvements. LVS is the single-ip-address mode for a ctdb cluster.
 - Fixes to supress rpmlint warnings
 - AXI compile fixes.
 - Change \s to [[:space:]] in some scripts. Not all RHEL5 packages come
   with a egrep that handles \s   even same version but different arch.
 - Revert the change to NFS restart. CTDB should NOT attempt to restart
   failed services.
 - Rewrite of the waitpid() patch to use the eventsystem for handling
   signals.

* Tue Jul 8 2008 : Version 1.0.45
 - Try to restart the nfs service if it has failed to respond 3 times in a row.
 - waitpid() can block if the child does not respond promptly to SIGTERM.
   ignore all SIGCHILD signals by setting SIGCHLD to SIG_DEF.
   get rid of all calls to waitpid().
 - make handling of eventscripts hanging more liberal.
   only consider the script to have failed and making the node unhealthy
   IF the eventscript terminated wiht an error
   OR the eventscript hung 5 or more times in a row

* Mon Jul 7 2008 : Version 1.0.44
 - Add a CTDB_VALGRIND option to /etc/sysconfig/ctdb to make it start
   ctdb under valgrind. Logs go to /var/log/ctdb_valgrind.PID
 - Add a hack to show the control opcode that caused uninitialized data
   in the valgrind output by encoding the opcode as the line number.
 - Initialize structures and allocated memory in various places in
   ctdb to make it valgrind-clean and remove all valgrind errors/warnings.
 - If/when we destroy a lockwait child, also make sure we cancel any pending transactions
 - If a transaction_commit fails, delete/cancel any pending transactions and
   return an error instead of calling ctdb_fatal()
 - When running ctdb under valgrind, make sure we run it with --nosetsched and also
   ensure that we do not use mem-mapped i/o when accessing the tdb's.
 - zero out ctdb->freeze_handle when we free/destroy a freeze-child.
   This prevent a heap corruption/ctdb crash bug that could trigger
   if the freeze child times out.
 - we dont need to explicitely thaw the databases from the recovery daemon
   since this is done implicitely when we restore the recovery mode back to normal.
 - track when we start and stop a recovery. Add the 'time it took to complete the
   recovery' to the 'ctdb uptime' output.
   Ensure by tracking the start/stop recovery timestamps that we do not
   check that the ip allocation is consistend from inside the recovery daemon
   while a different node (recovery master) is performing a recovery.
   This prevent a race that could cause a full recovery to trigger if the
   'ctdb disable/enable' commands took very long.
 - The freeze child indicates to the master daemon that all databases are locked
   by writing data to the pipe shared with the master daemon.
   This write sometimes fail and thus the master daemon never notices that the databases
   are locked cvausing long timeouts and extra recoveries.
   Check that the write is successful and try the write again if it failed.
 - In each node, verify that the recmaster have the right node flags for us
   and force a push of our flags to the recmaster if wrong.

* Tue Jul 1 2008 : Version 1.0.43
 - Updates and bugfixes to the specfile to keep rpmlint happy
 - Force a global flags update after each recovery event.
 - Verify that the recmaster agrees with our node flags and update the
   recmaster othervise.
 - When writing back to the parent from a freeze-child across the pipe,
   loop over the write in case the write failed with an error  othervise
   the parent will never be notified tha the child has completed the operation.
 - Automatically thaw all databases when recmaster marks us as being in normal
   mode instead of recovery mode.

* Fri Jun 13 2008 : Version 1.0.42
 - When event scripts have hung/timedout more than EventScriptBanCount times
   in a row the node will ban itself.
 - Many updates to persistent write tests and the test scripts.

* Wed May 28 2008 : Version 1.0.41
 - Reactivate the safe writes to persistent databases and solve the
   locking issues. Locking issues are solved the only possible way,
   by using a child process to do the writes.  Expensive and slow but... .

* Tue May 27 2008 : Version 1.0.40
 - Read the samba sysconfig file from the 50.samba eventscript
 - Fix some emmory hierarchical bugs in the persistent write handling

* Thu May 22 2008 : Version 1.0.39
 - Moved a CTDB_MANAGES_NFS, CTDB_MANAGES_ISCSI and CTDB_MANAGES_CSFTPD
   into /etc/sysconfig/ctdb
 - Lowered some debug messages to not fill the logfile with entries
   that normally occur in the default configuration.

* Fri May 16 2008 : Version 1.0.38
 - Add machine readable output support to "ctdb getmonmode"
 - Lots of tweaks and enhancements if the event scripts are "slow"
 - Merge from tridge: an attempt to break the chicken-and-egg deadlock that
   net conf introduces if used from an eventscript.
 - Enhance tickles so we can tickle an ipv6 connection.
 - Start adding ipv6 support : create a new container to replace sockaddr_in.
 - Add a checksum routine for ipv6/tcp
 - When starting up ctdb, let the init script do a tdbdump on all
   persistent databases and verify that they are good (i.e. not corrupted).
 - Try to use "safe transactions" when writing to a persistent database
   that was opened with the TDB_NOSYNC flag. If we can get the transaction
   thats great, if we cant  we have to write anyway since we cant block here.

* Mon May 12 2008 : Version 1.0.37
 - When we shutdown ctdb we close the transport down before we run the
   "shutdown" eventscripts. If ctdb decides to send a packet to a remote node
   after we have shutdown the transport but before we have shutdown ctdbd
   itself this could lead to a SEGV instead of a clean shutdown. Fix.
 - When using the "exportfs" command to extract which NFS export directories
   to monitor,  exportfs violates the "principle of least surprise" and
   sometimes report a single export line as two lines of text output
   causing the monitoring to fail.

* Fri May 9 2008 : Version 1.0.36
 - fix a memory corruption bug that could cause the recovery daemon to crash.
 - fix a bug with distributing public ip addresses during recovery.
   If the node that is the recovery master did NOT use public addresses,
   then it assumed that no other node in the cluster used them either and
   thus skipped the entire step of reallocating public addresses.

* Wed May 7 2008 : Version 1.0.35
 - During recovery, when we define the new set of lmasters (vnnmap)
   only consider those nodes that have the can-be-lmaster capability
   when we create the vnnmap. unless there are no nodes available which
   supports this capability in which case we allow the recmaster to
   become lmaster capable (temporarily).
 - Extend the async framework so that we can use paralell async calls
   to controls that return data.
 - If we do not have the "can be recmaster" capability, make sure we will
   lose any recmaster elections, unless there are no nodes available that
   have the capability, in which case we "take/win" the election anyway.
 - Close and reopen the reclock pnn file at regular intervals.
   Make it a non-fatal event if we occasionally fail to open/read/write
   to this file.
 - Monitor that the recovery daemon is still running from the main ctdb
   daemon and shutdown the main daemon when recovery daemon has terminated.
 - Add a "ctdb getcapabilities" command to read the capabilities off a node.
 - Define two new capabilities : can be recmaster and can be lmaster
   and default both capabilities to YES.
 - Log denied tcp connection attempts with DEBUG_ERR and not DEBUG_WARNING

* Thu Apr 24 2008 : Version 1.0.34
 - When deleting a public ip from a node, try to migrate the ip to a different
   node first.
 - Change catdb to produce output similar to tdbdump
 - When adding a new public ip address, if this ip does not exist yet in
   the cluster, then grab the ip on the local node and activate it.
 - When a node disagrees with the recmaster on WHO is the recmaster, then
   mark that node as a recovery culprit so it will eventually become
   banned.
 - Make ctdb eventscript support the -n all argument.

* Thu Apr 10 2008 : Version 1.0.33
 - Add facilities to include site local adaptations to the eventscript
   by /etc/ctdb/rc.local which will be read by all eventscripts.
 - Add a "ctdb version" command.
 - Secure the domain socket with proper permissions from Chris Cowan
 - Bugfixes for AIX from Chris Cowan

* Wed Apr 02 2008 : Version 1.0.32
 - Add a control to have a node execute the eventscripts with arbitrary
   command line arguments.
 - Add a control "rddumpmemory" that will dump the talloc memory allocations
   for the recovery daemon.
 - Decorate the talloc memdump to produce better and easier memory leak
   tracking.
 - Update the RHEL5 iscsi tgtd scripts to allow one iscsi target for each
   public address.
 - Add two new controls "addip/delip" that can be used to add/remove public
   addresses to a node at runtime. After using these controls a "ctdb recover"
   ir required to make the changes take.
 - Fix a couple of slow memory leaks.

* Tue Mar 25 2008 : Version 1.0.31
 - Add back controls to disable/enable monitoring on a node.
 - Fix a memory leak where we used to attach CALL data to the ctdb structure
   when performing a local call. Memory which would be lost if the call was
   aborted.
 - Reduce the loglevel for the log output when someone connects to a non
   public ip address for samba.
 - Redo and optimize the vacuuming process to send only one control to each
   other node containing all records to be vacuumed instead of one
   control per node per record.

* Tue Mar 04 2008 : Version 1.0.30
 - Update documentation cor new commands and tuneables
 - Add machinereadable output to the ip,uptime and getdebug commands
 - Add a moveip command to manually failover/failback public ips
 - Add NoIPFallback tuneable that prevents ip address failback
 - Use file locking inside the CFS as alternative to verify when other nodes
   Are connected/disconnected to be able to recover from split network
 - Add DisableWhenUnhealthy tunable
 - Add CTDB_START_AS_DISABLED sysconfig param
 - Add --start-as-disabled flag to ctdb
 - Add ability to monitor for OOM condition

* Thu Feb 21 2008 : Version 1.0.29
 - Add a new command to make expansion of an existing cluster easier
 - Fix bug with references to freed objects in the ctdb structure
 - Propagate debuglevel changes to the recovery daemon
 - Merge patches to event scripts from Mathieu Parent :
 - MP: Simulate "service" on systems which do not provide this tool
 - MP: Set correct permissions for events.d/README
 - Add nice helper functions to start/stop nfs from the event scripts

* Fri Feb 08 2008 : Version 1.0.28
 - Fix a problem where we tried to use ethtool on non-ethernet interfaces
 - Warn if the ipvsadm packege is missing when LVS is used
 - Dont use absolute pathnames in some of the event scripts
 - Fix for persistent tdbs growing inifinitely.

* Wed Feb 06 2008 : Version 1.0.27
 - Add eventscript for iscsi

* Thu Jan 31 2008 : Version 1.0.26
 - Fix crashbug in tdb transaction code

* Tue Jan 29 2008 : Version 1.0.25
 - added async recovery code
 - make event scripts more portable
 - fixed ctdb dumpmemory
 - more efficient tdb allocation code
 - improved machine readable ctdb status output
 - added ctdb uptime

* Wed Jan 16 2008 : Version 1.0.24
 - added syslog support
 - documentation updates

* Wed Jan 16 2008 : Version 1.0.23
 - fixed a memory leak in the recoveryd
 - fixed a corruption bug in the new transaction code
 - fixed a case where an packet for a disconnected client could be processed
 - added http event script
 - updated documentation

* Thu Jan 10 2008 : Version 1.0.22
 - auto-run vacuum and repack ops

* Wed Jan 09 2008 : Version 1.0.21
 - added ctdb vacuum and ctdb repack code

* Sun Jan 06 2008 : Version 1.0.20
 - new transaction based recovery code

* Sat Jan 05 2008 : Version 1.0.19
 - fixed non-master bug
 - big speedup in recovery for large databases
 - lots of changes to improve tdb and ctdb for high churn databases

* Thu Dec 27 2007 : Version 1.0.18
 - fixed crash bug in monitor_handler

* Tue Dec 04 2007 : Version 1.0.17
 - fixed bugs related to ban/unban of nodes
 - fixed a race condition that could lead to monitoring being permanently disabled,
   which would lead to long recovery times
 - make deterministic IPs the default
 - fixed a bug related to continuous recovery
 - added a debugging option --node-ip
