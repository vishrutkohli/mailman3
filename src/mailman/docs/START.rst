.. _start-here:

================================
Getting started with GNU Mailman
================================

Copyright (C) 2008-2012 by the Free Software Foundation, Inc.


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
archiver (known as `Hyperkitty`_) are in separate development.

Contributions are welcome.  Please submit bug reports on the Mailman bug
tracker at https://bugs.launchpad.net/mailman though you will currently need
to have a login on Launchpad to do so.  You can also send email to the
mailman-developers@python.org mailing list.


Requirements
============

Python 2.7 is required.  It can either be the default 'python' on your
``$PATH`` or it can be accessible via the ``python2.7`` binary.
If your operating system does not include Python, see http://www.python.org
downloading and installing it from source.  Python 3 is not yet supported.

In this documentation, a bare ``python`` refers to the Python executable used
to invoke ``bootstrap.py``.

Mailman 3 is now based on the `zc.buildout`_ infrastructure, which greatly
simplifies testing Mailman.  Buildout is not required for installation.

During the beta program, you may need some additional dependencies, such as a
C compiler and the Python development headers and libraries.  You will need an
internet connection.


Building Mailman 3
==================

We provide several recipes for building Mailman.  All should generally work,
but some may provide a better experience for developing Mailman versus
deploying Mailman.


Building for development
------------------------

The best way to build Mailman for development is to use the `zc.buildout`_
tools.  This will download all Mailman dependencies from the `Python
Cheeseshop`_.  The dependencies will get installed locally, but isolated from
your system Python.  Here are the commands to build Mailman for development::

    % python bootstrap.py
    % bin/buildout

Sit back and have some Kombucha while you wait for everything to download and
install.

Now you can run the test suite via::

    % bin/test -vv

You should see no failures.

Build the online docs by running::

    % python setup.py build_sphinx

Then visit::

    build/sphinx/html/index.html

in your browser to start reading the documentation.  Or you can just read the
doctests by looking in all the 'doc' directories under the 'mailman' package.
Doctests are documentation first, so they should give you a pretty good idea
how various components of Mailman 3 work.


Building for deployment using virtualenv
----------------------------------------

`virtualenv`_ is a way to create isolated Python environments.  You can use
virtualenv as a way to deploy Mailman without installing it into your system
Python.  There are lots of ways to use virtualenv, but as described here, it
will be default use any dependencies which are already installed in your
system, downloading from the Cheeseshop only those which are missing.  Here
are the steps to install Mailman using virtualenv::

    $ virtualenv --system-site-packages /path/to/your/installation
    $ source /path/to/your/installation/bin/activate
    $ python setup.py install

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

Run the ``bin/mailman info`` command to see which configuration file Mailman
will use, and where it will put its database file.  The first time you run
this, Mailman will also create any necessary run-time directories and log
files.

Try ``bin/mailman --help`` for more details.  You can use the commands
``bin/mailman start`` to start the runner subprocess daemons, and of course
``bin/mailman stop`` to stop them.

Postorius is being developed as a separate, Django-based project.  For now,
all configuration happens via the command line and REST API.


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
however, given Florian Fuchs' `Five Minute Guide` from his `blog post`_ on the
Mailman wiki.  (Check the `blog post`_ for the most recent version!)


The Archiver
------------

In Mailman 3, the archivers are decoupled from the core engine.  It is useful
to provide a simple, standard interface for third-party archiving tools and
services.  For this reason, Mailman 3 defines a formal interface to insert
messages into any of a number of configured archivers, using whatever protocol
is appropriate for that archiver.  Summary, search, and retrieval of archived
posts are handled by a separate application.

A new archive UI called `Hyperkitty`_, based on the `notmuch mail indexer`_
and `Django`_, was prototyped at the PyCon 2012 sprint by Toshio Kuratomi, and
like the web UI it is also in early alpha as of Mailman 3 beta 1.  The
Hyperkitty archiver is very loosely coupled to Mailman 3 core.  In fact, any
email application that speaks LMTP or SMTP will be able to use Hyperkitty.

A `five minute guide to Hyperkitty`_ is based on Toshio Kuratomi's README.


.. _`zc.buildout`: http://pypi.python.org/pypi/zc.buildout
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
