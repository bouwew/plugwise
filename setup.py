from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name='plugwise',
    version='0.0.19',
    description='Plugwise API to use in conjunction with Home Assistant.',
    long_description='Plugwise API supporting Adam and Anna/Smile (firmware 3.x and up) to use in conjunction with Home Assistant, but it can also be used without Home Assistant.',
    keywords='Home Assistant HA Adam Anna Smile Lisa Tom Floor Plugwise',
    url='https://github.com/bouwew/plugwise',
    author='bouwew',
    author_email='bouwe.s.westerdijk@gmail.com',
    license='MIT',
    packages=['plugwise'],
    install_requires=['requests','datetime','pytz'],
    zip_safe=False
)
