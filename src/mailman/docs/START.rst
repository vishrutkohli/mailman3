.. _start-here:

================================
Getting started with GNU Mailman
================================

Copyright (C) 2008-2015 by the Free Software Foundation, Inc.


Beta Release
============

This is a beta release.  The developers believe it has sufficient
functionality to provide full mailing list services, but it is not yet ready
for production use.

The Mailman 3 beta releases are being provided to give developers and other
interested people an early look at the next major version, and site
administrators a chance to prepare for an eventual upgrade.  The core list
management and post distribution functionality is now complete.  However,
unlike Mailman 2 whose web interface and archives were tightly integrated with
the core, Mailman 3 exposes a REST administrative interface to the web,
communicates with archivers via decoupled interfaces, and leaves summary,
search, and retrieval of archived messages to a separate application (a simple
implementation is provided).  The web interface (known as `Postorius`_) and
archiver (known as `Hyperkitty`_) are developed separately.


Contact Us
==========

Contributions of code, problem reports, and feature requests are welcome.
Please submit bug reports on the Mailman bug tracker at
https://bugs.launchpad.net/mailman (you need to have a login on Launchpad to
do so).  You can also send email to the mailman-developers@python.org mailing
list, or ask on IRC channel ``#mailman`` on Freenode.


Requirements
============

Python 3.4 or newer is required.  It can either be the default 'python3' on
your ``$PATH`` or it can be accessible via the ``python3.4`` binary.  If your
operating system does not include Python, see http://www.python.org for
information about downloading installers (where available) and installing it
from source (when necessary or preferred).  Python 2 is not supported.

You may need some additional dependencies, which are either available from
your OS vendor, or can be downloaded automatically from the `Python
Cheeseshop`_.


Documentation
=============

The documentation for Mailman 3 is distributed throughout the sources.
The core documentation (such as this file, ``START.rst``) is found in
the ``src/mailman/docs`` directory, but much of the documentation is
in module-specific places.  A prebuilt HTML version of `Mailman 3
documentation`_ is available at pythonhosted.org, as is `Postorius
documentation`_.  `HyperKitty documentation`_ is available at ReadTheDocs.

The `Development Setup Guide`_ is a recent step-by-step explanation of
how to set up a complete Mailman 3 system including the Mailman 3 core
and basic client API, Postorius, and HyperKitty.

Testing Mailman 3
=================

To run the Mailman test suite, just use the `tox`_ command::

    $ tox

`tox` creates a virtual environment (virtualenv) for you, installs all the
dependencies into that virtualenv, and runs the test suite from that
virtualenv.  By default it does not use the `--system-site-packages` so it
downloads everything from the Cheeseshop.

You do have access to the virtualenv, and you can use this to run individual
tests, e.g.::

    $ .tox/py34/bin/python -m nose2 -vv -P user

Use `.tox/py34/bin/python -m nose2 --help` for more options.

If you want to run the full test suite against the PostgreSQL database, set
the database up as described in :doc:`DATABASE`, then create a `postgres.cfg`
file any where you want.  This `postgres.cfg` file will contain the
``[database]`` section for PostgreSQL, e.g.::

    [database]
    class: mailman.database.postgresql.PostgreSQLDatabase
    url: postgres://myuser:mypassword@mypghost/mailman

Then run the test suite like so::

    $ MAILMAN_EXTRA_TESTING_CFG=/path/to/postgres.cfg tox -e pg

If you want to run an individual test against PostgreSQL, you would do it like
so::

    $ MAILMAN_EXTRA_TESTING_CFG=/path/to/postgres.cfg .tox/pg/bin/python -m nose2 -vv -P user


Building for development
------------------------

To build Mailman for development purposes, you can create a virtual
environment outside of tox.  You need to have the `virtualenv`_ program
installed.

First, create a virtual environment.  By default ``virtualenv`` uses the
``python`` executable it finds first on your ``$PATH``.  Make sure this is
Python 3.4 (just start the interactive interpreter and check the version in
the startup banner).  The directory you install the virtualenv into is up to
you, but for purposes of this document, we'll install it into ``/tmp/mm3``::

    % virtualenv -p python3 --system-site-packages /tmp/mm3

If your default Python is not version 3.4, use the ``--python`` option to
specify the Python executable.  You can use the command name if this version
is on your ``PATH``::

    % virtualenv --system-site-packages --python=python3.4 /tmp/mm3

or you may specify the full path to any Python 3.4 executable.

Now, activate the virtual environment and set it up for development::

    % source /tmp/mm3/bin/activate
    % python setup.py develop

Sit back and have some Kombucha while you wait for everything to download and
install.

Build the online docs by running::

    % python setup.py build_sphinx

If ``setup.py`` fails to recognize the ``build_sphinx`` command, then
just install Sphinx in your virtualenv::

    % pip install sphinx

This will automatically add the ``build_sphinx`` command to
``setup.py``, so just re-run the command.

Then visit::

    build/sphinx/html/index.html

in your browser to start reading the documentation.  Or you can just read the
doctests by looking in all the 'doc' directories under the 'mailman' package.
Doctests are documentation first, so they should give you a pretty good idea
how various components of Mailman 3 work.

Once everything is downloaded and installed, you can initialize Mailman and
get a display of the basic configuration settings by running::

    $ mailman info -v


Running Mailman 3
=================

What, you actually want to *run* Mailman 3?  Oh well, if you insist.  You will
need to set up a configuration file to override the defaults and set things up
for your environment.  Mailman is configured using an "ini"-style
configuration system.

``src/mailman/config/schema.cfg`` defines the ini-file schema and contains
documentation for every section and configuration variable.  Sections that end
in `.template` or `.master` are templates that must be overridden in actual
configuration files.  There is a default configuration file that defines these
basic overrides in ``src/mailman/config/mailman.cfg``.  Your own configuration
file will override those.

By default, all runtime files are put under a `var` directory in the current
working directory.

Mailman searches for its configuration file using the following search path.
The first existing file found wins.

 * ``-C config`` command line option
 * ``$MAILMAN_CONFIG_FILE`` environment variable
 * ``./mailman.cfg``
 * ``~/.mailman.cfg``
 * ``/etc/mailman.cfg``
 * ``argv[0]/../../etc/mailman.cfg``

Run the ``mailman info`` command to see which configuration file Mailman
will use, and where it will put its database file.  The first time you run
this, Mailman will also create any necessary run-time directories and log
files.

Try ``mailman --help`` for more details.  You can use the commands
``mailman start`` to start the runner subprocess daemons, and of course
``mailman stop`` to stop them.

Postorius, a web UI for administration and subscriber settings, is being
developed as a separate, Django-based project.  For now, the most flexible
means of configuration is via the command line and REST API.


Mailman Web UI
--------------

The Mailman 3 web UI, called *Postorius*, interfaces to core Mailman engine
via the REST client API.  It is expected that this architecture will make it
possible for users with other needs to adapt the web UI, or even replace it
entirely, with a reasonable amount of effort.  However, as a core feature of
Mailman, the web UI will emphasize usability over modularity at first, so most
users should use the web UI described here.

Postorius was prototyped at the `Pycon 2012 sprint`_, so it is "very alpha" as
of Mailman 3 beta 1, and comes in several components.  In particular, it
requires a `Django`_ installation, and Bazaar checkouts of the `REST client
module`_ and `Postorius`_ itself.  Building it is fairly straightforward,
based on Florian Fuchs' `Five Minute Guide` from his `blog post`_ on the
Mailman wiki.  (Check the `blog post`_ for the most recent version!)


The Archiver
------------

In Mailman 3, the archivers are decoupled from the core engine.  Instead,
Mailman 3 provides a simple, standard interface for third-party archiving tools
and services.  For this reason, Mailman 3 defines a formal interface to insert
messages into any of a number of configured archivers, using whatever protocol
is appropriate for that archiver.  Summary, search, and retrieval of archived
posts are handled by a separate application.

A new archive UI called `Hyperkitty`_, based on the `notmuch mail indexer`_
and `Django`_, was prototyped at the PyCon 2012 sprint by Toshio Kuratomi, and
like the web UI it is also in early alpha as of Mailman 3 beta 1.  The
Hyperkitty archiver is very loosely coupled to Mailman 3 core.  In fact, any
email application that speaks LMTP or SMTP will be able to use Hyperkitty.

A `five minute guide to Hyperkitty`_ is based on Toshio Kuratomi's README.


.. _`Postorius`: https://launchpad.net/postorius
.. _`Hyperkitty`: https://launchpad.net/hyperkitty
.. _`Django`: http://djangoproject.org/
.. _`REST client module`: https://launchpad.net/mailman.client
.. _`Five Minute Guide the Web UI`: WebUIin5.html
.. _`blog post`: http://wiki.list.org/display/DEV/A+5+minute+guide+to+get+the+Mailman+web+UI+running
.. _`notmuch mail indexer`: http://notmuchmail.org
.. _`five minute guide to Hyperkitty`: ArchiveUIin5.html
.. _`Pycon 2012 sprint`: https://us.pycon.org/2012/community/sprints/projects/
.. _`Python Cheeseshop`: http://pypi.python.org/pypi
.. _`virtualenv`: http://www.virtualenv.org/en/latest/
.. _`Mailman 3 documentation`: http://www.pythonhosted.org/mailman/
.. _`Postorius documentation`: http://www.pythonhosted.org/postorius/
.. _`HyperKitty documentation`: https://hyperkitty.readthedocs.org/en/latest/development.html
.. _`Development Setup Guide`: https://fedorahosted.org/hyperkitty/wiki/DevelopmentSetupGuide
.. _tox: https://testrun.org/tox/latest/
