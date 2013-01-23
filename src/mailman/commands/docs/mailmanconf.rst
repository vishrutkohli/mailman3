==================
Display configuration values
==================

Just like the postfix command postconf(1), mailmanconf lets you dump
one or more mailman configuration variables. Internally, these can be
retrieved by using the mailman.config.config object. Their structure
is based on the schema given by src/mailman/config/schema.cfg.
For more information on how the values are actually set, see
src/mailman/docs/START.rst

Basically, the configuration is divided in multiple sections which
contain multiple key-value pairs. The ``bin/mailman mailmanconf``
command allows you to display a specific or several key-value pairs.

    >>> class FakeArgs:
    ...     key = None
    ...     section = None
    ...     output = None
    >>> from mailman.commands.cli_mailmanconf import Mailmanconf
    >>> command = Mailmanconf()

To get a list of all key-value pairs of any section, you need to call
the command without any options.

    >>> command.process(FakeArgs)
    ... [logging.archiver] path: mailman.log
    ... [logging.archiver] level: info
    ... [logging.locks] propagate: no
    ... [logging.locks] level: info
    ... [passwords] configuration: python:mailman.config.passlib
    ... etc.
    
You can list all the key-value pairs of a specific section.

    >>> FakeArgs.section = 'mailman'
    >>> command.process(FakeArgs)
    ... [mailman] filtered_messages_are_preservable: no
    ... [mailman] post_hook: 
    ... [mailman] pending_request_life: 3d
    ... etc.
    
You can also pass a key and display all key-value pairs matching
the given key, along with the names of the corresponding sections.

    >>> FakeArgs.section = 'None'
    >>> FakeArgs.key = 'path'
    >>> command.process(FakeArgs)
    ... [logging.archiver] path: mailman.log
    ... [logging.mischief] path: mailman.log
    ... [logging.error] path: mailman.log
    ... [logging.smtp] path: smtp.log
    ... etc.
    
If you specify both a section and a key, you will get the corresponding value.

    >>> FakeArgs.section = 'mailman'
    >>> FakeArgs.key = 'site_owner'
    >>> command.process(FakeArgs)
    ... changeme@example.com
    