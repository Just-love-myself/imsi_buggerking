from setuptools import setup, find_packages

setup (
    name='buggerking',
    version='0.1.5',
    description='test buggerking package',
    author='DogyunHyunseoKyeongyeon',
    author_email='hyunseo0412@naver.com',
    url='https://github.com/hyunseopythonl/buggerking',
    license='MIT',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.6',
    install_requires=[
        "requests",
        "click>=8.0",
        "colorama",
    ],
    entry_points={
        'console_scripts': [
            'buggerking = buggerking.cli:main'
        ]
    },
    zip_safe=False
)
