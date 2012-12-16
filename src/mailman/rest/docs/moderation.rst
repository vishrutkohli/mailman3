==========
Moderation
==========

There are two kinds of moderation tasks a list administrator may need to
perform.  Messages which are held for approval can be accepted, rejected,
discarded, or deferred.  Subscription (and sometimes unsubscription) requests
can similarly be accepted, discarded, rejected, or deferred.


Message moderation
==================

Viewing the list of held messages
---------------------------------

Held messages can be moderated through the REST API.  A mailing list starts
with no held messages.

    >>> ant = create_list('ant@example.com')
    >>> transaction.commit()
    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held')
    http_etag: "..."
    start: 0
    total_size: 0

When a message gets held for moderator approval, it shows up in this list.
::

    >>> msg = message_from_string("""\
    ... From: anne@example.com
    ... To: ant@example.com
    ... Subject: Something
    ... Message-ID: <alpha>
    ...
    ... Something else.
    ... """)

    >>> from mailman.app.moderator import hold_message
    >>> request_id = hold_message(ant, msg, {'extra': 7}, 'Because')
    >>> transaction.commit()

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/held')
    entry 0:
        extra: 7
        hold_date: 2005-08-01T07:49:23
        http_etag: "..."
        message_id: <alpha>
        msg: From: anne@example.com
    To: ant@example.com
    Subject: Something
    Message-ID: <alpha>
    X-Message-ID-Hash: GCSMSG43GYWWVUMO6F7FBUSSPNXQCJ6M
    <BLANKLINE>
    Something else.
    <BLANKLINE>
        reason: Because
        request_id: 1
        sender: anne@example.com
        subject: Something
    http_etag: "..."
    start: 0
    total_size: 1

You can get an individual held message by providing the *request id* for that
message.  This will include the text of the message.
::

    >>> def url(request_id):
    ...     return ('http://localhost:9001/3.0/lists/'
    ...             'ant@example.com/held/{0}'.format(request_id))

    >>> dump_json(url(request_id))
    extra: 7
    hold_date: 2005-08-01T07:49:23
    http_etag: "..."
    message_id: <alpha>
    msg: From: anne@example.com
    To: ant@example.com
    Subject: Something
    Message-ID: <alpha>
    X-Message-ID-Hash: GCSMSG43GYWWVUMO6F7FBUSSPNXQCJ6M
    <BLANKLINE>
    Something else.
    <BLANKLINE>
    reason: Because
    request_id: 1
    sender: anne@example.com
    subject: Something


Disposing of held messages
--------------------------

Individual messages can be moderated through the API by POSTing back to the
held message's resource.   The POST data requires an action of one of the
following:

  * discard - throw the message away.
  * reject - bounces the message back to the original author.
  * defer - defer any action on the message (continue to hold it)
  * accept - accept the message for posting.

Let's see what happens when the above message is deferred.

    >>> dump_json(url(request_id), {
    ...     'action': 'defer',
    ...     })
    content-length: 0
    date: ...
    server: ...
    status: 204

The message is still in the moderation queue.

    >>> dump_json(url(request_id))
    extra: 7
    hold_date: 2005-08-01T07:49:23
    http_etag: "..."
    message_id: <alpha>
    msg: From: anne@example.com
    To: ant@example.com
    Subject: Something
    Message-ID: <alpha>
    X-Message-ID-Hash: GCSMSG43GYWWVUMO6F7FBUSSPNXQCJ6M
    <BLANKLINE>
    Something else.
    <BLANKLINE>
    reason: Because
    request_id: 1
    sender: anne@example.com
    subject: Something

The held message can be discarded.

    >>> dump_json(url(request_id), {
    ...     'action': 'discard',
    ...     })
    content-length: 0
    date: ...
    server: ...
    status: 204

After which, the message is gone from the moderation queue.

    >>> dump_json(url(request_id))
    Traceback (most recent call last):
    ...
    HTTPError: HTTP Error 404: 404 Not Found

Messages can also be accepted via the REST API.  Let's hold a new message for
moderation.
::

    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<bravo>'
    >>> request_id = hold_message(ant, msg)
    >>> transaction.commit()

    >>> results = call_http(url(request_id))
    >>> print results['message_id']
    <bravo>

    >>> dump_json(url(request_id), {
    ...     'action': 'accept',
    ...     })
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('pipeline')
    >>> len(messages)
    1
    >>> print messages[0].msg['message-id']
    <bravo>

Messages can be rejected via the REST API too.  These bounce the message back
to the original author.
::

    >>> del msg['message-id']
    >>> msg['Message-ID'] = '<charlie>'
    >>> request_id = hold_message(ant, msg)
    >>> transaction.commit()

    >>> results = call_http(url(request_id))
    >>> print results['message_id']
    <charlie>

    >>> dump_json(url(request_id), {
    ...     'action': 'reject',
    ...     })
    content-length: 0
    date: ...
    server: ...
    status: 204

    >>> from mailman.testing.helpers import get_queue_messages
    >>> messages = get_queue_messages('virgin')
    >>> len(messages)
    1
    >>> print messages[0].msg['subject']
    Request to mailing list "Ant" rejected


Subscription moderation
=======================

Viewing subscription requests
-----------------------------

Subscription and unsubscription requests can be moderated via the REST API as
well.  A mailing list starts with no pending subscription or unsubscription
requests.

    >>> ant.admin_immed_notify = False
    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/requests')
    http_etag: "..."
    start: 0
    total_size: 0

When Anne tries to subscribe to the Ant list, her subscription is held for
moderator approval.

    >>> from mailman.app.moderator import hold_subscription
    >>> from mailman.interfaces.member import DeliveryMode
    >>> hold_subscription(
    ...     ant, 'anne@example.com', 'Anne Person',
    ...     'password', DeliveryMode.regular, 'en')
    1
    >>> transaction.commit()

The subscription request is available from the mailing list.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/requests')
    entry 0:
        address: anne@example.com
        delivery_mode: regular
        display_name: Anne Person
        http_etag: "..."
        language: en
        password: password
        request_id: 1
        type: subscription
        when: 2005-08-01T07:49:23
    http_etag: "..."
    start: 0
    total_size: 1


Viewing unsubscription requests
-------------------------------

Bart tries to leave a mailing list, but he may not be allowed to.

    >>> from mailman.app.membership import add_member
    >>> from mailman.app.moderator import hold_unsubscription
    >>> bart = add_member(ant, 'bart@example.com', 'Bart Person',
    ...     'password', DeliveryMode.regular, 'en')
    >>> hold_unsubscription(ant, 'bart@example.com')
    2
    >>> transaction.commit()

The unsubscription request is also available from the mailing list.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/requests')
    entry 0:
        address: anne@example.com
        delivery_mode: regular
        display_name: Anne Person
        http_etag: "..."
        language: en
        password: password
        request_id: 1
        type: subscription
        when: 2005-08-01T07:49:23
    entry 1:
        address: bart@example.com
        http_etag: "..."
        request_id: 2
        type: unsubscription
    http_etag: "..."
    start: 0
    total_size: 2


Viewing individual requests
---------------------------

You can view an individual membership change request by providing the
request id.  Anne's subscription request looks like this.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/requests/1')
    address: anne@example.com
    delivery_mode: regular
    display_name: Anne Person
    http_etag: "..."
    language: en
    password: password
    request_id: 1
    type: subscription
    when: 2005-08-01T07:49:23

Bart's unsubscription request looks like this.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/requests/2')
    address: bart@example.com
    http_etag: "..."
    request_id: 2
    type: unsubscription


Disposing of subscription requests
----------------------------------

Similar to held messages, you can dispose of held subscription and
unsubscription requests by POSTing back to the request's resource.  The POST
data requires an action of one of the following:

 * discard - throw the request away.
 * reject - the request is denied and a notification is sent to the email
            address requesting the membership change.
 * defer - defer any action on this membership change (continue to hold it).
 * accept - accept the membership change.

Anne's subscription request is accepted.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'ant@example.com/requests/1', {
    ...           'action': 'accept',
    ...           })
    content-length: 0
    date: ...
    server: ...
    status: 204

Anne is now a member of the mailing list.

    >>> transaction.abort()
    >>> ant.members.get_member('anne@example.com')
    <Member: Anne Person <anne@example.com> on ant@example.com
             as MemberRole.member>
    >>> transaction.abort()

Bart's unsubscription request is discarded.

    >>> dump_json('http://localhost:9001/3.0/lists/'
    ...           'ant@example.com/requests/2', {
    ...           'action': 'discard',
    ...           })
    content-length: 0
    date: ...
    server: ...
    status: 204

Bart is still a member of the mailing list.

    >>> transaction.abort()
    >>> print ant.members.get_member('bart@example.com')
    <Member: Bart Person <bart@example.com> on ant@example.com
             as MemberRole.member>
    >>> transaction.abort()

There are no more membership change requests.

    >>> dump_json('http://localhost:9001/3.0/lists/ant@example.com/requests')
    http_etag: "..."
    start: 0
    total_size: 0
