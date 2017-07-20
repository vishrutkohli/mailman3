# Systers-Mailman3

Mailman is written in Python which is available for all platforms that Mailman is supported on, including GNU/Linux and most other Unix-like operating systems.Mailman is not supported on Windows, although web and mail clients on any platform should be able to interact with Mailman just fine.

[Mailman Home Page](http://www.list.org/)

**GNU Mailman 3** is actually a suite of 6 or 7 subprojects:

* 1\.Mailman Core - the core delivery engine which accepts messages, providers moderation and processing of the messages, and delivers messages to mailing list member recipients. It exposes its functionality to other components over a private, administrative REST API.

* 2\.Postorius - A new Django-based web user interface for end users and list administrators.

* 3\.HyperKitty - A new Django-based web archiver.

* 4\.mailman-hyperkitty - A plugin for the core to communicate with HyperKitty.

* 5\.django-mailman3 - Django modules and templates common to Postorius and HyperKitty (New in mailman 3.1).

* 6\.mailmanclient - The official Python 2 and 3 bindings to the administrative REST API. Used by Postorius and HyperKitty, this provides a convenient, object-based API for programmatic access to the Core.

The Core is required. Postorius and HyperKitty are awesome, and highly recommended, but you could of course roll your own web ui and archiver. mailman.client is useful, but you could always program directly against the REST API. 


**Systers** is an international community of over 3,000 women involved in technical-computing. The community uses a custom version of Mailman3, that includes : 
* 1\. Essay Feature
* 2\. Stats for Admins
    * 2.1\.Number of unsubscribers through different channels.
    * 2.2\.Number of total unique subject lines.
    * 2.3\.Number of subscribers that posted.

___
Systers was founded by Anita Borg in 1987 as a small electronic mailing list for women in “systems”. Today, Systers broadly promotes the interests of women in the computing and technology fields. Anita created Systers to “increase the number of women in computer science and make the environments in which women work more conducive to their continued participation in the field.” The Systers community serves this purpose by providing women a private space to seek advice from their peers, and discuss the challenges they share as women technologist.

[Homepage](https://anitaborg.org/get-involved/systers/)
