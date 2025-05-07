from setuptools import setup, find_packages

setup(
    name='diagnostic_analyzer_package', 
    version='0.1.0', 
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'diagnostic_analyzer_package': ['ThreadGroups.json'],
    },
    install_requires=[
        'openai',
    ],
)