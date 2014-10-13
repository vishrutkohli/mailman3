============================
Display configuration values
============================

Just like the `Postfix command postconf(1)`_, the ``bin/mailman conf`` command
lets you dump one or more Mailman configuration variables to standard output
or a file.

Mailman's configuration is divided in multiple sections which contain multiple
key-value pairs.  The ``bin/mailman conf`` command allows you to display
a specific key-value pair, or several key-value pairs.

    >>> class FakeArgs:
    ...     key = None
    ...     section = None
    ...     output = None
    ...     sort = False
    >>> from mailman.commands.cli_conf import Conf
    >>> command = Conf()

To get a list of all key-value pairs of any section, you need to call the
command without any options.

    >>> command.process(FakeArgs)
    [alembic] script_location: mailman.database:alembic
    ...
    [passwords] password_length: 8
    ...
    [mailman] site_owner: noreply@example.com
    ...

You can list all the key-value pairs of a specific section.

    >>> FakeArgs.section = 'shell'
    >>> command.process(FakeArgs)
    [shell] use_ipython: no
    [shell] banner: Welcome to the GNU Mailman shell
    [shell] prompt: >>>

You can also pass a key and display all key-value pairs matching the given
key, along with the names of the corresponding sections.

    >>> FakeArgs.section = None
    >>> FakeArgs.key = 'path'
    >>> command.process(FakeArgs)
    [logging.archiver] path: mailman.log
    [logging.locks] path: mailman.log
    [logging.mischief] path: mailman.log
    [logging.config] path: mailman.log
    [logging.error] path: mailman.log
    [logging.smtp] path: smtp.log
    [logging.database] path: mailman.log
    [logging.http] path: mailman.log
    [logging.root] path: mailman.log
    [logging.fromusenet] path: mailman.log
    [logging.bounce] path: bounce.log
    [logging.vette] path: mailman.log
    [logging.runner] path: mailman.log
    [logging.subscribe] path: mailman.log
    [logging.debug] path: debug.log

If you specify both a section and a key, you will get the corresponding value.

    >>> FakeArgs.section = 'mailman'
    >>> FakeArgs.key = 'site_owner'
    >>> command.process(FakeArgs)
    noreply@example.com

You can also sort the output.  The output is first sorted by section, then by
key.

    >>> FakeArgs.key = None
    >>> FakeArgs.section = 'shell'
    >>> FakeArgs.sort = True
    >>> command.process(FakeArgs)
    [shell] banner: Welcome to the GNU Mailman shell
    [shell] prompt: >>>
    [shell] use_ipython: no


.. _`Postfix command postconf(1)`: http://www.postfix.org/postconf.1.html
