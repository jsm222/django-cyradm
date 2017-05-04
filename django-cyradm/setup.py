import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-cyradm',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    license='BSD License', 
    description='A Django app to administrate postfix mail transfer agent.',
    long_description=README,
    url='https://djcyradm.schmitz.computer/',
    author='Jesper Schmitz Mouridsen',
    author_email='jesper@schmitz.computer',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Intended Audience :: System administrators',
        'License :: OSI Approved :: BSD License',  
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ],
    install_requires=['django_tables2', 'django-bootstrap3', 'django-session_security', 'rules', 'django-axes',
                      'django-simple-captcha', 'django-filter', 'humanize']
)
