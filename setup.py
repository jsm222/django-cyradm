import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-cyradm',
    version='0.1.3',
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
        'Framework :: Django :: 3.0.2',
        'Intended Audience :: System administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
        'Programming Language :: Python :: 3.7'
    ],
    setup_requires=["wheel"],
    install_requires=["wheel",
                      "Babel==2.9.1",
                      "Django==3.1.13",
                      "django-axes==5.2.2",
                      "django-bootstrap3==12.0.3",
                      "django-filter==2.4.0",
                      "django-ipware==2.1.0",
                      "django-ranged-response==0.2.0",
                      "django-session-security==2.6.6",
                      "django-simple-captcha==0.5.12",
                      "django-tables2==2.4.0",
                      "humanize==0.5.1",
                      "rules==3.3"
                      ]
)
