from setuptools import setup, find_packages

setup(
    name="pronunciation-mapper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "jamo",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A pronunciation-based mapping system for ASR output to database terms",
    keywords="ASR, speech recognition, database, pronunciation",
    url="https://github.com/hyeonsangjeon/pronunciation-mapper",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.6",
    entry_points={
        'console_scripts': [
            'pronunciation-mapper=pronunciation_mapper.cli:main',
        ],
    },
)