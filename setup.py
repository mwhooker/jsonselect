import jsonselect

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='jsonselect',
    version=jsonselect.__version__,
    description='Python implementation of jsonselect (http://jsonselect.org/)',
    long_description=open('README').read(),
    author='Matthew Hooker',
    author_email='mwhooker@gmail.com',
    url='https://github.com/mwhooker/jsonselect',
    license='ISC',
    packages=['jsonselect', 'tests'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    keywords=[
        'json'
    ]
)
