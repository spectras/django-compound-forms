#########################
Compound Forms for Django |build|
#########################

This allows building forms that encompass other forms. Either dynamically,
by giving already-instanciated forms to one of the Proxy variants, or statically,
building a Compound form class that manages and instanciates subforms by itself.

The purpose is to ease the use of packages such as crispy-forms: a layout applied
to a Compound form can re-order fields through all sub-forms.

Just shared as is for now. Further development into a fully grown module is
intended, but not yet planned.

- Supports python 2.7, 3.3 and 3.4.
- Supports Django 1.5, 1.6 and 1.7.

It is not documented yet, though it will feel familiar if you used django
forms and formsets for a while. It is quite well tested though, with code
coverage above 90%.

If you use it, please drop me a line to let me know. Pull requests are welcome
as well.

.. |build| image:: https://travis-ci.org/spectras/django-compound-forms.svg?branch=master
    :target: https://travis-ci.org/spectras/django-compound-forms
