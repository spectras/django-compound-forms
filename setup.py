from distutils.core import setup

setup(
    name='django-compound-forms',
    version='0.1.0',
    author='Julien Hartmann',
    author_email='juli1.hartmann@gmail.com',
    packages=['compound_forms'],
    url='http://pypi.python.org/pypi/django-compound-forms/',
    license='LICENSE.txt',
    description='Dynamic and static form composition for Django.',
    long_description=open('README.txt').read(),
    install_requires=[
        "Django >= 1.6",
    ],
)
